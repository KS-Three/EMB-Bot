import { test, expect } from "vitest";
import { fitTransform } from "./preview.js";
test("fitTransform centers and scales design into canvas with padding", () => {
  const design = { stitches: [ { x: -100, y: -50, type: "stitch" }, { x: 100, y: 50, type: "stitch" } ] };
  const t = fitTransform(design, 400, 300, 20);
  // design is 200 wide, 100 tall; canvas usable 360x260 -> scale limited by width 360/200=1.8
  expect(t.scale).toBeCloseTo(1.8, 1);
  // centered: midpoint (0,0) maps to canvas center (200,150)
  expect(t.ox).toBeCloseTo(200, 0);
  expect(t.oy).toBeCloseTo(150, 0);
});
