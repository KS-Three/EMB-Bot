(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // DST units are 0.1mm; divide by 10 for mm.
  const UNITS_PER_MM = 10;

  function rgb(color) {
    if (!color) return "rgb(0,0,0)";
    const c = (v) => Math.max(0, Math.min(255, v | 0));
    return "rgb(" + c(color.r) + "," + c(color.g) + "," + c(color.b) + ")";
  }

  function extentsOf(stitches) {
    let xMin = 0, xMax = 0, yMin = 0, yMax = 0;
    let have = false;
    for (const st of stitches) {
      const x = st.x | 0;
      const y = st.y | 0;
      if (!have) { xMin = xMax = x; yMin = yMax = y; have = true; }
      else {
        if (x < xMin) xMin = x;
        if (x > xMax) xMax = x;
        if (y < yMin) yMin = y;
        if (y > yMax) yMax = y;
      }
    }
    return { xMin, xMax, yMin, yMax, have };
  }

  // Build a mapper from DST units -> canvas px, fitting `extents` (plus any
  // extra box extents) into (canvasW - 2*padding) x (canvasH - 2*padding),
  // preserving aspect ratio, centered, with Y flipped (screen Y grows down).
  function buildMapper(canvasW, canvasH, padding, extents) {
    const { xMin, xMax, yMin, yMax } = extents;
    const spanX = Math.max(1, xMax - xMin);
    const spanY = Math.max(1, yMax - yMin);

    const availW = Math.max(1, canvasW - 2 * padding);
    const availH = Math.max(1, canvasH - 2 * padding);

    const scale = Math.min(availW / spanX, availH / spanY);

    const drawW = spanX * scale;
    const drawH = spanY * scale;
    const offsetX = (canvasW - drawW) / 2;
    const offsetY = (canvasH - drawH) / 2;

    const cx = (x) => offsetX + (x - xMin) * scale;
    const cy = (y) => offsetY + (yMax - y) * scale; // flip: +Y(dst)=up -> smaller screen-y

    return { cx, cy, scale };
  }

  function renderStitches(canvas, design, opts) {
    const options = opts || {};
    const padding = options.padding === undefined ? 20 : options.padding;
    const showBox = options.showBox || null;

    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const stitches = (design && design.stitches) || [];
    const colors = (design && design.colors) || [];

    const stitchExtents = extentsOf(stitches);

    // Include the garment box (in DST units) in the extents used for fitting,
    // so the box is always visible alongside the stitches.
    let extents = stitchExtents;
    if (showBox && showBox.widthMM && showBox.heightMM) {
      const boxHalfW = (showBox.widthMM * UNITS_PER_MM) / 2;
      const boxHalfH = (showBox.heightMM * UNITS_PER_MM) / 2;
      const bXMin = -boxHalfW, bXMax = boxHalfW, bYMin = -boxHalfH, bYMax = boxHalfH;
      if (extents.have) {
        extents = {
          xMin: Math.min(extents.xMin, bXMin),
          xMax: Math.max(extents.xMax, bXMax),
          yMin: Math.min(extents.yMin, bYMin),
          yMax: Math.max(extents.yMax, bYMax),
          have: true,
        };
      } else {
        extents = { xMin: bXMin, xMax: bXMax, yMin: bYMin, yMax: bYMax, have: true };
      }
    }

    if (!extents.have) {
      // Nothing to draw at all (no stitches, no box). Just leave canvas clear.
      extents = { xMin: -1, xMax: 1, yMin: -1, yMax: 1, have: true };
    }

    const mapper = buildMapper(canvas.width, canvas.height, padding, extents);

    // Garment placement box, drawn behind the stitches.
    if (showBox && showBox.widthMM && showBox.heightMM) {
      const boxHalfW = (showBox.widthMM * UNITS_PER_MM) / 2;
      const boxHalfH = (showBox.heightMM * UNITS_PER_MM) / 2;
      const x0 = mapper.cx(-boxHalfW);
      const y0 = mapper.cy(boxHalfH);
      const x1 = mapper.cx(boxHalfW);
      const y1 = mapper.cy(-boxHalfH);
      ctx.save();
      ctx.strokeStyle = "rgba(120,120,120,0.6)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
      ctx.restore();
    }

    // The thread's laid width — the same display constant the Studio preview
    // (`app/src/lib/preview.js` THREAD_WIDTH_MM) and the Python render
    // (`stitchviz.THREAD_MM`) draw with, scaled to this canvas so the sheet
    // shows the coverage the cloth gets. Until 2026-09-04 every stitch here
    // was one pixel wide whatever the scale, so the PDF sheet drew a 0.15 mm
    // fill as sparse hatching at print size. `mapper.scale` is px per DST
    // unit (0.1 mm); a 1 px floor keeps a tiny thumbnail legible.
    const THREAD_WIDTH_MM = 0.4;
    const lw = Math.max(1, THREAD_WIDTH_MM * UNITS_PER_MM * mapper.scale);

    // Walk stitches, drawing line segments per run, per current color.
    let colorIndex = 0;
    let havePoint = false;
    let prevPx = 0, prevPy = 0;

    const currentColor = () => colors[colorIndex] || colors[0] || { r: 0, g: 0, b: 0 };

    for (const st of stitches) {
      const type = st.type || "stitch";
      if (type === "stitch") {
        const px = mapper.cx(st.x | 0);
        const py = mapper.cy(st.y | 0);
        if (havePoint) {
          const strokeColor = rgb(currentColor());
          // Base thread line.
          ctx.strokeStyle = strokeColor;
          ctx.lineWidth = lw;
          ctx.lineCap = "round";
          ctx.beginPath();
          ctx.moveTo(prevPx, prevPy);
          ctx.lineTo(px, py);
          ctx.stroke();
          // Subtle highlight for a thread-like sheen.
          ctx.save();
          ctx.strokeStyle = "rgba(255,255,255,0.25)";
          ctx.lineWidth = lw * 0.4;
          ctx.beginPath();
          ctx.moveTo(prevPx, prevPy);
          ctx.lineTo(px, py);
          ctx.stroke();
          ctx.restore();
        }
        prevPx = px;
        prevPy = py;
        havePoint = true;
      } else {
        // jump/trim/color/end: break the current run, no visible segment.
        havePoint = false;
        if (type === "color") {
          colorIndex++;
        }
      }
    }

    ctx.restore();
  }

  function designToPNGBlob(design, cb) {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 800;
    renderStitches(canvas, design, {});
    canvas.toBlob(cb, "image/png");
  }

  return {
    renderStitches,
    designToPNGBlob,
  };
});
