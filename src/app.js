/* EMB Bot — app wiring. Ties the EMB modules to the DOM. Browser-only:
 * all real work runs inside DOMContentLoaded, so requiring this file in Node
 * (where `document`/`window` are absent) is a harmless no-op. */
(function () {
  "use strict";

  // Node-safety: if there's no document, do nothing. (Lets `require` not crash.)
  if (typeof document === "undefined") return;

  var EMB = (typeof window !== "undefined" ? window : globalThis).EMB || {};

  // --- Working-resolution + physical-size conventions ---------------------
  var WORK_MAX_PX = 400; // cap the longest side of the working image
  var NOMINAL_LONG_MM = 50; // pre-fit physical size of the source art long side
  var TEXT_SIZE_PX = 200; // glyph size used for tracing text
  var SIMPLIFY_TOL = 1.5; // Douglas-Peucker tolerance (px)
  var DESPECKLE_AREA = 6; // drop polygons smaller than this (px^2)

  // --- Module-level state --------------------------------------------------
  var currentDesign = null;
  var currentGarment = null;
  var loadedImage = null; // HTMLImageElement of the uploaded file

  // --- DOM refs (filled on DOMContentLoaded) ------------------------------
  var el = {};

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg, isError) {
    if (!el.status) return;
    el.status.textContent = msg || "";
    el.status.className = "status" + (isError ? " status-error" : "");
  }

  // --- Bounding-box helper over ColorRegion[] -----------------------------
  function regionsLongSidePx(regions) {
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (var r = 0; r < regions.length; r++) {
      var polys = regions[r].polygons || [];
      for (var p = 0; p < polys.length; p++) {
        var poly = polys[p];
        for (var i = 0; i < poly.length; i++) {
          var pt = poly[i];
          if (pt.x < minX) minX = pt.x;
          if (pt.x > maxX) maxX = pt.x;
          if (pt.y < minY) minY = pt.y;
          if (pt.y > maxY) maxY = pt.y;
        }
      }
    }
    if (!isFinite(minX)) return 1;
    return Math.max(maxX - minX, maxY - minY) || 1;
  }

  // --- IMAGE pipeline: File -> ColorRegion[] ------------------------------
  // Returns { regions, pxPerMm }.
  function imageToRegions(img, nColors, removeBg) {
    // Draw the image to an offscreen canvas, capped at WORK_MAX_PX long side.
    var longest = Math.max(img.width, img.height) || 1;
    var scale = Math.min(1, WORK_MAX_PX / longest);
    var w = Math.max(1, Math.round(img.width * scale));
    var h = Math.max(1, Math.round(img.height * scale));

    var cv = document.createElement("canvas");
    cv.width = w;
    cv.height = h;
    var ctx = cv.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);

    var rgba = ctx.getImageData(0, 0, w, h).data; // Uint8ClampedArray
    if (removeBg) {
      rgba = EMB.knockoutBackground(rgba, w, h, {});
    }

    var quant = EMB.medianCut(rgba, nColors); // {palette, indices}
    var palette = quant.palette;
    var indices = quant.indices;

    var regions = [];
    for (var ci = 0; ci < palette.length; ci++) {
      var mask = new Uint8Array(w * h);
      for (var p = 0; p < indices.length; p++) {
        if (indices[p] === ci) mask[p] = 1; // 255 = transparent -> skipped
      }
      var contours = EMB.traceContours(mask, w, h);
      var polygons = [];
      for (var c = 0; c < contours.length; c++) {
        var simplified = EMB.simplify(contours[c], SIMPLIFY_TOL);
        if (EMB.polygonArea(simplified) < DESPECKLE_AREA) continue;
        polygons.push(simplified);
      }
      if (polygons.length === 0) continue; // no geometry for this color
      regions.push({ rgb: palette[ci], polygons: polygons });
    }

    // Map the working image long side to NOMINAL_LONG_MM; fit handles final size.
    var pxPerMm = Math.max(w, h) / NOMINAL_LONG_MM;
    return { regions: regions, pxPerMm: pxPerMm };
  }

  // --- TEXT pipeline: text -> ColorRegion[] -------------------------------
  function textToRegionsPipeline(font, text) {
    var regions = EMB.textToRegions(font, text, { sizePx: TEXT_SIZE_PX });
    var pxPerMm = regionsLongSidePx(regions) / NOMINAL_LONG_MM;
    return { regions: regions, pxPerMm: pxPerMm };
  }

  // --- Read current control values ----------------------------------------
  function readOpts() {
    var garment = EMB.getGarment(el.garment.value);
    var densityMm = parseFloat(el.density.value);
    var outline = el.outline.checked;
    var nColors = parseInt(el.colors.value, 10);
    return {
      garment: garment,
      densityMm: densityMm,
      outline: outline,
      nColors: nColors,
    };
  }

  // --- Generate ------------------------------------------------------------
  function generate() {
    setStatus("Generating…");
    var opts;
    try {
      opts = readOpts();
    } catch (e) {
      setStatus("Bad options: " + e.message, true);
      return;
    }

    var mode = getMode();

    var buildFromRegions = function (regionData) {
      try {
        if (!regionData.regions || regionData.regions.length === 0) {
          setStatus("No shapes found to stitch. Try a different image/text or fewer colors.", true);
          return;
        }
        var design = EMB.buildDesign(regionData.regions, {
          garment: opts.garment,
          densityMm: opts.densityMm,
          outline: opts.outline,
          pxPerMm: regionData.pxPerMm,
        });
        currentDesign = design;
        currentGarment = opts.garment;
        renderPreview(design, opts.garment);
        updateStats(design, opts.garment);
        setStatus("Done.");
      } catch (e) {
        setStatus("Generate failed: " + e.message, true);
        // eslint-disable-next-line no-console
        console.error(e);
      }
    };

    if (mode === "text") {
      var text = (el.text.value || "").trim();
      if (!text) {
        setStatus("Type some text first.", true);
        return;
      }
      var fontUrl = el.font.value;
      setStatus("Loading font…");
      EMB.loadFont(fontUrl)
        .then(function (font) {
          // Font loaded successfully: from here on, any failure is a
          // region-building/generate problem, NOT a font-load problem, so it
          // must be reported separately rather than falling into the
          // font-load .catch() below.
          var regionData;
          try {
            regionData = textToRegionsPipeline(font, text);
          } catch (e) {
            setStatus("Couldn't generate design: " + e.message, true);
            // eslint-disable-next-line no-console
            console.error(e);
            return;
          }
          buildFromRegions(regionData);
        })
        .catch(function (e) {
          setStatus("Font load failed: " + e.message, true);
          // eslint-disable-next-line no-console
          console.error(e);
        });
    } else {
      if (!loadedImage) {
        setStatus("Choose an image file first.", true);
        return;
      }
      try {
        buildFromRegions(imageToRegions(loadedImage, opts.nColors, el.removeBg.checked));
      } catch (e) {
        setStatus("Image processing failed: " + e.message, true);
        // eslint-disable-next-line no-console
        console.error(e);
      }
    }
  }

  function renderPreview(design, garment) {
    EMB.renderStitches(el.canvas, design, {
      showBox: {
        widthMM: EMB.inToMm(garment.widthIn),
        heightMM: EMB.inToMm(garment.heightIn),
      },
    });
  }

  function updateStats(design, garment) {
    var wIn = EMB.mmToInch(design.widthMM);
    var hIn = EMB.mmToInch(design.heightMM);
    el.statStitches.textContent = String(design.stitchCount);
    el.statColors.textContent = String(design.colorCount);
    el.statSize.textContent =
      design.widthMM.toFixed(1) + " × " + design.heightMM.toFixed(1) + " mm" +
      "  (" + wIn.toFixed(2) + " × " + hIn.toFixed(2) + " in)";

    if (EMB.exceedsHoop(design.widthMM, design.heightMM)) {
      el.hoopWarn.textContent =
        "Large design: " + design.widthMM.toFixed(1) + " × " + design.heightMM.toFixed(1) + " mm" +
        " (" + wIn.toFixed(2) + " × " + hIn.toFixed(2) + " in). " +
        "Make sure your hoop/machine supports this size.";
      el.hoopWarn.style.display = "block";
    } else {
      el.hoopWarn.style.display = "none";
    }
  }

  // --- Download ------------------------------------------------------------
  function triggerDownload(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Revoke a tick later so the download has grabbed the URL.
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  function download() {
    if (!currentDesign) {
      setStatus("Generate a design first.", true);
      return;
    }
    var fmt = el.format.value;
    try {
      if (fmt === "dst") {
        triggerDownload(new Blob([EMB.encodeDST(currentDesign)], { type: "application/octet-stream" }), "embbot.dst");
      } else if (fmt === "exp") {
        triggerDownload(new Blob([EMB.encodeEXP(currentDesign)], { type: "application/octet-stream" }), "embbot.exp");
      } else if (fmt === "pes") {
        triggerDownload(new Blob([EMB.encodePES(currentDesign)], { type: "application/octet-stream" }), "embbot.pes");
      } else if (fmt === "svg") {
        triggerDownload(new Blob([EMB.designToSVG(currentDesign)], { type: "image/svg+xml" }), "embbot.svg");
      } else if (fmt === "png") {
        EMB.designToPNGBlob(currentDesign, function (blob) {
          if (!blob) {
            setStatus("PNG export failed.", true);
            return;
          }
          try {
            triggerDownload(blob, "embbot.png");
            setStatus("Downloaded embbot.png");
          } catch (e) {
            setStatus("Download failed: " + e.message, true);
            // eslint-disable-next-line no-console
            console.error(e);
          }
        });
        return; // async; status set in callback
      } else {
        setStatus("Unknown format: " + fmt, true);
        return;
      }
      setStatus("Downloaded embbot." + fmt);
    } catch (e) {
      setStatus("Download failed: " + e.message, true);
      // eslint-disable-next-line no-console
      console.error(e);
    }
  }

  // --- Export PDF ----------------------------------------------------------
  function exportPDF() {
    if (!currentDesign) {
      setStatus("Generate a design first.", true);
      return;
    }
    try {
      EMB.buildWorksheetPDF(currentDesign, {
        garmentLabel: currentGarment ? currentGarment.label : "",
        fileName: "embbot-worksheet.pdf",
        garmentBox: currentGarment
          ? {
              widthMM: EMB.inToMm(currentGarment.widthIn),
              heightMM: EMB.inToMm(currentGarment.heightIn),
            }
          : null,
      });
      setStatus("PDF worksheet exported.");
    } catch (e) {
      setStatus("PDF export failed: " + e.message, true);
      // eslint-disable-next-line no-console
      console.error(e);
    }
  }

  // --- Mode toggle ---------------------------------------------------------
  function getMode() {
    return el.modeText.checked ? "text" : "image";
  }

  function applyMode() {
    var mode = getMode();
    el.imageControls.style.display = mode === "image" ? "block" : "none";
    el.textControls.style.display = mode === "text" ? "block" : "none";
  }

  // --- Setup ---------------------------------------------------------------
  function populateSelects() {
    // Garments
    for (var i = 0; i < EMB.GARMENTS.length; i++) {
      var g = EMB.GARMENTS[i];
      var o = document.createElement("option");
      o.value = g.id;
      o.textContent = g.label;
      el.garment.appendChild(o);
    }
    el.garment.value = "left_chest";

    // Fonts
    for (var f = 0; f < EMB.FONTS.length; f++) {
      var font = EMB.FONTS[f];
      var fo = document.createElement("option");
      fo.value = font.url;
      fo.textContent = font.family;
      el.font.appendChild(fo);
    }
  }

  function checkCDN() {
    var ok = typeof window !== "undefined" && window.opentype && window.jspdf;
    if (!ok && el.cdnBanner) {
      el.cdnBanner.style.display = "block";
    }
    return ok;
  }

  function wire() {
    el.canvas = $("preview");
    el.status = $("status");
    el.cdnBanner = $("cdn-banner");
    el.hoopWarn = $("hoop-warning");

    el.modeImage = $("mode-image");
    el.modeText = $("mode-text");
    el.imageControls = $("image-controls");
    el.textControls = $("text-controls");

    el.file = $("file");
    el.removeBg = $("remove-bg");
    el.text = $("text-input");
    el.font = $("font");
    el.garment = $("garment");
    el.format = $("format");
    el.colors = $("colors");
    el.colorsVal = $("colors-val");
    el.density = $("density");
    el.densityVal = $("density-val");
    el.outline = $("outline");

    el.statStitches = $("stat-stitches");
    el.statColors = $("stat-colors");
    el.statSize = $("stat-size");

    populateSelects();

    // Mode toggle
    el.modeImage.addEventListener("change", applyMode);
    el.modeText.addEventListener("change", applyMode);
    applyMode();

    // File upload
    el.file.addEventListener("change", function () {
      var file = el.file.files && el.file.files[0];
      if (!file) return;
      var img = new Image();
      var url = URL.createObjectURL(file);
      img.onload = function () {
        loadedImage = img;
        URL.revokeObjectURL(url);
        setStatus("Image loaded (" + img.width + "×" + img.height + "px). Click Generate.");
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        setStatus("Couldn't read that image file.", true);
      };
      img.src = url;
    });

    // Slider labels
    el.colors.addEventListener("input", function () {
      el.colorsVal.textContent = el.colors.value;
    });
    el.colorsVal.textContent = el.colors.value;

    el.density.addEventListener("input", function () {
      el.densityVal.textContent = parseFloat(el.density.value).toFixed(2) + " mm";
    });
    el.densityVal.textContent = parseFloat(el.density.value).toFixed(2) + " mm";

    // Buttons
    $("btn-generate").addEventListener("click", generate);
    $("btn-download").addEventListener("click", download);
    $("btn-pdf").addEventListener("click", exportPDF);

    checkCDN();
    setStatus("Ready. Pick a mode, set options, and click Generate.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
