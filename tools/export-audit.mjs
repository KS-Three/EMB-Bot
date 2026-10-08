// Export audit: every stitch format EMB-Bot writes, on REAL designs, read back
// by an independent reader and drawn beside the Studio's own preview.
//
// The crossval harness (tools/crossval-stitch-formats.mjs) and
// tools/preview-vs-dst.mjs both pin hand-built fixtures — a dozen stitches,
// one diagonal, one letter. This asks the wider question on what customers
// actually make: does every file a customer can download say what the screen
// said? It drives the Studio's own `generateAll` (app/src/lib/generate.js,
// the function the field and the Download step both read) on projects built
// from each element type —
//
//   shape      the basic-shapes tool (star, heart): shapesToRegions ->
//              buildQualityDesign, engine classifier picks satin/fill
//   manual     hand-drawn shapes with a chosen stitch per shape
//   text       shipped .embf fonts, single colour, per-letter colour, arc
//   digitized  real artwork through the Python digitizer's stage chain
//              (tools/export_audit_digitize.py) — the design the service
//              returns, stored as `element.result` exactly as the Studio does
//   design     a third-party .dst imported through decodeDST
//
// — then writes the combined design through every encoder a customer can
// reach: the browser's DST / EXP / PES (src/), and the service `/export`
// body (design_to_pattern + formats.write) for DST / PES / EXP / JEF / XXX /
// VP3, plus PEC and U01 which /health advertises but the Studio has no button
// for. Every file is decoded by pystitch through tools/crossval_decode.py —
// never by src/dstimport.js (CLAUDE.md footgun 1).
//
// Per design x format it reports what a reader sees against what the model
// says: sewn stitches, jumps, trims, colour changes, sewn extents,
// orientation and stray (preview-vs-dst's own measures, against the
// preview's strands), sewn thread length, and the per-block thread colour.
// With --renders DIR it also writes one PNG per design: the preview's
// strands, then each file as the reader decoded it, each panel fitted to its
// own extents so a mirror or a turn shows as one.
//
// Usage:
//   node tools/export-audit.mjs [--json] [--renders DIR] [--keep DIR]
//        [--logos a.png,b.png] [--logo-json FILE] [--only name,name]
//
// Python: the crossval harness's resolution ($EMB_CROSSVAL_PYTHON, then the
// digitizer venv). The digitized designs need the full digitizer deps; with
// --no-digitize they are skipped and the rest still runs.
import { createRequire } from "module";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolvePython, pyDecode, longestSewnSegment } from "./crossval-stitch-formats.mjs";
import {
  fileSegments, travelSegments, bbox, threadUnits, maxStrayUnits, orientationFit,
} from "./preview-vs-dst.mjs";
import { designToStrands } from "../app/src/lib/strands.js";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
globalThis.window = globalThis;
// The Studio's engine list, in its load order (app/src/lib/emb.js ENGINE_KEYS).
for (const f of [
  "units.js", "sewtime.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "crossfill.js", "satinfont.js",
  "fontbin.js", "svgpath.js", "svgimport.js",
  "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "digitize.js", "render.js",
]) require(path.join(ROOT, "src", f));
const EMB = globalThis.EMB;
const { generateAll } = await import("../app/src/lib/generate.js");
const P = await import("../app/src/lib/project.js");

const U = 10; // units per mm

export const BROWSER_FORMATS = ["dst", "exp", "pes"];
// The service formats a customer reaches (Download step buttons), then the two
// /health advertises without a button. Kept apart so the table says which is which.
export const SERVICE_FORMATS = ["dst", "pes", "exp", "jef", "xxx", "vp3"];
export const SERVICE_UNSHIPPED = ["pec", "u01"];

function loadFont(key) {
  EMB.SATIN_FONTS = EMB.SATIN_FONTS || {};
  if (!EMB.SATIN_FONTS[key]) {
    EMB.SATIN_FONTS[key] = EMB.decodeFontBin(fs.readFileSync(path.join(ROOT, "src/fonts/bin", key + ".embf")));
  }
}

function project(garmentId, elements) {
  return { ...P.defaultProject(), garmentId, elements, selectedId: elements[0].id, selectedIds: [elements[0].id] };
}

function text(id, str, extra = {}) {
  const el = { ...P.defaultTextElement(id), text: str, ...extra };
  loadFont(el.fontKey);
  return el;
}

function shape(id, kind, extra = {}) {
  return { ...P.defaultShapeElement(id), kind, ...extra };
}

// Canvas-pixel rings, the frame ManualPanel draws in (600 x 400).
function ring(cx, cy, r, n, phase = 0) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = phase + (i / n) * Math.PI * 2;
    pts.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  }
  return pts;
}

function manual(id) {
  const el = P.defaultManualElement(id);
  el.shapes = [
    { ...P.defaultManualShape("m1"), points: [{ x: 120, y: 90 }, { x: 470, y: 90 }, { x: 470, y: 300 }, { x: 120, y: 300 }], stitchType: "fill", colorRgb: [20, 40, 110] },
    { ...P.defaultManualShape("m2"), points: ring(240, 195, 70, 40), stitchType: "fill", colorRgb: [240, 230, 200] },
    // An L-shaped stroke wide enough for a satin column, off to the right.
    { ...P.defaultManualShape("m3"), points: [{ x: 330, y: 130 }, { x: 350, y: 130 }, { x: 350, y: 250 }, { x: 440, y: 250 }, { x: 440, y: 270 }, { x: 330, y: 270 }], stitchType: "satin", colorRgb: [190, 30, 40] },
  ];
  return el;
}

// The digitized element the Studio stores: the service's `design` as
// `element.result`, generated offline through buildImportedDesign.
function digitized(id, design, extra = {}) {
  return { ...P.defaultDigitizedElement(id), result: design, ...extra };
}

function importedDst(id, file, extra = {}) {
  return { ...P.defaultDesignElement(id), dstBase64: fs.readFileSync(file).toString("base64"), ...extra };
}

export function buildProjects(logoDesigns = {}) {
  const out = {
    shape_star: project("left_chest", [shape("e1", "star", { colorRgb: [200, 30, 40] })]),
    shape_heart: project("left_chest", [shape("e1", "heart", { colorRgb: [220, 80, 140], sizeMm: 70 })]),
    manual_three: project("left_chest", [manual("e1")]),
    text_fritsch: project("left_chest", [text("e1", "FRITSCH")]),
    text_two_colour: project("left_chest", [text("e1", "Fritsch's Stitches", {
      colorRanges: [{ startIdx: 0, endIdx: 7, colorRgb: [20, 60, 160] }, { startIdx: 7, endIdx: 99, colorRgb: [200, 40, 40] }],
    })]),
    text_arc_script: project("left_chest", [text("e1", "Embroidery", { fontKey: "allegria55", arcDeg: 70 })]),
    mixed_full_back: project("full_back", [
      text("e1", "STITCHES", { fontKey: "manga_impact", sizeMm: 260, offsetYMm: 60 }),
      shape("e2", "star", { colorRgb: [30, 120, 60], sizeMm: 140, offsetYMm: -50 }),
    ]),
  };
  for (const [name, design] of Object.entries(logoDesigns)) {
    // As the customer has it: the default project's empty text element stays
    // (DOCTRINE 2026-09-07 — almost no real project removes it).
    out["logo_" + name] = project("left_chest", [P.defaultTextElement("e0"), digitized("e1", design)]);
  }
  const firstLogo = Object.keys(logoDesigns)[0];
  if (firstLogo) {
    // The resized path: a digitized logo enlarged on the field crosses the
    // one-record bar, so every encoder has to split.
    out["logo_" + firstLogo + "_250mm"] = project("full_back", [digitized("e1", logoDesigns[firstLogo], { sizeMm: 250 })]);
  }
  const becker = path.join(ROOT, "digitizer/testdata/reference/becker_chest_small_beckers_logo_lc_2_a.dst");
  if (fs.existsSync(becker)) out.imported_becker_dst = project("left_chest", [importedDst("e1", becker)]);
  return out;
}

// ---- what the MODEL says --------------------------------------------------
export function modelFacts(design) {
  const c = { stitch: 0, jump: 0, trim: 0, color: 0 };
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of design.stitches) {
    const t = s.type || "stitch";
    if (t in c) c[t]++;
    if (t === "stitch") {
      x0 = Math.min(x0, s.x); x1 = Math.max(x1, s.x);
      y0 = Math.min(y0, s.y); y1 = Math.max(y1, s.y);
    }
  }
  const segs = designToStrands(design).map((s) => [s.x0, s.y0, s.x1, s.y1]);
  let longest = 0;
  for (const s of segs) longest = Math.max(longest, Math.hypot(s[2] - s[0], s[3] - s[1]));
  return {
    stitches: c.stitch, jumps: c.jump, trims: c.trim, colorChanges: c.color,
    sizeMm: [+((x1 - x0) / U).toFixed(1), +((y1 - y0) / U).toFixed(1)],
    longestSewnMm: +(longest / U).toFixed(1),
    threadMm: +(threadUnits(segs) / U).toFixed(1),
    colors: (design.colors || []).map((k) => [k.r, k.g, k.b]),
  };
}

// ---- what the READER says -------------------------------------------------
// Block colours in the file: the thread pystitch assigns each sewn block, in
// order. Formats with no thread table (DST, EXP, XXX's fallbacks) read [].
function blockThreads(d) {
  const out = [];
  let k = 0, sewn = false;
  for (const [, , cmd] of d.stitches) {
    if (cmd === "COLOR_CHANGE") { if (sewn) out.push(d.threads[k] || null); k++; sewn = false; continue; }
    if (cmd === "STITCH") sewn = true;
  }
  if (sewn) out.push(d.threads[k] || null);
  return out;
}

function longestAxis(records) {
  let prev = null, worst = 0;
  for (const [x, y, cmd] of records) {
    if (cmd !== "STITCH") { prev = null; continue; }
    if (prev) worst = Math.max(worst, Math.abs(x - prev[0]), Math.abs(y - prev[1]));
    prev = [x, y];
  }
  return worst;
}

function rgbDist(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

function hexToRgb(h) {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

export function readerFacts(design, d, model) {
  const previewSegs = designToStrands(design).map((s) => [s.x0, s.y0, s.x1, s.y1]);
  const segs = fileSegments(d.stitches);
  const pb = bbox(previewSegs), fb = bbox(segs);
  const off = pb && fb ? [pb[0] - fb[0], pb[1] - fb[1]] : [0, 0];
  const aligned = segs.map((s) => [s[0] + off[0], s[1] + off[1], s[2] + off[0], s[3] + off[1]]);
  const xs = [], ys = [];
  for (const [x, y, cmd] of d.stitches) if (cmd === "STITCH") { xs.push(x); ys.push(-y); }
  const blocks = blockThreads(d);
  // Worst block colour against the design's own colour for that block. Null
  // when the format carries no colours at all — that is a format fact, not
  // a disagreement.
  let worstColor = null;
  if (d.threads.length) {
    worstColor = 0;
    blocks.forEach((h, i) => {
      const want = model.colors[i];
      if (!want || !h) { worstColor = Infinity; return; }
      worstColor = Math.max(worstColor, rgbDist(hexToRgb(h), want));
    });
    worstColor = Number.isFinite(worstColor) ? +worstColor.toFixed(1) : "missing";
  }
  return {
    stitches: d.counts.STITCH || 0,
    jumps: d.counts.JUMP || 0,
    trims: d.counts.TRIM || 0,
    colorChanges: d.counts.COLOR_CHANGE || 0,
    stops: d.counts.STOP || 0,
    other: Object.fromEntries(Object.entries(d.counts).filter(([k]) => !["STITCH", "JUMP", "TRIM", "COLOR_CHANGE", "STOP", "END"].includes(k))),
    sewnBlocks: blocks.length,
    threads: d.threads.length,
    worstBlockColorDist: worstColor,
    sizeMm: xs.length ? [+((Math.max(...xs) - Math.min(...xs)) / U).toFixed(1), +((Math.max(...ys) - Math.min(...ys)) / U).toFixed(1)] : null,
    longestSewnMm: +(longestSewnSegment(d.stitches) / U).toFixed(1),
    // Per axis, which is what a record limits: a 121 x 121 diagonal is 17.1 mm
    // long and still one DST record.
    longestSewnAxisMm: +(longestAxis(d.stitches) / U).toFixed(1),
    threadMm: +(threadUnits(segs) / U).toFixed(1),
    // Strided: an off-identity transform falls back to a full scan per point,
    // which is quadratic on a 25k-stitch design. ~1500 segments decide it.
    orientation: orientationFit(previewSegs, segs, Math.max(1, Math.ceil(segs.length / 1500))).best,
    strayMm: +((maxStrayUnits(aligned, previewSegs) || 0) / U).toFixed(2),
    missedMm: +((maxStrayUnits(previewSegs, aligned) || 0) / U).toFixed(2),
  };
}

// The disagreements worth a human's eyes, as words. Each rule says why it is
// a disagreement rather than a format convention.
export function flags(model, r, fmt) {
  const f = [];
  if (r.orientation !== "identity") f.push(`orientation ${r.orientation}`);
  // A split adds stitches (a long move laid as several); it never removes one.
  if (r.stitches < model.stitches) f.push(`lost ${model.stitches - r.stitches} stitches`);
  if (r.colorChanges !== model.colorChanges && !(fmt === "u01")) f.push(`colour changes ${r.colorChanges} vs ${model.colorChanges}`);
  // U01 changes thread with NEEDLE_SET (pystitch command 9; crossval_decode
  // names it CMD_9), one to set the first needle and one per change.
  if (fmt === "u01" && Math.max(0, (r.other.CMD_9 || 0) - 1) !== model.colorChanges) f.push(`needle changes ${Math.max(0, (r.other.CMD_9 || 0) - 1)} vs ${model.colorChanges} colour changes`);
  if (r.sizeMm && (Math.abs(r.sizeMm[0] - model.sizeMm[0]) > 0.2 || Math.abs(r.sizeMm[1] - model.sizeMm[1]) > 0.2)) {
    f.push(`size ${r.sizeMm.join("x")} vs ${model.sizeMm.join("x")}`);
  }
  if (r.strayMm > 0.2) f.push(`thread strays ${r.strayMm} mm from the preview`);
  if (r.missedMm > 0.2) f.push(`preview thread missing from file by ${r.missedMm} mm`);
  if (Math.abs(r.threadMm - model.threadMm) > Math.max(1, model.threadMm * 0.002)) f.push(`sewn thread ${r.threadMm} vs ${model.threadMm} mm`);
  // 12.7 mm: EXP's record, the widest of the three bars (DST 12.1).
  if (r.longestSewnAxisMm > 12.7) f.push(`sews a stitch ${r.longestSewnAxisMm} mm along one axis`);
  const other = Object.keys(r.other).filter((k) => !(fmt === "u01" && k === "CMD_9"));
  if (other.length) f.push(`unexpected ${other.join(", ")}`);
  if (r.worstBlockColorDist === "missing") f.push("a sewn block has no thread");
  return f;
}

// ---- harness ----------------------------------------------------------------
function runPy(python, args) {
  const r = spawnSync(python, args, { encoding: "utf8", timeout: 1800000, maxBuffer: 64 * 1024 * 1024 });
  if (r.status !== 0) throw new Error(`${args[0]} failed: ${r.stderr || r.error}`);
  return r.stdout;
}

export function digitizeLogos(python, images, dir) {
  if (!images.length) return {};
  const out = path.join(dir, "logos.json");
  runPy(python, [path.join(ROOT, "tools/export_audit_digitize.py"), out, ...images]);
  return JSON.parse(fs.readFileSync(out, "utf8"));
}

function colorHex(rgb) {
  return "#" + rgb.map((v) => Math.max(0, Math.min(255, v | 0)).toString(16).padStart(2, "0")).join("");
}

// A file's sewn segments coloured by the thread the reader assigned each block;
// with no thread table, by the design's colour for that block index (said in
// the panel title, so the picture does not claim the file carried colour).
function readerPanel(d, model) {
  const segs = [];
  let prev = null, k = 0;
  const pick = () => (d.threads.length ? d.threads[k] || "#ff00ff" : colorHex(model.colors[k] || [255, 0, 255]));
  for (const [x, y, cmd] of d.stitches) {
    if (cmd === "COLOR_CHANGE") { k++; prev = null; continue; }
    if (cmd !== "STITCH") { prev = null; continue; }
    const p = [x, -y];
    if (prev) segs.push([prev[0], prev[1], p[0], p[1], pick()]);
    prev = p;
  }
  return { segs, travel: travelSegments(d.stitches) };
}

export function runAudit({ python = resolvePython(), logos = null, logoJson = null, only = null, renders = null, keepDir = null, digitize = true } = {}) {
  if (!python) throw new Error("No python with pystitch found (set EMB_CROSSVAL_PYTHON or create digitizer/.venv)");
  const dir = keepDir || fs.mkdtempSync(path.join(os.tmpdir(), "emb-export-audit-"));
  fs.mkdirSync(dir, { recursive: true });
  const art = path.join(ROOT, "digitizer/testdata/art");
  const images = digitize
    ? (logos || ["logo_golke_roofing.png", "logo_mfab_lc.png", "logo_hotel_fremont_patch.png"]).map((f) => path.isAbsolute(f) ? f : path.join(art, f))
    : [];
  // --logo-json reuses a previous run's digitized designs (written to
  // <keep>/logos.json): the digitizer is the slow half of a run.
  const logoDesigns = logoJson ? JSON.parse(fs.readFileSync(logoJson, "utf8")) : digitizeLogos(python, images, dir);
  let projects = buildProjects(logoDesigns);
  if (only) projects = Object.fromEntries(Object.entries(projects).filter(([k]) => only.includes(k)));

  const designs = {};
  const files = [];
  for (const [name, proj] of Object.entries(projects)) {
    const { combined } = generateAll(proj, {});
    designs[name] = combined;
    for (const [fmt, enc] of [["dst", EMB.encodeDST], ["exp", EMB.encodeEXP], ["pes", EMB.encodePES]]) {
      const f = path.join(dir, `${name}.web.${fmt}`);
      fs.writeFileSync(f, Buffer.from(enc(combined)));
      files.push(f);
    }
  }
  // What exportViaService posts: the combined design, JSON round-tripped.
  fs.writeFileSync(path.join(dir, "designs.json"), JSON.stringify(designs));
  const svcFormats = [...SERVICE_FORMATS, ...SERVICE_UNSHIPPED];
  runPy(python, [path.join(ROOT, "tools/export_audit.py"), "write", path.join(dir, "designs.json"), dir, ...svcFormats]);
  for (const name of Object.keys(designs)) for (const fmt of svcFormats) files.push(path.join(dir, `${name}.svc.${fmt}`));
  const decoded = pyDecode(python, files);

  const routes = [
    ...BROWSER_FORMATS.map((f) => ["web", f]),
    ...svcFormats.map((f) => ["svc", f]),
  ];
  const results = {};
  for (const [name, design] of Object.entries(designs)) {
    const model = modelFacts(design);
    const row = { model, files: {} };
    const panels = [{
      title: `EMB-Bot preview (designToStrands)\n${model.sizeMm.join(" x ")} mm  ${model.stitches} st  ${model.colorChanges} cc  ${model.trims} trims`,
      segs: designToStrands(design).map((s) => [s.x0, s.y0, s.x1, s.y1, colorHex(s.rgb)]),
      travel: [],
    }];
    for (const [route, fmt] of routes) {
      const key = `${route}.${fmt}`;
      const d = decoded[`${name}.${route}.${fmt}`];
      if (!d || d.error) { row.files[key] = { error: (d && d.error) || "no decode output" }; continue; }
      const r = readerFacts(design, d, model);
      r.flags = flags(model, r, fmt);
      row.files[key] = r;
      const pan = readerPanel(d, model);
      panels.push({
        title: `${route === "web" ? "browser" : "service"} ${fmt.toUpperCase()} via pystitch${d.threads.length ? "" : " (no colours in file)"}\n` +
          `${r.sizeMm ? r.sizeMm.join(" x ") : "-"} mm  ${r.stitches} st  ${r.colorChanges} cc  ${r.trims} trims  ${r.jumps} jumps\n` +
          (r.flags.length ? "! " + r.flags.join("; ") : "agrees"),
        ...pan,
      });
    }
    results[name] = row;
    if (renders) {
      fs.mkdirSync(renders, { recursive: true });
      const spec = path.join(dir, `${name}.render.json`);
      fs.writeFileSync(spec, JSON.stringify({ title: `${name} — left: the Studio preview; then each file as pystitch reads it (each panel fitted to its own extents)`, panels }));
      runPy(python, [path.join(ROOT, "tools/export_audit.py"), "render", spec, path.join(renders, `${name}.png`)]);
    }
  }
  if (!keepDir) fs.rmSync(dir, { recursive: true, force: true });
  return { python, results };
}

export function report(results) {
  const lines = [];
  for (const [name, row] of Object.entries(results)) {
    const m = row.model;
    lines.push(`== ${name}: model ${m.stitches} st, ${m.jumps} jumps, ${m.trims} trims, ${m.colorChanges} cc, ${m.sizeMm.join("x")} mm, longest sewn ${m.longestSewnMm} mm, thread ${m.threadMm} mm`);
    for (const [key, r] of Object.entries(row.files)) {
      if (r.error) { lines.push(`  ${key.padEnd(8)} ERROR ${r.error}`); continue; }
      lines.push(
        `  ${key.padEnd(8)} ${String(r.stitches).padStart(6)} st ${String(r.jumps).padStart(5)} j ${String(r.trims).padStart(4)} t ${String(r.colorChanges).padStart(3)} cc` +
        ` ${(r.sizeMm || []).join("x").padStart(12)}  ${r.orientation.padEnd(8)} stray ${r.strayMm}  col ${r.worstBlockColorDist}` +
        (r.flags.length ? "  << " + r.flags.join("; ") : ""),
      );
    }
  }
  return lines.join("\n");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  const val = (k) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : null; };
  const out = runAudit({
    logos: val("--logos") ? val("--logos").split(",") : null,
    logoJson: val("--logo-json"),
    only: val("--only") ? val("--only").split(",") : null,
    renders: val("--renders"),
    keepDir: val("--keep"),
    digitize: !argv.includes("--no-digitize"),
  });
  if (argv.includes("--json")) console.log(JSON.stringify(out, null, 2));
  else console.log(report(out.results));
}
