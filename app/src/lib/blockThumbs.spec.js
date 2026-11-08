// Block thumbnails: the pure parts and the geometry contract, against a
// recording canvas double (jsdom has no 2d context). The pixel-level claim --
// ink only inside the block's bbox + 1 mm, built in <= 150 ms on a 22k-stitch
// file -- is measured in a real browser by e2e/design-block-thumbs.spec.js.
import { expect, test } from "vitest";
import { splitBlocks, blockStitchCounts, buildBlockThumbs, BBOX_MARGIN_MM } from "./blockThumbs.js";

const S = (x, y) => ({ x, y, type: "stitch" });
const C = () => ({ x: 0, y: 0, type: "color" });
// Two blocks: A at x 0..100 (10 mm), B at x 200..300; a jump inside A far
// away that must NOT count toward A's bbox (travel is not ink).
const design = {
  stitches: [S(0, 0), S(100, 0), S(100, 50), { x: 900, y: 900, type: "jump" }, S(0, 50), C(), S(200, 0), S(300, 0), S(300, 50)],
};

function recordingCanvas() {
  const calls = [];
  const ctx = new Proxy({}, {
    get(_t, k) {
      if (k === "calls") return calls;
      return (...a) => { calls.push([String(k), ...a]); };
    },
    set(_t, k, v) { calls.push(["set:" + String(k), v]); return true; },
  });
  return { width: 0, height: 0, getContext: () => ctx, calls };
}

test("splitBlocks cuts at colour records and counts only stitch records", () => {
  const b = splitBlocks(design);
  expect(b.map((x) => x.count)).toEqual([4, 3]);
  expect(b[0].bbox).toEqual({ x0: 0, y0: 0, x1: 100, y1: 50 }); // the jump at 900,900 is travel
  expect(b[1].bbox).toEqual({ x0: 200, y0: 0, x1: 300, y1: 50 });
});

test("blockStitchCounts agrees with splitBlocks and needs no canvas", () => {
  expect(blockStitchCounts(design)).toEqual([4, 3]);
  expect(blockStitchCounts({ stitches: [] })).toEqual([0]);
  expect(blockStitchCounts(null)).toEqual([0]);
});

test("one thumbnail per block, each with its count and bbox in mm", () => {
  const th = buildBlockThumbs(design, { colors: [[255, 0, 0], [0, 0, 255]], makeCanvas: recordingCanvas });
  expect(th).toHaveLength(2);
  expect(th.map((t) => t.count)).toEqual([4, 3]);
  expect(th[0].bboxMm).toEqual({ x0: 0, y0: 0, x1: 10, y1: 5 });
  expect(th.every((t) => t.canvas)).toBe(true);
});

test("each block's strokes are clipped to its bbox plus 1 mm, and only to that", () => {
  const dpr = 2, W = 64, H = 32;
  const th = buildBlockThumbs(design, { colors: [[255, 0, 0], [0, 0, 255]], width: W, height: H, dpr, makeCanvas: recordingCanvas, silhouette: false, background: false });
  // Replay the lib's one shared fit: extent x 0..300, y 0..50.
  const bw = W * dpr, bh = H * dpr, pad = 3 * dpr;
  const s = Math.min((bw - 2 * pad) / 300, (bh - 2 * pad) / 50);
  const SX = (x) => bw / 2 + (x - 150) * s, SY = (y) => bh / 2 - (y - 25) * s;
  const m = BBOX_MARGIN_MM * 10;
  expect(BBOX_MARGIN_MM).toBe(1);
  const boxes = [{ x0: 0, y0: 0, x1: 100, y1: 50 }, { x0: 200, y0: 0, x1: 300, y1: 50 }];
  th.forEach((t, i) => {
    const calls = t.canvas.calls;
    const rect = calls.find((c) => c[0] === "rect");
    const b = boxes[i];
    expect(rect[1]).toBeCloseTo(SX(b.x0 - m), 6);
    expect(rect[2]).toBeCloseTo(SY(b.y1 + m), 6);
    expect(rect[3]).toBeCloseTo(SX(b.x1 + m) - SX(b.x0 - m), 6);
    expect(rect[4]).toBeCloseTo(SY(b.y0 - m) - SY(b.y1 + m), 6);
    // clip() is issued after the rect and BEFORE any stroke.
    const iclip = calls.findIndex((c) => c[0] === "clip");
    const istroke = calls.findIndex((c) => c[0] === "stroke");
    expect(iclip).toBeGreaterThan(-1);
    expect(istroke).toBeGreaterThan(iclip);
  });
});

test("the silhouette is optional and the tile can be left transparent", () => {
  const plain = buildBlockThumbs(design, { colors: [[255, 0, 0], [0, 0, 255]], makeCanvas: recordingCanvas, silhouette: false, background: false });
  for (const t of plain) {
    expect(t.canvas.calls.some((c) => c[0] === "fillRect")).toBe(false);
    expect(t.canvas.calls.some((c) => c[0] === "drawImage")).toBe(false);
  }
  const full = buildBlockThumbs(design, { colors: [[255, 0, 0], [0, 0, 255]], makeCanvas: recordingCanvas });
  expect(full[0].canvas.calls.some((c) => c[0] === "fillRect")).toBe(true);
  // faint silhouette, then the block's own layer on top of it
  expect(full[0].canvas.calls.filter((c) => c[0] === "drawImage")).toHaveLength(2);
});

test("an empty block yields a count of 0 and no ink; no 2d context yields canvas null", () => {
  const withEmpty = { stitches: [S(0, 0), S(10, 0), C()] };
  const th = buildBlockThumbs(withEmpty, { colors: [[0, 0, 0], [0, 0, 0]], makeCanvas: recordingCanvas, silhouette: false, background: false });
  expect(th.map((t) => t.count)).toEqual([2, 0]);
  expect(th[1].bboxMm).toBeNull();
  expect(th[1].canvas.calls.some((c) => c[0] === "stroke")).toBe(false);

  const none = buildBlockThumbs(design, { colors: [], makeCanvas: () => ({ getContext: () => null }) });
  expect(none.map((t) => t.canvas)).toEqual([null, null]);
});
