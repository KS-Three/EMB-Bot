// The rule that decides how big an uploaded file is drawn — and the one place
// it now lives. There were three byte-identical copies of `loadImage` and
// three copies of the work-size rule (DigitizePanel, ImagePanel,
// TraceImportPanel), and the rule was wrong in all three for the same reason.
import { test, expect, vi } from "vitest";
import { isVectorFile, rasterSize, loadImage, UNREADABLE } from "./rasterize.js";

const file = (name, type) => ({ name, type });

test("isVectorFile reads the MIME type first and the extension as the fallback", () => {
  expect(isVectorFile(file("logo.svg", "image/svg+xml"))).toBe(true);
  expect(isVectorFile(file("logo.SVG", "IMAGE/SVG+XML"))).toBe(true);
  // A drag-and-drop, a rename, or an OS with no MIME database leaves this
  // empty — the case a MIME-only check would miss.
  expect(isVectorFile(file("logo.svg", ""))).toBe(true);
  expect(isVectorFile(file("logo.svgz", ""))).toBe(true);
  expect(isVectorFile(file("logo.png", "image/png"))).toBe(false);
  expect(isVectorFile(file("svg-mockup.png", "image/png"))).toBe(false);
  expect(isVectorFile(null)).toBe(false);
});

test("a raster is only ever scaled DOWN — upscaling a photo invents nothing", () => {
  // Bigger than the budget: fits to it.
  expect(rasterSize({ width: 2400, height: 1200 }, 1200)).toEqual({ w: 1200, h: 600 });
  // Smaller than the budget: left alone. This is the half that must NOT
  // change — a 300 px photo has 300 px of detail however big the canvas is.
  expect(rasterSize({ width: 300, height: 120 }, 1200)).toEqual({ w: 300, h: 120 });
});

test("a vector is rendered AT the budget, in either direction", () => {
  // The measured case: Chrome gives a viewBox-only SVG a 300 px default
  // width, which is a property of the browser and not of the artwork.
  expect(rasterSize({ width: 300, height: 120 }, 1200, { vector: true })).toEqual({ w: 1200, h: 480 });
  // And still fits down when the natural size is larger.
  expect(rasterSize({ width: 4000, height: 1000 }, 1200, { vector: true })).toEqual({ w: 1200, h: 300 });
});

test("degenerate sizes produce at least one pixel rather than a zero-size canvas", () => {
  expect(rasterSize({ width: 0, height: 0 }, 1200)).toEqual({ w: 1, h: 1 });
  expect(rasterSize({ width: 1, height: 10000 }, 480)).toEqual({ w: 1, h: 480 });
  expect(rasterSize(null, 1200)).toEqual({ w: 1, h: 1 });
});

test("loadImage prefers createImageBitmap and falls back to <img> — the path SVG needs", async () => {
  const bitmap = { width: 10, height: 5 };
  const createImageBitmap = vi.fn(async () => bitmap);
  const got = await loadImage(file("a.png", "image/png"), { createImageBitmap });
  expect(got).toBe(bitmap);
  expect(createImageBitmap).toHaveBeenCalledOnce();

  // createImageBitmap does NOT decode SVG. The fallback is not dead code.
  const revoked = [];
  class FakeImage {
    set src(v) { this._src = v; setTimeout(() => this.onload && this.onload(), 0); }
  }
  const viaImg = await loadImage(file("a.svg", "image/svg+xml"), {
    createImageBitmap: async () => { throw new Error("unsupported"); },
    Image: FakeImage,
    createObjectURL: () => "blob:x",
    revokeObjectURL: (u) => revoked.push(u),
  });
  expect(viaImg).toBeInstanceOf(FakeImage);
  expect(revoked).toEqual(["blob:x"]);
});

test("an undecodable file rejects with a message that names what DOES work", async () => {
  class FailingImage {
    set src(v) { setTimeout(() => this.onerror && this.onerror(), 0); }
  }
  const revoked = [];
  await expect(loadImage(file("a.pdf", "application/pdf"), {
    createImageBitmap: async () => { throw new Error("unsupported"); },
    Image: FailingImage,
    createObjectURL: () => "blob:y",
    revokeObjectURL: (u) => revoked.push(u),
  })).rejects.toThrow(UNREADABLE);
  // The object URL is released on the failure path too, not only on success.
  expect(revoked).toEqual(["blob:y"]);
  // "Could not read this image file." was the old text. A customer whose logo
  // is a PDF or an AI file needs the next step, not the verdict.
  expect(UNREADABLE).toMatch(/PNG, JPEG, WebP, GIF, BMP and SVG/);
  expect(UNREADABLE).toMatch(/PDF, AI or EPS/);
});
