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

  // Generate zig-zag satin stitch points bouncing between the two long edges of
  // a thin/elongated ring.
  //
  // opts = { spacingMm, pxPerMm, pullCompMm=0 }
  //
  // Pairing note: splitBoundary walks A forward (i->j) and B forward (j->i), so
  // B already runs the OPPOSITE direction along the length. Reversing the
  // resampled B ("pb") therefore makes pb'[k] progress the same direction as
  // pa[k], so pa[k] and pb'[k] are the two edge points at the same position
  // along the column length — the correct edge-to-edge cross pair.
  //
  // Emit order pa[0], pb'[0], pa[1], pb'[1], ... : each (pa[k] -> pb'[k]) is a
  // cross-stitch spanning the width, and consecutive crosses advance along the
  // length, producing the satin bounce.
  function satinColumn(ring, opts) {
    if (!ring || ring.length < 3) return [];
    const spacingMm = opts.spacingMm;
    const pxPerMm = opts.pxPerMm;
    const pullCompMm = opts.pullCompMm || 0;

    const [i, j] = farthestBoundaryPair(ring);
    const [A, B] = splitBoundary(ring, i, j);

    const denom = spacingMm * pxPerMm;
    const longest = Math.max(chainLength(A), chainLength(B));
    const steps = denom > 0 ? Math.max(2, Math.ceil(longest / denom)) : 2;

    const pa = resampleChain(A, steps);
    const pb = resampleChain(B, steps).reverse(); // pb'[k] pairs with pa[k]

    const offset = (pullCompMm * pxPerMm) / 2;
    const out = [];
    for (let k = 0; k < steps; k++) {
      let a = pa[k];
      let b = pb[k];
      if (offset > 0) {
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        a = pushOut(a, mx, my, offset);
        b = pushOut(b, mx, my, offset);
      }
      out.push(a);
      out.push(b);
    }
    return out;
  }

  return {
    farthestBoundaryPair,
    splitBoundary,
    chainLength,
    resampleChain,
    estimateWidthMm,
    satinColumn,
  };
});
