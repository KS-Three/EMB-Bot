// Cross-stitch fill (2026-08-21). See src/crossfill.js for why this is written
// from first principles rather than ported: Ink/Stitch's version is GPL-3.0 and
// this product is sold.
//
// The two things worth pinning are the ones that produced convincing wreckage
// during development:
//
//   1. NONZERO winding, not even-odd. Even-odd XORs overlapping rings into a
//      hole. It rendered jersey_15 (one ring per glyph) flawlessly and
//      jacquard_12 (two rings) as scattered fragments — with ~100% lattice fit
//      on both, so no numeric check caught it.
//   2. The grid is MEASURED. Gate 1 bars picking a physical cell size, so
//      detectLattice recovers the digitizer's own grid from the pixel-art
//      outlines. A font whose outlines do not actually lie on one grid must be
//      REFUSED, not guessed at — five upstream picture-fonts fit only 48-71%
//      and would otherwise be filled with crosses in meaningless places.
const assert = require("node:assert");
const { test } = require("node:test");
const CF = require("../src/crossfill.js");

// A 4x4-cell square on a step-10 lattice with origin 0.
const SQUARE = [[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]];
const LAT = { step: 10, offX: 0, offY: 0 };
const ring = (pts) => pts.map((p) => ({ x: p[0], y: p[1] }));

// Real pixel art traces cell boundaries, so its edges are mostly ONE cell long
// — that is what makes the cell recoverable. A plain 40x40 square is a poor
// fixture here precisely because its only edges are 40 long, and detectLattice
// correctly answers "the grid is 40". This staircase steps in 10s.
const PIXEL_ART = [
  [0, 0], [10, 0], [10, 10], [20, 10], [20, 20], [30, 20], [30, 30], [40, 30],
  [40, 40], [30, 40], [20, 40], [10, 40], [0, 40], [0, 30], [0, 20], [0, 10], [0, 0],
];

test("detectLattice recovers step and reports a high fit for grid-aligned art", () => {
  const lat = CF.detectLattice([PIXEL_ART]);
  assert.strictEqual(lat.step, 10, "the one-cell staircase edge is the grid");
  assert.ok(lat.fit > 0.9, `expected a confident fit, got ${lat.fit}`);
});

test("detectLattice reports a LOW fit for geometry that is not on a grid", () => {
  // Deliberately irregular — the shape of the picture-fonts that must be refused.
  const blob = [[0, 0], [13.7, 4.1], [22.3, 19.9], [7.7, 31.2], [0, 0]];
  const lat = CF.detectLattice([blob]);
  if (lat) assert.ok(lat.fit < 0.9, `expected a poor fit for off-grid art, got ${lat.fit}`);
});

test("a solid square fills every cell inside it", () => {
  const strokes = CF.crossFill([ring(SQUARE)], LAT, { method: "simple_cross" });
  // simple_cross is two diagonals per cell; 4x4 cells => 16 crosses => 32 strokes
  assert.strictEqual(strokes.length, 32, `expected 16 crosses, got ${strokes.length / 2}`);
  assert.ok(strokes.every((s) => s.kind === "cross"));
  assert.ok(strokes.every((s) => s.pts.length === 2));
});

test("double_cross adds the upright pair over the diagonals", () => {
  const simple = CF.crossFill([ring(SQUARE)], LAT, { method: "simple_cross" });
  const double = CF.crossFill([ring(SQUARE)], LAT, { method: "double_cross" });
  assert.strictEqual(double.length, simple.length * 2, "double_cross is 4 strokes per cell");
});

test("nonzero winding: a counter-wound inner ring is a HOLE", () => {
  // Outer CW, inner CCW — an "o". The middle 2x2 must stay empty.
  const outer = ring([[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]]);
  const inner = ring([[10, 10], [10, 30], [30, 30], [30, 10], [10, 10]]);
  assert.strictEqual(CF.insideRings([outer, inner], 20, 20), false, "hole should be empty");
  assert.strictEqual(CF.insideRings([outer, inner], 5, 5), true, "ring body should be filled");
  const strokes = CF.crossFill([outer, inner], LAT, { method: "simple_cross" });
  assert.strictEqual(strokes.length / 2, 12, "16 cells minus a 2x2 hole = 12 crosses");
});

test("nonzero winding: two SAME-wound overlapping rings union, they do not cancel", () => {
  // This is exactly what even-odd got wrong. Both wound the same way; the
  // overlap must stay filled rather than punching a hole.
  const a = ring([[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]]);
  const b = ring([[20, 20], [60, 20], [60, 60], [20, 60], [20, 20]]);
  assert.strictEqual(CF.insideRings([a, b], 25, 25), true,
    "overlap of two same-wound rings must remain INSIDE (even-odd would drop it)");
});

test("an empty or degenerate lattice yields no stitches rather than throwing", () => {
  assert.deepStrictEqual(CF.crossFill([ring(SQUARE)], null, {}), []);
  assert.deepStrictEqual(CF.crossFill([], LAT, {}), []);
  assert.deepStrictEqual(CF.crossFill([ring(SQUARE)], { step: 0, offX: 0, offY: 0 }, {}), []);
});

test("a pathologically fine lattice bails instead of hanging", () => {
  // 40x40 units at step 0.01 would be 16 million cells.
  const out = CF.crossFill([ring(SQUARE)], { step: 0.01, offX: 0, offY: 0 }, {});
  assert.deepStrictEqual(out, [], "must refuse rather than attempt a 16M-cell fill");
});

test("cells are visited in serpentine order so carries stay about one cell", () => {
  const strokes = CF.crossFill([ring(SQUARE)], LAT, { method: "simple_cross" });
  // Row 1 runs one way, row 2 the other: the x of the last cross in a row is
  // near the x of the first cross in the next.
  const centres = [];
  for (let i = 0; i < strokes.length; i += 2) {
    const s = strokes[i].pts;
    centres.push({ x: (s[0].x + s[1].x) / 2, y: (s[0].y + s[1].y) / 2 });
  }
  for (let i = 1; i < centres.length; i++) {
    const d = Math.hypot(centres[i].x - centres[i - 1].x, centres[i].y - centres[i - 1].y);
    assert.ok(d <= LAT.step * 1.5 + 1e-6, `carry of ${d} between consecutive crosses is too long`);
  }
});

test("a carry across a GAP in the ink lifts the needle instead of dragging thread", () => {
  // Two separate 1-cell blocks with a 2-cell gap on the same row — the shape of
  // an "M" valley. Crossing it needle-down draws a visible line over the letter.
  const a = ring([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]);
  const b = ring([[40, 0], [50, 0], [50, 10], [40, 10], [40, 0]]);
  const strokes = CF.crossFill([a, b], LAT, { method: "simple_cross", firstIsJump: false });
  const jumps = strokes.filter((s) => s.jump).length;
  assert.strictEqual(jumps, 1, `expected exactly one jump across the gap, got ${jumps}`);
});

test("adjacent cells do NOT jump — the whole point is a continuous walk", () => {
  const strokes = CF.crossFill([ring(SQUARE)], LAT, { method: "simple_cross", firstIsJump: false });
  assert.strictEqual(strokes.filter((s) => s.jump).length, 0,
    "a solid block is one continuous serpentine walk with no lifts");
});
