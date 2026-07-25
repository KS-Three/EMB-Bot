import { test, expect } from "vitest";
import { designRectPx, hitTest, dragResize, dragMove, clampOffsets, pickElement } from "./interact.js";

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
