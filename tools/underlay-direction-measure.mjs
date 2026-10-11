// The needle-up move between a satin bar's underlay and its column, in mm,
// with and without `underlayDirection` (defect 57, 2026-10-11).
//
//   node tools/underlay-direction-measure.mjs
//
// For each bar: the move from the underlay's last stitch to the column's
// first (both read off the emitted stream, 0.1 mm units), and the stitch
// count, flag off and on, on a centre-run garment (left chest, pique) and a
// zigzag one (full back, fleece). And a row of five bars, for the needle-up
// travel of the whole design (a turned column leaves its shape from the
// other end, so the move to the next shape changes too).
//
// test/satin-underlay-direction.test.js imports SHAPES, build and gapMm.
import "./_help.mjs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const engine = require(path.join(ROOT, "src", "digitize.js"));
const garments = require(path.join(ROOT, "src", "garments.js"));
const fabrics = require(path.join(ROOT, "src", "fabrics.js"));
const lib = (n) => import(pathToFileURL(path.join(ROOT, "app", "src", "lib", n)).href);
const { shapePresetPoints } = await lib("shapePresets.js");
const { shapesToRegions } = await lib("manualShapes.js");

export function rotate(pts, deg) {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  const cx = pts.reduce((t, p) => t + p.x, 0) / pts.length, cy = pts.reduce((t, p) => t + p.y, 0) / pts.length;
  return pts.map((p) => ({ x: cx + (p.x - cx) * c - (p.y - cy) * s, y: cy + (p.x - cx) * s + (p.y - cy) * c }));
}
export function build(points, garmentId, flag) {
  const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points, curves: {}, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null }]);
  const xs = points.map((p) => p.x);
  return engine.buildQualityDesign(regions, {
    garment: garments.getGarment(garmentId), fabric: fabrics.getFabric(fabrics.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / pxPerMm, offsetXMm: 0, offsetYMm: 0,
    underlayDirection: flag,
  });
}
// mm from the underlay's last stitch to the column's first record (a jump)
export function gapMm(d) {
  const ul = d.runs.filter((s) => s.kind === "underlay").pop(), sat = d.runs.find((s) => s.kind === "satin");
  if (!ul || !sat) return NaN;
  const a = d.stitches[ul.i1], b = d.stitches[sat.i0];
  return Math.hypot(a.x - b.x, a.y - b.y) / 10;
}
export const SHAPES = {
  "bar 30 x 3 mm": shapePresetPoints("rect", { heightMm: 3, cornerRadiusMm: 0 }, 30),
  "round-ended bar 30 x 3 mm": shapePresetPoints("rect", { heightMm: 3, cornerRadiusMm: 1.5 }, 30),
  "bar 50 x 4 mm at 35 deg": rotate(shapePresetPoints("rect", { heightMm: 4, cornerRadiusMm: 0 }, 50), 35),
  "bar 20 x 2.5 mm upright": rotate(shapePresetPoints("rect", { heightMm: 2.5, cornerRadiusMm: 0 }, 20), 90),
};

// Every needle-up move of a design (jump records, and the move a trim
// precedes), summed in mm: what the flag does to travel BETWEEN shapes, which
// it also moves, since a turned column leaves its shape from the other end.
export function needleUpMm(d) {
  let mm = 0;
  for (let i = 1; i < d.stitches.length; i++) {
    const s = d.stitches[i], p = d.stitches[i - 1];
    if (s.type === "jump") mm += Math.hypot(s.x - p.x, s.y - p.y) / 10;
  }
  return mm;
}
// Five upright bars side by side, one shape each: a row of strokes.
export function rowOfBars(n = 5) {
  return Array.from({ length: n }, (_, k) => rotate(shapePresetPoints("rect", { heightMm: 3, cornerRadiusMm: 0 }, 25), 90).map((p) => ({ x: p.x + k * 8 * 10, y: p.y })));
}
export function buildMany(shapes, garmentId, flag) {
  const { regions, pxPerMm } = shapesToRegions(shapes.map((points, k) => ({ id: "s" + k, points, curves: {}, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null })));
  const xs = shapes.flat().map((p) => p.x);
  return engine.buildQualityDesign(regions, {
    garment: garments.getGarment(garmentId), fabric: fabrics.getFabric(fabrics.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / pxPerMm, offsetXMm: 0, offsetYMm: 0,
    underlayDirection: flag,
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  for (const g of ["left_chest", "full_back"]) {
    const off = buildMany(rowOfBars(), g, false), on = buildMany(rowOfBars(), g, true);
    console.log(`${g.padEnd(10)} five bars in a row           all needle-up off ${needleUpMm(off).toFixed(1)} mm  on ${needleUpMm(on).toFixed(1)} mm  trims ${off._debug.nTrims} -> ${on._debug.nTrims}  stitches ${off.stitchCount} -> ${on.stitchCount}`);
  }
  for (const g of ["left_chest", "full_back"]) {
    for (const [name, pts] of Object.entries(SHAPES)) {
      const off = build(pts, g, false), on = build(pts, g, true);
      console.log(`${g.padEnd(10)} ${name.padEnd(26)} needle-up off ${gapMm(off).toFixed(2).padStart(6)} mm  on ${gapMm(on).toFixed(2).padStart(6)} mm  stitches ${off.stitchCount} -> ${on.stitchCount}`);
    }
  }
}
