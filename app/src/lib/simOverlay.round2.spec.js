// The simulator's round-2 drawing (lib/simOverlay.js): pending underlay drawn
// lighter and thinner, and Isolate (dim all, redraw the thread on the needle).
import { test, expect } from "vitest";
import { drawSimOverlay, drawPendingUnderlay, drawIsolate, strandTransform, threadPx, ISOLATE_WASH } from "./simOverlay.js";
import { simTimeline, underlayRuns } from "./simulate.js";
import { designToStrands } from "./strands.js";
import { THREAD_WIDTH_MM } from "./preview.js";

const S = (x, y, type = "stitch") => ({ x, y, type });
// Shape a: underlay (strands 0-1), fill (2). Then a second thread, plain.
const design = {
  colors: [{ r: 0, g: 0, b: 200 }, { r: 200, g: 0, b: 0 }],
  stitches: [S(0, 0), S(10, 0), S(20, 0), S(20, 10), S(20, 10, "trim"), S(20, 10, "color"), S(100, 100, "jump"), S(100, 100), S(110, 100), S(120, 100)],
  runs: [
    { i0: 0, i1: 2, kind: "underlay", shape: "a", role: "", block: 0 },
    { i0: 3, i1: 3, kind: "fill", shape: "a", role: "", block: 0 },
    { i0: 7, i1: 9, kind: "fill", shape: "b", role: "", block: 1 },
  ],
};
const strands = designToStrands(design);
const tl = simTimeline(design);
const ul = underlayRuns(strands, tl);
const toCanvas = (x, y) => ({ x: x * 10, y: -y * 10 });

function fakeCtx() {
  const ops = [];
  const ctx = {
    ops, globalAlpha: 1, lineWidth: 1,
    save() { ops.push(["save"]); },
    restore() { ops.push(["restore"]); },
    setLineDash(d) { ops.push(["dash", d.length]); },
    beginPath() { ops.push(["begin"]); },
    moveTo(x, y) { ops.push(["move", x, y]); },
    lineTo(x, y) { ops.push(["line", x, y]); },
    arc(x, y, r) { ops.push(["arc", x, y, r]); },
    stroke() { ops.push(["stroke", ctx.strokeStyle, ctx.lineWidth]); },
    fill() { ops.push(["fill", ctx.fillStyle]); },
    fillRect(x, y, w, h) { ops.push(["rect", x, y, w, h, ctx.fillStyle, ctx.globalAlpha]); },
    setTransform() {}, clip() {}, rect() {},
  };
  return ctx;
}

test("strandTransform is the affine map toCanvas applies, in DST units", () => {
  const { SX, SY } = strandTransform((x, y) => ({ x: 7 + 3 * x, y: 11 - 4 * y }));
  expect(SX(100)).toBeCloseTo(7 + 3 * 10);
  expect(SY(50)).toBeCloseTo(11 - 4 * 5);
  expect(threadPx(10)).toBeCloseTo(THREAD_WIDTH_MM * 10);
  expect(threadPx(0)).toBe(1.2);
});

test("pending underlay is drawn pale and thin, at its canvas position, only while pending", () => {
  const lw = 4;
  const mid = fakeCtx();
  expect(drawPendingUnderlay(mid, { strands, underlay: ul, idx: 2, toCanvas, lw })).toBe(2);
  const st = mid.ops.filter((o) => o[0] === "stroke");
  // A pale casing over the underlay's own 0.66 width, then a thin true core.
  expect(st[0][1]).toBe("rgb(158,158,234)");
  expect(st[0][2]).toBeCloseTo(lw * 0.66 + 0.75);
  expect(st[1][1]).toBe("rgb(0,0,200)");
  expect(st[1][2]).toBeLessThan(lw * 0.66);
  expect(mid.ops).toContainEqual(["move", 0, -0]);
  expect(mid.ops).toContainEqual(["line", 20, -0]);
  // Once shape a's fill has begun, the underlay is preview.js's again.
  const covered = fakeCtx();
  expect(drawPendingUnderlay(covered, { strands, underlay: ul, idx: 3, toCanvas, lw })).toBe(0);
  expect(covered.ops).toEqual([]);
});

test("drawSimOverlay marks pending underlay only when given the underlay runs", () => {
  const without = fakeCtx();
  drawSimOverlay(without, { strands, timeline: tl, idx: 1, toCanvas, showJumps: false });
  expect(without.ops.some((o) => o[0] === "stroke" && o[1] === "rgb(158,158,234)")).toBe(false);
  const withUl = fakeCtx();
  drawSimOverlay(withUl, { strands, timeline: tl, idx: 1, toCanvas, showJumps: false, underlay: ul, lw: 4 });
  const i = withUl.ops.findIndex((o) => o[0] === "stroke" && o[1] === "rgb(158,158,234)");
  const needle = withUl.ops.findIndex((o) => o[0] === "arc");
  expect(i).toBeGreaterThan(-1);
  expect(i).toBeLessThan(needle); // under the needle, never over it
});

test("isolate washes the design's box in the bed colour, then redraws only the thread on the needle", () => {
  const ctx = fakeCtx();
  const idx = 5; // block 1 has sewn 2 of its 3 strands
  const from = tl.blocks[1].start;
  // On screen this time: the flat view culls strands outside the canvas.
  const onScreen = (x, y) => ({ x: x * 10, y: 1500 - y * 10 });
  const n = drawIsolate(ctx, { strands, idx, from, toCanvas: onScreen, lw: 4, flat: true, wash: "#7b8190", bboxMm: { x0: 0, y0: 0, x1: 12, y1: 10 }, cw: 2000, ch: 2000 });
  expect(n).toBe(idx - from);
  const rect = ctx.ops.find((o) => o[0] === "rect");
  // 2 mm round the box, y flipped: x -20..140, y 1380..1520.
  expect(rect.slice(1, 7)).toEqual([-20, 1380, 160, 140, "#7b8190", ISOLATE_WASH]);
  // The redraw comes after the wash and is the current thread's strands only.
  const after = ctx.ops.slice(ctx.ops.indexOf(rect));
  const moves = after.filter((o) => o[0] === "move");
  expect(moves.length).toBe(idx - from);
  for (const m of moves) expect(m[1]).toBeGreaterThanOrEqual(100); // block 1 sews from x = 100 px
  expect(after.some((o) => o[0] === "stroke" && /200,0,0/.test(o[1]))).toBe(true);
  expect(after.some((o) => o[0] === "stroke" && /0,0,200/.test(o[1]))).toBe(false);
});

test("isolate with nothing yet sewn on the thread only washes", () => {
  const ctx = fakeCtx();
  expect(drawIsolate(ctx, { strands, idx: 3, from: 3, toCanvas, lw: 4, cw: 400, ch: 300 })).toBe(0);
  expect(ctx.ops.filter((o) => o[0] === "rect")).toEqual([["rect", 0, 0, 400, 300, "#7b8190", ISOLATE_WASH]]);
  expect(ctx.ops.some((o) => o[0] === "stroke")).toBe(false);
  expect(drawIsolate(null, { strands, idx: 3, from: 0, toCanvas })).toBe(0);
});
