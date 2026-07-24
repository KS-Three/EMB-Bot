import { test, expect } from "vitest";
import { fitTransform, hoopTransform } from "./preview.js";
test("fitTransform centers and scales design into canvas with padding", () => {
  const design = { stitches: [ { x: -100, y: -50, type: "stitch" }, { x: 100, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  // design is 200 wide, 100 tall; canvas usable 360x260 -> scale limited by width 360/200=1.8
  expect(t.scale).toBeCloseTo(1.8, 1);
  // centered: midpoint (0,0) maps to canvas center (200,150)
  expect(t.ox).toBeCloseTo(200, 0);
  expect(t.oy).toBeCloseTo(150, 0);
});

test("Y axis flips: DST y-up must map to canvas y-down (no mirrored letters)", () => {
  // DST units: +y is UP. A stitch at the design TOP (+y) must land at a
  // SMALLER canvas y than one at the design bottom (-y).
  const design = { stitches: [ { x: 0, y: -50, type: "stitch" }, { x: 0, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  const canvasYTop = t.oy - 50 * t.scale;    // design top (+50)
  const canvasYBottom = t.oy - (-50) * t.scale; // design bottom (-50)
  expect(canvasYTop).toBeLessThan(canvasYBottom);
  // and the pair stays centered: midpoint maps to canvas center
  expect((canvasYTop + canvasYBottom) / 2).toBeCloseTo(150, 0);
});

test("hoopTransform fits the full hoop (not the design) into the canvas, +y up", () => {
  // 5in x 2.25in garment (hat front) on a 640x420 canvas, 20px pad.
  const garment = { widthIn: 5, heightIn: 2.25 };
  const t = hoopTransform(garment, 640, 420, 20);
  expect(t.hoopWmm).toBeCloseTo(127, 1);      // 5 * 25.4
  expect(t.hoopHmm).toBeCloseTo(57.15, 1);    // 2.25 * 25.4
  // scale limited by width: min(600/127, 380/57.15) = min(4.724, 6.649)
  expect(t.scale).toBeCloseTo(4.724, 2);
  // origin is the canvas center (hoop-space origin = hoop center)
  expect(t.ox).toBeCloseTo(320, 0);
  expect(t.oy).toBeCloseTo(210, 0);
  // +y is UP in hoop space: a positive-y point must land ABOVE center (smaller canvas y)
  expect(t.oy - 10 * t.scale).toBeLessThan(t.oy);
});
