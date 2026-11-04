// Geometry for the auto-digitize shape overlay. This is the half of the
// feature that can be silently wrong rather than visibly broken — an outline
// that is subtly offset, mirrored, or mis-scaled still LOOKS like an outline —
// so it is tested here, without a browser or a live digitizer service.
import { describe, expect, test } from "vitest";
import {
  createPulseTracker,
  designOutlinesInFieldMm,
  fieldMmToOutlineMm,
  hitOverlay,
  insertNode,
  moveEdge,
  moveNode,
  moveNodes,
  removeNodes,
  nodesInBox,
  ringNodesInBox,
  outlineBBoxMm,
  outlineOf,
  pulseAt,
  pulseFadeAt,
  PULSE_MS,
  rotatePointsDeg,
  shapeOutlinesInFieldMm,
  simplifyRing,
} from "./shapeOverlay.js";
import { boundaryIssues } from "./digitizer.js";

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

  test("an upload's FIRST result pulses when the upload was seen before it", () => {
    // EmbroideryField sees an un-digitized upload with a null key. Without
    // that baseline the first result is a silent first sighting, and a fresh
    // upload digitized with no cue at all (found 2026-10-08).
    const t = createPulseTracker();
    expect(t.seen("e1", null, 0)).toBe(null);
    expect(t.seen("e1", null, 500)).toBe(null);
    expect(t.seen("e1", REV_A, 1000)).toBe(1000);
    expect(t.active(1000)).toBe(true);
  });
});

describe("pulseFadeAt", () => {
  test("is full at the start, gone at PULSE_MS, and never negative", () => {
    expect(pulseFadeAt(0)).toBe(1);
    expect(pulseFadeAt(PULSE_MS / 2)).toBeCloseTo(0.5, 6);
    expect(pulseFadeAt(PULSE_MS)).toBe(0);
    expect(pulseFadeAt(PULSE_MS + 1000)).toBe(0);
    expect(pulseFadeAt(-5)).toBe(0);
  });

  test("stays above zero through every beat, so the cue is not cut off between beats", () => {
    // pulseAt touches 0 between beats; a draw loop keyed on IT would stop
    // there. The fade is what says the window is still open.
    for (let t = 0; t < PULSE_MS; t += 5) expect(pulseFadeAt(t)).toBeGreaterThan(0);
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
//
// Since 2026-11-03 this soft pull (2x the drag distance) is the ALT drag; the
// default is a fixed 3mm neighbourhood, pinned in the next block.
// A circle of 120 vertices, radius 20mm: ~1mm of boundary per vertex, the
// same order of density as a traced photo region.
const DENSE = Array.from({ length: 120 }, (_, i) => {
  const a = (2 * Math.PI * i) / 120;
  return [20 * Math.cos(a), 20 * Math.sin(a)];
});
const movedCount = (before, after) =>
  after.filter(([x, y], i) => Math.hypot(x - before[i][0], y - before[i][1]) > 1e-9).length;
const SOFT = { soft: true };

describe("Alt-drag soft pull (dense, auto-traced rings)", () => {
  test("a drag carries the neighbouring boundary with it", () => {
    const out = moveNode(DENSE, 0, 6, 0, SOFT);
    expect(movedCount(DENSE, out)).toBeGreaterThan(10);
  });

  test("the grabbed vertex takes the FULL delta, neighbours a share of it", () => {
    const out = moveNode(DENSE, 0, 6, 0, SOFT);
    expect(out[0][0] - DENSE[0][0]).toBeCloseTo(6, 9);
    const near = out[2][0] - DENSE[2][0];
    const far = out[8][0] - DENSE[8][0];
    expect(near).toBeGreaterThan(far);
    expect(far).toBeGreaterThan(0);
  });

  test("the pulled stretch widens with the drag — pull further, yield further", () => {
    expect(movedCount(DENSE, moveNode(DENSE, 0, 12, 0, SOFT)))
      .toBeGreaterThan(movedCount(DENSE, moveNode(DENSE, 0, 3, 0, SOFT)));
  });

  test("the far side of the ring never moves, so a pull can never become a MOVE", () => {
    // Requirement 5 (drag the whole shape) is out of scope by Kent's ruling —
    // a translated shape gets a new centroid, and the centroid is what makes
    // shape ids stable across a re-digitize. However hard this is pulled, the
    // opposite side of the ring has to stay put.
    const out = moveNode(DENSE, 0, 500, 500, SOFT);
    const opposite = out[60];
    expect(Math.hypot(opposite[0] - DENSE[60][0], opposite[1] - DENSE[60][1])).toBe(0);
    expect(movedCount(DENSE, out)).toBeLessThan(DENSE.length);
  });

  test("even a tiny nudge moves a sewable stretch, not a needle", () => {
    // Below the floor the added area is too thin to hold a fill row, which is
    // the failure this whole mechanism exists to prevent.
    expect(movedCount(DENSE, moveNode(DENSE, 0, 0.2, 0, SOFT))).toBeGreaterThan(2);
  });

  test("moveEdge pulls from BOTH endpoints and keeps them exactly together", () => {
    const out = moveEdge(DENSE, 0, 0, 4, SOFT);
    expect(out[0][1] - DENSE[0][1]).toBeCloseTo(4, 9);
    expect(out[1][1] - DENSE[1][1]).toBeCloseTo(4, 9);
    expect(movedCount(DENSE, out)).toBeGreaterThan(10);
  });
});

// The default rule (2026-11-03): a FIXED 3mm neighbourhood, whatever the drag.
// Kent's Instagram outer ring has nodes ~5mm apart; the 2x-drag pull moved 9 of
// 36 of them on an 11mm drag ("the entire spline seems to follow").
describe("default drag: fixed 3mm neighbourhood", () => {
  // 36-gon whose chord length is 5mm: radius = 5 / (2 sin(pi/36)).
  const R5 = 5 / (2 * Math.sin(Math.PI / 36));
  const SPARSE = Array.from({ length: 36 }, (_, i) => {
    const a = (2 * Math.PI * i) / 36;
    return [R5 * Math.cos(a), R5 * Math.sin(a)];
  });

  test("a 5mm-spaced ring moves exactly ONE vertex at 1, 11 and 50mm", () => {
    for (const d of [1, 11, 50]) {
      const out = moveNode(SPARSE, 0, d, 0);
      expect(movedCount(SPARSE, out)).toBe(1);
      expect(out[0][0] - SPARSE[0][0]).toBeCloseTo(d, 9);
    }
  });

  test("a ~1mm-spaced ring still moves a small stretch, the grabbed vertex in full", () => {
    const out = moveNode(DENSE, 0, 6, 0);
    const n = movedCount(DENSE, out);
    expect(n).toBeGreaterThan(2);
    expect(n).toBeLessThan(10);
    expect(out[0][0] - DENSE[0][0]).toBeCloseTo(6, 9);
  });

  test("the far side never moves, however hard the pull", () => {
    const out = moveNode(DENSE, 0, 500, 500);
    expect(Math.hypot(out[60][0] - DENSE[60][0], out[60][1] - DENSE[60][1])).toBe(0);
    expect(movedCount(DENSE, out)).toBeLessThan(DENSE.length);
  });

  test("the neighbourhood does not widen with the drag", () => {
    expect(movedCount(DENSE, moveNode(DENSE, 0, 50, 0)))
      .toBe(movedCount(DENSE, moveNode(DENSE, 0, 1, 0)));
  });

  test("moveEdge: both endpoints take the full delta", () => {
    const out = moveEdge(SPARSE, 0, 0, 7);
    expect(out[0][1] - SPARSE[0][1]).toBeCloseTo(7, 9);
    expect(out[1][1] - SPARSE[1][1]).toBeCloseTo(7, 9);
    expect(movedCount(SPARSE, out)).toBe(2);
  });
});

describe("hitOverlay: nearest node wins", () => {
  const TWO = [{ id: "s1", points: [[100, 100], [106, 100], [106, 160], [100, 160]] }];

  test("pointer 2px from the second node of a close pair grabs the second", () => {
    expect(hitOverlay(TWO, 108, 100)).toMatchObject({ kind: "node", index: 1 });
  });

  test("pointer 2px from the first grabs the first", () => {
    expect(hitOverlay(TWO, 98, 100)).toMatchObject({ kind: "node", index: 0 });
  });

  test("an exact tie goes to the lower index", () => {
    expect(hitOverlay(TWO, 103, 100)).toMatchObject({ kind: "node", index: 0 });
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

// ---- hitShapeInterior: which shape is the pointer OVER ---------------------
import { hitShapeInterior } from "./shapeOverlay.js";

describe("hitShapeInterior", () => {
  const outer = { id: "outer", points: [[0, 0], [100, 0], [100, 100], [0, 100]] };
  const inner = { id: "inner", points: [[40, 40], [60, 40], [60, 60], [40, 60]] };
  const far = { id: "far", points: [[200, 200], [220, 200], [220, 220]] };

  test("inside one ring names it; outside every ring is null", () => {
    expect(hitShapeInterior([outer, far], 10, 10)).toEqual({ shapeId: "outer", kind: "interior" });
    expect(hitShapeInterior([outer, far], 150, 150)).toBeNull();
    expect(hitShapeInterior([], 10, 10)).toBeNull();
  });

  test("a shape inside another's hole wins: the smallest containing ring", () => {
    expect(hitShapeInterior([outer, inner], 50, 50).shapeId).toBe("inner");
    expect(hitShapeInterior([inner, outer], 50, 50).shapeId).toBe("inner");
    // and the surround still answers for a point between them
    expect(hitShapeInterior([outer, inner], 20, 80).shapeId).toBe("outer");
  });

  test("a point on the outline itself is inside — the border is the edge", () => {
    expect(hitShapeInterior([outer], 100, 50).shapeId).toBe("outer");
    expect(hitShapeInterior([outer], 0, 0).shapeId).toBe("outer");
  });

  test("a degenerate ring is skipped, not hit", () => {
    expect(hitShapeInterior([{ id: "line", points: [[0, 0], [10, 10]] }], 5, 5)).toBeNull();
  });
});

describe("designOutlinesInFieldMm", () => {
  test("passes engine outlines through untouched and drops what cannot be clicked", () => {
    const design = { shapeOutlines: [
      { id: "s1", points: [[0, 0], [10, 0], [10, 5], [0, 5]], holes: [], dropped: false },
      { id: "s2", points: [[0, 0], [1, 0]], holes: [], dropped: true },      // dropped by the engine
      { id: "",   points: [[0, 0], [10, 0], [10, 5]], holes: [], dropped: false }, // no id -> unaddressable
      { id: "s4", points: [[0, 0], [10, 0]], holes: [], dropped: false },     // under a triangle
    ] };
    expect(designOutlinesInFieldMm(design)).toEqual([
      { id: "s1", points: [[0, 0], [10, 0], [10, 5], [0, 5]] },
    ]);
  });
  test("a design without the field, or no design, is an empty list", () => {
    expect(designOutlinesInFieldMm({ stitches: [] })).toEqual([]);
    expect(designOutlinesInFieldMm(null)).toEqual([]);
  });
});

describe("Reshape mode: several points at once", () => {
  // A 60 mm ring with a vertex every 20 mm, so the 3 mm neighbourhood reaches
  // nobody and every seed moves alone.
  const big = [[0, 0], [20, 0], [40, 0], [60, 0], [60, 20], [60, 40], [60, 60], [40, 60], [20, 60], [0, 60], [0, 40], [0, 20]];

  test("three selected vertices each take the full delta, the rest stay", () => {
    const out = moveNodes(big, [1, 2, 7], 1.5, -2.5);
    for (const i of [1, 2, 7]) expect(out[i]).toEqual([big[i][0] + 1.5, big[i][1] - 2.5]);
    for (let i = 0; i < big.length; i++) if (![1, 2, 7].includes(i)) expect(out[i]).toEqual(big[i]);
  });

  test("never mutates, and ignores indices outside the ring", () => {
    const copy = JSON.parse(JSON.stringify(big));
    const out = moveNodes(big, [0, 99, -1, 1.5], 2, 0);
    expect(big).toEqual(copy);
    expect(out[0]).toEqual([2, 0]);
    expect(out.slice(1)).toEqual(big.slice(1));
  });

  test("exact moves the seeds and not their neighbours, even on a dense ring", () => {
    const dense = Array.from({ length: 40 }, (_, i) => [i * 1, 0]).concat([[39, 10], [0, 10]]);
    const soft = moveNodes(dense, [5], 0.1, 0);
    expect(soft[6][0]).not.toBe(dense[6][0]);          // default: the 3 mm neighbourhood follows
    const exact = moveNodes(dense, [5], 0.1, 0, { exact: true });
    expect(exact[5]).toEqual([5.1, 0]);
    expect(exact.filter((p, i) => i !== 5)).toEqual(dense.filter((p, i) => i !== 5));
  });

  // 2026-11-04 zero falloff: the Studio's bare drag passes { exact: true }, Alt passes { soft: true }.
  test("bare drag (exact) of one vertex on a 1.3 mm-spaced ring moves only that vertex", () => {
    const owl = Array.from({ length: 60 }, (_, i) => [i * 1.3, 0]).concat([[77, 10], [0, 10]]);
    const out = moveNodes(owl, [20], 4, 2, { exact: true });
    expect(out[20]).toEqual([owl[20][0] + 4, 2]);
    expect(out.filter((p, i) => i !== 20)).toEqual(owl.filter((p, i) => i !== 20));
  });

  test("Alt (soft) still pulls the neighbours of the same vertex", () => {
    const owl = Array.from({ length: 60 }, (_, i) => [i * 1.3, 0]).concat([[77, 10], [0, 10]]);
    const out = moveNodes(owl, [20], 4, 2, { soft: true });
    expect(out[19]).not.toEqual(owl[19]);
    expect(out[21]).not.toEqual(owl[21]);
  });

  test("a multi-selection drag (exact) moves each selected point by the full delta", () => {
    const owl = Array.from({ length: 60 }, (_, i) => [i * 1.3, 0]).concat([[77, 10], [0, 10]]);
    const out = moveNodes(owl, [10, 11, 30], -1, 3, { exact: true });
    for (const i of [10, 11, 30]) expect(out[i]).toEqual([owl[i][0] - 1, 3]);
    expect(out.filter((p, i) => ![10, 11, 30].includes(i))).toEqual(owl.filter((p, i) => ![10, 11, 30].includes(i)));
  });

  test("two seeds with overlapping neighbourhoods take the max weight, not the sum", () => {
    const dense = Array.from({ length: 30 }, (_, i) => [i * 1, 0]).concat([[29, 10], [0, 10]]);
    const out = moveNodes(dense, [10, 11], 2, 0);
    expect(out[10][0]).toBe(12);
    expect(out[11][0]).toBe(13);
    for (const i of [9, 12]) expect(out[i][0] - dense[i][0]).toBeLessThanOrEqual(2);
  });
});

describe("removeNodes", () => {
  const hex = [[0, 0], [10, 0], [15, 8], [10, 16], [0, 16], [-5, 8]];
  const area = (r) => r.reduce((a, p, i) => a + (r[(i + 1) % r.length][0] * p[1] - p[0] * r[(i + 1) % r.length][1]), 0) / 2;

  test("drops the chosen vertices and keeps the order of the rest", () => {
    expect(removeNodes(hex, [1, 4])).toEqual([[0, 0], [15, 8], [10, 16], [-5, 8]]);
  });
  test("keeps the winding", () => {
    const after = removeNodes(hex, [2]);
    expect(Math.sign(area(after))).toBe(Math.sign(area(hex)));
  });
  test("refuses under three: null, nothing removed", () => {
    expect(removeNodes([[0, 0], [5, 0], [5, 5]], [0])).toBeNull();
    expect(removeNodes(hex, [0, 1, 2, 3])).toBeNull();
    expect(removeNodes(hex, [0, 1, 2])).toHaveLength(3);          // exactly three left is allowed
  });
  test("an empty or out-of-range list is a copy", () => {
    expect(removeNodes(hex, [])).toEqual(hex);
    expect(removeNodes(hex, [40])).toEqual(hex);
  });
});

describe("nodesInBox (the marquee)", () => {
  const A = { id: "a", points: [[0, 0], [10, 0], [10, 10], [0, 10]] };
  const B = { id: "b", points: [[10, 0], [20, 0], [20, 10], [10, 10]] };
  test("takes every vertex inside, across EVERY shape — a seam's two sides", () => {
    const got = nodesInBox([A, B], 9, -1, 11, 11);
    expect([...got.get("a")].sort()).toEqual([1, 2]);
    expect([...got.get("b")].sort()).toEqual([0, 3]);
  });
  test("any drag direction, edges inclusive, empty shapes left out", () => {
    const got = nodesInBox([A, B], 10, 10, 0, 0);
    expect([...got.get("a")].sort()).toEqual([0, 1, 2, 3]);
    expect(got.get("b")).toEqual(new Set([0, 3]));
    expect(nodesInBox([A], 50, 50, 60, 60).size).toBe(0);
  });
  test("an open outline has no nodes", () => {
    expect(nodesInBox([{ id: "cap", open: true, points: [[1, 1], [2, 2]] }], 0, 0, 5, 5).size).toBe(0);
  });
});

describe("simplifyRing", () => {
  const circle = (n, r) => Array.from({ length: n }, (_, i) => [r * Math.cos((2 * Math.PI * i) / n), r * Math.sin((2 * Math.PI * i) / n)]);
  const distToRing = (p, ring) => {
    let best = Infinity;
    for (let i = 0; i < ring.length; i++) {
      const [ax, ay] = ring[i], [bx, by] = ring[(i + 1) % ring.length];
      const dx = bx - ax, dy = by - ay;
      const t = Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy || 1)));
      best = Math.min(best, Math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy));
    }
    return best;
  };

  test("a 120-vertex 20 mm circle at 0.5 mm drops points and keeps every original within 0.5 mm", () => {
    const ring = circle(120, 10);
    const out = simplifyRing(ring, 0.5);
    expect(out.length).toBeLessThan(ring.length);
    expect(out.length).toBeGreaterThanOrEqual(3);
    for (const p of ring) expect(distToRing(p, out)).toBeLessThanOrEqual(0.5 + 1e-9);
    expect(boundaryIssues(out)).toEqual([]);
  });

  test("a 4-point square is unchanged at any tolerance", () => {
    const sq = [[0, 0], [10, 0], [10, 10], [0, 10]];
    for (const tol of [0.2, 0.5, 1, 3]) expect(simplifyRing(sq, tol)).toEqual(sq);
  });

  test("a ring already under tolerance comes back equal, and never mutates the input", () => {
    const ring = circle(8, 10);
    const copy = ring.map((p) => [...p]);
    expect(simplifyRing(ring, 0.01)).toEqual(ring);
    expect(ring).toEqual(copy);
  });

  test("never below three points, even for a huge tolerance", () => {
    expect(simplifyRing(circle(120, 10), 1000).length).toBeGreaterThanOrEqual(3);
  });
});

describe("hole rings (v1.9)", () => {
  const OUTER = [[-20, -20], [20, -20], [20, 20], [-20, 20]];
  const H0 = [[-5, -5], [5, -5], [5, 5], [-5, 5]];
  const H1 = [[8, 8], [14, 8], [14, 14], [8, 14]];
  const BB = { x0: 0, y0: 0, x1: 40, y1: 40 };
  const holed = { id: "S", outlineFull: OUTER, holesFull: [H0, H1] };

  test("shapeOutlinesInFieldMm carries each hole as its own ring, tagged with the shape id and index", () => {
    const out = shapeOutlinesInFieldMm([holed], BB);
    expect(out.map((o) => [o.id, o.ring ?? "exterior", o.key])).toEqual([["S", "exterior", "S"], ["S", 0, "S#h0"], ["S", 1, "S#h1"]]);
    // the fit is the shell's: hole 0 is centred in the 40 mm box
    const b = bboxOf(out[1].points);
    expect(b.minX).toBeCloseTo(15, 6);
    expect(b.maxX).toBeCloseTo(25, 6);
  });

  test("a pending holes_override wins for drawing; the bbox fit stays on the original outlines", () => {
    const pend = new Map([["S", [[[-1, -1], [1, -1], [1, 1], [-1, 1]]]]]);
    const out = shapeOutlinesInFieldMm([holed], BB, 0, null, pend);
    expect(out.length).toBe(2);
    expect(bboxOf(out[1].points).minX).toBeCloseTo(19, 6);
    expect(shapeOutlinesInFieldMm([holed], BB, 0, null, new Map([["S", []]])).length).toBe(1);
  });

  test("a shape with no holesFull draws only its shell", () => {
    expect(shapeOutlinesInFieldMm([shape("S", OUTER)], BB).length).toBe(1);
  });

  test("hitOverlay reports the ring; between a hole node and a shell node the nearer wins", () => {
    const px = [
      { id: "S", points: [[0, 0], [100, 0], [100, 100], [0, 100]] },
      { id: "S", ring: 0, points: [[4, 4], [60, 4], [60, 60], [4, 60]] },
    ];
    expect(hitOverlay(px, 5, 5).ring).toBe(0);          // 1.4 px from the hole node, 7 from the shell's
    expect(hitOverlay(px, 1, 1).ring).toBe("exterior"); // 1.4 vs 4.2 the other way
    expect(hitOverlay(px, 30, 4)).toMatchObject({ kind: "edge", ring: 0 });
  });

  test("a point inside a hole is not inside the shape", () => {
    const shell = { id: "S", points: [[0, 0], [100, 0], [100, 100], [0, 100]] };
    const hole = { id: "S", ring: 0, points: [[30, 30], [70, 30], [70, 70], [30, 70]] };
    expect(hitShapeInterior([shell, hole], 10, 10)).toEqual({ shapeId: "S", kind: "interior" });
    expect(hitShapeInterior([hole], 50, 50)).toBeNull();
  });

  test("ringNodesInBox takes the points of both rings, keyed by ring; nodesInBox stays shell-only", () => {
    const px = [
      { id: "S", points: [[0, 0], [100, 0], [100, 100], [0, 100]] },
      { id: "S", ring: 0, points: [[4, 4], [60, 4], [60, 60], [4, 60]] },
    ];
    const got = ringNodesInBox(px, -1, -1, 10, 10);
    expect([...got.get("S").get("exterior")]).toEqual([0]);
    expect([...got.get("S").get(0)]).toEqual([0]);
    expect([...nodesInBox(px, -1, -1, 10, 10).get("S")]).toEqual([0]);
  });

  test("fieldMmToOutlineMm round-trips a hole ring through the shell's fit, rotated too", () => {
    for (const rot of [0, 30, 90]) {
      const bb = rot === 0 ? BB : { x0: 3, y0: 4, x1: 43, y1: 44 };
      const [, h0] = shapeOutlinesInFieldMm([holed], bb, rot);
      const back = fieldMmToOutlineMm(h0.points, [holed], bb, rot);
      back.forEach(([x, y], i) => {
        expect(x).toBeCloseTo(H0[i][0], 6);
        expect(y).toBeCloseTo(H0[i][1], 6);
      });
    }
  });

  test("a hole ring takes the same drag rules: one node at 10 mm spacing, the three-point floor per ring", () => {
    const ring = [[0, 0], [10, 0], [10, 10], [0, 10]];
    const moved = moveNode(ring, 0, 1, 1);
    expect(moved[0]).toEqual([1, 1]);
    expect(moved[1]).toEqual([10, 0]);
    expect(removeNodes(ring, [0, 1, 2])).toBeNull();
  });
});
