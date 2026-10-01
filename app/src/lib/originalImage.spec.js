import { expect, test } from "vitest";
import { originalDataUrl, fitRect, hasOriginal } from "./originalImage.js";

test("builds a PNG data URL from bare base64, and nothing from nothing", () => {
  expect(originalDataUrl("AAAA")).toBe("data:image/png;base64,AAAA");
  expect(originalDataUrl(null)).toBeNull();
  expect(originalDataUrl("")).toBeNull();
});

test("a wide image in a square rect is letterboxed and centred", () => {
  expect(fitRect(200, 100, { x: 10, y: 20, w: 100, h: 100 })).toEqual({ x: 10, y: 45, w: 100, h: 50 });
});

test("a tall image in a wide rect is pillarboxed and centred", () => {
  expect(fitRect(100, 200, { x: 0, y: 0, w: 300, h: 100 })).toEqual({ x: 125, y: 0, w: 50, h: 100 });
});

test("a degenerate image or rect yields null", () => {
  expect(fitRect(0, 100, { x: 0, y: 0, w: 10, h: 10 })).toBeNull();
  expect(fitRect(10, 10, { x: 0, y: 0, w: 0, h: 10 })).toBeNull();
  expect(fitRect(10, 10, null)).toBeNull();
});

test("only image and digitized elements with a sourcePng have an original", () => {
  expect(hasOriginal({ type: "image", sourcePng: "AAAA" })).toBe(true);
  expect(hasOriginal({ type: "digitized", sourcePng: "AAAA" })).toBe(true);
  expect(hasOriginal({ type: "digitized", sourcePng: null })).toBe(false);
  expect(hasOriginal({ type: "text", text: "A" })).toBe(false);
  expect(hasOriginal(null)).toBe(false);
});
