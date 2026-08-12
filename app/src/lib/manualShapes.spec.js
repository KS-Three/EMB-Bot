import { test, expect } from "vitest";
import {
  isValidShape, isNearStart, shapesToRegions, CLOSE_RADIUS_PX, PX_PER_MM,
  shapeIssues, isDuplicateOfLast, MAX_SHAPE_POINTS,
  quadraticControlForPointOnCurve, curveHandlePoint, curveControlOrNull,
  flattenQuadraticSegment, flattenShape, hitTestSegmentMidpoint, CURVE_HANDLE_HIT_R,
  nextShapeIds, pointInShape,
  distToSegment, nearestSegmentIndex, insertVertexAtSegment,
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

test("shapesToRegions: the explicit 'auto' stitchType sends NO tierOverride (preset shapes leave satin-vs-fill to the engine classifier)", () => {
  const shapes = [{ id: "s1", points: tri(0), stitchType: "auto", colorRgb: [1, 1, 1] }];
  const { regions } = shapesToRegions(shapes);
  expect(regions[0].shapes[0].tierOverride).toBeNull();
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

// ---- pointInShape ---------------------------------------------------------

const SQUARE = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];

test("pointInShape: true for a point well inside a simple polygon", () => {
  expect(pointInShape(SQUARE, 5, 5)).toBe(true);
});

test("pointInShape: false for a point well outside a simple polygon", () => {
  expect(pointInShape(SQUARE, -5, -5)).toBe(false);
  expect(pointInShape(SQUARE, 15, 5)).toBe(false);
});

// Even-odd ray casting is directional about its own boundary: a horizontal
// ray to the right from (x, y) crossing an edge counts that edge only under
// specific tie-breaking rules, so opposite edges of the same square don't
// necessarily agree on "on the boundary" — this pins the ACTUAL behavior
// (deterministic, not flaky) rather than asserting every edge reads as
// inside just because it sounds symmetric.
test("pointInShape: edge case — a point exactly on a vertex", () => {
  expect(pointInShape(SQUARE, 0, 0)).toBe(true);
  expect(pointInShape(SQUARE, 10, 10)).toBe(false);
});

test("pointInShape: edge case — a point exactly on an edge (not at a vertex)", () => {
  expect(pointInShape(SQUARE, 5, 0)).toBe(true); // bottom edge
  expect(pointInShape(SQUARE, 10, 5)).toBe(false); // right edge
});

// An "L" shape (a square with its top-right quadrant notched out) — the
// notch itself must read as outside even though it sits within the shape's
// bounding box, and the reflex (concave) vertex must not falsely read as
// inside.
const CONCAVE_L = [
  { x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 5 },
  { x: 5, y: 5 }, { x: 5, y: 10 }, { x: 0, y: 10 },
];

test("pointInShape: concave polygon — inside the solid body, in either arm", () => {
  expect(pointInShape(CONCAVE_L, 2, 2)).toBe(true); // lower-left, shared body
  expect(pointInShape(CONCAVE_L, 8, 2)).toBe(true); // lower-right arm
  expect(pointInShape(CONCAVE_L, 2, 8)).toBe(true); // upper-left arm
});

test("pointInShape: concave polygon — the notched-out region reads as outside", () => {
  expect(pointInShape(CONCAVE_L, 7, 7)).toBe(false);
  expect(pointInShape(CONCAVE_L, 6, 6)).toBe(false);
});

test("pointInShape: empty/absent points is always false, not a throw", () => {
  expect(pointInShape([], 0, 0)).toBe(false);
  expect(pointInShape(undefined, 0, 0)).toBe(false);
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

// ---- Edge-click-to-insert-vertex ------------------------------------------

const EDGE_SQUARE = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];

test("distToSegment: zero at either endpoint and the true perpendicular distance off a mid-point", () => {
  const a = { x: 0, y: 0 }, b = { x: 100, y: 0 };
  expect(distToSegment(a, a, b)).toBe(0);
  expect(distToSegment(b, a, b)).toBe(0);
  expect(distToSegment({ x: 50, y: 8 }, a, b)).toBeCloseTo(8, 9);
});

test("distToSegment: clamps to the nearest endpoint once the projection falls off either end", () => {
  const a = { x: 0, y: 0 }, b = { x: 100, y: 0 };
  // Off the b-end: closest point on the segment is b itself, not an
  // extension of the infinite line through a-b.
  expect(distToSegment({ x: 150, y: 0 }, a, b)).toBeCloseTo(50, 9);
});

test("distToSegment: a zero-length segment (a === b) falls back to plain point distance", () => {
  const a = { x: 10, y: 10 };
  expect(distToSegment({ x: 13, y: 14 }, a, a)).toBeCloseTo(5, 9);
});

test("nearestSegmentIndex: a point near a shared vertex resolves to whichever adjacent segment it's actually closer to", () => {
  // (2, 1) sits just off the corner (0,0) shared by segment 0 (top,
  // (0,0)-(100,0)) and segment 3 (left, (0,100)-(0,0)) — closer to the top
  // edge's own line (perpendicular distance 1) than the left edge's (2).
  const { index, dist } = nearestSegmentIndex(EDGE_SQUARE, {}, 2, 1, true);
  expect(index).toBe(0);
  expect(dist).toBeCloseTo(1, 9);
});

test("nearestSegmentIndex: a point centered on a straight edge finds that segment and its perpendicular distance", () => {
  const { index, dist } = nearestSegmentIndex(EDGE_SQUARE, {}, 50, 5, true);
  expect(index).toBe(0);
  expect(dist).toBeCloseTo(5, 9);
});

test("nearestSegmentIndex: a point far from the whole shape still resolves to its nearest segment, with a large distance", () => {
  const { index, dist } = nearestSegmentIndex(EDGE_SQUARE, {}, 500, 30, true);
  expect(index).toBe(1); // right edge (100,0)-(100,100)
  expect(dist).toBeCloseTo(400, 9);
});

test("nearestSegmentIndex: closed=false excludes the last-to-first wraparound segment, same as hitTestSegmentMidpoint", () => {
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }];
  // Nearest to the (would-be) wraparound edge (100,100)-(0,0) at its midpoint.
  const open = nearestSegmentIndex(pts, {}, 50, 50, false);
  expect(open.index).not.toBe(2); // segment 2 doesn't exist on the open polyline
  const closed = nearestSegmentIndex(pts, {}, 50, 50, true);
  expect(closed.index).toBe(2);
  expect(closed.dist).toBeCloseTo(0, 9);
});

test("nearestSegmentIndex: hit-tests a curved segment against its actual bowed line, not the straight chord", () => {
  const a = { x: 0, y: 0 }, c = { x: 100, y: 0 };
  const control = quadraticControlForPointOnCurve(a, { x: 50, y: 40 }, c);
  const pts = [a, c, { x: 50, y: 100 }];
  const curves = { 0: control };
  // Right on the curve's own on-curve point — very close.
  const onCurve = nearestSegmentIndex(pts, curves, 50, 41, false);
  expect(onCurve.index).toBe(0);
  expect(onCurve.dist).toBeLessThan(2);
  // The segment's plain straight-line chord midpoint (50, 0) is now far from
  // the actual (curved) line — proof this isn't just testing the chord.
  const atChordMid = nearestSegmentIndex(pts, curves, 50, 0, false);
  expect(atChordMid.dist).toBeGreaterThan(30);
});

test("nearestSegmentIndex: fewer than 2 points has no segment to find", () => {
  expect(nearestSegmentIndex([{ x: 0, y: 0 }], {}, 5, 5, false)).toEqual({ index: -1, dist: Infinity });
  expect(nearestSegmentIndex([], {}, 5, 5, true)).toEqual({ index: -1, dist: Infinity });
});

// insertVertexAtSegment: a 6-point ring, curved on segments 2 and 4 — chosen
// so an insert well away from both (segment 1) exercises the "shift every
// later index up by one, leave earlier ones alone" reindexing rule without
// also hitting the "drop the split segment's own curve" rule at the same time.
function hexRing() {
  const pts = [];
  for (let i = 0; i < 6; i++) pts.push({ x: i * 10, y: 0 });
  return pts;
}

test("insertVertexAtSegment: splices the new point at segIndex + 1, leaving every other anchor untouched", () => {
  const shape = { id: "s1", points: hexRing(), curves: {}, stitchType: "fill", colorRgb: [1, 2, 3] };
  const next = insertVertexAtSegment(shape, 1, { x: 15, y: 5 });
  expect(next.points).toHaveLength(7);
  expect(next.points[2]).toEqual({ x: 15, y: 5 });
  // Everything before and after the split is untouched, just shifted.
  expect(next.points[0]).toEqual({ x: 0, y: 0 });
  expect(next.points[1]).toEqual({ x: 10, y: 0 });
  expect(next.points[3]).toEqual({ x: 20, y: 0 });
  expect(next.points[6]).toEqual({ x: 50, y: 0 });
  // The original shape is never mutated.
  expect(shape.points).toHaveLength(6);
});

test("insertVertexAtSegment: reindexes curves after the split segment up by one, leaves earlier ones alone (the key regression case)", () => {
  const shape = {
    id: "s1",
    points: hexRing(),
    curves: { 2: { x: 99, y: 1 }, 4: { x: 99, y: 2 } },
    stitchType: "fill",
    colorRgb: [1, 2, 3],
  };
  const next = insertVertexAtSegment(shape, 1, { x: 15, y: 5 });
  expect(next.curves).toEqual({ 3: { x: 99, y: 1 }, 5: { x: 99, y: 2 } });
  expect(next.curves[2]).toBeUndefined();
  expect(next.curves[4]).toBeUndefined();
  // The original shape's curves map is never mutated.
  expect(shape.curves).toEqual({ 2: { x: 99, y: 1 }, 4: { x: 99, y: 2 } });
});

test("insertVertexAtSegment: a curve on the split segment itself is dropped, not carried onto either new half", () => {
  const shape = { id: "s1", points: hexRing(), curves: { 1: { x: 12, y: 8 } } };
  const next = insertVertexAtSegment(shape, 1, { x: 15, y: 5 });
  expect(next.curves[1]).toBeUndefined();
  expect(next.curves[2]).toBeUndefined();
});

test("insertVertexAtSegment: a curve before the split segment keeps its original index", () => {
  const shape = { id: "s1", points: hexRing(), curves: { 0: { x: 5, y: 5 } } };
  const next = insertVertexAtSegment(shape, 3, { x: 35, y: 5 });
  expect(next.curves).toEqual({ 0: { x: 5, y: 5 } });
});

test("insertVertexAtSegment: preserves every other shape field (id, stitchType, colorRgb, angleDeg) unchanged", () => {
  const shape = {
    id: "s7", points: hexRing(), curves: {}, stitchType: "satin", colorRgb: [9, 8, 7], angleDeg: 45,
  };
  const next = insertVertexAtSegment(shape, 0, { x: 5, y: 5 });
  expect(next.id).toBe("s7");
  expect(next.stitchType).toBe("satin");
  expect(next.colorRgb).toEqual([9, 8, 7]);
  expect(next.angleDeg).toBe(45);
});

test("insertVertexAtSegment: at MAX_SHAPE_POINTS, returns the exact same shape reference unchanged (no-op)", () => {
  const bigPoints = [];
  for (let i = 0; i < MAX_SHAPE_POINTS; i++) bigPoints.push({ x: i, y: 0 });
  const shape = { id: "s1", points: bigPoints, curves: {} };
  const next = insertVertexAtSegment(shape, 0, { x: 0.5, y: 1 });
  expect(next).toBe(shape);
  expect(next.points).toHaveLength(MAX_SHAPE_POINTS);
});

test("insertVertexAtSegment: a shape with no curves field at all still inserts cleanly (empty curves map, no throw)", () => {
  const shape = { id: "s1", points: hexRing() };
  const next = insertVertexAtSegment(shape, 2, { x: 25, y: 5 });
  expect(next.points).toHaveLength(7);
  expect(next.curves).toEqual({});
});
