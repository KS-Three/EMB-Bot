// @vitest-environment jsdom
//
// Download waits for the run (Kent 2026-10-25, "block until re-digitized").
//
// While a digitized element's stitches are behind its settings (lib/
// staleness.js — a resize since the run, a garment switched, a setting or edit
// nobody has run), the machine-file buttons are disabled and NOTHING explains
// it in words (his no-warnings ruling, 2026-10-02). The run button on the
// Content step is the way out. The other half — that the SAME rule drives that
// button and the field's hatch, and that the real file really goes out once
// the customer runs — is app/e2e/download-stale-artwork.spec.js.
//
// Mocks follow DownloadStep.spec.js, minus the ones this file never needs.
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

const exportCalls = [];
vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({ combined: { widthMM: 50, heightMM: 50, colors: [], blocks: [] } }),
}));
vi.mock("../lib/exporters.js", () => ({
  exportFileName: (name, ext) => `${name || "design"}.${ext}`,
  exportDesignPreferService: async (design, format) => {
    exportCalls.push(format);
    return { bytes: new Uint8Array([1]), filename: `design.${format}`, mime: "application/octet-stream", via: "service" };
  },
  exportWorksheetPDF: async () => {},
  exportPNG: async () => ({ blob: new Blob(), filename: "design.png", mime: "image/png" }),
  isServiceOnlyFormat: (fmt) => ["jef", "xxx", "vp3"].includes(fmt),
}));
vi.mock("../lib/download.js", () => ({ triggerDownload: () => {} }));
vi.mock("../lib/fontLoader.js", () => ({ ensureFonts: async () => {} }));
vi.mock("../lib/emb.js", () => ({ EMB: { getGarment: () => ({ label: "", widthIn: 4, heightIn: 4 }) } }));
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

let DownloadStep;
let configKey;
let buildDigitizeConfig;
beforeAll(async () => {
  ({ default: DownloadStep } = await import("./DownloadStep.svelte"));
  ({ configKey, buildDigitizeConfig } = await import("../lib/digitizer.js"));
});
beforeEach(() => {
  exportCalls.length = 0;
  localStorage.removeItem("embstudio:machine");
});

const OK = { status: "ok" };
// 80 x 40 mm as digitized (0.1 mm units).
const RESULT = {
  stitches: [{ x: 0, y: 0, type: "stitch" }, { x: 800, y: 400, type: "stitch" }],
  colors: [], stitchCount: 2, colorCount: 1, name: "t", widthMM: 80, heightMM: 40,
};

function digitized(extra = {}, project = { garmentId: "left_chest" }) {
  const el = {
    id: "e1", type: "digitized", name: "logo.png", sourcePng: "data:image/png;base64,AAAA",
    params: { target_width_mm: 80, max_colors: 6 },
    result: RESULT, review: null, shapeOverrides: {}, deletedShapeIds: [],
    appliedEdits: null, crop: null, sizeMm: null, rotationDeg: 0,
    ...extra,
  };
  if (!("appliedConfig" in extra)) el.appliedConfig = configKey(buildDigitizeConfig(el, project));
  return el;
}
const projectOf = (elements, garmentId = "left_chest") => ({ version: 2, name: "EMBBOT", garmentId, elements });

const ui = (view) => within(view.container);
const fmt = (view, label) => ui(view).getByRole("button", { name: label });
// Everything that writes a machine's file; PNG and the PDF worksheet do not.
const MACHINE_FILES = ["DST", "PES", "EXP", "JEF", "XXX", "VP3", "SVG"];

test("a current design downloads in one click", async () => {
  const view = render(DownloadStep, { props: { project: projectOf([digitized()]), runtime: {}, digitizerHealth: OK } });
  for (const label of MACHINE_FILES) expect(fmt(view, label), label).toBeEnabled();
  await fireEvent.click(fmt(view, "DST"));
  expect(exportCalls).toContain("dst");
});

test("after a resize every machine file is disabled, and a click writes nothing", async () => {
  const view = render(DownloadStep, {
    props: { project: projectOf([digitized({ sizeMm: 62 })]), runtime: {}, digitizerHealth: OK },
  });
  for (const label of MACHINE_FILES) expect(fmt(view, label), label).toBeDisabled();
  await fireEvent.click(fmt(view, "DST"));
  expect(exportCalls).toEqual([]);
  expect(view.container.querySelector('[role="dialog"]')).toBeNull();
});

test("after the garment is switched every machine file is disabled", () => {
  // Digitized on a left chest, now on a hat.
  const el = digitized({}, { garmentId: "left_chest" });
  const view = render(DownloadStep, {
    props: { project: projectOf([el], "hat_front"), runtime: {}, digitizerHealth: OK },
  });
  for (const label of MACHINE_FILES) expect(fmt(view, label), label).toBeDisabled();
});

test("one stale element among current ones is enough", () => {
  const els = [digitized({ id: "a" }), digitized({ id: "b", sizeMm: 62 }), { id: "t", type: "text", text: "Hi" }];
  const view = render(DownloadStep, { props: { project: projectOf(els), runtime: {}, digitizerHealth: OK } });
  expect(fmt(view, "DST")).toBeDisabled();
});

test("the machine button is locked too, and the lock says nothing in words", () => {
  localStorage.setItem("embstudio:machine", "brother");
  const view = render(DownloadStep, {
    props: { project: projectOf([digitized({ sizeMm: 62 })]), runtime: {}, digitizerHealth: OK },
  });
  const btn = view.container.querySelector('[data-testid="machine-download"]');
  expect(btn).toBeDisabled();
  // No warning text (Kent 2026-10-02): no note, no title, no live region.
  expect(view.container.querySelector(".machinepick-note")).toBeNull();
  expect(view.container.querySelector("[role=status], [role=alert]")).toBeNull();
  expect(view.container.textContent).not.toMatch(/stale|out of date|re-?digitize|behind|changed since/i);
  localStorage.removeItem("embstudio:machine");
});

test("PNG and the worksheet stay available: neither is a file a machine stitches", () => {
  const view = render(DownloadStep, {
    props: { project: projectOf([digitized({ sizeMm: 62 })]), runtime: {}, digitizerHealth: OK },
  });
  expect(fmt(view, "PNG")).toBeEnabled();
  expect(fmt(view, "PDF worksheet")).toBeEnabled();
});

test("it locks only what the customer can unlock: no service, or no stored art, and the file still ships", () => {
  const noService = render(DownloadStep, {
    props: { project: projectOf([digitized({ sizeMm: 62 })]), runtime: {}, digitizerHealth: null },
  });
  expect(fmt(noService, "DST")).toBeEnabled();
  noService.unmount();
  const noArt = render(DownloadStep, {
    props: { project: projectOf([digitized({ sizeMm: 62, sourcePng: null })]), runtime: {}, digitizerHealth: OK },
  });
  expect(fmt(noArt, "DST")).toBeEnabled();
});

test("it unlocks the moment the project is current again", async () => {
  const stale = projectOf([digitized({ sizeMm: 62 })]);
  const view = render(DownloadStep, { props: { project: stale, runtime: {}, digitizerHealth: OK } });
  expect(fmt(view, "DST")).toBeDisabled();
  // What a landing run writes: the scale goes, the width becomes the design's own.
  await view.rerender({
    project: projectOf([digitized({ sizeMm: null, params: { target_width_mm: 62, max_colors: 6 } })]),
    runtime: {},
    digitizerHealth: OK,
  });
  expect(fmt(view, "DST")).toBeEnabled();
});
