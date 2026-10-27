// Uncut needle-up moves in typed lettering, read off the machine file.
//
//   node tools/lettering-uncut-jumps.mjs [srcDir] [--fonts a,b] [--texts "A|B"]
//        [--sizes 50,90] [--garments hat_front,left_chest] [--every K]
//        [--on] [--pystitch python] [--json out.json] [--renders dir]
//
// srcDir:     the engine to measure (default: this checkout's src).
// --fonts:    font keys (default: every font in src/fonts/manifest.json).
// --texts:    texts, split on "|" (default: "Fritsch's Stitches", "Hotel
//             Fremont", "KENT").
// --sizes:    design widths in mm, passed as an explicit `targetWidthMm` so
//             no number here rides the garment's auto-fit (default 50,90).
// --garments: garment ids (default hat_front,left_chest). hat_front is a cap:
//             its glyphs sew centre-out, and every relocated glyph opens on a
//             jump.
// --every:    every K-th design only, for a quick look.
// --on:       build each design again with `cutEveryJump: true` and say what
//             it did: buried, walked, cut, the trims and stitches against OFF,
//             the uncut moves left in its DST, and the ORACLE below.
// --renders:  a folder: draw each design OFF | ON there instead of counting
//             (one PNG per font, text, size and garment). OFF, every uncut
//             move is a thick red line; ON, every cut it added is a blue
//             ring, every hop it sewed needle-down a thick green line. Thread
//             is dark, a move the needle is up for light grey.
// --pystitch: the main checkout's venv python. The browser DST is read again
//             by pystitch, and the design is written a second time by the
//             service's own /export writer (digitizer_core.adapter
//             .design_to_pattern + digitizer_service.formats.write, called
//             in-process, no server), whose DST is read by pystitch and by
//             src/dstimport.js. The Studio sends lettering to the browser
//             encoder; /export is the path `preferService` takes.
//
// AN UNCUT MOVE is one or two jump records in a row between two stitch
// records of one thread: a stitch before them with no colour change since,
// and a stitch after. A DST has no cut of its own; three jump records or more
// in a row are a cut to the machine (src/dst.js `splitTrim`), so one or two
// are a float: a thread across the work that someone snips by hand. The move
// to the design's first stitch, and to the first stitch after a colour
// change, have no thread on them and are not counted.
//
// Each uncut move is put down, from the file alone, to what its thread would
// lie on if it were sewn needle-down straight across (the classes
// stage7_sequence._cut_or_bury_jumps uses):
//   under later   every sample of it under thread sewn AFTER it (within one
//                 thread width of either end, thread of any order counts:
//                 the needle goes down there anyway);
//   on sewn       every sample on thread of any order, not all of it later;
//   bare          some sample on bare fabric.
// And, from the builder's stream (its run spans name the glyph), whether it
// is inside one glyph or between two.
//
// THE ORACLE (`onThread`, exported for test/lettering-cut-every-jump.test.js)
// shares no code with the engine's walk. It is a thread-footprint RASTER of
// the file's own needle-down segments, drawn at `CELL_MM` per cell around the
// segment it judges: a cell is thread when its centre lies within half a
// thread (`THREAD_W_MM`, machine.COVERAGE_THREAD_W_MM, the width stage7's
// _UnderThread uses) plus half a cell diagonal of some segment, so the raster
// reads a point as on thread only when it is within half a thread of one,
// give or take 0.007 mm. A segment is on thread when every sample of its
// centre and both its edges, one cell apart along it, falls on a thread cell.
// `--on` asks it of every needle-down segment the ON file has and the OFF
// file has not (the walks, the buries and the locks at new cuts), against the
// footprint of the segments both have (`bareNewSegments`). A lock is judged
// by its centreline alone: it is a bounce along the stitch it locks, and its
// far point is rounded to the file's unit, so an edge of it sits up to
// 0.035 mm past that stitch's edge, as every lock in the OFF file does. A
// lock laid along a FLOAT still fails: a float lays no thread.
import "./_help.mjs";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";
import { encodePNG } from "./png.mjs";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

// ---- the file, read from its bytes -------------------------------------------
// -> [{ x, y, kind }], absolute in file units (0.1 mm), kind stitch, jump or
// color; one entry per 3-byte record. Written from the Tajima record layout,
// not from src/dst.js or src/dstimport.js.
export function readDSTRecords(bytes) {
  const out = [];
  let x = 0, y = 0;
  for (let i = 512; i + 2 < bytes.length; i += 3) {
    const b0 = bytes[i], b1 = bytes[i + 1], b2 = bytes[i + 2];
    if ((b2 & 0xf3) === 0xf3) break;
    const bit = (b, m, v) => (b & m ? v : 0);
    x += bit(b0, 0x01, 1) - bit(b0, 0x02, 1) + bit(b0, 0x04, 9) - bit(b0, 0x08, 9) + bit(b1, 0x01, 3) - bit(b1, 0x02, 3) + bit(b1, 0x04, 27) - bit(b1, 0x08, 27) + bit(b2, 0x04, 81) - bit(b2, 0x08, 81);
    y += bit(b0, 0x80, 1) - bit(b0, 0x40, 1) + bit(b0, 0x20, 9) - bit(b0, 0x10, 9) + bit(b1, 0x80, 3) - bit(b1, 0x40, 3) + bit(b1, 0x20, 27) - bit(b1, 0x10, 27) + bit(b2, 0x20, 81) - bit(b2, 0x10, 81);
    out.push({ x, y, kind: b2 & 0x40 ? "color" : b2 & 0x80 ? "jump" : "stitch" });
  }
  return out;
}

// -> [{ a, b, k, n }]: the uncut moves of a record list, a the stitch before,
// b the stitch after, k b's record index, n how many jump records.
export function uncutMoves(recs) {
  const out = [];
  let last = null;   // the last stitch of the thread, null after a colour change
  for (let i = 0; i < recs.length;) {
    const r = recs[i];
    if (r.kind === "stitch") { last = r; i++; continue; }
    if (r.kind === "color") { last = null; i++; continue; }
    let j = i;
    while (j < recs.length && recs[j].kind === "jump") j++;
    const n = j - i, next = recs[j];
    if (last && n < 3 && next && next.kind === "stitch") out.push({ a: last, b: next, k: j, n });
    // A cut ends the thread: what follows it is a new one.
    if (n >= 3) last = null;
    i = j;
  }
  return out;
}

// -> [{ ax, ay, bx, by, k }]: every needle-down segment, k the index of its
// second record. A stitch on the point before it lays no thread.
export function threadSegments(recs) {
  const out = [];
  for (let k = 1; k < recs.length; k++) {
    const p = recs[k - 1], q = recs[k];
    if (p.kind !== "stitch" || q.kind !== "stitch" || (p.x === q.x && p.y === q.y)) continue;
    out.push({ ax: p.x, ay: p.y, bx: q.x, by: q.y, k });
  }
  return out;
}

export const THREAD_W_MM = 0.4;
export const CELL_MM = 0.01;
const UNITS_PER_MM = 10;

// The samples `onThread` judges: centre and both edges (or the centre only),
// one cell apart.
function samples(ax, ay, bx, by, half, step, edges) {
  const d = Math.hypot(bx - ax, by - ay);
  const n = Math.max(2, Math.ceil(d / step) + 1);
  const nx = d > 0 ? (ay - by) / d : 0, ny = d > 0 ? (bx - ax) / d : 0;
  const out = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1), cx = ax + (bx - ax) * t, cy = ay + (by - ay) * t;
    for (const o of edges ? [-half, 0, half] : [0]) out.push([cx + o * nx, cy + o * ny]);
  }
  return out;
}

// Is the thread of the straight segment a->b (file units) on thread? `cover`
// is the segments that count; `endCover`, if given, is what counts within one
// thread width of either end instead. `centreOnly`: judge the centreline
// alone (a lock, which lies along the stitch it locks, below). -> the samples
// that fell on bare fabric (empty: on thread).
export function bareSamples(ax, ay, bx, by, cover, endCover, centreOnly) {
  const half = (THREAD_W_MM / 2) * UNITS_PER_MM, cell = CELL_MM * UNITS_PER_MM;
  const pts = samples(ax, ay, bx, by, half, cell, !centreOnly);
  const near = (p) => endCover && (Math.hypot(p[0] - ax, p[1] - ay) <= 2 * half || Math.hypot(p[0] - bx, p[1] - by) <= 2 * half);
  const groups = endCover ? [[pts.filter((p) => !near(p)), cover], [pts.filter(near), endCover]] : [[pts, cover]];
  const bare = [];
  for (const [ps, segs] of groups) {
    if (!ps.length) continue;
    const x0 = Math.min(...ps.map((p) => p[0])) - cell, y0 = Math.min(...ps.map((p) => p[1])) - cell;
    const x1 = Math.max(...ps.map((p) => p[0])) + cell, y1 = Math.max(...ps.map((p) => p[1])) + cell;
    const W = Math.ceil((x1 - x0) / cell) + 1, H = Math.ceil((y1 - y0) / cell) + 1;
    const raster = new Uint8Array(W * H);
    const reach = half + cell * Math.SQRT1_2;
    for (const s of segs) {
      const sx0 = Math.min(s.ax, s.bx) - reach, sx1 = Math.max(s.ax, s.bx) + reach;
      const sy0 = Math.min(s.ay, s.by) - reach, sy1 = Math.max(s.ay, s.by) + reach;
      if (sx1 < x0 || sx0 > x1 || sy1 < y0 || sy0 > y1) continue;
      const c0 = Math.max(0, Math.floor((sx0 - x0) / cell)), c1 = Math.min(W - 1, Math.ceil((sx1 - x0) / cell));
      const r0 = Math.max(0, Math.floor((sy0 - y0) / cell)), r1 = Math.min(H - 1, Math.ceil((sy1 - y0) / cell));
      const dx = s.bx - s.ax, dy = s.by - s.ay, L2 = dx * dx + dy * dy;
      for (let r = r0; r <= r1; r++) {
        const py = y0 + (r + 0.5) * cell;
        for (let c = c0; c <= c1; c++) {
          if (raster[r * W + c]) continue;
          const px = x0 + (c + 0.5) * cell;
          let t = L2 > 0 ? ((px - s.ax) * dx + (py - s.ay) * dy) / L2 : 0;
          t = t < 0 ? 0 : t > 1 ? 1 : t;
          if (Math.hypot(px - (s.ax + t * dx), py - (s.ay + t * dy)) <= reach) raster[r * W + c] = 1;
        }
      }
    }
    for (const p of ps) {
      const c = Math.floor((p[0] - x0) / cell), r = Math.floor((p[1] - y0) / cell);
      if (!raster[r * W + c]) bare.push(p);
    }
  }
  return bare;
}
export const onThread = (ax, ay, bx, by, cover, endCover, centreOnly) => bareSamples(ax, ay, bx, by, cover, endCover, centreOnly).length === 0;

// What an uncut move's straight thread would lie on: "under later", "on sewn"
// or "bare". `segs` is threadSegments of the same records.
export function classifyMove(m, segs) {
  const later = segs.filter((s) => s.k > m.k);
  if (onThread(m.a.x, m.a.y, m.b.x, m.b.y, later, segs)) return "under later";
  if (onThread(m.a.x, m.a.y, m.b.x, m.b.y, segs)) return "on sewn";
  return "bare";
}

// The needle-down segments of `on` that `off` has not, as a multiset of
// their two ends: what a pass that only adds thread laid. Each is a `lock`
// when its record is inside a bounce of the file (five stitch records p q p q
// p): the lock a new cut gets, which lies ALONG the stitch it locks, its far
// point rounded to the file's unit, so one of its edges sits up to 0.035 mm
// off that stitch's own edge as every lock in the OFF file does.
export function newSegments(onRecs, offRecs) {
  const key = (s) => `${s.ax},${s.ay},${s.bx},${s.by}`;
  const left = new Map();
  for (const s of threadSegments(offRecs)) left.set(key(s), (left.get(key(s)) || 0) + 1);
  const same = (p, q) => p.x === q.x && p.y === q.y;
  const inLock = new Uint8Array(onRecs.length);
  for (let i = 0; i + 4 < onRecs.length; i++) {
    const f = onRecs.slice(i, i + 5);
    if (f.every((r) => r.kind === "stitch") && same(f[0], f[2]) && same(f[2], f[4]) && same(f[1], f[3]) && !same(f[0], f[1])) for (let k = i + 1; k <= i + 4; k++) inLock[k] = 1;
  }
  const fresh = [], old = [];
  for (const s of threadSegments(onRecs)) {
    const n = left.get(key(s)) || 0;
    if (n) { left.set(key(s), n - 1); old.push(s); } else fresh.push({ ...s, lock: !!inLock[s.k] });
  }
  return { fresh, old };
}

// THE ORACLE, whole: every needle-down segment the ON file has and the OFF
// file has not lies on the thread of the segments both have. A lock is
// judged by its centreline, everything else by its centre and both edges.
// -> the segments on bare fabric.
export function bareNewSegments(onRecs, offRecs) {
  const { fresh, old } = newSegments(onRecs, offRecs);
  return { fresh, bare: fresh.filter((s) => !onThread(s.ax, s.ay, s.bx, s.by, old, null, s.lock)) };
}

// A lock is a bounce between two places, x y x y x, ending (or starting) on
// the thread's last (or first) stitch. -> for each `trim` of the stream, are
// both its ends locked: [{ i, before, after }].
export function locksAtTrims(stitches) {
  const same = (p, q) => p && q && p.x === q.x && p.y === q.y;
  const bounce = (f) => f.length === 5 && f.every((s) => s && s.type === "stitch") && same(f[0], f[2]) && same(f[2], f[4]) && same(f[1], f[3]) && !same(f[0], f[1]);
  const out = [];
  for (let i = 0; i < stitches.length; i++) {
    if (stitches[i].type !== "trim") continue;
    let b = i - 1;
    while (b >= 0 && stitches[b].type !== "stitch") b--;
    let a = i + 1;
    while (a < stitches.length && stitches[a].type !== "stitch") a++;
    out.push({ i, before: b >= 4 && bounce(stitches.slice(b - 4, b + 1)), after: a < stitches.length && bounce(stitches.slice(a, a + 5)) });
  }
  return out;
}

// ---- OFF | ON, drawn ---------------------------------------------------------
// Two panels side by side from the two files' records, at `scale` px per mm.
// marks: [{ lines: [[a, b]], rgb, width }, { rings: [p], rgb }].
function drawPair(panels, scale, file) {
  const PAD = 24, GAP = 16;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of panels) for (const r of p.recs) { minX = Math.min(minX, r.x); maxX = Math.max(maxX, r.x); minY = Math.min(minY, r.y); maxY = Math.max(maxY, r.y); }
  const pw = Math.ceil(((maxX - minX) / 10) * scale) + 2 * PAD, ph = Math.ceil(((maxY - minY) / 10) * scale) + 2 * PAD;
  const W = pw * panels.length + GAP * (panels.length - 1), H = ph;
  const rgba = new Uint8Array(W * H * 4).fill(255);
  const put = (x, y, c) => { x = Math.round(x); y = Math.round(y); if (x < 0 || y < 0 || x >= W || y >= H) return; const i = (y * W + x) * 4; rgba[i] = c[0]; rgba[i + 1] = c[1]; rgba[i + 2] = c[2]; };
  const line = (x0, y0, x1, y1, c, w) => {
    const n = Math.max(1, Math.ceil(Math.hypot(x1 - x0, y1 - y0) * 2));
    for (let k = 0; k <= n; k++) { const x = x0 + ((x1 - x0) * k) / n, y = y0 + ((y1 - y0) * k) / n; for (let a = -w; a <= w; a++) for (let b = -w; b <= w; b++) if (a * a + b * b <= w * w) put(x + a, y + b, c); }
  };
  const ring = (x, y, c, r) => { for (let a = -r - 1; a <= r + 1; a++) for (let b = -r - 1; b <= r + 1; b++) { const q = a * a + b * b; if (q <= (r + 1) * (r + 1) && q >= (r - 1) * (r - 1)) put(x + a, y + b, c); } };
  panels.forEach((p, k) => {
    const ox = k * (pw + GAP);
    const tx = (u) => ox + PAD + ((u - minX) / 10) * scale, ty = (u) => PAD + ((maxY - u) / 10) * scale;
    if (k > 0) for (let y = 0; y < H; y++) for (let g = 0; g < GAP; g++) put(ox - GAP + g, y, [235, 235, 235]);
    for (let i = 1; i < p.recs.length; i++) {
      const a = p.recs[i - 1], s = p.recs[i];
      line(tx(a.x), ty(a.y), tx(s.x), ty(s.y), s.kind === "stitch" && a.kind === "stitch" ? [40, 40, 60] : [205, 205, 205], 0);
    }
    for (const m of p.marks) {
      for (const [a, b] of m.lines || []) line(tx(a.x), ty(a.y), tx(b.x), ty(b.y), m.rgb, m.width);
      for (const q of m.rings || []) ring(tx(q.x), ty(q.y), m.rgb, Math.max(4, Math.round(scale * 0.4)));
    }
  });
  writeFileSync(file, encodePNG(W, H, rgba));
}

// ---- the census --------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);
  const take = (name) => { const i = args.indexOf(name); return i < 0 ? null : args.splice(i, 2)[1]; };
  const flag = (name) => { const i = args.indexOf(name); if (i < 0) return false; args.splice(i, 1); return true; };
  const FONTS = take("--fonts"), TEXTS = (take("--texts") || "Fritsch's Stitches|Hotel Fremont|KENT").split("|");
  const SIZES = (take("--sizes") || "50,90").split(",").map(Number);
  const GARMENT_IDS = (take("--garments") || "hat_front,left_chest").split(",");
  const EVERY = Math.max(1, Number(take("--every")) || 1), PYTHON = take("--pystitch"), JSON_OUT = take("--json");
  const ON = flag("--on"), RENDERS = take("--renders");
  const SRC = resolve(args[0] || join(ROOT, "src"));
  const DG = require(join(SRC, "digitize.js")), BIN = require(join(SRC, "fontbin.js"));
  const GAR = require(join(SRC, "garments.js")), DST = require(join(SRC, "dst.js")), DSTI = require(join(SRC, "dstimport.js"));
  const dir = join(SRC, "fonts");
  const keys = FONTS ? FONTS.split(",") : JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8")).fonts.map((f) => f.key);
  const fonts = keys.map((key) => ({ key, data: BIN.decodeFontBin(readFileSync(join(dir, "bin", key + ".embf"))) }));

  // An uncut move in the builder's stream: a jump straight after a stitch.
  // -> [{ j, within }], j the jump's index, within: the stitches either side
  // are in spans of one glyph.
  const streamMoves = (d) => {
    const shapeAt = [];
    for (const r of d.runs || []) for (let i = r.i0; i <= r.i1; i++) shapeAt[i] = r.shape;
    const st = d.stitches, out = [];
    for (let j = 1; j < st.length; j++) {
      if (st[j].type !== "jump" || st[j - 1].type !== "stitch") continue;
      let n = j + 1;
      while (n < st.length && st[n].type === "jump") n++;
      if (!st[n] || st[n].type !== "stitch") continue;
      out.push({ j, within: shapeAt[j - 1] != null && shapeAt[j - 1] === shapeAt[n] });
    }
    return out;
  };
  // dstimport's reading: it folds a run of one or two jump records into one
  // `jump` and three or more into a `trim`.
  const importedUncut = (bytes) => {
    const st = DSTI.decodeDST(bytes).stitches;
    let n = 0, sewn = false;
    for (let i = 0; i < st.length; i++) {
      const s = st[i];
      if (s.type === "stitch") { sewn = true; continue; }
      if (s.type === "trim" || s.type === "color") { sewn = false; continue; }
      if (s.type === "jump" && sewn && st[i + 1] && st[i + 1].type === "stitch") n++;
    }
    return n;
  };

  const rows = new Map(), lens = new Map(), pyJobs = [];
  const row = (k) => { if (!rows.has(k)) { rows.set(k, {}); lens.set(k, []); } return rows.get(k); };
  const add = (r, k, v) => { r[k] = (r[k] || 0) + (v == null ? 1 : v); };
  let seq = 0;
  for (const gid of GARMENT_IDS) for (const w of SIZES) for (const text of TEXTS) for (const f of fonts) {
    if (seq++ % EVERY) continue;
    const garment = GAR.getGarment(gid);
    if (!garment) throw new Error("no garment " + gid);
    const opts = { garment, pxPerMm: 8, targetWidthMm: w };
    let d;
    try { d = DG.buildLetteringDesign(f.data, text, opts); } catch (e) { continue; }
    if (!d || !d.stitchCount) continue;
    const key = `${gid} | ${w} mm | ${JSON.stringify(text)}`, r = row(key);
    add(r, "designs");
    const bytes = DST.encodeDST(d), recs = readDSTRecords(bytes), segs = threadSegments(recs);
    if (RENDERS) {
      const e = DG.buildLetteringDesign(f.data, text, { ...opts, cutEveryJump: true }), onRecs = readDSTRecords(DST.encodeDST(e));
      const sewn = newSegments(onRecs, recs).fresh.filter((s) => !s.lock).map((s) => [{ x: s.ax, y: s.ay }, { x: s.bx, y: s.by }]);
      const offTrims = new Map();
      for (const s of d.stitches) if (s.type === "trim") offTrims.set(s.x + "," + s.y, (offTrims.get(s.x + "," + s.y) || 0) + 1);
      const cuts = e.stitches.filter((s) => {
        if (s.type !== "trim") return false;
        const n = offTrims.get(s.x + "," + s.y) || 0;
        if (n) offTrims.set(s.x + "," + s.y, n - 1);
        return !n;
      });
      const name = `${f.key}_${text.replace(/[^A-Za-z]+/g, "-").replace(/-+$/, "")}_${w}mm_${gid}.png`;
      mkdirSync(RENDERS, { recursive: true });
      drawPair([
        { recs, marks: [{ lines: uncutMoves(recs).map((m) => [m.a, m.b]), rgb: [220, 30, 30], width: 2 }] },
        { recs: onRecs, marks: [{ lines: sewn, rgb: [20, 160, 60], width: 2 }, { rings: cuts, rgb: [30, 90, 220] }] },
      ], w <= 60 ? 14 : 8, join(RENDERS, name));
      console.log(`${name}: OFF ${uncutMoves(recs).length} uncut, ${d.stitches.filter((s) => s.type === "trim").length} trims; ON ${JSON.stringify(e._debug.cutEveryJump)}, ${e.stitches.filter((s) => s.type === "trim").length} trims, ${uncutMoves(onRecs).length} uncut`);
      continue;
    }
    const sm = streamMoves(d), fm = uncutMoves(recs);
    add(r, "stream uncut", sm.length);
    add(r, "  within a glyph", sm.filter((m) => m.within).length);
    add(r, "  between glyphs", sm.filter((m) => !m.within).length);
    add(r, "DST uncut (bytes)", fm.length);
    add(r, "DST uncut (dstimport)", importedUncut(bytes));
    if (fm.length) add(r, "designs with one");
    for (const m of fm) {
      add(r, "  " + classifyMove(m, segs));
      lens.get(key).push(Math.hypot(m.b.x - m.a.x, m.b.y - m.a.y) / 10);
    }
    add(r, "trims OFF", d.stitches.filter((s) => s.type === "trim").length);
    add(r, "stitches OFF", d.stitchCount);
    if (PYTHON) pyJobs.push({ key, dst: Buffer.from(bytes).toString("base64"), design: { stitches: d.stitches.map((s) => ({ x: s.x, y: s.y, type: s.type })), colors: d.colors } });
    if (!ON) continue;
    const e = DG.buildLetteringDesign(f.data, text, { ...opts, cutEveryJump: true });
    const onRecs = readDSTRecords(DST.encodeDST(e)), dbg = e._debug.cutEveryJump || {};
    add(r, "ON DST uncut", uncutMoves(onRecs).length);
    add(r, "ON buried", dbg.buried || 0); add(r, "ON walked", dbg.walked || 0); add(r, "ON cut", dbg.cut || 0);
    add(r, "trims ON", e.stitches.filter((s) => s.type === "trim").length);
    add(r, "stitches ON", e.stitchCount);
    const locks = locksAtTrims(e.stitches);
    add(r, "ON trims with both ends locked", locks.filter((l) => l.before && l.after).length);
    const { fresh, bare: bad } = bareNewSegments(onRecs, recs);
    add(r, "ON new needle-down segments", fresh.length);
    add(r, "  of them locks", fresh.filter((s) => s.lock).length);
    add(r, "ORACLE: new segments on bare fabric", bad.length);
    if (bad.length) console.error(`bare: ${f.key} ${key}: ${bad.slice(0, 3).map((s) => `(${s.ax},${s.ay})->(${s.bx},${s.by})`).join(" ")}`);
  }

  if (RENDERS) return;
  if (PYTHON) runPystitch(PYTHON, pyJobs, (key, got) => {
    const r = rows.get(key);
    add(r, "pystitch: browser DST uncut", got.browser);
    add(r, "pystitch: /export DST uncut", got.service);
    const svc = Buffer.from(got.serviceDst, "base64");
    add(r, "/export DST uncut (bytes)", uncutMoves(readDSTRecords(svc)).length);
    add(r, "/export DST uncut (dstimport)", importedUncut(svc));
  });

  const q = (a, p) => (a.length ? a[Math.floor(p * (a.length - 1))].toFixed(2) : "-");
  const out = [];
  for (const [key, r] of rows) {
    const L = lens.get(key).sort((a, b) => a - b), n = r.designs;
    console.log(`\n${key}: ${n} designs`);
    for (const [k, v] of Object.entries(r)) if (k !== "designs") console.log(`  ${k.padEnd(40)} ${String(v).padStart(7)}  (${(v / n).toFixed(1)}/design)`);
    console.log(`  uncut move length mm: p10 ${q(L, 0.1)} p50 ${q(L, 0.5)} p90 ${q(L, 0.9)} max ${q(L, 1)}`);
    out.push({ key, ...r, lenP50: Number(q(L, 0.5)) || null, lenP90: Number(q(L, 0.9)) || null, lenMax: Number(q(L, 1)) || null });
  }
  if (JSON_OUT) writeFileSync(JSON_OUT, JSON.stringify(out, null, 1));
}

// The service's writer and pystitch's reader, in one python process per
// batch: each job's browser DST read by pystitch, and its design written by
// /export's own two calls and read back. -> calls back with { browser,
// service, serviceDst } per job.
const PY = String.raw`
import base64, io, json, sys
sys.path.insert(0, sys.argv[1])
import pystitch
from pystitch.EmbConstant import COMMAND_MASK, COLOR_CHANGE, END, JUMP, STITCH, STOP, TRIM
from digitizer_core.adapter import design_to_pattern
from digitizer_service import formats

def uncut(data):
    p = pystitch.read_dst(io.BytesIO(data))
    n, last, jumps = 0, False, 0
    for _x, _y, c in p.stitches:
        c &= COMMAND_MASK
        if c == STITCH:
            if last and jumps:
                n += 1
            last, jumps = True, 0
        elif c == JUMP:
            jumps += 1
        elif c in (TRIM, COLOR_CHANGE, STOP):
            last, jumps = False, 0
        elif c == END:
            break
    return n

for line in sys.stdin:
    job = json.loads(line)
    svc = formats.write(design_to_pattern(job["design"]), "dst")
    print(json.dumps({"key": job["key"], "browser": uncut(base64.b64decode(job["dst"])),
                      "service": uncut(svc), "serviceDst": base64.b64encode(svc).decode()}))
`;
function runPystitch(python, jobs, onEach) {
  for (let i = 0; i < jobs.length; i += 40) {
    const input = jobs.slice(i, i + 40).map((j) => JSON.stringify(j)).join("\n") + "\n";
    const r = spawnSync(python, ["-c", PY, join(ROOT, "digitizer")], { input, encoding: "utf8", maxBuffer: 1 << 30 });
    if (r.status !== 0) throw new Error("pystitch: " + r.stderr.slice(-1200));
    for (const line of r.stdout.split("\n")) if (line.trim()) { const got = JSON.parse(line); onEach(got.key, got); }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await main();
