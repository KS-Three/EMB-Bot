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
  columnWidthMm, withColumnWidthMm, columnSewnMm,
} from "./fieldNodeEdit.js";
import { withCutOut, shapeRing } from "./manualShapes.js";

let EMB, generateElement, fabricInForce, garment;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","quantize","flatten","satin","satinplay","satinfont","fontbin","dst","dstimport","exp","fonts","digitize"]) require("../../../src/" + f + ".js");
  ({ EMB } = await import("./emb.js"));
  ({ generateElement, fabricInForce } = await import("./generate.js"));
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

// ---- Columns: an open spine plus a drawn width (spec 2026-09-30 §6, amended 2026-10-01) ----
const col = (id, points, widthPx, extra = {}) => ({ id, kind: "column", points, curves: {}, widthPx, colorRgb: [0, 0, 200], ...extra });

describe("columns — an open spine", () => {
  const spine4 = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 200, y: 0 }, { x: 300, y: 0 }];
  const curved = () => col("c1", spine4, 20, { curves: { 0: { x: 50, y: -9 }, 1: { x: 150, y: -8 }, 2: { x: 250, y: -7 } } });
  const f1 = { cxPx: 0, cyPx: 0, mmPerPx: 0.2, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };

  test("authoredInFieldMm: n - 1 handles (no closing segment) and the rails in field mm", () => {
    const c = col("c1", [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }], 20);
    const a = authoredInFieldMm(c, f1);
    expect(a.anchors).toHaveLength(3);
    expect(a.handles).toHaveLength(2);
    expect(a.handles[1]).toEqual(pxToFieldMm(f1, { x: 100, y: 50 }));
    expect(a.rails.a).toHaveLength(3);
    expect(a.rails.b).toHaveLength(3);
    // the rails are the ring the engine sees: rail A, then rail B backwards
    const ring = shapeRing(c).map((p) => pxToFieldMm(f1, p));
    expect([...a.rails.a, ...a.rails.b.slice().reverse()]).toEqual(ring);
    // each rail end sits half a width (10 px = 2 mm) from the spine's first anchor
    expect(Math.hypot(a.rails.a[0][0] - a.anchors[0][0], a.rails.a[0][1] - a.anchors[0][1])).toBeCloseTo(2, 9);
    // a closed shape has no rails key
    expect(authoredInFieldMm(shapeA, fit).rails).toBeUndefined();
  });
  test("authoredInFieldMm: a column with no usable width still edits — empty rails", () => {
    const a = authoredInFieldMm(col("c1", spine4, 0), f1);
    expect(a.handles).toHaveLength(3);
    expect(a.rails).toEqual({ a: [], b: [] });
  });

  test("hitAuthored(..., false): no phantom closing handle or edge", () => {
    // an L: anchors (0,0) (100,0) (100,100); the closing chord would run (100,100) -> (0,0)
    const anchors = [[0, 0], [100, 0], [100, 100]];
    const open = { anchors, controls: {}, handles: [[50, 0], [100, 50]] };
    expect(hitAuthored(open, 50, 50, false)).toBeNull();              // dead on the closing chord's midpoint
    expect(hitAuthored(open, 30, 31, false)).toBeNull();              // on the closing chord
    expect(hitAuthored(open, 30, 31)).toMatchObject({ kind: "edge", index: 2 }); // closed (the default) still finds it
    expect(hitAuthored(open, 25, 2, false)).toMatchObject({ kind: "edge", index: 0 });
    expect(hitAuthored(open, 100, 52, false)).toMatchObject({ kind: "handle", index: 1 });
    expect(hitAuthored(open, 98, 99, false)).toMatchObject({ kind: "anchor", index: 2 });
    // even handed a stale closing handle, an open hit never answers index n - 1
    const stale = { anchors, controls: {}, handles: [[50, 0], [100, 50], [50, 50]] };
    expect(hitAuthored(stale, 50, 50, false)).toBeNull();
    expect(hitAuthored(stale, 50, 50)).toMatchObject({ kind: "handle", index: 2 });
    for (let x = -20; x <= 120; x += 5) for (let y = -20; y <= 120; y += 5) {
      const h = hitAuthored(stale, x, y, false);
      if (h && h.kind !== "anchor") expect(h.index).toBeLessThan(2);
    }
  });

  test("removeAnchor on a column: the FIRST anchor drops its own segment's curve and shifts the rest", () => {
    const s = removeAnchor(curved(), 0);
    expect(s.points.map((p) => p.x)).toEqual([100, 200, 300]);
    expect(s.curves).toEqual({ 0: { x: 150, y: -8 }, 1: { x: 250, y: -7 } });
  });
  test("removeAnchor on a column: the LAST anchor drops curves[n - 2] and nothing else", () => {
    const s = removeAnchor(curved(), 3);
    expect(s.points.map((p) => p.x)).toEqual([0, 100, 200]);
    expect(s.curves).toEqual({ 0: { x: 50, y: -9 }, 1: { x: 150, y: -8 } });
  });
  test("removeAnchor on a column: an INTERIOR anchor merges its two neighbours into one straight segment", () => {
    const s = removeAnchor(curved(), 1);
    expect(s.points.map((p) => p.x)).toEqual([0, 200, 300]);
    expect(s.curves).toEqual({ 1: { x: 250, y: -7 } });
  });
  test("removeAnchor on a column: a stale closing-segment curve never survives into a real segment", () => {
    const s = removeAnchor({ ...curved(), curves: { 3: { x: 1, y: 1 } } }, 0);
    expect(s.curves).toEqual({});
  });
  test("removeAnchor on a column: the floor is 2", () => {
    const three = col("c1", spine4.slice(0, 3), 20);
    expect(removeAnchor(three, 1).points).toHaveLength(2);
    expect(removeAnchor(col("c1", spine4.slice(0, 2), 20), 0)).toBeNull();
  });

  test("width reads and writes in mm through the fit; widthPx is the only thing stored", () => {
    const c = col("c1", spine4, 20);
    expect(columnWidthMm(c, f1)).toBeCloseTo(4, 12);
    expect(columnSewnMm(c, f1, 0.4)).toBeCloseTo(4.4, 12);
    const w = withColumnWidthMm(c, f1, 6);
    expect(w.widthPx).toBeCloseTo(30, 12);
    expect(w.widthMm).toBeUndefined();
    expect(c.widthPx).toBe(20); // input untouched
    expect(w.points).toBe(c.points);
    // floor 0.1 mm
    expect(withColumnWidthMm(c, f1, 0).widthPx).toBeCloseTo(0.5, 12);
    expect(withColumnWidthMm(c, f1, -3).widthPx).toBeCloseTo(0.5, 12);
    expect(withColumnWidthMm(c, f1, NaN).widthPx).toBeCloseTo(0.5, 12);
  });

  test("width helpers are safe with no fit or a non-column: null / unchanged, never a throw", () => {
    const c = col("c1", spine4, 20);
    const closed = { id: "s1", points: spine4, curves: {} };
    for (const bad of [null, undefined, {}, { mmPerPx: 0 }, { mmPerPx: -1 }, { mmPerPx: NaN }]) {
      expect(columnWidthMm(c, bad)).toBeNull();
      expect(columnSewnMm(c, bad, 0.4)).toBeNull();
      expect(withColumnWidthMm(c, bad, 5)).toBe(c);
    }
    expect(columnWidthMm(closed, f1)).toBeNull();
    expect(columnSewnMm(closed, f1, 0.4)).toBeNull();
    expect(withColumnWidthMm(closed, f1, 5)).toBe(closed);
    expect(columnWidthMm(null, f1)).toBeNull();
    expect(withColumnWidthMm(null, f1, 5)).toBeNull();
  });

  test("ringInsideBox sees the RAILS: a spine inside the box whose rail is past it fails", () => {
    // spine along y = 0 from -40 to 40 px (±8 mm); box 20 x 6 mm -> half height 3 mm = 15 px
    const sp = [{ x: -40, y: 0 }, { x: 40, y: 0 }];
    expect(ringInsideBox(col("c1", sp, 20), f1, { wMm: 20, hMm: 6 })).toBe(true);   // rails at ±10 px = ±2 mm
    expect(ringInsideBox(col("c1", sp, 40), f1, { wMm: 20, hMm: 6 })).toBe(false);  // rails at ±20 px = ±4 mm
  });

  test("editedElementPatch refuses a column edit by shapeProblems' first string", () => {
    const R = rect("s1", 100, 100, 300, 300);
    const c = col("c1", [{ x: 350, y: 200 }, { x: 500, y: 200 }], 20);
    const e = { id: "e1", type: "manual", shapes: [R, c], sizeMm: 60, offsetXMm: 0, offsetYMm: 0 };
    const f = { cxPx: 300, cyPx: 200, mmPerPx: 0.15, offsetXMm: 0, offsetYMm: 0, pxPerMm: 6 };
    expect(editedElementPatch(e, f, "c1", applyAnchorDrag(c, 1, { x: 351, y: 200 }))).toEqual({ error: "This column is too short to sew." });
    expect(editedElementPatch(e, f, "c1", { ...c, points: c.points.slice(0, 1) })).toEqual({ error: "A column needs at least 2 points." });
    // a healthy two-point column is NOT refused (the closed-ring rule would say "Needs at least 3 points.")
    expect(editedElementPatch(e, f, "c1", applyAnchorDrag(c, 1, { x: 480, y: 220 })).error).toBeUndefined();
  });
});

describe("columns — the re-fit rule and ruling 12, through the real engine", () => {
  const R = rect("s1", 100, 100, 300, 300);
  // a STRAIGHT horizontal column whose right end is the bbox's right edge
  const C = col("c1", [{ x: 350, y: 200 }, { x: 425, y: 200 }, { x: 500, y: 200 }], 20);
  const gen = (element) => generateElement(element, garment, {});
  const outline = (d) => Object.fromEntries(d.shapeOutlines.map((o) => [o.id, o.points]));
  const residualOf = (off) => Math.round(off * 10) / 10 - off;
  // The rectangle moved by exactly the offsets' rounding residual (the existing tolerance) and the scale held.
  function rectangleHeld(before, patch) {
    const d0 = gen(before), d1 = gen({ ...before, ...patch });
    expect(d1.fit.mmPerPx).toBeCloseTo(d0.fit.mmPerPx, 12);
    const rx = residualOf(patch.offsetXMm) - residualOf(before.offsetXMm);
    const ry = residualOf(patch.offsetYMm) - residualOf(before.offsetYMm);
    expect(Math.abs(rx)).toBeLessThanOrEqual(0.05 + 1e-9);
    expect(Math.abs(ry)).toBeLessThanOrEqual(0.05 + 1e-9);
    const o0 = outline(d0), o1 = outline(d1);
    expect(o1.s1).toHaveLength(o0.s1.length);
    o1.s1.forEach((p, i) => { expect(p[0] - o0.s1[i][0]).toBeCloseTo(rx, 6); expect(p[1] - o0.s1[i][1]).toBeCloseTo(ry, 6); });
    return { d0, d1, o0, o1 };
  }

  test("(a) dragging one spine anchor: the rectangle stays put and the scale holds", () => {
    const before = el([R, C]);
    const d0 = gen(before);
    expect(d0.shapeOutlines.map((o) => o.id).sort()).toEqual(["c1", "s1"]);
    const moved = applyAnchorDrag(C, 2, { x: 560, y: 330 }); // outward: grows the bbox right and down
    const patch = editedElementPatch(before, d0.fit, "c1", moved);
    expect(patch.error).toBeUndefined();
    expect(patch.sizeMm).not.toBe(before.sizeMm);
    const { o0, o1 } = rectangleHeld(before, patch);
    expect(o1.c1).not.toEqual(o0.c1); // the column itself did move
    // Without the patch's size and offsets the engine re-fits the grown bbox: the jump the rule removes.
    const jumped = gen({ ...before, shapes: patch.shapes });
    expect(Math.abs(jumped.fit.mmPerPx / d0.fit.mmPerPx - 1)).toBeGreaterThan(0.05);
  });

  test("(b) doubling the width through refitShapesPatch: the rectangle stays put — the bbox is the rail ring", () => {
    // A TALL column this time, so its rails (not its spine) are the bbox's right edge:
    // the spine's bbox does not change with the width, the rail ring's does.
    const tall = col("c1", [{ x: 480, y: 120 }, { x: 480, y: 280 }], 20);
    const before = el([R, tall]);
    const d0 = gen(before);
    const mm0 = columnWidthMm(tall, d0.fit);
    const wide = withColumnWidthMm(tall, d0.fit, 2 * mm0);
    expect(wide.widthPx).toBeCloseTo(40, 9);
    const shapes = [R, wide];
    const patch = refitShapesPatch(before, d0.fit, shapes);
    expect(patch.error).toBeUndefined();
    // rail ring: 100 .. 490 px before, 100 .. 500 px after
    expect(before.sizeMm).toBeCloseTo(390 * d0.fit.mmPerPx, 9);
    expect(patch.sizeMm).toBeCloseTo(400 * d0.fit.mmPerPx, 9);
    const { d1 } = rectangleHeld(before, patch);
    expect(columnWidthMm(wide, d1.fit)).toBeCloseTo(2 * mm0, 9);
  });

  // The sewn width, measured from the stitches. The column's satin span is a
  // zigzag emitted station by station as (lead, trail), so consecutive stitch
  // points alternate between a CROSS (rail to rail — the width) and the short
  // step along one rail to the next station (the 0.4 mm spacing). The crosses
  // are the lengths over half the longest; the statistic is their MEDIAN, on a
  // straight column, so the ends and the 0.1 mm stitch grid do not move it.
  function sewnMedianMm(d, id) {
    const spans = d.runs.filter((r) => r.kind === "satin" && r.shape === id);
    expect(spans.length).toBeGreaterThan(0);
    const lens = [];
    for (const sp of spans) {
      for (let i = sp.i0 + 1; i <= sp.i1; i++) {
        const a = d.stitches[i - 1], b = d.stitches[i];
        if (b.type !== "stitch") continue;
        lens.push(Math.hypot(b.x - a.x, b.y - a.y) / 10);
      }
    }
    const longest = Math.max(...lens);
    const crosses = lens.filter((l) => l > longest / 2).sort((p, q) => p - q);
    expect(crosses.length).toBeGreaterThan(20);
    return crosses[Math.floor(crosses.length / 2)];
  }

  test("(c) ruling 12: at twice the size the DRAWN width doubles and the SEWN width grows by less — pull comp is fixed on top", () => {
    const pullCompMm = fabricInForce(garment.id, null).pullCompMm;
    expect(pullCompMm).toBeGreaterThan(0);
    const S = 40;
    // The spine sits 1.3 px off the bbox's centre line ON PURPOSE. Stitches land
    // on the 0.1 mm DST grid, and a column centred on a grid line with a sewn
    // half-width of x.x5 mm puts BOTH rails on a rounding tie: measured with the
    // spine at y = 200, the crosses read 2.2 and 4.2 mm for a 2.3 / 4.3 model —
    // the grid, not the engine's width. The sewn width is drawn + pull comp,
    // good to one 0.1 mm grid step; the fixture sits off the tie so the
    // numbers are deterministic.
    const C = col("c1", [{ x: 350, y: 201.3 }, { x: 425, y: 201.3 }, { x: 500, y: 201.3 }], 20);
    const dS = gen(el([R, C], { sizeMm: S, offsetXMm: 0, offsetYMm: 0 }));
    const d2 = gen(el([R, C], { sizeMm: 2 * S, offsetXMm: 0, offsetYMm: 0 }));
    expect(d2.fit.mmPerPx).toBeCloseTo(2 * dS.fit.mmPerPx, 9);
    const drawnS = columnWidthMm(C, dS.fit), drawn2 = columnWidthMm(C, d2.fit);
    expect(Math.abs(drawn2 - 2 * drawnS)).toBeLessThanOrEqual(0.05);
    const sewnS = sewnMedianMm(dS, "c1"), sewn2 = sewnMedianMm(d2, "c1");
    // Measured 2026-10-01 on left_chest (pull comp 0.3 mm): drawn 2.0 -> 4.0 mm,
    // sewn 2.3 -> 4.3 mm, ratio 1.870 against 2.000 for the drawn width.
    expect(pullCompMm).toBeCloseTo(0.3, 9);
    expect(drawnS).toBeCloseTo(2.0, 9);
    expect(sewnS).toBeCloseTo(2.3, 6);
    expect(sewn2).toBeCloseTo(4.3, 6);
    // the model: sewn = drawn + pull comp, at both sizes
    expect(Math.abs(sewnS - columnSewnMm(C, dS.fit, pullCompMm))).toBeLessThanOrEqual(0.1);
    expect(Math.abs(sewn2 - columnSewnMm(C, d2.fit, pullCompMm))).toBeLessThanOrEqual(0.1);
    const predicted = (2 * drawnS + pullCompMm) / (drawnS + pullCompMm);
    const ratio = sewn2 / sewnS;
    expect(ratio).toBeLessThan(2);
    expect(Math.abs(ratio - predicted)).toBeLessThanOrEqual(0.03);
  });
});
