// `cutEveryJump` on buildLetteringDesign (built OFF 2026-10-27): the JS twin
// of the Python lane's `cut_every_jump` (#1048). Kent, 2026-10-26: "Sew-out
// arm on next card (Recommended)" -- both flags go on sew-out card v8 as an
// OFF-beside-ON arm, and neither default flips (ROADMAP gate 1).
//
// Typed lettering leaves one or two jump records between letters and between
// a letter's parts wherever the hop is under `trimAtMm`: a float, which no
// machine cuts. ON, each is buried under thread sewn later, else walked on
// thread already sewn, else cut and locked. Everything here is asked of the
// DST BYTES, read by tools/lettering-uncut-jumps.mjs's own reader, not of the
// builder's stream:
//
//   1. OFF is origin/main's file, byte for byte, on every shipped font (one
//      text, size and garment each, in turn, so every combination of three
//      texts, two sizes and a cap or a flat garment is met): the md5 of all
//      85 DSTs (the two Hebrew fonts read "empty"), taken on
//      origin/main at 45401200. The garments are literals
//      and the width is explicit, so no pin rides garment fit (#1118), and
//      every flag the lane reads is spread at its value that day (`FROZEN`),
//      so a later flip moves no pin here.
//   2. ON leaves no uncut needle-up move in the DST.
//   3. ON, every cut it adds is locked both sides by `ties`.
//   4. ON, no needle-down segment it adds lies on bare fabric, by THE ORACLE:
//      a thread-footprint raster of the file's own segments, sampled ten
//      times finer than the walk and sharing no code with it
//      (tools/lettering-uncut-jumps.mjs, `bareNewSegments`).
//   5. ON's trims and stitches against OFF, reported.
//   6. cutOrBuryJumps on streams written by hand: each of its three answers,
//      and the oracle failing a hop sewn across cloth.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const DG = require("../src/digitize.js");
const fb = require("../src/fontbin.js");
const dst = require("../src/dst.js");
const dsti = require("../src/dstimport.js");

const FONTS = path.join(__dirname, "..", "src", "fonts");
const BIN = path.join(FONTS, "bin");
const KEYS = JSON.parse(fs.readFileSync(path.join(FONTS, "manifest.json"), "utf8")).fonts.map((f) => f.key);
const oracle = import("../tools/lettering-uncut-jumps.mjs");
// The lane's flags at their values on 2026-10-27.
const FROZEN = { underlay: true, counterGuard: true, shortStitch: true, underlayShortColumns: true, crossFloor: true, satinZigzag: true, ties: true, dedupeHoles: true, underlayDirection: false, splitSatin: false, wideColumnFill: false };
// A cap by id (its glyphs sew centre-out, each relocated glyph opening on a
// jump) and a flat garment, both at the box garments.js gave neither.
const CAP = { id: "hat_front", widthIn: 5, heightIn: 2.25 }, FLAT = { widthIn: 5, heightIn: 2.25 };
const TEXTS = ["Fritsch's Stitches", "Hotel Fremont", "KENT"];
const load = (key) => fb.decodeFontBin(fs.readFileSync(path.join(BIN, key + ".embf")));
const build = (key, text, garment, widthMm, extra) => DG.buildLetteringDesign(load(key), text, { ...FROZEN, garment, pxPerMm: 8, targetWidthMm: widthMm, ...(extra || {}) });
const md5 = (bytes) => crypto.createHash("md5").update(bytes).digest("hex");
const count = (d, type) => d.stitches.filter((s) => s.type === type).length;

// Font i: text i % 3, garment i % 2, size (i >> 1) % 2 -- every twelve fonts
// meet all twelve combinations.
const pick = (i) => [TEXTS[i % 3], [CAP, FLAT][i % 2], [50, 90][(i >> 1) % 2]];
const OFF_PIN = "a92b19ff6c681d240b889ab823d6b79d";

test("OFF is origin/main's DST, byte for byte, on every shipped font (md5 of all of them)", () => {
  assert.ok(KEYS.length >= 80, `the library has ${KEYS.length} fonts`);
  const lines = KEYS.map((key, i) => {
    const [text, garment, w] = pick(i);
    let d;
    try { d = build(key, text, garment, w, { cutEveryJump: false }); } catch (e) { return `${key} throws`; }
    return `${key} ${d && d.stitchCount ? md5(dst.encodeDST(d)) : "empty"}`;
  });
  assert.strictEqual(md5(lines.join("\n")), OFF_PIN, "an OFF DST moved:\n" + lines.join("\n"));
});

test("cutEveryJump omitted is cutEveryJump: false", () => {
  for (const [key, text, garment, w] of [["medium_font", TEXTS[0], CAP, 50], ["mimosa_medium", TEXTS[1], FLAT, 90], ["pixel10", TEXTS[0], FLAT, 50]]) {
    const a = build(key, text, garment, w), b = build(key, text, garment, w, { cutEveryJump: false });
    assert.strictEqual(md5(dst.encodeDST(a)), md5(dst.encodeDST(b)), key);
    assert.deepStrictEqual(a.runs, b.runs, key);
    assert.deepStrictEqual(a._debug, b._debug, key);
  }
});

// The ON set: the Studio's default font, the six that walk or bury the most
// hops (of the 85, on these two designs), so the oracle has walks to judge
// and not only locks, and `neon`, whose apostrophe is one penetration
// between two hops on the cap (cutOrBuryJumps' `lone`).
const ON_FONTS = ["medium_font", "mimosa_medium", "mai_en_fleur", "pixel10", "initials_XL", "jersey_15", "montecarlo", "neon"];
const ON_DESIGNS = [[TEXTS[0], CAP, 50], [TEXTS[1], FLAT, 90]];
let pairs = null;
async function onPairs() {
  if (pairs) return pairs;
  const T = await oracle;
  pairs = [];
  for (const key of ON_FONTS) for (const [text, garment, w] of ON_DESIGNS) {
    const off = build(key, text, garment, w), on = build(key, text, garment, w, { cutEveryJump: true });
    const offBytes = dst.encodeDST(off), onBytes = dst.encodeDST(on);
    pairs.push({ name: `${key} ${JSON.stringify(text)} ${w} mm${garment.id ? " cap" : ""}`, off, on, offBytes, onBytes, offRecs: T.readDSTRecords(offBytes), onRecs: T.readDSTRecords(onBytes) });
  }
  return pairs;
}

test("ON: no uncut needle-up move is left in the DST (read from its bytes, and by dstimport)", async () => {
  const T = await oracle;
  let before = 0;
  for (const p of await onPairs()) {
    before += T.uncutMoves(p.offRecs).length;
    assert.strictEqual(T.uncutMoves(p.onRecs).length, 0, p.name);
    // dstimport folds one or two jump records into a `jump`, three or more
    // into a `trim`: a `jump` straight after a stitch is a float.
    const st = dsti.decodeDST(p.onBytes).stitches;
    assert.ok(!st.some((s, i) => s.type === "jump" && i > 0 && st[i - 1].type === "stitch"), p.name + " (dstimport)");
  }
  assert.ok(before > 100, `the OFF files had ${before} uncut moves: nothing to cure`);
});

test("ON: every cut it adds is locked both sides, and no thread it leaves goes down in one place", async () => {
  const T = await oracle;
  let added = 0, lone = 0;
  for (const p of await onPairs()) {
    const offLocked = T.locksAtTrims(p.off.stitches), onLocked = T.locksAtTrims(p.on.stitches);
    const both = (l) => l.filter((x) => x.before && x.after).length;
    const n = onLocked.length - offLocked.length;
    assert.strictEqual(n, p.on._debug.cutEveryJump.cut, p.name + ": trims added");
    assert.strictEqual(both(onLocked) - both(offLocked), n, p.name + ": an added cut is not locked both sides");
    added += n;
    lone += p.on._debug.cutEveryJump.lone;
  }
  assert.ok(added > 100, `${added} cuts added`);
  assert.ok(lone > 0, "no one-place thread met: the set no longer reaches the rule");
});

test("ON: no needle-down segment it adds lies on bare fabric (the oracle)", async () => {
  const T = await oracle;
  let walks = 0, locks = 0, sewn = 0;
  for (const p of await onPairs()) {
    const { fresh, bare } = T.bareNewSegments(p.onRecs, p.offRecs);
    assert.deepStrictEqual(bare.map((s) => `(${s.ax},${s.ay})->(${s.bx},${s.by})${s.lock ? " lock" : ""}`), [], p.name);
    walks += fresh.filter((s) => !s.lock).length;
    locks += fresh.filter((s) => s.lock).length;
    sewn += p.on._debug.cutEveryJump.buried + p.on._debug.cutEveryJump.walked;
  }
  // Not vacuous: the set sews hops, and every one lays a segment the OFF
  // file has not.
  assert.ok(sewn > 50 && walks >= sewn, `${sewn} hops sewn, ${walks} new segments that are not locks, ${locks} lock legs`);
});

test("ON: trims and stitches against OFF", async (t) => {
  let tOff = 0, tOn = 0, sOff = 0, sOn = 0, b = 0, w = 0, c = 0;
  for (const p of await onPairs()) {
    const dbg = p.on._debug.cutEveryJump;
    assert.ok(count(p.on, "trim") >= count(p.off, "trim") && p.on.stitchCount >= p.off.stitchCount, p.name);
    assert.strictEqual(count(p.on, "trim") - count(p.off, "trim"), dbg.cut, p.name);
    tOff += count(p.off, "trim"); tOn += count(p.on, "trim"); sOff += p.off.stitchCount; sOn += p.on.stitchCount;
    b += dbg.buried; w += dbg.walked; c += dbg.cut;
    t.diagnostic(`${p.name}: buried ${dbg.buried}, walked ${dbg.walked}, cut ${dbg.cut}, lone ${dbg.lone}; trims ${count(p.off, "trim")} -> ${count(p.on, "trim")}, stitches ${p.off.stitchCount} -> ${p.on.stitchCount}`);
  }
  t.diagnostic(`all: buried ${b}, walked ${w}, cut ${c}; trims ${tOff} -> ${tOn}, stitches ${sOff} -> ${sOn}`);
});

// ---- streams written by hand ---------------------------------------------------
// File units (0.1 mm). `block` is satin between two rails, 0.4 mm apart on
// each (0.2 from stitch to stitch); `line` a running stitch along y. A hop
// is A, jump B, stitch B.
const S = (x, y) => ({ x, y, type: "stitch" }), J = (x, y) => ({ x, y, type: "jump" });
const block = (x0, x1, y0, y1) => { const out = []; for (let x = x0, k = 0; x <= x1; x += 2, k++) out.push(S(x, k % 2 ? y1 : y0)); return out; };
const line = (y, ...xs) => xs.map((x) => S(x, y));

test("cutOrBuryJumps: a hop on bare fabric is cut, one on sewn thread walked, one under later thread buried", () => {
  // Bare: from one block's last stitch (20, 0) to the next's first (50, 0).
  {
    const st = [J(0, 0), ...block(0, 20, 0, 20), J(50, 0), ...block(50, 70, 0, 20)];
    const spans = [{ i0: 1, i1: 11, kind: "satin", shape: "c0", role: "", block: 0 }, { i0: 13, i1: 23, kind: "satin", shape: "c1", role: "", block: 0 }];
    const r = DG.cutOrBuryJumps(st, spans, true);
    assert.deepStrictEqual([r.buried, r.walked, r.cut], [0, 0, 1]);
    assert.deepStrictEqual(r.stitches.slice(11, 15), [S(20, 0), { x: 20, y: 0, type: "trim" }, J(50, 0), S(50, 0)]);
    assert.deepStrictEqual(spans.map((s) => [s.i0, s.i1]), [[1, 11], [14, 24]]);
  }
  // Walked: 2.4 mm back along the running stitch just sewn, one stitch
  // between at RUN_STITCH_MM (2.0), with a travel span in the glyph it
  // leads into.
  {
    const st = [J(0, 10), ...line(10, 0, 20, 40, 60), J(36, 10), S(36, 10), S(36, 30)];
    const spans = [{ i0: 1, i1: 4, kind: "run", shape: "c0", role: "", block: 0 }, { i0: 6, i1: 7, kind: "run", shape: "c1", role: "", block: 0 }];
    const r = DG.cutOrBuryJumps(st, spans, true);
    assert.deepStrictEqual([r.buried, r.walked, r.cut], [0, 1, 0]);
    assert.deepStrictEqual(r.stitches, [J(0, 10), ...line(10, 0, 20, 40, 60, 48, 36), S(36, 30)]);
    assert.deepStrictEqual(spans.map((s) => [s.i0, s.i1, s.kind, s.shape]), [[1, 4, "run", "c0"], [5, 5, "travel", "c1"], [6, 7, "run", "c1"]]);
  }
  // Buried: 2 mm of cloth from (0, 10) to (20, 10), which the block sewn
  // next covers from x = -4 to 40.
  {
    const st = [J(-10, 10), ...line(10, -10, 0), J(20, 10), S(20, 10), ...block(-4, 40, 0, 20)];
    const r = DG.cutOrBuryJumps(st, [], true);
    assert.deepStrictEqual([r.buried, r.walked, r.cut], [1, 0, 0]);
    assert.deepStrictEqual(r.stitches.slice(0, 5), [J(-10, 10), S(-10, 10), S(0, 10), S(20, 10), S(-4, 0)]);
  }
  // One penetration between two bare hops: cut both sides it lays no thread
  // and takes no lock, so it is left out with the second cut, and the
  // thread before it is cut once.
  {
    const st = [J(0, 0), ...line(0, 0, 10, 20), J(40, 0), S(40, 0), J(70, 0), ...line(0, 70, 80, 90)];
    const spans = [{ i0: 1, i1: 3, kind: "run", shape: "c0", role: "", block: 0 }, { i0: 5, i1: 5, kind: "run", shape: "c1", role: "", block: 0 }, { i0: 7, i1: 9, kind: "run", shape: "c2", role: "", block: 0 }];
    const r = DG.cutOrBuryJumps(st, spans, true);
    assert.deepStrictEqual([r.buried, r.walked, r.cut, r.lone], [0, 0, 1, 1]);
    assert.deepStrictEqual(r.stitches, [J(0, 0), ...line(0, 0, 10, 20), { x: 20, y: 0, type: "trim" }, J(70, 0), ...line(0, 70, 80, 90)]);
    assert.deepStrictEqual(spans.map((s) => [s.i0, s.i1, s.shape]), [[1, 3, "c0"], [6, 8, "c2"]]);
  }
  // Travel is not cover (Python's `lines` leave TRAVEL out): the same walk
  // back over a needle-down connector is cut.
  {
    const st = [J(0, 10), ...line(10, 0, 10, 20, 30), J(10, 10), S(10, 10), S(10, 40)];
    const span = { i0: 2, i1: 4, kind: "travel", shape: "c0", role: "", block: 0 };
    assert.strictEqual(DG.cutOrBuryJumps(st, [{ ...span }], true).cut, 1);
    assert.strictEqual(DG.cutOrBuryJumps(st, [{ ...span, kind: "run" }], true).walked, 1);
  }
});

test("the oracle fails a needle-down hop across cloth or off the thread's edge, and passes one on thread", async () => {
  const T = await oracle;
  const recs = (st) => st.map((s) => ({ x: s.x, y: s.y, kind: s.type }));
  // The bare hop above sewn needle-down instead of cut, through (35, 10).
  const off = [J(0, 0), ...block(0, 20, 0, 20), J(50, 0), ...block(50, 70, 0, 20)];
  const bad = [J(0, 0), ...block(0, 20, 0, 20), S(35, 10), ...block(50, 70, 0, 20)];
  assert.strictEqual(T.bareNewSegments(recs(bad), recs(off)).bare.length, 2, "both legs are on bare fabric");
  // The walk above: on thread.
  const offW = [J(0, 10), ...line(10, 0, 20, 40, 60), J(36, 10), S(36, 10)];
  const onW = [J(0, 10), ...line(10, 0, 20, 40, 60, 48, 36)];
  assert.deepStrictEqual(T.bareNewSegments(recs(onW), recs(offW)).bare, []);
  // The same walk 0.1 mm off the line: one edge of it is 0.1 mm past the
  // thread it rides.
  const offE = [J(0, 10), ...line(10, 0, 20, 40, 60), J(50, 11), S(50, 11), J(30, 11), S(30, 11)];
  const onE = [J(0, 10), ...line(10, 0, 20, 40, 60), J(50, 11), S(50, 11), S(30, 11)];
  assert.strictEqual(T.bareNewSegments(recs(onE), recs(offE)).bare.length, 1);
  // A lock is judged by its centreline: the same segment as a bounce passes.
  const onL = [J(0, 10), ...line(10, 0, 20, 40, 60), J(50, 11), S(50, 11), S(42, 11), S(50, 11), S(42, 11), S(50, 11)];
  const offL = [J(0, 10), ...line(10, 0, 20, 40, 60), J(50, 11), S(50, 11)];
  assert.deepStrictEqual(T.bareNewSegments(recs(onL), recs(offL)).bare, []);
});
