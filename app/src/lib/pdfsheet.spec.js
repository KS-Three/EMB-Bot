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
    // `page` matters: without it this recorder cannot tell a row printed on
    // the paper from one printed past its bottom edge, which is exactly the
    // defect that shipped (see the off-the-paper test below).
    this.texts.push({ str, x, y, page: this.pageCount });
  }
  splitTextToSize(str) {
    // Real jsPDF wraps to a width; buildWorksheetPDF only asks it to wrap the
    // hoop note. One line back is enough for a recorder — the wrapping itself
    // is jsPDF's, and pdfsheet.realpdf.spec.js exercises the real one.
    return [str];
  }
  setFillColor(r, g, b) {
    this.fillColors.push([r, g, b]);
  }
  rect(x, y, w, h, style) {
    this.rects.push({ x, y, w, h, style, page: this.pageCount });
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
    expect(strings).toContain("Stitch count: 4,321"); // grouped since 2026-09-07, like the cutaway line
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
    // ONE page. This asserted 2 until 2026-09-07, with a comment saying the
    // second page was "mostly blank" and that asserting it explicitly was
    // better than papering over it. Calling a defect out is right; making it
    // the contract is not — the assertion said the behaviour was correct, so
    // nobody went and looked at the sheet. When they did, the second page was
    // entirely blank AND the single thread row on a one-colour design was
    // being drawn at y = 11.09 on an 11.00 in page, i.e. off the paper. The
    // page break ran AFTER each row instead of before it, which produced both
    // symptoms at once.
    expect(doc.pageCount).toBe(1);
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

test("buildWorksheetPDF prints the chosen hoop next to the placement, and omits the line when none is given", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    // With a hoop (the shape exporters.js forwards from the picker).
    const withHoop = buildWorksheetPDF(baseDesign(), {
      fileName: "hooped.pdf",
      garmentLabel: "Left chest",
      hoop: { label: "4×4 in", widthMm: 100, heightMm: 100 },
    });
    const strings = withHoop.texts.map((t) => t.str);
    expect(strings).toContain("Hoop: 4×4 in (100 mm x 100 mm)");
    // Ordered under the placement line, both above the image.
    const placementY = withHoop.texts.find((t) => t.str.startsWith("Placement:")).y;
    const hoopY = withHoop.texts.find((t) => t.str.startsWith("Hoop:")).y;
    expect(hoopY).toBeGreaterThan(placementY);

    // A pre-picker caller (no hoop in meta) gets no Hoop line at all.
    const without = buildWorksheetPDF(baseDesign(), { fileName: "plain.pdf" });
    expect(without.texts.some((t) => t.str.startsWith("Hoop:"))).toBe(false);

    // Dims-less hoop still names it, without an empty parenthetical.
    const bare = buildWorksheetPDF(baseDesign(), {
      fileName: "bare.pdf",
      hoop: { label: "5×7 in" },
    });
    expect(bare.texts.map((t) => t.str)).toContain("Hoop: 5×7 in");
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

test("the 25k craft rule survives as an ESCALATION, not as the only trigger", () => {
  // The craft rule [P -- OESD, via docs/photo-digitizing-plan-2026-07-31.md
  // section 2 row 15]: est. > 25k stitches -> cutaway prescription on the
  // worksheet. The worksheet carries the rule itself (twin of the digitizer
  // preflight's STABILIZER_CUTAWAY finding) because it also serves designs
  // that never pass through the digitizer service -- lettering, imports,
  // combined designs -- whose stitch count is only known here.
  //
  // WHAT CHANGED, 2026-09-20, and why this test was rewritten rather than
  // deleted: the stitch count used to be the ONLY trigger, so under 25,000
  // the sheet said nothing about stabilizer at all -- and the same design on
  // jersey and on canvas, goods that want opposite stabilizers, got identical
  // silence. The backing class is a property of the GARMENT, so it now comes
  // from the fabric preset. The threshold above is not gone: it escalates a
  // garment whose own backing is lighter than cutaway. The rule survives; the
  // silence does not.
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };

  try {
    // Heavy on a tear-away garment: escalated, and it names the count that
    // did it rather than the threshold, so the operator can see the margin.
    const heavy = buildWorksheetPDF(baseDesign({ stitchCount: 26676 }), {
      fileName: "heavy.pdf",
      garmentId: "tote",
    });
    const heavyStrings = heavy.texts.map((t) => t.str);
    expect(heavyStrings).toContain(
      "Stabilizer: cutaway (escalated - 26,676 stitches; tear-away releases under this much thread)"
    );

    // The boundary is unchanged: exactly 25,000 is not "over", so a tear-away
    // garment is still told tear-away.
    const edge = buildWorksheetPDF(baseDesign({ stitchCount: 25000 }), {
      fileName: "edge.pdf",
      garmentId: "tote",
    });
    expect(edge.texts.map((t) => t.str)).toContain("Stabilizer: tearaway");

    // The quiet side moved rather than vanished: with NO garment named there
    // is no basis for a claim, so the sheet still says nothing -- the same
    // posture the thread-metres row takes without a thread factor.
    for (const count of [4321, 26676]) {
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

// ---- the operator's numbers reach the printed sheet (2026-09-07) ----------
//
// The Review step has always stated four facts — estimate.js calls them "the
// four facts an operator needs before loading a machine" — and this sheet
// printed two of them. Measured that day on one lettering design, one
// session, one design: the screen read "Size 102 × 15 mm / Stitches 1,336 /
// Trims 6 / Thread 2.5 m (estimate)" and the worksheet printed the size and
// the stitch count and dropped the other two. The screen stays at the desk;
// this sheet is what goes to the machine.

test("buildWorksheetPDF prints the trims and the thread estimate when given them", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };
  try {
    const doc = buildWorksheetPDF(baseDesign(), {
      fileName: "sew.pdf",
      sew: { trims: 6, threadM: 2.4813 },
    });
    const strings = doc.texts.map((t) => t.str);
    expect(strings).toContain("Trims: 6");
    // Same wording and the same one decimal as sewSummary's row: two
    // documents about one design must not phrase a fact differently.
    expect(strings).toContain("Thread: 2.5 m (estimate)");
    // In the stats block, under the counts it belongs with.
    const stitchY = doc.texts.find((t) => t.str.startsWith("Stitch count:")).y;
    const threadY = doc.texts.find((t) => t.str.startsWith("Thread:")).y;
    const seqY = doc.texts.find((t) => t.str === "Thread Sequence").y;
    expect(threadY).toBeGreaterThan(stitchY);
    expect(threadY).toBeLessThan(seqY);
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF prints zero trims but never invents a number it wasn't given", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };
  try {
    // Zero trims is a real answer — there is nothing to clip — so it prints.
    const zero = buildWorksheetPDF(baseDesign(), { fileName: "z.pdf", sew: { trims: 0, threadM: 1.2 } });
    expect(zero.texts.map((t) => t.str)).toContain("Trims: 0");

    // A caller that says nothing about sewing gets no lines, rather than
    // "Trims: 0 / Thread: 0.0 m" which reads as a measured zero.
    const silent = buildWorksheetPDF(baseDesign(), { fileName: "s.pdf" });
    expect(silent.texts.some((t) => t.str.startsWith("Trims:"))).toBe(false);
    expect(silent.texts.some((t) => t.str.startsWith("Thread:"))).toBe(false);

    // And a thread estimate that could not be computed (estimate.js returns
    // null when the engine constant is missing — a stale engine copy) is
    // dropped rather than printed as 0.0 m, for the same reason sewSummary
    // drops the row.
    const noFactor = buildWorksheetPDF(baseDesign(), { fileName: "n.pdf", sew: { trims: 3, threadM: null } });
    expect(noFactor.texts.map((t) => t.str)).toContain("Trims: 3");
    expect(noFactor.texts.some((t) => t.str.startsWith("Thread:"))).toBe(false);
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

test("buildWorksheetPDF names the chart the codes belong to, above the list", () => {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };
  try {
    // Measured 2026-09-07: picking "Isacord Polyester 40" snapped the
    // design's black to that catalog and the sheet printed "1. 1375 Dark
    // Charcoal" — a code with no chart. All 68 charts number independently,
    // so 1375 is a different colour in each of them.
    const doc = buildWorksheetPDF(baseDesign(), {
      fileName: "chart.pdf",
      chartLabel: "Isacord Polyester 40",
    });
    const strings = doc.texts.map((t) => t.str);
    expect(strings).toContain("Chart: Isacord Polyester 40");
    // Between the heading and the first cone: a customer scanning for a code
    // should meet the chart before the first number.
    const headY = doc.texts.find((t) => t.str === "Thread Sequence").y;
    const chartY = doc.texts.find((t) => t.str.startsWith("Chart:")).y;
    const firstConeY = doc.texts.find((t) => /^1\. /.test(t.str)).y;
    expect(chartY).toBeGreaterThan(headY);
    expect(chartY).toBeLessThan(firstConeY);

    // A caller with no chart to name gets no line — an empty "Chart:" is
    // worse than none.
    const bare = buildWorksheetPDF(baseDesign(), { fileName: "b.pdf" });
    expect(bare.texts.some((t) => t.str.startsWith("Chart:"))).toBe(false);
    const blank = buildWorksheetPDF(baseDesign(), { fileName: "e.pdf", chartLabel: "" });
    expect(blank.texts.some((t) => t.str.startsWith("Chart:"))).toBe(false);
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
});

// --- nothing is drawn off the paper ------------------------------------
//
// The guard that was missing. Page count alone cannot catch a row printed
// past the bottom edge, and neither can text extraction (the string is in the
// content stream wherever it sits) — which is why every existing tier passed
// while the operator's colour sequence was not on the sheet.

const PAGE_H_IN = 11;
const MARGIN_IN = 0.5;

function drawsBelowMargin(doc) {
  const bad = [];
  for (const t of doc.texts) if (t.y > PAGE_H_IN - MARGIN_IN) bad.push(`text ${JSON.stringify(t.str)} at y=${t.y.toFixed(2)}`);
  for (const r of doc.rects) if (r.y + r.h > PAGE_H_IN - MARGIN_IN) bad.push(`rect at y=${(r.y + r.h).toFixed(2)}`);
  return bad;
}

function buildWith(design, meta) {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };
  try {
    return buildWorksheetPDF(design, Object.assign({ garmentLabel: "Left chest" }, meta));
  } finally {
    dom.restore();
    globalThis.window.jspdf = originalJspdf;
  }
}

// EVERY count from 1 to 45, not a hand-picked few.
//
// The first version of these two tests sampled {1, 2, 8, 40} and passed
// against the very bug they were written for. With the render at 5.5 in the
// break-after-the-row defect produces a blank trailing page at EXACTLY n = 7
// — and that sample straddles it. A boundary that exists at one value is
// missed by any fixture set that does not happen to contain it, and the value
// moves whenever anything above the list changes height. Sweeping is cheap
// here; guessing is not.
const COLOUR_COUNTS = Array.from({ length: 45 }, (_, i) => i + 1);

// ...and with and without the hoop note, because it is the TALLEST optional
// thing above the list and it moves where the list starts: measured, the first
// row sits at 9.09 in with no note and 9.83 in with a three-line one, which is
// 6 rows on page one versus 3. The pagination does not care -- breaking before
// a row is height-independent -- but a test that only ever ran the short
// layout would not notice if that stopped being true. Found by reading the
// whole PR diff at once rather than each commit as it was written.
const HOOP_NOTES = [
  "",
  "Exceeds your 8\u00d78 in hoop \u2014 rotate the design 90\u00b0 and it fits",
  "Exceeds your 8\u00d78 in hoop, and every hoop this app offers \u2014 make it smaller under Size",
];

test("no part of the sheet is drawn past the bottom margin, at any colour count", () => {
  for (const n of COLOUR_COUNTS) {
    for (const hoopNote of HOOP_NOTES) {
      const colors = Array.from({ length: n }, (_, i) => ({ r: i * 6, g: 40, b: 90, name: "Thread " + (i + 1) }));
      const doc = buildWith(baseDesign({ colors, colorCount: n }), {
        hoop: { label: "8\u00d78 in", widthMm: 200, heightMm: 200 },
        chartLabel: "Studio basics",
        sew: { trims: 16, threadM: 7.1 },
        hoopNote,
      });
      expect({ n, noteLen: hoopNote.length, offPage: drawsBelowMargin(doc) })
        .toEqual({ n, noteLen: hoopNote.length, offPage: [] });
    }
  }
});

test("a page is never added unless there is a thread row to put on it", () => {
  // The break used to fire AFTER the last row, so a list whose final row
  // happened to cross the margin emitted a blank trailing page.
  for (const n of COLOUR_COUNTS) {
    for (const hoopNote of HOOP_NOTES) {
      const colors = Array.from({ length: n }, (_, i) => ({ r: 0, g: 0, b: 0, name: "T" + i }));
      const doc = buildWith(baseDesign({ colors, colorCount: n }), { hoopNote });
      const lastPage = doc.pageCount;
      const drawnOnLast = doc.texts.filter((t) => t.page === lastPage).length;
      expect({ n, noteLen: hoopNote.length, lastPage, drawnOnLast: drawnOnLast > 0 })
        .toEqual({ n, noteLen: hoopNote.length, lastPage, drawnOnLast: true });
    }
  }
});

test("every thread row reaches the sheet, however many there are", () => {
  const n = 40;
  const colors = Array.from({ length: n }, (_, i) => ({ r: 1, g: 2, b: 3, name: "Thread " + (i + 1) }));
  const doc = buildWith(baseDesign({ colors, colorCount: n }), {});
  const strings = doc.texts.map((t) => t.str);
  for (let i = 1; i <= n; i++) expect(strings).toContain(i + ". Thread " + i);
});

// --- the sheet says whether the design fits the hoop it names -----------

test("the worksheet prints the hoop-fit verdict directly under the hoop line", () => {
  // The Download step refuses a STITCH export for an oversize design until
  // the customer confirms, and rightly does not gate the worksheet. But the
  // sheet carried no trace of it: measured 2026-09-07, "Hoop: 8x8 in (200 mm
  // x 200 mm)" printed above a 305.0 mm design, with a picture showing it
  // comfortably inside the dashed box — because that box is the GARMENT
  // placement area, not the hoop. The one document that goes to the machine
  // was the one that did not mention the design cannot be hooped.
  const note = "Exceeds your 8\u00d78 in hoop, and every hoop this app offers \u2014 make it smaller under Size";
  const doc = buildWith(baseDesign({ widthMM: 305 }), {
    hoop: { label: "8\u00d78 in", widthMm: 200, heightMm: 200 },
    hoopNote: note,
  });
  const strings = doc.texts.map((t) => t.str);
  expect(strings).toContain(note);
  // Directly under the hoop line, above the render — a reader must meet the
  // contradiction where the claim is, not eight lines later.
  const hoopIdx = strings.findIndex((s) => s.startsWith("Hoop: "));
  const noteIdx = strings.indexOf(note);
  expect(noteIdx).toBe(hoopIdx + 1);
});

test("the worksheet says nothing about the hoop when the design fits", () => {
  // Absence has to be distinguishable from a design that fits: a sheet that
  // always carried a hoop sentence would train the reader to skip it.
  const doc = buildWith(baseDesign(), {
    hoop: { label: "5\u00d77 in", widthMm: 130, heightMm: 180 },
    hoopNote: "",
  });
  expect(doc.texts.map((t) => t.str).some((s) => /Exceeds/.test(s))).toBe(false);
});

// --- What the DIGITIZER assumed, stated on the sheet (playbook Part 3) -------
//
// The separation-of-duties argument: the stitch file can only demand, the
// operator must supply. Until now the sheet made exactly one supply-side
// claim — "Stabilizer: cutaway" — and based it on a stitch COUNT rather than
// on the goods, so a 3,000-stitch left chest on jersey and the same design on
// canvas got identical silence. These tests pin the claims that replace it,
// and every one of them is derived from something the engine actually knows:
// the fabric preset, or the design's own stitches and trims.

function metaFor(garmentId, extra) {
  return Object.assign(
    {
      garmentLabel: "Left chest",
      garmentId,
      fileName: "embbot-worksheet.pdf",
      garmentBox: { widthMM: 127, heightMM: 57.15 },
    },
    extra || {}
  );
}

function sheetStrings(design, meta) {
  const dom = installFakeDom();
  const originalJspdf = globalThis.window.jspdf;
  globalThis.window.jspdf = { jsPDF: FakeJsPDF };
  try {
    return buildWorksheetPDF(design, meta).texts.map((t) => t.str);
  } finally {
    globalThis.window.jspdf = originalJspdf;
    dom.restore && dom.restore();
  }
}

test("the stabilizer line comes from the GARMENT, not from a stitch count", () => {
  // A small design: under the 25,000-stitch rule that used to be the only
  // trigger, this sheet said nothing about stabilizer at all.
  const polo = sheetStrings(baseDesign(), metaFor("left_chest"));
  expect(polo).toContain("Stabilizer: cutaway");

  const tote = sheetStrings(baseDesign(), metaFor("tote"));
  expect(tote).toContain("Stabilizer: tearaway");

  const hat = sheetStrings(baseDesign(), metaFor("hat_front"));
  expect(hat).toContain("Stabilizer: cap buckram");
});

test("a heavy design escalates a tearaway garment to cutaway, and says why", () => {
  // The old CUTAWAY_STITCHES rule survives as an ESCALATION rather than as
  // the only trigger: past this much thread, tear-away releases whatever the
  // goods would otherwise have taken.
  const heavy = baseDesign({ stitchCount: 30000 });
  const strings = sheetStrings(heavy, metaFor("tote"));
  expect(strings.some((s) => s.startsWith("Stabilizer: cutaway"))).toBe(true);
  expect(strings.some((s) => s.includes("30,000 stitches"))).toBe(true);
});

test("a garment already on cutaway does not get told twice", () => {
  const heavy = baseDesign({ stitchCount: 30000 });
  const strings = sheetStrings(heavy, metaFor("left_chest"));
  const lines = strings.filter((s) => s.startsWith("Stabilizer:"));
  expect(lines).toHaveLength(1);
});

test("the topper line is stated either way, because absence is not an answer", () => {
  expect(sheetStrings(baseDesign(), metaFor("towel"))).toContain("Topper: yes");
  expect(sheetStrings(baseDesign(), metaFor("left_chest"))).toContain("Topper: no");
});

test("run time is printed with the basis that produced it", () => {
  // 4,321 stitches + 6 trims x 120 = 5,041 equivalents / 650 spm = 7.75 min.
  const strings = sheetStrings(
    baseDesign(),
    metaFor("left_chest", { sew: { trims: 6, threadM: 4.2 } })
  );
  expect(strings).toContain("Run time: ~8 min at 650 spm (incl. trims)");
});

test("run time still prints when the design was never walked for trims", () => {
  // `sew` is absent for a design the Studio has no walk for; the needle time
  // is still knowable from the stitch count alone.
  const strings = sheetStrings(baseDesign(), metaFor("left_chest"));
  expect(strings).toContain("Run time: ~7 min at 650 spm (incl. trims)");
});

test("the thread sequence says these numbers are the operator's to set", () => {
  const strings = sheetStrings(baseDesign(), metaFor("left_chest"));
  // DST carries no colour data at all, so the ordinal beside each cone is
  // hand-mapped at the machine every single job. The sheet has always
  // numbered them and never said what the numbers were for.
  expect(
    strings.some((s) => s.includes("DST carries no colour"))
  ).toBe(true);
});

test("an unknown garment states nothing rather than guessing", () => {
  // Same posture as the thread-metres row: no basis, no line. A worksheet
  // that invents a backing class is worse than one that stays quiet.
  const strings = sheetStrings(baseDesign(), metaFor("no_such_garment"));
  expect(strings.some((s) => s.startsWith("Stabilizer:"))).toBe(false);
  expect(strings.some((s) => s.startsWith("Topper:"))).toBe(false);
  // The run time needs no garment, so it survives.
  expect(strings.some((s) => s.startsWith("Run time:"))).toBe(true);
});
