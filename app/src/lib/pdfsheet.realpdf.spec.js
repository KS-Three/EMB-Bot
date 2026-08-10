import { test, expect, beforeAll, describe } from "vitest";
import { createRequire } from "node:module";
import { jsPDF } from "jspdf";
import fs from "node:fs";

// pdfsheet.spec.js's FakeJsPDF tests confirm buildWorksheetPDF makes the
// RIGHT CALLS (text(), rect(), addImage(), addPage()) in the right order --
// but a fake recorder can't tell you whether those calls actually assemble
// into a valid PDF: a jsPDF API change (e.g. a renamed/reordered arg) or a
// call-sequence bug that still "looks right" to the fake could ship a
// broken or empty document and every existing test would still pass (see
// MASTER_SCOPE.md). This file is the second tier: it runs buildWorksheetPDF
// against the REAL `jspdf` package (no fake) and inspects the actual
// generated PDF bytes -- page count, byte size, and embedded text/image
// structure -- so a regression in the real render path fails a real test.
//
// Why raw-byte/text-extraction instead of a new PDF-parsing dependency:
// app/package.json has no PDF-reading library (no pdfjs-dist, pdf-parse,
// etc.), and this environment's Python "pdf" tooling (pypdf/pdfplumber/
// pdftotext) isn't installed here either. Adding one just for this is
// unnecessary, though: jsPDF's default output (no /Filter FlateDecode
// compression unless {compress:true} is passed, and buildWorksheetPDF
// doesn't pass it) writes PDF content streams as plain, uncompressed
// PostScript-like text -- `(Embroidery Worksheet) Tj` for a text draw,
// `/Type /Page` per page object, `/Subtype /Image` for the embedded PNG.
// That's directly greppable/regex-extractable from the raw bytes, which
// covers everything the task asks for (page count, byte size, extractable
// text) without a new dependency. If pdfsheet.js ever starts passing
// {compress:true}, these regexes will need `zlib.inflateSync` on the
// stream bytes first -- worth knowing, not worth guarding against today.
let buildWorksheetPDF;
beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  buildWorksheetPDF = require("../../../src/pdfsheet.js").buildWorksheetPDF;
});

// Real jsPDF's addImage() actually parses the PNG header it's handed (real
// width/height/colorspace/bit-depth) -- unlike FakeJsPDF, which just records
// whatever string it's given. The other tier's placeholder,
// "data:image/png;base64,FAKE", throws "wrong PNG signature" here. This is
// a real (if minimal) 1x1 PNG so the real jsPDF pipeline has something
// genuine to embed.
const TINY_PNG_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

// Same no-canvas-in-Node workaround pdfsheet.spec.js uses: buildWorksheetPDF
// calls the real renderStitches(), which needs a 2D context Node doesn't
// have, so this double stands in for the canvas. It's only asked to
// produce a valid PNG data URL -- everything downstream of that (actually
// building the PDF bytes) is 100% real jsPDF, which is what this file is
// for.
function makeCtxSpy() {
  return {
    save() {}, restore() {},
    clearRect() {}, strokeRect() {},
    beginPath() {}, moveTo() {}, lineTo() {}, stroke() {},
    setLineDash() {},
    strokeStyle: "", lineWidth: 0, lineCap: "",
  };
}

function installFakeDom() {
  const canvas = {
    width: 0,
    height: 0,
    getContext: () => makeCtxSpy(),
    toDataURL: () => TINY_PNG_DATA_URL,
  };
  const originalDocument = globalThis.document;
  globalThis.document = {
    createElement: (tag) => (tag === "canvas" ? canvas : {}),
  };
  return {
    restore() {
      globalThis.document = originalDocument;
    },
  };
}

// buildWorksheetPDF's last step is doc.save(fileName). With the real
// jsPDF running under Node (no browser to trigger a download through),
// jsPDF's own save() falls back to fs.writeFileSync(fileName, ...) and
// actually writes a PDF to the working directory as a side effect. That's
// real jsPDF behavior, not something worth changing in pdfsheet.js just
// for this test -- so the test environment intercepts the disk write
// instead, the same way it already stubs out the canvas/document DOM APIs
// Node doesn't have. The PDF bytes themselves are still captured for real,
// straight from doc.output('arraybuffer'), which doesn't touch disk.
function installRealJsPDF() {
  const originalJsPDF = globalThis.window.jspdf;
  const originalWriteFileSync = fs.writeFileSync;
  globalThis.window.jspdf = { jsPDF };
  fs.writeFileSync = () => {};
  return {
    restore() {
      globalThis.window.jspdf = originalJsPDF;
      fs.writeFileSync = originalWriteFileSync;
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

// ---- raw-PDF inspection helpers (see file-header comment for why) ----

function toBytes(doc) {
  return Buffer.from(doc.output("arraybuffer"));
}

// Pulls every `(...) Tj` text-show operator's string out of the raw PDF
// content stream and un-escapes the `\(`, `\)`, `\\` PDF requires for
// literal parens/backslashes inside a string -- e.g. the stats line's
// "(100.0 mm x 50.0 mm)" is written as "\(100.0 mm x 50.0 mm\)" in the
// actual bytes.
function extractPdfText(bytes) {
  const raw = bytes.toString("latin1");
  const out = [];
  const re = /\(((?:\\.|[^\\()])*)\)\s*Tj/g;
  let m;
  while ((m = re.exec(raw))) {
    out.push(m[1].replace(/\\([()\\])/g, "$1"));
  }
  return out;
}

// Counts real page objects ("/Type /Page") in the raw bytes -- deliberately
// excludes the single "/Type /Pages" container object via the negative
// lookahead.
function countPageObjects(bytes) {
  const raw = bytes.toString("latin1");
  const matches = raw.match(/\/Type\s*\/Page(?!s)\b/g);
  return matches ? matches.length : 0;
}

// The Pages tree's own declared /Count, straight from the bytes.
function declaredPageCount(bytes) {
  const raw = bytes.toString("latin1");
  const m = raw.match(/\/Type\s*\/Pages[\s\S]*?\/Count\s+(\d+)/);
  return m ? Number(m[1]) : null;
}

// Counts filled rectangles ("<x> <y> <w> <h> re" immediately followed by an
// "f" fill operator) -- the thread-swatch rects buildWorksheetPDF draws via
// doc.rect(..., "F").
function countFilledRects(bytes) {
  const raw = bytes.toString("latin1");
  const matches = raw.match(/ re\nf\n/g);
  return matches ? matches.length : 0;
}

describe("buildWorksheetPDF against real jsPDF (byte/structure-level checks)", () => {
  test("produces a valid, correctly-paginated real PDF for the default 2-color worksheet", () => {
    const dom = installFakeDom();
    const realPdf = installRealJsPDF();
    try {
      const design = baseDesign();
      const meta = {
        garmentLabel: "Left chest",
        fileName: "embbot-worksheet.pdf",
        garmentBox: { widthMM: 127, heightMM: 57.15 },
      };

      const doc = buildWorksheetPDF(design, meta);
      const bytes = toBytes(doc);

      // Non-trivial byte size: a broken/empty document (e.g. an exception
      // swallowed somewhere upstream, leaving just a blank letter page)
      // would come back tiny. A real worksheet with an embedded image,
      // stats block, and thread list is comfortably larger.
      expect(bytes.byteLength).toBeGreaterThan(3000);

      // Real jsPDF's own page count (from the actual document it built)...
      expect(doc.internal.getNumberOfPages()).toBe(2);
      // ...matches what's structurally present in the raw bytes: two real
      // page objects, and the Pages tree's own declared count agrees too.
      expect(countPageObjects(bytes)).toBe(2);
      expect(declaredPageCount(bytes)).toBe(2);

      // The stitch-simulation PNG was actually embedded as an image
      // XObject, not just "some addImage call was made to a fake".
      expect(bytes.toString("latin1")).toMatch(/\/Subtype\s*\/Image/);
    } finally {
      realPdf.restore();
      dom.restore();
    }
  });

  test("embeds extractable title, placement, stats, and thread-sequence text in the real PDF", () => {
    const dom = installFakeDom();
    const realPdf = installRealJsPDF();
    try {
      const design = baseDesign();
      const meta = {
        garmentLabel: "Left chest",
        fileName: "embbot-worksheet.pdf",
        garmentBox: { widthMM: 127, heightMM: 57.15 },
      };

      const doc = buildWorksheetPDF(design, meta);
      const texts = extractPdfText(toBytes(doc));

      expect(texts).toContain("Embroidery Worksheet");
      expect(texts).toContain("Placement: Left chest");

      expect(texts).toContain("Design Stats");
      expect(texts).toContain(
        "Dimensions: 3.94 in x 1.97 in  (100.0 mm x 50.0 mm)"
      );
      expect(texts).toContain("Stitch count: 4321");
      expect(texts).toContain("Color count: 2");

      expect(texts).toContain("Thread Sequence");
      expect(texts).toContain("1. 1902 Poinsettia");
      expect(texts).toContain("2. Forest Green");
    } finally {
      realPdf.restore();
      dom.restore();
    }
  });

  test("paginates a many-color design in the real PDF the same way the fake-jsPDF tests assume", () => {
    const dom = installFakeDom();
    const realPdf = installRealJsPDF();
    try {
      const colors = Array.from({ length: 40 }, (_, i) => ({
        r: i, g: i, b: i, name: "Thread " + (i + 1),
      }));
      const design = baseDesign({ colors, colorCount: colors.length });

      const doc = buildWorksheetPDF(design, { fileName: "many-colors.pdf" });
      const bytes = toBytes(doc);
      const texts = extractPdfText(bytes);

      expect(doc.internal.getNumberOfPages()).toBeGreaterThan(1);
      // Real page count agrees between jsPDF's own bookkeeping and the raw
      // bytes' actual page objects / declared Pages count.
      expect(countPageObjects(bytes)).toBe(doc.internal.getNumberOfPages());
      expect(declaredPageCount(bytes)).toBe(doc.internal.getNumberOfPages());

      // All 40 thread swatches were really drawn as filled rects, and all
      // 40 labels are really present as extractable text, not just 40
      // doc.rect()/doc.text() calls recorded by a fake.
      expect(countFilledRects(bytes)).toBe(40);
      expect(texts).toContain("1. Thread 1");
      expect(texts).toContain("40. Thread 40");
    } finally {
      realPdf.restore();
      dom.restore();
    }
  });
});
