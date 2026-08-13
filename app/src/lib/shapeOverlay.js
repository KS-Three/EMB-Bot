// Shape outlines + nodes for auto-digitized elements, drawn over the design
// canvas (Kent's 2026-08-12 direct-manipulation request, requirements 1-3 and
// 7: "Populate Lines around the recognized shapes with nodes ... each outline
// shape/feature should be treated like it's own entity").
//
// The geometry lives here, apart from EmbroideryField.svelte, for one reason:
// the mm->field transform below is the only part of this feature that can be
// silently WRONG rather than visibly broken, and a pure module can be tested
// without a browser or a running digitizer service.
//
// ---------------------------------------------------------------------------
// The coordinate problem, and why this fits a bbox instead of recomputing one
//
// A review shape's `outlineFull` is in the service's own space: millimetres,
// origin at the DESIGN's centre, **y-down** (contract v1.4 — the same space
// `outline_mm` and `boundary_override` already use).
//
// The element on the field went through `EMB.buildImportedDesign`, which
// rotates the decoded stitches, RE-CENTRES them on the rotated bbox, scales to
// `element.sizeMm`, clamps that to the hoop, and applies the placement offset.
// Re-deriving that chain here would be a second implementation of it, and
// `generate.js` is explicit that riding one implementation is the point
// ("scale/hoop-clamp/rotate/offset in one place, no second implementation to
// drift"). A copy would drift on exactly the cases that are hardest to notice:
// a hoop-clamped oversize design, or a non-quadrant rotation.
//
// So this module derives the transform from the RESULT instead. Rotation is
// replicated (it is a pure geometric op, and it changes which bbox the shapes
// should be fitted to), and then a bbox->bbox fit absorbs scale, hoop clamping
// and offset in one step — whatever `buildImportedDesign` actually did, the
// rendered bbox already reflects it. The fit is uniform: one scale factor for
// both axes, because the pipeline never scales anisotropically, and using two
// would silently paper over a real disagreement instead of surfacing it.

// A shape needs at least a triangle to be an outline at all.
const MIN_RING_POINTS = 3;

// How close two points must be to count as the same vertex, in mm. Well below
// anything a user could mean, well above float noise from the mm round-trip.
const SAME_POINT_MM = 1e-6;

export function outlineOf(shape) {
  let pts = (shape && (shape.outlineFull || shape.outline)) || [];
  // Drop an explicitly-closed ring's duplicate final point.
  //
  // The service sends `outline_mm` closed — last point equal to first — and
  // `reviewFromJob` happens to run it through `dedupeRing`. Depending on that
  // is a trap: with the duplicate present, dragging vertex 0 (or the edge
  // that starts at it) moves one copy and leaves the other behind, so the ring
  // crosses itself and `boundaryIssues` rejects the edit. The user sees a drag
  // that silently snaps back. Found in a real browser, 2026-08-13.
  //
  // Every ring here is implicitly closed (the draw path closes the path, the
  // hit test wraps modulo length), so the duplicate carries no information —
  // it only creates a vertex that cannot be moved.
  const n = pts.length;
  if (n >= 2) {
    const a = pts[0];
    const b = pts[n - 1];
    if (Math.abs(a[0] - b[0]) < SAME_POINT_MM && Math.abs(a[1] - b[1]) < SAME_POINT_MM) {
      pts = pts.slice(0, n - 1);
    }
  }
  return pts.length >= MIN_RING_POINTS ? pts : null;
}

// Bounding box over every shape's outline, in the service's own mm space.
// Shapes that are hidden (`stitched === false`, or deleted by the user) still
// count: the transform must not shift when a shape is toggled off, or every
// remaining outline would jump.
export function outlineBBoxMm(shapes) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const s of shapes || []) {
    const pts = outlineOf(s);
    if (!pts) continue;
    for (const [x, y] of pts) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (!isFinite(minX)) return null;
  return { minX, minY, maxX, maxY };
}

// Rotate about the origin. Quadrant angles get exact values for the same
// reason `buildImportedDesign` special-cases them: Math.sin(Math.PI) leaves
// ~1e-16 of noise, which here would show up as an outline sitting a hair off
// the stitches it is supposed to trace.
const QUAD = { 0: [1, 0], 90: [0, 1], 180: [-1, 0], 270: [0, -1] };

export function rotatePointsDeg(points, deg) {
  const rot = (((deg || 0) % 360) + 360) % 360;
  if (rot === 0) return points.map(([x, y]) => [x, y]);
  const rad = (rot * Math.PI) / 180;
  const cos = QUAD[rot] ? QUAD[rot][0] : Math.cos(rad);
  const sin = QUAD[rot] ? QUAD[rot][1] : Math.sin(rad);
  return points.map(([x, y]) => [x * cos - y * sin, x * sin + y * cos]);
}

function bboxOf(points) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of points) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return { minX, minY, maxX, maxY };
}

/**
 * Field-space (mm, +y UP — `bboxMm`'s convention) outlines for one digitized
 * element's shapes.
 *
 * @param shapes      review rows (`reviewFromJob`'s output)
 * @param bboxMm      the element's RENDERED bbox, from generateAll's
 *                    perElement — {x0, y0, x1, y1}, +y up
 * @param rotationDeg the element's rotation, applied the same way
 *                    buildImportedDesign applies it
 * @returns [{ id, points: [[x, y], ...] }], empty when there is nothing
 *          trustworthy to draw
 */
export function shapeOutlinesInFieldMm(shapes, bboxMm, rotationDeg = 0, pendingById = null) {
  const rows = (shapes || []).filter((s) => outlineOf(s));
  if (!rows.length || !bboxMm) return [];

  // A hand edit lives in `shapeOverrides.boundary_override` until the next
  // re-digitize folds it into the review. Drawing straight from `outlineFull`
  // would make a just-dragged node snap back the instant the pointer came up,
  // and the edit would look lost even though it was saved. So a pending
  // override wins for DRAWING — while the transform below is still fitted to
  // the ORIGINAL outlines, so editing one shape cannot shift every other
  // shape on the canvas.
  const ringFor = (s) => {
    const pend = pendingById && pendingById.get ? pendingById.get(s.id) : null;
    return Array.isArray(pend) && pend.length >= MIN_RING_POINTS ? pend : outlineOf(s);
  };

  // y-down (service) -> y-up (field) BEFORE rotating, so the rotation angle
  // means the same thing here as it does to the stitches it must line up with.
  // Flipping afterwards would mirror the rotation and put a non-quadrant
  // outline on the wrong diagonal — the failure a bbox check cannot catch,
  // since a mirrored outline has the identical bounding box.
  const rotated = rows.map((s) => ({
    id: s.id,
    points: rotatePointsDeg(
      ringFor(s).map(([x, y]) => [x, -y]),
      rotationDeg
    ),
  }));

  // Fitted from the ORIGINAL outlines, never from the pending edits — see
  // ringFor above. An edit that moved the fit would drag every other shape
  // sideways as a side effect.
  const src = bboxOf(
    rows.flatMap((s) =>
      rotatePointsDeg(outlineOf(s).map(([x, y]) => [x, -y]), rotationDeg))
  );
  const srcW = src.maxX - src.minX;
  const srcH = src.maxY - src.minY;
  const dstW = Math.abs(bboxMm.x1 - bboxMm.x0);
  const dstH = Math.abs(bboxMm.y1 - bboxMm.y0);
  if (!(srcW > 1e-9) || !(srcH > 1e-9) || !(dstW > 1e-9) || !(dstH > 1e-9)) {
    return [];
  }

  // One uniform scale. The two axes should already agree (the pipeline scales
  // uniformly); the smaller factor keeps the outlines inside the rendered
  // artwork if they ever disagree, so a mismatch shows up as a visible inset
  // rather than as outlines hanging off the edge of the design.
  const scale = Math.min(dstW / srcW, dstH / srcH);
  const srcCx = (src.minX + src.maxX) / 2;
  const srcCy = (src.minY + src.maxY) / 2;
  const dstCx = (bboxMm.x0 + bboxMm.x1) / 2;
  const dstCy = (bboxMm.y0 + bboxMm.y1) / 2;

  return rotated.map((r) => ({
    id: r.id,
    points: r.points.map(([x, y]) => [
      dstCx + (x - srcCx) * scale,
      dstCy + (y - srcCy) * scale,
    ]),
  }));
}

// ---------------------------------------------------------------------------
// The pulse cue (requirement 2: "Let's have them 'pulse' for the first few
// seconds"). An attention cue that the app FOUND these shapes — not a
// permanent decoration, so it has to end on its own.

export const PULSE_MS = 2600;
// Three pulses over that window reads as a deliberate "look here" rather than
// a spinner or a fault indicator.
const PULSE_CYCLES = 3;

/**
 * Pulse strength at `elapsed` ms, in [0, 1]. 0 once the cue is over, so a
 * caller can treat "returns 0" as "stop animating" without a second clock.
 *
 * The envelope decays as it goes: each pulse is weaker than the last, which
 * lands the animation softly on the resting state instead of cutting off
 * mid-throb.
 */
export function pulseAt(elapsedMs) {
  if (!(elapsedMs >= 0) || elapsedMs >= PULSE_MS) return 0;
  const t = elapsedMs / PULSE_MS;
  const wave = 0.5 - 0.5 * Math.cos(2 * Math.PI * PULSE_CYCLES * t);
  return wave * (1 - t);
}

/**
 * Decides WHEN the cue fires. Split out from the component because the rule is
 * a judgement call rather than a mechanism, and getting it wrong is invisible
 * in a screenshot.
 *
 * The rule: pulse when a digitize produces a NEW result — not when an
 * already-digitized element merely comes into view. Reopening a saved project
 * would otherwise re-announce shapes the app found days ago, and the cue means
 * "I just found these", so firing it on load is a small lie that also trains
 * the user to ignore it. Caught in a real browser (2026-08-12): the first
 * version pulsed on every page load.
 *
 * Usage: one tracker per component instance; call `seen(id, key, now)` on every
 * change and it returns the pulse start time for that element, or null.
 */
export function createPulseTracker() {
  const keys = new Map();
  const starts = new Map();
  return {
    /** -> pulse start time for this element, or null if it should not pulse. */
    seen(id, key, now) {
      const known = keys.has(id);
      const changed = keys.get(id) !== key;
      keys.set(id, key);
      // First sighting establishes the baseline silently. Only a CHANGE after
      // that is a fresh digitize.
      if (known && changed) starts.set(id, now);
      return starts.has(id) ? starts.get(id) : null;
    },
    startedAt(id) {
      return starts.has(id) ? starts.get(id) : null;
    },
    /** True while any element's cue is still running. */
    active(now) {
      for (const t of starts.values()) if (now - t < PULSE_MS) return true;
      return false;
    },
  };
}

// ---------------------------------------------------------------------------
// Direct manipulation (Kent's requirements 4 and 4b: "I want the ability to
// manually move the nodes or lines to manually edit the auto digitized
// shape/feature (add nodes, move lines ...)").
//
// Pure, and in canvas-PIXEL space on the way in: hit radii are a property of
// the pointing device, not of the design, so a node must stay equally easy to
// grab at any zoom. The caller converts back to mm before writing an override.

// Grab radii, canvas px. The node radius is deliberately larger than the dot
// it selects — the same forgiveness the element-resize handles already use.
export const NODE_GRAB_PX = 9;
export const EDGE_GRAB_PX = 6;

function distToSegment(px, py, ax, ay, bx, by) {
  const vx = bx - ax;
  const vy = by - ay;
  const len2 = vx * vx + vy * vy;
  // t is where the perpendicular from the point lands along the segment,
  // clamped so a point past either END measures to that endpoint rather than
  // to the infinite line — otherwise an edge would grab far outside itself.
  const t = len2 <= 1e-12 ? 0 : Math.max(0, Math.min(1, ((px - ax) * vx + (py - ay) * vy) / len2));
  const cx = ax + t * vx;
  const cy = ay + t * vy;
  return { dist: Math.hypot(px - cx, py - cy), t, x: cx, y: cy };
}

/**
 * What is under the pointer, in one pass over the drawn outlines.
 *
 * @param outlinesPx [{ id, points: [[xPx, yPx], ...] }] — already projected
 * @returns { shapeId, kind: "node" | "edge", index, atPx } or null
 *
 * Nodes beat edges everywhere, not just when strictly nearer: a node sits ON
 * two edges, so a distance comparison would hand a dead-centre node hit to
 * whichever edge happened to round smaller, and dragging a node is both the
 * more common intent and the harder target.
 */
export function hitOverlay(outlinesPx, px, py) {
  let bestEdge = null;
  for (const o of outlinesPx) {
    const pts = o.points;
    for (let i = 0; i < pts.length; i++) {
      const d = Math.hypot(px - pts[i][0], py - pts[i][1]);
      if (d <= NODE_GRAB_PX) {
        return { shapeId: o.id, kind: "node", index: i, atPx: [pts[i][0], pts[i][1]] };
      }
    }
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i];
      const b = pts[(i + 1) % pts.length];
      const s = distToSegment(px, py, a[0], a[1], b[0], b[1]);
      if (s.dist <= EDGE_GRAB_PX && (!bestEdge || s.dist < bestEdge.dist)) {
        bestEdge = { shapeId: o.id, kind: "edge", index: i, atPx: [s.x, s.y], dist: s.dist };
      }
    }
  }
  if (!bestEdge) return null;
  const { dist, ...hit } = bestEdge;
  return hit;
}

/** Move one vertex by a delta. Returns a new ring; never mutates. */
export function moveNode(points, index, dx, dy) {
  return points.map(([x, y], i) => (i === index ? [x + dx, y + dy] : [x, y]));
}

/**
 * Move a whole EDGE by a delta — both of its endpoints together, so the
 * segment translates instead of rotating about one end. This is requirement
 * 4b, and it exists nowhere else in the codebase: the panel editor moves
 * vertices only.
 */
export function moveEdge(points, index, dx, dy) {
  const j = (index + 1) % points.length;
  return points.map(([x, y], i) =>
    i === index || i === j ? [x + dx, y + dy] : [x, y]
  );
}

/**
 * Insert a vertex on edge `index`, at `at` (a point already on or near that
 * edge). Inserting AFTER `index` is what keeps the ring's winding intact —
 * inserting before would reverse the two endpoints' order relative to the
 * rest of the ring.
 */
export function insertNode(points, index, at) {
  const out = points.map(([x, y]) => [x, y]);
  out.splice(index + 1, 0, [at[0], at[1]]);
  return out;
}

/**
 * Field mm -> the service's own outline space (design-centre origin, y-down),
 * which is what `boundary_override` must be written in.
 *
 * The inverse of `shapeOutlinesInFieldMm`'s fit. Rotation is inverted too, so
 * a hand edit on a rotated element lands where the pointer was rather than
 * spun by the element's own angle — the failure mode that would make editing
 * a rotated design feel broken while looking fine on an unrotated one.
 */
export function fieldMmToOutlineMm(pointsFieldMm, shapes, bboxMm, rotationDeg = 0) {
  const rows = (shapes || []).filter((s) => outlineOf(s));
  if (!rows.length || !bboxMm) return null;
  const rotated = rows.flatMap((s) =>
    rotatePointsDeg(outlineOf(s).map(([x, y]) => [x, -y]), rotationDeg)
  );
  const src = bboxOf(rotated);
  const srcW = src.maxX - src.minX;
  const srcH = src.maxY - src.minY;
  const dstW = Math.abs(bboxMm.x1 - bboxMm.x0);
  const dstH = Math.abs(bboxMm.y1 - bboxMm.y0);
  if (!(srcW > 1e-9) || !(srcH > 1e-9) || !(dstW > 1e-9) || !(dstH > 1e-9)) return null;

  const scale = Math.min(dstW / srcW, dstH / srcH);
  if (!(scale > 1e-12)) return null;
  const srcCx = (src.minX + src.maxX) / 2;
  const srcCy = (src.minY + src.maxY) / 2;
  const dstCx = (bboxMm.x0 + bboxMm.x1) / 2;
  const dstCy = (bboxMm.y0 + bboxMm.y1) / 2;

  return pointsFieldMm.map(([x, y]) => {
    const rx = srcCx + (x - dstCx) / scale;
    const ry = srcCy + (y - dstCy) / scale;
    const [ux, uy] = rotatePointsDeg([[rx, ry]], -rotationDeg)[0];
    return [ux, -uy];   // back to y-down
  });
}
