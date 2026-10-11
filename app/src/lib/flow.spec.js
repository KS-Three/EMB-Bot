import { expect, test } from "vitest";
import { isSewable } from "./flow.js";

test("a text element is sewable once it has non-blank text", () => {
  expect(isSewable({ type: "text", text: "" })).toBe(false);
  expect(isSewable({ type: "text", text: "   " })).toBe(false);
  expect(isSewable({ type: "text", text: "EMB" })).toBe(true);
});

test("an image element is sewable only via its runtime _hasImage flag", () => {
  expect(isSewable({ type: "image" })).toBe(false);
  expect(isSewable({ type: "image", _hasImage: true })).toBe(true);
});

test("design and digitized elements gate on their baked content, not _hasImage", () => {
  expect(isSewable({ type: "design", _hasImage: true })).toBe(false);
  expect(isSewable({ type: "design", dstBase64: "AAAA" })).toBe(true);
  expect(isSewable({ type: "digitized", _hasImage: true })).toBe(false);
  expect(isSewable({ type: "digitized", result: { ok: true } })).toBe(true);
});

test("a manual element holding only cut-outs sews nothing", () => {
  const tri = [{ x: 0, y: 0 }, { x: 40, y: 0 }, { x: 40, y: 40 }];
  expect(isSewable({ type: "manual", shapes: [{ points: tri, cutOut: true }] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: tri, cutOut: true }, { points: tri }] })).toBe(true);
});

test("a manual element needs at least one valid completed shape", () => {
  expect(isSewable({ type: "manual", shapes: [] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }] }] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }] }] })).toBe(true);
});

test("a manual element holding only a valid column is sewable", () => {
  const spine = [{ x: 50, y: 100 }, { x: 350, y: 100 }];
  const col = { id: "s1", kind: "column", points: spine, curves: {}, widthPx: 24, colorRgb: [20, 20, 20] };
  expect(isSewable({ type: "manual", shapes: [col] })).toBe(true);
  // one point is not a column yet; a 3 px stub is too short to sew
  expect(isSewable({ type: "manual", shapes: [{ ...col, points: spine.slice(0, 1) }] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ ...col, points: [{ x: 0, y: 0 }, { x: 3, y: 0 }] }] })).toBe(false);
});

test("a manual shape is judged on the ring generation sews, curves included", () => {
  // The raw anchors are a clean square; the bowed top edge crosses the bottom
  // one, and shapesToRegions skips it — so it is not sewable here either.
  const sq = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  expect(isSewable({ type: "manual", shapes: [{ points: sq, curves: { 0: { x: 50, y: 400 } } }] })).toBe(false);
  expect(isSewable({ type: "manual", shapes: [{ points: sq, curves: {} }] })).toBe(true);
});

test("a preset shape element is sewable from birth", () => {
  expect(isSewable({ type: "shape", kind: "circle", params: {} })).toBe(true);
});

test("null is not sewable", () => {
  expect(isSewable(null)).toBe(false);
});
