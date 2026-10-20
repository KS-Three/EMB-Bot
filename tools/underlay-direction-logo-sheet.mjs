// A logo digitized the way the Studio's image lane does it, written to .dst
// with `underlayDirection` off and on, each file decoded record by record and
// drawn, with the numbers a machine cares about (defect 57, 2026-10-11, the
// flip sitting; PR #822 measured bars only).
//
//   node tools/underlay-direction-logo-sheet.mjs <image.png> [outDir]
//        [--name slug] [--colors N] [--garment id] [--keep-bg]
//
// Writes <slug>.png (off on top, on below), <slug>-off.dst and <slug>-on.dst
// to outDir (default docs/renders/underlay-direction-on-2026-10-11/) and
// prints one line per arm:
//
//   needle-up  every jump record after the first stitch, summed in mm
//   trims      design `trim` stitches (what the engine asked the machine to cut)
//   3-jump     runs of 3 or more consecutive jump records in the FILE: what a
//              machine set to cut on three jumps reads as a trim, whether the
//              engine meant it or a long move was merely split into pieces
//   stitches   design stitch count
//
// Key: stitches shade orange (first sewn) to dark blue (last); a jump record
// after the first stitch is RED; the green dot is the first stitch.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { encodePNG, decodePNG, downscale } from "./png.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
globalThis.window = globalThis;
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(`../src/${f}.js`);
const DG = require("../src/digitize.js"), FAB = require("../src/fabrics.js"), GAR = require("../src/garments.js");
const { encodeDST } = require("../src/dst.js");
const { decodeDelta } = require("../src/dstimport.js");
const lib = (f) => import(pathToFileURL(path.join(ROOT, "app", "src", "lib", f)).href);

const args = process.argv.slice(2);
const take = (name, dflt) => { const i = args.indexOf(name); if (i < 0) return dflt; const v = args[i + 1]; args.splice(i, 2); return v; };
const flag = (name) => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
const N_COLORS = Number(take("--colors", 4)), GARMENT = take("--garment", "left_chest"), KEEP_BG = flag("--keep-bg");
const SLUG = take("--name", null);
const [SRC, OUT_ARG] = args;
if (!SRC) { console.error("usage: node tools/underlay-direction-logo-sheet.mjs <image.png> [outDir] [--name slug] [--colors N] [--garment id] [--keep-bg]"); process.exit(2); }
const slug = SLUG || path.basename(SRC, path.extname(SRC));
const outDir = path.resolve(OUT_ARG || path.join(ROOT, "docs", "renders", "underlay-direction-on-2026-10-11"));
fs.mkdirSync(outDir, { recursive: true });

const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
let img = decodePNG(SRC);
if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
const rgba0 = Uint8ClampedArray.from(img.rgba);
for (let i = 3; i < rgba0.length; i += 4) if (rgba0[i] < ALPHA_CUTOFF) rgba0[i] = 0;
const reg = flatToRegions(flattenRGBA(rgba0, img.width, img.height, { nColors: N_COLORS, removeBg: !KEEP_BG }));
const build = (underlayDirection) => DG.buildQualityDesign(JSON.parse(JSON.stringify(reg.regions)), {
  garment: GAR.getGarment(GARMENT), fabric: FAB.getFabric(FAB.fabricForGarment(GARMENT)), pxPerMm: reg.pxPerMm,
  satinMaxWidthMm: 3.0, underlay: true, offsetXMm: 0, offsetYMm: 0, underlayDirection,
});

// every record of the file: {x0,y0,x1,y1,kind:"stitch"|"jump"|"color"}
function records(buf) {
  const data = buf.subarray(512), segs = [];
  let x = 0, y = 0;
  for (let i = 0; i + 2 < data.length; i += 3) {
    const b0 = data[i], b1 = data[i + 1], b2 = data[i + 2];
    if (b0 === 0 && b1 === 0 && b2 === 0xf3) break;
    const [dx, dy] = decodeDelta(b0, b1, b2);
    const nx = x + dx, ny = y + dy;
    const kind = (b2 & 0xc0) === 0xc0 ? "color" : (b2 & 0x80) ? "jump" : "stitch";
    segs.push({ x0: x, y0: y, x1: nx, y1: ny, kind });
    x = nx; y = ny;
  }
  return segs;
}

function measure(d, segs) {
  const first = segs.findIndex((s) => s.kind === "stitch");
  let needleUp = 0, run = 0, threeJump = 0, jumpRecs = 0;
  segs.forEach((s, i) => {
    if (s.kind === "jump" && i > first) { needleUp += Math.hypot(s.x1 - s.x0, s.y1 - s.y0) / 10; jumpRecs++; run++; }
    else { if (run >= 3) threeJump++; run = 0; }
  });
  if (run >= 3) threeJump++;
  return {
    needleUpMm: needleUp, jumpRecords: jumpRecs, threeJumpRuns: threeJump,
    trims: d.stitches.filter((s) => s.type === "trim").length, stitches: d.stitchCount,
    nSatin: d._debug && d._debug.nSatin, nFill: d._debug && d._debug.nFill,
  };
}

const SCALE = 14, PAD = 20;
const arms = [];
for (const on of [false, true]) {
  const d = build(on);
  const buf = Buffer.from(encodeDST(d));
  fs.writeFileSync(path.join(outDir, `${slug}-${on ? "on" : "off"}.dst`), buf);
  const segs = records(buf);
  const m = measure(d, segs);
  arms.push({ on, segs, m });
  console.log(`${slug} ${on ? "on " : "off"}: needle-up ${m.needleUpMm.toFixed(1)} mm  jump records ${m.jumpRecords}  3-jump runs ${m.threeJumpRuns}  trims ${m.trims}  stitches ${m.stitches}  (satin ${m.nSatin}, fill ${m.nFill})`);
}

let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
for (const a of arms) for (const s of a.segs) { if (s.kind === "color") continue; minX = Math.min(minX, s.x0, s.x1); maxX = Math.max(maxX, s.x0, s.x1); minY = Math.min(minY, s.y0, s.y1); maxY = Math.max(maxY, s.y0, s.y1); }
const pw = Math.ceil((maxX - minX) / 10 * SCALE) + 2 * PAD, ph = Math.ceil((maxY - minY) / 10 * SCALE) + 2 * PAD + 22;
const W = pw, H = ph * arms.length;
const rgba = new Uint8Array(W * H * 4).fill(255);
const put = (x, y, c) => { x = Math.round(x); y = Math.round(y); if (x < 0 || y < 0 || x >= W || y >= H) return; const i = (y * W + x) * 4; rgba[i] = c[0]; rgba[i + 1] = c[1]; rgba[i + 2] = c[2]; rgba[i + 3] = 255; };
const line = (x0, y0, x1, y1, c, w) => { const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * 2)); for (let k = 0; k <= n; k++) { const t = k / n, x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t; for (let a = -w; a <= w; a++) for (let b = -w; b <= w; b++) put(x + a, y + b, c); } };
const dot = (x, y, c, r) => { for (let a = -r; a <= r; a++) for (let b = -r; b <= r; b++) if (a * a + b * b <= r * r) put(x + a, y + b, c); };
arms.forEach((a, k) => {
  const tx = (u) => PAD + (u - minX) / 10 * SCALE, ty = (u) => k * ph + PAD + (maxY - u) / 10 * SCALE;
  for (let x = 0; x < W; x++) put(x, k * ph, [200, 200, 200]);
  const n = a.segs.length, i0 = a.segs.findIndex((s) => s.kind === "stitch");
  a.segs.forEach((s, i) => {
    if (s.kind !== "stitch") return;
    const t = i / Math.max(1, n - 1);
    line(tx(s.x0), ty(s.y0), tx(s.x1), ty(s.y1), [Math.round(240 - 220 * t), Math.round(140 - 100 * t), Math.round(20 + 140 * t)], 0);
  });
  // jumps before the first stitch carry the frame from the design's origin: not drawn
  a.segs.forEach((s, i) => { if (s.kind === "jump" && i > i0) line(tx(s.x0), ty(s.y0), tx(s.x1), ty(s.y1), [220, 0, 0], 1); });
  if (i0 >= 0) dot(tx(a.segs[i0].x0), ty(a.segs[i0].y0), [0, 170, 60], 5);
});
fs.writeFileSync(path.join(outDir, `${slug}.png`), encodePNG(W, H, rgba));
console.log(`wrote ${path.relative(ROOT, outDir)}/${slug}{.png,-off.dst,-on.dst} (${W} x ${H}); off on top, on below`);
