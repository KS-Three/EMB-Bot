const assert = require("node:assert");
const { test } = require("node:test");
const satin = require("../src/satin.js");

// Long thin rectangle: 120 long, 12 wide. Closed ring (pixel coords).
const rect = [{ x: 0, y: 0 }, { x: 120, y: 0 }, { x: 120, y: 12 }, { x: 0, y: 12 }];

test("estimateWidthMm of a 120x12 rect ~1.1mm", () => {
  // area 1440, perimeter 264 -> 2*1440/264 = 10.909px -> /10 = 1.0909mm
  const w = satin.estimateWidthMm(rect, 10);
  assert.ok(Math.abs(w - 1.1) <= 0.4, `expected ~1.1mm, got ${w}`);
});

test("farthestBoundaryPair returns opposite ends of the rect", () => {
  const [i, j] = satin.farthestBoundaryPair(rect);
  const a = rect[i], b = rect[j];
  const d = Math.hypot(a.x - b.x, a.y - b.y); // ~sqrt(120^2+12^2)=120.6
  assert.ok(d > 118, `expected far pair distance > 118, got ${d}`);
});

test("chainLength sums euclidean segments", () => {
  const L = satin.chainLength([{ x: 0, y: 0 }, { x: 3, y: 4 }, { x: 3, y: 14 }]);
  assert.ok(Math.abs(L - 15) < 1e-9, `expected 15, got ${L}`); // 5 + 10
});

test("splitBoundary walks i->j and j->i sharing endpoints", () => {
  const [A, B] = satin.splitBoundary(rect, 0, 2);
  assert.deepStrictEqual(A, [{ x: 0, y: 0 }, { x: 120, y: 0 }, { x: 120, y: 12 }]);
  assert.deepStrictEqual(B, [{ x: 120, y: 12 }, { x: 0, y: 12 }, { x: 0, y: 0 }]);
});

test("resampleChain gives evenly arc-spaced points incl. endpoints", () => {
  const out = satin.resampleChain([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }], 3);
  assert.strictEqual(out.length, 3);
  assert.ok(Math.abs(out[0].x - 0) < 1e-9 && Math.abs(out[0].y - 0) < 1e-9, "first endpoint");
  assert.ok(Math.abs(out[2].x - 10) < 1e-9 && Math.abs(out[2].y - 10) < 1e-9, "last endpoint");
  // total length 20 -> midpoint at arc-length 10 sits exactly on the corner (10,0)
  assert.ok(Math.abs(out[1].x - 10) <= 0.5 && Math.abs(out[1].y - 0) <= 0.5,
    `middle should be ~(10,0), got (${out[1].x},${out[1].y})`);
});

test("satinColumn zig-zags edge-to-edge across the rect", () => {
  const pts = satin.satinColumn(rect, { spacingMm: 2, pxPerMm: 10 });
  // steps>=ceil(120/(2*10))=6 crosses -> at least 2*6=12 emitted points.
  assert.ok(pts.length >= 12, `expected >=12 points, got ${pts.length}`);
  // stays inside a small margin of the shape.
  assert.ok(pts.every(p => p.x >= -3 && p.x <= 123 && p.y >= -3 && p.y <= 15),
    "all points within bounds");
  // The bounce crosses the mid line y=6 on most consecutive steps: count pairs
  // where one point is below 6 and the next is above (or vice-versa). The two
  // shared tips coincide (zero width there) so a few pairs won't straddle, but
  // a strict majority must.
  let straddle = 0;
  for (let k = 1; k < pts.length; k++) {
    const lo = Math.min(pts[k - 1].y, pts[k].y);
    const hi = Math.max(pts[k - 1].y, pts[k].y);
    if (lo < 6 && hi > 6) straddle++;
  }
  assert.ok(straddle * 2 > (pts.length - 1),
    `expected a majority of consecutive steps to cross the midline, got ${straddle}/${pts.length - 1}`);
});

test("satinColumn with pull compensation widens the column", () => {
  const yRange = (pts) => {
    let lo = Infinity, hi = -Infinity;
    for (const p of pts) { if (p.y < lo) lo = p.y; if (p.y > hi) hi = p.y; }
    return hi - lo;
  };
  const base = satin.satinColumn(rect, { spacingMm: 2, pxPerMm: 10, pullCompMm: 0 });
  const comp = satin.satinColumn(rect, { spacingMm: 2, pxPerMm: 10, pullCompMm: 1 });
  const increase = yRange(comp) - yRange(base);
  // Ideal widening is pullCompMm*pxPerMm = 10px (each edge pushed out 5px). Here
  // the farthest pair is the rect DIAGONAL, so the cross direction runs ~45deg
  // and the vertical projection of the widening is ~10*cos(45)=~7px. Assert a
  // clear, on-the-order-of-10 widening rather than an exact value.
  assert.ok(increase > 4 && increase < 16,
    `expected column to widen by ~10px (diagonal-projected), got ${increase}`);
});

test("degenerate rings (n<3) return [] without crashing", () => {
  assert.deepStrictEqual(satin.satinColumn([], { spacingMm: 2, pxPerMm: 10 }), []);
  assert.deepStrictEqual(satin.satinColumn([{ x: 0, y: 0 }, { x: 1, y: 1 }], { spacingMm: 2, pxPerMm: 10 }), []);
});

test("a nearly-square ring still produces a valid column", () => {
  const nearSquare = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 98 }, { x: 0, y: 98 }];
  const pts = satin.satinColumn(nearSquare, { spacingMm: 3, pxPerMm: 10 });
  assert.ok(pts.length >= 4, `expected some stitches, got ${pts.length}`);
  assert.ok(pts.every(p => Number.isFinite(p.x) && Number.isFinite(p.y)), "all finite");
});
