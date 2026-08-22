// OFFLINE: parse an Ink/Stitch font into a compact pre-digitized glyph
// library JSON that src/satinfont.js plays back at runtime.
// Usage: node tools/build-font.mjs <fontDir> <outJson>
//   e.g. node tools/build-font.mjs scratch_ink/geneva_simple src/fonts/geneva_simple.json
// where fontDir has font.json + LICENSE and EITHER
//   ltr.svg              — the standard single-file variant, OR
//   ltr/*.svg            — the multi-file variant directory layout (e.g.
//                          mai_en_fleur, sunset): every .svg in the dir holds a
//                          subset of GlyphLayer-* layers and the union is the
//                          font. Upstream (inkstitch lib/lettering/
//                          font_variant.py) globs the dir and dict-assigns
//                          glyphs per file, so on duplicate labels the LAST
//                          file wins (roman_ags_bicolor: zbi.svg's bicolor
//                          capitals override mono.svg's, which matches the
//                          font's own preview). We sort filenames for
//                          determinism where upstream trusts os.listdir.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
// Grid detection lives with the fill algorithm it serves (src/crossfill.js),
// so the importer and the renderer can never disagree about the lattice.
const crossfill = require("../src/crossfill.js");

const SRC = process.argv[2];
const OUT = process.argv[3];
if (!SRC || !OUT) { console.error("usage: build-font.mjs <fontDir|svgFile> <outJson>"); process.exit(1); }
const svgFile = SRC.endsWith(".svg") ? SRC : path.join(SRC, "ltr.svg");
const metaFile = SRC.endsWith(".svg") ? SRC.replace(/ltr\.svg$/, "font.json") : path.join(SRC, "font.json");
const licFile = SRC.endsWith(".svg") ? SRC.replace(/ltr\.svg$/, "LICENSE") : path.join(SRC, "LICENSE");
const ltrDir = SRC.endsWith(".svg") ? null : path.join(SRC, "ltr");
const dirLayout = !fs.existsSync(svgFile) && ltrDir && fs.existsSync(ltrDir) && fs.statSync(ltrDir).isDirectory();
const svgFiles = dirLayout
  ? fs.readdirSync(ltrDir).filter((f) => f.endsWith(".svg")).sort((a, b) => a.localeCompare(b)).map((f) => path.join(ltrDir, f))
  : [svgFile];
const meta = JSON.parse(fs.readFileSync(metaFile, "utf8"));
// FULL license text, verbatim — audit item 8 (docs/font-license-audit-
// 2026-07-31.md): the OFL requires the complete license + copyright notice
// to accompany every copy, and machine-readable metadata inside the binary
// is an explicitly blessed delivery channel. The old 4-LF-line truncation
// here is what produced the mid-sentence attribution fragments the audit
// flagged (and with bare-CR upstream files, "4 lines" was often the whole
// blob mangled into one).
const license = fs.existsSync(licFile) ? fs.readFileSync(licFile, "utf8").trim() : "";

// --- SVG path parser -> subpaths (polylines); flattens C/S/Q/T beziers and
// A arcs. S/T reflect the previous control point (tracked via px2/py2 + the
// last curve family); A uses the endpoint->center conversion from the SVG
// spec (F.6.5) and samples the swept angle. The ltr/-dir fonts are the first
// to exercise S/T/A — the old parser silently DROPPED those segments' tokens.
function parsePath(d) {
  const toks = d.match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [];
  let i = 0; const num = () => parseFloat(toks[i++]);
  const subs = []; let cur = null, cx = 0, cy = 0, sx = 0, sy = 0, cmd = "";
  let px2 = 0, py2 = 0, lastFam = ""; // reflection seed for S ("c") / T ("q")
  const FLAT = +(process.env.FLATTEN || 8);
  const bez = (x0, y0, x1, y1, x2, y2, x3, y3) => { const N = FLAT; for (let k = 1; k <= N; k++) { const t = k / N, u = 1 - t; cur.push({ x: u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3, y: u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3 }); } };
  const arc = (rx, ry, phiDeg, fa, fs, x2, y2) => {
    // SVG spec F.6.5 endpoint -> center parameterization, then angle sampling.
    if (rx === 0 || ry === 0) { cur.push({ x: x2, y: y2 }); return; }
    rx = Math.abs(rx); ry = Math.abs(ry);
    const phi = phiDeg * Math.PI / 180, cosP = Math.cos(phi), sinP = Math.sin(phi);
    const dx = (cx - x2) / 2, dy = (cy - y2) / 2;
    const x1p = cosP * dx + sinP * dy, y1p = -sinP * dx + cosP * dy;
    const lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry);
    if (lam > 1) { const s = Math.sqrt(lam); rx *= s; ry *= s; }
    let rad = (rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p) / (rx * rx * y1p * y1p + ry * ry * x1p * x1p);
    rad = rad < 0 ? 0 : Math.sqrt(rad); if (fa === fs) rad = -rad;
    const cxp = rad * rx * y1p / ry, cyp = -rad * ry * x1p / rx;
    const ccx = cosP * cxp - sinP * cyp + (cx + x2) / 2, ccy = sinP * cxp + cosP * cyp + (cy + y2) / 2;
    const ang = (ux, uy, vx, vy) => { const dot = ux * vx + uy * vy, len = Math.hypot(ux, uy) * Math.hypot(vx, vy); let a = Math.acos(Math.min(1, Math.max(-1, dot / len))); if (ux * vy - uy * vx < 0) a = -a; return a; };
    const th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry);
    let dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry);
    if (!fs && dth > 0) dth -= 2 * Math.PI; else if (fs && dth < 0) dth += 2 * Math.PI;
    const N = Math.max(2, Math.ceil(Math.abs(dth) / (Math.PI / FLAT)));
    for (let k = 1; k <= N; k++) { const t = th1 + dth * k / N; cur.push({ x: ccx + rx * Math.cos(t) * cosP - ry * Math.sin(t) * sinP, y: ccy + rx * Math.cos(t) * sinP + ry * Math.sin(t) * cosP }); }
    cur[cur.length - 1] = { x: x2, y: y2 }; // pin the exact endpoint
  };
  while (i < toks.length) {
    // ANCHORED. This test was /[a-zA-Z]/ — unanchored — so any token merely
    // CONTAINING a letter counted as a command, and SVG scientific notation
    // ("5.2e-4", which Inkscape emits for sub-micron offsets) contains an "e".
    // The damage was not a desync but a full stop: cmd became "5.2e-4", no
    // branch below matches it, and since following tokens are plain numbers
    // nothing ever reassigns cmd — so the parser consumed the rest of the path
    // one token at a time and emitted no further points. Every path was
    // silently TRUNCATED at its first scientific-notation number.
    // 119 of 132 upstream fonts contain such numbers. Found 2026-08-21 while
    // the cross-stitch glyphs came out as unrecognisable fragments; see
    // test/parsepath.test.js.
    // The tokenizer only ever yields single letters or numbers, so ^...$ is
    // the exact discriminator.
    if (/^[a-zA-Z]$/.test(toks[i])) cmd = toks[i++];
    const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase();
    let fam = "";
    if (C === "M") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; sx = cx; sy = cy; cur = [{ x: cx, y: cy }]; subs.push(cur); cmd = rel ? "l" : "L"; }
    else if (C === "L") { const x = num(), y = num(); cx = rel ? cx + x : x; cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "H") { const x = num(); cx = rel ? cx + x : x; cur.push({ x: cx, y: cy }); }
    else if (C === "V") { const y = num(); cy = rel ? cy + y : y; cur.push({ x: cx, y: cy }); }
    else if (C === "C") { const a = num(), b = num(), c = num(), d2 = num(), e = num(), f = num(); const X1 = rel ? cx + a : a, Y1 = rel ? cy + b : b, X2 = rel ? cx + c : c, Y2 = rel ? cy + d2 : d2, X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, X1, Y1, X2, Y2, X, Y); cx = X; cy = Y; px2 = X2; py2 = Y2; fam = "c"; }
    else if (C === "S") { const c = num(), d2 = num(), e = num(), f = num(); const X1 = lastFam === "c" ? 2 * cx - px2 : cx, Y1 = lastFam === "c" ? 2 * cy - py2 : cy; const X2 = rel ? cx + c : c, Y2 = rel ? cy + d2 : d2, X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, X1, Y1, X2, Y2, X, Y); cx = X; cy = Y; px2 = X2; py2 = Y2; fam = "c"; }
    else if (C === "Q") { const a = num(), b = num(), e = num(), f = num(); const X1 = rel ? cx + a : a, Y1 = rel ? cy + b : b, X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, cx + 2 / 3 * (X1 - cx), cy + 2 / 3 * (Y1 - cy), X + 2 / 3 * (X1 - X), Y + 2 / 3 * (Y1 - Y), X, Y); cx = X; cy = Y; px2 = X1; py2 = Y1; fam = "q"; }
    else if (C === "T") { const e = num(), f = num(); const X1 = lastFam === "q" ? 2 * cx - px2 : cx, Y1 = lastFam === "q" ? 2 * cy - py2 : cy; const X = rel ? cx + e : e, Y = rel ? cy + f : f; bez(cx, cy, cx + 2 / 3 * (X1 - cx), cy + 2 / 3 * (Y1 - cy), X + 2 / 3 * (X1 - X), Y + 2 / 3 * (Y1 - Y), X, Y); cx = X; cy = Y; px2 = X1; py2 = Y1; fam = "q"; }
    else if (C === "A") { const rx = num(), ry = num(), rot = num(), fa = num(), fs = num(), e = num(), f = num(); const X = rel ? cx + e : e, Y = rel ? cy + f : f; arc(rx, ry, rot, fa ? 1 : 0, fs ? 1 : 0, X, Y); cx = X; cy = Y; }
    else if (C === "Z") { if (cur) cur.push({ x: sx, y: sy }); cx = sx; cy = sy; }
    else i++;
    lastFam = fam;
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

// --- 2D affine transforms (SVG transform attribute) ---
// The single-file fonts ship with paths in final coordinates, but the ltr/-dir
// fonts position their art through nested <g transform="..."> (mai_en_fleur's
// flowers are one drawn motif re-placed via matrix() dozens of times per
// glyph) and per-path transforms — ignoring them scatters the geometry.
const M_ID = [1, 0, 0, 1, 0, 0]; // x' = a x + c y + e ; y' = b x + d y + f
const mmul = (A, B) => [
  A[0] * B[0] + A[2] * B[1], A[1] * B[0] + A[3] * B[1],
  A[0] * B[2] + A[2] * B[3], A[1] * B[2] + A[3] * B[3],
  A[0] * B[4] + A[2] * B[5] + A[4], A[1] * B[4] + A[3] * B[5] + A[5],
];
const mapply = (M, p) => ({ x: M[0] * p.x + M[2] * p.y + M[4], y: M[1] * p.x + M[3] * p.y + M[5] });
function parseTransform(str) {
  let M = M_ID;
  const re = /(matrix|translate|scale|rotate)\s*\(([^)]*)\)/g; let m;
  while ((m = re.exec(str || ""))) {
    const n = m[2].split(/[\s,]+/).filter(Boolean).map(Number);
    let T = null;
    if (m[1] === "matrix" && n.length === 6) T = n;
    else if (m[1] === "translate") T = [1, 0, 0, 1, n[0] || 0, n[1] || 0];
    else if (m[1] === "scale") T = [n[0] != null ? n[0] : 1, 0, 0, n.length > 1 ? n[1] : (n[0] != null ? n[0] : 1), 0, 0];
    else if (m[1] === "rotate") {
      const a = (n[0] || 0) * Math.PI / 180, cos = Math.cos(a), sin = Math.sin(a);
      T = [cos, sin, -sin, cos, 0, 0];
      if (n.length === 3) T = mmul(mmul([1, 0, 0, 1, n[1], n[2]], T), [1, 0, 0, 1, -n[1], -n[2]]);
    }
    if (T) M = mmul(M, T);
  }
  return M;
}

// Stitch parameters the DIGITIZER authored on a running-stitch path. We read
// these rather than picking our own, deliberately: stitch length and bean
// repeats are physical settings, and ROADMAP gate 1 bars this project from
// choosing physical constants without a sew-out. The font's author already
// made that call on real fabric, so their value travels with the glyph and a
// path that carries no value is simply never stitched (see runFrom below).
//
// Ink/Stitch allows a SPACE-SEPARATED LIST, applied per subpath in order
// (neon_blinking: running_stitch_length_mm="1.5 3.5", bean_stitch_repeats="0 3"
// — two subpaths, different treatment each). Index into the list by subpath;
// a shorter list reuses its last entry, which is Ink/Stitch's own behaviour.
function numList(t, attr) {
  const m = t.match(new RegExp('inkstitch:' + attr + '="([^"]*)"'));
  if (!m) return null;
  const vals = m[1].trim().split(/\s+/).map(Number).filter((n) => Number.isFinite(n));
  return vals.length ? vals : null;
}
function pick(list, i) {
  if (!list) return null;
  return list[Math.min(i, list.length - 1)];
}
function stitchParams(t) {
  const isCross = /inkstitch:fill_method="cross_stitch"/.test(t);
  const csm = t.match(/inkstitch:cross_stitch_method="([^"]*)"/);
  return {
    lens: numList(t, "running_stitch_length_mm"),
    // Ink/Stitch spells bean repeats two ways depending on version.
    beans: numList(t, "bean_stitch_repeats") || numList(t, "repeats"),
    // A cross-stitch path is a filled REGION, not a stroke: its outline is
    // pixel art on the digitizer's grid, and src/crossfill.js fills it with
    // crosses at layout time. Note we do NOT record pattern_size_mm — the same
    // "2.0" appears on fonts whose measured cell spans 0.78mm to 4.41mm, so it
    // cannot be a cell size. The grid is measured from the outlines instead.
    cross: isCross ? (csm ? csm[1] : "simple_cross") : null,
  };
}
// Build one run entry. With an authored length we emit the richer
// {pts, lenMm, repeats} shape the lettering path knows how to stitch; without
// one we emit the bare point array exactly as before.
//
// IMPORTANT: satin fonts carry authored running-stitch paths too (montecarlo
// 646, cats 837), which EMB-Bot has always dropped. Honouring them would add
// stitches to all 62 shipped fonts — a change to every existing customer
// design, and Kent's call, not this change's. So stripRunParamsIfSatin() below
// removes these params again for any font that has satin columns, keeping
// those fonts byte-identical on rebuild. Only genuinely runs-only fonts keep
// the params and become stitchable.
function runFrom(poly, sp, i) {
  const pts = enc(poly);
  // A cross-stitch region is tagged rather than given a stitch length: what
  // fills it is a grid of crosses, and the grid is derived font-wide below.
  if (sp && sp.cross) return { pts, fill: "cross", method: sp.cross };
  const lenMm = pick(sp && sp.lens, i);
  if (!(lenMm > 0)) return pts;
  const repeats = pick(sp && sp.beans, i);
  const out = { pts, lenMm: r1(lenMm) };
  if (repeats > 0) out.repeats = Math.round(repeats);
  return out;
}

// --- iterate every glyph layer ---
// THE path walk, for BOTH layouts. There used to be a second, simpler paths()
// that read `d` and ignored transforms entirely, used for every single-ltr.svg
// font; it was removed 2026-08-22 when that omission turned out to be
// destroying glyphs (see the call site). Do not reintroduce a non-transform
// -aware fast path: reading `d` alone is only correct for a glyph whose
// coordinates are baked in, and nothing about a font guarantees that.
//
// Walk the layer's g/path tags keeping a matrix stack (the glyph layer's OWN
// transform counts — sunset puts one on every layer), apply the composed
// transform to each path's points, and skip what Ink/Stitch itself never
// stitches:
//   - pattern-marker paths (marker*:url(#inkstitch-pattern-marker...)) — they
//     texture a satin column, they are not stitch geometry (mai_en_fleur has
//     ~17 per glyph; imported as runs they'd scribble over the flowers);
//   - display:none paths — lettering command connectors (sunset's "Position
//     de fin" groups) are hidden hairlines, not stitches.
// Satin detection and toColumn() downstream are unchanged — this function only
// decides which coordinates the columns see.
function pathsTf(layer) {
  const out = []; const re = /<\/?(?:g|path)\b[\s\S]*?>/g; let m;
  const stack = [M_ID];
  while ((m = re.exec(layer))) {
    const t = m[0];
    if (t[1] === "/") { if (stack.length > 1) stack.pop(); continue; }
    const selfClosed = /\/>$/.test(t);
    const tfm = t.match(/\stransform="([^"]*)"/);
    const M = tfm ? mmul(stack[stack.length - 1], parseTransform(tfm[1])) : stack[stack.length - 1];
    if (/^<g\b/.test(t)) { if (!selfClosed) stack.push(M); continue; }
    const dq = t.match(/\sd="([^"]*)"/); if (!dq) continue;
    if (/marker-(?:start|mid|end)\s*:\s*url\(#inkstitch-pattern-marker/i.test(t)) continue;
    if (/style="[^"]*display\s*:\s*none/i.test(t)) continue;
    out.push({
      subs: parsePath(dq[1]).map((sub) => sub.map((p) => mapply(M, p))),
      satin: /satin_column="True"/i.test(t),
      sp: stitchParams(t),
    });
  }
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
for (const file of svgFiles) {
  const svg = fs.readFileSync(file, "utf8");
  const re = /inkscape:label="GlyphLayer-([\s\S]*?)"/g; let m;
  while ((m = re.exec(svg))) {
    const ch = decodeEntities(m[1]);
    const g0 = svg.lastIndexOf("<g", m.index);
    let depth = 0; const gre = /<\/?g\b/g; gre.lastIndex = g0; let gm, end = -1;
    while ((gm = gre.exec(svg))) { if (svg[gm.index + 1] === "/") { depth--; if (depth === 0) { end = gm.index; break; } } else depth++; }
    if (end < 0) continue;
    const layer = svg.slice(g0, end);
    const cols = [], runs = [];
    // ALWAYS the transform-aware walk, both layouts (2026-08-22). This was
    // gated on dirLayout, so every single-`ltr.svg` font — most of the library
    // — went through paths(), which ignores transforms outright.
    //
    // That is fine for a glyph whose coordinates are baked into its `d`, and
    // catastrophic for one that places repeated geometry BY transform.
    // mimosa_large is a dot-matrix face and does both: its "A" carries 38
    // distinct `d` values and no transforms and imports perfectly, while its
    // "D" carries ONE `d` — a single dot — repeated 38 times with 38 different
    // transforms. Dropping those stacked all 38 dots on one spot, so "D" sewed
    // 6,193 stitches into 40.0 x 0.0 mm against a healthy glyph's 996 in
    // 40.0 x 60.1 mm: a needle hammering one line thousands of times.
    //
    // pathsTf was already documented as "IDENTICAL downstream — this function
    // only changes which coordinates the columns see", so this is the narrow
    // fix. It also picks up two behaviours paths() lacked and Ink/Stitch itself
    // has: pattern-marker paths and display:none paths are skipped. Note the
    // display:none check applies to PATH tags only — glyph LAYERS are routinely
    // display:none (164 of mimosa_large's 165 are; Inkscape shows one at a
    // time), and skipping those would empty the library.
    for (const p of pathsTf(layer)) {
      if (p.satin && p.subs.length >= 2) cols.push(toColumn(p.subs));
      else if (p.subs.length) p.subs.forEach((s, i) => runs.push(runFrom(s, p.sp, i)));
    }
    if (!cols.length && !runs.length) continue;
    let advance = (meta.horiz_adv_x && meta.horiz_adv_x[ch] != null) ? meta.horiz_adv_x[ch] : meta.horiz_adv_x_default;
    if (advance == null) {
      // Font provides no metrics (e.g. medium_font) — derive advance from the
      // glyph's right edge + a side bearing, so glyphs don't collapse onto x=0.
      let maxX = -Infinity;
      for (const c of cols) { for (const p of c.railA) if (p[0] > maxX) maxX = p[0]; for (const p of c.railB) if (p[0] > maxX) maxX = p[0]; }
      // runs are either a bare point array or {pts, lenMm, ...} — see runFrom.
      for (const rr of runs) for (const p of (rr.pts || rr)) if (p[0] > maxX) maxX = p[0];
      advance = isFinite(maxX) ? Math.round(maxX + 0.08 * meta.units_per_em) : meta.units_per_em;
    }
    glyphs[ch] = { adv: advance, cols, runs }; // duplicate label => later file wins
  }
}
// See runFrom: honouring authored run params on a font that ALSO has satin
// columns would add stitches to every already-shipped satin font. Scope this
// change to runs-only fonts by stripping the params back off anything satin,
// which makes those fonts rebuild byte-identically (asserted by
// test/run-fonts.test.js against the committed .embf set). Revisit only as a
// deliberate decision to enrich the satin fonts, with a rebuild of all of them.
(function stripRunParamsIfSatin() {
  let hasSatin = false;
  for (const g of Object.values(glyphs)) if ((g.cols || []).length) { hasSatin = true; break; }
  if (!hasSatin) return;
  for (const g of Object.values(glyphs)) {
    if (!g.runs) continue;
    g.runs = g.runs.map((r) => (r && r.pts ? r.pts : r));
  }
})();

// Cross-stitch fonts: recover the digitizer's drawing grid ONCE for the whole
// font, from every glyph outline at once. Font-wide rather than per-glyph on
// purpose — a shared lattice is what makes crosses line up across letters, and
// a sparse glyph like "." has too few edges to solve a phase from. Expressed in
// glyph units, so it scales with the letterform and states nothing about
// millimetres (ROADMAP gate 1). See src/crossfill.js.
const crossGrid = (function detectCrossGrid() {
  let method = null;
  const rings = [];
  for (const g of Object.values(glyphs)) {
    for (const r of (g.runs || [])) {
      if (!r || r.fill !== "cross" || !Array.isArray(r.pts)) continue;
      method = method || r.method;
      if (r.pts.length > 2) rings.push(r.pts);
    }
  }
  if (!rings.length) return null;
  const lat = crossfill.detectLattice(rings);
  if (!lat || !(lat.step > 0)) {
    console.warn("cross-stitch font but no grid could be measured — fills will be skipped");
    return null;
  }
  // A poor fit means these outlines are not the pixel art this assumes, and a
  // guessed grid would fill the glyph with crosses in the wrong places. Refuse
  // rather than emit plausible-looking nonsense.
  if (lat.fit < 0.9) {
    console.warn(`cross-stitch grid fit only ${(lat.fit * 100).toFixed(1)}% — refusing to guess; fills skipped`);
    return null;
  }
  return { step: r1(lat.step), offX: r1(lat.offX), offY: r1(lat.offY), method: method || "simple_cross" };
})();
if (crossGrid) console.error(`  cross-stitch grid: step=${crossGrid.step} method=${crossGrid.method}`);

const count = Object.keys(glyphs).length;

const outObj = {
  name: meta.name, license, source: "Ink/Stitch embroidery-fonts",
  unitsPerEm: meta.units_per_em, sizeMm: meta.size, leading: meta.leading,
  advDefault: meta.horiz_adv_x_default != null ? meta.horiz_adv_x_default : Math.round(0.55 * meta.units_per_em),
  advSpace: meta.horiz_adv_x_space != null ? meta.horiz_adv_x_space : Math.round(0.3 * meta.units_per_em),
  kerning: meta.kerning_pairs || {}, glyphCount: count, glyphs,
  ...(crossGrid ? { crossGrid } : {}),
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(outObj));
console.log(JSON.stringify({ name: meta.name, glyphs: count, bytes: fs.statSync(OUT).size, sample: Object.keys(glyphs).slice(0, 20) }));
