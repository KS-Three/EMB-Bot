// Small-cap census of the Studio font engine (2026-10-12). MEASURES ONLY: no
// engine file is touched, nothing here is a physical constant (ROADMAP gate 1).
//
// Kent's direction: fonts should not be an issue, even with thin thread.
// docs/fine-detail-hair-research-2026-10-12.md section 5 puts the 40 wt
// lettering floor near 6 mm; the Studio warns under CAP_FLOOR_MM 4. Nobody had
// measured what the engine actually sews at 2.5 to 6 mm caps. This does.
//
// Every shipped font x each cap goes through buildLetteringDesign the way the
// Studio's generateElement calls it for a text element (pxPerMm 8, normal weight,
// no fabric, engine defaults for everything else), at a cap height set by
// `targetWidthMm` -- the knob the Studio's size field turns. The cap is
// CALIBRATED from the engine's own report: one build at a trial width gives
// capMm, and capMm is linear in the fit scale, so the width that lands the cap on
// the target is trial * target / capMm. The final build's own capMm is recorded
// (and `capMiss` flags a cell more than 2% off), so the table says what it
// measured, not what it asked.
//
// Floors, all READ from satinfont.LETTERING_GUARDS and named here, never restated:
//   SHORT_STITCH_AT_MM 0.3  the engine's short-stitch floor (Law 53)
//   SATIN_MIN_CROSS_MM 0.5  a satin cross under this is sewn as a bean run
//   COLUMN_FLOOR_MM    1.0  the minimum column width; reported, never clamped
//
// Per (font, text, cap) cell, read off the stitch stream the encoders get:
//   sewn        consecutive stitch->stitch segments (a jump / trim / colour cuts
//               the chain -- the long-stitch census's rule)
//   sub03       sewn segments under SHORT_STITCH_AT_MM (Euclidean, includes the
//               exact repeats). THE headline short-stitch count. The satin pitch
//               is 0.4 mm, so a healthy satin step is never under it.
//   sub05,sub1  under 0.5 / 1.0 mm. sub05 has a floor of about the satin share
//               of the stream (the 0.4 mm rail step is under 0.5 by construction).
//   repeat      same-hole repeats: two stitch records on one spot, length 0
//   overRec     sewn segments past one DST record: max(|dx|,|dy|) > 12.1 mm
//   satinSpans, strokeSpans, thinSpans, narrowestMm, minCrossMm
//               satin column widths measured off the stream (see satinColumns)
// and the engine's OWN report, read, not re-derived (design.lettering):
//   capMm, capFloorMm, thinMm (stroke length under 1.0 mm wide), hairlineMm /
//   hairlineSpans (under 0.5 mm, sewn as running stitch), shortStitches (pulls),
//   counterHeld, columns, strokeMm; plus stitchCount, trims, unsupported.
//
// A 12 mm CONTROL cell is measured beside the grid for every font, so "worse than
// usual" has something to be worse than. "Clean" has two readings (see the report
// block): engine (the engine's own say-so) and relative (engine, and no more
// short stitches than the font's own control by a stated margin).
//
// Usage:
//   node tools/small-cap-census.mjs --json out.json                  # all fonts, ~40-60 s
//   node tools/small-cap-census.mjs --from 0 --to 30 --json a.json   # font slice (chunking)
//   node tools/small-cap-census.mjs --font alchemy --text "Your Name"
//   node tools/small-cap-census.mjs --report a.json [b.json ...]     # summary tables
//   node tools/small-cap-census.mjs --report a.json --md [--top 10]  # ranked markdown table
//   node tools/small-cap-census.mjs --report a.json --csv out.csv    # every cell, one row each
//   node tools/small-cap-census.mjs --sheet sheet.png --sheet-fonts f1,f2,..   # contact sheet
//   (--caps 2.5,3,4,5,6 and --text narrow the grid; the sheet is 3 / 4 / 6 mm caps)
import "./_help.mjs";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { encodePNG } from "./png.mjs";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
global.window = global;
const DG = require("../src/digitize.js");
const fontbin = require("../src/fontbin.js");
const garments = require("../src/garments.js");
const GUARDS = require("../src/satinfont.js").LETTERING_GUARDS;
const RENDER = require("../src/render.js");

export const BIN_DIR = path.join(ROOT, "src", "fonts", "bin");
export const CAPS = [2.5, 3, 4, 5, 6];
export const CONTROL_CAP = 12; // a comfortable size: what the engine does when nothing is small
export const TEXTS = ["Hamburgefonstiv 0123"];
// full_back, not left_chest: this string is ~100-150 mm wide at a 6 mm cap and the
// engine scales text DOWN to fit the hoop, so on left_chest (101 mm) the wide fonts
// would land under the cap asked for. 304 mm clears every font; capMm is checked.
export const GARMENT = "full_back";
// The engine's own floors, read from satinfont.LETTERING_GUARDS, never restated:
//   SHORT_STITCH_AT_MM 0.3  Law 53 -- under this between penetrations the needle chews its hole
//   SATIN_MIN_CROSS_MM 0.5  a cross under this is two rails pinched; sewn as a bean run instead
//   COLUMN_FLOOR_MM    1.0  a column narrower than the needle minimum "sews as a scar"; reported, never clamped
// All three are CANDIDATE reference lines here, not settled constants (ROADMAP gate 1).
const U = (mm) => Math.round(mm * 10); // mm -> DST units (0.1 mm)
export const FLOORS = { shortMm: GUARDS.SHORT_STITCH_AT_MM, crossMm: GUARDS.SATIN_MIN_CROSS_MM, columnMm: GUARDS.COLUMN_FLOOR_MM };
const DST_MAX_UNITS = 121;  // src/dst.js MAX_DELTA: one record carries +-121 units (12.1 mm) per axis
const TRIAL_WIDTH_MM = 30; // the calibration build

export function loadFont(name) {
  return fontbin.decodeFontBin(fs.readFileSync(path.join(BIN_DIR, name + ".embf")));
}
export function fontNames() {
  return fs.readdirSync(BIN_DIR).filter((f) => f.endsWith(".embf")).map((f) => f.slice(0, -5)).sort();
}

// The Studio's text call (app/src/lib/generate.js, `// text`), minus the element
// fields a bare element does not set.
function build(font, text, targetWidthMm) {
  return DG.buildLetteringDesign(font, text, {
    garment: garments.getGarment(GARMENT), pxPerMm: 8,
    rgb: [20, 20, 20], weightPreset: "normal", targetWidthMm,
  });
}

// stitch stream -> the counts. Units are 0.1 mm.
export function streamCounts(design) {
  const u1 = U(FLOORS.columnMm) ** 2, u05 = U(FLOORS.crossMm) ** 2, u03 = U(FLOORS.shortMm) ** 2;
  let sewn = 0, sub1 = 0, sub05 = 0, sub03 = 0, repeat = 0, overRec = 0, maxMm = 0;
  let prev = null, prevWasStitch = false;
  for (const s of design.stitches || []) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && prevWasStitch) {
        // Integer DST units, so a 0.5 mm stitch (5 units) is exactly on the line
        // and not a float either side of it.
        const ux = Math.abs(s.x - prev.x), uy = Math.abs(s.y - prev.y), u2 = ux * ux + uy * uy;
        const mm = Math.sqrt(u2) / 10;
        sewn += 1;
        if (u2 < u1) sub1 += 1;
        if (u2 < u05) sub05 += 1;
        if (u2 < u03) sub03 += 1;
        if (u2 === 0) repeat += 1;
        if (Math.max(ux, uy) > DST_MAX_UNITS) overRec += 1;
        if (mm > maxMm) maxMm = mm;
      }
      prev = s; prevWasStitch = true;
    } else {
      if (s.type !== "color") prev = s;
      prevWasStitch = false;
    }
  }
  return { sewn, sub1, sub05, sub03, repeat, overRec, maxMm: +maxMm.toFixed(2) };
}

// Narrowest sewn satin column, read off the stream. The engine reports how much
// stroke LENGTH runs under each floor but never a column's width, and this tool
// changes no engine code, so it measures the crosses themselves. A satin span
// (design.runs, kind "satin") is laid cross, rail step, cross, rail step: the
// EVEN segments are the crosses, the odd ones the 0.4 mm pitch. Checked on alchemy
// "Hamburgefonstiv 0123" at 3 mm: the even segments' mean beat the odd ones' in 44
// of 45 spans (the miss is a span of near-pinched crosses, no longer than a step).
// A cross is what the needle sews, so it already carries pull compensation and the
// short-stitch pull and reads a hair under the drawn column. Hairline stretches
// never appear here: the engine sews those as a bean run (kind "run"), and counts
// them in hairlineSpans.
//
// Two widths, because the extreme alone misleads. `minCrossMm` is the shortest
// cross anywhere: it sits at 0.40-0.45 mm in nearly every font and size, because
// every column TAPERS to the engine's 0.5 mm cross floor at a serif or a tip (and
// rounding to 0.1 mm units reads a little under). It says "the floor is reached",
// not "this font is thin". `narrowestMm` is the thinnest STROKE: each span's width
// is the MEDIAN of its crosses (a taper tip does not move a median), and the
// narrowest is the smallest over spans of at least MIN_STROKE_CROSSES crosses.
// Most fonts' narrowest stroke reads 0.5 at 4 mm and under: anything thinner was
// not sewn as a satin at all. `thinSpans` / `strokeSpans` is the share of strokes
// whose median width is under COLUMN_FLOOR_MM. The engine's own length-weighted
// view (`thinMm` of `strokeMm`) is recorded beside it, untouched.
// 5 crosses is about 2 mm of stroke at the engine's 0.4 mm pitch: a measuring
// choice of this tool, not an engine or physical constant.
export const MIN_STROKE_CROSSES = 5;
export function satinColumns(design) {
  const st = design.stitches || [];
  let satinSpans = 0, strokeSpans = 0, thinSpans = 0, minCross = Infinity, narrowest = Infinity;
  for (const sp of design.runs || []) {
    if (sp.kind !== "satin") continue;
    const w = [];
    for (let i = sp.i0; i + 1 <= sp.i1; i += 2) {
      const a = st[i], b = st[i + 1];
      if (!a || !b || a.type !== "stitch" || b.type !== "stitch") continue;
      w.push(Math.hypot(a.x - b.x, a.y - b.y) / 10);
    }
    if (!w.length) continue;
    w.sort((p, q) => p - q);
    const med = w.length % 2 ? w[(w.length - 1) / 2] : (w[w.length / 2 - 1] + w[w.length / 2]) / 2;
    satinSpans += 1;
    if (w[0] < minCross) minCross = w[0];
    // A span of a few crosses is a tip, a serif end or a dot, not a stroke: it
    // counts in satinSpans and minCross, but its median is mostly taper.
    if (w.length < MIN_STROKE_CROSSES) continue;
    strokeSpans += 1;
    if (med < FLOORS.columnMm) thinSpans += 1;
    if (med < narrowest) narrowest = med;
  }
  return {
    satinSpans, strokeSpans, thinSpans,
    minCrossMm: isFinite(minCross) ? +minCross.toFixed(2) : null,
    narrowestMm: isFinite(narrowest) ? +narrowest.toFixed(2) : null,
  };
}

const r2 = (x) => (typeof x === "number" ? +x.toFixed(2) : x);

// One cell. `widthFor` is the calibration's trial/capMm pair for (font, text).
export function measureCell(font, text, capMm, cal) {
  const design = build(font, text, cal.trialWidth * capMm / cal.trialCap);
  const L = design.lettering;
  const cell = { cap: capMm, empty: !design.stitchCount || !L };
  const unsup = design.unsupported || (L && L.unsupported) || [];
  cell.unsupported = unsup.length;
  if (cell.empty) return Object.assign(cell, { engineClean: false });
  const c = streamCounts(design);
  Object.assign(cell, c, satinColumns(design), {
    stitches: design.stitchCount, trims: design._debug.nTrims,
    capMm: r2(L.capMm), capFloorMm: L.capFloorMm, underFloor: L.capMm < L.capFloorMm,
    // the cap the engine landed, against the one asked for: > 2% off means the
    // garment fit scaled the text down and the cell is not at its stated size
    capMiss: Math.abs(L.capMm - capMm) / capMm > 0.02,
    thinMm: r2(L.thinMm), hairlineMm: r2(L.hairlineMm), hairlineSpans: L.hairlineSpans,
    shortStitches: L.shortStitches, counterHeld: L.counterHeld, columns: L.columns,
    strokeMm: r2(L.strokeMm),
  });
  cell.engineClean = c.overRec === 0 && L.hairlineSpans === 0;
  return cell;
}

// -> { trialWidth, trialCap } for a (font, text), or null if nothing sews.
export function calibrate(font, text) {
  const d = build(font, text, TRIAL_WIDTH_MM);
  if (!d.stitchCount || !d.lettering || !(d.lettering.capMm > 0)) return null;
  return { trialWidth: TRIAL_WIDTH_MM, trialCap: d.lettering.capMm };
}

export function measureFont(name, caps, texts) {
  const font = loadFont(name);
  const out = { font: name, cells: [] };
  const fail = (text, cap, e) => ({ text, cap, empty: true, error: String((e && e.message) || e), engineClean: false, unsupported: 0 });
  for (const text of texts) {
    let cal = null;
    try { cal = calibrate(font, text); } catch (e) { for (const cap of caps) out.cells.push(fail(text, cap, e)); continue; }
    for (const cap of caps) {
      if (!cal) { out.cells.push({ text, cap, empty: true, engineClean: false, unsupported: 0 }); continue; }
      // An engine throw is a result, not a crash: record it in the cell and go on.
      try { out.cells.push(Object.assign({ text }, measureCell(font, text, cap, cal))); }
      catch (e) { out.cells.push(fail(text, cap, e)); }
    }
  }
  return out;
}

// ---- report -----------------------------------------------------------------
// Two readings of "clean", strictest last. A font's verdict at a cap is the AND
// over its texts. The smallest clean cap is the smallest grid cap from which the
// font STAYS clean at every larger grid cap -- clean at 3 mm and dirty at 4 is
// not "clean from 3".
//   engine    what the engine itself reports: no hairline span (a stroke under
//             SATIN_MIN_CROSS_MM wide that it sews as a bean run instead of a
//             satin), no segment over one DST record, no error, something sewn.
//   relative  engine, and the share of sewn segments under SHORT_STITCH_AT_MM is
//             no worse than the font's OWN 12 mm control by REL_SHORT_PP points.
//             Repeats (length 0) are inside that count. The margin is a CANDIDATE
//             to show the spread, not a ruling (gate 1: no sew-out, no constant).
// Not a clean criterion on purpose: columns under COLUMN_FLOOR_MM. Measured, that
// is nearly every column of nearly every font below ~6 mm, so it would fail the
// whole library and rank nothing. It is reported (thinSpans, thinMm) instead.
export const REL_SHORT_PP = 2;
export const MODES = {
  engine: (c) => !!c.engineClean,
  relative: (c, ctl) => !!c.engineClean && !!ctl && !ctl.empty &&
    100 * c.sub03 / c.sewn <= 100 * ctl.sub03 / ctl.sewn + REL_SHORT_PP,
};
// A font that sews nothing at any cell has no sample here (the Hebrew faces:
// no Latin glyphs). It is listed, not counted as a failure of size.
export const hasSample = (r) => !r.error && r.cells.some((c) => !c.empty);
export const gridCaps = (rows) => [...new Set(rows.flatMap((r) => r.cells.map((c) => c.cap)))]
  .filter((c) => c !== CONTROL_CAP).sort((a, b) => a - b);

export function verdicts(rows, mode) {
  const caps = gridCaps(rows);
  return rows.filter(hasSample).map((r) => {
    const at = {};
    for (const cap of caps) {
      const cs = r.cells.filter((c) => c.cap === cap);
      at[cap] = cs.length > 0 && cs.every((c) => MODES[mode](c, r.cells.find((x) => x.cap === CONTROL_CAP && x.text === c.text)));
    }
    let smallest = null;
    for (let i = caps.length - 1; i >= 0 && at[caps[i]]; i--) smallest = caps[i];
    return { font: r.font, at, smallest };
  });
}

const sumOf = (r, cap, k) => r.cells.filter((c) => c.cap === cap && !c.empty).reduce((a, c) => a + (c[k] || 0), 0);
const shareOf = (r, cap, k) => { const s = sumOf(r, cap, "sewn"); return s ? 100 * sumOf(r, cap, k) / s : 0; };
const pct = (x) => `${x.toFixed(1)}%`;

// Fonts best-first: smallest relative-clean cap, then smallest engine-clean cap,
// then fewest hairline spans at 4 mm, then least short-stitch share at 4 mm.
// "none" (never clean up to the largest grid cap) sorts after every number.
export function ranked(rows) {
  const rel = Object.fromEntries(verdicts(rows, "relative").map((x) => [x.font, x.smallest]));
  const eng = Object.fromEntries(verdicts(rows, "engine").map((x) => [x.font, x.smallest]));
  const k = (v) => (v == null ? Infinity : v);
  return rows.filter(hasSample).map((r) => ({
    font: r.font, relative: rel[r.font], engine: eng[r.font],
    hair4: sumOf(r, 4, "hairlineSpans"), short4: shareOf(r, 4, "sub03"),
  })).sort((a, b) => k(a.relative) - k(b.relative) || k(a.engine) - k(b.engine) || a.hair4 - b.hair4 || a.short4 - b.short4 || (a.font < b.font ? -1 : 1));
}

export function report(rows) {
  const caps = gridCaps(rows);
  const lines = [];
  const none = rows.filter((r) => !r.error && !hasSample(r)).map((r) => r.font);
  const live = rows.filter(hasSample);
  lines.push(`${rows.length} fonts, ${live.length} with a sample` + (none.length ? ` (no sample, nothing sews: ${none.join(", ")})` : ""));
  lines.push(`floors read from satinfont.LETTERING_GUARDS: short stitch ${FLOORS.shortMm} mm (SHORT_STITCH_AT_MM), cross ${FLOORS.crossMm} mm (SATIN_MIN_CROSS_MM), column ${FLOORS.columnMm} mm (COLUMN_FLOOR_MM)`);
  for (const mode of Object.keys(MODES)) {
    const v = verdicts(rows, mode);
    lines.push(`\n${mode}: fonts clean at each cap`);
    for (const cap of caps) lines.push(`  ${String(cap).padEnd(4)} mm  ${v.filter((x) => x.at[cap]).length} of ${v.length}`);
    const dist = new Map();
    for (const x of v) dist.set(x.smallest, (dist.get(x.smallest) || 0) + 1);
    lines.push("  smallest clean cap (stays clean above it): " +
      [...caps, null].filter((c) => dist.has(c)).map((c) => `${c === null ? "none up to " + caps[caps.length - 1] : c + " mm"}: ${dist.get(c)}`).join(", "));
  }
  lines.push("\nper cap, all fonts (12 = control):");
  lines.push("cap   cells  empty  stitches    sewn   short<floor (share)   sub05 (share)   repeat   overRec  hairlineSpans  cells w/ hairline  thin spans (share)   under-floor cells  capMiss");
  for (const cap of [...caps, CONTROL_CAP]) {
    const cs = rows.flatMap((r) => r.cells.filter((c) => c.cap === cap));
    const lv = cs.filter((c) => !c.empty);
    const sum = (k) => lv.reduce((a, c) => a + (c[k] || 0), 0);
    const pc = (k) => `(${pct(100 * sum(k) / (sum("sewn") || 1))})`;
    lines.push(`${String(cap).padEnd(5)} ${String(cs.length).padStart(5)} ${String(cs.length - lv.length).padStart(6)} ${String(sum("stitches")).padStart(9)} ${String(sum("sewn")).padStart(7)} ${String(sum("sub03")).padStart(9)} ${pc("sub03").padEnd(10)} ${String(sum("sub05")).padStart(8)} ${pc("sub05").padEnd(9)} ${String(sum("repeat")).padStart(6)} ${String(sum("overRec")).padStart(8)} ${String(sum("hairlineSpans")).padStart(14)} ${String(lv.filter((c) => c.hairlineSpans > 0).length).padStart(18)} ${String(sum("thinSpans")).padStart(10)} (${pct(100 * sum("thinSpans") / (sum("strokeSpans") || 1))}) ${String(lv.filter((c) => c.underFloor).length).padStart(14)} ${String(lv.filter((c) => c.capMiss).length).padStart(8)}`);
  }
  const top = (label, f, n = 8) => {
    const s = live.map((r) => [r.font, f(r)]).sort((a, b) => b[1] - a[1]).slice(0, n);
    lines.push(`\n${label}:\n  ` + s.map(([n2, x]) => `${n2} ${typeof x === "number" ? +x.toFixed(1) : x}`).join("\n  "));
  };
  top("worst offenders: hairline spans at 6 mm", (r) => sumOf(r, 6, "hairlineSpans"));
  top("worst offenders: share of segments under the short-stitch floor at 6 mm (%)", (r) => shareOf(r, 6, "sub03"));
  top("worst offenders: same-hole repeats at 6 mm", (r) => sumOf(r, 6, "repeat"));
  const errs = rows.flatMap((r) => r.error ? [`${r.font}: ${r.error}`] : r.cells.filter((c) => c.error).map((c) => `${r.font} @ ${c.cap} mm: ${c.error}`));
  const unsup = rows.filter((r) => r.cells.some((c) => c.unsupported)).map((r) => r.font);
  lines.push(`\nerrors: ${errs.length}` + errs.map((e) => "\n  " + e).join(""));
  lines.push(`fonts that drop characters of the test string: ${unsup.length}` + (unsup.length ? ` (${unsup.join(", ")})` : ""));
  return lines.join("\n");
}

// Markdown: ranked table. `n` rows from the top and the bottom, or all with n = 0.
export function markdown(rows, n = 0) {
  const rk = ranked(rows);
  const byFont = Object.fromEntries(rows.map((r) => [r.font, r]));
  const f = (x) => (x == null ? "none" : String(x));
  const head = ["| # | font | clean from, relative (mm) | clean from, engine (mm) | stitches @4 mm | short < floor @4 mm (12 mm control) | hairline spans @3 / 4 / 5 / 6 mm | thin spans @4 mm | narrowest column @4 mm (mm) | note |",
    "|---|---|---|---|---|---|---|---|---|---|"];
  const line = (x, i) => {
    const r = byFont[x.font];
    const at4 = r.cells.filter((c) => c.cap === 4 && !c.empty);
    const notes = [];
    if (r.cells.some((c) => c.unsupported)) notes.push("drops characters");
    if (r.cells.some((c) => c.capMiss)) notes.push("cap not reached");
    const nar = at4.map((c) => c.narrowestMm).filter((v) => v != null);
    return `| ${i + 1} | ${x.font} | ${f(x.relative)} | ${f(x.engine)} | ${sumOf(r, 4, "stitches")} | ${pct(shareOf(r, 4, "sub03"))} (${pct(shareOf(r, CONTROL_CAP, "sub03"))}) | ${[3, 4, 5, 6].map((c) => sumOf(r, c, "hairlineSpans")).join(" / ")} | ${sumOf(r, 4, "thinSpans")} of ${sumOf(r, 4, "strokeSpans")} | ${nar.length ? Math.min(...nar) : "no satin"} | ${notes.join("; ")} |`;
  };
  if (!n || rk.length <= 2 * n) return [...head, ...rk.map(line)].join("\n");
  const sep = `| | ... ${rk.length - 2 * n} fonts between ... | | | | | | | | |`;
  return [...head, ...rk.slice(0, n).map(line), sep, ...rk.slice(-n).map((x, j) => line(x, rk.length - n + j))].join("\n");
}

const CSV_COLS = ["font", "text", "cap", "capMm", "capMiss", "stitches", "sewn", "sub03", "shortShare", "sub05", "repeat", "overRec", "maxMm",
  "hairlineSpans", "hairlineMm", "thinMm", "strokeMm", "columns", "satinSpans", "strokeSpans", "thinSpans", "narrowestMm", "minCrossMm",
  "shortStitches", "trims", "unsupported", "engineClean", "error"];
export function csv(rows) {
  const q = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const out = [CSV_COLS.join(",")];
  for (const r of rows) {
    if (r.error) { out.push(q(r.font) + "," + CSV_COLS.slice(1, -1).map(() => "").join(",") + "," + q(r.error)); continue; }
    for (const c of r.cells) {
      const v = Object.assign({ font: r.font }, c, { shortShare: c.sewn ? +(100 * c.sub03 / c.sewn).toFixed(2) : "" });
      out.push(CSV_COLS.map((k) => q(v[k])).join(","));
    }
  }
  return out.join("\n") + "\n";
}

// ---- contact sheet ----------------------------------------------------------
// renderStitches draws with a 2D canvas context. This one rasterizes into an
// RGBA buffer: a round-capped segment at its laid width, anti-aliased by
// distance, source-over. It implements only what render.js calls.
function fakeCanvas(w, h, bg) {
  const buf = new Float32Array(w * h * 4);
  for (let i = 0; i < w * h; i++) { buf[i * 4] = bg[0]; buf[i * 4 + 1] = bg[1]; buf[i * 4 + 2] = bg[2]; buf[i * 4 + 3] = 255; }
  const parse = (s) => {
    const m = /rgba?\(([^)]+)\)/.exec(s) || [];
    const p = (m[1] || "0,0,0").split(",").map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  let path = [], state = { strokeStyle: "rgb(0,0,0)", lineWidth: 1 };
  const stack = [];
  const ctx = {
    save() { stack.push({ ...state }); }, restore() { state = stack.pop() || state; },
    clearRect() {}, setLineDash() {}, strokeRect() {},
    beginPath() { path = []; },
    moveTo(x, y) { path.push([x, y, x, y]); },
    lineTo(x, y) { const p = path[path.length - 1]; path.push([p[2], p[3], x, y]); },
    stroke() {
      const [r, g, b, a] = parse(state.strokeStyle), hw = state.lineWidth / 2;
      for (const [x0, y0, x1, y1] of path) {
        if (x0 === x1 && y0 === y1 && path.length > 1) continue;
        const dx = x1 - x0, dy = y1 - y0, L2 = dx * dx + dy * dy || 1;
        const xa = Math.max(0, Math.floor(Math.min(x0, x1) - hw - 1)), xb = Math.min(w - 1, Math.ceil(Math.max(x0, x1) + hw + 1));
        const ya = Math.max(0, Math.floor(Math.min(y0, y1) - hw - 1)), yb = Math.min(h - 1, Math.ceil(Math.max(y0, y1) + hw + 1));
        for (let y = ya; y <= yb; y++) for (let x = xa; x <= xb; x++) {
          const t = Math.max(0, Math.min(1, ((x + 0.5 - x0) * dx + (y + 0.5 - y0) * dy) / L2));
          const d = Math.hypot(x + 0.5 - (x0 + t * dx), y + 0.5 - (y0 + t * dy));
          const cov = Math.max(0, Math.min(1, hw - d + 0.5)) * a;
          if (cov <= 0) continue;
          const o = (y * w + x) * 4;
          buf[o] += (r - buf[o]) * cov; buf[o + 1] += (g - buf[o + 1]) * cov; buf[o + 2] += (b - buf[o + 2]) * cov;
        }
      }
    },
  };
  Object.defineProperty(ctx, "strokeStyle", { get: () => state.strokeStyle, set: (v) => { state.strokeStyle = v; } });
  Object.defineProperty(ctx, "lineWidth", { get: () => state.lineWidth, set: (v) => { state.lineWidth = v; } });
  ctx.lineCap = "round";
  return { width: w, height: h, getContext: () => ctx, buf };
}

// Draw one design at `pxPerMm` (the thread is 0.4 mm wide in render.js, so this is
// the laid size) -> { w, h, buf } with a 1-mm margin.
function drawDesign(design, pxPerMm, bg) {
  const st = design.stitches.filter((s) => s.type === "stitch");
  const xs = st.map((s) => s.x), ys = st.map((s) => s.y);
  const spanX = Math.max(1, Math.max(...xs) - Math.min(...xs)), spanY = Math.max(1, Math.max(...ys) - Math.min(...ys));
  const pad = Math.round(pxPerMm);
  // buildMapper scales by min(availW/spanX, availH/spanY) in px per DST unit.
  const w = Math.ceil(spanX / 10 * pxPerMm) + 2 * pad, h = Math.ceil(spanY / 10 * pxPerMm) + 2 * pad;
  const cv = fakeCanvas(w, h, bg);
  RENDER.renderStitches(cv, design, { padding: pad });
  return cv;
}

export function contactSheet(fonts, caps, text, pxPerMm) {
  const bg = [244, 238, 224], cellGap = 14;
  const rows = fonts.map((name) => {
    const font = loadFont(name);
    const cal = calibrate(font, text);
    return caps.map((cap) => drawDesign(build(font, text, cal.trialWidth * cap / cal.trialCap), pxPerMm, bg));
  });
  const rowH = rows.map((r) => Math.max(...r.map((c) => c.height)));
  const colW = caps.map((_, i) => Math.max(...rows.map((r) => r[i].width)));
  const W = colW.reduce((a, b) => a + b, 0) + cellGap * (caps.length + 1);
  const H = rowH.reduce((a, b) => a + b, 0) + cellGap * (rows.length + 1);
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) { out[i * 4] = bg[0] - 14; out[i * 4 + 1] = bg[1] - 14; out[i * 4 + 2] = bg[2] - 14; out[i * 4 + 3] = 255; }
  let y0 = cellGap;
  rows.forEach((r, ri) => {
    let x0 = cellGap;
    r.forEach((c, ci) => {
      const ox = x0, oy = y0 + Math.floor((rowH[ri] - c.height) / 2);
      for (let y = 0; y < c.height; y++) for (let x = 0; x < c.width; x++) {
        const s = (y * c.width + x) * 4, d = ((oy + y) * W + ox + x) * 4;
        out[d] = c.buf[s]; out[d + 1] = c.buf[s + 1]; out[d + 2] = c.buf[s + 2];
      }
      x0 += colW[ci] + cellGap;
    });
    y0 += rowH[ri] + cellGap;
  });
  return { W, H, png: encodePNG(W, H, out) };
}

// ---- CLI --------------------------------------------------------------------
const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 ? argv[i + 1] : d; };
  const caps = flag("caps", null) ? flag("caps").split(",").map(Number) : [...CAPS, CONTROL_CAP];
  const texts = flag("text", null) ? [flag("text")] : TEXTS;

  if (argv.includes("--report")) {
    const rest = argv.slice(argv.indexOf("--report") + 1);
    const files = rest.slice(0, rest.findIndex((a) => a.startsWith("--")) < 0 ? rest.length : rest.findIndex((a) => a.startsWith("--")));
    const rows = files.flatMap((f) => JSON.parse(fs.readFileSync(f, "utf8")));
    if (flag("csv", null)) { fs.writeFileSync(flag("csv"), csv(rows)); console.log(`${flag("csv")}: ${rows.reduce((a, r) => a + r.cells.length, 0)} cells`); }
    else if (argv.includes("--md")) console.log(markdown(rows, +flag("top", 0)));
    else console.log(`${rows.reduce((a, r) => a + r.cells.length, 0)} cells\n` + report(rows));
  } else if (flag("sheet", null)) {
    const fonts = (flag("sheet-fonts", "") || "").split(",").filter(Boolean);
    const { W, H, png } = contactSheet(fonts, [3, 4, 6], flag("text", TEXTS[0]), +flag("px-per-mm", 12));
    fs.writeFileSync(flag("sheet"), png);
    console.log(`${flag("sheet")}: ${W}x${H} px, ${png.length} bytes; rows ${fonts.join(", ")}; columns 3 / 4 / 6 mm caps`);
  } else {
    let names = fontNames();
    if (flag("font", null)) names = [flag("font")];
    else names = names.slice(+flag("from", 0), +flag("to", names.length));
    const rows = [];
    const t0 = Date.now();
    for (const n of names) {
      try { rows.push(measureFont(n, caps, texts)); }
      catch (e) { rows.push({ font: n, error: String(e.message || e), cells: [] }); }
    }
    if (flag("json", null)) fs.writeFileSync(flag("json"), JSON.stringify(rows));
    console.log(`${names.length} fonts in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
    console.log(report(rows));
  }
}
