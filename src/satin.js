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

  // Scanline-fill a ring into a binary grid at `gscale` px-per-unit.
  function rasterize(ring, gscale, minX, minY, gw, gh) {
    const mask = new Uint8Array(gw * gh);
    const n = ring.length;
    for (let j = 0; j < gh; j++) {
      const wy = minY + (j + 0.5) / gscale;
      const xs = [];
      for (let k = 0; k < n; k++) {
        const a = ring[k], b = ring[(k + 1) % n];
        if ((a.y <= wy && b.y > wy) || (b.y <= wy && a.y > wy)) {
          xs.push(a.x + (b.x - a.x) * ((wy - a.y) / (b.y - a.y)));
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

  function pointInRing(pt, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i].x, yi = ring[i].y, xj = ring[j].x, yj = ring[j].y;
      if ((yi > pt.y) !== (yj > pt.y) && pt.x < (xj - xi) * (pt.y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // Extend each end of the spine along its end-tangent, staying inside the ring,
  // so the satin reaches the stroke terminals (the skeleton retracts from ends).
  function extendSpine(spine, ring, maxExtPx) {
    const ext = (pIdx, qIdx) => {
      const p = spine[pIdx], q = spine[qIdx];
      let dx = p.x - q.x, dy = p.y - q.y; const L = Math.hypot(dx, dy) || 1; dx /= L; dy /= L;
      let added = null;
      for (let d = 2; d <= maxExtPx; d += 2) {
        const c = { x: p.x + dx * d, y: p.y + dy * d };
        if (pointInRing(c, ring)) added = c; else break;
      }
      return added;
    };
    const head = ext(0, 1), tail = ext(spine.length - 1, spine.length - 2);
    const res = spine.slice();
    if (tail) res.push(tail);
    if (head) res.unshift(head);
    return res;
  }

  // Satin along the medial axis (skeleton) of a single solid ring. Handles
  // strokes that double back (S, hooks) that the outline-split satinColumn
  // cannot. opts = { spacingMm, pxPerMm, pullCompMm=0, slantDeg=0 }.
  function medialSatin(ring, opts) {
    if (!ring || ring.length < 3) return [];
    const spacingMm = opts.spacingMm, pxPerMm = opts.pxPerMm;
    const pullCompMm = opts.pullCompMm || 0;
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const q of ring) { if (q.x < minX) minX = q.x; if (q.x > maxX) maxX = q.x; if (q.y < minY) minY = q.y; if (q.y > maxY) maxY = q.y; }
    const dim = Math.max(maxX - minX, maxY - minY);
    if (!(dim > EPS)) return [];

    const gscale = Math.min(1.5, 260 / dim);
    const gw = Math.ceil((maxX - minX) * gscale) + 3, gh = Math.ceil((maxY - minY) * gscale) + 3;
    const mask = thin(rasterize(ring, gscale, minX, minY, gw, gh), gw, gh);
    const gridPath = skeletonPath(mask, gw, gh);
    if (gridPath.length < 3) return satinColumn(ring, opts); // fallback to outline split

    let spine = gridPath.map(([i, j]) => ({ x: minX + (i + 0.5) / gscale, y: minY + (j + 0.5) / gscale }));
    spine = smoothChain(spine, 3);
    // Reach the terminals: extend each end along its tangent (skeleton retracts
    // from stroke ends by ~half the stroke width).
    const halfWidthPx = estimateWidthMm(ring, 1) / 2;
    if (halfWidthPx > EPS) spine = extendSpine(spine, ring, halfWidthPx * 1.3);
    const denom = spacingMm * pxPerMm;
    const stepPx = denom > 0 ? denom : 4;
    const spineLen = chainLength(spine);
    if (!(spineLen > EPS)) return satinColumn(ring, opts);
    spine = resampleChain(spine, Math.max(2, Math.ceil(spineLen / stepPx)));

    const N = spine.length;
    // Per-station stitch normal from the local spine tangent (+ optional slant).
    const norm = new Array(N);
    for (let t = 0; t < N; t++) {
      const prev = spine[Math.max(0, t - 1)], next = spine[Math.min(N - 1, t + 1)];
      let tx = next.x - prev.x, ty = next.y - prev.y;
      const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
      let nx = -ty, ny = tx;
      if (slantRad) { const cs = Math.cos(slantRad), sn = Math.sin(slantRad); const rx = nx * cs - ny * sn, ry = nx * sn + ny * cs; nx = rx; ny = ry; }
      norm[t] = { x: nx, y: ny };
    }
    // Square off the terminals: within ~one stroke width of each end, HOLD the
    // stitch angle at the "shoulder" so the cap stitches stay parallel to the
    // last good ones (rather than rotating with the curling spine and fanning
    // into a crossing at the tip).
    const arc = new Array(N); arc[0] = 0;
    for (let t = 1; t < N; t++) arc[t] = arc[t - 1] + Math.hypot(spine[t].x - spine[t - 1].x, spine[t].y - spine[t - 1].y);
    const total = arc[N - 1];
    const capLen = halfWidthPx * 1.4;
    let head = 0; while (head < N - 1 && arc[head] < capLen) head++;
    let tail = N - 1; while (tail > 0 && (total - arc[tail]) < capLen) tail--;
    const clampCaps = head < tail; // only when there's a stable middle to borrow from

    const out = [];
    const offset = (pullCompMm * pxPerMm) / 2;
    for (let t = 0; t < N; t++) {
      const s = spine[t];
      let n = norm[t];
      if (clampCaps) { if (t < head) n = norm[head]; else if (t > tail) n = norm[tail]; }
      const hitP = rayRingHit(ring, s.x, s.y, n.x, n.y);
      const hitN = rayRingHit(ring, s.x, s.y, -n.x, -n.y);
      if (!hitP || !hitN) continue;
      let pA = hitP, pB = hitN;
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < 0.5) continue;
      if (offset > 0) { const mx = (pA.x + pB.x) / 2, my = (pA.y + pB.y) / 2; pA = pushOut(pA, mx, my, offset); pB = pushOut(pB, mx, my, offset); }
      if (t % 2 === 0) { out.push(pA); out.push(pB); } else { out.push(pB); out.push(pA); }
    }
    return out.length >= 4 ? out : satinColumn(ring, opts);
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
  };
});
