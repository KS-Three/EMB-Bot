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
  // Cross-stitch fill. In the browser this arrives via root.EMB, which means
  // crossfill.js must be in ALL THREE engine-file lists (copy-engine.mjs,
  // emb.js, index.html) — miss the third and cross-stitch fonts break only in
  // the live Studio while every test stays green (COOKBOOK's standing trap).
  const crossfill = _node ? require("./crossfill.js") : root.EMB;
  const columnGeom = satinplay.columnGeom;
  const satinFromGeom = satinplay.satinFromGeom;
  const centerFromGeom = satinplay.centerFromGeom;
  const centerUnderlayFromGeom = satinplay.centerUnderlayFromGeom;
  const edgeUnderlayFromGeom = satinplay.edgeUnderlayFromGeom;
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // Law 50's underlay ladder, keyed to CAP height (see capHeightMm below for
  // how cap is obtained — it is measured from the font's own glyphs, not
  // assumed equal to the em). Thresholds are in FINAL SEWN mm.
  //
  //   under 5 mm   none      "Lettering with heights under 5 mm should not
  //                           have underlay"
  //   5 - 10 mm    center    center walk, 2 repeats, 3 mm stitch, 50% position
  //   over 10 mm   edge      contour, 3 mm stitch, 0.4 mm inset per side
  //
  // The published table's fourth row — extra-large jacket-back work gets a
  // second layer and a double zigzag for loft — is deliberately NOT
  // implemented. No vendor publishes the cap height where "large" becomes
  // "extra-large", so the threshold would be invented, and the same is true of
  // the >4 mm column-width zigzag cross-cut (the mechanism is cheap, but our
  // corpus is overwhelmingly sub-3 mm columns, so it would ship untested on
  // real work). Both are follow-ups, not silent approximations.
  const UNDERLAY_CAP_MIN_MM = 5;    // below this: none
  const UNDERLAY_CAP_EDGE_MM = 10;  // above this: edge run instead of center
  const UNDERLAY_STEP_MM = 3;       // Ink/Stitch center-walk + contour default
  const UNDERLAY_REPEATS = 2;       // Ink/Stitch center-walk default
  const UNDERLAY_INSET_MM = 0.4;    // Ink/Stitch contour default, per side
  // Law 51: ship a min-stitch floor, keep it at or under 0.5 mm, and never
  // apply a 1 mm floor globally — that is what shreds small lettering.
  const UNDERLAY_MIN_STITCH_MM = 0.5;

  // Which rung of the ladder a given final-sewn cap height lands on.
  function underlayModeForCapMm(capMm) {
    if (!(capMm > 0) || capMm < UNDERLAY_CAP_MIN_MM) return null;
    return capMm > UNDERLAY_CAP_EDGE_MM ? "edge" : "center";
  }

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
  // Every [x,y] a glyph's ink actually occupies — rails AND run paths. Run
  // paths were ignored here while the lettering path was satin-only, which was
  // harmless then; once a runs-only font can stitch, a cols-only scan returns
  // Infinity for it and every metric derived from it (baseline, ink centering,
  // cap height) collapses. Runs are either a bare [x,y][] or {pts:[x,y][]} —
  // see build-font.mjs runFrom — so accept both shapes.
  // Only STITCHABLE runs count as ink — the same {pts, lenMm} test routeRuns
  // uses. This is not a detail: satin fonts carry construction/centerline run
  // paths that are never sewn, and counting those as ink shifted measured cap
  // height and ink centering for every satin font (caught by satinfont.test.js
  // — emilio_20_bold's cap/em moved 16.47 -> 16.542, and circle-layout
  // baselines drifted with it). Geometry that will never be sewn is not ink.
  function glyphPoints(g) {
    const out = [];
    for (const col of (g.cols || [])) { out.push(col.railA, col.railB); }
    for (const r of (g.runs || [])) {
      if (!r || !r.pts || !(r.lenMm > 0)) continue;
      if (r.pts.length) out.push(r.pts);
    }
    return out;
  }

  // Will this glyph put thread down? Mirrors routeGlyph/routeRuns/crossFill —
  // satin columns sew, a run sews only with an authored stitch length (ROADMAP
  // gate 1 bars inventing one), and a cross-stitch region sews only when the
  // font carries the measured grid to fill it. Same rule as qc-font's
  // `stitchable`; if one changes, change both.
  function sewsSomething(font, g) {
    if ((g.cols || []).length) return true;
    if (font.crossGrid && (g.runs || []).some((r) => r && r.fill === "cross" && r.pts)) return true;
    return (g.runs || []).some((r) => r && r.pts && r.lenMm > 0);
  }

  const glyphBottomCache = new WeakMap();
  function glyphBottomUnits(g) {
    if (glyphBottomCache.has(g)) return glyphBottomCache.get(g);
    let maxy = -Infinity;
    for (const ring of glyphPoints(g)) {
      for (const p of ring) { if (p[1] > maxy) maxy = p[1]; }
    }
    const c = maxy > -Infinity ? maxy : 0;
    glyphBottomCache.set(g, c);
    return c;
  }
  function medianOf(nums) {
    const s = nums.slice().sort((a, b) => a - b);
    return s.length ? s[s.length >> 1] : 0;
  }

  // Horizontal INK extent of a glyph in its own frame (font units) — the min/
  // max x its rails actually reach, as opposed to its advance box. Arc layout
  // centers on ink (see below): advance includes side bearings AND the
  // trailing letter-spacing gap after the last glyph, neither of which is
  // visible, so centering on advance rotates the whole arch toward the
  // trailing end — most visibly at max letter spacing, where the end letters'
  // baselines miss each other by the full spacing amount (Kent's SCHAEFER
  // -180° report: 4.6mm end-to-end tilt at 5.5mm spacing).
  const glyphInkXCache = new WeakMap();
  function glyphInkXUnits(g) {
    let hit = glyphInkXCache.get(g);
    if (hit) return hit;
    let min = Infinity, max = -Infinity;
    for (const ring of glyphPoints(g)) {
      for (const p of ring) { if (p[0] < min) min = p[0]; if (p[0] > max) max = p[0]; }
    }
    hit = min <= max ? { min, max } : { min: 0, max: 0 };
    glyphInkXCache.set(g, hit);
    return hit;
  }

  // CAP HEIGHT, measured — not assumed (Law 46).
  //
  // Every published lettering rule (the underlay ladder, the small-text floor,
  // placement charts) is keyed to UPPER-CASE height. This runtime's size knob
  // is `emMm`, which is em height: `u2px = (emMm/unitsPerEm)*pxPerMm`. Those
  // are not the same number and the gap is not small — measured cap/em across
  // the 24 shipped JSON fonts runs 0.58 (chicken_scratch) to 0.97 (monicha),
  // with digory_doodles_bean a 1.50 outlier whose unitsPerEm is smaller than
  // its own cap. Gating the ladder on emMm would put geneva_simple's 5 mm cap
  // and monicha's 8.1 mm cap on the same rung.
  //
  // So measure it. A glyph's rails ARE its stroke outline, so the y-extent of
  // an upper-case reference glyph's rails is its ink height, i.e. the font's
  // cap height in font units. `H` is the standard reference (flat terminals,
  // no overshoot); every font in the corpus has one, and the fallback chain
  // below only exists for fonts we have not seen.
  //
  // If a font has NO upper-case reference glyph at all, we fall back to a
  // PROXY — emMm * 0.73, the measured median cap/em of the corpus — and say so
  // here rather than pretending em is cap. `capIsProxy` is returned alongside
  // so callers can tell the two apart. This path is unreachable for every font
  // we currently ship.
  const CAP_REF_CHARS = ["H", "E", "T", "I", "L", "F", "B", "D", "N", "M"];
  const CAP_EM_PROXY = 0.73;
  const capUnitsCache = new WeakMap();
  function capUnitsOf(font) {
    if (capUnitsCache.has(font)) return capUnitsCache.get(font);
    let out = null;
    for (const ch of CAP_REF_CHARS) {
      const g = font.glyphs && font.glyphs[ch];
      // Was `!g.cols.length` — that skipped every glyph of a runs-only font, so
      // cap height came back null and the font had no measured size reference.
      if (!g) continue;
      const rings = glyphPoints(g);
      if (!rings.length) continue;
      let mn = Infinity, mx = -Infinity;
      for (const ring of rings) {
        for (const p of ring) { if (p[1] < mn) mn = p[1]; if (p[1] > mx) mx = p[1]; }
      }
      if (mx > mn) { out = { units: mx - mn, ref: ch }; break; }
    }
    capUnitsCache.set(font, out);
    return out;
  }
  // Cap height of `font` at nominal size `emMm`, in mm. `proxy` is true when
  // no upper-case glyph was available and the corpus-median ratio was used.
  function capHeightMm(font, emMm) {
    const upm = font && font.unitsPerEm;
    const hit = upm > 0 ? capUnitsOf(font) : null;
    if (!hit) return { mm: emMm * CAP_EM_PROXY, proxy: true, ref: null };
    return { mm: (hit.units / upm) * emMm, proxy: false, ref: hit.ref };
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
  //
  // STRUCTURAL UNDERLAY (opts.underlay, Law 50). Before this commit this
  // option was passed in by layoutText and never read, so every satin letter
  // this engine has ever sewn went down bare and the app's underlay switch
  // moved nothing. It is now honored: when set, each span that sews as SATIN
  // gets its own underlay run emitted immediately before it, over the same
  // fraction span, in the same traversal direction. Both underlay forms are
  // closed walks that finish back at the span's f0 — the point the satin then
  // starts from — so real underlay adds no travel and no extra trims.
  //   opts.underlay = "center" | "edge" | null/false
  //   opts.underlayStepMm / underlayInsetMm / minStitchMm  (caller-space mm)
  //
  // Returns [{pts, kind:"satin"|"underlay"|"underpath", jump}].
  //
  // KIND RENAME, same commit. The Euler-walk travel spans used to be tagged
  // `kind: "underlay"`. They are not underlay — they are needle-down travel
  // between satin spans. They are now `"underpath"`, which is what the rest of
  // this file already called them in prose, and `"underlay"` now means only
  // the real thing. Downstream only ever tested for `"satin"` (digitize.js's
  // nSatin counter), so the stitch stream is unaffected; the tags are what
  // change, and they change so that these two can never be confused again.
  // Route a glyph's RUN paths (bean / running-stitch fonts). Satin fonts have
  // always had their run paths dropped here; this stitches them only when the
  // font itself authored a stitch length, which build-font.mjs attaches as
  // {pts, lenMm, repeats} and strips again for any font that has satin columns.
  // That is deliberate on two counts: ROADMAP gate 1 bars us from inventing a
  // physical stitch length, so a run with no authored length is not stitchable
  // and is skipped; and scoping to runs-only fonts keeps every shipped satin
  // font's stitch stream byte-identical.
  //
  // `runs` arrive already transformed into design px. Each is resampled at the
  // authored length and, when the font asks for bean repeats, each stitch is
  // backtracked r times (r=1 => the classic triple stitch), matching
  // Ink/Stitch's own per-stitch bean semantics rather than per-path passes.
  function routeRuns(runs, opts) {
    const pxPerMm = opts.pxPerMm;
    const out = [];
    let first = opts.firstIsJump !== false;
    for (const r of runs || []) {
      const pts = r && r.pts;
      if (!pts || pts.length < 2) continue;
      const stepPx = r.lenMm * pxPerMm;
      if (!(stepPx > 0)) continue;
      // Walk the polyline emitting a point every stepPx of arc length. The
      // final vertex is always kept so the stroke reaches its authored end.
      const walk = [pts[0]];
      let carry = 0;
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1], b = pts[i];
        const dx = b.x - a.x, dy = b.y - a.y;
        const seg = Math.hypot(dx, dy);
        if (!(seg > 0)) continue;
        let t = stepPx - carry;
        while (t <= seg) {
          walk.push({ x: a.x + (dx * t) / seg, y: a.y + (dy * t) / seg });
          t += stepPx;
        }
        carry = (carry + seg) % stepPx;
      }
      const last = pts[pts.length - 1];
      const tail = walk[walk.length - 1];
      if (Math.hypot(last.x - tail.x, last.y - tail.y) > 1e-9) walk.push(last);
      if (walk.length < 2) continue;
      const reps = r.repeats > 0 ? Math.round(r.repeats) : 0;
      let final = walk;
      if (reps > 0) {
        final = [walk[0]];
        for (let i = 1; i < walk.length; i++) {
          final.push(walk[i]);
          for (let k = 0; k < reps; k++) { final.push(walk[i - 1]); final.push(walk[i]); }
        }
      }
      out.push({ pts: final, kind: "run", jump: first });
      first = false;
    }
    return out;
  }

  function routeGlyph(cols, opts) {
    const pxPerMm = opts.pxPerMm, spacingMm = opts.spacingMm, pullCompMm = opts.pullCompMm || 0, slantDeg = opts.slantDeg || 0;
    const satinOpts = { spacingMm, pxPerMm, pullCompMm, slantDeg };
    const underlayMode = opts.underlay === "center" || opts.underlay === "edge" ? opts.underlay : null;
    const underlayOpts = underlayMode ? {
      pxPerMm,
      stepMm: opts.underlayStepMm == null ? UNDERLAY_STEP_MM : opts.underlayStepMm,
      insetMm: opts.underlayInsetMm == null ? UNDERLAY_INSET_MM : opts.underlayInsetMm,
      minStitchMm: opts.minStitchMm == null ? UNDERLAY_MIN_STITCH_MM : opts.minStitchMm,
      repeats: UNDERLAY_REPEATS,
    } : null;
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
        // Underlay first, then the satin that covers it. The generators take
        // the span in TRAVERSAL order (f0,f1 — not lo,hi), so the walk ends
        // where this satin run begins. A span too short to carry one stitch at
        // the minimum length returns [] and simply gets no underlay.
        if (sp.sat && underlayOpts) {
          const upts = underlayMode === "edge"
            ? edgeUnderlayFromGeom(geom, sp.f0, sp.f1, underlayOpts)
            : centerUnderlayFromGeom(geom, sp.f0, sp.f1, underlayOpts);
          if (upts && upts.length >= 2) { runs.push({ pts: upts, kind: "underlay", jump: first }); first = false; }
        }
        runs.push({ pts, kind: sp.sat ? "satin" : "underpath", jump: first });
        first = false;
      }
    }
    return runs;
  }

  // Lay out `text` in a pre-digitized font. Returns:
  //   { runs:[{pts:[{x,y}…], kind, jump}], bbox:{x0,y0,x1,y1}, cap:{…} }
  // in DESIGN PIXELS (y-down). Columns are routed per glyph with underpathing
  // (see routeGlyph). A run's jump=true means "lift needle & travel to its
  // start" (the caller trims if far); jump=false means "continue with a needle-
  // down running connector". opts = { emMm=18, pxPerMm=10, spacingMm=0.4,
  // pullCompMm=0, letterSpacingMm=0, underlay=true, fitScale=1, arcDeg=0,
  // circleLayout=false (two-line circular badge — contract documented at the
  // option below) }.
  //
  // `kind` is one of:
  //   "satin"     the cover stitching
  //   "underlay"  STRUCTURAL underlay under a satin span (Law 50's ladder)
  //   "underpath" needle-down Euler-walk travel between satin spans
  // "underpath" was called "underlay" before this commit, which conflated the
  // two — see routeGlyph's note.
  //
  // `cap` reports what the ladder decided and what it decided it from:
  //   { mm, finalMm, ref, proxy, underlay }
  // `ref` is the glyph the cap height was measured off; `proxy: true` means no
  // upper-case glyph existed and a corpus-median ratio was used instead.
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
    const arcDeg = o.arcDeg || 0;
    // ---- Structural underlay: Law 50's ladder, decided HERE (layoutText is
    // where the font, the size and the fit scale are all known at once) and
    // handed to routeGlyph as a resolved mode string.
    //
    // `o.underlay`:
    //   false          off — byte-identical geometry to before this commit.
    //   true / absent  AUTO: pick the ladder rung from the measured cap height.
    //   "none" | "center" | "edge"   force a rung (tests, and a future UI that
    //                  wants to override; the ladder is a default, not a law
    //                  of physics).
    //
    // `o.fitScale` (default 1) is the uniform scale a downstream caller will
    // apply to this layout — digitize.js's garment fit. It matters twice:
    // the ladder is keyed to FINAL SEWN cap height, and the ladder's own mm
    // constants (3 mm stitch, 0.4 mm inset, 0.5 mm floor) have to land at
    // those values on the garment, not in layout space. Both are handled by
    // dividing through here, exactly the way digitize.js already pre-divides
    // spacingMm and pullCompMm so the final density lands where it was asked.
    const fitScale = (typeof o.fitScale === "number" && isFinite(o.fitScale) && o.fitScale > 0) ? o.fitScale : 1;
    const cap = capHeightMm(font, emMm);
    const capFinalMm = cap.mm * fitScale;
    const forced = o.underlay === "none" || o.underlay === "center" || o.underlay === "edge" ? o.underlay : null;
    const underlayMode = o.underlay === false ? null
      : forced ? (forced === "none" ? null : forced)
      : underlayModeForCapMm(capFinalMm);
    const underlayOpts = underlayMode ? {
      underlay: underlayMode,
      underlayStepMm: UNDERLAY_STEP_MM / fitScale,
      underlayInsetMm: UNDERLAY_INSET_MM / fitScale,
      minStitchMm: UNDERLAY_MIN_STITCH_MM / fitScale,
    } : { underlay: null };
    // Two-line circular badge layout (Lettering parity round). Falsy (absent/
    // false/null) = today's behavior byte-identical (snapshot-pinned). Truthy:
    //   - The FIRST line arcs along the TOP of a circle (arch up, exactly the
    //     existing arcDeg>0 math) and the LAST line arcs along the BOTTOM
    //     (arch DOWN — the existing negative-arc "valley" math with one
    //     baseline-side correction, see the placement branch below), BOTH
    //     sharing ONE circle center, so a badge comes out concentric: every
    //     arc'd glyph's baseline sits at radius R from that shared center
    //     EXACTLY (derivation at the branch). The bottom line's glyphs stay
    //     upright (middle glyph rotation 0, tangent rotation elsewhere) and
    //     read left-to-right — not upside-down.
    //   - 3+ lines: first and last arc as above; the lines BETWEEN them stack
    //     STRAIGHT through the middle, each ink-centered on the circle's
    //     vertical axis, baseline-spaced by leading and vertically centered
    //     on the circle center — the classic badge "name arcs / EST. 2020
    //     straight / city arcs" composition.
    //   - Single line: that one line arcs along the top only (identical to a
    //     plain arcDeg layout at the derived span — pinned by test).
    // Radius contract — circleLayout is `true` or `{ radiusMm }`:
    //   - { radiusMm: N } pins the baseline-circle radius at N mm (nominal,
    //     BEFORE any downstream garment-fit scaling — the same nominal-mm
    //     semantics emMm/letterSpacingMm already have). Each arc'd line then
    //     spans inkSpanPx/R radians of the circle.
    //   - true (or an object without a positive radiusMm) derives R the same
    //     way single-line arcs already do — R = inkSpanPx / arcRad — using
    //     the WIDEST arc'd line's ink span, so no line ever exceeds |arcDeg|
    //     (default 180: the widest line hugs its full semicircle). arcDeg's
    //     SIGN is ignored in badge mode (top/bottom arch directions are what
    //     define a badge); `align` is ignored too (every line centers on the
    //     circle's own vertical axis).
    const circle = o.circleLayout ? (typeof o.circleLayout === "object" ? o.circleLayout : {}) : null;
    // Multi-line justification: how shorter lines sit relative to the widest
    // line. "center" (default) is the pre-existing behavior; "left"/"right"
    // flush-align instead. Single-line text and arc'd lines are unaffected
    // (one line has nothing to justify against; each arc'd line centers on
    // its own circle).
    const align = o.align === "left" || o.align === "right" ? o.align : "center";
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
    // Right-to-left fonts (Hebrew; 2026-08-22). Text is stored in LOGICAL
    // order — first letter first — and rendered with the first letter at the
    // RIGHT, so the only change needed is to walk each line's characters in
    // reverse when laying them out. Everything downstream (arc, badge,
    // per-letter colour, underlay) then works unchanged, because it all keys
    // off `ox` rather than off character order.
    //
    // charIdx deliberately keeps pointing at the ORIGINAL string position, not
    // the visual one: it exists so the UI can map a <textarea> selection onto
    // glyphs, and a selection is logical. Reversing it would silently colour
    // the wrong letters.
    //
    // Hebrew needs no more than this — it has no contextual letter forms.
    // Arabic DOES (initial/medial/final/isolated) and is deliberately NOT
    // enabled by this: without a joining engine its letters render unjoined,
    // which is wrong text rather than merely plain text. The three Arabic
    // fonts upstream stay out until that exists.
    const rtl = font.dir === "rtl";
    // Recorded with the source index so the report comes out in LOGICAL order.
    // An RTL line is walked in reverse, so collecting bare characters would
    // report "Emb" as b, m, E — technically the order they were laid out in,
    // and useless in a message to a human.
    const unsupportedAt = [];
    let globalIdx = 0;
    const lineList = rawLines.map((lineText, lineNum) => {
      const chars = Array.from(lineText);
      const lineStart = globalIdx;
      const order = chars.map((_, i) => i);
      if (rtl) order.reverse();
      let penX = 0, prev = null;
      const glyphs = [];
      for (const i of order) {
        const ch = chars[i];
        const charIdx = lineStart + i;
        if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
        const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
        // A character the font has no glyph for advances the pen and stitches
        // NOTHING, silently. That was survivable while the library was all
        // Latin; with Hebrew in it, picking a Hebrew font and typing "Emb"
        // produces a 0-stitch, 0x0mm design and no explanation anywhere. The
        // engine cannot decide what the UI should say, but it can stop hiding
        // the fact — so the characters it dropped are reported.
        if (!g) { unsupportedAt.push([charIdx, ch]); penX += font.advDefault; prev = null; continue; }
        // A glyph that EXISTS but sews nothing is the same silent gap wearing a
        // disguise, and the report has to cover it or it reads as a promise it
        // does not keep: type "ç" in western_light and the letter simply is not
        // there, while a character the font lacks outright gets a note.
        // Measured 2026-08-22 across the sellable library: two such glyphs,
        // western_light's "ç" and ondulamarif_XL's "º". The personal build is
        // where it bites — paquerette has 31 of its 52 letters in this state,
        // because only 72 of its 1,641 runs carry an authored stitch length.
        // Same test routeRuns and glyphPoints use, so "sews nothing" here means
        // exactly what the stitch path will do, not an approximation of it. The
        // glyph keeps its own advance: it is a hole of the right width, and
        // collapsing the text would be a second wrong answer.
        if (!sewsSomething(font, g)) {
          unsupportedAt.push([charIdx, ch]);
          penX += (g.adv || font.advDefault); prev = null; continue;
        }
        if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
        glyphs.push({ g, ox: penX, charIdx });
        penX += g.adv + lsUnits;
        prev = ch;
      }
      globalIdx = lineStart + chars.length;
      if (lineNum < rawLines.length - 1) globalIdx++; // the "\n" separator itself
      return { glyphs, adv: penX };
    });
    const maxAdvUnits = lineList.reduce((m, ln) => Math.max(m, ln.adv), 0);

    const runs = [];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const acc = (p) => { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; };

    const signArc = arcDeg > 0 ? 1 : (arcDeg < 0 ? -1 : 0);
    const arcRad = arcDeg ? Math.abs(arcDeg) * Math.PI / 180 : 0;

    // Ink x-extent of a measured line in design px (the same glyph-ink logic
    // the arc branch uses inline); null when the line has no glyphs.
    const lineInkPx = (line) => {
      if (!line.glyphs.length) return null;
      let minU = Infinity, maxU = -Infinity;
      for (const gl of line.glyphs) {
        const ext = glyphInkXUnits(gl.g);
        if (gl.ox + ext.min < minU) minU = gl.ox + ext.min;
        if (gl.ox + ext.max > maxU) maxU = gl.ox + ext.max;
      }
      return { start: minU * u2px, end: maxU * u2px };
    };
    // Circle-badge shared geometry (see the circleLayout contract above). One
    // radius R for the whole badge; the circle CENTER is fixed at (0, R) in
    // this layout's font-space (y-down), i.e. R below the top line's apex:
    // the top line's apex baseline then lands at y=0, exactly where a plain
    // arcDeg>0 first line would put it.
    let circleParams = null;
    if (circle) {
      const nLines = lineList.length;
      const topIdx = 0, botIdx = nLines > 1 ? nLines - 1 : -1;
      let maxSpanPx = 0;
      for (const li of (botIdx >= 0 ? [topIdx, botIdx] : [topIdx])) {
        const ink = lineInkPx(lineList[li]);
        if (ink && ink.end - ink.start > maxSpanPx) maxSpanPx = ink.end - ink.start;
      }
      let R;
      if (typeof circle.radiusMm === "number" && isFinite(circle.radiusMm) && circle.radiusMm > 0) {
        R = circle.radiusMm * pxPerMm;
      } else {
        const arcAbsRad = (Math.abs(arcDeg) || 180) * Math.PI / 180;
        R = maxSpanPx > 0 ? maxSpanPx / arcAbsRad : 0;
      }
      circleParams = { topIdx, botIdx, R, cy: R };
    }

    // ---- PLACEMENT pass.
    lineList.forEach((line, lineIdx) => {
      const lineYunits = lineIdx * leadingUnits;                  // font units, y-down: later lines sit below
      // Straight multi-line: place this line against the widest per `align`.
      const slack = maxAdvUnits - line.adv;
      const lineOriginXunits = arcDeg ? 0 : align === "left" ? 0 : align === "right" ? slack : slack / 2;
      // Arc geometry references the line's INK span, not its advance span:
      // advance carries invisible width (side bearings + one trailing
      // letter-spacing gap), and centering/radius built from it tilt the arch
      // toward the trailing end. Ink start/end come from each glyph's actual
      // rail extents (glyphInkXUnits) offset by its pen position.
      // Which role this line plays in circle-badge mode (null when off):
      // "top" arcs up, "bottom" arcs down on the same circle, "middle"
      // stacks straight through the center.
      const circleRole = circleParams
        ? (lineIdx === circleParams.topIdx ? "top" : lineIdx === circleParams.botIdx ? "bottom" : "middle")
        : null;
      let inkStartPx = 0, inkEndPx = 0;
      if ((arcDeg || circleParams) && line.glyphs.length) {
        const ink = lineInkPx(line);
        inkStartPx = ink.start;
        inkEndPx = ink.end;
      }
      const inkSpanPx = inkEndPx - inkStartPx;
      const inkMidPx = (inkStartPx + inkEndPx) / 2;
      const R = arcDeg && inkSpanPx > 0 ? (inkSpanPx / arcRad) : 0; // px; arc radius for this line (plain-arc mode)
      // Shared rotation-pivot height for every glyph in this line: the MEDIAN
      // of each glyph's own baseline (see glyphBottomUnits above). One value
      // per line (not each glyph's own reference) keeps every letter's
      // baseline aligned on the SAME arc; using the true baseline (not the
      // vertical center) keeps that arc at the radius the curve was actually
      // designed for, instead of collapsed inward by half a letter-height.
      const baselinePx = (arcDeg || circleParams) && line.glyphs.length
        ? medianOf(line.glyphs.map((gl) => glyphBottomUnits(gl.g))) * u2px
        : 0;
      // Circle-badge middle band: baseline of middle line k (0-based within
      // the band) sits at cy + (k - (count-1)/2) * leading — the band is
      // vertically centered on the circle center and keeps normal leading.
      let midBaseY = 0;
      if (circleRole === "middle") {
        const midCount = lineList.length - 2;
        const midRank = lineIdx - 1;
        midBaseY = circleParams.cy + (midRank - (midCount - 1) / 2) * leadingUnits * u2px;
      }

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
        // Run paths that carry an authored stitch length (bean/running-stitch
        // fonts). Only the {pts, lenMm} shape qualifies, so satin fonts — whose
        // runs build-font.mjs leaves as bare arrays — contribute nothing here
        // and their stitch stream is unchanged. Satin first, then runs: the
        // runs are the glyph's own strokes, not travel between columns.
        const stitchableRuns = (g.runs || []).filter((r) => r && r.pts && r.lenMm > 0);
        const gCols = routeGlyph(cols, Object.assign({ pxPerMm, spacingMm, pullCompMm, slantDeg }, underlayOpts));
        let gRuns = stitchableRuns.length
          ? gCols.concat(routeRuns(
              stitchableRuns.map((r) => ({
                pts: r.pts.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })),
                lenMm: r.lenMm,
                repeats: r.repeats,
              })),
              { pxPerMm, firstIsJump: gCols.length === 0 }))
          : gCols;

        // Cross-stitch regions. The lattice was measured from the whole font at
        // import (font.crossGrid, in glyph units) and is scaled here by the very
        // same u2px the outlines are — so cells stay square, stay aligned across
        // letters, and scale with the design instead of pinning a millimetre
        // size the fabric was never asked about.
        const crossRuns = (g.runs || []).filter((r) => r && r.fill === "cross" && r.pts);
        if (font.crossGrid && crossRuns.length && crossfill && crossfill.crossFill) {
          const rings = crossRuns.map((r) => r.pts.map((p) => ({ x: TX(p[0]), y: TY(p[1]) })));
          const lat = {
            step: font.crossGrid.step * u2px,
            // offsets share the glyph's own x-shift, so the grid travels with it
            offX: (font.crossGrid.offX + ox) * u2px,
            offY: font.crossGrid.offY * u2px,
          };
          const cf = crossfill.crossFill(rings, lat, {
            method: crossRuns[0].method || font.crossGrid.method,
            firstIsJump: gRuns.length === 0,
          });
          if (cf.length) gRuns = gRuns.concat(cf);
        }

        let place;
        if (circleRole === "middle") {
          // Straight middle band: ink-centered on the circle's vertical axis
          // (x=0 through the shared center), baseline moved onto this line's
          // stacked position. A pure translate — glyphs are not rotated.
          place = (p) => ({ x: p.x - inkMidPx, y: p.y - baselinePx + midBaseY });
        } else if (circleRole) {
          // Circle-badge top/bottom arc. Same rigid per-glyph motion as the
          // plain-arc branch below with the line-level knobs swapped: the
          // radius is the SHARED badge radius Rc (not this line's own
          // span-derived one), the arch sign is fixed per role (+1 top arch-
          // up, -1 bottom arch-down), and the line's vertical anchor WyBase
          // replaces lineYunits — chosen so both arcs share ONE center:
          //   center = (0, cy). Top:    WyBase = cy - Rc (apex baseline at
          //   the circle's topmost point). Bottom: WyBase = cy + Rc (middle
          //   glyph's baseline at the circle's bottommost point).
          // Derivation that baselines sit ON the circle exactly: a glyph at
          // arc angle theta maps its baseline anchor to
          //   (Rc*sin(theta), WyBase + sgn*Rc*(1 - cos(theta)))
          // and center.y - that.y = sgn*Rc - sgn*Rc*(1-cos) = sgn*Rc*cos, so
          // dist from center = Rc*sqrt(sin^2+cos^2) = Rc for EVERY glyph on
          // BOTH lines — the badge is concentric by construction.
          // The bottom line is thus the existing negated-curvature "valley"
          // path (phi = -theta keeps each glyph's baseline tangent to the
          // circle with its ink pointing INWARD — i.e. screen-up at the
          // bottom of the circle: upright, reading left-to-right) plus the
          // baseline-side correction WyBase = cy + Rc that drops the
          // valley's midpoint onto the shared circle's bottom.
          const sgnC = circleRole === "top" ? 1 : -1;
          const Rc = circleParams.R;
          const ext = glyphInkXUnits(g);
          const inkCenterPx = (ox + (ext.min + ext.max) / 2) * u2px;
          const sPx = inkCenterPx - inkMidPx;
          const theta = Rc > 0 ? sPx / Rc : 0;
          const phi = sgnC * theta;
          const cosPhi = Math.cos(phi), sinPhi = Math.sin(phi);
          const Wx = Rc * Math.sin(theta);
          const Wy = (circleParams.cy - sgnC * Rc) + sgnC * Rc * (1 - Math.cos(theta));
          place = (p) => {
            const lx = p.x - inkCenterPx, ly = p.y - baselinePx;
            return { x: Wx + lx * cosPhi - ly * sinPhi, y: Wy + lx * sinPhi + ly * cosPhi };
          };
        } else if (!arcDeg) {
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
          // The glyph's INK CENTER is both its arc-position parameter and its
          // rotation pivot — using the pen center for either re-introduces
          // the glyph's own bearing asymmetry as a visible tilt (an H whose
          // ink sits right-of-center in its advance box would lean ~8° at the
          // apex if positioned by ink but pivoted by pen).
          const ext = glyphInkXUnits(g);
          const inkCenterPx = (ox + (ext.min + ext.max) / 2) * u2px;
          const sPx = inkCenterPx - inkMidPx;
          const theta = R > 0 ? sPx / R : 0;
          const phi = signArc * theta;
          const cosPhi = Math.cos(phi), sinPhi = Math.sin(phi);
          const Wx = R * Math.sin(theta);
          const Wy = lineYunits * u2px + signArc * R * (1 - Math.cos(theta));
          place = (p) => {
            const lx = p.x - inkCenterPx, ly = p.y - baselinePx;
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
    return {
      runs,
      bbox: { x0, y0, x1, y1 },
      cap: { mm: cap.mm, finalMm: capFinalMm, ref: cap.ref, proxy: cap.proxy, underlay: underlayMode },
      // Distinct characters this font had no glyph for, in the order they
      // appear in the SOURCE text. Empty for every font/text pair that works,
      // so a caller can treat a non-empty array as "tell the user".
      unsupported: [...new Set(unsupportedAt.sort((a, b) => a[0] - b[0]).map((e) => e[1]))],
    };
  }

  return { layoutText, capHeightMm, underlayModeForCapMm };
});
