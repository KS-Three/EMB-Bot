// A ring handed over CLOSED says its first point again at the end. What that
// does to buildQualityDesign, who hands one over, and what does not move.
//
//   node tools/closed-ring-census.mjs [srcDir]                   the four tables
//   node tools/closed-ring-census.mjs [srcDir] --art             ... and every other PNG fixture once through the image lane
//   node tools/closed-ring-census.mjs [srcDir] --hash out.json   a hash of every output on rings that say no point twice
//   node tools/closed-ring-census.mjs --compare a.json b.json    do two such files agree, and were they two engines
//
// srcDir: the engine to measure (default: this checkout's src). Point it at
// another checkout to measure that one, which is how every "before" in
// docs/scope-history.md was made. The Studio's lane code is always this
// checkout's.
//
// THE DEFECT (fixed 2026-10-03). The repeated point is an edge of no length,
// with no direction and so no normal. `offsetRing` moved each of its two ends
// along the one real edge beside it, the first by the whole mitre clamp:
// three times the distance. Under a fabric preset the fill is sewn to the
// offset rings, so that wedge was sewn.
//
// 1. THE WEDGE, preset by preset, on a 40 mm box, an island in it, and both
//    as drawn open.
// 2. CLOSED AGAINST OPEN: every design below with every ring closed, against
//    itself open, built by the SAME engine. The angle is fixed, because the
//    auto angle is read off the points and a point said twice is one more.
//    "Fill" is the fill runs; "stream" is every record.
// 3. WHO HANDS ONE OVER: the Studio's own generateElement, with the builder
//    watched for the rings it is given. Three lanes reach it.
// 4. THE NEAR REPEAT, which the fix of 2026-10-03 did NOT reach (MASTER_SCOPE
//    defect 55; offsetRing drops one shorter than the offset since 2026-10-08):
//    a hand-drawn shape with an anchor a pixel or two from the one before it.
//    The short edge doubles back and gets the same clamp. Until 2026-10-03 a
//    double-click whose second click slipped more than half a canvas pixel
//    left one (ManualPanel now lets that click go by); a shape saved before
//    then still carries it, and two anchors dragged together make another.
import "./_help.mjs";
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { decodePNG, downscale } from "./png.mjs";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i < 0 ? null : args.slice(i + 1); };

if (opt("--compare")) {
  const [a, b] = opt("--compare").map((f) => JSON.parse(readFileSync(resolve(f), "utf8")));
  const made = [a, b].map((o) => { const e = o.__engine || { src: "(not recorded)", sha: "" }; delete o.__engine; return e; });
  made.forEach((e, i) => console.log(`${i ? "b" : "a"}: engine ${e.sha || "?"} at ${e.src}`));
  // Two files from ONE engine agree by construction, and that proves nothing.
  if (made[0].sha && made[0].sha === made[1].sha) { console.log("BOTH FILES WERE MADE BY THE SAME ENGINE: nothing has been compared."); process.exit(2); }
  const keys = Object.keys(a), differ = keys.filter((k) => a[k] !== b[k]), missing = keys.filter((k) => !(k in b)).length + Object.keys(b).filter((k) => !(k in a)).length;
  console.log(`${keys.length} outputs, ${new Set(Object.values(a)).size} distinct; in one file only: ${missing}; DIFFERENT: ${differ.length}`);
  for (const k of differ.slice(0, 20)) console.log("  " + k);
  process.exit(differ.length || missing ? 1 : 0);
}

const SRC = resolve(args[0] && !args[0].startsWith("--") ? args[0] : join(ROOT, "src"));
// the Studio's own list and order (app/src/lib/emb.js), less the two that draw
globalThis.window = globalThis;
const ENGINE_FILES = ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel", "digitize"];
for (const f of ENGINE_FILES) require(join(SRC, f + ".js"));
// which engine this is: its files' text, line endings aside
const ENGINE = { src: SRC, sha: createHash("sha256").update(ENGINE_FILES.map((f) => readFileSync(join(SRC, f + ".js"), "utf8").replace(/\r\n/g, "\n")).join("\0")).digest("hex").slice(0, 16) };
const EMB = globalThis.EMB;
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { generateElement } = await lib("generate.js");
const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
const { shapesToRegions, shapeIssues, flattenShape, isValidShape, isDuplicateOfLast, isNearStart } = await lib("manualShapes.js");
const { shapePresetPoints } = await lib("shapePresets.js");
const { traceShapesFromRGBA } = await lib("manualTrace.js");
const build = EMB.buildQualityDesign;
const PRESETS = EMB.FABRICS.map((f) => f.id);

const P = (x, y) => ({ x, y });
const ring = (pts) => pts.map(([x, y]) => P(x, y));
const box = (x0, y0, x1, y1) => [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)];
const ngon = (cx, cy, rx, ry, n, ph = 0) => Array.from({ length: n }, (_, i) => P(cx + rx * Math.cos(2 * Math.PI * i / n + ph), cy + ry * Math.sin(2 * Math.PI * i / n + ph)));
const star = (cx, cy, r, n, ratio) => Array.from({ length: 2 * n }, (_, i) => { const rr = i % 2 ? r * ratio : r, a = -Math.PI / 2 + i * Math.PI / n; return P(cx + rr * Math.cos(a), cy + rr * Math.sin(a)); });
const closed = (r) => r.concat([{ x: r[0].x, y: r[0].y }]);
const clone = (o) => JSON.parse(JSON.stringify(o));
const sha = (s) => createHash("sha256").update(s).digest("hex").slice(0, 24);
const widthOf = (regions) => { let a = Infinity, b = -Infinity; for (const r of regions) for (const s of r.shapes) for (const q of s.outer) { a = Math.min(a, q.x); b = Math.max(b, q.x); } return b - a; };
// a point said twice running, as the engine reads it (distinctCorners: 1e-9 px on both axes)
const repeats = (r) => r.filter((p, i) => { const q = r[(i + 1) % r.length]; return !(Math.abs(p.x - q.x) > 1e-9 || Math.abs(p.y - q.y) > 1e-9); }).length;
const shortestEdge = (r) => Math.min(...r.map((p, i) => Math.hypot(p.x - r[(i + 1) % r.length].x, p.y - r[(i + 1) % r.length].y)));

// The repo's own artwork at the Studio's working size (ImagePanel.prepRGBA).
const ART_DIR = join(ROOT, "digitizer", "testdata");
function art(rel) {
  let img = decodePNG(join(ART_DIR, rel));
  if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);   // never scaled up
  const rgba = Uint8ClampedArray.from(img.rgba);
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
  return { rgba, w: img.width, h: img.height };
}
const lcg = (seed) => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
function noiseFlat(rnd, t) {
  const w = 16 + Math.floor(rnd() * 80), h = 16 + Math.floor(rnd() * 80), K = 2 + Math.floor(rnd() * 3);
  const indices = new Uint8Array(w * h), p = [0.5, 0.3, 0.15, 0.05][t % 4];
  let cur = 0;
  for (let i = 0; i < w * h; i++) { if (rnd() < p) cur = Math.floor(rnd() * K); indices[i] = cur; }
  return { palette: Array.from({ length: K }, (_, k) => [k * 60, 40 + k * 50, 200 - k * 60]), indices, w, h };
}

// ---- the designs: 10 px per mm unless a lane says otherwise ------------------
function designs() {
  const out = [];
  const add = (name, regions, opts, pxPerMm = 10) => out.push({ name, regions, pxPerMm, opts: Object.assign({ darkOnTop: false }, opts) });
  const hand = (name, shape, opts) => { const regions = [{ rgb: [27, 58, 92], shapes: [Object.assign({ tierOverride: "fill" }, shape)] }]; add("hand: " + name, regions, Object.assign({ targetWidthMm: widthOf(regions) / 10 }, opts)); };
  hand("box 40", { outer: box(0, 0, 400, 400), holes: [] });
  hand("bar 30 x 12", { outer: box(0, 0, 300, 120), holes: [] });
  hand("triangle", { outer: ring([[0, 300], [200, 0], [400, 300]]), holes: [] });
  hand("L", { outer: ring([[0, 0], [400, 0], [400, 150], [150, 150], [150, 400], [0, 400]]), holes: [] });
  hand("U", { outer: ring([[250, 0], [360, 0], [360, 360], [0, 360], [0, 0], [110, 0], [110, 240], [250, 240]]), holes: [] });
  hand("T", { outer: ring([[0, 0], [400, 0], [400, 100], [250, 100], [250, 400], [150, 400], [150, 100], [0, 100]]), holes: [] });
  hand("plus", { outer: ring([[150, 0], [250, 0], [250, 150], [400, 150], [400, 250], [250, 250], [250, 400], [150, 400], [150, 250], [0, 250], [0, 150], [150, 150]]), holes: [] });
  hand("comb", { outer: ring([[0, 0], [440, 0], [440, 300], [380, 300], [380, 80], [320, 80], [320, 300], [260, 300], [260, 80], [200, 80], [200, 300], [140, 300], [140, 80], [80, 80], [80, 300], [0, 300]]), holes: [] });
  hand("badge, two counters", { outer: box(0, 0, 260, 360), holes: [box(80, 60, 180, 140), box(80, 200, 200, 300)] });
  hand("box, a 0.2 mm slot", { outer: box(0, 0, 400, 400), holes: [box(199, 100, 201, 300)] });
  for (const w of [4, 6, 7, 8, 10, 12]) hand(`box, a slot ${w / 10} mm (twice a preset's pull)`, { outer: box(0, 0, 400, 400), holes: [box(200 - w / 2, 100, 200 + w / 2, 300)] });
  hand("bullseye", { outer: box(0, 0, 400, 400), holes: [box(80, 80, 320, 320), box(160, 160, 240, 240)] });
  hand("island near its hole's wall", { outer: box(0, 0, 400, 400), holes: [box(80, 80, 320, 320), box(90, 90, 310, 310)] });
  hand("four nested rings", { outer: box(0, 0, 400, 400), holes: [box(40, 40, 360, 360), box(80, 80, 320, 320), box(140, 140, 260, 260)] });
  hand("ellipse, an ellipse hole", { outer: ngon(150, 180, 150, 180, 64), holes: [ngon(150, 180, 70, 100, 40)] });
  hand("star 5", { outer: star(200, 200, 200, 5, 0.45), holes: [] });
  hand("star 12, thin tips", { outer: star(200, 200, 200, 12, 0.2), holes: [] });
  hand("box 2 mm", { outer: box(0, 0, 20, 20), holes: [] });
  hand("triangle 1.5 mm", { outer: ring([[0, 13], [7.5, 0], [15, 13]]), holes: [] });
  hand("circle of 200 corners, round hole", { outer: ngon(200, 200, 200, 200, 200), holes: [ngon(200, 200, 60, 60, 90)] });
  hand("sawtooth edge", { outer: ring(Array.from({ length: 21 }, (_, i) => [i * 20, i % 2 ? 30 : 0]).concat([[400, 300], [0, 300]])), holes: [] });
  hand("a spike that doubles back", { outer: ring([[0, 0], [200, 0], [100, 0], [100, 100], [0, 100]]), holes: [] });
  hand("box and hole wound the other way", { outer: box(0, 0, 400, 400).reverse(), holes: [box(100, 100, 300, 300).reverse()] });
  hand("holed box sewn at 100 mm", { outer: box(0, 0, 400, 400), holes: [box(100, 100, 300, 300)] }, { targetWidthMm: 100 });
  hand("holed box sewn at 12 mm", { outer: box(0, 0, 400, 400), holes: [box(100, 100, 300, 300)] }, { targetWidthMm: 12 });
  add("hand: thin bar, tier left to the engine", [{ rgb: [27, 58, 92], shapes: [{ outer: box(0, 0, 400, 30), holes: [] }] }], { targetWidthMm: 40 });
  add("hand: thin C, forced satin", [{ rgb: [27, 58, 92], shapes: [{ outer: ring([[0, 0], [200, 0], [200, 20], [20, 20], [20, 180], [200, 180], [200, 200], [0, 200]]), holes: [], tierOverride: "satin" }] }], { targetWidthMm: 20 });
  add("hand: three shapes, two colours, sorted light to dark", [
    { rgb: [240, 240, 240], shapes: [{ outer: box(0, 0, 200, 200), holes: [box(60, 60, 140, 140)] }, { outer: ngon(320, 100, 70, 90, 24), holes: [] }] },
    { rgb: [10, 10, 10], shapes: [{ outer: box(0, 240, 400, 320), holes: [] }] },
  ], { targetWidthMm: 40, darkOnTop: undefined });

  // shapes nobody chose
  const rnd = lcg(20261003);
  for (let t = 0; t < 60; t++) {
    const n = 5 + Math.floor(rnd() * 36), R = 60 + rnd() * 190, ph = rnd() * 6.28;
    const rad = Array.from({ length: n }, () => R * (0.45 + 0.55 * rnd()));
    const outer = rad.map((r, i) => P(300 + r * Math.cos(2 * Math.PI * i / n + ph), 300 + r * Math.sin(2 * Math.PI * i / n + ph)));
    const rmin = Math.min(...rad), holes = [], k = Math.floor(rnd() * 4);
    for (let h = 0; h < k; h++) {
      const a = (h + rnd() * 0.5) * 2 * Math.PI / k, d = rmin * 0.38, hr = rmin * (0.08 + 0.1 * rnd()), hn = 3 + Math.floor(rnd() * 12);
      const c = k === 1 ? P(300, 300) : P(300 + d * Math.cos(a), 300 + d * Math.sin(a));
      holes.push(ngon(c.x, c.y, hr, hr * (0.6 + 0.4 * rnd()), hn, rnd() * 6.28));
      if (t % 5 === 0 && h === 0) holes.push(ngon(c.x, c.y, hr * 0.4, hr * 0.3, 3 + Math.floor(rnd() * 6), rnd() * 6.28));   // an island
    }
    const regions = [{ rgb: [Math.floor(rnd() * 255), Math.floor(rnd() * 255), Math.floor(rnd() * 255)], shapes: [Object.assign({ outer, holes }, t % 3 ? { tierOverride: "fill" } : {})] }];
    add(`seeded: ${t}, ${n} corners, ${holes.length} rings inside`, regions, { targetWidthMm: (widthOf(regions) / 10) * [1, 0.5, 2.5][t % 3] });
  }

  // the Studio's lanes: basic shapes, hand-drawn shapes with curves and cut-outs, the image lane
  for (const s of [8, 20, 37.3, 50, 90]) {
    for (const [kind, params] of [["circle", {}], ["heart", {}], ["rect", { heightMm: 30, cornerRadiusMm: 0 }], ["rect", { heightMm: 12, cornerRadiusMm: 3 }], ["rect", { heightMm: 30, cornerRadiusMm: 1000 }],
      ["star", { points: 5, innerRatio: 0.45 }], ["star", { points: 8, innerRatio: 0.3 }], ["star", { points: 3, innerRatio: 0.15 }]]) {
      const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points: shapePresetPoints(kind, params, s), curves: {}, stitchType: "auto", colorRgb: [27, 58, 92], angleDeg: null }]);
      if (regions.length) add(`basic shape: ${kind} ${JSON.stringify(params)} ${s} mm`, regions, { targetWidthMm: s }, pxPerMm);
    }
  }
  const fill = { curves: {}, stitchType: "fill", colorRgb: [10, 10, 10] };
  const manual = {
    "two boxes, one side curved": [
      { id: "s1", ...fill, points: [P(60, 60), P(260, 60), P(260, 220), P(60, 220)], curves: { 1: P(320, 140) }, colorRgb: [20, 20, 120] },
      { id: "s2", ...fill, points: [P(320, 80), P(520, 80), P(520, 300), P(320, 300)], colorRgb: [200, 180, 40], angleDeg: 30 }],
    "a D with a cut-out": [
      { id: "s1", ...fill, points: [P(100, 60), P(260, 60), P(260, 340), P(100, 340)], curves: { 1: P(460, 200) } },
      { id: "s2", ...fill, points: [P(150, 130), P(230, 130), P(230, 270), P(150, 270)], curves: { 1: P(300, 200) }, cutOut: true }],
    "a U, a bar forced satin, a triangle": [
      { id: "s1", ...fill, points: [P(40, 40), P(120, 40), P(120, 260), P(240, 260), P(240, 40), P(320, 40), P(320, 340), P(40, 340)], colorRgb: [150, 20, 20] },
      { id: "s2", ...fill, points: [P(360, 60), P(560, 60), P(560, 78), P(360, 78)], stitchType: "satin", colorRgb: [20, 150, 20] },
      { id: "s3", ...fill, points: [P(380, 140), P(560, 340), P(360, 320)], colorRgb: [20, 20, 150] }],
    "a badge with three cut-outs": [
      { id: "s1", ...fill, points: [P(60, 40), P(540, 40), P(540, 360), P(60, 360)], curves: { 0: P(300, 0), 2: P(300, 400) }, colorRgb: [30, 60, 90] },
      { id: "s2", ...fill, points: [P(120, 120), P(200, 120), P(200, 280), P(120, 280)], cutOut: true },
      { id: "s3", ...fill, points: [P(260, 150), P(340, 150), P(300, 250)], cutOut: true },
      { id: "s4", ...fill, points: [P(400, 120), P(480, 120), P(480, 132), P(400, 132)], cutOut: true }],
  };
  for (const [name, shapes] of Object.entries(manual)) { const { regions, pxPerMm } = shapesToRegions(shapes); add("hand-drawn: " + name, regions, {}, pxPerMm); }
  for (const [rel, counts] of [["becker_marine_logo.png", [3]], ["photo/enthusiast_logo.png", [2, 4]], ["logo_alpha.png", [4]], ["logo_whitebg.png", [4]], ["ribbon_curve.png", [2]], ["photo/region_blobs.png", [4]], ["photo/summit_badge.png", [4]]]) {
    if (!existsSync(join(ART_DIR, rel))) continue;
    const a = art(rel);
    for (const nColors of counts) { const { regions, pxPerMm } = flatToRegions(flattenRGBA(a.rgba.slice(), a.w, a.h, { nColors, removeBg: false }), {}); if (regions.length) add(`image lane: ${rel}, ${nColors} colours`, regions, { satinMaxWidthMm: 3.0, darkOnTop: undefined }, pxPerMm); }
  }
  const noise = lcg(777);
  for (let t = 0; t < 6; t++) { const { regions, pxPerMm } = flatToRegions(noiseFlat(noise, t), {}); if (regions.length) add(`image lane: noise map ${t}, no smoothing`, regions, { satinMaxWidthMm: 3.0, darkOnTop: undefined }, pxPerMm); }
  for (const d of out) for (const r of d.regions) for (const s of r.shapes) for (const rg of [s.outer].concat(s.holes || [])) if (repeats(rg)) throw new Error("a ring that says a point twice in " + d.name);
  return out;
}

function made(d, fabricId, extra, how, garmentId = "left_chest") {
  const regions = clone(d.regions);
  if (how) for (const r of regions) for (const s of r.shapes) {
    s.angleOverride = 0;
    if (how === "closed") { s.outer = closed(s.outer); s.holes = (s.holes || []).map(closed); }
  }
  const opts = Object.assign({ garment: EMB.getGarment(garmentId), pxPerMm: d.pxPerMm, underlay: true }, clone(d.opts), extra);
  if (fabricId) opts.fabric = EMB.getFabric(fabricId);
  return build(regions, opts);
}
const runsOf = (d, kind) => (d.runs || []).filter((s) => s.kind === kind).map((s) => d.stitches.slice(s.i0, s.i1 + 1));
const runsHash = (runs) => sha(runs.map((r) => sha(JSON.stringify(r.map((s) => [s.x, s.y, s.type])))).sort().join());

// ---- --hash: everything the builder returns, on rings that say no point twice --
if (opt("--hash")) {
  const out = {}, all = designs();
  all.forEach((d, di) => {
    for (const fabricId of [null].concat(PRESETS)) for (const [fname, flag] of [["absent", {}], ["off", { fillColumns: false }], ["on", { fillColumns: true }]]) {
      const cases = [["", {}]];
      if (di % 4 === 0 && [null, "pique_knit", "terry_towel"].includes(fabricId) && fname !== "off") cases.push([" | no underlay", { underlay: false }], [" | ties", { ties: true }], [" | fillStagger", { fillStagger: true }], [" | hat front", {}, "hat_front"]);
      for (const [xname, x, garmentId] of cases) {
        const r = made(d, fabricId, Object.assign({}, flag, x), null, garmentId);
        out[`${d.name} | ${fabricId || "no fabric"} | fillColumns ${fname}${xname}`] = sha(JSON.stringify([r.stitches, r.colors, r.widthMM, r.heightMM, r.stitchCount, r.colorCount, r.runs, r.shapeOutlines, r.fit, r._debug]));
      }
    }
  });
  const n = Object.keys(out).length;
  out.__engine = ENGINE;
  writeFileSync(resolve(opt("--hash")[0]), JSON.stringify(out));
  console.log(`engine ${ENGINE.sha} at ${SRC}\n${n} outputs of ${all.length} designs hashed (none and ${PRESETS.length} presets; fillColumns absent, off, on) -> ${opt("--hash")[0]}`);
  process.exit(0);
}

console.log(`engine ${ENGINE.sha} at ${SRC}\n`);

// ---- 1. the wedge ---------------------------------------------------------------
{
  const fillOf = (shape, fabricId) => {
    const d = build([{ rgb: [0, 0, 0], shapes: [Object.assign({ tierOverride: "fill", angleOverride: 0 }, shape)] }],
      { garment: EMB.getGarment("left_chest"), pxPerMm: 10, targetWidthMm: 40, darkOnTop: false, underlay: true, fabric: EMB.getFabric(fabricId) });
    return runsOf(d, "fill").flat().filter((s) => s.type === "stitch");
  };
  const outer = box(0, 0, 400, 400), moat = box(80, 80, 320, 320), island = box(160, 160, 240, 240), mm = (u) => (u / 10).toFixed(1);
  // 1 px is 1 unit, the centre (200, 200): the box's top edge is 200 up, the island's 40
  const top = (r, f) => Math.max(...fillOf({ outer: r, holes: [] }, f).map((s) => s.y)) - 200;
  const past = (isl, f) => Math.max(...fillOf({ outer, holes: [moat, isl] }, f).filter((s) => Math.abs(s.x) < 100 && Math.abs(s.y) < 100).map((s) => Math.abs(s.y))) - 40;
  console.log("1. THE WEDGE: mm of fill past the drawn edge, at its furthest (40 mm box; an 8 mm island in a 24 mm hole in it)\n");
  console.log("| preset | pull comp mm | outline closed | outline open | island closed | island open |\n|---|---|---|---|---|---|");
  for (const f of PRESETS) console.log(`| ${f} | ${EMB.getFabric(f).pullCompMm} | ${mm(top(closed(outer), f))} | ${mm(top(outer, f))} | ${mm(past(closed(island), f))} | ${mm(past(island, f))} |`);
}

// How far (units of 0.1 mm) the stitches of runs `a` lie from the thread of
// runs `b`, at the worst. b's segments are kept in 3 mm cells: one within a
// cell's width of a point is in the point's cell or one beside it.
function furthestFrom(a, b) {
  const CELL = 30, grid = new Map(), segs = [], key = (i, j) => i * 100003 + j;
  for (const r of b) for (let i = 1; i < r.length; i++) {
    const u = r[i - 1], v = r[i], si = segs.push([u, v]) - 1;
    for (let ci = Math.floor(Math.min(u.x, v.x) / CELL); ci <= Math.floor(Math.max(u.x, v.x) / CELL); ci++) {
      for (let cj = Math.floor(Math.min(u.y, v.y) / CELL); cj <= Math.floor(Math.max(u.y, v.y) / CELL); cj++) { const k = key(ci, cj); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(si); }
    }
  }
  const dist = (s, [u, v]) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy, t = l2 ? Math.max(0, Math.min(1, ((s.x - u.x) * dx + (s.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(s.x - (u.x + t * dx), s.y - (u.y + t * dy));
  };
  let worst = 0;
  for (const r of a) for (const s of r) {
    if (s.type !== "stitch") continue;
    const ci = Math.floor(s.x / CELL), cj = Math.floor(s.y / CELL);
    let best = Infinity;
    for (let i = ci - 1; i <= ci + 1; i++) for (let j = cj - 1; j <= cj + 1; j++) for (const si of grid.get(key(i, j)) || []) best = Math.min(best, dist(s, segs[si]));
    if (best > CELL) best = segs.reduce((m, sg) => Math.min(m, dist(s, sg)), Infinity);   // nothing near: ask them all
    if (best < Infinity && best > worst) worst = best;
  }
  return worst;
}

// ---- 2. closed against open -----------------------------------------------------
{
  const all = designs();
  const groups = {};
  for (const d of all) for (const fabricId of [null].concat(PRESETS)) for (const cols of [false, true]) {
    const g = groups[`${fabricId ? "a preset" : "no fabric"}, fillColumns ${cols ? "on" : "absent"}`] ||= { n: 0, fill: 0, order: 0, stream: 0, near: 0, far: 0, worst: "" };
    const c = made(d, fabricId, cols ? { fillColumns: true } : {}, "closed"), o = made(d, fabricId, cols ? { fillColumns: true } : {}, "open");
    g.n++;
    // the same fill runs whatever order a colour's shapes came in; then, the order
    if (runsHash(runsOf(c, "fill")) !== runsHash(runsOf(o, "fill"))) g.fill++;
    else if (JSON.stringify(runsOf(c, "fill")) !== JSON.stringify(runsOf(o, "fill"))) g.order++;
    if (sha(JSON.stringify(c.stitches)) === sha(JSON.stringify(o.stitches))) continue;
    g.stream++;
    // what is left once the fill is the same: the underlay, read off the points
    const uc = runsOf(c, "underlay"), uo = runsOf(o, "underlay"), u = Math.max(furthestFrom(uc, uo), furthestFrom(uo, uc)) / 10;
    if (u <= 0.2) g.near++;
    if (u > g.far) { g.far = u; g.worst = `${d.name}, ${fabricId || "no fabric"}`; }
  }
  console.log(`\n2. CLOSED AGAINST OPEN: ${all.length} designs, every ring closed, against the same design open\n`);
  console.log("| | outputs | fill differs | same fills, another order | stream differs | of those, underlay within 0.2 mm of the open one's | underlay furthest, mm |\n|---|---|---|---|---|---|---|");
  for (const [name, g] of Object.entries(groups)) console.log(`| ${name} | ${g.n} | ${g.fill} | ${g.order} | ${g.stream} | ${g.near} | ${g.far.toFixed(1)} (${g.worst}) |`);
}

// ---- 3. who hands one over ------------------------------------------------------
{
  const tally = {};
  let lane = "", last = null;
  EMB.buildQualityDesign = (regions, opts) => {
    const t = tally[lane] ||= { calls: 0, withFabric: 0, rings: 0, closed: 0, shortest: Infinity };
    t.calls++; if (opts && opts.fabric) t.withFabric++;
    last = [];
    for (const r of regions) for (const s of r.shapes || []) for (const rg of [s.outer].concat(s.holes || [])) { t.rings++; const n = repeats(rg); if (n) t.closed++; t.shortest = Math.min(t.shortest, shortestEdge(rg)); last.push(n); }
    return { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, runs: [], shapeOutlines: [], fit: null };
  };
  const garments = ["left_chest", "hat_front", "full_back"].map((g) => EMB.getGarment(g));
  const base = { underlay: true, sizeMm: null, offsetXMm: 0, offsetYMm: 0 };

  lane = "basic shapes";
  for (const g of garments) for (const s of [1, 2, 5, 10, 20, 37.3, 50, 80, 100, 150, 250, 300, null]) {
    const shape = (kind, params) => generateElement({ ...base, id: "p", type: "shape", kind, params, sizeMm: s, colorRgb: [0, 0, 0] }, g, {});
    shape("circle", {}); shape("heart", {});
    for (const heightMm of [1, 5, 30, 50, 100]) for (const cornerRadiusMm of [0, 0.005, 0.05, 0.1, 0.5, 2, 5, 15, 25, 1000]) shape("rect", { heightMm, cornerRadiusMm });
    for (let points = 3; points <= 12; points++) for (const innerRatio of [0.15, 0.3, 0.45, 0.6, 0.9]) shape("star", { points, innerRatio });
  }

  // Hand-drawn: what the lane does with a shape whose own points repeat. A
  // row is one drawing, or sixteen (the last point set `gap` px from the
  // first, in sixteen directions): how many the lane takes as valid, and of
  // the rings the builder is then given, how many the ENGINE reads as saying
  // a point twice (1e-9 px).
  const sq = box(100, 100, 300, 300), fill = { curves: {}, stitchType: "fill", colorRgb: [0, 0, 0] };
  const near = (gap) => Array.from({ length: 16 }, (_, k) => [{ id: "s1", ...fill, points: sq.concat([P(100 + gap * Math.cos(k * Math.PI / 8 + 0.2), 100 + gap * Math.sin(k * Math.PI / 8 + 0.2))]) }]);
  const drawn = {
    "a box, open": [[{ id: "s1", ...fill, points: sq }]],
    "the box closed": [[{ id: "s1", ...fill, points: closed(sq) }]],
    "the box, a middle corner said twice": [[{ id: "s1", ...fill, points: [sq[0], sq[1], P(300, 100), sq[2], sq[3]] }]],
    "the box closed, its closing side curved": [[{ id: "s1", ...fill, points: closed(sq), curves: { 3: P(60, 200) } }]],
    "an open box with a closed cut-out": [[{ id: "s1", ...fill, points: sq }, { id: "s2", ...fill, points: closed(box(150, 150, 250, 250)), cutOut: true }]],
    "the box closed to within 1e-12 px": near(1e-12),
    "the box closed to within 1e-10 px": near(1e-10),
    "the box closed to within 1e-6 px": near(1e-6),
  };
  const rows = [];
  for (const [name, drawings] of Object.entries(drawn)) {
    let valid = 0, rings = 0, twice = 0;
    for (const shapes of drawings) {
      lane = "hand-drawn (the cases below)"; last = null;
      generateElement({ ...base, id: "m", type: "manual", shapes }, garments[0], {});
      if (shapes.every((s) => !shapeIssues(flattenShape(s.points, s.curves, true)).length)) valid++;
      if (last) { rings += last.length; twice += last.filter(Boolean).length; }
    }
    rows.push(`| ${name} | ${drawings.length} | ${valid} | ${rings} | ${twice} |`);
  }
  delete tally["hand-drawn (the cases below)"];   // made to repeat, not what the lane makes: they have their own table

  const full = ["becker_marine_logo.png", "logo_alpha.png", "logo_whitebg.png", "ribbon_curve.png", "photo/enthusiast_logo.png", "photo/region_blobs.png", "photo/summit_badge.png"].filter((f) => existsSync(join(ART_DIR, f)));
  for (const rel of full) {
    const a = art(rel);
    lane = "image lane, seven PNG fixtures, 2 4 and 8 colours, background kept and removed";
    for (const nColors of [2, 4, 8]) for (const removeBg of [false, true]) generateElement({ ...base, id: "i", type: "image", threadRgb: {} }, garments[nColors % 3], { flats: { i: flattenRGBA(a.rgba.slice(), a.w, a.h, { nColors, removeBg }) } });
    lane = "trace import, the same seven";
    const traced = traceShapesFromRGBA(a.rgba.slice(), a.w, a.h, {});
    const shapes = Array.isArray(traced) ? traced : traced.shapes || [];
    if (shapes.length) generateElement({ ...base, id: "t", type: "manual", shapes }, garments[0], {});
  }
  if (opt("--art")) {
    // every other PNG fixture, photographs too: once, at four colours (six
    // flattens and a trace of each photograph is an hour and a half)
    lane = "image lane, every other PNG fixture, 4 colours";
    for (const rel of ["", "photo"].flatMap((sub) => readdirSync(join(ART_DIR, sub)).filter((f) => f.endsWith(".png")).map((f) => (sub ? sub + "/" : "") + f))) {
      if (full.includes(rel)) continue;
      const a = art(rel);
      generateElement({ ...base, id: "i", type: "image", threadRgb: {} }, garments[0], { flats: { i: flattenRGBA(a.rgba.slice(), a.w, a.h, { nColors: 4, removeBg: false }) } });
    }
  }
  lane = "image lane, 400 noise maps with no smoothing";
  const rnd = lcg(12345);
  for (let t = 0; t < 400; t++) generateElement({ ...base, id: "i", type: "image", threadRgb: {} }, garments[t % 3], { flats: { i: noiseFlat(rnd, t) } });
  EMB.buildQualityDesign = build;

  console.log("\n3. WHO HANDS ONE OVER: the rings generateElement gives the builder\n");
  console.log("| lane | calls | with a preset | rings | rings that say a point twice | shortest edge px |\n|---|---|---|---|---|---|");
  for (const [name, t] of Object.entries(tally)) console.log(`| ${name} | ${t.calls} | ${t.withFabric} | ${t.rings} | ${t.closed} | ${t.shortest.toFixed(2)} |`);
  console.log("\nA hand-drawn shape whose own points repeat:\n\n| drawn | drawings | taken as valid | rings the builder is given | of those, said twice as the engine reads it |\n|---|---|---|---|---|");
  for (const r of rows) console.log(r);
}

// ---- 4. the near repeat: an anchor a pixel or two from the last ------------------
{
  // The anchors a run of clicks left BEFORE 2026-10-03, when the second click
  // of a double-click was a click like any other: one within 10 px of the
  // first anchor finished the shape, one within 0.5 px of the last was
  // dropped, any other was an anchor. Then dblclick -> finishShape, which
  // keeps the shape if isValidShape says so. (ManualPanel.onCanvasClick now
  // lets that second click go by, so it makes no new one; these are the
  // shapes already saved.)
  const drawnBy = (clicks) => {
    let draft = [];
    for (const c of clicks) {
      if (draft.length >= 2 && isNearStart(draft, c.x, c.y)) break;
      if (isDuplicateOfLast(draft, c.x, c.y)) continue;
      draft = [...draft, c];
    }
    return draft;
  };
  const toSeg = (p, u, v) => { const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy, t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0; return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)); };
  const within = (pt, poly) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const a = poly[i], b = poly[j]; if ((a.y > pt.y) !== (b.y > pt.y) && pt.x < (b.x - a.x) * (pt.y - a.y) / (b.y - a.y) + a.x) c = !c; } return c; };
  // mm of FILL past the ring AS DRAWN, every anchor of it, at the worst; the
  // options are generate.js's own for a hand-drawn shape, 40 mm wide
  const past = (points, fabricId) => {
    const { regions, pxPerMm } = shapesToRegions([{ id: "s1", points, curves: {}, stitchType: "fill", colorRgb: [0, 0, 0] }]);
    const d = build(regions, { garment: EMB.getGarment("left_chest"), fabric: EMB.getFabric(fabricId), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: 40, offsetXMm: 0, offsetYMm: 0 });
    let worst = 0;
    for (const s of runsOf(d, "fill").flat()) {
      if (s.type !== "stitch") continue;
      const p = { x: d.fit.cxPx + (s.x / 10 - d.fit.offsetXMm) / d.fit.mmPerPx, y: d.fit.cyPx - (s.y / 10 - d.fit.offsetYMm) / d.fit.mmPerPx };
      if (within(p, points)) continue;
      worst = Math.max(worst, Math.min(...points.map((u, i) => toSeg(p, u, points[(i + 1) % points.length]))) * d.fit.mmPerPx);
    }
    return worst;
  };
  const corners = box(100, 100, 300, 300);   // the fourth click is the double-click's first
  const clean = drawnBy(corners.concat([P(100.2, 300.3)])), slipped = drawnBy(corners.concat([P(99.8, 300.98)]));
  console.log("\n4. THE NEAR REPEAT (offsetRing drops a near repeat shorter than the offset since 2026-10-08): a box whose last anchor is a slipped second click, mm of fill past the ring as drawn\n");
  console.log(`As clicks were taken before 2026-10-03: a second click 0.36 px off was dropped (${clean.length} anchors), one 1 px off was kept (${slipped.length} anchors, valid: ${isValidShape(flattenShape(slipped, {}, true))}).\n`);
  console.log("| preset | pull comp mm | clean double-click | second click 1 px off | 80 slips of 0.6 to 3 px, 16 directions: refused as crossing | kept as an anchor | of those, over 0.15 mm further out than clean | worst |\n|---|---|---|---|---|---|---|---|");
  for (const f of PRESETS) {
    const base = past(clean, f);
    let refused = 0, kept = 0, over = 0, worst = 0;
    for (const mag of [0.6, 1, 1.5, 2, 3]) for (let k = 0; k < 16; k++) {
      const pts = drawnBy(corners.concat([P(100 + mag * Math.cos(k * Math.PI / 8 + 0.2), 300 + mag * Math.sin(k * Math.PI / 8 + 0.2))]));
      if (!isValidShape(flattenShape(pts, {}, true))) { refused++; continue; }
      kept++;
      const w = past(pts, f);
      if (w - base > 0.15) over++;
      worst = Math.max(worst, w);
    }
    console.log(`| ${f} | ${EMB.getFabric(f).pullCompMm} | ${base.toFixed(2)} | ${past(slipped, f).toFixed(2)} | ${refused} | ${kept} | ${over} | ${worst.toFixed(2)} |`);
  }
}
