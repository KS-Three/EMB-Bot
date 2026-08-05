import { test, expect } from "vitest";
import { isValidShape, isNearStart, shapesToRegions, CLOSE_RADIUS_PX, PX_PER_MM } from "./manualShapes.js";

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
