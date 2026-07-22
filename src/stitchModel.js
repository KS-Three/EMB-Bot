const _req = typeof module !== "undefined" && module.exports;
const units = _req
  ? require("./units.js")
  : (typeof globalThis !== "undefined" ? globalThis : this).EMB;
const garments = _req
  ? require("./garments.js")
  : (typeof globalThis !== "undefined" ? globalThis : this).EMB;
const fillmod = _req
  ? require("./fill.js")
  : (typeof globalThis !== "undefined" ? globalThis : this).EMB;

(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const { DST_UNITS_PER_MM } = units;
  const { fitScale } = garments;
  const { tatamiFill, runningOutline } = fillmod;

  // Assemble color regions (pixel coords) into a final Design.
  // colorRegions: Array<{ rgb:[r,g,b], polygons: Array<Array<{x,y}>> }>
  // opts: { garment, densityMm, outline, maxStitchMm=4.0, outlineStitchMm=1.8, pxPerMm }
  function buildDesign(colorRegions, opts) {
    const pxPerMm = opts.pxPerMm;
    const densityMm = opts.densityMm;
    const outline = !!opts.outline;
    const maxStitchMm = opts.maxStitchMm != null ? opts.maxStitchMm : 4.0;
    const outlineStitchMm =
      opts.outlineStitchMm != null ? opts.outlineStitchMm : 1.8;
    const garment = opts.garment;

    // 1. Overall bbox across all polygons in all regions (px).
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const region of colorRegions) {
      if (!region.polygons) continue;
      for (const poly of region.polygons) {
        for (const p of poly) {
          if (p.x < minX) minX = p.x;
          if (p.x > maxX) maxX = p.x;
          if (p.y < minY) minY = p.y;
          if (p.y > maxY) maxY = p.y;
        }
      }
    }

    const hasBounds = isFinite(minX) && isFinite(maxX) && isFinite(minY) && isFinite(maxY);
    const bboxWpx = hasBounds ? maxX - minX : 0;
    const bboxHpx = hasBounds ? maxY - minY : 0;
    const cx = hasBounds ? (minX + maxX) / 2 : 0;
    const cy = hasBounds ? (minY + maxY) / 2 : 0;

    // 2. px -> mm, then fit to garment.
    const bboxWmm = bboxWpx / pxPerMm;
    const bboxHmm = bboxHpx / pxPerMm;
    const fit = fitScale(bboxWmm || 1e-9, bboxHmm || 1e-9, garment);

    // 3. px -> DST-unit transform centered at origin (Y flipped up).
    const scalePxToDst = fit.scale * (1 / pxPerMm) * DST_UNITS_PER_MM;
    const toDst = (p) => ({
      x: Math.round((p.x - cx) * scalePxToDst),
      y: Math.round((cy - p.y) * scalePxToDst),
    });

    // maxStitch threshold in DST units, for jump detection. The fill densifies
    // in px so no source gap exceeds maxStitchMm*pxPerMm; after the fit scale is
    // applied that gap maps to maxStitchMm*fit.scale in the final (DST) space.
    // So a genuine jump is a move that exceeds that scaled spacing. A small
    // tolerance absorbs per-coordinate rounding.
    const maxStitchDst = maxStitchMm * fit.scale * DST_UNITS_PER_MM * 1.001 + 2;

    // Convert mm spacings to px for the fill/outline (which run in px space).
    const rowSpacingPx = densityMm * pxPerMm;
    const maxStitchPx = maxStitchMm * pxPerMm;
    const outlineStitchPx = outlineStitchMm * pxPerMm;

    const stitches = [];
    const colors = [];
    let regionOrdinal = 0;

    for (let ri = 0; ri < colorRegions.length; ri++) {
      const region = colorRegions[ri];
      const rgb = region.rgb || [0, 0, 0];
      colors.push({
        r: rgb[0],
        g: rgb[1],
        b: rgb[2],
        name: "Color " + (ri + 1),
      });

      const polygons = region.polygons || [];
      // Skip empty region for stitch generation (but color still counts).
      const hasGeom = polygons.some((poly) => poly && poly.length >= 2);
      if (!hasGeom) continue;

      // 4. Fill in px, then transform to DST units.
      const fillPx = tatamiFill(polygons, {
        rowSpacing: rowSpacingPx,
        angleDeg: 0,
        maxStitch: maxStitchPx,
      });
      const regionPts = fillPx.map(toDst);

      if (outline) {
        for (const poly of polygons) {
          if (!poly || poly.length < 2) continue;
          const outPx = runningOutline(poly, { stitchLen: outlineStitchPx });
          for (const p of outPx) regionPts.push(toDst(p));
        }
      }

      if (regionPts.length === 0) continue;

      // Prepend a color-change marker for every region after the first that
      // actually emits stitches.
      if (regionOrdinal > 0) {
        stitches.push({ x: regionPts[0].x, y: regionPts[0].y, type: "color" });
      }
      regionOrdinal++;

      // Emit points; mark jumps where the gap exceeds maxStitch.
      let prev = null;
      for (const pt of regionPts) {
        let type = "stitch";
        if (prev) {
          const dx = pt.x - prev.x;
          const dy = pt.y - prev.y;
          if (Math.hypot(dx, dy) > maxStitchDst) type = "jump";
        }
        stitches.push({ x: pt.x, y: pt.y, type });
        prev = pt;
      }
    }

    // 5. Append end marker.
    if (stitches.length > 0) {
      const last = stitches[stitches.length - 1];
      stitches.push({ x: last.x, y: last.y, type: "end" });
    } else {
      stitches.push({ x: 0, y: 0, type: "end" });
    }

    const stitchCount = stitches.filter((s) => s.type === "stitch").length;

    return {
      stitches,
      colors,
      widthMM: fit.targetWmm,
      heightMM: fit.targetHmm,
      stitchCount,
      colorCount: colorRegions.length,
    };
  }

  return { buildDesign };
});
