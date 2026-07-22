// Generic runner: PNG -> ColorRegions -> buildQualityDesign -> DST + colors.
import { createRequire } from "module";
import fs from "node:fs";
import { decodePNG, downscale } from "./png.mjs";
const require = createRequire(import.meta.url);
const Q = require("../src/quantize.js");
const G = require("../src/geometry.js");
const D = require("../src/dst.js");
const DG = require("../src/digitize.js");

const IN = process.argv[2] || "scratch_flat.png";
const OUTDST = process.argv[3] || "scratch_new.dst";
const OUTCOL = process.argv[4] || "scratch_new_colors.json";
const T0 = Date.now(); const log = (m) => console.error(`[${Date.now() - T0}ms] ${m}`);
const opt = {
  workPx: +(process.env.WORKPX || 360),
  nColors: +(process.env.NCOLORS || 7),
  alphaMin: 128, despeckleFrac: 0.0010, maxPolysPerColor: 30, simplifyTol: 1.6,
  densityMm: +(process.env.DENSITY || 0.45), satinMaxWidthMm: +(process.env.SATINMAX || 3.0),
  underlay: process.env.UNDERLAY !== "0",
  garment: { widthIn: +(process.env.GW || 5), heightIn: +(process.env.GH || 2.25) },
  pxPerMm: 8,
};

function polyArea(p){let a=0;for(let i=0,j=p.length-1;i<p.length;j=i++)a+=(p[j].x*p[i].y-p[i].x*p[j].y);return Math.abs(a)/2;}

log("decode " + IN);
const img = downscale(decodePNG(IN), opt.workPx);
const w = img.width, h = img.height, data = img.rgba;
for (let i = 0; i < w * h; i++) if (data[i * 4 + 3] < opt.alphaMin) data[i * 4 + 3] = 0;
log(`work ${w}x${h}`);
const { palette, indices } = Q.medianCut(data, opt.nColors);
log(`palette ${palette.length}`);
const despeckle = w * h * opt.despeckleFrac;
const holeMin = Math.max(6, despeckle * 0.3); // keep smaller holes than blobs (letter counters)
const regions = [];
for (let i = 0; i < palette.length; i++) {
  const mask = new Uint8Array(w * h); let cnt = 0;
  for (let p = 0; p < indices.length; p++) if (indices[p] === i) { mask[p] = 1; cnt++; }
  if (cnt < despeckle) continue;
  let shapes = G.traceRegions(mask, w, h)
    .map((s) => ({
      outer: G.simplify(s.outer, opt.simplifyTol),
      holes: s.holes.map((hh) => G.simplify(hh, opt.simplifyTol)).filter((hh) => hh.length >= 4 && polyArea(hh) > holeMin),
    }))
    .filter((s) => s.outer.length >= 4 && polyArea(s.outer) > despeckle);
  shapes.sort((a, b) => polyArea(b.outer) - polyArea(a.outer));
  if (shapes.length > opt.maxPolysPerColor) shapes = shapes.slice(0, opt.maxPolysPerColor);
  if (shapes.length) regions.push({ rgb: palette[i], shapes });
}
log(`regions ${regions.length}`);
const design = DG.buildQualityDesign(regions, opt);
log(`design: ${design.stitchCount} stitches, ${design.colorCount} colors, satin ${design._debug.nSatin} fill ${design._debug.nFill}`);
const dst = D.encodeDST(design);
fs.writeFileSync(OUTDST, Buffer.from(dst));
fs.writeFileSync(OUTCOL, JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
log(`wrote ${OUTDST} ${dst.length}b`);
console.log(JSON.stringify({ colors: design.colorCount, stitches: design.stitchCount, satin: design._debug.nSatin, fill: design._debug.nFill, sizeMM: [+design.widthMM.toFixed(1), +design.heightMM.toFixed(1)] }));
