const deps =
  typeof module !== "undefined" && module.exports
    ? { units: require("./units.js"), render: require("./render.js") }
    : {
        units: (typeof globalThis !== "undefined" ? globalThis : this).EMB,
        render: (typeof globalThis !== "undefined" ? globalThis : this).EMB,
      };

(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const { mmToInch } = deps.units;
  const { renderStitches } = deps.render;

  const PAGE_W_IN = 8.5;
  const PAGE_H_IN = 11;
  const MARGIN_IN = 0.5;

  // Stitch count past which the worksheet prescribes cutaway stabilizer: a
  // design this heavy needs permanent support or it distorts when the hoop
  // comes off. Craft rule [P — OESD, via docs/photo-digitizing-plan-
  // 2026-07-31.md §2 row 15: "est. > 25k st -> cutaway prescription on the
  // worksheet"]. Twin of the digitizer preflight's STABILIZER_CUTAWAY
  // constant (digitizer/digitizer_core/preflight.py, STITCHES_CUTAWAY_MIN)
  // — duplicated deliberately, not carelessly: the worksheet also serves
  // designs that never pass through the digitizer service (lettering,
  // imports, combined multi-element designs), and the combined design's
  // stitch count is only known here. Change one and change both.
  const CUTAWAY_STITCHES = 25000;

  function rgbCss(color) {
    if (!color) return [0, 0, 0];
    const c = (v) => Math.max(0, Math.min(255, v | 0));
    return [c(color.r), c(color.g), c(color.b)];
  }

  function buildWorksheetPDF(design, meta) {
    const options = meta || {};
    const jsPDF = window.jspdf.jsPDF;
    const doc = new jsPDF({ unit: "in", format: "letter" });

    const widthMM = (design && design.widthMM) || 0;
    const heightMM = (design && design.heightMM) || 0;
    const widthIn = mmToInch(widthMM);
    const heightIn = mmToInch(heightMM);
    const stitchCount = (design && design.stitchCount) || 0;
    const colors = (design && design.colors) || [];
    const colorCount = (design && design.colorCount) || colors.length;

    let cursorY = MARGIN_IN;

    // Title
    doc.setFontSize(18);
    doc.setFont(undefined, "bold");
    doc.text("Embroidery Worksheet", MARGIN_IN, cursorY + 0.25);
    cursorY += 0.45;

    doc.setFontSize(11);
    doc.setFont(undefined, "normal");
    if (options.garmentLabel) {
      doc.text("Placement: " + options.garmentLabel, MARGIN_IN, cursorY + 0.15);
      cursorY += 0.3;
    }
    // The chosen hoop (launch item 2 — hoop picker), next to the placement:
    // the operator mounts a physical hoop, so the sheet names it. `hoop` is
    // { label, widthMm, heightMm } (a garments.js HOOPS preset, forwarded by
    // app exporters.js); absent on pre-picker callers -> no line, same
    // optional treatment as garmentLabel above.
    if (options.hoop && options.hoop.label) {
      let hoopLine = "Hoop: " + options.hoop.label;
      if (options.hoop.widthMm && options.hoop.heightMm) {
        hoopLine += " (" + options.hoop.widthMm + " mm x " + options.hoop.heightMm + " mm)";
      }
      doc.text(hoopLine, MARGIN_IN, cursorY + 0.15);
      cursorY += 0.3;
    }
    // ...and whether the design actually FITS that hoop.
    //
    // The Download step refuses a stitch export for an oversize design until
    // the customer confirms ("the machine cannot stitch past the edge of the
    // hoop"), and rightly does not gate the worksheet, which is a reference
    // document. But the sheet then carried no trace of it. Measured
    // 2026-09-07 by rendering a real worksheet and looking at it: Full Back,
    // a name auto-fitted to the placement area, "Hoop: 8x8 in (200 mm x
    // 200 mm)" printed above a 305.0 mm design -- and the picture below shows
    // it comfortably inside the dashed box, because that box is the GARMENT
    // placement area, not the hoop. The one document that goes to the machine
    // was the one that did not mention the design cannot be hooped.
    //
    // Directly under the hoop line, not down in the stats: it contradicts the
    // line above it, and a reader should meet the contradiction there rather
    // than eight lines later. Same sentence the screen shows, passed in
    // rather than re-derived -- two documents about one design must not
    // phrase the same fact differently.
    if (options.hoopNote) {
      doc.setFont(undefined, "bold");
      for (const line of doc.splitTextToSize(options.hoopNote, PAGE_W_IN - 2 * MARGIN_IN)) {
        doc.text(line, MARGIN_IN, cursorY + 0.15);
        cursorY += 0.22;
      }
      doc.setFont(undefined, "normal");
      cursorY += 0.08;
    }

    // Rendered stitch simulation image.
    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 900;
    renderStitches(canvas, design, {
      padding: 20,
      showBox: options.garmentBox || null,
    });
    const dataUrl = canvas.toDataURL("image/png");

    // The render used to take the full text width, 7.5 in of an 11 in page,
    // and everything below it was pushed toward the bottom edge with nothing
    // checking that it fit. Measured 2026-09-07 by rendering a real worksheet
    // to an image and LOOKING at it: on a one-colour design the single thread
    // row was drawn at y = 11.09 on an 11.00 in page -- off the paper -- and a
    // blank second page followed. The operator's colour sequence was simply
    // not on the sheet.
    //
    // Nothing caught it because the row IS in the content stream: text
    // extraction (worksheet-numbers.spec.js, pdfsheet.realpdf.spec.js) finds
    // it wherever it sits, on the page or past its edge.
    //
    // 5.5 in is a judgement call, not a measurement. It keeps the picture the
    // dominant thing on the sheet while leaving room for the stats block and
    // about seven thread rows, so an ordinary design prints on ONE page. The
    // pagination below is what makes any number correct; this only decides how
    // often a second page is needed at all.
    const imgSizeIn = Math.min(PAGE_W_IN - 2 * MARGIN_IN, 5.5);
    const imgY = cursorY + 0.1;
    // The 8th argument is jsPDF's zlib level, and it defaults to NONE — the
    // 900x900 render was embedded as RAW pixels. Measured 2026-09-07 on a real
    // worksheet: 2.43 MB of image plus a 0.81 MB alpha mask, 100% of a 3.24 MB
    // file, with 900 x 900 x 3 and 900 x 900 x 1 landing on those numbers
    // exactly.
    //
    // Same render, same page, one argument, measured in the shipped jsPDF:
    //
    //   NONE (shipping) .... 2.43 MB   157 ms
    //   FAST ............... 0.20 MB   193 ms
    //   MEDIUM ............. 0.12 MB   201 ms
    //   SLOW ............... 0.10 MB   373 ms
    //
    // MEDIUM: FAST's time for 40% less, and well short of SLOW's. zlib is
    // lossless, so the sheet a customer prints is pixel-identical to the one
    // this used to produce.
    //
    // NOT JPEG, which measured smaller still (0.07 MB, 2 ms): this render is
    // thin dark lines on a pale ground, exactly the content JPEG ringing
    // damages, and the sheet is the reference an operator works from.
    doc.addImage(dataUrl, "PNG", MARGIN_IN, imgY, imgSizeIn, imgSizeIn, undefined, "MEDIUM");
    cursorY = imgY + imgSizeIn + 0.25;

    // Stats block.
    doc.setFontSize(12);
    doc.setFont(undefined, "bold");
    doc.text("Design Stats", MARGIN_IN, cursorY);
    cursorY += 0.22;

    doc.setFontSize(10);
    doc.setFont(undefined, "normal");
    const statsLines = [
      "Dimensions: " +
        widthIn.toFixed(2) + " in x " + heightIn.toFixed(2) + " in  (" +
        widthMM.toFixed(1) + " mm x " + heightMM.toFixed(1) + " mm)",
      // Grouped, like the cutaway line four lines down — which has always
      // said "over 8,000 stitches" while this one printed a bare 26676 two
      // lines above it, on the same sheet. Explicit "en-US" for the same
      // reason that line uses it: a PDF's text should not change with the
      // machine that generated it. (The Studio's on-screen counts use a bare
      // toLocaleString(), which follows the viewer's locale, and that is the
      // right default there.)
      "Stitch count: " + stitchCount.toLocaleString("en-US"),
      "Color count: " + colorCount,
    ];
    // The two operator numbers the SCREEN has always had and this sheet did
    // not. Measured 2026-09-07 on one lettering design, same session, same
    // design: the Review step read "Size 102 x 15 mm / Stitches 1,336 /
    // Trims 6 / Thread 2.5 m (estimate)", and the worksheet printed the
    // first two and dropped the last two. estimate.js calls these "the four
    // facts an operator needs before loading a machine" — and this sheet is
    // the one that goes to the machine, while the screen stays at the desk.
    //
    // Same wording as `sewSummary`'s rows on purpose: two documents about
    // one design that phrase the same fact differently invite the reader to
    // wonder which is right.
    //
    // Optional, like `hoop` above: a caller that passes no `sew` gets no
    // lines rather than a zero. "0 trims" is a real and useful answer (there
    // is nothing to clip), so absence has to be distinguishable from zero,
    // which is why this tests the object and not the numbers.
    if (options.sew) {
      if (typeof options.sew.trims === "number") {
        statsLines.push("Trims: " + options.sew.trims);
      }
      if (typeof options.sew.threadM === "number" && options.sew.threadM > 0) {
        statsLines.push("Thread: " + options.sew.threadM.toFixed(1) + " m (estimate)");
      }
    }
    if (stitchCount > CUTAWAY_STITCHES) {
      // The cutaway prescription (see CUTAWAY_STITCHES above). A line in
      // the stats block, not a warning banner: nothing is wrong with the
      // design — the operator just hoops the right stabilizer under it.
      statsLines.push(
        "Stabilizer: cutaway (over " + CUTAWAY_STITCHES.toLocaleString("en-US") +
          " stitches - tear-away releases under this much thread)"
      );
    }
    for (const line of statsLines) {
      doc.text(line, MARGIN_IN, cursorY);
      cursorY += 0.18;
    }

    cursorY += 0.15;

    // Ordered thread list.
    doc.setFontSize(12);
    doc.setFont(undefined, "bold");
    doc.text("Thread Sequence", MARGIN_IN, cursorY);
    cursorY += 0.22;

    doc.setFontSize(10);
    doc.setFont(undefined, "normal");
    // WHOSE numbering the codes below are. Measured 2026-09-07: picking
    // "Isacord Polyester 40" in the Studio snapped the design's black to
    // that catalog's nearest cone and this sheet printed "1. 1375 Dark
    // Charcoal" — a code with no chart. Every one of the 68 charts numbers
    // independently, so 1375 names a different colour in each of them, and
    // the sheet is what a customer carries to a shop or orders from. The
    // screen said "Chart: Isacord Polyester 40" one panel away.
    //
    // Above the list rather than beside the heading: it qualifies every row
    // under it, and a customer scanning for a code should meet the chart
    // before the first number, not after.
    if (options.chartLabel) {
      doc.text("Chart: " + options.chartLabel, MARGIN_IN, cursorY);
      cursorY += 0.2;
    }
    const swatchSize = 0.16;
    const ROW_H = 0.22;
    for (let i = 0; i < colors.length; i++) {
      // BEFORE the row, not after it. Checking afterwards did both halves of
      // the defect at once: it drew a row that did not fit (at worst past the
      // paper's edge, where it is invisible but still "printed"), and then it
      // added a page for content already drawn -- so a list ending near the
      // bottom always emitted a blank trailing page. A page is now only ever
      // added because there is a row to put on it.
      if (cursorY + ROW_H > PAGE_H_IN - MARGIN_IN) {
        doc.addPage();
        cursorY = MARGIN_IN;
      }
      const color = colors[i];
      const [r, g, b] = rgbCss(color);
      doc.setFillColor(r, g, b);
      doc.rect(MARGIN_IN, cursorY - swatchSize + 0.03, swatchSize, swatchSize, "F");
      const label = (i + 1) + ". " + (color.name || "Color " + (i + 1));
      doc.text(label, MARGIN_IN + swatchSize + 0.12, cursorY);
      cursorY += ROW_H;
    }

    doc.save(options.fileName || "worksheet.pdf");
    return doc;
  }

  return {
    buildWorksheetPDF,
  };
});
