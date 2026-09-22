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

// ---- what the panel SENDS (2026-09-20) --------------------------------------
//
// The file itself, when the service's decoder can read it and it is inside
// the service's limits; the canvas PNG otherwise. The reasons are named so a
// caller can say which one applied.
import { uploadPlan, SERVICE_DECODES } from "./rasterize.js";

const img = (width, height) => ({ width, height });

test("a raster the service decodes goes up as the file itself", () => {
  expect(uploadPlan({ name: "logo.png", type: "image/png", size: 40_000 }, img(1400, 316))).toEqual({ asIs: true, reason: "", type: "image/png" });
  expect(uploadPlan({ name: "logo.webp", type: "image/webp", size: 90_000 }, img(2500, 1345)).asIs).toBe(true);
  expect(uploadPlan({ name: "photo.JPG", type: "image/jpeg", size: 3_000_000 }, img(4000, 3000)).asIs).toBe(true);
  // A drag-and-drop or a bare OS leaves the MIME empty: the extension decides.
  expect(uploadPlan({ name: "logo.jpeg", type: "", size: 10 }, img(10, 10))).toEqual({ asIs: true, reason: "", type: "image/jpeg" });
  for (const t of ["image/png", "image/jpeg", "image/webp", "image/bmp"]) expect(SERVICE_DECODES.has(t)).toBe(true);
});

test("a vector or a GIF keeps the canvas path — only a browser rasterises those", () => {
  expect(uploadPlan({ name: "logo.svg", type: "image/svg+xml", size: 10 }, img(300, 150)).reason).toBe("vector");
  expect(uploadPlan({ name: "logo.svg", type: "", size: 10 }, img(300, 150)).reason).toBe("vector");
  expect(uploadPlan({ name: "anim.gif", type: "image/gif", size: 10 }, img(300, 150)).reason).toBe("format");
  expect(uploadPlan({ name: "mystery", type: "", size: 10 }, img(300, 150)).reason).toBe("format");
  // A GIF is not even rescued by its bytes being small: the service cannot
  // decode it at all.
  expect(uploadPlan({ name: "anim.gif", type: "image/gif", size: 10 }, img(300, 150)).asIs).toBe(false);
});

test("the service's limits decide, from /health when it has answered and from its own constants before", () => {
  const big = { name: "scan.png", type: "image/png", size: 13 * 1024 * 1024 };
  expect(uploadPlan(big, img(1000, 1000)).reason).toBe("bytes");
  expect(uploadPlan({ ...big, size: 1000 }, img(7000, 6000)).reason).toBe("pixels");
  // /health's numbers win over the defaults, in both directions.
  expect(uploadPlan(big, img(1000, 1000), { max_upload_bytes: 20 * 1024 * 1024, max_pixels: 40_000_000 }).asIs).toBe(true);
  expect(uploadPlan({ ...big, size: 1000 }, img(1000, 1000), { max_upload_bytes: 12 * 1024 * 1024, max_pixels: 500_000 }).reason).toBe("pixels");
  // A partial limits object still gets the other default.
  expect(uploadPlan({ ...big, size: 1000 }, img(7000, 6000), { max_upload_bytes: 1 }).reason).toBe("bytes");
});

test("a JPEG the browser rotated on decode keeps the canvas path — the service ignores EXIF orientation", async () => {
  const { jpegDimensions } = await import("./rasterize.js");
  // SOI, then a SOF0 declaring 50 high x 100 wide (the header is what cv2 decodes to).
  const sof = (h, w) => new Uint8Array([0xff, 0xd8, 0xff, 0xe1, 0x00, 0x04, 0x00, 0x00,   // an APP1 segment to step over
                                        0xff, 0xc0, 0x00, 0x11, 0x08, h >> 8, h & 255, w >> 8, w & 255, 0x03]);
  expect(jpegDimensions(sof(50, 100))).toEqual({ height: 50, width: 100 });
  expect(jpegDimensions(new Uint8Array([0x89, 0x50, 0x4e, 0x47]))).toBeNull();     // a PNG
  expect(jpegDimensions(new Uint8Array([0xff, 0xd8, 0xff, 0xd9]))).toBeNull();     // no SOF before EOI
  const jpg = { name: "phone.jpg", type: "image/jpeg", size: 1000 };
  // Upright: the bitmap is the header's size -> the file goes as it is.
  expect(uploadPlan(jpg, img(100, 50), null, sof(50, 100)).asIs).toBe(true);
  // Rotated by EXIF: the browser's bitmap is 50 x 100 against a 100 x 50 header.
  expect(uploadPlan(jpg, img(50, 100), null, sof(50, 100))).toEqual({ asIs: false, reason: "orientation", type: "image/jpeg" });
  // Without the bytes the cheaper checks alone decide (the panel's first ask).
  expect(uploadPlan(jpg, img(50, 100)).asIs).toBe(true);
  // A PNG is never orientation-checked: it carries no EXIF rotation the browser applies.
  expect(uploadPlan({ name: "a.png", type: "image/png", size: 10 }, img(50, 100), null, sof(50, 100)).asIs).toBe(true);
});
