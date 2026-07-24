// Pre-digitized satin FONT runtime: lay out text from a parsed glyph library
// (built by tools/build-font.mjs) and play each glyph's authored satin columns
// through satinplay. Produces clean lettering without any auto-tracing.
// Dual-mode (Node require + browser via root.EMB).
(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  const _node = typeof module !== "undefined" && module.exports;
  const satinplay = _node ? require("./satinplay.js") : root.EMB;
  const columnGeom = satinplay.columnGeom;
  const satinFromGeom = satinplay.satinFromGeom;
  const centerFromGeom = satinplay.centerFromGeom;
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // Nearest arc-length fraction on a centerline chain C (with cumulative table
  // cum,total) to point p, plus that distance.
  function nearestOnCenter(C, cum, total, p) {
    let bd = Infinity, bf = 0;
    for (let i = 0; i + 1 < C.length; i++) {
      const ax = C[i].x, ay = C[i].y, ex = C[i + 1].x - ax, ey = C[i + 1].y - ay;
      const L2 = ex * ex + ey * ey; let t = L2 > 1e-9 ? ((p.x - ax) * ex + (p.y - ay) * ey) / L2 : 0;
      if (t < 0) t = 0; else if (t > 1) t = 1;
      const qx = ax + ex * t, qy = ay + ey * t, d = Math.hypot(p.x - qx, p.y - qy);
      if (d < bd) { bd = d; bf = total > 0 ? (cum[i] + t * (cum[i + 1] - cum[i])) / total : 0; }
    }
    return { d: bd, f: bf };
  }

  // Route ONE glyph's satin columns with UNDERPATHING (Ink/Stitch method).
  // Dice each column centerline at its endpoints AND wherever another column's
  // end lands on it (mid-stroke junctions), giving graph nodes; each diced span
  // is a satin edge. Merge coincident nodes. Per connected component find an
  // Euler circuit over the doubled edge set (each edge traversed both ways);
  // walking it in REVERSE, a span's LAST visit sews as satin and earlier visits
  // as RUNNING — so the running underpath is always laid first and the satin
  // covers it. Result: one continuous needle-down path per component (no trims
  // inside it); jumps only BETWEEN components (dots) and between glyphs.
  // Returns [{pts, kind:"satin"|"underlay", jump}].
  function routeGlyph(cols, opts) {
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0;
    const satinOpts = { spacingMm, pxPerMm, pullCompMm };
    const G = [];
    for (const c of cols) {
      const geom = columnGeom(c.railA, c.railB, c.rungs, 12);
      if (!geom || geom.total <= 1e-6 || geom.C.length < 2) continue;
      const w = Math.max(dist(c.railA[0], c.railB[0]), dist(c.railA[c.railA.length - 1], c.railB[c.railB.length - 1]));
      G.push({ geom, w });
    }
    if (!G.length) return [];
    const ws = G.map((g) => g.w).sort((a, b) => a - b);
    const medW = ws[ws.length >> 1] || 4;
    const mergeR = Math.max(2, 1.3 * medW);

    // Endpoints of every column (to find mid-stroke junctions on others).
    const endpts = [];
    for (const g of G) { const C = g.geom.C; endpts.push(C[0], C[C.length - 1]); }
    // Cut fractions per column.
    for (const g of G) {
      const { C, cum, total } = g.geom; const cuts = [0, 1];
      for (const p of endpts) { const nr = nearestOnCenter(C, cum, total, p); if (nr.d <= mergeR && nr.f > 0.06 && nr.f < 0.94) cuts.push(nr.f); }
      cuts.sort((a, b) => a - b);
      const uniq = [cuts[0]]; for (let i = 1; i < cuts.length; i++) if (cuts[i] - uniq[uniq.length - 1] > 0.04) uniq.push(cuts[i]);
      g.cuts = uniq;
    }
    // Nodes + satin edges (one per diced span).
    const nodes = [];
    const nodeOf = (p) => { for (let i = 0; i < nodes.length; i++) if (dist(nodes[i], p) <= mergeR) return i; nodes.push({ x: p.x, y: p.y }); return nodes.length - 1; };
    const ptAtFrac = (geom, f) => { const { C, cum, total } = geom; const s = f * total; let i = 0; while (i < C.length - 2 && cum[i + 1] < s) i++; const seg = cum[i + 1] - cum[i] || 1; const t = (s - cum[i]) / seg; return { x: C[i].x + (C[i + 1].x - C[i].x) * t, y: C[i].y + (C[i + 1].y - C[i].y) * t }; };
    const edges = []; // {gi, f0, f1, na, nb}
    G.forEach((g, gi) => { for (let k = 0; k + 1 < g.cuts.length; k++) { const f0 = g.cuts[k], f1 = g.cuts[k + 1]; edges.push({ gi, f0, f1, na: nodeOf(ptAtFrac(g.geom, f0)), nb: nodeOf(ptAtFrac(g.geom, f1)) }); } });
    if (!edges.length) return [];

    // Directed-edge adjacency (each undirected span usable both ways).
    const dedges = []; edges.forEach((e, ei) => { dedges.push({ from: e.na, to: e.nb, ei, fwd: true }); dedges.push({ from: e.nb, to: e.na, ei, fwd: false }); });
    const outAdj = nodes.map(() => []); dedges.forEach((de, i) => outAdj[de.from].push(i));
    const usedDE = dedges.map(() => false);
    const ptr = nodes.map(() => 0);
    function euler(start) { // Hierholzer → ordered list of directed-edge indices
      const stackN = [start], stackE = [], circ = [];
      while (stackN.length) {
        const v = stackN[stackN.length - 1];
        while (ptr[v] < outAdj[v].length && usedDE[outAdj[v][ptr[v]]]) ptr[v]++;
        if (ptr[v] < outAdj[v].length) { const dei = outAdj[v][ptr[v]++]; usedDE[dei] = true; stackE.push(dei); stackN.push(dedges[dei].to); }
        else { stackN.pop(); if (stackE.length) circ.push(stackE.pop()); }
      }
      return circ.reverse();
    }

    // Emit: iterate components (start at each node that still has unused edges,
    // preferring smaller x so words read left→right). Each component = one
    // Euler circuit → typed spans → geometry.
    const runs = [];
    const nodeOrder = nodes.map((n, i) => i).sort((a, b) => nodes[a].x - nodes[b].x);
    for (const start of nodeOrder) {
      if (ptr[start] >= outAdj[start].length || outAdj[start].every((i) => usedDE[i])) continue;
      const circ = euler(start);
      if (!circ.length) continue;
      // reverse-dedupe: last visit of an edge = satin, earlier = running
      const isSatin = new Array(circ.length);
      const seen = new Set();
      for (let k = circ.length - 1; k >= 0; k--) { const ei = dedges[circ[k]].ei; if (seen.has(ei)) isSatin[k] = false; else { seen.add(ei); isSatin[k] = true; } }
      // build typed spans, collapsing contiguous same-column-same-type steps
      const spans = [];
      for (let k = 0; k < circ.length; k++) {
        const de = dedges[circ[k]], e = edges[de.ei];
        const f0 = de.fwd ? e.f0 : e.f1, f1 = de.fwd ? e.f1 : e.f0;
        const sat = isSatin[k];
        const prev = spans[spans.length - 1];
        if (prev && prev.gi === e.gi && prev.sat === sat && Math.abs(prev.f1 - f0) < 1e-6) prev.f1 = f1;
        else spans.push({ gi: e.gi, sat, f0, f1 });
      }
      let first = true;
      for (const sp of spans) {
        const geom = G[sp.gi].geom;
        const lo = Math.min(sp.f0, sp.f1), hi = Math.max(sp.f0, sp.f1);
        let pts = sp.sat ? satinFromGeom(geom, lo, hi, satinOpts) : centerFromGeom(geom, lo, hi, 2, pxPerMm);
        if (!pts || pts.length < 2) continue;
        if (sp.f1 < sp.f0) pts = pts.slice().reverse(); // follow traversal direction
        runs.push({ pts, kind: sp.sat ? "satin" : "underlay", jump: first });
        first = false;
      }
    }
    return runs;
  }

  // Lay out `text` in a pre-digitized font. Returns:
  //   { runs:[{pts:[{x,y}…], kind, jump}], bbox:{x0,y0,x1,y1} }
  // in DESIGN PIXELS (y-down). Columns are routed per glyph with underpathing
  // (see routeGlyph). A run's jump=true means "lift needle & travel to its
  // start" (the caller trims if far); jump=false means "continue with a needle-
  // down running connector". opts = { emMm=18, pxPerMm=10, spacingMm=0.4,
  // pullCompMm=0, letterSpacingMm=0, underlay=true }.
  function layoutText(font, text, opts) {
    const o = opts || {};
    const emMm = o.emMm || 18;
    const pxPerMm = o.pxPerMm || 10;
    const spacingMm = o.spacingMm || 0.4;
    const pullCompMm = o.pullCompMm || 0;
    const doUnderlay = o.underlay !== false;
    const u2px = (emMm / font.unitsPerEm) * pxPerMm;       // font units -> design px
    const lsUnits = (o.letterSpacingMm || 0) * font.unitsPerEm / emMm;
    const chars = Array.from(text);

    const runs = [];
    let penX = 0, prev = null;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const acc = (p) => { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; };

    for (const ch of chars) {
      if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
      const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
      if (!g) { penX += font.advDefault; prev = null; continue; }
      if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
      const ox = penX;
      const TX = (x) => (x + ox) * u2px, TY = (y) => y * u2px;
      const cols = g.cols.map((col) => ({
        railA: col.railA.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })),
        railB: col.railB.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })),
        rungs: (col.rungs || []).map((rg) => [{ x: TX(rg[0][0]), y: TY(rg[0][1]) }, { x: TX(rg[1][0]), y: TY(rg[1][1]) }]),
      }));
      const gRuns = routeGlyph(cols, { pxPerMm, spacingMm, pullCompMm, underlay: doUnderlay });
      for (const r of gRuns) { runs.push(r); for (const p of r.pts) acc(p); }
      penX += g.adv + lsUnits;
      prev = ch;
    }
    return { runs, bbox: { x0, y0, x1, y1 } };
  }

  return { layoutText };
});
