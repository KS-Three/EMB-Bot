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

    // Rendered stitch simulation image.
    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 900;
    renderStitches(canvas, design, {
      padding: 20,
      showBox: options.garmentBox || null,
    });
    const dataUrl = canvas.toDataURL("image/png");

    const imgSizeIn = PAGE_W_IN - 2 * MARGIN_IN;
    const imgY = cursorY + 0.1;
    doc.addImage(dataUrl, "PNG", MARGIN_IN, imgY, imgSizeIn, imgSizeIn);
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
      "Stitch count: " + stitchCount,
      "Color count: " + colorCount,
    ];
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
    const swatchSize = 0.16;
    for (let i = 0; i < colors.length; i++) {
      const color = colors[i];
      const [r, g, b] = rgbCss(color);
      doc.setFillColor(r, g, b);
      doc.rect(MARGIN_IN, cursorY - swatchSize + 0.03, swatchSize, swatchSize, "F");
      const label = (i + 1) + ". " + (color.name || "Color " + (i + 1));
      doc.text(label, MARGIN_IN + swatchSize + 0.12, cursorY);
      cursorY += 0.22;
      if (cursorY > PAGE_H_IN - MARGIN_IN) {
        doc.addPage();
        cursorY = MARGIN_IN;
      }
    }

    doc.save(options.fileName || "worksheet.pdf");
    return doc;
  }

  return {
    buildWorksheetPDF,
  };
});
