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
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import CropBox from "./CropBox.svelte";

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
