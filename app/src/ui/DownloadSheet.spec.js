// @vitest-environment jsdom
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { defaultProject } from "../lib/project.js";

vi.mock("../lib/generate.js", () => ({
  generateAll: () => ({ combined: { widthMM: 50, heightMM: 50, colors: [], blocks: [] } }),
}));
vi.mock("../lib/exporters.js", () => ({
  exportDesignPreferService: async (design, format) => ({
    bytes: new Uint8Array([1, 2, 3]), filename: `design.${format}`, mime: "application/octet-stream", via: "browser",
  }),
  exportWorksheetPDF: async () => {},
  exportPNG: async () => ({ blob: new Blob(), filename: "design.png", mime: "image/png" }),
  isServiceOnlyFormat: (fmt) => ["jef", "xxx", "vp3"].includes(fmt),
}));

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  require("../../../src/fabrics.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: Harness } = await import("./DownloadSheet.testHarness.svelte"));
});

const ROWS = [
  { label: "Garment", value: "Left Chest" },
  { label: "Hoop", value: "4×4 in (suggested)" },
  { label: "Content", value: 'Text — "EMB"' },
];

test("is a dialog named Download with the Download heading inside", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS });
  expect(screen.getByRole("dialog", { name: "Download" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Download", exact: true })).toBeInTheDocument();
});

test("is modal: the dialog carries aria-modal", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS });
  expect(screen.getByRole("dialog", { name: "Download" })).toHaveAttribute("aria-modal", "true");
});

test("recaps the rows it is given and says Ready to stitch", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS, ready: true });
  expect(screen.getByRole("heading", { name: "Ready to stitch" })).toBeInTheDocument();
  expect(screen.getByText("Left Chest")).toBeInTheDocument();
  expect(screen.getByText('Text — "EMB"')).toBeInTheDocument();
});

test("says Nothing to stitch yet when the design cannot sew", () => {
  render(Harness, { project: defaultProject(), summaryRows: ROWS, ready: false });
  expect(screen.getByRole("heading", { name: "Nothing to stitch yet" })).toBeInTheDocument();
});

test("Escape and the close button both dispatch close", async () => {
  const onClose = vi.fn();
  render(Harness, { project: defaultProject(), summaryRows: ROWS, onClose });
  await fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(onClose).toHaveBeenCalledTimes(1);
  await fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
  expect(onClose).toHaveBeenCalledTimes(2);
});
