// @vitest-environment jsdom
//
// The typed-width bound is the PLACEMENT's box (2026-10-27), against the real
// engine table — SizePanel.spec.js stubs the engine with the left chest's
// inch pair and is about the display; this is about which box the clamp
// reads. Until today it read the garment's round-inch pair: a hat front let a
// typed width run to 127 mm while auto-fit stopped at the pro's 113.5.
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./SizePanel.testHarness.svelte"));
});

async function typeWidthOn(project, mm) {
  const updates = [];
  const { getByLabelText, getByRole } = render(Harness, {
    project: { ...project, sizeMm: null, elements: [] },
    designDims: { widthMM: 60, heightMM: 20 },
    onUpdate: (u) => updates.push(u),
  });
  await fireEvent.change(getByRole("combobox", { name: "Size unit" }), { target: { value: "mm" } });
  await fireEvent.change(getByLabelText("Width"), { target: { value: String(mm) } });
  return updates.at(-1).sizeMm;
}

test("a hat front clamps a typed width to the pro's 113.5, not the inch table's 127", async () => {
  expect(await typeWidthOn({ garmentId: "hat_front" }, 120)).toBeCloseTo(113.5, 5);
});

test("the hat's rear placement clamps to ITS box, 88.9", async () => {
  expect(await typeWidthOn({ garmentId: "hat_front", placementId: "hat_rear" }, 120)).toBeCloseTo(88.9, 5);
});

test("a tee's left chest clamps to the pro's 96", async () => {
  expect(await typeWidthOn({ garmentId: "full_back", placementId: "left_chest" }, 120)).toBeCloseTo(96, 5);
});

test("a tee's own full back clamps to the inch table's 304.8", async () => {
  expect(await typeWidthOn({ garmentId: "full_back" }, 320)).toBeCloseTo(304.8, 5);
});
