// @vitest-environment jsdom
//
// Component-level coverage for GarmentStep's hoop picker (launch item 2):
// the four home-machine presets render, the per-garment suggestion is both
// tagged and selected by default (project.hoopId null), a manual pick
// dispatches an "update" with the hoopId and moves the selection while the
// "Suggested" tag stays put, and the reset link hands control back to the
// suggestion (hoopId null).
//
// Same render-through-a-real-parent-component harness pattern
// TextStep.spec.js established (Svelte 5's mounted-instance `$on` gap —
// see GarmentStep.testHarness.svelte).
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

// GarmentStep imports "../lib/emb.js" (via lib/hoop.js and directly) at
// module load time, and emb.js throws unless the engine global already
// exists — so the REAL units/garments engine modules load first (the picker
// tests assert on the real suggestion rule, not a stub's), the
// buildLetteringDesign gate gets a stub (TemplateRow only calls it inside
// its own try/catch preview path), and the harness is imported dynamically
// after. Same "stub before importing" ordering TextStep.spec.js documents.
let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  // TemplateRow kicks off font-manifest fetches for its previews; jsdom has
  // no network and TemplateRow's own catch handles the rejection — this
  // just keeps the run quiet.
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./GarmentStep.testHarness.svelte"));
});

function baseProject(patch = {}) {
  return {
    version: 2,
    garmentId: "left_chest",
    selectedId: "e1",
    selectedIds: ["e1"],
    elements: [{ id: "e1", type: "text", text: "" }],
    fabricRgb: [235, 232, 223],
    hoopId: null,
    ...patch,
  };
}

function renderStep(patch = {}) {
  const updates = [];
  const utils = render(Harness, {
    props: { project: baseProject(patch), onUpdate: (d) => updates.push(d) },
  });
  return { ...utils, updates };
}

function hoopButton(container, label) {
  const name = [...container.querySelectorAll(".hooptile .hooptile-name")].find(
    (el) => el.textContent === label
  );
  return name && name.closest("button");
}

test("renders the four hoop presets with their mm fields", () => {
  const { container, getByText } = renderStep();
  const tiles = container.querySelectorAll(".hooptile");
  expect(tiles).toHaveLength(4);
  for (const label of ["4×4 in", "5×7 in", "6×10 in", "8×8 in"]) {
    expect(hoopButton(container, label)).toBeInTheDocument();
  }
  expect(getByText("100 × 100 mm")).toBeInTheDocument();
  expect(getByText("160 × 250 mm")).toBeInTheDocument();
});

test("with no manual pick, the per-garment suggestion is selected and tagged", () => {
  // left_chest's 4x4in placement box (101.6 mm) just exceeds the 4x4 hoop's
  // 100 mm field, so the engine suggests 5x7 — the real rule, not a stub.
  const { container } = renderStep();
  const suggested = hoopButton(container, "5×7 in");
  expect(suggested).toHaveAttribute("aria-pressed", "true");
  expect(suggested.querySelector(".hooptile-chip")).toHaveTextContent("Suggested");
  expect(hoopButton(container, "4×4 in")).toHaveAttribute("aria-pressed", "false");
  // No override yet — nothing to reset to.
  expect(container.querySelector(".hoopreset")).toBeNull();
});

test("picking a hoop dispatches the override, moves the selection, and keeps the Suggested tag honest", async () => {
  const { container, updates } = renderStep();
  await fireEvent.click(hoopButton(container, "8×8 in"));

  expect(updates).toContainEqual({ hoopId: "8x8" });
  expect(hoopButton(container, "8×8 in")).toHaveAttribute("aria-pressed", "true");
  expect(hoopButton(container, "5×7 in")).toHaveAttribute("aria-pressed", "false");
  // The tag marks the suggestion, not the selection.
  expect(hoopButton(container, "5×7 in").querySelector(".hooptile-chip")).toHaveTextContent("Suggested");
  expect(hoopButton(container, "8×8 in").querySelector(".hooptile-chip")).toBeNull();
});

test("the reset link returns control to the suggestion (hoopId null)", async () => {
  const { container, updates } = renderStep({ hoopId: "8x8" });
  const reset = container.querySelector(".hoopreset button");
  expect(reset).toHaveTextContent(/suggested 5×7 in hoop/i);

  await fireEvent.click(reset);
  expect(updates).toContainEqual({ hoopId: null });
  expect(hoopButton(container, "5×7 in")).toHaveAttribute("aria-pressed", "true");
  expect(container.querySelector(".hoopreset")).toBeNull();
});

test("manually picking the suggested hoop itself shows no redundant reset link", () => {
  const { container } = renderStep({ hoopId: "5x7" });
  expect(hoopButton(container, "5×7 in")).toHaveAttribute("aria-pressed", "true");
  expect(container.querySelector(".hoopreset")).toBeNull();
});
