import { test, expect } from "vitest";
import {
  isValidShape, isNearStart, shapesToRegions, CLOSE_RADIUS_PX, PX_PER_MM,
  shapeIssues, isDuplicateOfLast, MAX_SHAPE_POINTS,
  quadraticControlForPointOnCurve, curveHandlePoint, curveControlOrNull,
  flattenQuadraticSegment, flattenShape, hitTestSegmentMidpoint, CURVE_HANDLE_HIT_R,
  nextShapeIds,
} from "./manualShapes.js";

// ---- isValidShape -----------------------------------------------------

test("isValidShape: rejects fewer than 3 points", () => {
  expect(isValidShape([])).toBe(false);
  expect(isValidShape([{ x: 0, y: 0 }])).toBe(false);
  expect(isValidShape([{ x: 0, y: 0 }, { x: 10, y: 10 }])).toBe(false);
});

test("isValidShape: accepts a real triangle", () => {
  expect(isValidShape([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 5, y: 10 }])).toBe(true);
});

test("isValidShape: rejects a degenerate (zero-area, collinear) triple", () => {
  expect(isValidShape([{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }])).toBe(false);
});

test("isValidShape: rejects three points that are all the same click (no real geometry)", () => {
  expect(isValidShape([{ x: 3, y: 3 }, { x: 3, y: 3 }, { x: 3, y: 3 }])).toBe(false);
});

test("isValidShape: rejects non-array input", () => {
  expect(isValidShape(null)).toBe(false);
  expect(isValidShape(undefined)).toBe(false);
});

// ---- isNearStart --------------------------------------------------------

test("isNearStart: true when within CLOSE_RADIUS_PX of the first point", () => {
  const pts = [{ x: 100, y: 100 }, { x: 150, y: 100 }];
  expect(isNearStart(pts, 100 + CLOSE_RADIUS_PX - 1, 100)).toBe(true);
  expect(isNearStart(pts, 100, 100)).toBe(true);
});

test("isNearStart: false when outside the radius", () => {
  const pts = [{ x: 100, y: 100 }, { x: 150, y: 100 }];
  expect(isNearStart(pts, 100 + CLOSE_RADIUS_PX + 5, 100)).toBe(false);
});

test("isNearStart: false with fewer than 2 points placed (closing a 1-point shape is meaningless)", () => {
  expect(isNearStart([{ x: 100, y: 100 }], 100, 100)).toBe(false);
  expect(isNearStart([], 100, 100)).toBe(false);
});

// ---- shapesToRegions ------------------------------------------------------

function tri(dx = 0) {
  return [{ x: 0 + dx, y: 0 }, { x: 20 + dx, y: 0 }, { x: 10 + dx, y: 20 }];
}

test("shapesToRegions: each shape becomes its own region carrying tierOverride/angleOverride/rgb", () => {
  const shapes = [
    { id: "s1", points: tri(0), stitchType: "satin", colorRgb: [200, 10, 10], angleDeg: 30 },
    { id: "s2", points: tri(100), stitchType: "fill", colorRgb: [10, 10, 200], angleDeg: null },
  ];
  const { regions, pxPerMm } = shapesToRegions(shapes);
  expect(regions).toHaveLength(2);
  expect(pxPerMm).toBe(PX_PER_MM);

  expect(regions[0].rgb).toEqual([200, 10, 10]);
  expect(regions[0].shapes).toHaveLength(1);
  expect(regions[0].shapes[0].tierOverride).toBe("satin");
  expect(regions[0].shapes[0].angleOverride).toBe(30);
  expect(regions[0].shapes[0].holes).toEqual([]);
  expect(regions[0].shapes[0].outer).toHaveLength(3);

  expect(regions[1].rgb).toEqual([10, 10, 200]);
  expect(regions[1].shapes[0].tierOverride).toBe("fill");
  expect(regions[1].shapes[0].angleOverride).toBeNull();
});

test("shapesToRegions: skips invalid/degenerate shapes without throwing", () => {
  const shapes = [
    { id: "s1", points: [{ x: 0, y: 0 }, { x: 1, y: 1 }], stitchType: "fill", colorRgb: [1, 1, 1] }, // only 2 points
    { id: "s2", points: tri(0), stitchType: "fill", colorRgb: [1, 1, 1] },
  ];
  const { regions } = shapesToRegions(shapes);
  expect(regions).toHaveLength(1);
});

test("shapesToRegions: empty/absent shape list produces zero regions, not a throw", () => {
  expect(shapesToRegions([]).regions).toEqual([]);
  expect(shapesToRegions(undefined).regions).toEqual([]);
});

test("shapesToRegions: an unrecognized stitchType falls back to 'fill' (never silently satin)", () => {
  const shapes = [{ id: "s1", points: tri(0), stitchType: "bogus", colorRgb: [1, 1, 1] }];
  const { regions } = shapesToRegions(shapes);
  expect(regions[0].shapes[0].tierOverride).toBe("fill");
});

test("shapesToRegions: missing colorRgb falls back to a sane default instead of undefined", () => {
  const shapes = [{ id: "s1", points: tri(0), stitchType: "fill" }];
  const { regions } = shapesToRegions(shapes);
  expect(regions[0].rgb).toEqual([20, 20, 20]);
});

// ---- shapeIssues / self-intersection ------------------------------------

// Classic bowtie: the two "diagonal" edges of a unit square, wired in an
// order that makes them the non-adjacent boundary segments (0-1) and (2-3)
// — they cross at the square's center even though the shoelace formula
// still reports a nonzero (kite-shaped) area for this vertex order.
const BOWTIE = [{ x: 0, y: 0 }, { x: 10, y: 10 }, { x: 10, y: 0 }, { x: 0, y: 10 }];

test("shapeIssues: flags a self-intersecting bowtie polygon with a clear reason", () => {
  const issues = shapeIssues(BOWTIE);
  expect(issues).toContain("This shape crosses itself.");
});

test("isValidShape: rejects the bowtie even though it has plenty of shoelace area", () => {
  expect(isValidShape(BOWTIE)).toBe(false);
});

test("shapeIssues: a normal (non-crossing) square has no issues", () => {
  const square = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  expect(shapeIssues(square)).toEqual([]);
  expect(isValidShape(square)).toBe(true);
});

test("shapeIssues: fewer than 3 points reports the point-count reason, not a crash", () => {
  expect(shapeIssues([{ x: 0, y: 0 }, { x: 1, y: 1 }])).toEqual(["Needs at least 3 points."]);
});

// ---- isDuplicateOfLast --------------------------------------------------

test("isDuplicateOfLast: true for an exact repeat of the last-placed point", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
  expect(isDuplicateOfLast(pts, 10, 0)).toBe(true);
});

test("isDuplicateOfLast: true within the sub-pixel jitter epsilon", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
  expect(isDuplicateOfLast(pts, 10.2, 0)).toBe(true);
});

test("isDuplicateOfLast: false once a click is a real distance away", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
  expect(isDuplicateOfLast(pts, 12, 0)).toBe(false);
});

test("isDuplicateOfLast: false with no points placed yet (nothing to compare against)", () => {
  expect(isDuplicateOfLast([], 0, 0)).toBe(false);
  expect(isDuplicateOfLast(undefined, 0, 0)).toBe(false);
});

// ---- MAX_SHAPE_POINTS cap ------------------------------------------------

// A convex, non-self-crossing ring of `n` points so the point-count check
// is isolated from the self-intersection check.
function convexRing(n) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const angle = (2 * Math.PI * i) / n;
    pts.push({ x: 200 + 150 * Math.cos(angle), y: 200 + 150 * Math.sin(angle) });
  }
  return pts;
}

test("shapeIssues: exactly MAX_SHAPE_POINTS is not flagged as too many", () => {
  const issues = shapeIssues(convexRing(MAX_SHAPE_POINTS));
  expect(issues.some((m) => m.includes("Too many points"))).toBe(false);
});

test("shapeIssues: MAX_SHAPE_POINTS + 1 is flagged as too many", () => {
  const issues = shapeIssues(convexRing(MAX_SHAPE_POINTS + 1));
  expect(issues.some((m) => m.includes("Too many points"))).toBe(true);
});

// ---- Curved segments -------------------------------------------------

const A = { x: 0, y: 0 };
const C = { x: 100, y: 0 };

test("quadraticControlForPointOnCurve + curveHandlePoint round-trip exactly: the curve passes through the original point", () => {
  const through = { x: 50, y: 30 };
  const control = quadraticControlForPointOnCurve(A, through, C);
  const onCurveMid = curveHandlePoint(A, C, control);
  expect(onCurveMid.x).toBeCloseTo(through.x, 9);
  expect(onCurveMid.y).toBeCloseTo(through.y, 9);
});

test("curveHandlePoint: falls back to the plain chord midpoint when there's no control point (straight segment)", () => {
  expect(curveHandlePoint(A, C, null)).toEqual({ x: 50, y: 0 });
  expect(curveHandlePoint(A, C, undefined)).toEqual({ x: 50, y: 0 });
});

test("curveControlOrNull: null when dragged back near the straight-line midpoint", () => {
  expect(curveControlOrNull(A, C, { x: 50, y: 0.5 })).toBeNull();
  expect(curveControlOrNull(A, C, { x: 50, y: 0 })).toBeNull();
});

test("curveControlOrNull: a real control point once far enough from the midpoint", () => {
  const control = curveControlOrNull(A, C, { x: 50, y: 30 });
  expect(control).not.toBeNull();
  // Round-trips back through the same point (see the exact round-trip test above).
  expect(curveHandlePoint(A, C, control).y).toBeCloseTo(30, 9);
});

test("flattenQuadraticSegment: excludes both endpoints and actually passes near the intended through-point at its middle sample", () => {
  const through = { x: 50, y: 40 };
  const control = quadraticControlForPointOnCurve(A, through, C);
  const pts = flattenQuadraticSegment(A, control, C);
  expect(pts.length).toBeGreaterThan(0);
  // Never re-emits either endpoint.
  for (const p of pts) {
    expect(p).not.toEqual(A);
    expect(p).not.toEqual(C);
  }
  // The middle sample (even count of points -> two straddle t=0.5; odd -> a
  // real midpoint sample) should land close to the through-point.
  const mid = pts[Math.floor(pts.length / 2)];
  expect(Math.hypot(mid.x - through.x, mid.y - through.y)).toBeLessThan(5);
});

test("flattenQuadraticSegment: longer chords get more sub-points than short ones", () => {
  const shortChord = flattenQuadraticSegment({ x: 0, y: 0 }, { x: 10, y: 5 }, { x: 20, y: 0 });
  const longChord = flattenQuadraticSegment({ x: 0, y: 0 }, { x: 200, y: 50 }, { x: 400, y: 0 });
  expect(longChord.length).toBeGreaterThan(shortChord.length);
});

test("flattenShape: with no curves, an open list flattens to itself unchanged", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }];
  expect(flattenShape(pts, {}, false)).toEqual(pts);
  expect(flattenShape(pts, undefined, false)).toEqual(pts);
});

test("flattenShape: with no curves, a closed ring flattens to itself unchanged (no duplicated start point)", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }];
  expect(flattenShape(pts, {}, true)).toEqual(pts);
});

test("flattenShape: a curved segment inserts extra points between its two anchors, endpoints untouched", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const control = quadraticControlForPointOnCurve(pts[0], { x: 50, y: -30 }, pts[1]);
  const flat = flattenShape(pts, { 0: control }, true);
  expect(flat.length).toBeGreaterThan(pts.length);
  expect(flat[0]).toEqual(pts[0]);
  expect(flat[flat.length - 1]).toEqual(pts[3]); // last real anchor, not a re-added pts[0]
  // The inserted points sit strictly between anchor 0 and anchor 1 in the list.
  const anchor1Index = flat.findIndex((p) => p.x === 100 && p.y === 0);
  expect(anchor1Index).toBeGreaterThan(1);
});

test("flattenShape: the closing (wraparound) segment can be curved too, only when closed=true", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const control = quadraticControlForPointOnCurve(pts[3], { x: -20, y: 50 }, pts[0]);
  const closedFlat = flattenShape(pts, { 3: control }, true);
  expect(closedFlat.length).toBeGreaterThan(pts.length);
  // Segment index 3 doesn't exist on the open (draft) polyline (only 3
  // segments: 0-1, 1-2, 2-3) — the same curves map is simply inert there.
  const openFlat = flattenShape(pts, { 3: control }, false);
  expect(openFlat).toEqual(pts);
});

test("flattenShape: empty/absent points returns an empty list, not a throw", () => {
  expect(flattenShape([], {}, true)).toEqual([]);
  expect(flattenShape(null, {}, true)).toEqual([]);
  expect(flattenShape(undefined, {}, false)).toEqual([]);
});

test("hitTestSegmentMidpoint: finds a straight segment's chord midpoint within CURVE_HANDLE_HIT_R", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }];
  expect(hitTestSegmentMidpoint(pts, {}, 50, 0, false)).toBe(0);
  expect(hitTestSegmentMidpoint(pts, {}, 100, 50, false)).toBe(1);
  expect(hitTestSegmentMidpoint(pts, {}, 50, 0 + CURVE_HANDLE_HIT_R + 5, false)).toBe(-1);
});

test("hitTestSegmentMidpoint: finds a CURVED segment's on-curve handle position, not its straight chord midpoint", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }];
  const control = quadraticControlForPointOnCurve(pts[0], { x: 50, y: 40 }, pts[1]);
  // The chord midpoint (50, 0) is no longer the handle once curved.
  expect(hitTestSegmentMidpoint(pts, { 0: control }, 50, 0, false)).toBe(-1);
  expect(hitTestSegmentMidpoint(pts, { 0: control }, 50, 40, false)).toBe(0);
});

test("hitTestSegmentMidpoint: closed=false doesn't offer the last-to-first wraparound segment (a draft isn't closed yet)", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }];
  // Wraparound chord midpoint would be (50, 50).
  expect(hitTestSegmentMidpoint(pts, {}, 50, 50, false)).toBe(-1);
  expect(hitTestSegmentMidpoint(pts, {}, 50, 50, true)).toBe(2);
});

test("shapesToRegions: a curved shape's outer ring is the FLATTENED geometry, not the raw anchors", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const control = quadraticControlForPointOnCurve(pts[0], { x: 50, y: -30 }, pts[1]);
  const shapes = [{ id: "s1", points: pts, curves: { 0: control }, stitchType: "satin", colorRgb: [1, 1, 1] }];
  const { regions } = shapesToRegions(shapes);
  expect(regions).toHaveLength(1);
  expect(regions[0].shapes[0].outer.length).toBeGreaterThan(pts.length);
});

test("shapesToRegions: a curve that makes the flattened shape self-intersect is skipped, even though the raw anchors alone would be valid", () => {
  // A long, thin rectangle; bow the top edge so far down that the curve
  // itself crosses the bottom edge — the anchors form a perfectly fine
  // rectangle, but the real (flattened) geometry self-intersects.
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 10 }, { x: 0, y: 10 }];
  const control = quadraticControlForPointOnCurve(pts[0], { x: 50, y: 200 }, pts[1]);
  const shapes = [{ id: "s1", points: pts, curves: { 0: control }, stitchType: "fill", colorRgb: [1, 1, 1] }];
  const { regions } = shapesToRegions(shapes);
  expect(regions).toHaveLength(0);
});

test("shapesToRegions: a shape with no curves field at all behaves exactly as before this feature existed", () => {
  const pts = [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 10, y: 20 }];
  const shapes = [{ id: "s1", points: pts, stitchType: "fill", colorRgb: [1, 1, 1] }];
  const { regions } = shapesToRegions(shapes);
  expect(regions[0].shapes[0].outer).toEqual(pts);
});

// ---- nextShapeIds ----------------------------------------------------

test("nextShapeIds: allocates N unique sequential ids from one call", () => {
  const list = [{ id: "s3" }, { id: "s1" }];
  expect(nextShapeIds(list, 3)).toEqual(["s4", "s5", "s6"]);
});

test("nextShapeIds: starts at s1 on an empty list", () => {
  expect(nextShapeIds([], 2)).toEqual(["s1", "s2"]);
  expect(nextShapeIds(undefined, 1)).toEqual(["s1"]);
});

test("nextShapeIds: correctly continues past gaps and non-sequential-format ids", () => {
  // s2 is missing (deleted shape) and "custom-id" doesn't match the "s"+N
  // format at all — neither should confuse the max-id scan.
  const list = [{ id: "s1" }, { id: "s5" }, { id: "custom-id" }, { id: "s3" }];
  expect(nextShapeIds(list, 2)).toEqual(["s6", "s7"]);
});

// Regression test for the actual bug scenario nextShapeIds exists to
// prevent: ManualPanel's own nextShapeId(list) recomputes the max id from
// `shapes` every call, so looping IT across a batch (with no patch() in
// between) returns the same id every time. nextShapeIds must not inherit
// that: within one call it hands back non-colliding sequential ids. Two
// back-to-back calls against the SAME unchanged list, on the other hand, are
// only well-defined to each independently start right after the list's
// current max — a caller is expected to call this once per batch, right
// before building the final patch, not call it again before that patch
// lands (which would allocate the same ids twice, same as nextShapeId would
// — this test documents that behavior rather than treating it as a bug).
test("nextShapeIds: within one call, ids never collide; two back-to-back calls against an unchanged list are well-defined (both start after the same max, expected caller usage is once per batch)", () => {
  const list = [{ id: "s1" }];
  const firstBatch = nextShapeIds(list, 2);
  expect(firstBatch).toEqual(["s2", "s3"]);
  expect(new Set(firstBatch).size).toBe(firstBatch.length); // no internal collision

  const secondBatch = nextShapeIds(list, 2); // same unchanged `list`, no patch() in between
  expect(secondBatch).toEqual(["s2", "s3"]); // identical to firstBatch — well-defined, not a crash
});
