// `fillColumns` off beside on, for the two Studio lanes that do not pass it
// yet: the basic-shape presets and the image lane ("Waiting on Kent" 22).
//
//   node tools/fill-columns-lanes.mjs [--lane control|shapes|image] [--json out.json]
//        [--src engineDir] [--on '{"option": value}']
//
// Each design is built the way app/src/lib/generate.js builds it (its shape
// and image branches, the Studio's own modules for the rings), once with the
// lane as shipped and once with `fillColumns: true`, and the two stitch
// streams are measured the same way:
//
//   stitches    needle penetrations (`stitch` records)
//   cuts        `trim` records
//   floats off  a FLOAT is a move made with the thread attached (a `jump`
//               after a stitch, no trim between). It is OFF THE FILL when it
//               runs deeper than OFF_MM outside the ground it belongs to: the
//               drawn shape (outline less its holes, `design.shapeOutlines`)
//               when both ends are in one shape's runs, else every shape of
//               the design. OFF_MM (0.8) clears a preset's pull compensation
//               (terry sews the fill 0.6 mm outside the drawing), a fill row
//               and a stitch's rounding, so what is counted is thread over a
//               hole, a notch or the outside, not the comp band.
//   rim lines   on the worst millimetre of any drawn rim: how many lines of
//               thread run along it -- segments within RIM_BAND_MM of the
//               millimetre's centre and within 30 deg of the rim's tangent,
//               not counting the fill's own rows (fill-run segments within
//               8 deg of the shape's dominant row direction).
//   travel      fill-run thread that is neither a row nor a row turn: a
//               segment off the row direction and longer than 0.5 mm. "over
//               sewn" is the part of it laid on cells (0.25 mm) a row of the
//               same shape already covered; "face" the part of that more
//               than OFF_MM inside the ground (not on the rim).
//   ms          build time, the faster of two builds.
//
// Nothing here has been sewn: these are measurements of the stitch stream the
// encoders are handed.
import { writeFileSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { performance } from "node:perf_hooks";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
// The app's modules find the engine on the global, as in a browser: load it in
// the Studio's own order (app/src/lib/emb.js), less the two that draw.
globalThis.window = globalThis;
// `--src dir` measures another engine (a candidate fix) the same way.
const SRC = opt("--src") ? resolve(opt("--src")) : join(ROOT, "src");
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(join(SRC, f + ".js"));
const DG = require(join(SRC, "digitize.js"));
const FAB = require(join(SRC, "fabrics.js"));
const GAR = require(join(SRC, "garments.js"));
const LANES = opt("--lane") ? [opt("--lane")] : ["control", "shapes", "image"];
const JSON_OUT = opt("--json");
// `--on '{"opt":true}'`: more builder options for the "on" arm, beside fillColumns.
// `--colors 4`: the image lane at these colour counts only (a quicker look).
const COLORS = opt("--colors") ? opt("--colors").split(",").map(Number) : [2, 4, 6];
const ON_EXTRA = opt("--on") ? JSON.parse(opt("--on")) : {};

const OFF_MM = 0.8, RIM_BAND_MM = 0.5, ROW_TOL_DEG = 8, CELL_MM = 0.25;

// ---- the lanes, as generate.js calls them ----------------------------------
const SHAPE_SIZES = [20, 50, 100];
const SHAPE_GARMENTS = ["left_chest", "hat_front", "towel"];
const SHAPE_KINDS = [
  ["circle", {}], ["rect", {}], ["rect", { cornerRadiusMm: 6 }], ["heart", {}],
  ["star", {}], ["star", { points: 8, innerRatio: 0.3 }], ["star", { points: 4, innerRatio: 0.6 }],
];
async function shapesLane() {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const out = [];
  for (const [kind, params] of SHAPE_KINDS) for (const sizeMm of SHAPE_SIZES) for (const gid of SHAPE_GARMENTS) {
    const garment = GAR.getGarment(gid);
    const label = `${kind}${Object.keys(params).length ? " " + JSON.stringify(params).replace(/"/g, "") : ""}`;
    out.push({ group: label, size: sizeMm, garment: gid, build: (extra) => {
      const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null }]);
      return DG.buildQualityDesign(regions, Object.assign({ garment, fabric: FAB.getFabric(FAB.fabricForGarment(gid)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0 }, extra));
    } });
  }
  return out;
}

// The instrument's control: two of tools/fill-columns-sheet.mjs's manual-lane
// shapes, whose answer is known (every row floats across the cut-out or the
// notch with the option off; none does with it on). A metric that reads the
// same off and on here cannot see the defect.
async function controlLane() {
  const PX = 10, mm = (pts) => pts.map(([x, y]) => ({ x: x * PX, y: y * PX }));
  const box = (x0, y0, x1, y1) => mm([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
  const shapes = {
    "badge, two cut-outs": { outer: box(0, 0, 40, 40), holes: [box(6, 14, 18, 26), box(28.5, 18.5, 31.5, 21.5)] },
    "wide U (a notch)": { outer: mm([[0, 0], [14, 0], [14, 18], [30, 18], [30, 0], [44, 0], [44, 28], [0, 28]]), holes: [] },
  };
  return Object.entries(shapes).map(([name, s]) => ({ group: name, size: 40, garment: "left_chest", build: (extra) =>
    DG.buildQualityDesign([{ rgb: [27, 58, 92], shapes: [{ id: "s", outer: s.outer, holes: s.holes, tierOverride: "fill" }] }],
      Object.assign({ garment: GAR.getGarment("left_chest"), fabric: FAB.getFabric(FAB.fabricForGarment("left_chest")), pxPerMm: PX, targetWidthMm: 40, darkOnTop: false, underlay: true }, extra)) }));
}

// Real artwork already in the repo (logos; no synthetic fixtures, no photos).
const ART = [
  "art/logo_golke_roofing.png", "art/logo_hotel_fremont_patch.png", "art/logo_mfab_hat.png", "art/logo_mfab_lc.png",
  "art/logo_toat_beanie.png", "art/logo_toat_machine.png", "becker_marine_logo.png", "logo_alpha.png",
  "logo_whitebg.png", "logo_script_tires.png", "photo/enthusiast_logo.png", "photo/summit_badge.png",
  "photo/logo_drone_thermal_badge.png", "photo/logo_gaulke_roofing.png",
];
async function imageLane() {
  const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
  const { flatToRegions } = await lib("imageRegions.js");
  const { decodePNG, downscale } = await import(pathToFileURL(join(ROOT, "tools", "png.mjs")).href);
  const out = [];
  for (const rel of ART) {
    let img = decodePNG(join(ROOT, "digitizer", "testdata", rel));
    if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
    const w = img.width, h = img.height;
    // the Studio's default element is nColors 4, removeBg true (project.js)
    for (const nColors of COLORS) {
      const rgba = Uint8ClampedArray.from(img.rgba);
      for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
      const reg = flatToRegions(flattenRGBA(rgba, w, h, { nColors, removeBg: true }));
      if (!reg.regions.length) continue;
      for (const gid of ["left_chest", "hat_front", "full_back"]) {
        const garment = GAR.getGarment(gid);
        out.push({ group: rel.replace(/^.*\//, ""), size: `${nColors} col`, garment: gid, build: (extra) => {
          const regions = JSON.parse(JSON.stringify(reg.regions));
          regions.forEach((r, ri) => r.shapes.forEach((s, si) => { s.id = `r${ri}s${si}`; }));
          return DG.buildQualityDesign(regions, Object.assign({ garment, fabric: FAB.getFabric(FAB.fabricForGarment(gid)), pxPerMm: reg.pxPerMm, satinMaxWidthMm: 3.0, underlay: true, offsetXMm: 0, offsetYMm: 0 }, extra));
        } });
      }
    }
  }
  return out;
}

// ---- geometry ----------------------------------------------------------------
const segDist = (px, py, ax, ay, bx, by) => {
  const dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
  const t = L ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / L)) : 0;
  return Math.hypot(px - ax - t * dx, py - ay - t * dy);
};
const inRing = (x, y, r) => {
  let c = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const [xi, yi] = r[i], [xj, yj] = r[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
};
// one drawn shape -> { rings, inside(x, y), edgeDist(x, y) } in mm, y up
function groundOf(outlines) {
  const shapes = outlines.filter((o) => !o.dropped && o.points && o.points.length > 2);
  const rings = shapes.flatMap((o) => [o.points].concat(o.holes || []));
  const inside = (x, y) => shapes.some((o) => inRing(x, y, o.points) && !(o.holes || []).some((h) => inRing(x, y, h)));
  const edgeDist = (x, y) => {
    let d = Infinity;
    for (const r of rings) for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length]; d = Math.min(d, segDist(x, y, a[0], a[1], b[0], b[1])); }
    return d;
  };
  return { rings, inside, edgeDist };
}
// deepest point of p->q outside the ground, mm
function depthOutside(g, p, q) {
  const L = Math.hypot(q.x - p.x, q.y - p.y), n = Math.max(1, Math.ceil(L / 0.1));
  let deepest = 0;
  for (let k = 0; k <= n; k++) {
    const x = p.x + ((q.x - p.x) * k) / n, y = p.y + ((q.y - p.y) * k) / n;
    if (!g.inside(x, y)) deepest = Math.max(deepest, g.edgeDist(x, y));
  }
  return deepest;
}
const angOf = (p, q) => ((Math.atan2(q.y - p.y, q.x - p.x) * 180) / Math.PI + 180) % 180;
const angDiff = (a, b) => { const d = Math.abs(a - b) % 180; return Math.min(d, 180 - d); };

// ---- one design --------------------------------------------------------------
function measure(d) {
  const st = d.stitches.map((s) => ({ x: s.x / 10, y: s.y / 10, type: s.type }));
  const runOf = new Array(st.length).fill(null);
  for (const r of d.runs || []) for (let i = r.i0; i <= r.i1 && i < st.length; i++) runOf[i] = r;
  const outlines = d.shapeOutlines || [];
  const byShape = new Map(outlines.map((o) => [o.id, groundOf([o])]));
  const all = groundOf(outlines);

  // every piece of thread on the cloth, in sewing order
  const segs = [];
  let attached = false, prev = null, prevStitch = -1;
  const floats = [];
  st.forEach((s, i) => {
    if (s.type === "end" || s.type === "stop") { attached = false; return; }
    if (s.type === "trim" || s.type === "color") { attached = false; prev = s; return; }
    if (prev && attached && (prev.x !== s.x || prev.y !== s.y)) {
      const seg = { p: prev, q: s, i, run: runOf[i], sewn: s.type === "stitch" };
      segs.push(seg);
      if (!seg.sewn) floats.push(Object.assign(seg, { from: prevStitch }));
    }
    if (s.type === "stitch") { attached = true; prevStitch = i; }
    prev = s;
  });

  // floats: a jump is often one of several records of one move; join them
  let floatsOff = 0, floatOffMm = 0, deepestOff = 0;
  for (let k = 0; k < floats.length;) {
    let e = k;
    while (e + 1 < floats.length && floats[e + 1].p === floats[e].q) e++;
    const a = floats[k].from, last = floats[e];
    let b = last.i + 1; while (b < st.length && st[b].type !== "stitch") b++;
    const ra = runOf[a], rb = runOf[b];
    const g = ra && rb && ra.shape === rb.shape && byShape.get(ra.shape) ? byShape.get(ra.shape) : all;
    let deep = 0, len = 0;
    for (let j = k; j <= e; j++) { deep = Math.max(deep, depthOutside(g, floats[j].p, floats[j].q)); len += Math.hypot(floats[j].q.x - floats[j].p.x, floats[j].q.y - floats[j].p.y); }
    if (deep > OFF_MM) { floatsOff++; floatOffMm += len; deepestOff = Math.max(deepestOff, deep); }
    k = e + 1;
  }

  // each shape's row direction: the length-weighted mode of its fill segments
  const rowAng = new Map();
  for (const o of outlines) {
    const hist = new Float64Array(180);
    for (const s of segs) if (s.sewn && s.run && s.run.kind === "fill" && s.run.shape === o.id) hist[Math.floor(angOf(s.p, s.q)) % 180] += Math.hypot(s.q.x - s.p.x, s.q.y - s.p.y);
    let best = -1, at = 0;
    for (let a = 0; a < 180; a++) { const v = hist[a] + hist[(a + 1) % 180] + hist[(a + 179) % 180]; if (v > best) { best = v; at = a + 0.5; } }
    if (best > 0) rowAng.set(o.id, at);
  }
  const isRow = (s) => s.run && s.run.kind === "fill" && rowAng.has(s.run.shape) && angDiff(angOf(s.p, s.q), rowAng.get(s.run.shape)) <= ROW_TOL_DEG;

  // travel inside fill runs, and how much of it lies on rows already sewn
  let travelMm = 0, overSewnMm = 0, faceOverSewnMm = 0;
  const cells = new Map(); // shape -> Set of covered cells
  const key = (x, y) => Math.floor(x / CELL_MM) * 100003 + Math.floor(y / CELL_MM);
  for (const s of segs) {
    if (!s.sewn || !s.run || s.run.kind !== "fill") continue;
    const sh = s.run.shape, L = Math.hypot(s.q.x - s.p.x, s.q.y - s.p.y), n = Math.max(1, Math.ceil(L / 0.1));
    if (!cells.has(sh)) cells.set(sh, new Set());
    const cov = cells.get(sh), g = byShape.get(sh) || all;
    if (isRow(s)) { for (let k = 0; k <= n; k++) cov.add(key(s.p.x + ((s.q.x - s.p.x) * k) / n, s.p.y + ((s.q.y - s.p.y) * k) / n)); continue; }
    if (L <= 0.5) continue;
    travelMm += L;
    for (let k = 0; k < n; k++) {
      const x = s.p.x + ((s.q.x - s.p.x) * (k + 0.5)) / n, y = s.p.y + ((s.q.y - s.p.y) * (k + 0.5)) / n;
      if (!cov.has(key(x, y))) continue;
      overSewnMm += L / n;
      if (g.inside(x, y) && g.edgeDist(x, y) > OFF_MM) faceOverSewnMm += L / n;
    }
  }

  // rim pile-up: lines of thread along the worst millimetre of drawn rim
  const grid = new Map(), G = 1;
  const gk = (cx, cy) => cx * 100003 + cy;
  segs.forEach((s, si) => {
    if (isRow(s)) return;
    const x0 = Math.floor(Math.min(s.p.x, s.q.x) / G), x1 = Math.floor(Math.max(s.p.x, s.q.x) / G);
    const y0 = Math.floor(Math.min(s.p.y, s.q.y) / G), y1 = Math.floor(Math.max(s.p.y, s.q.y) / G);
    for (let cx = x0; cx <= x1; cx++) for (let cy = y0; cy <= y1; cy++) { const k = gk(cx, cy); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(si); }
  });
  let rimWorst = 0;
  for (const r of all.rings) for (let i = 0; i < r.length; i++) {
    const a = r[i], b = r[(i + 1) % r.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const tang = angOf({ x: a[0], y: a[1] }, { x: b[0], y: b[1] });
    for (let t = 0.5; t < L; t += 1) {
      const cx = a[0] + ((b[0] - a[0]) * t) / L, cy = a[1] + ((b[1] - a[1]) * t) / L;
      const seen = new Set();
      for (let gx = Math.floor((cx - RIM_BAND_MM) / G); gx <= Math.floor((cx + RIM_BAND_MM) / G); gx++)
        for (let gy = Math.floor((cy - RIM_BAND_MM) / G); gy <= Math.floor((cy + RIM_BAND_MM) / G); gy++)
          for (const si of grid.get(gk(gx, gy)) || []) {
            if (seen.has(si)) continue;
            const s = segs[si];
            if (segDist(cx, cy, s.p.x, s.p.y, s.q.x, s.q.y) <= RIM_BAND_MM && angDiff(angOf(s.p, s.q), tang) <= 30 && Math.hypot(s.q.x - s.p.x, s.q.y - s.p.y) >= 0.2) seen.add(si);
          }
      rimWorst = Math.max(rimWorst, seen.size);
    }
  }

  return {
    stitches: st.filter((s) => s.type === "stitch").length,
    cuts: st.filter((s) => s.type === "trim").length,
    floatsOff, floatOffMm, deepestOff, rimWorst, travelMm, overSewnMm, faceOverSewnMm,
  };
}

function timed(build, extra) {
  let best = Infinity, d;
  for (let k = 0; k < 2; k++) { const t0 = performance.now(); d = build(extra); best = Math.min(best, performance.now() - t0); }
  return { d, ms: best };
}

// ---- run ---------------------------------------------------------------------
const pct = (a, b) => (a ? ((b - a) / a) * 100 : 0);
const r1 = (n) => Math.round(n * 10) / 10;
const results = {};
for (const lane of LANES) {
  const designs = await ({ shapes: shapesLane, image: imageLane, control: controlLane })[lane]();
  const rows = [];
  for (const des of designs) {
    const say = (m) => { if (process.env.PROGRESS) process.stderr.write(`${new Date().toISOString().slice(11, 19)} ${m}\n`); };
    say(`${des.group} ${des.size} ${des.garment}: off`);
    const off = timed(des.build, {});
    say(`on (off ${Math.round(off.ms)} ms)`);
    const on = timed(des.build, Object.assign({ fillColumns: true }, ON_EXTRA));
    say(`measure (on ${Math.round(on.ms)} ms)`);
    const same = JSON.stringify(off.d.stitches) === JSON.stringify(on.d.stitches);
    rows.push({ group: des.group, size: des.size, garment: des.garment, same, off: Object.assign(measure(off.d), { ms: off.ms }), on: Object.assign(measure(on.d), { ms: on.ms }) });
    say(`${rows.length}/${designs.length} done`);
  }
  results[lane] = rows;

  console.log(`\n## ${lane}: ${rows.length} designs, ${rows.filter((r) => r.same).length} byte-identical off and on\n`);
  console.log("| group | designs | changed | stitches off → on | worst Δ | cuts off → on | floats off the fill off → on (mm) | rim lines, worst mm (max) off → on | travel mm: all / over sewn rows / of that on the face, off → on | ms off → on (max) |");
  console.log("|---|---|---|---|---|---|---|---|---|---|");
  const groups = [...new Set(rows.map((r) => (lane === "shapes" ? `${r.group} @ ${r.size} mm` : r.group)))];
  const sum = (rs, arm, k) => rs.reduce((a, r) => a + r[arm][k], 0);
  const max = (rs, arm, k) => Math.max(...rs.map((r) => r[arm][k]));
  const tr = (rs, arm) => ["travelMm", "overSewnMm", "faceOverSewnMm"].map((k) => Math.round(sum(rs, arm, k))).join(" / ");
  const line = (name, rs) => {
    const so = sum(rs, "off", "stitches"), sn = sum(rs, "on", "stitches");
    const worst = Math.max(...rs.map((r) => pct(r.off.stitches, r.on.stitches)));
    console.log(`| ${name} | ${rs.length} | ${rs.filter((r) => !r.same).length} | ${so.toLocaleString("en-US")} → ${sn.toLocaleString("en-US")} (${pct(so, sn) >= 0 ? "+" : ""}${r1(pct(so, sn))}%) | ${worst >= 0 ? "+" : ""}${r1(worst)}% | ${sum(rs, "off", "cuts")} → ${sum(rs, "on", "cuts")} | ${sum(rs, "off", "floatsOff")} (${Math.round(sum(rs, "off", "floatOffMm"))}) → ${sum(rs, "on", "floatsOff")} (${Math.round(sum(rs, "on", "floatOffMm"))}) | ${max(rs, "off", "rimWorst")} → ${max(rs, "on", "rimWorst")} | ${tr(rs, "off")} → ${tr(rs, "on")} | ${Math.round(max(rs, "off", "ms"))} → ${Math.round(max(rs, "on", "ms"))} |`);
  };
  for (const g of groups) line(g, rows.filter((r) => (lane === "shapes" ? `${r.group} @ ${r.size} mm` : r.group) === g));
  line("**all**", rows);
}
if (JSON_OUT) writeFileSync(JSON_OUT, JSON.stringify(results, null, 1));
