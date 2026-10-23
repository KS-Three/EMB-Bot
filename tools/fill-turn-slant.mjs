// The browser fill's SLANTED TURN (`fillTurnSlant`, built OFF 2026-10-22; the
// JS twin of the Python engine's `cfg.fill_turn_slant`, PR #1036), measured off
// beside on. At the end of every fill row the engine stepped straight across
// to the next row, one row spacing long (0.15 mm at the builder's row, the
// needle beside its own hole); the pro's turn runs 0.7 mm along the row.
//
//   node tools/fill-turn-slant.mjs                 the table: every design off and on
//   node tools/fill-turn-slant.mjs --json out.json the same as JSON
//   node tools/fill-turn-slant.mjs --pins          print the OFF md5 of the pinned set
//
// Designs: the builder fixture `test/fill-stagger.test.js` and
// `test/fill-turn-slant.test.js` share (three fill shapes, one with a hole; with
// the plain walk and with `fillColumns`), and six shapes built exactly as the
// Studio builds a `shape` element set to fill on left chest (`shapesToRegions`,
// `buildQualityDesign` with the pique preset). Nothing here is sewn: every
// number is of the stitch plan, read from the design's 0.1 mm stitch stream.
//
// Per design and arm: stitches, stitches under 0.5 mm (consecutive `stitch`
// records; a jump or trim between them is not a stitch), the row turns among
// them (a stitch whose ends sit on different rows of the cover fill, read from
// the tatami passes the builder asks for, in the fill's own frame), the turn
// length p50 of the cover fill, and the md5 of the stitch stream (x, y, type of
// every record). The md5 is what `test/fill-turn-slant.test.js` pins: with the
// option off it must not move.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(ROOT, "src", "digitize.js"));
const DG = require(path.join(ROOT, "src/digitize.js"));
const fill = require(path.join(ROOT, "src/fill.js"));
const GAR = require(path.join(ROOT, "src/garments.js"));
const FAB = require(path.join(ROOT, "src/fabrics.js"));
const lib = (name) => import(pathToFileURL(path.join(ROOT, "app", "src", "lib", name)).href);

const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : null; };

const GARMENT = "left_chest";
const garment = GAR.getGarment(GARMENT), fabric = FAB.getFabric(FAB.fabricForGarment(GARMENT));

// ---- the designs ------------------------------------------------------------
const rect = (x, y, w, h) => [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
// the test fixture: `ties` and `dedupeHoles` OFF, as its pins were taken
const FIXTURE_REGIONS = [
  { rgb: [10, 10, 10], shapes: [{ outer: rect(0, 0, 400, 200), holes: [], tierOverride: "fill" }, { outer: rect(600, 0, 300, 300), holes: [rect(700, 100, 100, 100)], tierOverride: "fill" }] },
  { rgb: [200, 30, 30], shapes: [{ outer: rect(0, 400, 250, 250), holes: [], tierOverride: "fill" }] },
];
const fixture = (extra) => DG.buildQualityDesign(FIXTURE_REGIONS, Object.assign({ garment: { widthIn: 6, heightIn: 6 }, pxPerMm: 10, darkOnTop: false, underlay: true, ties: false, dedupeHoles: false }, extra));

export const SHAPES = [
  { id: "square30", label: "30 mm square", kind: "rect", params: { heightMm: 30, cornerRadiusMm: 0 }, sizeMm: 30 },
  { id: "disc30", label: "30 mm disc", kind: "circle", params: {}, sizeMm: 30 },
  { id: "bar40x8", label: "40 x 8 mm bar, round ends", kind: "rect", params: { heightMm: 8, cornerRadiusMm: 4 }, sizeMm: 40 },
  { id: "star40", label: "5-point star, 40 mm, inner ratio 0.45", kind: "star", params: { points: 5, innerRatio: 0.45 }, sizeMm: 40 },
  { id: "heart30", label: "30 mm heart", kind: "heart", params: {}, sizeMm: 30 },
  { id: "strip30x3", label: "30 x 3 mm strip", kind: "rect", params: { heightMm: 3, cornerRadiusMm: 0 }, sizeMm: 30 },
];
let mods = null;
async function studio() {
  if (!mods) mods = { presets: await lib("shapePresets.js"), manual: await lib("manualShapes.js") };
  return mods;
}
export async function buildShape(spec, on, extra) {
  const { presets, manual } = await studio();
  const points = presets.shapePresetPoints(spec.kind, spec.params, spec.sizeMm);
  const { regions, pxPerMm } = manual.shapesToRegions([
    { id: spec.id, points, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  return DG.buildQualityDesign(regions, { garment, fabric, pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: spec.sizeMm, offsetXMm: 0, offsetYMm: 0, fillTurnSlant: !!on, ...extra });
}

// ---- measures ---------------------------------------------------------------
// the stream as `test/fill-turn-slant.test.js` hashes it: "x,y,type" records joined by ";"
export const md5Of = (design) => createHash("md5").update(design.stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";")).digest("hex");
const p50 = (xs) => { const s = xs.slice().sort((a, b) => a - b); return s.length ? s[(s.length - 1) >> 1] : NaN; };

// Build with every tatami pass the builder asks for recorded, and read the
// cover fill's turns in the fill's own frame (a turn: a sewn stitch whose two
// ends sit on different rows). The pass's units are pixels at the design's
// final scale; `maxStitch` is the builder's 4 mm stitch, so mm = px * 4 / maxStitch.
function withPasses(build) {
  const real = fill.tatamiFill, seen = [];
  fill.tatamiFill = (polys, opts) => { const pts = real(polys, opts); seen.push({ polys, opts, pts }); return pts; };
  try { return { design: build(), seen }; } finally { fill.tatamiFill = real; }
}
async function withPassesAsync(build) {
  const real = fill.tatamiFill, seen = [];
  fill.tatamiFill = (polys, opts) => { const pts = real(polys, opts); seen.push({ polys, opts, pts }); return pts; };
  try { return { design: await build(), seen }; } finally { fill.tatamiFill = real; }
}
function turnsOf(seen) {
  const coverRow = Math.min(...seen.map((p) => p.opts.rowSpacing));
  const out = [];
  for (const p of seen) {
    if (p.opts.rowSpacing !== coverRow) continue;        // the underlay passes have wider rows
    const mmPerPx = 4 / p.opts.maxStitch;
    const t = (p.opts.angleDeg || 0) * Math.PI / 180, c = Math.cos(-t), s = Math.sin(-t);
    const rowY = (q) => q.x * s + q.y * c;
    for (let i = 1; i < p.pts.length; i++) {
      const a = p.pts[i - 1], b = p.pts[i];
      if (b.travel || b.trim) continue;
      const d = Math.hypot(b.x - a.x, b.y - a.y) * mmPerPx;
      if (d <= 1e-6) continue;
      if (Math.abs(rowY(a) - rowY(b)) * mmPerPx > 1e-6) out.push(d);
    }
  }
  return out;
}
export function measure(design, seen) {
  const st = design.stitches;
  let n = 0, short = 0;
  for (let i = 1; i < st.length; i++) {
    if (st[i].type !== "stitch") continue;
    n++;
    if (st[i - 1].type === "stitch" && Math.hypot(st[i].x - st[i - 1].x, st[i].y - st[i - 1].y) < 5) short++;
  }
  const turns = turnsOf(seen);
  return { stitches: n, under05: short, under05Pct: n ? (100 * short) / n : 0, turns: turns.length, turnsUnder05: turns.filter((d) => d < 0.5).length, turnP50: p50(turns), trims: st.filter((s) => s.type === "trim").length, md5: md5Of(design) };
}

// ---- main -------------------------------------------------------------------
async function main() {
  const rows = [];
  for (const fc of [false, true]) {
    const id = "fixture" + (fc ? "_columns" : "");
    const off = withPasses(() => fixture({ fillColumns: fc, fillTurnSlant: false })), on = withPasses(() => fixture({ fillColumns: fc, fillTurnSlant: true }));
    rows.push({ id, label: "test fixture, three fill shapes" + (fc ? ", fillColumns" : ""), off: measure(off.design, off.seen), on: measure(on.design, on.seen), pinned: true });
  }
  for (const spec of SHAPES) {
    const off = await withPassesAsync(() => buildShape(spec, false)), on = await withPassesAsync(() => buildShape(spec, true));
    rows.push({ id: spec.id, label: spec.label, off: measure(off.design, off.seen), on: measure(on.design, on.seen) });
  }
  if (flag("--pins")) {
    for (const r of rows.filter((r) => r.pinned)) console.log(`  ${r.id}: "${r.off.md5}",`);
    return;
  }
  if (opt("--json")) fs.writeFileSync(opt("--json"), JSON.stringify(rows, null, 2));
  const f = (x, d = 0) => (Number.isFinite(x) ? x.toFixed(d) : "-");
  console.log("| design | stitches off -> on | under 0.5 mm off -> on | row turns under 0.5 off -> on | turn p50 mm off -> on | trims | OFF md5 |");
  console.log("|---|---|---|---|---|---|---|");
  for (const r of rows) {
    const a = r.off, b = r.on;
    console.log(`| ${r.label} | ${a.stitches} -> ${b.stitches} (${f(100 * (b.stitches / a.stitches - 1), 1)}%) | ${a.under05} (${f(a.under05Pct, 1)}%) -> ${b.under05} (${f(b.under05Pct, 1)}%) | ${a.turnsUnder05} of ${a.turns} -> ${b.turnsUnder05} of ${b.turns} | ${f(a.turnP50, 2)} -> ${f(b.turnP50, 2)} | ${a.trims} ${a.trims === b.trims ? "=" : "->"} ${a.trims === b.trims ? "" : b.trims} | ${a.md5.slice(0, 8)} |`);
  }
}
main().catch((e) => { console.error(e); process.exit(1); });
