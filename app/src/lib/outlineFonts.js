// Outline fonts: TrueType/OpenType fonts the digitizer SERVICE lays out and
// stitches on demand (POST /lettering), beside the pre-digitized `.embf`
// library the browser engine sews on its own.
//
// Kent, 2026-11-06: "import some more fonts, that are not pre-digitized, but
// embot will have the ability to digitize them (slower, but easier than
// importing an image of the font)". The service side is
// digitizer/digitizer_core/outline_fonts.py: the font's own curves go to the
// Column lane as lettering-tagged shapes, so a typed word gets the same satin
// construction a word traced out of artwork gets, without the trace. This
// module is the Studio's half: the font rows, the request, the key that says
// whether a stored result is behind its settings, and the run.
//
// A text element keeps using `fontKey`; an outline font's key carries the
// `outline:` prefix (`outline:montserrat-bold`), so every reader that switches
// on the key can tell the two kinds apart without a second field, and a
// project saved with one loads as a text element whose font the browser
// engine does not have — exactly the state a text element is in while its
// `.embf` is still downloading, which every path already survives.
//
// The result lands on the element the way a `digitized` element's does:
// `result` (the service Design), `appliedConfig` (the key of the request it
// was digitized with), `stats`/`review`/`preflight`/`warnings`, and the
// service's `lettering` echo. generate.js renders it through
// buildImportedDesign; staleness.js compares `appliedConfig` with the request
// the element would send NOW (text, font, width, spacing, colour, garment,
// fabric, chart) so Download stays disabled until the customer re-digitizes
// (Kent's 2026-10-25 ruling, lib/staleness.js). Nothing runs on its own
// (2026-10-05): the run is the button in TextStep.
import { digitizerUrl, pollJob, configKey, canonicalFabricProfile } from "./digitizer.js";
import { loadPreferredPaletteId } from "./threads.js";

export const OUTLINE_PREFIX = "outline:";
export const OUTLINE_GROUP = "Outline";

export function isOutlineKey(key) {
  return typeof key === "string" && key.startsWith(OUTLINE_PREFIX);
}

export function serviceKeyOf(fontKey) {
  return isOutlineKey(fontKey) ? fontKey.slice(OUTLINE_PREFIX.length) : fontKey;
}

export function outlineKeyOf(serviceKey) {
  return OUTLINE_PREFIX + serviceKey;
}

// The CSS family name the font browser previews an outline font under: the
// service serves the TTF itself (GET /fonts/outline/{key}/file), and the
// browser's own text engine draws the tile — no satin render exists for a
// font that has never been digitized.
export function previewFamily(fontKey) {
  return "embot-outline-" + serviceKeyOf(fontKey).replace(/[^a-z0-9-]/gi, "-");
}

// One service row -> a manifest-shaped font row, so FontBrowser, FontSelect
// and FontCredits read it exactly as they read `src/fonts/manifest.json`'s.
// `tier: "verified"` because the loader keeps only verified rows (every font
// here passed the licence gate at fetch time: OFL, unmodified, licence text
// beside the file — tools/fetch_outline_fonts.py).
export function outlineFontRow(row, base) {
  const origin = String(base || "").replace(/\/+$/, "");
  const name = row.name || row.key;
  return {
    key: outlineKeyOf(row.key),
    serviceKey: row.key,
    name,
    family: row.family || name,
    group: OUTLINE_GROUP,
    styleGroup: row.group || "",
    weight: row.weight || 400,
    style: row.style || "Regular",
    tier: "verified",
    kind: "outline",
    licenseId: row.licenseId || "OFL-1.1",
    attribution:
      `${name} is an unmodified copy of the ${row.family || name} font family, ` +
      `licensed under the SIL Open Font License, Version 1.1; its licence text ships with the stitch service. ` +
      `Digitized to satin stitches on demand by EMB-Bot.`,
    source: row.source || "",
    fileUrl: origin + (row.file || `/fonts/outline/${row.key}/file`),
    licenseUrl: origin + (row.license || `/fonts/outline/${row.key}/license`),
    // The .embf manifest's `sizeMm` is a hand-digitized font's best size;
    // an outline font sews at whatever size the Column lane is given.
    sizeMm: null,
  };
}

// GET /fonts/outline -> { rows, coverage }: the rows above plus the coverage
// map in lib/fontCoverage.js's shape (key -> codepoints or [lo, hi] runs),
// keyed by the OUTLINE key so "fits your text" can merge it straight into the
// `.embf` coverage. Throws on any failure; the loader decides what that means.
export async function fetchOutlineFonts(fetchFn = globalThis.fetch, base = digitizerUrl()) {
  const r = await fetchFn(base + "/fonts/outline");
  if (!r.ok) throw new Error("outline fonts: HTTP " + r.status);
  const body = await r.json();
  const rows = [];
  const coverage = {};
  for (const row of (body && body.fonts) || []) {
    if (!row || !row.key) continue;
    const out = outlineFontRow(row, base);
    rows.push(out);
    if (Array.isArray(row.coverage)) coverage[out.key] = row.coverage;
  }
  return { rows, coverage };
}

// Load each outline font into the page under its preview family, once. The
// FontFace API is absent under jsdom and in a worker; both are fine without
// previews. A variable TTF answers every weight; the per-row weight picks.
const registered = new Set();
export function registerFontFaces(rows) {
  if (typeof document === "undefined" || !document.fonts || typeof FontFace === "undefined") return;
  for (const row of rows || []) {
    const family = previewFamily(row.key);
    const id = family + "@" + row.weight;
    if (registered.has(id)) continue;
    registered.add(id);
    try {
      const face = new FontFace(family, `url(${row.fileUrl})`, { weight: String(row.weight || 400) });
      document.fonts.add(face);
      face.load().catch(() => {});
    } catch (e) { /* no preview for this one */ }
  }
}

// The width the service lays the text out at: the element's own Design width
// when the customer typed or dragged one, else the placement box's width —
// "the most that fits where it sits" (lib/placement.js). In the 10-400 mm
// range the Design width field accepts.
export function outlineWidthMm(element, project) {
  const typed = element && Number(element.sizeMm);
  if (typed > 0) return Math.min(400, Math.max(10, Math.round(typed * 10) / 10));
  const box = placementBox(project);
  const w = box && box.w > 0 ? box.w : 80;
  return Math.min(400, Math.max(10, Math.round(w * 10) / 10));
}

// lib/placement.js's placementBoxOf, read off the engine global directly so
// this module (and flow.js / staleness.js through it) imports without the
// engine loaded — lib/emb.js throws at import time when it is not, and
// those two are imported by specs that never load it. Same resolution:
// the project's placement when the engine knows placements, else the
// garment's inch pair. Null without an engine or a garment.
const MM_PER_INCH = 25.4;
function placementBox(project) {
  const EMB = typeof globalThis !== "undefined" ? globalThis.EMB : null;
  if (!EMB || !project || !project.garmentId) return null;
  const g = EMB.resolvePlacement
    ? EMB.resolvePlacement(project.garmentId, project.placementId || null)
    : (EMB.getGarment ? EMB.getGarment(project.garmentId) : null);
  if (!g) return null;
  if (EMB.placementBoxMm) return EMB.placementBoxMm(g);
  return { w: g.widthIn * MM_PER_INCH, h: g.heightIn * MM_PER_INCH };
}

// The POST /lettering body this element would send NOW. Every field the
// service reads is here and nothing else, because its key (below) is what
// decides whether a stored result is behind: text, font, width, letter
// spacing, line justification, thread colour, and the garment-side config
// the image route sends too (garment, fabric colour, calibration profile,
// chart). Canonical spellings so a no-op edit is the same key.
export function outlineRequest(element, project) {
  const rgb = Array.isArray(element.colorRgb) && element.colorRgb.length >= 3
    ? element.colorRgb.slice(0, 3).map((v) => Math.max(0, Math.min(255, Math.round(Number(v) || 0))))
    : [0, 0, 0];
  const req = {
    font: serviceKeyOf(element.fontKey),
    text: String(element.text || "").replace(/\s+$/, ""),
    width_mm: outlineWidthMm(element, project),
    thread_rgb: rgb,
    config: {},
  };
  const spacing = Number(element.letterSpacingMm) || 0;
  if (spacing) req.letter_spacing_mm = Math.round(spacing * 100) / 100;
  const align = element.align || "center";
  if (align !== "center") req.align = align;
  const cfg = req.config;
  if (project && project.garmentId) cfg.garment_id = project.garmentId;
  if (project && Array.isArray(project.fabricRgb) && project.fabricRgb.length >= 3) {
    cfg.garment_rgb = project.fabricRgb.slice(0, 3).map((v) => Math.round(Number(v)));
  }
  const profile = canonicalFabricProfile(project && project.fabricProfile);
  if (profile) cfg.fabric_profile = profile;
  const brand = loadPreferredPaletteId();
  if (brand && brand !== "studio") cfg.thread_brand = brand;
  return req;
}

export function outlineRequestKey(req) {
  return configKey(req);
}

// A stored result is behind when the request it would send now is not the
// one it was digitized with. No result: nothing to be behind (the element is
// simply not sewable yet — lib/flow.js).
export function outlineStale(element, project, { baselineKey = null } = {}) {
  if (!element || !isOutlineKey(element.fontKey) || !element.result) return false;
  const applied = element.appliedConfig || baselineKey;
  if (!applied) return false;
  return outlineRequestKey(outlineRequest(element, project)) !== applied;
}

async function httpDetail(r) {
  try {
    const body = await r.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch (e) { /* not JSON */ }
  return "The digitizer answered " + r.status + ".";
}

// POST /lettering -> { job_id, state, cached }.
export async function startLettering(req, fetchFn = globalThis.fetch) {
  const r = await fetchFn(digitizerUrl() + "/lettering", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!r.ok) {
    const e = new Error(await httpDetail(r));
    e.status = r.status;
    throw e;
  }
  return r.json();
}

// Submit and poll, exactly as lib/digitizer.js's `digitize` does for an
// image: the same /jobs/{id} poll, the same states, the same budget.
export async function digitizeLettering(req, opts = {}) {
  const sub = await startLettering(req, opts.fetchFn || globalThis.fetch);
  return pollJob(sub.job_id, opts);
}
