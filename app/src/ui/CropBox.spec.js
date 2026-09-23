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
});
