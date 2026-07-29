import { test, expect } from "vitest";
import {
  designRectPx, hitTest, dragResize, dragMove, clampOffsets, pickElement, clampPan,
  buildSnapLines, snapMove, snapResizeWidth, rotateHandlePx, dragRotate, alignOffset,
} from "./interact.js";

// ---- designRectPx ---------------------------------------------------------

test("designRectPx maps an mm bbox to a canvas rect, +y up -> smaller canvas y at top", () => {
  // Simple identity-ish transform: origin at canvas (100,100), 2 px/mm, y flipped.
  const toCanvas = (xMm, yMm) => ({ x: 100 + xMm * 2, y: 100 - yMm * 2 });
  const bboxMm = { x0: -10, y0: -5, x1: 10, y1: 5 }; // 20mm wide, 10mm tall
  const rect = designRectPx(bboxMm, toCanvas);
  expect(rect.w).toBeCloseTo(40, 5); // 20mm * 2px/mm
  expect(rect.h).toBeCloseTo(20, 5); // 10mm * 2px/mm
  // x1 (right, larger mm x) -> larger canvas x; y1 (top, larger mm y) -> SMALLER canvas y
  expect(rect.x).toBeCloseTo(100 + -10 * 2, 5); // left edge from x0
  expect(rect.y).toBeCloseTo(100 - 5 * 2, 5); // top edge from y1 (the top in mm-space)
});

// ---- hitTest ---------------------------------------------------------------

const rect = { x: 100, y: 50, w: 200, h: 100 }; // corners: (100,50) (300,50) (100,150) (300,150)

test("hitTest recognizes all four corners within handleR", () => {
  expect(hitTest(rect, 100, 50, 8)).toBe("nw");
  expect(hitTest(rect, 300, 50, 8)).toBe("ne");
  expect(hitTest(rect, 100, 150, 8)).toBe("sw");
  expect(hitTest(rect, 300, 150, 8)).toBe("se");
});

test("hitTest corners win over body when overlapping", () => {
  // A point 3px from the nw corner is within handleR=8 AND inside the rect body area.
  expect(hitTest(rect, 103, 53, 8)).toBe("nw");
});

test("hitTest returns body for points inside the rect away from corners", () => {
  expect(hitTest(rect, 200, 100, 8)).toBe("body");
});

test("hitTest returns none for points outside the rect and away from corners", () => {
  expect(hitTest(rect, 10, 10, 8)).toBe("none");
  expect(hitTest(rect, 500, 500, 8)).toBe("none");
});

// ---- dragResize --------------------------------------------------------------

test("dragResize on a square design: se corner, equal dx/dy grows width predictably", () => {
  // square design: w=h=40mm; se growth rule: widthDelta = (dx + dy*(w/h))/2 = (dx+dy)/2 for square
  const w = dragResize(40, 40, "se", 10, 10, 5, 200);
  expect(w).toBeCloseTo(40 + 10, 5); // (10+10*1)/2 = 10
});

test("dragResize is aspect-consistent across opposite corners (nw mirrors se)", () => {
  // Dragging se outward (+dx,+dy) and nw outward (-dx,-dy) by the same magnitude
  // must produce the same growth (both corners moving away from center grow the design).
  const grow = dragResize(40, 40, "se", 10, 10, 5, 200);
  const growNw = dragResize(40, 40, "nw", -10, -10, 5, 200);
  expect(growNw).toBeCloseTo(grow, 5);
});

test("dragResize scales the dy contribution by aspect ratio for non-square designs", () => {
  // w=80,h=40 (aspect w/h=2): se with dx=0,dy=10 -> widthDelta=(0+10*2)/2=10
  const w = dragResize(80, 40, "se", 0, 10, 5, 200);
  expect(w).toBeCloseTo(90, 5);
});

test("dragResize never shrinks below minWmm even with a large negative delta", () => {
  const w = dragResize(40, 40, "se", -1000, -1000, 5, 200);
  expect(w).toBe(5);
});

test("dragResize never grows above maxWmm even with a large positive delta", () => {
  const w = dragResize(40, 40, "se", 1000, 1000, 5, 100);
  expect(w).toBe(100);
});

// ---- dragMove ------------------------------------------------------------------

test("dragMove: canvas dx right increases offsetX; canvas dy down DECREASES offsetY (+y up)", () => {
  const r = dragMove(0, 0, 5, 5, 20, 20, 200, 200);
  expect(r.offsetXMm).toBeCloseTo(5, 5);
  expect(r.offsetYMm).toBeCloseTo(-5, 5);
});

test("dragMove clamps at the right hoop edge", () => {
  // hoop 100x100, design 20x20 -> max offset = (100-20)/2 = 40
  const r = dragMove(0, 0, 1000, 0, 20, 20, 100, 100);
  expect(r.offsetXMm).toBeCloseTo(40, 5);
  expect(r.offsetYMm).toBeCloseTo(0, 5);
});

test("dragMove clamps at the left hoop edge", () => {
  const r = dragMove(0, 0, -1000, 0, 20, 20, 100, 100);
  expect(r.offsetXMm).toBeCloseTo(-40, 5);
});

test("dragMove clamps at the top hoop edge (canvas up = offset +y)", () => {
  // dragging pointer up (negative canvas dy) increases offsetY (design moves toward +y/top)
  const r = dragMove(0, 0, 0, -1000, 20, 20, 100, 100);
  expect(r.offsetYMm).toBeCloseTo(40, 5);
});

test("dragMove clamps at the bottom hoop edge (canvas down = offset -y)", () => {
  const r = dragMove(0, 0, 0, 1000, 20, 20, 100, 100);
  expect(r.offsetYMm).toBeCloseTo(-40, 5);
});

test("dragMove collapses the clamp range to 0 when the design is bigger than the hoop", () => {
  const r = dragMove(0, 0, 1000, 1000, 300, 300, 100, 100);
  expect(r.offsetXMm).toBe(0);
  expect(r.offsetYMm).toBe(0);
});

// ---- clampOffsets ---------------------------------------------------------
// Same clamp math dragMove uses, exposed standalone so EmbroideryField can
// re-clamp a persisted/stale offset (e.g. after a garment or size change)
// without synthesizing a fake drag delta.

test("clampOffsets passes through an offset that's already inside the hoop", () => {
  // hoop 100x100, design 20x20 -> max offset = 40; 10 is well inside.
  const r = clampOffsets(10, -10, 20, 20, 100, 100);
  expect(r.offsetXMm).toBeCloseTo(10, 5);
  expect(r.offsetYMm).toBeCloseTo(-10, 5);
});

test("clampOffsets clamps an over-the-edge offset back to the max on each axis", () => {
  const r = clampOffsets(1000, -1000, 20, 20, 100, 100);
  expect(r.offsetXMm).toBeCloseTo(40, 5);
  expect(r.offsetYMm).toBeCloseTo(-40, 5);
});

test("clampOffsets collapses the clamp range to 0 when the design is bigger than the hoop", () => {
  const r = clampOffsets(15, 15, 300, 300, 100, 100);
  expect(r.offsetXMm).toBe(0);
  expect(r.offsetYMm).toBe(0);
});

test("clampOffsets normalizes -0 to +0", () => {
  const r = clampOffsets(-1000, 0, 300, 20, 100, 100);
  expect(Object.is(r.offsetXMm, -0)).toBe(false);
  expect(r.offsetXMm).toBe(0);
});

test("dragMove delegates to clampOffsets (same result for the equivalent absolute offset)", () => {
  const viaDrag = dragMove(5, 5, 10, -20, 20, 20, 100, 100); // start (5,5), dx=10, dy=-20 -> raw (15, 25)
  const viaClamp = clampOffsets(15, 25, 20, 20, 100, 100);
  expect(viaDrag).toEqual(viaClamp);
});

// ---- clampPan --------------------------------------------------------------
// Same soft-clamp rule zoomBy() has always applied on zoom, now shared with
// the pan-drag branch of onPointerMove (EmbroideryField.svelte) so a
// pointer-capture drag that travels far past the canvas edge can't push the
// hoop entirely off-canvas.

test("clampPan passes through a pan that's already within range", () => {
  // canvas 760x560, zoom 2 -> maxPanX = (760*1)/2+40 = 420, maxPanY = (560*1)/2+40 = 320
  const r = clampPan(100, -50, 2, 760, 560);
  expect(r.panX).toBeCloseTo(100, 5);
  expect(r.panY).toBeCloseTo(-50, 5);
});

test("clampPan clamps an over-the-edge pan back to the max on each axis", () => {
  const r = clampPan(10000, -10000, 2, 760, 560);
  expect(r.panX).toBeCloseTo(420, 5);
  expect(r.panY).toBeCloseTo(-320, 5);
});

test("clampPan still allows the flat 40px slack at MIN_ZOOM (zoom=1)", () => {
  // At zoom=1 the "(cw*(zoom-1))/2" term is 0, leaving just the flat +40 slack.
  const r = clampPan(1000, 1000, 1, 760, 560);
  expect(r.panX).toBe(40);
  expect(r.panY).toBe(40);
});

test("clampPan's reachable range grows with zoom", () => {
  const atZoom2 = clampPan(10000, 0, 2, 760, 560);
  const atZoom4 = clampPan(10000, 0, 4, 760, 560);
  expect(atZoom4.panX).toBeGreaterThan(atZoom2.panX);
});

test("clampPan is symmetric (negative pan clamps to -max, matching positive's +max)", () => {
  const pos = clampPan(10000, 10000, 2, 760, 560);
  const neg = clampPan(-10000, -10000, 2, 760, 560);
  expect(neg.panX).toBeCloseTo(-pos.panX, 5);
  expect(neg.panY).toBeCloseTo(-pos.panY, 5);
});

// ---- pickElement -----------------------------------------------------------
// Topmost-wins hit-testing for multi-element click-to-select.

test("pickElement returns null (a miss) when no rect contains the point", () => {
  const rects = [{ id: "a", x: 0, y: 0, w: 10, h: 10 }];
  expect(pickElement(rects, 50, 50)).toBeNull();
});

test("pickElement returns null for an empty rects array", () => {
  expect(pickElement([], 10, 10)).toBeNull();
});

test("pickElement returns the id of the single rect containing the point", () => {
  const rects = [{ id: "a", x: 0, y: 0, w: 10, h: 10 }];
  expect(pickElement(rects, 5, 5)).toBe("a");
});

test("pickElement returns the only matching rect's id when rects don't overlap at that point", () => {
  const rects = [
    { id: "a", x: 0, y: 0, w: 10, h: 10 },
    { id: "b", x: 50, y: 50, w: 10, h: 10 },
  ];
  expect(pickElement(rects, 2, 2)).toBe("a");
  expect(pickElement(rects, 52, 52)).toBe("b");
});

test("pickElement picks the LAST matching rect on overlap (topmost wins, matching paint order)", () => {
  const rects = [
    { id: "a", x: 0, y: 0, w: 20, h: 20 },
    { id: "b", x: 5, y: 5, w: 20, h: 20 },
  ];
  // (10,10) is inside both -- "b" is later in array order (drawn on top), so it wins.
  expect(pickElement(rects, 10, 10)).toBe("b");
  // Reversed order flips the winner too -- it's purely array-order, not geometry.
  expect(pickElement([rects[1], rects[0]], 10, 10)).toBe("a");
});

test("pickElement treats rect edges as inclusive", () => {
  const rects = [{ id: "a", x: 10, y: 10, w: 10, h: 10 }];
  expect(pickElement(rects, 10, 10)).toBe("a"); // nw corner
  expect(pickElement(rects, 20, 20)).toBe("a"); // se corner
});

// ---- alignOffset -----------------------------------------------------------
// One-click flush align of an element inside the hoop (SizePanel's
// "Align in hoop" row). Shares clampOffsets' (hoop-design)/2 bound.

test("alignOffset: left/center/right land at -max / 0 / +max", () => {
  // hoop 100, design 20 -> max offset 40
  expect(alignOffset("left", 20, 100)).toBeCloseTo(-40, 5);
  expect(alignOffset("center", 20, 100)).toBe(0);
  expect(alignOffset("right", 20, 100)).toBeCloseTo(40, 5);
});

test("alignOffset: y-axis modes respect +y UP (top is positive)", () => {
  expect(alignOffset("top", 20, 100)).toBeCloseTo(40, 5);
  expect(alignOffset("bottom", 20, 100)).toBeCloseTo(-40, 5);
});

test("alignOffset: an unknown/absent mode centers", () => {
  expect(alignOffset(undefined, 20, 100)).toBe(0);
  expect(alignOffset("middle", 20, 100)).toBe(0);
});

test("alignOffset: a design bigger than the hoop has no slack — every mode centers", () => {
  expect(alignOffset("left", 300, 100)).toBe(0);
  expect(alignOffset("right", 300, 100)).toBe(0);
  expect(alignOffset("center", 300, 100)).toBe(0);
});

test("alignOffset: an exactly hoop-sized design pins to 0 on every mode", () => {
  expect(alignOffset("left", 100, 100)).toBe(0);
  expect(alignOffset("right", 100, 100)).toBe(0);
});

test("alignOffset results are already inside clampOffsets' range (clamping is a no-op)", () => {
  for (const mode of ["left", "center", "right"]) {
    const offX = alignOffset(mode, 20, 100);
    const r = clampOffsets(offX, 0, 20, 20, 100, 100);
    expect(r.offsetXMm).toBeCloseTo(offX, 5);
  }
});

// ---- buildSnapLines / snapMove ---------------------------------------------
// Move-drag auto-snap: other elements' edges/centers + the hoop centerlines.

test("buildSnapLines collects each bbox's edges and center per axis, plus the hoop centerlines", () => {
  const lines = buildSnapLines([{ x0: 10, y0: -20, x1: 30, y1: 0 }]);
  expect(lines.xs).toEqual([0, 10, 20, 30]); // hoop center, left, center, right
  expect(lines.ys).toEqual([0, -20, -10, 0]); // hoop center, bottom, center, top
});

test("buildSnapLines can exclude the hoop centerlines", () => {
  const lines = buildSnapLines([{ x0: 10, y0: 10, x1: 30, y1: 30 }], { hoopCenter: false });
  expect(lines.xs).toEqual([10, 20, 30]);
  expect(lines.ys).toEqual([10, 20, 30]);
});

test("snapMove snaps an edge to a nearby line within threshold and reports the guide", () => {
  // bbox right edge at 9.2, candidate line at 10, threshold 2 -> dx +0.8
  const bbox = { x0: -10.8, y0: 50, x1: 9.2, y1: 70 }; // y far from any candidate
  const s = snapMove(bbox, { xs: [10], ys: [0] }, 2);
  expect(s.dx).toBeCloseTo(0.8, 5);
  expect(s.guideXMm).toBe(10);
  expect(s.dy).toBe(0);
  expect(s.guideYMm).toBeNull();
});

test("snapMove snaps centers to the hoop centerline (the centering use case)", () => {
  // bbox center at x=1.5, y=-1.0; hoop centerlines at 0 -> pulls to dead center
  const bbox = { x0: -8.5, y0: -11, x1: 11.5, y1: 9 };
  const s = snapMove(bbox, buildSnapLines([]), 2);
  expect(s.dx).toBeCloseTo(-1.5, 5);
  expect(s.dy).toBeCloseTo(1.0, 5);
  expect(s.guideXMm).toBe(0);
  expect(s.guideYMm).toBe(0);
});

test("snapMove does not snap beyond the threshold", () => {
  const bbox = { x0: -10, y0: -10, x1: 10, y1: 10 }; // center (0,0), edges ±10
  const s = snapMove(bbox, { xs: [15], ys: [-16] }, 2); // nearest own lines 5 and 6 away
  expect(s.dx).toBe(0);
  expect(s.dy).toBe(0);
  expect(s.guideXMm).toBeNull();
  expect(s.guideYMm).toBeNull();
});

test("snapMove picks the nearest candidate when several are in range", () => {
  // right edge 10: candidates 10.5 (0.5 away) and 11.9 (1.9 away) -> 10.5 wins
  const bbox = { x0: -10, y0: 100, x1: 10, y1: 120 };
  const s = snapMove(bbox, { xs: [10.5, 11.9], ys: [] }, 2);
  expect(s.dx).toBeCloseTo(0.5, 5);
  expect(s.guideXMm).toBe(10.5);
});

test("snapMove axes are independent (y snaps to center while x stays put)", () => {
  // x: center 5, edges -5/15 — all > 2mm from the only candidate (0) -> no snap.
  // y: center 0.8 -> snaps to the hoop centerline.
  const bbox = { x0: -5, y0: -9.2, x1: 15, y1: 10.8 };
  const s = snapMove(bbox, buildSnapLines([]), 2);
  expect(s.dx).toBe(0);
  expect(s.guideXMm).toBeNull();
  expect(s.dy).toBeCloseTo(-0.8, 5);
  expect(s.guideYMm).toBe(0);
});

// ---- snapResizeWidth --------------------------------------------------------
// Aspect-locked resize snapping to another element's exact width or height.

test("snapResizeWidth snaps to another element's width within threshold", () => {
  const s = snapResizeWidth(41.2, 2, [{ w: 40, h: 100 }], 1.5);
  expect(s.widthMm).toBe(40);
  expect(s.match).toBe("width");
});

test("snapResizeWidth snaps via HEIGHT equality through the aspect ratio", () => {
  // dragged aspect w/h=2 -> matching other's h=15 needs width 30
  const s = snapResizeWidth(30.8, 2, [{ w: 100, h: 15 }], 1.5);
  expect(s.widthMm).toBeCloseTo(30, 5);
  expect(s.match).toBe("height");
});

test("snapResizeWidth leaves the width alone beyond the threshold", () => {
  const s = snapResizeWidth(45, 2, [{ w: 40, h: 100 }], 1.5);
  expect(s.widthMm).toBe(45);
  expect(s.match).toBeNull();
});

test("snapResizeWidth picks the nearest candidate across elements and kinds", () => {
  // width candidates: 40 (1.2 away); height candidates: 20.5*2=41 (0.2 away) -> height wins
  const s = snapResizeWidth(41.2, 2, [{ w: 40, h: 20.5 }], 1.5);
  expect(s.widthMm).toBeCloseTo(41, 5);
  expect(s.match).toBe("height");
});

// ---- rotateHandlePx / dragRotate -------------------------------------------
// The lollipop rotate handle above the selection box (text elements only).

test("rotateHandlePx sits centered above the rect's top edge by stalkPx", () => {
  const p = rotateHandlePx({ x: 100, y: 50, w: 200, h: 100 }, 22);
  expect(p.x).toBe(200);
  expect(p.y).toBe(28);
});

// Canvas-px point at `deg` (y-up screen convention) on a 100px circle around c.
const ptAt = (c, deg) => ({
  x: c.x + Math.cos((deg * Math.PI) / 180) * 100,
  y: c.y - Math.sin((deg * Math.PI) / 180) * 100,
});
const C = { x: 400, y: 300 };

test("dragRotate: sweeping the pointer counterclockwise 90° adds 90° (engine's +deg direction)", () => {
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 180))).toBe(90);
});

test("dragRotate is delta-based: starting rotation is preserved under a small sweep", () => {
  expect(dragRotate(30, C, ptAt(C, 90), ptAt(C, 100))).toBe(40);
});

test("dragRotate normalizes into [0,360) across the wrap", () => {
  expect(dragRotate(350, C, ptAt(C, 90), ptAt(C, 110))).toBe(10); // 350+20 -> 10
  expect(dragRotate(10, C, ptAt(C, 90), ptAt(C, 70))).toBe(350); // 10-20 -> 350
});

test("dragRotate magnets onto 45° multiples within 3°", () => {
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 134))).toBe(45); // raw 44 -> 45
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 178))).toBe(90); // raw 88 -> 90
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 92))).toBe(0); // raw 2 -> 0
});

test("dragRotate with free:true skips the magnets", () => {
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 134), { free: true })).toBe(44);
});

test("dragRotate magnet near 360 wraps to 0", () => {
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 88), { magnetDeg: 3 })).toBe(0); // raw 358 -> 0
});

test("dragRotate leaves an angle mid-way between magnets untouched", () => {
  expect(dragRotate(0, C, ptAt(C, 90), ptAt(C, 112))).toBe(22); // raw 22, nearest 45 is 23 away
});

// ---- multi-select group geometry -------------------------------------------

import { unionBBox, clampGroupDelta, groupResizePatches } from "./interact.js";

test("unionBBox spans all members; null for empty", () => {
  expect(unionBBox([])).toBeNull();
  const u = unionBBox([
    { x0: -10, y0: 0, x1: 10, y1: 8 },
    { x0: -14, y0: -20, x1: 6, y1: -12 },
  ]);
  expect(u).toEqual({ x0: -14, y0: -20, x1: 10, y1: 8 });
});

test("clampGroupDelta passes an in-range delta and clamps at hoop edges", () => {
  const g = { x0: -10, y0: -5, x1: 10, y1: 5 }; // 20x10 group, centered
  // hoop 100x50: slack 40 each side in x, 20 in y
  expect(clampGroupDelta(15, -10, g, 100, 50)).toEqual({ dxMm: 15, dyMm: -10 });
  expect(clampGroupDelta(1000, -1000, g, 100, 50)).toEqual({ dxMm: 40, dyMm: -20 });
});

test("clampGroupDelta collapses to 0 on an axis where the group exceeds the hoop", () => {
  const g = { x0: -60, y0: -5, x1: 60, y1: 5 }; // 120 wide vs 100 hoop
  const r = clampGroupDelta(10, 3, g, 100, 50);
  expect(r.dxMm).toBe(0);
  expect(r.dyMm).toBe(3);
});

test("groupResizePatches scales targets and offsets about the group center", () => {
  const members = [
    { id: "e1", widthMm: 40, targetMm: 40, offsetXMm: -15, offsetYMm: 10 },
    { id: "e2", widthMm: 20, targetMm: 20, offsetXMm: 15, offsetYMm: -10 },
  ];
  const { patches, factor } = groupResizePatches(members, 2, 5, 0, 5);
  expect(factor).toBe(2);
  expect(patches.e1).toEqual({ sizeMm: 80, offsetXMm: 5 + (-15 - 5) * 2, offsetYMm: 20 });
  expect(patches.e2).toEqual({ sizeMm: 40, offsetXMm: 5 + (15 - 5) * 2, offsetYMm: -20 });
});

test("groupResizePatches raises the factor so no member drops below minWmm", () => {
  const members = [
    { id: "big", widthMm: 100, targetMm: 100, offsetXMm: 0, offsetYMm: 0 },
    { id: "small", widthMm: 10, targetMm: 10, offsetXMm: 20, offsetYMm: 0 },
  ];
  // requested 0.2 would take "small" to 2mm; min 5 -> factor raised to 0.5
  const { patches, factor } = groupResizePatches(members, 0.2, 0, 0, 5);
  expect(factor).toBeCloseTo(0.5, 10);
  expect(patches.small.sizeMm).toBeCloseTo(5, 10);
  expect(patches.big.sizeMm).toBeCloseTo(50, 10);
});

test("groupResizePatches with factor 1 is an identity for offsets and targets", () => {
  const members = [{ id: "e1", widthMm: 30, targetMm: 28, offsetXMm: -7, offsetYMm: 3 }];
  const { patches } = groupResizePatches(members, 1, 0, 0, 5);
  expect(patches.e1).toEqual({ sizeMm: 28, offsetXMm: -7, offsetYMm: 3 });
});

// ---- rotateHandlePx flip (grip reachable at high zoom) ----------------------

test("rotateHandlePx default hangs above the top edge; flip hangs below the bottom", () => {
  const r = { x: 100, y: 50, w: 200, h: 100 };
  expect(rotateHandlePx(r, 22)).toEqual({ x: 200, y: 28 });
  expect(rotateHandlePx(r, 22, { flip: true })).toEqual({ x: 200, y: 172 }); // y + h + stalk
});

test("rotateHandlePx flip:false matches the default exactly", () => {
  const r = { x: 0, y: 40, w: 60, h: 30 };
  expect(rotateHandlePx(r, 22, { flip: false })).toEqual(rotateHandlePx(r, 22));
});
