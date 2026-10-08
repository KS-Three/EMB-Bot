// Times the JS stitch engine (fill, satin, digitize) on the engine fixtures and
// on one large design, and prints a table.
//
//   node tools/bench-engine.mjs [--runs N] [--json]
//
// Report-only: nothing here gates CI. Each case runs one warm-up call, then N
// timed runs (default 7); the table shows median and min in ms plus a stitch
// count so a speed-up that changes the output shows up as a changed count.
// `--json` prints the rows as JSON instead. To find the hot function:
//   node --cpu-prof --cpu-prof-dir=/tmp/prof tools/bench-engine.mjs
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const fill = require(path.join(root, "src/fill.js"));
const satin = require(path.join(root, "src/satin.js"));
const DG = require(path.join(root, "src/digitize.js"));
const geneva = require(path.join(root, "test/fixtures/fonts/geneva_simple.json"));
const emilio = require(path.join(root, "test/fixtures/fonts/emilio_20_bold.json"));

const args = process.argv.slice(2);
const runsAt = args.indexOf("--runs");
const RUNS = runsAt >= 0 ? Math.max(1, Number(args[runsAt + 1]) || 7) : 7;
const AS_JSON = args.includes("--json");

const rect = (x, y, w, h) => [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
const star = (cx, cy, r0, r1, n) =>
  Array.from({ length: n * 2 }, (_, i) => {
    const a = (Math.PI * i) / n, r = i % 2 ? r0 : r1;
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
  });
const circle = (cx, cy, r, n = 96) =>
  Array.from({ length: n }, (_, i) => ({ x: cx + r * Math.cos((2 * Math.PI * i) / n), y: cy + r * Math.sin((2 * Math.PI * i) / n) }));

// A large design: a grid of 5x4 colour layers' worth of shapes, each a star
// with a circular counter, spread over a 5x2.25 in hoop at 8 px/mm.
function largeLayers() {
  const layers = [];
  for (let c = 0; c < 4; c++) {
    const shapes = [];
    for (let i = 0; i < 5; i++) {
      const cx = 120 + i * 220, cy = 150 + c * 200;
      shapes.push({ outer: star(cx, cy, 60 + c * 3, 130, 7 + i), holes: [circle(cx, cy, 30)] });
    }
    layers.push({ rgb: [30 + c * 50, 60, 200 - c * 40], shapes });
  }
  return layers;
}
const bigOpts = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, densityMm: 0.4, underlay: true, satinMaxWidthMm: 3 };

const count = (r) => (Array.isArray(r) ? r.length : r && r.stitchCount != null ? r.stitchCount : 0);
const bar = rect(0, 0, 200, 24);
const ring = circle(0, 0, 60), counter = circle(0, 0, 40);

const CASES = [
  ["fill", "tatami rect 300x200", () => fill.tatamiFill([rect(0, 0, 300, 200)], { rowSpacing: 1.5, angleDeg: 0, maxStitch: 40 })],
  ["fill", "tatami star+hole", () => fill.tatamiFill([star(0, 0, 150, 400, 9), circle(0, 0, 60)], { rowSpacing: 1.5, angleDeg: 20, maxStitch: 40, markConnectors: true })],
  ["fill", "tatami 1200x800 (large)", () => fill.tatamiFill([rect(0, 0, 1200, 800), circle(600, 400, 150)], { rowSpacing: 1.5, angleDeg: 35, maxStitch: 40 })],
  ["fill", "running outline ring", () => fill.runningOutline(ring, { stitchLen: 3 })],
  ["satin", "column bar", () => satin.satinColumn(bar, { spacingMm: 0.4, pxPerMm: 8 })],
  ["satin", "medial annulus", () => satin.medialSatin(ring, { spacingMm: 0.4, pxPerMm: 8, holes: [counter] })],
  ["digitize", "quality: 1 shape+hole", () => DG.buildQualityDesign([{ rgb: [10, 10, 10], shapes: [{ outer: rect(0, 0, 100, 100), holes: [rect(20, 20, 60, 60)] }] }], { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 })],
  ["digitize", "lettering geneva 'AB'", () => DG.buildLetteringDesign(geneva, "AB", { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 })],
  ["digitize", "lettering emilio 'Fritsch'", () => DG.buildLetteringDesign(emilio, "Fritsch", { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 100 })],
  ["digitize", "quality: large 20 shapes", () => DG.buildQualityDesign(largeLayers(), bigOpts)],
];

const rows = [];
for (const [area, name, fn] of CASES) {
  let result = fn(); // warm-up, also the output size
  const ms = [];
  for (let i = 0; i < RUNS; i++) {
    const t0 = process.hrtime.bigint();
    result = fn();
    ms.push(Number(process.hrtime.bigint() - t0) / 1e6);
  }
  ms.sort((a, b) => a - b);
  rows.push({ area, name, medianMs: ms[ms.length >> 1], minMs: ms[0], out: count(result) });
}

if (AS_JSON) console.log(JSON.stringify(rows, null, 2));
else {
  const w = Math.max(...rows.map((r) => r.name.length));
  console.log(`engine bench, ${RUNS} runs after 1 warm-up (node ${process.version})`);
  console.log(`${"area".padEnd(9)}${"case".padEnd(w + 2)}${"median ms".padStart(10)}${"min ms".padStart(10)}${"output".padStart(10)}`);
  for (const r of rows)
    console.log(`${r.area.padEnd(9)}${r.name.padEnd(w + 2)}${r.medianMs.toFixed(1).padStart(10)}${r.minMs.toFixed(1).padStart(10)}${String(r.out).padStart(10)}`);
}
