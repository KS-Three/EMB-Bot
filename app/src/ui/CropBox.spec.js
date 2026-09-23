// @vitest-environment jsdom
//
// Component-level coverage for CropBox.svelte -- the draggable crop
// rectangle over the upload preview (Task 7). Pure presentational
// component, props in / onchange callback out, no engine or store
// dependency -- like Icon.spec.js, rendered directly with no test harness
// needed (its `onchange` is a plain callback prop, not a dispatched
// Svelte event, so Svelte 5's render(Component, { props }) reaches it
// directly; the harness-wrapper pattern elsewhere in this directory exists
// only for components that dispatch through `createEventDispatcher`, e.g.
// ManualPanel.spec.js's own comment).
//
// Fix round 2 added the "dragging" describe block below, simulating the
// real pointerdown/pointermove/pointerup/pointercancel sequence -- the
// coverage gap the round-1 review flagged: round 1's actual mechanism
// (draft state gating `onchange` to fire exactly once, on release) had no
// automated test anywhere, so nothing would have stopped someone re-adding
// `onchange(next)` inside `move()` and reintroducing the localStorage-
// thrashing bug that round fixed. `fireEvent.pointerDown/Move/Up/Cancel`
// work fine in this project's vitest/jsdom setup -- ManualPanel.spec.js's
// own drag tests are the existing precedent, including its fix for the same
// underlying gap this file has: jsdom's `getBoundingClientRect` returns an
// all-zero rect by default (no real layout engine), which would make
// `move()`'s `dx`/`dy` divide by zero. Stubbed the same way, below.
import { beforeAll, describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import CropBox from "./CropBox.svelte";

beforeAll(() => {
  // Stubbed on the generic Element prototype, not HTMLCanvasElement --
  // CropBox measures a plain <div> (`.crop-host`), not a canvas. A 200x200
  // box makes the drag math easy to hand-check: one pixel of clientX/Y
  // movement is exactly 0.005 of a fraction on either axis.
  Element.prototype.getBoundingClientRect = () => ({
    left: 0, top: 0, right: 200, bottom: 200, width: 200, height: 200, x: 0, y: 0, toJSON() {},
  });
});

describe("CropBox", () => {
  it("renders the full frame when given no crop", () => {
    render(CropBox, { src: "data:image/png;base64,iVBORw0KGgo=" });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.width).toBe("100%");
    expect(box.style.height).toBe("100%");
  });

  it("positions the rectangle from fractions", () => {
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.25, y0: 0.1, x1: 0.75, y1: 0.6 },
    });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.left).toBe("25%");
    expect(box.style.width).toBe("50%");
  });

  it("offers the reset even when uncropped, but disabled", () => {
    render(CropBox, { src: "data:image/png;base64,iVBORw0KGgo=" });
    expect(screen.getByRole("button", { name: "Use whole image" })).toBeDisabled();
  });

  it("emits the full frame when reset is clicked", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 },
      onchange,
    });
    screen.getByRole("button", { name: "Use whole image" }).click();
    expect(onchange).toHaveBeenCalledWith({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });
});

// ---- dragging: draft gating, single emit on release (fix round 2) ---------
//
// Round 1's fix (draft state, onchange only on drag end) had no test that
// actually drove a pointer sequence -- these do. All four dispatch straight
// on `.crop-rect` (the "Crop area" group, the move handle's own pointerdown
// target); pointermove/up/cancel are bound on the ancestor `.crop-host`
// (CropBox.svelte's own comment explains why: matches the capture-on-
// descendant/listen-on-ancestor pattern this codebase's other drag handlers
// use), so dispatching on the descendant and letting it bubble is the same
// path a real drag takes.
describe("CropBox dragging", () => {
  const START = { x0: 0.2, y0: 0.2, x1: 0.6, y1: 0.6 }; // 0.4 x 0.4 box

  function renderDragging(onchange) {
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { ...START },
      onchange,
    });
    return screen.getByRole("group", { name: "Crop area" });
  }

  it("pointerdown, several pointermoves, pointerup: onchange fires exactly once, with the final rectangle", async () => {
    const onchange = vi.fn();
    const box = renderDragging(onchange);
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 120, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 140, clientY: 110, pointerId: 1 });
    expect(onchange).not.toHaveBeenCalled();
    await fireEvent.pointerUp(box, { clientX: 140, clientY: 110, pointerId: 1 });
    expect(onchange).toHaveBeenCalledTimes(1);
    // 200x200 host: total movement is dx=40px/200=0.2, dy=10px/200=0.05,
    // applied to the 0.2/0.2/0.6/0.6 starting box.
    const [got] = onchange.mock.calls[0];
    expect(got.x0).toBeCloseTo(0.4, 5);
    expect(got.y0).toBeCloseTo(0.25, 5);
    expect(got.x1).toBeCloseTo(0.8, 5);
    expect(got.y1).toBeCloseTo(0.65, 5);
  });

  it("pointerdown and pointermoves with no pointerup yet: onchange has not fired", async () => {
    const onchange = vi.fn();
    const box = renderDragging(onchange);
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 130, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 160, clientY: 90, pointerId: 1 });
    expect(onchange).not.toHaveBeenCalled();
    // The rectangle itself IS tracking the pointer, though -- draft gates
    // onchange, not the on-screen box (round 1's whole point).
    expect(box.style.left).toBe("50%"); // 0.2 + 60px/200
  });

  it("a cancelled gesture reverts the displayed rectangle to the committed crop, not the abandoned draft", async () => {
    const onchange = vi.fn();
    const box = renderDragging(onchange);
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(box, { clientX: 140, clientY: 110, pointerId: 1 });
    // Mid-drag: the box has moved off the committed crop's 20%/20%.
    expect(box.style.left).toBe("40%");
    await fireEvent.pointerCancel(box, { pointerId: 1 });
    expect(onchange).not.toHaveBeenCalled();
    // Finding 3: reverted to the still-committed START box, not frozen on
    // the abandoned draft.
    expect(box.style.left).toBe("20%");
    expect(box.style.top).toBe("20%");
    expect(box.style.width).toBe("40%");
    expect(box.style.height).toBe("40%");
    // And the drag is genuinely OVER, not merely paused: a fresh pointermove
    // with no new pointerdown must not resume it.
    await fireEvent.pointerMove(box, { clientX: 180, clientY: 150, pointerId: 1 });
    expect(box.style.left).toBe("20%");
  });

  it("pointerdown then pointerup with no movement at all: onchange does not fire", async () => {
    const onchange = vi.fn();
    const box = renderDragging(onchange);
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerUp(box, { clientX: 100, clientY: 100, pointerId: 1 });
    expect(onchange).not.toHaveBeenCalled();
  });

  // Finding 7 (2026-09-22 review): `next.x1 = clamp(next.x0 + w)` let x1
  // saturate at 1 while x0 kept advancing, so a move past the right/bottom
  // edge SHRANK the box instead of stopping it. A 0.4x0.4 box moved right
  // and down by 0.5 (well past the 0.3 of room it actually has on either
  // axis, box starting at 0.3/0.3/0.7/0.7) must stop flush against the
  // edges at its ORIGINAL size, not shrink into a corner.
  it("a move dragged past the right/bottom edge stops flush against them, size preserved", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.3, y0: 0.3, x1: 0.7, y1: 0.7 },
      onchange,
    });
    const box = screen.getByRole("group", { name: "Crop area" });
    await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
    // dx = dy = 100px / 200px host = 0.5 -- more room than the 0.3 available.
    await fireEvent.pointerMove(box, { clientX: 200, clientY: 200, pointerId: 1 });
    await fireEvent.pointerUp(box, { clientX: 200, clientY: 200, pointerId: 1 });
    expect(onchange).toHaveBeenCalledTimes(1);
    const [got] = onchange.mock.calls[0];
    expect(got.x0).toBeCloseTo(0.6, 5);
    expect(got.y0).toBeCloseTo(0.6, 5);
    expect(got.x1).toBeCloseTo(1.0, 5);
    expect(got.y1).toBeCloseTo(1.0, 5);
    // The width/height the box started with, not the ~0.2 the old code left.
    expect(got.x1 - got.x0).toBeCloseTo(0.4, 5);
    expect(got.y1 - got.y0).toBeCloseTo(0.4, 5);
  });
});

// ---- minFrac: a caller-supplied drag floor (finding 4, 2026-09-22 review) -
//
// CropBox's own minimum used to be a hardcoded 2%, which is under the
// service's 16 px floor on any preview raster narrower than 800 px.
// `minFrac` lets a caller (DigitizePanel, from the preview's own pixel
// size) raise that floor; these drive the same resize-handle path finding
// 8's edge handles use, so they also exercise HANDLES/HANDLE_LABEL beyond
// the pre-existing corner-only coverage above.
describe("CropBox minFrac", () => {
  it("rejects a resize below a caller-supplied minFrac even though it clears the default 0.02", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.0, y0: 0.0, x1: 0.5, y1: 0.5 },
      onchange,
      minFrac: 0.3,
    });
    const handle = screen.getByRole("button", { name: "Drag se corner" });
    await fireEvent.pointerDown(handle, { clientX: 100, clientY: 100, pointerId: 1 });
    // dx = dy = -45px / 200px host = -0.225 -> shrinks the 0.5-wide box to
    // 0.275, which is under the 0.3 minFrac but well above the default 0.02.
    await fireEvent.pointerMove(handle, { clientX: 55, clientY: 55, pointerId: 1 });
    await fireEvent.pointerUp(handle, { clientX: 55, clientY: 55, pointerId: 1 });
    // The pre-fix component (flat 0.02) would have accepted this resize;
    // with minFrac: 0.3 it must not.
    expect(onchange).not.toHaveBeenCalled();
  });

  it("the default (no minFrac passed) still allows a resize below 0.3, matching the pre-fix 0.02 floor", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.0, y0: 0.0, x1: 0.5, y1: 0.5 },
      onchange,
    });
    const handle = screen.getByRole("button", { name: "Drag se corner" });
    await fireEvent.pointerDown(handle, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(handle, { clientX: 55, clientY: 55, pointerId: 1 });
    await fireEvent.pointerUp(handle, { clientX: 55, clientY: 55, pointerId: 1 });
    expect(onchange).toHaveBeenCalledTimes(1);
  });
});

// ---- edge handles (finding 8, 2026-09-22 review) ---------------------------
//
// Spec section 6 asks for handles on corners AND edges; `move()` already
// implemented the single-axis logic for them (`h.includes("w")` etc. work
// fine for a one-letter handle name) -- the array just never emitted them.
describe("CropBox edge handles", () => {
  it("renders all four edge handles alongside the four corners", () => {
    render(CropBox, { src: "data:image/png;base64,iVBORw0KGgo=" });
    for (const name of ["Drag top edge", "Drag bottom edge", "Drag left edge", "Drag right edge"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    for (const name of ["Drag nw corner", "Drag ne corner", "Drag sw corner", "Drag se corner"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
  });

  it("dragging the right edge handle resizes only x1", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.2, y0: 0.2, x1: 0.6, y1: 0.6 },
      onchange,
    });
    const handle = screen.getByRole("button", { name: "Drag right edge" });
    await fireEvent.pointerDown(handle, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(handle, { clientX: 140, clientY: 130, pointerId: 1 });   // dx=0.2, dy=0.15 (ignored on this axis)
    await fireEvent.pointerUp(handle, { clientX: 140, clientY: 130, pointerId: 1 });
    expect(onchange).toHaveBeenCalledTimes(1);
    const [got] = onchange.mock.calls[0];
    expect(got.x0).toBeCloseTo(0.2, 5);
    expect(got.y0).toBeCloseTo(0.2, 5);
    expect(got.x1).toBeCloseTo(0.8, 5);
    expect(got.y1).toBeCloseTo(0.6, 5);   // untouched by a right-edge drag
  });
});
