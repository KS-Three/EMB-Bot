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

  // Lay out `text` in a pre-digitized font. Returns:
  //   { runs:[[{x,y}…]], travels:[[from,to]], bbox:{x0,y0,x1,y1} }
  // in DESIGN PIXELS (y-down). runs are satin zig-zag point lists (consecutive
  // pairs = crosses); travels are needle-up hops between columns.
  // opts = { emMm=18, pxPerMm=10, spacingMm=0.4, pullCompMm=0, letterSpacingMm=0 }.
  function layoutText(font, text, opts) {
    const o = opts || {};
    const emMm = o.emMm || 18;
    const pxPerMm = o.pxPerMm || 10;
    const spacingMm = o.spacingMm || 0.4;
    const pullCompMm = o.pullCompMm || 0;
    const u2px = (emMm / font.unitsPerEm) * pxPerMm;       // font units -> design px
    const lsUnits = (o.letterSpacingMm || 0) * font.unitsPerEm / emMm;
    const chars = Array.from(text);

    const runs = [], travels = [];
    let penX = 0, prev = null, lastPt = null;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const acc = (p) => { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; };

    for (const ch of chars) {
      if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
      const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
      if (!g) { penX += font.advDefault; prev = null; continue; }
      if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
      const ox = penX;
      const TX = (x) => (x + ox) * u2px, TY = (y) => y * u2px;
      for (const col of g.cols) {
        const railA = col.railA.map((p) => ({ x: TX(p[0]), y: TY(p[1]) }));
        const railB = col.railB.map((p) => ({ x: TX(p[0]), y: TY(p[1]) }));
        const rungs = (col.rungs || []).map((rg) => [{ x: TX(rg[0][0]), y: TY(rg[0][1]) }, { x: TX(rg[1][0]), y: TY(rg[1][1]) }]);
        const pts = satinFromRails(railA, railB, rungs, { spacingMm, pxPerMm, pullCompMm });
        if (pts.length >= 2) {
          if (lastPt) travels.push([lastPt, pts[0]]);
          runs.push(pts);
          for (const p of pts) acc(p);
          lastPt = pts[pts.length - 1];
        }
      }
      penX += g.adv + lsUnits;
      prev = ch;
    }
    return { runs, travels, bbox: { x0, y0, x1, y1 } };
  }

  return { layoutText };
});
