import { test, expect } from "vitest";
import { drawSimOverlay, needleAt } from "./simOverlay.js";
import { simTimeline } from "./simulate.js";
import { designToStrands } from "./strands.js";

const S = (x, y, type = "stitch") => ({ x, y, type });
const design = {
  colors: [{ r: 200, g: 0, b: 0 }, { r: 0, g: 0, b: 200 }],
  stitches: [S(0, 0), S(10, 0), S(20, 0), S(20, 0, "trim"), S(20, 0, "color"), S(100, 100, "jump"), S(100, 100), S(110, 100)],
};
const strands = designToStrands(design);
const tl = simTimeline(design);
// DST units are 0.1 mm; this transform is 10 px per mm with y flipped.
const toCanvas = (x, y) => ({ x: x * 10, y: -y * 10 });

// A recording 2D-context double: just enough surface for drawSimOverlay.
function fakeCtx() {
  const ops = [];
  const ctx = {
    ops,
    save() { ops.push(["save"]); },
    restore() { ops.push(["restore"]); },
    setLineDash(d) { ops.push(["dash", d.length]); },
    beginPath() { ops.push(["begin"]); },
    moveTo(x, y) { ops.push(["move", x, y]); },
    lineTo(x, y) { ops.push(["line", x, y]); },
    arc(x, y, r) { ops.push(["arc", x, y, r]); },
    stroke() { ops.push(["stroke", ctx.strokeStyle]); },
    fill() { ops.push(["fill", ctx.fillStyle]); },
  };
  return ctx;
}
const strokes = (ctx, re) => ctx.ops.some((o) => o[0] === "stroke" && re.test(o[1]));

test("needleAt: the end of the last strand drawn, the first strand's start before any", () => {
  expect(needleAt(strands, 0)).toEqual({ x: 0, y: 0 });
  expect(needleAt(strands, 1)).toEqual({ x: 10, y: 0 });
  expect(needleAt(strands, 2)).toEqual({ x: 20, y: 0 });
  expect(needleAt(strands, 3)).toEqual({ x: 110, y: 100 });
  expect(needleAt(strands, 99)).toEqual({ x: 110, y: 100 });
  expect(needleAt([], 0)).toBe(null);
});

test("the needle is drawn at its canvas position, cored in the thread on it", () => {
  const ctx = fakeCtx();
  drawSimOverlay(ctx, { strands, timeline: tl, idx: 1, toCanvas, showJumps: false, rgb: [200, 0, 0] });
  const arcs = ctx.ops.filter((o) => o[0] === "arc");
  expect(arcs.length).toBeGreaterThan(0);
  for (const a of arcs) { expect(a[1]).toBeCloseTo(10); expect(a[2]).toBeCloseTo(0); } // (10,0) dst = 1 mm = 10 px
  expect(ctx.ops.some((o) => o[0] === "fill" && o[1] === "rgb(200,0,0)")).toBe(true);
  // Nothing has been trimmed or travelled yet, so nothing red or blue.
  expect(strokes(ctx, /220,38,38|37,99,235/)).toBe(false);
});

test("trims appear as they happen, never ahead of the needle", () => {
  const before = fakeCtx();
  drawSimOverlay(before, { strands, timeline: tl, idx: 1, toCanvas, showJumps: false });
  expect(strokes(before, /220,38,38/)).toBe(false);
  const after = fakeCtx();
  drawSimOverlay(after, { strands, timeline: tl, idx: 2, toCanvas, showJumps: false });
  expect(strokes(after, /220,38,38/)).toBe(true);
});

test("the travel in flight runs from where the needle left to where it lands", () => {
  const ctx = fakeCtx();
  drawSimOverlay(ctx, { strands, timeline: tl, idx: 2, toCanvas, showJumps: false });
  const i = ctx.ops.findIndex((o) => o[0] === "move" && o[1] === 20 && Object.is(Math.abs(o[2]), 0));
  expect(i).toBeGreaterThan(-1);
  expect(ctx.ops[i + 1]).toEqual(["line", 100, -100]);
  expect(strokes(ctx, /37,99,235,0.7/)).toBe(true);
});

test("Jumps on shows only the travel that has happened", () => {
  const early = fakeCtx();
  drawSimOverlay(early, { strands, timeline: tl, idx: 1, toCanvas, showJumps: true });
  expect(strokes(early, /37,99,235,0.45/)).toBe(false);
  const done = fakeCtx();
  drawSimOverlay(done, { strands, timeline: tl, idx: tl.total, toCanvas, showJumps: true });
  expect(strokes(done, /37,99,235,0.45/)).toBe(true);
});

test("a finished design draws no needle: the machine has stopped", () => {
  const ctx = fakeCtx();
  drawSimOverlay(ctx, { strands, timeline: tl, idx: tl.total, toCanvas, showJumps: false });
  expect(ctx.ops.some((o) => o[0] === "arc")).toBe(false);
});

test("no timeline, no transform or no context draws nothing and does not throw", () => {
  const ctx = fakeCtx();
  drawSimOverlay(ctx, { strands, timeline: null, idx: 1, toCanvas });
  drawSimOverlay(ctx, { strands, timeline: tl, idx: 1 });
  drawSimOverlay(null, { strands, timeline: tl, idx: 1, toCanvas });
  expect(ctx.ops).toEqual([]);
});
