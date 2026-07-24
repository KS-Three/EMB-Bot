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

  // ---- Medial-axis (skeleton) satin, for strokes that double back (S, curves) ----

  // Scanline-fill one-or-more contours into a binary grid at `gscale`
  // px-per-unit. Accepts a single ring OR an array of rings [outer, ...holes];
  // all edges feed one even-odd crossing test per scanline, so enclosed holes
  // (letter counters in B/R/A/O) come out UNFILLED automatically — winding
  // direction is irrelevant to even-odd.
  function rasterize(ringOrContours, gscale, minX, minY, gw, gh) {
    const contours = Array.isArray(ringOrContours) && ringOrContours[0] && !("x" in ringOrContours[0])
      ? ringOrContours : [ringOrContours];
    const mask = new Uint8Array(gw * gh);
    for (let j = 0; j < gh; j++) {
      const wy = minY + (j + 0.5) / gscale;
      const xs = [];
      for (const ring of contours) {
        const n = ring.length;
        for (let k = 0; k < n; k++) {
          const a = ring[k], b = ring[(k + 1) % n];
          if ((a.y <= wy && b.y > wy) || (b.y <= wy && a.y > wy)) {
            xs.push(a.x + (b.x - a.x) * ((wy - a.y) / (b.y - a.y)));
          }
        }
      }
      xs.sort((p, q) => p - q);
      for (let m = 0; m + 1 < xs.length; m += 2) {
        let i0 = Math.ceil((xs[m] - minX) * gscale - 0.5);
        let i1 = Math.floor((xs[m + 1] - minX) * gscale - 0.5);
        if (i0 < 0) i0 = 0; if (i1 >= gw) i1 = gw - 1;
        for (let i = i0; i <= i1; i++) mask[j * gw + i] = 1;
      }
    }
    return mask;
  }

  // Zhang–Suen thinning to a 1px skeleton (in place; returns the same array).
  function thin(mask, w, h) {
    const P = (x, y) => (x < 0 || y < 0 || x >= w || y >= h) ? 0 : mask[y * w + x];
    let changed = true, guard = 0;
    while (changed && guard++ < 200) {
      changed = false;
      for (let step = 0; step < 2; step++) {
        const del = [];
        for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
          if (!mask[y * w + x]) continue;
          const p2 = P(x, y - 1), p3 = P(x + 1, y - 1), p4 = P(x + 1, y), p5 = P(x + 1, y + 1),
            p6 = P(x, y + 1), p7 = P(x - 1, y + 1), p8 = P(x - 1, y), p9 = P(x - 1, y - 1);
          const nb = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9;
          if (nb < 2 || nb > 6) continue;
          const seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2];
          let A = 0; for (let k = 0; k < 8; k++) if (seq[k] === 0 && seq[k + 1] === 1) A++;
          if (A !== 1) continue;
          if (step === 0) { if (p2 * p4 * p6 !== 0 || p4 * p6 * p8 !== 0) continue; }
          else { if (p2 * p4 * p8 !== 0 || p2 * p6 * p8 !== 0) continue; }
          del.push(y * w + x);
        }
        if (del.length) { changed = true; for (const d of del) mask[d] = 0; }
      }
    }
    return mask;
  }

  // Strip short dead-end branches (spurs) from a 1px skeleton: iteratively
  // delete deg<=1 pixels for `maxLen` rounds. Thinning leaves tiny hairs at
  // corners that would fragment a clean loop (O) or stroke into arcs; this
  // removes them. Real strokes are far longer than maxLen, so their tips only
  // shrink by a few px (the rail pass trims free ends anyway).
  function pruneSkeleton(skel, w, h, maxLen) {
    const idx = (x, y) => y * w + x;
    const degOf = (x, y) => {
      let d = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue; const nx = x + dx, ny = y + dy;
        if (nx >= 0 && ny >= 0 && nx < w && ny < h && skel[idx(nx, ny)]) d++;
      }
      return d;
    };
    for (let iter = 0; iter < maxLen; iter++) {
      const del = [];
      for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
        if (skel[idx(x, y)] && degOf(x, y) <= 1) del.push(idx(x, y));
      }
      if (!del.length) break;
      for (const d of del) skel[d] = 0;
    }
    return skel;
  }

  // Longest path through the skeleton via double BFS (graph diameter). Returns
  // an ordered list of grid [i,j] pixels — the stroke spine.
  function skeletonPath(skel, w, h) {
    const nbrs = (x, y) => {
      const r = [];
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const nx = x + dx, ny = y + dy;
        if (nx >= 0 && ny >= 0 && nx < w && ny < h && skel[ny * w + nx]) r.push([nx, ny]);
      }
      return r;
    };
    let start = -1;
    for (let i = 0; i < skel.length; i++) if (skel[i]) { start = i; break; }
    if (start < 0) return [];
    function bfsFar(sx, sy) {
      const par = new Int32Array(w * h).fill(-2);
      let q = [[sx, sy]]; par[sy * w + sx] = -1; let last = [sx, sy];
      while (q.length) {
        const nq = [];
        for (const [x, y] of q) {
          last = [x, y];
          for (const [nx, ny] of nbrs(x, y)) if (par[ny * w + nx] === -2) { par[ny * w + nx] = y * w + x; nq.push([nx, ny]); }
        }
        q = nq;
      }
      return { far: last, par };
    }
    const a = bfsFar(start % w, (start / w) | 0).far;
    const { far: b, par } = bfsFar(a[0], a[1]);
    const path = [];
    let cur = b[1] * w + b[0];
    let guard = 0;
    while (cur !== -1 && guard++ < w * h) { path.push([cur % w, (cur / w) | 0]); cur = par[cur]; }
    return path;
  }

  // Moving-average smooth of a polyline (endpoints fixed).
  function smoothChain(pts, passes) {
    let cur = pts.map((p) => ({ x: p.x, y: p.y }));
    for (let s = 0; s < (passes || 1); s++) {
      const next = cur.map((p) => ({ x: p.x, y: p.y }));
      for (let i = 1; i < cur.length - 1; i++) {
        next[i] = { x: (cur[i - 1].x + cur[i].x + cur[i + 1].x) / 3, y: (cur[i - 1].y + cur[i].y + cur[i + 1].y) / 3 };
      }
      cur = next;
    }
    return cur;
  }

  // Nearest positive-t intersection of the RAY (o,dir) with the closed ring.
  function rayRingHit(ring, ox, oy, dx, dy) {
    let best = null, bt = Infinity;
    const n = ring.length;
    for (let k = 0; k < n; k++) {
      const a = ring[k], b = ring[(k + 1) % n];
      const t = lineSegX(ox, oy, dx, dy, a.x, a.y, b.x, b.y);
      if (t === null || t <= EPS) continue;
      if (t < bt) { bt = t; best = { x: ox + dx * t, y: oy + dy * t }; }
    }
    return best;
  }

  // Nearest positive-t ray hit across MANY contours (outer + holes). The stroke
  // ribbon of a counter-bearing glyph is bounded by whichever edge is closer —
  // the outer wall or the counter wall — so the rail stops at the nearer of the
  // two. Distance measured Euclidean (rayRingHit only returns forward hits).
  function rayContoursHit(contours, ox, oy, dx, dy) {
    let best = null, bd = Infinity;
    for (const ring of contours) {
      const h = rayRingHit(ring, ox, oy, dx, dy);
      if (!h) continue;
      const d = Math.hypot(h.x - ox, h.y - oy);
      if (d < bd) { bd = d; best = h; }
    }
    return best;
  }

  // Rail-satin ONE spine (world coords). Smooth; optionally trim the veering
  // tail at FREE ends only (junction ends run in); resample; build two rails
  // (spine ± smoothed half-width along the smoothed normal) and emit crosses.
  // `contours` = [outer, ...holes]; rails stop at the nearest wall (so a stroke
  // beside a counter narrows against the counter edge, not the far outer edge).
  // opts._halfWidthPx is the ring's approx half-width (for trim sizing).
  function railSatinFromSpine(contours, spinePx, opts, trimStart, trimEnd) {
    const spacingMm = opts.spacingMm, pxPerMm = opts.pxPerMm;
    const pullCompMm = opts.pullCompMm || 0;
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;
    const halfWidthPx = opts._halfWidthPx || 0;

    let spine = smoothChain(spinePx, 3);
    if (halfWidthPx > EPS && (trimStart || trimEnd)) {
      const L0 = chainLength(spine);
      const trim = 0.5 * halfWidthPx;
      const s0 = trimStart ? trim : 0, s1 = trimEnd ? L0 - trim : L0;
      if (s1 - s0 > 2 * trim) spine = subChainByArc(spine, s0, s1);
    }
    const denom = spacingMm * pxPerMm;
    const stepPx = denom > 0 ? denom : 4;
    const spineLen = chainLength(spine);
    if (!(spineLen > EPS)) return [];
    spine = resampleChain(spine, Math.max(2, Math.ceil(spineLen / stepPx)));

    const N = spine.length;
    const ang = new Array(N);
    for (let t = 0; t < N; t++) {
      const prev = spine[Math.max(0, t - 1)], next = spine[Math.min(N - 1, t + 1)];
      let tx = next.x - prev.x, ty = next.y - prev.y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
      ang[t] = Math.atan2(tx, -ty); // angle of the normal (-ty, tx)
    }
    for (let t = 1; t < N; t++) {
      while (ang[t] - ang[t - 1] > Math.PI / 2) ang[t] -= Math.PI;
      while (ang[t] - ang[t - 1] < -Math.PI / 2) ang[t] += Math.PI;
    }
    for (let pass = 0; pass < 6; pass++) { const cp = ang.slice(); for (let t = 1; t < N - 1; t++) ang[t] = (cp[t - 1] + cp[t] + cp[t + 1]) / 3; }
    if (slantRad) for (let t = 0; t < N; t++) ang[t] += slantRad; // italic lean

    const dA = new Array(N), dB = new Array(N);
    for (let t = 0; t < N; t++) {
      const s = spine[t], nx = Math.cos(ang[t]), ny = Math.sin(ang[t]);
      const hp = rayContoursHit(contours, s.x, s.y, nx, ny);
      const hn = rayContoursHit(contours, s.x, s.y, -nx, -ny);
      dA[t] = hp ? Math.hypot(hp.x - s.x, hp.y - s.y) : NaN;
      dB[t] = hn ? Math.hypot(hn.x - s.x, hn.y - s.y) : NaN;
    }
    const fillNaN = (arr) => {
      let last = NaN;
      for (let t = 0; t < N; t++) { if (!isNaN(arr[t])) last = arr[t]; else if (!isNaN(last)) arr[t] = last; }
      last = NaN;
      for (let t = N - 1; t >= 0; t--) { if (!isNaN(arr[t])) last = arr[t]; else if (!isNaN(last)) arr[t] = last; }
      for (let t = 0; t < N; t++) if (isNaN(arr[t])) arr[t] = 0;
    };
    fillNaN(dA); fillNaN(dB);
    for (let pass = 0; pass < 3; pass++) {
      const a = dA.slice(), b = dB.slice();
      for (let t = 1; t < N - 1; t++) { dA[t] = (a[t - 1] + a[t] + a[t + 1]) / 3; dB[t] = (b[t - 1] + b[t] + b[t + 1]) / 3; }
    }

    const offset = (pullCompMm * pxPerMm) / 2;
    const out = [];
    for (let t = 0; t < N; t++) {
      const s = spine[t], nx = Math.cos(ang[t]), ny = Math.sin(ang[t]);
      const pA = { x: s.x + nx * (dA[t] + offset), y: s.y + ny * (dA[t] + offset) };
      const pB = { x: s.x - nx * (dB[t] + offset), y: s.y - ny * (dB[t] + offset) };
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.5) continue;
      if (t % 2 === 0) { out.push(pA); out.push(pB); } else { out.push(pB); out.push(pA); }
    }
    return out;
  }

  // Decompose a 1px skeleton into edges (strokes) between nodes. Nodes are
  // ENDPOINTS (one neighbor) and BRANCH points, where "branch" is detected by
  // the Rutovitz CROSSING NUMBER (count of arms leaving the pixel), NOT the raw
  // 8-neighbor count. This matters: a pixelated curve is a staircase, and a
  // staircase pixel has 3 raw neighbors yet is an ordinary through-point — raw
  // degree would flag it as a false branch and shatter a smooth loop (O) into
  // hundreds of fragments. Returns [{pts:[[i,j]…], freeStart, freeEnd, closed}].
  function skeletonEdges(skel, w, h) {
    const id = (x, y) => y * w + x;
    const on = (x, y) => x >= 0 && y >= 0 && x < w && y < h && !!skel[id(x, y)];
    const nbrs = (x, y) => {
      const r = [];
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue; if (on(x + dx, y + dy)) r.push([x + dx, y + dy]);
      }
      return r;
    };
    // Ordered 8-ring (clockwise); crossing number = # of 0→1 transitions around
    // it = # of distinct neighbor runs = # of arms.
    const RING = [[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]];
    const crossing = (x, y) => {
      let c = 0;
      for (let k = 0; k < 8; k++) {
        const a = on(x + RING[k][0], y + RING[k][1]) ? 1 : 0;
        const b = on(x + RING[(k + 1) % 8][0], y + RING[(k + 1) % 8][1]) ? 1 : 0;
        if (a === 0 && b === 1) c++;
      }
      return c;
    };
    const isEnd = (x, y) => nbrs(x, y).length === 1;
    const isNode = (x, y) => isEnd(x, y) || crossing(x, y) >= 3;
    const edges = [];
    const usedDir = new Set();  // directed first-steps already walked
    const seen = new Set();     // every skeleton pixel covered by an edge

    // Walk from node (sx,sy) toward neighbor (fx,fy) until the next node. At a
    // staircase pixel with two forward candidates prefer the unvisited one so we
    // don't ping-pong; mark every pixel seen.
    const walk = (sx, sy, fx, fy) => {
      const path = [[sx, sy], [fx, fy]];
      seen.add(id(sx, sy)); seen.add(id(fx, fy));
      let px = sx, py = sy, cx = fx, cy = fy, guard = 0;
      while (guard++ < w * h) {
        if (isNode(cx, cy)) break;
        const cand = nbrs(cx, cy).filter(([a, b]) => !(a === px && b === py));
        if (!cand.length) break;
        let nx = cand[0][0], ny = cand[0][1];
        for (const [a, b] of cand) if (!seen.has(id(a, b))) { nx = a; ny = b; break; }
        px = cx; py = cy; cx = nx; cy = ny;
        path.push([cx, cy]); seen.add(id(cx, cy));
      }
      return path;
    };

    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (!skel[id(x, y)] || !isNode(x, y)) continue;
      for (const [nx, ny] of nbrs(x, y)) {
        const k = id(x, y) + ':' + id(nx, ny);
        if (usedDir.has(k)) continue;
        usedDir.add(k);
        const path = walk(x, y, nx, ny);
        const e = path[path.length - 1], b = path[path.length - 2];
        if (b) usedDir.add(id(e[0], e[1]) + ':' + id(b[0], b[1])); // reverse walk
        edges.push({ pts: path, freeStart: isEnd(x, y), freeEnd: isEnd(e[0], e[1]) });
      }
    }
    // Pure cycles (O, 0, counters, closed bowls) contain no node, so the scan
    // above never touched them. Walk each remaining loop as a CLOSED stroke:
    // no free ends → no terminal trim, rails close back on themselves.
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (!skel[id(x, y)] || seen.has(id(x, y))) continue;
      const start = nbrs(x, y);
      if (start.length !== 2) continue; // not part of a clean loop
      const path = [[x, y]]; seen.add(id(x, y));
      let px = x, py = y, cx = start[0][0], cy = start[0][1], guard = 0;
      while (guard++ < w * h) {
        if (cx === x && cy === y) break; // closed the loop
        path.push([cx, cy]); seen.add(id(cx, cy));
        const cand = nbrs(cx, cy).filter(([a, b]) => !(a === px && b === py));
        if (!cand.length) break;
        let nx = cand[0][0], ny = cand[0][1];
        for (const [a, b] of cand) if (!seen.has(id(a, b)) || (a === x && b === y)) { nx = a; ny = b; break; }
        px = cx; py = cy; cx = nx; cy = ny;
      }
      path.push([x, y]); // close ring explicitly
      if (path.length >= 5) edges.push({ pts: path, freeStart: false, freeEnd: false, closed: true });
    }
    return edges;
  }

  // Signed-area magnitude and closed perimeter of a ring (px).
  function ringArea(r) { let a = 0; for (let i = 0, j = r.length - 1; i < r.length; j = i++) a += r[j].x * r[i].y - r[i].x * r[j].y; return Math.abs(a) / 2; }
  function ringPerim(r) { let p = 0; for (let i = 0; i < r.length; i++) { const a = r[i], b = r[(i + 1) % r.length]; p += Math.hypot(b.x - a.x, b.y - a.y); } return p; }

  // Rasterize a ring(+counters) to a 1px skeleton and decompose it into stroke
  // spines in WORLD coords. Shared by medialSatin (stitch immediately) and
  // glyphColumns (extract storable rails). Returns
  // { strokes:[{spine,freeStart,freeEnd,closed}], contours, halfWidthPx }.
  function ringToSpines(ring, opts) {
    const holes = ((opts && opts.holes) || []).filter((h) => h && h.length >= 3);
    const contours = [ring].concat(holes);
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const q of ring) { if (q.x < minX) minX = q.x; if (q.x > maxX) maxX = q.x; if (q.y < minY) minY = q.y; if (q.y > maxY) maxY = q.y; }
    const dim = Math.max(maxX - minX, maxY - minY);
    if (!(dim > EPS)) return { strokes: [], contours, halfWidthPx: 0 };

    const gscale = Math.min(1.5, 260 / dim);
    const gw = Math.ceil((maxX - minX) * gscale) + 3, gh = Math.ceil((maxY - minY) * gscale) + 3;
    // Net ribbon half-width (outer area minus counters) over total wall length.
    const netArea = Math.max(0, ringArea(ring) - holes.reduce((s, h) => s + ringArea(h), 0));
    const totPerim = ringPerim(ring) + holes.reduce((s, h) => s + ringPerim(h), 0);
    const halfWidthPx = (totPerim > EPS ? (2 * netArea / totPerim) : 0) / 2;
    const mask = thin(rasterize(contours, gscale, minX, minY, gw, gh), gw, gh);
    // Strip thinning SPURS — short dead-end twigs (one free end, other end on a
    // branch) that thinning grows at curvature bumps. Removing them keeps closed
    // loops (O) a single clean cycle. Only short one-free-end edges are erased,
    // so real open strokes (both ends free) and long arms are untouched. Iterate
    // because erasing one spur can expose another.
    const spurLenGrid = Math.max(3, halfWidthPx * gscale * 1.6);
    for (let pass = 0; pass < 4; pass++) {
      let removed = 0;
      for (const e of skeletonEdges(mask, gw, gh)) {
        if (((e.freeStart ? 1 : 0) + (e.freeEnd ? 1 : 0)) !== 1) continue; // spur = exactly one free end
        let L = 0; for (let i = 0; i + 1 < e.pts.length; i++) L += Math.hypot(e.pts[i + 1][0] - e.pts[i][0], e.pts[i + 1][1] - e.pts[i][1]);
        if (L >= spurLenGrid) continue;
        const keep = e.freeStart ? e.pts[e.pts.length - 1] : e.pts[0]; // preserve the branch node
        for (const [gx, gy] of e.pts) { if (gx === keep[0] && gy === keep[1]) continue; mask[gy * gw + gx] = 0; removed++; }
      }
      if (!removed) break;
    }
    const toWorld = (p) => ({ x: minX + (p[0] + 0.5) / gscale, y: minY + (p[1] + 0.5) / gscale });

    let strokes = skeletonEdges(mask, gw, gh).map((e) => ({ spine: e.pts.map(toWorld), freeStart: e.freeStart, freeEnd: e.freeEnd, closed: !!e.closed }));
    const minEdgeLen = Math.max(3, 1.2 * halfWidthPx);
    strokes = strokes.filter((s) => { const L = chainLength(s.spine); return L > EPS && (L >= minEdgeLen || (s.freeStart && s.freeEnd)); });
    if (strokes.length === 0) {
      const gp = skeletonPath(mask, gw, gh);
      if (gp.length < 3) return { strokes: [], contours, halfWidthPx };
      strokes = [{ spine: gp.map(toWorld), freeStart: true, freeEnd: true, closed: false }];
    }
    strokes.sort((a, b) => chainLength(b.spine) - chainLength(a.spine));
    if (strokes.length > 24) strokes = strokes.slice(0, 24);
    return { strokes, contours, halfWidthPx };
  }

  // Satin along the medial axis (skeleton). Decomposes branched letters (B, R,
  // T…) into individual strokes and rail-satins each; single strokes (S, C, I)
  // satin as one column. Counters (opts.holes: [ring,…]) are punched out of the
  // raster so the skeleton follows the stroke ribbons AROUND the hole and the
  // rails stop at the counter edge. Falls back to outline-split satinColumn for
  // tiny rings. opts = { spacingMm, pxPerMm, pullCompMm=0, slantDeg=0, holes=[] }.
  function medialSatin(ring, opts) {
    if (!ring || ring.length < 3) return [];
    const { strokes, contours, halfWidthPx } = ringToSpines(ring, opts);
    if (!strokes.length) return satinColumn(ring, opts);
    if (typeof globalThis !== "undefined" && globalThis.__DBG_SPINE) globalThis.__spine = strokes.reduce((acc, s) => acc.concat(s.spine), []);

    const o = Object.assign({ _halfWidthPx: halfWidthPx }, opts);
    const out = [];
    let started = false;
    for (const st of strokes) {
      const pts = railSatinFromSpine(contours, st.spine, o, st.freeStart, st.freeEnd);
      if (pts.length < 2) continue;
      if (started) pts[0] = { x: pts[0].x, y: pts[0].y, travel: true }; // needle-up jump between strokes
      for (const p of pts) out.push(p);
      started = true;
    }
    return out.length >= 4 ? out : satinColumn(ring, opts);
  }

  // Like railSatinFromSpine but returns the two RAILS (+corresponding rungs)
  // for STORAGE — a pre-digitized satin column that satinplay.satinFromRails
  // plays back. Same smoothing/normal/ray logic. Trims FREE ends by ~half-width
  // (the terminal veer) and JUNCTION ends by a smaller amount (so abutting
  // strokes don't overlap into a knot). Closed loops (O) are never trimmed.
  function spineToRails(contours, spinePx, opts, trimStart, trimEnd, closed) {
    const pullCompMm = opts.pullCompMm || 0, pxPerMm = opts.pxPerMm || 1;
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;
    const halfWidthPx = opts._halfWidthPx || 0;
    const spacingMm = opts.spacingMm;

    let spine = smoothChain(spinePx, 3);
    if (halfWidthPx > EPS && !closed) {
      const L0 = chainLength(spine);
      const freeTrim = 0.5 * halfWidthPx;   // veer at a true terminal
      const juncTrim = 0.4 * halfWidthPx;   // pull back from a junction
      const s0 = trimStart ? freeTrim : juncTrim;
      const s1 = L0 - (trimEnd ? freeTrim : juncTrim);
      if (s1 - s0 > 0.5 * halfWidthPx) spine = subChainByArc(spine, s0, s1);
    }
    const denom = spacingMm * pxPerMm, stepPx = denom > 0 ? denom : 4;
    const spineLen = chainLength(spine);
    if (!(spineLen > EPS)) return null;
    spine = resampleChain(spine, Math.max(2, Math.ceil(spineLen / stepPx)));
    const N = spine.length;
    const ang = new Array(N);
    for (let t = 0; t < N; t++) {
      const prev = spine[Math.max(0, t - 1)], next = spine[Math.min(N - 1, t + 1)];
      let tx = next.x - prev.x, ty = next.y - prev.y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
      ang[t] = Math.atan2(tx, -ty);
    }
    for (let t = 1; t < N; t++) { while (ang[t] - ang[t - 1] > Math.PI / 2) ang[t] -= Math.PI; while (ang[t] - ang[t - 1] < -Math.PI / 2) ang[t] += Math.PI; }
    for (let pass = 0; pass < 6; pass++) { const cp = ang.slice(); for (let t = 1; t < N - 1; t++) ang[t] = (cp[t - 1] + cp[t] + cp[t + 1]) / 3; }
    if (slantRad) for (let t = 0; t < N; t++) ang[t] += slantRad;
    const dA = new Array(N), dB = new Array(N);
    for (let t = 0; t < N; t++) {
      const s = spine[t], nx = Math.cos(ang[t]), ny = Math.sin(ang[t]);
      const hp = rayContoursHit(contours, s.x, s.y, nx, ny), hn = rayContoursHit(contours, s.x, s.y, -nx, -ny);
      dA[t] = hp ? Math.hypot(hp.x - s.x, hp.y - s.y) : NaN;
      dB[t] = hn ? Math.hypot(hn.x - s.x, hn.y - s.y) : NaN;
    }
    const fillNaN = (arr) => { let last = NaN; for (let t = 0; t < N; t++) { if (!isNaN(arr[t])) last = arr[t]; else if (!isNaN(last)) arr[t] = last; } last = NaN; for (let t = N - 1; t >= 0; t--) { if (!isNaN(arr[t])) last = arr[t]; else if (!isNaN(last)) arr[t] = last; } for (let t = 0; t < N; t++) if (isNaN(arr[t])) arr[t] = 0; };
    fillNaN(dA); fillNaN(dB);
    for (let pass = 0; pass < 3; pass++) { const a = dA.slice(), b = dB.slice(); for (let t = 1; t < N - 1; t++) { dA[t] = (a[t - 1] + a[t] + a[t + 1]) / 3; dB[t] = (b[t - 1] + b[t] + b[t + 1]) / 3; } }
    const offset = (pullCompMm * pxPerMm) / 2;
    const railA = [], railB = [];
    for (let t = 0; t < N; t++) {
      const s = spine[t], nx = Math.cos(ang[t]), ny = Math.sin(ang[t]);
      railA.push({ x: s.x + nx * (dA[t] + offset), y: s.y + ny * (dA[t] + offset) });
      railB.push({ x: s.x - nx * (dB[t] + offset), y: s.y - ny * (dB[t] + offset) });
    }
    const rungs = []; for (let t = 0; t < N; t += 6) rungs.push([railA[t], railB[t]]);
    if (rungs.length && rungs[rungs.length - 1][0] !== railA[N - 1]) rungs.push([railA[N - 1], railB[N - 1]]);
    return { railA, railB, rungs };
  }

  // Extract storable satin columns (rails+rungs) for a glyph/region — the same
  // skeleton decomposition medialSatin uses, but returning geometry for
  // satinplay.satinFromRails instead of stitching immediately. This is the
  // offline "digitizer" half of the pre-digitized-font pipeline.
  function glyphColumns(ring, opts) {
    if (!ring || ring.length < 3) return [];
    const { strokes, contours, halfWidthPx } = ringToSpines(ring, opts);
    const o = Object.assign({ _halfWidthPx: halfWidthPx }, opts);
    const cols = [];
    for (const st of strokes) {
      const c = spineToRails(contours, st.spine, o, st.freeStart, st.freeEnd, st.closed);
      if (c && c.railA.length >= 2) { c.closed = !!st.closed; cols.push(c); }
    }
    return cols;
  }

  return {
    farthestBoundaryPair,
    splitBoundary,
    chainLength,
    resampleChain,
    estimateWidthMm,
    lineSegX,
    satinColumn,
    medialSatin,
    glyphColumns,
    // internals exposed for testing/diagnostics
    rasterize,
    thin,
    pruneSkeleton,
    skeletonEdges,
    skeletonPath,
  };
});
