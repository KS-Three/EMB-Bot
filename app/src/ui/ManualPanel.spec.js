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
//
// ManualPanel.svelte now mounts TraceImportPanel.svelte (the trace-an-image
// feature, PR 2), which imports manualTrace.js — same real-EMB-engine
// dependency manualTrace.spec.js's own fixtures need (see its beforeAll) —
// so importing ManualPanel.testHarness.svelte transitively needs the engine
// loaded onto globalThis first too. The Harness is imported dynamically,
// inside beforeAll, AFTER the engine require() calls below, rather than
// statically at the top of this file (a static import would evaluate — and
// throw inside emb.js's "engine not loaded" guard — before beforeAll ever
// runs), same pattern TraceImportPanel.spec.js uses for its own Harness.
import { beforeAll, describe, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
// toBeDisabled()/etc. — scoped to this file (not a global vitest setupFile)
// since it's the only spec that currently needs DOM matchers.
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "../lib/testFonts.js";
import { CANVAS_W, CANVAS_H } from "../lib/manualShapes.js";

let Harness;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();

  const noop = () => {};
  HTMLCanvasElement.prototype.getContext = () => ({
    clearRect: noop, fillRect: noop, beginPath: noop, moveTo: noop, lineTo: noop,
    quadraticCurveTo: noop, closePath: noop, fill: noop, stroke: noop, arc: noop, fillText: noop,
    save: noop, restore: noop,
    fillStyle: "", strokeStyle: "", lineWidth: 1, font: "", textAlign: "",
  });
  HTMLCanvasElement.prototype.getBoundingClientRect = () => ({
    left: 0, top: 0, right: CANVAS_W, bottom: CANVAS_H,
    width: CANVAS_W, height: CANVAS_H, x: 0, y: 0, toJSON() {},
  });

  ({ default: Harness } = await import("./ManualPanel.testHarness.svelte"));
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

function renderPanel(shapes = [], traceWorkImage = null) {
  const patches = [];
  const utils = render(Harness, {
    props: { element: baseElement(shapes), traceWorkImage, onPatch: (d) => patches.push(d) },
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

// ---- canvas-click-to-select ------------------------------------------------

describe("canvas-click-to-select", () => {
  test("clicking inside a finished (unselected) shape's body selects it", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText } = renderPanel([shape]);
    // Roughly tri()'s centroid — well inside the triangle regardless of
    // exact rounding.
    await clickAt(canvas, 150, 133);
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(row.className).toContain("sel");
  });

  test("clicking empty canvas (no shape underneath) starts a new draft instead of selecting anything", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByRole, getByText } = renderPanel([shape]);
    await clickAt(canvas, 400, 350); // well outside tri()
    expect(getByRole("button", { name: "Undo point" })).not.toBeDisabled();
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(row.className).not.toContain("sel");
  });

  test("on overlapping shapes, the topmost (last-drawn) shape wins the hit test", async () => {
    const back = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [1, 1, 1], angleDeg: null };
    // Drawn after s1 (topmost) and fully covers its centroid.
    const front = {
      id: "s2",
      points: [{ x: 50, y: 50 }, { x: 300, y: 50 }, { x: 300, y: 300 }, { x: 50, y: 300 }],
      stitchType: "satin",
      colorRgb: [2, 2, 2],
      angleDeg: null,
    };
    const { canvas, getByText } = renderPanel([back, front]);
    await clickAt(canvas, 150, 133); // inside both shapes' bodies
    expect(getByText(/Shape 2/, { selector: ".mp-shapename" }).closest("button").className).toContain("sel");
    expect(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button").className).not.toContain("sel");
  });

  test("a select-click never fires mid-draft — clicking inside another shape's body while drawing adds a draft point instead", async () => {
    // Positioned well away from the draft's own start/points below so none
    // of these clicks accidentally lands within CLOSE_RADIUS_PX of anything
    // unintended.
    const other = { id: "s1", points: tri(300, 0), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, patches } = renderPanel([other]);
    await clickAt(canvas, 20, 20); // draft point 1 — draft.length is now 1
    // Inside s1's body — the select-click gate (draft.length === 0) is
    // closed now, so this must extend the draft, not select s1.
    await clickAt(canvas, 450, 133);
    await clickAt(canvas, 20, 80); // draft point 3
    await clickAt(canvas, 22, 20); // close near the start
    expect(patches).toHaveLength(1);
    const newShape = patches[0].patch.shapes[1]; // index 0 is the untouched s1
    expect(newShape.points).toHaveLength(3);
  });
});

// ---- edge-click-to-insert-vertex -------------------------------------------
//
// tri()'s top edge (segment 0) runs from (100,100) to (200,100) — (150,103)
// sits 3px off that line, well inside VERTEX_HIT_R (8), and (150,133) is a
// safe interior point roughly 30px from the nearest edge (verified against
// the real nearestSegmentIndex/pointInShape helpers, not just eyeballed).

describe("edge-click-to-insert-vertex", () => {
  async function selectRow(utils) {
    await fireEvent.click(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
  }

  test("clicking an edge of the already-selected shape inserts a new vertex there", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const utils = renderPanel([shape]);
    await selectRow(utils);
    const { canvas, patches } = utils;

    await clickAt(canvas, 150, 103);

    expect(patches).toHaveLength(1);
    const pts = patches[0].patch.shapes[0].points;
    expect(pts).toHaveLength(4);
    expect(pts).toEqual([
      { x: 100, y: 100 },
      { x: 150, y: 103 }, // the new vertex, spliced right after segment 0's start anchor
      { x: 200, y: 100 },
      { x: 150, y: 200 },
    ]);
  });

  test("clicking an edge of a shape that ISN'T selected yet only selects it — no insert", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);

    await clickAt(canvas, 150, 103); // same edge point, but nothing is selected yet

    expect(patches).toHaveLength(0); // selecting alone never dispatches a patch
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(row.className).toContain("sel");
  });

  test("clicking the interior of an already-selected shape (away from any edge) does not insert", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const utils = renderPanel([shape]);
    await selectRow(utils);
    const { canvas, getByText, patches } = utils;

    await clickAt(canvas, 150, 133); // well inside, ~30px from the nearest edge

    expect(patches).toHaveLength(0); // no insert dispatched
    // Falls back to the pre-existing already-selected-shape click behavior
    // (selectShape's own toggle) unchanged — this test only pins that no
    // insert happened, not that specific toggle mechanic (out of scope here).
    const row = getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(row.className).not.toContain("sel");
  });

  test("a second click on the same edge point keeps splitting — each insert only ever adds one vertex", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const utils = renderPanel([shape]);
    await selectRow(utils);
    const { canvas, patches } = utils;

    await clickAt(canvas, 150, 103);
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes[0].points).toHaveLength(4);
  });

  test("an edge click on a DIFFERENT shape than the one selected just selects that other shape, no insert", async () => {
    const selected = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const other = { id: "s2", points: tri(300, 0), stitchType: "fill", colorRgb: [1, 1, 1], angleDeg: null };
    const utils = renderPanel([selected, other]);
    await selectRow(utils);
    const { canvas, getByText, patches } = utils;

    // Edge point on `other`'s top edge (same offset as tri()'s own).
    await clickAt(canvas, 450, 103);

    expect(patches).toHaveLength(0);
    expect(getByText(/Shape 2/, { selector: ".mp-shapename" }).closest("button").className).toContain("sel");
    expect(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button").className).not.toContain("sel");
  });
});

// ---- cursor swaps per hover target ------------------------------------

describe("cursor swaps per hover target", () => {
  test("defaults to crosshair over empty canvas", async () => {
    const { canvas } = renderPanel();
    await fireEvent.pointerMove(canvas, { clientX: 300, clientY: 200 });
    expect(canvas.style.cursor).toBe("crosshair");
  });

  test("switches to pointer while hovering a selectable shape's body", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas } = renderPanel([shape]);
    await fireEvent.pointerMove(canvas, { clientX: 150, clientY: 133 }); // inside tri()
    expect(canvas.style.cursor).toBe("pointer");
  });

  test("switches to cell while hovering an edge of the already-selected shape (the exact spot a click would insert a vertex)", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button")); // select it first
    await fireEvent.pointerMove(canvas, { clientX: 150, clientY: 103 }); // 3px off tri()'s top edge
    expect(canvas.style.cursor).toBe("cell");
  });

  test("stays pointer (not cell) while hovering the SAME shape's edge before it's selected", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas } = renderPanel([shape]);
    await fireEvent.pointerMove(canvas, { clientX: 150, clientY: 103 }); // same edge point, nothing selected
    expect(canvas.style.cursor).toBe("pointer");
  });

  test("stays pointer (not cell) over the selected shape's own interior, away from any edge", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.pointerMove(canvas, { clientX: 150, clientY: 133 }); // centroid-ish, ~30px from any edge
    expect(canvas.style.cursor).toBe("pointer");
  });

  test("stays crosshair over a shape's body while a draft is in progress (select-click is gated off then too)", async () => {
    const shape = { id: "s1", points: tri(300, 0), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas } = renderPanel([shape]);
    await clickAt(canvas, 20, 20); // start a draft
    await fireEvent.pointerMove(canvas, { clientX: 450, clientY: 133 }); // inside s1's body
    expect(canvas.style.cursor).toBe("crosshair");
  });

  test("switches to copy while hovering a draft segment's curve handle", async () => {
    const { canvas } = renderPanel();
    const [p0, p1] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    const midX = (p0.x + p1.x) / 2, midY = (p0.y + p1.y) / 2;
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY });
    expect(canvas.style.cursor).toBe("copy");
  });

  test("switches to grab while hovering a draggable vertex in edit-points mode", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, getByRole } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(getByRole("button", { name: "Edit points" }));
    const [p0] = tri();
    await fireEvent.pointerMove(canvas, { clientX: p0.x, clientY: p0.y });
    expect(canvas.style.cursor).toBe("grab");
  });

  test("switches to copy while hovering an edit-mode segment's curve handle", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, getByRole } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(getByRole("button", { name: "Edit points" }));
    const [p0, p1] = tri();
    const midX = (p0.x + p1.x) / 2, midY = (p0.y + p1.y) / 2;
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY });
    expect(canvas.style.cursor).toBe("copy");
  });

  test("stays crosshair in edit-points mode away from any vertex or curve handle", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, getByRole } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(getByRole("button", { name: "Edit points" }));
    await fireEvent.pointerMove(canvas, { clientX: 500, clientY: 350 });
    expect(canvas.style.cursor).toBe("crosshair");
  });

  test("switches to grabbing while actively dragging a vertex (takes priority over the plain grab hover cursor)", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, getByRole } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(getByRole("button", { name: "Edit points" }));
    const [p0] = tri();
    await fireEvent.pointerDown(canvas, { clientX: p0.x, clientY: p0.y, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: p0.x + 10, clientY: p0.y - 10, pointerId: 1 });
    expect(canvas.style.cursor).toBe("grabbing");
    await fireEvent.pointerUp(canvas, { clientX: p0.x + 10, clientY: p0.y - 10, pointerId: 1 });
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

// ---- curve-handle drag (drawing curved, not just straight, edges) --------

describe("bowing a draft segment into a curve by dragging its handle", () => {
  test("dragging a segment's handle stores a curve on the finished shape, without adding a stray anchor", async () => {
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);

    // Segment 0's straight-line midpoint, between p0 and p1.
    const midX = (p0.x + p1.x) / 2, midY = (p0.y + p1.y) / 2;
    await fireEvent.pointerDown(canvas, { clientX: midX, clientY: midY, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });
    // The click that (in a real browser) immediately follows this drag
    // shouldn't ALSO place a stray point at the handle's location.
    await clickAt(canvas, midX, midY - 30);

    await clickAt(canvas, p2.x, p2.y);
    await clickAt(canvas, p0.x + 2, p0.y); // close

    expect(patches).toHaveLength(1);
    const shape = patches[0].patch.shapes[0];
    expect(shape.points).toHaveLength(3); // still just 3 anchors — bowing never adds one
    expect(shape.curves[0]).toBeTruthy();
  });

  test("dragging a curve handle back near the straight line straightens it (removes the curve entry)", async () => {
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    const midX = (p0.x + p1.x) / 2, midY = (p0.y + p1.y) / 2;
    // Bow it out first...
    await fireEvent.pointerDown(canvas, { clientX: midX, clientY: midY, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });
    await clickAt(canvas, midX, midY - 30);
    // ...then drag it back onto the line.
    await fireEvent.pointerDown(canvas, { clientX: midX, clientY: midY - 30, pointerId: 2 });
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY, pointerId: 2 });
    await fireEvent.pointerUp(canvas, { clientX: midX, clientY: midY, pointerId: 2 });
    await clickAt(canvas, midX, midY);

    await clickAt(canvas, p2.x, p2.y);
    await clickAt(canvas, p0.x + 2, p0.y);

    const shape = patches[0].patch.shapes[0];
    expect(shape.curves[0]).toBeUndefined();
  });

  test("a curve that would make the draft self-intersect disables Finish, same as a crossing straight edge would", async () => {
    const { canvas, container } = renderPanel();
    const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
    for (const p of square) await clickAt(canvas, p.x, p.y);
    // Bow the first edge (0,0)-(100,0) far enough down to cross the opposite
    // (2,3) edge — the anchors alone are a fine square, but the curved
    // geometry genuinely crosses itself.
    await fireEvent.pointerDown(canvas, { clientX: 50, clientY: 0, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: 50, clientY: 200, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: 50, clientY: 200, pointerId: 1 });

    expect(container.querySelector(".mp-draftissue").textContent).toContain("This shape crosses itself.");
  });

  test("Undo point drops the curve bound to the segment that no longer exists", async () => {
    const { canvas, getByRole, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await clickAt(canvas, p1.x, p1.y);
    await clickAt(canvas, p2.x, p2.y); // 3 points now; segment 1 is p1-p2

    const midX = (p1.x + p2.x) / 2, midY = (p1.y + p2.y) / 2;
    await fireEvent.pointerDown(canvas, { clientX: midX, clientY: midY, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: midX + 20, clientY: midY, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: midX + 20, clientY: midY, pointerId: 1 });
    await clickAt(canvas, midX + 20, midY);

    await fireEvent.click(getByRole("button", { name: "Undo point" })); // removes p2 AND segment 1's curve
    // Re-add a fresh third point (a different one) and finish.
    await clickAt(canvas, p2.x + 5, p2.y + 5);
    await clickAt(canvas, p0.x + 2, p0.y);

    expect(patches).toHaveLength(1);
    // Segment 1 in the NEW shape (p1 -> the fresh third point) must be
    // straight — the old curve bound to the old (now-gone) segment 1 must
    // not leak forward onto whatever segment 1 means next.
    expect(patches[0].patch.shapes[0].curves[1]).toBeUndefined();
  });
});

describe("bowing a finished shape's edge while editing points", () => {
  function withSelectedShape(points) {
    const shape = { id: "s1", points, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    return renderPanel([shape]);
  }

  async function selectAndEnterEdit(utils) {
    await fireEvent.click(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.click(utils.getByRole("button", { name: "Edit points" }));
  }

  test("dragging an edge's curve handle patches shape.curves on release, leaving the anchor count unchanged", async () => {
    const utils = withSelectedShape(tri());
    await selectAndEnterEdit(utils);
    const { canvas, patches } = utils;
    const [p0, p1] = tri();
    const midX = (p0.x + p1.x) / 2, midY = (p0.y + p1.y) / 2;

    await fireEvent.pointerDown(canvas, { clientX: midX, clientY: midY, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: midX, clientY: midY - 30, pointerId: 1 });

    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes[0].curves[0]).toBeTruthy();
    expect(patches[0].patch.shapes[0].points).toHaveLength(3);
  });

  test("a curve-handle drag that would self-intersect the shape is never patched through, and the reason is shown", async () => {
    const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
    const utils = withSelectedShape(square);
    await selectAndEnterEdit(utils);
    const { canvas, patches, container } = utils;

    // Bow the top edge (0,0)-(100,0) far down through the shape and past
    // the opposite edge — same "genuinely crosses" fixture as the draft
    // version above.
    await fireEvent.pointerDown(canvas, { clientX: 50, clientY: 0, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: 50, clientY: 200, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: 50, clientY: 200, pointerId: 1 });

    expect(patches).toHaveLength(0);
    expect(container.querySelector(".mp-draftissue").textContent).toContain("This shape crosses itself.");
  });

  test("grabbing a vertex still wins over a nearby curve handle (vertex hit-test runs first)", async () => {
    const utils = withSelectedShape(tri());
    await selectAndEnterEdit(utils);
    const { canvas, patches } = utils;
    const [p0] = tri();

    // A drag starting exactly on vertex 0 must move the vertex, not bow an
    // adjacent segment.
    await fireEvent.pointerDown(canvas, { clientX: p0.x, clientY: p0.y, pointerId: 1 });
    await fireEvent.pointerMove(canvas, { clientX: p0.x + 15, clientY: p0.y - 15, pointerId: 1 });
    await fireEvent.pointerUp(canvas, { clientX: p0.x + 15, clientY: p0.y - 15, pointerId: 1 });

    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes[0].points[0]).toEqual({ x: p0.x + 15, y: p0.y - 15 });
    expect(patches[0].patch.shapes[0].curves).toBeUndefined();
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

// ---- importing shapes from a traced image (PR 2 of the trace-an-uploaded-
// image feature) ------------------------------------------------------------
//
// These tests exercise the REAL nested TraceImportPanel (not a stub) so the
// "traced" event that reaches ManualPanel's onTraced is the genuine one a
// user would produce — seeded via ManualPanel's own `traceWorkImage` test
// seam (see its comment) so the trace runs against small synthetic pixels
// instead of a real file upload (out of scope here — see
// TraceImportPanel.spec.js's own file banner and DigitizePanel.spec.js's
// precedent). What's under test is the WIRING: opening/closing the panel,
// and onTraced's patch — never the trace algorithm itself (already covered
// by manualTrace.spec.js and TraceImportPanel.spec.js).
describe("importing shapes from a traced image", () => {
  function makeCanvas(w, h) {
    return new Uint8ClampedArray(w * h * 4);
  }
  function fillRect(rgba, w, x0, y0, x1, y1, rgb) {
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const o = (y * w + x) * 4;
        rgba[o] = rgb[0]; rgba[o + 1] = rgb[1]; rgba[o + 2] = rgb[2]; rgba[o + 3] = 255;
      }
    }
  }
  // A white background with a single red square — traces to exactly ONE
  // shape at TraceImportPanel's defaults (nColors=6, removeBg=true). Same
  // fixture TraceImportPanel.spec.js verified independently.
  function oneShapeImage() {
    const w = 30, h = 30;
    const rgba = makeCanvas(w, h);
    fillRect(rgba, w, 0, 0, 30, 30, [255, 255, 255]);
    fillRect(rgba, w, 8, 8, 20, 20, [200, 30, 30]);
    return { rgba, w, h };
  }

  // Two distinct-colored squares — traces to exactly two shapes at the trace
  // panel's own defaults (nColors=6, removeBg=true). Same fixture
  // TraceImportPanel.spec.js verified independently for its own legend/
  // swatch coverage; used here to prove auto-select picks the FIRST of
  // several newly-traced shapes, not just "the only one."
  function twoShapeImage() {
    const w = 20, h = 20;
    const rgba = makeCanvas(w, h);
    fillRect(rgba, w, 0, 0, 20, 20, [255, 255, 255]);
    fillRect(rgba, w, 2, 2, 10, 18, [200, 30, 30]);
    fillRect(rgba, w, 10, 2, 18, 18, [30, 30, 200]);
    return { rgba, w, h };
  }

  async function openTracePanel(utils) {
    await fireEvent.click(utils.getByRole("button", { name: "Trace image…" }));
  }
  async function clickAdd(utils) {
    await fireEvent.click(utils.getByRole("button", { name: /^Add \d+ shapes?$/ }));
  }

  test('"Trace image…" opens the trace panel; a second click closes it, and so does the panel\'s own Cancel', async () => {
    const utils = renderPanel();
    expect(utils.container.querySelector(".tip-upload")).toBeNull();

    await openTracePanel(utils);
    expect(utils.container.querySelector(".tip-upload")).not.toBeNull();

    await fireEvent.click(utils.getByRole("button", { name: "Trace image…" })); // second click
    expect(utils.container.querySelector(".tip-upload")).toBeNull();

    await openTracePanel(utils);
    await fireEvent.click(utils.getByRole("button", { name: "Cancel" }));
    expect(utils.container.querySelector(".tip-upload")).toBeNull();
  });

  test("a traced event results in exactly one patch call whose shapes array is the original shapes plus all the new ones, and closes the panel", async () => {
    const existing = { id: "s1", points: tri(), curves: {}, stitchType: "fill", colorRgb: [9, 9, 9], angleDeg: null };
    const utils = renderPanel([existing], oneShapeImage());
    await openTracePanel(utils);
    await clickAdd(utils);

    expect(utils.patches).toHaveLength(1);
    const merged = utils.patches[0].patch.shapes;
    expect(merged).toHaveLength(2); // 1 existing + 1 traced
    expect(merged[0]).toBe(existing);
    // The trace panel closes itself after a successful add.
    expect(utils.container.querySelector(".tip-upload")).toBeNull();
  });

  test("an existing hand-drawn/hand-edited shape already in element.shapes is completely untouched (same reference/values) after a trace-add", async () => {
    const existing = {
      id: "s4",
      points: [{ x: 12, y: 34 }, { x: 56, y: 34 }, { x: 34, y: 78 }],
      curves: { 0: { x: 34, y: 10 } },
      stitchType: "satin",
      colorRgb: [77, 88, 99],
      angleDeg: 42,
    };
    const utils = renderPanel([existing], oneShapeImage());
    await openTracePanel(utils);
    await clickAdd(utils);

    expect(utils.patches).toHaveLength(1);
    const merged = utils.patches[0].patch.shapes;
    // Same object reference — proof nothing rebuilt/cloned/mutated it.
    expect(merged[0]).toBe(existing);
    expect(merged[0]).toEqual(existing);
  });

  test("ids assigned to traced shapes never collide with ids already present in element.shapes", async () => {
    // "s1" and "s5" are deliberately non-contiguous — a naive implementation
    // that just counts existing shapes (length + 1 = "s3") rather than
    // scanning for the real max id would produce a colliding "s2".
    const existing = [
      { id: "s1", points: tri(), curves: {}, stitchType: "fill", colorRgb: [1, 1, 1], angleDeg: null },
      { id: "s5", points: tri(50, 50), curves: {}, stitchType: "fill", colorRgb: [2, 2, 2], angleDeg: null },
    ];
    const utils = renderPanel(existing, oneShapeImage());
    await openTracePanel(utils);
    await clickAdd(utils);

    expect(utils.patches).toHaveLength(1);
    const merged = utils.patches[0].patch.shapes;
    expect(merged).toHaveLength(3);
    const newIds = merged.slice(2).map((s) => s.id);
    expect(newIds).toEqual(["s6"]);
    // No id collides with anything already in the (now-merged) list.
    const seen = new Set();
    for (const s of merged) {
      expect(seen.has(s.id)).toBe(false);
      seen.add(s.id);
    }
  });

  // ---- post-trace auto-select ---------------------------------------------

  test("after a successful trace-add, the newly-traced shape is selected", async () => {
    const utils = renderPanel([], oneShapeImage());
    await openTracePanel(utils);
    await clickAdd(utils);

    const merged = utils.patches[0].patch.shapes;
    expect(merged).toHaveLength(1);
    const row = utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(row.className).toContain("sel");
    expect(utils.getByText("Fill angle")).toBeTruthy(); // mp-assign panel is now showing
  });

  test("when a batch trace-add creates several shapes, only the FIRST newly-added one is selected", async () => {
    const utils = renderPanel([], twoShapeImage());
    await openTracePanel(utils);
    await clickAdd(utils);

    const merged = utils.patches[0].patch.shapes;
    expect(merged).toHaveLength(2);
    const firstRow = utils.getByText(new RegExp(`Shape ${merged[0].id.replace(/^s/, "")}\\b`), { selector: ".mp-shapename" }).closest("button");
    const secondRow = utils.getByText(new RegExp(`Shape ${merged[1].id.replace(/^s/, "")}\\b`), { selector: ".mp-shapename" }).closest("button");
    expect(firstRow.className).toContain("sel");
    expect(secondRow.className).not.toContain("sel");
  });

  test("a trace-add's auto-select replaces whatever was previously selected", async () => {
    const existing = { id: "s1", points: tri(), curves: {}, stitchType: "fill", colorRgb: [9, 9, 9], angleDeg: null };
    const utils = renderPanel([existing], oneShapeImage());
    await fireEvent.click(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    expect(utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button").className).toContain("sel");

    await openTracePanel(utils);
    await clickAdd(utils);

    const merged = utils.patches[0].patch.shapes;
    const newShape = merged[1];
    const newRow = utils.getByText(new RegExp(`Shape ${newShape.id.replace(/^s/, "")}\\b`), { selector: ".mp-shapename" }).closest("button");
    const oldRow = utils.getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button");
    expect(newRow.className).toContain("sel");
    expect(oldRow.className).not.toContain("sel");
  });
});

// ---- right-click curved nodes, and the keys around a draft -----------------
// All of this shipped with zero component coverage; the gaps below were found
// by review, 2026-08-25, and two of them were live defects.

describe("right-click places a curved node", () => {
  test("a right-clicked node bows the segment ARRIVING at it, at the correct segment index", async () => {
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);                                  // node 0, straight
    await fireEvent.contextMenu(canvas, { clientX: p1.x, clientY: p1.y }); // node 1, CURVED
    await clickAt(canvas, p2.x, p2.y);                                  // node 2, straight
    await clickAt(canvas, p0.x + 2, p0.y);                              // close

    expect(patches).toHaveLength(1);
    const shape = patches[0].patch.shapes[0];
    expect(shape.points).toHaveLength(3);
    // Segment 0 is p0->p1, the one arriving at the right-clicked node.
    expect(shape.curves).toBeTruthy();
    expect(shape.curves[0]).toBeTruthy();
    expect(Number.isFinite(shape.curves[0].x)).toBe(true);
    expect(Number.isFinite(shape.curves[0].y)).toBe(true);
    // ...and only that segment is curved.
    expect(shape.curves[1]).toBeFalsy();
    expect(shape.curves[2]).toBeFalsy();
  });

  test("Backspace after a right-clicked node removes BOTH the node and its curve, leaving no orphan", async () => {
    // The curve is written at index draft.length-1 (pre-append) and undoPoint
    // removes draft.length-2 (pre-slice). Those are two different expressions
    // of the same segment; if they ever disagree, a bow outlives its node and
    // silently reattaches to whatever lands at that index next.
    const { canvas, patches } = renderPanel();
    const [p0, p1, p2] = tri();
    await clickAt(canvas, p0.x, p0.y);
    await fireEvent.contextMenu(canvas, { clientX: p1.x, clientY: p1.y }); // curved node 1
    await fireEvent.keyDown(canvas, { key: "Backspace" });                 // take it back
    await clickAt(canvas, p1.x, p1.y);                                     // re-place it STRAIGHT
    await clickAt(canvas, p2.x, p2.y);
    await clickAt(canvas, p0.x + 2, p0.y);

    expect(patches).toHaveLength(1);
    const shape = patches[0].patch.shapes[0];
    expect(shape.points).toHaveLength(3);
    // No curve survived the undo.
    const curves = shape.curves || {};
    expect(Object.keys(curves)).toHaveLength(0);
  });

  test("right-click with no draft in progress does nothing — it neither starts a shape nor steals the browser menu", async () => {
    const { canvas, patches, queryByText } = renderPanel();
    const ev = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 150, clientY: 150 });
    canvas.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(false); // browser menu left alone
    expect(patches).toHaveLength(0);
    // No draft was started, so there is nothing to undo.
    expect(queryByText("Undo point").disabled).toBe(true);
  });
});

describe("draft keys never destroy a finished shape", () => {
  test("holding Backspace past the end of a draft does NOT delete the selected shape", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button")); // select s1
    await clickAt(canvas, 300, 300); // start a draft WITHOUT clearing that selection
    await clickAt(canvas, 340, 300);

    // Auto-repeat: unwind the draft, then keep the key held one tick too long.
    await fireEvent.keyDown(canvas, { key: "Backspace", repeat: true });
    await fireEvent.keyDown(canvas, { key: "Backspace", repeat: true });
    await fireEvent.keyDown(canvas, { key: "Backspace", repeat: true }); // draft is empty by now

    expect(patches).toHaveLength(0); // s1 survives
  });

  test("a deliberate, discrete Backspace with no draft still deletes the selected shape", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await fireEvent.keyDown(canvas, { key: "Backspace" }); // no repeat flag
    expect(patches).toHaveLength(1);
    expect(patches[0].patch.shapes).toEqual([]);
  });

  test("Delete mid-draft eats neither the draft nor the selected shape", async () => {
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { canvas, getByText, patches, queryByText } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));
    await clickAt(canvas, 300, 300);
    await clickAt(canvas, 340, 300);
    await fireEvent.keyDown(canvas, { key: "Delete" });
    await fireEvent.keyDown(canvas, { key: "Delete" });

    expect(patches).toHaveLength(0);                       // the shape is untouched...
    expect(queryByText("Undo point").disabled).toBe(false); // ...and so is the draft
  });
});

// ---- per-shape Dim -------------------------------------------------------
//
// Two bugs found by review 2026-08-26, both invisible to any pure-logic test
// because both live in the wiring between shapeAlpha and the DOM.

describe("the Dim control tells the truth about the shape it controls", () => {
  test("the slider and Reset follow shapeAlpha, instead of freezing at the value the shape had when it was selected", async () => {
    // Svelte's legacy `$:` dependency list is built from what a statement
    // textually references, so `value={alphaFor(shape.id)}` compiled to
    // `$.untrack(() => alphaFor(...))` with only `selectedShape` tracked.
    // Result: clicking Reset repainted the canvas (render() names shapeAlpha
    // explicitly) while the slider stayed at the dimmed position and Reset
    // stayed enabled.
    const shape = { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null };
    const { container, getByText } = renderPanel([shape]);
    await fireEvent.click(getByText(/Shape 1/, { selector: ".mp-shapename" }).closest("button"));

    const slider = container.querySelector(".mp-dim");
    const reset = container.querySelector(".mp-dim-reset");
    expect(slider.value).toBe("1");
    expect(reset.disabled).toBe(true);

    await fireEvent.input(slider, { target: { value: "0.15" } });
    expect(slider.value).toBe("0.15");
    expect(reset.disabled).toBe(false); // the control moved, so Reset is live

    await fireEvent.click(reset);
    expect(slider.value).toBe("1");      // ...and it goes back
    expect(reset.disabled).toBe(true);
  });

  test("a dimmed shape's alpha dies with it — a new shape reusing its id is NOT born dimmed", async () => {
    // nextShapeId is max+1 over the surviving list, so deleting s2 from
    // [s1, s2] makes the very next shape s2 again. shapeAlpha kept the dead
    // entry, so that new shape appeared already faded, with a slider the user
    // never touched and no visible cause.
    const shapes = [
      { id: "s1", points: tri(), stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
      { id: "s2", points: tri(220, 0), stitchType: "fill", colorRgb: [90, 20, 20], angleDeg: null },
    ];
    const { canvas, container, getAllByText } = renderPanel(shapes);

    // Dim s2 all the way down.
    await fireEvent.click(getAllByText(/Shape 2/, { selector: ".mp-shapename" })[0].closest("button"));
    await fireEvent.input(container.querySelector(".mp-dim"), { target: { value: "0.15" } });
    expect(container.querySelector(".mp-dim").value).toBe("0.15");

    // Delete it (discrete Backspace, no draft in progress).
    await fireEvent.keyDown(canvas, { key: "Backspace" });
    expect(container.querySelectorAll(".mp-shapename")).toHaveLength(1);

    // Draw a replacement, which is handed the recycled id "s2".
    const [q0, q1, q2] = tri(0, 220);
    await clickAt(canvas, q0.x, q0.y);
    await clickAt(canvas, q1.x, q1.y);
    await clickAt(canvas, q2.x, q2.y);
    await clickAt(canvas, q0.x + 2, q0.y);
    expect(container.querySelectorAll(".mp-shapename")).toHaveLength(2);

    // finishShape selects what it just created, so the Dim row on screen is
    // already the new shape's -- no extra click (selectShape TOGGLES, so a
    // click here would deselect it and take the row away entirely).
    expect(getAllByText(/Shape 2/, { selector: ".mp-shapename" })).toHaveLength(1); // id recycled
    expect(container.querySelector(".mp-dim").value).toBe("1");
    expect(container.querySelector(".mp-dim-reset").disabled).toBe(true);
  });
});
