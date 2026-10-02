import { test, expect } from "vitest";
import {
  designFacts,
  smallestHoop,
  factsLine,
  filterProjects,
  hasFactCriteria,
} from "./libraryFacts.js";

// The engine's own hoop table and fit rule (src/garments.js), copied here so
// this spec stays engine-free. hoop.spec.js is the one that pins the real ones.
const HOOPS = [
  { id: "4x4", label: "4×4 in", widthMm: 100, heightMm: 100 },
  { id: "5x7", label: "5×7 in", widthMm: 130, heightMm: 180 },
  { id: "6x10", label: "6×10 in", widthMm: 160, heightMm: 250 },
  { id: "8x8", label: "8×8 in", widthMm: 200, heightMm: 200 },
];
function hoopFit(w, h, hoop) {
  if (w <= hoop.widthMm && h <= hoop.heightMm) return "fits";
  if (h <= hoop.widthMm && w <= hoop.heightMm) return "rotated";
  return "exceeds";
}

function design(n, widthMM, heightMM) {
  const stitches = [];
  for (let i = 0; i < n; i++) stitches.push({ type: "stitch", x: i, y: 0 });
  stitches.push({ type: "color" }, { type: "trim" }, { type: "end" });
  return { stitches, widthMM, heightMM };
}

// --- designFacts -------------------------------------------------------------

test("designFacts counts needle-down stitches only and rounds size to 0.1 mm", () => {
  expect(designFacts(design(5, 76.04, 18.26), 2)).toEqual({ st: 5, col: 2, w: 76, h: 18.3 });
});

test("designFacts is null when there is nothing to measure", () => {
  expect(designFacts(null, 0)).toBe(null);
  expect(designFacts({ stitches: [] }, 0)).toBe(null);
  expect(designFacts(design(0, 10, 10), 1)).toBe(null);
  // A size that is not a number is not a size: no facts rather than a NaN
  // that every numeric filter would silently pass or fail.
  expect(designFacts(design(5, undefined, 10), 1)).toBe(null);
});

// --- smallestHoop / factsLine -----------------------------------------------

test("smallestHoop takes the first hoop the design fits in either orientation", () => {
  expect(smallestHoop({ w: 90, h: 90 }, HOOPS, hoopFit).id).toBe("4x4");
  expect(smallestHoop({ w: 170, h: 120 }, HOOPS, hoopFit).id).toBe("5x7"); // rotated
  expect(smallestHoop({ w: 150, h: 240 }, HOOPS, hoopFit).id).toBe("6x10");
  expect(smallestHoop({ w: 300, h: 300 }, HOOPS, hoopFit)).toBe(null);
  expect(smallestHoop(null, HOOPS, hoopFit)).toBe(null);
});

test("factsLine prints the facts a row is filtered on", () => {
  expect(factsLine({ st: 5412, col: 2, w: 76, h: 18.3 }, HOOPS, hoopFit)).toBe(
    `${(5412).toLocaleString()} stitches · 2 colors · 76 × 18 mm · fits 4×4 in`
  );
  expect(factsLine({ st: 1, col: 1, w: 300, h: 300 }, HOOPS, hoopFit)).toBe(
    "1 stitch · 1 color · 300 × 300 mm · larger than every hoop"
  );
  expect(factsLine(undefined, HOOPS, hoopFit)).toBe("");
});

// --- filterProjects ----------------------------------------------------------

const ENTRIES = [
  { id: "a", name: "Dog on porch", facts: { st: 5400, col: 2, w: 90, h: 80 } },
  { id: "b", name: "DOG big", facts: { st: 14000, col: 5, w: 170, h: 120 } },
  { id: "c", name: "Cat", facts: { st: 3000, col: 1, w: 150, h: 240 } },
  { id: "d", name: "Old dog" }, // saved before facts existed
];
const ids = (r) => r.shown.map((e) => e.id);

test("no criteria shows everything, measured or not", () => {
  const r = filterProjects(ENTRIES, {}, hoopFit);
  expect(ids(r)).toEqual(["a", "b", "c", "d"]);
  expect(r.unmeasured).toBe(0);
  expect(hasFactCriteria({})).toBe(false);
  expect(hasFactCriteria({ text: "dog" })).toBe(false);
});

test("name text is case-insensitive and needs no facts", () => {
  const r = filterProjects(ENTRIES, { text: "  dOg " }, hoopFit);
  expect(ids(r)).toEqual(["a", "b", "d"]);
  expect(r.unmeasured).toBe(0);
});

test("the list's own example: dogs under 6000 stitches, two colors, fits 4x4", () => {
  const criteria = { text: "dog", maxStitches: 6000, maxColors: 2, hoop: HOOPS[0] };
  expect(hasFactCriteria(criteria)).toBe(true);
  const r = filterProjects(ENTRIES, criteria, hoopFit);
  expect(ids(r)).toEqual(["a"]);
  // "Old dog" matches the name but cannot be judged on stitches: it is
  // counted, not shown and not silently dropped.
  expect(r.unmeasured).toBe(1);
});

test("each fact criterion is an upper bound, inclusive", () => {
  expect(ids(filterProjects(ENTRIES, { maxStitches: 5400 }, hoopFit))).toEqual(["a", "c"]);
  expect(ids(filterProjects(ENTRIES, { maxColors: 1 }, hoopFit))).toEqual(["c"]);
});

test("the hoop criterion is 'fits in', rotation allowed, not 'smallest hoop is'", () => {
  // 90×80 fits a 5×7 too; 170×120 fits it turned; 150×240 does not.
  expect(ids(filterProjects(ENTRIES, { hoop: HOOPS[1] }, hoopFit))).toEqual(["a", "b"]);
  // 8×8 is the last preset but not the longest: 150×240 fits 6×10 only.
  expect(ids(filterProjects(ENTRIES, { hoop: HOOPS[3] }, hoopFit))).toEqual(["a", "b"]);
  expect(ids(filterProjects(ENTRIES, { hoop: HOOPS[2] }, hoopFit))).toEqual(["a", "b", "c"]);
});

test("unmeasured counts only entries the name text still lets through", () => {
  const r = filterProjects(ENTRIES, { text: "cat", maxStitches: 6000 }, hoopFit);
  expect(ids(r)).toEqual(["c"]);
  expect(r.unmeasured).toBe(0);
});

test("malformed facts are treated as unmeasured, never as a match", () => {
  const r = filterProjects([{ id: "x", name: "x", facts: { st: "many" } }], { maxStitches: 10 }, hoopFit);
  expect(r.shown).toEqual([]);
  expect(r.unmeasured).toBe(1);
});
