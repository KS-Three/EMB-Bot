import { test, expect } from "vitest";
import { designToStrands } from "./strands.js";

const design = { colors: [{ r: 10, g: 20, b: 30 }], stitches: [
  { x: 0, y: 0, type: "jump" }, { x: 0, y: 0, type: "stitch" },
  { x: 10, y: 0, type: "stitch" }, { x: 10, y: 5, type: "stitch" },
  { x: 40, y: 5, type: "trim" }, { x: 40, y: 5, type: "end" },
]};

test("one strand per consecutive sewn segment, colored by block", () => {
  const s = designToStrands(design, {});
  expect(s.length).toBe(2); // (0,0)->(10,0) and (10,0)->(10,5)
  expect(s[0]).toMatchObject({ x0: 0, y0: 0, x1: 10, y1: 0, rgb: [10, 20, 30] });
});

test("no strand spans a jump/trim boundary", () => {
  const s = designToStrands(design, {});
  expect(s.some(v => v.x1 === 40)).toBe(false);
});

test("colorOverride recolors all strands", () => {
  const s = designToStrands(design, { colorOverride: [200, 0, 0] });
  expect(s[0].rgb).toEqual([200, 0, 0]);
});
