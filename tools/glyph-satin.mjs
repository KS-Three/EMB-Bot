// Pre-digitized-glyph pipeline proof: font outline -> glyphColumns (rails+rungs)
// -> satinFromRails playback -> render. Orders columns nearest-neighbour and
// draws travel faintly so satin quality is what stands out.
// Usage: TEXT=B FAMILY=Roboto SIZE=400 node tools/glyph-satin.mjs out.png
import fs from "node:fs";
import { createRequire } from "module";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
global.window = global;
const opentype = require("../scratch_opentype.js");
globalThis.opentype = opentype;
const F = require("../src/fonts.js");
const DG = require("../src/digitize.js");
const S = require("../src/satin.js");
const SP = require("../src/satinplay.js");

const CH = process.env.TEXT || "B";
const FAMILY = process.env.FAMILY || "Roboto";
const SIZE = +(process.env.SIZE || 400);
const SPACING = +(process.env.SPACING || 0.4);
const PXPERMM = +(process.env.PXPERMM || 10);
const OUT = process.argv[2] || "scratch_glyph.png";

const fe = F.FONTS.find((f) => f.family === FAMILY);
const cache = "scratch_font_" + FAMILY.replace(/\W+/g, "_") + ".ttf";
if (!fs.existsSync(cache)) { const r = await fetch(fe.url); fs.writeFileSync(cache, Buffer.from(await r.arrayBuffer())); }
const font = opentype.parse(fs.readFileSync(cache).buffer.slice(0));

const polys = F.pathToPolygons(font.getPath(CH, 0, 0, SIZE), 8);
const shapes = DG.groupRingsIntoShapes(polys);

// collect columns across every shape of the glyph
let cols = [];
for (const sh of shapes) {
  const cc = S.glyphColumns(sh.outer, { spacingMm: SPACING, pxPerMm: PXPERMM, holes: sh.holes });
  cols = cols.concat(cc);
}

// nearest-neighbour ordering: start each column where the last ended; reverse a
// column when its far end is closer.
function ends(c) { return [c.railA[0], c.railA[c.railA.length - 1]]; }
function mid(p, q) { return { x: (p.x + q.x) / 2, y: (p.y + q.y) / 2 }; }
const remaining = cols.slice();
const ordered = [];
let cur = { x: 0, y: 0 };
while (remaining.length) {
  let bi = 0, brev = false, bd = Infinity;
  for (let i = 0; i < remaining.length; i++) {
    const [s, e] = ends(remaining[i]);
    const ds = Math.hypot(s.x - cur.x, s.y - cur.y), de = Math.hypot(e.x - cur.x, e.y - cur.y);
    if (ds < bd) { bd = ds; bi = i; brev = false; }
    if (de < bd) { bd = de; bi = i; brev = true; }
  }
  const c = remaining.splice(bi, 1)[0];
  if (brev) { c.railA.reverse(); c.railB.reverse(); if (c.rungs) c.rungs.reverse(); }
  ordered.push(c);
  const [, e] = ends(c);
  cur = e;
}

// play back + collect travel connectors
const runs = [];      // each run = array of stitch points (satin)
const travels = [];   // [fromPt, toPt]
let last = null;
for (const c of ordered) {
  const pts = SP.satinFromRails(c.railA, c.railB, c.rungs, { spacingMm: SPACING, pxPerMm: PXPERMM, pullCompMm: 0 });
  if (pts.length < 2) continue;
  if (last) travels.push([last, pts[0]]);
  runs.push(pts);
  last = pts[pts.length - 1];
}

// ---- render ----
let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
for (const p of polys) for (const q of p) { minX = Math.min(minX, q.x); minY = Math.min(minY, q.y); maxX = Math.max(maxX, q.x); maxY = Math.max(maxY, q.y); }
const pad = 24, W = Math.ceil(maxX - minX) + pad * 2, H = Math.ceil(maxY - minY) + pad * 2;
const px = new Uint8ClampedArray(W * H * 4); for (let i = 0; i < px.length; i += 4) { px[i] = px[i + 1] = px[i + 2] = 255; px[i + 3] = 255; }
const TX = (x) => pad + (x - minX), TY = (y) => pad + (y - minY);
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1; let e = dx - dy; for (; ;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sx; } if (e2 < dx) { e += dx; y0 += sy; } } }
// outline (light gray)
for (const p of polys) for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 210, 210, 210); }
// satin crosses (blue)
for (const pts of runs) for (let k = 0; k + 1 < pts.length; k += 2) { const a = pts[k], b = pts[k + 1]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 20, 80, 210); }
// travel (faint orange)
for (const [a, b] of travels) line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 245, 200, 160);
fs.writeFileSync(OUT, encodePNG(W, H, px));
console.log(JSON.stringify({ ch: CH, shapes: shapes.length, columns: cols.length, travels: travels.length, out: OUT }));
