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
  // SIGNED shoelace area (sign encodes winding). Do NOT confuse with polyArea (abs).
  function signedArea(p) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j].x * p[i].y - p[i].x * p[j].y); return a / 2; }
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

  // Offset a polygon ring by `dPx` along per-vertex OUTWARD normals (miter join).
  // outward=true grows the ring, outward=false shrinks it — correct regardless of
  // winding (signed area picks the outward sense). Miter displacement is clamped
  // at 3*dPx so sharp concave vertices don't produce spikes. Returns a fresh ring.
  function offsetRing(ring, dPx, outward) {
    const n = ring ? ring.length : 0;
    const copy = ring ? ring.map((q) => ({ x: q.x, y: q.y })) : [];
    if (n < 3 || !(Math.abs(dPx) > 1e-9)) return copy;
    // signed area (shoelace): >0 and <0 pick opposite outward-normal senses.
    let area2 = 0;
    for (let i = 0; i < n; i++) { const a = ring[i], b = ring[(i + 1) % n]; area2 += a.x * b.y - b.x * a.y; }
    const sgn = area2 >= 0 ? 1 : -1;      // winding sign
    const dir = outward ? 1 : -1;         // grow vs shrink
    const maxDisp = 3 * dPx;              // miter clamp
    const out = [];
    for (let i = 0; i < n; i++) {
      const prev = ring[(i - 1 + n) % n], cur = ring[i], next = ring[(i + 1) % n];
      let e1x = cur.x - prev.x, e1y = cur.y - prev.y;
      let e2x = next.x - cur.x, e2y = next.y - cur.y;
      const L1 = Math.hypot(e1x, e1y) || 1, L2 = Math.hypot(e2x, e2y) || 1;
      e1x /= L1; e1y /= L1; e2x /= L2; e2y /= L2;
      // outward unit normal of an edge (dx,dy) is sgn*(dy,-dx)
      const n1x = sgn * e1y, n1y = -sgn * e1x;
      const n2x = sgn * e2y, n2y = -sgn * e2x;
      let bx = n1x + n2x, by = n1y + n2y;
      const bl = Math.hypot(bx, by);
      let dispx, dispy;
      if (bl < 1e-6) { dispx = n1x * dPx; dispy = n1y * dPx; }  // ~180° cusp
      else {
        bx /= bl; by /= bl;
        const cosH = bx * n1x + by * n1y;         // cos(half exterior angle)
        let m = dPx / Math.max(cosH, 1e-3);       // miter length = d/cos(halfAngle)
        if (m > maxDisp) m = maxDisp;             // clamp spikes at sharp vertices
        dispx = bx * m; dispy = by * m;
      }
      out.push({ x: cur.x + dir * dispx, y: cur.y + dir * dispy });
    }
    return out;
  }

  // Build underlay point-runs for a shape under a named style. Returns an array
  // of runs (each becomes one pushRun). ctx: { fillAngle, pxPerFinalMm, maxStitch,
  // underlayStitchPx, underlayRowPx, runningOutline, tatamiFill, insetRing,
  // pcaAngleDeg }. Styles: none | edge_run | center_run | zigzag | edge_zigzag |
  // edge_lattice | double_lattice.
  function underlayRuns(shape, styleName, ctx) {
    const style = styleName || "none";
    if (style === "none") return [];
    const outer = shape.outer;
    const holes = (shape.holes || []).filter((hh) => hh && hh.length >= 4);
    const rings = [outer].concat(holes);
    const pxPerFinalMm = ctx.pxPerFinalMm;
    const fillAngle = ctx.fillAngle || 0;
    const edgeInset = Math.min(2, 0.6 * pxPerFinalMm);
    const edgeStitch = ctx.underlayStitchPx;
    const latticeRow = ctx.underlayRowPx;              // ~2.5mm sparse tatami
    const zigRow = Math.max(3, 2.0 * pxPerFinalMm);    // ~2.0mm zig-zag rows
    const maxStitch = ctx.maxStitch;

    function edgeRun() {
      const r = [ctx.runningOutline(ctx.insetRing(outer, edgeInset), { stitchLen: edgeStitch })];
      for (const hh of holes) r.push(ctx.runningOutline(ctx.insetRing(hh, edgeInset), { stitchLen: edgeStitch }));
      return r;
    }
    function zigzag() {
      return [ctx.tatamiFill(rings, { rowSpacing: zigRow, angleDeg: fillAngle + 90, maxStitch, markConnectors: true })];
    }
    function lattice(angleOff) {
      return [ctx.tatamiFill(rings, { rowSpacing: latticeRow, angleDeg: fillAngle + angleOff, maxStitch, markConnectors: true })];
    }
    // Single running stitch along the shape's PCA-major axis, clipped to the
    // interior (longest contiguous inside segment through the centroid).
    function centerRun() {
      const c = centroid(outer);
      const ang = ctx.pcaAngleDeg(rings) * Math.PI / 180;
      const dx = Math.cos(ang), dy = Math.sin(ang);
      let ext = 0;
      for (const q of outer) { const L = Math.hypot(q.x - c.x, q.y - c.y); if (L > ext) ext = L; }
      ext *= 1.1;
      const step = Math.max(2, edgeStitch);
      let best = [], cur = [];
      for (let t = -ext; t <= ext + 1e-9; t += step) {
        const p = { x: c.x + dx * t, y: c.y + dy * t };
        const inside = pointInPoly(p, outer) && !holes.some((hh) => pointInPoly(p, hh));
        if (inside) cur.push(p);
        else { if (cur.length > best.length) best = cur; cur = []; }
      }
      if (cur.length > best.length) best = cur;
      return best.length >= 2 ? [best] : [];
    }

    switch (style) {
      case "edge_run": return edgeRun();
      case "center_run": return centerRun();
      case "zigzag": return zigzag();
      case "edge_zigzag": return edgeRun().concat(zigzag());
      case "edge_lattice": return edgeRun().concat(lattice(90));
      case "double_lattice": return edgeRun().concat(lattice(45)).concat(lattice(-45));
      default: return edgeRun().concat(lattice(90));
    }
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
  // opts: { garment, pxPerMm, densityMm, maxStitchMm, satinMaxWidthMm, underlay, pullCompMm, perRegionAngle, darkOnTop, angleOverrides }
  //
  // Stitch angle (Phase 3): by DEFAULT each fill SHAPE gets its OWN PCA angle
  // from its own rings (outer+holes) — long thin fills align to their length,
  // adjacent elements read separately. A fixed angle can be forced per COLOR two
  // ways (both keyed to the ORIGINAL caller region order, before the internal
  // light→dark sort): set `region.angleOverride` (number degrees, or null=auto)
  // on the input region, OR pass `opts.angleOverrides` as a map/array from the
  // original region index → degrees. region.angleOverride wins when both given.
  // When an override is present, ALL that region's shapes (fill + derived
  // underlay) use it; otherwise per-shape auto. `perRegionAngle:false` disables
  // auto entirely (fixed 45°).
  function buildQualityDesign(colorRegions, opts) {
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 8;
    // Fabric preset (from getFabric) drives pull comp, density, trim, underlay.
    // When absent, every derived value falls back to the pre-fabric defaults and
    // the underlay code path stays byte-identical to before (see below).
    const fabric = o.fabric || null;
    const densityAdjust = (fabric && fabric.densityAdjust) ? fabric.densityAdjust : 1;
    const densityMm = (o.densityMm || 0.45) * densityAdjust;
    const maxStitchMm = o.maxStitchMm || 4;
    const satinMaxWidthMm = o.satinMaxWidthMm || 3.0;
    const pullCompMm = (fabric && fabric.pullCompMm != null) ? fabric.pullCompMm
      : (o.pullCompMm == null ? 0.2 : o.pullCompMm);
    const useUnderlay = o.underlay !== false;
    const perRegionAngle = o.perRegionAngle !== false;
    const garment = o.garment || { widthIn: 5, heightIn: 2.25 };

    // filter empty; accept {shapes:[{outer,holes}]} or legacy {polygons:[ring]}
    const regions = colorRegions.filter((r) => r && ((r.shapes && r.shapes.length) || (r.polygons && r.polygons.length)));
    for (const r of regions) if (!r.polygons) r.polygons = r.shapes.map((s) => s.outer);
    if (!regions.length) return { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, _debug: { nSatin: 0, nFill: 0, nTrims: 0 } };

    // Tag each region with its ORIGINAL caller index before we reorder, so
    // opts.angleOverrides (keyed by original index) survives the sort below.
    regions.forEach((r, i) => { r._origIdx = i; });
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
    const pullCompPx = pullCompMm * pxPerFinalMm; // fill pull-comp offset (px)
    // Shared context for named underlay styles (used only in fabric mode).
    const underlayCtxBase = {
      pxPerFinalMm, maxStitch: maxPx, underlayStitchPx, underlayRowPx,
      runningOutline: fillmod.runningOutline, tatamiFill: fillmod.tatamiFill,
      insetRing, pcaAngleDeg,
    };

    // Trim policy: trim before any travel longer than trimAtMm (FINAL mm).
    const trimAtMm = (fabric && fabric.trimAtMm != null) ? fabric.trimAtMm
      : (o.trimAtMm == null ? 3.0 : o.trimAtMm);
    const trimAtPx = trimAtMm * pxPerFinalMm; // threshold in source px
    // Cap garments sew crown-distortion-safe: center-out per color block.
    const capMode = garment && (garment.id === "hat_front" || garment.id === "beanie");

    const stitches = [];
    const colors = [];
    let first = true, nSatin = 0, nFill = 0, nTrims = 0, nCenterOut = 0;
    // Large fills sew center-out (rows interleaved from the vertical center) so
    // fabric push radiates symmetrically. "Large" = both final-mm bbox dims over
    // this threshold; applies to the TOP fill only (underlay stays sequential).
    const centerOutMinMm = 15;
    const minimizeColorChanges = !!o.minimizeColorChanges;
    let lastPx = { x: cx, y: cy }; // last emitted point in px; origin = design center (DST 0,0)
    let started = false;           // no trim before the very first stitch of the design
    let justChangedColor = false;  // color change already cut the thread; skip the next per-shape travel-trim

    function pushRun(pts) {
      if (!pts || !pts.length) return;
      const f = T(pts[0]);
      stitches.push({ x: f.x, y: f.y, type: "jump" });
      for (const q of pts) {
        const d = T(q);
        stitches.push({ x: d.x, y: d.y, type: q.travel ? "jump" : "stitch" });
      }
      lastPx = pts[pts.length - 1];
    }
    // Emit a trim command at the current (last) position — zero-travel; the
    // following jump carries the machine to the next shape.
    function emitTrimAtLast() {
      const tp = T(lastPx);
      stitches.push({ x: tp.x, y: tp.y, type: "trim" });
      nTrims++;
    }

    // Order a color block's shapes: cap center-out (unchanged, takes precedence),
    // else background-first — the LARGEST-area shape sews first (it's the
    // background), then greedy nearest-neighbor from there for the rest. Only the
    // FIRST pick changed from pure nearest-neighbor-from-previous-position; the
    // remaining picks still chain by centroid proximity for short travel.
    function orderShapes(list, startPx) {
      if (list.length <= 1) return list.slice();
      const cents = list.map((s) => centroid(s.outer));
      if (capMode) {
        const idx = list.map((_, i) => i);
        idx.sort((a, b) => {
          const da = Math.abs(cents[a].x - cx), db = Math.abs(cents[b].x - cx);
          if (da !== db) return da - db;          // |x - center| ascending
          return cents[b].y - cents[a].y;         // tiebreak y DESCENDING (bottom-up)
        });
        return idx.map((i) => list[i]);
      }
      const remaining = list.map((s, i) => ({ s, c: cents[i], a: polyArea(s.outer) }));
      const out = [];
      // Background-first: seed the walk at the LARGEST-area shape rather than the
      // one nearest the previous position, so wide background regions sew before
      // detail sitting on top of them. Deterministic (input-order independent):
      // area DESC, then nearest to startPx, then centroid x, then y.
      let seed = 0;
      for (let i = 1; i < remaining.length; i++) {
        const ri = remaining[i], rb = remaining[seed];
        if (ri.a !== rb.a) { if (ri.a > rb.a) seed = i; continue; }
        const di = Math.hypot(ri.c.x - startPx.x, ri.c.y - startPx.y);
        const db = Math.hypot(rb.c.x - startPx.x, rb.c.y - startPx.y);
        if (di !== db) { if (di < db) seed = i; continue; }
        if (ri.c.x !== rb.c.x) { if (ri.c.x < rb.c.x) seed = i; continue; }
        if (ri.c.y < rb.c.y) seed = i;
      }
      const pick0 = remaining.splice(seed, 1)[0];
      out.push(pick0.s);
      let cur = { x: pick0.c.x, y: pick0.c.y };
      while (remaining.length) {
        let best = 0, bd = Infinity;
        for (let i = 0; i < remaining.length; i++) {
          const d = Math.hypot(remaining[i].c.x - cur.x, remaining[i].c.y - cur.y);
          if (d < bd) { bd = d; best = i; }
        }
        const pick = remaining.splice(best, 1)[0];
        out.push(pick.s);
        cur = pick.c;
      }
      return out;
    }

    let prevRgb = null;
    for (const r of regions) {
      // minimizeColorChanges: when the current region's EXACT rgb matches the
      // previous emitted region's, keep sewing on the same thread — no color
      // change, no new color record. Same-rgb regions are contiguous after the
      // light→dark sort (identical brightness), so a same-as-previous test
      // groups them all. NOTE: with the flatten pipeline every palette color is
      // unique, so this is a no-op there; it only bites on repeated-color inputs
      // (e.g. future SVG import). Default (false) → strict light→dark, unchanged.
      const sameThread = minimizeColorChanges && prevRgb &&
        r.rgb[0] === prevRgb[0] && r.rgb[1] === prevRgb[1] && r.rgb[2] === prevRgb[2];
      if (!first && !sameThread) {
        // Always trim before a color change (thread must be cut), then change.
        emitTrimAtLast();
        const last = stitches[stitches.length - 1] || { x: 0, y: 0 };
        stitches.push({ x: last.x, y: last.y, type: "color" });
        justChangedColor = true; // thread already cut; don't double-trim the first shape of this block
      }
      first = false;
      prevRgb = r.rgb;
      if (!sameThread) colors.push({ r: r.rgb[0], g: r.rgb[1], b: r.rgb[2], name: "Color " + (colors.length + 1) });
      // shapes: [{outer, holes}] (hole-aware) — or bare polygons for back-compat
      const shapesRaw = r.shapes || r.polygons.map((p) => ({ outer: p, holes: [] }));
      const shapes0 = shapesRaw.filter((s) => s && s.outer && s.outer.length >= 4);
      // Resolve a fixed per-color angle override (degrees) if the caller set one.
      // region.angleOverride wins; else opts.angleOverrides[originalIndex]. A
      // finite number forces every shape in this color; null/absent → per-shape.
      let regionAngle = null;
      const ov = (r.angleOverride != null) ? r.angleOverride
        : (o.angleOverrides != null ? o.angleOverrides[r._origIdx] : null);
      if (ov != null && isFinite(ov)) regionAngle = ((ov % 180) + 180) % 180;
      const shapes = orderShapes(shapes0, lastPx);
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
            if (ratio > 1.5) thin = false;
            // rung containment: in a true column every cross-stitch midpoint
            // lies inside the shape; on branched shapes (T, M, Y) the rungs
            // shortcut across concavities and land outside — reject those.
            if (thin) {
              const K = 9;
              const pa = satinmod.resampleChain(ca, K);
              const pb = satinmod.resampleChain(cb, K);
              let outside = 0;
              for (let k = 1; k < K - 1; k++) {
                const q = pb[K - 1 - k];
                const mid = { x: (pa[k].x + q.x) / 2, y: (pa[k].y + q.y) / 2 };
                if (!pointInPoly(mid, poly)) outside++;
              }
              if (outside > 0) thin = false;
            }
          } catch (e) { thin = false; }
        }
        const rings = [poly].concat(holes);
        // Per-SHAPE stitch angle: a fixed color override wins; otherwise this
        // shape's OWN PCA axis (outer+holes) so each element's stitches follow
        // its own length/axis. perRegionAngle:false disables auto (fixed 45°).
        const angle = (regionAngle != null) ? regionAngle
          : (perRegionAngle ? pcaAngleDeg(rings) : 45);

        // Build this shape's runs in sew order; trim (if needed) is decided once
        // per shape so we never trim between a shape's own underlay and top.
        const runs = [];
        if (useUnderlay) {
          if (fabric) {
            // Fabric mode: named underlay style per shape type.
            try {
              const style = thin ? (fabric.satinUnderlay || "center_run") : (fabric.fillUnderlay || "edge_lattice");
              const uctx = Object.assign({ fillAngle: angle }, underlayCtxBase);
              for (const run of underlayRuns(shape, style, uctx)) if (run && run.length) runs.push(run);
            } catch (e) { /* underlay best-effort */ }
          } else {
            // No-fabric path: byte-identical to pre-Phase-2 behavior.
            try {
              const inset = insetRing(poly, Math.min(2, 0.6 * pxPerFinalMm));
              runs.push(fillmod.runningOutline(inset, { stitchLen: underlayStitchPx }));
              if (!thin) runs.push(fillmod.tatamiFill(rings, { rowSpacing: underlayRowPx, angleDeg: angle + 90, maxStitch: maxPx, markConnectors: true }));
            } catch (e) { /* underlay best-effort */ }
          }
        }
        // top stitching. Fills get pull compensation via polygon offset (grow
        // outer, shrink holes) so they sew to true size on stretchy fabric; this
        // applies in fabric mode only (no-fabric fills stay unoffset). Satin
        // compensates internally through pullCompMm (unchanged). Underlay/outline
        // trace the TRUE edge and are never offset.
        let pts = [];
        try {
          if (thin) { pts = satinmod.satinColumn(poly, { spacingMm: densityMm, pxPerMm: pxPerFinalMm, pullCompMm }); nSatin++; }
          else {
            let fillRings = rings;
            if (fabric && pullCompPx > 0) {
              // Outer outset never inverts (growing). Hole insets can: a hole
              // thinner than ~2*pullCompPx collapses and flips winding (walls
              // cross), yielding a self-intersecting boundary the miter clamp
              // can't prevent. Per hole: if the inset flips signed-area sign vs
              // the original (winding inverted) or its area is ~0 (collapsed),
              // discard the offset and keep the ORIGINAL hole ring.
              const insetHoles = holes.map((hh) => {
                const off = offsetRing(hh, pullCompPx, false);
                const a0 = signedArea(hh), a1 = signedArea(off);
                if (Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6) return hh;
                return off;
              });
              fillRings = [offsetRing(poly, pullCompPx, true)].concat(insetHoles);
            }
            // Large-fill center-out: qualify by this shape's final-mm bbox.
            let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
            for (const q of poly) { if (q.x < bx0) bx0 = q.x; if (q.x > bx1) bx1 = q.x; if (q.y < by0) by0 = q.y; if (q.y > by1) by1 = q.y; }
            const wMm = (bx1 - bx0) * mmPerPxFinal, hMm = (by1 - by0) * mmPerPxFinal;
            const largeFill = wMm > centerOutMinMm && hMm > centerOutMinMm;
            pts = fillmod.tatamiFill(fillRings, { rowSpacing: rowPx, angleDeg: angle, maxStitch: maxPx, markConnectors: true, centerOut: largeFill }); nFill++;
            if (largeFill) nCenterOut++;
          }
        } catch (e) { pts = []; }
        runs.push(pts);
        // finishing outline: running stitch along the outer edge (and holes)
        if (o.outline) {
          try {
            const edgeLen = Math.max(3, 1.8 * pxPerFinalMm);
            for (const ring of rings) runs.push(fillmod.runningOutline(ring, { stitchLen: edgeLen }));
          } catch (e) { /* best-effort */ }
        }

        const nonEmpty = runs.filter((rn) => rn && rn.length);
        if (!nonEmpty.length) continue;
        const entry = nonEmpty[0][0]; // first sewn point of this shape (px)
        if (started && !justChangedColor) {
          const d = Math.hypot(entry.x - lastPx.x, entry.y - lastPx.y);
          if (d > trimAtPx) emitTrimAtLast(); // long travel → trim at last pos before jump
        }
        justChangedColor = false; // only the first shape after a color change is exempt
        for (const rn of nonEmpty) pushRun(rn);
        started = true;
      }
    }
    stitches.push({ x: 0, y: 0, type: "end" });
    const stitchCount = stitches.filter((s) => s.type === "stitch").length;
    return { stitches, colors, widthMM: fit.targetWmm, heightMM: fit.targetHmm, stitchCount, colorCount: colors.length, _debug: { nSatin, nFill, nTrims, nCenterOut } };
  }

  return { buildQualityDesign, groupRingsIntoShapes, offsetRing, signedArea, underlayRuns };
});
