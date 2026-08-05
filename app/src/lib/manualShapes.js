// Manual digitizing mode (Studio's third content type, MVP slice): pure
// logic for a hand-drawn shape list. Zero image analysis anywhere in this
// file — every shape and its stitch assignment comes straight from what the
// user drew and picked. The one job here is turning that shape list into
// EXACTLY the colorRegions shape src/digitize.js's buildQualityDesign
// already accepts (the same shape imageRegions.js's flatToRegions produces
// for Image mode) so generation rides the identical pull-comp/underlay/
// sequencing pipeline — see digitize.js's shape.tierOverride /
// shape.angleOverride, both additive hooks this module is the first caller
// of on the Studio side.

// A nominal authoring-canvas size manual shapes are drawn against. Only the
// RELATIVE geometry between shapes matters — buildQualityDesign fits the
// combined bbox to the garment/hoop regardless of absolute px scale — so any
// fixed canvas size + pxPerMm pair produces the same final design. Mirrors
// imageRegions.js's own NOMINAL_LONG_MM approach.
export const CANVAS_W = 600;
export const CANVAS_H = 400;
export const NOMINAL_LONG_MM = 100;
export const PX_PER_MM = Math.max(CANVAS_W, CANVAS_H) / NOMINAL_LONG_MM;

// Canvas-pixel radius for "click near the shape's start point" (closing a
// shape by clicking back on its first point).
export const CLOSE_RADIUS_PX = 10;

// Points-per-shape cap — mirrors digitizer.js's BOUNDARY_MAX_POINTS (the
// service side's analogous ceiling on hand-edited/manual boundary rings).
// Clicks past this are ignored rather than silently growing a shape into
// something the stitch engine chokes on.
export const MAX_SHAPE_POINTS = 500;

const MIN_AREA_PX2 = 4; // degenerate/zero-area guard (a mis-click sliver)

function polygonArea(points) {
  let a = 0;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    a += points[j].x * points[i].y - points[i].x * points[j].y;
  }
  return Math.abs(a) / 2;
}

// Standard orientation/on-segment test (CLRS) — used only to answer "do
// these two segments cross", not to classify HOW. Ported from
// digitizer.js's own segmentsIntersect/orientation/onSegment (the boundary
// editor's self-intersection check), adapted from [x, y] tuples to this
// module's {x, y} point objects.
function orientation(p, q, r) {
  const val = (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y);
  if (Math.abs(val) < 1e-9) return 0;
  return val > 0 ? 1 : 2;
}
function onSegment(p, q, r) {
  return (
    Math.min(p.x, r.x) - 1e-9 <= q.x && q.x <= Math.max(p.x, r.x) + 1e-9 &&
    Math.min(p.y, r.y) - 1e-9 <= q.y && q.y <= Math.max(p.y, r.y) + 1e-9
  );
}
function segmentsIntersect(p1, p2, p3, p4) {
  const o1 = orientation(p1, p2, p3);
  const o2 = orientation(p1, p2, p4);
  const o3 = orientation(p3, p4, p1);
  const o4 = orientation(p3, p4, p2);
  if (o1 !== o2 && o3 !== o4) return true;
  if (o1 === 0 && onSegment(p1, p3, p2)) return true;
  if (o2 === 0 && onSegment(p1, p4, p2)) return true;
  if (o3 === 0 && onSegment(p3, p1, p4)) return true;
  if (o4 === 0 && onSegment(p3, p2, p4)) return true;
  return false;
}

// Human-readable problems with the CURRENT point list, or [] when it's a
// clean sewable polygon. Mirrors digitizer.js's boundaryIssues — same
// pattern (reason strings, not just a boolean) so callers can surface WHY a
// shape is rejected instead of just disabling a button. Point-count/area
// checks live here too (not only in isValidShape) so a single call gives
// the full picture; isValidShape stays a cheap boolean wrapper around this.
export function shapeIssues(points) {
  const pts = points || [];
  const issues = [];
  if (!Array.isArray(pts) || pts.length < 3) {
    issues.push("Needs at least 3 points.");
    return issues;
  }
  if (pts.length > MAX_SHAPE_POINTS) {
    issues.push(`Too many points (max ${MAX_SHAPE_POINTS}).`);
  }
  const n = pts.length;
  outer: for (let i = 0; i < n; i++) {
    const a1 = pts[i], a2 = pts[(i + 1) % n];
    for (let j = i + 1; j < n; j++) {
      const adjacent = j === i + 1 || (i === 0 && j === n - 1);
      if (adjacent) continue;
      const b1 = pts[j], b2 = pts[(j + 1) % n];
      if (segmentsIntersect(a1, a2, b1, b2)) {
        issues.push("This shape crosses itself.");
        break outer;
      }
    }
  }
  if (polygonArea(pts) <= MIN_AREA_PX2) {
    issues.push("This shape is too small to sew.");
  }
  return issues;
}

// A shape is sewable once it has >= 3 points, real (non-degenerate) area —
// two points on top of each other, or three collinear points, can't trace
// to a real polygon — and doesn't cross itself (a self-intersecting
// "bowtie" can still have plenty of shoelace area, so that alone isn't
// enough; see shapeIssues).
export function isValidShape(points) {
  return shapeIssues(points).length === 0;
}

// Sub-pixel click-jitter guard for the duplicate-consecutive-point dedupe
// below — two clicks landing at the "same" screen spot can still differ by
// a fractional pixel once converted through canvasPointFromEvent's scale
// factor, so exact equality (like dedupeRing's) is too strict here.
const DUP_POINT_EPS_PX = 0.5;

// True when (x, y) is (nearly) on top of the last-placed point in `points`
// — the click-time equivalent of dedupeRing's duplicate-consecutive-point
// dedupe (see digitizer.js::dedupeRing, digitizer_core.regions._dedupe_ring,
// digitizer_service/app.py's copy of the same), applied as each point is
// placed rather than post-hoc over a finished ring.
export function isDuplicateOfLast(points, x, y) {
  const last = Array.isArray(points) && points.length ? points[points.length - 1] : null;
  if (!last) return false;
  return Math.hypot(x - last.x, y - last.y) <= DUP_POINT_EPS_PX;
}

// Whether (x,y) is within closing distance of a shape's own first point —
// the "click the start point to close" gesture. Requires at least 2 points
// already placed (closing a 1-point "shape" is meaningless).
export function isNearStart(points, x, y) {
  if (!Array.isArray(points) || points.length < 2) return false;
  const p0 = points[0];
  return Math.hypot(x - p0.x, y - p0.y) <= CLOSE_RADIUS_PX;
}

// Convert an element's COMPLETED shapes into buildQualityDesign's
// colorRegions input. Each shape becomes its OWN region (a manual choice,
// not an auto-merge-by-color step: two shapes the user happens to color the
// same still sew as two independently-ordered pieces, matching how the
// canvas draws them one at a time). Invalid/degenerate shapes are silently
// skipped, mirroring flatToRegions dropping empty-geometry palette entries,
// rather than throwing — one bad shape shouldn't block generating the rest.
export function shapesToRegions(shapes) {
  const regions = [];
  for (const shape of shapes || []) {
    if (!shape || !isValidShape(shape.points)) continue;
    const angleOverride = (typeof shape.angleDeg === "number" && isFinite(shape.angleDeg)) ? shape.angleDeg : null;
    regions.push({
      rgb: Array.isArray(shape.colorRgb) ? shape.colorRgb : [20, 20, 20],
      shapes: [{
        outer: shape.points.map((p) => ({ x: p.x, y: p.y })),
        holes: [],
        tierOverride: shape.stitchType === "satin" ? "satin" : "fill",
        angleOverride,
      }],
    });
  }
  return { regions, pxPerMm: PX_PER_MM };
}
