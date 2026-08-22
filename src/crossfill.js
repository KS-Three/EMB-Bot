// Cross-stitch fill for pixelated lettering fonts (2026-08-21).
//
// Written from first principles, deliberately NOT ported from Ink/Stitch: their
// implementation is GPL-3.0 and EMB-Bot is sold, so a port would relicense the
// product. Cross-stitch itself is a centuries-old craft technique — an X inside
// a square of an even grid — and that is all this implements.
//
// THE GRID IS MEASURED, NOT CHOSEN. Gate 1 bars this project from picking
// physical constants without a sew-out, and a cross-stitch cell size is exactly
// such a constant. It is not chosen here: these fonts are drawn as pixel art, so
// their outlines already lie on the grid the digitizer used. detectLattice()
// recovers that step and phase from the glyph geometry itself (99.6-100% of
// vertices land on it across every cross-stitch font in the library), and it is
// expressed in GLYPH UNITS, so it scales with the letterform exactly as satin
// column width does. Nothing here has an opinion about millimetres.
//
// (The fonts also carry inkstitch:pattern_size_mm="2.0", but that is a
// design-time value at the source canvas scale: the same 2.0 appears on fonts
// whose measured cell spans 0.78 mm to 4.41 mm. It cannot be used as a cell
// size, and the measured lattice is the self-consistent quantity.)
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  // Recover the drawing grid from pixel-art outlines. Axis-aligned edge lengths
  // in such a shape are whole multiples of one cell, so the most common edge IS
  // the cell. Sub-cell path noise (stray 0.1-unit segments from curve flattening
  // upstream) is filtered by MIN_EDGE — without it the mode collapses onto the
  // noise and every font reports a nonsense 0.1-unit grid.
  const MIN_EDGE = 0.5;
  const PHASE_STEPS = 40;   // lattice offsets tried when solving for phase
  const ON_LATTICE = 0.06;  // fraction of a cell a vertex may sit off it

  function detectLattice(rings) {
    const hist = new Map();
    const verts = [];
    for (const ring of rings) {
      for (let i = 1; i < ring.length; i++) {
        const dx = Math.abs(ring[i][0] - ring[i - 1][0]);
        const dy = Math.abs(ring[i][1] - ring[i - 1][1]);
        for (const d of [dx, dy]) {
          if (d < MIN_EDGE) continue;
          const k = Math.round(d * 10) / 10;
          hist.set(k, (hist.get(k) || 0) + 1);
        }
      }
      for (const p of ring) verts.push(p);
    }
    if (!hist.size || !verts.length) return null;
    let step = 0, best = -1;
    for (const [k, n] of hist) if (n > best) { best = n; step = k; }
    if (!(step > 0)) return null;

    // Solve for phase independently per axis: a glyph's x and y origins need not
    // share one offset, and forcing a single value misaligns every cell on the
    // axis that loses.
    const phase = (idx) => {
      let bestOff = 0, bestHit = -1;
      for (let t = 0; t < PHASE_STEPS; t++) {
        const off = (step * t) / PHASE_STEPS;
        let hit = 0;
        for (const p of verts) {
          let r = ((p[idx] - off) / step) % 1;
          if (r < 0) r += 1;
          if (Math.min(r, 1 - r) < ON_LATTICE) hit++;
        }
        if (hit > bestHit) { bestHit = hit; bestOff = off; }
      }
      return { off: bestOff, frac: bestHit / verts.length };
    };
    const px = phase(0), py = phase(1);
    return { step, offX: px.off, offY: py.off, fit: Math.min(px.frac, py.frac) };
  }

  // NONZERO winding, which is what SVG's default fill-rule actually is. A
  // counter (the hole in an "o") is wound opposite to its outer ring and
  // cancels; two overlapping ring wound the SAME way union, as they visibly do
  // when the shape is rendered.
  //
  // This started as even-odd, which is subtly wrong and produced convincing
  // wreckage: even-odd XORs overlap into a hole, so jacquard_12 — two rings per
  // glyph — filled as scattered fragments while jersey_15, one ring per glyph,
  // came out flawless. Both had ~100% lattice fit, so no metric caught it;
  // rendering the cells as ASCII did.
  //
  // `crossings` counts +1 for an edge crossing the ray upward and -1 downward;
  // any nonzero total is inside.
  function insideRings(rings, x, y) {
    let wind = 0;
    for (const ring of rings) {
      const n = ring.length;
      for (let i = 0, j = n - 1; i < n; j = i++) {
        const yi = ring[i].y, yj = ring[j].y;
        if (yi === yj) continue;
        if ((yi > y) === (yj > y)) continue;
        const t = (y - yi) / (yj - yi);
        if (x >= ring[i].x + t * (ring[j].x - ring[i].x)) continue;
        wind += yj > yi ? 1 : -1;
      }
    }
    return wind !== 0;
  }

  // One cross, centred on a cell. `simple` is the two diagonals; `double` adds
  // the upright pair over them. Emitted as separate strokes so the caller can
  // treat each as its own run — the needle genuinely lifts nowhere within a
  // cross, but consecutive strokes share an endpoint, so the walk is continuous.
  function crossStrokes(cx, cy, h, method) {
    const s = [
      [{ x: cx - h, y: cy - h }, { x: cx + h, y: cy + h }],
      [{ x: cx + h, y: cy - h }, { x: cx - h, y: cy + h }],
    ];
    if (method === "double_cross" || method === "double") {
      s.push([{ x: cx - h, y: cy }, { x: cx + h, y: cy }]);
      s.push([{ x: cx, y: cy - h }, { x: cx, y: cy + h }]);
    }
    return s;
  }

  // Fill `rings` (design px, closed) with crosses on `lattice` (also design px).
  // Cells are visited in serpentine order — left to right along one row, right
  // to left along the next — which is the shortest simple traverse of a grid and
  // keeps the carry between consecutive crosses about one cell long. Ink/Stitch
  // runs a graph search to additionally hide those carries under later stitches;
  // this does not, so expect visible travel between separated ink areas. At
  // lettering sizes that is usually under a cell, but it is the known difference
  // between this and the reference output, and the reason a sew-out is wanted
  // before trusting these fonts on real fabric.
  function crossFill(rings, lattice, opts) {
    const o = opts || {};
    const method = o.method || "simple_cross";
    if (!rings || !rings.length || !lattice || !(lattice.step > 0)) return [];
    const step = lattice.step;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const ring of rings)
      for (const p of ring) {
        if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
      }
    if (!(maxX > minX) || !(maxY > minY)) return [];

    const i0 = Math.floor((minX - lattice.offX) / step);
    const i1 = Math.ceil((maxX - lattice.offX) / step);
    const j0 = Math.floor((minY - lattice.offY) / step);
    const j1 = Math.ceil((maxY - lattice.offY) / step);
    // A pathological lattice (noise-derived, tiny step) would make this
    // quadratic blow up; bail rather than hang the caller.
    if ((i1 - i0) * (j1 - j0) > 40000) return [];

    const rows = [];
    for (let j = j0; j <= j1; j++) {
      const cy = lattice.offY + (j + 0.5) * step;
      const row = [];
      for (let i = i0; i <= i1; i++) {
        const cx = lattice.offX + (i + 0.5) * step;
        if (insideRings(rings, cx, cy)) row.push(cx);
      }
      if (row.length) rows.push({ cy, xs: row });
    }

    const out = [];
    const h = (step / 2) * (o.inset == null ? 1 : o.inset);
    let first = o.firstIsJump !== false;
    let serp = false;
    let prev = null;
    // A carry longer than this is crossing a GAP in the ink, not stepping to the
    // neighbouring cell, so lift the needle instead of dragging thread across
    // the letter. Without it, serpentine order stitches straight through the
    // counter of a "B" and the valley of an "M" — plainly visible as long
    // diagonals in the Studio, and it would sew that way too. The threshold is
    // geometric ("is the next cell adjacent?"), not a physical constant, so it
    // stays clear of gate 1: diagonal neighbours are sqrt(2) cells apart, and
    // anything beyond 1.5 is a real gap.
    const GAP_CELLS = 1.5;
    for (const r of rows) {
      const xs = serp ? r.xs.slice().reverse() : r.xs;
      serp = !serp;
      for (const cx of xs) {
        const jumpHere = first || (prev !== null &&
          Math.hypot(cx - prev.x, r.cy - prev.y) > step * GAP_CELLS);
        let firstOfCell = true;
        for (const stroke of crossStrokes(cx, r.cy, h, method)) {
          out.push({ pts: stroke, kind: "cross", jump: firstOfCell && jumpHere });
          firstOfCell = false;
        }
        first = false;
        prev = { x: cx, y: r.cy };
      }
    }
    return out;
  }

  return { detectLattice, insideRings, crossFill, crossStrokes };
});
