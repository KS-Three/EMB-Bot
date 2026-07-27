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

  // This font format has no explicit baseline field — glyph y-coordinates are
  // authored relative to an arbitrary top-of-canvas origin (e.g. this repo's
  // geneva_simple font sits its cap letters around y=27..63, not near y=0).
  // For straight layout that arbitrary origin doesn't matter (every glyph
  // shares it, so rows stay level); for arcing text we need a real pivot
  // height, or rotation swings the ink (which can be 60+ units from y=0) by a
  // huge lateral distance and scrambles glyph order.
  //
  // The pivot MUST be the baseline (where letters rest — i.e. the BOTTOM of a
  // glyph's ink, the max y in this y-down font space), not its vertical
  // CENTER: a glyph's center varies hugely with its own height (a full
  // cap-height "A"/"t" vs an x-height "a"/"n"), so averaging centers across a
  // line put the whole arc's baseline ~30% of a letter's height away from
  // where it should sit — every letter floated off the intended curve by the
  // same large, constant amount (confirmed empirically: ~5mm inward at
  // emMm=18). Bottoms, by contrast, are nearly IDENTICAL across almost every
  // non-descending glyph in this font (empirically ~62-63 font units for caps
  // AND x-height letters alike) — descenders (g/j/p/q/y) are the exception,
  // dropping well below. So: take each glyph's own bottom, memoized per glyph
  // object since the same glyph repeats often, and combine them with the
  // MEDIAN (not mean) across the line so a stray descender can't drag the
  // whole line's reference down.
  const glyphBottomCache = new WeakMap();
  function glyphBottomUnits(g) {
    if (glyphBottomCache.has(g)) return glyphBottomCache.get(g);
    let maxy = -Infinity;
    for (const col of g.cols) {
      for (const p of col.railA) { if (p[1] > maxy) maxy = p[1]; }
      for (const p of col.railB) { if (p[1] > maxy) maxy = p[1]; }
    }
    const c = maxy > -Infinity ? maxy : 0;
    glyphBottomCache.set(g, c);
    return c;
  }
  function medianOf(nums) {
    const s = nums.slice().sort((a, b) => a - b);
    return s.length ? s[s.length >> 1] : 0;
  }

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
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0, slantDeg = opts.slantDeg || 0;
    const satinOpts = { spacingMm, pxPerMm, pullCompMm, slantDeg };
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
    // Undirected multigraph of edge INSTANCES. Chinese-Postman: per component,
    // make it Eulerian by DUPLICATING only a minimal set of edges (greedy odd-
    // node pairing along shortest edge-paths). Duplicated instances become the
    // running underpath (covered by the satin); every other edge is sewn once as
    // satin. This adds travel ONLY where needed — no doubling everywhere, so
    // intersections don't pile up extra density.
    const adj = nodes.map(() => []);       // per node: {inst, to}
    const inst = [];                        // {ei, a, b}
    const addInst = (ei, a, b) => { const id = inst.length; inst.push({ ei, a, b }); adj[a].push({ inst: id, to: b }); adj[b].push({ inst: id, to: a }); };
    edges.forEach((e, ei) => addInst(ei, e.na, e.nb));

    // connected components
    const comp = nodes.map(() => -1); let nc = 0;
    for (let s = 0; s < nodes.length; s++) {
      if (comp[s] !== -1 || !adj[s].length) continue;
      comp[s] = nc; const q = [s];
      while (q.length) { const u = q.pop(); for (const e of adj[u]) if (comp[e.to] === -1) { comp[e.to] = nc; q.push(e.to); } }
      nc++;
    }
    const compNodes = []; for (let c = 0; c < nc; c++) compNodes.push([]);
    nodes.forEach((n, i) => { if (comp[i] >= 0) compNodes[comp[i]].push(i); });
    compNodes.sort((a, b) => Math.min.apply(null, a.map((i) => nodes[i].x)) - Math.min.apply(null, b.map((i) => nodes[i].x)));

    const runs = [];
    for (const cnodes of compNodes) {
      if (!cnodes.length) continue;
      const deg = {}; for (const i of cnodes) deg[i] = adj[i].length;
      let odd = cnodes.filter((i) => deg[i] % 2 === 1);
      // greedy: pair odd nodes, duplicating edges along the shortest path between
      // them (parity of interior nodes is preserved; both endpoints go even).
      let guard = 0;
      while (odd.length > 2 && guard++ < 200) {
        const u = odd[0];
        const prevN = {}, prevI = {}, seen = new Set([u]); const q = [u]; let tgt = -1;
        while (q.length) { const x = q.shift(); if (x !== u && deg[x] % 2 === 1) { tgt = x; break; } for (const e of adj[x]) if (!seen.has(e.to)) { seen.add(e.to); prevN[e.to] = x; prevI[e.to] = e.inst; q.push(e.to); } }
        if (tgt < 0) break;
        let x = tgt; while (x !== u) { const p = prevN[x]; const ii = inst[prevI[x]]; addInst(ii.ei, ii.a, ii.b); deg[x]++; deg[p]++; x = p; }
        odd = cnodes.filter((i) => deg[i] % 2 === 1);
      }
      // Hierholzer Euler trail over the (now near-Eulerian) multigraph.
      const start = odd.length ? odd[0] : cnodes.reduce((a, b) => (nodes[a].x <= nodes[b].x ? a : b));
      const used = new Set(); const ptr = {}; for (const i of cnodes) ptr[i] = 0;
      const st = [start], edgeSt = [], circuit = [];
      while (st.length) {
        const v = st[st.length - 1];
        while (ptr[v] < adj[v].length && used.has(adj[v][ptr[v]].inst)) ptr[v]++;
        if (ptr[v] < adj[v].length) { const e = adj[v][ptr[v]++]; used.add(e.inst); edgeSt.push({ inst: e.inst, from: v }); st.push(e.to); }
        else { st.pop(); if (edgeSt.length) circuit.push(edgeSt.pop()); }
      }
      circuit.reverse();
      if (!circuit.length) continue;
      // reverse-dedupe by span id: LAST visit sews as satin, earlier as running
      const isSatin = new Array(circuit.length); const seenEi = new Set();
      for (let k = circuit.length - 1; k >= 0; k--) { const ei = inst[circuit[k].inst].ei; if (seenEi.has(ei)) isSatin[k] = false; else { seenEi.add(ei); isSatin[k] = true; } }
      // typed spans (with traversal direction), collapse contiguous
      const spans = [];
      for (let k = 0; k < circuit.length; k++) {
        const c = circuit[k], e = edges[inst[c.inst].ei];
        const fwd = c.from === e.na; const f0 = fwd ? e.f0 : e.f1, f1 = fwd ? e.f1 : e.f0;
        const sat = isSatin[k]; const prev = spans[spans.length - 1];
        if (prev && prev.gi === e.gi && prev.sat === sat && Math.abs(prev.f1 - f0) < 1e-6) prev.f1 = f1;
        else spans.push({ gi: e.gi, sat, f0, f1 });
      }
      let first = true;
      for (const sp of spans) {
        const geom = G[sp.gi].geom; const lo = Math.min(sp.f0, sp.f1), hi = Math.max(sp.f0, sp.f1);
        let pts = sp.sat ? satinFromGeom(geom, lo, hi, satinOpts) : centerFromGeom(geom, lo, hi, 2, pxPerMm);
        if (!pts || pts.length < 2) continue;
        if (sp.f1 < sp.f0) pts = pts.slice().reverse();
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
  // pullCompMm=0, letterSpacingMm=0, underlay=true, arcDeg=0 }.
  //
  // `text` may contain "\n" for multiple lines, stacked by `font.leading`
  // (falls back to unitsPerEm). `opts.arcDeg` bends a line onto a circular
  // arc: positive arcs ARCH UP (rainbow — middle higher than the ends) in the
  // final rendered/sewn output; negative flips to a valley (ends higher). 0
  // or absent is today's straight behavior, unchanged.
  //
  // Two-pass per line: MEASURE walks the existing advance/kerning/letter-
  // spacing logic to record each glyph's pen offset (font units) and the
  // line's total advance, WITHOUT placing anything. PLACEMENT then routes
  // each glyph in its own straight/local frame — byte-identical inputs to the
  // pre-arc/multi-line code — and applies a per-glyph affine to the FINISHED
  // run points (routeGlyph is a rigid, orientation-agnostic geometry step, so
  // transforming its output is equivalent to transforming its input, and
  // touches none of its internals): for straight lines this is just a
  // per-line translate (identity for single-line text, so the single-line
  // legacy output is byte-for-byte unchanged); for an arc, a rotation about
  // the glyph's own pen-center followed by a translation onto the circle.
  function layoutText(font, text, opts) {
    const o = opts || {};
    const emMm = o.emMm || 18;
    const pxPerMm = o.pxPerMm || 10;
    const spacingMm = o.spacingMm || 0.4;
    const pullCompMm = o.pullCompMm || 0;
    const slantDeg = o.slantDeg || 0;
    const doUnderlay = o.underlay !== false;
    const arcDeg = o.arcDeg || 0;
    const u2px = (emMm / font.unitsPerEm) * pxPerMm;       // font units -> design px
    const lsUnits = (o.letterSpacingMm || 0) * font.unitsPerEm / emMm;
    const leadingUnits = font.leading || font.unitsPerEm;

    // ---- MEASURE pass: split on "\n"; per line, walk chars accumulating pen
    // position (kerning resets at each line start) and record each glyph's
    // {g, ox} (ox = pen x at glyph start, font units) plus the line's total
    // advance. No placement happens here.
    // charIdx (Font editing abilities Round 1, per-letter color): the index
    // of each glyph's SOURCE CHARACTER in the original `text` string,
    // counting "\n" as one position — matching a <textarea>'s native
    // selectionStart/selectionEnd exactly, so the UI can let a user select
    // text and tag that range with a color with zero custom index math.
    const rawLines = String(text).split("\n");
    let globalIdx = 0;
    const lineList = rawLines.map((lineText, lineNum) => {
      const chars = Array.from(lineText);
      let penX = 0, prev = null;
      const glyphs = [];
      for (const ch of chars) {
        const charIdx = globalIdx++;
        if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
        const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
        if (!g) { penX += font.advDefault; prev = null; continue; }
        if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
        glyphs.push({ g, ox: penX, charIdx });
        penX += g.adv + lsUnits;
        prev = ch;
      }
      if (lineNum < rawLines.length - 1) globalIdx++; // the "\n" separator itself
      return { glyphs, adv: penX };
    });
    const maxAdvUnits = lineList.reduce((m, ln) => Math.max(m, ln.adv), 0);

    const runs = [];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const acc = (p) => { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; };

    const signArc = arcDeg > 0 ? 1 : (arcDeg < 0 ? -1 : 0);
    const arcRad = arcDeg ? Math.abs(arcDeg) * Math.PI / 180 : 0;

    // ---- PLACEMENT pass.
    lineList.forEach((line, lineIdx) => {
      const lineYunits = lineIdx * leadingUnits;                  // font units, y-down: later lines sit below
      const lineOriginXunits = arcDeg ? 0 : (maxAdvUnits - line.adv) / 2; // straight multi-line: center vs widest
      const lineAdvPx = line.adv * u2px;
      const R = arcDeg ? (lineAdvPx / arcRad) : 0;                 // px; arc radius for this line
      // Shared rotation-pivot height for every glyph in this line: the MEDIAN
      // of each glyph's own baseline (see glyphBottomUnits above). One value
      // per line (not each glyph's own reference) keeps every letter's
      // baseline aligned on the SAME arc; using the true baseline (not the
      // vertical center) keeps that arc at the radius the curve was actually
      // designed for, instead of collapsed inward by half a letter-height.
      const baselinePx = arcDeg && line.glyphs.length
        ? medianOf(line.glyphs.map((gl) => glyphBottomUnits(gl.g))) * u2px
        : 0;

      for (const { g, ox, charIdx } of line.glyphs) {
        // Route in the glyph's own straight/local frame — identical to the
        // pre-refactor TX/TY, so routeGlyph's inputs (and thus its internal
        // distance-based decisions) are completely unaffected by arc/multi-line.
        const TX = (x) => (x + ox) * u2px, TY = (y) => y * u2px;
        const cols = g.cols.map((col) => ({
          railA: col.railA.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })),
          railB: col.railB.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })),
          rungs: (col.rungs || []).map((rg) => [{ x: TX(rg[0][0]), y: TY(rg[0][1]) }, { x: TX(rg[1][0]), y: TY(rg[1][1]) }]),
        }));
        const gRuns = routeGlyph(cols, { pxPerMm, spacingMm, pullCompMm, slantDeg, underlay: doUnderlay });

        let place;
        if (!arcDeg) {
          // Straight: pure per-line translate. Single-line text has
          // lineOriginXunits===0 and lineYunits===0, so `place` is the
          // identity — the legacy single-line output is unchanged.
          const dx = lineOriginXunits * u2px, dy = lineYunits * u2px;
          place = dx === 0 && dy === 0 ? (p) => p : (p) => ({ x: p.x + dx, y: p.y + dy });
        } else {
          // Arc: rotate this glyph's points about its own pen-center by
          // phi = signArc*theta (theta = signed pen-center offset from the
          // line's middle, in radians of arc), then translate the pen-center
          // onto the circle. The circle's center sits `R` further along +y
          // (font-space y-down) than the line's baseline when arcDeg>0 (so
          // the line's middle — theta=0 — is the circle's topmost point and
          // the ends sag down into the render's up direction after the
          // downstream y-flip: ARCH UP); arcDeg<0 puts the center at -R
          // (middle is the circle's bottommost point: a valley).
          const penCenterPx = (ox + g.adv / 2) * u2px;
          const sPx = penCenterPx - lineAdvPx / 2;
          const theta = R > 0 ? sPx / R : 0;
          const phi = signArc * theta;
          const cosPhi = Math.cos(phi), sinPhi = Math.sin(phi);
          const Wx = R * Math.sin(theta);
          const Wy = lineYunits * u2px + signArc * R * (1 - Math.cos(theta));
          place = (p) => {
            const lx = p.x - penCenterPx, ly = p.y - baselinePx;
            return { x: Wx + lx * cosPhi - ly * sinPhi, y: Wy + lx * sinPhi + ly * cosPhi };
          };
        }

        for (const r of gRuns) {
          const pts = r.pts.map(place);
          for (const q of pts) acc(q);
          runs.push({ pts, kind: r.kind, jump: r.jump, charIdx });
        }
      }
    });
    return { runs, bbox: { x0, y0, x1, y1 } };
  }

  return { layoutText };
});
