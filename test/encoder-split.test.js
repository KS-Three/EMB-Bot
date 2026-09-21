// A move too long for one record is SPLIT. Where the intermediate points land
// is what this file pins.
//
// All three encoders clamped each axis INDEPENDENTLY until 2026-09-20
// (`clampStep(dx)` and `clampStep(dy)` in the same loop), which spends the
// smaller axis entirely in the first record and then runs straight along the
// other one. The endpoints were right, the bounding box was right, the stitch
// count was right — and the path between them was an L where the design, and
// the Studio's preview, drew a diagonal. Measured on a customer path the day
// it was found: an auto-digitized logo resized to 250 mm produced 24 such
// segments and put the file's thread up to 0.41 mm off the drawn line; a
// synthetic 30.6 mm diagonal was 3.6 mm off.
//
// Nothing caught it because every over-length fixture in the repo was
// AXIS-ALIGNED — the crossval harness's `long` fixture is 300 units in x and
// zero in y, and an axis-aligned split is straight however you clamp it. So
// the cases below are deliberately diagonal, with both axes over the limit,
// one axis over, and the smaller axis just under.
const assert = require("node:assert");
const { test } = require("node:test");

const { splitSteps: dstSplit, encodeDST } = require("../src/dst.js");
const { splitSteps: expSplit } = require("../src/exp.js");
const { splitSteps: pesSplit } = require("../src/pes.js");
const { decodeDST } = require("../src/dstimport.js");

// Every intermediate landing point, as offsets from the segment's start.
function walk(steps) {
  const pts = [];
  let x = 0, y = 0;
  for (const [sx, sy] of steps) { x += sx; y += sy; pts.push([x, y]); }
  return pts;
}

// How far a point strays from the straight line (0,0)->(dx,dy).
function strayFromLine(px, py, dx, dy) {
  const len = Math.hypot(dx, dy);
  if (len === 0) return Math.hypot(px, py);
  return Math.abs(dx * py - dy * px) / len;
}

const CASES = [
  [600, 121, "both axes over once split; the classic L"],
  [60, 300, "small x, long y — the 2026-09-20 repro"],
  [1000, 200, "long run with a shallow rise"],
  [-437, 289, "negative x, both over"],
  [121, 121, "exactly at the limit, no split needed"],
  [0, 0, "zero move"],
  [-5, 3, "short move, one record"],
];

for (const [name, split, limit] of [["dst", dstSplit, 121], ["exp", expSplit, 127], ["pes", pesSplit, 2047]]) {
  test(`${name}: split steps sum exactly, stay within the record limit, and follow the line`, () => {
    for (const [dx, dy, why] of CASES) {
      const steps = split(dx, dy, limit, 1);
      const sum = steps.reduce((a, s) => [a[0] + s[0], a[1] + s[1]], [0, 0]);
      assert.deepStrictEqual(sum, [dx, dy], `${why}: steps must land exactly on the target`);
      for (const [sx, sy] of steps) {
        assert.ok(Math.abs(sx) <= limit && Math.abs(sy) <= limit,
          `${why}: step (${sx},${sy}) exceeds the ${limit}-unit record limit`);
      }
      const needed = Math.max(Math.ceil(Math.abs(dx) / limit), Math.ceil(Math.abs(dy) / limit), 1);
      assert.ok(steps.length >= needed && steps.length <= needed + 1,
        `${why}: ${steps.length} steps for a move needing ${needed}`);
      for (const [px, py] of walk(steps)) {
        // Cumulative rounding puts each landing point within half a unit of
        // the exact line on each axis, so under 1 unit (0.1 mm) off it.
        assert.ok(strayFromLine(px, py, dx, dy) < 1,
          `${why}: (${px},${py}) is ${strayFromLine(px, py, dx, dy).toFixed(2)} units off the line`);
      }
    }
  });

  test(`${name}: a minimum step count still follows the line (the trim case)`, () => {
    const steps = split(40, 260, limit, 3);
    assert.ok(steps.length >= 3, "a trim needs at least 3 records to read as a trim");
    assert.deepStrictEqual(steps.reduce((a, s) => [a[0] + s[0], a[1] + s[1]], [0, 0]), [40, 260]);
    for (const [px, py] of walk(steps)) {
      assert.ok(strayFromLine(px, py, 40, 260) < 1, `(${px},${py}) is off the line`);
    }
  });
}

test("dst: a long diagonal stitch sews along the line a reader can see", () => {
  // The preview draws one straight segment from (200,900) to (260,1200).
  // Before the fix the file walked (260,1021) -> (260,1142) -> (260,1200):
  // the whole 60-unit x move spent in the first record, 36 units (3.6 mm)
  // off the line the customer was shown.
  const stitches = [
    { x: 200, y: 900, type: "stitch" },
    { x: 260, y: 1200, type: "stitch" },
    { x: 900, y: 1300, type: "stitch" },
    { x: 900, y: 1300, type: "end" },
  ];
  const design = {
    label: "SPLIT", stitches, colors: [{ r: 0, g: 0, b: 0 }],
    stitchCount: 3, widthMM: 70, heightMM: 40,
  };
  const decoded = decodeDST(encodeDST(design));
  const raw = decoded.stitches.filter((s) => (s.type || "stitch") === "stitch").map((s) => [s.x, s.y]);
  // decodeDST re-centres on the stitch bbox, so align on the first point:
  // where the design sits is not what this test is about.
  const ox = 200 - raw[0][0], oy = 900 - raw[0][1];
  const pts = raw.map(([x, y]) => [x + ox, y + oy]);

  // endpoints survive
  assert.deepStrictEqual(pts[0], [200, 900]);
  assert.deepStrictEqual(pts[pts.length - 1], [900, 1300]);

  // and every point in between lies on one of the two drawn segments
  const segs = [[200, 900, 260, 1200], [260, 1200, 900, 1300]];
  for (const [px, py] of pts) {
    const best = Math.min(...segs.map(([x0, y0, x1, y1]) => {
      const vx = x1 - x0, vy = y1 - y0;
      const t = Math.max(0, Math.min(1, ((px - x0) * vx + (py - y0) * vy) / (vx * vx + vy * vy)));
      return Math.hypot(px - (x0 + vx * t), py - (y0 + vy * t));
    }));
    assert.ok(best < 1, `stitch (${px},${py}) is ${best.toFixed(1)} units off every drawn segment`);
  }
});
