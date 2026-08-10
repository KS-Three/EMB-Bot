// Trace an uploaded image into a set of STARTING manual-digitizing shapes
// (app/src/ui/ManualPanel.svelte's hand-drawn shape list), so a user can
// upload art and get a rough shape-per-color-region draft to hand-refine
// instead of clicking every anchor point from scratch.
//
// This module is pure logic: plain-data in (a decoded RGBA buffer), plain
// data out (manualShapes.js-shaped shape drafts). No DOM/Svelte/canvas here
// — image decoding is the caller's job, wiring the result into ManualPanel's
// state is PR 2's job.
//
// Deliberately NOT a from-scratch tracer: this reuses EMB-Bot's own already-
// hardened, already-tested pipeline —
//   app/src/lib/flatten.js's flattenRGBA()  (color quantization + background
//     removal + mode-filter denoise + despeckle)
//   src/geometry.js's EMB.traceRegions()    (hole-aware contour tracing)
//   src/geometry.js's EMB.simplify()        (Douglas-Peucker)
// — the same building blocks Image mode's own imageRegions.js already relies
// on for final generation geometry (see flatToRegions there). The one
// genuinely new piece is fitCurvesForRing: deciding which simplified
// segments should become manualShapes.js's native quadratic curves instead
// of staying straight, so a rounded source edge doesn't turn into a
// corner-spiked polygon.

import { EMB } from "./emb.js";
import { flattenRGBA } from "./flatten.js";
import {
  CANVAS_W,
  CANVAS_H,
  MAX_SHAPE_POINTS,
  quadraticControlForPointOnCurve,
  isValidShape,
} from "./manualShapes.js";

// ---- Tuning defaults --------------------------------------------------
// Deliberately looser / fewer-shapes than app/src/lib/imageRegions.js's
// analogous constants (SIMPLIFY_TOL=1.6, MAX_SHAPES_PER_COLOR=60,
// DESPECKLE_SHARE=0.0004): imageRegions.js's output is FINAL stitch
// geometry, generated once and sewn as-is. This module's output is a
// starting point a human is expected to hand-edit afterward, so a coarser,
// lower-shape-count draft is a better starting point than a highly-accurate
// but fiddly-to-clean-up one.
const DEFAULT_N_COLORS = 6;
const DEFAULT_SIMPLIFY_TOL_PX = 2.5; // vs. imageRegions.js's 1.6px
const DEFAULT_CURVE_TOL_PX = 3; // only curve segments with a clear bulge
const DEFAULT_MAX_SHAPES_PER_COLOR = 20; // vs. imageRegions.js's 60
const DEFAULT_DESPECKLE_SHARE = 0.0008; // vs. imageRegions.js's 0.0004 — a bit
// more aggressive, matching the "fewer/coarser starting shapes" goal; same
// px^2-share-of-image units as absorbSmallRegions' own internal threshold
// (src/flatten.js's ABSORB_SHARE=0.0005), just tuned for this feature.

const HOLE_DROPPED_WARNING =
  "A traced shape had an interior hole that isn't supported yet — it will render solid; cut it in by hand if needed.";

function pointsEqual(p, q, eps = 1e-6) {
  return Math.abs(p.x - q.x) <= eps && Math.abs(p.y - q.y) <= eps;
}

function decimateUniform(points, maxPoints) {
  if (points.length <= maxPoints) return points.slice();
  const stride = points.length / maxPoints;
  const out = [];
  for (let i = 0; i < maxPoints; i++) out.push(points[Math.floor(i * stride)]);
  return out;
}

// ---- simplifyRingAdaptive -------------------------------------------------
// EMB.simplify (Douglas-Peucker) wrapped with a retry-with-looser-tolerance
// loop so a pathologically detailed ring never produces more than maxPoints
// vertices. Never throws, never truncates mid-ring (which would cut off part
// of the shape's boundary) — either converges to <= maxPoints by loosening
// tolerance, or as a last resort uniformly decimates the ALREADY-simplified
// ring (never the raw ring).
export function simplifyRingAdaptive(ring, tolPx, maxPoints = MAX_SHAPE_POINTS, maxAttempts = 6) {
  const src = ring || [];
  let tol = tolPx;
  let simplified = EMB.simplify(src, tol);
  for (let attempt = 1; simplified.length > maxPoints && attempt < maxAttempts; attempt++) {
    tol *= 2; // loosen and retry
    simplified = EMB.simplify(src, tol);
  }
  if (simplified.length > maxPoints) {
    simplified = decimateUniform(simplified, maxPoints);
  }
  return simplified;
}

// ---- spansForSimplifiedRing -----------------------------------------------
// Maps each segment of the simplified ring [simplified[i] -> simplified[i+1]]
// to the contiguous run of RAW (pre-simplify) points that fell strictly
// BETWEEN those two endpoints (endpoints themselves excluded — callers
// already have those as `a`/`c`). Douglas-Peucker only ever keeps a
// subsequence of the original points (never invents new ones), so each
// simplified vertex's raw-ring index can be found by walking the raw ring
// forward and matching by value. Handles the wraparound span (last
// simplified vertex back to the first) via modulo indexing.
export function spansForSimplifiedRing(rawRing, simplifiedRing) {
  const raw = rawRing || [];
  const simp = simplifiedRing || [];
  const n = simp.length;
  if (n === 0 || raw.length === 0) return simp.map(() => []);

  // Locate each simplified vertex's index in the raw ring, always searching
  // forward from the previous match (cyclically) so the vertices resolve in
  // ring order even if a coordinate value happens to repeat elsewhere.
  const rawIdx = new Array(n);
  let searchFrom = 0;
  for (let i = 0; i < n; i++) {
    let found = searchFrom;
    for (let k = 0; k < raw.length; k++) {
      const idx = (searchFrom + k) % raw.length;
      if (pointsEqual(raw[idx], simp[i])) { found = idx; break; }
    }
    rawIdx[i] = found;
    searchFrom = (found + 1) % raw.length;
  }

  const spans = [];
  for (let i = 0; i < n; i++) {
    const startIdx = rawIdx[i];
    const endIdx = rawIdx[(i + 1) % n];
    const span = [];
    let k = (startIdx + 1) % raw.length;
    let guard = 0;
    while (k !== endIdx && guard <= raw.length) {
      span.push(raw[k]);
      k = (k + 1) % raw.length;
      guard++;
    }
    spans.push(span);
  }
  return spans;
}

// ---- maxDeviationPoint -----------------------------------------------------
// Perpendicular-distance-to-chord a-c for every point in `pts` (the raw
// interior points of one span), returning the point of MAXIMUM deviation and
// its distance. A degenerate/empty span (the simplified segment IS the raw
// segment, no interior points) returns a clean zero-ish result — the chord
// midpoint at distance 0 — rather than throwing or dividing by zero.
export function maxDeviationPoint(pts, a, c) {
  const list = pts || [];
  if (list.length === 0) {
    return { point: { x: (a.x + c.x) / 2, y: (a.y + c.y) / 2 }, dist: 0 };
  }
  const dx = c.x - a.x, dy = c.y - a.y;
  const lenSq = dx * dx + dy * dy;
  let bestPt = list[0];
  let bestDist = -1;
  for (const p of list) {
    let d;
    if (lenSq === 0) {
      d = Math.hypot(p.x - a.x, p.y - a.y);
    } else {
      const num = Math.abs(dy * p.x - dx * p.y + c.x * a.y - c.y * a.x);
      d = num / Math.sqrt(lenSq);
    }
    if (d > bestDist) { bestDist = d; bestPt = p; }
  }
  return { point: { x: bestPt.x, y: bestPt.y }, dist: bestDist };
}

// ---- fitCurvesForRing -------------------------------------------------
// THE core new algorithm piece. For each segment of the simplified ring,
// decide whether it stays a straight line or gets a manualShapes.js-native
// quadratic curve control point:
//   - find the segment's raw span and its point of max deviation from the
//     straight chord;
//   - deviation <= curveTolPx: stays straight, no curves[i] entry at all
//     (genuinely absent, matching manualShapes.js's sparse-map convention —
//     not present-and-zero);
//   - deviation > curveTolPx: reuse manualShapes.js's OWN
//     quadraticControlForPointOnCurve so the fitted curve passes through the
//     worst raw point at its own parametric midpoint. No curve math is
//     reimplemented here.
// A true sharp corner in the raw ring gets picked up by Douglas-Peucker as
// its own simplified VERTEX (large single-point deviation -> kept as a
// vertex, splitting the ring there) rather than surviving as an interior
// deviation inside some other segment's span — so the segments on either
// side of a real corner are straight runs with near-zero interior deviation,
// and never get curved. That's what fixes the corner-spike defect this
// feature exists partly to address: a naive "connect all traced points"
// approach turns rounded source edges into spiky straight-segment fans;
// curving only genuine per-segment bulges (while leaving real corners sharp)
// avoids both problems at once.
export function fitCurvesForRing(rawRing, simplifiedRing, curveTolPx) {
  const simp = simplifiedRing || [];
  const n = simp.length;
  const curves = {};
  if (n < 2) return { curves };
  const spans = spansForSimplifiedRing(rawRing, simp);
  for (let i = 0; i < n; i++) {
    const a = simp[i];
    const c = simp[(i + 1) % n];
    const span = spans[i] || [];
    const { point, dist } = maxDeviationPoint(span, a, c);
    if (dist > curveTolPx) {
      curves[i] = quadraticControlForPointOnCurve(a, point, c);
    }
  }
  return { curves };
}

// ---- rescaleTracedShapes -------------------------------------------------
// One shared uniform scale+center transform applied to every shape from the
// same trace, so shapes keep their relative alignment (a circle traced
// inside a square stays inside it). Fits srcW x srcH into
// (canvasW - 2*marginPx) x (canvasH - 2*marginPx), preserving aspect ratio
// (letterbox, never stretched), centered. Transforms BOTH anchor points and
// curve control points identically.
export function rescaleTracedShapes(shapes, srcW, srcH, canvasW = CANVAS_W, canvasH = CANVAS_H, marginPx = 12) {
  const availW = Math.max(1, canvasW - 2 * marginPx);
  const availH = Math.max(1, canvasH - 2 * marginPx);
  const scale = srcW > 0 && srcH > 0 ? Math.min(availW / srcW, availH / srcH) : 1;
  const drawnW = srcW * scale;
  const drawnH = srcH * scale;
  const offsetX = (canvasW - drawnW) / 2;
  const offsetY = (canvasH - drawnH) / 2;

  const transformPoint = (p) => ({ x: p.x * scale + offsetX, y: p.y * scale + offsetY });

  return (shapes || []).map((shape) => {
    const points = (shape.points || []).map(transformPoint);
    let curves = shape.curves;
    if (curves) {
      const scaledCurves = {};
      for (const key of Object.keys(curves)) scaledCurves[key] = transformPoint(curves[key]);
      curves = scaledCurves;
    }
    return { ...shape, points, curves };
  });
}

// ---- traceShapesFromRGBA -------------------------------------------------
// Main entry point. Pipeline: flattenRGBA -> per palette color, build a
// binary mask for that color's indices -> EMB.traceRegions on that mask ->
// per traced ring, simplifyRingAdaptive -> fitCurvesForRing -> assemble a
// shape draft. Ids are NOT assigned here — that's the caller's job via
// manualShapes.js's nextShapeIds, once, right before building the batch
// patch (see that function's own docs for why).
//
// Hole handling (see this PR's write-up): manualShapes.js shapes have no
// hole concept — emitting a traced hole as its own same-color shape would
// just fill it back in, corrupting exactly the kind of art (rings, letters
// with counters, washers) this feature exists to help with. So a detected
// hole is never emitted as a shape; one warning is added per shape that had
// at least one dropped hole instead.
export function traceShapesFromRGBA(rgba, w, h, opts = {}) {
  const nColors = opts.nColors || DEFAULT_N_COLORS;
  const removeBg = opts.removeBg !== false; // default true
  const simplifyTolPx = opts.simplifyTolPx != null ? opts.simplifyTolPx : DEFAULT_SIMPLIFY_TOL_PX;
  const curveTolPx = opts.curveTolPx != null ? opts.curveTolPx : DEFAULT_CURVE_TOL_PX;
  const maxShapesPerColor = opts.maxShapesPerColor != null ? opts.maxShapesPerColor : DEFAULT_MAX_SHAPES_PER_COLOR;
  const despeckleShare = opts.despeckleShare != null ? opts.despeckleShare : DEFAULT_DESPECKLE_SHARE;

  const flat = flattenRGBA(rgba, w, h, { nColors, removeBg });
  const { palette, indices } = flat;

  const despeckleMin = w * h * despeckleShare; // area-relative per-shape despeckle
  const holeMin = Math.max(6, despeckleMin * 0.3); // keep smaller holes meaningful (mirrors imageRegions.js)

  const shapes = [];
  const warnings = [];

  for (let ci = 0; ci < palette.length; ci++) {
    const mask = new Uint8Array(w * h);
    for (let p = 0; p < indices.length; p++) {
      if (indices[p] === ci) mask[p] = 1;
    }

    let regions = EMB.traceRegions(mask, w, h)
      .filter((r) => r.outer.length >= 4 && EMB.polygonArea(r.outer) > despeckleMin);
    regions.sort((a, b) => EMB.polygonArea(b.outer) - EMB.polygonArea(a.outer));

    if (regions.length > maxShapesPerColor) {
      const dropped = regions.length - maxShapesPerColor;
      regions = regions.slice(0, maxShapesPerColor);
      const [r, g, b] = palette[ci];
      warnings.push(
        `Color rgb(${r},${g},${b}) traced ${dropped} extra shape${dropped === 1 ? "" : "s"} beyond the ${maxShapesPerColor}-shape cap; the smallest were dropped.`
      );
    }

    for (const region of regions) {
      const simplifiedOuter = simplifyRingAdaptive(region.outer, simplifyTolPx);
      if (simplifiedOuter.length < 3) continue; // degenerate after simplify

      const { curves } = fitCurvesForRing(region.outer, simplifiedOuter, curveTolPx);

      // Defensive: guarantee every emitted shape is sewable (matches
      // shapesToRegions' own silently-skip-invalid convention) rather than
      // trusting the traced+simplified ring is automatically clean.
      if (!isValidShape(simplifiedOuter)) continue;

      shapes.push({
        points: simplifiedOuter,
        curves,
        colorRgb: palette[ci].slice(),
        stitchType: "fill",
        angleDeg: null,
      });

      const realHoles = region.holes.filter((hh) => hh.length >= 4 && EMB.polygonArea(hh) > holeMin);
      if (realHoles.length > 0) warnings.push(HOLE_DROPPED_WARNING);
    }
  }

  return { shapes, warnings };
}
