// What a machine CUTS, read off the file and not off the builder's stream.
//
//   node tools/file-cut-census.mjs [srcDir] [--set shapes|lettering|image|file]...
//        [--on flag[=value]]... [--every K] [--jobs N] [--json out.json]
//        [--keep dir [--parts N]] [--against otherSrc]
//        [--pystitch python [--sample N] [--tmp dir]]
//
// srcDir: the engine to measure (default: this checkout's src).
// --on:   beside each arm of a set, the same arm with this builder option on.
// --every: every K-th design only, for a quick look.
// --against: build every design with a second engine too and say how the
//         two streams differ: not at all, by cuts put in and nothing else (a
//         jump turned into a trim where it stands, or a trim on the spot
//         before a jump), or some other way.
// --keep: the work is cut into N parts (48) and each finished part is kept in
//         this folder, so a run that is cut short picks up where it stopped.
//         One folder per set of arguments: a part is not checked against them.
//
// A DST has no "cut". Its writer lays a `trim` as three or more jump records,
// because a machine reads three jumps in a row as a cut (src/dst.js). But the
// writer also lays any MOVE too long for one record (12.1 mm an axis) as
// several, and a needle-up move as jumps. So a float of more than 24.2 mm is
// three jumps in a row too, and a reader cannot tell it from a cut. The
// builder did not ask for that cut: it wrote no `trim`, so nothing downstream
// that goes by `trim` records (the lock stitches, the counts) knows of it.
//
// THE FILE IS READ HERE, by this file's own readers of the three formats,
// written from the formats and not from the writers. Each design is written
// with the engine's writer, read back, and its records lined up with the
// stream's by where they land: a file that does not line up stops the run.
//
// A CUT IN THE FILE (DST): a run of three or more jump records. Each is put
// down to what it was in the stream:
//   trim          the builder asked for it (a `trim` record is in the run)
//   after colour  the move to a new colour's first stitch; the thread was cut
//   start         the move to the design's first stitch; no thread yet
//   between two runs of one shape, between shapes, inside a run
//                 thread attached, and no `trim` in the stream
// The last three are the cuts nobody asked for. EXP and PES have a trim of
// their own, so there the writer's trims are the stream's and a long float is
// only ever jump records; those are counted too.
//
// TWO jump records in a row are counted beside them: some machines cut at two
// as shipped (docs/dst-float-cuts-2026-10-04.md), and any move over 12.1 mm
// is two.
//
// `--pystitch`: a third-party reader's count beside this one's, on a sample.
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync, renameSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import { fork, spawnSync } from "node:child_process";
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
const WANT = take("--set");
const JOBS = Math.max(1, Number(take("--jobs")[0]) || Math.min(6, os.cpus().length));
const JSON_OUT = take("--json")[0], PART = take("--part")[0];
const EVERY = Math.max(1, Number(take("--every")[0]) || 1);
const KEEP = take("--keep")[0], AGAINST = take("--against")[0];
const PARTS = Math.max(JOBS, Number(take("--parts")[0]) || (KEEP ? 48 : JOBS));
const ON = take("--on").map((kv) => { const [k, v] = kv.split("="); return [k, v === undefined || v === "true" ? true : v === "false" ? false : isNaN(Number(v)) ? v : Number(v)]; });
const PYTHON = take("--pystitch")[0], SAMPLE = Number(take("--sample")[0]) || 120, TMP = take("--tmp")[0];
const SRC = resolve(args[0] || join(ROOT, "src"));

// The engine whole, in the Studio's own load order, so that the app's modules
// find it on the global as they do in a browser.
for (const f of ["units.js", "sewtime.js", "garments.js", "fabrics.js", "fill.js", "geometry.js", "quantize.js", "flatten.js", "satin.js", "satinplay.js", "crossfill.js", "satinfont.js", "fontbin.js", "svgpath.js", "svgimport.js", "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js"]) require(join(SRC, f));
const DG = require(join(SRC, "digitize.js"));
const FAB = require(join(SRC, "fabrics.js")), GAR = require(join(SRC, "garments.js")), BIN = require(join(SRC, "fontbin.js"));
const WRITE = { dst: require(join(SRC, "dst.js")).encodeDST, exp: require(join(SRC, "exp.js")).encodeEXP, pes: require(join(SRC, "pes.js")).encodePES };
const OTHER = AGAINST ? require(join(resolve(AGAINST), "digitize.js")) : null;
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);

// ---- the three files, read from their formats ------------------------------
// -> [{ dx, dy, kind }], kind one of stitch, jump, trim, color; +y up.
function readDST(bytes) {
  const out = [];
  for (let i = 512; i + 2 < bytes.length; i += 3) {
    const b0 = bytes[i], b1 = bytes[i + 1], b2 = bytes[i + 2];
    if ((b2 & 0xf3) === 0xf3) break;
    const bit = (b, m, v) => (b & m ? v : 0);
    const dx = bit(b0, 0x01, 1) - bit(b0, 0x02, 1) + bit(b0, 0x04, 9) - bit(b0, 0x08, 9) + bit(b1, 0x01, 3) - bit(b1, 0x02, 3) + bit(b1, 0x04, 27) - bit(b1, 0x08, 27) + bit(b2, 0x04, 81) - bit(b2, 0x08, 81);
    const dy = bit(b0, 0x80, 1) - bit(b0, 0x40, 1) + bit(b0, 0x20, 9) - bit(b0, 0x10, 9) + bit(b1, 0x80, 3) - bit(b1, 0x40, 3) + bit(b1, 0x20, 27) - bit(b1, 0x10, 27) + bit(b2, 0x20, 81) - bit(b2, 0x10, 81);
    out.push({ dx, dy, kind: b2 & 0x40 ? "color" : b2 & 0x80 ? "jump" : "stitch" });
  }
  return out;
}
function readEXP(bytes) {
  const out = [], sb = (v) => (v > 127 ? v - 256 : v);
  for (let i = 0; i + 1 < bytes.length;) {
    if (bytes[i] !== 0x80) { out.push({ dx: sb(bytes[i]), dy: sb(bytes[i + 1]), kind: "stitch" }); i += 2; continue; }
    const code = bytes[i + 1];
    if (code === 0x01) out.push({ dx: 0, dy: 0, kind: "color" });
    else if (code === 0x04) out.push({ dx: sb(bytes[i + 2]), dy: sb(bytes[i + 3]), kind: "jump" });
    else if (code === 0x80) out.push({ dx: 0, dy: 0, kind: "trim" });
    else throw new Error("EXP: a control this reader does not know, 0x" + code.toString(16));
    i += 4;
  }
  return out;
}
function readPES(bytes) {
  const pec = bytes[8] | (bytes[9] << 8) | (bytes[10] << 16) | (bytes[11] << 24), out = [];
  let i = pec + 532;   // past the label, the colours, the block's header and its first jump
  const axis = () => {
    const b = bytes[i++];
    if (!(b & 0x80)) return [b >= 0x40 ? b - 0x80 : b, 0];
    const v = (b << 8) | bytes[i++], d = v & 0x0fff;
    return [d >= 0x800 ? d - 0x1000 : d, v & 0x7000];
  };
  while (i < bytes.length && bytes[i] !== 0xff) {
    if (bytes[i] === 0xfe && bytes[i + 1] === 0xb0) { out.push({ dx: 0, dy: 0, kind: "color" }); i += 3; continue; }
    const [dx, fx] = axis(), [dy, fy] = axis(), f = fx | fy;
    out.push({ dx, dy: -dy, kind: f & 0x2000 ? "trim" : f & 0x1000 ? "jump" : "stitch" });
  }
  return out;
}
const READ = { dst: readDST, exp: readEXP, pes: readPES };

// Which stream record each record of the file belongs to: a stream record's
// file records end where it lands. Throws when the two do not line up.
function owners(stream, recs, fmt) {
  const own = new Int32Array(recs.length);
  let k = 0, x = 0, y = 0;
  const step = (i) => {
    const r = recs[k];
    if (!r) throw new Error(`${fmt}: the file ends before stream record ${i}`);
    x += r.dx; y += r.dy; own[k++] = i;
    return r;
  };
  for (let i = 0; i < stream.length && stream[i].type !== "end"; i++) {
    const s = stream[i], tx = s.x | 0, ty = s.y | 0;
    let last;
    // EXP and PES write a colour change as a control with no move in it, and
    // an EXP trim as a control followed by the move.
    if (s.type === "color" && fmt !== "dst") last = step(i);
    else if (s.type === "trim" && fmt === "exp") { last = step(i); while (x !== tx || y !== ty) step(i); }
    else for (let n = 0, need = s.type === "trim" && fmt === "dst" ? 3 : 1; n < need || x !== tx || y !== ty; n++) last = step(i);
    const want = s.type === "trim" && fmt === "dst" ? "jump" : s.type;
    if (last.kind !== want) throw new Error(`${fmt}: stream record ${i} is a ${s.type} and its file record a ${last.kind}`);
  }
  if (k !== recs.length) throw new Error(`${fmt}: ${recs.length - k} records in the file past the stream's end`);
  return own;
}

// B is A with cuts put in and nothing else: a jump of A's turned into a trim
// where it stands, or a trim on the spot before a jump of A's. -> how many
// cuts, or -1 when the two differ some other way.
function cutsPutIn(A, B) {
  const same = (p, q) => p.x === q.x && p.y === q.y;
  let i = 0, k = 0, cuts = 0;
  while (i < A.length || k < B.length) {
    const a = A[i], b = B[k];
    if (a && b && a.type === "jump" && b.type === "trim" && i > 0 && same(b, A[i - 1]) && B[k + 1] && B[k + 1].type === "jump" && same(B[k + 1], a)) { cuts++; k++; continue; }
    if (a && b && a.type === "jump" && b.type === "trim" && same(a, b)) { cuts++; i++; k++; continue; }
    if (a && b && a.type === b.type && same(a, b)) { i++; k++; continue; }
    return -1;
  }
  return cuts;
}
const stitchesOnly = (d) => d.stitches.filter((q) => q.type === "stitch" || q.type === "color").map((q) => `${q.type[0]}${q.x},${q.y}`).join(" ");
const tally = () => ({ n: {}, max: {} });
const bump = (t, k, by) => { t.n[k] = (t.n[k] || 0) + (by == null ? 1 : by); };
const peak = (t, k, v) => { if (!(t.max[k] >= v)) t.max[k] = v; };
const merge = (into, t) => { for (const k in t.n) bump(into, k, t.n[k]); for (const k in t.max) peak(into, k, t.max[k]); };
const FLOATS = [[24.2, "under 24.2 mm"], [30, "24.2 to 30"], [50, "30 to 50"], [100, "50 to 100"]];
const floatBucket = (mm) => (FLOATS.find(([top]) => mm < top) || [0, "100 and over"])[1];
const UNASKED = ["between two runs of one shape", "between shapes", "inside a run"];
const WHATS = ["trim", "after colour", "start", ...UNASKED];
// The fewest records a move can be written in: 12.1 mm an axis each.
const fewest = (dx, dy) => Math.max(1, Math.ceil(Math.abs(dx) / 121), Math.ceil(Math.abs(dy) / 121));

// One design: its stream, its three files, and what each cut in the DST was.
// -> the cuts nobody asked for: [{ before, after }], stream indices of the
// stitch either side.
function readDesign(des, t, where) {
  const st = des.stitches, spans = des.runs || [];
  bump(t, "designs"); bump(t, `lane/${where.lane}/designs`);
  bump(t, "stitches", st.filter((s) => s.type === "stitch").length);
  const trims = st.filter((s) => s.type === "trim").length;
  bump(t, "trims in the stream", trims); bump(t, `lane/${where.lane}/trims in the stream`, trims);
  const opens = new Map(spans.map((r, k) => [r.i0, k]));
  const spanOf = (i) => {
    for (let lo = 0, hi = spans.length - 1; lo <= hi;) {
      const m = (lo + hi) >> 1;
      if (spans[m].i1 < i) lo = m + 1; else if (spans[m].i0 > i) hi = m - 1; else return m;
    }
    return -1;
  };
  // Thread attached, no `trim` and no colour change in it: what the float is.
  const floatOf = (i0, i1) => {
    for (let i = i0; i <= i1; i++) {
      const k = opens.get(i);
      if (k === undefined) continue;
      const prev = k > 0 ? spans[k - 1] : null;
      return [prev && prev.shape === spans[k].shape ? UNASKED[0] : UNASKED[1], `${prev ? prev.kind : "nothing"} to ${spans[k].kind}`];
    }
    const k = spanOf(i0);
    return [UNASKED[2], k < 0 ? "no run" : spans[k].kind];
  };
  const stitchBefore = (i) => { for (let j = i - 1; j >= 0; j--) if (st[j].type === "stitch") return j; return -1; };
  const stitchAfter = (i) => { for (let j = i + 1; j < st.length; j++) if (st[j].type === "stitch") return j; return -1; };
  const unasked = [];
  let twos = 0;
  for (const fmt of ["dst", "exp", "pes"]) {
    const recs = READ[fmt](WRITE[fmt](des)), own = owners(st, recs, fmt);
    bump(t, `${fmt}/trim records`, recs.filter((r) => r.kind === "trim").length);
    bump(t, `${fmt}/jump records`, recs.filter((r) => r.kind === "jump").length);
    for (let a = 0; a < recs.length;) {
      if (recs[a].kind !== "jump") { a++; continue; }
      let b = a;
      while (b + 1 < recs.length && recs[b + 1].kind === "jump") b++;
      const len = b - a + 1, i0 = own[a], i1 = own[b];
      let dx = 0, dy = 0;
      for (let k = a; k <= b; k++) { dx += recs[k].dx; dy += recs[k].dy; }
      a = b + 1;
      if (len >= 3) bump(t, `${fmt}/runs of three jumps or more`);
      if (fmt !== "dst") continue;
      let what, detail = "";
      const before = stitchBefore(i0), after = stitchAfter(i1 - (st[i1].type === "stitch" ? 1 : 0));
      if (st.slice(i0, i1 + 1).some((s) => s.type === "trim")) what = "trim";
      else if (before < 0) what = "start";
      else if (st.slice(before + 1, i0).some((s) => s.type === "color" || s.type === "trim")) what = "after colour";
      else [what, detail] = floatOf(i0, i1);
      if (len < 3) {
        if (!UNASKED.includes(what)) continue;
        // Not a cut to a machine that cuts at three. One that cuts at two cuts
        // at two; and a float of one record is still a float.
        const mm = after < 0 ? 0 : Math.hypot(st[after].x - st[before].x, st[after].y - st[before].y) / 10;
        if (len === 2) { bump(t, "two jumps in a row, thread attached"); twos++; }
        else if (mm >= 4) bump(t, "one jump, thread attached, 4 mm and over");
        else if (mm >= 3) bump(t, "one jump, thread attached, 3 to 4 mm");
        continue;
      }
      bump(t, "cuts in the DST"); bump(t, `cuts in the DST/${what}`);
      bump(t, `lane/${where.lane}/cuts in the DST`); bump(t, `lane/${where.lane}/cuts in the DST/${what}`);
      if (!UNASKED.includes(what)) continue;
      bump(t, `joins/${what}: ${detail}`);
      const mm = after < 0 ? 0 : Math.hypot(st[after].x - st[before].x, st[after].y - st[before].y) / 10;
      bump(t, `float/${floatBucket(mm)}`); peak(t, "longest float, mm", mm);
      if (fewest(dx, dy) < 3) bump(t, "could be two records or fewer");
      bump(t, `size/${where.size}/cuts nobody asked for`);
      bump(t, `lane/${where.lane}/cuts nobody asked for`);
      unasked.push({ before, after });
    }
  }
  if (unasked.length) { bump(t, "designs with a cut nobody asked for"); bump(t, `lane/${where.lane}/designs with a cut nobody asked for`); }
  if (unasked.length + twos) bump(t, "designs with one at two");
  peak(t, "most in one design", unasked.length);
  bump(t, `size/${where.size}/designs`);
  return unasked;
}

// With `ties: true`: is the thread locked either side of a cut nobody asked
// for? A lock is a bounce between two places, x y x y x, ending (or starting)
// on the last (or first) stitch of the thread.
function locksAt(des, unasked, t) {
  const st = des.stitches;
  const same = (p, q) => p.x === q.x && p.y === q.y;
  const bounce = (five) => five.length === 5 && five.every((s) => s && s.type === "stitch") && same(five[0], five[2]) && same(five[2], five[4]) && same(five[1], five[3]) && !same(five[0], five[1]);
  for (const c of unasked) {
    bump(t, `ties/thread ends at a cut nobody asked for`, 2);
    if (bounce(st.slice(c.before - 4, c.before + 1))) bump(t, "ties/of them locked");
    if (c.after >= 0 && bounce(st.slice(c.after, c.after + 5))) bump(t, "ties/of them locked");
  }
}

// ---- the designs ------------------------------------------------------------
// shapes: the Studio's own preset and hand-drawn lanes, with its own modules
// and the options generate.js passes (the set PR 623's census calls "studio").
async function shapes() {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions, flattenShape, isValidShape, CANVAS_W, CANVAS_H } = await lib("manualShapes.js");
  const designs = [];
  const kinds = [["circle", {}], ["heart", {}]];
  for (const heightMm of [10, 30, 50]) for (const cornerRadiusMm of [0, 3, 8]) kinds.push(["rect", { heightMm, cornerRadiusMm }]);
  for (const points of [3, 4, 5, 6, 8, 12]) for (const innerRatio of [0.15, 0.3, 0.45, 0.6, 0.9]) kinds.push(["star", { points, innerRatio }]);
  for (const [kind, params] of kinds) for (const sizeMm of [12, 20, 30, 40, 50, 65, 80]) for (const garment of GAR.GARMENTS) {
    const list = [{ id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null }];
    designs.push({ lane: "preset", list, sizeMm, garment });
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
      designs.push({ lane: "manual", list: [{ id: "s", points, curves, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: angle }].concat(cuts), sizeMm, garment });
    }
    made++;
  }
  const build = (d, extra, dg) => {
    const { regions, pxPerMm } = shapesToRegions(d.list);
    return (dg || DG).buildQualityDesign(regions, Object.assign({ garment: d.garment, fabric: FAB.getFabric(FAB.fabricForGarment(d.garment.id)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: d.sizeMm || undefined, offsetXMm: 0, offsetYMm: 0 }, extra));
  };
  return { designs, build, arms: { "as shipped": {}, "fillColumns on": { fillColumns: true } } };
}

// lettering: every shipped font, three texts, three garments, as generate.js
// calls the lettering builder.
async function lettering() {
  const dir = join(SRC, "fonts");
  const fonts = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8")).fonts.map((f) => BIN.decodeFontBin(readFileSync(join(dir, "bin", f.key + ".embf"))));
  const designs = [];
  for (const font of fonts) for (const text of ["KENT", "Your Name", "YOUR NAME\nSecond Line"]) for (const id of ["hat_front", "left_chest", "full_back"]) {
    designs.push({ lane: "lettering", font, text, sizeMm: null, garment: GAR.getGarment(id) });
  }
  const build = (d, extra, dg) => (dg || DG).buildLetteringDesign(d.font, d.text, Object.assign({ garment: d.garment, pxPerMm: 8, underlay: true, rgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, offsetXMm: 0, offsetYMm: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, align: "center" }, extra));
  return { designs, build, arms: { "as shipped": {} } };
}

// image: the logos under digitizer/testdata through the Studio's own flatten
// and trace, as generate.js's image branch builds them.
async function image() {
  const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
  const { flatToRegions } = await lib("imageRegions.js");
  const { decodePNG, downscale } = await import(pathToFileURL(join(ROOT, "tools", "png.mjs")).href);
  const dir = join(ROOT, "digitizer", "testdata"), designs = [];
  for (const f of readdirSync(dir).filter((n) => n.endsWith(".png")).sort()) {
    const img = downscale(decodePNG(join(dir, f)), WORK_MAX_PX), w = img.width, h = img.height;
    for (const nColors of [2, 4, 6]) for (const removeBg of [false, true]) {
      const rgba = new Uint8ClampedArray(img.rgba);
      for (let i = 0; i < w * h; i++) if (rgba[i * 4 + 3] < ALPHA_CUTOFF) rgba[i * 4 + 3] = 0;
      let reg;
      try { reg = flatToRegions(flattenRGBA(rgba, w, h, { nColors, removeBg })); } catch { continue; }
      if (!reg.regions.length) continue;
      for (const id of ["left_chest", "hat_front", "full_back"]) for (const sizeMm of [null, 40]) designs.push({ lane: "image", reg, sizeMm, garment: GAR.getGarment(id) });
    }
  }
  const build = (d, extra, dg) => (dg || DG).buildQualityDesign(named(JSON.parse(JSON.stringify(d.reg.regions))), Object.assign({ garment: d.garment, fabric: FAB.getFabric(FAB.fabricForGarment(d.garment.id)), pxPerMm: d.reg.pxPerMm, satinMaxWidthMm: 3.0, underlay: true, targetWidthMm: d.sizeMm || undefined, offsetXMm: 0, offsetYMm: 0 }, extra));
  return { designs, build, arms: { "as shipped": {}, "fillColumns on": { fillColumns: true } } };
}
// A shape with no id gets "" in the spans, and then no two shapes can be told
// apart. The id places no stitch.
function named(regions) {
  regions.forEach((r, ri) => (r.shapes || []).forEach((sh, si) => { if (sh.id == null) sh.id = `r${ri}s${si}`; }));
  return regions;
}
// A set that is none of the three: a module whose default export, given the
// engine, returns { designs: [{ lane, sizeMm, ... }], build(d, extra, dg), arms };
// `dg` is the engine to build with, when it is not the one handed over.
async function setNamed(name) {
  if (name === "shapes") return shapes();
  if (name === "lettering") return lettering();
  if (name === "image") return image();
  const mod = await import(pathToFileURL(resolve(name)).href);
  return (mod.default || mod)({ DG, FAB, GAR, named });
}
// --on: beside each arm, the same arm with the option on.
async function setWithArms(name) {
  const set = await setNamed(name);
  for (const [flag, value] of ON) for (const arm of Object.keys(set.arms)) {
    if (!(flag in set.arms[arm])) set.arms[`${arm} + ${flag}`] = Object.assign({}, set.arms[arm], { [flag]: value });
  }
  return set;
}
const SETS = WANT.length ? WANT : ["shapes", "lettering", "image"];
const sizeOf = (des) => { const w = des.widthMM || 0; return w < 30 ? "under 30 mm" : w < 60 ? "30 to 60" : w < 100 ? "60 to 100" : "100 and over"; };

async function runPart(part, parts) {
  const out = {};
  for (const name of SETS) {
    const set = await setWithArms(name), res = { errors: 0 };
    for (const arm of Object.keys(set.arms)) res[arm] = tally();
    set.designs.forEach((d, i) => {
      if (i % EVERY || (i / EVERY) % parts !== part) return;
      for (const arm of Object.keys(set.arms)) {
        try {
          const des = set.build(d, set.arms[arm]);
          readDesign(des, res[arm], { lane: d.lane, size: sizeOf(des) });
          if (OTHER) {
            const was = set.build(d, set.arms[arm], OTHER);
            const cuts = JSON.stringify(was.stitches) === JSON.stringify(des.stitches) ? 0 : cutsPutIn(was.stitches, des.stitches);
            const spans = JSON.stringify((was.runs || []).map((r) => [r.kind, r.shape])) === JSON.stringify((des.runs || []).map((r) => [r.kind, r.shape]));
            const how = cuts === 0 && JSON.stringify(was.runs) === JSON.stringify(des.runs) ? "the same"
              : cuts > 0 && spans && stitchesOnly(was) === stitchesOnly(des) && (des.runs || []).every((r) => des.stitches[r.i0].type === "jump") ? "cuts put in and nothing else" : "something else";
            bump(res[arm], `against/${how}`);
            if (cuts > 0) bump(res[arm], "against/cuts put in", cuts);
            if (how === "something else" && (res[arm].n["against/something else"] || 0) <= 2) console.error(`${name} ${i} ${arm}: differs from the other engine some other way`);
          }
          const tied = set.build(d, Object.assign({ ties: true }, set.arms[arm])), tiedTally = tally();
          locksAt(tied, readDesign(tied, tiedTally, { lane: d.lane, size: "" }), res[arm]);
          bump(res[arm], "ties/stitches", tiedTally.n.stitches);
          bump(res[arm], "ties/locks", (tied._debug && tied._debug.nTies) || 0);
        } catch (e) { res.errors++; if (res.errors <= 3) console.error(`${name} ${i} ${arm}: ${e && e.stack || e}`); }
      }
    });
    out[name] = res;
  }
  return out;
}

// A third-party reader beside this one, on a sample: pystitch reads each of
// the three files and says how many TRIM commands it finds.
async function withPystitch() {
  const tmp = resolve(TMP || join(os.tmpdir(), "file-cut-census"));
  mkdirSync(tmp, { recursive: true });
  const rows = [];
  for (const name of SETS) {
    const set = await setNamed(name), arm = Object.keys(set.arms)[0], stride = Math.max(1, Math.floor(set.designs.length / SAMPLE));
    for (let i = 0; i < set.designs.length; i += stride) {
      const des = set.build(set.designs[i], set.arms[arm]), mine = tally();
      readDesign(des, mine, { lane: set.designs[i].lane, size: "" });
      const files = [];
      for (const fmt of ["dst", "exp", "pes"]) { const f = join(tmp, `d.${fmt}`); writeFileSync(f, WRITE[fmt](des)); files.push(f); }
      const r = spawnSync(PYTHON, [join(ROOT, "tools", "crossval_decode.py"), ...files], { encoding: "utf8", maxBuffer: 1 << 28 });
      if (r.status !== 0) throw new Error("pystitch: " + r.stderr.slice(0, 400));
      const got = JSON.parse(r.stdout), trims = (fmt) => (got[`d.${fmt}`].counts.TRIM || 0);
      // pystitch makes a TRIM of three jumps only once something has been sewn
      // since the last cut, so not of "start" and not of "after colour".
      const attached = ["trim", ...UNASKED].reduce((a, k) => a + (mine.n[`cuts in the DST/${k}`] || 0), 0);
      rows.push({ set: name, stream: mine.n["trims in the stream"] || 0, dstMine: attached, dstTheirs: trims("dst"), expMine: mine.n["exp/trim records"] || 0, expTheirs: trims("exp"), pesMine: mine.n["pes/trim records"] || 0, pesTheirs: trims("pes") });
    }
  }
  const sum = (k) => rows.reduce((a, r) => a + r[k], 0), agree = (a, b) => rows.filter((r) => r[a] === r[b]).length;
  console.log(`\npystitch beside this reader, ${rows.length} designs as shipped:`);
  console.log(`  trims in the stream ${sum("stream")}`);
  console.log(`  DST: cuts here with thread attached ${sum("dstMine")}, TRIM as pystitch reads it ${sum("dstTheirs")}; the same on ${agree("dstMine", "dstTheirs")} designs`);
  console.log(`  EXP: trim records here ${sum("expMine")}, pystitch ${sum("expTheirs")}; the same on ${agree("expMine", "expTheirs")}`);
  console.log(`  PES: trim records here ${sum("pesMine")}, pystitch ${sum("pesTheirs")}; the same on ${agree("pesMine", "pesTheirs")}`);
}

if (PART) {
  const [part, parts] = PART.split("/").map(Number);
  process.send(await runPart(part, parts), () => process.exit(0));
} else if (PYTHON) {
  await withPystitch();
} else {
  const t0 = Date.now();
  const pass = [SRC].concat(...SETS.map((s) => ["--set", s]), ...ON.map(([k, v]) => ["--on", `${k}=${v}`]), ["--every", String(EVERY)], AGAINST ? ["--against", AGAINST] : []);
  if (KEEP) mkdirSync(resolve(KEEP), { recursive: true });
  const kept = (i) => join(resolve(KEEP), `part-${i}-of-${PARTS}.json`);
  const one = (i) => new Promise((done, fail) => {
    if (KEEP && existsSync(kept(i))) return done(JSON.parse(readFileSync(kept(i), "utf8")));
    const kid = fork(SELF, pass.concat(["--part", `${i}/${PARTS}`]));
    let got = null;
    kid.on("message", (m) => { got = m; });
    kid.on("exit", (code) => {
      if (!got) return fail(new Error(`part ${i} ended with ${code} and no result`));
      if (KEEP) { writeFileSync(kept(i) + ".part", JSON.stringify(got)); renameSync(kept(i) + ".part", kept(i)); }
      done(got);
    });
  });
  const parts = new Array(PARTS);
  let next = 0;
  await Promise.all(Array.from({ length: JOBS }, async () => { while (next < PARTS) { const i = next++; parts[i] = await one(i); } }));
  const all = {};
  for (const name of SETS) {
    all[name] = { errors: 0 };
    for (const p of parts) for (const arm in p[name]) {
      if (arm === "errors") { all[name].errors += p[name].errors; continue; }
      merge(all[name][arm] || (all[name][arm] = tally()), p[name][arm]);
    }
  }
  if (JSON_OUT) writeFileSync(resolve(JSON_OUT), JSON.stringify({ src: SRC, sets: all }, null, 1));
  const num = (v) => (v || 0).toLocaleString("en-US");
  const table = (rows) => {
    const w = rows[0].map((_, c) => Math.max(...rows.map((r) => String(r[c]).length)));
    for (const r of rows) console.log("  " + r.map((v, c) => (c ? String(v).padStart(w[c]) : String(v).padEnd(w[c]))).join("  "));
  };
  console.log(`engine: ${SRC}`);
  if (AGAINST) console.log(`against: ${resolve(AGAINST)}`);
  for (const name of SETS) {
    const arms = Object.keys(all[name]).filter((a) => a !== "errors");
    const col = (f) => arms.map((a) => f(all[name][a]));
    console.log(`\n=== "${name}": ${num(all[name][arms[0]].n.designs)} designs${all[name].errors ? `, ${all[name].errors} BUILDS FAILED` : ""} ===`);
    table([
      ["", ...arms],
      ["stitches", ...col((t) => num(t.n.stitches))],
      ["trims in the stream", ...col((t) => num(t.n["trims in the stream"]))],
      ["cuts in the DST (three jumps or more in a row)", ...col((t) => num(t.n["cuts in the DST"]))],
      ...WHATS.map((k) => [`  ${k}`, ...col((t) => num(t.n[`cuts in the DST/${k}`]))]),
      ["cuts nobody asked for (the last three)", ...col((t) => num(UNASKED.reduce((a, k) => a + (t.n[`cuts in the DST/${k}`] || 0), 0)))],
      ["designs with one", ...col((t) => num(t.n["designs with a cut nobody asked for"]))],
      ["most in one design", ...col((t) => num(t.max["most in one design"]))],
      ["longest float that reads as a cut, mm", ...col((t) => (t.max["longest float, mm"] || 0).toFixed(1))],
      ...FLOATS.map((f) => f[1]).concat("100 and over").map((b) => [`  floats ${b}`, ...col((t) => num(t.n[`float/${b}`]))]),
      ["  could be written as two jump records or fewer", ...col((t) => num(t.n["could be two records or fewer"]))],
      ["two jumps in a row, thread attached (a cut at two)", ...col((t) => num(t.n["two jumps in a row, thread attached"]))],
      ["designs with a cut nobody asked for, cutting at two", ...col((t) => num(t.n["designs with one at two"]))],
      ["one jump record, thread attached: 3 to 4 mm", ...col((t) => num(t.n["one jump, thread attached, 3 to 4 mm"]))],
      ["one jump record, thread attached: 4 mm and over", ...col((t) => num(t.n["one jump, thread attached, 4 mm and over"]))],
      ["EXP: trim records", ...col((t) => num(t.n["exp/trim records"]))],
      ["EXP: runs of three jumps or more", ...col((t) => num(t.n["exp/runs of three jumps or more"]))],
      ["PES: trim records", ...col((t) => num(t.n["pes/trim records"]))],
      ["PES: runs of three jumps or more", ...col((t) => num(t.n["pes/runs of three jumps or more"]))],
      ...(AGAINST ? ["the same", "cuts put in and nothing else", "something else"].map((k) => [`against the other engine: ${k}`, ...col((t) => num(t.n[`against/${k}`]))]).concat([["  cuts put in", ...col((t) => num(t.n["against/cuts put in"]))]]) : []),
      ["with ties: stitches", ...col((t) => num(t.n["ties/stitches"]))],
      ["with ties: locks", ...col((t) => num(t.n["ties/locks"]))],
      ["with ties: thread ends at a cut nobody asked for", ...col((t) => num(t.n["ties/thread ends at a cut nobody asked for"]))],
      ["  of them locked", ...col((t) => num(t.n["ties/of them locked"]))],
    ]);
    for (const arm of arms) {
      const t = all[name][arm];
      const lanes = [...new Set(Object.keys(t.n).filter((k) => k.startsWith("lane/")).map((k) => k.split("/")[1]))];
      console.log(`\n  -- ${arm}: by lane --`);
      table([["lane", "designs", "with one", "trims", "cuts in the DST", "nobody asked for"]].concat(lanes.map((l) => [l, num(t.n[`lane/${l}/designs`]), num(t.n[`lane/${l}/designs with a cut nobody asked for`]), num(t.n[`lane/${l}/trims in the stream`]), num(t.n[`lane/${l}/cuts in the DST`]), num(t.n[`lane/${l}/cuts nobody asked for`])])));
      const joins = Object.keys(t.n).filter((k) => k.startsWith("joins/")).sort((a, b) => t.n[b] - t.n[a]);
      if (joins.length) {
        console.log(`  -- ${arm}: what the float joins --`);
        table(joins.map((k) => [k.slice(6), num(t.n[k])]));
      }
      console.log(`  -- ${arm}: by sewn width --`);
      table([["width", "designs", "cuts nobody asked for"]].concat(["under 30 mm", "30 to 60", "60 to 100", "100 and over"].map((s) => [s, num(t.n[`size/${s}/designs`]), num(t.n[`size/${s}/cuts nobody asked for`])])));
    }
  }
  console.log(`\n${((Date.now() - t0) / 1000).toFixed(0)} s, ${JOBS} jobs`);
}
