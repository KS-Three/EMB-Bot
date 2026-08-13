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

export function outlineOf(shape) {
  const pts = (shape && (shape.outlineFull || shape.outline)) || [];
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
export function shapeOutlinesInFieldMm(shapes, bboxMm, rotationDeg = 0) {
  const rows = (shapes || []).filter((s) => outlineOf(s));
  if (!rows.length || !bboxMm) return [];

  // y-down (service) -> y-up (field) BEFORE rotating, so the rotation angle
  // means the same thing here as it does to the stitches it must line up with.
  // Flipping afterwards would mirror the rotation and put a non-quadrant
  // outline on the wrong diagonal — the failure a bbox check cannot catch,
  // since a mirrored outline has the identical bounding box.
  const rotated = rows.map((s) => ({
    id: s.id,
    points: rotatePointsDeg(
      outlineOf(s).map(([x, y]) => [x, -y]),
      rotationDeg
    ),
  }));

  const src = bboxOf(rotated.flatMap((r) => r.points));
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
