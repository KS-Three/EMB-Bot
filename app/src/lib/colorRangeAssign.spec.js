import { expect, test } from "vitest";
import { assignColorRange } from "./colorRangeAssign.js";

const R = [255, 0, 0], B = [0, 0, 255];
const colorAt = (ranges, i, base) => (ranges.find((r) => i >= r.startIdx && i < r.endIdx) || { colorRgb: base }).colorRgb;

test("recolouring already-coloured letters wins (engine resolves first-match)", () => {
  const next = assignColorRange([{ startIdx: 0, endIdx: 3, colorRgb: R }], 0, 3, B);
  for (let i = 0; i < 3; i++) expect(colorAt(next, i, null)).toEqual(B);
  expect(next).toHaveLength(1);
});

test("a span inside a range splits it", () => {
  const next = assignColorRange([{ startIdx: 0, endIdx: 5, colorRgb: R }], 2, 3, B);
  expect([0, 1, 2, 3, 4].map((i) => colorAt(next, i, null))).toEqual([R, R, B, R, R]);
});

test("a straddling span trims both neighbours; disjoint ranges are untouched", () => {
  const far = { startIdx: 8, endIdx: 9, colorRgb: R };
  const next = assignColorRange([{ startIdx: 0, endIdx: 3, colorRgb: R }, { startIdx: 4, endIdx: 7, colorRgb: R }, far], 2, 5, B);
  expect([0, 1, 2, 3, 4, 5, 6].map((i) => colorAt(next, i, null))).toEqual([R, R, B, B, B, R, R]);
  expect(next).toContain(far);
});

test("empty span is a no-op", () => {
  const rs = [{ startIdx: 0, endIdx: 1, colorRgb: R }];
  expect(assignColorRange(rs, 2, 2, B)).toBe(rs);
});
