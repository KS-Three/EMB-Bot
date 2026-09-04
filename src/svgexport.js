(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // DST units are 0.1mm; divide by 10 for mm.
  const UNITS_PER_MM = 10;

  function rgb(color) {
    if (!color) return "#000000";
    const c = (v) => {
      const n = Math.max(0, Math.min(255, v | 0));
      return n.toString(16).padStart(2, "0");
    };
    return "#" + c(color.r) + c(color.g) + c(color.b);
  }

  function fmt(n) {
    // Trim to a compact fixed-precision string.
    const r = Math.round(n * 1000) / 1000;
    return String(r);
  }

  function designToSVG(design) {
    const stitches = (design && design.stitches) || [];
    const colors = (design && design.colors) || [];

    // Compute extents in DST units from stitch coordinates.
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
    if (!have) { xMin = xMax = yMin = yMax = 0; }

    const widthMM = (xMax - xMin) / UNITS_PER_MM;
    const heightMM = (yMax - yMin) / UNITS_PER_MM;

    // Screen coords (mm): +X right, Y flipped so +Y(dst)=up maps to top.
    const sx = (x) => (x - xMin) / UNITS_PER_MM;
    const sy = (y) => (yMax - y) / UNITS_PER_MM;

    // Group consecutive `stitch` points into runs. color/jump/trim/end break.
    const paths = [];
    let colorIndex = 0;
    let run = [];
    const flush = () => {
      if (run.length >= 2) {
        paths.push({ points: run, colorIndex });
      }
      run = [];
    };
    for (const st of stitches) {
      const type = st.type || "stitch";
      if (type === "stitch") {
        run.push([sx(st.x | 0), sy(st.y | 0)]);
      } else {
        flush();
        if (type === "color") {
          colorIndex++;
        }
      }
    }
    flush();

    // The thread's laid width in the SVG's millimetre viewBox — the same
    // display constant the Studio preview and the PDF sheet draw with
    // (0.4 mm nominal 40wt); it was 0.35 here until 2026-09-04.
    const THREAD_WIDTH_MM = 0.4;
    const parts = [];
    const vbW = widthMM > 0 ? widthMM : 1;
    const vbH = heightMM > 0 ? heightMM : 1;
    parts.push(
      '<svg xmlns="http://www.w3.org/2000/svg" ' +
        'viewBox="0 0 ' + fmt(vbW) + " " + fmt(vbH) + '" ' +
        'width="' + fmt(vbW) + 'mm" height="' + fmt(vbH) + 'mm">'
    );

    for (const p of paths) {
      const color = colors[p.colorIndex] || colors[0];
      const pts = p.points.map((pt) => fmt(pt[0]) + "," + fmt(pt[1])).join(" ");
      parts.push(
        '<polyline fill="none" stroke="' + rgb(color) +
          '" stroke-width="' + THREAD_WIDTH_MM + '" stroke-linejoin="round" stroke-linecap="round" ' +
          'points="' + pts + '"/>'
      );
    }

    parts.push("</svg>");
    return parts.join("\n");
  }

  return { designToSVG };
});
