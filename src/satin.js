(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const EPS = 1e-9;

  // Indices [i, j] of the two boundary points that are farthest apart
  // (Euclidean). O(n^2); rings are small after simplification. These
  // approximate the two "tips"/ends of an elongated shape. Ties resolve to the
  // first pair found in scan order.
  function farthestBoundaryPair(ring) {
    const n = ring ? ring.length : 0;
    let best = -1, bi = 0, bj = 0;
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const dx = ring[i].x - ring[j].x;
        const dy = ring[i].y - ring[j].y;
        const d2 = dx * dx + dy * dy; // compare squared distance (monotonic)
        if (d2 > best) { best = d2; bi = i; bj = j; }
      }
    }
    return [bi, bj];
  }

  // Split the closed ring into its two long sides.
  //   chainA = ring points walking i -> j (inclusive, forward with wrap)
  //   chainB = ring points walking j -> i (inclusive, forward with wrap)
  // The two chains therefore SHARE their endpoints (ring[i] and ring[j]) and
  // together cover the whole boundary. Points are copied so callers can mutate.
  function splitBoundary(ring, i, j) {
    const n = ring.length;
    const chainA = [];
    let k = i;
    while (true) {
      chainA.push({ x: ring[k].x, y: ring[k].y });
      if (k === j) break;
      k = (k + 1) % n;
    }
    const chainB = [];
    k = j;
    while (true) {
      chainB.push({ x: ring[k].x, y: ring[k].y });
      if (k === i) break;
      k = (k + 1) % n;
    }
    return [chainA, chainB];
  }

  // Total Euclidean length of a polyline.
  function chainLength(chain) {
    let total = 0;
    for (let i = 0; i + 1 < chain.length; i++) {
      total += Math.hypot(chain[i + 1].x - chain[i].x, chain[i + 1].y - chain[i].y);
    }
    return total;
  }

  // Exactly n points evenly spaced by arc length along the chain (n >= 2),
  // including both endpoints. Degenerate (zero-length) chains yield n copies of
  // the first point.
  function resampleChain(chain, n) {
    const first = chain[0];
    const last = chain[chain.length - 1];
    if (n <= 1) return [{ x: first.x, y: first.y }];

    const total = chainLength(chain);
    const out = [{ x: first.x, y: first.y }];
    if (total <= EPS) {
      for (let k = 1; k < n; k++) out.push({ x: first.x, y: first.y });
      return out;
    }

    const step = total / (n - 1);
    let seg = 0;                                   // current segment start index
    let accum = 0;                                 // arc length at chain[seg]
    let segLen = Math.hypot(chain[1].x - chain[0].x, chain[1].y - chain[0].y);
    for (let k = 1; k < n - 1; k++) {
      const target = k * step;
      while (seg < chain.length - 2 && accum + segLen < target) {
        accum += segLen;
        seg++;
        segLen = Math.hypot(chain[seg + 1].x - chain[seg].x, chain[seg + 1].y - chain[seg].y);
      }
      const t = segLen > EPS ? (target - accum) / segLen : 0;
      const a = chain[seg], b = chain[seg + 1];
      out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
    }
    out.push({ x: last.x, y: last.y }); // exact final endpoint
    return out;
  }

  // Approximate stroke width in mm ~= 2 * area / perimeter (both in px),
  // divided by pxPerMm. Uses shoelace absolute area and summed edge lengths.
  function estimateWidthMm(ring, pxPerMm) {
    const n = ring ? ring.length : 0;
    if (n < 3 || !pxPerMm) return 0;
    let cross = 0, per = 0;
    for (let i = 0; i < n; i++) {
      const p1 = ring[i], p2 = ring[(i + 1) % n];
      cross += p1.x * p2.y - p2.x * p1.y;
      per += Math.hypot(p2.x - p1.x, p2.y - p1.y);
    }
    const area = Math.abs(cross) / 2;
    if (per <= EPS) return 0;
    return (2 * area / per) / pxPerMm;
  }

  // Push point p outward from the pair midpoint (mx,my) by `dist` px along the
  // normalized (p - midpoint) direction. Degenerate (coincident) pairs don't
  // move — the column has zero width there (e.g. at the shared tips).
  function pushOut(p, mx, my, dist) {
    const vx = p.x - mx;
    const vy = p.y - my;
    const len = Math.hypot(vx, vy);
    if (len <= EPS) return { x: p.x, y: p.y };
    return { x: p.x + (vx / len) * dist, y: p.y + (vy / len) * dist };
  }

  // Intersection of the INFINITE line through (ox,oy) with direction (dx,dy)
  // against the SEGMENT (ax,ay)-(bx,by). Returns the signed distance `t` along
  // (dx,dy) at which they meet, or null if parallel or the hit falls outside
  // the segment. Solve o + t*d = a + u*(b-a), u in [0,1].
  function lineSegX(ox, oy, dx, dy, ax, ay, bx, by) {
    const ex = bx - ax, ey = by - ay;
    const det = ex * dy - dx * ey; // determinant of [d | -e]
    if (Math.abs(det) < EPS) return null; // parallel
    const rx = ax - ox, ry = ay - oy;
    // Cramer's rule (see derivation): t solves the line param, u the segment.
    const t = (ex * ry - ey * rx) / det;
    const u = (dx * ry - dy * rx) / det;
    if (u < -EPS || u > 1 + EPS) return null; // outside the segment
    return t;
  }

  // Nearest point on a polyline `chain` to (px,py). Used as a tip fallback when
  // the perpendicular line misses a rail entirely.
  function nearestOnChain(chain, px, py) {
    let best = { x: chain[0].x, y: chain[0].y };
    let bd = Infinity;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const ex = b.x - a.x, ey = b.y - a.y;
      const L2 = ex * ex + ey * ey;
      let u = L2 > EPS ? ((px - a.x) * ex + (py - a.y) * ey) / L2 : 0;
      if (u < 0) u = 0; else if (u > 1) u = 1;
      const qx = a.x + ex * u, qy = a.y + ey * u;
      const d = Math.hypot(px - qx, py - qy);
      if (d < bd) { bd = d; best = { x: qx, y: qy }; }
    }
    return best;
  }

  // Hit of the infinite line (o,d) against rail polyline `chain`, choosing the
  // intersection NEAREST to o (smallest |t|). Returns the point or null if no
  // segment is crossed.
  function railHit(chain, ox, oy, dx, dy) {
    let best = null, bt = Infinity;
    for (let k = 0; k + 1 < chain.length; k++) {
      const t = lineSegX(ox, oy, dx, dy, chain[k].x, chain[k].y, chain[k + 1].x, chain[k + 1].y);
      if (t === null) continue;
      if (Math.abs(t) < Math.abs(bt)) { bt = t; best = { x: ox + dx * t, y: oy + dy * t }; }
    }
    return best;
  }

  // Return the sub-polyline of `chain` between arc-lengths s0..s1 (s0 < s1),
  // with interpolated endpoints. Used to skip the tip/end-cap region of the
  // centerline where cross geometry degenerates. Falls back to a copy if the
  // requested span is degenerate.
  function subChainByArc(chain, s0, s1) {
    const out = [];
    let acc = 0;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const segLen = Math.hypot(b.x - a.x, b.y - a.y);
      const segEnd = acc + segLen;
      if (segEnd < s0) { acc = segEnd; continue; }
      if (out.length === 0) {
        const t = segLen > EPS ? (s0 - acc) / segLen : 0;
        out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
      }
      if (segEnd >= s1) {
        const t = segLen > EPS ? (s1 - acc) / segLen : 1;
        out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
        break;
      }
      out.push({ x: b.x, y: b.y });
      acc = segEnd;
    }
    return out.length >= 2 ? out : chain.map((q) => ({ x: q.x, y: q.y }));
  }

  // Generate zig-zag satin stitch points whose cross-stitches are PERPENDICULAR
  // to the two edges of a thin/elongated ring and FAN ALONG THE ARC on curves.
  //
  // opts = { spacingMm, pxPerMm, pullCompMm=0 }
  //
  // Approach: build a centerline from the two rails, then at each station along
  // the centerline shoot a ray perpendicular to the LOCAL tangent and intersect
  // both rails. The resulting cross is perpendicular to the centerline tangent
  // (hence to the edges) and rotates with the arc — no arc-length index skew.
  //
  // Emit: the leading edge alternates per station (even -> A then B, odd -> B
  // then A) so consecutive crosses share a side (a short connector), producing
  // the satin bounce. Width-spanning crosses are therefore the even-indexed
  // point pairs (pts[2k], pts[2k+1]); connectors are pts[2k+1]->pts[2k+2].
  function satinColumn(ring, opts) {
    if (!ring || ring.length < 3) return [];
    const spacingMm = opts.spacingMm;
    const pxPerMm = opts.pxPerMm;
    const pullCompMm = opts.pullCompMm || 0;
    // slantDeg leans the cross direction off perpendicular (italic-style satin):
    // 0 = perpendicular (default), + / - lean toward the stroke direction.
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;

    const [i, j] = farthestBoundaryPair(ring);
    const [A, B] = splitBoundary(ring, i, j);

    const denom = spacingMm * pxPerMm;
    const lenA = chainLength(A), lenB = chainLength(B);
    const longest = Math.max(lenA, lenB);
    if (!(longest > EPS)) return []; // degenerate

    // Fine common resample of both rails so the centerline is smooth. Reverse B
    // so index runs the same direction along the length as A.
    let M;
    if (denom > 0) M = Math.ceil(longest / denom) * 3;
    else M = 16;
    if (!(M >= 16)) M = 16;
    if (M > 600) M = 600;
    const fineA = resampleChain(A, M);
    const fineB = resampleChain(B, M).reverse();

    // Centerline as midpoints of paired fine samples.
    const C = [];
    for (let k = 0; k < M; k++) {
      C.push({ x: (fineA[k].x + fineB[k].x) / 2, y: (fineA[k].y + fineB[k].y) / 2 });
    }
    const cLen = chainLength(C);
    if (!(cLen > EPS)) return []; // zero-length centerline

    // On strokes long enough to have real end caps, start/end the satin a short
    // margin in from the tips: cross geometry degenerates at the caps (the
    // farthest-pair tips can sit at corners, bending the centerline there).
    // Short strokes keep their full length so tiny shapes still get a column.
    const fullSteps = denom > 0 ? Math.max(2, Math.ceil(cLen / denom)) : 2;
    // Trim only the degenerate end-cap region (~one stroke width), capped at a
    // fraction of length so long strokes keep tip-to-tip coverage and short
    // strokes aren't over-trimmed. Width ~= 2*area/perimeter of the ring (px).
    const widthPx = estimateWidthMm(ring, 1);
    const trim = fullSteps >= 8 ? Math.min(0.9 * widthPx, 0.12 * cLen) : 0;
    const Ct = trim > EPS ? subChainByArc(C, trim, cLen - trim) : C;
    const ctLen = chainLength(Ct);
    const steps = denom > 0 ? Math.max(2, Math.ceil(ctLen / denom)) : 2;
    if (!Number.isFinite(steps)) return [];
    const stations = resampleChain(Ct, steps);

    const offset = (pullCompMm * pxPerMm) / 2;
    const out = [];
    for (let t = 0; t < steps; t++) {
      const s = stations[t];
      // Local tangent from neighbor stations (fwd/back difference at the ends).
      const prev = stations[Math.max(0, t - 1)];
      const next = stations[Math.min(steps - 1, t + 1)];
      let tx = next.x - prev.x, ty = next.y - prev.y;
      let tl = Math.hypot(tx, ty);
      if (tl <= EPS) continue; // no meaningful tangent here
      tx /= tl; ty /= tl;
      // Normal = tangent rotated 90deg, then leaned by the slant angle.
      let nx = -ty, ny = tx;
      if (slantRad) {
        const cs = Math.cos(slantRad), sn = Math.sin(slantRad);
        const rx = nx * cs - ny * sn, ry = nx * sn + ny * cs;
        nx = rx; ny = ry;
      }

      // Perpendicular ray hits each rail; fall back to nearest rail point.
      let pA = railHit(A, s.x, s.y, nx, ny) || nearestOnChain(A, s.x, s.y);
      let pB = railHit(B, s.x, s.y, nx, ny) || nearestOnChain(B, s.x, s.y);

      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.5) continue; // drop degenerate cross

      if (offset > 0) {
        const mx = (pA.x + pB.x) / 2, my = (pA.y + pB.y) / 2;
        pA = pushOut(pA, mx, my, offset);
        pB = pushOut(pB, mx, my, offset);
      }

      // Alternate the leading edge so consecutive crosses share a side.
      if (t % 2 === 0) { out.push(pA); out.push(pB); }
      else { out.push(pB); out.push(pA); }
    }
    return out;
  }

  return {
    farthestBoundaryPair,
    splitBoundary,
    chainLength,
    resampleChain,
    estimateWidthMm,
    lineSegX,
    satinColumn,
  };
});
