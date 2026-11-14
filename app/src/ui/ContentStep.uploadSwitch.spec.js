// @vitest-environment jsdom
//
// Async work a panel started for design A must not land on design B once B
// is opened (App.enterProject) -- the second half of the 2026-11-13 review.
// ContentStep now remounts its panel per design (`{#key projectId/el.id}`),
// but a torn-down Svelte 5 panel's continuation still runs, and its
// `d("elupdate")` still reaches ContentStep. Pinned here, one path each:
//   * DigitizePanel "Replace file…" still being read when B is opened: it
//     cancelled A's run at the service and erased A's resume mark.
//   * DigitizePanel's thread recolour, waiting on the palette: only
//     ContentStep's `relayRun` stands between its patch and B's `e1`.
//   * ImagePanel's upload: its "image"/"flat" events carry no id, and App
//     applies them to whatever element is selected when they arrive.
//   * DesignPanel's .dst upload, waiting on file.arrayBuffer().
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, waitFor, screen } from "@testing-library/svelte";
import Harness from "./ContentStep.testHarness.svelte";
import {
  defaultProject, defaultDigitizedElement, defaultImageElement, defaultDesignElement, DEFAULT_DIGITIZE_PARAMS,
} from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign = globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used"); });
  return { EMB: globalThis.EMB };
});
vi.mock("../lib/digitizer.js", async (orig) => ({
  ...(await orig()),
  classifyArt: () => new Promise(() => {}),
  recountArt: () => new Promise(() => {}),
}));
// Each held step is a gate the test opens after switching designs.
const gates = { image: null, palette: null };
function gate(name) {
  let open;
  gates[name] = new Promise((r) => (open = r));
  return open;
}
vi.mock("../lib/rasterize.js", async (orig) => ({
  ...(await orig()),
  loadImage: async () => {
    if (gates.image) await gates.image;
    return { width: 1400, height: 316 };
  },
}));
vi.mock("../lib/threads.js", async (orig) => {
  const real = await orig();
  return {
    ...real,
    loadPalette: async (...a) => {
      if (gates.palette) await gates.palette;
      return real.loadPalette(...a);
    },
  };
});
vi.mock("../lib/designImport.js", async (orig) => ({
  ...(await orig()),
  designFilePatch: (bytes, name) => ({ dstBase64: "AAAA", name }),
}));

beforeEach(() => {
  sessionStorage.clear();
  gates.image = null;
  gates.palette = null;
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  // Any 2d call is a no-op (ImagePanel's preview clears and paints).
  const ctx = new Proxy({}, { get: (t, k) => (k === "then" ? undefined : () => ({ data: new Uint8ClampedArray(4), width: 1, height: 1 })) });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(ctx);
  vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockImplementation(() => "data:image/png;base64,BBBB");
});
afterEach(() => vi.restoreAllMocks());

const HEALTH = { ok: true, limits: { max_upload_bytes: 12e6, max_pixels: 4e7 } };
const settle = () => new Promise((r) => setTimeout(r, 60));
const one = (el) => ({ ...defaultProject(), elements: [el], selectedId: el.id, selectedIds: [el.id] });

function pick(input, file) {
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  return fireEvent.change(input);
}

// Records every event, and which design was open when it arrived.
function recorder() {
  const log = { open: "pA", updates: [], images: [], flats: [] };
  log.props = {
    onElUpdate: (d) => log.updates.push({ open: log.open, ...d }),
    onImage: (d) => log.images.push({ open: log.open, d }),
    onFlat: (d) => log.flats.push({ open: log.open, d }),
  };
  log.after = (k) => log[k].filter((e) => e.open === "pB");
  return log;
}

async function openB(utils, log, B) {
  log.open = "pB";
  await utils.rerender({ project: B, projectId: "pB", digitizerHealth: HEALTH, ...log.props });
  await settle();
}

test("Replace file still being read when design B opens: A's run is not cancelled and its resume mark survives", async () => {
  const mod = await import("../lib/digitizer.js");
  const runs = [];
  vi.spyOn(mod, "digitize").mockImplementation((image, cfg, opts) => {
    runs.push(opts.stop);
    return new Promise(() => {});
  });
  const art = (png) => ({ ...defaultDigitizedElement("e1"), name: png + ".png", sourcePng: png, params: { ...DEFAULT_DIGITIZE_PARAMS } });
  const log = recorder();
  const utils = render(Harness, { props: { project: one(art("AAAA")), projectId: "pA", digitizerHealth: HEALTH, ...log.props } });
  await fireEvent.click(await screen.findByRole("button", { name: "Auto Digitize Image" }));
  await waitFor(() => expect(runs).toHaveLength(1));

  const release = gate("image");
  await pick(utils.container.querySelector('.dgp-upload input[type="file"]'), new File([new Uint8Array([1])], "new.png", { type: "image/png" }));
  await openB(utils, log, one(art("CCCC")));
  release();
  await settle();

  expect(log.after("updates")).toEqual([]);
  expect(runs[0].aborted).toBe(false);
  expect(sessionStorage.getItem("embot.digitizing.pA/e1")).toBe("1");
});

test("a thread recolour waiting on the palette when design B opens does not land on B's e1 (ContentStep relayRun)", async () => {
  const shape = {
    id: "s1", threadIndex: 0, threadNumber: "1000", rgb: [10, 10, 10], areaMm2: 120, layer: 0, sewOrder: null,
    sewIndex: 0, sewBlock: 0, tier: "fill", stitched: true, outline: [[0, 0], [10, 0], [10, 10]],
    outlineFull: [[0, 0], [10, 0], [10, 10]], textCandidate: false, textClusterId: null, ocrChar: null,
    ocrConfidence: null, enclosedColourUnknown: false,
  };
  const art = (png) => ({
    ...defaultDigitizedElement("e1"), name: png + ".png", sourcePng: png, params: { ...DEFAULT_DIGITIZE_PARAMS },
    result: { stitchCount: 100, widthMM: 50, heightMM: 50, colorCount: 1, colors: [], stitches: [] },
    review: { brandId: "studio", shapes: [shape] },
  });
  const log = recorder();
  const utils = render(Harness, { props: { project: one(art("AAAA")), projectId: "pA", digitizerHealth: null, ...log.props } });
  await screen.findByRole("button", { name: "Auto Digitize Image" });
  const tab = [...utils.container.querySelectorAll('button[role="tab"]')].find((b) => b.textContent.trim().startsWith("Shapes"));
  await fireEvent.click(tab);
  const shapesBtn = [...utils.container.querySelectorAll("button")].find((b) => /^Edit shapes/.test(b.textContent.trim()));
  await fireEvent.click(shapesBtn);
  const row = await waitFor(() => {
    const b = utils.container.querySelector('.tp-trigger[aria-label^="Thread color for"]');
    expect(b).toBeTruthy();
    return b;
  });
  await fireEvent.click(row);
  const swatch = await waitFor(() => {
    const s = utils.container.querySelector("[role='listbox'] [role='option']");
    expect(s).toBeTruthy();
    return s;
  });

  const release = gate("palette");
  await fireEvent.click(swatch);
  await openB(utils, log, one(art("CCCC")));
  release();
  await settle();

  expect(log.after("updates")).toEqual([]);
});

test("an ImagePanel upload still loading when design B opens sends nothing to B", async () => {
  const log = recorder();
  const utils = render(Harness, { props: { project: one(defaultImageElement("e1")), projectId: "pA", digitizerHealth: null, ...log.props } });
  const release = gate("image");
  await pick(utils.container.querySelector('input[type="file"]'), new File([new Uint8Array([1])], "logo.png", { type: "image/png" }));
  await openB(utils, log, one({ ...defaultImageElement("e1"), sourcePng: "CCCC", name: "b-logo.png" }));
  release();
  await settle();

  expect(log.after("updates")).toEqual([]);
  expect(log.after("images")).toEqual([]);
  expect(log.after("flats")).toEqual([]);
});

test("a DesignPanel .dst still being read when design B opens does not land on B's e1", async () => {
  const log = recorder();
  const utils = render(Harness, { props: { project: one(defaultDesignElement("e1")), projectId: "pA", digitizerHealth: null, ...log.props } });
  let release;
  const held = new Promise((r) => (release = r));
  const file = { name: "a.dst", size: 3, arrayBuffer: () => held.then(() => new Uint8Array([1, 2, 3]).buffer) };
  await pick(utils.container.querySelector('input[type="file"]'), file);
  await openB(utils, log, one({ ...defaultDesignElement("e1"), name: "b.dst" }));
  release();
  await settle();

  expect(log.after("updates")).toEqual([]);
});
