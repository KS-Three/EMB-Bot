// One satin bar written to .dst with `underlayDirection` off and on, each file
// decoded record by record and drawn: the needle-up move between the underlay
// and the column made visible (defect 57, 2026-10-11).
//
//   node tools/underlay-direction-sheet.mjs [outDir]
//
// Writes off.dst, on.dst and bar.png (off on top, on below) to outDir
// (default docs/renders/underlay-direction-2026-10-11/), and prints each
// file's jump records. The bar is the shape tool's 30 x 3 mm rectangle on left
// chest (pique: centre-run underlay). Drawn from the FILE, with the delta
// table from src/dstimport.js, as tools/render-dst.mjs is.
//
// Key: stitches shade from orange (first sewn: the underlay) to dark blue
// (last: the end of the column); every jump record after the first stitch
// is a RED line (the ones before it, from the design's origin, are not drawn); the green
// dot is the first stitch of the file, the magenta dot the column's first.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { encodePNG } from "./png.mjs";
import { SHAPES, build, gapMm } from "./underlay-direction-measure.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const { encodeDST } = require(path.join(ROOT, "src", "dst.js"));
const { decodeDelta } = require(path.join(ROOT, "src", "dstimport.js"));

const outDir = path.resolve(process.argv[2] || path.join(ROOT, "docs", "renders", "underlay-direction-2026-10-11"));
fs.mkdirSync(outDir, { recursive: true });

function records(buf) {
  const data = buf.subarray(512), segs = [];
  let x = 0, y = 0;
  for (let i = 0; i + 2 < data.length; i += 3) {
    const b0 = data[i], b1 = data[i + 1], b2 = data[i + 2];
    if (b0 === 0 && b1 === 0 && b2 === 0xf3) break;
    const [dx, dy] = decodeDelta(b0, b1, b2);
    const nx = x + dx, ny = y + dy;
    if (!(b2 & 0x40)) segs.push({ x0: x, y0: y, x1: nx, y1: ny, jump: (b2 & 0x80) !== 0 });
    x = nx; y = ny;
  }
  return segs;
}

const SCALE = 24, PAD = 24;   // px per mm, px
const panels = [];
for (const flag of [false, true]) {
  const d = build(SHAPES["bar 30 x 3 mm"], "left_chest", flag);
  const buf = Buffer.from(encodeDST(d));
  fs.writeFileSync(path.join(outDir, flag ? "on.dst" : "off.dst"), buf);
  const segs = records(buf);
  // the column's first record: where the satin span starts, in the design stream
  const sat = d.runs.find((s) => s.kind === "satin");
  const colStart = d.stitches[sat.i0];
  const jumps = segs.filter((s) => s.jump);
  console.log(`${flag ? "on " : "off"}: ${segs.length} records, ${jumps.length} jump records (${jumps.map((s) => (Math.hypot(s.x1 - s.x0, s.y1 - s.y0) / 10).toFixed(1)).join(", ")} mm); underlay -> column ${gapMm(d).toFixed(2)} mm; ${d.stitchCount} stitches`);
  panels.push({ segs, colStart, first: segs.find((s) => !s.jump) });
}

let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
for (const p of panels) for (const s of p.segs) { minX = Math.min(minX, s.x0, s.x1); maxX = Math.max(maxX, s.x0, s.x1); minY = Math.min(minY, s.y0, s.y1); maxY = Math.max(maxY, s.y0, s.y1); }
const pw = Math.ceil((maxX - minX) / 10 * SCALE) + 2 * PAD, ph = Math.ceil((maxY - minY) / 10 * SCALE) + 2 * PAD;
const W = pw, H = ph * panels.length;
const rgba = new Uint8Array(W * H * 4).fill(255);
const put = (x, y, c) => { x = Math.round(x); y = Math.round(y); if (x < 0 || y < 0 || x >= W || y >= H) return; const i = (y * W + x) * 4; rgba[i] = c[0]; rgba[i + 1] = c[1]; rgba[i + 2] = c[2]; rgba[i + 3] = 255; };
const line = (x0, y0, x1, y1, c, w) => { const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * 2)); for (let k = 0; k <= n; k++) { const t = k / n, x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t; for (let a = -w; a <= w; a++) for (let b = -w; b <= w; b++) put(x + a, y + b, c); } };
const dot = (x, y, c, r) => { for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) if (a * a + b * b <= r * r) put(x + a, y + b, c); };
panels.forEach((p, k) => {
  const tx = (u) => PAD + (u - minX) / 10 * SCALE, ty = (u) => k * ph + PAD + (maxY - u) / 10 * SCALE;
  for (let x = 0; x < W; x++) put(x, k * ph, [200, 200, 200]);
  const n = p.segs.length;
  p.segs.forEach((s, i) => {
    if (s.jump) return;
    const t = i / Math.max(1, n - 1);
    line(tx(s.x0), ty(s.y0), tx(s.x1), ty(s.y1), [Math.round(240 - 220 * t), Math.round(140 - 100 * t), Math.round(20 + 140 * t)], 0);
  });
  // the jumps before the first stitch carry the frame from the design's
  // origin to the shape: not drawn, they would lie over the underlay
  const i0 = p.segs.indexOf(p.first);
  p.segs.forEach((s, i) => { if (s.jump && i > i0) line(tx(s.x0), ty(s.y0), tx(s.x1), ty(s.y1), [220, 0, 0], 1); });
  if (p.first) dot(tx(p.first.x0), ty(p.first.y0), [0, 170, 60], 5);
  dot(tx(p.colStart.x), ty(p.colStart.y), [200, 0, 200], 5);
});
fs.writeFileSync(path.join(outDir, "bar.png"), encodePNG(W, H, rgba));
console.log(`wrote ${path.relative(ROOT, outDir)}/{off.dst,on.dst,bar.png} (${W} x ${H})`);
