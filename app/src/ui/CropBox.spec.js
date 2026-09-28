// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/svelte";
import { render, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import CropBox from "./CropBox.svelte";

const SRC = "data:image/png;base64,iVBORw0KGgo=";

afterEach(cleanup);

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

  it("emits the full frame when reset is clicked", () => {
    const onchange = vi.fn();
    render(CropBox, { src: SRC, crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 }, onchange });
    screen.getByRole("button", { name: "Use whole image" }).click();
    expect(onchange).toHaveBeenCalledWith({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });
});
