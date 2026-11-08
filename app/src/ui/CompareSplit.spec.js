// @vitest-environment jsdom
//
// CompareSplit.svelte: the Compare view's overlay. The field renders the
// artwork side offscreen and hands it in as `src` (an <img>, never a second
// <canvas> in .hoop); the component owns only the split (a CSS clip) and its
// handle. Pointer geometry and the no-layout-space
// overlay rule are pinned in e2e/field-compare.spec.js (jsdom has
// no layout or stylesheet); here: the handle's accessible contract, its keys,
// and that keys it does not own pass through to the field.
import { describe, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import CompareSplit from "./CompareSplit.svelte";

function handleOf(utils) {
  return utils.getByRole("separator", { name: "Compare split" });
}
const SRC = "data:image/png;base64,iVBORw0KGgo=";
function artOf(utils) {
  return utils.container.querySelector("img.cmp-art");
}

describe("the handle's accessible contract", () => {
  test("a focusable vertical separator with a name and both sides in its value", () => {
    const utils = render(CompareSplit, { props: { split: 0.5 } });
    const h = handleOf(utils);
    expect(h).toHaveAttribute("tabindex", "0");
    expect(h).toHaveAttribute("aria-orientation", "vertical");
    expect(h).toHaveAttribute("aria-valuemin", "0");
    expect(h).toHaveAttribute("aria-valuemax", "100");
    expect(h).toHaveAttribute("aria-valuenow", "50");
    expect(h).toHaveAttribute("aria-valuetext", "Artwork 50%, stitches 50%");
  });

  test("the artwork image is hidden from assistive tech and clipped to the split", () => {
    const utils = render(CompareSplit, { props: { split: 0.3, src: SRC } });
    const art = artOf(utils);
    expect(art).toHaveAttribute("src", SRC);
    expect(art).toHaveAttribute("alt", "");
    expect(art).toHaveAttribute("aria-hidden", "true");
    expect(art.getAttribute("style")).toContain("inset(0 70% 0 0)");
    expect(handleOf(utils).getAttribute("style")).toContain("left: 30%");
  });

  test("no <canvas> of its own, and no image until the field has one", () => {
    const utils = render(CompareSplit, { props: { split: 0.5 } });
    expect(utils.container.querySelector("canvas")).toBeNull();
    expect(artOf(utils)).toBeNull();
    expect(handleOf(utils)).toBeInTheDocument();
  });
});

describe("keys", () => {
  test("arrows move the split, Shift moves it further, Home/End go to the ends", async () => {
    const utils = render(CompareSplit, { props: { split: 0.5, src: SRC } });
    const h = handleOf(utils);
    await fireEvent.keyDown(h, { key: "ArrowRight" });
    expect(h).toHaveAttribute("aria-valuenow", "52");
    await fireEvent.keyDown(h, { key: "ArrowLeft", shiftKey: true });
    expect(h).toHaveAttribute("aria-valuenow", "42");
    await fireEvent.keyDown(h, { key: "End" });
    expect(h).toHaveAttribute("aria-valuenow", "100");
    expect(artOf(utils).getAttribute("style")).toContain("inset(0 0% 0 0)");
    await fireEvent.keyDown(h, { key: "Home" });
    expect(h).toHaveAttribute("aria-valuenow", "0");
  });

  test("a key the handle uses never reaches the window (no field nudge, no Delete)", async () => {
    const utils = render(CompareSplit, { props: { split: 0.5 } });
    const onWin = vi.fn();
    window.addEventListener("keydown", onWin);
    try {
      await fireEvent.keyDown(handleOf(utils), { key: "ArrowLeft" });
      expect(onWin).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener("keydown", onWin);
    }
  });

  test("keys it does not own pass through untouched: Tab, [ ], < > , ., modified arrows", async () => {
    const utils = render(CompareSplit, { props: { split: 0.5 } });
    const h = handleOf(utils);
    const seen = [];
    const onWin = (e) => seen.push({ key: e.key, prevented: e.defaultPrevented });
    window.addEventListener("keydown", onWin);
    try {
      for (const key of ["Tab", "[", "]", "<", ">", ",", "."]) await fireEvent.keyDown(h, { key });
      await fireEvent.keyDown(h, { key: "ArrowLeft", ctrlKey: true });
    } finally {
      window.removeEventListener("keydown", onWin);
    }
    expect(seen.map((s) => s.key)).toEqual(["Tab", "[", "]", "<", ">", ",", ".", "ArrowLeft"]);
    expect(seen.every((s) => !s.prevented)).toBe(true);
    expect(h).toHaveAttribute("aria-valuenow", "50");
  });
});

