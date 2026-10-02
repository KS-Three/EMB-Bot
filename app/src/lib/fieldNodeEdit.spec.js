// Node editing of hand-drawn shapes on the field (2026-09-29 spec §3-§4):
// the px<->mm maps, the authored geometry in field mm, the hit test, the four
// edits, and the re-fit rule — pinned as an invariant through the REAL
// engine, because the rule exists so that nothing unedited ever moves.
import { beforeAll, describe, expect, test } from "vitest";
import { createRequire } from "node:module";
import {
  pxToFieldMm, fieldMmToPx, authoredInFieldMm, hitAuthored,
  applyAnchorDrag, applyHandleDrag, insertAnchor, removeAnchor, editedElementPatch, clampMmToBox,
  breaksContainment, ringInsideBox, cutOutOutlinesInFieldMm, CUTOUT_HOLD_HINT, refitShapesPatch,
} from "./fieldNodeEdit.js";
import { withCutOut } from "./manualShapes.js";

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

describe("clampMmToBox — a dragged node stops at the placement box (Kent, 2026-09-29)", () => {
  const box = { wMm: 200, hMm: 100 };
  test("a point inside is unchanged", () => {
    expect(clampMmToBox([30, -20], box)).toEqual([30, -20]);
  });
  test("each side clamps to the half-extent, independently", () => {
    expect(clampMmToBox([500, 0], box)).toEqual([100, 0]);
    expect(clampMmToBox([-500, 0], box)).toEqual([-100, 0]);
    expect(clampMmToBox([0, 500], box)).toEqual([0, 50]);
    expect(clampMmToBox([0, -500], box)).toEqual([0, -50]);
    expect(clampMmToBox([500, -500], box)).toEqual([100, -50]);
  });
  test("a zero box collapses to the origin", () => {
    expect(clampMmToBox([12, -7], { wMm: 0, hMm: 0 })).toEqual([0, 0]);
  });
});

const rect = (id, x0, y0, x1, y1, extra = {}) => ({ id, points: [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }], curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null, ...extra });

describe("cut-outs", () => {
  const P = rect("s1", 0, 0, 300, 300);
  const C = rect("s2", 100, 100, 200, 200, { cutOut: true });
  const cfit = { cxPx: 150, cyPx: 150, mmPerPx: 0.2, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };

  test("breaksContainment: dragging a cut-out's corner outside its parent", () => {
    const moved = applyAnchorDrag(C, 1, { x: 350, y: 100 });
    expect(breaksContainment([P, C], [P, moved])).toBe(true);
    expect(breaksContainment([P, C], [P, applyAnchorDrag(C, 1, { x: 250, y: 100 })])).toBe(false);
  });
  test("breaksContainment: pulling the parent's edge across its cut-out", () => {
    const pulled = applyAnchorDrag(P, 0, { x: 180, y: 180 });
    expect(breaksContainment([P, C], [pulled, C])).toBe(true);
  });
  test("breaksContainment: a cut-out that already cut nothing is free to move", () => {
    const orphan = rect("s2", 400, 400, 450, 450, { cutOut: true });
    expect(breaksContainment([P, orphan], [P, applyAnchorDrag(orphan, 0, { x: 380, y: 380 })])).toBe(false);
  });
  test("editedElementPatch refuses a containment-breaking edit with the hint", () => {
    const e = { id: "e1", type: "manual", shapes: [P, C], sizeMm: 60, offsetXMm: 0, offsetYMm: 0 };
    const out = editedElementPatch(e, cfit, "s2", applyAnchorDrag(C, 1, { x: 350, y: 100 }));
    expect(out).toEqual({ error: CUTOUT_HOLD_HINT });
  });
  test("the bbox ignores cut-outs: moving an orphan cut-out far away changes no size or offset", () => {
    const orphan = rect("s2", 400, 400, 450, 450, { cutOut: true });
    const e = { id: "e1", type: "manual", shapes: [P, orphan], sizeMm: 60, offsetXMm: 1, offsetYMm: -2 };
    const out = editedElementPatch(e, cfit, "s2", applyAnchorDrag(orphan, 2, { x: 590, y: 390 }));
    expect(out.error).toBeUndefined();
    expect(out.sizeMm).toBeCloseTo(60, 9);
    expect(out.offsetXMm).toBeCloseTo(1, 9);
    expect(out.offsetYMm).toBeCloseTo(-2, 9);
  });
  test("ringInsideBox tests the FLATTENED curve, not the handle's through point", () => {
    const sh = { id: "s1", curves: {}, points: [{ x: 0, y: 0 }, { x: 25, y: -100 }, { x: 0, y: -100 }] };
    const f = { cxPx: 0, cyPx: 0, mmPerPx: 0.2, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };
    const bent = applyHandleDrag(sh, 0, { x: 50, y: -50 });
    expect(ringInsideBox(sh, f, { wMm: 20, hMm: 40 })).toBe(true);
    expect(ringInsideBox(bent, f, { wMm: 20, hMm: 40 })).toBe(false);
    expect(ringInsideBox(bent, f, { wMm: 0, hMm: 0 })).toBe(true);
  });
  test("cutOutOutlinesInFieldMm: one entry per cut-out, mapped through the fit, resolved or not", () => {
    const orphan = rect("s3", 400, 400, 450, 450, { cutOut: true });
    const out = cutOutOutlinesInFieldMm([P, C, orphan], cfit);
    expect(out.map((o) => o.id)).toEqual(["s2", "s3"]);
    expect(out[0].cutOut).toBe(true);
    expect(out[0].points[0][0]).toBeCloseTo((100 - 150) * 0.2, 9);
    expect(out[0].points[0][1]).toBeCloseTo((150 - 100) * 0.2, 9);
  });

  // The Cut out switch on the hoop goes through the same re-fit rule as a node
  // edit (fix wave, ruling after Task 8): a cut-out emits no region, so marking a
  // shape OUTSIDE every other one drops it from the engine's bbox — without the
  // re-fit the element re-fitted to the rest and the remaining shape jumped
  // (e2e (f): 81x39 -> 81x91 mm). These run the real engine on both sides, and
  // double as the orphan-bbox engine test: the orphan sits far outside the parent,
  // so a bbox that counted it would move the parent by tens of mm, not 0.05.
  describe("refitShapesPatch — the Cut out switch moves nothing else", () => {
    const parent = rect("s1", 100, 100, 300, 300);
    const stray = rect("s2", 380, 120, 460, 200, { stitchType: "fill", colorRgb: [200, 0, 0] });
    const outline = (d) => Object.fromEntries(d.shapeOutlines.map((o) => [o.id, o.points]));
    function holdsStill(before, patch) {
      const d0 = generateElement(before, garment, {});
      const d1 = generateElement({ ...before, ...patch }, garment, {});
      expect(d1.fit.mmPerPx).toBeCloseTo(d0.fit.mmPerPx, 12);
      const rx = Math.round(patch.offsetXMm * 10) / 10 - patch.offsetXMm - (Math.round(before.offsetXMm * 10) / 10 - before.offsetXMm);
      const ry = Math.round(patch.offsetYMm * 10) / 10 - patch.offsetYMm - (Math.round(before.offsetYMm * 10) / 10 - before.offsetYMm);
      expect(Math.abs(rx)).toBeLessThanOrEqual(0.05 + 1e-9);
      expect(Math.abs(ry)).toBeLessThanOrEqual(0.05 + 1e-9);
      const o0 = outline(d0), o1 = outline(d1);
      expect(o1.s1).toHaveLength(o0.s1.length);
      o1.s1.forEach((p, i) => { expect(p[0] - o0.s1[i][0]).toBeCloseTo(rx, 6); expect(p[1] - o0.s1[i][1]).toBeCloseTo(ry, 6); });
      return { d0, d1 };
    }
    test("marking the stray shape Cut out: the parent stays put and the scale holds", () => {
      const before = el([parent, stray]);
      const d0 = generateElement(before, garment, {});
      const shapes = [parent, withCutOut(stray, true)];
      const patch = refitShapesPatch(before, d0.fit, shapes);
      expect(patch.error).toBeUndefined();
      expect(patch.shapes).toBe(shapes);
      expect(patch.sizeMm).toBeCloseTo(200 * d0.fit.mmPerPx, 9); // the width that is left, at the held scale
      const { d1 } = holdsStill(before, patch);
      expect(d1.shapeOutlines.map((o) => o.id)).toEqual(["s1"]);
      // Without the patch the element re-fits to the parent alone: the jump the rule removes.
      const jumped = generateElement({ ...before, shapes }, garment, {});
      expect(Math.abs(jumped.fit.mmPerPx / d0.fit.mmPerPx - 1)).toBeGreaterThan(0.2);
    });
    test("and turning it off again: the parent stays put and the scale holds", () => {
      const before = el([parent, withCutOut(stray, true)], { sizeMm: 40 });
      const d0 = generateElement(before, garment, {});
      const shapes = [parent, stray];
      const patch = refitShapesPatch(before, d0.fit, shapes);
      expect(patch.error).toBeUndefined();
      expect(patch.sizeMm).toBeCloseTo(360 * d0.fit.mmPerPx, 9);
      const { d1 } = holdsStill(before, patch);
      expect(d1.shapeOutlines.map((o) => o.id).sort()).toEqual(["s1", "s2"]);
    });
    test("nothing sewn before, or nothing left after: the plain shapes patch (nothing to hold still)", () => {
      const only = el([parent]);
      const f0 = generateElement(only, garment, {}).fit;
      const allCut = [withCutOut(parent, true)];
      expect(refitShapesPatch(only, f0, allCut)).toEqual({ shapes: allCut });
      const none = el([withCutOut(parent, true)]);
      expect(refitShapesPatch(none, f0, [parent])).toEqual({ shapes: [parent] });
    });
  });

  test("through the real engine: editing a cut-out moves nothing of its parent (bbox agreement)", () => {
    const eP = rect("s1", 100, 100, 300, 300), eC = rect("s2", 150, 150, 250, 250, { cutOut: true });
    const before = el([eP, eC]);
    const d0 = generateElement(before, garment, {});
    const o0 = Object.fromEntries(d0.shapeOutlines.map((o) => [o.id, o.points]));
    const patch = editedElementPatch(before, d0.fit, "s2", applyAnchorDrag(eC, 1, { x: 270, y: 140 }));
    expect(patch.error).toBeUndefined();
    const d1 = generateElement({ ...before, ...patch }, garment, {});
    const o1 = Object.fromEntries(d1.shapeOutlines.map((o) => [o.id, o.points]));
    expect(d1.fit.mmPerPx).toBeCloseTo(d0.fit.mmPerPx, 12);
    const rx = Math.round(patch.offsetXMm * 10) / 10 - patch.offsetXMm - (Math.round(before.offsetXMm * 10) / 10 - before.offsetXMm);
    const ry = Math.round(patch.offsetYMm * 10) / 10 - patch.offsetYMm - (Math.round(before.offsetYMm * 10) / 10 - before.offsetYMm);
    expect(Math.abs(rx)).toBeLessThanOrEqual(0.05 + 1e-9);
    expect(Math.abs(ry)).toBeLessThanOrEqual(0.05 + 1e-9);
    expect(o1.s1).toHaveLength(o0.s1.length);
    o1.s1.forEach((p, i) => { expect(p[0] - o0.s1[i][0]).toBeCloseTo(rx, 6); expect(p[1] - o0.s1[i][1]).toBeCloseTo(ry, 6); });
  });
});
