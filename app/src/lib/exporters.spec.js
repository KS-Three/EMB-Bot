import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";

// Registered up front so exporters.js's dynamic `import("jspdf")` resolves to
// this fake instead of the real (browser-oriented) package.
vi.mock("jspdf", () => ({ jsPDF: class FakeJsPDF {} }));

let design;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","pes","svgexport","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, update } = await import("./project.js");
  design = generateDesign(update(defaultProject(), { text: "AB" }));
});
test("DST export yields bytes and a .dst filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "dst");
  expect(out.filename.endsWith(".dst")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(100);
});
test("EXP export yields bytes and a .exp filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "exp");
  expect(out.filename.endsWith(".exp")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(50);
});
test("PES export yields bytes and a .pes filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "pes");
  expect(out.filename.endsWith(".pes")).toBe(true);
  expect(out.bytes.length).toBeGreaterThan(50);
});
test("SVG export yields an <svg> string and a .svg filename", async () => {
  const { exportDesign } = await import("./exporters.js");
  const out = exportDesign(design, "svg");
  expect(out.filename.endsWith(".svg")).toBe(true);
  expect(String(out.bytes)).toContain("<svg");
});
test("unknown format throws", async () => {
  const { exportDesign } = await import("./exporters.js");
  expect(() => exportDesign(design, "zzz")).toThrow();
});
test("exportWorksheetPDF wires window.jspdf and forwards garment box (mm) to EMB.buildWorksheetPDF", async () => {
  const { exportWorksheetPDF } = await import("./exporters.js");
  const { EMB } = await import("./emb.js");

  // Fresh, jspdf-less environment: no window.jspdf yet, and buildWorksheetPDF
  // stubbed out (the real one needs a DOM canvas, which node doesn't have).
  delete globalThis.window.jspdf;
  const originalBuild = EMB.buildWorksheetPDF;
  const buildSpy = vi.fn();
  EMB.buildWorksheetPDF = buildSpy;

  try {
    await exportWorksheetPDF(design, { label: "Left chest", widthIn: 5, heightIn: 2.25 });

    expect(buildSpy).toHaveBeenCalledTimes(1);
    const [passedDesign, meta] = buildSpy.mock.calls[0];
    expect(passedDesign).toBe(design);
    expect(meta.garmentLabel).toBe("Left chest");
    expect(meta.fileName).toBe("embbot-worksheet.pdf");
    expect(meta.garmentBox.widthMM).toBeCloseTo(127, 5);
    expect(meta.garmentBox.heightMM).toBeCloseTo(57.15, 5);

    expect(window.jspdf).toBeDefined();
    expect(typeof window.jspdf.jsPDF).toBe("function");
  } finally {
    if (originalBuild === undefined) delete EMB.buildWorksheetPDF;
    else EMB.buildWorksheetPDF = originalBuild;
    delete globalThis.window.jspdf;
  }
});
