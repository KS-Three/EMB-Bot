// tools/small-cap-census.mjs pins (2026-10-12). Fast: three fonts, a few cells.
//
// Hand counts are the ground truth for the counters (a stream dumped and counted
// by eye, then a synthetic stream built to sit exactly on each floor); the
// full-text rows pin the engine as it stood when the census was taken, so a
// change to the lettering engine that moves a small-size cell shows up here as a
// number to look at, not as silence. They pin MEASUREMENTS, not constants: no
// floor here is settled without a sew-out (ROADMAP gate 1).
import { test } from "node:test";
import assert from "node:assert";

const T = await import("../tools/small-cap-census.mjs");

// `ties`, `fillStagger` and `dedupeHoles` went ON by default on 2026-10-20
// (Kent). Every count below was taken with them OFF -- a lock is four 0.8 mm
// stitches, which would read as short stitches here -- so cells are built OFF.
const TRIO_OFF = { ties: false, fillStagger: false, dedupeHoles: false };
const cell = (font, text, cap) => {
  const f = T.loadFont(font);
  return T.measureCell(f, text, cap, T.calibrate(f, text, TRIO_OFF), TRIO_OFF);
};
const pick = (c, keys) => Object.fromEntries(keys.map((k) => [k, c[k]]));

test("the floors are the engine's own, read, not restated", () => {
  assert.deepStrictEqual(T.FLOORS, { shortMm: 0.3, crossMm: 0.5, columnMm: 1.0 },
    "SHORT_STITCH_AT_MM, SATIN_MIN_CROSS_MM, COLUMN_FLOOR_MM of satinfont.LETTERING_GUARDS");
});

// alchemy "I" at a 3 mm cap sews 18 stitches, 17 consecutive segments, in mm,
// read off the dump by eye:
//   2.60 0.64 1.60 0.45 1.20 0.41 1.00 0.40 1.00 0.40 1.00 0.41 1.20 0.45 1.60 0.64 2.60
// The even entries are the nine crosses (2.6 1.6 1.2 1.0 1.0 1.0 1.2 1.6 2.6), the
// odd ones the satin's 0.4 mm rail steps.
// under 1.0 mm: 0.64 0.45 0.41 0.40 0.40 0.41 0.45 0.64 = 8 (the three 1.00s are
// not under it); under 0.5 mm: 0.45 0.41 0.40 0.40 0.41 0.45 = 6; under 0.3: none.
// Narrowest cross 1.0; the single span's median cross (5th of 9 sorted) is 1.2.
//
// THAT DUMP IS THE ALTERNATING-RAIL STREAM. Since 2026-10-13 the zigzag order
// is the default: the same 18 penetrations, but the eight rail steps are
// diagonal crosses back, each longer than the cross beside it, so nothing is
// under 1.0 mm any more (sub1 8 -> 0, sub05 6 -> 0).
test("hand count: alchemy 'I' at 3 mm", () => {
  const c = cell("alchemy", "I", 3);
  assert.deepStrictEqual(pick(c, ["sewn", "sub1", "sub05", "sub03", "repeat", "overRec", "hairlineSpans"]),
    { sewn: 17, sub1: 0, sub05: 0, sub03: 0, repeat: 0, overRec: 0, hairlineSpans: 0 });
  assert.deepStrictEqual(pick(c, ["satinSpans", "strokeSpans", "thinSpans", "minCrossMm", "narrowestMm"]),
    { satinSpans: 1, strokeSpans: 1, thinSpans: 0, minCrossMm: 1, narrowestMm: 1.2 });
  assert.strictEqual(c.capMm, 3, "the cap lands on the target");
  assert.strictEqual(c.capMiss, false);
  assert.strictEqual(c.engineClean, true);
});

// montecarlo "l" at 3 mm: one stroke under the 0.5 mm floor, so the engine sews it
// as a running stitch -- 29 segments of 0.50 to 0.91 mm, none under 0.5 (the 0.50s
// are exactly 5 units), none a repeat; the engine reports one hairline span, and
// there is no satin in it to measure.
test("hand count: montecarlo 'l' at 3 mm", () => {
  const c = cell("montecarlo", "l", 3);
  assert.deepStrictEqual(pick(c, ["sewn", "sub1", "sub05", "sub03", "repeat", "overRec", "hairlineSpans"]),
    { sewn: 29, sub1: 29, sub05: 0, sub03: 0, repeat: 0, overRec: 0, hairlineSpans: 1 });
  assert.strictEqual(c.maxMm, 0.91);
  assert.strictEqual(c.narrowestMm, null, "no satin column to measure");
  assert.strictEqual(c.engineClean, false, "a hairline span is not engine-clean");
});

// Built by hand in DST units (0.1 mm): lengths 0, 2, 3, 4 and 5 units, then a jump
// that cuts the chain, then 1 unit. The short-stitch floor is 0.3 mm = 3 units and
// "under" is strict: 0 and 2 count, 3 does not. 5 units is exactly the 0.5 mm line.
test("streamCounts: the floors are strict and a jump cuts the chain", () => {
  const P = (x, y, type = "stitch") => ({ x, y, type });
  const stream = [P(0, 0, "jump"), P(0, 0), P(0, 0), P(2, 0), P(5, 0), P(9, 0), P(14, 0), P(30, 30, "jump"), P(30, 30), P(31, 30), P(0, 0, "end")];
  const c = T.streamCounts({ stitches: stream });
  // segments (units): 0 2 3 4 5 | jump | 1 -- six sewn, the first stitch after a
  // jump starts a chain and is not a segment. Under 1.0 mm (10 units): all six.
  // Under 0.5 mm (5 units): 0 2 3 4 1 = five (the 5 is on the line). Under 0.3: 0 2 1.
  assert.deepStrictEqual(c, { sewn: 6, sub1: 6, sub05: 5, sub03: 3, repeat: 1, overRec: 0, maxMm: 0.5 });
});

// A satin span laid cross, step, cross, step, cross, step, cross, step, cross.
// Crosses 20, 14, 8, 8, 12 units (2.0 1.4 0.8 0.8 1.2 mm); steps 4 units. Median
// cross 1.2 mm; narrowest cross 0.8 mm. Five crosses is exactly MIN_STROKE_CROSSES.
test("satinColumns: median per span, narrowest across spans, short spans excluded", () => {
  const P = (x, y) => ({ x, y, type: "stitch" });
  const pts = [P(0, 0), P(20, 0), P(24, 0), P(24, 14), P(24, 18), P(24, 26), P(28, 26), P(28, 18), P(32, 18), P(32, 30)];
  // a second span of only two crosses (a tip): counts in satinSpans, not in strokeSpans
  const tip = [P(100, 0), P(103, 0), P(103, 4), P(106, 4)];
  const stitches = [...pts, ...tip];
  const runs = [{ kind: "satin", i0: 0, i1: 9 }, { kind: "satin", i0: 10, i1: 13 }, { kind: "run", i0: 0, i1: 3 }];
  const c = T.satinColumns({ stitches, runs });
  assert.strictEqual(c.satinSpans, 2);
  assert.strictEqual(c.strokeSpans, 1);
  assert.strictEqual(c.narrowestMm, 1.2);
  assert.strictEqual(c.thinSpans, 0);
  assert.strictEqual(c.minCrossMm, 0.3, "the tip's 3-unit cross is the shortest cross anywhere");
});

test("pins: full test string on two fonts, 3 and 6 mm", () => {
  const keys = ["stitches", "sewn", "sub1", "sub05", "sub03", "repeat", "overRec", "hairlineSpans", "satinSpans", "strokeSpans", "thinSpans", "narrowestMm", "minCrossMm"];
  const t = T.TEXTS[0];
  assert.strictEqual(t, "Hamburgefonstiv 0123");
  // Re-pinned 2026-10-13, zigzag default ON. The short-stitch columns were
  // sub1 / sub05 / sub03 = 515 / 199 / 18 (alchemy 3), 1076 / 350 / 28
  // (alchemy 6, one more stitch: 1837) and 1450 / 376 / 107 (montecarlo 6).
  // montecarlo at 3 mm has no satin and did not move.
  assert.deepStrictEqual(pick(cell("alchemy", t, 3), keys),
    { stitches: 664, sewn: 645, sub1: 407, sub05: 18, sub03: 4, repeat: 0, overRec: 0, hairlineSpans: 1, satinSpans: 45, strokeSpans: 35, thinSpans: 27, narrowestMm: 0.59, minCrossMm: 0.45 });
  assert.deepStrictEqual(pick(cell("alchemy", t, 6), keys),
    { stitches: 1836, sewn: 1817, sub1: 549, sub05: 19, sub03: 7, repeat: 1, overRec: 0, hairlineSpans: 0, satinSpans: 46, strokeSpans: 43, thinSpans: 1, narrowestMm: 0.97, minCrossMm: 0.41 });
  assert.deepStrictEqual(pick(cell("montecarlo", t, 3), keys),
    { stitches: 543, sewn: 522, sub1: 508, sub05: 111, sub03: 80, repeat: 49, overRec: 0, hairlineSpans: 44, satinSpans: 0, strokeSpans: 0, thinSpans: 0, narrowestMm: null, minCrossMm: null });
  assert.deepStrictEqual(pick(cell("montecarlo", t, 6), keys),
    { stitches: 1532, sewn: 1511, sub1: 1444, sub05: 188, sub03: 89, repeat: 47, overRec: 0, hairlineSpans: 51, satinSpans: 48, strokeSpans: 30, thinSpans: 30, narrowestMm: 0.5, minCrossMm: 0.41 });
});

// jersey_15 is the extreme: at a 4 mm cap 11,180 of its 11,789 sewn segments are
// under the short-stitch floor (94.8%), against 0.0% at its own 12 mm control.
test("pins: jersey_15 at 4 mm is nearly all short stitches", () => {
  const c = cell("jersey_15", T.TEXTS[0], 4);
  assert.deepStrictEqual(pick(c, ["stitches", "sewn", "sub03", "satinSpans"]), { stitches: 11920, sewn: 11789, sub03: 11180, satinSpans: 0 });
  assert.strictEqual(c.capMiss, false);
});

test("the engine's own report is read, not re-derived", () => {
  const c = cell("alchemy", T.TEXTS[0], 3);
  assert.strictEqual(c.capFloorMm, 4, "CAP_FLOOR_MM");
  assert.strictEqual(c.underFloor, true, "3 mm is under the Studio's 4 mm warning");
  assert.strictEqual(c.hairlineMm, 22.97);
  assert.strictEqual(c.thinMm, 101.97);
  assert.strictEqual(c.columns, 37);
});

test("errors are rows, not crashes: reported and written to the CSV", () => {
  const rows = [
    { font: "boom", error: 'no "such" font, really', cells: [] },
    { font: "cellfail", cells: [{ text: "t", cap: 3, empty: true, error: "engine threw", engineClean: false, unsupported: 0 }] },
  ];
  assert.ok(T.report(rows).includes("errors: 2"));
  const lines = T.csv(rows).trim().split("\n");
  assert.strictEqual(lines.length, 3, "header and one row each");
  assert.ok(lines[1].endsWith(',"no ""such"" font, really"'));
  assert.ok(lines[2].endsWith(",false,engine threw"));
  // a text the font sews nothing of is an empty cell with no error, not a throw
  const none = T.measureFont("alchemy", [3], ["אב"]);
  assert.strictEqual(none.cells[0].empty, true);
  assert.ok(!none.cells[0].error);
});

test("verdicts: the smallest clean cap must hold at every larger cap", () => {
  const mk = (font, flags) => ({ font, cells: flags.flatMap((f) => [3, 4, 5].map((cap, j) => ({ text: "t", cap, empty: false, engineClean: f[j] }))) });
  const rows = [mk("up", [[false, true, true]]), mk("dip", [[true, false, true]]), mk("never", [[false, false, false]]), mk("all", [[true, true, true]])];
  const v = Object.fromEntries(T.verdicts(rows, "engine").map((x) => [x.font, x.smallest]));
  assert.deepStrictEqual(v, { up: 4, dip: 5, never: null, all: 3 });
});

test("relative: a font is held to its own 12 mm control, by the margin", () => {
  const c = (cap, sub03, extra = {}) => Object.assign({ text: "t", cap, empty: false, engineClean: true, sewn: 100, sub03 }, extra);
  const ok = { font: "ok", cells: [c(3, 4), c(12, 2)] };      // 4% vs 2% + 2pp: on the line, clean
  const bad = { font: "bad", cells: [c(3, 5), c(12, 2)] };    // 5% vs 4%: over
  const v = Object.fromEntries(T.verdicts([ok, bad], "relative").map((x) => [x.font, x.smallest]));
  assert.deepStrictEqual(v, { ok: 3, bad: null });
  assert.strictEqual(T.REL_SHORT_PP, 2);
});

test("a font that sews nothing is listed, not scored", () => {
  const rows = [{ font: "blank", cells: [{ text: "t", cap: 3, empty: true }] }, { font: "ok", cells: [{ text: "t", cap: 3, empty: false, engineClean: true }] }];
  assert.deepStrictEqual(T.verdicts(rows, "engine").map((x) => x.font), ["ok"]);
});

test("contact sheet: renders through render.js at laid size", () => {
  const { W, H, png } = T.contactSheet(["alchemy"], [3, 6], "Hi", 10);
  assert.ok(W > 100 && H > 20 && H < 200, `${W}x${H}`);
  assert.strictEqual(png.subarray(1, 4).toString("latin1"), "PNG");
});
