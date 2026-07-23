// Visualize satinColumn on a synthetic CURVED stroke (a "C" arc band) so we can
// see whether cross-stitches are perpendicular to the edges and follow the arc.
import { createRequire } from "module";
import fs from "node:fs";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
const S = require("../src/satin.js");

// arc band: outer arc (a0->a1 @ r1) then inner arc (a1->a0 @ r0)  => open "C"
function arcBand(cx, cy, r0, r1, a0, a1, steps) {
  const ring = [];
  for (let k = 0; k <= steps; k++) { const a = a0 + (a1 - a0) * k / steps; ring.push({ x: cx + r1 * Math.cos(a), y: cy + r1 * Math.sin(a) }); }
  for (let k = 0; k <= steps; k++) { const a = a1 + (a0 - a1) * k / steps; ring.push({ x: cx + r0 * Math.cos(a), y: cy + r0 * Math.sin(a) }); }
  return ring;
}

const WHICH = process.argv[2] || "C";
let ring;
if (WHICH === "C") ring = arcBand(200, 200, 120, 150, Math.PI * 0.35, Math.PI * 1.65, 60); // ~C, 30px wide band
else if (WHICH === "bar") { ring = [{x:40,y:180},{x:360,y:170},{x:362,y:200},{x:42,y:210}]; } // slightly skewed bar
else if (WHICH === "taper") { ring = [{x:40,y:190},{x:360,y:150},{x:362,y:175},{x:42,y:215}]; } // tapered

const pts = S.satinColumn(ring, { spacingMm: 2.2, pxPerMm: 4, pullCompMm: 0 });

// render: draw the ring (light gray) + each cross-stitch (alternating a->b) in blue, spine dots red
const W = 420, H = 420;
const px = new Uint8ClampedArray(W * H * 4).fill(255);
for (let i = 0; i < px.length; i += 4) px[i + 3] = 255;
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 |= 0; y0 |= 0; x1 |= 0; y1 |= 0; const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx - dy; for (;;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sx; } if (e2 < dx) { e += dx; y0 += sy; } } }
// ring outline
for (let i = 0; i < ring.length; i++) { const a = ring[i], b = ring[(i + 1) % ring.length]; line(a.x, a.y, b.x, b.y, 210, 210, 210); }
// satin cross-stitches: points come in pairs (a,b),(a,b)... each consecutive pair is a stitch
for (let k = 0; k + 1 < pts.length; k++) { const a = pts[k], b = pts[k + 1]; line(a.x, a.y, b.x, b.y, 30, 90, 200); }
fs.writeFileSync("scratch_satin_" + WHICH + ".png", encodePNG(W, H, px));
console.log(JSON.stringify({ which: WHICH, ringPts: ring.length, stitchPts: pts.length }));
