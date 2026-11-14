// Garment-switch auto-fit of a pre-digitized stitch file stops at the safe
// range's edge (Kent 2026-11-14, "Stop at 75%, say so"): the monarch on Hat is
// 68x65 mm, not 60x57. Typed widths, digitized art and lettering are untouched.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
let dst;
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  dst = require("../../../src/dst.js");
});

// A two-point diagonal: a bbox of wMm x hMm, nothing else.
function fileOf(wMm, hMm) {
  const w = Math.round((wMm * 10) / 2), h = Math.round((hMm * 10) / 2);
  const bytes = dst.encodeDST({
    stitches: [{ x: -w, y: -h, type: "stitch" }, { x: w, y: h, type: "stitch" }, { x: w, y: h, type: "end" }],
    colors: [{ r: 0, g: 0, b: 0 }],
  });
  return Buffer.from(bytes).toString("base64");
}
const designEl = (wMm, hMm, o = {}) => ({ id: "d1", type: "design", name: "x.dst", dstBase64: fileOf(wMm, hMm), sizeMm: null, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, blockColors: {}, ...o });

async function hat() {
  const { EMB } = await import("./emb.js");
  const { generateElement } = await import("./generate.js");
  return { generateElement, garment: EMB.getGarment("hat_front") };
}

test("a stitch file the Hat box would shrink to 66% lands at 75%, past the box", async () => {
  const { generateElement, garment } = await hat();
  const d = generateElement(designEl(91, 86), garment, {});
  expect(d._debug.scale).toBe(0.75);
  expect(d.widthMM).toBeCloseTo(68.25, 1);
});

test("a stitch file that lands at 90% is unchanged", async () => {
  const { generateElement, garment } = await hat();
  const noRange = (await import("./emb.js")).EMB;
  const el = designEl(60, 63);
  const d = generateElement(el, garment, {});
  const plain = noRange.buildImportedDesign(noRange.decodeDSTStandard(Uint8Array.from(Buffer.from(el.dstBase64, "base64"))), { garment });
  expect(d._debug.scale).toBeGreaterThan(0.75);
  expect(d._debug.scale).toBeLessThan(1);
  expect(d._debug.scale).toBe(plain._debug.scale);
});

test("a hand-typed 42% still applies", async () => {
  const { generateElement, garment } = await hat();
  const d = generateElement(designEl(91, 86, { sizeMm: 38.22 }), garment, {});
  expect(d._debug.scale).toBeCloseTo(0.42, 2);
});

test("digitized art still fits the box (no 75% floor)", async () => {
  const { generateElement, garment } = await hat();
  const result = {
    stitches: [{ x: -455, y: -430, type: "stitch" }, { x: 455, y: 430, type: "stitch" }, { x: 455, y: 430, type: "end" }],
    colors: [{ r: 0, g: 0, b: 0 }], widthMM: 91, heightMM: 86, stitchCount: 2, colorCount: 1,
  };
  const d = generateElement({ id: "g1", type: "digitized", result, sizeMm: null, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0 }, garment, {});
  expect(d._debug.scale).toBeLessThan(0.75);
  expect(d.heightMM).toBeLessThanOrEqual(garment.heightIn * 25.4 + 1e-6);
});
