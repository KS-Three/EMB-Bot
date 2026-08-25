import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "./testFonts.js";
import { shapeIssues, isValidShape, CANVAS_W, CANVAS_H, MAX_SHAPE_POINTS } from "./manualShapes.js";

// Same engine-loading convention as flatten.spec.js / imageRegions.spec.js:
// manualTrace.js sits on the same app/src/lib -> src/*.js vanilla-engine
// bridge (via emb.js) as those files, so tests need the same real
// EMB.traceRegions / EMB.simplify / EMB.medianCut etc. loaded before import.
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();
});

// ---- Fixture helpers -------------------------------------------------

function makeCanvas(w, h) {
  return new Uint8ClampedArray(w * h * 4);
}

function fillRect(rgba, w, x0, y0, x1, y1, rgb) {
  for (let y = y0; y < y1; y++) {
    for (let x = x0; x < x1; x++) {
      const o = (y * w + x) * 4;
      rgba[o] = rgb[0];
      rgba[o + 1] = rgb[1];
      rgba[o + 2] = rgb[2];
      rgba[o + 3] = 255;
    }
  }
}

const WHITE = [255, 255, 255];
const RED = [200, 30, 30];
const BLUE = [30, 30, 200];
const GREEN = [10, 150, 10];

// ---- traceShapesFromRGBA ------------------------------------------------

test("traceShapesFromRGBA: two touching, differently-colored solid regions trace as two separate shapes, never merged", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 20, h = 20;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 20, 20, WHITE);
  fillRect(rgba, w, 2, 2, 10, 18, RED); // touches the blue square along x=10
  fillRect(rgba, w, 10, 2, 18, 18, BLUE);
  const { shapes, warnings } = traceShapesFromRGBA(rgba, w, h, { nColors: 2, removeBg: true });
  expect(shapes).toHaveLength(2);
  const colors = shapes.map((s) => s.colorRgb).sort((a, b) => a[2] - b[2]);
  expect(colors).toEqual([RED, BLUE]);
  expect(warnings).toEqual([]);
});

test("traceShapesFromRGBA: two disjoint same-color blobs trace as two separate shapes with the same colorRgb", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 30, h = 20;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 30, 20, WHITE);
  fillRect(rgba, w, 2, 2, 10, 10, RED);
  fillRect(rgba, w, 20, 10, 28, 18, RED); // far apart, background between
  const { shapes } = traceShapesFromRGBA(rgba, w, h, { nColors: 1, removeBg: true });
  expect(shapes).toHaveLength(2);
  expect(shapes[0].colorRgb).toEqual(RED);
  expect(shapes[1].colorRgb).toEqual(RED);
});

test("traceShapesFromRGBA: an annulus (ring with a same-background-color hole) traces as ONE shape, the hole is dropped with a warning", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 24, h = 24;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 24, 24, WHITE);
  fillRect(rgba, w, 4, 4, 20, 20, GREEN); // the ring
  fillRect(rgba, w, 9, 9, 15, 15, WHITE); // the hole, same color as background
  const { shapes, warnings } = traceShapesFromRGBA(rgba, w, h, { nColors: 1, removeBg: true });
  expect(shapes).toHaveLength(1); // outer boundary only, hole is NOT its own shape
  expect(shapes[0].colorRgb).toEqual(GREEN);
  expect(warnings.some((m) => m.includes("interior hole"))).toBe(true);
});

test("traceShapesFromRGBA: a clean solid blob plus scattered single-pixel color speckle is despeckled, not traced as spurious tiny shapes", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 40, h = 40;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 40, 40, WHITE);
  fillRect(rgba, w, 5, 5, 20, 20, RED); // the real blob
  // JPEG-artifact-style scattered single-pixel noise, same color, isolated
  // (far enough from the blob and from each other to trace as their own
  // 1x1 components rather than merging into the blob).
  for (const [x, y] of [[30, 2], [35, 10], [25, 30], [38, 38], [2, 35]]) {
    const o = (y * w + x) * 4;
    rgba[o] = RED[0]; rgba[o + 1] = RED[1]; rgba[o + 2] = RED[2]; rgba[o + 3] = 255;
  }
  const { shapes } = traceShapesFromRGBA(rgba, w, h, { nColors: 1, removeBg: true });
  expect(shapes).toHaveLength(1); // only the real blob survives despeckle
});

test("traceShapesFromRGBA: a blank/all-background image produces zero shapes without throwing", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 20, h = 20;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 20, 20, WHITE);
  expect(() => traceShapesFromRGBA(rgba, w, h, { nColors: 3, removeBg: true })).not.toThrow();
  const { shapes, warnings } = traceShapesFromRGBA(rgba, w, h, { nColors: 3, removeBg: true });
  expect(shapes).toEqual([]);
  expect(warnings).toEqual([]);
});

test("traceShapesFromRGBA: a simple 2-color synthetic image produces one shape per color", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 24, h = 16;
  const rgba = makeCanvas(w, h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const o = (y * w + x) * 4;
      const c = x < w / 2 ? RED : BLUE;
      rgba[o] = c[0]; rgba[o + 1] = c[1]; rgba[o + 2] = c[2]; rgba[o + 3] = 255;
    }
  }
  const { shapes } = traceShapesFromRGBA(rgba, w, h, { nColors: 2, removeBg: false });
  expect(shapes).toHaveLength(2);
});

test("traceShapesFromRGBA: never truncates a color's shapes silently — hitting maxShapesPerColor caps the output and emits a warning", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const w = 60, h = 10;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 60, 10, WHITE);
  // Four disjoint same-color blobs, cap set to 3.
  fillRect(rgba, w, 0, 2, 4, 8, RED);
  fillRect(rgba, w, 8, 2, 12, 8, RED);
  fillRect(rgba, w, 16, 2, 20, 8, RED);
  fillRect(rgba, w, 24, 2, 28, 8, RED);
  const { shapes, warnings } = traceShapesFromRGBA(rgba, w, h, { nColors: 1, removeBg: true, maxShapesPerColor: 3 });
  expect(shapes).toHaveLength(3);
  expect(warnings.some((m) => m.includes("3-shape cap"))).toBe(true);
});

test("traceShapesFromRGBA: every returned shape passes manualShapes.js's own validation with zero issues (regression guard)", async () => {
  const { traceShapesFromRGBA } = await import("./manualTrace.js");
  const fixtures = [];

  {
    const w = 20, h = 20;
    const rgba = makeCanvas(w, h);
    fillRect(rgba, w, 0, 0, 20, 20, WHITE);
    fillRect(rgba, w, 2, 2, 10, 18, RED);
    fillRect(rgba, w, 10, 2, 18, 18, BLUE);
    fixtures.push(traceShapesFromRGBA(rgba, w, h, { nColors: 2, removeBg: true }));
  }
  {
    const w = 24, h = 24;
    const rgba = makeCanvas(w, h);
    fillRect(rgba, w, 0, 0, 24, 24, WHITE);
    fillRect(rgba, w, 4, 4, 20, 20, GREEN);
    fillRect(rgba, w, 9, 9, 15, 15, WHITE);
    fixtures.push(traceShapesFromRGBA(rgba, w, h, { nColors: 1, removeBg: true }));
  }

  let checked = 0;
  for (const { shapes } of fixtures) {
    for (const shape of shapes) {
      expect(shapeIssues(shape.points)).toEqual([]);
      expect(isValidShape(shape.points)).toBe(true);
      checked++;
    }
  }
  expect(checked).toBeGreaterThan(0); // sanity: the guard actually exercised some shapes
});

// ---- rescaleTracedShapes --------------------------------------------------

test("rescaleTracedShapes: fits a portrait source into the canvas without stretching (letterboxed, aspect preserved)", async () => {
  const { rescaleTracedShapes } = await import("./manualTrace.js");
  const srcW = 100, srcH = 400; // tall portrait
  const shape = { points: [{ x: 0, y: 0 }, { x: srcW, y: 0 }, { x: srcW, y: srcH }, { x: 0, y: srcH }], curves: {} };
  const [scaled] = rescaleTracedShapes([shape], srcW, srcH, CANVAS_W, CANVAS_H, 12);
  const xs = scaled.points.map((p) => p.x);
  const ys = scaled.points.map((p) => p.y);
  const drawnW = Math.max(...xs) - Math.min(...xs);
  const drawnH = Math.max(...ys) - Math.min(...ys);
  // Aspect ratio preserved (no stretch): drawn W/H matches source W/H.
  expect(drawnW / drawnH).toBeCloseTo(srcW / srcH, 3);
  // Height-limited (portrait into a wider canvas) so it should hug the full
  // available height, not the full available width.
  expect(drawnH).toBeCloseTo(CANVAS_H - 2 * 12, 1);
  expect(drawnW).toBeLessThan(CANVAS_W - 2 * 12);
});

test("rescaleTracedShapes: applies the identical transform to curve control points as to anchor points", async () => {
  const { rescaleTracedShapes } = await import("./manualTrace.js");
  const srcW = 200, srcH = 200;
  const a = { x: 0, y: 0 }, c = { x: 100, y: 0 }, control = { x: 50, y: -30 };
  const shape = { points: [a, c, { x: 100, y: 100 }], curves: { 0: control } };
  const [scaled] = rescaleTracedShapes([shape], srcW, srcH, CANVAS_W, CANVAS_H, 12);

  // Derive the actual scale+offset the implementation used from its OWN
  // output on the anchor points (whose source values we know independently)
  // rather than re-deriving the margin/fit formula ourselves — that would
  // just test the formula against itself. This isolates the real claim:
  // the curve control point obeys the exact same transform as the anchors.
  const scaleX = (scaled.points[1].x - scaled.points[0].x) / (c.x - a.x);
  const offsetX = scaled.points[0].x - a.x * scaleX;
  const scaleY = (scaled.points[2].y - scaled.points[0].y) / (100 - a.y);
  const offsetY = scaled.points[0].y - a.y * scaleY;

  expect(scaled.curves[0].x).toBeCloseTo(control.x * scaleX + offsetX, 6);
  expect(scaled.curves[0].y).toBeCloseTo(control.y * scaleY + offsetY, 6);
});

test("rescaleTracedShapes: two shapes from the same trace keep their original relative position to each other", async () => {
  const { rescaleTracedShapes } = await import("./manualTrace.js");
  const srcW = 300, srcH = 200;
  // A small square fully inside a larger square, offset toward one corner.
  const outer = { points: [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 200 }, { x: 0, y: 200 }], curves: {} };
  const inner = { points: [{ x: 50, y: 50 }, { x: 100, y: 50 }, { x: 100, y: 100 }, { x: 50, y: 100 }], curves: {} };
  const [scaledOuter, scaledInner] = rescaleTracedShapes([outer, inner], srcW, srcH, CANVAS_W, CANVAS_H, 12);

  // The inner square's rescaled bbox must stay fully within the outer's.
  const bbox = (pts) => ({
    minX: Math.min(...pts.map((p) => p.x)), maxX: Math.max(...pts.map((p) => p.x)),
    minY: Math.min(...pts.map((p) => p.y)), maxY: Math.max(...pts.map((p) => p.y)),
  });
  const oBox = bbox(scaledOuter.points);
  const iBox = bbox(scaledInner.points);
  expect(iBox.minX).toBeGreaterThan(oBox.minX);
  expect(iBox.maxX).toBeLessThan(oBox.maxX);
  expect(iBox.minY).toBeGreaterThan(oBox.minY);
  expect(iBox.maxY).toBeLessThan(oBox.maxY);
});

// ---- spansForSimplifiedRing ------------------------------------------------

// Hand-built pentagon-ish raw ring (cyclic: A-B-C-D-E-A). Coordinates aren't
// geometrically meaningful — only the ring ORDER matters for this function.
const A = { x: 0, y: 0 }, B = { x: 10, y: 0 }, C = { x: 20, y: 0 }, D = { x: 20, y: 10 }, E = { x: 10, y: 10 };
const PENTAGON = [A, B, C, D, E];

test("spansForSimplifiedRing: correctly maps a simple hand-built case", async () => {
  const { spansForSimplifiedRing } = await import("./manualTrace.js");
  // Simplified ring drops B and D, keeping every other vertex.
  const spans = spansForSimplifiedRing(PENTAGON, [A, C, E]);
  expect(spans).toEqual([[B], [D], []]); // A->C has B; C->E has D; E->A (wrap) has nothing
});

test("spansForSimplifiedRing: correctly handles the wraparound span back to the first vertex", async () => {
  const { spansForSimplifiedRing } = await import("./manualTrace.js");
  // Simplified ring keeps only B and D — the wraparound segment D->B must
  // walk past E and A (cyclically) to collect its interior points.
  const spans = spansForSimplifiedRing(PENTAGON, [B, D]);
  expect(spans).toEqual([[C], [E, A]]);
});

test("spansForSimplifiedRing: an empty simplified ring or raw ring returns no throw and an empty result", async () => {
  const { spansForSimplifiedRing } = await import("./manualTrace.js");
  expect(spansForSimplifiedRing(PENTAGON, [])).toEqual([]);
  expect(spansForSimplifiedRing([], PENTAGON)).toEqual(PENTAGON.map(() => []));
});

// ---- maxDeviationPoint -----------------------------------------------------

test("maxDeviationPoint: returns ~zero deviation for an already-straight raw span", async () => {
  const { maxDeviationPoint } = await import("./manualTrace.js");
  const a = { x: 0, y: 0 }, c = { x: 10, y: 0 };
  const { dist } = maxDeviationPoint([{ x: 2, y: 0 }, { x: 5, y: 0 }, { x: 8, y: 0 }], a, c);
  expect(dist).toBeCloseTo(0, 9);
});

test("maxDeviationPoint: finds the correct point/distance on a hand-built triangular bulge", async () => {
  const { maxDeviationPoint } = await import("./manualTrace.js");
  const a = { x: 0, y: 0 }, c = { x: 10, y: 0 };
  // (5,3) sits 3px perpendicular off the a-c chord (the x-axis) — the exact
  // answer is known by hand: perpendicular distance from a point to the
  // x-axis is just its y-coordinate.
  const { point, dist } = maxDeviationPoint([{ x: 3, y: 1 }, { x: 5, y: 3 }, { x: 7, y: 1 }], a, c);
  expect(point).toEqual({ x: 5, y: 3 });
  expect(dist).toBeCloseTo(3, 9);
});

test("maxDeviationPoint: a zero-length/degenerate span (no interior points) returns a clean zero result, not a throw", async () => {
  const { maxDeviationPoint } = await import("./manualTrace.js");
  const a = { x: 0, y: 0 }, c = { x: 10, y: 0 };
  expect(() => maxDeviationPoint([], a, c)).not.toThrow();
  const { point, dist } = maxDeviationPoint([], a, c);
  expect(dist).toBe(0);
  expect(point).toEqual({ x: 5, y: 0 }); // chord midpoint
});

test("maxDeviationPoint: a degenerate a===c chord (zero-length) falls back to plain distance from a, not a divide-by-zero", async () => {
  const { maxDeviationPoint } = await import("./manualTrace.js");
  const a = { x: 5, y: 5 }, c = { x: 5, y: 5 };
  const { dist } = maxDeviationPoint([{ x: 8, y: 9 }], a, c);
  expect(dist).toBeCloseTo(5, 9); // hypot(3,4) = 5
});

// ---- fitCurvesForRing -------------------------------------------------

test("fitCurvesForRing: a straight raw run produces NO curve entry at all for that segment (absent, not present-and-zero)", async () => {
  const { fitCurvesForRing } = await import("./manualTrace.js");
  // Raw ring: a perfect square with one extra collinear midpoint on the top
  // edge — that midpoint is a straight run, not a bulge.
  const raw = [{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  const simplified = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  const { curves } = fitCurvesForRing(raw, simplified, 1);
  expect(Object.prototype.hasOwnProperty.call(curves, 0)).toBe(false);
  expect(curves).toEqual({});
});

test("fitCurvesForRing: a genuine bulge produces a curve entry that round-trips close to the original bulge point via flattenShape", async () => {
  const { fitCurvesForRing } = await import("./manualTrace.js");
  const { flattenShape, curveHandlePoint } = await import("./manualShapes.js");
  const a = { x: 0, y: 0 }, bulge = { x: 5, y: 3 }, c = { x: 10, y: 0 };
  const raw = [a, { x: 2.5, y: 1.6 }, bulge, { x: 7.5, y: 1.6 }, c, { x: 10, y: -10 }, { x: 0, y: -10 }];
  const simplified = [a, c, { x: 10, y: -10 }, { x: 0, y: -10 }];
  const { curves } = fitCurvesForRing(raw, simplified, 1);
  expect(curves[0]).toBeDefined();
  // The stored control point should make curveHandlePoint land close to the
  // original worst-deviation raw point (the round-trip check).
  const handle = curveHandlePoint(a, c, curves[0]);
  expect(Math.hypot(handle.x - bulge.x, handle.y - bulge.y)).toBeLessThan(0.5);
  // And flattening the shape actually produces extra geometry near the bulge.
  const flat = flattenShape(simplified, curves, true);
  expect(flat.length).toBeGreaterThan(simplified.length);
});

test("fitCurvesForRing: a true sharp corner between two straight raw runs is never curved (the corner-spike regression this feature exists partly to fix)", async () => {
  const { fitCurvesForRing } = await import("./manualTrace.js");
  // An L-shaped raw ring with a genuine sharp corner at (10,0) and straight
  // runs (with collinear midpoints) on both sides of it.
  const raw = [
    { x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }, // straight run into the corner
    { x: 10, y: 5 }, { x: 10, y: 10 }, // straight run out of the corner
    { x: 0, y: 10 },
  ];
  const simplified = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  const { curves } = fitCurvesForRing(raw, simplified, 1);
  // Segment 0 (0,0)->(10,0) and segment 1 (10,0)->(10,10) both meet exactly
  // at the sharp corner — a naive approach might try to "smooth" through it;
  // this must not curve either segment.
  expect(curves[0]).toBeUndefined();
  expect(curves[1]).toBeUndefined();
});

// ---- simplifyRingAdaptive --------------------------------------------------

function circleRing(n, r = 100, cx = 150, cy = 150) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = (2 * Math.PI * i) / n;
    pts.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  }
  return pts;
}

test("simplifyRingAdaptive: stays within MAX_SHAPE_POINTS on a normal ring at the base tolerance", async () => {
  const { simplifyRingAdaptive } = await import("./manualTrace.js");
  const ring = circleRing(64);
  const simplified = simplifyRingAdaptive(ring, 2);
  expect(simplified.length).toBeLessThanOrEqual(MAX_SHAPE_POINTS);
});

// A jittery/staircase boundary: far more raw points than MAX_SHAPE_POINTS,
// and adversarial in the sense that a naive single-pass simplify at a tight
// tolerance could still leave it well over the cap.
function jitteryStaircaseRing() {
  const pts = [];
  const n = 4000;
  for (let i = 0; i < n; i++) {
    const t = i / n;
    const angle = 2 * Math.PI * t;
    const jitter = (i % 2 === 0 ? 1 : -1) * 0.7; // alternating stair-step
    pts.push({ x: 200 + 150 * Math.cos(angle) + jitter, y: 200 + 150 * Math.sin(angle) + jitter });
  }
  return pts;
}

test("simplifyRingAdaptive: a pathologically detailed (jittery/staircase) ring never exceeds MAX_SHAPE_POINTS, even after retries, and doesn't throw", async () => {
  const { simplifyRingAdaptive } = await import("./manualTrace.js");
  const ring = jitteryStaircaseRing();
  expect(() => simplifyRingAdaptive(ring, 0.1)).not.toThrow();
  const simplified = simplifyRingAdaptive(ring, 0.1);
  expect(simplified.length).toBeLessThanOrEqual(MAX_SHAPE_POINTS);
  expect(simplified.length).toBeGreaterThan(0);
});

test("simplifyRingAdaptive: falls back to uniform-stride decimation of the simplified ring (never the raw ring) as a last resort", async () => {
  const { simplifyRingAdaptive } = await import("./manualTrace.js");
  const ring = jitteryStaircaseRing();
  // maxAttempts=1 forces the loosening loop to give up after the very first
  // (base-tolerance) attempt, so the decimation fallback must kick in.
  const simplified = simplifyRingAdaptive(ring, 0.1, 50, 1);
  expect(simplified.length).toBeLessThanOrEqual(50);
  // Every emitted point must be a real point FROM the ring (decimation, not
  // interpolation/invention).
  for (const p of simplified) {
    expect(ring.some((rp) => rp.x === p.x && rp.y === p.y)).toBe(true);
  }
});

// ---- traceFitRect ---------------------------------------------------------
// The tracing backdrop (ManualPanel paints the reference artwork under the
// drawing canvas) and the traced shapes must land in the SAME rectangle. These
// own that invariant: if they ever disagree, auto-traced outlines sit slightly
// off the artwork they came from, which reads as an inaccurate tracer rather
// than as a transform bug.

test("traceFitRect: letterboxes without stretching — one scale for both axes, centred", async () => {
  const { traceFitRect } = await import("./manualTrace.js");
  // A wide source into a 600x400 canvas with a 12px margin: width-limited.
  const fit = traceFitRect(1200, 300, 600, 400, 12);
  expect(fit.scale).toBeCloseTo(576 / 1200, 9); // (600 - 24) / 1200
  expect(fit.drawnW).toBeCloseTo(576, 6);
  expect(fit.drawnH).toBeCloseTo(144, 6);
  expect(fit.offsetX).toBeCloseTo(12, 6);
  expect(fit.offsetY).toBeCloseTo((400 - 144) / 2, 6); // centred vertically
  // Never bigger than the available box on either axis.
  expect(fit.drawnW).toBeLessThanOrEqual(600 - 24 + 1e-9);
  expect(fit.drawnH).toBeLessThanOrEqual(400 - 24 + 1e-9);
});

test("traceFitRect: a portrait source is height-limited and centred horizontally", async () => {
  const { traceFitRect } = await import("./manualTrace.js");
  const fit = traceFitRect(300, 1200, 600, 400, 12);
  expect(fit.scale).toBeCloseTo(376 / 1200, 9); // (400 - 24) / 1200
  expect(fit.offsetY).toBeCloseTo(12, 6);
  expect(fit.offsetX).toBeCloseTo((600 - fit.drawnW) / 2, 6);
});

test("traceFitRect: degenerate source dimensions fall back to scale 1 instead of NaN/Infinity", async () => {
  const { traceFitRect } = await import("./manualTrace.js");
  for (const [w, h] of [[0, 0], [0, 100], [100, 0]]) {
    const fit = traceFitRect(w, h, 600, 400, 12);
    expect(Number.isFinite(fit.scale)).toBe(true);
    expect(fit.scale).toBe(1);
    expect(Number.isFinite(fit.offsetX)).toBe(true);
    expect(Number.isFinite(fit.offsetY)).toBe(true);
  }
});

test("traceFitRect and rescaleTracedShapes agree — a shape spanning the whole source lands exactly on the backdrop's corners", async () => {
  const { traceFitRect, rescaleTracedShapes } = await import("./manualTrace.js");
  const srcW = 640, srcH = 480;
  const fit = traceFitRect(srcW, srcH, CANVAS_W, CANVAS_H, 12);
  // A rectangle covering the source image exactly.
  const [scaled] = rescaleTracedShapes(
    [{ points: [{ x: 0, y: 0 }, { x: srcW, y: 0 }, { x: srcW, y: srcH }, { x: 0, y: srcH }] }],
    srcW, srcH, CANVAS_W, CANVAS_H, 12,
  );
  // Its corners must be the drawn image's corners, to the pixel.
  expect(scaled.points[0].x).toBeCloseTo(fit.offsetX, 9);
  expect(scaled.points[0].y).toBeCloseTo(fit.offsetY, 9);
  expect(scaled.points[2].x).toBeCloseTo(fit.offsetX + fit.drawnW, 9);
  expect(scaled.points[2].y).toBeCloseTo(fit.offsetY + fit.drawnH, 9);
});
