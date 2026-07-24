// Parse ONE glyph from an Ink/Stitch font ltr.svg into satin columns
// (rails+rungs) and play it through our satinplay engine, then render — to
// validate that Ink/Stitch's hand-authored columns + our playback = clean.
// Usage: SVG=scratch_ink/apex_ltr.svg CH=B node tools/parse-inkstitch.mjs out.png
import fs from "node:fs";
import { createRequire } from "module";
import { encodePNG } from "./png.mjs";
const require = createRequire(import.meta.url);
global.window = global;
const SP = require("../src/satinplay.js");

const SVGFILE = process.env.SVG || "scratch_ink/apex_ltr.svg";
const CH = process.env.CH || "B";
const OUT = process.argv[2] || "scratch_ink_glyph.png";
const svg = fs.readFileSync(SVGFILE, "utf8");

// --- extract the glyph's layer (nested-<g> aware) ---
function glyphLayer(svg, ch) {
  const marker = 'inkscape:label="GlyphLayer-' + ch + '"';
  const i = svg.indexOf(marker);
  if (i < 0) throw new Error("glyph not found: " + ch);
  const g0 = svg.lastIndexOf("<g", i);
  let depth = 0; const re = /<\/?g\b/g; re.lastIndex = g0; let m, end = -1;
  while ((m = re.exec(svg))) { if (svg[m.index + 1] === "/") { depth--; if (depth === 0) { end = m.index; break; } } else depth++; }
  return svg.slice(g0, end);
}

// --- minimal SVG path parser -> array of subpaths (each a polyline) ---
function parsePath(d) {
  const toks = d.match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [];
  let i = 0; const num = () => parseFloat(toks[i++]);
  const subs = []; let cur = null; let cx = 0, cy = 0, sx = 0, sy = 0; let cmd = "";
  const bez = (x0, y0, x1, y1, x2, y2, x3, y3) => { const N = 10; for (let k = 1; k <= N; k++) { const t = k / N, u = 1 - t; const x = u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3, y = u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3; cur.push({ x, y }); } };
  while (i < toks.length) {
    if (/[a-zA-Z]/.test(toks[i])) cmd = toks[i++];
    const rel = cmd === cmd.toLowerCase();
    const C = cmd.toUpperCase();
    if (C === "M") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; sx = cx; sy = cy; cur = [{ x: cx, y: cy }]; subs.push(cur); cmd = rel ? "l" : "L"; }
    else if (C === "L") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "H") { const x = num(); cx = rel ? cx + x : x; cur.push({ x: cx, y: cy }); }
    else if (C === "V") { const y = num(); cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "C") { const x1 = num(), y1 = num(), x2 = num(), y2 = num(), x = num(), y = num(); const X1 = rel ? cx + x1 : x1, Y1 = rel ? cy + y1 : y1, X2 = rel ? cx + x2 : x2, Y2 = rel ? cy + y2 : y2, X = rel ? cx + x : x, Y = rel ? cy + y : y; bez(cx, cy, X1, Y1, X2, Y2, X, Y); cx = X; cy = Y; }
    else if (C === "Q") { const x1 = num(), y1 = num(), x = num(), y = num(); const X1 = rel ? cx + x1 : x1, Y1 = rel ? cy + y1 : y1, X = rel ? cx + x : x, Y = rel ? cy + y : y; bez(cx, cy, cx + 2 / 3 * (X1 - cx), cy + 2 / 3 * (Y1 - cy), X + 2 / 3 * (X1 - X), Y + 2 / 3 * (Y1 - Y), X, Y); cx = X; cy = Y; }
    else if (C === "Z") { if (cur) cur.push({ x: sx, y: sy }); cx = sx; cy = sy; }
    else { i++; } // skip unknown
  }
  return subs.filter((s) => s.length >= 2);
}

function plen(p) { let L = 0; for (let k = 0; k + 1 < p.length; k++) L += Math.hypot(p[k + 1].x - p[k].x, p[k + 1].y - p[k].y); return L; }
function d2(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

// --- pull each <path .../> out of the layer with its attrs ---
function paths(layer) {
  const out = []; const re = /<path\b[\s\S]*?\/>/g; let m;
  while ((m = re.exec(layer))) {
    const t = m[0];
    const dq = t.match(/\sd="([^"]*)"/);
    const satin = /satin_column="True"/i.test(t);
    const running = /running_stitch_length_mm/i.test(t) && !satin;
    if (dq) out.push({ d: dq[1], satin, running });
  }
  return out;
}

// --- build satin column {railA,railB,rungs} from a satin path's subpaths ---
function toColumn(subs) {
  const sorted = subs.slice().sort((a, b) => plen(b) - plen(a));
  let railA = sorted[0], railB = sorted[1];
  const rungSubs = sorted.slice(2);
  // orient railB same direction as railA
  if (d2(railA[0], railB[0]) > d2(railA[0], railB[railB.length - 1])) railB = railB.slice().reverse();
  // rungs: endpoints, oriented [nearA, nearB]
  const rungs = rungSubs.map((r) => {
    const p0 = r[0], p1 = r[r.length - 1];
    const p0A = Math.min(...railA.map((q) => d2(p0, q))), p0B = Math.min(...railB.map((q) => d2(p0, q)));
    return p0A <= p0B ? [p0, p1] : [p1, p0];
  });
  return { railA, railB, rungs };
}

const layer = glyphLayer(svg, CH);
const ps = paths(layer);
const columns = [], runnings = [];
for (const p of ps) {
  const subs = parsePath(p.d);
  if (p.satin && subs.length >= 2) columns.push(toColumn(subs));
  else if (subs.length) runnings.push(subs);
}

// playback
const SPACING = +(process.env.SPACING || 0.4);
const PXPERMM = +(process.env.PXPERMM || 3);
const runs = [];
for (const c of columns) {
  const pts = SP.satinFromRails(c.railA, c.railB, c.rungs, { spacingMm: SPACING, pxPerMm: PXPERMM, pullCompMm: 0 });
  if (pts.length >= 2) runs.push(pts);
}

// --- render ---
let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
for (const c of columns) for (const r of [c.railA, c.railB]) for (const q of r) { minX = Math.min(minX, q.x); minY = Math.min(minY, q.y); maxX = Math.max(maxX, q.x); maxY = Math.max(maxY, q.y); }
const sc = 3, pad = 20;
const W = Math.ceil((maxX - minX) * sc) + pad * 2, H = Math.ceil((maxY - minY) * sc) + pad * 2;
const px = new Uint8ClampedArray(W * H * 4); for (let i = 0; i < px.length; i += 4) { px[i] = px[i + 1] = px[i + 2] = 255; px[i + 3] = 255; }
const TX = (x) => pad + (x - minX) * sc, TY = (y) => pad + (y - minY) * sc;
function set(x, y, r, g, b) { x |= 0; y |= 0; if (x < 0 || y < 0 || x >= W || y >= H) return; const o = (y * W + x) * 4; px[o] = r; px[o + 1] = g; px[o + 2] = b; }
function line(x0, y0, x1, y1, r, g, b) { x0 = Math.round(x0); y0 = Math.round(y0); x1 = Math.round(x1); y1 = Math.round(y1); const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0), sxp = x0 < x1 ? 1 : -1, syp = y0 < y1 ? 1 : -1; let e = dx - dy; for (; ;) { set(x0, y0, r, g, b); if (x0 === x1 && y0 === y1) break; const e2 = 2 * e; if (e2 > -dy) { e -= dy; x0 += sxp; } if (e2 < dx) { e += dx; y0 += syp; } } }
// rails (light gray) + rungs (green) + satin (blue)
for (const c of columns) {
  for (const r of [c.railA, c.railB]) for (let k = 0; k + 1 < r.length; k++) line(TX(r[k].x), TY(r[k].y), TX(r[k + 1].x), TY(r[k + 1].y), 205, 205, 205);
  for (const rg of c.rungs) line(TX(rg[0].x), TY(rg[0].y), TX(rg[1].x), TY(rg[1].y), 30, 170, 30);
}
for (const pts of runs) for (let k = 0; k + 1 < pts.length; k += 2) { const a = pts[k], b = pts[k + 1]; line(TX(a.x), TY(a.y), TX(b.x), TY(b.y), 20, 80, 210); }
fs.writeFileSync(OUT, encodePNG(W, H, px));
console.log(JSON.stringify({ ch: CH, paths: ps.length, columns: columns.length, runnings: runnings.length, rungsTotal: columns.reduce((a, c) => a + c.rungs.length, 0), out: OUT }));
