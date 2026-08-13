// Geometry for the auto-digitize shape overlay. This is the half of the
// feature that can be silently wrong rather than visibly broken — an outline
// that is subtly offset, mirrored, or mis-scaled still LOOKS like an outline —
// so it is tested here, without a browser or a live digitizer service.
import { describe, expect, test } from "vitest";
import {
  createPulseTracker,
  outlineBBoxMm,
  outlineOf,
  pulseAt,
  PULSE_MS,
  rotatePointsDeg,
  shapeOutlinesInFieldMm,
} from "./shapeOverlay.js";

// A 20x10mm rectangle centred on the design origin, in the service's y-down
// mm space. Deliberately non-square so a transposed or mirrored result cannot
// pass by coincidence.
const RECT = [[-10, -5], [10, -5], [10, 5], [-10, 5]];
const shape = (id, points) => ({ id, outlineFull: points });

// The rendered element bbox that rectangle should map onto: same 2:1 aspect,
// +y up, offset well away from the origin so a dropped translation shows up.
const BBOX = { x0: 30, y0: 100, x1: 50, y1: 110 };

function bboxOf(points) {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  return {
    minX: Math.min(...xs), maxX: Math.max(...xs),
    minY: Math.min(...ys), maxY: Math.max(...ys),
  };
}

describe("outlineOf", () => {
  test("prefers outlineFull — `outline` is decimated for a 24px thumbnail", () => {
    // Starting the overlay from `outline` would silently reshape the polygon,
    // the same trap the panel's boundary editor documents.
    const s = { outlineFull: RECT, outline: [[0, 0], [1, 0], [0, 1]] };
    expect(outlineOf(s)).toBe(RECT);
  });

  test("falls back to outline when outlineFull is absent", () => {
    expect(outlineOf({ outline: RECT })).toBe(RECT);
  });

  test("rejects anything that cannot be a ring", () => {
    expect(outlineOf({ outlineFull: [[0, 0], [1, 1]] })).toBe(null);
    expect(outlineOf({ outlineFull: [] })).toBe(null);
    expect(outlineOf(null)).toBe(null);
    expect(outlineOf(undefined)).toBe(null);
  });
});

describe("outlineBBoxMm", () => {
  test("spans every shape", () => {
    const box = outlineBBoxMm([shape("a", RECT), shape("b", [[20, 20], [30, 20], [30, 30]])]);
    expect(box).toEqual({ minX: -10, minY: -5, maxX: 30, maxY: 30 });
  });

  test("is null when nothing has a usable outline", () => {
    expect(outlineBBoxMm([{ outlineFull: [[0, 0]] }])).toBe(null);
    expect(outlineBBoxMm([])).toBe(null);
  });
});

describe("rotatePointsDeg", () => {
  test("quadrant angles are exact, not floating-point noise", () => {
    // buildImportedDesign special-cases these for the same reason: 1e-16 of
    // slop here puts the outline a hair off the stitches it traces.
    expect(rotatePointsDeg([[1, 0]], 90)).toEqual([[0, 1]]);
    expect(rotatePointsDeg([[1, 0]], 180)).toEqual([[-1, 0]]);
    expect(rotatePointsDeg([[1, 0]], 270)).toEqual([[0, -1]]);
  });

  test("0 and 360 are identity, and negatives normalise", () => {
    expect(rotatePointsDeg([[3, 4]], 0)).toEqual([[3, 4]]);
    expect(rotatePointsDeg([[3, 4]], 360)).toEqual([[3, 4]]);
    expect(rotatePointsDeg([[1, 0]], -90)).toEqual([[0, -1]]);
  });

  test("does not mutate its input", () => {
    const src = [[1, 2]];
    rotatePointsDeg(src, 90);
    expect(src).toEqual([[1, 2]]);
  });
});

describe("shapeOutlinesInFieldMm", () => {
  test("maps a shape onto the rendered element's bbox", () => {
    const [out] = shapeOutlinesInFieldMm([shape("s1", RECT)], BBOX);
    expect(out.id).toBe("s1");
    const b = bboxOf(out.points);
    expect(b.minX).toBeCloseTo(30, 6);
    expect(b.maxX).toBeCloseTo(50, 6);
    expect(b.minY).toBeCloseTo(100, 6);
    expect(b.maxY).toBeCloseTo(110, 6);
  });

  test("flips y — the service is y-down, the field is y-up", () => {
    // The point that is TOP in service space (y = -5, most negative) must come
    // back as the top of the field bbox (y = 110, most positive). Getting this
    // backwards mirrors every outline vertically, which a bbox check alone
    // cannot catch.
    const tri = [[-10, -5], [10, 5], [-10, 5]];
    const [out] = shapeOutlinesInFieldMm([shape("s1", tri)], BBOX);
    expect(out.points[0][1]).toBeCloseTo(110, 6);
    expect(out.points[1][1]).toBeCloseTo(100, 6);
  });

  test("preserves point order and count, so nodes stay indexable", () => {
    // The editing slice addresses a node by index against the same array the
    // boundary_override contract round-trips; reordering here would rewire
    // which node a drag moves.
    const [out] = shapeOutlinesInFieldMm([shape("s1", RECT)], BBOX);
    expect(out.points).toHaveLength(RECT.length);
    expect(out.points[0][0]).toBeCloseTo(30, 6);   // the x=-10 corner stays first
  });

  test("scales uniformly rather than stretching each axis", () => {
    // A square outline against a 2:1 bbox must stay square. Fitting the axes
    // independently would distort every shape to fill its element, which looks
    // plausible and is wrong.
    const square = [[-5, -5], [5, -5], [5, 5], [-5, 5]];
    const [out] = shapeOutlinesInFieldMm([shape("s1", square)], BBOX);
    const b = bboxOf(out.points);
    expect(b.maxX - b.minX).toBeCloseTo(b.maxY - b.minY, 6);
  });

  test("shares one transform across shapes, so relative placement survives", () => {
    // Each shape must NOT be fitted to the bbox on its own — that would stack
    // every shape on top of every other.
    const left = shape("l", [[-10, -5], [-6, -5], [-6, 5], [-10, 5]]);
    const right = shape("r", [[6, -5], [10, -5], [10, 5], [6, 5]]);
    const out = shapeOutlinesInFieldMm([left, right], BBOX);
    const lb = bboxOf(out[0].points);
    const rb = bboxOf(out[1].points);
    expect(lb.maxX).toBeLessThan(rb.minX);
    expect(lb.minX).toBeCloseTo(30, 6);
    expect(rb.maxX).toBeCloseTo(50, 6);
  });

  test("a 90-degree rotation swaps the fitted extents", () => {
    const tall = { x0: 0, y0: 0, x1: 10, y1: 20 };
    const [out] = shapeOutlinesInFieldMm([shape("s1", RECT)], tall, 90);
    const b = bboxOf(out.points);
    expect(b.maxX - b.minX).toBeCloseTo(10, 6);
    expect(b.maxY - b.minY).toBeCloseTo(20, 6);
  });

  test("rotation happens after the y-flip, not before", () => {
    // Flipping after rotating mirrors the rotation. A 45-degree outline then
    // lands on the opposite diagonal with an IDENTICAL bounding box, so no
    // extent check can catch it — only a corner's actual position can.
    //
    // Worked through for this fixture, first vertex (-10, -10):
    //   flip then rotate (correct): -> (-10, +10) -> rot45 (-14.14, 0)
    //                                  -> bbox fit  (-10, -5)
    //   rotate then flip (wrong):   -> rot45 (0, -14.14) -> flip (0, +14.14)
    //                                  -> bbox fit  (-5, +10)
    // The two disagree on BOTH axes, so this pins the ordering rather than
    // just the shape.
    const diag = [[-10, -10], [10, 10], [10, -10]];
    const box = { x0: -10, y0: -10, x1: 10, y1: 10 };
    const [out] = shapeOutlinesInFieldMm([shape("s1", diag)], box, 45);
    expect(out.points[0][0]).toBeCloseTo(-10, 3);
    expect(out.points[0][1]).toBeCloseTo(-5, 3);
  });

  test("degenerate input returns nothing rather than NaN geometry", () => {
    expect(shapeOutlinesInFieldMm([], BBOX)).toEqual([]);
    expect(shapeOutlinesInFieldMm([shape("s", RECT)], null)).toEqual([]);
    // A zero-extent bbox would divide by zero and paint NaN, which silently
    // blanks a canvas rather than erroring.
    expect(shapeOutlinesInFieldMm([shape("s", RECT)], { x0: 5, y0: 5, x1: 5, y1: 5 })).toEqual([]);
    // A zero-extent OUTLINE (every point identical) is the same hazard.
    const flat = [[1, 1], [1, 1], [1, 1]];
    expect(shapeOutlinesInFieldMm([shape("s", flat)], BBOX)).toEqual([]);
  });

  test("skips unusable shapes but still draws the rest", () => {
    const out = shapeOutlinesInFieldMm(
      [shape("bad", [[0, 0], [1, 1]]), shape("good", RECT)], BBOX);
    expect(out.map((o) => o.id)).toEqual(["good"]);
  });
});

describe("pulseAt", () => {
  test("is silent before it starts and after it ends", () => {
    expect(pulseAt(0)).toBeCloseTo(0, 6);
    expect(pulseAt(PULSE_MS)).toBe(0);
    expect(pulseAt(PULSE_MS + 1000)).toBe(0);
    expect(pulseAt(-5)).toBe(0);
  });

  test("stays within [0, 1] across the whole window", () => {
    for (let t = 0; t <= PULSE_MS; t += 17) {
      const v = pulseAt(t);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
  });

  test("decays, so it lands softly instead of cutting off mid-throb", () => {
    // Peak of the first pulse should beat the peak of the last.
    let early = 0;
    let late = 0;
    for (let t = 0; t < PULSE_MS / 3; t += 5) early = Math.max(early, pulseAt(t));
    for (let t = (2 * PULSE_MS) / 3; t < PULSE_MS; t += 5) late = Math.max(late, pulseAt(t));
    expect(early).toBeGreaterThan(late);
  });

  test("actually pulses — it is not a monotone fade", () => {
    // A fade would also satisfy the decay test above; this pins that the value
    // comes back UP at least twice, which is what makes it read as a pulse.
    const vals = [];
    for (let t = 0; t < PULSE_MS; t += 10) vals.push(pulseAt(t));
    let rises = 0;
    for (let i = 2; i < vals.length; i++) {
      if (vals[i - 1] < vals[i] && vals[i - 2] >= vals[i - 1]) rises++;
    }
    expect(rises).toBeGreaterThanOrEqual(2);
  });
});

describe("createPulseTracker", () => {
  const REV_A = { shapes: [] };
  const REV_B = { shapes: [] };

  test("a first sighting does NOT pulse", () => {
    // Reopening a saved project must not re-announce shapes the app found
    // days ago. Caught in a real browser — the first version pulsed on every
    // page load, which is both a small lie and a good way to train the user
    // to ignore the cue.
    const t = createPulseTracker();
    expect(t.seen("e1", REV_A, 1000)).toBe(null);
    expect(t.startedAt("e1")).toBe(null);
    expect(t.active(1000)).toBe(false);
  });

  test("a changed result pulses from the moment it changed", () => {
    const t = createPulseTracker();
    t.seen("e1", REV_A, 1000);
    expect(t.seen("e1", REV_B, 5000)).toBe(5000);
    expect(t.active(5000)).toBe(true);
  });

  test("re-seeing the SAME result does not restart the cue", () => {
    // Panning, selecting, and editing an unrelated element all re-run this.
    const t = createPulseTracker();
    t.seen("e1", REV_A, 0);
    t.seen("e1", REV_B, 1000);
    t.seen("e1", REV_B, 1500);
    t.seen("e1", REV_B, 2000);
    expect(t.startedAt("e1")).toBe(1000);
  });

  test("the cue expires on its own", () => {
    const t = createPulseTracker();
    t.seen("e1", REV_A, 0);
    t.seen("e1", REV_B, 1000);
    expect(t.active(1000 + PULSE_MS - 1)).toBe(true);
    expect(t.active(1000 + PULSE_MS)).toBe(false);
  });

  test("elements are tracked independently", () => {
    const t = createPulseTracker();
    t.seen("e1", REV_A, 0);
    t.seen("e2", REV_A, 0);
    t.seen("e1", REV_B, 900);
    expect(t.startedAt("e1")).toBe(900);
    expect(t.startedAt("e2")).toBe(null);
    // One element still pulsing keeps the loop alive for the whole canvas.
    expect(t.active(1000)).toBe(true);
  });

  test("re-digitizing the same element pulses again", () => {
    const t = createPulseTracker();
    t.seen("e1", REV_A, 0);
    t.seen("e1", REV_B, 1000);
    t.seen("e1", REV_A, 9000);   // a third distinct result object
    expect(t.startedAt("e1")).toBe(9000);
  });
});
