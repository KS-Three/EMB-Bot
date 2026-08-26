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
        outer: outer.map((p) => ({ x: p.x, y: p.y })),
        holes: [],
        tierOverride,
        angleOverride,
      }],
    });
  }
  return { regions, pxPerMm: PX_PER_MM };
}
