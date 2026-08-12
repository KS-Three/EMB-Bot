import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";
import fixture from "./fixtures/digitized-asym.json";

// Engine load, same recipe as generate.spec.js (buildImportedDesign and the
// DST codec live on the EMB global).
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
});

// localStorage doesn't exist in the node test env; digitizer.js and
// threads.js both read it through try/catch, so a minimal stub is enough to
// exercise the brand-preference path.
function stubStorage(entries = {}) {
  const store = new Map(Object.entries(entries));
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
}

function digitizedElement(overrides = {}) {
  return {
    id: "e1", type: "digitized", name: "asym.png", sourcePng: null,
    params: { target_width_mm: 80, max_colors: 6, satin: true, fill_angle_deg: null, border: "off" },
    result: null, warnings: [], blockColors: {},
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0,
    ...overrides,
  };
}

const PROJECT = { version: 2, garmentId: "left_chest", selectedId: "e1", elements: [] };

// A 1x1 transparent PNG — a real, decodable base64 payload for the wire specs.
const TINY_PNG_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

// ---- the /digitize request shape (pinned against the service's tests) ------
//
// The other end of this seam is digitizer/tests/test_service.py: multipart
// fields "image" + "config", config keys drawn from PipelineConfig
// (digitizer_core/config.py) — anything else 400s as "unknown config
// field(s)". This list IS that dataclass (minus debug_dir/extra, which the
// service refuses). If a key ever leaves this set, the service rejects the
// request, so the two ends cannot drift silently — this spec makes the drift
// loud on the JS side too.
const PIPELINE_CONFIG_FIELDS = [
  "target_width_mm", "thread_brand", "max_colors", "seed", "merge_delta_e",
  "aa_iterations", "aa_phantom_edge_frac", "bg_tolerance_lab", "bg_margin_mm",
  "bg_intrusion_min_mm", "min_px_per_mm", "upscale_cap", "denoise",
  "min_detail_mm", "report_absorb_frac", "simplify_tol_mm", "garment_id",
  "fabric_id", "overlap_mm", "fill_row_mm", "fill_stitch_mm", "fill_angle_deg",
  "underlay_style", "underlay", "satin", "satin_max_width_mm", "border",
  "border_width_mm", "deleted_shape_ids", "shape_overrides",
  "merge_shape_ids", "split_shapes", "photo_segment_sam2", "detail_layer",
];

test("buildDigitizeConfig sends the stored thread-brand preference and the project garment, in service field names", async () => {
  stubStorage({ "embstudio:threadPalette": "madeira-rayon" });
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const cfg = buildDigitizeConfig(digitizedElement(), PROJECT);

  expect(cfg).toEqual({
    target_width_mm: 80,
    max_colors: 6,
    satin: true,
    border: "off",
    detail_layer: false,
    thread_brand: "madeira-rayon",
    garment_id: "left_chest",
  });
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("buildDigitizeConfig omits thread_brand for the generic Studio palette (service default applies), includes fill_angle_deg only when set", async () => {
  stubStorage({}); // no stored preference -> "studio"
  const { buildDigitizeConfig } = await import("./digitizer.js");

  const plain = buildDigitizeConfig(digitizedElement(), PROJECT);
  expect("thread_brand" in plain).toBe(false);
  expect("fill_angle_deg" in plain).toBe(false);

  const angled = buildDigitizeConfig(
    digitizedElement({ params: { target_width_mm: 60, max_colors: 4, satin: false, fill_angle_deg: 45, border: "bean" } }),
    PROJECT
  );
  expect(angled.fill_angle_deg).toBe(45);
  expect(angled.satin).toBe(false);
  expect(angled.border).toBe("bean");
  expect(angled.target_width_mm).toBe(60);
});

test("buildDigitizeConfig sends photo_segment_sam2 only when the embstudio:sam2 dev seam is on", async () => {
  // SAM2 is an internal/advanced seam, not a product control (see sam2Enabled
  // in digitizer.js): absent by default so the service's own False default
  // applies, and never stored in element.params so it can't persist into a
  // saved project.
  stubStorage({});
  let mod = await import("./digitizer.js");
  expect("photo_segment_sam2" in mod.buildDigitizeConfig(digitizedElement(), PROJECT)).toBe(false);

  stubStorage({ "embstudio:sam2": "1" });
  vi.resetModules();
  mod = await import("./digitizer.js");
  expect(mod.buildDigitizeConfig(digitizedElement(), PROJECT).photo_segment_sam2).toBe(true);

  // Only the exact string "1" arms it -- a stale/garbage value must not
  // silently route every photo design through a 156 MB model.
  stubStorage({ "embstudio:sam2": "true" });
  vi.resetModules();
  mod = await import("./digitizer.js");
  expect("photo_segment_sam2" in mod.buildDigitizeConfig(digitizedElement(), PROJECT)).toBe(false);
});

test("sam2Enabled is false when localStorage throws, like digitizerUrl's own fallback", async () => {
  globalThis.localStorage = {
    getItem: () => { throw new Error("storage disabled"); },
    setItem: () => {},
    removeItem: () => {},
  };
  vi.resetModules();
  const { sam2Enabled } = await import("./digitizer.js");
  expect(sam2Enabled()).toBe(false);
});

test("detail_layer rides buildDigitizeConfig both ways, and back-fills false for projects saved before the field existed", async () => {
  stubStorage({});
  const { buildDigitizeConfig } = await import("./digitizer.js");

  // digitizedElement()'s params deliberately predate detail_layer — the spread
  // of DEFAULT_DIGITIZE_PARAMS is what keeps an older saved project loadable
  // (and re-digitizing to its stored result) instead of sending undefined.
  expect(buildDigitizeConfig(digitizedElement(), PROJECT).detail_layer).toBe(false);

  const on = digitizedElement({
    params: {
      target_width_mm: 80, max_colors: 6, satin: true,
      fill_angle_deg: null, border: "off", detail_layer: true,
    },
  });
  expect(buildDigitizeConfig(on, PROJECT).detail_layer).toBe(true);
});

test("startDigitize POSTs multipart image+config to /digitize exactly as test_service.py's client does", async () => {
  stubStorage({ "embstudio:threadPalette": "isacord" });
  const { startDigitize, buildDigitizeConfig } = await import("./digitizer.js");

  const calls = [];
  const fetchFn = vi.fn(async (url, opts) => {
    calls.push({ url, opts });
    return { ok: true, status: 202, json: async () => ({ job_id: "j1", state: "queued", cached: false }) };
  });

  const cfg = buildDigitizeConfig(digitizedElement(), PROJECT);
  const sub = await startDigitize(TINY_PNG_B64, cfg, fetchFn);
  expect(sub.job_id).toBe("j1");

  expect(calls).toHaveLength(1);
  expect(calls[0].url).toBe("http://127.0.0.1:8721/digitize");
  expect(calls[0].opts.method).toBe("POST");

  const form = calls[0].opts.body;
  expect(form).toBeInstanceOf(FormData);
  const image = form.get("image");
  expect(image.type).toBe("image/png");
  expect(image.size).toBeGreaterThan(0);

  const sent = JSON.parse(form.get("config"));
  expect(sent.thread_brand).toBe("isacord");
  expect(sent.garment_id).toBe("left_chest");
  for (const k of Object.keys(sent)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("startDigitize surfaces the service's own detail sentence on a 400", async () => {
  stubStorage({});
  const { startDigitize } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: false, status: 400,
    json: async () => ({ detail: "unknown thread brand 'nope'. See /health for the list." }),
  });
  await expect(startDigitize(TINY_PNG_B64, {}, fetchFn)).rejects.toThrow(/unknown thread brand 'nope'/);
});

test("pollJob follows queued -> running -> done, reports states, and returns the finished payload", async () => {
  stubStorage({});
  const { pollJob } = await import("./digitizer.js");
  const states = [
    { state: "queued", job_id: "j1" },
    { state: "running", job_id: "j1" },
    { state: "done", job_id: "j1", design: { stitches: [] }, warnings: [] },
  ];
  let i = 0;
  const fetchFn = async () => ({ ok: true, json: async () => states[Math.min(i++, states.length - 1)] });
  const seen = [];
  const job = await pollJob("j1", { fetchFn, intervalMs: 0, onState: (s) => seen.push(s) });
  expect(job.state).toBe("done");
  expect(job.design).toBeDefined();
  expect(seen).toEqual(["queued", "running"]);
});

test("pollJob throws the job's error for a failed job", async () => {
  stubStorage({});
  const { pollJob } = await import("./digitizer.js");
  const fetchFn = async () => ({ ok: true, json: async () => ({ state: "error", error: "ValueError: bad art" }) });
  await expect(pollJob("j1", { fetchFn, intervalMs: 0 })).rejects.toThrow(/bad art/);
});

test("fetchHealth returns the payload when the service is up and null for down/non-ok/garbage", async () => {
  stubStorage({});
  const { fetchHealth } = await import("./digitizer.js");
  const up = await fetchHealth(async () => ({ ok: true, json: async () => ({ status: "ok", brands: [] }) }));
  expect(up && up.status).toBe("ok");
  expect(await fetchHealth(async () => ({ ok: false, status: 500, json: async () => ({}) }))).toBeNull();
  expect(await fetchHealth(async () => { throw new TypeError("fetch failed"); })).toBeNull();
});

test("exportViaService POSTs the design as JSON to /export and returns bytes+filename+mime from the response", async () => {
  const { exportViaService } = await import("./digitizer.js");
  let seenUrl, seenOpts;
  const fakeBlob = new Blob([new Uint8Array([1, 2, 3])]);
  const fetchFn = async (url, opts) => {
    seenUrl = url;
    seenOpts = opts;
    return {
      ok: true,
      status: 200,
      blob: async () => fakeBlob,
      headers: {
        get: (k) => {
          if (k === "Content-Disposition") return 'attachment; filename="left_chest.dst"';
          if (k === "Content-Type") return "application/octet-stream";
          return null;
        },
      },
    };
  };
  const design = { stitches: [{ x: 0, y: 0, type: "stitch" }], colors: [], widthMM: 10, heightMM: 10 };
  const out = await exportViaService(design, "dst", "left_chest", fetchFn);

  expect(seenUrl).toBe("http://127.0.0.1:8721/export");
  expect(seenOpts.method).toBe("POST");
  expect(seenOpts.headers["Content-Type"]).toBe("application/json");
  const sentBody = JSON.parse(seenOpts.body);
  expect(sentBody).toEqual({ design, format: "dst", label: "left_chest" });

  expect(out.bytes).toBe(fakeBlob);
  expect(out.filename).toBe("left_chest.dst");
  expect(out.mime).toBe("application/octet-stream");
});

test("exportViaService falls back to a design.<format> filename when Content-Disposition is missing", async () => {
  const { exportViaService } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: true,
    status: 200,
    blob: async () => new Blob([]),
    headers: { get: () => null },
  });
  const out = await exportViaService({ stitches: [] }, "exp", "x", fetchFn);
  expect(out.filename).toBe("design.exp");
  expect(out.mime).toBe("application/octet-stream");
});

test("exportViaService surfaces the service's own detail sentence on a non-ok response", async () => {
  const { exportViaService } = await import("./digitizer.js");
  const fetchFn = async () => ({
    ok: false, status: 400,
    json: async () => ({ detail: "payload.design must be a design with stitches." }),
  });
  await expect(exportViaService({ stitches: [] }, "dst", "x", fetchFn))
    .rejects.toThrow(/payload\.design must be a design with stitches/);
});

test("exportViaService includes a request timeout so a hung service can't block Download forever", async () => {
  const { exportViaService } = await import("./digitizer.js");
  let seenOpts;
  const fetchFn = async (url, opts) => {
    seenOpts = opts;
    return { ok: true, status: 200, blob: async () => new Blob([]), headers: { get: () => null } };
  };
  await exportViaService({ stitches: [] }, "dst", "x", fetchFn);
  expect(seenOpts.signal).toBeInstanceOf(AbortSignal);
});

// ---- shape-layers edits (review-screen contract v1) ------------------------
//
// The other end of this seam is digitizer_service/app.py's
// _canonicalize_shape_edits: the job cache keys on sha256(image) + the
// canonical config, so the app must send edits ALREADY canonical — sorted,
// deduped, no null/"auto"/app-only fields — or two spellings of one edit
// would be two jobs (and the panel's pending-edits check would lie).

test("canonicalShapeEdits: sorts+dedupes deletions, strips rgb/null/auto, drops empty entries and overrides for deleted shapes", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    deletedShapeIds: ["Sbbb", "Saaa", "Sbbb"],
    shapeOverrides: {
      Szzz: { thread_index: 4, rgb: [1, 2, 3], tier: "auto", fill_angle_deg: null },
      Saaa: { tier: "satin" }, // deleted above -> omitted (engine would only warn)
      Smmm: { tier: "auto", rgb: [9, 9, 9] }, // canonicalizes to nothing -> dropped
      Sfff: { fill_angle_deg: 90, layer: 2, border: "bean" },
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    deleted_shape_ids: ["Saaa", "Sbbb"],
    shape_overrides: {
      Sfff: { fill_angle_deg: 90, border: "bean", layer: 2 },
      Szzz: { thread_index: 4 },
    },
  });
  // No edits at all -> a config indistinguishable from the pre-layers one.
  expect(canonicalShapeEdits(digitizedElement())).toEqual({});
});

// "sketch" (contract v1.3, photo plan row 12) joined satin/fill/run as a
// forceable per-shape tier — digitizer_service/app.py's _TIER_VALUES and
// digitizer_core/regions.py's own copy both list it. Pinned here the same
// way the other three tiers are: a value this module doesn't recognize
// canonicalizes to nothing and never reaches the wire, exactly what almost
// shipped when the Layers-panel dropdown gained a Sketch option before this
// module's SHAPE_TIERS set did.
test("canonicalShapeEdits accepts the sketch tier alongside satin/fill/run", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: { Ssk: { tier: "sketch" } },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: { Ssk: { tier: "sketch" } },
  });
});

// "streamline" (contract v1.6) joined the same closed set the same way
// "sketch" did, alongside the tier dropdown's Streamline option — this is
// what lets a manually-classified (flat-lane) shape opt into the evenly-
// spaced thread-paint tier without the whole design setting
// fill_technique="streamline". Same regression this file already guards
// against for "sketch": a value SHAPE_TIERS doesn't recognize
// canonicalizes to nothing and silently never reaches the wire.
test("canonicalShapeEdits accepts the streamline tier alongside satin/fill/run/sketch", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: { Ssl: { tier: "streamline" } },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: { Ssl: { tier: "streamline" } },
  });
});

// "crosshatch" (the two-pass angled tatami fill, digitizer_core/
// stage6_fill.py's _crosshatch_fill_paths) joined the same closed set the
// same way "streamline" did, alongside the tier dropdown's Cross-hatch
// option — a per-shape opt-in reachable on any design, no fill_technique
// change required. Same regression this file already guards against for
// "sketch"/"streamline": a value SHAPE_TIERS doesn't recognize canonicalizes
// to nothing and silently never reaches the wire.
test("canonicalShapeEdits accepts the crosshatch tier alongside satin/fill/run/sketch/streamline", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: { Sch: { tier: "crosshatch" } },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: { Sch: { tier: "crosshatch" } },
  });
});

// "wave"/"chevron"/"brick" (digitizer_core/stage6_fill.py's
// _wave_row_points / _chevron_row_points / _brick_row_points) joined the
// same closed set the same way "crosshatch" did, alongside the tier
// dropdown's Wave/Chevron/Brick options — three more purely-geometric
// per-shape opt-ins, each changing only how one row's own interior points
// land rather than adding a new pass. Same regression this file already
// guards against for every tier above: a value SHAPE_TIERS doesn't
// recognize canonicalizes to nothing and silently never reaches the wire.
test("canonicalShapeEdits accepts the wave/chevron/brick tiers alongside crosshatch", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: {
      Swv: { tier: "wave" },
      Sch2: { tier: "chevron" },
      Sbr: { tier: "brick" },
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Swv: { tier: "wave" },
      Sch2: { tier: "chevron" },
      Sbr: { tier: "brick" },
    },
  });
});

// ---- BACKGROUND_ENCLOSED restore (contract v1.1: shapes[].stitched, ------
// shape_overrides[sid].stitched) --------------------------------------------
//
// The other end is the same digitizer_service/app.py seam as the rest of
// this section, extended with a `stitched` boolean field — restoring an
// enclosed-background region the digitizer excluded by default. Unlike
// tier/border it has no "auto" spelling of its own; the absence of the key
// IS auto, so only a real true/false survives canonicalization.

test("canonicalShapeEdits accepts and round-trips a `stitched` override (both true and false), rejecting non-booleans", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: {
      Srestore: { stitched: true },
      Sskip: { stitched: false },
      Sjunk: { stitched: "yes" }, // not a boolean -> canonicalizes to nothing
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Srestore: { stitched: true },
      Sskip: { stitched: false },
    },
  });
});

test("canonicalShapeEdits combines `stitched` with the other override fields on one shape, and still drops it for a deleted shape", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    deletedShapeIds: ["Sdeleted"],
    shapeOverrides: {
      Sboth: { stitched: true, tier: "fill", thread_index: 2 },
      Sdeleted: { stitched: true }, // deleted wins -> omitted from shape_overrides
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    deleted_shape_ids: ["Sdeleted"],
    shape_overrides: {
      Sboth: { thread_index: 2, tier: "fill", stitched: true },
    },
  });
});

// ---- per-shape border override (contract v1; Layers-panel control) ---------
//
// The wire contract (digitizer_service/app.py's _BORDER_VALUES, enforced
// again engine-side in regions.apply_shape_edits) accepts "off" | "auto" |
// "bean" — and unlike tier, "auto" is a REAL override value, not the
// no-override spelling: it forces the border decision back ON for one shape
// even when the design-wide Border param is "off". The absence of the key is
// the only "use the design setting" spelling.

test("canonicalShapeEdits round-trips every border value — off, auto AND bean (auto is a real override, unlike tier) — and drops junk", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: {
      Soff: { border: "off" },
      Sauto: { border: "auto" }, // must SURVIVE — not the tier "auto" clearing rule
      Sbean: { border: "bean" },
      Sjunk: { border: "zigzag" }, // not in the closed vocabulary -> dropped
      Snull: { border: null }, // null = absence -> entry canonicalizes away
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Sauto: { border: "auto" },
      Sbean: { border: "bean" },
      Soff: { border: "off" },
    },
  });
});

// ---- underlay_style override (shape-layers contract v1) --------------------
//
// Mirrors digitizer_service/app.py's own closed vocabulary (fabrics.py's
// underlay ids). Unlike `tier`/`border` it has no "auto" spelling of its
// own — the absence of the key IS auto, exactly like `stitched` above and
// `fill_angle_deg`'s null.

test("canonicalShapeEdits accepts a valid underlay_style, rejects an unknown one, and combines it with the other override fields", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: {
      Sedge: { underlay_style: "edge_zigzag" },
      Snone: { underlay_style: "none" },
      Sjunk: { underlay_style: "sparkly" }, // not in the vocabulary -> dropped
      Sboth: { underlay_style: "zigzag", tier: "fill", thread_index: 3 },
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Sedge: { underlay_style: "edge_zigzag" },
      Snone: { underlay_style: "none" },
      Sboth: { thread_index: 3, tier: "fill", underlay_style: "zigzag" },
    },
  });
});

// ---- boundary_override (contract v1.4; the boundary editor) ----------------
//
// The shallow half of the contract this file can check without a live
// service: canonicalShapeEdits' point-count/shape gate (mirrors
// digitizer_service/app.py's own), the pure geometry helpers the editor uses
// for live feedback (boundaryIssues, dedupeRing, ringArea), and that
// reviewFromJob keeps a full-resolution working copy (`outlineFull`)
// DISTINCT from the thumbnail's hard-decimated `outline` — starting the
// editor from the thumbnail copy would silently reshape the polygon the
// moment it opened, with no drag at all.

test("canonicalShapeEdits accepts a valid boundary_override, rejects too few points, and combines it with other override fields", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const tri = [[0, 0], [10, 0], [5, 8]];
  const el = digitizedElement({
    shapeOverrides: {
      Sgood: { boundary_override: tri },
      Stooshort: { boundary_override: [[0, 0], [1, 1]] }, // < 3 points -> dropped
      Snotarray: { boundary_override: "nope" }, // wrong type -> dropped
      Sboth: { boundary_override: tri, tier: "fill" },
      Snull: { boundary_override: null }, // absence -> canonicalizes away
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Sgood: { boundary_override: tri },
      Sboth: { boundary_override: tri, tier: "fill" },
    },
  });
});

test("a boundary_override rides buildDigitizeConfig and changes the cache key (editsKey), and clearing it restores the no-edits config", async () => {
  stubStorage({});
  const { buildDigitizeConfig, canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const tri = [[0, 0], [10, 0], [5, 8]];
  const plain = digitizedElement();
  const edited = digitizedElement({ shapeOverrides: { S1: { boundary_override: tri } } });
  expect(editsKey(canonicalShapeEdits(edited))).not.toBe(editsKey(canonicalShapeEdits(plain)));
  // A different shape is a different edit (distinct job).
  const other = digitizedElement({ shapeOverrides: { S1: { boundary_override: [[0, 0], [5, 0], [5, 5]] } } });
  expect(editsKey(canonicalShapeEdits(other))).not.toBe(editsKey(canonicalShapeEdits(edited)));
  const cfg = buildDigitizeConfig(edited, PROJECT);
  expect(cfg.shape_overrides).toEqual({ S1: { boundary_override: tri } });
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
  const cleared = digitizedElement({ shapeOverrides: { S1: { boundary_override: null } } });
  expect(buildDigitizeConfig(cleared, PROJECT)).toEqual(buildDigitizeConfig(plain, PROJECT));
});

test("dedupeRing drops a closing point that repeats the first, and consecutive duplicates, without disturbing an already-open ring", async () => {
  stubStorage({});
  const { dedupeRing } = await import("./digitizer.js");
  expect(dedupeRing([[0, 0], [10, 0], [10, 10], [0, 0]])).toEqual([[0, 0], [10, 0], [10, 10]]);
  expect(dedupeRing([[0, 0], [0, 0], [10, 0], [10, 10]])).toEqual([[0, 0], [10, 0], [10, 10]]);
  expect(dedupeRing([[0, 0], [10, 0], [10, 10]])).toEqual([[0, 0], [10, 0], [10, 10]]);
  expect(dedupeRing([])).toEqual([]);
});

test("ringArea computes the shoelace area of a simple polygon", async () => {
  stubStorage({});
  const { ringArea } = await import("./digitizer.js");
  expect(ringArea([[0, 0], [10, 0], [10, 10], [0, 10]])).toBeCloseTo(100, 6);
  expect(ringArea([[0, 0], [10, 0], [5, 8]])).toBeCloseTo(40, 6);
});

test("boundaryIssues is clean for a simple polygon and flags a self-crossing bowtie, a near-zero-area sliver, and too few points", async () => {
  stubStorage({});
  const { boundaryIssues } = await import("./digitizer.js");
  expect(boundaryIssues([[0, 0], [10, 0], [10, 10], [0, 10]])).toEqual([]);
  const bowtie = boundaryIssues([[0, 0], [10, 10], [10, 0], [0, 10]]);
  expect(bowtie).toContain("This boundary crosses itself.");
  const sliver = boundaryIssues([[0, 0], [0.01, 0], [0.01, 0.01]]);
  expect(sliver).toContain("This shape is too small to sew.");
  expect(boundaryIssues([[0, 0], [1, 1]])[0]).toMatch(/at least 3 points/);
});

test("reviewFromJob keeps a full-resolution outlineFull distinct from the hard-decimated thumbnail outline, deduping a closed ring", async () => {
  stubStorage({});
  const { reviewFromJob } = await import("./digitizer.js");
  // 120 points, closed (first repeated as last) — the exact shape the wire's
  // outline_mm arrives in (shapely's exterior.coords convention).
  const ring = Array.from({ length: 120 }, (_, i) => [i, i * 2]);
  const closed = [...ring, ring[0]];
  const wire = {
    palette: [{ brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] }],
    shapes: [
      { shape_id: "Sa", thread_index: 0, thread_number: "0020", area_mm2: 1, source: "quant",
        layer: 0, sew_index: 0, sew_block: 0, tier: "fill", outline_mm: closed, holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.shapes[0].outline.length).toBeLessThanOrEqual(48);
  expect(r.shapes[0].outlineFull).toEqual(ring); // all 120 points, no closing duplicate
  expect(r.shapes[0].outlineFull.length).not.toBe(r.shapes[0].outline.length);
});

test("a border override rides buildDigitizeConfig and changes the cache key (editsKey), and clearing it restores the no-edits config", async () => {
  stubStorage({});
  const { buildDigitizeConfig, canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const plain = digitizedElement();
  const edited = digitizedElement({ shapeOverrides: { S1: { border: "bean" } } });
  expect(editsKey(canonicalShapeEdits(edited))).not.toBe(editsKey(canonicalShapeEdits(plain)));
  // Distinct border values are distinct edits (distinct jobs).
  const off = digitizedElement({ shapeOverrides: { S1: { border: "off" } } });
  expect(editsKey(canonicalShapeEdits(off))).not.toBe(editsKey(canonicalShapeEdits(edited)));
  const cfg = buildDigitizeConfig(edited, PROJECT);
  expect(cfg.shape_overrides).toEqual({ S1: { border: "bean" } });
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
  // The panel's clear spelling (setShapeBorder "default" -> border: null)
  // reads as no edits at all — the pre-layers config, byte for byte.
  const cleared = digitizedElement({ shapeOverrides: { S1: { border: null } } });
  expect(buildDigitizeConfig(cleared, PROJECT)).toEqual(buildDigitizeConfig(plain, PROJECT));
});

// ---- within-layer sew order (contract v1.2; Layers-panel reorder control) --
//
// The wire contract (digitizer_service/app.py's sew_order validation,
// enforced again engine-side in regions.apply_shape_edits) accepts a
// non-negative integer — a shape's explicit slot within its OWN color
// layer's sew sequence. Unlike `layer` (which picks WHICH layer sews), this
// picks WHERE within it, and unlike tier/border it has no closed vocabulary
// to normalize — just an integer bound.

test("canonicalShapeEdits accepts a non-negative sew_order and rejects junk (negative, float, non-numeric)", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: {
      Sfirst: { sew_order: 0 },
      Slater: { sew_order: 3 },
      Sneg: { sew_order: -1 },       // rejected -> entry canonicalizes to nothing
      Sfloat: { sew_order: 1.5 },    // not an integer -> dropped
      Sstr: { sew_order: "2" },      // not a number -> dropped
      Snull: { sew_order: null },    // absence -> canonicalizes away
    },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: {
      Sfirst: { sew_order: 0 },
      Slater: { sew_order: 3 },
    },
  });
});

test("sew_order combines with layer and other override fields on one shape", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({
    shapeOverrides: { S1: { layer: 2, sew_order: 1, tier: "fill" } },
  });
  expect(canonicalShapeEdits(el)).toEqual({
    shape_overrides: { S1: { tier: "fill", layer: 2, sew_order: 1 } },
  });
});

test("a sew_order override rides buildDigitizeConfig and changes the cache key (editsKey)", async () => {
  stubStorage({});
  const { buildDigitizeConfig, canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const plain = digitizedElement();
  const edited = digitizedElement({ shapeOverrides: { S1: { sew_order: 0 } } });
  expect(editsKey(canonicalShapeEdits(edited))).not.toBe(editsKey(canonicalShapeEdits(plain)));
  // Distinct positions are distinct edits (distinct jobs).
  const other = digitizedElement({ shapeOverrides: { S1: { sew_order: 1 } } });
  expect(editsKey(canonicalShapeEdits(other))).not.toBe(editsKey(canonicalShapeEdits(edited)));
  const cfg = buildDigitizeConfig(edited, PROJECT);
  expect(cfg.shape_overrides).toEqual({ S1: { sew_order: 0 } });
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
  // Clearing it (null) reads as no edits at all — the pre-layers config.
  const cleared = digitizedElement({ shapeOverrides: { S1: { sew_order: null } } });
  expect(buildDigitizeConfig(cleared, PROJECT)).toEqual(buildDigitizeConfig(plain, PROJECT));
});

test("reviewFromJob maps the sew_order override in effect, and null when the shape has none", async () => {
  stubStorage({});
  const { reviewFromJob } = await import("./digitizer.js");
  const wire = {
    palette: [{ brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] }],
    shapes: [
      { shape_id: "Spinned", thread_index: 0, thread_number: "0020", area_mm2: 10, source: "quant",
        layer: 0, sew_order: 0, sew_index: 0, sew_block: 0, tier: "fill",
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Sauto", thread_index: 0, thread_number: "0020", area_mm2: 5, source: "quant",
        layer: 0, sew_order: null, sew_index: 1, sew_block: 0, tier: "fill",
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.shapes.map((s) => [s.id, s.sewOrder])).toEqual([
    ["Spinned", 0],
    ["Sauto", null],
  ]);
});

// ---- reorderWithinLayer (pure logic behind the within-layer up/down UI) ----

test("reorderWithinLayer swaps the target with its neighbour and assigns every sibling an explicit slot", async () => {
  stubStorage({});
  const { reorderWithinLayer } = await import("./digitizer.js");
  const ids = ["L", "M", "R"];
  expect(reorderWithinLayer(ids, "M", -1)).toEqual({ M: 0, L: 1, R: 2 });
  expect(reorderWithinLayer(ids, "M", 1)).toEqual({ L: 0, R: 1, M: 2 });
});

test("reorderWithinLayer refuses to move a shape past either edge", async () => {
  stubStorage({});
  const { reorderWithinLayer } = await import("./digitizer.js");
  const ids = ["L", "M", "R"];
  expect(reorderWithinLayer(ids, "L", -1)).toBeNull();
  expect(reorderWithinLayer(ids, "R", 1)).toBeNull();
});

test("reorderWithinLayer is a no-op (null) for a shape id it doesn't know", async () => {
  stubStorage({});
  const { reorderWithinLayer } = await import("./digitizer.js");
  expect(reorderWithinLayer(["L", "M", "R"], "GHOST", 1)).toBeNull();
});

test("reorderWithinLayer on a two-shape layer is a full reversal either direction", async () => {
  stubStorage({});
  const { reorderWithinLayer } = await import("./digitizer.js");
  expect(reorderWithinLayer(["A", "B"], "A", 1)).toEqual({ B: 0, A: 1 });
  expect(reorderWithinLayer(["A", "B"], "B", -1)).toEqual({ B: 0, A: 1 });
});

// ---- effLayer / sortShapes / effSewOrder / layerSiblings / effRgb ---------
// (pure Layers-list logic shared by the plain per-shape list and the
// color-block Sequencer view)

function seqRow(id, extra = {}) {
  return { id, rgb: [10, 20, 30], threadNumber: "0134", layer: 0, sewOrder: null, sewIndex: 0, ...extra };
}

test("effLayer: an explicit override beats the row's own layer, which beats sewIndex, which beats nothing", async () => {
  stubStorage({});
  const { effLayer } = await import("./digitizer.js");
  expect(effLayer(seqRow("a", { layer: 2 }), { a: { layer: 5 } })).toBe(5);
  expect(effLayer(seqRow("a", { layer: 2 }), {})).toBe(2);
  expect(effLayer(seqRow("a", { layer: null, sewIndex: 7 }), {})).toBe(7);
  expect(effLayer(seqRow("a", { layer: null, sewIndex: null }), {})).toBe(1e9);
});

test("sortShapes: orders by effLayer, then sewIndex, then id — the list IS the sew order", async () => {
  stubStorage({});
  const { sortShapes } = await import("./digitizer.js");
  const rows = [
    seqRow("c", { layer: 1, sewIndex: 0 }),
    seqRow("a", { layer: 0, sewIndex: 1 }),
    seqRow("b", { layer: 0, sewIndex: 0 }),
  ];
  expect(sortShapes(rows, {}).map((r) => r.id)).toEqual(["b", "a", "c"]);
});

test("effSewOrder: an explicit override beats the last-applied sewOrder, which beats sewIndex", async () => {
  stubStorage({});
  const { effSewOrder } = await import("./digitizer.js");
  expect(effSewOrder(seqRow("a", { sewOrder: 2, sewIndex: 9 }), { a: { sew_order: 5 } })).toBe(5);
  expect(effSewOrder(seqRow("a", { sewOrder: 2, sewIndex: 9 }), {})).toBe(2);
  expect(effSewOrder(seqRow("a", { sewOrder: null, sewIndex: 9 }), {})).toBe(9);
});

test("layerSiblings: only rows sharing the effective layer, sorted by effSewOrder", async () => {
  stubStorage({});
  const { layerSiblings } = await import("./digitizer.js");
  const rows = [
    seqRow("a", { layer: 0, sewOrder: 1 }),
    seqRow("b", { layer: 1, sewOrder: 0 }),
    seqRow("c", { layer: 0, sewOrder: 0 }),
  ];
  expect(layerSiblings(rows[0], rows, {}).map((r) => r.id)).toEqual(["c", "a"]);
});

test("effRgb: an explicit override beats the row's own thread color, which beats the placeholder grey", async () => {
  stubStorage({});
  const { effRgb } = await import("./digitizer.js");
  expect(effRgb(seqRow("a", { rgb: [1, 2, 3] }), { a: { rgb: [9, 9, 9] } })).toEqual([9, 9, 9]);
  expect(effRgb(seqRow("a", { rgb: [1, 2, 3] }), {})).toEqual([1, 2, 3]);
  expect(effRgb(seqRow("a", { rgb: null }), {})).toEqual([136, 136, 136]);
});

// ---- groupIntoBlocks (the Sequencer view's color-block grouping) ----------

test("groupIntoBlocks: one block per distinct effLayer, in sew order, each carrying its own swatch/thread/count/span", async () => {
  stubStorage({});
  const { groupIntoBlocks } = await import("./digitizer.js");
  const rows = [
    seqRow("a", { layer: 0, sewIndex: 0, rgb: [200, 0, 0], threadNumber: "0111" }),
    seqRow("b", { layer: 0, sewIndex: 1, rgb: [200, 0, 0], threadNumber: "0111" }),
    seqRow("c", { layer: 1, sewIndex: 2, rgb: [0, 200, 0], threadNumber: "0222" }),
  ];
  const blocks = groupIntoBlocks(rows, {});
  expect(blocks).toHaveLength(2);
  expect(blocks[0]).toMatchObject({
    layer: 0, rgb: [200, 0, 0], threadNumber: "0111", sewIndexMin: 0, sewIndexMax: 1,
  });
  expect(blocks[0].rows.map((r) => r.id)).toEqual(["a", "b"]);
  expect(blocks[1]).toMatchObject({
    layer: 1, rgb: [0, 200, 0], threadNumber: "0222", sewIndexMin: 2, sewIndexMax: 2,
  });
});

test("groupIntoBlocks: an override moving one shape into another's layer merges it into that block", async () => {
  stubStorage({});
  const { groupIntoBlocks } = await import("./digitizer.js");
  const rows = [
    seqRow("a", { layer: 0, sewIndex: 0 }),
    seqRow("b", { layer: 1, sewIndex: 1 }),
  ];
  const blocks = groupIntoBlocks(rows, { b: { layer: 0 } });
  expect(blocks).toHaveLength(1);
  expect(blocks[0].rows.map((r) => r.id)).toEqual(["a", "b"]);
});

test("groupIntoBlocks: a shape with no sewIndex at all doesn't poison its block's span", async () => {
  stubStorage({});
  const { groupIntoBlocks } = await import("./digitizer.js");
  const blocks = groupIntoBlocks([seqRow("a", { layer: 0, sewIndex: null })], {});
  expect(blocks[0].sewIndexMin).toBeNull();
  expect(blocks[0].sewIndexMax).toBeNull();
});

test("groupIntoBlocks: empty input is an empty list, not a throw", async () => {
  stubStorage({});
  const { groupIntoBlocks } = await import("./digitizer.js");
  expect(groupIntoBlocks([], {})).toEqual([]);
});

test("editsKey distinguishes an underlay_style override from no edits, and a no-op round trip stays stable", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const plain = editsKey(canonicalShapeEdits(digitizedElement()));
  const edited = editsKey(
    canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { underlay_style: "none" } } }))
  );
  expect(edited).not.toBe(plain);
  const again = editsKey(
    canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { underlay_style: "none" } } }))
  );
  expect(again).toBe(edited);
});

test("editsKey distinguishes standalone tier: fill, underlay: 'zigzag', and both together as three different edits", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const tierOnly = editsKey(
    canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { tier: "fill" } } }))
  );
  const underlayOnly = editsKey(
    canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { underlay_style: "zigzag" } } }))
  );
  const both = editsKey(
    canonicalShapeEdits(
      digitizedElement({ shapeOverrides: { Sa: { tier: "fill", underlay_style: "zigzag" } } })
    )
  );
  expect(new Set([tierOnly, underlayOnly, both]).size).toBe(3);
});

test("editsKey distinguishes a `stitched` restore from no edits, and a no-op stitched round trip stays stable", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const plain = editsKey(canonicalShapeEdits(digitizedElement()));
  const restored = editsKey(canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { stitched: true } } })));
  expect(restored).not.toBe(plain);
  // Same edit, re-canonicalized twice (e.g. after a reload) -> identical key.
  const again = editsKey(canonicalShapeEdits(digitizedElement({ shapeOverrides: { Sa: { stitched: true } } })));
  expect(again).toBe(restored);
});

test("editsKey is stable across edit spellings and distinguishes real differences (the pending-edits check)", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const a = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sb", "Sa"] })));
  const b = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sa", "Sb", "Sa"] })));
  expect(a).toBe(b);
  const c = editsKey(canonicalShapeEdits(digitizedElement({ deletedShapeIds: ["Sa"] })));
  expect(c).not.toBe(a);
  expect(editsKey(canonicalShapeEdits(digitizedElement()))).toBe(editsKey({}));
});

test("buildDigitizeConfig carries the edits — two elements differing only in shape_overrides produce different configs (cache-key proof, app side)", async () => {
  stubStorage({});
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const plain = buildDigitizeConfig(digitizedElement(), PROJECT);
  const edited = buildDigitizeConfig(
    digitizedElement({ shapeOverrides: { S1: { tier: "fill" } }, deletedShapeIds: ["S9"] }),
    PROJECT
  );
  expect("shape_overrides" in plain).toBe(false);
  expect("deleted_shape_ids" in plain).toBe(false);
  expect(edited.shape_overrides).toEqual({ S1: { tier: "fill" } });
  expect(edited.deleted_shape_ids).toEqual(["S9"]);
  expect(JSON.stringify(edited)).not.toBe(JSON.stringify(plain));
  for (const k of Object.keys(edited)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
});

test("buildDigitizeConfig pins thread_brand to the chart a recolor's indexes were picked against, and only then", async () => {
  // Preference moved to madeira AFTER the user picked threads against an
  // isacord job: sending madeira would re-aim every stored thread_index at
  // a different manufacturer's chart, so the config pins isacord.
  stubStorage({ "embstudio:threadPalette": "madeira-rayon" });
  const { buildDigitizeConfig } = await import("./digitizer.js");
  const recolored = buildDigitizeConfig(
    digitizedElement({
      review: { brandId: "isacord", shapes: [] },
      shapeOverrides: { S1: { thread_index: 7, rgb: [1, 2, 3] } },
    }),
    PROJECT
  );
  expect(recolored.thread_brand).toBe("isacord");
  // No thread_index override -> the preference rides as always.
  const tiered = buildDigitizeConfig(
    digitizedElement({
      review: { brandId: "isacord", shapes: [] },
      shapeOverrides: { S1: { tier: "fill" } },
    }),
    PROJECT
  );
  expect(tiered.thread_brand).toBe("madeira-rayon");
});

test("reviewFromJob slims the wire review: per-shape thread rgb by number, sew facts kept, outlines thinned", async () => {
  stubStorage({});
  const { reviewFromJob, thinOutline } = await import("./digitizer.js");
  const bigOutline = Array.from({ length: 300 }, (_, i) => [i, i * 2]);
  const wire = {
    palette: [
      { brand: "Isacord Polyester 40", brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] },
      { brand: "Isacord Polyester 40", brand_id: "isacord", number: "1902", name: "Poinsettia", rgb: [204, 0, 0] },
    ],
    design_size_mm: [80, 40],
    shapes: [
      { shape_id: "Sa", thread_index: 4, thread_number: "1902", area_mm2: 412.126, source: "quant",
        layer: 1, sew_index: 1, sew_block: 1, tier: "fill", outline_mm: bigOutline, holes_mm: [] },
      // Unstitched shape: no sew facts, but its thread still resolves by number.
      { shape_id: "Sb", thread_index: 0, thread_number: "0020", area_mm2: 3.2, source: "quant",
        layer: null, sew_index: null, sew_block: null, tier: null, outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.brandId).toBe("isacord");
  expect(r.shapes).toHaveLength(2);
  expect(r.shapes[0]).toMatchObject({
    id: "Sa", threadNumber: "1902", rgb: [204, 0, 0], areaMm2: 412.126,
    layer: 1, sewIndex: 1, sewBlock: 1, tier: "fill",
  });
  expect(r.shapes[0].outline.length).toBeLessThanOrEqual(48);
  // Endpoints survive thinning (aggregate check, not per-entry).
  expect(r.shapes[0].outline[0]).toEqual([0, 0]);
  expect(r.shapes[0].outline[r.shapes[0].outline.length - 1]).toEqual([299, 598]);
  expect(r.shapes[1].rgb).toEqual([0, 0, 0]);
  expect(r.shapes[1].tier).toBeNull();
  expect(thinOutline([[0, 0], [1, 1]])).toEqual([[0, 0], [1, 1]]); // short outlines pass through
  expect(reviewFromJob(null)).toBeNull();
});

test("reviewFromJob maps `stitched` (contract v1.1): explicit false for an excluded enclosed region, true when explicit, and true when the field is absent (a pre-contract service)", async () => {
  stubStorage({});
  const { reviewFromJob } = await import("./digitizer.js");
  const wire = {
    palette: [{ brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] }],
    shapes: [
      { shape_id: "Snormal", thread_index: 0, thread_number: "0020", area_mm2: 10, source: "quant",
        layer: 0, sew_index: 0, sew_block: 0, tier: "fill", outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Senclosed", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: null, sew_index: null, sew_block: null, tier: null, stitched: false,
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Sexplicit", thread_index: 0, thread_number: "0020", area_mm2: 5, source: "quant",
        layer: 0, sew_index: 1, sew_block: 0, tier: "fill", stitched: true,
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.shapes.map((s) => [s.id, s.stitched])).toEqual([
    ["Snormal", true], // field absent -> stitched, same as every shape before this contract
    ["Senclosed", false], // BACKGROUND_ENCLOSED, excluded by default
    ["Sexplicit", true],
  ]);
});

test("reviewFromJob maps text_candidate/text_cluster_id (text-cluster detection): true+id for a tagged shape, false+null for an untagged one, and false+null when a pre-contract service sends neither field", async () => {
  stubStorage({});
  const { reviewFromJob } = await import("./digitizer.js");
  const wire = {
    palette: [{ brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] }],
    shapes: [
      { shape_id: "Stagged", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 0, sew_block: 0, tier: "fill", text_candidate: true, text_cluster_id: "clu1",
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Suntagged", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 1, sew_block: 0, tier: "fill", text_candidate: false, text_cluster_id: null,
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Sold", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 2, sew_block: 0, tier: "fill",
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.shapes.map((s) => [s.id, s.textCandidate, s.textClusterId])).toEqual([
    ["Stagged", true, "clu1"],
    ["Suntagged", false, null],
    ["Sold", false, null],
  ]);
});

test("reviewFromJob maps ocr_char/ocr_confidence (OCR-suggested text): a real read, a measurement-failed null pair, and false-shaped defaults when a pre-contract service sends neither field", async () => {
  stubStorage({});
  const { reviewFromJob } = await import("./digitizer.js");
  const wire = {
    palette: [{ brand_id: "isacord", number: "0020", name: "Black", rgb: [0, 0, 0] }],
    shapes: [
      { shape_id: "Sread", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 0, sew_block: 0, tier: "fill", text_candidate: true, text_cluster_id: "clu1",
        ocr_char: "K", ocr_confidence: 91.0,
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Sfailed", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 1, sew_block: 0, tier: "fill", text_candidate: true, text_cluster_id: "clu1",
        ocr_char: null, ocr_confidence: null,
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
      { shape_id: "Sold", thread_index: 0, thread_number: "0020", area_mm2: 2, source: "quant",
        layer: 0, sew_index: 2, sew_block: 0, tier: "fill",
        outline_mm: [[0, 0], [1, 0], [1, 1]], holes_mm: [] },
    ],
  };
  const r = reviewFromJob(wire);
  expect(r.shapes.map((s) => [s.id, s.ocrChar, s.ocrConfidence])).toEqual([
    ["Sread", "K", 91.0],
    ["Sfailed", null, null],
    ["Sold", null, null],
  ]);
});

test("reconcileReview keeps a deleted shape's last known row so the panel can strike it through and restore it", async () => {
  stubStorage({});
  const { reconcileReview } = await import("./digitizer.js");
  const prev = { brandId: "isacord", shapes: [
    { id: "Sa", tier: "fill" }, { id: "Sdead", tier: "satin", areaMm2: 5 },
  ]};
  // The fresh review after digitizing WITH the deletion: Sdead is gone (the
  // engine dropped it after stage 4 — it was never planned).
  const fresh = { brandId: "isacord", shapes: [{ id: "Sa", tier: "fill" }] };
  const merged = reconcileReview(prev, fresh, ["Sdead"]);
  expect(merged.shapes.map((s) => s.id)).toEqual(["Sa", "Sdead"]);
  expect(merged.shapes[1].areaMm2).toBe(5); // the carried row is the old one
  // A deletion the previous review never knew either simply isn't renderable.
  expect(reconcileReview(prev, fresh, ["Sghost"]).shapes.map((s) => s.id)).toEqual(["Sa"]);
  // Un-deleted (restored, then applied): the fresh review wins outright.
  expect(reconcileReview(prev, fresh, []).shapes).toHaveLength(1);
  // No fresh review (a failed run patches nothing, but be safe): keep prev.
  expect(reconcileReview(prev, null, ["Sdead"])).toBe(prev);
});

// ---- adapter ---------------------------------------------------------------

test("decodedFromDesign strips the end record, centers on the sewn bbox, and counts every record type", async () => {
  stubStorage({});
  const { decodedFromDesign } = await import("./digitizer.js");
  // Uncentered on purpose: stitch bbox x 100..300, y 50..150 -> center (200, 100).
  const design = {
    stitches: [
      { x: 100, y: 50, type: "jump" },
      { x: 100, y: 50, type: "stitch" },
      { x: 300, y: 50, type: "stitch" },
      { x: 300, y: 150, type: "trim" },
      { x: 300, y: 150, type: "color" },
      { x: 300, y: 150, type: "stitch" },
      { x: 0, y: 0, type: "end" },
    ],
    colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }],
    name: "spec",
  };
  const dec = decodedFromDesign(design);
  expect(dec.stitchCount).toBe(3);
  expect(dec.jumpCount).toBe(1);
  expect(dec.trimCount).toBe(1);
  expect(dec.colorCount).toBe(2);
  expect(dec.widthMM).toBeCloseTo(20, 5);
  expect(dec.heightMM).toBeCloseTo(10, 5);
  expect(dec.stitches.some((s) => s.type === "end")).toBe(false);
  // Centered: first stitch (100,50) -> (-100,-50).
  const first = dec.stitches.find((s) => s.type === "stitch");
  expect(first.x).toBe(-100);
  expect(first.y).toBe(-50);
});

test("digitizedBlockColors defaults every block to the service palette; a user override wins per block", async () => {
  stubStorage({});
  const { digitizedBlockColors } = await import("./digitizer.js");
  const el = digitizedElement({
    result: { colors: [{ r: 0, g: 0, b: 0 }, { r: 204, g: 0, b: 0 }] },
    blockColors: { 1: [10, 20, 30] },
  });
  expect(digitizedBlockColors(el)).toEqual({ 0: [0, 0, 0], 1: [10, 20, 30] });
});

// ---- THE Y-AXIS GOLDEN (blueprint demand: day one) --------------------------
//
// fixtures/digitized-asym.json was captured from the LIVE service at this
// branch's base: asym_source.png is a black bar across the TOP of the image
// and a red square at the BOTTOM-LEFT, on white. The service Design is +y UP
// (digitizer_core/adapter.py owns the one flip), so in the app's design
// space the bar must sit at POSITIVE y and the red square at NEGATIVE y and
// NEGATIVE x. If any layer between the service and the field flips an axis,
// these signs invert and this fails.

function blocksOf(design) {
  const blocks = [[]];
  for (const s of design.stitches) {
    if (s.type === "color") blocks.push([]);
    else if (s.type === "stitch") blocks[blocks.length - 1].push(s);
  }
  return blocks;
}

test("GOLDEN: a service-digitized asymmetric design renders right way up (and right way round) through generateElement", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const el = digitizedElement({ result: fixture.design, warnings: fixture.warnings });
  const d = generateElement(el, garment, {});
  expect(d.stitchCount).toBe(fixture.design.stitchCount);
  expect(d.widthMM).toBeCloseTo(fixture.design.widthMM, 0);

  // Service thread palette flows through as block colors (black, then red).
  expect(d.colors[0]).toMatchObject({ r: 0, g: 0, b: 0 });
  expect(d.colors[1]).toMatchObject({ r: 204, g: 0, b: 0 });

  const blocks = blocksOf(d);
  expect(blocks).toHaveLength(2);
  // Aggregate min/max, then assert once (per-entry expect() over big arrays
  // is a known Vitest-timeout foot-gun in this repo).
  const bar = blocks[0], square = blocks[1];
  const barMinY = Math.min(...bar.map((s) => s.y));
  const squareMaxY = Math.max(...square.map((s) => s.y));
  const squareMaxX = Math.max(...square.map((s) => s.x));
  expect(bar.length).toBeGreaterThan(100);
  expect(barMinY).toBeGreaterThan(0); // the TOP bar sews entirely above center
  expect(squareMaxY).toBeLessThan(0); // the BOTTOM square entirely below
  expect(squareMaxX).toBeLessThan(0); // ...and on the LEFT
});

test("GOLDEN: placement controls act on the digitized result like any element (scale + offset)", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");

  const native = generateElement(digitizedElement({ result: fixture.design }), garment, {});
  const sized = generateElement(digitizedElement({ result: fixture.design, sizeMm: 20 }), garment, {});
  expect(sized.widthMM).toBeCloseTo(20, 1);
  expect(sized.heightMM).toBeCloseTo((20 / native.widthMM) * native.heightMM, 1);

  const shifted = generateElement(digitizedElement({ result: fixture.design, offsetXMm: 10 }), garment, {});
  const a = native.stitches.find((s) => s.type === "stitch");
  const b = shifted.stitches.find((s) => s.type === "stitch");
  expect(b.x).toBe(a.x + 100); // 10 mm = 100 units
  expect(b.y).toBe(a.y);
});

test("a digitized element with no result yet is not ready (null), and an element with a result needs no service at all", async () => {
  stubStorage({});
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const garment = EMB.getGarment("left_chest");
  expect(generateElement(digitizedElement(), garment, {})).toBeNull();
  // No fetch stub installed here: generation from the baked result must be
  // fully offline (the hybrid-persistence decision).
  const d = generateElement(digitizedElement({ result: fixture.design }), garment, {});
  expect(d.stitchCount).toBeGreaterThan(0);
});

test("export: Studio bakes its OWN DST from a digitized element and it round-trips through its own decoder", async () => {
  stubStorage({});
  const { generateAll } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const project = {
    version: 2, garmentId: "left_chest", selectedId: "e1", fabricRgb: [235, 232, 223],
    elements: [digitizedElement({ result: fixture.design })],
  };
  const { combined } = generateAll(project, {});
  const bytes = EMB.encodeDST(combined);
  expect(bytes.length).toBeGreaterThan(512);
  const back = EMB.decodeDST(bytes);
  // +1: the trailing "end" record encodes as one extra stitch at the design
  // origin (encodeDST's documented fall-through — see combine.js's note);
  // identical behavior to every other single-element export.
  expect(back.stitchCount).toBe(fixture.design.stitchCount + 1);
  expect(back.colorCount).toBe(fixture.design.colorCount);
  expect(back.widthMM).toBeCloseTo(combined.widthMM, 0);
});

// ---- warnings --------------------------------------------------------------

test("describeWarnings translates pipeline codes to customer language, with counts", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([
    { code: "DROPPED_SMALL_SHAPES", message: "engine prose", count: 3 },
    { code: "DROPPED_SMALL_SHAPES", message: "engine prose", count: 1 },
    { code: "LONG_JUMPS_TRIMMED", message: "engine prose", count: 2 },
  ]);
  expect(out[0].text).toBe("3 parts of the art were too small to sew and were left out.");
  expect(out[1].text).toBe("One part of the art was too small to sew and was left out.");
  expect(out[2].text).toBe("The thread gets cut 2 times where it has to travel a long way.");
});

test("describeWarnings speaks the two shape-edit codes: deletions agree with the panel's count, unmatched edits are named, not swallowed", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([
    { code: "SHAPES_DELETED_BY_USER", message: "engine prose", count: 2, ids: ["Sa", "Sb"] },
    { code: "SHAPE_EDIT_UNKNOWN_ID", message: "engine prose", count: 1, ids: ["Sz"] },
  ]);
  expect(out[0].text).toBe("2 shapes are hidden by you. Restore them from the Layers list to sew them again.");
  expect(out[1].text).toBe("One layer edit no longer matches any shape in the art, so it wasn't applied.");
});

test("describeWarnings falls back to the service's own message for a code it doesn't know (codes are append-only)", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([{ code: "SOME_FUTURE_CODE", message: "The engine said a thing." }]);
  expect(out[0].text).toBe("The engine said a thing.");
});

test("the fixture's own warnings translate cleanly (no raw codes leak to the panel)", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings(fixture.warnings);
  const anyRaw = out.some((w) => /_/.test(w.text));
  expect(anyRaw).toBe(false);
  expect(out.length).toBe(fixture.warnings.length);
});

// ---- shape identity edits (contract v1.5: merge and split) ------------------
//
// The other half of the shape-recognition gap `boundary_override` (above)
// didn't touch: `canonicalShapeEdits`'s mirror of the service's own
// canonicalization for `merge_shape_ids`/`split_shapes`, and the pure
// geometry helpers the two new controls use for live feedback
// (`mergeGroupIssues`, `splitLineIssues`) — the same shallow-check,
// server-has-the-final-word posture `boundaryIssues` already has.

test("canonicalShapeEdits dedupes and sorts merge groups, and sorts the outer list of groups, so two spellings of one merge are one edit", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const a = digitizedElement({ mergeGroups: [["B", "A", "A"], ["D", "C"]] });
  const b = digitizedElement({ mergeGroups: [["C", "D"], ["A", "B"]] });
  expect(canonicalShapeEdits(a)).toEqual({ merge_shape_ids: [["A", "B"], ["C", "D"]] });
  expect(editsKey(canonicalShapeEdits(a))).toBe(editsKey(canonicalShapeEdits(b)));
});

test("canonicalShapeEdits drops a merge group under the 2-shape minimum and an empty mergeGroups list entirely", async () => {
  stubStorage({});
  const { canonicalShapeEdits } = await import("./digitizer.js");
  const el = digitizedElement({ mergeGroups: [["A"], ["B", "C"]] });
  expect(canonicalShapeEdits(el)).toEqual({ merge_shape_ids: [["B", "C"]] });
  expect(canonicalShapeEdits(digitizedElement({ mergeGroups: [] }))).toEqual({});
  expect(canonicalShapeEdits(digitizedElement({ mergeGroups: [["A"]] }))).toEqual({});
});

test("canonicalShapeEdits accepts a valid split_shapes line, canonicalizes point order, coerces coordinates, and drops a zero-length or malformed one", async () => {
  stubStorage({});
  const { canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const forward = digitizedElement({ splitLines: { Q: [[0, -5], [0, 5]] } });
  const backward = digitizedElement({ splitLines: { Q: [[0, 5], [0, -5]] } });
  expect(canonicalShapeEdits(forward)).toEqual({ split_shapes: { Q: [[0, -5], [0, 5]] } });
  expect(editsKey(canonicalShapeEdits(forward))).toBe(editsKey(canonicalShapeEdits(backward)));

  const bad = digitizedElement({
    splitLines: {
      Zero: [[1, 1], [1, 1]],       // zero length -> dropped
      OnePoint: [[0, 0]],           // wrong shape -> dropped
      NotNum: [["a", 0], [1, 1]],   // not numbers -> dropped
    },
  });
  expect(canonicalShapeEdits(bad)).toEqual({});
});

test("merge_shape_ids/split_shapes ride buildDigitizeConfig and change the cache key (editsKey)", async () => {
  stubStorage({});
  const { buildDigitizeConfig, canonicalShapeEdits, editsKey } = await import("./digitizer.js");
  const plain = digitizedElement();
  const merged = digitizedElement({ mergeGroups: [["A", "B"]] });
  const split = digitizedElement({ splitLines: { Q: [[0, -5], [0, 5]] } });

  expect(editsKey(canonicalShapeEdits(merged))).not.toBe(editsKey(canonicalShapeEdits(plain)));
  expect(editsKey(canonicalShapeEdits(split))).not.toBe(editsKey(canonicalShapeEdits(plain)));

  const cfg = buildDigitizeConfig(merged, PROJECT);
  expect(cfg.merge_shape_ids).toEqual([["A", "B"]]);
  for (const k of Object.keys(cfg)) expect(PIPELINE_CONFIG_FIELDS).toContain(k);
  expect(buildDigitizeConfig(digitizedElement({ mergeGroups: [] }), PROJECT)).toEqual(
    buildDigitizeConfig(plain, PROJECT)
  );
});

test("mergeGroupIssues requires at least 2 shapes and rejects a selection spanning more than one thread", async () => {
  stubStorage({});
  const { mergeGroupIssues } = await import("./digitizer.js");
  expect(mergeGroupIssues([{ id: "A", threadNumber: "0020" }])[0]).toMatch(/at least 2/);
  expect(mergeGroupIssues([])[0]).toMatch(/at least 2/);
  expect(mergeGroupIssues([
    { id: "A", threadNumber: "0020" },
    { id: "B", threadNumber: "0020" },
  ])).toEqual([]);
  expect(mergeGroupIssues([
    { id: "A", threadNumber: "0020" },
    { id: "B", threadNumber: "1305" },
  ])[0]).toMatch(/one color/);
});

test("splitLineIssues is clean for a line crossing a simple square exactly twice, and flags too few points, a zero-length line, and a line crossing more than twice", async () => {
  stubStorage({});
  const { splitLineIssues } = await import("./digitizer.js");
  const square = [[0, 0], [10, 0], [10, 10], [0, 10]];
  expect(splitLineIssues(square, [[5, -6], [5, 6]])).toEqual([]);
  // Extended internally — a short line fully inside the square still crosses
  // its exterior exactly twice once extended along its own direction.
  expect(splitLineIssues(square, [[3, 3], [5, 4]])).toEqual([]);

  expect(splitLineIssues([[0, 0], [1, 1]], [[0, -6], [0, 6]])[0]).toMatch(/no outline/);
  expect(splitLineIssues(square, [[1, 1], [1, 1]])[0]).toMatch(/different/);
  expect(splitLineIssues(square, [])[0]).toMatch(/two points/);

  // A "comb" with two teeth: a horizontal cut through both teeth crosses 4
  // times, not 2 — the same concave-shape guardrail the core enforces.
  const comb = [[0, 0], [2, 10], [4, 0], [6, 10], [8, 0], [8, -2], [0, -2]];
  expect(splitLineIssues(comb, [[-5, 5], [15, 5]])[0]).toMatch(/exactly twice/);
});

// ---- text-cluster detection (Studio-side helpers) ---------------------------

test("textClusterIds returns unique cluster ids in first-seen order, only for text_candidate rows, ignoring rows with no cluster id", async () => {
  stubStorage({});
  const { textClusterIds } = await import("./digitizer.js");
  const rows = [
    { id: "A", textCandidate: true, textClusterId: "clu1" },
    { id: "B", textCandidate: true, textClusterId: "clu2" },
    { id: "C", textCandidate: true, textClusterId: "clu1" }, // same cluster as A -> not repeated
    { id: "D", textCandidate: false, textClusterId: "clu3" }, // not a candidate -> excluded
    { id: "E", textCandidate: true, textClusterId: null }, // candidate but no id -> excluded
  ];
  expect(textClusterIds(rows)).toEqual(["clu1", "clu2"]);
  expect(textClusterIds([])).toEqual([]);
  expect(textClusterIds(null)).toEqual([]);
});

test("textClusterMembers filters rows down to one cluster id", async () => {
  stubStorage({});
  const { textClusterMembers } = await import("./digitizer.js");
  const rows = [
    { id: "A", textClusterId: "clu1" },
    { id: "B", textClusterId: "clu2" },
    { id: "C", textClusterId: "clu1" },
  ];
  expect(textClusterMembers(rows, "clu1").map((r) => r.id)).toEqual(["A", "C"]);
  expect(textClusterMembers(rows, "nope")).toEqual([]);
});

test("textClusterSeed computes a design-center-relative offset, a height-based sizeMm guess, a majority-vote color, an empty text/fontKey, and rotationDeg 0", async () => {
  stubStorage({});
  const { textClusterSeed } = await import("./digitizer.js");
  // Two member letters side by side, each a 4mm-tall box; the design's other
  // (non-member) shape sits far to the right, pulling the overall design
  // bbox — and so its center — away from the cluster's own center.
  const members = [
    { id: "L1", rgb: [10, 10, 10], outline: [[0, 0], [2, 0], [2, 4], [0, 4]] },
    { id: "L2", rgb: [10, 10, 10], outline: [[3, 0], [5, 0], [5, 4], [3, 4]] },
  ];
  const allRows = [
    ...members,
    { id: "Other", rgb: [200, 0, 0], outline: [[0, 0], [25, 0], [25, 10], [0, 10]] },
  ];
  const seed = textClusterSeed(members, allRows);
  expect(seed.text).toBe("");
  expect(seed.fontKey).toBeNull();
  expect(seed.textSource).toBeNull(); // no ocrChar/ocrConfidence on these rows -> ungated
  expect(seed.rotationDeg).toBe(0);
  expect(seed.sizeMm).toBe(4); // cluster bbox height: 4 - 0
  expect(seed.colorRgb).toEqual([10, 10, 10]); // both members agree
  // Cluster bbox center: (2.5, 2); design bbox (all rows) center: (12.5, 5).
  expect(seed.offsetXMm).toBeCloseTo(2.5 - 12.5, 5);
  expect(seed.offsetYMm).toBeCloseTo(2 - 5, 5);
});

test("textClusterSeed picks the most common member color (majority vote, not an average) and falls back to a sane default with no rows", async () => {
  stubStorage({});
  const { textClusterSeed } = await import("./digitizer.js");
  const members = [
    { id: "A", rgb: [1, 1, 1], outline: [[0, 0], [1, 0], [1, 1], [0, 1]] },
    { id: "B", rgb: [9, 9, 9], outline: [[0, 0], [1, 0], [1, 1], [0, 1]] },
    { id: "C", rgb: [9, 9, 9], outline: [[0, 0], [1, 0], [1, 1], [0, 1]] },
  ];
  expect(textClusterSeed(members, members).colorRgb).toEqual([9, 9, 9]);

  const empty = textClusterSeed([], []);
  expect(empty.colorRgb).toEqual([20, 20, 20]);
  expect(empty.sizeMm).toBeNull();
  expect(empty.offsetXMm).toBe(0);
  expect(empty.offsetYMm).toBe(0);
});

// ---- textClusterSeed's OCR-suggested-text gate ------------------------------
//
// The UX-safety-critical half of this feature: a prefilled-but-wrong guess
// must be measurably rarer than an empty field, never a bare swap of one for
// the other. Every case below is asserted against the exact threshold
// (OCR_SUGGESTION_MIN_CONFIDENCE) so a constant change is a deliberate,
// visible diff here, not a silent behavior shift.

function ocrMember(id, x0, ocrChar, ocrConfidence) {
  return { id, rgb: [10, 10, 10], outline: [[x0, 0], [x0 + 1, 0], [x0 + 1, 2], [x0, 2]], ocrChar, ocrConfidence };
}

test("textClusterSeed fills text from ocrChar (left-to-right by bbox) and sets textSource when every member clears the confidence floor", async () => {
  stubStorage({});
  const { textClusterSeed, OCR_SUGGESTION_MIN_CONFIDENCE } = await import("./digitizer.js");
  // Deliberately supplied out of reading order — the seed must sort by each
  // member's own bbox minX, not array order.
  const members = [
    ocrMember("mid", 5, "G", OCR_SUGGESTION_MIN_CONFIDENCE + 10),
    ocrMember("first", 0, "O", OCR_SUGGESTION_MIN_CONFIDENCE + 30),
    ocrMember("last", 10, "K", OCR_SUGGESTION_MIN_CONFIDENCE),
  ];
  const seed = textClusterSeed(members, members);
  expect(seed.text).toBe("OGK");
  expect(seed.textSource).toBe("ocr-suggested");
  expect(seed.fontKey).toBeNull(); // OCR gives characters, never a typeface, regardless of confidence
});

test("textClusterSeed falls back to empty text/null textSource when the cluster's weakest member is below the confidence floor", async () => {
  stubStorage({});
  const { textClusterSeed, OCR_SUGGESTION_MIN_CONFIDENCE } = await import("./digitizer.js");
  const members = [
    ocrMember("A", 0, "O", 99),
    ocrMember("B", 1, "K", OCR_SUGGESTION_MIN_CONFIDENCE - 0.1), // the one weak link
  ];
  const seed = textClusterSeed(members, members);
  expect(seed.text).toBe("");
  expect(seed.textSource).toBeNull();
});

test("textClusterSeed gates on the CLUSTER MINIMUM, not a mean — one confident member cannot hide a weak one", async () => {
  stubStorage({});
  const { textClusterSeed, OCR_SUGGESTION_MIN_CONFIDENCE } = await import("./digitizer.js");
  // Mean of [100, 10] is 55, comfortably above a naive mean-based floor —
  // but the true minimum (10) must still fail the gate.
  const members = [ocrMember("A", 0, "X", 100), ocrMember("B", 1, "Y", 10)];
  expect(textClusterSeed(members, members).textSource).toBeNull();
});

test("textClusterSeed treats the gate boundary as inclusive (>=)", async () => {
  stubStorage({});
  const { textClusterSeed, OCR_SUGGESTION_MIN_CONFIDENCE } = await import("./digitizer.js");
  const atFloor = [ocrMember("A", 0, "K", OCR_SUGGESTION_MIN_CONFIDENCE)];
  expect(textClusterSeed(atFloor, atFloor).textSource).toBe("ocr-suggested");

  const justBelow = [ocrMember("A", 0, "K", OCR_SUGGESTION_MIN_CONFIDENCE - 0.01)];
  expect(textClusterSeed(justBelow, justBelow).textSource).toBeNull();
});

test("textClusterSeed treats a member with no OCR data (older service, or a failed per-member measurement) as no signal, not as confidence 0", async () => {
  stubStorage({});
  const { textClusterSeed } = await import("./digitizer.js");
  const members = [
    ocrMember("A", 0, "O", 99),
    ocrMember("B", 1, undefined, undefined), // Python's (None, None) case
  ];
  const seed = textClusterSeed(members, members);
  expect(seed.text).toBe("");
  expect(seed.textSource).toBeNull();
});

test("describeWarnings speaks the two shape-identity codes (contract v1.5)", async () => {
  stubStorage({});
  const { describeWarnings } = await import("./digitizer.js");
  const out = describeWarnings([
    { code: "SHAPES_MERGED_BY_USER", message: "engine prose", count: 1, groups: [] },
    { code: "SHAPE_SPLIT_BY_USER", message: "engine prose", count: 2, groups: [] },
  ]);
  expect(out[0].text).toBe("Two shapes were combined into one on the review screen.");
  expect(out[1].text).toBe("{n} shapes were cut into two on the review screen.".replace("{n}", "2"));
});
