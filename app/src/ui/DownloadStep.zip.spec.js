// @vitest-environment jsdom
//
// "Download all" on the Download step: one zip, every format the step offers,
// the worksheet, a preview picture and the thread list (Kent, 2026-11-05).
//
// exportZip.js and fflate are the real ones; the writers are mocked so the test
// can say exactly which bytes each format returns and check they arrive in the
// zip untouched. The lock (stale stitches) is covered beside the single buttons
// in DownloadStep.stale.spec.js.
import { beforeAll, beforeEach, expect, test, vi } from "vitest";
import { render, fireEvent, within, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { unzipSync } from "fflate";

const saved = [];
const calls = [];
let failFormat = null;
let hoopNote = "";
// What each format's read-back reports, as the real exporters report it: SVG is
// never re-read; XXX and VP3 are re-read with checks the service reader cannot do.
let readbackFor = (fmt) => {
  if (fmt === "svg") return { verified: false, reason: "SVG is a picture of the design, not a stitch file" };
  const rb = { verified: true, stitches: 20, trims: 1, colors: 2 };
  if (fmt === "xxx") return { ...rb, skipped: ["trim_order", "color_order", "bounding_box", "stitch_positions"] };
  if (fmt === "vp3") return { ...rb, skipped: ["longest_stitch"] };
  return rb;
};
const defaultReadbackFor = readbackFor;

const bytesFor = (fmt) => Uint8Array.from({ length: 200 }, (_, i) => (i * 13 + fmt.charCodeAt(0)) & 255);
const PDF = Uint8Array.from([0x25, 0x50, 0x44, 0x46, 7]);
const PNG = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 5]);

vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({
    combined: {
      widthMM: 50, heightMM: 50, blocks: [],
      colors: [{ r: 200, g: 30, b: 40 }, { r: 0, g: 0, b: 0 }],
    },
  }),
}));
vi.mock("../lib/exporters.js", () => ({
  exportFileName: (name, ext) => (String(name || "design").toLowerCase().replace(/[^a-z0-9]+/g, "-") || "design") + "." + ext,
  exportDesignPreferService: async (design, format, opts) => {
    calls.push({ format, opts });
    if (format === failFormat) throw new Error("Export failed: stitch count (expected 20, read back 19).");
    return { bytes: bytesFor(format), filename: "design." + format, mime: "application/octet-stream", via: "service", readback: readbackFor(format) };
  },
  exportWorksheetPDF: async (design, garment, hoop, chartLabel, note, o = {}) => (o.asBytes ? PDF : undefined),
  exportPNG: async () => ({ blob: new Blob([PNG], { type: "image/png" }), filename: "design.png", mime: "image/png" }),
  isServiceOnlyFormat: (fmt) => ["jef", "xxx", "vp3"].includes(fmt),
}));
vi.mock("../lib/download.js", () => ({ triggerDownload: (out) => { saved.push(out); } }));
vi.mock("../lib/fontLoader.js", () => ({ ensureFonts: async () => {} }));
vi.mock("../lib/emb.js", () => ({ EMB: { getGarment: () => ({ label: "", widthIn: 4, heightIn: 4 }) } }));
vi.mock("../lib/hoop.js", () => ({
  effectiveHoop: () => ({ hoop: { label: "4×4 in", widthMm: 100, heightMm: 100 } }),
  hoopFitNote: () => hoopNote,
}));
const PALETTE = {
  label: "Madeira Polyneon",
  threads: [{ rgb: [200, 30, 40], code: "1902", name: "Poinsettia" }, { rgb: [0, 0, 0], code: "1000", name: "Black" }],
};
vi.mock("../lib/threads.js", () => ({
  PALETTE_INDEX: [{ id: "studio", label: "Studio" }],
  STUDIO_PALETTE: { threads: [] },
  getCachedPalette: () => PALETTE,
  loadPalette: async () => PALETTE,
  nearestInList: (list, rgb) => (rgb[0] > 100 ? list[0] : list[1]),
  loadPreferredPaletteId: () => "studio",
  savePreferredPaletteId: () => {},
}));

let DownloadStep;
beforeAll(async () => {
  ({ default: DownloadStep } = await import("./DownloadStep.svelte"));
});
beforeEach(() => {
  saved.length = 0;
  calls.length = 0;
  failFormat = null;
  hoopNote = "";
  readbackFor = defaultReadbackFor;
  localStorage.clear();
});

const project = { version: 2, name: "EMBBOT", garmentId: "left_chest", elements: [{ id: "t", type: "text", text: "Hi" }] };
const view = (over = {}) =>
  render(DownloadStep, { props: { project, designName: "Fritsch Hat", runtime: {}, digitizerHealth: { status: "ok" }, ...over } });
const allButton = (v) => within(v.container).getByRole("button", { name: "Download all" });

test("one click saves ONE zip holding every format, the worksheet, the picture and the threads", async () => {
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  const out = saved[0];
  expect(out.filename).toBe("fritsch-hat.zip");
  expect(out.mime).toBe("application/zip");
  const files = unzipSync(out.bytes);
  expect(Object.keys(files)).toEqual([
    "fritsch-hat.dst", "fritsch-hat.pes", "fritsch-hat.exp", "fritsch-hat.jef", "fritsch-hat.xxx", "fritsch-hat.vp3", "fritsch-hat.svg",
    "fritsch-hat-worksheet.pdf", "fritsch-hat-preview.png", "fritsch-hat-threads.txt",
  ]);
  for (const f of ["dst", "pes", "exp", "jef", "xxx", "vp3", "svg"]) {
    expect(Array.from(files[`fritsch-hat.${f}`]), f).toEqual(Array.from(bytesFor(f)));
  }
  expect(Array.from(files["fritsch-hat-worksheet.pdf"])).toEqual(Array.from(PDF));
  expect(Array.from(files["fritsch-hat-preview.png"])).toEqual(Array.from(PNG));
  expect(new TextDecoder().decode(files["fritsch-hat-threads.txt"])).toBe(
    "Thread chart: Madeira Polyneon\r\n1. 1902 Poinsettia (#C81E28)\r\n2. 1000 Black (#000000)\r\n",
  );
  expect(v.container.textContent).toMatch(/Saved ZIP/);
});

test("the success line says how many files were re-read, and names the ones that were not or only partly", async () => {
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(v.container.querySelector("p[aria-live]").textContent).toBe(
    "Saved ZIP - 6 of 7 stitch files re-read and verified (SVG not re-read; XXX, VP3 with some checks skipped)",
  );
});

test("when every stitch file was fully re-read the line says so plainly", async () => {
  readbackFor = () => ({ verified: true, stitches: 20, trims: 1, colors: 2 });
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(v.container.querySelector("p[aria-live]").textContent).toBe("Saved ZIP - 7 stitch files re-read and verified");
});

test("a service whose verify headers could not be read is 'not re-read', never 'verified'", async () => {
  readbackFor = (fmt) => (fmt === "jef" ? undefined : defaultReadbackFor(fmt));
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(v.container.querySelector("p[aria-live]").textContent).toMatch(/5 of 7 stitch files re-read and verified \(JEF, SVG not re-read;/);
});

test("each format goes through the same export call the single buttons make", async () => {
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(calls.map((c) => c.format)).toEqual(["dst", "pes", "exp", "jef", "xxx", "vp3", "svg"]);
  for (const c of calls) expect(c.opts.label).toBe("EMBBOT");
});

test("the DST inside the zip honours Jumps per trim; no other format is told", async () => {
  const v = view();
  const input = v.container.querySelector('[data-testid="jumps-per-trim"]');
  await fireEvent.change(input, { target: { value: "6" } });
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(calls.find((c) => c.format === "dst").opts.jumpsPerTrim).toBe(6);
  for (const c of calls.filter((c) => c.format !== "dst")) expect(c.opts.jumpsPerTrim).toBeUndefined();
});

test("one format failing read-back saves NOTHING and shows that format's reason", async () => {
  failFormat = "vp3";
  const v = view();
  await fireEvent.click(allButton(v));
  await waitFor(() => expect(v.container.textContent).toMatch(/Export failed: stitch count \(expected 20, read back 19\)/));
  expect(saved).toEqual([]);
  expect(v.container.textContent).not.toMatch(/Saved ZIP/);
  // The button is back for another try.
  expect(allButton(v)).toBeEnabled();
});

test("it needs the digitizer service, like JEF / XXX / VP3: no service, no button", () => {
  const v = view({ digitizerHealth: null });
  expect(allButton(v)).toBeDisabled();
});

test("a design bigger than the hoop asks first, like the format buttons", async () => {
  hoopNote = "Design is 150 mm wide; the hoop is 100 mm.";
  const v = view();
  await fireEvent.click(allButton(v));
  expect(saved).toEqual([]);
  const dialog = v.container.querySelector('[role="dialog"]');
  expect(dialog).not.toBeNull();
  await fireEvent.click(within(dialog).getByRole("button", { name: "Download all anyway" }));
  await waitFor(() => expect(saved).toHaveLength(1));
  expect(saved[0].filename).toBe("fritsch-hat.zip");
});
