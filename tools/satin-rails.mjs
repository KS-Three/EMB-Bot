// Render satinFromRails on a synthetic curved+tapered column to validate the
// rail+rung playback. Draws rails (gray), rungs (green), crosses (blue).
import fs from "node:fs";
import { createRequire } from "module";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
global.window = global;
const SP = require("../src/satinplay.js");

// Curved tapered column: a 270° arc, inner radius rises (taper), rungs every 60°.
const cx = 300, cy = 300, steps = 72;
const a0 = Math.PI * 0.25, a1 = Math.PI * 1.9;
const railA = [], railB = [], rungs = [];
for (let k = 0; k <= steps; k++) {
  const t = k / steps, a = a0 + (a1 - a0) * t;
  const rOut = 220, rIn = 150 + 45 * t;               // outer fixed, inner rises → taper
  railA.push({ x: cx + rOut * Math.cos(a), y: cy + rOut * Math.sin(a) });
  railB.push({ x: cx + rIn * Math.cos(a), y: cy + rIn * Math.sin(a) });
}
for (let k = 1; k < 6; k++) {
  const a = a0 + (a1 - a0) * (k / 6);
  const rOut = 220, rIn = 150 + 45 * (k / 6);
  rungs.push([{ x: cx + rOut * Math.cos(a), y: cy + rOut * Math.sin(a) }, { x: cx + rIn * Math.cos(a), y: cy + rIn * Math.sin(a) }]);
}

const pts = SP.satinFromRails(railA, railB, rungs, { spacingMm: 0.5, pxPerMm: 4, pullCompMm: 0 });

// bounds + raster
let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
for (const r of [railA, railB]) for (const p of r) { minX = Math.min(minX, p.x); minY = Math.min(minY, p.y); maxX = Math.max(maxX, p.x); maxY = Math.max(maxY, p.y); }
const pad = 20, W = Math.ceil(maxX - minX) + pad * 2, H = Math.ceil(maxY - minY) + pad * 2;
const px = new Uint8ClampedArray(W * H * 4); for (let i = 0; i < px.length; i += 4) { px[i] = px[i + 1] = px[i + 2] = 255; px[i + 3] = 255; }
const TX = (x) => pad + (x - minX), TY = (y) => pad + (y - minY);
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx - dy; for (; ;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sx; } if (e2 < dx) { e += dx; y0 += sy; } } }
for (const r of [railA, railB]) for (let i = 0; i + 1 < r.length; i++) line(TX(r[i].x), TY(r[i].y), TX(r[i + 1].x), TY(r[i + 1].y), 200, 200, 200);
for (let k = 0; k + 1 < pts.length; k += 2) { const a = pts[k], b = pts[k + 1]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 20, 80, 210); }
for (const rg of rungs) line(TX(rg[0].x), TY(rg[0].y), TX(rg[1].x), TY(rg[1].y), 20, 170, 20);
fs.writeFileSync("scratch_rails.png", encodePNG(W, H, px));
console.log(JSON.stringify({ crosses: pts.length / 2, W, H, out: "scratch_rails.png" }));
