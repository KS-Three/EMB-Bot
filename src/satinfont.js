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

  // Order a glyph's columns for sewing: greedy nearest-neighbour from the pen
  // position, reversing a column when its far end is the closer entry — so the
  // needle always enters the nearest column end and inter-column travel stays
  // short (and local to a junction).
  function orderColumns(cols, startPt) {
    const rem = cols.slice(), out = [];
    let cur = startPt;
    while (rem.length) {
      let bi = 0, brev = false, bd = Infinity;
      for (let i = 0; i < rem.length; i++) {
        const rA = rem[i].railA; const s = rA[0], e = rA[rA.length - 1];
        const ds = dist(s, cur), de = dist(e, cur);
        if (ds < bd) { bd = ds; bi = i; brev = false; }
        if (de < bd) { bd = de; bi = i; brev = true; }
      }
      const c = rem.splice(bi, 1)[0];
      if (brev) { c.railA.reverse(); c.railB.reverse(); if (c.rungs) c.rungs.reverse(); }
      out.push(c);
      const rA = c.railA; cur = rA[rA.length - 1];
    }
    return out;
  }

  // Lay out `text` in a pre-digitized font. Returns:
  //   { runs:[{pts:[{x,y}…], kind:"underlay"|"satin"}], bbox:{x0,y0,x1,y1} }
  // in DESIGN PIXELS (y-down). Each satin column gets a center-walk underlay run
  // (sewn first, hidden under the satin). Columns are ordered nearest-neighbour
  // so travel between them is short. opts = { emMm=18, pxPerMm=10, spacingMm=0.4,
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
      for (const c of orderColumns(cols, { x: ox * u2px, y: 0 })) {
        const satin = satinFromRails(c.railA, c.railB, c.rungs, { spacingMm, pxPerMm, pullCompMm });
        if (satin.length < 2) continue;
        if (doUnderlay) {
          let under = centerRun(c.railA, c.railB, c.rungs, { stepMm: 2, pxPerMm });
          // orient underlay to END where the satin STARTS (contiguous, no jump)
          if (under.length >= 2) {
            if (dist(under[under.length - 1], satin[0]) > dist(under[0], satin[0])) under = under.slice().reverse();
            runs.push({ pts: under, kind: "underlay" });
            for (const p of under) acc(p);
          }
        }
        runs.push({ pts: satin, kind: "satin" });
        for (const p of satin) acc(p);
      }
      penX += g.adv + lsUnits;
      prev = ch;
    }
    return { runs, bbox: { x0, y0, x1, y1 } };
  }

  return { layoutText };
});
