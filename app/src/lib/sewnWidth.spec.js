import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { shrinkSatinStrands, SEWN_WIDTH_FLOOR_MM } from "./strands.js";
import { THREAD_WIDTH_MM } from "./preview.js";

// sewnWidth.js reaches the fabric table through the engine global, so the
// engine is loaded the way emb.spec.js loads it and the module is imported
// after (a static import would throw before beforeAll ran).
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
});

// A satin column 1.3 mm wide (rails at y=0 and y=1.3), crossed at 0.4 mm.
function column(kind) {
  const s = [];
  for (let i = 0; i < 4; i++) {
    const x = i * 0.4;
    s.push({ x0: x, y0: 0, x1: x, y1: 1.3, rgb: [0, 0, 0], kind, role: "", shape: "S1" });
    s.push({ x0: x, y0: 1.3, x1: x + 0.4, y1: 0, rgb: [0, 0, 0], kind, role: "", shape: "S1" });
  }
  return s;
}

test("a satin strand loses the pull at each end, along its own direction", () => {
  const out = shrinkSatinStrands(column("satin"), 0.3);
  const cross = out[0];
  expect(cross.x0).toBeCloseTo(0, 6);
  expect(cross.y0).toBeCloseTo(0.3, 6);
  expect(cross.y1).toBeCloseTo(1.0, 6);
  // the lean leg shortens along ITS direction, so its x moves too
  const lean = out[1];
  const len = Math.hypot(0.4, 1.3);
  expect(Math.hypot(lean.x1 - lean.x0, lean.y1 - lean.y0)).toBeCloseTo(len - 0.6, 6);
  expect(lean.y0).toBeCloseTo(1.3 - 0.3 * (1.3 / len), 6);
});

test("fill, run, underlay, travel and kind-less strands are untouched, and the input is not mutated", () => {
  for (const kind of ["fill", "run", "underlay", "travel", "stitch"]) {
    const src = column(kind);
    const before = JSON.stringify(src);
    const out = shrinkSatinStrands(src, 0.3);
    expect(JSON.stringify(out)).toBe(before);
    expect(JSON.stringify(src)).toBe(before);
  }
  const src = column("satin");
  const before = JSON.stringify(src);
  shrinkSatinStrands(src, 0.3);
  expect(JSON.stringify(src)).toBe(before);
});

test("a cross too short to give up two pulls keeps a thread width, centred", () => {
  const s = [{ x0: 0, y0: 0, x1: 0, y1: 0.9, rgb: [0, 0, 0], kind: "satin", role: "", shape: "S1" }];
  const out = shrinkSatinStrands(s, 0.3);
  // 0.9 - 0.6 = 0.3 < the 0.4 floor: shrink to the floor instead, symmetric
  expect(out[0].y0).toBeCloseTo(0.25, 6);
  expect(out[0].y1).toBeCloseTo(0.65, 6);
});

test("the floor is the preview's thread width, kept in step by hand", () => {
  expect(SEWN_WIDTH_FLOOR_MM).toBe(THREAD_WIDTH_MM);
});

test("no pull, or no strands, is the identity", () => {
  const src = column("satin");
  expect(shrinkSatinStrands(src, 0)).toBe(src);
  expect(shrinkSatinStrands([], 0.3)).toEqual([]);
  expect(shrinkSatinStrands(null, 0.3)).toEqual([]);
});

test("the pull in force comes from the project's garment, profile applied", async () => {
  const { sewnPullFor } = await import("./sewnWidth.js");
  // pique_knit is 0.3 mm; the profile's delta rides on top, clamped by fabrics.js
  expect(sewnPullFor({ garmentId: "left_chest" })).toBeCloseTo(0.3, 6);
  expect(sewnPullFor({ garmentId: "left_chest", fabricProfile: { pull_comp_delta_mm: 0.1 } })).toBeCloseTo(0.4, 6);
  expect(sewnPullFor({ garmentId: "patch" })).toBeCloseTo(0.2, 6);
  expect(sewnPullFor(null)).toBe(0);
});

test("the toggle has something to act on only when the design carries satin spans", async () => {
  const { hasSatinSpans } = await import("./sewnWidth.js");
  expect(hasSatinSpans({ stitches: [], runs: [{ i0: 0, i1: 3, kind: "satin", shape: "S1", role: "", block: 0 }] })).toBe(true);
  expect(hasSatinSpans({ stitches: [], runs: [{ i0: 0, i1: 3, kind: "fill", shape: "S1", role: "", block: 0 }] })).toBe(false);
  expect(hasSatinSpans({ stitches: [] })).toBe(false);
  expect(hasSatinSpans(null)).toBe(false);
});
