const assert = require("node:assert");
const { test } = require("node:test");
const svgpath = require("../src/svgpath.js");

test("parses absolute moveto and lineto", () => {
  const subs = svgpath.parsePathData("M 10 20 L 30 40 L 50 60");
  assert.strictEqual(subs.length, 1);
  assert.strictEqual(subs[0].closed, false);
  assert.deepStrictEqual(subs[0].points, [
    { x: 10, y: 20 }, { x: 30, y: 40 }, { x: 50, y: 60 },
  ]);
});

test("relative commands accumulate from the current point", () => {
  const subs = svgpath.parsePathData("M 10 10 l 5 0 l 0 5");
  assert.deepStrictEqual(subs[0].points, [
    { x: 10, y: 10 }, { x: 15, y: 10 }, { x: 15, y: 15 },
  ]);
});

test("H and V produce horizontal and vertical segments", () => {
  const subs = svgpath.parsePathData("M 0 0 H 10 V 10 h -5 v -5");
  assert.deepStrictEqual(subs[0].points, [
    { x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 },
    { x: 5, y: 10 }, { x: 5, y: 5 },
  ]);
});

test("Z closes the subpath and a following command starts a new one", () => {
  const subs = svgpath.parsePathData("M 0 0 L 10 0 L 10 10 Z M 20 20 L 30 20");
  assert.strictEqual(subs.length, 2);
  assert.strictEqual(subs[0].closed, true);
  assert.strictEqual(subs[0].points.length, 3);
  assert.strictEqual(subs[1].closed, false);
  assert.deepStrictEqual(subs[1].points, [{ x: 20, y: 20 }, { x: 30, y: 20 }]);
});

test("after Z the current point returns to the subpath start", () => {
  const subs = svgpath.parsePathData("M 5 5 L 10 5 Z l 0 10");
  assert.strictEqual(subs.length, 2);
  assert.deepStrictEqual(subs[1].points[0], { x: 5, y: 5 });
  assert.deepStrictEqual(subs[1].points[1], { x: 5, y: 15 });
});

test("implicit repeated coordinates repeat the last command", () => {
  const subs = svgpath.parsePathData("M 0 0 10 10 20 20");
  assert.deepStrictEqual(subs[0].points, [
    { x: 0, y: 0 }, { x: 10, y: 10 }, { x: 20, y: 20 },
  ]);
});

test("comma and negative-sign separated numbers parse", () => {
  const subs = svgpath.parsePathData("M0,0L-5.5,3e1");
  assert.deepStrictEqual(subs[0].points, [{ x: 0, y: 0 }, { x: -5.5, y: 30 }]);
});

test("empty or whitespace path data yields no subpaths", () => {
  assert.deepStrictEqual(svgpath.parsePathData(""), []);
  assert.deepStrictEqual(svgpath.parsePathData("   "), []);
});

test("explicit tolerance of 0 is respected, not treated as falsy", () => {
  // With tolerance 0.2 (default), few points are emitted. With an explicit
  // tolerance of 0, the curve must be subdivided far more finely, since only
  // an exact (near-zero-deviation) approximation is acceptable. If the
  // implementation used `||` instead of a nullish check, an explicit 0 would
  // silently fall back to 0.2 and this would fail.
  const withDefault = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0.2 });
  const withZero = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0 });
  assert.ok(withZero[0].points.length > withDefault[0].points.length);
});

function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

// Maximum distance from any emitted point to the true cubic curve,
// sampled densely. Used to assert the flattening tolerance is honored.
function maxDeviationFromCubic(points, p0, p1, p2, p3) {
  const samples = [];
  for (let i = 0; i <= 2000; i++) {
    const t = i / 2000, u = 1 - t;
    samples.push({
      x: u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x,
      y: u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y,
    });
  }
  let worst = 0;
  for (const s of samples) {
    let best = Infinity;
    for (const p of points) best = Math.min(best, dist(p, s));
    worst = Math.max(worst, best);
  }
  return worst;
}

test("cubic bezier flattens within tolerance", () => {
  const subs = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0.5 });
  const pts = subs[0].points;
  assert.ok(pts.length > 4, "expected subdivision, got " + pts.length + " points");
  assert.deepStrictEqual(pts[0], { x: 0, y: 0 });
  assert.deepStrictEqual(pts[pts.length - 1], { x: 100, y: 0 });
  const dev = maxDeviationFromCubic(pts,
    { x: 0, y: 0 }, { x: 0, y: 100 }, { x: 100, y: 100 }, { x: 100, y: 0 });
  assert.ok(dev <= 0.5, "deviation " + dev + " exceeded tolerance 0.5");
});

test("tighter tolerance produces more points", () => {
  const coarse = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 2 });
  const fine = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0", { tolerance: 0.05 });
  assert.ok(fine[0].points.length > coarse[0].points.length);
});

test("quadratic bezier flattens and ends at its endpoint", () => {
  const subs = svgpath.parsePathData("M 0 0 Q 50 100 100 0", { tolerance: 0.5 });
  const pts = subs[0].points;
  assert.ok(pts.length > 3);
  assert.deepStrictEqual(pts[pts.length - 1], { x: 100, y: 0 });
  // Apex of this symmetric quadratic is at t=0.5 -> (50, 50).
  let closest = Infinity;
  for (const p of pts) closest = Math.min(closest, dist(p, { x: 50, y: 50 }));
  assert.ok(closest < 1, "expected a point near the apex, closest was " + closest);
});

test("S reflects the previous cubic control point", () => {
  // Explicit equivalent of the smooth form: reflection of (0,100) about
  // (100,0) is (200,-100).
  const smooth = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0 S 200 -100 200 0", { tolerance: 0.25 });
  const explicit = svgpath.parsePathData("M 0 0 C 0 100 100 100 100 0 C 100 -100 200 -100 200 0", { tolerance: 0.25 });
  assert.deepStrictEqual(smooth[0].points, explicit[0].points);
});

test("T reflects the previous quadratic control point", () => {
  const smooth = svgpath.parsePathData("M 0 0 Q 50 100 100 0 T 200 0", { tolerance: 0.25 });
  const explicit = svgpath.parsePathData("M 0 0 Q 50 100 100 0 Q 150 -100 200 0", { tolerance: 0.25 });
  assert.deepStrictEqual(smooth[0].points, explicit[0].points);
});

test("S without a preceding curve uses the current point as control", () => {
  const subs = svgpath.parsePathData("M 10 10 S 20 20 30 10", { tolerance: 0.5 });
  assert.deepStrictEqual(subs[0].points[0], { x: 10, y: 10 });
  assert.deepStrictEqual(subs[0].points[subs[0].points.length - 1], { x: 30, y: 10 });
});
