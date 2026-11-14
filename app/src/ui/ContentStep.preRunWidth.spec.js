// @vitest-environment jsdom
//
// A width typed in the Size panel BEFORE the first digitize is the width that
// run digitizes at (Kent's 2026-11-13 walkthrough, item 5). It used to land in
// `element.sizeMm` -- the scale of stitches that did not exist yet -- so the
// first run sewed at the default fit, the result then differed from `sizeMm`,
// and the "Resized to N mm ... restitch" cue sent the customer through a second
// full digitize (owl: 140 s, then 115 s). The W box was also empty until a run.
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./ContentStep.stateHarness.svelte";
import { defaultProject, defaultDigitizedElement } from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign = globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used"); });
  return { EMB: globalThis.EMB };
});

const cfgs = [];
// What the service would sew: the width asked for (0.1 mm units), 2:1.
function resultAt(w) {
  return {
    stitches: [{ x: 0, y: 0, type: "stitch" }, { x: Math.round(w * 10), y: Math.round(w * 5), type: "stitch" }],
    colors: [], stitchCount: 2, colorCount: 1, name: "t", widthMM: w, heightMM: w / 2,
  };
}
vi.mock("../lib/digitizer.js", async (orig) => ({
  ...(await orig()),
  classifyArt: () => new Promise(() => {}),
  recountArt: () => new Promise(() => {}),
  digitize: (_img, cfg) => {
    cfgs.push(cfg);
    return Promise.resolve({
      design: resultAt(cfg.target_width_mm), warnings: [], review: null, stats: null, preflight: null,
    });
  },
}));

beforeEach(() => {
  cfgs.length = 0;
  sessionStorage.clear();
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
});
afterEach(() => vi.restoreAllMocks());

const HEALTH = { ok: true, limits: { max_upload_bytes: 12e6, max_pixels: 4e7 } };

function artProject(extra = {}) {
  const el = {
    ...defaultDigitizedElement("e1"),
    name: "owl.png",
    sourcePng: "data:image/png;base64,AAAA",
    sourcePx: { w: 800, h: 400 },
    ...extra,
  };
  return { ...defaultProject(), garmentId: "left_chest", elements: [el], selectedId: "e1", selectedIds: ["e1"] };
}

async function typeMm(utils, mm) {
  await fireEvent.change(await utils.findByRole("combobox", { name: "Size unit" }, { timeout: 15000 }), { target: { value: "mm" } });
  await fireEvent.change(utils.getByLabelText("Width"), { target: { value: String(mm) } });
}

test("the W box shows the width the first run will use, not nothing", async () => {
  const el = { params: { ...defaultDigitizedElement("e1").params, target_width_mm: 91 } };
  const utils = render(Harness, { project: artProject(el), digitizerHealth: HEALTH });
  await fireEvent.change(await utils.findByRole("combobox", { name: "Size unit" }, { timeout: 15000 }), { target: { value: "mm" } });
  expect(utils.getByLabelText("Width")).toHaveValue(91);
});

test("a width typed before the first run is the width that run digitizes at, once", async () => {
  const utils = render(Harness, { project: artProject(), digitizerHealth: HEALTH });
  await typeMm(utils, 90.5);
  expect(utils.getByLabelText("Width")).toHaveValue(90.5);   // tenths, not "91"

  await fireEvent.click(utils.container.querySelector(".dgp-run"));
  await waitFor(() => expect(cfgs).toHaveLength(1));
  expect(cfgs[0].target_width_mm).toBe(90.5);

  // The run landed at the typed width: nothing is behind it, so there is no
  // "Resized to ..." cue and no second run to press.
  await waitFor(() => expect(utils.container.querySelector(".dgp-run")).not.toBeDisabled());
  expect(utils.queryByTestId("digitize-stale")).toBeNull();
  expect(cfgs).toHaveLength(1);
});

test("Auto-fit before the first run puts the placement's width back", async () => {
  const utils = render(Harness, { project: artProject(), digitizerHealth: HEALTH });
  await typeMm(utils, 60);
  await fireEvent.click(utils.getByRole("button", { name: "Auto-fit" }));
  await fireEvent.click(utils.container.querySelector(".dgp-run"));
  await waitFor(() => expect(cfgs).toHaveLength(1));
  expect(cfgs[0].target_width_mm).not.toBe(60);
});
