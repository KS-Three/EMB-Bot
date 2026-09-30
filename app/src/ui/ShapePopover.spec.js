// @vitest-environment jsdom
// ShapePopover renders a shapePopover.js model and emits what the field
// needs; the model's contents are shapePopover.spec.js's business. Uses the
// render-through-a-real-parent harness ShapePanel.spec.js established.
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { popoverModel } from "../lib/shapePopover.js";

let Harness;
beforeAll(async () => {
  globalThis.fetch = () => Promise.reject(new Error("no network in tests")); // ThreadPicker's catalog loader
  ({ default: Harness } = await import("./ShapePopover.testHarness.svelte"));
});

const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
const manualEl = { id: 4, type: "manual", shapes: [
  { id: "s1", points: square, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
] };
const digitizedEl = { id: 6, type: "digitized", params: { border: null },
  review: { brandId: "isacord", shapes: [{ id: "Sabc", threadNumber: "1301", areaMm2: 123.4, tier: "fill", rgb: [10, 20, 30] }] },
  shapeOverrides: {}, deletedShapeIds: [] };

function renderPop(model, extra = {}) {
  const events = [];
  // Under `props`: `anchor` is also a Svelte mount option, so a top-level
  // anchor/bounds makes testing-library throw UnknownSvelteOptionsError.
  const utils = render(Harness, { props: { model, onEvent: (kind, detail) => events.push({ kind, detail }), ...extra } });
  return { events, ...utils };
}

test("is a dialog named after the shape, and focus lands inside it", () => {
  const { getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  const dlg = getByRole("dialog", { name: "Shape 1 · Fill" });
  expect(dlg).toBeInTheDocument();
  expect(dlg.contains(document.activeElement)).toBe(true);
});

test("manual lane: Fill/Satin select, numeric angle, Edit points, Delete — each emits its key", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  const tier = getByRole("combobox", { name: "Stitch type" });
  expect(tier).toHaveValue("fill");
  await fireEvent.change(tier, { target: { value: "satin" } });
  const angle = getByRole("spinbutton", { name: "Fill angle" });
  await fireEvent.input(angle, { target: { value: "60" } });
  await fireEvent.click(getByRole("button", { name: "Edit points" }));
  await fireEvent.click(getByRole("button", { name: "Delete shape" }));
  expect(events).toEqual([
    { kind: "change", detail: { key: "stitchType", value: "satin" } },
    { kind: "change", detail: { key: "angle", value: "60" } },
    { kind: "action", detail: { key: "editPoints" } },
    { kind: "action", detail: { key: "delete" } },
  ]);
});

test("digitized lane: the Layers row's selects, in its words", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: digitizedEl, shapeId: "Sabc" }));
  expect(getByRole("dialog", { name: "Thread #1301 · 123 mm²" })).toBeInTheDocument();
  expect(getByRole("combobox", { name: "Stitch type" })).toHaveValue("auto");
  expect(getByRole("combobox", { name: "Fill angle" })).toHaveValue("auto");
  expect(getByRole("combobox", { name: "Underlay style" })).toHaveValue("auto");
  const border = getByRole("combobox", { name: "Border" });
  expect(border).toHaveValue("default");
  await fireEvent.change(border, { target: { value: "auto" } });
  expect(events).toEqual([{ kind: "change", detail: { key: "border", value: "auto" } }]);
});

test("Escape closes", async () => {
  const { events, getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }));
  await fireEvent.keyDown(getByRole("dialog"), { key: "Escape" });
  expect(events).toEqual([{ kind: "close", detail: null }]);
});

test("clamps inside its bounds", () => {
  const { getByRole } = renderPop(popoverModel({ element: manualEl, shapeId: "s1" }), {
    anchor: { x: 790, y: 590 }, bounds: { w: 800, h: 600 },
  });
  const dlg = getByRole("dialog");
  // jsdom has no layout, so the component's fallback size (POP_W/POP_H) is
  // what gets clamped; the assertion is that the anchor was NOT used raw.
  expect(parseFloat(dlg.style.left)).toBeLessThan(790);
  expect(parseFloat(dlg.style.top)).toBeLessThan(590);
});
