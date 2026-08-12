// Preset basic shapes (launch-checklist item 4): pure geometry generators
// for circle / rectangle / heart / star elements. Zero UI in this file.
//
// Every generator emits a plain point ring in EXACTLY the model manual draw
// uses (manualShapes.js: an array of {x, y} in authoring-canvas px, closed
// implicitly, no duplicate end point) — a preset shape is just a
// programmatically-generated manual shape, so generation rides
// shapesToRegions -> buildQualityDesign with no parallel pipeline. Outputs
// are guaranteed simple polygons: they must pass manualShapes' shapeIssues
// (self-intersection / area / point-cap checks) — shapePresets.spec.js pins
// that for the full parameter range the UI can produce.
//
// Sizing contract: `sizeMm` is the shape's bbox WIDTH in mm. Rings come out
// with bbox width = sizeMm * PX_PER_MM, centered on the authoring canvas, so
// generate.js passing targetWidthMm = element.sizeMm reproduces the requested
// width exactly (hoop clamp aside) — same rule every other element type
// follows. Heights follow from each shape's own aspect.

import { CANVAS_W, CANVAS_H, PX_PER_MM, MAX_SHAPE_POINTS } from "./manualShapes.js";

export const SHAPE_KINDS = ["circle", "rect", "heart", "star"];

export const SHAPE_LABELS = {
  circle: "Circle",
  rect: "Rectangle",
  heart: "Heart",
  star: "Star",
};

// Width used when an element's sizeMm is unset (SizePanel's Auto-fit clears
// it) — only drives tessellation density there; the sewn size then comes
// from the garment auto-fit, same as any other element with sizeMm null.
export const DEFAULT_SHAPE_SIZE_MM = 50;

// Max chord-to-arc deviation (sagitta) when a curve is flattened to
// segments, in FINAL mm — the "n-gon at tolerance" knob. 0.1 mm is well
// under a stitch's own placement error, so flattened curves are
// indistinguishable in thread.
export const DEFAULT_TOLERANCE_MM = 0.1;

export const STAR_MIN_POINTS = 3;
export const STAR_MAX_POINTS = 12;
export const STAR_MIN_INNER_RATIO = 0.15;
export const STAR_MAX_INNER_RATIO = 0.9;

// Per-kind SHAPE parameters (aspect/detail only — size lives on
// element.sizeMm, see the sizing contract above; rect height/corner radius
// are true mm at the element's default width).
export function defaultShapeParams(kind) {
  if (kind === "rect") return { heightMm: 30, cornerRadiusMm: 0 };
  if (kind === "star") return { points: 5, innerRatio: 0.45 };
  return {}; // circle, heart: no shape params beyond size
}

// The params object to actually read values from: caller-stored params
// spread over the kind's defaults, so an element saved before a param
// existed (or one with a sparse bag) always resolves to a complete set.
export function resolvedShapeParams(kind, params) {
  return { ...defaultShapeParams(kind), ...(params && typeof params === "object" ? params : {}) };
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

function finiteOr(v, fallback) {
  return typeof v === "number" && isFinite(v) ? v : fallback;
}

// Segments needed to flatten an arc of `radiusMm` over `sweepRad` radians
// with chord sagitta <= tolMm: s = r * (1 - cos(step/2)) <= tol.
function arcSteps(radiusMm, sweepRad, tolMm) {
  if (!(radiusMm > tolMm)) return 2;
  const maxStep = 2 * Math.acos(1 - tolMm / radiusMm);
  return Math.max(2, Math.ceil(sweepRad / maxStep));
}

// Uniform-scale + translate a raw ring (any units) onto the authoring canvas
// so its bbox width is exactly widthMm * PX_PER_MM and its bbox center sits
// at the canvas center. Uniform on purpose: aspect is part of each shape's
// identity, never squashed to fit.
function fitRing(raw, widthMm) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of raw) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  const s = (widthMm * PX_PER_MM) / (maxX - minX || 1);
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  return raw.map((p) => ({
    x: CANVAS_W / 2 + (p.x - cx) * s,
    y: CANVAS_H / 2 + (p.y - cy) * s,
  }));
}

// Drop consecutive (and wraparound) near-duplicate points — parametric
// sampling near a cusp (the heart's bottom point) or arc endpoints meeting
// at a stadium-radius rect corner can land two samples on effectively the
// same px, and degenerate micro-segments are exactly what downstream
// offset/inset code chokes on. Runs in FINAL px space, after fitRing.
const DEDUPE_EPS_PX = 0.35;
function dedupeRing(pts) {
  const out = [];
  for (const p of pts) {
    const last = out[out.length - 1];
    if (last && Math.hypot(p.x - last.x, p.y - last.y) <= DEDUPE_EPS_PX) continue;
    out.push(p);
  }
  while (
    out.length > 1 &&
    Math.hypot(out[0].x - out[out.length - 1].x, out[0].y - out[out.length - 1].y) <= DEDUPE_EPS_PX
  ) {
    out.pop();
  }
  return out;
}

// fit -> dedupe -> fit again: dedupe needs px space to mean anything, but
// dropping a point can nudge the bbox, so a second fit restores the exact
// width/centering contract the spec pins.
function finishRing(raw, widthMm) {
  return fitRing(dedupeRing(fitRing(raw, widthMm)), widthMm);
}

// Circle: a regular n-gon with n chosen from the tolerance at the FINAL mm
// size (a 100 mm circle genuinely needs more segments than a 20 mm one).
// sizeMm is the diameter (= bbox width).
export function circlePoints(sizeMm, opts) {
  const tol = finiteOr(opts && opts.toleranceMm, DEFAULT_TOLERANCE_MM);
  const dMm = Math.max(finiteOr(sizeMm, DEFAULT_SHAPE_SIZE_MM), 1);
  const r = dMm / 2;
  // Rounded UP to a multiple of 4 so a vertex lands on all four cardinal
  // points — the polygon's bbox is then exactly 2r, so fitting the bbox to
  // sizeMm doesn't inflate the radius (which would silently exceed the
  // flattening tolerance the segment count was computed for).
  const n = Math.min(200, Math.ceil(clamp(arcSteps(r, 2 * Math.PI, tol), 16, 200) / 4) * 4);
  const raw = [];
  for (let i = 0; i < n; i++) {
    const a = -Math.PI / 2 + (i / n) * 2 * Math.PI;
    raw.push({ x: r * Math.cos(a), y: r * Math.sin(a) });
  }
  return finishRing(raw, dMm);
}

// Rectangle, optionally with rounded corners (quarter arcs flattened at
// tolerance). Corner radius clamps to half the short side — at the clamp the
// two adjacent arcs meet and the shape degrades gracefully to a stadium/
// circle rather than self-intersecting.
export function rectPoints(widthMm, heightMm, cornerRadiusMm, opts) {
  const tol = finiteOr(opts && opts.toleranceMm, DEFAULT_TOLERANCE_MM);
  const w = Math.max(finiteOr(widthMm, DEFAULT_SHAPE_SIZE_MM), 1);
  const h = Math.max(finiteOr(heightMm, 30), 1);
  const r = clamp(Math.max(finiteOr(cornerRadiusMm, 0), 0), 0, Math.min(w, h) / 2);
  const hw = w / 2, hh = h / 2;
  let raw;
  if (r < Math.max(tol, 0.01)) {
    raw = [
      { x: -hw, y: -hh },
      { x: hw, y: -hh },
      { x: hw, y: hh },
      { x: -hw, y: hh },
    ];
  } else {
    // k segments per quarter arc, capped so even a stadium-sized radius
    // stays far under MAX_SHAPE_POINTS (4 * (48 + 1) = 196 points worst
    // case).
    const k = Math.min(arcSteps(r, Math.PI / 2, tol), 48);
    // Corner arc centers, walked clockwise in screen (y-down) space.
    const corners = [
      { cx: -hw + r, cy: -hh + r, a0: Math.PI },       // top-left: 180° -> 270°
      { cx: hw - r, cy: -hh + r, a0: 1.5 * Math.PI },  // top-right: 270° -> 360°
      { cx: hw - r, cy: hh - r, a0: 0 },               // bottom-right: 0° -> 90°
      { cx: -hw + r, cy: hh - r, a0: 0.5 * Math.PI },  // bottom-left: 90° -> 180°
    ];
    raw = [];
    for (const c of corners) {
      for (let i = 0; i <= k; i++) {
        const a = c.a0 + (i / k) * (Math.PI / 2);
        raw.push({ x: c.cx + r * Math.cos(a), y: c.cy + r * Math.sin(a) });
      }
    }
  }
  return finishRing(raw, w);
}

// Heart: the classic two-lobe parametric curve
//   x(t) = 16 sin^3 t
//   y(t) = 13 cos t - 5 cos 2t - 2 cos 3t - cos 4t
// — smooth round lobes, a soft dip between them, and a single cusp at the
// bottom point. The curve is defined y-up (lobes on top), so y is negated
// into canvas (y-down) space. A fixed 120 samples keeps the cusp crisp and
// the lobes smooth at any sewable size while staying far under
// MAX_SHAPE_POINTS.
const HEART_SAMPLES = 120;
export function heartPoints(sizeMm) {
  const w = Math.max(finiteOr(sizeMm, DEFAULT_SHAPE_SIZE_MM), 1);
  const raw = [];
  for (let i = 0; i < HEART_SAMPLES; i++) {
    const t = (i / HEART_SAMPLES) * 2 * Math.PI;
    const s = Math.sin(t);
    raw.push({
      x: 16 * s * s * s,
      y: -(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)),
    });
  }
  return finishRing(raw, w);
}

// Star: `points` tips (default 5) alternating between an outer radius and
// innerRatio * outer, first tip pointing up. Alternating radii on evenly
// spaced angles always produce a simple polygon for 0 < ratio < 1; the
// clamps just keep the UI range from producing needle tips (ratio too low)
// or a shape indistinguishable from a polygon (too high).
export function starPoints(sizeMm, points, innerRatio) {
  const w = Math.max(finiteOr(sizeMm, DEFAULT_SHAPE_SIZE_MM), 1);
  const n = clamp(Math.round(finiteOr(points, 5)), STAR_MIN_POINTS, STAR_MAX_POINTS);
  const ratio = clamp(finiteOr(innerRatio, 0.45), STAR_MIN_INNER_RATIO, STAR_MAX_INNER_RATIO);
  const raw = [];
  for (let i = 0; i < 2 * n; i++) {
    const rad = i % 2 === 0 ? 1 : ratio;
    const a = -Math.PI / 2 + (i * Math.PI) / n;
    raw.push({ x: rad * Math.cos(a), y: rad * Math.sin(a) });
  }
  return finishRing(raw, w);
}

// The one entry point generation/UI use: kind + params bag + element size ->
// point ring. Unknown kinds fall back to circle rather than throwing — a
// project file from a future version with a new kind still loads and sews
// SOMETHING visible instead of dying.
export function shapePresetPoints(kind, params, sizeMm) {
  const p = resolvedShapeParams(kind, params);
  const w = finiteOr(sizeMm, DEFAULT_SHAPE_SIZE_MM);
  if (kind === "rect") return rectPoints(w, p.heightMm, p.cornerRadiusMm);
  if (kind === "heart") return heartPoints(w);
  if (kind === "star") return starPoints(w, p.points, p.innerRatio);
  return circlePoints(w);
}

// Sanity re-export so specs can assert the cap without importing two files.
export { MAX_SHAPE_POINTS };
