// @vitest-environment jsdom
//
// The Rotation slider keeps the lettering's size even before its font has
// loaded (review follow-up, 2026-11-13). Without the font the panel cannot
// generate the lettering for its fit aspect, so the patch used to turn it
// only, and the engine then refit it to the old width at the new angle (the
// original rotate bug), with nothing putting it right once the font arrived.
// The turn now waits for fontLoader's ensureFont. The engine is stubbed: a
// "lettering" 100 x 10 mm upright whose design exists only once its font is.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

let resolveFont;
vi.mock("../lib/fontLoader.js", async (orig) => ({
  ...(await orig()),
  ensureFont: () => new Promise((res) => { resolveFont = () => { globalThis.EMB.SATIN_FONTS.slow_font = {}; res({}); }; }),
}));
vi.mock("../lib/generate.js", async (orig) => ({
  ...(await orig()),
  generateElement: (el) => {
    if (!globalThis.EMB.SATIN_FONTS[el.fontKey]) throw new Error("Unknown font: " + el.fontKey);
    return { fitMm: { w0: 100, h0: 10 } };
  },
}));

let Harness;
beforeAll(async () => {
  globalThis.EMB = {
    buildLetteringDesign: () => { throw new Error("not used by this spec"); },
    SATIN_FONTS: {},
    getGarment: () => ({ id: "left_chest", widthIn: 4, heightIn: 4 }),
  };
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./TextStep.testHarness.svelte"));
});

const element = {
  id: "e1", type: "text", text: "HELLO", fontKey: "slow_font", colorRgb: [20, 20, 20], colorRanges: [],
  weightPreset: "normal", slantDeg: 0, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, align: "center", sizeMm: 100,
};

test("turning lettering whose font is still loading keeps its size once the font arrives", async () => {
  const patches = [];
  const { container } = render(Harness, { props: { element, project: { garmentId: "left_chest" }, onPatch: (d) => patches.push(d.patch) } });
  const slider = container.querySelector('label.letterspacing input[type="range"][max="359"], label.letterspacing input[type="range"][max="360"]');
  const rot = [...container.querySelectorAll('input[type="range"]')].find((i) => i.closest("label") && /Rotation/.test(i.closest("label").textContent));
  await fireEvent.input(rot || slider, { target: { value: "90" } });
  resolveFont && resolveFont();
  await new Promise((r) => setTimeout(r, 0));
  const turn = patches.find((p) => p.rotationDeg === 90);
  expect(turn, "a turn was patched").toBeTruthy();
  // 100 x 10 upright turned a quarter: the request becomes the old height
  expect(turn.sizeMm).toBeCloseTo(10, 9);
});
