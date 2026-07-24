// OFFLINE: parse an Ink/Stitch font (ltr.svg + font.json) into a compact
// pre-digitized glyph library JSON that src/satinfont.js plays back at runtime.
// Usage: node tools/build-font.mjs <fontDir> <outJson>
//   e.g. node tools/build-font.mjs scratch_ink/geneva_simple src/fonts/geneva_simple.json
// where fontDir has ltr.svg + font.json + LICENSE.
import fs from "node:fs";
import path from "node:path";

const SRC = process.argv[2];
const OUT = process.argv[3];
if (!SRC || !OUT) { console.error("usage: build-font.mjs <fontDir|svgFile> <outJson>"); process.exit(1); }
const svgFile = SRC.endsWith(".svg") ? SRC : path.join(SRC, "ltr.svg");
const metaFile = SRC.endsWith(".svg") ? SRC.replace(/ltr\.svg$/, "font.json") : path.join(SRC, "font.json");
const licFile = SRC.endsWith(".svg") ? SRC.replace(/ltr\.svg$/, "LICENSE") : path.join(SRC, "LICENSE");
const svg = fs.readFileSync(svgFile, "utf8");
const meta = JSON.parse(fs.readFileSync(metaFile, "utf8"));
const license = fs.existsSync(licFile) ? fs.readFileSync(licFile, "utf8").split("\n").slice(0, 4).join(" ").trim() : "";

// --- SVG path parser -> subpaths (polylines); flattens C/Q beziers ---
function parsePath(d) {
  const toks = d.match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [];
  let i = 0; const num = () => parseFloat(toks[i++]);
  const subs = []; let cur = null, cx = 0, cy = 0, sx = 0, sy = 0, cmd = "";
  const FLAT = +(process.env.FLATTEN || 8);
  const bez = (x0, y0, x1, y1, x2, y2, x3, y3) => { const N = FLAT; for (let k = 1; k <= N; k++) { const t = k / N, u = 1 - t; cur.push({ x: u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3, y: u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3 }); } };
  while (i < toks.length) {
    if (/[a-zA-Z]/.test(toks[i])) cmd = toks[i++];
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase();
    if (C === "M") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; sx = cx; sy = cy; cur = [{ x: cx, y: cy }]; subs.push(cur); cmd = rel ? "l" : "L"; }
    else if (C === "L") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "H") { const x = num(); cx = rel ? cx + x : x; cur.push({ x: cx, y: cy }); }
    else if (C === "V") { const y = num(); cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "C") { const a = num(), b = num(), c = num(), d2 = num(), e = num(), f = num(); const X1 = rel ? cx + a : a, Y1 = rel ? cy + b : b, X2 = rel ? cx + c : c, Y2 = rel ? cy + d2 : d2, X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, X1, Y1, X2, Y2, X, Y); cx = X; cy = Y; }
    else if (C === "Q") { const a = num(), b = num(), e = num(), f = num(); const X1 = rel ? cx + a : a, Y1 = rel ? cy + b : b, X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, cx + 2 / 3 * (X1 - cx), cy + 2 / 3 * (Y1 - cy), X + 2 / 3 * (X1 - X), Y + 2 / 3 * (Y1 - Y), X, Y); cx = X; cy = Y; }
    else if (C === "Z") { if (cur) cur.push({ x: sx, y: sy }); cx = sx; cy = sy; }
    else i++;
  }
  return subs.filter((s) => s.length >= 2);
}
const plen = (p) => { let L = 0; for (let k = 0; k + 1 < p.length; k++) L += Math.hypot(p[k + 1].x - p[k].x, p[k + 1].y - p[k].y); return L; };
const d2 = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const r1 = (n) => Math.round(n * 10) / 10;
const enc = (poly) => poly.map((p) => [r1(p.x), r1(p.y)]);

// Do polylines P and Q have any crossing segments? (rung↔rail intersection test)
function segCross(a, b, c, d) { const rx = b.x - a.x, ry = b.y - a.y, sx = d.x - c.x, sy = d.y - c.y; const den = rx * sy - ry * sx; if (Math.abs(den) < 1e-9) return false; const t = ((c.x - a.x) * sy - (c.y - a.y) * sx) / den, u = ((c.x - a.x) * ry - (c.y - a.y) * rx) / den; return t >= -0.01 && t <= 1.01 && u >= -0.01 && u <= 1.01; }
function polyCross(P, Q) { for (let i = 0; i + 1 < P.length; i++) for (let j = 0; j + 1 < Q.length; j++) if (segCross(P[i], P[i + 1], Q[j], Q[j + 1])) return true; return false; }

// Ink/Stitch's rail identification (satin_column.py rail_indices): rungs cross
// both rails, so classify by how many OTHER subpaths each intersects — NOT by
// length (a rung can be longer than short rails on cursive/wide columns).
function railIndices(subs) {
  const n = subs.length; const lens = subs.map(plen);
  const byLen = subs.map((_, i) => i).sort((a, b) => lens[b] - lens[a]);
  if (n <= 2) return [0, 1].slice(0, n);
  const inter = subs.map((_, i) => subs.reduce((acc, __, j) => acc + (i !== j && polyCross(subs[i], subs[j]) ? 1 : 0), 0));
  // 3 subpaths → a rail meets the single rung once; >3 → a rail meets many rungs (>2).
  const cand = (n === 3)
    ? subs.map((_, i) => i).filter((i) => inter[i] === 1 && lens[i] > 0.1)
    : subs.map((_, i) => i).filter((i) => inter[i] > 2 && lens[i] > 0.1);
  return cand.length === 2 ? cand : byLen.slice(0, 2); // ambiguous (#-shape) → longest
}

// Sample-based rail orientation (satin_column.py _get_rails_to_reverse): if the
// average corresponding-point distance is smaller with railB reversed, it was
// drawn backwards — reverse it so both rails run the same direction.
function orientRailB(railA, railB) {
  const at = (poly, f) => { const L = plen(poly), s = f * L; let acc = 0; for (let i = 0; i + 1 < poly.length; i++) { const seg = Math.hypot(poly[i + 1].x - poly[i].x, poly[i + 1].y - poly[i].y); if (acc + seg >= s) { const t = seg > 1e-9 ? (s - acc) / seg : 0; return { x: poly[i].x + (poly[i + 1].x - poly[i].x) * t, y: poly[i].y + (poly[i + 1].y - poly[i].y) * t }; } acc += seg; } return poly[poly.length - 1]; };
  let fwd = 0, rev = 0;
  for (let k = 1; k <= 9; k++) { const f = k / 10; const a = at(railA, f); fwd += d2(a, at(railB, f)); rev += d2(a, at(railB, 1 - f)); }
  return rev < fwd ? railB.slice().reverse() : railB;
}

function toColumn(subs) {
  const ri = railIndices(subs);
  let railA = subs[ri[0]], railB = orientRailB(subs[ri[0]], subs[ri[1]]);
  const rungs = subs.filter((_, i) => i !== ri[0] && i !== ri[1]).map((r) => {
    const p0 = r[0], p1 = r[r.length - 1];
    const p0A = Math.min(...railA.map((q) => d2(p0, q))), p0B = Math.min(...railB.map((q) => d2(p0, q)));
    return p0A <= p0B ? [p0, p1] : [p1, p0];
  });
  return { railA: enc(railA), railB: enc(railB), rungs: rungs.map((rg) => [[r1(rg[0].x), r1(rg[0].y)], [r1(rg[1].x), r1(rg[1].y)]]) };
}

// --- iterate every glyph layer ---
function paths(layer) {
  const out = []; const re = /<path\b[\s\S]*?\/>/g; let m;
  while ((m = re.exec(layer))) { const t = m[0]; const dq = t.match(/\sd="([^"]*)"/); if (!dq) continue; out.push({ d: dq[1], satin: /satin_column="True"/i.test(t), running: /running_stitch_length_mm/i.test(t) && !/satin_column="True"/i.test(t) }); }
  return out;
}

// Decode the XML entities Inkscape writes into layer labels so glyph keys are
// the real characters (" & < > ' and numeric refs), letting text lookups hit.
function decodeEntities(s) {
  return s.replace(/&#x([0-9a-fA-F]+);/g, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(parseInt(d, 10)))
    .replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}

const glyphs = {};
const re = /inkscape:label="GlyphLayer-([\s\S]*?)"/g; let m; let count = 0;
while ((m = re.exec(svg))) {
  const ch = decodeEntities(m[1]);
  const g0 = svg.lastIndexOf("<g", m.index);
  let depth = 0; const gre = /<\/?g\b/g; gre.lastIndex = g0; let gm, end = -1;
  while ((gm = gre.exec(svg))) { if (svg[gm.index + 1] === "/") { depth--; if (depth === 0) { end = gm.index; break; } } else depth++; }
  if (end < 0) continue;
  const layer = svg.slice(g0, end);
  const cols = [], runs = [];
  for (const p of paths(layer)) {
    const subs = parsePath(p.d);
    if (p.satin && subs.length >= 2) cols.push(toColumn(subs));
    else if (subs.length) for (const s of subs) runs.push(enc(s));
  }
  if (!cols.length && !runs.length) continue;
  let advance = (meta.horiz_adv_x && meta.horiz_adv_x[ch] != null) ? meta.horiz_adv_x[ch] : meta.horiz_adv_x_default;
  if (advance == null) {
    // Font provides no metrics (e.g. medium_font) — derive advance from the
    // glyph's right edge + a side bearing, so glyphs don't collapse onto x=0.
    let maxX = -Infinity;
    for (const c of cols) { for (const p of c.railA) if (p[0] > maxX) maxX = p[0]; for (const p of c.railB) if (p[0] > maxX) maxX = p[0]; }
    for (const rr of runs) for (const p of rr) if (p[0] > maxX) maxX = p[0];
    advance = isFinite(maxX) ? Math.round(maxX + 0.08 * meta.units_per_em) : meta.units_per_em;
  }
  glyphs[ch] = { adv: advance, cols, runs };
  count++;
}

const outObj = {
  name: meta.name, license, source: "Ink/Stitch embroidery-fonts",
  unitsPerEm: meta.units_per_em, sizeMm: meta.size, leading: meta.leading,
  advDefault: meta.horiz_adv_x_default != null ? meta.horiz_adv_x_default : Math.round(0.55 * meta.units_per_em),
  advSpace: meta.horiz_adv_x_space != null ? meta.horiz_adv_x_space : Math.round(0.3 * meta.units_per_em),
  kerning: meta.kerning_pairs || {}, glyphCount: count, glyphs,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(outObj));
console.log(JSON.stringify({ name: meta.name, glyphs: count, bytes: fs.statSync(OUT).size, sample: Object.keys(glyphs).slice(0, 20) }));
