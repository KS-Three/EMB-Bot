import { test, expect } from "vitest";
import {
  SHAPE_KINDS, defaultShapeParams, resolvedShapeParams, shapePresetPoints,
  circlePoints, rectPoints, heartPoints, starPoints,
  DEFAULT_SHAPE_SIZE_MM, DEFAULT_TOLERANCE_MM,
  STAR_MIN_POINTS, STAR_MAX_POINTS, STAR_MIN_INNER_RATIO, STAR_MAX_INNER_RATIO,
} from "./shapePresets.js";
import { shapeIssues, PX_PER_MM, MAX_SHAPE_POINTS, CANVAS_W, CANVAS_H } from "./manualShapes.js";

function bbox(pts) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of pts) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, maxX, minY, maxY, w: maxX - minX, h: maxY - minY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2 };
}

// Every point has a mirror partner across the vertical line x = cx. eps is
// loose enough to survive the generators' consecutive-duplicate dedupe
// (which can drop one member of a near-coincident pair at the heart's cusp).
function isMirrorSymmetric(pts, eps = 1) {
  const { cx } = bbox(pts);
  return pts.every((p) =>
    pts.some((q) => Math.abs(q.x - (2 * cx - p.x)) <= eps && Math.abs(q.y - p.y) <= eps)
  );
}

// ---- Contract shared by every generator ------------------------------------

const SIZES_MM = [10, 30, 50, 100];

test("every kind, across sizes: output passes manual draw's own shape validation", () => {
  for (const kind of SHAPE_KINDS) {
    for (const sizeMm of SIZES_MM) {
      const pts = shapePresetPoints(kind, defaultShapeParams(kind), sizeMm);
      expect(shapeIssues(pts), `${kind} @ ${sizeMm}mm`).toEqual([]);
      expect(pts.length).toBeLessThanOrEqual(MAX_SHAPE_POINTS);
    }
  }
});

test("every kind: bbox width is exactly sizeMm * PX_PER_MM, centered on the canvas", () => {
  for (const kind of SHAPE_KINDS) {
    for (const sizeMm of SIZES_MM) {
      const b = bbox(shapePresetPoints(kind, defaultShapeParams(kind), sizeMm));
      expect(b.w, `${kind} @ ${sizeMm}mm width`).toBeCloseTo(sizeMm * PX_PER_MM, 6);
      expect(b.cx, `${kind} centered x`).toBeCloseTo(CANVAS_W / 2, 6);
      expect(b.cy, `${kind} centered y`).toBeCloseTo(CANVAS_H / 2, 6);
    }
  }
});

test("every kind is mirror-symmetric about its vertical centerline", () => {
  for (const kind of SHAPE_KINDS) {
    const pts = shapePresetPoints(kind, defaultShapeParams(kind), 50);
    expect(isMirrorSymmetric(pts), kind).toBe(true);
  }
});

test("garbage size/params fall back to sane defaults instead of throwing", () => {
  for (const kind of SHAPE_KINDS) {
    for (const sizeMm of [null, undefined, NaN, -5, "40"]) {
      const pts = shapePresetPoints(kind, null, sizeMm);
      expect(shapeIssues(pts), `${kind} size=${sizeMm}`).toEqual([]);
    }
  }
  const b = bbox(shapePresetPoints("circle", null, null));
  expect(b.w).toBeCloseTo(DEFAULT_SHAPE_SIZE_MM * PX_PER_MM, 6);
});

test("unknown kind falls back to a circle rather than throwing", () => {
  const pts = shapePresetPoints("hexagram_from_the_future", {}, 40);
  expect(shapeIssues(pts)).toEqual([]);
  expect(bbox(pts).w).toBeCloseTo(40 * PX_PER_MM, 6);
});

// ---- Circle -----------------------------------------------------------------

test("circle: all points lie on the radius (it is actually round)", () => {
  const pts = circlePoints(50);
  const { cx, cy } = bbox(pts);
  const r = (50 * PX_PER_MM) / 2;
  for (const p of pts) {
    expect(Math.hypot(p.x - cx, p.y - cy)).toBeCloseTo(r, 6);
  }
});

test("circle: n-gon resolution follows the tolerance — bigger circles get more segments", () => {
  const small = circlePoints(20);
  const large = circlePoints(100);
  expect(large.length).toBeGreaterThan(small.length);
});

test("circle: chord midpoints deviate from the true arc by at most the tolerance", () => {
  for (const sizeMm of [20, 50, 100]) {
    const pts = circlePoints(sizeMm);
    const { cx, cy } = bbox(pts);
    const r = (sizeMm * PX_PER_MM) / 2;
    const tolPx = DEFAULT_TOLERANCE_MM * PX_PER_MM;
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      const sagitta = r - Math.hypot(mid.x - cx, mid.y - cy);
      expect(sagitta, `${sizeMm}mm seg ${i}`).toBeLessThanOrEqual(tolPx + 1e-9);
    }
  }
});

// ---- Rectangle ----------------------------------------------------------------

test("rect: zero corner radius is exactly the 4 corners at the requested w x h", () => {
  const pts = rectPoints(60, 30, 0);
  expect(pts).toHaveLength(4);
  const b = bbox(pts);
  expect(b.w).toBeCloseTo(60 * PX_PER_MM, 6);
  expect(b.h).toBeCloseTo(30 * PX_PER_MM, 6);
});

test("rect: rounded corners stay inside the w x h box and cut the sharp corner", () => {
  const pts = rectPoints(60, 30, 8);
  expect(shapeIssues(pts)).toEqual([]);
  const b = bbox(pts);
  expect(b.w).toBeCloseTo(60 * PX_PER_MM, 6);
  expect(b.h).toBeCloseTo(30 * PX_PER_MM, 6);
  // No point may sit in the corner square that the radius is supposed to
  // round off — check the top-left corner's outermost pocket.
  const rPx = 8 * PX_PER_MM;
  const pocket = pts.filter(
    (p) => p.x < b.minX + rPx * 0.29 && p.y < b.minY + rPx * 0.29
  );
  expect(pocket).toHaveLength(0);
});

test("rect: corner radius clamps to half the short side (stadium, not a bowtie)", () => {
  const pts = rectPoints(60, 20, 999);
  expect(shapeIssues(pts)).toEqual([]);
  const b = bbox(pts);
  expect(b.w).toBeCloseTo(60 * PX_PER_MM, 6);
  expect(b.h).toBeCloseTo(20 * PX_PER_MM, 6);
});

test("rect: height is honored independently of width (the w/h contract)", () => {
  const b = bbox(rectPoints(40, 80, 0));
  expect(b.w).toBeCloseTo(40 * PX_PER_MM, 6);
  expect(b.h).toBeCloseTo(80 * PX_PER_MM, 6);
});

// ---- Heart --------------------------------------------------------------------

test("heart: two lobes up, single point down (canvas y-down space)", () => {
  const pts = heartPoints(50);
  const b = bbox(pts);
  // Bottom tip: the max-y point sits on the vertical centerline.
  const tip = pts.reduce((best, p) => (p.y > best.y ? p : best), pts[0]);
  expect(Math.abs(tip.x - b.cx)).toBeLessThan(1);
  // Two lobes: the topmost points sit OFF the centerline (one per lobe)...
  const top = pts.reduce((best, p) => (p.y < best.y ? p : best), pts[0]);
  expect(Math.abs(top.x - b.cx)).toBeGreaterThan(0.1 * b.w);
  // ...and the curve dips back down between them: the parametric t=0 sample
  // lands EXACTLY on the centerline (sin^3(0) = 0), and that on-centerline
  // top point sits measurably below the lobe tops — the cusp dip.
  const onCenterlineTop = pts.filter((p) => Math.abs(p.x - b.cx) < 1e-6 && p.y < b.cy);
  expect(onCenterlineTop.length).toBeGreaterThan(0);
  const dipY = Math.max(...onCenterlineTop.map((p) => p.y));
  expect(dipY - b.minY).toBeGreaterThan(0.15 * b.h);
});

test("heart: wider than tall (the classic curve's own aspect), and validation-clean", () => {
  const pts = heartPoints(50);
  expect(shapeIssues(pts)).toEqual([]);
  const b = bbox(pts);
  expect(b.w).toBeGreaterThan(b.h);
  expect(b.h / b.w).toBeGreaterThan(0.8); // but not squashed flat
});

// ---- Star ---------------------------------------------------------------------

test("star: 2n vertices, first tip pointing straight up", () => {
  const pts = starPoints(50, 5, 0.45);
  expect(pts).toHaveLength(10);
  const b = bbox(pts);
  const top = pts.reduce((best, p) => (p.y < best.y ? p : best), pts[0]);
  expect(Math.abs(top.x - b.cx)).toBeLessThan(1e-6);
  expect(top.y).toBeCloseTo(b.minY, 6);
});

test("star: inner/outer vertex distance ratio matches innerRatio exactly", () => {
  for (const ratio of [0.3, 0.45, 0.6]) {
    const pts = starPoints(50, 5, ratio);
    // Center = mean of vertices (exact for evenly-spaced alternating radii).
    const cx = pts.reduce((a, p) => a + p.x, 0) / pts.length;
    const cy = pts.reduce((a, p) => a + p.y, 0) / pts.length;
    const dists = pts.map((p) => Math.hypot(p.x - cx, p.y - cy)).sort((a, b) => a - b);
    const inner = dists[0], outer = dists[dists.length - 1];
    expect(inner / outer).toBeCloseTo(ratio, 6);
  }
});

test("star: valid, non-self-intersecting across the full configurable range", () => {
  for (let n = STAR_MIN_POINTS; n <= STAR_MAX_POINTS; n++) {
    for (const ratio of [STAR_MIN_INNER_RATIO, 0.45, STAR_MAX_INNER_RATIO]) {
      const pts = starPoints(50, n, ratio);
      expect(shapeIssues(pts), `star n=${n} ratio=${ratio}`).toEqual([]);
      expect(pts).toHaveLength(2 * n);
    }
  }
});

test("star: point count and inner ratio clamp instead of producing garbage", () => {
  expect(starPoints(50, 1, 0.45)).toHaveLength(2 * STAR_MIN_POINTS);
  expect(starPoints(50, 99, 0.45)).toHaveLength(2 * STAR_MAX_POINTS);
  const tooSharp = starPoints(50, 5, 0.01);
  expect(shapeIssues(tooSharp)).toEqual([]);
});

// ---- Params helpers -------------------------------------------------------------

test("resolvedShapeParams fills a sparse/corrupt bag from the kind's defaults", () => {
  expect(resolvedShapeParams("star", null)).toEqual({ points: 5, innerRatio: 0.45 });
  expect(resolvedShapeParams("star", { points: 7 })).toEqual({ points: 7, innerRatio: 0.45 });
  expect(resolvedShapeParams("rect", {})).toEqual({ heightMm: 30, cornerRadiusMm: 0 });
  expect(resolvedShapeParams("circle", { stray: 1 })).toEqual({ stray: 1 });
});
