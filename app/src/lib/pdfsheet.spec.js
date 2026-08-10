import { test, expect, beforeAll, vi } from "vitest";
import { createRequire } from "node:module";

// pdfsheet.js's buildWorksheetPDF is the ONLY code that assembles the PDF
// worksheet (title, stitch-simulation render, stats block, thread sequence).
// exporters.spec.js only checks that exporters.js *wires up* to
// EMB.buildWorksheetPDF (with buildWorksheetPDF itself stubbed out) -- it
// never loads the real src/pdfsheet.js, so the worksheet's actual CONTENT
// has never been asserted on anywhere. This file closes that gap.
//
// pdfsheet.js resolves its own `./units.js` and `./render.js` deps via a
// plain Node `require` (see the top of the file), independent of the
// globalThis.EMB façade, so requiring it directly here is enough -- no need
// to preload the rest of the engine or go through emb.js.
let buildWorksheetPDF;
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  buildWorksheetPDF = require("../../../src/pdfsheet.js").buildWorksheetPDF;
});

// Records every jsPDF call the real pdfsheet.js makes, in the same spirit as
// preview.spec.js's makeCtxSpy: a plain double, not a real PDF renderer
// (rendered PDF bytes are opaque to assert on directly -- see report), so
// tests assert on the STRUCTURED CALLS that would produce the PDF content.
class FakeJsPDF {
  constructor(opts) {
    this.opts = opts;
    this.texts = []; // { str, x, y }
    this.rects = []; // { x, y, w, h, style }
    this.fillColors = []; // [r,g,b]
    this.images = []; // { dataUrl, format, x, y, w, h }
    this.pageCount = 1;
    this.savedAs = null;
  }
  setFontSize() {}
  setFont() {}
  text(str, x, y) {
    this.texts.push({ str, x, y });
  }
  setFillColor(r, g, b) {
    this.fillColors.push([r, g, b]);
  }
  rect(x, y, w, h, style) {
    this.rects.push({ x, y, w, h, style });
  }
  addImage(dataUrl, format, x, y, w, h) {
    this.images.push({ dataUrl, format, x, y, w, h });
  }
  addPage() {
    this.pageCount += 1;
  }
  save(fileName) {
    this.savedAs = fileName;
  }
}

// A ctx double covering every 2D-context call render.js's renderStitches()
// makes (buildWorksheetPDF renders the stitch-simulation image via the real
// renderStitches, not a mock -- node has no canvas 2D context, hence the
// double, same workaround preview.spec.js and exporters.spec.js document).
function makeCtxSpy() {
  return {
    save: vi.fn(), restore: vi.fn(),
    clearRect: vi.fn(), strokeRect: vi.fn(),
    beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(),
    setLineDash: vi.fn(),
    strokeStyle: "", lineWidth: 0, lineCap: "",
  };
}

function installFakeDom() {
  const ctx = makeCtxSpy();
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => ctx,
    toDataURL: vi.fn(() => "data:image/png;base64,FAKE"),
  };
  const originalDocument = globalThis.document;
  globalThis.document = {
    createElement: vi.fn((tag) => (tag === "canvas" ? canvas : {})),
  };
  return {
    ctx,
    canvas,
    restore: () => {
      globalThis.document = originalDocument;
    },
  };
}

function baseDesign(overrides) {
  return Object.assign(
    {
      widthMM: 100,
      heightMM: 50,
      stitchCount: 4321,
      colorCount: 2,
      colors: [
        { r: 255, g: 0, b: 0, name: "1902 Poinsettia" },
        { r: 0, g: 128, b: 0, name: "Forest Green" },
      ],
      stitches: [
        { x: 0, y: 0, type: "stitch" },
        { x: 500, y: 300, type: "stitch" },
      ],
    },
    overrides
  );
}

test("buildWorksheetPDF renders title, placement, stats, and thread sequence", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    const design = baseDesign();
    const meta = {
      garmentLabel: "Left chest",
      fileName: "embbot-worksheet.pdf",
      garmentBox: { widthMM: 127, heightMM: 57.15 },
    };

    const doc = buildWorksheetPDF(design, meta);
    const strings = doc.texts.map((t) => t.str);

    // Title + placement.
    expect(strings).toContain("Embroidery Worksheet");
    expect(strings).toContain("Placement: Left chest");

    // Stats block: dimensions in both in/mm, stitch count, color count.
    expect(strings).toContain("Design Stats");
    expect(strings).toContain(
      "Dimensions: 3.94 in x 1.97 in  (100.0 mm x 50.0 mm)"
    );
    expect(strings).toContain("Stitch count: 4321");
    expect(strings).toContain("Color count: 2");

    // Thread sequence: numbered, named, one swatch (rect) per color, in order.
    expect(strings).toContain("Thread Sequence");
    expect(strings).toContain("1. 1902 Poinsettia");
    expect(strings).toContain("2. Forest Green");
    expect(doc.rects.length).toBe(2);
    expect(doc.fillColors).toEqual([
      [255, 0, 0],
      [0, 128, 0],
    ]);

    // Stitch-simulation image: rendered once, embedded as a PNG data URL.
    expect(doc.images.length).toBe(1);
    expect(doc.images[0].dataUrl).toBe("data:image/png;base64,FAKE");
    expect(doc.images[0].format).toBe("PNG");

    // The garment placement box was forwarded into the render (drawn via
    // ctx.strokeRect in render.js's renderStitches) -- proves
    // exportWorksheetPDF's garmentBox actually reaches the preview image,
    // not just the text.
    expect(dom.ctx.strokeRect).toHaveBeenCalledTimes(1);

    expect(doc.savedAs).toBe("embbot-worksheet.pdf");
    // Note: the stitch-simulation image is a full-page-width SQUARE
    // (imgSizeIn = PAGE_W_IN - 2*MARGIN_IN = 7.5in on an 8.5x11in sheet),
    // so it alone eats most of the page's height. With a placement label
    // present, only ~1 thread row fits before the cursor crosses the
    // bottom margin and pdfsheet.js calls addPage() -- so even this
    // 2-color worksheet already spills onto a (mostly blank) second page.
    // Confirmed by hand-tracing pdfsheet.js's cursorY math; not something
    // this test suite should silently paper over, so it's asserted
    // explicitly rather than assumed to be 1.
    expect(doc.pageCount).toBe(2);
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF omits the Placement line when no garment label is given", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    const design = baseDesign();
    const doc = buildWorksheetPDF(design, { fileName: "no-label.pdf" });
    const strings = doc.texts.map((t) => t.str);

    expect(strings).toContain("Embroidery Worksheet");
    expect(strings.some((s) => s.startsWith("Placement:"))).toBe(false);
    // No garmentBox this time -- render.js shouldn't draw a placement box.
    expect(dom.ctx.strokeRect).not.toHaveBeenCalled();
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF falls back to 'Color N' when a thread has no name, and to colors.length when colorCount is missing", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    const design = baseDesign({
      colorCount: undefined,
      colors: [{ r: 10, g: 20, b: 30 }, { r: 40, g: 50, b: 60, name: "Navy" }],
    });
    const doc = buildWorksheetPDF(design, { fileName: "fallback.pdf" });
    const strings = doc.texts.map((t) => t.str);

    expect(strings).toContain("1. Color 1");
    expect(strings).toContain("2. Navy");
    expect(strings).toContain("Color count: 2"); // colors.length, since colorCount was undefined
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF paginates the thread sequence once it runs past the bottom margin", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    // Each thread row advances the cursor 0.22in; the sheet is 11in tall
    // with a 0.5in margin and the thread list starts well down the page
    // (after title/stats/image), so a few dozen rows is enough to force
    // at least one addPage() -- exercising the multi-color-count reality
    // of real embroidery designs, which the zero-coverage baseline never
    // touched.
    const colors = Array.from({ length: 40 }, (_, i) => ({
      r: i, g: i, b: i, name: "Thread " + (i + 1),
    }));
    const design = baseDesign({ colors, colorCount: colors.length });
    const doc = buildWorksheetPDF(design, { fileName: "many-colors.pdf" });

    expect(doc.rects.length).toBe(40);
    expect(doc.pageCount).toBeGreaterThan(1);
    const strings = doc.texts.map((t) => t.str);
    expect(strings).toContain("40. Thread 40");
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF treats a missing design as all-zero stats rather than throwing", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    const doc = buildWorksheetPDF(undefined, { fileName: "empty.pdf" });
    const strings = doc.texts.map((t) => t.str);

    expect(strings).toContain(
      "Dimensions: 0.00 in x 0.00 in  (0.0 mm x 0.0 mm)"
    );
    expect(strings).toContain("Stitch count: 0");
    expect(strings).toContain("Color count: 0");
    expect(doc.rects.length).toBe(0);
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF prescribes cutaway stabilizer past 25k stitches, and only past it", () => {
  // The craft rule [P -- OESD, via docs/photo-digitizing-plan-2026-07-31.md
  // section 2 row 15]: est. > 25k stitches -> cutaway prescription on the
  // worksheet. The worksheet carries the rule itself (twin of the digitizer
  // preflight's STABILIZER_CUTAWAY finding) because it also serves designs
  // that never pass through the digitizer service -- lettering, imports,
  // combined designs -- whose stitch count is only known here.
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    const heavy = buildWorksheetPDF(baseDesign({ stitchCount: 26676 }), {
      fileName: "heavy.pdf",
    });
    const heavyStrings = heavy.texts.map((t) => t.str);
    expect(heavyStrings).toContain(
      "Stabilizer: cutaway (over 25,000 stitches - tear-away releases under this much thread)"
    );

    // The quiet side: the base design (4,321 stitches) and the boundary
    // itself (exactly 25,000 is not "over") both stay silent -- a worksheet
    // line that shows on every design trains the operator to ignore it.
    for (const count of [4321, 25000]) {
      const doc = buildWorksheetPDF(baseDesign({ stitchCount: count }), {
        fileName: "modest.pdf",
      });
      const strings = doc.texts.map((t) => t.str);
      expect(strings.some((s) => s.startsWith("Stabilizer:"))).toBe(false);
    }
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});
