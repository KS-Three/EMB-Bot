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
  const satinFromRails = satinplay.satinFromRails;
  const centerRun = satinplay.centerRun;
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // Route ONE glyph's satin columns with underpathing. Each column is sewn as a
  // round trip that ENTERS and EXITS at the same end: a center-walk underlay in
  // (hidden under the satin that follows) then the satin back out. Column ends
  // are merged into shared JUNCTION nodes; the router prefers the next column
  // that shares the current node, so the connecting stitch is a short needle-
  // DOWN run tucked at the junction (no trim). A column at a different node gets
  // a real jump (marked jump:true → the caller trims if it's long). This is the
  // Ink/Stitch underpathing idea: travel is only hidden when the satin covers
  // it, so we only ever run under a column we are about to sew, and otherwise
  // jump honestly. Returns [{pts,kind:"underlay"|"satin",jump}].
  function routeGlyph(cols, opts) {
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0;
    const doUnderlay = opts.underlay !== false;
    const info = [];
    for (const c of cols) {
      const satin = satinFromRails(c.railA, c.railB, c.rungs, { spacingMm, pxPerMm, pullCompMm });
      if (satin.length < 2) continue;
      const center = centerRun(c.railA, c.railB, c.rungs, { stepMm: 1.5, pxPerMm });
      if (!center || center.length < 2) continue;
      const w = Math.max(dist(c.railA[0], c.railB[0]), dist(c.railA[c.railA.length - 1], c.railB[c.railB.length - 1]));
      info.push({ satin, center, w });
    }
    if (!info.length) return [];
    const ws = info.map((x) => x.w).sort((a, b) => a - b);
    const medW = ws[ws.length >> 1] || 4;
    const mergeR = Math.max(2, 1.3 * medW);   // endpoints this close share a junction
    const nodes = [];
    const nodeOf = (p) => { for (let i = 0; i < nodes.length; i++) if (dist(nodes[i], p) <= mergeR) return i; nodes.push({ x: p.x, y: p.y }); return nodes.length - 1; };
    for (const x of info) { x.n0 = nodeOf(x.center[0]); x.n1 = nodeOf(x.center[x.center.length - 1]); }

    const runs = [], unsewn = info.slice();
    let curNode = -1, curPos = null;
    while (unsewn.length) {
      let best = null;
      for (const x of unsewn) {
        for (const which of [0, 1]) {
          const enter = which === 0 ? x.center[0] : x.center[x.center.length - 1];
          const enNode = which === 0 ? x.n0 : x.n1;
          const shares = curNode >= 0 && enNode === curNode;
          const d = curNode < 0 ? enter.x : dist(curPos, enter);
          const cost = curNode < 0 ? enter.x : (shares ? d - 1e6 : d); // strongly prefer a shared junction
          if (!best || cost < best.cost) best = { x, which, enter, enNode, cost };
        }
      }
      const x = best.x; unsewn.splice(unsewn.indexOf(x), 1);
      const enter = best.enter, enNode = best.enNode;
      let center = x.center.slice(); if (best.which === 1) center.reverse();  // center[0] = enter
      const far = center[center.length - 1];
      const jump = curNode < 0 || enNode !== curNode;
      if (doUnderlay) {
        let satin = x.satin.slice(); if (dist(satin[0], far) > dist(satin[satin.length - 1], far)) satin.reverse(); // satin: far -> enter
        runs.push({ pts: center, kind: "underlay", jump });     // enter -> far (hidden under satin)
        runs.push({ pts: satin, kind: "satin", jump: false });  // far -> enter (exit at enter)
        curNode = enNode; curPos = enter;
      } else {
        let satin = x.satin.slice(); if (dist(satin[0], enter) > dist(satin[satin.length - 1], enter)) satin.reverse(); // enter -> far
        runs.push({ pts: satin, kind: "satin", jump });
        curNode = (enNode === x.n0) ? x.n1 : x.n0; curPos = far; // exit at the far end
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
