// @vitest-environment jsdom
// Keyboard / screen-reader contract of Move shape, Reshape mode and Add hole.
import { expect, test, describe } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { readFileSync } from "node:fs";
import { editModeBar, stepHoleCursor, ringCentre, holePointPhrase, MODE_SAYS, stepNodeCursor, nodeCursorPhrase, sameNode } from "../lib/editModeA11y.js";
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

describe("Reshape node cursor", () => {
  // Two shapes: a 3-point shell + a 2-point hole ring on "a", then a 2-point shell on "b".
  const list = [
    { shapeId: "a", ring: "exterior", index: 0 },
    { shapeId: "a", ring: "exterior", index: 1 },
    { shapeId: "a", ring: "exterior", index: 2 },
    { shapeId: "a", ring: 0, index: 0 },
    { shapeId: "a", ring: 0, index: 1 },
    { shapeId: "b", ring: "exterior", index: 0 },
    { shapeId: "b", ring: "exterior", index: 1 },
  ];
  test("forward from nothing starts at the first point, backward at the last", () => {
    expect(stepNodeCursor(list, null, 1, false)).toEqual(list[0]);
    expect(stepNodeCursor(list, null, -1, false)).toEqual(list[6]);
  });
  test("steps cross rings and shapes in list order", () => {
    expect(stepNodeCursor(list, list[2], 1, true)).toEqual(list[3]);
    expect(stepNodeCursor(list, list[4], 1, true)).toEqual(list[5]);
    expect(stepNodeCursor(list, list[3], -1, true)).toEqual(list[2]);
  });
  test("past either end: [ and ] wrap, Tab returns null so focus can leave", () => {
    expect(stepNodeCursor(list, list[6], 1, true)).toEqual(list[0]);
    expect(stepNodeCursor(list, list[0], -1, true)).toEqual(list[6]);
    expect(stepNodeCursor(list, list[6], 1, false)).toBeNull();
    expect(stepNodeCursor(list, list[0], -1, false)).toBeNull();
  });
  test("an empty list or a stale cursor is safe", () => {
    expect(stepNodeCursor([], null, 1, true)).toBeNull();
    expect(stepNodeCursor(list, { shapeId: "gone", ring: "exterior", index: 9 }, 1, true)).toEqual(list[0]);
    expect(nodeCursorPhrase(list, { shapeId: "gone", ring: "exterior", index: 9 }, false)).toBeNull();
  });
  test("announces point N of M in its ring, ring K across rings, and selection", () => {
    expect(nodeCursorPhrase(list, list[0], false)).toBe("Point 1 of 3, ring 1, not selected");
    expect(nodeCursorPhrase(list, list[2], true)).toBe("Point 3 of 3, ring 1, selected");
    expect(nodeCursorPhrase(list, list[4], false)).toBe("Point 2 of 2, ring 2, not selected");
    expect(nodeCursorPhrase(list, list[5], true)).toBe("Point 1 of 2, ring 3, selected");
  });
  test("sameNode compares all three fields", () => {
    expect(sameNode(list[0], { ...list[0] })).toBe(true);
    expect(sameNode(list[0], list[1])).toBe(false);
    expect(sameNode(list[0], null)).toBe(false);
  });
  test("the mode bar hint names the keys", () => {
    expect(editModeBar({ reshape: true }).hint).toMatch(/Tab or \[ and \]/);
    expect(editModeBar({ reshape: true }).hint).toMatch(/Space/);
  });
});
