// Pen strokes (spec docs/superpowers/specs/2026-11-13-pen-auto-branch-design.md
// section 2). penStroke.js reaches the engine through manualTrace -> emb.js, so
// the engine is loaded before the module is imported, as manualTrace.spec.js
// does it.
import { test, expect, describe, beforeAll, beforeEach } from "vitest";
import { createRequire } from "node:module";
import {
  flattenShape, distToSegment, runIssues, columnIssues, COLUMN_DEFAULT_MM, PX_PER_MM,
} from "./manualShapes.js";

let pen;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  pen = await import("./penStroke.js");
});
beforeEach(() => pen.resetPenMemory());

// ---- Fixtures: a true path, and the same path as a jittery hand reports it --
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
// Ends are left exact: a stroke's ends are where the pointer went down and up.
function jitter(truth, amp, seed) {
  const r = rng(seed);
  return truth.map((p, i) => (i === 0 || i === truth.length - 1) ? p : ({ x: p.x + (r() * 2 - 1) * amp, y: p.y + (r() * 2 - 1) * amp }));
}
function arc(R, deg, step = 3) {
  const n = Math.ceil((R * deg * Math.PI / 180) / step), o = [];
  for (let i = 0; i <= n; i++) { const a = (deg * Math.PI / 180) * i / n; o.push({ x: 300 + R * Math.cos(a), y: 200 + R * Math.sin(a) }); }
  return o;
}
function sine() { const o = []; for (let x = 0; x <= 400; x += 3) o.push({ x: 100 + x, y: 200 + 40 * Math.sin(2 * Math.PI * x / 200) }); return o; }
// Two straight legs meeting at a 150 degree turn: a leaf tip.
function vee() {
  const o = [];
  for (let t = 0; t <= 40; t++) o.push({ x: 200 + t * 3 * Math.cos(1.3), y: 320 - t * 3 * Math.sin(1.3) });
  const tip = o[40];
  for (let t = 1; t <= 40; t++) o.push({ x: tip.x + t * 3 * Math.cos(0.78), y: tip.y + t * 3 * Math.sin(1.82) });
  return { pts: o, tip };
}
function worstErr(truth, poly) {
  let worst = 0;
  for (const p of truth) {
    let d = Infinity;
    for (let i = 0; i + 1 < poly.length; i++) d = Math.min(d, distToSegment(p, poly[i], poly[i + 1]));
    worst = Math.max(worst, d);
  }
  return worst;
}
// Worst change of direction at an interior anchor, degrees: the tangent a
// segment arrives on against the tangent the next one leaves on.
function worstKink(points, curves) {
  let worst = 0;
  for (let i = 1; i + 1 < points.length; i++) {
    const inC = curves[i - 1] || points[i - 1], outC = curves[i] || points[i + 1];
    const a = Math.atan2(points[i].y - inC.y, points[i].x - inC.x), b = Math.atan2(outC.y - points[i].y, outC.x - points[i].x);
    let d = Math.abs(a - b) * 180 / Math.PI; if (d > 180) d = 360 - d;
    worst = Math.max(worst, d);
  }
  return worst;
}
const flat = (r) => flattenShape(r.points, r.curves, false);

describe("the gesture's thresholds", () => {
  test("a press is a stroke only past the dead zone", () => {
    expect(pen.pastPenDeadZone({ x: 10, y: 10 }, { x: 13, y: 12 })).toBe(false); // 3.6 px
    expect(pen.pastPenDeadZone({ x: 10, y: 10 }, { x: 14, y: 10 })).toBe(false); // exactly 4
    expect(pen.pastPenDeadZone({ x: 10, y: 10 }, { x: 14.1, y: 10 })).toBe(true);
  });
  test("pathLength adds the segments", () => {
    expect(pen.pathLength([{ x: 0, y: 0 }, { x: 3, y: 4 }, { x: 3, y: 10 }])).toBeCloseTo(11, 9);
    expect(pen.pathLength([])).toBe(0);
  });
});

describe("resamplePath", () => {
  test("keeps both ends exactly and spaces the rest evenly", () => {
    const out = pen.resamplePath([{ x: 0, y: 0 }, { x: 7, y: 0 }, { x: 21, y: 0 }], 2);
    expect(out[0]).toEqual({ x: 0, y: 0 });
    expect(out[out.length - 1]).toEqual({ x: 21, y: 0 });
    for (let i = 1; i < out.length - 1; i++) expect(out[i].x - out[i - 1].x).toBeCloseTo(2, 9);
    expect(out.length).toBe(12); // 0,2,...,20 then 21
  });
});

describe("strokeToPath: the record", () => {
  test("is the open-shape record: points, and curves keyed by segment index", () => {
    const r = pen.strokeToPath(jitter(arc(60, 270), 0.5, 1));
    expect(Object.keys(r).sort()).toEqual(["curves", "points"]);
    expect(r.points.length).toBeGreaterThanOrEqual(2);
    for (const p of r.points) expect(Object.keys(p).sort()).toEqual(["x", "y"]);
    for (const k of Object.keys(r.curves)) {
      expect(Number(k)).toBeGreaterThanOrEqual(0);
      expect(Number(k)).toBeLessThan(r.points.length - 1); // n - 1 segments, no closing one
      expect(isFinite(r.curves[k].x) && isFinite(r.curves[k].y)).toBe(true);
    }
  });
  test("the first and last samples come back as the first and last points, exactly", () => {
    const raw = jitter(sine(), 1.2, 2);
    const r = pen.strokeToPath(raw);
    expect(r.points[0]).toEqual(raw[0]);
    expect(r.points[r.points.length - 1]).toEqual(raw[raw.length - 1]);
  });
  test("a straight drag is two points and no curve", () => {
    const raw = []; for (let x = 100; x <= 400; x += 5) raw.push({ x, y: 150 });
    const r = pen.strokeToPath(raw);
    expect(r.points).toEqual([{ x: 100, y: 150 }, { x: 400, y: 150 }]);
    expect(r.curves).toEqual({});
  });
  test("fewer than two distinct samples is no stroke", () => {
    expect(pen.strokeToPath([])).toBe(null);
    expect(pen.strokeToPath([{ x: 5, y: 5 }, { x: 5, y: 5 }])).toBe(null);
  });
  test("never more points than the cap", () => {
    const r = pen.strokeToPath(jitter(sine(), 1.2, 3), { maxPoints: 6 });
    expect(r.points.length).toBeLessThanOrEqual(6);
    expect(r.points.length).toBeGreaterThanOrEqual(2);
  });
});

// The numbers PEN_SMOOTH_SIGMA_PX / PEN_FIT_TOL_PX / PEN_STRAIGHT_TOL_PX were
// chosen on. Each row is the worst of three jitter seeds; the bars sit just
// above what was measured on 2026-11-13 (in the comment beside each), so a
// change that makes the fit worse fails here.
describe("fit error", () => {
  const worstOf = (truth, amp) => {
    let err = 0, nodes = 0, kink = 0;
    for (const seed of [1, 2, 3]) {
      const r = pen.strokeToPath(jitter(truth, amp, seed));
      err = Math.max(err, worstErr(truth, flat(r)));
      nodes = Math.max(nodes, r.points.length);
      kink = Math.max(kink, worstKink(r.points, r.curves));
    }
    return { err, nodes, kink };
  };
  test("a 10 mm-radius arc, light jitter (0.5 px): few nodes, no kink", () => {
    const m = worstOf(arc(60, 270), 0.5);
    expect(m.err).toBeLessThan(1.0);   // 0.80
    expect(m.nodes).toBeLessThanOrEqual(8); // 7
    expect(m.kink).toBeLessThan(5);    // 0
  });
  test("the same arc, heavy jitter (1.2 px): still under the jitter it was given", () => {
    const m = worstOf(arc(60, 270), 1.2);
    expect(m.err).toBeLessThan(1.2);   // 0.91
    expect(m.nodes).toBeLessThanOrEqual(15); // 13
    expect(m.kink).toBeLessThan(25);   // 18 (the tracer's fit: 138)
  });
  test("a 2 mm-radius loop is one smooth curve, not a string of corners", () => {
    const m = worstOf(arc(12, 300, 2), 1.2);
    expect(m.err).toBeLessThan(1.5);   // 1.19
    expect(m.nodes).toBeLessThanOrEqual(6); // 5
    expect(m.kink).toBeLessThan(5);    // 0
  });
  test("an S curve", () => {
    const m = worstOf(sine(), 1.2);
    expect(m.err).toBeLessThan(1.5);   // 1.18
    expect(m.nodes).toBeLessThanOrEqual(27); // 24
    expect(m.kink).toBeLessThan(25);   // 15
  });
  test("a tip is kept sharp: an anchor lands on it", () => {
    const { pts, tip } = vee();
    for (const seed of [1, 2, 3]) {
      const r = pen.strokeToPath(jitter(pts, 1.2, seed));
      const near = Math.min(...r.points.map((p) => Math.hypot(p.x - tip.x, p.y - tip.y)));
      expect(near).toBeLessThan(2.5); // the tip sample's own jitter is up to 1.7
    }
  });
});

describe("a pen stroke sews as a line and as a column", () => {
  const col = (r, mm) => ({ kind: "column", points: r.points, curves: r.curves, widthPx: mm * PX_PER_MM });
  test("no issues as a line or a 1 mm column: the rails do not fold on it", () => {
    for (const truth of [arc(60, 270), sine(), arc(12, 300, 2)]) {
      for (const seed of [1, 2, 3]) {
        const r = pen.strokeToPath(jitter(truth, 1.2, seed));
        expect(runIssues({ kind: "run", points: r.points, curves: r.curves })).toEqual([]);
        expect(columnIssues(col(r, 1))).toEqual([]);
      }
    }
  });
  test("nor as the default 4 mm column, on bends a 4 mm column can make", () => {
    // (not the 2 mm-radius loop: its radius IS half of 4 mm, and that folds
    // however it is drawn)
    for (const truth of [arc(60, 270), sine()]) {
      for (const seed of [1, 2, 3]) expect(columnIssues(col(pen.strokeToPath(jitter(truth, 1.2, seed)), 4))).toEqual([]);
    }
  });
  // e2e (p2), 2026-11-13: two long straight legs meeting at a shallow bend.
  // One curve per leg fits to within the tolerance with its control 3 px from
  // the bend, which is a straight line ending in a hairpin, and the column was
  // refused as "folds over itself". The lopsided control is refused now.
  test("a shallow V: straight legs and a small bend, sewable at any width", () => {
    const seg = (a, b, n) => { const o = []; for (let i = 1; i <= n; i++) o.push({ x: a.x + (b.x - a.x) * i / n, y: a.y + (b.y - a.y) * i / n }); return o; };
    const A = { x: 120, y: 280 }, B = { x: 300, y: 320 }, C = { x: 480, y: 280 };
    const r = pen.strokeToPath([A, ...seg(A, B, 8), ...seg(B, C, 8)]);
    for (const mm of [1, 2, 4, 6.5]) expect(columnIssues(col(r, mm))).toEqual([]);
    expect(r.points.length).toBeLessThanOrEqual(6); // 5
    // no control point sits in the last tenth of its segment
    for (const [k, c] of Object.entries(r.curves)) {
      const a = r.points[Number(k)], b = r.points[Number(k) + 1], chord = Math.hypot(b.x - a.x, b.y - a.y);
      expect(Math.min(Math.hypot(c.x - a.x, c.y - a.y), Math.hypot(c.x - b.x, c.y - b.y))).toBeGreaterThan(0.1 * chord);
    }
  });
});

describe("snapTarget", () => {
  const line = (id, a, b) => ({ id, kind: "run", points: [a, b], curves: {}, colorRgb: [0, 0, 0] });
  const col = (id, a, b) => ({ id, kind: "column", points: [a, b], curves: {}, widthPx: 12, colorRgb: [0, 0, 0] });
  const shapes = [line("s1", { x: 100, y: 100 }, { x: 300, y: 100 }), col("s2", { x: 100, y: 300 }, { x: 300, y: 300 })];
  const snap = (pt, kind) => pen.snapTarget(pt, pen.snapSpines(shapes, kind));

  test("lands on the END of a same-kind stroke within the radius", () => {
    expect(snap({ x: 304, y: 97 }, "run")).toEqual({ x: 300, y: 100, on: "end", shapeId: "s1" });
  });
  test("else on the nearest point of its spine", () => {
    expect(snap({ x: 200, y: 106 }, "run")).toEqual({ x: 200, y: 100, on: "spine", shapeId: "s1" });
  });
  test("an end wins over a nearer spine point", () => {
    // 7.1 px from the end at (300,100), 5 px from the spine
    expect(snap({ x: 295, y: 105 }, "run").on).toBe("end");
  });
  test("only the same kind: a Line does not snap to a Column, nor a Column to a Line", () => {
    expect(snap({ x: 200, y: 303 }, "run")).toBe(null);
    expect(snap({ x: 200, y: 103 }, "column")).toBe(null);
    expect(snap({ x: 200, y: 303 }, "column").shapeId).toBe("s2");
  });
  test("nothing within the radius is null; closed modes have no spines to snap to", () => {
    expect(snap({ x: 200, y: 111 }, "run")).toBe(null);
    expect(pen.snapSpines(shapes, "shape")).toEqual([]);
    expect(snap({ x: 200, y: 100 }, "shape")).toBe(null);
  });
  test("snapSpines: one flattened spine per valid same-kind shape; a shape with problems is no target", () => {
    const folded = { id: "s3", kind: "column", points: [{ x: 100, y: 200 }, { x: 300, y: 200 }, { x: 100, y: 204 }], curves: {}, widthPx: 24 };
    const spines = pen.snapSpines([...shapes, folded], "column");
    expect(spines.map((s) => s.id)).toEqual(["s2"]);
    expect(spines[0].flat).toEqual([{ x: 100, y: 300 }, { x: 300, y: 300 }]);
  });
});

describe("clampToCanvas", () => {
  test("holds a point to the authored canvas, and leaves one inside it alone", () => {
    expect(pen.clampToCanvas({ x: 640, y: -12 })).toEqual({ x: 600, y: 0 });
    expect(pen.clampToCanvas({ x: -3, y: 450 })).toEqual({ x: 0, y: 400 });
    expect(pen.clampToCanvas({ x: 250.5, y: 99 })).toEqual({ x: 250.5, y: 99 });
  });
});

describe("withSnappedEnds", () => {
  // The pointer goes down 6 px to the RIGHT of the end it snaps to and draws
  // to the LEFT: without the trim the path leaves the snap point rightwards,
  // then doubles back through it.
  const snap = { x: 400, y: 100 };
  const raw = []; for (let x = 406; x >= 200; x -= 3) raw.push({ x, y: 103 + (406 - x) * 0.5 });

  test("drops every sample inside the snap radius, so the path leaves the snap point once", () => {
    const pts = pen.withSnappedEnds(raw, snap, null);
    expect(pts[0]).toEqual(snap);
    for (const p of pts.slice(1)) expect(Math.hypot(p.x - snap.x, p.y - snap.y)).toBeGreaterThan(pen.PEN_SNAP_RADIUS_PX);
    // monotone leftwards from the snap point: no sample back to its right
    for (let i = 1; i < pts.length; i++) expect(pts[i].x).toBeLessThan(pts[i - 1].x);
  });
  test("the hook it removes is what folded a 4 mm column", () => {
    const hooked = pen.strokeToPath([snap, ...raw]);
    const clean = pen.strokeToPath(pen.withSnappedEnds(raw, snap, null));
    const col = (r) => ({ kind: "column", points: r.points, curves: r.curves, widthPx: 4 * PX_PER_MM });
    expect(columnIssues(col(hooked))).not.toEqual([]);
    expect(columnIssues(col(clean))).toEqual([]);
  });
  test("the same at the other end, and both ends together keep both snap points", () => {
    const endSnap = { x: 197, y: 210 };
    const pts = pen.withSnappedEnds(raw, snap, endSnap);
    expect(pts[0]).toEqual(snap);
    expect(pts.at(-1)).toEqual(endSnap);
    for (const p of pts.slice(1, -1)) expect(Math.hypot(p.x - endSnap.x, p.y - endSnap.y)).toBeGreaterThan(pen.PEN_SNAP_RADIUS_PX);
  });
  test("no snap: the samples come back as they were", () => {
    expect(pen.withSnappedEnds(raw, null, null)).toEqual(raw);
  });
  test("a stroke that never leaves the start's radius still has two ends", () => {
    const pts = pen.withSnappedEnds([{ x: 402, y: 101 }, { x: 404, y: 103 }], snap, { x: 404, y: 108 });
    expect(pts).toEqual([snap, { x: 404, y: 108 }]);
  });
});

describe("what the next stroke is born with", () => {
  test("the first column is the default width; later ones take the remembered width", () => {
    expect(pen.nextColumnWidthMm()).toBe(COLUMN_DEFAULT_MM);
    pen.rememberColumnWidthMm(1);
    expect(pen.nextColumnWidthMm()).toBe(1);
    pen.rememberColumnWidthMm(0); pen.rememberColumnWidthMm(NaN); pen.rememberColumnWidthMm(-2);
    expect(pen.nextColumnWidthMm()).toBe(1);
  });
  test("colour: the selected shape's, else the last shape's, else the fallback; read off the drawing only", () => {
    const red = { id: "s1", colorRgb: [200, 0, 0] }, blue = { id: "s2", colorRgb: [0, 0, 200] };
    expect(pen.nextOpenShapeColor([], null, [20, 20, 20])).toEqual([20, 20, 20]);
    expect(pen.nextOpenShapeColor([red, blue], null, [20, 20, 20])).toEqual([0, 0, 200]);
    expect(pen.nextOpenShapeColor([red, blue], red, [20, 20, 20])).toEqual([200, 0, 0]);
    // a copy, never the shape's own array
    expect(pen.nextOpenShapeColor([red], red, [20, 20, 20])).not.toBe(red.colorRgb);
    // nothing is held between calls: an empty drawing is the fallback again
    expect(pen.nextOpenShapeColor([], null, [20, 20, 20])).toEqual([20, 20, 20]);
    expect(pen.nextOpenShapeColor([{ id: "s3" }, { id: "s4", colorRgb: "red" }], null, [20, 20, 20])).toEqual([20, 20, 20]);
  });
  test("widthEditedColumn: exactly one column's width changed, same ids", () => {
    const a = { id: "s1", kind: "column", points: [], curves: {}, widthPx: 24 };
    const b = { id: "s2", kind: "column", points: [], curves: {}, widthPx: 24 };
    const r = { id: "s3", kind: "run", points: [], curves: {} };
    const a2 = { ...a, widthPx: 6 };
    expect(pen.widthEditedColumn([a, b, r], [a2, b, r])).toBe(a2);
    expect(pen.widthEditedColumn([a, b, r], [a, b, r])).toBe(null);            // nothing changed
    expect(pen.widthEditedColumn([a, b], [a2, { ...b, widthPx: 6 }])).toBe(null); // two changed
    expect(pen.widthEditedColumn([a], [a, b])).toBe(null);                     // a new shape is not an edit
    expect(pen.widthEditedColumn([a, b], [a2])).toBe(null);                    // nor a deletion
  });
});
