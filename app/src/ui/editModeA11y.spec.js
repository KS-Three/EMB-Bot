// @vitest-environment jsdom
// Keyboard / screen-reader contract of Move shape, Reshape mode and Add hole.
import { expect, test, describe } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { readFileSync } from "node:fs";
import { editModeBar, stepHoleCursor, ringCentre, holePointPhrase, MODE_SAYS } from "../src/lib/editModeA11y.js";
import Harness from "./EditModeBar.testHarness.svelte";

describe("editModeBar model", () => {
  test("null when no mode is on", () => {
    expect(editModeBar({ move: false, reshape: false, holePoints: null })).toBeNull();
    expect(editModeBar(null)).toBeNull();
  });
  test("each mode names every canvas-strip action as a button", () => {
    expect(editModeBar({ move: true }).buttons.map((b) => b.id)).toEqual(["moveDone", "moveCancel"]);
    expect(editModeBar({ reshape: true }).buttons.map((b) => b.id)).toEqual(["reshapeDone", "reshapeDiscard"]);
    expect(editModeBar({ holePoints: 0 }).buttons.map((b) => b.id)).toEqual(["holeClose", "holeUndo", "holeCancel"]);
  });
  test("every button and bar has a non-empty accessible name and hint", () => {
    for (const st of [{ move: true }, { reshape: true }, { holePoints: 2 }]) {
      const bar = editModeBar(st);
      expect(bar.label.length).toBeGreaterThan(0);
      expect(bar.hint.length).toBeGreaterThan(10);
      for (const b of bar.buttons) expect(b.label.trim().length).toBeGreaterThan(0);
    }
  });
  test("hole: Close needs three points, Remove needs one", () => {
    const by = (n) => Object.fromEntries(editModeBar({ holePoints: n }).buttons.map((b) => [b.id, b.disabled]));
    expect(by(0)).toMatchObject({ holeClose: true, holeUndo: true, holeCancel: false });
    expect(by(2)).toMatchObject({ holeClose: true, holeUndo: false });
    expect(by(3)).toMatchObject({ holeClose: false, holeUndo: false });
  });
  test("hint names the keyboard path: Escape cancels, Enter commits", () => {
    expect(editModeBar({ move: true }).hint).toMatch(/Enter finishes, Escape cancels/);
    expect(editModeBar({ holePoints: 0 }).hint).toMatch(/Enter closes/);
    expect(editModeBar({ holePoints: 0 }).hint).toMatch(/Escape cancels/);
    expect(editModeBar({ reshape: true }).hint).toMatch(/Enter or Escape/);
  });
  test("every mode has enter / end announcements", () => {
    for (const k of ["moveEnter", "moveDone", "moveCancel", "reshapeEnter", "reshapeDone", "reshapeDiscard", "holeEnter", "holeClosed", "holeCancel", "holeNeedThree"]) {
      expect(MODE_SAYS[k]).toBeTruthy();
    }
  });
});

describe("hole keyboard cursor", () => {
  test("arrows step 1 mm, Shift 5 mm, +y is up", () => {
    expect(stepHoleCursor([10, 10], "ArrowRight", false)).toEqual([11, 10]);
    expect(stepHoleCursor([10, 10], "ArrowLeft", true)).toEqual([5, 10]);
    expect(stepHoleCursor([10, 10], "ArrowUp", false)).toEqual([10, 11]);
    expect(stepHoleCursor([10, 10], "ArrowDown", true)).toEqual([10, 5]);
    expect(stepHoleCursor([10, 10], "a", false)).toBeNull();
  });
  test("ringCentre and the point phrase", () => {
    expect(ringCentre([[0, 0], [10, 0], [10, 10], [0, 10]])).toEqual([5, 5]);
    expect(ringCentre([])).toEqual([0, 0]);
    expect(holePointPhrase(2, 5, 6.25)).toBe("Point 2 placed at 5.0, 6.3 mm");
  });
});

describe("EditModeBar component", () => {
  test("renders nothing when no mode", () => {
    const { queryByTestId } = render(Harness, { props: { bar: null } });
    expect(queryByTestId("modebar")).toBeNull();
  });
  test("a named group whose buttons are tabbable by name and fire actions", async () => {
    const seen = [];
    const { getByRole, getByTestId } = render(Harness, { props: { bar: editModeBar({ reshape: true }), onEvent: (id) => seen.push(id) } });
    expect(getByRole("group", { name: "Edit points" })).toBeInTheDocument();
    expect(getByTestId("modebar")).toHaveAccessibleDescription(/Enter or Escape/);
    const done = getByRole("button", { name: "Done editing points" });
    const discard = getByRole("button", { name: "Discard point edits" });
    expect(done.tabIndex).toBe(0);
    expect(discard.tabIndex).toBe(0);
    await fireEvent.click(done);
    await fireEvent.click(discard);
    expect(seen).toEqual(["reshapeDone", "reshapeDiscard"]);
  });
  test("Close hole is disabled until three points", async () => {
    const seen = [];
    const { getByRole } = render(Harness, { props: { bar: editModeBar({ holePoints: 2 }), onEvent: (id) => seen.push(id) } });
    const close = getByRole("button", { name: "Close hole" });
    expect(close).toBeDisabled();
    await fireEvent.click(getByRole("button", { name: "Cancel hole" }));
    expect(seen).toEqual(["holeCancel"]);
  });
});

describe("EmbroideryField wiring (source pins; the canvas is not mountable in jsdom)", () => {
  const src = readFileSync("src/ui/EmbroideryField.svelte", "utf8");
  test("mounts the bar beside the live region, outside .hoop", () => {
    expect(src).toMatch(/<EditModeBar bar=\{modeBar\} on:action=\{onModeBarAction\}/);
    expect(src.indexOf("<EditModeBar")).toBeGreaterThan(src.indexOf('class="fieldlive"'));
  });
  test("Escape cancels hole draft and move; Enter commits both", () => {
    expect(src).toMatch(/if \(e\.key === "Escape"\) \{ endShapeMove\(\)/);
    expect(src).toMatch(/if \(e\.key === "Escape"\) \{ cancelHoleDraft\(\)/);
    expect(src).toMatch(/commitShapeMove\(\);\s+e\.preventDefault/);
    expect(src).toMatch(/closeHoleDraft\(\)/);
  });
  test("arrows and Space drive the hole cursor instead of nudging the design", () => {
    expect(src).toMatch(/holeDraftOn\(\) && \(e\.key\.startsWith\("Arrow"\) \|\| e\.key === " "\)/);
  });
});
