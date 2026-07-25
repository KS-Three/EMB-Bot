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
test("generateImageDesign produces stitches from a flat", async () => {
  const { flattenRGBA } = await import("./flatten.js");
  const { generateImageDesign } = await import("./generate.js");
  const { defaultImageElement } = await import("./project.js");
  const w = 96, h = 64;
  const flat = flattenRGBA(synthRGBA(w, h), w, h, { nColors: 2, removeBg: false });
  // generate.js still expects a flat v1-ish project object (Task 2 reworks
  // it); build a COMPAT object from the v2 default image element — see
  // generate.spec.js for the full rationale.
  const d = generateImageDesign(flat, { ...defaultImageElement("e1"), garmentId: "left_chest" });
  expect(d.stitchCount).toBeGreaterThan(100);
  expect(d.colorCount).toBe(2);
});
