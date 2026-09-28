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

  it("keeps dark ink on a transparent background", () => {
    // RGB 0,0,0 alpha 0 everywhere; getImageData's rendering of transparency.
    const w = 400, h = 200;
    const data = new Uint8ClampedArray(w * h * 4); // all zero
    for (let y = 100; y < 160; y++) {
      for (let x = 250; x < 350; x++) {
        const i = (y * w + x) * 4;
        data[i] = data[i + 1] = data[i + 2] = 20;
        data[i + 3] = 255;
      }
    }
    const r = proposeCrop({ data, width: w, height: h }, 80);
    expect(r.x0).toBeLessThanOrEqual(250 / w);
    expect(r.x1).toBeGreaterThanOrEqual(350 / w);
    expect(r.y0).toBeLessThanOrEqual(100 / h);
    expect(r.y1).toBeGreaterThanOrEqual(160 / h);
    expect((r.x1 - r.x0) * (r.y1 - r.y0)).toBeLessThan(0.5);
  });

  it("keeps both dark and light ink on a transparent border", () => {
    const w = 400, h = 200;
    const data = new Uint8ClampedArray(w * h * 4);
    const paint = (x0, y0, x1, y1, v) => {
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = (y * w + x) * 4;
          data[i] = data[i + 1] = data[i + 2] = v;
          data[i + 3] = 255;
        }
      }
    };
    paint(100, 80, 160, 130, 20);   // dark
    paint(170, 80, 230, 130, 240);  // light, close by
    const r = proposeCrop({ data, width: w, height: h }, 80);
    expect(r.x0).toBeLessThanOrEqual(100 / w);
    expect(r.x1).toBeGreaterThanOrEqual(230 / w);
    expect(r.y0).toBeLessThanOrEqual(80 / h);
    expect(r.y1).toBeGreaterThanOrEqual(130 / h);
  });

  it("reads ink carried only in alpha, with the same RGB under the transparency", () => {
    // becker_marine_logo.png's shape: ONE RGB colour everywhere, the shape
    // carried entirely in alpha. The transparent border's RGB is the ink's
    // own colour, so sampling it would class the ink as background.
    const width = 200, height = 200;
    const data = new Uint8ClampedArray(width * height * 4);
    for (let p = 0; p < width * height; p++) {
      data[p * 4] = 32; data[p * 4 + 1] = 31; data[p * 4 + 2] = 35; data[p * 4 + 3] = 0;
    }
    for (let y = 60; y < 140; y++) {
      for (let x = 60; x < 140; x++) data[(y * width + x) * 4 + 3] = 255;
    }
    const r = proposeCrop({ data, width, height }, 80);
    expect(r.x0).toBeLessThanOrEqual(60 / width);
    expect(r.x1).toBeGreaterThanOrEqual(140 / width);
    expect(r.y0).toBeLessThanOrEqual(60 / height);
    expect(r.y1).toBeGreaterThanOrEqual(140 / height);
    expect(r.x1 - r.x0).toBeLessThan(0.9);
    expect(r.y1 - r.y0).toBeLessThan(0.9);
  });

  it("stays sane when a large ink region touches the frame edge", () => {
    // Half of two border sides is ink here. A per-channel MEAN over the
    // border lands ~59 units off white -- past INK_TOLERANCE -- so the white
    // frame itself reads as ink and the proposal is the whole frame. A
    // median ignores a minority of edge-touching ink.
    const img = art(300, 300, [[0, 0, 150, 150]]);
    const r = proposeCrop(img, 80);
    expect(r.x0).toBeLessThanOrEqual(0.05);
    expect(r.y0).toBeLessThanOrEqual(0.05);
    expect(r.x1).toBeGreaterThanOrEqual(150 / 300);
    expect(r.y1).toBeGreaterThanOrEqual(150 / 300);
    expect(r.x1 - r.x0).toBeLessThan(0.7);
    expect(r.y1 - r.y0).toBeLessThan(0.7);
  });

  it("merges marks about 3 mm apart into one proposal", () => {
    // 400 px over 80 mm = 5 px/mm, so a 15 px gap is 3 mm.
    const img = art(400, 200, [[60, 60, 160, 140], [175, 60, 275, 140]]);
    const r = proposeCrop(img, 80);
    expect(r.x0).toBeLessThanOrEqual(60 / 400);
    expect(r.x1).toBeGreaterThanOrEqual(275 / 400);
  });

  it("drops a much lighter mark ~20 mm away", () => {
    // 100 px gap = 20 mm at 5 px/mm.
    const img = art(600, 200, [[20, 40, 60, 80], [160, 40, 360, 160]]);
    const r = proposeCrop(img, 120);
    expect(r.x0).toBeGreaterThan(100 / 600);
    expect(r.x1).toBeGreaterThanOrEqual(360 / 600);
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
});
