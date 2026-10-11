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

import { railsFromSpine } from "./spineRails.js";

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

// Does any edge of the closed ring `pts` touch a NON-adjacent edge of it? The
// one self-intersection check in this module: a closed shape's own ring
// (shapeIssues) and a column's rail ring (columnIssues) both ask it.
function ringSelfCrosses(pts) {
  const n = pts.length;
  for (let i = 0; i < n; i++) {
    const a1 = pts[i], a2 = pts[(i + 1) % n];
    for (let j = i + 1; j < n; j++) {
      const adjacent = j === i + 1 || (i === 0 && j === n - 1);
      if (adjacent) continue;
      if (segmentsIntersect(a1, a2, pts[j], pts[(j + 1) % n])) return true;
    }
  }
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
  if (ringSelfCrosses(pts)) issues.push("This shape crosses itself.");
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

// How far a curved node bows its incoming segment, as a fraction of that
// segment's chord length. Big enough to read as a deliberate curve at a
// glance, small enough that it is a starting point rather than a shape of its
// own — the user still drags the segment handle to finish it.
export const CURVED_NODE_BOW = 0.16;

// The on-curve "through" point for the incoming segment of a node placed as
// CURVED (right-click while drawing).
//
// Which SIDE it bows to is the whole difficulty. Bowing to a fixed side makes
// a run of curved nodes alternate into scallops as the path changes heading.
// So the side is taken from the turn itself: perpendicular to this chord, on
// the OUTSIDE of the corner the path is making at `a`. A rounded-off outline —
// a mushroom cap, a letter bowl — is exactly a sequence of outward turns, so
// this reads as one continuous arc.
//
// `before` is the anchor preceding `a`, or null on the very first segment,
// where there is no turn yet to take a side from and either choice is
// arbitrary; the handle drag is one gesture away.
export function curvedNodeThrough(a, b, before, bow = CURVED_NODE_BOW) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  const mid = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  if (len < 1e-9) return mid;
  // Left-hand normal of the chord a->b.
  let px = -dy / len, py = dx / len;
  if (before) {
    // Cross product of the incoming chord with this one: > 0 means the path
    // is turning left here, so the outside of the corner is to the RIGHT.
    const cross = (a.x - before.x) * dy - (a.y - before.y) * dx;
    if (cross > 0) { px = -px; py = -py; }
  }
  return { x: mid.x + px * len * bow, y: mid.y + py * len * bow };
}

// Per-node "is this a curved node", for drawing them in Ember's colour
// vocabulary (straight one colour, curved another) so the shape's structure is
// readable without clicking anything.
//
// A node is curved when the segment ARRIVING at it is curved — which makes
// right-click-to-place and drag-a-handle-to-bow agree on the same meaning
// rather than being two unrelated notions of curvedness.
export function curvedNodeFlags(points, curves, closed) {
  const n = points.length;
  const crv = curves || {};
  const flags = new Array(n).fill(false);
  for (let i = 0; i < n; i++) {
    const incoming = i === 0 ? (closed ? n - 1 : -1) : i - 1;
    flags[i] = incoming >= 0 && !!crv[incoming];
  }
  return flags;
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

// ---- Columns: an open spine plus a drawn width ------------------------------
// A shape with `kind: "column"` is a hand-drawn satin column (spec 2026-09-30
// §6, "Amended 2026-10-01"): `{ id, kind: "column", points, curves, widthPx,
// colorRgb }`. `points`/`curves` are an OPEN spine — `curves[i]` is segment
// i -> i+1 and there is no closing segment — and `widthPx` is the full drawn
// width in the same authored canvas px (Kent's ruling 12: a resize scales it
// with everything else; millimetres are a view through the element's fit).
// It has no stitchType and no angleDeg, and it takes no part in cut-outs:
// never a hole, never a hole's parent. `kind` absent means a closed shape, so
// every record that predates this reads exactly as it did.

// A new column's drawn width (Kent's ruling 9). The caller converts through
// the element's fit; this module never stores a width in mm.
export const COLUMN_DEFAULT_MM = 4.0;

// A spine this long or shorter (flattened, canvas px) is a mis-click, not a
// column. The engine has no minimum column length of its own, so the floor
// lives here. Same magnitude as MIN_AREA_PX2's sliver guard.
export const MIN_COLUMN_LEN_PX = 4;

const COLUMN_NEEDS_2 = "A column needs at least 2 points.";
const COLUMN_TOO_SHORT = "This column is too short to sew.";
const COLUMN_FOLDS = "This column folds over itself — widen the bend or narrow the column.";

export function isColumn(shape) {
  return !!shape && shape.kind === "column";
}

function columnSpine(shape) {
  return flattenShape(shape.points, shape.curves, false);
}

// The rails the engine sews between, or null when the column has none (under
// two distinct points, or no positive width). Same point count, same
// direction — see spineRails.js for why that is the whole contract.
export function columnRails(shape) {
  if (!isColumn(shape)) return null;
  const rails = railsFromSpine(columnSpine(shape), shape.widthPx);
  return rails ? { railA: rails.railA, railB: rails.railB } : null;
}

// THE ring any shape presents to the engine, and so to everything that asks
// "where is this shape": a closed shape's flattened ring, a column's rail A
// followed by rail B backwards. [] when a column has no rails.
export function shapeRing(shape) {
  if (!shape) return [];
  if (!isColumn(shape)) return flattenShape(shape.points, shape.curves, true);
  const rails = railsFromSpine(columnSpine(shape), shape.widthPx);
  return rails ? rails.ring : [];
}

// A column's problems, in shapeIssues' reason-string form.
//
// "Folds over itself" is asked of the RAIL RING, not the spine: a spine may
// pass near itself, or even cross itself, and what matters is whether the
// outline the rails make is a simple ring. That makes it a statement about
// the bend AND the width — the same hairpin folds at 24 px and is clean at 4.
// It also means a spine that ends on its own start is refused: the two end
// caps meet. A closed loop is a closed shape's job, not a column's.
export function columnIssues(shape) {
  const pts = shape && Array.isArray(shape.points) ? shape.points : [];
  if (pts.length < 2) return [COLUMN_NEEDS_2];
  const issues = [];
  if (pts.length > MAX_SHAPE_POINTS) issues.push(`Too many points (max ${MAX_SHAPE_POINTS}).`);
  const spine = columnSpine(shape);
  let len = 0;
  for (let i = 1; i < spine.length; i++) len += Math.hypot(spine[i].x - spine[i - 1].x, spine[i].y - spine[i - 1].y);
  if (len <= MIN_COLUMN_LEN_PX) {
    issues.push(COLUMN_TOO_SHORT);
    return issues;
  }
  const rails = railsFromSpine(spine, shape.widthPx);
  // Long enough, but no rails: the width is missing, zero, negative or NaN.
  // Nothing would sew, so it must not read as a healthy column. It takes the
  // too-short message rather than a new string — either way there is no
  // column here to sew.
  if (!rails) issues.push(COLUMN_TOO_SHORT);
  else if (ringSelfCrosses(rails.ring)) issues.push(COLUMN_FOLDS);
  return issues;
}

// Why this shape will not sew, whichever kind it is. A closed shape is judged
// on the ring it presents — curves flattened — which is the ring
// shapesToRegions hands the engine.
export function shapeProblems(shape) {
  if (isColumn(shape)) return columnIssues(shape);
  return shapeIssues(shapeRing(shape));
}

// Will shapesToRegions emit a region for this shape? No problems, not a
// cut-out — and a column must actually have rails (a column with no usable
// width has no message of its own, and sews nothing). A column's `cutOut`
// flag is ignored: a column cannot be a cut-out.
export function isSewableShape(shape) {
  if (!shape) return false;
  if (isColumn(shape)) return columnIssues(shape).length === 0 && columnRails(shape) !== null;
  return !shape.cutOut && shapeProblems(shape).length === 0;
}

// ---- Edge-click-to-insert-vertex ------------------------------------------
// Clicking an already-selected shape's edge (rather than its vertex or curve
// handle) inserts a brand-new anchor right there, splitting one segment into
// two independently-editable ones — the one gap the curve-handle-per-segment
// model (above) doesn't cover: bowing lets you curve a whole segment, but
// there was previously no way to add a hard new corner or a second
// independent curve control point partway along a long edge.

// Point-to-segment distance: how far `p` is from the closest point on the
// line segment a-b (clamped to the segment, not the infinite line through
// it) — same standard closest-point-on-segment projection every hit-test in
// this file that isn't a plain point-to-point distance eventually needs,
// just not one any existing helper here already exposed.
export function distToSegment(p, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

// Which ANCHOR segment (x, y) is closest to, and how far — walks each
// segment's real, on-screen geometry (its flattened curve chain when it has
// a control point, same sub-points flattenQuadraticSegment already produces
// for drawing/flattenShape, or just its two endpoints when straight) so a
// curved segment hit-tests against the visible bowed line, not the straight
// anchor-to-anchor chord a naive check would use. `closed` mirrors every
// other hit-test in this file (hitTestSegmentMidpoint, flattenShape): false
// for an open in-progress draft, true for a finished shape's closed ring.
// Returns { index: -1, dist: Infinity } for a degenerate (<2-point) input.
export function nearestSegmentIndex(points, curves, x, y, closed) {
  const pt = { x, y };
  const n = points.length;
  const segCount = closed ? n : n - 1;
  let index = -1;
  let dist = Infinity;
  for (let i = 0; i < segCount; i++) {
    const a = points[i];
    const c = points[(i + 1) % n];
    const control = curves && curves[i];
    const chain = control ? [a, ...flattenQuadraticSegment(a, control, c), c] : [a, c];
    for (let k = 0; k < chain.length - 1; k++) {
      const d = distToSegment(pt, chain[k], chain[k + 1]);
      if (d < dist) {
        dist = d;
        index = i;
      }
    }
  }
  return { index, dist };
}

// Splits segment `segIndex` (points[segIndex] -> points[segIndex + 1]) by
// inserting `point` as a brand-new anchor between them, and returns a NEW
// shape object — `shape` itself is never mutated. Both halves of the split
// start straight: any curve that segment used to carry is simply dropped
// rather than preserved/interpolated onto either half (deliberately — the
// user can re-curve either new half afterward if they want it). Every
// OTHER curve, on a segment index greater than segIndex, shifts up by one to
// stay bound to the same visual edge, since splicing a point renumbers every
// later segment; curves at or before segIndex are untouched. Respects the
// same MAX_SHAPE_POINTS ceiling the draft-drawing flow enforces — a shape
// already at the cap is returned completely unchanged (same reference) so a
// caller can detect the no-op with `=== `, mirroring how a click past the
// cap during drafting is just silently dropped rather than erroring.
export function insertVertexAtSegment(shape, segIndex, point) {
  const points = shape.points || [];
  if (points.length >= MAX_SHAPE_POINTS) return shape;
  const newPoints = [
    ...points.slice(0, segIndex + 1),
    { x: point.x, y: point.y },
    ...points.slice(segIndex + 1),
  ];
  const oldCurves = shape.curves || {};
  const newCurves = {};
  for (const key in oldCurves) {
    const idx = Number(key);
    if (idx === segIndex) continue; // the split segment's curve doesn't carry forward onto either new half
    newCurves[idx > segIndex ? idx + 1 : idx] = oldCurves[key];
  }
  return { ...shape, points: newPoints, curves: newCurves };
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
// How far a pasted copy lands from its original, in canvas px. Non-zero on
// purpose: a paste dropped exactly on top of its source is indistinguishable
// from nothing having happened, and the user cannot grab either copy to
// separate them. Small enough that the copy stays inside the canvas for any
// shape that fits with room to spare.
// Should the drawing canvas scroll itself into view on entry?
//
// Measured in a real browser 2026-08-26: ManualPanel opens with a seven-line
// instruction paragraph above the canvas, so at a 1280x720 viewport only 14%
// of the canvas sat inside the scroll port -- you land in "Draw shapes" unable
// to see most of the surface you draw on. 1440x900 was 92%, 1920x1080 was
// 100%, which is why it never showed up on a desktop.
//
// Two things it must NOT do, and both are the reason this is a predicate
// rather than an unconditional scrollIntoView:
//   - Never scroll where nothing is clipped. A jump the user did not ask for
//     is its own bug, and it is the common case on a tall screen.
//   - Never scroll off an unmeasurable rect. A zero-height canvas means
//     layout has not happened (or there is none, as under jsdom), not that
//     the canvas is hidden. Returning false is the safe reading; scrolling on
//     a guess is not. (NaN from 0/0 would also fall through the comparison,
//     but relying on that is a coincidence, not a decision.)
//
// Pure and exported so the rule can be asserted directly -- the same reason
// preview.js's threadLodLayers is a standalone function. Testing it through a
// mounted component would mean faking a layout jsdom does not have, which is
// how you end up with a test that cannot fail.
export function shouldScrollCanvasIntoView(canvasRect, portRect, minVisible = 0.9) {
  if (!canvasRect || !portRect) return false;
  const h = canvasRect.bottom - canvasRect.top;
  if (!(h > 0)) return false;
  const visible = Math.max(
    0,
    Math.min(canvasRect.bottom, portRect.bottom) - Math.max(canvasRect.top, portRect.top),
  );
  return visible / h < minVisible;
}

export const PASTE_OFFSET_PX = 18;

// Duplicate a shape: same geometry, same stitch settings, NEW id, nudged clear
// of the original. Curve control points move with their anchors — a bowed edge
// that kept its old controls would flatten or invert on the copy, because a
// quadratic control is an absolute canvas point, not a delta.
//
// Clamped so a paste can never push a copy off-canvas: if the offset would
// carry any point past an edge, the whole copy shifts back by the overflow, so
// it stays whole and grabbable rather than being partly unreachable. A shape
// bigger than the canvas has no on-canvas offset at all -- that one keeps the
// nominal nudge, because every alternative is equally off-canvas.
export function duplicateShape(shape, id, offset = PASTE_OFFSET_PX, canvasW = CANVAS_W, canvasH = CANVAS_H) {
  if (!shape || !Array.isArray(shape.points) || shape.points.length === 0) return null;

  let dx = offset, dy = offset;
  let maxX = -Infinity, maxY = -Infinity, minX = Infinity, minY = Infinity;
  const consider = (pt) => {
    if (!pt) return;
    if (pt.x > maxX) maxX = pt.x;
    if (pt.y > maxY) maxY = pt.y;
    if (pt.x < minX) minX = pt.x;
    if (pt.y < minY) minY = pt.y;
  };
  for (const pt of shape.points) consider(pt);
  for (const key of Object.keys(shape.curves || {})) consider(shape.curves[key]);

  // Clamp to the range of offsets that keeps the copy on-canvas, then pick the
  // one closest to `offset`. Two bugs lived in the obvious four-if version
  // (both found by review 2026-08-26):
  //
  //   1. The min-edge ifs OVERWROTE the max-edge ifs instead of intersecting
  //      with them. A shape already hanging off both edges (minX < 0 and
  //      maxX > canvasW -- routine for artwork wider than the canvas) got
  //      dx = -minX, pushing the copy FURTHER right, the exact opposite of
  //      what the comment above promises.
  //   2. Nothing kept the offset off zero. A shape whose bounds touch the
  //      right and bottom edges -- routine for a traced outline, since
  //      traceFitRect letterboxes artwork flush to the canvas -- clamped to
  //      dx = dy = 0, landing the copy exactly on the original. Invisible
  //      duplicate, and dragging "the copy" moves the original instead.
  //
  // When the shape is larger than the canvas the window is empty (lo > hi);
  // there is no offset that keeps it whole, so clamping is pointless and we
  // keep the nominal offset rather than making things worse.
  const clampAxis = (d, minV, maxV, extent) => {
    const lo = -minV;          // smallest offset that keeps the low edge on-canvas
    const hi = extent - maxV;  // largest offset that keeps the high edge on-canvas
    if (lo > hi) return d;
    return Math.min(Math.max(d, lo), hi);
  };
  dx = clampAxis(dx, minX, maxX, canvasW);
  dy = clampAxis(dy, minY, maxY, canvasH);

  // Never land exactly on the original. If the clamp took BOTH axes to zero
  // there is no room in the +offset direction, so go the other way -- the
  // window is guaranteed to have room there or the shape fills the canvas
  // exactly, in which case an overlapping copy is unavoidable and honest.
  if (dx === 0 && dy === 0) {
    dx = clampAxis(-offset, minX, maxX, canvasW);
    dy = clampAxis(-offset, minY, maxY, canvasH);
  }

  const move = (pt) => ({ x: pt.x + dx, y: pt.y + dy });
  const curves = {};
  for (const key of Object.keys(shape.curves || {})) curves[key] = move(shape.curves[key]);

  return {
    ...shape,
    id,
    points: shape.points.map(move),
    curves,
  };
}

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

// ---- Cut-outs (holes) -------------------------------------------------------
// A hole is an ordinary shape marked `cutOut: true` (spec 2026-09-30 §5,
// Kent's ruling 11). Nothing is stored about WHICH shape it cuts — that is
// resolved here, by containment, every time, so moving, duplicating or
// deleting shapes can never leave a stale link behind.
export const CUTOUT_NO_PARENT = "Not inside a shape — cuts nothing.";
export const CUTOUT_OVERLAP = "Overlaps another cut-out — cuts nothing.";

function ringBox(ring) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of ring) { if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x; if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y; }
  return { minX, minY, maxX, maxY };
}
function ringsCross(a, b) {
  for (let i = 0; i < a.length; i++) {
    const a1 = a[i], a2 = a[(i + 1) % a.length];
    for (let j = 0; j < b.length; j++) {
      if (segmentsIntersect(a1, a2, b[j], b[(j + 1) % b.length])) return true;
    }
  }
  return false;
}
// Every vertex of `inner` inside `outer`, and no edge of one touching an edge
// of the other. The box test first: most pairs fail it, and this runs on
// every frame of a node drag.
function ringInside(inner, innerBox, outer, outerBox) {
  if (innerBox.minX < outerBox.minX || innerBox.maxX > outerBox.maxX || innerBox.minY < outerBox.minY || innerBox.maxY > outerBox.maxY) return false;
  for (const p of inner) if (!pointInShape(outer, p.x, p.y)) return false;
  return !ringsCross(inner, outer);
}

// -> { parentOf: {cutId: parentId|null}, reasonOf: {cutId: why it cuts
// nothing}, holesOf: {parentId: [cutId...]}, flat: Map(id -> flattened ring) }.
// Parent = the SMALLEST valid non-cut-out shape that contains the cut-out
// (an O's counter drawn over a patch cuts the O, not the patch); an
// equal-area tie (to a relative 1e-9) stays with the EARLIER shape, so
// Duplicate leaves the hole with the original. Two cut-outs of one parent that cross or
// nest: the earlier in the list stands — the engine fills even-odd, so both
// would sew the overlap back in. Shapes without an id take no part.
export function resolveCutOuts(shapes) {
  const list = (shapes || []).filter((s) => s && s.id != null);
  // Null-prototype maps: a shape id is user data, and a plain {} would answer
  // holesOf["constructor"] with a function.
  const parentOf = Object.create(null), reasonOf = Object.create(null), holesOf = Object.create(null);
  // The common case — no cut-out at all — flattens nothing. This runs on every
  // drag frame and every shapesToRegions; callers read `flat` only for ids in
  // holesOf, so an empty Map is all they can ask of it.
  // A column takes no part: it is never a cut-out (a stray flag on one is
  // ignored) and never a solid, however much of the canvas its rails enclose.
  const isCut = (s) => !!s.cutOut && !isColumn(s);
  if (!list.some(isCut)) return { parentOf, reasonOf, holesOf, flat: new Map() };
  const flat = new Map(), box = new Map(), valid = new Map();
  for (const s of list) {
    if (isColumn(s)) continue;
    const ring = flattenShape(s.points, s.curves, true);
    flat.set(s.id, ring);
    box.set(s.id, ringBox(ring));
    valid.set(s.id, shapeIssues(ring).length === 0);
  }
  const solids = list.filter((s) => !s.cutOut && !isColumn(s) && valid.get(s.id));
  const area = new Map(solids.map((s) => [s.id, polygonArea(flat.get(s.id))]));
  for (const c of list) {
    if (!isCut(c)) continue;
    parentOf[c.id] = null;
    const ring = flat.get(c.id);
    if (!valid.get(c.id)) { reasonOf[c.id] = shapeIssues(ring)[0]; continue; }
    let best = null;
    for (const p of solids) {
      if (!ringInside(ring, box.get(c.id), flat.get(p.id), box.get(p.id))) continue;
      // An equal-area tie stays with the EARLIER shape. The one case that
      // produces real ties is Duplicate (a copy 18 px over, same area): the
      // original must keep its hole, and without the epsilon the float noise
      // in two shoelace sums would hand it to either one at random.
      if (!best || area.get(p.id) < area.get(best.id) * (1 - 1e-9)) best = p;
    }
    if (!best) { reasonOf[c.id] = CUTOUT_NO_PARENT; continue; }
    const taken = holesOf[best.id] || [];
    const clash = taken.some((id) => {
      const other = flat.get(id);
      return ringsCross(ring, other)
        || pointInShape(other, ring[0].x, ring[0].y)
        || pointInShape(ring, other[0].x, other[0].y);
    });
    if (clash) { reasonOf[c.id] = CUTOUT_OVERLAP; continue; }
    parentOf[c.id] = best.id;
    holesOf[best.id] = [...taken, c.id];
  }
  return { parentOf, reasonOf, holesOf, flat };
}

// A copy of `shape` marked as a cut-out, or with the mark REMOVED — never
// `cutOut: false`, so an untouched record equals a pre-feature record.
export function withCutOut(shape, on) {
  // A column cannot be a cut-out: handed back untouched, the same reference.
  if (isColumn(shape)) return shape;
  if (on) return { ...shape, cutOut: true };
  const rest = { ...shape };
  delete rest.cutOut;
  return rest;
}

// The one name a shape goes by — list row, assign box, popover heading. A
// shape with a cut-out in it reads Fill whatever it stores: the engine cannot
// satin round a hole, and the name says what will sew.
export function manualShapeName(shape, cut) {
  const n = String(shape.id).replace(/^s/, "");
  if (isColumn(shape)) return `Shape ${n} · Column`;
  if (shape.cutOut) return `Shape ${n} · Cut out`;
  const holed = !!(cut && cut.holesOf && (cut.holesOf[shape.id] || []).length);
  return `Shape ${n} · ${shape.stitchType === "satin" && !holed ? "Satin" : "Fill"}`;
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
// A shape marked `cutOut` emits no region of its own; if it resolves to a
// parent (see resolveCutOuts) its flattened ring arrives as that parent's hole.
export function shapesToRegions(shapes) {
  const regions = [];
  const cut = resolveCutOuts(shapes);
  for (const shape of shapes || []) {
    if (!shape) continue;
    // A column: its rail ring is a truthful `outer` for everything in the
    // engine that reads an outline, and `sewAs` carries the rails the satin is
    // sewn between. Forced satin, no angle (the rails ARE the direction), no
    // holes. Only a column's region has a `sewAs` key — every other region is
    // exactly what it was before columns existed.
    if (isColumn(shape)) {
      if (columnIssues(shape).length) continue;
      const rails = railsFromSpine(flattenShape(shape.points, shape.curves, false), shape.widthPx);
      if (!rails) continue;
      const copy = (ring) => ring.map((p) => ({ x: p.x, y: p.y }));
      regions.push({
        rgb: Array.isArray(shape.colorRgb) ? shape.colorRgb : [20, 20, 20],
        shapes: [{
          id: shape.id == null ? "" : String(shape.id),
          outer: copy(rails.ring),
          holes: [],
          tierOverride: "satin",
          angleOverride: null,
          sewAs: { kind: "column", railA: copy(rails.railA), railB: copy(rails.railB) },
        }],
      });
      continue;
    }
    // A cut-out sews nothing.
    if (shape.cutOut) continue;
    const outer = flattenShape(shape.points, shape.curves, true);
    if (!isValidShape(outer)) continue;
    const angleOverride = (typeof shape.angleDeg === "number" && isFinite(shape.angleDeg)) ? shape.angleDeg : null;
    // "satin"/"fill" are the user's explicit manual choice, forced through
    // digitize.js's tierOverride hook. The explicit value "auto" (preset
    // shape elements, generate.js's "shape" branch) sends NO override,
    // leaving satin-vs-fill to the engine's own width/branch-guard
    // classifier — digitize.js treats an absent/null tierOverride as
    // exactly that. Any OTHER unrecognized value still falls back to
    // "fill", the long-pinned "never silently satin" conservative default
    // for manual mode's garbage-input case.
    const tierOverride =
      shape.stitchType === "satin" ? "satin" :
      shape.stitchType === "auto" ? null : "fill";
    regions.push({
      rgb: Array.isArray(shape.colorRgb) ? shape.colorRgb : [20, 20, 20],
      shapes: [{
        // The Studio's own shape id, so the engine's spans and outlines
        // (design.runs / design.shapeOutlines) can be mapped back to the shape
        // a click landed on. "" when the caller has none.
        id: shape.id == null ? "" : String(shape.id),
        outer: outer.map((p) => ({ x: p.x, y: p.y })),
        holes: (cut.holesOf[shape.id] || []).map((id) => cut.flat.get(id).map((p) => ({ x: p.x, y: p.y }))),
        tierOverride,
        angleOverride,
      }],
    });
  }
  return { regions, pxPerMm: PX_PER_MM };
}
