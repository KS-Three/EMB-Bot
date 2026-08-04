// digitizer.js — Studio's side of the auto-digitize seam (build step 10).
//
// Three jobs, one module, because they are one contract:
//
//   1. CLIENT — talk to the localhost digitizer service (GET /health,
//      POST /digitize, poll GET /jobs/{id}). Every function takes an optional
//      fetch so specs can stub the wire without a network.
//   2. ADAPTER — turn the service's result into what the engine's
//      buildImportedDesign eats. THE LOAD-BEARING CONTRACT: /digitize returns
//      an EMB-Bot Design ({ stitches:[{x,y,type}], colors, widthMM, heightMM },
//      integer 0.1 mm units, +y UP — see digitizer_core/adapter.py, which owns
//      the one y-flip). That is the SAME space decodeDST outputs, so a
//      digitized element rides the imported-design path for scale/clamp/
//      rotate/offset and no second flip ever happens here. The fixture spec
//      (fixtures/digitized-asym.json, captured from the live service) pins
//      this: flip an axis anywhere and it fails.
//   3. WARNINGS — translate the pipeline's machine-readable warning codes
//      (digitizer_core/warnings_codes.py: UI switches on codes, never prose)
//      into customer language.
//
// No DST ever crosses this boundary (the JS/pyembroidery DST axis dispute is
// deliberately routed around it): Studio bakes its own machine files from the
// Design with its own encoder, same as lettering.

import { loadPreferredPaletteId } from "./threads.js";
import { DEFAULT_DIGITIZE_PARAMS } from "./project.js";

// The service binds 127.0.0.1:8721 by default (digitizer_service/__main__.py).
// The localStorage override is a dev/ops seam — e.g. a second instance on
// another port — never a way to leave the machine.
export const DIGITIZER_URL_KEY = "embstudio:digitizerUrl";
export const DEFAULT_DIGITIZER_URL = "http://127.0.0.1:8721";

export function digitizerUrl() {
  try {
    return localStorage.getItem(DIGITIZER_URL_KEY) || DEFAULT_DIGITIZER_URL;
  } catch (e) {
    return DEFAULT_DIGITIZER_URL;
  }
}

// ---- client ----------------------------------------------------------------

// GET /health, null on ANY failure (down, refused, non-ok, bad JSON). Studio
// gates the whole auto-digitize feature on this returning an object.
export async function fetchHealth(fetchFn = globalThis.fetch) {
  try {
    const r = await fetchFn(digitizerUrl() + "/health");
    if (!r.ok) return null;
    const h = await r.json();
    return h && h.status === "ok" ? h : null;
  } catch (e) {
    return null;
  }
}

// The exact /digitize config for an element. Field names are PipelineConfig's
// own (digitizer_core/config.py) — element.params stores them verbatim so the
// persisted params ARE the request, with only per-request context added here:
//   thread_brand — the user's stored brand preference (embstudio:threadPalette,
//     via threads.js). NEVER hardcoded. "studio" is Studio's generic palette,
//     not a manufacturer chart the service knows, so it is omitted and the
//     service default applies. A genuinely unknown brand 400s server-side by
//     design (the operator buys the cone the palette names).
//   garment_id — the project's garment, which picks the fabric preset (pull
//     compensation, underlay, density) service-side. Ids match by construction
//     (digitizer_core/fabrics.py mirrors the engine's GARMENT_FABRIC).
// fill_angle_deg is omitted when null: null means "per-shape auto" and the
// service treats an absent key the same way — omitting keeps the config (and
// the job cache key) minimal.
export function buildDigitizeConfig(element, project) {
  const p = { ...DEFAULT_DIGITIZE_PARAMS, ...((element && element.params) || {}) };
  const cfg = {
    target_width_mm: p.target_width_mm,
    max_colors: p.max_colors,
    satin: p.satin,
    border: p.border,
  };
  if (p.fill_angle_deg != null) cfg.fill_angle_deg = p.fill_angle_deg;
  const brand = loadPreferredPaletteId();
  if (brand && brand !== "studio") cfg.thread_brand = brand;
  if (project && project.garmentId) cfg.garment_id = project.garmentId;
  // Shape-layers edits (contract v1) ride the same config — already in the
  // service's canonical spelling (canonicalShapeEdits below), so the job
  // cache key changes exactly when an edit changes and a no-op edit stays a
  // cache hit.
  const edits = canonicalShapeEdits(element || {});
  if (edits.deleted_shape_ids) cfg.deleted_shape_ids = edits.deleted_shape_ids;
  if (edits.shape_overrides) cfg.shape_overrides = edits.shape_overrides;
  // A recolor's thread_index indexes the CHART OF THE JOB IT WAS PICKED
  // AGAINST (element.review.brandId). If the user's brand preference moved
  // on since, sending the new brand would silently re-aim every picked
  // index at a different manufacturer's numbers — so a config carrying
  // recolors pins the brand the indexes were computed for.
  if (
    edits.shape_overrides &&
    Object.values(edits.shape_overrides).some((e) => e.thread_index != null) &&
    element && element.review && element.review.brandId
  ) {
    cfg.thread_brand = element.review.brandId;
  }
  return cfg;
}

// ---- shape-layers edits (review-screen contract v1) ------------------------

// Closed vocabularies, mirrored from the service's _canonicalize_shape_edits
// (digitizer_service/app.py). "auto" tier is the absence of an override on
// both ends.
const SHAPE_TIERS = new Set(["satin", "fill", "run"]);
const SHAPE_BORDERS = new Set(["off", "auto", "bean"]);

// The element's shape edits in the service's own canonical wire form:
// deleted ids sorted + deduped, override keys sorted, null/"auto"/app-only
// fields (rgb) dropped, empty entries dropped, and overrides for deleted
// shapes omitted (the engine would only warn SHAPE_EDIT_UNKNOWN_ID for
// them). Canonical HERE, not just server-side, because the panel compares
// this against `element.appliedEdits` to know whether edits are pending —
// two spellings of the same edit must never read as "pending changes".
//
// `stitched` (BACKGROUND_ENCLOSED restore, contract v1.1) is a plain
// boolean, not a closed vocabulary: `true` restores a shape the digitizer
// excluded by default (an enclosed-background region — see reviewFromJob's
// `stitched` mapping), `false` explicitly excludes one. Unlike the other
// fields it has no "auto" spelling — the absence of the key IS auto,
// exactly like every other override here.
//
// `sew_order` (contract v1.2) is a shape's explicit position within its OWN
// color layer's sew sequence — distinct from `layer`, which picks WHICH
// layer a shape sews in. Like `layer`, absence is the whole "no override"
// spelling (there is no "auto" word for it): the service falls back to
// nearest-neighbour for any shape in the layer that carries no override.
export function canonicalShapeEdits(element) {
  const out = {};
  const deleted = Array.from(new Set(element.deletedShapeIds || []))
    .filter((s) => typeof s === "string" && s)
    .sort();
  if (deleted.length) out.deleted_shape_ids = deleted;
  const del = new Set(deleted);
  const src = element.shapeOverrides || {};
  const overrides = {};
  for (const sid of Object.keys(src).sort()) {
    if (del.has(sid)) continue;
    const e = src[sid] || {};
    const entry = {};
    if (Number.isInteger(e.thread_index) && e.thread_index >= 0) entry.thread_index = e.thread_index;
    if (typeof e.fill_angle_deg === "number" && isFinite(e.fill_angle_deg)) entry.fill_angle_deg = e.fill_angle_deg;
    if (SHAPE_TIERS.has(e.tier)) entry.tier = e.tier;
    if (SHAPE_BORDERS.has(e.border)) entry.border = e.border;
    if (Number.isInteger(e.layer)) entry.layer = e.layer;
    if (typeof e.stitched === "boolean") entry.stitched = e.stitched;
    if (Number.isInteger(e.sew_order) && e.sew_order >= 0) entry.sew_order = e.sew_order;
    if (Object.keys(entry).length) overrides[sid] = entry;
  }
  if (Object.keys(overrides).length) out.shape_overrides = overrides;
  return out;
}

// Stable string identity for a canonical edit set (canonicalShapeEdits
// builds its objects in sorted key order, so JSON.stringify is
// deterministic). Stored as element.appliedEdits when a result lands;
// compared against the current edits to drive the "Apply changes" state.
export function editsKey(edits) {
  return JSON.stringify([
    (edits && edits.deleted_shape_ids) || [],
    (edits && edits.shape_overrides) || {},
  ]);
}

// Within-layer sew-order reorder (contract v1.2, the Layers panel's up/down
// control for shapes sharing one color). `rowIds` is the layer's OWN shapes
// in their currently displayed order — already accounting for any sew_order
// override in effect and, absent one, the natural nearest-neighbour order —
// `targetId` the shape being moved, `dir` -1 (earlier) or 1 (later).
//
// Returns { shape_id: newSewOrder, ... } for EVERY shape in the layer, or
// null when the move is out of bounds (already first/last). Every member is
// assigned an explicit slot, not just the two that swapped: a partial pin —
// "move these two, leave the rest to nearest-neighbour" — cannot express
// "swap adjacent items" unambiguously once nearest-neighbour is free to
// reshuffle the untouched slots around them (the service falls back to it
// per shape, not per layer). Committing the whole layer's order the first
// time the user touches it is the predictable reading: from then on, this
// layer sews exactly the order the list shows.
export function reorderWithinLayer(rowIds, targetId, dir) {
  const i = rowIds.indexOf(targetId);
  if (i < 0) return null;
  const j = i + dir;
  if (j < 0 || j >= rowIds.length) return null;
  const next = rowIds.slice();
  [next[i], next[j]] = [next[j], next[i]];
  const out = {};
  next.forEach((id, idx) => {
    out[id] = idx;
  });
  return out;
}

// Outline decimation for the row thumbnails: keep at most `max` points,
// evenly strided, endpoints preserved. The review outlines are already
// simplified polygons, but a complex logo shape can still carry hundreds of
// vertices — far more than a 24 px thumbnail can show, and this rides
// localStorage with the project.
export function thinOutline(points, max = 48) {
  const pts = points || [];
  if (pts.length <= max) return pts.map((p) => [p[0], p[1]]);
  const step = (pts.length - 1) / (max - 1);
  const out = [];
  for (let i = 0; i < max; i++) {
    const p = pts[Math.round(i * step)];
    out.push([p[0], p[1]]);
  }
  return out;
}

// Slim the job's review payload down to what the Layers list renders and
// persists with the element. Field name mapping is deliberate: the wire
// names (shape_id, thread_index, ...) stay in digitizer.js; the element
// stores app-shaped camelCase like every other element field.
//   rgb — the shape's OWN thread color, resolved by thread number against
//   the job palette first (a shape that produced no stitches has no
//   sew_block but still has a thread), block index as the fallback.
//   stitched — the digitizer's own default for the shape (contract v1.1):
//   `false` means a BACKGROUND_ENCLOSED region left out of the stitch plan
//   by default (e.g. white icon linework enclosed by a colored logo), not a
//   user action. Missing on a response from a service that predates this
//   field reads as `true` (every shape stitched, today's behavior) — the
//   same "absent key = default" reading the field has on the wire.
export function reviewFromJob(review) {
  if (!review || !Array.isArray(review.shapes)) return null;
  const palette = review.palette || [];
  const brandId = (palette.length && palette[0].brand_id) || null;
  const byNumber = new Map(palette.map((p) => [p.number, p.rgb]));
  return {
    brandId,
    shapes: review.shapes.map((s) => ({
      id: s.shape_id,
      threadIndex: s.thread_index,
      threadNumber: s.thread_number,
      rgb:
        byNumber.get(s.thread_number) ||
        (s.sew_block != null && palette[s.sew_block] && palette[s.sew_block].rgb) ||
        null,
      areaMm2: s.area_mm2,
      layer: s.layer,
      // The within-layer sew-order override in effect (contract v1.2), or
      // null when this shape falls back to nearest-neighbour — echoed back
      // the same way `layer` is, so the panel can tell an applied override
      // from the computed default.
      sewOrder: s.sew_order == null ? null : s.sew_order,
      sewIndex: s.sew_index,
      sewBlock: s.sew_block,
      tier: s.tier,
      stitched: s.stitched !== false,
      outline: thinOutline(s.outline_mm),
    })),
  };
}

// A digitize run with deletions returns a review WITHOUT the deleted shapes
// (they are dropped after stage 4, so the engine never planned them). The
// Layers list must keep showing them — struck through, restorable — so the
// stored review carries each deleted shape's LAST KNOWN row forward from
// the previous review. Restoring is then just removing the id from
// deletedShapeIds; the next apply brings the shape back for real.
export function reconcileReview(prev, fresh, deletedShapeIds) {
  if (!fresh) return prev || null;
  const have = new Set(fresh.shapes.map((s) => s.id));
  const carried = [];
  for (const sid of deletedShapeIds || []) {
    if (have.has(sid)) continue;
    const old = prev && (prev.shapes || []).find((s) => s.id === sid);
    if (old) carried.push(old);
  }
  return carried.length ? { ...fresh, shapes: [...fresh.shapes, ...carried] } : fresh;
}

function b64ToBytes(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

// FastAPI errors are { detail: "human sentence" }; surface that sentence.
async function httpDetail(r) {
  try {
    const body = await r.json();
    if (body && body.detail) return String(body.detail);
  } catch (e) {
    // fall through
  }
  return "The digitizer service answered " + r.status + ".";
}

// POST /digitize (multipart image + config JSON) -> { job_id, state, cached }.
// 202 is the service's accept status; anything non-ok throws with the
// service's own detail sentence.
export async function startDigitize(pngBase64, config, fetchFn = globalThis.fetch) {
  const form = new FormData();
  form.append("image", new Blob([b64ToBytes(pngBase64)], { type: "image/png" }), "art.png");
  form.append("config", JSON.stringify(config));
  const r = await fetchFn(digitizerUrl() + "/digitize", { method: "POST", body: form });
  if (!r.ok) throw new Error(await httpDetail(r));
  return r.json();
}

// Poll GET /jobs/{id} until done/error. done -> the full job payload
// ({ design, review, stats, warnings }); error -> throws the job's error.
// opts.onState hears every observed state ("queued"/"running") for honest
// pending UI; opts.isCancelled() stops the loop quietly (a torn-down panel
// must not keep a timer alive — the job cache means re-asking is free).
export async function pollJob(jobId, opts = {}) {
  const fetchFn = opts.fetchFn || globalThis.fetch;
  const intervalMs = opts.intervalMs == null ? 500 : opts.intervalMs;
  const timeoutMs = opts.timeoutMs == null ? 300000 : opts.timeoutMs;
  const t0 = Date.now();
  for (;;) {
    if (opts.isCancelled && opts.isCancelled()) return null;
    const r = await fetchFn(digitizerUrl() + "/jobs/" + jobId);
    if (!r.ok) throw new Error(await httpDetail(r));
    const job = await r.json();
    if (job.state === "done") return job;
    if (job.state === "error") throw new Error(job.error || "Digitizing failed.");
    if (opts.onState) opts.onState(job.state);
    if (Date.now() - t0 > timeoutMs) {
      throw new Error("Digitizing timed out. Check the service window, then digitize again.");
    }
    await new Promise((res) => setTimeout(res, intervalMs));
  }
}

// Submit + poll in one call. An identical image+config re-run returns the
// finished job immediately (the service's content-hash cache) — that is what
// makes the change-a-param-look-again loop usable.
export async function digitize(pngBase64, config, opts = {}) {
  const sub = await startDigitize(pngBase64, config, opts.fetchFn || globalThis.fetch);
  return pollJob(sub.job_id, opts);
}

// ---- adapter: service Design -> buildImportedDesign's decoded shape --------

// The engine's buildImportedDesign consumes decodeDST's output shape:
// stitches CENTERED on the sewn-stitch bbox midpoint, plus counts and mm
// extents. The service Design is the same units and orientation but keeps the
// artwork-bbox origin (pull comp can leave the stitch bbox a few tenths
// off-center — adapter.py documents why), and carries a trailing "end" record
// buildImportedDesign must never see (it would scale it like a stitch and
// then append its own). So: strip "end", count, center. Pure; null when the
// design has nothing sewn.
export function decodedFromDesign(design) {
  const src = (design && design.stitches) || [];
  const stitches = [];
  let stitchCount = 0;
  let jumpCount = 0;
  let trimCount = 0;
  let colorChanges = 0;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const s of src) {
    if (s.type === "end") continue;
    stitches.push({ x: s.x, y: s.y, type: s.type });
    if (s.type === "stitch") {
      stitchCount++;
      if (s.x < minX) minX = s.x;
      if (s.x > maxX) maxX = s.x;
      if (s.y < minY) minY = s.y;
      if (s.y > maxY) maxY = s.y;
    } else if (s.type === "jump") jumpCount++;
    else if (s.type === "trim") trimCount++;
    else if (s.type === "color") colorChanges++;
  }
  if (!stitchCount) return null;
  const cx = Math.round((minX + maxX) / 2);
  const cy = Math.round((minY + maxY) / 2);
  for (const s of stitches) {
    s.x -= cx;
    s.y -= cy;
  }
  return {
    stitches,
    stitchCount,
    jumpCount,
    trimCount,
    colorCount: (design.colors && design.colors.length) || colorChanges + 1,
    widthMM: (maxX - minX) / 10,
    heightMM: (maxY - minY) / 10,
    label: design.name || "",
  };
}

// Per-frame regen cache (drag/resize regenerate every element per frame —
// the same reason generate.js caches decoded DSTs). Keyed by the result
// object itself: a re-digitize patches a NEW result object onto the element,
// and a WeakMap lets an abandoned result's decoded copy be collected.
const decodedCache = new WeakMap();
export function decodedFromDesignCached(design) {
  if (!design || typeof design !== "object") return null;
  let hit = decodedCache.get(design);
  if (hit === undefined) {
    hit = decodedFromDesign(design);
    if (hit) decodedCache.set(design, hit);
  }
  return hit;
}

// Block colors for buildImportedDesign: the service palette (real thread
// colors, already brand-snapped) as the default for every block, the user's
// per-block overrides on top. Passing a FULL map matters — any block left out
// would fall back to the engine's IMPORT_BLOCK_COLORS placeholder hues, which
// exist for colorless DST imports, not for a design that knows its threads.
export function digitizedBlockColors(element) {
  const colors = (element && element.result && element.result.colors) || [];
  const overrides = (element && element.blockColors) || {};
  const out = {};
  for (let i = 0; i < colors.length; i++) {
    out[i] = overrides[i] || [colors[i].r || 0, colors[i].g || 0, colors[i].b || 0];
  }
  return out;
}

// ---- warnings: pipeline codes -> customer language -------------------------

// Codes are append-only (warnings_codes.py). Unknown codes fall back to the
// service's own message — honest, if less polished — so a new pipeline
// warning is never silently swallowed.
function plural(n, one, many) {
  return n === 1 ? one : many.replace("{n}", String(n));
}

const WARNING_TEXT = {
  BACKGROUND_UNCERTAIN: () =>
    "The background was hard to separate from the art. Check the stitch preview for missing or extra areas.",
  INPUT_LOW_RESOLUTION: () =>
    "The image is low resolution for this stitch size. A larger image or a smaller size will sew sharper.",
  BACKGROUND_ENCLOSED: () =>
    "Enclosed background-colored areas were left open, like the hole in an O. " +
    "Find them in the Layers list, marked \"not sewn — enclosed area,\" to sew them.",
  COLOR_CAP_APPLIED: () =>
    "The art has more colors than the limit. The smallest areas now reuse the nearest kept color — raise Colors to keep more.",
  DROPPED_SMALL_SHAPES: (w) =>
    plural(w.count || 0,
      "One part of the art was too small to sew and was left out.",
      "{n} parts of the art were too small to sew and were left out."),
  ABSORBED_SMALL_SHAPES: (w) =>
    plural(w.count || 0,
      "One tiny detail was merged into the shape around it.",
      "{n} tiny details were merged into the shapes around them."),
  EMPTY_THREAD_LAYER: () =>
    "One color ended up with nothing to sew and was removed.",
  HOLE_NEARLY_CLOSED: (w) =>
    plural(w.count || 0,
      "One small opening was held open so stitching doesn't swallow it.",
      "{n} small openings were held open so stitching doesn't swallow them."),
  SAME_THREAD_SHAPES_MERGED: () =>
    "Same-color shapes that nearly touch were held apart so they sew as separate shapes.",
  SHAPE_TOO_THIN_TO_FILL: (w) =>
    plural(w.count || 0,
      "One area was too narrow to fill with stitches. Satin usually catches these — check it's on.",
      "{n} areas were too narrow to fill with stitches. Satin usually catches these — check it's on."),
  SHAPE_NOT_STITCHED: (w) =>
    plural(w.count || 0,
      "One shape couldn't be stitched and was left out.",
      "{n} shapes couldn't be stitched and were left out."),
  LONG_JUMPS_TRIMMED: (w) =>
    plural(w.count || 0,
      "The thread gets cut once where it has to travel a long way.",
      "The thread gets cut {n} times where it has to travel a long way."),
  BORDER_SKIPPED_TOO_NARROW: (w) =>
    plural(w.count || 0,
      "One shape was too narrow for a border and sews without one.",
      "{n} shapes were too narrow for a border and sew without one."),
  BORDER_LIGHTENED: (w) =>
    plural(w.count || 0,
      "One border sews as a light run line — the shape was too narrow for a satin border.",
      "{n} borders sew as light run lines — those shapes were too narrow for satin borders."),
  SHAPES_DELETED_BY_USER: (w) =>
    plural(w.count || 0,
      "One shape is hidden by you. Restore it from the Layers list to sew it again.",
      "{n} shapes are hidden by you. Restore them from the Layers list to sew them again."),
  SHAPE_EDIT_UNKNOWN_ID: (w) =>
    plural(w.count || 0,
      "One layer edit no longer matches any shape in the art, so it wasn't applied.",
      "{n} layer edits no longer match any shape in the art, so they weren't applied."),
};

// [{ code, message, ...extra }] -> [{ code, text }] for the panel.
export function describeWarnings(warnings) {
  return (warnings || []).map((w) => {
    const t = w && WARNING_TEXT[w.code];
    return {
      code: (w && w.code) || "",
      text: t ? t(w) : String((w && w.message) || w),
    };
  });
}
