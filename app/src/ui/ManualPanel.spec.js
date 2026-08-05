// @vitest-environment jsdom
//
// Component-level coverage for ManualPanel.svelte (Mode 2's manual-digitize
// canvas) — everything manualShapes.spec.js's pure-logic tests can't reach:
// the actual click/drag/keyboard wiring, button disabled-states, and the
// "an edit gets rejected the same way a draft does" UX this component adds
// on top of manualShapes.js.
//
// This is the first Svelte *component* spec in the repo (manualShapes.spec.js
// and its siblings are all pure-logic). @testing-library/svelte + jsdom
// were not previously dependencies — see package.json/vite.config.js for
// what got added and why (a `resolve.conditions: ["browser"]` override
// under Vitest only, so "svelte" resolves to its client build — the one
// with mount() — instead of the SSR build Vite's default node condition
// picks).
//
// Two environment gaps jsdom has no real implementation for, both stubbed
// in beforeAll below rather than pulled in as extra dependencies:
//   - HTMLCanvasElement#getContext("2d") returns null without the native
//     `canvas` package installed — stubbed to a no-op 2D context so
//     ManualPanel's render() (called reactively on every render) doesn't
//     throw. Nothing here asserts on actual pixels, only on component state
//     (button text/disabled, dispatched patches) — canvas content is out of
//     reach for this kind of test either way.
//   - getBoundingClientRect() returns an all-zero rect by default, which
//     would make canvasPointFromEvent's rect-based scale factor divide by
//     zero. Stubbed to CANVAS_W x CANVAS_H at (0,0) so a click's clientX/Y
//     maps 1:1 onto canvas coordinates — every coordinate used below can be
//     read directly as a canvas-space point.
import { beforeAll, describe, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
// toBeDisabled()/etc. — scoped to this file (not a global vitest setupFile)
// since it's the only spec that currently needs DOM matchers.
import "@testing-library/jest-dom/vitest";
import Harness from "./ManualPanel.testHarness.svelte";
import { CANVAS_W, CANVAS_H } from "../lib/manualShapes.js";

beforeAll(() => {
  const noop = () => {};
  HTMLCanvasElement.prototype.getContext = () => ({
    clearRect: noop, fillRect: noop, beginPath: noop, moveTo: noop, lineTo: noop,
    closePath: noop, fill: noop, stroke: noop, arc: noop, fillText: noop,
    save: noop, restore: noop,
    fillStyle: "", strokeStyle: "", lineWidth: 1, font: "", textAlign: "",
  });
  HTMLCanvasElement.prototype.getBoundingClientRect = () => ({
    left: 0, top: 0, right: CANVAS_W, bottom: CANVAS_H,
    width: CANVAS_W, height: CANVAS_H, x: 0, y: 0, toJSON() {},
  });
});

function baseElement(shapes = []) {
  return { id: "e1", type: "manual", shapes };
}

function tri(dx = 0, dy = 0) {
  return [
    { x: 100 + dx, y: 100 + dy },
    { x: 200 + dx, y: 100 + dy },
    { x: 150 + dx, y: 200 + dy },
  ];
}

function renderPanel(shapes = []) {
  const patches = [];
  const utils = render(Harness, {
    props: { element: baseElement(shapes), onPatch: (d) => patches.push(d) },
  });
  const canvas = utils.container.querySelector("canvas");
  return { ...utils, canvas, patches };
}

async function clickAt(canvas, x, y) {
  await fireEvent.click(canvas, { clientX: x, clientY: y });
}

// ---- click-sequence drawing --------------------------------------------

describe("drawing a shape via clicks", () => {
  test("three points + a click near the start closes a valid triangle", async () => {
    const { canvas, patches, getByText } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    await clickAt(canvas, p2.x, p2.y);
    // Within CLOSE_RADIUS_PX of p0 — closes the shape instead of adding a 4th point.
    await clickAt(canvas, p0.x + 2, p0.y);

    expect(patches).toHaveLength(1);
    expect(patches[0].id).toBe("e1");
    expect(patches[0].patch.shapes).toHaveLength(1);
    expect(patches[0].patch.shapes[0].points).toHaveLength(3);
    // finishShape() auto-selects the new shape, so its name now appears
    // twice (the shape-list row AND the assignment panel's heading) —
    // pin the query to the row specifically.
    expect(getByText(/Shape 1/, { selector: ".mp-shapename" })).toBeTruthy();
  });

  test("a genuine double-click finishes the draft without double-counting the repeated point", async () => {
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    // A double-click is two `click`s landing on the same spot, THEN one
    // `dblclick` — exactly ManualPanel's own comment on onCanvasDblClick.
    await clickAt(canvas, p2.x, p2.y);
    await clickAt(canvas, p2.x, p2.y); // the dup-consecutive click; dedupe should drop it
    await fireEvent.dblClick(canvas, { clientX: p2.x, clientY: p2.y });

    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes[0].points).toHaveLength(3); // not 4
  });

  test("a self-intersecting draft surfaces the rejection message and Finish stays disabled", async () => {
    const { canvas, container, getByRole } = renderPanel();
    // Same bowtie shape as manualShapes.spec.js's own BOWTIE fixture (the
    // two diagonals of a square, wired as edges instead of a normal
    // perimeter), scaled up ×10 so none of these clicks accidentally lands
    // within CLOSE_RADIUS_PX of the start point and triggers an early close.
    await clickAt(canvas, 0, 0);
    await clickAt(canvas, 100, 100);
    await clickAt(canvas, 100, 0);
    await clickAt(canvas, 0, 100);

    expect(container.querySelector(".mp-draftissue").textContent).toContain("This shape crosses itself.");
    expect(getByRole("button", { name: "Finish shape" })).toBeDisabled();
  });
});

// ---- Undo / Clear disabled-states --------------------------------------

describe("Undo point / Clear shape button states", () => {
  test("both start disabled with an empty draft, and enable once a point exists", async () => {
    const { canvas, getByRole } = renderPanel();
    const undoBtn = getByRole("button", { name: "Undo point" });
    const clearBtn = getByRole("button", { name: "Clear shape" });
    expect(undoBtn).toBeDisabled();
    expect(clearBtn).toBeDisabled();

    await clickAt(canvas, 100, 100);
    expect(undoBtn).not.toBeDisabled();
    expect(clearBtn).not.toBeDisabled();
  });

  test("Undo point removes the last point and re-disables once the draft is empty again", async () => {
    const { canvas, getByRole } = renderPanel();
    const undoBtn = getByRole("button", { name: "Undo point" });
    await clickAt(canvas, 100, 100);
    await fireEvent.click(undoBtn);
    expect(undoBtn).toBeDisabled();
  });

  test("Clear shape empties the draft in one step", async () => {
    const { canvas, getByRole } = renderPanel();
    const clearBtn = getByRole("button", { name: "Clear shape" });
    const [p0, p1] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    await fireEvent.click(clearBtn);
    expect(getByRole("button", { name: "Undo point" })).toBeDisabled();
  });
});

// ---- select / delete shape ----------------------------------------------

describe("selecting and deleting a finished shape", () => {
  test("clicking a shape row selects it (assignment panel + sel styling)", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { getByText } = renderPanel([shape]);
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    await fireEvent.click(row);
    expect(row.className).toContain("sel");
    expect(getByText("Fill angle")).toBeTruthy(); // mp-assign panel is now showing
  });

  test("the ✕ button deletes the shape and dispatches the shrunk shape list", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { getByRole, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByRole("button", { name: "Delete shape" }));
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toEqual([]);
    expect(getByText("No shapes yet — draw one above to get started.")).toBeTruthy();
  });
});

// ---- vertex-drag edit (task 1) -------------------------------------------

describe("editing a finished shape's points by dragging a vertex", () => {
  function withSelectedShape(points) {
    const shape = { id: "s1", points, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    return renderPanel([shape]);
  }

  async function selectAndEnterEdit(utils) {
    await fireEvent.click(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(utils.getByRole("button", { name: "Edit points" }));
  }

  test("dragging a vertex to a still-valid spot patches the shape's points on release", async () => {
    const utils = withSelectedShape(tri());
    await selectAndEnterEdit(utils);
    const { canvas, patches } = utils;

    // Vertex 0 sits at (100, 100) — drag it a little.
    await fireEvent.pointerDown(canvas, { clientX: 100, clientY: 100, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: 110, clientY: 90, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: 110, clientY: 90, pointerId: 1 });

    expect(patches).toHaveLength(1); // only the drag-release patch — nothing during the move
    const moved = patches[0].patch.shapes[0].points;
    expect(moved[0]).toEqual({ x: 110, y: 90 });
    expect(moved).toHaveLength(3);
  });

  test("a drag that would self-intersect the shape is never patched through, and the reason is shown", async () => {
    // A square, dragged so corner 0 crosses the opposite edge — see
    // manualShapes.spec.js's own BOWTIE fixture for the same "adjacent
    // edges don't count" shape of check this exercises end to end.
    const square = [
      { x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 },
    ];
    const utils = withSelectedShape(square);
    await selectAndEnterEdit(utils);
    const { canvas, patches, container } = utils;

    await fireEvent.pointerDown(canvas, { clientX: 0, clientY: 0, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: 150, clientY: 50, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: 150, clientY: 50, pointerId: 1 });

    expect(patches).toHaveLength(0); // rejected — never wrote back
    expect(container.querySelector(".mp-draftissue").textContent).toContain("This shape crosses itself.");
  });

  test("Edit points is disabled while a draft is in progress", async () => {
    const utils = withSelectedShape(tri());
    await fireEvent.click(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await clickAt(utils.canvas, 300, 300); // start an unrelated draft
    expect(utils.getByRole("button", { name: "Edit points" })).toBeDisabled();
  });

  test("Done editing exits edit mode without discarding the already-applied drag", async () => {
    const utils = withSelectedShape(tri());
    await selectAndEnterEdit(utils);
    await fireEvent.click(utils.getByRole("button", { name: "Done editing" }));
    expect(utils.getByRole("button", { name: "Edit points" })).toBeTruthy();
  });
});

// ---- keyboard shortcuts (task 2) -----------------------------------------

describe("keyboard shortcuts", () => {
  test("Escape cancels the current draft", async () => {
    const { canvas, getByRole } = renderPanel();
    await clickAt(canvas, 100, 100);
    await clickAt(canvas, 200, 100);
    await fireEvent.keyDown(canvas, { key: "Escape" });
    expect(getByRole("button", { name: "Undo point" })).toBeDisabled();
  });

  test("Enter finishes the draft once it's a valid (canFinish) shape", async () => {
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    await clickAt(canvas, p2.x, p2.y);
    await fireEvent.keyDown(canvas, { key: "Enter" });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toHaveLength(1);
  });

  test("Enter does nothing while the draft isn't finishable yet", async () => {
    const { canvas, patches } = renderPanel();
    await clickAt(canvas, 100, 100);
    await clickAt(canvas, 200, 100); // only 2 points — not sewable
    await fireEvent.keyDown(canvas, { key: "Enter" });
    expect(patches).toHaveLength(0);
  });

  test("Delete removes the selected finished shape when no draft is in progress", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.keyDown(canvas, { key: "Delete" });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toEqual([]);
  });

  test("Delete also fires from the shape row button itself (where selecting a row actually leaves focus)", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { getByText, patches } = renderPanel([shape]);
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    await fireEvent.click(row);
    await fireEvent.keyDown(row, { key: "Delete" });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toEqual([]);
  });

  test("Delete does NOT touch the selected shape while a draft is mid-progress", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button")); // select s1
    await clickAt(canvas, 300, 300); // start a different, unrelated draft
    await fireEvent.keyDown(canvas, { key: "Delete" });
    expect(patches).toHaveLength(0); // s1 must still be there
  });

  test("Backspace is equivalent to Delete for removing the selected shape", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.keyDown(canvas, { key: "Backspace" });
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toEqual([]);
  });

  test("Escape exits an active vertex edit instead of touching an (empty) draft", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, getByRole } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(getByRole("button", { name: "Edit points" }));
    await fireEvent.keyDown(canvas, { key: "Escape" });
    expect(getByRole("button", { name: "Edit points" })).toBeTruthy();
  });
});
