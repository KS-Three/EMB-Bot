// @vitest-environment jsdom
//
// A digitize result belongs to the ARTWORK it was sent, and new artwork
// starts clean (2026-11-13 review, both reproduced):
//   * "Replace file…" while Auto Digitize ran: art A's stitches landed under
//     art B's name, read as current, Download unlocked, and the file sewed A.
//   * "Replace file…" kept the old art's "Sew as flat art" (forced_class), its
//     text-to-lettering conversions, and its last run's preflight/stats/
//     priorRun/appliedBase -- a photo replacing a flat logo was sent as flat
//     art, and the Download step read the old art's findings.
// Plus the panel's own half of the per-design guard (ContentStep keys the
// panel by design too; ContentStep.projectSwitch.spec.js): a run never lands
// once the design it was started in is no longer the one shown.
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import Harness from "./DigitizePanel.testHarness.svelte";
import { DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign = globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used"); });
  return { EMB: globalThis.EMB };
});
vi.mock("../lib/rasterize.js", async (orig) => ({
  ...(await orig()),
  loadImage: () => Promise.resolve({ width: 1400, height: 316 }),
}));
vi.mock("../lib/digitizer.js", async (orig) => ({
  ...(await orig()),
  classifyArt: () => new Promise(() => {}),
  recountArt: () => new Promise(() => {}),
}));

// The new upload's preview, as the canvas encodes it.
beforeEach(() => {
  sessionStorage.clear();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage() {} });
  vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockImplementation(() => "data:image/png;base64,BBBB");
});
afterEach(() => vi.restoreAllMocks());

const HEALTH = { ok: true, limits: { max_upload_bytes: 12e6, max_pixels: 4e7 } };
const DESIGN_A = {
  name: "art-A", stitchCount: 2, widthMM: 50, heightMM: 10, colorCount: 1, colors: [{ r: 200, g: 0, b: 0 }],
  stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 500, y: 100, type: "stitch" }, { x: 0, y: 0, type: "end" }],
};
const JOB_A = { design: DESIGN_A, warnings: [], review: null, stats: null, preflight: null };
const settle = () => new Promise((r) => setTimeout(r, 60));

function artElement(extra = {}) {
  return {
    id: "e1", type: "digitized", name: "A.png", sourcePng: "AAAA", sourceFile: null, crop: null,
    sourcePx: { w: 1400, h: 316 }, widthTyped: true,
    params: { ...DEFAULT_DIGITIZE_PARAMS }, result: null, warnings: [], blockColors: {}, review: null,
    shapeOverrides: {}, deletedShapeIds: [], appliedEdits: null, appliedConfig: null, sizeMm: null,
    offsetXMm: 0, offsetYMm: 0, rotationDeg: 0,
    ...extra,
  };
}

async function spyDigitize() {
  const mod = await import("../lib/digitizer.js");
  const runs = [];
  vi.spyOn(mod, "digitize").mockImplementation((image, cfg, opts) => new Promise((resolve) => {
    runs.push({ image, stop: opts && opts.stop, resolve });
  }));
  return runs;
}

function replaceWith(container, name) {
  const input = container.querySelector('.dgp-upload input[type="file"]');
  Object.defineProperty(input, "files", { value: [new File([new Uint8Array([1, 2, 3])], name, { type: "image/png" })], configurable: true });
  return fireEvent.change(input);
}

test("Replace file while Auto Digitize runs: the run is cancelled and art A's stitches never land on art B", async () => {
  const runs = await spyDigitize();
  let el = artElement();
  const { container, getByRole } = render(Harness, {
    props: { element: el, health: HEALTH, onPatch: (d) => { el = { ...el, ...d.patch }; } },
  });
  await fireEvent.click(getByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(runs).toHaveLength(1));
  expect(runs[0].image).toBe("AAAA");

  await replaceWith(container, "B.png");
  await waitFor(() => expect(el.sourcePng).toBe("BBBB"));
  // Through the customer's own Cancel: the service is told to stop.
  expect(runs[0].stop.aborted).toBe(true);

  // Even if the abandoned job still answers, nothing of it lands.
  runs[0].resolve(JOB_A);
  await settle();
  expect(el.name).toBe("B.png");
  expect(el.result).toBeNull();
  expect(el.appliedConfig).toBeNull();
  // ...and the panel is free to digitize art B.
  await waitFor(() => expect(getByRole("button", { name: "Auto Digitize Image" }).disabled).toBe(false));
});

test("a result for art that is no longer on the element is dropped, even without a cancel", async () => {
  // The element's art changed by another route (an undo, a restore): the
  // landing compares what it sent with what the element holds now.
  const runs = await spyDigitize();
  let el = artElement();
  const patches = [];
  const utils = render(Harness, {
    props: { element: el, health: HEALTH, onPatch: (d) => patches.push(d.patch) },
  });
  await fireEvent.click(utils.getByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(runs).toHaveLength(1));
  await utils.rerender({ element: artElement({ sourcePng: "CCCC", name: "C.png" }), health: HEALTH, onPatch: (d) => patches.push(d.patch) });
  runs[0].resolve(JOB_A);
  await settle();
  expect(patches.filter((p) => "result" in p)).toEqual([]);
});

test("a run started in one design does not land after the panel is shown another design", async () => {
  const runs = await spyDigitize();
  const details = [];
  const onPatch = (d) => details.push(d);
  const utils = render(Harness, { props: { element: artElement(), projectId: "pA", health: HEALTH, onPatch } });
  await fireEvent.click(utils.getByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(runs).toHaveLength(1));
  await utils.rerender({ element: artElement(), projectId: "pB", health: HEALTH, onPatch });
  runs[0].resolve(JOB_A);
  await settle();
  expect(details.filter((d) => "result" in d.patch)).toEqual([]);
});

test("a result that does land is addressed to the design it was started in", async () => {
  const runs = await spyDigitize();
  const details = [];
  const utils = render(Harness, { props: { element: artElement(), projectId: "pA", health: HEALTH, onPatch: (d) => details.push(d) } });
  await fireEvent.click(utils.getByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(runs).toHaveLength(1));
  runs[0].resolve(JOB_A);
  await waitFor(() => expect(details.some((d) => "result" in d.patch)).toBe(true));
  const landed = details.find((d) => "result" in d.patch);
  expect(landed.id).toBe("e1");
  expect(landed.projectId).toBe("pA");
  expect(landed.patch.result.name).toBe("art-A");
});

test("Replace file resets what the OLD art produced or was told, and keeps the design's own settings", async () => {
  const { buildDigitizeConfig } = await import("../lib/digitizer.js");
  let el = artElement({
    name: "icon.png",
    params: { ...DEFAULT_DIGITIZE_PARAMS, forced_class: "flat", max_colors: 3, satin: false, edge_cap: "bean" },
    result: { ...DESIGN_A }, review: { brandId: "studio", shapes: [] },
    shapeOverrides: { S1: { stitched: false } },
    textConversions: { TCabcd1234: "e2" }, preflight: { score: 40, grade: "D" }, stats: { trims: 31 },
    priorRun: { stitch_count: 900, color_changes: 2, trims: 30, score: 41, grade: "D" }, appliedBase: "base-of-A",
    offsetXMm: 7, offsetYMm: -3, rotationDeg: 15,
  });
  const { container } = render(Harness, {
    props: { element: el, health: HEALTH, onPatch: (d) => { el = { ...el, ...d.patch }; } },
  });
  await replaceWith(container, "photo.png");
  await waitFor(() => expect(el.sourcePng).toBe("BBBB"));

  // Read fresh: "Sew as flat art" was about the old art's reading.
  expect("forced_class" in el.params).toBe(false);
  expect(buildDigitizeConfig(el, {}).forced_class).toBeUndefined();
  expect(el.textConversions).toEqual({});
  expect(el.preflight).toBeNull();
  expect(el.stats).toBeNull();
  expect(el.priorRun).toBeNull();
  expect(el.appliedBase).toBeNull();
  expect(el.result).toBeNull();
  expect(el.shapeOverrides).toEqual({});

  // The customer's choices for the DESIGN stay.
  expect(el.params.max_colors).toBe(3);
  expect(el.params.satin).toBe(false);
  expect(el.params.edge_cap).toBe("bean");
  expect(el.params.target_width_mm).toBe(DEFAULT_DIGITIZE_PARAMS.target_width_mm); // typed: not re-fitted
  expect(el.widthTyped).toBe(true);
  expect([el.offsetXMm, el.offsetYMm, el.rotationDeg]).toEqual([7, -3, 15]);
});
