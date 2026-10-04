// What `fillStagger: true` does to a shape's cover fill, measured on the points
// the fill module hands the builder: how many needle holes stand in line with
// a hole of the next row (and of the row after that), what the stagger costs
// in stitches, and how short a stitch it makes. Prints the tables
// docs/fill-stagger-2026-10-03.md carries; with --sheet it draws the holes.
//
//   node tools/fill-stagger-census.mjs [srcDir] [--sheet out.svg]
//
// srcDir: the engine to measure (default: this checkout's src).
//
// A HOLE is a needle penetration BETWEEN the two ends of a row. The ends are
// the shape's edge and stand in line wherever the edge is straight; that is
// the edge, not a channel. The rows are cut here, by this file's own scanline,
// from the rings the builder gave the fill -- not read back from the engine.
//
// IN LINE is within 0.3 mm along the row. A hole "with one under it" has a
// hole of the next row that near; "three in a line" has one on each of the
// next two rows. The second is the one to read: a long step cut in half lands
// near the next row's grid point by the rule itself, once, and goes no further.
import { writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const sheetAt = args.indexOf("--sheet");
const SHEET = sheetAt >= 0 ? resolve(args[sheetAt + 1]) : null;
if (sheetAt >= 0) args.splice(sheetAt, 2);
const SRC = resolve(args[0] || join(ROOT, "src"));
const DG = require(join(SRC, "digitize.js"));
const FAB = require(join(SRC, "fabrics.js"));
const FILL = require(join(SRC, "fill.js"));

const MAX_STITCH_MM = 4, NEAR_MM = 0.3;
const turned = (p, deg) => {
  const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
  return { x: p.x * c - p.y * s, y: p.x * s + p.y * c };
};
// One cover pass -> its rows, each span with the holes between its ends, in
// the rows' own frame and in mm.
function rowsOf(pass) {
  const { polys, opts, pts } = pass, pitch = opts.rowSpacing, angleDeg = opts.angleDeg || 0;
  const perMm = opts.maxStitch / MAX_STITCH_MM, eps = 1e-6 * perMm;
  const rings = polys.map((ring) => ring.map((p) => turned(p, -angleDeg)));
  let minY = Infinity, maxY = -Infinity;
  for (const ring of rings) for (const p of ring) { minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  const rows = [];
  for (let y = minY; y <= maxY + 1e-9; y += pitch) {
    const xs = [];
    for (const ring of rings) for (let i = 0; i < ring.length; i++) {
      const u = ring[i], v = ring[(i + 1) % ring.length];
      if (u.y === v.y) continue;
      if (y >= Math.min(u.y, v.y) && y < Math.max(u.y, v.y)) xs.push(u.x + ((y - u.y) / (v.y - u.y)) * (v.x - u.x));
    }
    xs.sort((p, q) => p - q);
    const spans = [];
    for (let i = 0; i + 1 < xs.length; i += 2) spans.push({ x0: xs[i], x1: xs[i + 1], holes: [] });
    rows.push({ y, spans });
  }
  for (const p of pts) {
    if (p.travel || p.trim) continue;
    const q = turned(p, -angleDeg), k = (q.y - minY) / pitch, ri = Math.round(k);
    if (Math.abs(k - ri) * pitch > eps || !rows[ri]) continue;
    const span = rows[ri].spans.find((s) => q.x > s.x0 + eps && q.x < s.x1 - eps);
    if (span) span.holes.push(q.x);
  }
  for (const row of rows) {
    for (const s of row.spans) { s.holes.sort((p, q) => p - q); s.x0 /= perMm; s.x1 /= perMm; s.holes = s.holes.map((x) => x / perMm); }
    row.y /= perMm;
    row.holes = [].concat(...row.spans.map((s) => s.holes));
  }
  return rows;
}
function measure(passes) {
  // `fromEnd`: for each hole with one under it, how far it is from the nearer
  // end of its own row. `rows`: the scanlines with thread on them.
  const m = { holes: 0, pairs: 0, threes: 0, steps: 0, shortest: Infinity, longest: 0, under2: 0, spans: 0, rows: 0, fromEnd: [] };
  for (const pass of passes) {
    const rows = rowsOf(pass);
    for (let ri = 0; ri < rows.length; ri++) {
      m.spans += rows[ri].spans.length;
      if (rows[ri].spans.length) m.rows++;
      const next = ri + 1 < rows.length ? rows[ri + 1].holes : [], after = ri + 2 < rows.length ? rows[ri + 2].holes : [];
      for (const s of rows[ri].spans) for (const h of s.holes) {
        m.holes++;
        if (!next.some((g) => Math.abs(g - h) <= NEAR_MM)) continue;
        m.pairs++;
        m.fromEnd.push(Math.min(h - s.x0, s.x1 - h));
        if (after.some((g) => Math.abs(g - h) <= NEAR_MM)) m.threes++;
      }
      // the stitches along the row: only rows the stagger has a say in
      for (const s of rows[ri].spans) {
        if (!s.holes.length) continue;
        const seq = [s.x0].concat(s.holes, [s.x1]);
        for (let k = 1; k < seq.length; k++) {
          const d = seq[k] - seq[k - 1];
          m.steps++;
          if (d < 2 - 1e-9) m.under2++;
          m.shortest = Math.min(m.shortest, d);
          m.longest = Math.max(m.longest, d);
        }
      }
    }
  }
  return m;
}
// Build, and keep every cover pass the builder asks the fill module for. The
// builder looks `tatamiFill` up when it calls it; the cover pass is the one
// that is told whether to sew center-out. (With `fillColumns` the builder
// also ASKS whether the cover is the plain walk's, `plainOnly`: an answer of
// null is no pass.)
function build(regions, widthMm, fabricId, extra) {
  const real = FILL.tatamiFill, cover = [];
  FILL.tatamiFill = (polys, opts) => {
    const pts = real(polys, opts);
    if (pts && "centerOut" in opts) cover.push({ polys, opts, pts });
    return pts;
  };
  try {
    const design = DG.buildQualityDesign(JSON.parse(JSON.stringify(regions)),
      { garment: { id: "left_chest", widthIn: 6, heightIn: 6 }, fabric: fabricId ? FAB.getFabric(fabricId) : null,
        pxPerMm: PX, targetWidthMm: widthMm, maxStitchMm: MAX_STITCH_MM, darkOnTop: false, underlay: true, ...extra });
    return { design, cover };
  } finally { FILL.tatamiFill = real; }
}

const PX = 10;
const mm = (pts) => pts.map(([x, y]) => ({ x: x * PX, y: y * PX }));
const box = (x0, y0, x1, y1) => mm([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
const round = (cx, cy, r, n = 48) => mm(Array.from({ length: n }, (_, i) => [cx + r * Math.cos((2 * Math.PI * i) / n), cy + r * Math.sin((2 * Math.PI * i) / n)]));
const star = (cx, cy, r, n = 5) => mm(Array.from({ length: 2 * n }, (_, i) => {
  const rr = i % 2 ? r * 0.45 : r, a = (Math.PI * i) / n - Math.PI / 2;
  return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
}));
const fill = (outer, holes) => ({ outer, holes: holes || [], tierOverride: "fill" });
const one = (shape) => [{ rgb: [27, 58, 92], shapes: [shape] }];
const holes36 = [];
for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) holes36.push(box(6 + c * 9, 6 + r * 9, 10 + c * 9, 10 + r * 9));
// Sizes in mm.
const DESIGNS = [
  ["Square, 40 mm", 40, one(fill(box(0, 0, 40, 40)))],
  ["Bar, 40 x 8 mm", 40, one(fill(box(0, 0, 40, 8)))],
  ["Circle, 30 mm", 30, one(fill(round(15, 15, 15)))],
  ["Star, 40 mm", 38, one(fill(star(20, 20, 20)))],
  ["Triangle, 10 mm", 10, one(fill(mm([[0, 10], [5, 0], [10, 10]])))],
  ["Badge, two cut-outs, 40 mm", 40, one(fill(box(0, 0, 40, 40), [box(6, 14, 18, 26), box(28.5, 18.5, 31.5, 21.5)]))],
  ["Ring (an O), 40 mm", 40, one(fill(round(20, 20, 20, 64), [round(20, 20, 11)]))],
  ["Badge, 36 holes, 60 mm", 60, one(fill(box(0, 0, 60, 60), holes36))],
  ["Three squares apart, one colour", 100, [{ rgb: [27, 58, 92], shapes: [fill(box(0, 0, 20, 20)), fill(box(40, 0, 60, 20)), fill(box(80, 0, 100, 20))] }]],
  ["Twelve 6 mm dots, one colour", 51, [{ rgb: [27, 58, 92], shapes: Array.from({ length: 12 }, (_, i) => fill(round(3 + (i % 4) * 15, 3 + Math.floor(i / 4) * 15, 3, 20))) }]],
];
const PIQUE = FAB.fabricForGarment("left_chest");
const share = (a, b) => (b ? ((100 * a) / b).toFixed(1) + "%" : "-");
const more = (on, off) => (on >= off ? "+" : "") + ((on / off - 1) * 100).toFixed(2) + "%";
const mmOf = (x) => (isFinite(x) ? x.toFixed(2) : "-");
const count = (d, k) => d.stitches.filter((s) => s.type === k).length;

console.log("\nLeft chest, the pique preset, underlay on, `fillColumns` off. A hole is a penetration between a row's ends:\n");
console.log("| design | holes | with one under it: off | on | three in a line: off | on | stitches off | on | more |");
console.log("|---|---|---|---|---|---|---|---|---|");
for (const [name, widthMm, regions] of DESIGNS) {
  const off = build(regions, widthMm, PIQUE), on = build(regions, widthMm, PIQUE, { fillStagger: true });
  const a = measure(off.cover), b = measure(on.cover);
  console.log(`| ${name} | ${a.holes.toLocaleString()} | ${share(a.pairs, a.holes)} | ${share(b.pairs, b.holes)} | ${share(a.threes, a.holes)} | ${share(b.threes, b.holes)} | ${off.design.stitchCount.toLocaleString()} | ${on.design.stitchCount.toLocaleString()} | ${more(on.design.stitchCount, off.design.stitchCount)} |`);
}

console.log("\nEvery design above under every preset (and none), by walk:\n");
console.log("| `fillColumns` | builds | holes off | on | with one under it: off | on | three in a line: off | on | stitches | stitches a row: off | on | cuts off | on | shortest stitch along a row: off | on | under 2 mm: off | on |");
console.log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
const presets = [null].concat(FAB.FABRICS.map((f) => f.id));
for (const fillColumns of [false, true]) {
  const tot = { builds: 0, sOff: 0, sOn: 0, cOff: 0, cOn: 0 }, A = [], B = [];
  for (const fabricId of presets) for (const [, widthMm, regions] of DESIGNS) {
    const off = build(regions, widthMm, fabricId, { fillColumns }), on = build(regions, widthMm, fabricId, { fillColumns, fillStagger: true });
    A.push(...off.cover); B.push(...on.cover);
    tot.builds++; tot.sOff += off.design.stitchCount; tot.sOn += on.design.stitchCount;
    tot.cOff += count(off.design, "trim"); tot.cOn += count(on.design, "trim");
    if (off.design.widthMM !== on.design.widthMM || off.design.heightMM !== on.design.heightMM) throw new Error("the stagger moved the design's edge");
  }
  const a = measure(A), b = measure(B);
  const aRow = ((a.holes + a.spans) / a.spans).toFixed(2), bRow = ((b.holes + b.spans) / b.spans).toFixed(2);
  console.log(`| ${fillColumns ? "on" : "off"} | ${tot.builds} | ${a.holes.toLocaleString()} | ${b.holes.toLocaleString()} | ${share(a.pairs, a.holes)} | ${share(b.pairs, b.holes)} | ${share(a.threes, a.holes)} | ${share(b.threes, b.holes)} (${b.threes}) | ${more(tot.sOn, tot.sOff)} | ${aRow} | ${bRow} | ${tot.cOff} | ${tot.cOn} | ${mmOf(a.shortest)} mm | ${mmOf(b.shortest)} mm | ${share(a.under2, a.steps)} | ${share(b.under2, b.steps)} |`);
}

// ---- what is left: the holes that still have one under them ---------------
// A first or last step longer than a stitch is cut in half, and the half lands
// by the next row's first grid hole. Along a straight edge that is the same
// place every cycle: a pair of holes every four rows, a line of dashes beside
// the edge.
{
  const B = [];
  for (const fabricId of presets) for (const [, widthMm, regions] of DESIGNS) B.push(...build(regions, widthMm, fabricId, { fillStagger: true }).cover);
  const b = measure(B), near = b.fromEnd.filter((d) => d >= 1.5 && d <= 2.6).length;
  console.log(`\nStaggered, the holes that still have one under them: ${b.pairs.toLocaleString()}. ${share(near, b.pairs)} of them are 1.5 to 2.6 mm from an end of their own row.`);
  console.log("\nOne 40 mm square, by preset. A pair is a hole with one under it:\n");
  console.log("| preset | rows | pairs | rows to a pair | from the nearer edge, median |");
  console.log("|---|---|---|---|---|");
  for (const fabricId of presets) {
    const s = measure(build(DESIGNS[0][2], DESIGNS[0][1], fabricId, { fillStagger: true }).cover);
    const mid = s.fromEnd.slice().sort((p, q) => p - q)[Math.floor(s.fromEnd.length / 2)];
    console.log(`| ${fabricId || "none"} | ${s.rows} | ${s.pairs} | ${s.pairs ? (s.rows / s.pairs).toFixed(1) : "-"} | ${s.pairs ? mmOf(mid) + " mm" : "-"} |`);
  }
}

// ---- the picture ----------------------------------------------------------
// The holes of a patch of fill, off and on, at 16x: one dot a penetration, one
// faint line a row. Rows are drawn 0.4 mm apart so that they can be told apart
// (the engine's own are 0.15 mm, and at that pitch the dots of four rows touch).
if (SHEET) {
  const Z = 16, patches = [
    ["Rectangle, rows across", [box(0, 0, 30, 9)], 0],
    ["The same, rows at 30 degrees", [box(0, 0, 30, 9)], 30],
    ["Circle, 14 mm", [round(7, 7, 7, 64)], 0],
  ];
  const cell = (polys, angleDeg, stagger) => {
    const opts = Object.assign({ rowSpacing: 0.4 * PX, angleDeg, maxStitch: MAX_STITCH_MM * PX, markConnectors: true },
      stagger ? { stagger: 4, minStitch: PX, splitTol: 1e-6 * PX } : null);
    return { pts: FILL.tatamiFill(polys, opts), polys };
  };
  let y = 20, out = "";
  const W = 30 * Z + 40;
  for (const [label, polys, angleDeg] of patches) {
    let h = 0;
    for (const ring of polys) for (const p of ring) h = Math.max(h, p.y / PX);
    [false, true].forEach((stagger, col) => {
      const { pts } = cell(polys, angleDeg, stagger), ox = 20 + col * W;
      out += `<text x="${ox}" y="${y - 6}" class="t">${label}: ${stagger ? "fillStagger on" : "as shipped"}</text>`;
      for (const ring of polys) out += `<polygon class="o" points="${ring.map((p) => `${(ox + (p.x / PX) * Z).toFixed(1)},${(y + (p.y / PX) * Z).toFixed(1)}`).join(" ")}"/>`;
      let d = "";
      pts.forEach((p, i) => { d += `${i && !p.travel ? "L" : "M"}${(ox + (p.x / PX) * Z).toFixed(1)} ${(y + (p.y / PX) * Z).toFixed(1)}`; });
      out += `<path class="r" d="${d}"/>`;
      for (const p of pts) if (!p.travel) out += `<circle class="h" cx="${(ox + (p.x / PX) * Z).toFixed(1)}" cy="${(y + (p.y / PX) * Z).toFixed(1)}" r="1.5"/>`;
    });
    y += h * Z + 44;
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${2 * W + 20} ${y}" width="${2 * W + 20}" height="${y}">` +
    `<style>.t{font:13px sans-serif;fill:#222}.o{fill:#f4f1ea;stroke:#999;stroke-width:1}.r{fill:none;stroke:#1b3a5c;stroke-width:0.5;stroke-opacity:0.35}.h{fill:#1b3a5c}</style>` +
    `<rect width="100%" height="100%" fill="#fff"/>${out}</svg>\n`;
  writeFileSync(SHEET, svg);
  console.log(`\nwrote ${SHEET}`);
}
