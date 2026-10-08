import { expect, test, vi } from "vitest";
import { originalDataUrl, fitRect, hasOriginal, placeByContent, flatContentBox, digitizedContentBox, loadOriginal, ORIGINAL_CACHE_MAX } from "./originalImage.js";

test("the content box, not the frame, is fitted to the rect", () => {
  // 200x100 image whose art is the middle half: the image is drawn at twice
  // the rect's size, shifted so the art fills the rect exactly.
  expect(placeByContent(200, 100, { x: 50, y: 25, w: 100, h: 50 }, { x: 0, y: 0, w: 200, h: 100 }))
    .toEqual({ x: -100, y: -50, w: 400, h: 200 });
});

test("off-centre content, uniform scale, centred in a rect of another aspect", () => {
  // Content 40x20 at (20,60) in a 100x100 image; rect 80x80 at (10,10).
  // s = min(80/40, 80/20) = 2 -> content 80x40, centred at y 10+20 = 30.
  expect(placeByContent(100, 100, { x: 20, y: 60, w: 40, h: 20 }, { x: 10, y: 10, w: 80, h: 80 }))
    .toEqual({ x: 10 - 40, y: 30 - 120, w: 200, h: 200 });
});

test("content equal to the whole frame is exactly fitRect", () => {
  const rect = { x: 10, y: 20, w: 100, h: 100 };
  expect(placeByContent(200, 100, { x: 0, y: 0, w: 200, h: 100 }, rect)).toEqual(fitRect(200, 100, rect));
});

test("placeByContent refuses degenerate input", () => {
  const rect = { x: 0, y: 0, w: 10, h: 10 };
  expect(placeByContent(0, 10, { x: 0, y: 0, w: 5, h: 5 }, rect)).toBeNull();
  expect(placeByContent(10, 10, { x: 0, y: 0, w: 0, h: 5 }, rect)).toBeNull();
  expect(placeByContent(10, 10, null, rect)).toBeNull();
  expect(placeByContent(10, 10, { x: 0, y: 0, w: 5, h: 5 }, { x: 0, y: 0, w: 10, h: 0 })).toBeNull();
});

test("the flat's content box skips the transparent index (255) only", () => {
  // 5x4 grid, kept pixels at (1,1), (3,1) and (2,2); index 0 counts as art.
  const T = 255;
  const idx = new Uint8Array([
    T, T, T, T, T,
    T, 0, T, 1, T,
    T, T, 0, T, T,
    T, T, T, T, T,
  ]);
  expect(flatContentBox(idx, 5, 4)).toEqual({ x: 1, y: 1, w: 3, h: 2 });
  expect(flatContentBox(new Uint8Array(4).fill(T), 2, 2)).toBeNull();
  expect(flatContentBox(new Uint8Array([0, 0, 0, 0]), 2, 2)).toEqual({ x: 0, y: 0, w: 2, h: 2 });
});

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

test("digitizedContentBox maps the service's art fractions back through the crop", () => {
  // Uncropped: fractions of the whole frame.
  const a = digitizedContentBox(1000, 500, [0.1, 0.2, 0.6, 0.8], null);
  expect([a.x, a.y, a.w, a.h].map(Math.round)).toEqual([100, 100, 500, 300]);
  // Cropped to the right half: the art box is a fraction of THAT half.
  const b = digitizedContentBox(1000, 500, [0, 0, 0.5, 1], { x0: 0.5, y0: 0, x1: 1, y1: 1 });
  expect(b).toEqual({ x: 500, y: 0, w: 250, h: 500 });
  // No box (an older saved review), or a degenerate one: no registration.
  expect(digitizedContentBox(1000, 500, null, null)).toBeNull();
  expect(digitizedContentBox(1000, 500, [0.5, 0.5, 0.5, 0.9], null)).toBeNull();
});

test("loadOriginal keeps a bounded cache: a repeat is the same decode, the oldest upload is evicted", async () => {
  let decodes = 0;
  vi.stubGlobal("Image", class {
    set src(_) { decodes++; queueMicrotask(() => this.onload && this.onload()); }
  });
  try {
    const png = (i) => "iVBORw0KGgo" + i;
    const first = loadOriginal(png(0));
    expect(loadOriginal(png(0))).toBe(first);
    expect(decodes).toBe(1);
    for (let i = 1; i <= ORIGINAL_CACHE_MAX; i++) loadOriginal(png(i));
    expect(decodes).toBe(ORIGINAL_CACHE_MAX + 1);
    loadOriginal(png(0)); // evicted by the ninth distinct image: decodes again
    expect(decodes).toBe(ORIGINAL_CACHE_MAX + 2);
  } finally {
    vi.unstubAllGlobals();
  }
});
