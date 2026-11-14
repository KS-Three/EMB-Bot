// Turning an element keeps its SIZE (Kent's approval 2026-11-13). The rotate
// grip and the Rotation inputs used to patch rotationDeg alone, but sizeMm is
// the width AFTER rotation, so the engine rescaled the turned design to the
// old width: "HELLO WORLD" at 90 mm sewed 90.2 x 7.4 upright, 88.2 x 88.3 at
// 45 degrees and 8.4 x 101.8 at 90 (review repro, 2026-11-13). Every control
// now patches through hoop.js rotationPatch; this file drives it against the
// real engine and asserts what the customer sees: the sewn design after the
// turn is the sewn design before, turned.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";

let EMB, generateElement, bboxMmFromStitches, rotationPatch, isElementStale, resizedTargetWidth, nativeWidthOf, defaultProject;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  ({ bboxMmFromStitches } = await import("./combine.js"));
  ({ rotationPatch } = await import("./hoop.js"));
  ({ isElementStale, nativeWidthOf } = await import("./staleness.js"));
  ({ resizedTargetWidth } = await import("./digitizer.js"));
  ({ defaultProject } = await import("./project.js"));
});

const garment = (id = "full_back") => EMB.getGarment(id);
const textEl = (o = {}) => ({
  id: "t", type: "text", text: "HELLO WORLD", fontKey: "medium_font", colorRgb: [20, 20, 20], colorRanges: [],
  weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, underlay: true,
  sizeMm: 90, offsetXMm: 0, offsetYMm: 0, ...o,
});
function designEl(o = {}) {
  const fs = createRequire(import.meta.url)("node:fs");
  const { fileURLToPath } = createRequire(import.meta.url)("node:url");
  const path = createRequire(import.meta.url)("node:path");
  const file = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../test/fixtures/standard-tajima.dst");
  return { id: "s", type: "design", name: "x.dst", dstBase64: fs.readFileSync(file).toString("base64"), blockColors: {}, sizeMm: 120, rotationDeg: 0, offsetXMm: 0, offsetYMm: 0, ...o };
}
// A round-ish result (an octagon of stitches, native 100 x 100 mm, 0.1 mm
// ints): the shape a rectangle rule gets most wrong at 45 degrees.
function ringResult() {
  const pts = [];
  for (let i = 0; i <= 64; i++) {
    const a = (i / 64) * Math.PI * 2;
    pts.push({ x: Math.round(500 * Math.cos(a)), y: Math.round(500 * Math.sin(a)), type: "stitch" });
  }
  return { colors: [{ r: 30, g: 60, b: 160 }], stitches: [...pts, { x: 0, y: 0, type: "end" }] };
}
const digitizedEl = (o = {}) => ({
  id: "d", type: "digitized", result: ringResult(), blockColors: {}, params: {}, sizeMm: 80, rotationDeg: 0,
  offsetXMm: 0, offsetYMm: 0, deletedShapeIds: [], shapeOverrides: {}, review: { shapes: [] }, appliedEdits: null, ...o,
});

const sewn = (el, g = garment()) => generateElement(el, g, {});
const dims = (d) => { const b = bboxMmFromStitches(d.stitches); return { w: b.x1 - b.x0, h: b.y1 - b.y0 }; };
// The sewn stitches of `d` turned by `deg` about their centre: the design the
// customer expects to see after turning it.
function turnedDims(d, deg) {
  const r = (deg * Math.PI) / 180, c = Math.cos(r), s = Math.sin(r);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of d.stitches) {
    if (p.type !== "stitch") continue;
    const x = (p.x * c - p.y * s) / 10, y = (p.x * s + p.y * c) / 10;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  return { w: x1 - x0, h: y1 - y0 };
}
function turn(el, deg, g = garment()) {
  const before = sewn(el, g);
  const after = { ...el, ...rotationPatch(el, deg, before) };
  return { before, after, d: sewn(after, g) };
}

test("lettering turned by the grip or a slider sews the same lettering, turned (15, 30, 45, 90, 180, 300)", () => {
  for (const deg of [15, 30, 45, 90, 180, 300]) {
    const { before, after, d } = turn(textEl(), deg);
    const want = turnedDims(before, deg), got = dims(d);
    expect(after.rotationDeg).toBe(deg);
    expect(Math.abs(got.w - want.w), `${deg}: width ${got.w} vs ${want.w}`).toBeLessThan(0.3);
    expect(Math.abs(got.h - want.h), `${deg}: height ${got.h} vs ${want.h}`).toBeLessThan(0.3);
    expect(d.stitchCount, `${deg}: same stitches`).toBe(before.stitchCount);
  }
});

test("the 90 mm HELLO WORLD at 45 degrees is not 28% longer, and at 90 is 7.4 x 90, not 8.4 x 101.8", () => {
  const at45 = turn(textEl(), 45, garment("left_chest")).d;
  const at90 = turn(textEl(), 90, garment("left_chest")).d;
  expect(dims(at45).w).toBeLessThan(72); // 90.2 x 7.4 turned 45 measures ~69 x 69
  expect(dims(at90).w).toBeCloseTo(7.4, 0);
  expect(dims(at90).h).toBeCloseTo(90.2, 0);
});

test("a turned element turned back is the element it was: the request is turned, not accumulated", () => {
  let el = textEl({ rotationDeg: 0 });
  // a slider dragged 0 -> 90 in 10-degree steps, each step from the element as it then stood
  for (let deg = 10; deg <= 90; deg += 10) el = { ...el, ...rotationPatch(el, deg, sewn(el)) };
  expect(el.sizeMm).toBeCloseTo(rotationPatch(textEl(), 90, sewn(textEl())).sizeMm, 6);
  el = { ...el, ...rotationPatch(el, 0, sewn(el)) };
  expect(el.sizeMm).toBeCloseTo(90, 6);
});

test("an imported design turned by any angle sews its own stitches turned", () => {
  for (const deg of [30, 45, 90, 135]) {
    const { before, d } = turn(designEl(), deg);
    const want = turnedDims(before, deg), got = dims(d);
    expect(Math.abs(got.w - want.w), `${deg}: width`).toBeLessThan(0.3);
    expect(Math.abs(got.h - want.h), `${deg}: height`).toBeLessThan(0.3);
  }
});

test("digitized artwork keeps its size turned, and a pure rotation neither marks it behind nor moves its Design width", () => {
  const project = { ...defaultProject(), garmentId: "full_back" };
  for (const deg of [45, 90, 200]) {
    const el = digitizedEl();
    const { before, after, d } = turn(el, deg);
    const want = turnedDims(before, deg), got = dims(d);
    expect(Math.abs(got.w - want.w), `${deg}: width ${got.w} vs ${want.w}`).toBeLessThan(0.3);
    expect(Math.abs(got.h - want.h), `${deg}: height`).toBeLessThan(0.3);
    // 80 mm of a 100 mm result is a resize: stale before, the same resize after
    expect(isElementStale(el, project)).toBe(true);
    expect(isElementStale(after, project)).toBe(true);
    expect(resizedTargetWidth(after, nativeWidthOf(after))).toBe(resizedTargetWidth(el, nativeWidthOf(el)));
    // and at its native size it reads current, before and after
    const native = digitizedEl({ sizeMm: 100 });
    const turnedNative = { ...native, ...rotationPatch(native, deg) };
    expect(isElementStale(native, project)).toBe(false);
    expect(isElementStale(turnedNative, project), `${deg}: native stays current`).toBe(false);
  }
});

test("left alone: a null sizeMm stays null; image, manual and shape elements; outline lettering", () => {
  expect(rotationPatch(textEl({ sizeMm: null }), 45, null)).toEqual({ rotationDeg: 45 });
  expect(rotationPatch(digitizedEl({ sizeMm: null }), 90)).toEqual({ rotationDeg: 90 });
  for (const type of ["image", "manual", "shape"]) expect(rotationPatch({ id: "x", type, sizeMm: 60 }, 90)).toEqual({ rotationDeg: 90 });
  expect(rotationPatch(textEl({ fontKey: "outline:anything" }), 90, null).sizeMm).toBeUndefined();
  // lettering whose design is not to hand (font still loading) only turns
  expect(rotationPatch(textEl(), 90, null)).toEqual({ rotationDeg: 90 });
});

test("the hoop clamp still applies: a turn that would not fit shrinks to the box, and turning back restores it", () => {
  const g = garment("blanket"); // 254 x 203.2 mm engine box: landscape
  const el = textEl({ sizeMm: 240 });
  const { after, d } = turn(el, 90, g);
  expect(dims(d).h).toBeLessThanOrEqual(203.2 + 0.5); // clamped to the box height
  expect(dims(d).h).toBeGreaterThan(200);
  const back = { ...after, ...rotationPatch(after, 0, d) };
  expect(back.sizeMm).toBeCloseTo(240, 6);
  expect(dims(sewn(back, g)).w).toBeCloseTo(dims(sewn(el, g)).w, 1);
});
