// @vitest-environment jsdom
//
// Component-level coverage for ShapePanel.svelte (the preset basic-shapes
// editor): kind picking resets params to the new kind's defaults, per-kind
// param inputs dispatch the right { id, patch } shapes, and a sparse params
// bag still renders real default values. Pure geometry lives in
// shapePresets.spec.js; end-to-end digitizing in generate.spec.js — this
// file only covers the wiring in between.
//
// Uses the same render-through-a-real-parent harness pattern
// ManualPanel.spec.js established (Svelte 5's mounted-instance `$on` gap —
// see ShapePanel.testHarness.svelte).
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { defaultShapeElement } from "../lib/project.js";

let Harness;
beforeAll(async () => {
  // ThreadPicker's brand-catalog loader fetches on demand; jsdom has no
  // network and nothing here asserts on the picker — same silencing stub
  // TextStep.spec.js uses.
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./ShapePanel.testHarness.svelte"));
});

function renderPanel(overrides = {}) {
  const patches = [];
  const element = { ...defaultShapeElement("e1"), ...overrides };
  const utils = render(Harness, { element, onPatch: (d) => patches.push(d) });
  return { patches, ...utils };
}

test("renders all four shape kinds with the element's kind active", () => {
  const { getByRole } = renderPanel();
  for (const label of ["Circle", "Rectangle", "Heart", "Star"]) {
    expect(getByRole("button", { name: label })).toBeInTheDocument();
  }
  expect(getByRole("button", { name: "Circle" })).toHaveClass("active");
  expect(getByRole("button", { name: "Star" })).not.toHaveClass("active");
});

test("picking a new kind dispatches { kind, params: that kind's defaults }", async () => {
  const { patches, getByRole } = renderPanel();
  await fireEvent.click(getByRole("button", { name: "Star" }));
  expect(patches).toHaveLength(1);
  expect(patches[0]).toEqual({
    id: "e1",
    patch: { kind: "star", params: { points: 5, innerRatio: 0.45 } },
  });
});

test("re-picking the current kind is a no-op (params are not reset under the user)", async () => {
  const { patches, getByRole } = renderPanel({ kind: "star", params: { points: 7, innerRatio: 0.3 } });
  await fireEvent.click(getByRole("button", { name: "Star" }));
  expect(patches).toHaveLength(0);
});

test("star: points and inner-radius controls patch the params bag", async () => {
  const { patches, getByLabelText } = renderPanel({ kind: "star", params: { points: 5, innerRatio: 0.45 } });
  const pointsInput = getByLabelText("Star points");
  await fireEvent.change(pointsInput, { target: { value: "7" } });
  expect(patches[0]).toEqual({ id: "e1", patch: { params: { points: 7, innerRatio: 0.45 } } });

  const slider = getByLabelText(/Inner radius/);
  await fireEvent.input(slider, { target: { value: "30" } });
  expect(patches[1]).toEqual({ id: "e1", patch: { params: { points: 7, innerRatio: 0.3 } } });
});

test("rect: height and corner-radius inputs patch the params bag", async () => {
  const { patches, getByLabelText } = renderPanel({ kind: "rect", params: { heightMm: 30, cornerRadiusMm: 0 } });
  await fireEvent.change(getByLabelText(/Height/), { target: { value: "22" } });
  expect(patches[0]).toEqual({ id: "e1", patch: { params: { heightMm: 22, cornerRadiusMm: 0 } } });
  await fireEvent.change(getByLabelText(/Corner radius/), { target: { value: "6" } });
  expect(patches[1]).toEqual({ id: "e1", patch: { params: { heightMm: 22, cornerRadiusMm: 6 } } });
});

test("a sparse params bag renders the kind's defaults, never blank inputs", () => {
  const { getByLabelText } = renderPanel({ kind: "star", params: {} });
  expect(getByLabelText("Star points")).toHaveValue(5);
  expect(getByLabelText(/Inner radius/)).toHaveValue("45");
});

test("circle and heart show no extra param inputs (size lives in the Size panel)", () => {
  const { queryByLabelText } = renderPanel({ kind: "heart", params: {} });
  expect(queryByLabelText("Star points")).toBeNull();
  expect(queryByLabelText(/Height/)).toBeNull();
});
