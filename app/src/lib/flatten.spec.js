import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});

// build a synthetic 24x16 two-color image: left half red, right half blue
function synthRGBA(w, h) {
  const rgba = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const o = (y * w + x) * 4;
    if (x < w / 2) { rgba[o] = 200; rgba[o + 1] = 30; rgba[o + 2] = 30; }
    else { rgba[o] = 30; rgba[o + 1] = 30; rgba[o + 2] = 200; }
    rgba[o + 3] = 255;
  }
  return rgba;
}
test("flattenRGBA reduces to the requested palette and covers all pixels", async () => {
  const { flattenRGBA, flatShares } = await import("./flatten.js");
  const w = 24, h = 16;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  expect(flat.palette.length).toBe(2);
  expect(flat.indices.length).toBe(w * h);
  const shares = flatShares(flat);
  expect(shares.length).toBe(2);
  expect(shares[0] + shares[1]).toBeCloseTo(1, 1);
});
test("mergeFlat collapses two entries into one", async () => {
  const { flattenRGBA, mergeFlat } = await import("./flatten.js");
  const w = 24, h = 16;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const merged = mergeFlat(flat, [0, 1]);
  expect(merged.palette.length).toBe(1);
});

// ---- the slider is a ceiling, not a count (2026-09-08) ---------------------
//
// `nColors` is what the customer ASKED for. Median-cut hands back only as many
// entries as the art actually needs, so the two part company on any artwork
// simpler than the slider — no empty palette slot required, which is why this
// went unnoticed: the swatch strip renders the truth and the review card two
// clicks later printed the slider.
test("median-cut returns what the art needs, so nColors is a ceiling", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const w = 24, h = 16;
  for (const nColors of [2, 3, 4, 6, 8]) {
    const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors, removeBg: false });
    expect(flat.palette.length, `nColors=${nColors}`).toBe(2);
  }
});

test("sewnColorCount reports the colours that carry pixels", async () => {
  const { flattenRGBA, sewnColorCount, MIN_SWATCH_SHARE } = await import("./flatten.js");
  const w = 24, h = 16;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 4, removeBg: false });
  // The number a customer is billed for: two cones, not the four they asked
  // for. This is the assertion that fails if the review card goes back to
  // reading the slider.
  expect(sewnColorCount(flat)).toBe(2);
  // Same rule ImagePanel's swatch strip renders by, shared rather than copied.
  expect(MIN_SWATCH_SHARE).toBeGreaterThan(0);
});

test("sewnColorCount answers null, not a confident zero, with nothing flattened", async () => {
  const { sewnColorCount } = await import("./flatten.js");
  // A caller has to be able to tell "no image yet" from "flattened to
  // nothing" — summary.js falls back to the slider on the first and would
  // print "Colors 0" on the second.
  for (const empty of [null, undefined, {}, { palette: null }]) {
    expect(sewnColorCount(empty)).toBe(null);
  }
});
