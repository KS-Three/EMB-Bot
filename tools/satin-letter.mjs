// Render a single letter's satin (real glyph outline) so we can dial it in.
// Usage: TEXT=S FAMILY=Roboto node tools/satin-letter.mjs [out.png]
import { createRequire } from "module";
import fs from "node:fs";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
global.window = global;
const opentype = require("../scratch_opentype.js");
globalThis.opentype = opentype;
const F = require("../src/fonts.js");
const S = require("../src/satin.js");

const CH = process.env.TEXT || "S";
const FAMILY = process.env.FAMILY || "Roboto";
const SIZE = +(process.env.SIZE || 400);          // glyph px height-ish
const SPACING = +(process.env.SPACING || 0.4);    // mm peak-to-peak
const PXPERMM = +(process.env.PXPERMM || 10);     // so glyph ~ SIZE/PXPERMM mm
const PULL = +(process.env.PULL || 0);
const OUT = process.argv[2] || "scratch_letter.png";

const fe = F.FONTS.find((f) => f.family === FAMILY);
if (!fe) { console.error("no font " + FAMILY); process.exit(1); }
const cache = "scratch_font_" + FAMILY.replace(/\W+/g, "_") + ".ttf";
if (!fs.existsSync(cache)) { const r = await fetch(fe.url); fs.writeFileSync(cache, Buffer.from(await r.arrayBuffer())); }
const font = opentype.parse(fs.readFileSync(cache).buffer.slice(0));

const path = font.getPath(CH, 0, 0, SIZE);
const polys = F.pathToPolygons(path, 8);
// largest ring by |area|
function area(p) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += p[j].x * p[i].y - p[i].x * p[j].y; return Math.abs(a) / 2; }
polys.sort((a, b) => area(b) - area(a));
const ring = polys[0];

const fn = process.env.MEDIAL === "0" ? S.satinColumn : S.medialSatin;
const pts = fn.call(S, ring, { spacingMm: SPACING, pxPerMm: PXPERMM, pullCompMm: PULL });

// bounds
let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
for (const q of ring) { minX = Math.min(minX, q.x); minY = Math.min(minY, q.y); maxX = Math.max(maxX, q.x); maxY = Math.max(maxY, q.y); }
const pad = 30, sc = 1;
const W = Math.ceil((maxX - minX) * sc) + pad * 2, H = Math.ceil((maxY - minY) * sc) + pad * 2;
const px = new Uint8ClampedArray(W * H * 4); for (let i = 0; i < px.length; i += 4) { px[i] = px[i + 1] = px[i + 2] = 255; px[i + 3] = 255; }
const TX = (x) => pad + (x - minX) * sc, TY = (y) => pad + (y - minY) * sc;
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx - dy; for (;;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sx; } if (e2 < dx) { e += dx; y0 += sy; } } }
// outline (light gray)
for (const p of polys) for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 205, 205, 205); }
// crosses (blue) = consecutive pairs; connectors (faint orange) between crosses
for (let k = 0; k + 1 < pts.length; k += 2) {
  const a = pts[k], b = pts[k + 1];
  line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 20, 80, 200);
  if (k + 2 < pts.length) { const c = pts[k + 2]; line(TX(b.x), TY(b.y), TX(c.x), TY(c.y), 235, 170, 120); }
}
fs.writeFileSync(OUT, encodePNG(W, H, px));

// diagnostics
const [fi, fj] = S.farthestBoundaryPair(ring);
console.log(JSON.stringify({
  family: FAMILY, ch: CH, rings: polys.length, ringPts: ring.length,
  crosses: Math.floor(pts.length / 2), sizeMM: [+((maxX - minX) / PXPERMM).toFixed(1), +((maxY - minY) / PXPERMM).toFixed(1)],
  farthest: [{ x: Math.round(ring[fi].x), y: Math.round(ring[fi].y) }, { x: Math.round(ring[fj].x), y: Math.round(ring[fj].y) }],
  out: OUT,
}));
