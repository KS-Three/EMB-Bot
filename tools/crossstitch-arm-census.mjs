// Cross-stitch arm census (2026-10-13). MEASURE ONLY: changes no rendering.
//
// After the splitSatin flip the fonts that still sew a stitch past one DST record
// are all cross-stitch fonts. src/crossfill.js draws its lattice in GLYPH UNITS,
// so an X arm grows with the letter. This sweeps those fonts across Studio cap
// heights and reports the longest sewn segment per (font, cap), against the
// limits the census already uses:
//   record  12.1 mm PER AXIS (src/dst.js MAX_DELTA 121 @ 10 units/mm), the
//           machine max the encoders enforce
//   split   5.0 mm LENGTH (satinfont SPLIT_SATIN_ABOVE_MM), the satin split
//           threshold; reported so fix A has its own line, not a machine limit
// An X arm is a 45-degree sewn segment (|dx| = |dy| within DST rounding). Its
// length scales linearly with cap height (the lattice is in glyph units), so the
// threshold cap is solved from the measured arm-per-cap ratio and the sweep rows
// are the check: `linearity` is the spread of that ratio across the sizes. The
// longest segment of ANY kind is reported too (it is what long-stitch-census
// counts), but it is not the arm: at small caps it is a cell-to-satin carry.
//
// Usage:
//   node tools/crossstitch-arm-census.mjs                  # the 9 fonts, caps 10/15/25/40/60
//   node tools/crossstitch-arm-census.mjs --caps 10,20 --fonts jersey_15,noble
//   node tools/crossstitch-arm-census.mjs --hoop           # long-stitch-census's own rows, with their cap
//   node tools/crossstitch-arm-census.mjs --detect         # re-derive the font list
//   node tools/crossstitch-arm-census.mjs --json out.json
import "./_help.mjs";
import { createRequire } from "module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadFont, fontNames, calibrate } from "./small-cap-census.mjs";

const require = createRequire(import.meta.url);
global.window = global;
const DG = require("../src/digitize.js");
const garments = require("../src/garments.js");

export const DST_MM = 12.1;     // src/dst.js MAX_DELTA 121 @ 10 units/mm, per axis
export const SPLIT_MM = 5.0;    // satinfont SPLIT_SATIN_ABOVE_MM, by length
export const CAPS = [10, 15, 25, 40, 60];
export const TEXT = "AB";
// The nine fonts `node tools/long-stitch-census.mjs --big --arm split` leaves over
// one record (2026-10-13); --detect re-derives them.
export const FONTS = ["egyptian", "egyptian_small", "eloquent", "eloquent_small", "heavenly",
  "heavenly_small", "jaquarda_bastarda_9", "jersey_15", "noble"];
const DIAG_TOL_MM = 0.15;       // |dx|-|dy| a 45-degree arm may show after 0.1 mm DST rounding
export const RATIO_MIN_CAP = 25;
const GARMENT = "full_back";    // 304 mm: the 60 mm cap clears it without the fit scaling it down

function build(font, targetWidthMm) {
  return DG.buildLetteringDesign(font, TEXT, {
    garment: garments.getGarment(GARMENT), pxPerMm: 8, rgb: [20, 20, 20],
    weightPreset: "normal", targetWidthMm,
  });
}

// Longest sewn segment of a stream, by the census's chain rule (a jump, trim or
// colour cuts it). Units are 0.1 mm.
export function longest(design) {
  let sewn = 0, maxAx = 0, maxMm = 0, over12 = 0, over5 = 0, prev = null, was = false;
  let armMm = 0, armAx = 0, arms = 0;
  for (const s of design.stitches || []) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && was) {
        const dx = Math.abs(s.x - prev.x) / 10, dy = Math.abs(s.y - prev.y) / 10;
        const ax = Math.max(dx, dy), mm = Math.hypot(dx, dy);
        sewn++;
        if (Math.abs(dx - dy) <= DIAG_TOL_MM && Math.min(dx, dy) > 0.3) {
          arms++;
          if (mm > armMm) { armMm = mm; armAx = ax; }
        }
        if (ax > DST_MM) over12++;
        if (mm > SPLIT_MM) over5++;
        if (ax > maxAx) maxAx = ax;
        if (mm > maxMm) maxMm = mm;
      }
      prev = s; was = true;
    } else {
      if (s.type !== "color") prev = s;
      was = false;
    }
  }
  return { sewn, over12, over5, maxAx, maxMm, arms, armMm, armAx };
}

export function measureFont(name, caps) {
  const font = loadFont(name);
  const cal = calibrate(font, TEXT);
  if (!cal) return { font: name, error: "nothing sews", cells: [] };
  const cells = caps.map((cap) => {
    const d = build(font, cal.trialWidth * cap / cal.trialCap);
    const capMm = d.lettering.capMm;
    return Object.assign({ cap, capMm, capMiss: Math.abs(capMm - cap) / cap > 0.02,
      stitches: d.stitchCount }, longest(d));
  });
  // mm of worst arm per mm of cap: constant if the lattice scales with the glyph
  // Under RATIO_MIN_CAP a 0.1 mm DST rounding is >5% of a 1-2 mm arm, so the
  // ratio is taken from the sizes where an arm is long enough to measure.
  const fit = cells.filter((c) => c.cap >= RATIO_MIN_CAP);
  const use = fit.length ? fit : cells;
  const axRatio = use.map((c) => c.armAx / c.capMm), lenRatio = use.map((c) => c.armMm / c.capMm);
  const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
  const spread = (a) => (Math.max(...a) - Math.min(...a)) / mean(a);
  const ax = mean(axRatio), len = mean(lenRatio);
  return {
    font: name, cells, linearity: Math.max(spread(axRatio), spread(lenRatio)),
    // cap height (mm) at which the worst arm first passes each limit: the record
    // (per axis, what the encoders enforce), 12.1 mm read as a LENGTH, and 5.0
    armPerCap: len, axisPerCap: ax,
    startsOver12Mm: DST_MM / ax, startsOver12LenMm: DST_MM / len, startsOver5Mm: SPLIT_MM / len,
  };
}

function detect() {
  const out = [];
  for (const name of fontNames()) {
    const f = loadFont(name);
    if (!f.crossGrid) continue;
    const cal = calibrate(f, TEXT);
    if (!cal) continue;
    // the hoop-filling configuration of long-stitch-census, where the defect shows
    if (hoopRow(name, "AB", "full_back").over12 > 0 || hoopRow(name, "A", "left_chest").over12 > 0) out.push(name);
  }
  return out;
}

const f1 = (x) => x.toFixed(1);
export function markdown(rows, caps) {
  const L = [];
  L.push(`| font | ${caps.map((c) => `${c} mm`).join(" | ")} | arm / cap | over 5.0 mm from cap | over 12.1 mm (length) from cap | over a record (12.1 mm/axis) from cap |`);
  L.push(`|---|${caps.map(() => "---:").join("|")}|---:|---:|---:|---:|`);
  for (const r of rows) {
    L.push(`| ${r.font} | ${r.cells.map((c) => `${f1(c.armMm)} (${f1(c.armAx)})`).join(" | ")} | ${r.armPerCap.toFixed(3)} | ${f1(r.startsOver5Mm)} mm | ${f1(r.startsOver12LenMm)} mm | ${f1(r.startsOver12Mm)} mm |`);
  }
  return L.join("\n");
}

// The long-stitch-census configuration (emMm 18, splitSatin on): on a hoop-sized
// garment the engine fills the hoop, so "AB" on full_back is a ~250 mm cap. This
// is the row that reproduces that tool's 31.0 mm, with the cap it was sewn at.
export function hoopRow(name, text, garmentId) {
  const d = DG.buildLetteringDesign(loadFont(name), text, {
    garment: garments.getGarment(garmentId), pxPerMm: 8, emMm: 18,
    rgb: [25, 25, 25], pullCompMm: 0.2, splitSatin: true,
  });
  return Object.assign({ font: name, text, garment: garmentId, capMm: d.lettering.capMm }, longest(d));
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 ? argv[i + 1] : d; };
  if (argv.includes("--hoop")) {
    console.log("font                  text  garment       cap mm  longest mm  arm mm  worst axis");
    for (const n of flag("fonts", null) ? flag("fonts").split(",") : FONTS) {
      for (const [t, g] of [["AB", "full_back"], ["A", "left_chest"]]) {
        const r = hoopRow(n, t, g);
        console.log(`${n.padEnd(21)} ${t.padEnd(5)} ${g.padEnd(13)} ${f1(r.capMm).padStart(6)} ${f1(r.maxMm).padStart(11)} ${f1(r.armMm).padStart(7)} ${f1(r.maxAx).padStart(11)}`);
      }
    }
  } else if (argv.includes("--detect")) {
    const d = detect();
    console.log(d.length + " cross-stitch fonts past one record at the hoop-filling size: " + d.join(", "));
  } else {
    const caps = flag("caps", null) ? flag("caps").split(",").map(Number) : CAPS;
    const fonts = flag("fonts", null) ? flag("fonts").split(",") : FONTS;
    const rows = fonts.map((n) => measureFont(n, caps));
    if (flag("json", null)) fs.writeFileSync(flag("json"), JSON.stringify(rows, null, 1));
    console.log(`cells are "worst X arm mm (its axis delta mm)"; text ${TEXT}, ${GARMENT}`);
    console.log(markdown(rows, caps));
    const miss = rows.flatMap((r) => r.cells.filter((c) => c.capMiss).map((c) => `${r.font}@${c.cap}`));
    console.log(`\nmax arm/cap spread over caps >= ${RATIO_MIN_CAP} mm ${(100 * Math.max(...rows.map((r) => r.linearity))).toFixed(2)}%; cap misses: ${miss.length ? miss.join(", ") : "none"}`);
  }
}
