// Node editing of hand-drawn shapes on the field (2026-09-29 spec §3-§4):
// the px<->mm maps, the authored geometry in field mm, the hit test, the four
// edits, and the re-fit rule — pinned as an invariant through the REAL
// engine, because the rule exists so that nothing unedited ever moves.
import { beforeAll, describe, expect, test } from "vitest";
import { createRequire } from "node:module";
import {
  pxToFieldMm, fieldMmToPx, authoredInFieldMm, hitAuthored,
  applyAnchorDrag, applyHandleDrag, insertAnchor, removeAnchor, editedElementPatch,
} from "./fieldNodeEdit.js";

let EMB, generateElement, garment;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  ({ EMB } = await import("./emb.js"));
  ({ generateElement } = await import("./generate.js"));
  garment = EMB.getGarment("left_chest");
});

const fit = { cxPx: 300, cyPx: 200, mmPerPx: 0.2, offsetXMm: 5, offsetYMm: -3, pxPerMm: 6 };
const sq = (x0, y0, s) => [{ x: x0, y: y0 }, { x: x0 + s, y: y0 }, { x: x0 + s, y: y0 + s }, { x: x0, y: y0 + s }];
const shapeA = { id: "s1", points: sq(100, 100, 100), curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
const shapeB = { id: "s2", points: sq(350, 150, 80), curves: {}, stitchType: "fill", colorRgb: [200, 0, 0], angleDeg: null };
const el = (shapes, extra = {}) => ({ id: 4, type: "manual", shapes, underlay: true, sizeMm: 60, offsetXMm: 5, offsetYMm: -3, ...extra });

describe("maps", () => {
  test("pxToFieldMm is T() unrounded and fieldMmToPx inverts it", () => {
    expect(pxToFieldMm(fit, { x: 300, y: 200 })).toEqual([5, -3]);
    expect(pxToFieldMm(fit, { x: 400, y: 200 })).toEqual([25, -3]);   // +100 px -> +20 mm
    expect(pxToFieldMm(fit, { x: 300, y: 100 })).toEqual([5, 17]);    // px y up (smaller) -> mm y up
    const back = fieldMmToPx(fit, [25, 17]);
    expect(back.x).toBeCloseTo(400, 9); expect(back.y).toBeCloseTo(100, 9);
  });
});

describe("authoredInFieldMm", () => {
  test("anchors, controls and handles are mapped; a straight segment's handle is the chord midpoint", () => {
    const s = { ...shapeA, curves: { 0: { x: 150, y: 40 } } };
    const a = authoredInFieldMm(s, fit);
    expect(a.anchors).toHaveLength(4);
    expect(a.anchors[0]).toEqual(pxToFieldMm(fit, { x: 100, y: 100 }));
    expect(a.controls[0]).toEqual(pxToFieldMm(fit, { x: 150, y: 40 }));
    expect(a.controls[1]).toBeUndefined();
    // handle 0 is B(0.5) of the quadratic; handle 1 is the chord midpoint of anchors 1-2
    expect(a.handles[0]).toEqual(pxToFieldMm(fit, { x: 0.25 * 100 + 0.5 * 150 + 0.25 * 200, y: 0.25 * 100 + 0.5 * 40 + 0.25 * 100 }));
    expect(a.handles[1]).toEqual(pxToFieldMm(fit, { x: 200, y: 150 }));
  });
});

describe("hitAuthored (px space)", () => {
  // a plain 100-px square drawn 1:1 in px for readability
  const px = { anchors: [[0, 0], [100, 0], [100, 100], [0, 100]], controls: {}, handles: [[50, 0], [100, 50], [50, 100], [0, 50]] };
  test("anchor beats handle beats edge; each within its radius", () => {
    expect(hitAuthored(px, 3, 3)).toMatchObject({ kind: "anchor", index: 0 });
    expect(hitAuthored(px, 50, 4)).toMatchObject({ kind: "handle", index: 0 });
    expect(hitAuthored(px, 25, 3)).toMatchObject({ kind: "edge", index: 0 });
    expect(hitAuthored(px, 50, 50)).toBeNull();
  });
  test("an edge hit lands on the BOWED part of a curved segment", () => {
    // segment 0 bowed up to y=-40 at its middle; the chord is y=0
    const control = [50, -80]; // quadratic through (50,-40) at t=0.5
    const bowed = { anchors: px.anchors, controls: { 0: control }, handles: [[50, -40], [100, 50], [50, 100], [0, 50]] };
    expect(hitAuthored(bowed, 25, -30)).toMatchObject({ kind: "edge", index: 0 }); // on the curve, 30 px off the chord
    expect(hitAuthored(bowed, 25, 3)).toBeNull(); // the chord is no longer where the edge is
  });
});

describe("edits", () => {
  test("applyAnchorDrag moves ONE anchor and nothing else", () => {
    const s = applyAnchorDrag(shapeA, 2, { x: 250, y: 260 });
    expect(s.points[2]).toEqual({ x: 250, y: 260 });
    expect(s.points[1]).toBe(shapeA.points[1]);
    expect(shapeA.points[2]).toEqual({ x: 200, y: 200 }); // input untouched
  });
  test("applyHandleDrag stores a control, and a drag back to the chord straightens", () => {
    const bent = applyHandleDrag(shapeA, 0, { x: 150, y: 60 });
    expect(bent.curves[0]).toBeDefined();
    const straight = applyHandleDrag(bent, 0, { x: 150, y: 100.5 });
    expect(straight.curves[0]).toBeUndefined();
  });
  test("insertAnchor splices after the segment and reindexes curves; the cap is a no-op", () => {
    const s = insertAnchor({ ...shapeA, curves: { 2: { x: 1, y: 1 } } }, 0, { x: 150, y: 100 });
    expect(s.points).toHaveLength(5);
    expect(s.points[1]).toEqual({ x: 150, y: 100 });
    expect(s.curves[3]).toEqual({ x: 1, y: 1 });
    const capped = { ...shapeA, points: Array.from({ length: 500 }, (_, i) => ({ x: i, y: 0 })) };
    expect(insertAnchor(capped, 0, { x: 0.5, y: 0 })).toBe(capped);
  });
  test("removeAnchor drops the anchor and both curves that touched it, reindexes, floors at 3", () => {
    const s = removeAnchor({ ...shapeA, curves: { 0: { x: 9, y: 9 }, 1: { x: 8, y: 8 }, 2: { x: 7, y: 7 } } }, 1);
    expect(s.points.map((p) => p.x)).toEqual([100, 200, 100]);
    expect(s.curves).toEqual({ 1: { x: 7, y: 7 } }); // old seg 2 (anchors 2->3) is now seg 1; segs 0 and 1 (touching anchor 1) are gone
    const tri = { ...shapeA, points: shapeA.points.slice(0, 3) };
    expect(removeAnchor(tri, 0)).toBeNull();
  });
});

describe("editedElementPatch — the re-fit rule, through the real engine", () => {
  function outlinesOf(element) {
    const d = generateElement(element, garment, {});
    return { fit: d.fit, byId: Object.fromEntries(d.shapeOutlines.map((o) => [o.id, o.points])) };
  }
  // The engine applies offsets rounded to the 0.1 mm DST grid (offXu = round(off*10)),
  // so "unmoved" means moved by EXACTLY the change in that rounding residual.
  const residual = (offMm) => Math.round(offMm * 10) / 10 - offMm;
  // pts1 vs pts0 (same rings, same order): every point translated by exactly [dx, dy].
  function movedBy(pts1, pts0, dx, dy) {
    expect(pts1).toHaveLength(pts0.length);
    pts1.forEach((p, i) => {
      expect(p[0] - pts0[i][0]).toBeCloseTo(dx, 6);
      expect(p[1] - pts0[i][1]).toBeCloseTo(dy, 6);
    });
  }
  // Returns the residual change [rx, ry] after asserting scale held and it is within half a DST unit.
  function pinResidual(before, o0, patch, o1) {
    expect(o1.fit.mmPerPx).toBeCloseTo(o0.fit.mmPerPx, 12); // scale held exactly
    const rx = residual(patch.offsetXMm) - residual(before.offsetXMm);
    const ry = residual(patch.offsetYMm) - residual(before.offsetYMm);
    expect(Math.abs(rx)).toBeLessThanOrEqual(0.05 + 1e-9);
    expect(Math.abs(ry)).toBeLessThanOrEqual(0.05 + 1e-9);
    return [rx, ry];
  }

  test("dragging one of A's anchors outward leaves B and A's other anchors exactly where they were", () => {
    const before = el([shapeA, shapeB]);
    const o0 = outlinesOf(before);
    const moved = applyAnchorDrag(shapeA, 0, { x: 20, y: 20 }); // outward: grows the whole bbox
    const patch = editedElementPatch(before, o0.fit, "s1", moved);
    expect(patch.error).toBeUndefined();
    expect(patch.shapes[0].points[0]).toEqual({ x: 20, y: 20 });
    const after = { ...before, ...patch };
    const o1 = outlinesOf(after);
    const [rx, ry] = pinResidual(before, o0, patch, o1);
    movedBy(o1.byId.s2, o0.byId.s2, rx, ry);
    movedBy(o1.byId.s1.slice(1), o0.byId.s1.slice(1), rx, ry);
    // and the moved anchor landed where the drag put it (same rounding allowance)
    expect(o1.byId.s1[0][0]).toBeCloseTo(pxToFieldMm(o0.fit, { x: 20, y: 20 })[0] + rx, 6);
    expect(o1.byId.s1[0][1]).toBeCloseTo(pxToFieldMm(o0.fit, { x: 20, y: 20 })[1] + ry, 6);
    expect(patch.sizeMm).not.toBe(before.sizeMm); // width grew, scale held
  });
  test("the same from an auto-fit element (sizeMm null): the patch seeds sizeMm and holds the scale", () => {
    const before = el([shapeA, shapeB], { sizeMm: null });
    const o0 = outlinesOf(before);
    // Outward in Y, not X: the auto-fit already fills left_chest's PLACEMENT box width
    // (330 px * 0.3079 = 101.6 mm = 4 in), so growing X would hit the engine's
    // placement-box clamp and break the invariant (spec §4 and its erratum — knowingly).
    const patch = editedElementPatch(before, o0.fit, "s2", applyAnchorDrag(shapeB, 1, { x: 430, y: 60 }));
    expect(typeof patch.sizeMm).toBe("number");
    const o1 = outlinesOf({ ...before, ...patch });
    const [rx, ry] = pinResidual(before, o0, patch, o1);
    movedBy(o1.byId.s1, o0.byId.s1, rx, ry);
  });
  test("auto-fit (sizeMm null), an INWARD x drag that narrows the bbox: only the held scale keeps everything put", () => {
    // The Y-only case above never changes the bbox WIDTH, and width is what auto-fit
    // scales by — so it cannot tell the held scale from auto-fit. Here the rightmost
    // extent is ONE anchor (a triangle's tip), dragged inward 30 px: the width drops
    // 330 -> 300 px and stays inside the box, so auto-fit WOULD re-scale.
    const tri = { id: "s3", points: [{ x: 350, y: 150 }, { x: 430, y: 190 }, { x: 350, y: 230 }], curves: {}, stitchType: "fill", colorRgb: [0, 0, 200], angleDeg: null };
    const before = el([shapeA, tri], { sizeMm: null });
    const o0 = outlinesOf(before);
    const moved = applyAnchorDrag(tri, 1, { x: 400, y: 190 });
    const patch = editedElementPatch(before, o0.fit, "s3", moved);
    expect(patch.error).toBeUndefined();
    expect(patch.sizeMm).toBeCloseTo(300 * o0.fit.mmPerPx, 9);
    // Without the patch's sizeMm the engine re-fits the narrower bbox to the box: the
    // scale changes, which is exactly what the patch is there to prevent.
    const autoFit = outlinesOf({ ...before, shapes: patch.shapes });
    expect(Math.abs(autoFit.fit.mmPerPx / o0.fit.mmPerPx - 1)).toBeGreaterThan(0.05);
    const o1 = outlinesOf({ ...before, ...patch });
    const [rx, ry] = pinResidual(before, o0, patch, o1);
    movedBy(o1.byId.s1, o0.byId.s1, rx, ry);
    movedBy([o1.byId.s3[0], o1.byId.s3[2]], [o0.byId.s3[0], o0.byId.s3[2]], rx, ry);
  });
  test("an edit that leaves the shape invalid is refused with the issue text", () => {
    const before = el([shapeA]);
    const o0 = outlinesOf(before);
    const bowtie = { ...shapeA, points: [{ x: 100, y: 100 }, { x: 200, y: 200 }, { x: 200, y: 100 }, { x: 100, y: 200 }] };
    const r = editedElementPatch(before, o0.fit, "s1", bowtie);
    expect(r.shapes).toBeUndefined();
    expect(typeof r.error).toBe("string");
    expect(r.error.length).toBeGreaterThan(0);
  });
});
