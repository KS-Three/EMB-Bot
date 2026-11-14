// A corner-handle resize moves the REQUEST in step with the sewn width (Kent's
// approval 2026-11-13). The handle sits on the sewn box, and the field used
// to write the sewn width as `sizeMm`, the requested width: they differ by
// pull compensation and, on turned lettering, by the rotated-rect fit, so a
// 1 px touch on 120 mm lettering at 45 degrees wrote 117.5 and five touches
// 108.1. `fieldResize` is EmbroideryField onPointerMove "resize" (dragResize,
// the optional size-match snap, then resizeTargetMm); the press-release dead
// zone in front of it is the field's own, driven in a browser by
// e2e/core-flows.spec.js ("a press on a corner handle that does not travel
// writes nothing", single element and group; added 2026-11-13).
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

let EMB, generateElement, bboxMmFromStitches, dragResize, resizeTargetMm, resizeIsAdditive;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  ({ bboxMmFromStitches } = await import("./combine.js"));
  ({ dragResize, resizeTargetMm, resizeIsAdditive } = await import("./interact.js"));
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
  return resizeTargetMm(T, S, w, resizeIsAdditive(el, false));
}

// The size-match snap lands the sewn width EXACTLY (to the stitch box's
// 0.1 mm), upright, on every quarter turn and off them (review follow-up,
// 2026-11-13; the reviewer's table plus 90/270 and 135).
test("a snap to another element's width lands on it, upright, turned a quarter, and at 45/135", () => {
  const cases = [[0, 120, [60, 61, 80, 120, 30]], [0, 60, [120, 30]], [180, 120, [60, 30]],
    [90, 10, [5, 8, 12, 15]], [270, 10, [8, 15]], [45, 120, [100, 140]], [135, 120, [100, 140]]];
  for (const [rot, T, snaps] of cases) {
    const el = textEl({ rotationDeg: rot, sizeMm: T });
    for (const s of snaps) {
      const got = sewnBox({ ...el, sizeMm: fieldResize(el, 0, s) }).w;
      expect(Math.abs(got - s), `rot ${rot}, ${T} -> snap ${s}: ${got}`).toBeLessThan(0.05);
    }
  }
});

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

// The group corner (review follow-up, 2026-11-13): an auto-fit lettering
// member was seeded with its SEWN width as its request, so even a factor-1
// touch rewrote its size (upright 96.2 -> 97.2 over five touches, 45 degrees
// 72.8 -> 58.0). The field seeds every member through resizeStartTargetMm.
test("five factor-1 touches of the group corner leave auto-fit lettering at its size", async () => {
  const { groupResizePatches, resizeStartTargetMm } = await import("./interact.js");
  for (const rot of [0, 45]) {
    let els = [textEl({ id: "a", sizeMm: null, rotationDeg: rot }), textEl({ id: "b", text: "HI", sizeMm: 40, offsetYMm: -40 })];
    const sewn0 = sewnBox(els[0]).w;
    for (let i = 0; i < 5; i++) {
      const members = els.map((el) => {
        const d = generateElement(el, garment(), {});
        const b = bboxMmFromStitches(d.stitches);
        const w = b.x1 - b.x0;
        return { id: el.id, offsetXMm: el.offsetXMm, offsetYMm: el.offsetYMm, widthMm: w, targetMm: resizeStartTargetMm(el, d, w) };
      });
      const r = groupResizePatches(members, 1, 0, 0, 5);
      els = els.map((el) => ({ ...el, ...r.patches[el.id] }));
    }
    expect(Math.abs(sewnBox(els[0]).w - sewn0), `rot ${rot}: ${sewnBox(els[0]).w} vs ${sewn0}`).toBeLessThan(0.15);
    expect(els[1].sizeMm).toBeCloseTo(40, 9);
  }
});

test("resizeStartTargetMm: sizeMm when set, lettering's fit width when auto-fit, else the sewn width", async () => {
  const { resizeStartTargetMm } = await import("./interact.js");
  expect(resizeStartTargetMm({ type: "text", sizeMm: 50 }, { fitMm: { w: 70 } }, 71)).toBe(50);
  expect(resizeStartTargetMm({ type: "text", sizeMm: null }, { fitMm: { w: 70 } }, 71)).toBe(70);
  expect(resizeStartTargetMm({ type: "design", sizeMm: null }, { widthMM: 80 }, 80)).toBe(80);
  expect(resizeStartTargetMm({ type: "text", sizeMm: null }, null, 71)).toBe(71);
});
