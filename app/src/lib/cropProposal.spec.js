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
});
