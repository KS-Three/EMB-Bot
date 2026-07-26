import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";

// Registered up front so exporters.js's dynamic `import("jspdf")` resolves to
// this fake instead of the real (browser-oriented) package.
vi.mock("jspdf", () => ({ jsPDF: class FakeJsPDF {} }));

// Mock preview.js to stub renderRealistic (node env has no canvas 2D context).
vi.mock("./preview.js", () => ({
  renderRealistic: vi.fn(),
}));

let design;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;

  // Set up a minimal fake document for canvas testing.
  if (!globalThis.document) {
    globalThis.document = {
      createElement: (tag) => {
        if (tag === "canvas") {
          return {
            width: 0,
            height: 0,
            getContext: () => ({}),
            toBlob: () => {},
          };
        }
        return {};
      },
    };
  }

  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","dst","exp","pes","svgexport","fonts","digitize"]) require("../../../src/" + f + ".js");
  new Function(require("node:fs").readFileSync(require("node:path").join(__dirname, "../../../src/fonts/satin-fonts.js"), "utf8"))();
  const { generateDesign } = await import("./generate.js");
  const { defaultProject, updateElement } = await import("./project.js");
  // Real v2 project (garmentId + elements) — generateDesign is a thin
  // generateAll(project) wrapper for the single-ready-element case, so no
  // compat shim is needed here anymore (Task 2 reworked generate.js).
  const project = updateElement(defaultProject(), "e1", { text: "AB" });
  design = generateDesign(project);
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

test("exportPNG renders design to PNG with correct canvas aspect ratio", async () => {
  const { exportPNG } = await import("./exporters.js");
  const { renderRealistic } = await import("./preview.js");

  // Create a design-like object with widthMM 100 and heightMM 50 (aspect 2:1).
  // Expected canvas: long side 1200, other side 600 → 1200×600.
  const testDesign = { widthMM: 100, heightMM: 50, stitches: [] };

  // Mock document.createElement to return a fake canvas with toBlob method.
  const originalCreateElement = globalThis.document.createElement;
  const mockCanvas = {
    width: 0,
    height: 0,
    toBlob: vi.fn(function (callback) {
      callback({ size: 10 }); // Fake blob-like object
    }),
    getContext: vi.fn(() => ({})),
  };

  globalThis.document.createElement = vi.fn((tag) => {
    if (tag === "canvas") return mockCanvas;
    return originalCreateElement.call(globalThis.document, tag);
  });

  try {
    const out = await exportPNG(testDesign);

    // Verify canvas was created.
    expect(globalThis.document.createElement).toHaveBeenCalledWith("canvas");

    // Verify renderRealistic was called with the mock canvas of expected dimensions.
    expect(renderRealistic).toHaveBeenCalledTimes(1);
    const [canvasArg, designArg, optsArg] = renderRealistic.mock.calls[0];
    expect(canvasArg).toBe(mockCanvas);
    expect(canvasArg.width).toBe(1200);
    expect(canvasArg.height).toBe(600);
    expect(designArg).toBe(testDesign);
    expect(optsArg.pad).toBe(40);

    // Verify returned object.
    expect(out.filename).toBe("design.png");
    expect(out.mime).toBe("image/png");
    expect(out.blob).toEqual({ size: 10 });
  } finally {
    globalThis.document.createElement = originalCreateElement;
  }
});

test("exportPNG handles null blob from canvas.toBlob with friendly error", async () => {
  const { exportPNG } = await import("./exporters.js");
  const { renderRealistic } = await import("./preview.js");

  const testDesign = { widthMM: 100, heightMM: 50, stitches: [] };

  // Mock document.createElement to return a fake canvas that produces null blob.
  const originalCreateElement = globalThis.document.createElement;
  const mockCanvas = {
    width: 0,
    height: 0,
    toBlob: vi.fn(function (callback) {
      callback(null); // Simulate failure
    }),
    getContext: vi.fn(() => ({})),
  };

  globalThis.document.createElement = vi.fn((tag) => {
    if (tag === "canvas") return mockCanvas;
    return originalCreateElement.call(globalThis.document, tag);
  });

  try {
    renderRealistic.mockClear();

    await expect(exportPNG(testDesign)).rejects.toThrow(/Failed to generate PNG/);
  } finally {
    globalThis.document.createElement = originalCreateElement;
  }
});

test("exportPNG handles aspect ratio guard (zero height treated as 1mm)", async () => {
  const { exportPNG } = await import("./exporters.js");
  const { renderRealistic } = await import("./preview.js");

  const testDesign = { widthMM: 100, heightMM: 0, stitches: [] };

  // Mock document.createElement to return a fake canvas.
  const originalCreateElement = globalThis.document.createElement;
  const mockCanvas = {
    width: 0,
    height: 0,
    toBlob: vi.fn(function (callback) {
      callback({ size: 10 });
    }),
    getContext: vi.fn(() => ({})),
  };

  globalThis.document.createElement = vi.fn((tag) => {
    if (tag === "canvas") return mockCanvas;
    return originalCreateElement.call(globalThis.document, tag);
  });

  try {
    renderRealistic.mockClear();

    const out = await exportPNG(testDesign);

    // When height is 0, it defaults to 1 (aspect 100:1).
    // Long side is 1200, so dimensions are 1200×12.
    expect(renderRealistic).toHaveBeenCalledTimes(1);
    const [canvasArg] = renderRealistic.mock.calls[0];
    expect(canvasArg).toBe(mockCanvas);
    expect(canvasArg.width).toBe(1200);
    expect(canvasArg.height).toBe(12);

    expect(out.filename).toBe("design.png");
  } finally {
    globalThis.document.createElement = originalCreateElement;
  }
});
