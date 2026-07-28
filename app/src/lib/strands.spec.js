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

// --- jumpTrimMarks (field diagnostic overlays) --------------------------

import { jumpTrimMarks } from "./strands.js";

test("jumpTrimMarks: jump/trim moves become dashed segments, trims get markers, stitches do not", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 10, y: 0, type: "stitch" },
    { x: 50, y: 50, type: "jump" },     // travel -> one jump segment
    { x: 60, y: 50, type: "stitch" },
    { x: 90, y: 90, type: "trim" },     // trim with a move -> marker + segment
    { x: 91, y: 90, type: "stitch" },
    { x: 91, y: 90, type: "end" },
  ] };
  const m = jumpTrimMarks(design);
  expect(m.jumps).toEqual([
    { x0: 10, y0: 0, x1: 50, y1: 50 },
    { x0: 60, y0: 50, x1: 90, y1: 90 },
  ]);
  expect(m.trims).toEqual([{ x: 90, y: 90 }]);
});

test("jumpTrimMarks: zero-length jump moves draw nothing; color/end break the chain", () => {
  const design = { stitches: [
    { x: 0, y: 0, type: "stitch" },
    { x: 0, y: 0, type: "trim" },       // in-place trim: marker, no segment
    { x: 0, y: 0, type: "color" },
    { x: 40, y: 0, type: "stitch" },    // first stitch after color: no segment (chain broken)
  ] };
  const m = jumpTrimMarks(design);
  expect(m.jumps).toEqual([]);
  expect(m.trims).toEqual([{ x: 0, y: 0 }]);
});
