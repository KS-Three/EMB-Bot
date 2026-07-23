// Flatten pipeline preview: PNG -> quantize N -> modeFilter -> absorb -> flat PNG
// (+ optional merges via MERGE env "0,1;3,4") -> digitize -> DST.
import { createRequire } from "module";
import fs from "node:fs";
import { decodePNG, downscale, encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
const Q = require("../src/quantize.js");
const FL = require("../src/flatten.js");
const G = require("../src/geometry.js");
const DG = require("../src/digitize.js");
const FB = require("../src/fabrics.js");
const D = require("../src/dst.js");

const IN = process.argv[2] || "scratch_logo.png";
const N = +(process.env.NCOLORS || 6);
const WORK = +(process.env.WORKPX || 420);
const img = downscale(decodePNG(IN), WORK);
const w = img.width, h = img.height, data = img.rgba;
for (let i = 0; i < w * h; i++) if (data[i * 4 + 3] < 128) data[i * 4 + 3] = 0;

let { palette, indices } = Q.medianCut(data, N);
console.error("auto palette:", JSON.stringify(palette));
indices = FL.modeFilter(indices, w, h, { iterations: 2 });
indices = FL.absorbSmallRegions(indices, w, h, Math.round(w * h * +(process.env.ABSORB || 0.0012)));

// optional manual merges: MERGE="0,1;2,5" merges palette idx 0+1, then (post-remap) 2+5
if (process.env.MERGE) {
  for (const grp of process.env.MERGE.split(";")) {
    const ids = grp.split(",").map(Number);
    ({ palette, indices } = FL.mergeColors(palette, indices, ids));
  }
  indices = FL.absorbSmallRegions(indices, w, h, Math.round(w * h * 0.0012));
  console.error("after merges:", JSON.stringify(palette));
}
console.error("shares:", FL.paletteShares(indices, palette.length).map((s) => +(s * 100).toFixed(1)).join("% , ") + "%");

// flat art PNG
fs.writeFileSync("scratch_flatart.png", encodePNG(w, h, FL.indicesToRGBA(indices, palette, w, h)));

// digitize the flattened result
function polyArea(p){let a=0;for(let i=0,j=p.length-1;i<p.length;j=i++)a+=(p[j].x*p[i].y-p[i].x*p[j].y);return Math.abs(a)/2;}
const despeckle = w * h * +(process.env.DESPECKLE || 0.0010), holeMin = Math.max(6, despeckle * 0.3);
const regions = [];
for (let i = 0; i < palette.length; i++) {
  const mask = new Uint8Array(w * h);
  let cnt = 0; for (let p = 0; p < indices.length; p++) if (indices[p] === i) { mask[p] = 1; cnt++; }
  if (cnt < despeckle) continue;
  let shapes = G.traceRegions(mask, w, h)
    .map((s) => ({ outer: G.simplify(s.outer, 1.6), holes: s.holes.map((hh) => G.simplify(hh, 1.6)).filter((hh) => hh.length >= 4 && polyArea(hh) > holeMin) }))
    .filter((s) => s.outer.length >= 4 && polyArea(s.outer) > despeckle);
  shapes.sort((a, b) => polyArea(b.outer) - polyArea(a.outer));
  const cap = +(process.env.MAXPOLYS || 30); if (shapes.length > cap) shapes = shapes.slice(0, cap);
  if (shapes.length) regions.push({ rgb: palette[i], shapes });
}
// Fabric: explicit FABRIC env wins; else derive from garment id (GID); else none.
const GID = process.env.GID || null;
const FABRIC = process.env.FABRIC || (GID ? FB.fabricForGarment(GID) : null);
const fabric = FABRIC ? FB.getFabric(FABRIC) : null;
const garment = { widthIn: +(process.env.GW || 5), heightIn: +(process.env.GH || 2.25) };
if (GID) garment.id = GID;
console.error(`garment ${GID || "(none)"} fabric ${fabric ? fabric.id : "(none)"}`);
const design = DG.buildQualityDesign(regions, { garment, pxPerMm: 8, densityMm: 0.45, satinMaxWidthMm: 3.0, underlay: true, fabric });
console.error(`design ${design.stitchCount} stitches, ${design.colorCount} colors, satin ${design._debug.nSatin} fill ${design._debug.nFill} centerOut ${design._debug.nCenterOut} trims ${design._debug.nTrims}`);
fs.writeFileSync("scratch_flatart.dst", Buffer.from(D.encodeDST(design)));
fs.writeFileSync("scratch_flatart_colors.json", JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
console.log(JSON.stringify({ palette: palette.length, stitches: design.stitchCount, sizeMM: [+design.widthMM.toFixed(1), +design.heightMM.toFixed(1)] }));
