import { test, expect } from "vitest";
import { remapColorRanges } from "./colorRanges.js";

const RED = [200, 30, 30];
const range = (startIdx, endIdx) => ({ startIdx, endIdx, colorRgb: RED });
const covered = (text, ranges) => ranges.map((r) => text.slice(r.startIdx, r.endIdx));

test("a typo fixed before a coloured word moves the colour with the word", () => {
  const before = "Fritschs Stitches", after = "Fritsch's Stitches";
  const out = remapColorRanges(before, after, [range(9, 17)], 8);
  expect(covered(after, out)).toEqual(["Stitches"]);
  expect(out[0].colorRgb).toBe(RED);
});

test("an edit after the coloured word leaves it alone", () => {
  const out = remapColorRanges("Bob Smith", "Bob Smithers", [range(0, 3)], 12);
  expect(covered("Bob Smithers", out)).toEqual(["Bob"]);
});

test("a letter typed inside the word takes its colour; at either edge it does not", () => {
  expect(covered("Stiches!", [range(0, 7)])).toEqual(["Stiches"]);
  expect(covered("Stitches!", remapColorRanges("Stiches!", "Stitches!", [range(0, 7)], 4))).toEqual(["Stitches"]);
  expect(covered("xStiches!", remapColorRanges("Stiches!", "xStiches!", [range(0, 7)], 1))).toEqual(["Stiches"]);
  expect(covered("Stichesx!", remapColorRanges("Stiches!", "Stichesx!", [range(0, 7)], 8))).toEqual(["Stiches"]);
});

test("replacing the selected word keeps its colour on the new word", () => {
  const out = remapColorRanges("Hello World", "Hello Earth", [range(6, 11)], 11);
  expect(covered("Hello Earth", out)).toEqual(["Earth"]);
});

test("deleting part or all of a coloured word shrinks or drops it", () => {
  expect(covered("Ho World", remapColorRanges("Hello World", "Ho World", [range(0, 5)], 1))).toEqual(["Ho"]);
  expect(remapColorRanges("Hello World", " World", [range(0, 5)], 0)).toEqual([]);
});

test("the caret places a repeated letter where it was typed", () => {
  // "Ann" with both n's red; an "n" typed after the "A" sits at the range's
  // start edge, so it stays uncoloured and the two red n's move right.
  expect(remapColorRanges("Ann", "Annn", [range(1, 3)], 2)).toEqual([range(2, 4)]);
  // Typed at the end instead: also an edge, also uncoloured.
  expect(remapColorRanges("Ann", "Annn", [range(1, 3)], 4)).toEqual([range(1, 3)]);
});

test("no ranges or no change returns the input untouched", () => {
  expect(remapColorRanges("a", "ab", [], 2)).toEqual([]);
  const rs = [range(0, 1)];
  expect(remapColorRanges("ab", "ab", rs)).toBe(rs);
});
