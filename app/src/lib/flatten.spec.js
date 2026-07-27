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
