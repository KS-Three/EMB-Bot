// "Join touching strokes" (pen + auto-branch spec 2026-11-13 §3 and §4): the
// instrument. A joined group promises no jump, no trim and no bare travel
// inside it; the third is the one a green suite can hide, so it is measured
// here on the stitches as emitted, not assumed from how the router is built.
//
//   node tools/join-strokes.mjs                 the table, joined beside unjoined
//   node tools/join-strokes.mjs --svg out.svg   + a sheet of every fixture
//
// test/join-strokes.test.js imports FIXTURES, build and measure from here.
//
// EXPOSED TRAVEL. Inside a group, every stitch that is not a satin cross
// (an underpath, an underlay pass, the needle-down step from one span to the
// next) is walked at one DST unit (0.1 mm), and each point is asked: is it
// inside the body of a satin span sewn AFTER it? A span's body is the strip
// its own stitches sweep: for each four stitches in a row (two crosses), the
// quad they bound. (Not "even stitches one rail, odd the other": the zigzag
// leads with the other rail on every second cross, and a polygon built on that
// parity crosses itself. The first build of this file did that; caught in
// review, 2026-11-14. And not each THREE in a row: those triangles leave a
// gap at alternate rails that pinches to the centre line, where the travel
// runs.) A point within EDGE_TOL_MM of the strip
// counts as inside: the needle lands on a 0.1 mm grid, so a point ON a rail is
// up to that far out of the rounded strip.
// What is left is `exposedMm`: thread no LATER satin covers. Of that,
// `bareMm` is under no satin of the group at all, earlier or later: thread on
// bare cloth. The rest lies on top of satin already sewn.
import "./_help.mjs";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DG = require(path.join(ROOT, "src", "digitize.js"));
const SF = require(path.join(ROOT, "src", "satinfont.js"));
const FAB = require(path.join(ROOT, "src", "fabrics.js"));
const MS = await import(pathToFileURL(path.join(ROOT, "app", "src", "lib", "manualShapes.js")).href);

export const EDGE_TOL_MM = 0.1;
const U = 10;   // DST units per mm

const P = (x, y) => ({ x, y });
const col = (id, pts, widthPx, rgb) => ({ id, kind: "column", points: pts, curves: {}, widthPx, colorRgb: rgb || [20, 20, 20] });
// A circle as two half-ring strokes meeting at its top and bottom.
function arc(cx, cy, r, a0, a1, n) {
  const pts = [];
  for (let i = 0; i <= n; i++) { const a = a0 + (a1 - a0) * (i / n); pts.push(P(cx + r * Math.cos(a), cy + r * Math.sin(a))); }
  return pts;
}

// Each fixture: (widthPx) -> { shapes, groups: [[ids of one expected group]] }.
// Authored canvas px, 6 to the mm, the manual lane's own frame.
export const FIXTURES = {
  T: (w) => ({
    shapes: [col("s1", [P(100, 100), P(400, 100)], w), col("s2", [P(250, 100), P(250, 300)], w)],
    groups: [["s1", "s2"]],
  }),
  X: (w) => ({
    shapes: [col("s1", [P(100, 100), P(400, 300)], w), col("s2", [P(100, 300), P(400, 100)], w)],
    groups: [["s1", "s2"]],
  }),
  Y: (w) => ({
    shapes: [col("s1", [P(250, 320), P(250, 200)], w), col("s2", [P(250, 200), P(150, 100)], w), col("s3", [P(250, 200), P(350, 100)], w)],
    groups: [["s1", "s2", "s3"]],
  }),
  "loop + stem": (w) => ({
    shapes: [
      col("s1", arc(250, 150, 80, Math.PI / 2, Math.PI * 1.5, 12), w),
      col("s2", arc(250, 150, 80, -Math.PI / 2, Math.PI / 2, 12), w),
      col("s3", [P(250, 230), P(250, 360)], w),
    ],
    groups: [["s1", "s2", "s3"]],
  }),
  "two sets": (w) => ({
    shapes: [
      col("s1", [P(100, 100), P(220, 100)], w), col("s2", [P(220, 100), P(220, 220)], w),
      col("s3", [P(380, 240), P(500, 240)], w), col("s4", [P(500, 240), P(500, 360)], w),
    ],
    groups: [["s1", "s2"], ["s3", "s4"]],
  }),
};
export const WIDTHS_MM = [1, 4];

// The Studio's manual branch (app/src/lib/generate.js), option for option,
// at the drawing's own scale: one mm of thread per PX_PER_MM canvas px.
export function build(shapes, join, extra) {
  const { regions, pxPerMm } = MS.shapesToRegions(shapes, join ? { joinStrokes: true, joinComponents: SF.joinComponents } : undefined);
  let x0 = Infinity, x1 = -Infinity;
  for (const r of regions) for (const s of r.shapes) for (const p of s.outer) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; }
  const design = DG.buildQualityDesign(regions, Object.assign({
    garment: { widthIn: 8, heightIn: 8 }, fabric: FAB.getFabric("pique_knit"), pxPerMm,
    darkOnTop: false, fillColumns: true, cutFloats: true, underlay: true,
    targetWidthMm: (x1 - x0) / pxPerMm,
  }, extra || {}));
  return { regions, design };
}

function distToSeg(px, py, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy;
  const t = L2 ? Math.max(0, Math.min(1, ((px - a.x) * dx + (py - a.y) * dy) / L2)) : 0;
  return Math.hypot(px - (a.x + t * dx), py - (a.y + t * dy));
}
const side = (px, py, a, b) => (b.x - a.x) * (py - a.y) - (b.y - a.y) * (px - a.x);
function under(px, py, body, tol) {
  if (px < body.x0 - tol || px > body.x1 + tol || py < body.y0 - tol || py > body.y1 + tol) return false;
  const q = body.pts;
  const inTri = (a, b, c) => {
    const s1 = side(px, py, a, b), s2 = side(px, py, b, c), s3 = side(px, py, c, a);
    return (s1 >= 0 && s2 >= 0 && s3 >= 0) || (s1 <= 0 && s2 <= 0 && s3 <= 0);
  };
  for (let i = 0; i + 1 < q.length; i++) {
    const a = q[i], b = q[i + 1], c = q[i + 2], d = q[i + 3];
    if (distToSeg(px, py, a, b) <= tol) return true;
    if (c && inTri(a, b, c)) return true;
    if (d && (inTri(a, b, d) || inTri(a, c, d) || inTri(b, c, d))) return true;
  }
  return false;
}

// One group of a built design. ids: its members' shape ids.
// -> { stitches, satinSpans, jumps, trims, travelMm, exposedMm, bareMm, exposed: [[x, y] DST units] }
export function measure(design, ids) {
  const want = new Set(ids.map(String));
  const st = design.stitches, spans = (design.runs || []).filter((sp) => want.has(sp.shape));
  if (!spans.length) return { stitches: 0, satinSpans: 0, jumps: 0, trims: 0, travelMm: 0, exposedMm: 0, bareMm: 0, exposed: [] };
  const lo = Math.min(...spans.map((sp) => sp.i0)), hi = Math.max(...spans.map((sp) => sp.i1));
  const satinOf = new Array(st.length).fill(-1);
  const bodies = [];
  for (const sp of spans) {
    if (sp.kind !== "satin") continue;
    const pts = [];
    for (let i = sp.i0; i <= sp.i1; i++) { satinOf[i] = bodies.length; if (st[i].type === "stitch") pts.push(st[i]); }
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of pts) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
    bodies.push({ i0: sp.i0, pts, x0, y0, x1, y1 });
  }
  const tol = EDGE_TOL_MM * U;
  let jumps = 0, trims = 0, stitches = 0, travel = 0, open = 0, bare = 0;
  const exposed = [];
  for (let i = lo; i <= hi; i++) {
    const s = st[i];
    if (s.type === "jump") jumps++;
    else if (s.type === "trim") trims++;
    else if (s.type === "stitch") stitches++;
    if (i === lo || s.type !== "stitch" || st[i - 1].type !== "stitch") continue;
    if (satinOf[i] >= 0 && satinOf[i] === satinOf[i - 1]) continue;   // a satin cross
    const p = st[i - 1], len = Math.hypot(s.x - p.x, s.y - p.y);
    if (!(len > 0)) continue;
    travel += len;
    const later = bodies.filter((b) => b.i0 >= i);
    const n = Math.max(1, Math.ceil(len));
    for (let k = 0; k < n; k++) {
      const t = (k + 0.5) / n, x = p.x + (s.x - p.x) * t, y = p.y + (s.y - p.y) * t;
      if (later.some((b) => under(x, y, b, tol))) continue;
      open += len / n; exposed.push([x, y]);
      if (!bodies.some((b) => under(x, y, b, tol))) bare += len / n;
    }
  }
  return { stitches, satinSpans: bodies.length, jumps, trims, travelMm: travel / U, exposedMm: open / U, bareMm: bare / U, exposed };
}

// Whole-design counts, for joined beside unjoined.
export function totals(design) {
  let trims = 0, jumps = 0, colors = 0;
  for (const s of design.stitches) { if (s.type === "trim") trims++; else if (s.type === "jump") jumps++; else if (s.type === "color") colors++; }
  return { stitches: design.stitchCount, trims, jumps, colorStops: colors };
}

function svgOf(design, exposed) {
  const st = design.stitches, kindOf = new Array(st.length).fill("");
  for (const sp of design.runs || []) for (let i = sp.i0; i <= sp.i1; i++) kindOf[i] = sp.kind;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const s of st) { if (s.type === "end") continue; if (s.x < x0) x0 = s.x; if (s.x > x1) x1 = s.x; if (s.y < y0) y0 = s.y; if (s.y > y1) y1 = s.y; }
  const paint = { satin: ["#1a1a1a", 0.6], travel: ["#d4380d", 1.2], underlay: ["#1d6fd6", 0.9], "": ["#1a1a1a", 0.6] };
  const lines = [];
  for (let i = 1; i < st.length; i++) {
    const p = st[i - 1], s = st[i];
    if (s.type === "end" || s.type === "color" || s.type === "trim") continue;
    if (s.type === "jump") { if (p.x !== s.x || p.y !== s.y) lines.push(`<line x1="${p.x}" y1="${-p.y}" x2="${s.x}" y2="${-s.y}" stroke="#2f9e44" stroke-width="1.2" stroke-dasharray="4 3"/>`); continue; }
    if (p.type === "end") continue;
    const same = kindOf[i] === "satin" && kindOf[i - 1] === "satin";
    const [c, w] = same ? paint.satin : (paint[kindOf[i] === "satin" ? "travel" : kindOf[i]] || paint[""]);
    lines.push(`<line x1="${p.x}" y1="${-p.y}" x2="${s.x}" y2="${-s.y}" stroke="${c}" stroke-width="${w}"/>`);
  }
  for (const [x, y] of exposed || []) lines.push(`<circle cx="${x}" cy="${-y}" r="2.5" fill="none" stroke="#e8590c" stroke-width="1"/>`);
  for (let i = 0; i < st.length; i++) if (st[i].type === "trim") lines.push(`<path d="M${st[i].x - 5} ${-st[i].y - 5}l10 10m0 -10l-10 10" stroke="#2f9e44" stroke-width="1.5"/>`);
  return { body: lines.join(""), x0, y0: -y1, w: x1 - x0, h: y1 - y0 };
}

function rows() {
  const out = [];
  for (const [name, make] of Object.entries(FIXTURES)) {
    for (const mm of WIDTHS_MM) {
      const fx = make(mm * MS.PX_PER_MM);
      const off = build(fx.shapes, false), on = build(fx.shapes, true);
      const groups = fx.groups.map((ids) => measure(on.design, ids));
      out.push({ name, mm, fx, off, on, groups, tOff: totals(off.design), tOn: totals(on.design) });
    }
  }
  return out;
}

function main(argv) {
  const all = rows();
  console.log("| fixture | width mm | stitches off -> on | trims off -> on | colour stops off -> on | jumps + trims in group | travel mm | exposed mm | on bare cloth mm |");
  console.log("|---|---|---|---|---|---|---|---|---|");
  for (const r of all) {
    const g = r.groups;
    console.log(`| ${r.name} | ${r.mm} | ${r.tOff.stitches} -> ${r.tOn.stitches} | ${r.tOff.trims} -> ${r.tOn.trims} | ${r.tOff.colorStops} -> ${r.tOn.colorStops} | ${g.map((m) => m.jumps + m.trims).join(", ")} | ${g.map((m) => m.travelMm.toFixed(1)).join(", ")} | ${g.map((m) => m.exposedMm.toFixed(2)).join(", ")} | ${g.map((m) => m.bareMm.toFixed(2)).join(", ")} |`);
  }
  const at = argv.indexOf("--svg");
  if (at >= 0 && argv[at + 1]) {
    const cellW = 520, cellH = 400, pad = 30;
    let y = 0; const parts = [];
    for (const r of all) {
      const exposed = r.groups.flatMap((m) => m.exposed);
      [[r.off.design, [], "as drawn"], [r.on.design, exposed, "joined"]].forEach(([d, ex, label], k) => {
        const s = svgOf(d, ex), sc = Math.min((cellW - 2 * pad) / Math.max(1, s.w), (cellH - 2 * pad - 20) / Math.max(1, s.h));
        const t = totals(d);
        parts.push(`<text x="${k * cellW + pad}" y="${y + 22}" font-family="sans-serif" font-size="14">${r.name}, ${r.mm} mm, ${label}: ${t.stitches} stitches, ${t.trims} trims, ${t.colorStops} colour stops</text>`);
        parts.push(`<g transform="translate(${k * cellW + pad},${y + pad + 10}) scale(${sc}) translate(${-s.x0},${-s.y0})">${s.body}</g>`);
      });
      y += cellH;
    }
    const legend = `<text x="${pad}" y="${y + 20}" font-family="sans-serif" font-size="13">black: satin. red: travel sewn needle down (underpath, step between spans). blue: underlay. green dashes: a jump; green cross: a trim. orange ring: travel no later satin covers.</text>`;
    fs.writeFileSync(argv[at + 1], `<svg xmlns="http://www.w3.org/2000/svg" width="${2 * cellW}" height="${y + 40}" viewBox="0 0 ${2 * cellW} ${y + 40}"><rect width="100%" height="100%" fill="#fff"/>${parts.join("")}${legend}</svg>`);
    console.log("\nsheet: " + argv[at + 1]);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2));
