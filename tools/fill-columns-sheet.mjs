// Draws what `fillColumns` changes: the same shapes sewn with the option off
// and on, thread by thread, with every float and every cut marked.
//
//   node tools/fill-columns-sheet.mjs [outDir]
//
// Writes <outDir>/sheet.svg (default docs/renders/fill-columns-2026-10-03) and
// prints the table that folder's README carries.
//
// It reads `design.stitches` straight from buildQualityDesign, called the way
// the Studio's manual lane calls it (app/src/lib/generate.js): a garment, its
// fabric preset, `darkOnTop: false`, underlay on. Nothing is decoded from a
// file, so what is drawn is what the encoders are handed.
//
// THREAD, not penetrations. A move lays thread unless the thread has been cut
// since the last penetration, so a `jump` that follows a stitch is a float on
// the cloth. That is the thing the engine's own test could not see: it counts
// needle points inside a hole, and a float has none.
import { mkdirSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const DG = require("../src/digitize.js");
const FAB = require("../src/fabrics.js");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = process.argv[2] || join(ROOT, "docs", "renders", "fill-columns-2026-10-03");

const PX = 10; // source px per mm
const mm = (pts) => pts.map(([x, y]) => ({ x: x * PX, y: y * PX }));
const box = (x0, y0, x1, y1) => mm([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
const ellipse = (cx, cy, rx, ry, n = 64) =>
  mm(Array.from({ length: n }, (_, i) => [cx + rx * Math.cos((2 * Math.PI * i) / n), cy + ry * Math.sin((2 * Math.PI * i) / n)]));

// Four shapes a person draws in the manual lane. Sizes in mm.
const DESIGNS = [
  { name: "Badge, two cut-outs (12 mm and 3 mm)", widthMm: 40,
    outer: box(0, 0, 40, 40), holes: [box(6, 14, 18, 26), box(28.5, 18.5, 31.5, 21.5)] },
  { name: "Ring (an O)", widthMm: 30,
    outer: ellipse(15, 18, 15, 18), holes: [ellipse(15, 18, 7, 10)] },
  { name: "Two counters (a B)", widthMm: 26,
    outer: box(0, 0, 26, 36), holes: [box(8, 6, 18, 14), box(8, 20, 20, 30)] },
  // Wide, so the rows (the shape's own long axis) run ACROSS the notch.
  { name: "Wide U (no hole at all: a notch)", widthMm: 44,
    outer: mm([[0, 0], [14, 0], [14, 18], [30, 18], [30, 0], [44, 0], [44, 28], [0, 28]]), holes: [] },
];

function build(design, fillColumns) {
  return DG.buildQualityDesign(
    [{ rgb: [27, 58, 92], shapes: [{ outer: design.outer, holes: design.holes, tierOverride: "fill" }] }],
    // generate.js's own spelling: fabricForGarment() returns the preset's ID.
    { garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, fabric: FAB.getFabric(FAB.fabricForGarment("left_chest")),
      pxPerMm: PX, targetWidthMm: design.widthMm, darkOnTop: false, underlay: true, fillColumns });
}

// -> { sewn: [[p, q]...], floats: [[p, q]...], cuts: [p...], counts }
function thread(d) {
  const sewn = [], floats = [], cuts = [];
  let attached = false, prev = null;
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "trim") { attached = false; cuts.push(s); prev = s; continue; }
    if (prev && attached && (prev.x !== s.x || prev.y !== s.y)) (s.type === "stitch" ? sewn : floats).push([prev, s]);
    if (s.type === "stitch") attached = true;
    prev = s;
  }
  const len = (segs) => segs.reduce((a, [p, q]) => a + Math.hypot(q.x - p.x, q.y - p.y), 0) / 10;
  return { sewn, floats, cuts,
    counts: { stitches: d.stitches.filter((s) => s.type === "stitch").length, floats: floats.length,
      floatMm: Math.round(len(floats)), cuts: cuts.length } };
}

// --- the sheet ----------------------------------------------------------------
const S = 9;              // svg px per mm
const PAD = 5, CAPTION = 13, GAP = 8; // mm
const colW = Math.max(...DESIGNS.map((d) => d.widthMm)) + 2 * PAD;
const rowH = (d) => (Math.max(...d.outer.map((p) => p.y)) / PX) + 2 * PAD + CAPTION;
const totalH = DESIGNS.reduce((a, d) => a + rowH(d) + GAP, 12) + 6;
const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const f = (n) => (Math.round(n * 100) / 100).toString();

const svg = [];
svg.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${f((2 * colW + GAP) * S)} ${f(totalH * S)}" font-family="system-ui, Segoe UI, Arial, sans-serif">`);
svg.push(`<rect width="100%" height="100%" fill="#ffffff"/>`);
svg.push(`<text x="${f(PAD * S)}" y="${f(7 * S)}" font-size="${f(3.6 * S)}" font-weight="600" fill="#111">fillColumns off</text>`);
svg.push(`<text x="${f((colW + GAP + PAD) * S)}" y="${f(7 * S)}" font-size="${f(3.6 * S)}" font-weight="600" fill="#111">fillColumns on</text>`);

const rows = [];
let y0 = 12;
for (const design of DESIGNS) {
  const w = design.widthMm, h = Math.max(...design.outer.map((p) => p.y)) / PX;
  const stats = [];
  [false, true].forEach((on, col) => {
    const d = build(design, on);
    const t = thread(d);
    stats.push(t.counts);
    // design units are 0.1 mm, centred, y up; the sheet is mm, y down
    const ox = (col * (colW + GAP) + PAD + w / 2) * S, oy = (y0 + PAD + h / 2) * S;
    const f1 = (n) => (Math.round(n * 10) / 10).toString();
    const P = (p) => `${f1(ox + (p.x / 10) * S)},${f1(oy - (p.y / 10) * S)}`;
    // consecutive sewn moves share a point: one polyline per unbroken stretch
    const chains = [];
    for (const [p, q] of t.sewn) {
      const last = chains[chains.length - 1];
      if (last && last[last.length - 1] === p) last.push(q); else chains.push([p, q]);
    }
    const ring = (r, fill) => `<polygon points="${r.map((p) => `${f(ox + (p.x / PX - w / 2) * S)},${f(oy + (p.y / PX - h / 2) * S)}`).join(" ")}" fill="${fill}" stroke="#9aa3ad" stroke-width="0.6"/>`;
    svg.push(ring(design.outer, "#eef2f6"));
    for (const hole of design.holes) svg.push(ring(hole, "#fff7d6"));
    svg.push(`<path d="${chains.map((c) => "M" + c.map(P).join(" ")).join("")}" stroke="#1b3a5c" stroke-width="0.7" stroke-opacity="0.75" fill="none"/>`);
    if (t.floats.length) svg.push(`<path d="${t.floats.map(([p, q]) => `M${P(p)}L${P(q)}`).join("")}" stroke="#d81e1e" stroke-width="1.1" fill="none"/>`);
    for (const c of t.cuts) svg.push(`<circle cx="${P(c).split(",")[0]}" cy="${P(c).split(",")[1]}" r="3.2" fill="#f08c00" stroke="#7a4300" stroke-width="0.8"/>`);
    const ty = (y0 + PAD + h + PAD) * S;
    svg.push(`<text x="${f((col * (colW + GAP) + PAD) * S)}" y="${f(ty + 2.2 * S)}" font-size="${f(2.6 * S)}" fill="#111">${esc(col === 0 ? design.name : "")}</text>`);
    svg.push(`<text x="${f((col * (colW + GAP) + PAD) * S)}" y="${f(ty + 6.2 * S)}" font-size="${f(2.2 * S)}" fill="${t.counts.floats > 5 ? "#b01212" : "#1a6b2f"}">${esc(`${t.counts.floats} floats, ${t.counts.floatMm} mm loose · ${t.counts.cuts} cut${t.counts.cuts === 1 ? "" : "s"} · ${t.counts.stitches.toLocaleString("en-US")} st`)}</text>`);
  });
  rows.push({ name: design.name, off: stats[0], on: stats[1] });
  y0 += rowH(design) + GAP;
}
svg.push(`<text x="${f(PAD * S)}" y="${f((totalH - 5.5) * S)}" font-size="${f(2.2 * S)}" fill="#444">blue: sewn thread · red: a float left on the cloth (a jump with the thread still attached)</text>`);
svg.push(`<text x="${f(PAD * S)}" y="${f((totalH - 2) * S)}" font-size="${f(2.2 * S)}" fill="#444">orange dot: the thread is cut here · pale yellow: a hole, which must stay empty</text>`);
svg.push(`</svg>`);

mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, "sheet.svg"), svg.join("\n") + "\n");

const pct = (a, b) => (((b - a) / a) * 100).toFixed(1);
console.log("| shape | floats off | floats on | cuts off | cuts on | stitches off | stitches on |");
console.log("|---|---|---|---|---|---|---|");
for (const r of rows) {
  console.log(`| ${r.name} | ${r.off.floats} (${r.off.floatMm} mm) | ${r.on.floats} (${r.on.floatMm} mm) | ${r.off.cuts} | ${r.on.cuts} | ${r.off.stitches.toLocaleString("en-US")} | ${r.on.stitches.toLocaleString("en-US")} (${pct(r.off.stitches, r.on.stitches) >= 0 ? "+" : ""}${pct(r.off.stitches, r.on.stitches)}%) |`);
}
console.log(`\nwrote ${join(OUT, "sheet.svg")}`);

// --- what it costs: cuts, stitches and time, on shapes with many holes ---------
//
// The drawings are here so that the README's second table can be re-measured:
// an audit could not reproduce the first version of it, because the badge it
// was measured on was in nobody's repo, and the count turned out to depend on
// the order the holes were drawn in.
const round = (cx, cy, r, n = 24) => ellipse(cx, cy, r, r, n);
const grid = (n, sizeMm, make) => {
  const out = [], pitch = sizeMm / n;
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) out.push(make((c + 0.5) * pitch, (r + 0.5) * pitch));
  return out;
};
const COSTS = [
  { name: "36 square holes of 4 mm, 60 mm badge", widthMm: 60, outer: box(0, 0, 60, 60), holes: grid(6, 60, (x, y) => box(x - 2, y - 2, x + 2, y + 2)) },
  { name: "36 round holes of 4 mm, 60 mm badge", widthMm: 60, outer: box(0, 0, 60, 60), holes: grid(6, 60, (x, y) => round(x, y, 2)) },
  { name: "196 square holes of 3 mm, 100 mm", widthMm: 100, outer: box(0, 0, 100, 100), holes: grid(14, 100, (x, y) => box(x - 1.5, y - 1.5, x + 1.5, y + 1.5)) },
  // A stress shape, not a design: it is here for the time column. An audit
  // found 3.5 to 18 seconds on it with the rows at 30 degrees, where the
  // README had said 1.3 at most -- measured at the engine's own angle only.
  { name: "2,025 square holes of 1.2 mm, 100 mm", widthMm: 100, outer: box(0, 0, 100, 100), holes: grid(45, 100, (x, y) => box(x - 0.6, y - 0.6, x + 0.6, y + 0.6)) },
];
const PRESETS = [["no fabric", null], ["pique_knit", "pique_knit"], ["structured_cap", "structured_cap"], ["terry_towel", "terry_towel"]];
console.log("\n| shape | preset | rows | cuts off | cuts on | stitches | time off | time on |");
console.log("|---|---|---|---|---|---|---|---|");
for (const design of COSTS) {
  for (const [label, id] of PRESETS) {
    for (const angleOverride of [null, 30]) {
      const run = (fillColumns) => {
        const shape = { outer: design.outer, holes: design.holes, tierOverride: "fill" };
        if (angleOverride != null) shape.angleOverride = angleOverride;
        const t0 = Date.now();
        const d = DG.buildQualityDesign([{ rgb: [27, 58, 92], shapes: [shape] }],
          Object.assign({ garment: { id: "left_chest", widthIn: 8, heightIn: 8 }, pxPerMm: PX, targetWidthMm: design.widthMm, darkOnTop: false, underlay: true, fillColumns },
            id ? { fabric: FAB.getFabric(id) } : {}));
        return { ms: Date.now() - t0, cuts: d.stitches.filter((s) => s.type === "trim").length, st: d.stitchCount };
      };
      const off = run(false), on = run(true);
      console.log(`| ${design.name} | ${label} | ${angleOverride == null ? "the engine's own angle" : angleOverride + "°"} | ${off.cuts} | ${on.cuts} | ${pct(off.st, on.st) >= 0 ? "+" : ""}${pct(off.st, on.st)}% | ${off.ms} ms | ${on.ms} ms |`);
    }
  }
}
