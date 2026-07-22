// Node prototype of the quality auto-digitize pipeline. Logs per-stage timing
// so hangs are localized. Writes scratch_new.dst + scratch_new_colors.json.
import { createRequire } from "module";
import fs from "node:fs";
import { decodePNG, downscale } from "./png.mjs";
const require = createRequire(import.meta.url);
const Q = require("../src/quantize.js");
const G = require("../src/geometry.js");
const F = require("../src/fill.js");
const S = require("../src/satin.js");
const D = require("../src/dst.js");
const U = require("../src/units.js");
const GAR = require("../src/garments.js");

const T0 = Date.now();
const log = (m) => console.error(`[${Date.now() - T0}ms] ${m}`);

const OPTS = {
  workPx: +(process.env.WORKPX || 300),
  nColors: +(process.env.NCOLORS || 8),
  alphaMin: 128,
  despeckleFrac: 0.0012,
  maxPolysPerColor: 28,
  simplifyTol: 1.6,
  densityMm: 0.5,
  maxStitchMm: 4,
  satinMaxWidthMm: 3.2,
  pullCompMm: 0.2,
  perRegionAngle: true,
  satin: process.env.SATIN !== "0",
  garment: { widthIn: 5, heightIn: 2.25 },
  pxPerMm: 8,
};

function polyArea(p){let a=0;for(let i=0,j=p.length-1;i<p.length;j=i++)a+=(p[j].x*p[i].y-p[i].x*p[j].y);return Math.abs(a)/2;}
function polyPerim(p){let L=0;for(let i=0;i<p.length;i++){const q=p[(i+1)%p.length];L+=Math.hypot(q.x-p[i].x,q.y-p[i].y);}return L;}
function pcaAngle(polys){let n=0,mx=0,my=0;for(const p of polys)for(const q of p){mx+=q.x;my+=q.y;n++;}if(!n)return 45;mx/=n;my/=n;let sxx=0,syy=0,sxy=0;for(const p of polys)for(const q of p){const dx=q.x-mx,dy=q.y-my;sxx+=dx*dx;syy+=dy*dy;sxy+=dx*dy;}return 0.5*Math.atan2(2*sxy,sxx-syy)*180/Math.PI;}

log("decode");
const full = decodePNG("scratch_logo.png");
const img = downscale(full, OPTS.workPx);
const w = img.width, h = img.height, data = img.rgba;
log(`downscaled ${w}x${h}`);

// alpha threshold: drop glow/background
for (let i = 0; i < w * h; i++) if (data[i * 4 + 3] < OPTS.alphaMin) data[i * 4 + 3] = 0;

log("quantize");
const { palette, indices } = Q.medianCut(data, OPTS.nColors);
log(`palette ${palette.length}`);

const despeckle = w * h * OPTS.despeckleFrac;
const regions = [];
for (let i = 0; i < palette.length; i++) {
  const mask = new Uint8Array(w * h);
  let cnt = 0;
  for (let p = 0; p < indices.length; p++) if (indices[p] === i) { mask[p] = 1; cnt++; }
  if (cnt < despeckle) continue;
  let polys = G.traceContours(mask, w, h).map((pl) => G.simplify(pl, OPTS.simplifyTol)).filter((pl) => pl.length >= 4 && polyArea(pl) > despeckle);
  polys.sort((a, b) => polyArea(b) - polyArea(a));
  if (polys.length > OPTS.maxPolysPerColor) polys = polys.slice(0, OPTS.maxPolysPerColor);
  if (polys.length) regions.push({ rgb: palette[i], polygons: polys, tot: cnt });
  log(`  color ${i} rgb=${palette[i]} px=${cnt} polys=${polys.length}`);
}
regions.sort((a, b) => (b.rgb[0] + b.rgb[1] + b.rgb[2]) - (a.rgb[0] + a.rgb[1] + a.rgb[2]));
log(`regions ${regions.length}`);
if (!regions.length) { console.log("NO REGIONS"); process.exit(0); }

// fit
let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
for (const r of regions) for (const p of r.polygons) for (const q of p) { minX = Math.min(minX, q.x); minY = Math.min(minY, q.y); maxX = Math.max(maxX, q.x); maxY = Math.max(maxY, q.y); }
const pxPerMm = OPTS.pxPerMm;
const fit = GAR.fitScale((maxX - minX) / pxPerMm, (maxY - minY) / pxPerMm, OPTS.garment);
const sc = (fit.scale > 0 && isFinite(fit.scale)) ? fit.scale : 1;
const scalePxToDst = sc * (1 / pxPerMm) * U.DST_UNITS_PER_MM;
const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
const T = (q) => ({ x: Math.round((q.x - cx) * scalePxToDst), y: Math.round((cy - q.y) * scalePxToDst) });
const rowPx = Math.max(0.8, OPTS.densityMm * pxPerMm / sc);
const maxPx = Math.max(3, OPTS.maxStitchMm * pxPerMm / sc);
const satinPxPerMm = Math.max(0.6, pxPerMm / sc);

log("stitching");
const stitches = [], colors = [];
let first = true, cSat = 0, cFill = 0;
for (const r of regions) {
  if (!first) { const last = stitches[stitches.length - 1] || { x: 0, y: 0 }; stitches.push({ type: "color", x: last.x, y: last.y }); }
  first = false; colors.push(r.rgb);
  const angle = OPTS.perRegionAngle ? pcaAngle(r.polygons) : 45;
  for (const poly of r.polygons) {
    const area = polyArea(poly), perim = polyPerim(poly);
    if (area <= 0 || perim <= 0) continue;
    const widthMm = (2 * area / perim) / pxPerMm;
    let pts = [];
    try {
      if (OPTS.satin && widthMm <= OPTS.satinMaxWidthMm) { pts = S.satinColumn(poly, { spacingMm: OPTS.densityMm, pxPerMm: satinPxPerMm, pullCompMm: OPTS.pullCompMm }); cSat++; }
      else { pts = F.tatamiFill([poly], { rowSpacing: rowPx, angleDeg: angle, maxStitch: maxPx }); cFill++; }
    } catch (e) { log(`  poly err ${e.message}`); pts = []; }
    if (!pts || !pts.length) continue;
    const f = T(pts[0]); stitches.push({ type: "jump", x: f.x, y: f.y });
    for (const q of pts) { const d = T(q); stitches.push({ type: "stitch", x: d.x, y: d.y }); }
  }
  log(`  region rgb=${r.rgb} done (satin ${cSat} fill ${cFill}, stitches ${stitches.length})`);
}
stitches.push({ type: "end", x: 0, y: 0 });
const stitchCount = stitches.filter((s) => s.type === "stitch").length;
const design = { stitches, colors: colors.map((c, i) => ({ r: c[0], g: c[1], b: c[2], name: "C" + i })), widthMM: fit.targetWmm, heightMM: fit.targetHmm, stitchCount, colorCount: colors.length };
log(`encode DST (${stitchCount} stitches, ${colors.length} colors)`);
const dst = D.encodeDST(design);
fs.writeFileSync("scratch_new.dst", Buffer.from(dst));
fs.writeFileSync("scratch_new_colors.json", JSON.stringify(colors));
log(`wrote scratch_new.dst ${dst.length} bytes`);
console.log(JSON.stringify({ colors: colors.length, stitchCount, satin: cSat, fill: cFill, sizeMM: [+fit.targetWmm.toFixed(1), +fit.targetHmm.toFixed(1)] }));
