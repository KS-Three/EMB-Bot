// Two stitch records in a row on ONE point of the stitch file: where the
// browser fill makes them, how far apart the two penetrations were before the
// builder rounded them to the file's unit (0.1 mm), and what kind of move each
// was. Prints the tables docs/sub-unit-stitches-2026-10-03.md carries.
//
//   node tools/sub-unit-stitch-census.mjs [srcDir] [--corpus sweep|studio|file]
//        [--on name=value]... [--off name=value]... [--jobs N]
//        [--against otherSrcDir] [--json out.json] [--pairs out.ndjson]
//
// srcDir: the engine to measure (default: this checkout's src). Point it at
// another checkout, or at a copy with a candidate rule in it, to measure that.
// --against: build every design with a second engine as well and say how the
// two record streams differ: not at all; only in that this engine laid no
// second stitch in a hole where that one did; or in some other way.
//
// Every design is built twice: with every flag ABSENT (what ships), and ON
// (`fillColumns: true`). `--on` and `--off` add builder options to one arm,
// which is how a rule behind a flag is priced beside the engine as it is:
// `--on dedupeHoles=true --off dedupeHoles=true` is the builder's own rule.
//
// THE ENGINE IS NOT TOUCHED. `tatamiFill` is wrapped, so each pass is seen as
// the fill module handed it over, in the drawing's own units and before any
// rounding. A pass is then found in the finished record stream by the span
// the builder wrote for it (`design.runs`): one jump, then a record a point.
// A pass that cannot be found is counted and said, not skipped.
//
// A PAIR is two `stitch` records in a row with the same x and y. The needle
// goes down twice in one hole. EXACT: the two points were one point before
// rounding too (no further apart than 1e-6 px, the walk's own measure of "the
// same point"). SHORT: they were a real distance apart and the rounding put
// them together.
//
// WHAT MADE IT is read off this file's own scanline, cut from the rings the
// builder gave the fill, not asked of the engine:
//   corner   a span of no length: the scanline runs through a corner
//   tip      a row at the end of a strip that narrows to nothing
//   lone     a narrow row with no row of the shape standing over or under it:
//            the point of a slanted spike, or a speck
//   sliver   a row of a strip, two rows or more, that is narrow from end to end
//   waist    a row where a strip narrows between two wider parts
//   touch    the move between two spans of one scanline that meet at a point
//   gap      the move between two spans of one scanline a hair apart
//   turn     the move from the end of one row to the start of the next
//   other    anything else: a leg round a ring, a run along a column's side
// "Narrow" is under the longest row that can round onto one point, the unit
// times the square root of two. That is the file's arithmetic, not a physical
// constant.
import { writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { fork } from "node:child_process";
import os from "node:os";

const require = createRequire(import.meta.url);
const SELF = fileURLToPath(import.meta.url);
const ROOT = join(dirname(SELF), "..");
const args = process.argv.slice(2);
const take = (name) => {
  const out = [];
  for (let i = args.indexOf(name); i >= 0; i = args.indexOf(name)) out.push(args.splice(i, 2)[1]);
  return out;
};
const optsOf = (list) => {
  const o = {};
  for (const kv of list) {
    const i = kv.indexOf("="), v = kv.slice(i + 1);
    try { o[kv.slice(0, i)] = JSON.parse(v); } catch { o[kv.slice(0, i)] = v; }
  }
  return o;
};
const ON_ARGS = take("--on"), OFF_ARGS = take("--off");
const ARMS = { absent: optsOf(OFF_ARGS), on: Object.assign({ fillColumns: true }, optsOf(ON_ARGS)) };
const WANT = take("--corpus");
const JOBS = Math.max(1, Number(take("--jobs")[0]) || Math.min(8, os.cpus().length));
const JSON_OUT = take("--json")[0], PAIRS_OUT = take("--pairs")[0];
const PART = take("--part")[0];
const AGAINST = take("--against")[0];
const SRC = resolve(args[0] || join(ROOT, "src"));

const DG = require(join(SRC, "digitize.js"));
const FAB = require(join(SRC, "fabrics.js"));
const FILL = require(join(SRC, "fill.js"));
const GAR = require(join(SRC, "garments.js"));
const DG_OTHER = AGAINST ? require(join(resolve(AGAINST), "digitize.js")) : null;

// every tatami pass of the design being built, as the fill module returned it
let PASSES = [];
const tatami = FILL.tatamiFill;
FILL.tatamiFill = function (polys, opts) {
  const pts = tatami.call(this, polys, opts);
  PASSES.push({ polys, opts, pts });
  return pts;
};

const UNIT_MM = 0.1, SAME_PX = 1e-6;

// ---- corpus "sweep": the 8,255 designs PR 616 and PR 617 were measured on --
// 117 shapes drawn on whole numbers (quarter turns of each), under every
// preset and none, at four row angles; and 260 random shapes of that sweep's
// own seed. Ported as it was, so the counts can be set beside those PRs'.
function sweepCorpus() {
  const R = (pts) => pts.map(([x, y]) => ({ x, y }));
  const box = (x0, y0, x1, y1) => R([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
  const round = (cx, cy, rx, ry, n) => Array.from({ length: n }, (_, i) => ({ x: cx + rx * Math.cos(2 * Math.PI * i / n), y: cy + ry * Math.sin(2 * Math.PI * i / n) }));
  const comb = (n, tw, gw, tl, sp) => {
    const pts = []; let x = 0;
    for (let i = 0; i < n; i++) { pts.push([x, 0], [x + tw, 0]); if (i < n - 1) pts.push([x + tw, tl], [x + tw + gw, tl]); x += tw + gw; }
    const w = n * tw + (n - 1) * gw;
    pts.push([w, tl + sp], [0, tl + sp]);
    return R(pts);
  };
  const bbox = (ring) => { let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity; for (const p of ring) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); } return { x0, x1, y0, y1 }; };
  const turn = (shape, q) => {
    const f = [(p) => ({ x: p.x, y: p.y }), (p) => ({ x: -p.y, y: p.x }), (p) => ({ x: -p.x, y: -p.y }), (p) => ({ x: p.y, y: -p.x })][q];
    const outer = shape.outer.map(f), b = bbox(outer), mv = (p) => ({ x: p.x - b.x0, y: p.y - b.y0 });
    return { outer: outer.map(mv), holes: shape.holes.map((h) => h.map(f).map(mv)) };
  };
  const drawn = [];
  const add = (name, outer, holes, turns) => { for (const q of (turns || [0])) drawn.push([name + (turns && turns.length > 1 ? " q" + q : ""), turn({ outer, holes: holes || [] }, q)]); };
  const Q = [0, 1, 2, 3];
  for (const [n, tw, gw, tl, sp] of [[8, 28, 17.5, 245, 105], [3, 60, 45, 180, 120], [5, 30, 20, 200, 100], [6, 24, 15, 210, 90], [4, 40, 25, 150, 100], [8, 24, 15, 210, 90]]) add(`comb ${n}x${tw}/${gw}`, comb(n, tw, gw, tl, sp), [], Q);
  add("T", R([[0, 0], [350, 0], [350, 105], [227.5, 105], [227.5, 350], [122.5, 350], [122.5, 105], [0, 105]]), [], Q);
  add("L", R([[0, 0], [100, 0], [100, 235], [300, 235], [300, 335], [0, 335]]), [], Q);
  add("wide U", R([[0, 0], [140, 0], [140, 180], [300, 180], [300, 0], [440, 0], [440, 280], [0, 280]]), [], Q);
  add("tall U", R([[0, 0], [100, 0], [100, 300], [200, 300], [200, 0], [300, 0], [300, 400], [0, 400]]), [], Q);
  add("E", R([[0, 0], [260, 0], [260, 60], [80, 60], [80, 130], [220, 130], [220, 190], [80, 190], [80, 260], [260, 260], [260, 320], [0, 320]]), [], Q);
  add("H", R([[0, 0], [90, 0], [90, 120], [210, 120], [210, 0], [300, 0], [300, 300], [210, 300], [210, 180], [90, 180], [90, 300], [0, 300]]), [], [0, 1]);
  add("plus", R([[122.5, 0], [227.5, 0], [227.5, 122.5], [350, 122.5], [350, 227.5], [227.5, 227.5], [227.5, 350], [122.5, 350], [122.5, 227.5], [0, 227.5], [0, 122.5], [122.5, 122.5]]), [], [0]);
  add("stairs", R([[0, 0], [75, 0], [75, 75], [150, 75], [150, 150], [225, 150], [225, 225], [300, 225], [300, 300], [0, 300]]), [], Q);
  add("badge, two cut-outs", box(0, 0, 400, 400), [box(60, 140, 180, 260), box(285, 185, 315, 215)], Q);
  add("square, one hole", box(0, 0, 300, 300), [box(100, 100, 200, 200)], [0]);
  add("B", box(0, 0, 260, 360), [box(80, 60, 180, 140), box(80, 200, 200, 300)], Q);
  { const h = []; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) h.push(box(60 + c * 100, 60 + r * 100, 100 + c * 100, 100 + r * 100)); add("badge 3x3", box(0, 0, 360, 360), h, [0]); }
  { const h = []; for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) h.push(box(40 + c * 95, 40 + r * 95, 80 + c * 95, 80 + r * 95)); add("badge 4x4", box(0, 0, 410, 410), h, [0]); }
  { const h = []; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) h.push(round(100 + c * 150, 100 + r * 150, 35, 35, 24)); add("nine round holes", box(0, 0, 500, 500), h, [0]); }
  add("ring", round(150, 180, 150, 180, 64), [round(150, 180, 70, 100, 64)], [0, 1]);
  add("annulus", round(200, 200, 200, 200, 64), [round(200, 200, 110, 110, 48)], [0]);
  add("house, window on the grid", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [box(100, 150, 200, 250)], Q);
  add("house, window off it", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [box(95, 150, 195, 250)], Q);
  add("house, no window", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [], Q);
  add("diamond with a hole", R([[150, 0], [300, 150], [150, 300], [0, 150]]), [box(110, 110, 190, 190)], [0, 1]);
  add("triangle with a hole", R([[150, 0], [300, 260], [0, 260]]), [box(120, 150, 180, 210)], Q);
  add("two peaks", R([[0, 300], [100, 0], [200, 200], [300, 50], [400, 300]]), [], Q);
  add("three peaks, a hole", R([[0, 300], [60, 0], [120, 180], [180, 30], [240, 180], [300, 0], [360, 300]]), [box(150, 220, 210, 270)], Q);
  add("arrow", R([[150, 0], [300, 150], [210, 150], [210, 350], [90, 350], [90, 150], [0, 150]]), [], Q);
  for (const n of [5, 6, 8]) {
    const star = []; for (let i = 0; i < 2 * n; i++) { const a = -Math.PI / 2 + Math.PI * i / n, r = i % 2 ? 80 : 180; star.push({ x: Math.round(180 + r * Math.cos(a)), y: Math.round(180 + r * Math.sin(a)) }); }
    add(`star ${n}`, star, [], [0, 1]);
    add(`star ${n}, a hole`, star, [box(160, 160, 200, 200)], [0, 1]);
    add(`polygon ${n}, a hole`, round(180, 180, 180, 180, n).map((p) => ({ x: Math.round(p.x), y: Math.round(p.y) })), [box(130, 130, 230, 230)], [0, 1]);
  }
  add("bullseye", box(0, 0, 400, 400), [box(80, 80, 320, 320), box(160, 160, 240, 240)], [0]);
  add("slot", box(0, 0, 300, 300), [box(145, 60, 155, 240)], [0, 1]);

  let seed = 4242;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const starR = (cx, cy, r, n, rough) => { const ph = rnd() * Math.PI * 2, pts = []; for (let i = 0; i < n; i++) { const a = ph + (2 * Math.PI * i) / n, rr = r * (1 - rough * rnd()); pts.push({ x: cx + rr * Math.cos(a), y: cy + rr * Math.sin(a) }); } return pts; };
  const stairsR = (w, h) => { const steps = 2 + Math.floor(rnd() * 4), top = [], bottom = []; let x = 0; for (let i = 0; i < steps; i++) { const nx = i === steps - 1 ? w : x + (w - x) * (0.2 + 0.5 * rnd()); const y0 = h * 0.4 * rnd(), y1 = h * (0.6 + 0.4 * rnd()); top.push({ x, y: y0 }, { x: nx, y: y0 }); bottom.push({ x, y: y1 }, { x: nx, y: y1 }); x = nx; } return top.concat(bottom.reverse()); };
  const edgesOf = (polys) => { const e = []; for (const p of polys) for (let i = 0; i < p.length; i++) e.push([p[i], p[(i + 1) % p.length]]); return e; };
  const insideE = (p, edges) => { let c = false; for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c; return c; };
  const depthE = (p, edges) => { let m = Infinity; for (const [u, v] of edges) { const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy; const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0; m = Math.min(m, Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy))); } return m; };
  const random = [];
  for (let t = 0; t < 260; t++) {
    const k = 1.5 + 2 * rnd();
    const sc = (r) => r.map((p) => ({ x: p.x * k, y: p.y * k }));
    const whole = rnd() < 0.35;
    const snap = (r) => whole ? r.map((p) => ({ x: Math.round(p.x), y: Math.round(p.y) })) : r;
    const outer0 = rnd() < 0.67 ? starR(100, 100, 60 + 40 * rnd(), 5 + Math.floor(rnd() * 30), pick([0, 0.2, 0.5])) : stairsR(160 + 60 * rnd(), 120 + 80 * rnd());
    const oe = edgesOf([outer0]), placed = [], holes0 = [];
    for (let h = Math.floor(rnd() * 6); h > 0; h--) {
      for (let tries = 0; tries < 20; tries++) {
        const c = { x: 20 + 180 * rnd(), y: 20 + 180 * rnd() }, r = 4 + 16 * rnd();
        if (!insideE(c, oe) || depthE(c, oe) < r + 4) continue;
        if (placed.some((q) => Math.hypot(q.c.x - c.x, q.c.y - c.y) < q.r + r + 3)) continue;
        holes0.push(starR(c.x, c.y, r, pick([4, 4, 6, 12, 20]), pick([0, 0, 0.3])));
        placed.push({ c, r });
        break;
      }
    }
    random.push([`random ${t}${whole ? " (whole px)" : ""}`, { outer: snap(sc(outer0)), holes: holes0.map((h) => snap(sc(h))) }, rnd() * 180]);
  }

  const designs = [];
  const fabrics = [null].concat(FAB.FABRICS);
  for (const [name, shape] of drawn) for (const fabric of fabrics) for (const angle of [null, 0, 90, 30]) designs.push({ name, shape, fabric, angle, underlay: true, set: "drawn" });
  for (const [name, shape] of drawn) for (const angle of [null, 0, 90]) designs.push({ name, shape, fabric: null, angle, underlay: false, set: "drawn" });
  for (const [name, shape, ang] of random) for (const fabric of fabrics) for (const angle of [null, Math.round(ang * 10) / 10]) designs.push({ name, shape, fabric, angle, underlay: true, set: "random" });
  const build = (d, extra, dg) => {
    const s = Object.assign({ tierOverride: "fill" }, d.shape);
    if (d.angle != null) s.angleOverride = d.angle;
    const b = bbox(d.shape.outer);
    const o = { garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: (b.x1 - b.x0) / 10, darkOnTop: false, underlay: d.underlay };
    if (d.fabric) o.fabric = d.fabric;
    return (dg || DG).buildQualityDesign([{ rgb: [0, 0, 0], shapes: [s] }], Object.assign(o, extra));
  };
  const tag = (d) => ({ fabric: d.fabric ? d.fabric.id : "none", angle: d.angle == null ? "auto" : String(d.angle), set: d.set });
  return { designs, build, tag };
}

// ---- corpus "studio": what the Studio's own shape lanes hand the builder ---
// Built with the Studio's own modules and the options generate.js passes, so
// a count here is a count of what a customer's design carries today.
//   preset   circle, heart, rectangle and star over the ranges the panel
//            offers, at seven widths, on every garment. The classifier picks
//            satin or fill, as it does for a preset.
//   manual   150 shapes of this file's own seed, drawn the way a hand draws
//            them (corners on and off whole px, some sides bowed, some with
//            cut-outs), fill chosen, row angle left alone or set, at three
//            sizes on a garment of each fabric.
async function studioCorpus() {
  const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions, flattenShape, isValidShape, CANVAS_W, CANVAS_H } = await lib("manualShapes.js");
  const designs = [];
  const kinds = [["circle", {}], ["heart", {}]];
  for (const heightMm of [10, 30, 50]) for (const cornerRadiusMm of [0, 3, 8]) kinds.push(["rect", { heightMm, cornerRadiusMm }]);
  for (const points of [3, 4, 5, 6, 8, 12]) for (const innerRatio of [0.15, 0.3, 0.45, 0.6, 0.9]) kinds.push(["star", { points, innerRatio }]);
  for (const [kind, params] of kinds) for (const sizeMm of [12, 20, 30, 40, 50, 65, 80]) for (const garment of GAR.GARMENTS) {
    const shapes = [{ id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null }];
    designs.push({ name: `${kind} ${JSON.stringify(params)} ${sizeMm} mm`, shapes, sizeMm, garment, angle: null, set: "preset " + kind });
  }
  let seed = 20261003;
  const rnd = () => { seed = (Math.imul(seed, 1103515245) + 12345) >>> 0; return seed / 4294967296; };
  const oneOfEach = ["hat_front", "left_chest", "beanie", "full_back", "tote", "towel"].map((id) => GAR.getGarment(id));
  for (let t = 0, made = 0; made < 150 && t < 2000; t++) {
    const n = 3 + Math.floor(rnd() * 12), reach = 60 + 120 * rnd(), whole = rnd() < 0.5;
    const snap = (v) => (whole ? Math.round(v) : Math.round(v * 100) / 100);
    const at = (cx, cy, r, a, wide) => ({ x: snap(Math.max(2, Math.min(CANVAS_W - 2, cx + wide * r * Math.cos(a)))), y: snap(Math.max(2, Math.min(CANVAS_H - 2, cy + r * Math.sin(a)))) });
    const points = [];
    for (let i = 0; i < n; i++) points.push(at(CANVAS_W / 2, CANVAS_H / 2, reach * (0.35 + 0.65 * rnd()), (2 * Math.PI * (i + 0.6 * (rnd() - 0.5))) / n, 1.4));
    const curves = {};
    for (let i = 0; i < n; i++) {
      if (rnd() >= 0.4) continue;
      const a = points[i], c = points[(i + 1) % n], bow = -0.2 + 0.5 * rnd();
      curves[i] = { x: (a.x + c.x) / 2 + bow * (c.y - a.y), y: (a.y + c.y) / 2 - bow * (c.x - a.x) };
    }
    if (!isValidShape(flattenShape(points, curves, true))) continue;
    const cuts = [];
    for (let h = rnd() < 0.5 ? 1 + Math.floor(rnd() * 2) : 0; h > 0; h--) {
      const m = 4 + Math.floor(rnd() * 5), r = 8 + 22 * rnd(), off = 0.3 * reach * rnd(), dir = 2 * Math.PI * rnd(), turn = 2 * Math.PI * rnd();
      const ring = [];
      for (let i = 0; i < m; i++) ring.push(at(CANVAS_W / 2 + off * Math.cos(dir), CANVAS_H / 2 + off * Math.sin(dir), r, turn + (2 * Math.PI * i) / m, 1));
      if (isValidShape(ring)) cuts.push({ id: "c" + cuts.length, points: ring, curves: {}, cutOut: true });
    }
    const setAngle = Math.round(rnd() * 179);
    for (const angle of [null, setAngle]) for (const sizeMm of [null, 25, 60]) for (const garment of oneOfEach) {
      const shapes = [{ id: "s", points, curves, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: angle }].concat(cuts);
      designs.push({ name: `manual ${made}${whole ? " (whole px)" : ""}`, shapes, sizeMm, garment, angle, set: "manual" });
    }
    made++;
  }
  const build = (d, extra, dg) => {
    const { regions, pxPerMm } = shapesToRegions(d.shapes);
    const fabric = FAB.getFabric(FAB.fabricForGarment(d.garment.id));
    return (dg || DG).buildQualityDesign(regions, Object.assign({ garment: d.garment, fabric, pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: d.sizeMm || undefined, offsetXMm: 0, offsetYMm: 0 }, extra));
  };
  const tag = (d) => ({ fabric: FAB.fabricForGarment(d.garment.id), angle: d.angle == null ? "auto" : "set", set: d.set });
  return { designs, build, tag };
}

// ---- the reader ------------------------------------------------------------
const tally = () => ({ n: {}, max: {}, pairs: [] });
const bump = (t, k, by) => { t.n[k] = (t.n[k] || 0) + (by == null ? 1 : by); };
const peak = (t, k, v) => { if (!(t.max[k] >= v)) t.max[k] = v; };
const merge = (into, t) => {
  for (const k in t.n) bump(into, k, t.n[k]);
  for (const k in t.max) peak(into, k, t.max[k]);
  for (const p of t.pairs) into.pairs.push(p);
};
// how long a stitch was before rounding, in mm
const BUCKETS = [[0.01, "under 0.01"], [0.05, "0.01 to 0.05"], [UNIT_MM, "0.05 to 0.10"], [UNIT_MM * Math.SQRT2, "0.10 to 0.141"], [0.3, "0.141 to 0.3"], [0.5, "0.3 to 0.5"], [1.0, "0.5 to 1.0"]];
const bucketOf = (px, mm) => (px <= SAME_PX ? "exact" : (BUCKETS.find(([top]) => mm < top) || [0, "1.0 and over"])[1]);

// The pass's own rows, cut here from the rings it was given, with the
// engine's arithmetic (so that a row end here is the engine's to the bit).
function frameOf(pass) {
  const theta = ((pass.opts.angleDeg || 0) * Math.PI) / 180, c = Math.cos(-theta), s = Math.sin(-theta);
  const rot = (p) => ({ x: p.x * c - p.y * s, y: p.x * s + p.y * c });
  const rings = pass.polys.filter((r) => r.length >= 2).map((r) => r.map(rot));
  let minY = Infinity, maxY = -Infinity;
  for (const r of rings) for (const p of r) { if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  const pitch = pass.opts.rowSpacing, rows = [];
  for (let y = minY; y <= maxY + 1e-9; y += pitch) {
    const xs = [];
    for (const ring of rings) for (let i = 0; i < ring.length; i++) {
      const a = ring[i], b = ring[(i + 1) % ring.length];
      if (a.y === b.y) continue;
      if (y >= Math.min(a.y, b.y) && y < Math.max(a.y, b.y)) xs.push(a.x + ((y - a.y) / (b.y - a.y)) * (b.x - a.x));
    }
    xs.sort((p, q) => p - q);
    const spans = [];
    for (let i = 0; i + 1 < xs.length; i += 2) spans.push([xs[i], xs[i + 1]]);
    rows.push({ y, spans });
  }
  return { rot, rings, rows, minY, pitch };
}

const NEAR = 1e-6;
function whatMadeIt(fr, a, b, unitPx) {
  const A = fr.rot(a), B = fr.rot(b);
  const rowOf = (p) => {
    const k = Math.round((p.y - fr.minY) / fr.pitch);
    return fr.rows[k] && Math.abs(fr.rows[k].y - p.y) < NEAR ? k : -1;
  };
  const ka = rowOf(A), kb = rowOf(B);
  const isEnd = (k, x) => fr.rows[k].spans.some((s) => Math.abs(s[0] - x) < NEAR || Math.abs(s[1] - x) < NEAR);
  if (ka >= 0 && ka === kb) {
    const spans = fr.rows[ka].spans;
    const row = spans.find((s) => (Math.abs(s[0] - A.x) < NEAR && Math.abs(s[1] - B.x) < NEAR) || (Math.abs(s[1] - A.x) < NEAR && Math.abs(s[0] - B.x) < NEAR));
    if (row) {
      const len = row[1] - row[0];
      if (len <= SAME_PX) return { cls: "corner", rows: 1 };
      // how far the narrow strip this row is in runs each way, and what ends it
      const narrow = Math.SQRT2 * unitPx;
      const over = (p, q) => Math.min(p[1], q[1]) - Math.max(p[0], q[0]) > SAME_PX;
      const reach = (dir) => {
        let k = ka, s = row, n = 0;
        for (;;) {
          const next = ((fr.rows[k + dir] || {}).spans || []).filter((q) => over(q, s));
          if (!next.length) return { open: true, n };
          if (next.length > 1 || next[0][1] - next[0][0] >= narrow || n >= 1000) return { open: false, n };
          k += dir; s = next[0]; n++;
        }
      };
      const up = reach(-1), down = reach(1);
      const rows = up.n + down.n + 1;
      return { cls: up.open && down.open ? (rows > 1 ? "sliver" : "lone") : up.open || down.open ? "tip" : "waist", rows };
    }
    if (isEnd(ka, A.x) && isEnd(ka, B.x)) return { cls: Math.abs(A.x - B.x) <= SAME_PX ? "touch" : "gap", rows: 1 };
    return { cls: "other", rows: 1 };
  }
  if (ka >= 0 && kb >= 0 && Math.abs(ka - kb) === 1 && isEnd(ka, A.x) && isEnd(kb, B.x)) return { cls: "turn", rows: 2 };
  return { cls: "other", rows: 0 };
}

// One built design -> counts, and the pairs themselves.
function readDesign(des, passes, t, where) {
  const st = des.stitches || [], spans = des.runs || [], fit = des.fit;
  bump(t, "designs");
  bump(t, "stitches", des.stitchCount || 0);
  const same = (i) => st[i].type === "stitch" && st[i - 1].type === "stitch" && st[i].x === st[i - 1].x && st[i].y === st[i - 1].y;
  let inStream = 0;
  for (let i = 1; i < st.length; i++) if (same(i)) inStream++;
  bump(t, "cuts", st.filter((s) => s.type === "trim").length);
  // The same hole twice with only jumps between the two: the last stitch of
  // one run, and the first of the next when it begins on that spot (every run
  // opens with a jump). Not a pair as defined above, and counted apart.
  for (let i = 2; i < st.length; i++) {
    if (st[i].type !== "stitch" || st[i - 1].type !== "jump") continue;
    let j = i - 1, moved = false;
    while (j > 0 && st[j].type === "jump") { if (st[j].x !== st[i].x || st[j].y !== st[i].y) moved = true; j--; }
    if (st[j].type !== "stitch" || st[j].x !== st[i].x || st[j].y !== st[i].y) continue;
    bump(t, "over a jump");
    if (moved) bump(t, "over a jump that moved");
    if (PAIRS_OUT) {
      const span = spans.find((r) => i >= r.i0 && i <= r.i1) || {};
      t.pairs.push({ i: where.i, arm: where.arm, cls: moved ? "over a float" : "over a jump", kind: span.kind, at: i, records: st.slice(j, i + 2).map((r) => `${r.type[0]}${r.x},${r.y}`).join(" "), fabric: where.fabric, name: where.name });
    }
  }
  // Each pass to its span: one jump, then a record a point, every point within
  // half a unit of its record. -> the record index of each point, or null.
  // A point with NO record is allowed in one case only, and said (-1): a
  // stitch on the point this thread's last stitch is on. That is what a
  // builder with a rule against them (`dedupeHoles`) leaves out.
  const live = passes.filter((p) => p.pts.length);
  const fits = (q, r) => Math.abs((q.x - fit.cxPx) * fit.mmPerPx * 10 + fit.offsetXMm * 10 - r.x) <= 0.5 + 1e-6 && Math.abs((fit.cyPx - q.y) * fit.mmPerPx * 10 + fit.offsetYMm * 10 - r.y) <= 0.5 + 1e-6;
  const recordsOf = (pass, span) => {
    if (pass.pts.length < span.i1 - span.i0) return null;
    const at = [];
    // this thread's last stitch as the pass begins: jumps lay nothing, a cut
    // ends the thread
    let j = span.i0;
    while (j > 0 && st[j].type === "jump") j--;
    let i = span.i0 + 1, laid = st[j].type === "stitch" ? j : -1;
    for (const q of pass.pts) {
      if (i <= span.i1 && fits(q, st[i])) {
        if (st[i].type === "stitch") laid = i;
        else if (st[i].type !== "jump") laid = -1;
        at.push(i++);
        continue;
      }
      if (laid < 0 || q.travel || q.trim || !fits(q, st[laid])) return null;
      at.push(-1);
    }
    return i === span.i1 + 1 ? at : null;
  };
  let next = 0, found = 0, inPasses = 0;
  for (const span of spans) {
    const pass = live[next], at = pass ? recordsOf(pass, span) : null;
    if (!at) {
      // not a tatami pass: an edge run, a centre run, a satin column
      for (let i = span.i0 + 1; i <= span.i1; i++) if (same(i)) { bump(t, `outside/${span.kind}`); bump(t, `outside set/${where.set}/${span.kind}`); }
      continue;
    }
    next++; found++;
    const walk = pass.pts.columnWalk ? "column" : "plain", unitPx = UNIT_MM / fit.mmPerPx;
    bump(t, `passes/${walk}`);
    let fr = null;
    for (let k = 1; k < pass.pts.length; k++) {
      const i = at[k];
      if (i < 0) { bump(t, `left out/${walk}`); continue; }
      if (at[k - 1] !== i - 1 || st[i].type !== "stitch" || st[i - 1].type !== "stitch") continue;
      const a = pass.pts[k - 1], b = pass.pts[k], px = Math.hypot(b.x - a.x, b.y - a.y), mm = px * fit.mmPerPx;
      const together = st[i].x === st[i - 1].x && st[i].y === st[i - 1].y;
      if (mm < 1.0) bump(t, `length/${walk}/${bucketOf(px, mm)}/${together ? "one point" : "apart"}`);
      if (!together) continue;
      inPasses++;
      const exact = px <= SAME_PX;
      fr = fr || frameOf(pass);
      const why = whatMadeIt(fr, a, b, unitPx);
      bump(t, "pairs");
      bump(t, `walk/${walk}/${exact ? "exact" : "short"}`);
      bump(t, `kind/${span.kind}/${walk}`);
      bump(t, `why/${walk}/${why.cls}`);
      bump(t, `why+kind/${walk}/${span.kind}/${why.cls}`);
      bump(t, `fabric/${where.fabric}/pairs/${exact ? "exact" : "short"}`);
      bump(t, `set/${where.set}/pairs`);
      if (!exact) {
        bump(t, `short by/${walk}/${why.cls}`);
        bump(t, `short fabric/${where.fabric}/${why.cls}`);
        bump(t, `short angle/${where.angle}`);
        peak(t, `longest/${walk}`, mm);
        peak(t, `longest why/${why.cls}`, mm);
        if (why.cls === "tip" || why.cls === "sliver") bump(t, `strip rows/${why.cls}/${why.rows > 5 ? "6 and over" : why.rows}`);
      }
      if (PAIRS_OUT) t.pairs.push({ i: where.i, arm: where.arm, walk, kind: span.kind, k, px, mm, cls: why.cls, rows: why.rows, pitchMm: pass.opts.rowSpacing * fit.mmPerPx, rowAngle: pass.opts.angleDeg, fabric: where.fabric, name: where.name });
    }
  }
  const rest = inStream - inPasses;
  if (rest) { bump(t, "pairs", rest); bump(t, "pairs outside a tatami pass", rest); }
  if (live.length !== found) bump(t, "passes not found in the stream", live.length - found);
  if (inStream) { bump(t, "designs with a pair"); bump(t, `fabric/${where.fabric}/designs with a pair`); bump(t, `set/${where.set}/designs with a pair`); }
  bump(t, `fabric/${where.fabric}/designs`);
  bump(t, `set/${where.set}/designs`);
}

// How this engine's stream differs from the other engine's for one design.
// "second stitches only": take every stitch on the point its thread's last
// stitch is on out of both, and they are one stream; and this engine has no
// record the other lacks. So nothing moved, was added or was reordered. A jump
// lays nothing and changes nothing; a cut ends the thread.
function against(mine, theirs) {
  const key = (st) => st.map((s) => `${s.type},${s.x},${s.y}`);
  const a = key(mine), b = key(theirs);
  if (a.length === b.length && a.every((v, i) => v === b[i])) return "the same";
  const once = (st) => {
    const out = [];
    let hole = null;
    for (const s of st) {
      if (s.type === "stitch") {
        if (hole && hole.x === s.x && hole.y === s.y) continue;
        hole = s;
      } else if (s.type !== "jump") hole = null;
      out.push(s);
    }
    return out;
  };
  const a1 = key(once(mine)), b1 = key(once(theirs));
  if (mine.length < theirs.length && a1.length === b1.length && a1.every((v, i) => v === b1[i])) return "second stitches only";
  return "something else";
}

// A corpus that is not one of the two above: the path of a module whose
// default export, given the engine, returns { designs, build(d, extra, dg),
// tag(d) -> { fabric, angle, set } } as the two above do.
async function corpusNamed(name) {
  if (name === "sweep") return sweepCorpus();
  if (name === "studio") return studioCorpus();
  const mod = await import(pathToFileURL(resolve(name)).href);
  return (mod.default || mod)({ DG, FAB, GAR });
}
const CORPORA = WANT.length ? WANT : ["sweep", "studio"];

async function runPart(part, parts) {
  const out = {};
  for (const name of CORPORA) {
    const corpus = await corpusNamed(name), res = { absent: tally(), on: tally(), errors: 0 };
    corpus.designs.forEach((d, i) => {
      if (i % parts !== part) return;
      for (const arm of ["absent", "on"]) {
        try {
          PASSES = [];
          const des = corpus.build(d, ARMS[arm]);
          readDesign(des, PASSES, res[arm], Object.assign({ i, arm, name: d.name }, corpus.tag(d)));
          if (DG_OTHER) bump(res[arm], `against/${against(des.stitches, corpus.build(d, ARMS[arm], DG_OTHER).stitches)}`);
        } catch (e) { res.errors++; if (res.errors <= 3) console.error(`${name} ${i} ${arm}: ${e && e.stack || e}`); }
      }
    });
    out[name] = res;
  }
  return out;
}

if (PART) {
  const [part, parts] = PART.split("/").map(Number);
  const res = await runPart(part, parts);
  process.send(res, () => process.exit(0));
} else {
  const t0 = Date.now();
  const pass = [SRC].concat(...CORPORA.map((c) => ["--corpus", c]), ...ON_ARGS.map((v) => ["--on", v]), ...OFF_ARGS.map((v) => ["--off", v]), PAIRS_OUT ? ["--pairs", "1"] : [], AGAINST ? ["--against", AGAINST] : []);
  const parts = await Promise.all(Array.from({ length: JOBS }, (_, i) => new Promise((done, fail) => {
    const kid = fork(SELF, pass.concat(["--part", `${i}/${JOBS}`]));
    let got = null;
    kid.on("message", (m) => { got = m; });
    kid.on("exit", (code) => (got ? done(got) : fail(new Error(`part ${i} ended with ${code} and no result`))));
  })));
  const all = {};
  for (const name of CORPORA) {
    all[name] = { absent: tally(), on: tally(), errors: 0 };
    for (const p of parts) { merge(all[name].absent, p[name].absent); merge(all[name].on, p[name].on); all[name].errors += p[name].errors; }
  }
  if (PAIRS_OUT) {
    const lines = [];
    for (const name of CORPORA) for (const arm of ["absent", "on"]) for (const p of all[name][arm].pairs) lines.push(JSON.stringify(Object.assign({ corpus: name }, p)));
    writeFileSync(resolve(PAIRS_OUT), lines.join("\n") + "\n");
  }
  if (JSON_OUT) writeFileSync(resolve(JSON_OUT), JSON.stringify({ src: SRC, arms: ARMS, corpora: Object.fromEntries(CORPORA.map((c) => [c, { absent: { n: all[c].absent.n, max: all[c].absent.max }, on: { n: all[c].on.n, max: all[c].on.max }, errors: all[c].errors }])) }, null, 1));

  const num = (v) => (v || 0).toLocaleString("en-US");
  const under = (t, prefix) => Object.keys(t.n).filter((k) => k.startsWith(prefix)).sort();
  const table = (rows) => {
    const w = rows[0].map((_, c) => Math.max(...rows.map((r) => String(r[c]).length)));
    for (const r of rows) console.log("  " + r.map((v, c) => (c ? String(v).padStart(w[c]) : String(v).padEnd(w[c]))).join("  "));
  };
  console.log(`engine: ${SRC}${AGAINST ? `\nagainst: ${resolve(AGAINST)}` : ""}`);
  console.log(`arms: absent ${JSON.stringify(ARMS.absent)}, on ${JSON.stringify(ARMS.on)}`);
  for (const name of CORPORA) {
    const c = all[name];
    console.log(`\n=== corpus "${name}": ${num(c.absent.n.designs)} designs${c.errors ? `, ${c.errors} BUILDS FAILED` : ""} ===`);
    const both = (f) => [f(c.absent), f(c.on)];
    table([
      ["", "flag absent", "fillColumns on"],
      ["stitches", ...both((t) => num(t.n.stitches))],
      ["pairs of stitch records on one point", ...both((t) => num(t.n.pairs))],
      ["designs with one", ...both((t) => num(t.n["designs with a pair"]))],
      ["  plain walk, exact", ...both((t) => num(t.n["walk/plain/exact"]))],
      ["  plain walk, short", ...both((t) => num(t.n["walk/plain/short"]))],
      ["  column walk, exact", ...both((t) => num(t.n["walk/column/exact"]))],
      ["  column walk, short", ...both((t) => num(t.n["walk/column/short"]))],
      ["  outside a tatami pass", ...both((t) => num(t.n["pairs outside a tatami pass"]))],
      ["one hole twice with only a jump between", ...both((t) => num(t.n["over a jump"]))],
      ["  of them, the frame went away and came back", ...both((t) => num(t.n["over a jump that moved"]))],
      ["passes: plain walk", ...both((t) => num(t.n["passes/plain"]))],
      ["passes: column walk", ...both((t) => num(t.n["passes/column"]))],
      ["passes not found in the stream", ...both((t) => num(t.n["passes not found in the stream"]))],
      ["second stitches the builder left out", ...both((t) => num((t.n["left out/plain"] || 0) + (t.n["left out/column"] || 0)))],
      ["cuts", ...both((t) => num(t.n.cuts))],
      ...(AGAINST ? ["the same", "second stitches only", "something else"].map((k) => [`against the other engine: ${k}`, ...both((t) => num(t.n[`against/${k}`]))]) : []),
      ["longest short stitch, mm", ...both((t) => Math.max(t.max["longest/plain"] || 0, t.max["longest/column"] || 0).toFixed(4))],
    ]);
    for (const [arm, t] of [["flag absent", c.absent], ["fillColumns on", c.on]]) {
      console.log(`\n  -- ${arm}: what made each pair (pass kind, walk) --`);
      const keys = under(t, "why+kind/");
      table([["walk / pass / what", "pairs"]].concat(keys.map((k) => [k.slice(9), num(t.n[k])])));
      console.log(`\n  -- ${arm}: the SHORT ones (a real distance apart before rounding) --`);
      table([["walk / what", "pairs", "longest mm"]].concat(under(t, "short by/").map((k) => [k.slice(9), num(t.n[k]), (t.max[`longest why/${k.split("/")[2]}`] || 0).toFixed(4)])));
      table([["rows in the narrow strip", "pairs"]].concat(under(t, "strip rows/").map((k) => [k.slice(11), num(t.n[k])])));
      console.log(`\n  -- ${arm}: by fabric --`);
      const fabs = [...new Set(under(t, "fabric/").map((k) => k.split("/")[1]))];
      table([["fabric", "designs", "with a pair", "exact", "short"]].concat(fabs.map((f) => [f, num(t.n[`fabric/${f}/designs`]), num(t.n[`fabric/${f}/designs with a pair`]), num(t.n[`fabric/${f}/pairs/exact`]), num(t.n[`fabric/${f}/pairs/short`])])));
      const sets = [...new Set(under(t, "set/").map((k) => k.split("/")[1]))];
      table([["shapes", "designs", "with a pair", "pairs in tatami passes"]].concat(sets.map((s) => [s, num(t.n[`set/${s}/designs`]), num(t.n[`set/${s}/designs with a pair`]), num(t.n[`set/${s}/pairs`])])));
      if (under(t, "outside/").length) {
        console.log(`\n  -- ${arm}: pairs OUTSIDE a tatami pass, by the run they are in --`);
        table([["run", "pairs"]].concat(under(t, "outside/").map((k) => [k.slice(8), num(t.n[k])])));
        table([["shapes / run", "pairs"]].concat(under(t, "outside set/").map((k) => [k.slice(12), num(t.n[k])])));
      }
      console.log(`\n  -- ${arm}: every stitch of a tatami pass under 1 mm before rounding --`);
      const rowsOut = [["walk", "length before rounding, mm", "on one point", "apart"]];
      for (const walk of ["plain", "column"]) for (const b of ["exact"].concat(BUCKETS.map((q) => q[1]))) {
        const one = t.n[`length/${walk}/${b}/one point`] || 0, apart = t.n[`length/${walk}/${b}/apart`] || 0;
        if (one || apart) rowsOut.push([walk, b, num(one), num(apart)]);
      }
      table(rowsOut);
    }
  }
  console.log(`\n${((Date.now() - t0) / 1000).toFixed(0)} s, ${JOBS} jobs`);
}
