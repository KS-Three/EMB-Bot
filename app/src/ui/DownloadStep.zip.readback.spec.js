// @vitest-environment jsdom
//
// Download all goes through the read-back too (PR #1253, Kent 2026-11-05).
//
// The real exporters.js and the real engine run here (not mocks), as in
// DownloadStep.readback.spec.js: the browser writer is made to lose a stitch
// and "Download all" must show "Export failed: <check> ..." with NOTHING
// saved -- no zip, no folder write -- exactly as the single DST button does.
// The service-only formats (JEF / XXX / VP3) are not reached: the archive stops
// at the first file that fails.
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
vi.mock("../lib/emb.js", () => ({ EMB: globalThis.EMB }));

let DownloadStep;
let realDST;
let realPES;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "pes", "readback", "svgexport", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  realDST = globalThis.EMB.encodeDST;
  realPES = globalThis.EMB.encodePES;
  ({ default: DownloadStep } = await import("./DownloadStep.svelte"));
});
beforeEach(() => { saved.length = 0; });
afterEach(() => {
  globalThis.EMB.encodeDST = realDST;
  globalThis.EMB.encodePES = realPES;
});

const project = { version: 2, name: "EMBBOT", garmentId: "left_chest", elements: [{ id: "t", type: "text", text: "Hi" }] };
const view = () => render(DownloadStep, { props: { project, runtime: {}, digitizerHealth: { status: "ok" } } });
const allButton = (v) => within(v.container).getByRole("button", { name: "Download all" });

test("a DST that loses a stitch in the writer fails Download all and saves NOTHING", async () => {
  // drops the 5th record: the file is whole, the design is not in it
  globalThis.EMB.encodeDST = (d, o) => {
    const b = realDST(d, o);
    const out = new Uint8Array(b.length - 3);
    out.set(b.subarray(0, 512 + 3 * 4));
    out.set(b.subarray(512 + 3 * 5), 512 + 3 * 4);
    return out;
  };
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(v.container.textContent).toMatch(/Export failed: stitch count \(expected \d+, read back \d+\)/));
  expect(saved).toEqual([]);
  expect(v.container.textContent).not.toMatch(/Saved ZIP/);
  // the error text IS the status line: the customer reads why, and nothing says verified
  const line = v.container.querySelector("p[aria-live]").textContent;
  expect(line).toMatch(/^Export failed: stitch count \(expected \d+, read back \d+\)/);
  expect(line).not.toMatch(/verified|re-read and/);
  // the button is back for another try
  expect(allButton(v)).toBeEnabled();
});

test("so does a PES that fails its read-back, behind a DST that passed", async () => {
  globalThis.EMB.encodePES = (d) => {
    const b = realPES(d);
    const pec = b[8] | (b[9] << 8) | (b[10] << 16) | (b[11] << 24);
    const out = Uint8Array.from(b);
    out[pec + 532 + 2] = 0x3f;
    return out;
  };
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(v.container.textContent).toMatch(/Export failed: /));
  expect(saved).toEqual([]);
});
