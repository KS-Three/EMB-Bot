// Geometry for the auto-digitize shape overlay. This is the half of the
// feature that can be silently wrong rather than visibly broken — an outline
// that is subtly offset, mirrored, or mis-scaled still LOOKS like an outline —
// so it is tested here, without a browser or a live digitizer service.
import { describe, expect, test } from "vitest";
import {
  createPulseTracker,
  fieldMmToOutlineMm,
  hitOverlay,
  insertNode,
  moveEdge,
  moveNode,
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

// --- Direct manipulation (requirements 4 and 4b) -----------------------------

describe("hitOverlay", () => {
  // A 100x100px square in canvas pixels, corners at the nice round numbers.
  const SQ = [{ id: "s1", points: [[100, 100], [200, 100], [200, 200], [100, 200]] }];

  test("grabs a node when the pointer is near a vertex", () => {
    const h = hitOverlay(SQ, 102, 103);
    expect(h).toMatchObject({ shapeId: "s1", kind: "node", index: 0 });
  });

  test("grabs an edge when the pointer is near a segment but no vertex", () => {
    const h = hitOverlay(SQ, 150, 102);
    expect(h).toMatchObject({ shapeId: "s1", kind: "edge", index: 0 });
    expect(h.atPx[0]).toBeCloseTo(150, 6);
    expect(h.atPx[1]).toBeCloseTo(100, 6);
  });

  test("the closing edge is hit-testable, not just the ones between listed points", () => {
    // Edge 3 runs from the last point back to the first. An implementation
    // that loops `i < n - 1` silently makes one side of every shape dead.
    const h = hitOverlay(SQ, 100, 150);
    expect(h).toMatchObject({ kind: "edge", index: 3 });
  });

  test("a node beats an edge it sits on", () => {
    // A vertex is ON two edges, so a pure distance comparison could hand a
    // dead-centre node hit to whichever edge rounded smaller.
    const h = hitOverlay(SQ, 200, 200);
    expect(h.kind).toBe("node");
    expect(h.index).toBe(2);
  });

  test("misses cleanly when the pointer is nowhere near", () => {
    expect(hitOverlay(SQ, 150, 150)).toBe(null);   // dead centre, inside
    expect(hitOverlay(SQ, 400, 400)).toBe(null);   // far outside
    expect(hitOverlay([], 100, 100)).toBe(null);
  });

  test("an edge does not grab past its own endpoints", () => {
    // Measuring to the infinite LINE instead of the segment would make this
    // point — 50px beyond the corner, but collinear with the top edge — a hit.
    expect(hitOverlay(SQ, 250, 100)).toBe(null);
  });

  test("picks the nearest edge when two are in range", () => {
    const h = hitOverlay(SQ, 197, 150);
    expect(h).toMatchObject({ kind: "edge", index: 1 });
  });
});

describe("node and edge editing", () => {
  const RING = [[0, 0], [10, 0], [10, 10], [0, 10]];

  test("moveNode moves exactly one vertex when its neighbours are far away", () => {
    // A 3.6mm drag pulls 7.2mm of boundary; this ring's vertices are 10mm
    // apart, so nothing else is in range. Sparse, hand-drawn-scale geometry
    // keeps the plain one-vertex behaviour it always had.
    expect(moveNode(RING, 1, 3, -2)).toEqual([[0, 0], [13, -2], [10, 10], [0, 10]]);
  });

  test("moveEdge translates BOTH endpoints, so the segment does not pivot", () => {
    // Requirement 4b. Moving one end would rotate the edge instead of
    // sliding it, which is what "move lines" plainly does not mean.
    expect(moveEdge(RING, 1, 0, 5)).toEqual([[0, 0], [10, 5], [10, 15], [0, 10]]);
  });

  test("moveEdge wraps around the closing segment", () => {
    expect(moveEdge(RING, 3, 1, 0)).toEqual([[1, 0], [10, 0], [10, 10], [1, 10]]);
  });

  test("insertNode puts the new vertex AFTER its edge, preserving winding", () => {
    // Inserting before would swap the two endpoints' order relative to the
    // rest of the ring, quietly reversing part of the boundary.
    expect(insertNode(RING, 0, [5, 0])).toEqual([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10]]);
  });

  test("insertNode on the closing edge appends rather than corrupting the ring", () => {
    expect(insertNode(RING, 3, [0, 5])).toEqual([...RING, [0, 5]]);
  });

  test("none of the edit ops mutate their input", () => {
    const src = RING.map((p) => [...p]);
    moveNode(src, 0, 9, 9);
    moveEdge(src, 0, 9, 9);
    insertNode(src, 0, [9, 9]);
    expect(src).toEqual(RING);
  });
});

// ---------------------------------------------------------------------------
// Proportional dragging on DENSE outlines — the auto-traced case.
//
// A one-vertex move is fine on hand-drawn geometry and useless on a traced
// photo outline: `owl_kent.jpg`'s body region carries 346 vertices around a
// 458mm perimeter, so one vertex owns ~1.3mm of boundary and dragging it adds
// a needle. Measured against the real pipeline 2026-08-13, a 6mm single-vertex
// pull there grew the polygon by 7mm² and put ZERO stitches in the area it
// added — the outline moved and the stitching did not. These tests pin the
// falloff that fixes it, and the two limits that keep it from becoming
// something else.
describe("proportional dragging (dense, auto-traced rings)", () => {
  // A circle of 120 vertices, radius 20mm: ~1mm of boundary per vertex, the
  // same order of density as a traced photo region.
  const DENSE = Array.from({ length: 120 }, (_, i) => {
    const a = (2 * Math.PI * i) / 120;
    return [20 * Math.cos(a), 20 * Math.sin(a)];
  });
  const movedCount = (before, after) =>
    after.filter(([x, y], i) => Math.hypot(x - before[i][0], y - before[i][1]) > 1e-9).length;

  test("a drag carries the neighbouring boundary with it", () => {
    const out = moveNode(DENSE, 0, 6, 0);
    expect(movedCount(DENSE, out)).toBeGreaterThan(10);
  });

  test("the grabbed vertex takes the FULL delta, neighbours a share of it", () => {
    const out = moveNode(DENSE, 0, 6, 0);
    expect(out[0][0] - DENSE[0][0]).toBeCloseTo(6, 9);
    const near = out[2][0] - DENSE[2][0];
    const far = out[8][0] - DENSE[8][0];
    expect(near).toBeGreaterThan(far);
    expect(far).toBeGreaterThan(0);
  });

  test("the pulled stretch widens with the drag — pull further, yield further", () => {
    expect(movedCount(DENSE, moveNode(DENSE, 0, 12, 0)))
      .toBeGreaterThan(movedCount(DENSE, moveNode(DENSE, 0, 3, 0)));
  });

  test("the far side of the ring never moves, so a pull can never become a MOVE", () => {
    // Requirement 5 (drag the whole shape) is out of scope by Kent's ruling —
    // a translated shape gets a new centroid, and the centroid is what makes
    // shape ids stable across a re-digitize. However hard this is pulled, the
    // opposite side of the ring has to stay put.
    const out = moveNode(DENSE, 0, 500, 500);
    const opposite = out[60];
    expect(Math.hypot(opposite[0] - DENSE[60][0], opposite[1] - DENSE[60][1])).toBe(0);
    expect(movedCount(DENSE, out)).toBeLessThan(DENSE.length);
  });

  test("even a tiny nudge moves a sewable stretch, not a needle", () => {
    // Below the floor the added area is too thin to hold a fill row, which is
    // the failure this whole mechanism exists to prevent.
    expect(movedCount(DENSE, moveNode(DENSE, 0, 0.2, 0))).toBeGreaterThan(2);
  });

  test("moveEdge pulls from BOTH endpoints and keeps them exactly together", () => {
    const out = moveEdge(DENSE, 0, 0, 4);
    expect(out[0][1] - DENSE[0][1]).toBeCloseTo(4, 9);
    expect(out[1][1] - DENSE[1][1]).toBeCloseTo(4, 9);
    expect(movedCount(DENSE, out)).toBeGreaterThan(10);
  });
});

describe("fieldMmToOutlineMm", () => {
  // The round trip is where a coordinate bug hides: forward-only tests pass
  // happily while an edit lands somewhere other than the pointer.
  const shapes = [shape("s1", RECT)];

  test("round-trips a point back to where it started", () => {
    const [fwd] = shapeOutlinesInFieldMm(shapes, BBOX);
    const back = fieldMmToOutlineMm(fwd.points, shapes, BBOX);
    for (let i = 0; i < RECT.length; i++) {
      expect(back[i][0]).toBeCloseTo(RECT[i][0], 6);
      expect(back[i][1]).toBeCloseTo(RECT[i][1], 6);
    }
  });

  test("round-trips under rotation too", () => {
    // A rotated element is exactly where a forgotten inverse shows up: the
    // outline draws correctly, and every edit lands spun by the element angle.
    for (const deg of [90, 180, 270, 37]) {
      const [fwd] = shapeOutlinesInFieldMm(shapes, BBOX, deg);
      const back = fieldMmToOutlineMm(fwd.points, shapes, BBOX, deg);
      for (let i = 0; i < RECT.length; i++) {
        expect(back[i][0]).toBeCloseTo(RECT[i][0], 6);
        expect(back[i][1]).toBeCloseTo(RECT[i][1], 6);
      }
    }
  });

  test("a dragged node maps back to a proportional move in service space", () => {
    // BBOX is 20mm wide for a 20mm-wide RECT, so the scale here is 1:1 and a
    // 2mm field move must read as a 2mm service move — with y NEGATED, since
    // the two spaces disagree about which way is up.
    const [fwd] = shapeOutlinesInFieldMm(shapes, BBOX);
    const moved = moveNode(fwd.points, 0, 2, 3);
    const back = fieldMmToOutlineMm(moved, shapes, BBOX);
    expect(back[0][0]).toBeCloseTo(RECT[0][0] + 2, 6);
    expect(back[0][1]).toBeCloseTo(RECT[0][1] - 3, 6);
  });

  test("declines rather than returning NaN when there is no usable transform", () => {
    expect(fieldMmToOutlineMm([[0, 0]], [], BBOX)).toBe(null);
    expect(fieldMmToOutlineMm([[0, 0]], shapes, null)).toBe(null);
    expect(fieldMmToOutlineMm([[0, 0]], shapes, { x0: 1, y0: 1, x1: 1, y1: 1 })).toBe(null);
  });
});

describe("pending boundary overrides", () => {
  const A = shape("a", [[-10, -5], [0, -5], [0, 5], [-10, 5]]);
  const B = shape("b", [[2, -5], [10, -5], [10, 5], [2, 5]]);
  const BOX = { x0: 0, y0: 0, x1: 20, y1: 10 };

  test("a pending override is what gets drawn", () => {
    // Without this, a just-dragged node snaps back to the last digitized
    // outline the moment the pointer comes up — the edit is saved but looks
    // lost, which is worse than not saving it.
    const edited = [[-10, -5], [0, -5], [0, 0], [-10, 5]];
    const out = shapeOutlinesInFieldMm([A, B], BOX, 0, new Map([["a", edited]]));
    const plain = shapeOutlinesInFieldMm([A, B], BOX, 0);
    expect(out[0].points).not.toEqual(plain[0].points);
    expect(out[1].points).toEqual(plain[1].points);   // untouched shape unmoved
  });

  test("the transform stays fitted to the ORIGINAL outlines", () => {
    // Fitting to the edited ring would let dragging one node shift every
    // other shape on the canvas sideways — an edit with spooky action at a
    // distance. Shape B must land in exactly the same place either way.
    const wild = [[-400, -400], [400, -400], [400, 400], [-400, 400]];
    const out = shapeOutlinesInFieldMm([A, B], BOX, 0, new Map([["a", wild]]));
    const plain = shapeOutlinesInFieldMm([A, B], BOX, 0);
    expect(out[1].points).toEqual(plain[1].points);
  });

  test("a malformed or too-short override is ignored, not drawn", () => {
    const plain = shapeOutlinesInFieldMm([A, B], BOX, 0);
    for (const bad of [[[0, 0], [1, 1]], [], null, "nope"]) {
      const out = shapeOutlinesInFieldMm([A, B], BOX, 0, new Map([["a", bad]]));
      expect(out[0].points).toEqual(plain[0].points);
    }
  });

  test("no pending map at all behaves exactly as before", () => {
    const plain = shapeOutlinesInFieldMm([A, B], BOX, 0);
    expect(shapeOutlinesInFieldMm([A, B], BOX, 0, null)).toEqual(plain);
    expect(shapeOutlinesInFieldMm([A, B], BOX, 0, new Map())).toEqual(plain);
  });
});

describe("explicitly-closed rings", () => {
  // The service sends outline_mm CLOSED (last point == first). With the
  // duplicate left in, dragging vertex 0 — or the edge starting at it — moves
  // one copy and strands the other, so the ring self-crosses and the edit is
  // silently rejected. Found in a real browser 2026-08-13, on edge 0 of a
  // digitized square.
  const CLOSED = [[-10, -5], [10, -5], [10, 5], [-10, 5], [-10, -5]];

  test("the duplicate closing point is dropped", () => {
    expect(outlineOf({ outlineFull: CLOSED })).toHaveLength(4);
    expect(outlineOf({ outlineFull: CLOSED })).toEqual(RECT);
  });

  test("an open ring is left exactly as it is", () => {
    expect(outlineOf({ outlineFull: RECT })).toEqual(RECT);
  });

  test("a ring that is only 3 points once closed is still usable", () => {
    const tri = [[0, 0], [4, 0], [2, 3], [0, 0]];
    expect(outlineOf({ outlineFull: tri })).toEqual([[0, 0], [4, 0], [2, 3]]);
  });

  test("a degenerate closed ring is rejected, not turned into a 2-point line", () => {
    expect(outlineOf({ outlineFull: [[0, 0], [1, 1], [0, 0]] })).toBe(null);
  });

  test("moving edge 0 of a closed ring no longer self-crosses", () => {
    // The end-to-end symptom, at the unit level: with the duplicate present
    // this moved 2 of 5 points and left the 5th behind.
    const ring = outlineOf({ outlineFull: CLOSED });
    const moved = moveEdge(ring, 0, 0, 4);
    expect(moved).toEqual([[-10, -1], [10, -1], [10, 5], [-10, 5]]);
  });
});
