// A corner-handle resize moves the REQUEST in step with the sewn width (Kent's
// approval 2026-11-13). The handle sits on the sewn box, and the field used
// to write the sewn width as `sizeMm`, the requested width: they differ by
// pull compensation and, on turned lettering, by the rotated-rect fit, so a
// 1 px touch on 120 mm lettering at 45 degrees wrote 117.5 and five touches
// 108.1. `fieldResize` is EmbroideryField onPointerMove "resize" (dragResize,
// the optional size-match snap, then resizeTargetMm); the press-release dead
// zone in front of it is the field's own and is covered by e2e.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

let EMB, generateElement, bboxMmFromStitches, dragResize, resizeTargetMm;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  ({ bboxMmFromStitches } = await import("./combine.js"));
  ({ dragResize, resizeTargetMm } = await import("./interact.js"));
});

const textEl = (o = {}) => ({
  id: "e1", type: "text", text: "HELLO WORLD", fontKey: "medium_font", colorRgb: [20, 20, 20], colorRanges: [],
  weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
  sizeMm: 120, offsetXMm: 0, offsetYMm: 0, ...o,
});
const garment = () => EMB.getGarment("full_back");
function sewnBox(el) {
  const b = bboxMmFromStitches(generateElement(el, garment(), {}).stitches);
  return { w: b.x1 - b.x0, h: b.y1 - b.y0 };
}
// The field's resize, from the element as pressed: sewn box, request, and a
// diagonal drag of the SE handle that moves the sewn width by `dMm`.
function fieldResize(el, dMm, snapSewnW = null) {
  const { w: S, h: H } = sewnBox(el);
  const T = el.sizeMm;
  let w = dragResize(S, H, "se", dMm, (dMm * H) / S, 5, garment().widthIn * 25.4);
  if (snapSewnW != null) w = snapSewnW;
  return resizeTargetMm(T, S, w);
}

test("a zero-distance resize is the identity, upright and turned", () => {
  for (const rot of [0, 30, 45]) {
    const el = textEl({ rotationDeg: rot });
    expect(fieldResize(el, 0), `rot ${rot}`).toBeCloseTo(120, 9);
  }
});

test("five touches on a 45-degree corner leave the lettering at 120 mm", () => {
  let el = textEl({ rotationDeg: 45 });
  const sewn0 = sewnBox(el).w;
  for (let i = 0; i < 5; i++) el = { ...el, sizeMm: fieldResize(el, 0) };
  expect(el.sizeMm).toBeCloseTo(120, 6);
  expect(sewnBox(el).w).toBeCloseTo(sewn0, 1);
});

test("a drag of d mm changes the sewn width by d mm, upright and turned", () => {
  for (const rot of [0, 45]) {
    for (const d of [10, -20]) {
      const el = textEl({ rotationDeg: rot });
      const before = sewnBox(el).w;
      const after = sewnBox({ ...el, sizeMm: fieldResize(el, d) }).w;
      expect(Math.abs(after - before - d), `rot ${rot}, d ${d}: ${after - before}`).toBeLessThan(0.25);
    }
  }
});

test("the size-match snap and a plain drag to the same sewn width write the same request", () => {
  for (const rot of [0, 45]) {
    const el = textEl({ rotationDeg: rot });
    const plain = fieldResize(el, -30);
    const target = sewnBox({ ...el, sizeMm: plain }).w;
    const S = sewnBox(el).w;
    const snapped = fieldResize(el, -29, S - 30); // dragged near, snapped onto S - 30
    expect(snapped, `rot ${rot}`).toBeCloseTo(plain, 6);
    expect(Math.abs(target - (S - 30)), `rot ${rot}: lands on the matched width`).toBeLessThan(0.25);
  }
});
