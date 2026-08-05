import { test, expect } from "vitest";
import {
  isValidShape, isNearStart, shapesToRegions, CLOSE_RADIUS_PX, PX_PER_MM,
  shapeIssues, isDuplicateOfLast, MAX_SHAPE_POINTS,
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
