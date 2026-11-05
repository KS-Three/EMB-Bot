// @vitest-environment jsdom
//
// Download blocks on a file that fails its own read-back (Kent, 2026-11-05).
//
// The real exporters.js runs here (not a mock): the browser DST writer is made
// to lose a stitch, and the customer must see "Export failed: <check> ..." with
// NOTHING saved — no download, no folder write. A clean file still saves.
import { beforeAll, beforeEach, afterEach, expect, test, vi } from "vitest";
import { render, fireEvent, within, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

const S = (x, y, type = "stitch") => ({ x, y, type });
const DESIGN = {
  stitches: [S(0, 0, "jump"), S(0, 0), S(30, 0), S(60, 0), S(90, 0), S(120, 0), S(150, 0), S(0, 0, "end")],
  colors: [{ r: 200, g: 30, b: 30 }], widthMM: 15, heightMM: 1, blocks: [],
};

const saved = [];
vi.mock("../lib/generate.js", () => ({ generateAll: () => ({ combined: DESIGN }) }));
vi.mock("../lib/download.js", () => ({ triggerDownload: (out) => { saved.push(out.filename); } }));
vi.mock("../lib/preview.js", () => ({ renderRealistic: () => {} }));
vi.mock("../lib/fontLoader.js", () => ({ ensureFonts: async () => {} }));
vi.mock("../lib/hoop.js", () => ({
  effectiveHoop: () => ({ hoop: { label: "4×4 in", widthMm: 100, heightMm: 100 } }),
  hoopFitNote: () => "",
}));
vi.mock("../lib/threads.js", () => ({
  PALETTE_INDEX: [{ id: "studio", label: "Studio" }],
  STUDIO_PALETTE: { threads: [] },
  getCachedPalette: () => ({ threads: [] }),
  loadPalette: async () => ({ threads: [] }),
  nearestInList: () => ({ rgb: [0, 0, 0], name: "Black" }),
  loadPreferredPaletteId: () => "studio",
  savePreferredPaletteId: () => {},
}));
// The engine the real exporters read: loaded as the browser loads it.
vi.mock("../lib/emb.js", () => ({ EMB: globalThis.EMB }));

let DownloadStep;
let realDST;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "pes", "readback", "svgexport", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  realDST = globalThis.EMB.encodeDST;
  ({ default: DownloadStep } = await import("./DownloadStep.svelte"));
});
beforeEach(() => { saved.length = 0; });
afterEach(() => { globalThis.EMB.encodeDST = realDST; });

const project = { version: 2, name: "EMBBOT", garmentId: "left_chest", elements: [{ id: "t", type: "text", text: "Hi" }] };
const view = () => render(DownloadStep, { props: { project, runtime: {}, digitizerHealth: { status: "ok" } } });
const button = (v, name) => within(v.container).getByRole("button", { name });

test("a clean DST saves and says so", async () => {
  const v = view();
  await fireEvent.click(button(v, "DST"));
  await waitFor(() => expect(saved).toEqual(["design.dst"]));
  expect(v.container.textContent).toMatch(/Saved DST/);
});

test("a DST that loses a stitch in the writer saves NOTHING and shows the check", async () => {
  // drops the 5th record: the file is whole, the design is not in it
  globalThis.EMB.encodeDST = (d, o) => {
    const b = realDST(d, o);
    const out = new Uint8Array(b.length - 3);
    out.set(b.subarray(0, 512 + 3 * 4));
    out.set(b.subarray(512 + 3 * 5), 512 + 3 * 4);
    return out;
  };
  const v = view();
  await fireEvent.click(button(v, "DST"));
  await waitFor(() => expect(v.container.textContent).toMatch(/Export failed: /));
  expect(saved).toEqual([]);
  expect(v.container.textContent).toMatch(/Export failed: stitch count \(expected \d+, read back \d+\)/);
  expect(v.container.textContent).not.toMatch(/Saved DST/);
});

test("the other machine formats are guarded the same way", async () => {
  const realPES = globalThis.EMB.encodePES;
  globalThis.EMB.encodePES = (d) => {
    const b = realPES(d);
    const pec = b[8] | (b[9] << 8) | (b[10] << 16) | (b[11] << 24);
    const out = Uint8Array.from(b);
    out[pec + 532 + 2] = 0x3f;
    return out;
  };
  const v = view();
  try {
    await fireEvent.click(button(v, "PES"));
    await waitFor(() => expect(v.container.textContent).toMatch(/Export failed: /));
    expect(saved).toEqual([]);
  } finally {
    globalThis.EMB.encodePES = realPES;
  }
});
