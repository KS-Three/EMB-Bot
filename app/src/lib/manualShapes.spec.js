import { test, expect, describe, it, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import {
  COLUMN_DEFAULT_MM, isColumn, columnIssues, shapeRing, shapeProblems, isSewableShape, columnRails,
  isValidShape, isNearStart, shapesToRegions, CLOSE_RADIUS_PX, PX_PER_MM,
  shapeIssues, isDuplicateOfLast, MAX_SHAPE_POINTS,
  quadraticControlForPointOnCurve, curveHandlePoint, curveControlOrNull,
  flattenQuadraticSegment, flattenShape, hitTestSegmentMidpoint, CURVE_HANDLE_HIT_R,
  nextShapeIds, pointInShape,
  distToSegment, nearestSegmentIndex, insertVertexAtSegment,
  curvedNodeThrough, curvedNodeFlags, CURVED_NODE_BOW,
  duplicateShape, PASTE_OFFSET_PX, CANVAS_W, CANVAS_H,
  shouldScrollCanvasIntoView,
  resolveCutOuts, manualShapeName, withCutOut, CUTOUT_NO_PARENT, CUTOUT_OVERLAP,
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

// ---- curved nodes (right-click while drawing) -----------------------------

test("curvedNodeThrough: bows perpendicular to the chord, by CURVED_NODE_BOW of its length", () => {
  const a = { x: 0, y: 0 }, b = { x: 100, y: 0 };
  const t = curvedNodeThrough(a, b, null);
  expect(t.x).toBeCloseTo(50, 6);                        // stays at the chord midpoint...
  expect(Math.abs(t.y)).toBeCloseTo(100 * CURVED_NODE_BOW, 6); // ...displaced across it
});

test("curvedNodeThrough: takes its side from the TURN, so a run of curved nodes arcs one way instead of scalloping", () => {
  // A path turning consistently left (counter-clockwise around a square).
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const sides = [];
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], before = i >= 2 ? pts[i - 2] : null;
    if (!before) continue;
    const t = curvedNodeThrough(a, b, before);
    // Signed side of `through` relative to the chord a->b.
    const cross = (b.x - a.x) * (t.y - a.y) - (b.y - a.y) * (t.x - a.x);
    sides.push(Math.sign(cross));
  }
  expect(sides.length).toBeGreaterThan(1);
  // Every bow lands on the SAME side of its own chord — no alternation.
  expect(new Set(sides).size).toBe(1);
});

test("curvedNodeThrough: the bow FLIPS when the path reverses its turn — the side really is read from the corner", () => {
  // The consistently-left square above cannot tell the real rule apart from
  // "always bow left" or from an inverted flip: every corner there turns the
  // same way, so all three implementations agree. Deleting the turn logic
  // outright left that test green (checked by mutation, 2026-08-25).
  //
  // This fixture zigzags, so it contains BOTH a left turn and right turns, and
  // the bow must land on the outside of each corner independently.
  const pts = [
    { x: 0, y: 0 }, { x: 100, y: 0 }, { x: 150, y: 80 },
    { x: 250, y: 80 }, { x: 300, y: 0 },
  ];
  const samples = [];
  for (let i = 2; i < pts.length; i++) {
    const before = pts[i - 2], a = pts[i - 1], b = pts[i];
    const t = curvedNodeThrough(a, b, before);
    const dx = b.x - a.x, dy = b.y - a.y;
    const turn = Math.sign((a.x - before.x) * dy - (a.y - before.y) * dx);
    const side = Math.sign(dx * (t.y - a.y) - dy * (t.x - a.x));
    samples.push({ turn, side });
  }
  // The fixture genuinely exercises both directions — otherwise this test
  // would be no stronger than the one above.
  expect(new Set(samples.map((s) => s.turn)).size).toBe(2);
  // Bow to the OUTSIDE of the corner: the side is the opposite of the turn.
  for (const s of samples) {
    expect(s.turn).not.toBe(0);
    expect(s.side).toBe(-s.turn);
  }
});

test("curvedNodeThrough: a zero-length chord returns the midpoint rather than NaN", () => {
  const p = { x: 7, y: 9 };
  const t = curvedNodeThrough(p, { ...p }, null);
  expect(Number.isFinite(t.x)).toBe(true);
  expect(Number.isFinite(t.y)).toBe(true);
  expect(t).toEqual({ x: 7, y: 9 });
});

test("curvedNodeThrough round-trips through the existing curve helpers — the drawn curve passes through it", () => {
  const a = { x: 10, y: 10 }, b = { x: 90, y: 40 }, before = { x: 0, y: 0 };
  const through = curvedNodeThrough(a, b, before);
  const control = quadraticControlForPointOnCurve(a, through, b);
  // curveHandlePoint is the inverse: the handle must sit back on `through`,
  // so a right-clicked node and a hand-dragged one are the same kind of thing.
  const back = curveHandlePoint(a, b, control);
  expect(back.x).toBeCloseTo(through.x, 9);
  expect(back.y).toBeCloseTo(through.y, 9);
});

test("curvedNodeFlags: a node is curved when the segment ARRIVING at it is curved", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  // Segment 1 (pts[1] -> pts[2]) is curved, so node 2 is the curved one.
  const flags = curvedNodeFlags(pts, { 1: { x: 15, y: 5 } }, true);
  expect(flags).toEqual([false, false, true, false]);
});

test("curvedNodeFlags: on a CLOSED shape the closing segment feeds node 0; on an open draft node 0 is never curved", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }];
  const closingCurved = { 2: { x: -5, y: 5 } }; // segment pts[2] -> pts[0]
  expect(curvedNodeFlags(pts, closingCurved, true)[0]).toBe(true);
  // An open draft has no closing segment at all, so nothing can arrive at 0.
  expect(curvedNodeFlags(pts, closingCurved, false)[0]).toBe(false);
});

test("curvedNodeFlags: no curves at all means every node reads straight", () => {
  const pts = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }];
  expect(curvedNodeFlags(pts, {}, true)).toEqual([false, false, false]);
  expect(curvedNodeFlags(pts, null, true)).toEqual([false, false, false]);
});

// ---- duplicateShape (copy / paste / duplicate) ----------------------------

test("duplicateShape: same geometry and settings, new id, offset clear of the original", () => {
  const src = {
    id: "s1",
    points: [{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 150, y: 200 }],
    curves: { 0: { x: 150, y: 60 } },
    stitchType: "satin",
    colorRgb: [10, 20, 30],
    angleDeg: 45,
  };
  const copy = duplicateShape(src, "s2");
  expect(copy.id).toBe("s2");
  expect(copy.stitchType).toBe("satin");
  expect(copy.colorRgb).toEqual([10, 20, 30]);
  expect(copy.angleDeg).toBe(45);
  // Every anchor moved by the same offset...
  for (let i = 0; i < src.points.length; i++) {
    expect(copy.points[i].x).toBe(src.points[i].x + PASTE_OFFSET_PX);
    expect(copy.points[i].y).toBe(src.points[i].y + PASTE_OFFSET_PX);
  }
  // ...and so did the curve CONTROL point. A quadratic control is an absolute
  // canvas point, not a delta, so a copy that kept the old control would bow
  // toward the original and read as a different shape.
  expect(copy.curves[0]).toEqual({ x: 150 + PASTE_OFFSET_PX, y: 60 + PASTE_OFFSET_PX });
});

test("duplicateShape: the copy does not alias the original — editing one cannot move the other", () => {
  const src = { id: "s1", points: [{ x: 10, y: 10 }, { x: 20, y: 10 }, { x: 15, y: 20 }], curves: { 0: { x: 15, y: 5 } } };
  const copy = duplicateShape(src, "s2");
  copy.points[0].x = 999;
  copy.curves[0].x = 999;
  expect(src.points[0].x).toBe(10);
  expect(src.curves[0].x).toBe(15);
});

test("duplicateShape: a shape near the edge is pulled back so the copy stays whole and grabbable", () => {
  // Right up against the bottom-right corner: a naive +offset would push part
  // of the copy off-canvas, where it cannot be selected or dragged.
  const src = {
    id: "s1",
    points: [
      { x: CANVAS_W - 5, y: CANVAS_H - 5 },
      { x: CANVAS_W - 40, y: CANVAS_H - 5 },
      { x: CANVAS_W - 20, y: CANVAS_H - 40 },
    ],
    curves: {},
  };
  const copy = duplicateShape(src, "s2");
  for (const pt of copy.points) {
    expect(pt.x).toBeLessThanOrEqual(CANVAS_W);
    expect(pt.y).toBeLessThanOrEqual(CANVAS_H);
    expect(pt.x).toBeGreaterThanOrEqual(0);
    expect(pt.y).toBeGreaterThanOrEqual(0);
  }
});

test("duplicateShape: a shape FLUSH to the edge still moves — the copy never lands on the original", () => {
  // The bug this exists for: with the bounds exactly ON the right and bottom
  // edges, both clamps collapsed to `Math.min(18, 0)` = 0 and the copy was
  // placed at dx = dy = 0, precisely on top of the original. Invisible
  // duplicate; dragging "the copy" moved the original instead. Flush bounds
  // are not exotic -- traceFitRect letterboxes imported artwork right up
  // against the canvas, so any traced outline hits this. Found by review,
  // 2026-08-26.
  const src = {
    id: "s1",
    points: [
      { x: CANVAS_W, y: CANVAS_H },
      { x: CANVAS_W - 100, y: CANVAS_H },
      { x: CANVAS_W - 50, y: CANVAS_H - 100 },
    ],
    curves: {},
  };
  const copy = duplicateShape(src, "s2");
  const dx = copy.points[0].x - src.points[0].x;
  const dy = copy.points[0].y - src.points[0].y;
  expect(dx === 0 && dy === 0).toBe(false);
  expect(Math.abs(dx)).toBe(PASTE_OFFSET_PX);
  expect(Math.abs(dy)).toBe(PASTE_OFFSET_PX);
  // ...and it is still fully on-canvas, which is what the clamp is FOR.
  for (const pt of copy.points) {
    expect(pt.x).toBeGreaterThanOrEqual(0);
    expect(pt.y).toBeGreaterThanOrEqual(0);
    expect(pt.x).toBeLessThanOrEqual(CANVAS_W);
    expect(pt.y).toBeLessThanOrEqual(CANVAS_H);
  }
});

test("duplicateShape: a shape bigger than the canvas is not shoved FURTHER off it", () => {
  // The min-edge clamps used to overwrite the max-edge clamps rather than
  // intersect with them, so a shape hanging off both sides got dx = -minX --
  // pushing the copy further right, the exact opposite of the doc comment's
  // promise. Measured: maxX 700 -> 750 on a 640-wide canvas.
  const src = {
    id: "s1",
    points: [{ x: -50, y: -50 }, { x: CANVAS_W + 60, y: -50 }, { x: CANVAS_W + 60, y: CANVAS_H + 80 }],
    curves: {},
  };
  const copy = duplicateShape(src, "s2");
  const srcMaxX = Math.max(...src.points.map((p) => p.x));
  const copyMaxX = Math.max(...copy.points.map((p) => p.x));
  // No offset can keep an oversize shape whole, so the nominal nudge stands --
  // but it must not exceed it, which is what the overwrite bug did.
  expect(copyMaxX - srcMaxX).toBeLessThanOrEqual(PASTE_OFFSET_PX);
});

test("duplicateShape: curve control points are clamped alongside the anchors", () => {
  // consider() folds curves into the bounds, so a bowed edge bulging past the
  // canvas must pull the whole copy back with it -- otherwise the anchors look
  // on-canvas while the bow the user actually sees is not.
  const src = {
    id: "s1",
    points: [{ x: CANVAS_W - 60, y: 100 }, { x: CANVAS_W - 60, y: 200 }, { x: CANVAS_W - 120, y: 150 }],
    curves: { 0: { x: CANVAS_W, y: 150 } },
    stitchType: "fill",
  };
  const copy = duplicateShape(src, "s2");
  expect(copy.curves[0].x).toBeLessThanOrEqual(CANVAS_W);
  // and the control moved by the SAME delta as the anchors, or the bow warps.
  expect(copy.curves[0].x - src.curves[0].x).toBe(copy.points[0].x - src.points[0].x);
  expect(copy.curves[0].y - src.curves[0].y).toBe(copy.points[0].y - src.points[0].y);
});

test("duplicateShape: the copy is still a valid, sewable shape", () => {
  const src = { id: "s1", points: [{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 150, y: 200 }], curves: {} };
  const copy = duplicateShape(src, "s2");
  expect(isValidShape(flattenShape(copy.points, copy.curves, true))).toBe(true);
  // ...and it survives the trip to the stitch plan as its own region.
  // shapesToRegions returns { regions, pxPerMm }, not a bare array.
  const { regions } = shapesToRegions([src, copy]);
  expect(regions).toHaveLength(2);
});

test("duplicateShape: refuses a shape with no geometry rather than emitting a degenerate one", () => {
  expect(duplicateShape(null, "s2")).toBeNull();
  expect(duplicateShape({ id: "s1", points: [] }, "s2")).toBeNull();
  expect(duplicateShape({ id: "s1" }, "s2")).toBeNull();
});

// ---- shouldScrollCanvasIntoView -----------------------------------------

test("shouldScrollCanvasIntoView: scrolls only when the canvas is actually clipped", () => {
  const port = { top: 0, bottom: 500 };
  // Fully inside the scroll port -- nothing is wrong, so do not move the page.
  expect(shouldScrollCanvasIntoView({ top: 100, bottom: 340 }, port)).toBe(false);
  // Exactly flush with the bottom edge: still fully visible.
  expect(shouldScrollCanvasIntoView({ top: 260, bottom: 500 }, port)).toBe(false);

  // The measured real case: entry at 1280x720 put 34px of a 234px canvas
  // inside the port (14%).
  expect(shouldScrollCanvasIntoView({ top: 466, bottom: 700 }, port)).toBe(true);
  // Entirely below the fold.
  expect(shouldScrollCanvasIntoView({ top: 600, bottom: 834 }, port)).toBe(true);
  // Clipped at the TOP counts too -- scrolled past, not just not-reached-yet.
  expect(shouldScrollCanvasIntoView({ top: -200, bottom: 34 }, port)).toBe(true);

  // The 1440x900 measurement: 92% visible, above the 90% threshold.
  expect(shouldScrollCanvasIntoView({ top: 0, bottom: 274 }, { top: 0, bottom: 252 })).toBe(false);
});

test("shouldScrollCanvasIntoView: an unmeasurable rect is never a reason to scroll", () => {
  const port = { top: 0, bottom: 500 };
  // Zero-height canvas = layout has not happened (or there is none, as under
  // jsdom). That is "cannot tell", not "hidden" -- scrolling on a guess yanks
  // the page for no reason. 0/0 would be NaN and fall through the comparison
  // anyway, but this is a decision, not a coincidence, so it is pinned.
  expect(shouldScrollCanvasIntoView({ top: 120, bottom: 120 }, port)).toBe(false);
  expect(shouldScrollCanvasIntoView({ top: 0, bottom: 0 }, { top: 0, bottom: 0 })).toBe(false);
  // A negative-height rect is nonsense, not an instruction.
  expect(shouldScrollCanvasIntoView({ top: 300, bottom: 100 }, port)).toBe(false);
  // Missing rects (a detached node) must not throw.
  expect(shouldScrollCanvasIntoView(null, port)).toBe(false);
  expect(shouldScrollCanvasIntoView({ top: 0, bottom: 100 }, null)).toBe(false);
});

test("shapesToRegions: the shape's id rides onto the region shape (the field maps clicks back through it)", () => {
  const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const { regions } = shapesToRegions([
    { id: "s3", points: square, curves: {}, stitchType: "fill", colorRgb: [1, 2, 3], angleDeg: null },
    { points: square.map((p) => ({ x: p.x + 200, y: p.y })), curves: {}, stitchType: "satin", colorRgb: [1, 2, 3], angleDeg: null },
  ]);
  expect(regions[0].shapes[0].id).toBe("s3");
  expect(regions[1].shapes[0].id).toBe("");
});

const rect = (id, x0, y0, x1, y1, extra = {}) => ({
  id, points: [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }],
  curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null, ...extra,
});

describe("resolveCutOuts", () => {
  it("a cut-out inside one shape cuts that shape", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200, { cutOut: true })]);
    expect(r.parentOf).toEqual({ s2: "s1" });
    expect(r.holesOf).toEqual({ s1: ["s2"] });
    expect(r.reasonOf).toEqual({});
  });
  it("list order does not matter: a cut-out listed before its parent still resolves", () => {
    const r = resolveCutOuts([rect("s2", 100, 100, 200, 200, { cutOut: true }), rect("s1", 0, 0, 300, 300)]);
    expect(r.parentOf.s2).toBe("s1");
  });
  it("the SMALLEST containing shape is the parent (an O's counter over a patch cuts the O)", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 400, 400), rect("s2", 50, 50, 350, 350), rect("s3", 150, 150, 250, 250, { cutOut: true }),
    ]);
    expect(r.parentOf.s3).toBe("s2");
    expect(r.holesOf.s1).toBeUndefined();
  });
  it("no containing shape: cuts nothing, with the reason", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), rect("s2", 200, 200, 260, 260, { cutOut: true })]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe(CUTOUT_NO_PARENT);
  });
  it("crossing the parent's edge is not inside", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), rect("s2", 50, 50, 150, 90, { cutOut: true })]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe(CUTOUT_NO_PARENT);
  });
  it("two cut-outs of one parent that cross: the earlier stands, the later cuts nothing", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300),
      rect("s2", 50, 50, 150, 150, { cutOut: true }),
      rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(r.parentOf).toEqual({ s2: "s1", s3: null });
    expect(r.reasonOf.s3).toBe(CUTOUT_OVERLAP);
    expect(r.holesOf.s1).toEqual(["s2"]);
  });
  it("a cut-out nested in a sibling cut-out is an overlap, not a second hole", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300),
      rect("s2", 50, 50, 250, 250, { cutOut: true }),
      rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(r.parentOf.s3).toBeNull();
    expect(r.reasonOf.s3).toBe(CUTOUT_OVERLAP);
  });
  it("a cut-out never has a cut-out as its parent; an island's own cut-out resolves to the island", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 400, 400),
      rect("s2", 50, 50, 350, 350, { cutOut: true }),
      rect("s3", 100, 100, 300, 300),                    // island inside the hole
      rect("s4", 150, 150, 250, 250, { cutOut: true }),  // the island's hole
    ]);
    expect(r.parentOf).toEqual({ s2: "s1", s4: "s3" });
  });
  it("an invalid cut-out reports its own shape issue", () => {
    const bow = { id: "s2", cutOut: true, curves: {}, points: [{ x: 10, y: 10 }, { x: 90, y: 90 }, { x: 90, y: 10 }, { x: 10, y: 90 }] };
    const r = resolveCutOuts([rect("s1", 0, 0, 100, 100), bow]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe("This shape crosses itself.");
  });
  it("a triangle is a legal cut-out (three points)", () => {
    const tri = { id: "s2", cutOut: true, curves: {}, points: [{ x: 100, y: 200 }, { x: 200, y: 200 }, { x: 150, y: 100 }] };
    expect(resolveCutOuts([rect("s1", 0, 0, 300, 300), tri]).parentOf.s2).toBe("s1");
  });
  it("no cut-outs: empty maps", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 10, 10)]);
    expect(r.parentOf).toEqual({}); expect(r.holesOf).toEqual({}); expect(r.reasonOf).toEqual({});
  });
  it("no cut-outs: nothing is flattened either (the early-out every drag frame takes)", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 10, 10), rect("s2", 20, 20, 30, 30)]);
    expect(r.flat.size).toBe(0);
  });
  it("an equal-area tie stays with the EARLIER shape (the one that already had the hole)", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300), rect("s2", 0, 0, 300, 300), rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(r.parentOf.s3).toBe("s1");
    expect(r.holesOf).toEqual({ s1: ["s3"] });
  });
  it("Duplicate leaves the hole with the original: a rectangle and its copy 18 px over", () => {
    const parent = rect("s1", 100, 50, 400, 350);
    const hole = rect("s2", 200, 150, 300, 250, { cutOut: true });
    const copy = duplicateShape(parent, "s9");
    const r = resolveCutOuts([parent, hole, copy]);
    expect(r.parentOf.s2).toBe("s1");
    expect(r.holesOf).toEqual({ s1: ["s2"] });
  });
  it("Duplicate leaves the hole with the original: an irregular polygon (the float-noise tie)", () => {
    // Non-integer vertices chosen so the copy's shoelace area comes out
    // 1.5e-11 SMALLER than the original's — pure float noise. Both the old
    // `<=` rule and a bare `<` handed the hole to the copy; only the
    // relative epsilon keeps it with the original.
    const poly = (pts) => pts.map(([x, y]) => ({ x, y }));
    const parent = {
      id: "s1", curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null,
      points: poly([[341.94, 190], [292.32, 280.68], [193.11, 307.82], [103.11, 246.29], [108.78, 136.44], [193.17, 72.44], [299.43, 90.4]]),
    };
    const hole = {
      id: "s2", cutOut: true, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null,
      points: poly([[205.3, 175.7], [235.1, 180.2], [225.9, 205.4], [200.6, 200.8]]),
    };
    const copy = duplicateShape(parent, "s9");
    const r = resolveCutOuts([parent, hole, copy]);
    expect(r.parentOf.s2).toBe("s1");
    expect(r.holesOf).toEqual({ s1: ["s2"] });
  });
  it("a genuinely smaller container listed LATER still wins over an earlier bigger one", () => {
    const r = resolveCutOuts([
      rect("s1", 0, 0, 300, 300), rect("s3", 100, 100, 200, 200, { cutOut: true }), rect("s2", 50, 50, 250, 250),
    ]);
    expect(r.parentOf.s3).toBe("s2");
  });
  it("the maps carry no inherited keys (a shape id like 'constructor' is not pre-set)", () => {
    const r = resolveCutOuts([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200, { cutOut: true })]);
    expect(r.holesOf.constructor).toBeUndefined();
    expect(r.parentOf.toString).toBeUndefined();
  });
});

describe("shapesToRegions with cut-outs", () => {
  it("without any cut-out the output is exactly today's (holes: [])", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200)]);
    expect(regions).toHaveLength(2);
    expect(regions[0].shapes[0].holes).toEqual([]);
    expect(regions[1].shapes[0].holes).toEqual([]);
  });
  it("a resolved cut-out becomes its parent's hole and emits no region", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 300, 300), rect("s2", 100, 100, 200, 200, { cutOut: true })]);
    expect(regions).toHaveLength(1);
    expect(regions[0].shapes[0].id).toBe("s1");
    expect(regions[0].shapes[0].holes).toEqual([[{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 200, y: 200 }, { x: 100, y: 200 }]]);
  });
  it("a cut-out that cuts nothing emits no region and no hole", () => {
    const { regions } = shapesToRegions([rect("s1", 0, 0, 100, 100), rect("s2", 200, 200, 260, 260, { cutOut: true })]);
    expect(regions).toHaveLength(1);
    expect(regions[0].shapes[0].holes).toEqual([]);
  });
  it("a curved cut-out is flattened like an outer ring", () => {
    const c = rect("s2", 100, 100, 200, 200, { cutOut: true, curves: { 0: { x: 150, y: 60 } } });
    const hole = shapesToRegions([rect("s1", 0, 0, 300, 300), c]).regions[0].shapes[0].holes[0];
    expect(hole.length).toBeGreaterThan(4);
  });
});

describe("names and the toggle", () => {
  it("manualShapeName", () => {
    const shapes = [rect("s1", 0, 0, 300, 300, { stitchType: "satin" }), rect("s2", 100, 100, 200, 200, { cutOut: true })];
    const cut = resolveCutOuts(shapes);
    expect(manualShapeName(shapes[1], cut)).toBe("Shape 2 · Cut out");
    expect(manualShapeName(shapes[0], cut)).toBe("Shape 1 · Fill");      // holed: sews as fill
    expect(manualShapeName(shapes[0])).toBe("Shape 1 · Satin");          // no cut info: the stored type
  });
  it("withCutOut adds the key, and removes it rather than storing false", () => {
    const s = rect("s1", 0, 0, 10, 10);
    expect(withCutOut(s, true).cutOut).toBe(true);
    expect("cutOut" in withCutOut(withCutOut(s, true), false)).toBe(false);
    expect(withCutOut(s, false)).toEqual(s);
  });
});

describe("cut-out neighbours", () => {
  it("a duplicated cut-out is still a cut-out", () => {
    const copy = duplicateShape(rect("s1", 100, 100, 200, 200, { cutOut: true }), "s2");
    expect(copy.cutOut).toBe(true);
    expect(copy.id).toBe("s2");
  });
});

// ---- Columns: an open spine plus a drawn width (spec 2026-09-30 §6, amended
// 2026-10-01) -------------------------------------------------------------
const column = (id, points, extra = {}) => ({ id, kind: "column", points, curves: {}, widthPx: 24, colorRgb: [20, 20, 20], ...extra });
const NEEDS_2 = "A column needs at least 2 points.";
const TOO_SHORT = "This column is too short to sew.";
const FOLDS = "This column folds over itself — widen the bend or narrow the column.";

describe("columns: the model", () => {
  const straight = column("s1", [{ x: 50, y: 100 }, { x: 350, y: 100 }]);
  const curved = column("s2", [{ x: 100, y: 300 }, { x: 300, y: 300 }, { x: 500, y: 300 }], { curves: { 0: { x: 200, y: 180 } } });

  it("COLUMN_DEFAULT_MM is Kent's ruling 9", () => {
    expect(COLUMN_DEFAULT_MM).toBe(4.0);
  });

  it("isColumn reads kind, and an absent kind is a closed shape", () => {
    expect(isColumn(straight)).toBe(true);
    expect(isColumn(rect("s1", 0, 0, 10, 10))).toBe(false);
    expect(isColumn(null)).toBe(false);
  });

  it("shapeRing: a closed shape presents its flattened closed ring", () => {
    const r = rect("s1", 0, 0, 100, 100, { curves: { 0: { x: 50, y: -40 } } });
    expect(shapeRing(r)).toEqual(flattenShape(r.points, r.curves, true));
    expect(shapeRing(rect("s1", 0, 0, 100, 100))).toEqual(rect("s1", 0, 0, 100, 100).points);
  });

  it("shapeRing: a column presents rail A then rail B reversed", () => {
    const ring = shapeRing(straight);
    expect(ring).toHaveLength(4);
    const ys = ring.map((p) => p.y).sort((a, b) => a - b);
    expect(ys[0]).toBeCloseTo(88, 9);
    expect(ys[3]).toBeCloseTo(112, 9);
    const rails = columnRails(straight);
    expect(ring).toEqual(rails.railA.concat(rails.railB.slice().reverse()));
    // a curved spine: the ring is the FLATTENED spine's, both sides
    const spine = flattenShape(curved.points, curved.curves, false);
    expect(shapeRing(curved)).toHaveLength(spine.length * 2);
    // the closing curve key a closed shape would use is ignored on a spine
    expect(shapeRing({ ...curved, curves: { ...curved.curves, 2: { x: 0, y: 0 } } })).toEqual(shapeRing(curved));
  });

  it("shapeRing / columnRails: nothing to offset gives [] / null", () => {
    expect(shapeRing(column("s1", [{ x: 5, y: 5 }]))).toEqual([]);
    expect(columnRails(column("s1", [{ x: 5, y: 5 }]))).toBeNull();
    expect(shapeRing({ ...straight, widthPx: 0 })).toEqual([]);
    expect(columnRails({ ...straight, widthPx: undefined })).toBeNull();
    expect(columnRails(rect("s1", 0, 0, 10, 10))).toBeNull();
  });

  it("columnIssues: under two points", () => {
    expect(columnIssues(column("s1", []))).toEqual([NEEDS_2]);
    expect(columnIssues(column("s1", [{ x: 5, y: 5 }]))).toEqual([NEEDS_2]);
    expect(columnIssues({ kind: "column", widthPx: 24 })).toEqual([NEEDS_2]);
  });

  it("columnIssues: too short is the FLATTENED spine's length, 4 px or under", () => {
    expect(columnIssues(column("s1", [{ x: 0, y: 0 }, { x: 4, y: 0 }]))).toEqual([TOO_SHORT]);
    expect(columnIssues(column("s1", [{ x: 0, y: 0 }, { x: 0, y: 0 }]))).toEqual([TOO_SHORT]);
    expect(columnIssues(column("s1", [{ x: 0, y: 0 }, { x: 4.5, y: 0 }]))).toEqual([]);
    // 3 px chord, bowed 40 px out: the path is long though the ends are close
    expect(columnIssues(column("s1", [{ x: 0, y: 0 }, { x: 3, y: 0 }], { widthPx: 2, curves: { 0: { x: 1.5, y: 80 } } }))).not.toContain(TOO_SHORT);
  });

  it("columnIssues: a hairpin wider than its bend folds; the same hairpin narrowed does not", () => {
    const hairpin = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 10 }, { x: -50, y: 10 }];
    expect(columnIssues(column("s1", hairpin, { widthPx: 24 }))).toEqual([FOLDS]);
    expect(columnIssues(column("s1", hairpin, { widthPx: 4 }))).toEqual([]);
  });

  it("columnIssues: a spine that ends on its own start is refused as a fold (its end caps meet)", () => {
    const loop = [{ x: 100, y: 100 }, { x: 300, y: 100 }, { x: 300, y: 300 }, { x: 100, y: 300 }, { x: 100, y: 100 }];
    expect(columnIssues(column("s1", loop))).toEqual([FOLDS]);
  });

  it("columnIssues: a spine that passes NEAR itself without its rails touching is fine", () => {
    // a U whose legs are 60 px apart, 24 px wide: 36 px of daylight
    const u = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 60 }, { x: 0, y: 60 }];
    expect(columnIssues(column("s1", u))).toEqual([]);
  });

  it("columnIssues: too many points uses the closed shape's message", () => {
    const pts = [];
    for (let i = 0; i <= MAX_SHAPE_POINTS; i++) pts.push({ x: i * 3, y: 0 });
    expect(columnIssues(column("s1", pts))).toEqual([`Too many points (max ${MAX_SHAPE_POINTS}).`]);
  });

  it("shapeProblems routes by kind", () => {
    expect(shapeProblems(straight)).toEqual([]);
    expect(shapeProblems(column("s1", [{ x: 5, y: 5 }]))).toEqual([NEEDS_2]);
    expect(shapeProblems(rect("s1", 0, 0, 100, 100))).toEqual([]);
    expect(shapeProblems({ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }] })).toEqual(["Needs at least 3 points."]);
    // a closed shape is judged on its FLATTENED ring, like shapesToRegions does
    const bow = { points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }], curves: { 0: { x: 50, y: 400 } } };
    expect(shapeProblems(bow)).toEqual(["This shape crosses itself."]);
  });

  it("isSewableShape: a 2-point column sews; a cut-out and a broken shape do not", () => {
    expect(isSewableShape(straight)).toBe(true);
    expect(isSewableShape(curved)).toBe(true);
    expect(isSewableShape(column("s1", [{ x: 5, y: 5 }]))).toBe(false);
    expect(isSewableShape(rect("s1", 0, 0, 100, 100))).toBe(true);
    expect(isSewableShape(rect("s1", 0, 0, 100, 100, { cutOut: true }))).toBe(false);
    expect(isSewableShape({ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }] })).toBe(false);
    expect(isSewableShape(null)).toBe(false);
    // no width, no rails: nothing would sew, so it is not sewable
    expect(isSewableShape({ ...straight, widthPx: 0 })).toBe(false);
    // a column cannot be a cut-out: a stray flag is ignored
    expect(isSewableShape({ ...straight, cutOut: true })).toBe(true);
  });

  it("manualShapeName: Shape N · Column, whatever else the record carries", () => {
    expect(manualShapeName(column("s7", straight.points))).toBe("Shape 7 · Column");
    expect(manualShapeName(column("s7", straight.points, { cutOut: true, stitchType: "fill" }))).toBe("Shape 7 · Column");
  });

  it("withCutOut leaves a column exactly as it was", () => {
    expect(withCutOut(straight, true)).toBe(straight);
    expect("cutOut" in withCutOut(straight, true)).toBe(false);
    expect(withCutOut(straight, false)).toBe(straight);
  });
});

describe("columns: resolveCutOuts", () => {
  // a fat column whose rail ring (x 0..300, y 0..300) contains the cut-out
  const fat = column("s1", [{ x: 0, y: 150 }, { x: 300, y: 150 }], { widthPx: 300 });
  const hole = rect("s2", 100, 100, 200, 200, { cutOut: true });

  it("a column is never a parent, even when its ring contains the cut-out", () => {
    const r = resolveCutOuts([fat, hole]);
    expect(r.parentOf.s2).toBeNull();
    expect(r.reasonOf.s2).toBe(CUTOUT_NO_PARENT);
    expect(r.holesOf.s1).toBeUndefined();
  });

  it("a closed-looking spine (3+ points) is not a solid either", () => {
    const ringLike = column("s1", [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }], { widthPx: 4 });
    expect(resolveCutOuts([ringLike, hole]).parentOf.s2).toBeNull();
  });

  it("the cut-out still finds the real shape behind the column", () => {
    const r = resolveCutOuts([rect("s3", -10, -10, 310, 310), fat, hole]);
    expect(r.parentOf.s2).toBe("s3");
  });

  it("a column carrying a stray cutOut flag is not a cut-out", () => {
    const r = resolveCutOuts([rect("s3", -10, -10, 310, 310), { ...fat, cutOut: true }, hole]);
    expect("s1" in r.parentOf).toBe(false);
    expect(r.holesOf.s3).toEqual(["s2"]);
    // ...and on its own it does not even leave the no-cut-out fast path
    expect(resolveCutOuts([rect("s3", -10, -10, 310, 310), { ...fat, cutOut: true }]).flat.size).toBe(0);
  });
});

describe("columns: shapesToRegions", () => {
  const straight = column("s4", [{ x: 50, y: 100 }, { x: 350, y: 100 }], { colorRgb: [9, 8, 7] });

  it("a valid column emits its rail ring as outer, forced satin, with the rails as sewAs", () => {
    const { regions, pxPerMm } = shapesToRegions([straight]);
    expect(pxPerMm).toBe(PX_PER_MM);
    expect(regions).toHaveLength(1);
    const rails = columnRails(straight);
    expect(regions[0]).toEqual({
      rgb: [9, 8, 7],
      shapes: [{
        id: "s4",
        outer: shapeRing(straight),
        holes: [],
        tierOverride: "satin",
        angleOverride: null,
        sewAs: { kind: "column", railA: rails.railA, railB: rails.railB },
      }],
    });
    const s = regions[0].shapes[0];
    expect(s.sewAs.railA).toHaveLength(s.sewAs.railB.length);
    expect(s.sewAs.railA.length).toBeGreaterThanOrEqual(2);
  });

  it("a column ignores stitchType, angleDeg and cutOut on its record", () => {
    const { regions } = shapesToRegions([{ ...straight, stitchType: "fill", angleDeg: 45, cutOut: true }]);
    expect(regions).toHaveLength(1);
    expect(regions[0].shapes[0].tierOverride).toBe("satin");
    expect(regions[0].shapes[0].angleOverride).toBeNull();
  });

  it("an invalid column is skipped like an invalid shape", () => {
    const { regions } = shapesToRegions([
      column("s1", [{ x: 5, y: 5 }]),
      column("s2", [{ x: 0, y: 0 }, { x: 3, y: 0 }]),
      column("s3", [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 10 }, { x: -50, y: 10 }]),
      { ...straight, id: "s5", widthPx: 0 },
      straight,
    ]);
    expect(regions.map((r) => r.shapes[0].id)).toEqual(["s4"]);
  });

  it("draw order is kept, and a column never takes a hole", () => {
    const { regions } = shapesToRegions([
      rect("s1", 0, 0, 300, 300),
      column("s2", [{ x: 0, y: 150 }, { x: 300, y: 150 }], { widthPx: 280 }),
      rect("s3", 100, 100, 200, 200, { cutOut: true }),
    ]);
    expect(regions.map((r) => r.shapes[0].id)).toEqual(["s1", "s2"]);
    expect(regions[0].shapes[0].holes).toHaveLength(1);
    expect(regions[1].shapes[0].holes).toEqual([]);
  });

  it("shapes with no column emit exactly what they emitted before columns existed — no sewAs key at all", () => {
    // Pinned literally, and seen green at 8ee893e1 before manualShapes.js changed.
    const shapes = [
      rect("s1", 0, 0, 300, 300, { stitchType: "satin", angleDeg: 30, colorRgb: [1, 2, 3] }),
      rect("s2", 100, 100, 200, 200, { cutOut: true }),
      { points: tri(400), stitchType: "auto" },
      { id: "s9", points: tri(500), stitchType: "nonsense", colorRgb: [4, 5, 6], angleDeg: NaN },
    ];
    const { regions, pxPerMm } = shapesToRegions(shapes);
    expect(pxPerMm).toBe(PX_PER_MM);
    expect(regions).toEqual([
      { rgb: [1, 2, 3], shapes: [{ id: "s1", outer: rect("s1", 0, 0, 300, 300).points, holes: [rect("s2", 100, 100, 200, 200).points], tierOverride: "satin", angleOverride: 30 }] },
      { rgb: [20, 20, 20], shapes: [{ id: "", outer: tri(400), holes: [], tierOverride: null, angleOverride: null }] },
      { rgb: [4, 5, 6], shapes: [{ id: "s9", outer: tri(500), holes: [], tierOverride: "fill", angleOverride: null }] },
    ]);
    for (const r of regions) expect(Object.keys(r.shapes[0])).toEqual(["id", "outer", "holes", "tierOverride", "angleOverride"]);
  });
});

// ---- Through the REAL engine ------------------------------------------------
// The module above can be right about its own shapes and the engine still sew
// nothing: bad rails are silent there. So one curved column goes all the way
// through, and one design with no column is hashed against the value this same
// test produced at 8ee893e1, before this module knew what a column was.
const RECT_STITCH_COUNT_AT_8ee893e1 = 3556;
const RECT_HASH_AT_8ee893e1 = "8077390b3c32a3fc778e0bf069243f9c7219b2ed640e916baba2f04d2136300e";

describe("columns: through the real engine", () => {
  let generateElement, garment;
  beforeAll(async () => {
    const require = createRequire(import.meta.url);
    globalThis.window = globalThis;
    for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
    const { EMB } = await import("./emb.js");
    ({ generateElement } = await import("./generate.js"));
    garment = EMB.getGarment("left_chest");
  }, 60000);
  const el = (shapes) => ({ id: 4, type: "manual", shapes, underlay: true, sizeMm: 60, offsetXMm: 0, offsetYMm: 0 });
  const hashOf = (d) => createHash("sha256").update(JSON.stringify(d.stitches)).digest("hex");

  it("a curved column sews satin between its rails", () => {
    const col = column("s1", [{ x: 100, y: 300 }, { x: 300, y: 300 }, { x: 500, y: 300 }], { curves: { 0: { x: 200, y: 180 } }, widthPx: 24 });
    const d = generateElement(el([col]), garment, {});
    const satin = d.runs.filter((r) => r.kind === "satin" && r.shape === "s1");
    const nSatin = satin.reduce((n, r) => n + (r.i1 - r.i0 + 1), 0);
    expect(satin.length).toBeGreaterThan(0);
    expect(nSatin).toBeGreaterThan(100);
    expect(d._debug.nSatin).toBe(1);
    expect(d._debug.nFill).toBe(0);
    expect(d.shapeOutlines).toHaveLength(1);
    expect(d.shapeOutlines[0].id).toBe("s1");
    expect(d.shapeOutlines[0].dropped).toBe(false);
    // Not a bow-tie. The engine sews a column as cross, step along the rail,
    // cross, step: so the stitch lengths fall in two clean groups — steps of
    // about the row spacing, and crosses of about the drawn width plus pull
    // comp — with NOTHING in between. Rails running in opposite directions
    // sew crosses of every length from zero (where they meet) up to the
    // column's whole length, which fills exactly that gap. Stitches are 0.1 mm.
    const drawnMm = 24 * d.fit.mmPerPx;
    const lens = [];
    for (const r of satin) {
      for (let i = r.i0 + 1; i <= r.i1; i++) lens.push(Math.hypot(d.stitches[i].x - d.stitches[i - 1].x, d.stitches[i].y - d.stitches[i - 1].y) / 10);
    }
    const steps = lens.filter((l) => l <= 1.0);
    const crosses = lens.filter((l) => l >= drawnMm * 0.9);
    expect(steps.length + crosses.length).toBe(lens.length);     // the gap is empty
    expect(crosses.length).toBeGreaterThan(100);
    // The widest crosses are NOT square to the spine: with no rungs the engine
    // pairs the rails by whole-rail arc-length fraction, and this column's
    // rails differ in length (431 vs 450 px), so crosses past the bend lean —
    // measured 2026-10-01, up to 1.61x the drawn width. Bounded here, not
    // endorsed: same-index rungs bring it to 1.10x (see the task-2 report).
    expect(Math.max(...crosses)).toBeLessThan(drawnMm * 2);
    crosses.sort((a, b) => a - b);
    const median = crosses[crosses.length >> 1];
    expect(median).toBeGreaterThan(drawnMm);                     // drawn + pull comp...
    expect(median).toBeLessThan(drawnMm + 1.0);                  // ...and never a mm more
    if (process.env.EMB_TASK_NUMBERS) {
      console.log("COLUMN_ENGINE " + JSON.stringify({
        stitchCount: d.stitchCount, satinStitches: nSatin, spans: d.runs.map((r) => r.kind + ":" + (r.i1 - r.i0 + 1)),
        widthMM: d.widthMM, heightMM: d.heightMM, mmPerPx: d.fit.mmPerPx, drawnMm,
        steps: { n: steps.length, max: Math.max(...steps) },
        crosses: { n: crosses.length, min: crosses[0], median, p95: crosses[Math.floor(crosses.length * 0.95)], max: crosses[crosses.length - 1] },
      }));
    }
  });

  it("a design holding only a closed rectangle is byte-identical to before", () => {
    const d = generateElement(el([rect("s1", 100, 100, 400, 250)]), garment, {});
    expect(d.stitchCount).toBe(RECT_STITCH_COUNT_AT_8ee893e1);
    expect(hashOf(d)).toBe(RECT_HASH_AT_8ee893e1);
  });
});
