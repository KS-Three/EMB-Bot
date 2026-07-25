import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","dst","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
});

// build a synthetic two-color image: left half red, right half blue
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

test("flatToRegions traces one region per palette color", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { flatToRegions } = await import("./imageRegions.js");
  const w = 96, h = 64; // big enough to survive despeckle
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  const { regions, pxPerMm } = flatToRegions(flat);
  expect(regions.length).toBe(2);
  expect(regions[0].shapes.length).toBeGreaterThan(0);
  expect(pxPerMm).toBeCloseTo(96 / 50, 2);
});

test("flatToRegions respects per-swatch thread color overrides", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { flatToRegions } = await import("./imageRegions.js");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  // Get regions without override to compare
  const { regions: regionsNoOverride } = flatToRegions(flat);
  // Get regions with thread color override on palette index 0
  const overrideRgb = [255, 0, 0];
  const { regions: regionsWithOverride } = flatToRegions(flat, { threadRgb: { 0: overrideRgb } });
  // Verify the override was applied to region for palette index 0
  expect(regionsWithOverride[0].rgb).toEqual(overrideRgb);
  // Verify the other region keeps its palette color
  expect(regionsWithOverride[1].rgb).toEqual(regionsNoOverride[1].rgb);
  // Verify region for palette index 1 was not affected
  expect(regionsWithOverride[1].rgb).not.toEqual(overrideRgb);
});
// Regression note (final-review-s5.md Important #1): element.threadRgb is
// keyed by PALETTE INDEX, and that palette is rebuilt from scratch on every
// re-flatten/merge (ImagePanel.svelte now clears threadRgb whenever that
// happens -- see flattenFrom/mergeSelected there). This is the lib-level
// half of that guard: flatToRegions must reference threadRgb defensively
// (`ci in threadRgb` for `ci` in `0..palette.length-1` only), so if a stale
// override key ever DID slip through (out of range for the current
// palette), it's ignored harmlessly rather than throwing or corrupting an
// unrelated swatch.
test("flatToRegions ignores threadRgb overrides for indices beyond the current palette (stale-key safety net)", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { flatToRegions } = await import("./imageRegions.js");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  expect(flat.palette.length).toBe(2);

  const { regions: regionsNoOverride } = flatToRegions(flat);
  // Index 5 doesn't exist on a 2-color flat -- as if a prior merge/re-flatten
  // shrank the palette out from under a stale threadRgb key.
  expect(() => flatToRegions(flat, { threadRgb: { 5: [1, 2, 3] } })).not.toThrow();
  const { regions: regionsWithStaleOverride } = flatToRegions(flat, { threadRgb: { 5: [1, 2, 3] } });

  expect(regionsWithStaleOverride.length).toBe(regionsNoOverride.length);
  expect(regionsWithStaleOverride.map((r) => r.rgb)).toEqual(regionsNoOverride.map((r) => r.rgb));
});

test("generateImageDesign produces stitches from a flat", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { generateImageDesign } = await import("./generate.js");
  const { defaultImageElement } = await import("./project.js");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  // generateImageDesign is the deliberately-kept-deprecated shim for callers
  // still passing a flat, v1-ish object (element fields spread onto a
  // garmentId-bearing object) instead of a real project + element — see the
  // "Deprecated" note on generateImageDesign in generate.js.
  const d = generateImageDesign(flat, { ...defaultImageElement("e1"), garmentId: "left_chest" });
  expect(d.stitchCount).toBeGreaterThan(100);
  expect(d.colorCount).toBe(2);
});
