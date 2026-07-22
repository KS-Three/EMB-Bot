/* EMB Bot — app wiring. Ties the EMB modules to the DOM. Browser-only:
 * all real work runs inside DOMContentLoaded, so requiring this file in Node
 * (where `document`/`window` are absent) is a harmless no-op. */
(function () {
  "use strict";

  // Node-safety: if there's no document, do nothing. (Lets `require` not crash.)
  if (typeof document === "undefined") return;

  var EMB = (typeof window !== "undefined" ? window : globalThis).EMB || {};

  // --- Working-resolution + physical-size conventions ---------------------
  var WORK_MAX_PX = 480; // flatten working resolution (longest side)
  var NOMINAL_LONG_MM = 50; // pre-fit physical size of the source art long side
  var TEXT_SIZE_PX = 200; // glyph size used for tracing text
  var SIMPLIFY_TOL = 1.6; // Douglas-Peucker tolerance (px)
  var MODE_FILTER_ITERS = 2; // majority-smoothing passes over flattened indices
  var ABSORB_SHARE = 0.0005; // absorb color patches smaller than round(w*h*this) px
  var DESPECKLE_SHARE = 0.0004; // drop traced shapes below w*h*this (px^2)
  var MAX_SHAPES_PER_COLOR = 60; // cap shapes per color (largest kept first)
  var ALPHA_CUTOFF = 128; // pixels with alpha < this become transparent

  // --- Module-level state --------------------------------------------------
  var currentDesign = null;
  var currentGarment = null;
  var loadedImage = null; // HTMLImageElement of the uploaded file

  // Flattened-art state (image mode). Recomputed on load / Colors change /
  // Remove-background change; mutated in place by manual merges. Generate
  // consumes this exactly, so stitches match the preview.
  //   { palette:[[r,g,b],...], indices:Uint8Array(255=transparent), w, h, srcW, srcH }
  var flatState = null;
  var selectedSwatches = {}; // palette index -> true, cleared on any recompute

  // --- DOM refs (filled on DOMContentLoaded) ------------------------------
  var el = {};

  function $(id) {
    return document.getElementById(id);
  }

  // Absolute polygon area (px^2). Thin wrapper so region/hole filtering reads
  // cleanly; EMB.polygonArea always returns a non-negative area.
  function area(poly) {
    return EMB.polygonArea(poly);
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

  // --- Flatten pipeline (image mode) --------------------------------------

  // Draw `img` to an offscreen canvas (longest side capped at maxPx, or natural
  // size when maxPx is falsy) and return { rgba, w, h }. Pixels with alpha
  // below ALPHA_CUTOFF are forced fully transparent (alpha 0) so downstream
  // medianCut / flatten treat them as background.
  function prepRGBA(img, maxPx) {
    var longest = Math.max(img.width, img.height) || 1;
    var scale = maxPx ? Math.min(1, maxPx / longest) : 1;
    var w = Math.max(1, Math.round(img.width * scale));
    var h = Math.max(1, Math.round(img.height * scale));

    var cv = document.createElement("canvas");
    cv.width = w;
    cv.height = h;
    var ctx = cv.getContext("2d");
    ctx.drawImage(img, 0, 0, w, h);

    var rgba = ctx.getImageData(0, 0, w, h).data; // Uint8ClampedArray
    for (var i = 3; i < rgba.length; i += 4) {
      if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
    }
    return { rgba: rgba, w: w, h: h };
  }

  // Recompute the AUTO flattened art from the loaded image at the current
  // Colors / Remove-background settings and store it in flatState. Any manual
  // merges are discarded (spec'd). Re-renders the preview + swatch bar.
  function recomputeFlatten() {
    if (!loadedImage) { flatState = null; return; }
    var prep = prepRGBA(loadedImage, WORK_MAX_PX);
    var rgba = prep.rgba, w = prep.w, h = prep.h;
    if (el.removeBg.checked) rgba = EMB.knockoutBackground(rgba, w, h, {});

    var nColors = parseInt(el.colors.value, 10);
    var quant = EMB.medianCut(rgba, nColors); // {palette, indices}
    var indices = EMB.modeFilter(quant.indices, w, h, { iterations: MODE_FILTER_ITERS });
    var minPx = Math.round(w * h * ABSORB_SHARE);
    indices = EMB.absorbSmallRegions(indices, w, h, minPx);

    flatState = {
      palette: quant.palette.map(function (c) { return c.slice(); }),
      indices: indices,
      w: w,
      h: h,
      srcW: loadedImage.width,
      srcH: loadedImage.height,
    };
    selectedSwatches = {};
    renderFlatten();
  }

  // Paint the flattened indices onto the preview canvas, upscaled with nearest-
  // neighbor (imageSmoothingEnabled=false) so the flat art reads crisply.
  function renderFlatPreview() {
    var cv = el.flatPreview;
    if (!cv) return;
    var ctx = cv.getContext("2d");
    if (!flatState) {
      cv.width = 1;
      cv.height = 1;
      ctx.clearRect(0, 0, cv.width, cv.height);
      return;
    }
    var w = flatState.w, h = flatState.h;
    var off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    var rgba = EMB.indicesToRGBA(flatState.indices, flatState.palette, w, h);
    off.getContext("2d").putImageData(new ImageData(rgba, w, h), 0, 0);

    // Integer upscale for small art; large art stays 1:1 and is capped by CSS.
    var scale = Math.max(1, Math.round(360 / Math.max(w, h)));
    cv.width = w * scale;
    cv.height = h * scale;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.drawImage(off, 0, 0, cv.width, cv.height);
  }

  // One clickable chip per palette entry: color + % of opaque pixels. Click
  // toggles selection (multi-select) for Merge.
  function renderSwatches() {
    var bar = el.flatSwatches;
    if (!bar) return;
    bar.innerHTML = "";
    if (!flatState) {
      var hint = document.createElement("span");
      hint.className = "flat-hint";
      hint.textContent = "Load an image to see the flattened palette.";
      bar.appendChild(hint);
      return;
    }
    var shares = EMB.paletteShares(flatState.indices, flatState.palette.length);
    flatState.palette.forEach(function (c, i) {
      var sw = document.createElement("button");
      sw.type = "button";
      sw.className = "flat-swatch" + (selectedSwatches[i] ? " selected" : "");
      var chip = document.createElement("span");
      chip.className = "chip";
      chip.style.background = "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
      var pct = document.createElement("span");
      pct.className = "pct";
      pct.textContent = (shares[i] * 100).toFixed(1) + "%";
      sw.appendChild(chip);
      sw.appendChild(pct);
      sw.addEventListener("click", function () {
        if (selectedSwatches[i]) delete selectedSwatches[i];
        else selectedSwatches[i] = true;
        sw.classList.toggle("selected");
      });
      bar.appendChild(sw);
    });
  }

  function renderFlatten() {
    renderFlatPreview();
    renderSwatches();
  }

  // Merge every selected swatch into one population-weighted color, then re-run
  // small-region absorb so the merge doesn't leave sub-threshold specks.
  function mergeSelected() {
    if (!flatState) { setStatus("Load an image first.", true); return; }
    var sel = Object.keys(selectedSwatches).map(Number);
    if (sel.length < 2) {
      setStatus("Select at least two swatches to merge.", true);
      return;
    }
    var res = EMB.mergeColors(flatState.palette, flatState.indices, sel);
    var minPx = Math.round(flatState.w * flatState.h * ABSORB_SHARE);
    var indices = EMB.absorbSmallRegions(res.indices, flatState.w, flatState.h, minPx);
    flatState.palette = res.palette;
    flatState.indices = indices;
    selectedSwatches = {};
    renderFlatten();
    setStatus("Merged " + sel.length + " colors → " + flatState.palette.length + " thread color(s).");
  }

  function resetFlatten() {
    if (!loadedImage) { setStatus("Load an image first.", true); return; }
    recomputeFlatten();
    setStatus("Colors reset to auto flatten (" + (flatState ? flatState.palette.length : 0) + ").");
  }

  // Export the flattened art at ORIGINAL resolution: map every opaque source
  // pixel to the CURRENT final palette by nearest RGB, one modeFilter pass to
  // knock out lone speckles, then encode a transparent-background PNG.
  function downloadFlatPNG() {
    if (!flatState) { setStatus("Load an image first.", true); return; }
    setStatus("Rendering full-resolution flat PNG…");
    // Defer so the status text paints before the (possibly heavy) work.
    setTimeout(function () {
      try {
        var prep = prepRGBA(loadedImage, null); // natural size
        var rgba = prep.rgba, w = prep.w, h = prep.h;
        if (el.removeBg.checked) rgba = EMB.knockoutBackground(rgba, w, h, {});

        var pal = flatState.palette;
        var n = w * h;
        var idx = new Uint8Array(n).fill(255);
        for (var i = 0; i < n; i++) {
          var o = i * 4;
          if (rgba[o + 3] === 0) continue; // transparent stays transparent
          var r = rgba[o], g = rgba[o + 1], b = rgba[o + 2];
          var best = 0, bestDist = Infinity;
          for (var k = 0; k < pal.length; k++) {
            var dr = r - pal[k][0], dg = g - pal[k][1], db = b - pal[k][2];
            var d = dr * dr + dg * dg + db * db;
            if (d < bestDist) { bestDist = d; best = k; }
          }
          idx[i] = best;
        }
        idx = EMB.modeFilter(idx, w, h, { iterations: 1 });

        var out = EMB.indicesToRGBA(idx, pal, w, h);
        var cv = document.createElement("canvas");
        cv.width = w;
        cv.height = h;
        cv.getContext("2d").putImageData(new ImageData(out, w, h), 0, 0);
        cv.toBlob(function (blob) {
          if (!blob) { setStatus("Flat PNG export failed.", true); return; }
          try {
            triggerDownload(blob, "flat-art.png");
            setStatus("Downloaded flat-art.png (" + w + "×" + h + ").");
          } catch (e) {
            setStatus("Download failed: " + e.message, true);
            // eslint-disable-next-line no-console
            console.error(e);
          }
        }, "image/png");
      } catch (e) {
        setStatus("Flat PNG export failed: " + e.message, true);
        // eslint-disable-next-line no-console
        console.error(e);
      }
    }, 20);
  }

  // --- IMAGE pipeline: flatState -> ColorRegion[] -------------------------
  // Build per-color masks from the CURRENT flattened indices and trace them,
  // so the generated stitches match the flatten preview exactly.
  function imageToRegions() {
    var w = flatState.w, h = flatState.h;
    var palette = flatState.palette, indices = flatState.indices;

    var despeckleMin = w * h * DESPECKLE_SHARE;    // area-relative per-shape despeckle
    var holeMin = Math.max(6, despeckleMin * 0.3); // keep smaller holes (counters)

    var regions = [];
    for (var ci = 0; ci < palette.length; ci++) {
      var mask = new Uint8Array(w * h);
      for (var p = 0; p < indices.length; p++) {
        if (indices[p] === ci) mask[p] = 1; // 255 = transparent -> skipped
      }
      // Hole-aware tracing: each blob -> { outer, holes[] }. Simplify every
      // ring, drop specks (outer) and pinholes (holes), then keep the largest
      // shapes up to the per-color cap.
      var shapes = EMB.traceRegions(mask, w, h)
        .map(function (s) {
          return {
            outer: EMB.simplify(s.outer, SIMPLIFY_TOL),
            holes: s.holes
              .map(function (hh) { return EMB.simplify(hh, SIMPLIFY_TOL); })
              .filter(function (hh) { return hh.length >= 4 && area(hh) > holeMin; }),
          };
        })
        .filter(function (s) { return s.outer.length >= 4 && area(s.outer) > despeckleMin; });
      shapes.sort(function (a, b) { return area(b.outer) - area(a.outer); });
      if (shapes.length > MAX_SHAPES_PER_COLOR) shapes = shapes.slice(0, MAX_SHAPES_PER_COLOR);
      if (shapes.length === 0) continue; // no geometry for this color
      regions.push({ rgb: palette[ci], shapes: shapes });
    }

    // Map the working image long side to NOMINAL_LONG_MM; fit handles final size.
    var pxPerMm = Math.max(w, h) / NOMINAL_LONG_MM;
    return { regions: regions, pxPerMm: pxPerMm };
  }

  // --- TEXT pipeline: text -> ColorRegion[] -------------------------------
  function textToRegionsPipeline(font, text) {
    // textToRegions returns a single black region as a flat ring list
    // ([{ rgb, polygons }]). Measure pxPerMm from those rings (unchanged),
    // then group the rings into hole-aware shapes (outer + counters) for the
    // quality engine.
    var regions = EMB.textToRegions(font, text, { sizePx: TEXT_SIZE_PX });
    var pxPerMm = regionsLongSidePx(regions) / NOMINAL_LONG_MM;
    var rings = (regions[0] && regions[0].polygons) || [];
    var shapes = EMB.groupRingsIntoShapes(rings, 4);
    return { regions: [{ rgb: [0, 0, 0], shapes: shapes }], pxPerMm: pxPerMm };
  }

  // --- Read current control values ----------------------------------------
  function readOpts() {
    var garment = EMB.getGarment(el.garment.value);
    var densityMm = parseFloat(el.density.value);
    var outline = el.outline.checked;
    var underlay = el.underlay.checked;
    var nColors = parseInt(el.colors.value, 10);
    return {
      garment: garment,
      densityMm: densityMm,
      outline: outline,
      underlay: underlay,
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
        var design = EMB.buildQualityDesign(regionData.regions, {
          garment: opts.garment,
          pxPerMm: regionData.pxPerMm,
          densityMm: opts.densityMm,
          satinMaxWidthMm: 3.0,
          underlay: opts.underlay,
          outline: opts.outline,
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
      if (!flatState) {
        setStatus("Load an image first.", true);
        return;
      }
      try {
        buildFromRegions(imageToRegions());
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
    if (el.flatPanel) el.flatPanel.style.display = mode === "image" ? "block" : "none";
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
    el.flatPanel = $("flat-panel");
    el.flatPreview = $("flat-preview");
    el.flatSwatches = $("flat-swatches");
    el.text = $("text-input");
    el.font = $("font");
    el.garment = $("garment");
    el.format = $("format");
    el.colors = $("colors");
    el.colorsVal = $("colors-val");
    el.density = $("density");
    el.densityVal = $("density-val");
    el.outline = $("outline");
    el.underlay = $("underlay");

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
        setStatus("Flattening image (" + img.width + "×" + img.height + "px)…");
        try {
          recomputeFlatten();
          setStatus("Image loaded (" + img.width + "×" + img.height + "px). Review the flattened art, then click Generate.");
        } catch (e) {
          setStatus("Couldn't flatten that image: " + e.message, true);
          // eslint-disable-next-line no-console
          console.error(e);
        }
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        setStatus("Couldn't read that image file.", true);
      };
      img.src = url;
    });

    // Remove-background toggle re-runs the auto flatten.
    el.removeBg.addEventListener("change", function () {
      if (loadedImage) recomputeFlatten();
    });

    // Slider labels. Colors change re-runs the auto flatten (on release, so we
    // don't re-quantize on every tick of the drag).
    el.colors.addEventListener("input", function () {
      el.colorsVal.textContent = el.colors.value;
    });
    el.colors.addEventListener("change", function () {
      if (loadedImage) recomputeFlatten();
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

    // Flatten panel buttons
    $("btn-merge").addEventListener("click", mergeSelected);
    $("btn-reset-colors").addEventListener("click", resetFlatten);
    $("btn-flat-png").addEventListener("click", downloadFlatPNG);
    renderFlatten(); // draw the "load an image" placeholder state

    checkCDN();
    setStatus("Ready. Pick a mode, set options, and click Generate.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
