// @vitest-environment jsdom
//
// Component-level coverage for TraceImportPanel.svelte (PR 2/3 of the
// image-trace-to-manual-shapes feature) — the upload/preview/controls UI
// wired on top of PR 1's pure app/src/lib/manualTrace.js. Deliberately NOT
// covered here: real file-upload/image-decode (jsdom has no
// createImageBitmap/canvas decode path — see DigitizePanel.spec.js's own
// file-banner precedent for leaving that to Playwright, PR 3's job).
// Instead, every test below seeds the "already decoded an image" state
// directly via the component's own `workImage` prop (see
// TraceImportPanel.svelte's comment on it — a real, documented seam, not a
// backdoor) and drives the REAL traceShapesFromRGBA/rescaleTracedShapes
// against small synthetic RGBA fixtures, so the trace/preview/legend/
// warnings pipeline under test is the real one, not a stub.
//
// TraceImportPanel.svelte imports manualTrace.js, which (like
// manualTrace.spec.js's own fixtures) needs the real EMB engine loaded onto
// globalThis BEFORE that module is ever evaluated — so the Harness is
// imported dynamically, inside beforeAll, AFTER the engine require() calls
// below, rather than statically at the top of this file (a static import
// would evaluate — and throw inside emb.js's "engine not loaded" guard —
// before beforeAll ever runs).
import { beforeAll, describe, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { preloadAllFontsSync } from "../lib/testFonts.js";

let Harness;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "exp", "fonts", "digitize"]) require("../../../src/" + f + ".js");
  preloadAllFontsSync();

  // Same no-op 2D context stub ManualPanel.spec.js uses — jsdom has no real
  // HTMLCanvasElement#getContext("2d") without the native `canvas` package.
  // Nothing here asserts on actual pixels, only on component state (button
  // text/disabled, legend/warning text, dispatched events).
  const noop = () => {};
  HTMLCanvasElement.prototype.getContext = () => ({
    clearRect: noop, fillRect: noop, beginPath: noop, moveTo: noop, lineTo: noop,
    closePath: noop, fill: noop, stroke: noop,
    fillStyle: "", strokeStyle: "", lineWidth: 1,
  });

  ({ default: Harness } = await import("./TraceImportPanel.testHarness.svelte"));
});

// ---- Fixture helpers (same shape as manualTrace.spec.js's own) -----------

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
const WHITE = [255, 255, 255];
const RED = [200, 30, 30];
const BLUE = [30, 30, 200];

// A white background with a single red square. Verified (see this PR's own
// scratch check) to trace to exactly ONE shape with removeBg on (the
// default) and zero warnings; toggling removeBg OFF brings the background in
// as its own shape too (the red square becomes an interior hole of the now-
// untouched white ring), which is what surfaces the dropped-hole warning.
function oneShapeImage() {
  const w = 30, h = 30;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 30, 30, WHITE);
  fillRect(rgba, w, 8, 8, 20, 20, RED);
  return { rgba, w, h };
}

// Two distinct-colored squares on a white background — traces to exactly two
// shapes (one per color) at the component's own defaults (nColors=6,
// removeBg=true), used for the legend/swatch coverage.
function twoShapeImage() {
  const w = 20, h = 20;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 20, 20, WHITE);
  fillRect(rgba, w, 2, 2, 10, 18, RED);
  fillRect(rgba, w, 10, 2, 18, 18, BLUE);
  return { rgba, w, h };
}

function blankImage() {
  const w = 20, h = 20;
  const rgba = makeCanvas(w, h);
  fillRect(rgba, w, 0, 0, 20, 20, WHITE);
  return { rgba, w, h };
}

function renderPanel(props = {}) {
  const traced = [];
  const cancels = [];
  const utils = render(Harness, {
    props: { onTraced: (d) => traced.push(d), onCancel: () => cancels.push(true), ...props },
  });
  return { ...utils, traced, cancels };
}

function addButton(utils) {
  return utils.getByRole("button", { name: /^Add \d+ shapes?$/ });
}

// ---- initial state ---------------------------------------------------

describe("initial (no image yet) state", () => {
  test("renders with no preview canvas/legend and a disabled, zero-count Add button", () => {
    const utils = renderPanel();
    expect(utils.container.querySelector(".tip-preview")).toBeNull();
    expect(utils.container.querySelector(".tip-legend")).toBeNull();
    const btn = addButton(utils);
    expect(btn).toHaveTextContent("Add 0 shapes");
    expect(btn).toBeDisabled();
  });
});

// ---- colors / remove-background controls -------------------------------

describe("color count and remove-background controls", () => {
  test("render with the documented defaults once an image is decoded", () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    const slider = utils.container.querySelector('input[type="range"]');
    const checkbox = utils.container.querySelector('input[type="checkbox"]');
    expect(slider.value).toBe("6");
    expect(checkbox.checked).toBe(true);
    expect(utils.getByText("Colors: 6")).toBeTruthy();
  });

  test("moving the colors slider updates the displayed value (local state)", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    const slider = utils.container.querySelector('input[type="range"]');
    await fireEvent.input(slider, { target: { value: "3" } });
    expect(utils.getByText("Colors: 3")).toBeTruthy();
  });

  test("unchecking remove-background re-traces live against the cached pixels and updates the preview + warnings", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    expect(addButton(utils)).toHaveTextContent("Add 1 shape");
    expect(utils.container.querySelector(".tip-warnings")).toBeNull();

    const checkbox = utils.container.querySelector('input[type="checkbox"]');
    await fireEvent.click(checkbox); // uncheck remove-background

    expect(addButton(utils)).toHaveTextContent("Add 2 shapes");
    expect(utils.container.querySelector(".tip-warnings")).not.toBeNull();
    expect(utils.container.querySelector(".tip-warnings").textContent).toContain("interior hole");
  });
});

// ---- Add button ---------------------------------------------------------

describe("the Add button", () => {
  test("stays disabled while the decoded image traces to zero shapes", () => {
    const utils = renderPanel({ workImage: blankImage() });
    expect(addButton(utils)).toBeDisabled();
    expect(addButton(utils)).toHaveTextContent("Add 0 shapes");
  });

  test("enables once the trace produces shapes, and clicking it dispatches a traced event with the expected shape count/shape of data", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    const btn = addButton(utils);
    expect(btn).not.toBeDisabled();
    await fireEvent.click(btn);

    expect(utils.traced).toHaveLength(1);
    const { shapes } = utils.traced[0];
    expect(shapes).toHaveLength(1);
    const s = shapes[0];
    expect(s.id).toBe("s1"); // no existingShapes -> starts fresh
    expect(Array.isArray(s.points)).toBe(true);
    expect(s.points.length).toBeGreaterThanOrEqual(3);
    expect(s.colorRgb).toEqual(RED);
    expect(s.stitchType).toBe("fill");
    expect(s.angleDeg).toBeNull();
  });

  test("assigns ids that skip past ids already used by existingShapes, never colliding", async () => {
    // A naive "start counting from 1" implementation would hand back "s1"
    // here and silently collide with an id already in use.
    const existingShapes = [{ id: "s1" }, { id: "s2" }];
    const utils = renderPanel({ workImage: oneShapeImage(), existingShapes });
    await fireEvent.click(addButton(utils));
    expect(utils.traced).toHaveLength(1);
    expect(utils.traced[0].shapes.map((s) => s.id)).toEqual(["s3"]);
  });

  test("clicking Add resets local state back to the initial (no image) view", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    await fireEvent.click(addButton(utils));
    expect(utils.container.querySelector(".tip-preview")).toBeNull();
    expect(addButton(utils)).toHaveTextContent("Add 0 shapes");
  });
});

// ---- warnings -------------------------------------------------------------

describe("warnings", () => {
  test("renders the trace's warnings when the result includes any", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    const checkbox = utils.container.querySelector('input[type="checkbox"]');
    await fireEvent.click(checkbox); // removeBg off -> triggers the dropped-hole warning
    const list = utils.container.querySelector(".tip-warnings");
    expect(list).not.toBeNull();
    expect(list.querySelectorAll("li")).toHaveLength(1);
  });

  test("renders no warnings list when the trace result has none", () => {
    const utils = renderPanel({ workImage: oneShapeImage() }); // removeBg on by default -> no warnings
    expect(utils.container.querySelector(".tip-warnings")).toBeNull();
  });
});

// ---- legend ---------------------------------------------------------------

describe("the per-color legend", () => {
  test("shows one swatch entry per distinct traced color with its shape count", () => {
    const utils = renderPanel({ workImage: twoShapeImage() });
    const swatches = utils.container.querySelectorAll(".tip-swatch");
    expect(swatches).toHaveLength(2);
    expect(utils.container.querySelector(".tip-legend").textContent).toContain("1 shape");
    expect(addButton(utils)).toHaveTextContent("Add 2 shapes");
  });
});

// ---- Cancel ---------------------------------------------------------------

describe("Cancel", () => {
  test("resets local state to the initial view and dispatches a cancel event, without ever dispatching traced", async () => {
    const utils = renderPanel({ workImage: oneShapeImage() });
    await fireEvent.click(utils.getByRole("button", { name: "Cancel" }));

    expect(utils.cancels).toHaveLength(1);
    expect(utils.traced).toHaveLength(0);
    expect(utils.container.querySelector(".tip-preview")).toBeNull();
    expect(addButton(utils)).toHaveTextContent("Add 0 shapes");
  });
});
