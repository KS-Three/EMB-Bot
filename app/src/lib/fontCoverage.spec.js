// Which fonts can stitch what, and the sentence that says so.
//
// The behaviour under test is the one that turns a dead end into advice:
// "This font can’t stitch «Р», «у», «с». Try a different font, or different
// text." was true and unactionable — three shipped fonts cover Cyrillic and
// finding them meant opening up to 85 by hand.
import { test, expect } from "vitest";
import { fontsCovering, unsupportedMessage } from "./fontCoverage.js";

// Hand-built rather than loaded from the shipped index: this file is about the
// LOGIC, and test/font-coverage.test.js already pins the real index against
// the real binaries. Ranges are `cp | [lo, hi]`, ascending — the shape
// tools/build-font-coverage.mjs writes.
const A = "A".codePointAt(0);          // 65
const Z = "Z".codePointAt(0);          // 90
const CYR_A = "А".codePointAt(0);      // 1040
const CYR_YA = "я".codePointAt(0);     // 1103
const HEB_ALEF = "א".codePointAt(0);   // 1488
const HEB_TAV = "ת".codePointAt(0);    // 1514

const COV = {
  version: 1,
  fonts: {
    latin_only: [[A, Z]],
    latin_and_cyrillic: [[A, Z], [CYR_A, CYR_YA]],
    cyrillic_only: [[CYR_A, CYR_YA]],
    hebrew_only: [[HEB_ALEF, HEB_TAV]],
    // A font whose coverage is single code points, not runs — the other half
    // of the encoding, and the one an all-ranges reader would mis-scan.
    sparse: [A, Z, CYR_A],
  },
};

test("a font qualifies only when it covers EVERY character, not the failing ones", () => {
  // The distinction that makes this advice instead of a new dead end:
  // hebrew_only covers exactly what fails in "Shalom שלום" and none of what
  // works, so suggesting it would move the problem.
  expect(fontsCovering("AZ", COV)).toEqual(["latin_and_cyrillic", "latin_only", "sparse"]);
  expect(fontsCovering("Ая", COV)).toEqual(["cyrillic_only", "latin_and_cyrillic"]);
  expect(fontsCovering("AЯя", COV)).toEqual(["latin_and_cyrillic"]);
  expect(fontsCovering("Aא", COV)).toEqual([]);
});

test("whitespace never disqualifies a font", () => {
  // Requiring a space glyph would rule out every font on any multi-word name;
  // the layout engine advances instead of looking one up.
  expect(fontsCovering("A Z", COV)).toEqual(fontsCovering("AZ", COV));
  expect(fontsCovering("A\nZ\tA", COV)).toEqual(fontsCovering("AZ", COV));
  // …and whitespace alone is not a question worth answering.
  expect(fontsCovering("   ", COV)).toEqual([]);
});

test("a sparse (single-code-point) coverage list is read correctly", () => {
  expect(fontsCovering("AZ", COV)).toContain("sparse");
  // 'B' sits between two listed points and is NOT covered — an implementation
  // that treated the list as ranges would wrongly say it is.
  expect(fontsCovering("AB", COV)).not.toContain("sparse");
});

test("bad input answers nothing rather than throwing", () => {
  expect(fontsCovering("A", null)).toEqual([]);
  expect(fontsCovering("A", {})).toEqual([]);
  expect(fontsCovering(null, COV)).toEqual([]);
  expect(fontsCovering("", COV)).toEqual([]);
});

test("the message names the fonts that can, and caps the list", () => {
  const msg = unsupportedMessage("“Я”", "AЯ", COV, (k) => k.toUpperCase());
  expect(msg).toBe("This font can’t stitch “Я” — LATIN_AND_CYRILLIC can. Switch fonts and it will stitch.");

  const many = { version: 1, fonts: { a: [[A, Z]], b: [[A, Z]], c: [[A, Z]], d: [[A, Z]], e: [[A, Z]] } };
  const capped = unsupportedMessage("“x”", "A", many);
  expect(capped).toBe("This font can’t stitch “x” — a, b and c (2 more too) can. Switch fonts and it will stitch.");
});

test("when nothing in the library can, it leads with that — the current font is not the problem", () => {
  // Measured on the shipped library: Japanese, Korean and Arabic have no font
  // at all, so "try a different font" is advice to keep looking for something
  // that is not there.
  const msg = unsupportedMessage("“日” and “本”", "日本", COV);
  expect(msg).toBe("No font in this library can stitch “日” and “本” — try different text.");
  expect(msg).not.toContain("This font");
});

test("with no index at all, the message is exactly what shipped before it existed", () => {
  // An older build, an offline fetch, a 404: the suggestion is lost and
  // nothing else is.
  expect(unsupportedMessage("“Я”", "AЯ", null))
    .toBe("This font can’t stitch “Я”. Try a different font, or different text.");
});

// ---- the typographic fold (2026-09-07) ------------------------------------
//
// The engine stitches an ASCII twin when a font lacks the typographic form
// (satinfont.js TYPOGRAPHIC_FOLD). This module has to agree, or it suggests
// the customer keep looking past fonts that already work.

test("a font that lacks U+2019 but has an apostrophe counts as covering it", async () => {
  const { fontsCovering } = await import("./fontCoverage.js");
  // Ranges must be SORTED ASCENDING — rangesCover bails early on the first
  // range past the codepoint, so 39 has to precede [65,90]. (A first draft put
  // it last and both assertions failed, which is the guard working.)
  const coverage = { fonts: {
    plainonly: [39, [65, 90], [97, 122]],           // plain apostrophe only
    curlyonly: [[65, 90], [97, 122], 0x2019],       // curly only
    neither: [[65, 90], [97, 122]],
  } };
  const prior = globalThis.EMB;
  globalThis.EMB = { TYPOGRAPHIC_FOLD: { "’": "'" } };
  try {
    expect(fontsCovering("Fritsch’s", coverage)).toEqual(["curlyonly", "plainonly"]);
    // The fold is one-directional by design: a font with only the curly form
    // is not offered for text containing a plain apostrophe, because the
    // engine does not fold that way either.
    expect(fontsCovering("Fritsch's", coverage)).toEqual(["plainonly"]);
  } finally {
    globalThis.EMB = prior;
  }
});

test("with no engine loaded the fold is skipped rather than guessed", async () => {
  // A stale app/public/engine/ copy leaves EMB without the map. The honest
  // answer there is the pre-fold one — conservative, never wrong.
  const { fontsCovering } = await import("./fontCoverage.js");
  const coverage = { fonts: { plainonly: [39, [65, 90], [97, 122]] } };
  const prior = globalThis.EMB;
  globalThis.EMB = undefined;
  try {
    expect(fontsCovering("Fritsch’s", coverage)).toEqual([]);
    expect(fontsCovering("Fritsch's", coverage)).toEqual(["plainonly"]);
  } finally {
    globalThis.EMB = prior;
  }
});
