// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/svelte";
import { render, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import CropBox from "./CropBox.svelte";

const SRC = "data:image/png;base64,iVBORw0KGgo=";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CropBox", () => {
  it("renders the full frame when given no crop", () => {
    render(CropBox, { src: SRC });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.width).toBe("100%");
    expect(box.style.height).toBe("100%");
  });

  it("positions the rectangle from fractions", () => {
    render(CropBox, { src: SRC, crop: { x0: 0.25, y0: 0.1, x1: 0.75, y1: 0.6 } });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.left).toBe("25%");
    expect(box.style.width).toBe("50%");
  });

  it("offers the reset even when uncropped, but disabled", () => {
    render(CropBox, { src: SRC });
    expect(screen.getByRole("button", { name: "Use whole image" })).toBeDisabled();
  });

  function stubHost() {
    // jsdom has no layout: give the host a 200 x 100 box so pixel deltas map to fractions.
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, right: 200, bottom: 100, width: 200, height: 100, x: 0, y: 0,
    });
  }
  function ptr(type, x, y) {
    const e = new Event(type, { bubbles: true, cancelable: true });
    e.clientX = x; e.clientY = y;
    return e;
  }

  it("has handles on every corner and every edge, all inside the box", () => {
    render(CropBox, { src: SRC });
    for (const n of ["top-left corner", "bottom-right corner", "top edge", "bottom edge", "left edge", "right edge"]) {
      expect(screen.getByRole("button", { name: `Drag ${n}` })).toBeInTheDocument();
    }
  });

  it("fires onchange ONCE, on pointerup, with the dragged fractions", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    const h = screen.getByRole("button", { name: "Drag right edge" });
    h.dispatchEvent(ptr("pointerdown", 100, 50));
    window.dispatchEvent(ptr("pointermove", 110, 50));
    window.dispatchEvent(ptr("pointermove", 120, 50));
    expect(onchange).not.toHaveBeenCalled();
    window.dispatchEvent(ptr("pointerup", 120, 50));
    expect(onchange).toHaveBeenCalledTimes(1);
    const n = onchange.mock.calls[0][0];
    expect(n.x1).toBeCloseTo(0.9); // +20 px of 200 = +0.1 from 0.8
    expect([n.x0, n.y0, n.y1]).toEqual([0.2, 0.2, 0.8]);
  });

  it("does not fire when a drag ends where it began", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    screen.getByRole("button", { name: "Drag right edge" }).dispatchEvent(ptr("pointerdown", 100, 50));
    window.dispatchEvent(ptr("pointerup", 100, 50));
    expect(onchange).not.toHaveBeenCalled();
  });

  it("refuses to shrink the box under 2% of the image", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    screen.getByRole("button", { name: "Drag right edge" }).dispatchEvent(ptr("pointerdown", 160, 50));
    // -150 px of 200 puts x1 at 0.05, width -0.15: below the floor, ignored.
    window.dispatchEvent(ptr("pointermove", 10, 50));
    window.dispatchEvent(ptr("pointerup", 10, 50));
    expect(onchange).not.toHaveBeenCalled();
  });

  it("honours a caller's minFrac above the default 2%", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange, minFrac: 0.3 });
    screen.getByRole("button", { name: "Drag right edge" }).dispatchEvent(ptr("pointerdown", 160, 50));
    // -70 px of 200 puts x1 at 0.45: width 0.25, above 2% but under 0.3.
    window.dispatchEvent(ptr("pointermove", 90, 50));
    window.dispatchEvent(ptr("pointerup", 90, 50));
    expect(onchange).not.toHaveBeenCalled();
  });

  it("a move dragged past the right/bottom edge stops flush, size preserved", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.3, y0: 0.3, x1: 0.7, y1: 0.7 }, onchange });
    screen.getByRole("group", { name: "Crop area" }).dispatchEvent(ptr("pointerdown", 100, 50));
    // +0.5 on each axis, more than the 0.3 of room there is.
    window.dispatchEvent(ptr("pointermove", 200, 100));
    window.dispatchEvent(ptr("pointerup", 200, 100));
    const n = onchange.mock.calls[0][0];
    expect(n.x1).toBeCloseTo(1);
    expect(n.y1).toBeCloseTo(1);
    expect(n.x1 - n.x0).toBeCloseTo(0.4);
    expect(n.y1 - n.y0).toBeCloseTo(0.4);
  });

  it("captures the pointer on the element that started the drag", () => {
    stubHost();
    const cap = vi.fn();
    HTMLElement.prototype.setPointerCapture = cap;
    try {
      render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 } });
      const h = screen.getByRole("button", { name: "Drag right edge" });
      const e = ptr("pointerdown", 100, 50);
      e.pointerId = 7;
      h.dispatchEvent(e);
      expect(cap).toHaveBeenCalledWith(7);
      expect(cap.mock.contexts[0]).toBe(h);
    } finally {
      delete HTMLElement.prototype.setPointerCapture;
    }
  });

  it("a pointercancel discards the drag: the box snaps back and nothing is emitted", () => {
    stubHost();
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    const box = screen.getByRole("group", { name: "Crop area" });
    screen.getByRole("button", { name: "Drag right edge" }).dispatchEvent(ptr("pointerdown", 100, 50));
    window.dispatchEvent(ptr("pointermove", 120, 50));
    window.dispatchEvent(ptr("pointercancel", 120, 50));
    // The drag is over: later moves and a stray pointerup change nothing.
    window.dispatchEvent(ptr("pointermove", 140, 50));
    window.dispatchEvent(ptr("pointerup", 140, 50));
    expect(onchange).not.toHaveBeenCalled();
    return Promise.resolve().then(() => expect(parseFloat(box.style.width)).toBeCloseTo(60));
  });

  it("emits the full frame when reset is clicked", () => {
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    screen.getByRole("button", { name: "Use whole image" }).click();
    expect(onchange).toHaveBeenCalledWith({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });
});
