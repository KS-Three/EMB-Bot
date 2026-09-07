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

// --- strandStitchOrdinals (the simulator's counter) ------------------------
//
// A strand is a SEGMENT BETWEEN two consecutive stitches, so N stitches in K
// runs make N − K strands. That put two numbers on screen together saying
// different things — "1289 stitches · 102×12 mm" under the canvas and
// "1280 / 1280" in the simulator bar, on a design with nine runs. Both were
// correct measurements of different things and only one was labelled.
import { strandStitchOrdinals } from "./strands.js";

test("each strand reports the stitch number it ends at", () => {
  // `design` above: jump, stitch#1, stitch#2, stitch#3, trim, end.
  // Two strands: #1->#2 ends at 2, #2->#3 ends at 3.
  expect(strandStitchOrdinals(design)).toEqual([2, 3]);
  // One entry per strand — the arrays index together, which is the whole
  // contract the simulator relies on.
  expect(strandStitchOrdinals(design).length).toBe(designToStrands(design, {}).length);
});

test("ordinals keep counting across a break, and the run that starts it paints nothing", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2  <- strand ends here
    { x: 9, y: 9, type: "trim" },
    { x: 9, y: 9, type: "jump" },
    { x: 9, y: 9, type: "stitch" },   // 3  <- first of a new run: no strand
    { x: 9, y: 8, type: "stitch" },   // 4  <- strand ends here
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 4]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("a single-stitch run paints no segment, so its ordinal never appears", () => {
  // This is why the simulator's total is the LAST ORDINAL and not
  // design.stitchCount: it must never claim to have drawn a stitch it cannot.
  const d = { colors: [{ r: 0, g: 0, b: 0 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2
    { x: 5, y: 5, type: "trim" },
    { x: 5, y: 5, type: "stitch" },   // 3 — alone between two breaks
    { x: 8, y: 8, type: "trim" },
    { x: 8, y: 8, type: "stitch" },   // 4
    { x: 8, y: 9, type: "stitch" },   // 5
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 5]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("a colour change breaks the chain for both, identically", () => {
  const d = { colors: [{ r: 0, g: 0, b: 0 }, { r: 9, g: 9, b: 9 }], stitches: [
    { x: 0, y: 0, type: "stitch" },   // 1
    { x: 1, y: 0, type: "stitch" },   // 2
    { x: 1, y: 0, type: "color" },
    { x: 1, y: 0, type: "stitch" },   // 3
    { x: 2, y: 0, type: "stitch" },   // 4
  ]};
  expect(strandStitchOrdinals(d)).toEqual([2, 4]);
  expect(strandStitchOrdinals(d).length).toBe(designToStrands(d, {}).length);
});

test("an empty or absent design answers nothing rather than throwing", () => {
  expect(strandStitchOrdinals({ stitches: [] })).toEqual([]);
  expect(strandStitchOrdinals({})).toEqual([]);
  expect(strandStitchOrdinals(null)).toEqual([]);
});
