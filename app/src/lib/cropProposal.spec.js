import { describe, it, expect } from "vitest";
import { proposeCrop } from "./cropProposal.js";

/** A white frame with dark rectangles painted into it. */
function art(width, height, rects) {
  const data = new Uint8ClampedArray(width * height * 4).fill(255);
  for (const [x0, y0, x1, y1] of rects) {
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const i = (y * width + x) * 4;
        data[i] = data[i + 1] = data[i + 2] = 20;
      }
    }
  }
  return { data, width, height };
}

describe("proposeCrop", () => {
  it("returns the full frame when ink already fills it", () => {
    const img = art(200, 200, [[10, 10, 190, 190]]);
    const r = proposeCrop(img, 80);
    expect(r.x1 - r.x0).toBeGreaterThan(0.9);
    expect(r.y1 - r.y0).toBeGreaterThan(0.9);
  });

  it("picks the dominant cluster, not the bbox of all ink", () => {
    // A phone screenshot in miniature: a thin chrome band top and bottom,
    // and a big logo in the middle. Bbox-of-all-ink would span the whole
    // frame; the dominant cluster must not.
    const img = art(200, 600, [
      [10, 4, 190, 14],      // top chrome
      [40, 250, 160, 350],   // logo
      [10, 586, 190, 596],   // bottom chrome
    ]);
    const r = proposeCrop(img, 80);
    expect(r.y0).toBeGreaterThan(0.25);
    expect(r.y1).toBeLessThan(0.75);
    expect(r.y1 - r.y0).toBeLessThan(0.5);
  });

  it("keeps the whole of the chosen cluster", () => {
    const img = art(400, 200, [[100, 60, 300, 140]]);
    const r = proposeCrop(img, 80);
    expect(r.x0).toBeLessThanOrEqual(100 / 400);
    expect(r.x1).toBeGreaterThanOrEqual(300 / 400);
    expect(r.y0).toBeLessThanOrEqual(60 / 200);
    expect(r.y1).toBeGreaterThanOrEqual(140 / 200);
  });

  it("returns the full frame when there is no ink at all", () => {
    const r = proposeCrop(art(100, 100, []), 80);
    expect(r).toEqual({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });

  it("always returns fractions inside the unit square", () => {
    const img = art(200, 200, [[0, 0, 40, 40]]);
    const r = proposeCrop(img, 80);
    for (const v of [r.x0, r.y0, r.x1, r.y1]) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
    expect(r.x1).toBeGreaterThan(r.x0);
    expect(r.y1).toBeGreaterThan(r.y0);
  });

  it("finds ink under a fully transparent border, without inverting", () => {
    // becker_marine_logo.png shape: one RGB colour everywhere, the shape
    // carried entirely in alpha. A transparent border sampled for its RGB
    // (ignoring alpha) would estimate a near-black background and invert
    // ink detection across the whole image. The border here is fully
    // transparent, so the correct fallback is white -- against which the
    // opaque dark block reads as ink, not background.
    const width = 200, height = 200;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let p = 0; p < width * height; p++) {
      const i = p * 4;
      data[i] = 32; data[i + 1] = 31; data[i + 2] = 35; data[i + 3] = 0;
    }
    for (let y = 60; y < 140; y++) {
      for (let x = 60; x < 140; x++) {
        data[(y * width + x) * 4 + 3] = 255; // same RGB, now opaque
      }
    }
    const r = proposeCrop({ data, width, height }, 80);
    expect(r.x0).toBeLessThanOrEqual(60 / width);
    expect(r.x1).toBeGreaterThanOrEqual(140 / width);
    expect(r.y0).toBeLessThanOrEqual(60 / height);
    expect(r.y1).toBeGreaterThanOrEqual(140 / height);
    // Not the whole frame -- that would mean the block was never detected
    // as ink at all (inverted against a near-black background estimate).
    expect(r.x1 - r.x0).toBeLessThan(0.9);
    expect(r.y1 - r.y0).toBeLessThan(0.9);
  });

  it("stays sane when a large ink region touches the frame edge", () => {
    // A per-channel MEAN over the border would be skewed dark enough by
    // this much edge-touching ink to push the background estimate more
    // than INK_TOLERANCE off white, misclassifying most of the rest of the
    // white frame as ink too. The median must not.
    const img = art(300, 300, [[0, 0, 150, 150]]);
    const r = proposeCrop(img, 80);
    expect(r.x0).toBeLessThanOrEqual(0.05);
    expect(r.y0).toBeLessThanOrEqual(0.05);
    expect(r.x1).toBeGreaterThanOrEqual(150 / 300);
    expect(r.y1).toBeGreaterThanOrEqual(150 / 300);
    // Sane crop, not the whole (300x300) frame.
    expect(r.x1 - r.x0).toBeLessThan(0.7);
    expect(r.y1 - r.y0).toBeLessThan(0.7);
  });
});
