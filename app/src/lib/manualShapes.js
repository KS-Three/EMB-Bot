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

// ---- Canvas hit-testing (shape selection) ---------------------------------

// Even-odd ray-casting point-in-polygon test — same algorithm as
// digitize.js's own pointInPoly (there used to group glyph contours into
// shapes with holes), adapted from [x, y] tuples to this module's {x, y}
// point objects. Operates on a shape's FLATTENED geometry (flattenShape's
// output, curves already baked to points) — a caller hit-testing a curved
// shape's body must flatten first, same as shapeIssues/isValidShape already
// require. ManualPanel uses this back-to-front over element.shapes (last
// element checked first) for canvas-click-to-select and hover-cursor
// feedback, so the topmost/last-drawn shape wins on overlap.
export function pointInShape(points, x, y) {
  const pts = points || [];
  let inside = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const xi = pts[i].x, yi = pts[i].y, xj = pts[j].x, yj = pts[j].y;
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

// ---- Curved segments ------------------------------------------------------
// A shape's `points` stay a plain straight-line anchor ring, exactly as
// before — nothing downstream (shapeIssues/isValidShape, the Python
// pipeline, satin/fill) ever needs to know a curve exists. A shape can
// additionally carry `curves`, a sparse { [segmentIndex]: {x,y} } map: key i
// is the segment from anchor i to anchor (i+1) % points.length, value is
// that segment's quadratic-bezier CONTROL point. Only flattenShape (below)
// and shapesToRegions ever expand a curved segment into real geometry —
// everywhere else (vertex hit-testing, Undo point, MAX_SHAPE_POINTS) keeps
// operating on the anchor count alone, unaffected by how many segments are
// curved.

// Sub-pixel snap: dragging a curve handle back within this distance of the
// segment's own straight-line midpoint counts as "put it back" rather than
// "a very subtle curve" — see curveControlOrNull.
const CURVE_STRAIGHTEN_EPS_PX = 2;

// Longest and shortest a curved segment gets flattened to, plus the target
// spacing driving the count in between (chord-length / this, clamped) — a
// short segment doesn't need 24 points to look smooth, a long one needs more
// than 4 to avoid visible faceting.
const CURVE_MIN_SUBPOINTS = 4;
const CURVE_MAX_SUBPOINTS = 24;
const CURVE_PX_PER_SUBPOINT = 10;

// The quadratic-bezier control point that makes the curve from `a` to `c`
// pass through `through` at its own midpoint (t=0.5). Standard "curve
// through a point" inversion of B(0.5) = 0.25*a + 0.5*control + 0.25*c —
// this is what makes dragging a handle feel WYSIWYG: the curve follows the
// cursor instead of bowing away from it.
export function quadraticControlForPointOnCurve(a, through, c) {
  return {
    x: 2 * through.x - 0.5 * (a.x + c.x),
    y: 2 * through.y - 0.5 * (a.y + c.y),
  };
}

// Inverse of the above: where a curve segment's own on-curve midpoint sits,
// given its stored control point — the exact point a curve handle should be
// drawn/hit-tested at (round-trips exactly with quadraticControlForPointOnCurve,
// no drift). Falls back to the plain chord midpoint for a straight (no
// control point) segment, so one function serves both cases.
export function curveHandlePoint(a, c, control) {
  if (!control) return { x: (a.x + c.x) / 2, y: (a.y + c.y) / 2 };
  return {
    x: 0.25 * a.x + 0.5 * control.x + 0.25 * c.x,
    y: 0.25 * a.y + 0.5 * control.y + 0.25 * c.y,
  };
}

// The control point for dragging this segment's handle to `through`, or
// null if `through` landed close enough to the straight-line midpoint that
// the segment should just go back to being straight (see
// CURVE_STRAIGHTEN_EPS_PX) — the one place both the live drag preview and
// the on-release commit decide "is this actually curved," so they can never
// disagree.
export function curveControlOrNull(a, c, through) {
  const mx = (a.x + c.x) / 2, my = (a.y + c.y) / 2;
  if (Math.hypot(through.x - mx, through.y - my) < CURVE_STRAIGHTEN_EPS_PX) return null;
  return quadraticControlForPointOnCurve(a, through, c);
}

// Canvas-px hit radius for grabbing a segment's curve handle — same value as
// ManualPanel's own VERTEX_HIT_R, kept here (rather than local to the
// component) so hitTestSegmentMidpoint is unit-testable like every other
// hit-test helper in this file.
export const CURVE_HANDLE_HIT_R = 8;

// Index of the segment whose curve handle is within CURVE_HANDLE_HIT_R of
// (x, y), or -1. `closed` mirrors flattenShape's: false while a draft is
// still an open polyline (no anchor-n-1-to-anchor-0 segment exists yet),
// true for a finished/editing shape's closed ring.
export function hitTestSegmentMidpoint(points, curves, x, y, closed) {
  const n = points.length;
  const segCount = closed ? n : n - 1;
  let best = -1;
  let bestD = CURVE_HANDLE_HIT_R;
  for (let i = 0; i < segCount; i++) {
    const a = points[i];
    const c = points[(i + 1) % n];
    const hp = curveHandlePoint(a, c, curves && curves[i]);
    const d = Math.hypot(hp.x - x, hp.y - y);
    if (d <= bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

// De Casteljau sampling of one quadratic segment, EXCLUDING both endpoints
// (callers already have those as real anchors) — the number of sub-points
// scales with chord length so long curved edges stay smooth without
// spending the same budget on short ones.
export function flattenQuadraticSegment(a, control, c) {
  const chord = Math.hypot(c.x - a.x, c.y - a.y);
  const n = Math.max(CURVE_MIN_SUBPOINTS, Math.min(CURVE_MAX_SUBPOINTS, Math.round(chord / CURVE_PX_PER_SUBPOINT)));
  const pts = [];
  for (let i = 1; i < n; i++) {
    const t = i / n;
    const mt = 1 - t;
    pts.push({
      x: mt * mt * a.x + 2 * mt * t * control.x + t * t * c.x,
      y: mt * mt * a.y + 2 * mt * t * control.y + t * t * c.y,
    });
  }
  return pts;
}

// The real, walkable geometry for an anchor+curves shape: every anchor, with
// each curved segment's flattened sub-points spliced in between its two
// endpoints. This is the ONLY place curves become points — feed the result
// to shapeIssues/isValidShape for validation, or to shapesToRegions' `outer`
// for generation, and neither needs to know curves exist at all. A shape
// with no curved segments flattens to EXACTLY its own `points` array
// (same length, same order), so this is a no-op for every pre-existing
// shape that predates this feature. `closed` = false renders/validates the
// in-progress draft as an open polyline (no synthetic last-to-first edge
// yet); true walks the full ring, including the closing segment.
export function flattenShape(points, curves, closed) {
  if (!Array.isArray(points) || points.length === 0) return [];
  const n = points.length;
  const segCount = closed ? n : n - 1;
  const out = [points[0]];
  for (let i = 0; i < segCount; i++) {
    const a = points[i];
    const c = points[(i + 1) % n];
    const control = curves && curves[i];
    if (control) {
      for (const p of flattenQuadraticSegment(a, control, c)) out.push(p);
    }
    // The final wraparound segment's endpoint is points[0], already the
    // first element of `out` — skip re-appending it so the ring doesn't
    // carry a duplicate point back at the start.
    if (!(closed && i === segCount - 1)) out.push(c);
  }
  return out;
}

// Batch-safe id allocation for callers (e.g. the trace-to-shapes feature)
// that build several new shapes at once and patch them in with a SINGLE
// `patch()` call. ManualPanel.svelte's own nextShapeId(list) recomputes the
// max "s"+N id from `shapes` on every call — fine for one-shape-at-a-time
// drawing, where a patch() happens between clicks, but wrong for a batch: if
// a caller looped nextShapeId N times before ever patching, every call would
// return the SAME id, because `shapes` doesn't change until that one patch
// lands. nextShapeIds scans the list ONCE and hands back `count` sequential
// new ids in a single array, so a batch caller gets ["s7","s8","s9"] instead
// of ["s7","s7","s7"]. Same "s"+N id-format convention/regex as
// ManualPanel's nextShapeId, so ids from either path never collide.
export function nextShapeIds(list, count) {
  let max = 0;
  for (const s of list || []) {
    const m = /^s(\d+)$/.exec(s.id);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  const ids = [];
  for (let i = 1; i <= count; i++) ids.push("s" + (max + i));
  return ids;
}

// Convert an element's COMPLETED shapes into buildQualityDesign's
// colorRegions input. Each shape becomes its OWN region (a manual choice,
// not an auto-merge-by-color step: two shapes the user happens to color the
// same still sew as two independently-ordered pieces, matching how the
// canvas draws them one at a time). Invalid/degenerate shapes are silently
// skipped, mirroring flatToRegions dropping empty-geometry palette entries,
// rather than throwing — one bad shape shouldn't block generating the rest.
// Curved segments (shape.curves) are flattened to plain points here, at
// this exact hand-off boundary — everything past this function (the stitch
// engine, the Python pipeline) only ever sees straight-line rings.
export function shapesToRegions(shapes) {
  const regions = [];
  for (const shape of shapes || []) {
    if (!shape) continue;
    const outer = flattenShape(shape.points, shape.curves, true);
    if (!isValidShape(outer)) continue;
    const angleOverride = (typeof shape.angleDeg === "number" && isFinite(shape.angleDeg)) ? shape.angleDeg : null;
    regions.push({
      rgb: Array.isArray(shape.colorRgb) ? shape.colorRgb : [20, 20, 20],
      shapes: [{
        outer: outer.map((p) => ({ x: p.x, y: p.y })),
        holes: [],
        tierOverride: shape.stitchType === "satin" ? "satin" : "fill",
        angleOverride,
      }],
    });
  }
  return { regions, pxPerMm: PX_PER_MM };
}
