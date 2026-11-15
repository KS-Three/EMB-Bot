// The upload's auto-fit fits the INK, not the padded crop (review 2026-11-14).
//
// The engine sizes the ink box inside the crop to the Design width
// (digitizer_core/stage1_prep: px_per_mm = art width / target_width_mm). The
// upload proposes a crop (cropProposal.proposeCrop) padded by 2 mm on every
// side, and the auto-fit (placement.fitTargetWidthMm) fitted THAT aspect, so
// tall art sewed over the placement's height and multi-part art under its
// width: 14 of 126 garment fits over the 42 eye-sweep designs. Each shape
// below is drawn as the upload canvas draws it, put through the panel's own
// two calls (proposeCrop at the default 80 mm, then the fit), and "sewn" is
// what the engine makes of that width: the ink's width, and its height by
// the ink's own aspect.
import { beforeAll, expect, test } from "vitest";
import { createRequire } from "node:module";
import { inkBox, proposeCrop } from "./cropProposal.js";

let placement;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  placement = await import("./placement.js");
});

const hat = { garmentId: "hat_front", placementId: null };
const HAT_H = 64;

// A width x height RGBA frame of `bg`, with `rects` ([x0, y0, x1, y1, rgba])
// painted over it.
function frame(width, height, bg, rects) {
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < width * height; i++) data.set(bg, i * 4);
  for (const [x0, y0, x1, y1, c] of rects) {
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) data.set(c, (y * width + x) * 4);
  }
  return { data, width, height };
}

const CLEAR = [0, 0, 0, 0], WHITE = [255, 255, 255, 255], BLACK = [0, 0, 0, 255], GREY = [180, 180, 180, 255];

// The panel's upload: proposal, ink box, then the fit before (crop) and
// after (ink); `ink` is the art's true ink box in px, which the engine sizes.
function upload(img, ink) {
  const px = { w: img.width, h: img.height };
  const crop = proposeCrop(img, 80);
  const box = inkBox(img, crop);
  const before = placement.fitTargetWidthMm(px, crop, hat);
  const after = placement.fitTargetWidthMm(px, crop, hat, box);
  const aspect = (ink[2] - ink[0]) / (ink[3] - ink[1]);
  return { crop, box, before, after, sewnHBefore: before / aspect, sewnHAfter: after / aspect };
}

test("tight art: ink to the frame's edges fits as it did", () => {
  const ink = [0, 10, 400, 190];
  const u = upload(frame(400, 200, WHITE, [[...ink, BLACK]]), ink);
  expect(u.box).toEqual({ x0: 0, y0: 10 / 200, x1: 1, y1: 190 / 200 });
  expect(u.after).toBe(113.5);
  expect(u.after).toBe(u.before);
});

test("transparent margins (a badge on an RGBA canvas): sewn inside the hat's height, not over it", () => {
  // 480 x 600, aspect 0.8, on the proposal's 30 px cells (2 mm at the default
  // 80 mm over 1200 px), so its 2 mm pad is the same on every side
  const ink = [360, 90, 840, 690];
  const u = upload(frame(1200, 800, CLEAR, [[...ink, BLACK]]), ink);
  expect(u.sewnHBefore).toBeGreaterThan(HAT_H + 1);      // the bug: the padded crop's aspect, fitted (65.5)
  expect(u.sewnHAfter).toBeLessThanOrEqual(HAT_H + 0.06);
  expect(u.after).toBe(51.2);                              // 64 x 0.8
});

test("letterbox screenshot: the logo between the phone's bars sews at the logo's width", () => {
  const ink = [77, 515, 477, 685];                        // 400 x 170, aspect 2.35 (Gaulke's is 2.35)
  const img = frame(555, 1200, WHITE, [[0, 0, 555, 15, GREY], [0, 1185, 555, 1200, GREY], [...ink, BLACK]]);
  const u = upload(img, ink);
  expect(placement.fitTargetWidthMm({ w: 555, h: 1200 }, null, hat)).toBe(29.6);   // the whole file, as the trace fitted it
  expect(u.box).toEqual({ x0: 77 / 555, y0: 515 / 1200, x1: 477 / 555, y1: 685 / 1200 });
  expect(u.after).toBe(113.5);
  expect(u.sewnHAfter).toBeLessThanOrEqual(HAT_H);
});

test("tall art: a narrow upright mark is height-bound by its own aspect", () => {
  const ink = [350, 200, 450, 600];                       // 100 x 400, aspect 0.25
  const u = upload(frame(800, 800, CLEAR, [[...ink, BLACK]]), ink);
  expect(u.sewnHBefore).toBeGreaterThan(HAT_H * 1.15);   // the padding is a big share of a narrow mark
  expect(u.after).toBe(16);
  expect(u.sewnHAfter).toBeLessThanOrEqual(HAT_H + 0.06);
});

test("user crop: a crop the customer drew carries no ink box and fits exactly as before", () => {
  const px = { w: 1000, h: 1000 };
  const crop = { x0: 0, y0: 0.25, x1: 1, y1: 0.75 };
  const old = placement.fitTargetWidthMm(px, crop, hat);
  expect(old).toBe(113.5);                                 // placement.spec's own case, unchanged
  expect(placement.fitTargetWidthMm(px, crop, hat, null)).toBe(old);
  const el = { id: "e", type: "digitized", sourcePx: px, crop, inkBox: null, sourcePng: "x", result: null,
               params: { target_width_mm: 80 } };
  const out = placement.refitDigitized({ garmentId: "hat_front", placementId: null, elements: [el] });
  expect(out.elements[0].params.target_width_mm).toBe(old);
  const p = placement.preRunSizePatch(el, { sizeMm: null }, hat);
  expect(p.params.target_width_mm).toBe(old);
});

test("a re-fit and the Auto-fit reset read the stored ink box", () => {
  const px = { w: 1200, h: 800 };
  const crop = { x0: 0.25, y0: 0.15, x1: 0.75, y1: 0.85 };
  const ink = { x0: 0.3, y0: 0.18, x1: 0.7, y1: 0.82 };       // 480 x 512 px
  const want = placement.fitTargetWidthMm(px, crop, hat, ink);
  expect(want).toBeCloseTo(HAT_H * 480 / 512, 1);
  const el = { id: "e", type: "digitized", sourcePx: px, crop, inkBox: ink, sourcePng: "x", result: null,
               params: { target_width_mm: 80 } };
  expect(placement.refitDigitized({ garmentId: "hat_front", elements: [el] }).elements[0].params.target_width_mm).toBe(want);
  expect(placement.preRunSizePatch(el, { sizeMm: null }, hat).params.target_width_mm).toBe(want);
});

test("inkBox: nothing inked is null; ink outside the crop is not read", () => {
  expect(inkBox(frame(50, 50, WHITE, []), null)).toBeNull();
  const img = frame(200, 100, WHITE, [[10, 10, 30, 30, BLACK], [150, 40, 190, 90, BLACK]]);
  expect(inkBox(img, { x0: 0.5, y0: 0, x1: 1, y1: 1 })).toEqual({ x0: 150 / 200, y0: 40 / 100, x1: 190 / 200, y1: 90 / 100 });
  expect(inkBox(img, null)).toEqual({ x0: 10 / 200, y0: 10 / 100, x1: 190 / 200, y1: 90 / 100 });
});
