// Satin-column PLAYBACK for pre-digitized glyphs.
//
// A satin column is defined the way Ink/Stitch defines one: TWO RAILS (the two
// long sides) plus optional RUNGS (cross-lines that pin the stitch angle). This
// module turns that explicit, clean geometry into zig-zag satin stitches. The
// quality comes from the rails+rungs being authored/derived cleanly — this code
// just plays them back faithfully (no skeletonization, no guessing).
//
// Output format matches src/satin.js satinColumn: a flat point list where
// consecutive pairs (pts[2k], pts[2k+1]) are the width-spanning cross-stitches
// and pts[2k+1]->pts[2k+2] are the short connectors (the satin bounce). The
// leading edge alternates per station so consecutive crosses share a side.
(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  const _node = typeof module !== "undefined" && module.exports;
  const satin = _node ? require("./satin.js") : root.EMB;
  const chainLength = satin.chainLength;
  const resampleChain = satin.resampleChain;
  const EPS = 1e-9;

  // Arc-length fraction (0..1) of the nearest point on `chain` to (px,py).
  function nearestFrac(chain, px, py) {
    let acc = 0, best = 0, bd = Infinity, total = chainLength(chain) || 1;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const ex = b.x - a.x, ey = b.y - a.y;
      const L2 = ex * ex + ey * ey;
      let u = L2 > EPS ? ((px - a.x) * ex + (py - a.y) * ey) / L2 : 0;
      if (u < 0) u = 0; else if (u > 1) u = 1;
      const qx = a.x + ex * u, qy = a.y + ey * u;
      const d = Math.hypot(px - qx, py - qy);
      if (d < bd) { bd = d; best = (acc + u * Math.sqrt(L2)) / total; }
      acc += Math.sqrt(L2);
    }
    return best;
  }

  // Sub-polyline of `chain` between arc-fractions f0..f1 (0<=f0<f1<=1), with
  // interpolated endpoints. Returns >=2 points.
  function subByFrac(chain, f0, f1) {
    const total = chainLength(chain);
    if (!(total > EPS)) return [{ x: chain[0].x, y: chain[0].y }, { x: chain[0].x, y: chain[0].y }];
    const s0 = f0 * total, s1 = f1 * total;
    const out = [];
    let acc = 0;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const segLen = Math.hypot(b.x - a.x, b.y - a.y);
      const segEnd = acc + segLen;
      if (segEnd < s0) { acc = segEnd; continue; }
      if (out.length === 0) { const t = segLen > EPS ? (s0 - acc) / segLen : 0; out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }); }
      if (segEnd >= s1) { const t = segLen > EPS ? (s1 - acc) / segLen : 1; out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t }); break; }
      out.push({ x: b.x, y: b.y });
      acc = segEnd;
    }
    return out.length >= 2 ? out : [{ x: chain[0].x, y: chain[0].y }, { x: chain[chain.length - 1].x, y: chain[chain.length - 1].y }];
  }

  // Build DENSE corresponded rail-point pairs {A:[…], B:[…]}. Rungs (if any)
  // partition BOTH rails into matching sections so the correspondence follows
  // the authored angle instead of nearest-point (which skews on curves/tapers).
  // Each rung is [{x,y}(near railA), {x,y}(near railB)]; order along the column
  // is inferred from its position on rail A.
  function correspond(railA, railB, rungs, samplesPerSection) {
    const sps = samplesPerSection || 12;
    // Cut fractions on each rail, from rungs, plus the two ends (0 and 1).
    const cuts = [{ a: 0, b: 0 }, { a: 1, b: 1 }];
    if (rungs && rungs.length) {
      for (const rg of rungs) {
        const pa = rg[0], pb = rg[1];
        cuts.push({ a: nearestFrac(railA, pa.x, pa.y), b: nearestFrac(railB, pb.x, pb.y) });
      }
    }
    cuts.sort((p, q) => p.a - q.a);
    const A = [], B = [];
    for (let i = 0; i + 1 < cuts.length; i++) {
      const c0 = cuts[i], c1 = cuts[i + 1];
      if (c1.a - c0.a < 1e-6) continue; // degenerate/duplicate cut
      const sa = resampleChain(subByFrac(railA, c0.a, c1.a), sps);
      const sb = resampleChain(subByFrac(railB, c0.b, c1.b), sps);
      // drop the shared first point of every section after the first (continuity)
      const startK = i === 0 ? 0 : 1;
      for (let k = startK; k < sps; k++) { A.push(sa[k]); B.push(sb[k]); }
    }
    return { A, B };
  }

  // Turn corresponded pairs into zig-zag satin at the given density.
  // opts = { spacingMm, pxPerMm, pullCompMm=0 }.
  function emitZigzag(A, B, opts) {
    const denom = (opts.spacingMm || 0.4) * (opts.pxPerMm || 1);
    const offset = ((opts.pullCompMm || 0) * (opts.pxPerMm || 1)) / 2;
    const M = A.length;
    if (M < 2) return [];
    // Centerline cumulative arc length, to space stations evenly along the run.
    const C = []; for (let i = 0; i < M; i++) C.push({ x: (A[i].x + B[i].x) / 2, y: (A[i].y + B[i].y) / 2 });
    const cum = [0]; for (let i = 1; i < M; i++) cum.push(cum[i - 1] + Math.hypot(C[i].x - C[i - 1].x, C[i].y - C[i - 1].y));
    const total = cum[M - 1];
    if (!(total > EPS)) return [];
    const steps = Math.max(2, Math.ceil(total / (denom > 0 ? denom : 4)));
    const out = [];
    let seg = 0;
    for (let t = 0; t <= steps; t++) {
      const target = (t / steps) * total;
      while (seg < M - 2 && cum[seg + 1] < target) seg++;
      const segLen = cum[seg + 1] - cum[seg];
      const f = segLen > EPS ? (target - cum[seg]) / segLen : 0;
      let ax = A[seg].x + (A[seg + 1].x - A[seg].x) * f, ay = A[seg].y + (A[seg + 1].y - A[seg].y) * f;
      let bx = B[seg].x + (B[seg + 1].x - B[seg].x) * f, by = B[seg].y + (B[seg + 1].y - B[seg].y) * f;
      if (offset > 0) {
        let vx = ax - bx, vy = ay - by; const L = Math.hypot(vx, vy) || 1; vx /= L; vy /= L;
        ax += vx * offset; ay += vy * offset; bx -= vx * offset; by -= vy * offset;
      }
      const pA = { x: ax, y: ay }, pB = { x: bx, y: by };
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.3) continue;
      if (t % 2 === 0) { out.push(pA, pB); } else { out.push(pB, pA); }
    }
    return out;
  }

  // Precompute a column's corresponded rails + centerline + arc-length table, so
  // satin OR running can be generated for any FRACTION SPAN [f0,f1] of the
  // column (needed for underpath routing that enters/exits columns partway).
  function columnGeom(railA, railB, rungs, samplesPerSection) {
    const { A, B } = correspond(railA, railB, rungs || [], samplesPerSection || 12);
    const C = []; for (let i = 0; i < A.length; i++) C.push({ x: (A[i].x + B[i].x) / 2, y: (A[i].y + B[i].y) / 2 });
    const cum = [0]; for (let i = 1; i < C.length; i++) cum.push(cum[i - 1] + Math.hypot(C[i].x - C[i - 1].x, C[i].y - C[i - 1].y));
    return { A, B, C, cum, total: cum[cum.length - 1] || 0 };
  }

  // Slice several index-parallel point arrays to arc-length span [s0,s1] along
  // `cum`, with interpolated endpoints. Returns one sliced array per input.
  function sliceParallel(arrs, cum, s0, s1) {
    const n = cum.length, total = cum[n - 1] || 0;
    s0 = Math.max(0, Math.min(total, s0)); s1 = Math.max(0, Math.min(total, s1));
    const interp = (arr, i, t) => ({ x: arr[i].x + (arr[i + 1].x - arr[i].x) * t, y: arr[i].y + (arr[i + 1].y - arr[i].y) * t });
    const at = (s) => { if (s <= 0) return { i: 0, t: 0 }; if (s >= total) return { i: n - 2, t: 1 }; let i = 0; while (i < n - 2 && cum[i + 1] < s) i++; const seg = cum[i + 1] - cum[i] || 1; return { i, t: (s - cum[i]) / seg }; };
    const a = at(s0), b = at(s1);
    return arrs.map((arr) => {
      const out = [interp(arr, a.i, a.t)];
      for (let i = a.i + 1; i <= b.i; i++) out.push({ x: arr[i].x, y: arr[i].y });
      out.push(interp(arr, b.i, b.t));
      return out;
    });
  }

  // Satin over centerline fraction span [f0,f1] of a precomputed columnGeom.
  function satinFromGeom(geom, f0, f1, opts) {
    if (!geom || geom.total <= EPS || geom.A.length < 2) return [];
    const [As, Bs] = sliceParallel([geom.A, geom.B], geom.cum, f0 * geom.total, f1 * geom.total);
    return emitZigzag(As, Bs, opts || {});
  }

  // Running-stitch centerline over span [f0,f1], resampled to ~stepMm.
  function centerFromGeom(geom, f0, f1, stepMm, pxPerMm) {
    if (!geom || geom.total <= EPS) return [];
    const [Cs] = sliceParallel([geom.C], geom.cum, f0 * geom.total, f1 * geom.total);
    let len = 0; for (let i = 0; i + 1 < Cs.length; i++) len += Math.hypot(Cs[i + 1].x - Cs[i].x, Cs[i + 1].y - Cs[i].y);
    const step = (stepMm || 2) * (pxPerMm || 1);
    return resampleChain(Cs, Math.max(2, Math.ceil(len / (step > 0 ? step : 4))));
  }

  // Main entry: explicit rails (+optional rungs) -> satin zig-zag point list.
  function satinFromRails(railA, railB, rungs, opts) {
    if (!railA || !railB || railA.length < 2 || railB.length < 2) return [];
    const { A, B } = correspond(railA, railB, rungs || [], (opts && opts.samplesPerSection) || 12);
    return emitZigzag(A, B, opts || {});
  }

  // Center-walk underlay: a running stitch down the column centerline (midpoints
  // of the corresponded rails), resampled to ~stepMm. Sewn before the top satin
  // to stabilize the column; hidden under it. opts = { stepMm=2, pxPerMm=1 }.
  function centerRun(railA, railB, rungs, opts) {
    if (!railA || !railB || railA.length < 2 || railB.length < 2) return [];
    const o = opts || {};
    const { A, B } = correspond(railA, railB, rungs || [], o.samplesPerSection || 12);
    const C = []; for (let i = 0; i < A.length; i++) C.push({ x: (A[i].x + B[i].x) / 2, y: (A[i].y + B[i].y) / 2 });
    if (C.length < 2) return [];
    const step = (o.stepMm || 2) * (o.pxPerMm || 1);
    const len = chainLength(C);
    const n = step > 0 ? Math.max(2, Math.ceil(len / step)) : Math.max(2, C.length);
    return resampleChain(C, n);
  }

  return { satinFromRails, centerRun, correspond, columnGeom, satinFromGeom, centerFromGeom };
});
