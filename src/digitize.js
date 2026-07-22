// Quality auto-digitize orchestrator: turns ColorRegions (from raster tracing
// OR SVG import) into a Design with underlay, satin-for-thin-shapes,
// fill-with-per-region-angle, and pull compensation. Dual-mode (Node + browser).
(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  const _node = typeof module !== "undefined" && module.exports;
  const dep = _node ? require : null;
  const units = _node ? dep("./units.js") : root.EMB;
  const garments = _node ? dep("./garments.js") : root.EMB;
  const fillmod = _node ? dep("./fill.js") : root.EMB;
  const satinmod = _node ? dep("./satin.js") : root.EMB;

  function polyArea(p) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j].x * p[i].y - p[i].x * p[j].y); return Math.abs(a) / 2; }
  function polyPerim(p) { let L = 0; for (let i = 0; i < p.length; i++) { const q = p[(i + 1) % p.length]; L += Math.hypot(q.x - p[i].x, q.y - p[i].y); } return L; }
  function centroid(p) { let x = 0, y = 0; for (const q of p) { x += q.x; y += q.y; } return { x: x / p.length, y: y / p.length }; }
  // principal-axis angle (degrees) of a set of polygons
  function pcaAngleDeg(polys) {
    let n = 0, mx = 0, my = 0;
    for (const p of polys) for (const q of p) { mx += q.x; my += q.y; n++; }
    if (!n) return 45;
    mx /= n; my /= n;
    let sxx = 0, syy = 0, sxy = 0;
    for (const p of polys) for (const q of p) { const dx = q.x - mx, dy = q.y - my; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
    return 0.5 * Math.atan2(2 * sxy, sxx - syy) * 180 / Math.PI;
  }
  // inset a ring toward its centroid by `d` px (crude but fine for underlay)
  function insetRing(ring, d) {
    const c = centroid(ring);
    return ring.map((q) => {
      const dx = c.x - q.x, dy = c.y - q.y, L = Math.hypot(dx, dy) || 1;
      const t = Math.min(d, L * 0.4);
      return { x: q.x + dx / L * t, y: q.y + dy / L * t };
    });
  }

  function pointInPoly(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
      if ((yi > pt.y) !== (yj > pt.y) && pt.x < (xj - xi) * (pt.y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // Group a flat list of rings (e.g. glyph contours) into shapes with holes:
  // a ring whose centroid lies inside a larger ring becomes that ring's hole.
  // Handles one nesting level (outer + counters) — enough for text glyphs.
  function groupRingsIntoShapes(rings, minArea) {
    const items = rings
      .filter((p) => p && p.length >= 4)
      .map((p) => ({ ring: p, area: polyArea(p) }))
      .filter((it) => it.area > (minArea || 0));
    items.sort((a, b) => b.area - a.area);
    const shapes = [];
    for (const it of items) {
      const c = centroid(it.ring);
      let parent = null;
      for (const s of shapes) if (s._area > it.area && pointInPoly(c, s.outer)) { parent = s; break; }
      if (parent) parent.holes.push(it.ring);
      else shapes.push({ outer: it.ring, holes: [], _area: it.area });
    }
    return shapes.map((s) => ({ outer: s.outer, holes: s.holes }));
  }

  // colorRegions: [{rgb:[r,g,b], polygons:[[{x,y}...]...]}] in PIXEL coords.
  // opts: { garment, pxPerMm, densityMm, maxStitchMm, satinMaxWidthMm, underlay, pullCompMm, perRegionAngle, darkOnTop }
  function buildQualityDesign(colorRegions, opts) {
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 8;
    const densityMm = o.densityMm || 0.45;
    const maxStitchMm = o.maxStitchMm || 4;
    const satinMaxWidthMm = o.satinMaxWidthMm || 3.0;
    const pullCompMm = o.pullCompMm == null ? 0.2 : o.pullCompMm;
    const useUnderlay = o.underlay !== false;
    const perRegionAngle = o.perRegionAngle !== false;
    const garment = o.garment || { widthIn: 5, heightIn: 2.25 };

    // filter empty; accept {shapes:[{outer,holes}]} or legacy {polygons:[ring]}
    const regions = colorRegions.filter((r) => r && ((r.shapes && r.shapes.length) || (r.polygons && r.polygons.length)));
    for (const r of regions) if (!r.polygons) r.polygons = r.shapes.map((s) => s.outer);
    if (!regions.length) return { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, _debug: { nSatin: 0, nFill: 0 } };

    // sequence: light colors first, dark last (dark sits on top) unless overridden
    if (o.darkOnTop !== false) regions.sort((a, b) => (b.rgb[0] + b.rgb[1] + b.rgb[2]) - (a.rgb[0] + a.rgb[1] + a.rgb[2]));

    // bbox in px across all polygons
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const r of regions) for (const p of r.polygons) for (const q of p) { if (q.x < minX) minX = q.x; if (q.x > maxX) maxX = q.x; if (q.y < minY) minY = q.y; if (q.y > maxY) maxY = q.y; }
    const bboxWmm = (maxX - minX) / pxPerMm, bboxHmm = (maxY - minY) / pxPerMm;
    const fit = garments.fitScale(bboxWmm || 1, bboxHmm || 1, garment);
    const sc = (fit.scale > 0 && isFinite(fit.scale)) ? fit.scale : 1;
    const scalePxToDst = sc * (1 / pxPerMm) * units.DST_UNITS_PER_MM;
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    const T = (q) => ({ x: Math.round((q.x - cx) * scalePxToDst), y: Math.round((cy - q.y) * scalePxToDst) });

    const mmPerPxFinal = scalePxToDst / units.DST_UNITS_PER_MM; // final mm per source px
    const pxPerFinalMm = 1 / mmPerPxFinal;                       // source px per final mm
    const rowPx = Math.max(0.8, densityMm * pxPerFinalMm);
    const maxPx = Math.max(3, maxStitchMm * pxPerFinalMm);
    const underlayStitchPx = Math.max(4, 2.0 * pxPerFinalMm);
    const underlayRowPx = Math.max(3, 2.5 * pxPerFinalMm);

    const stitches = [];
    const colors = [];
    let first = true, nSatin = 0, nFill = 0;

    function pushRun(pts) {
      if (!pts || !pts.length) return;
      const f = T(pts[0]);
      stitches.push({ x: f.x, y: f.y, type: "jump" });
      for (const q of pts) {
        const d = T(q);
        stitches.push({ x: d.x, y: d.y, type: q.travel ? "jump" : "stitch" });
      }
    }

    for (const r of regions) {
      if (!first) { const last = stitches[stitches.length - 1] || { x: 0, y: 0 }; stitches.push({ x: last.x, y: last.y, type: "color" }); }
      first = false;
      colors.push({ r: r.rgb[0], g: r.rgb[1], b: r.rgb[2], name: "Color " + (colors.length + 1) });
      // shapes: [{outer, holes}] (hole-aware) — or bare polygons for back-compat
      const shapes = r.shapes || r.polygons.map((p) => ({ outer: p, holes: [] }));
      const allRings = [];
      for (const s of shapes) { allRings.push(s.outer); for (const hh of s.holes) allRings.push(hh); }
      const angle = perRegionAngle ? pcaAngleDeg(allRings) : 45;
      for (const shape of shapes) {
        const poly = shape.outer;
        if (!poly || poly.length < 4) continue;
        const holes = (shape.holes || []).filter((hh) => hh && hh.length >= 4);
        const outerArea = polyArea(poly), holeArea = holes.reduce((a, hh) => a + polyArea(hh), 0);
        const area = Math.max(0, outerArea - holeArea), perim = polyPerim(poly) + holes.reduce((a, hh) => a + polyPerim(hh), 0);
        if (area <= 0 || perim <= 0) continue;
        const widthMmFinal = (2 * area / perim) * mmPerPxFinal;
        // satin only for genuinely thin SOLID strokes; ring-with-hole goes to
        // even-odd fill (satinColumn can't represent holes)
        let thin = widthMmFinal <= satinMaxWidthMm && holes.length === 0;
        // branch guard: a clean column splits into two side chains of similar
        // length; branched shapes (most letters, Y/T/E forms) don't — satin
        // would zigzag chaotically across them, so route those to fill.
        if (thin && satinmod.farthestBoundaryPair) {
          try {
            const [bi, bj] = satinmod.farthestBoundaryPair(poly);
            const [ca, cb] = satinmod.splitBoundary(poly, bi, bj);
            const la = satinmod.chainLength(ca), lb = satinmod.chainLength(cb);
            const ratio = Math.max(la, lb) / Math.max(1e-6, Math.min(la, lb));
            if (ratio > 1.6) thin = false;
          } catch (e) { thin = false; }
        }
        const rings = [poly].concat(holes);

        // underlay (same thread color, laid first)
        if (useUnderlay) {
          try {
            const inset = insetRing(poly, Math.min(2, 0.6 * pxPerFinalMm));
            pushRun(fillmod.runningOutline(inset, { stitchLen: underlayStitchPx }));
            if (!thin) pushRun(fillmod.tatamiFill(rings, { rowSpacing: underlayRowPx, angleDeg: angle + 90, maxStitch: maxPx, markConnectors: true }));
          } catch (e) { /* underlay best-effort */ }
        }

        // top stitching
        let pts = [];
        try {
          if (thin) { pts = satinmod.satinColumn(poly, { spacingMm: densityMm, pxPerMm: pxPerFinalMm, pullCompMm }); nSatin++; }
          else { pts = fillmod.tatamiFill(rings, { rowSpacing: rowPx, angleDeg: angle, maxStitch: maxPx, markConnectors: true }); nFill++; }
        } catch (e) { pts = []; }
        pushRun(pts);
      }
    }
    stitches.push({ x: 0, y: 0, type: "end" });
    const stitchCount = stitches.filter((s) => s.type === "stitch").length;
    return { stitches, colors, widthMM: fit.targetWmm, heightMM: fit.targetHmm, stitchCount, colorCount: colors.length, _debug: { nSatin, nFill } };
  }

  return { buildQualityDesign, groupRingsIntoShapes };
});
