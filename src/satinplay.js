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

  // Arc-length fraction where the SEGMENT p0-p1 crosses the polyline `chain`,
  // or null if it never crosses. A rung is authored to INTERSECT both rails
  // (Ink/Stitch: "each rung should intersect both rails once") — the crossing
  // is the true anchor. Nearest-point anchoring can grab the wrong pass of a
  // rail that doubles back (a cursive eye), which is what fanned those glyphs.
  // If it crosses more than once, the crossing nearest the segment midpoint is
  // used. The segment is extended slightly (5% each end) for robustness.
  function segCrossFrac(chain, p0, p1) {
    const ex0 = p0.x - 0.05 * (p1.x - p0.x), ey0 = p0.y - 0.05 * (p1.y - p0.y);
    const ex1 = p1.x + 0.05 * (p1.x - p0.x), ey1 = p1.y + 0.05 * (p1.y - p0.y);
    const rx = ex1 - ex0, ry = ey1 - ey0;
    const total = chainLength(chain) || 1;
    let best = null, bestScore = Infinity;
    let acc = 0;
    for (let k = 0; k + 1 < chain.length; k++) {
      const a = chain[k], b = chain[k + 1];
      const sx = b.x - a.x, sy = b.y - a.y;
      const den = rx * sy - ry * sx;
      const segLen = Math.hypot(sx, sy);
      if (Math.abs(den) > EPS) {
        const t = ((a.x - ex0) * sy - (a.y - ey0) * sx) / den;   // along rung
        const u = ((a.x - ex0) * ry - (a.y - ey0) * rx) / den;   // along rail seg
        if (t >= -0.01 && t <= 1.01 && u >= -0.01 && u <= 1.01) {
          const score = Math.abs(t - 0.5);                        // prefer mid-rung crossing
          if (score < bestScore) { bestScore = score; best = (acc + u * segLen) / total; }
        }
      }
      acc += segLen;
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
    const floor = samplesPerSection || 12;   // minimum samples per section
    const STEP = 2;                            // px between corresponded samples
    // Cut fractions on each rail. A rung's anchor on a rail is where it CROSSES
    // that rail (true intersection); nearest-point is only a fallback. This
    // matters on rails that double back (cursive eyes): nearest-point could
    // anchor a rung to the wrong pass of the rail, producing a section whose
    // rail-B span ran BACKWARD — subByFrac then degenerated to a straight chord
    // across the glyph, which read as a fan/spray of long stitches.
    const cuts = [{ a: 0, b: 0 }, { a: 1, b: 1 }];
    if (rungs && rungs.length) {
      for (const rg of rungs) {
        const pa = rg[0], pb = rg[1];
        const a = segCrossFrac(railA, pa, pb);
        const b = segCrossFrac(railB, pa, pb);
        cuts.push({
          a: a != null ? a : nearestFrac(railA, pa.x, pa.y),
          b: b != null ? b : nearestFrac(railB, pb.x, pb.y),
        });
      }
    }
    cuts.sort((p, q) => p.a - q.a);
    // Enforce monotonic rail-B fractions: a rung whose B anchor goes backward
    // relative to the previous cut would create a reversed section — drop it.
    const mono = [cuts[0]];
    for (let i = 1; i < cuts.length; i++) {
      if (cuts[i].b >= mono[mono.length - 1].b - 1e-6) mono.push(cuts[i]);
    }
    if (mono[mono.length - 1].a !== 1) mono.push({ a: 1, b: 1 });
    const A = [], B = [];
    for (let i = 0; i + 1 < mono.length; i++) {
      const c0 = mono[i], c1 = mono[i + 1];
      if (c1.a - c0.a < 1e-6) continue; // degenerate/duplicate cut
      const subA = subByFrac(railA, c0.a, c1.a);
      const subB = subByFrac(railB, Math.min(c0.b, c1.b), Math.max(c0.b, c1.b));
      // Sample density scales with the section's length, so long / tightly
      // curved sections (e.g. the eye of an "e") are followed finely instead of
      // corner-cut by a flat count — which skewed the cross-stitches.
      const secLen = Math.max(chainLength(subA), chainLength(subB));
      const nn = Math.max(floor, Math.min(600, Math.ceil(secLen / STEP)));
      const sa = resampleChain(subA, nn);
      const sb = resampleChain(subB, nn);
      // drop the shared first point of every section after the first (continuity)
      const startK = i === 0 ? 0 : 1;
      for (let k = startK; k < nn; k++) { A.push(sa[k]); B.push(sb[k]); }
    }
    return { A, B };
  }

  // Interpolate a point on `arr` at arc-length position `s` along `cum`
  // (arr's own cumulative arc-length table, same length as arr). Used by
  // slantDeg below to sample rail A and rail B at DIFFERENT arc-length
  // positions (a lean) instead of always the same one (perpendicular).
  function interpAt(arr, cum, s) {
    const n = arr.length;
    if (s <= 0) return { x: arr[0].x, y: arr[0].y };
    const total = cum[n - 1];
    if (s >= total) return { x: arr[n - 1].x, y: arr[n - 1].y };
    let i = 0;
    while (i < n - 2 && cum[i + 1] < s) i++;
    const segLen = cum[i + 1] - cum[i] || 1;
    const f = (s - cum[i]) / segLen;
    return { x: arr[i].x + (arr[i + 1].x - arr[i].x) * f, y: arr[i].y + (arr[i + 1].y - arr[i].y) * f };
  }

  // ---- Counter guard (fine-lettering review item 4, 2026-09-03) ----------
  // "Enlarge, never close, the counters." The Bold weight preset widens every
  // column by pushing its rails apart (the same mechanism as pull comp), and
  // a counter — the eye of an e, the bowl of a d, the slot between two stems
  // — is nothing but the gap between two rails that face each other. Widen
  // both blindly and the gap closes: at 0.3 mm of weight a 0.7 mm eye is
  // 0.4 mm, under the width at which two rails pile thread on a point. The
  // Python engine's pull comp already holds a HOLE open when shrinking it
  // would take it under the detail floor (stage5_overlap, `hole_floor`);
  // this is the font path's version, per rail station, because a font glyph
  // is columns, not a polygon with holes.
  //
  // `railCloud` samples every rail of a glyph's columns into points with
  // OUTWARD normals, at emitZigzag's own station spacing, so a station can
  // ask what faces it. `counterGap` answers: the distance straight ahead to
  // the nearest rail whose normal points back at us, or Infinity for an
  // outside edge (nothing faces the outside of an H's stem; its own far rail
  // is BEHIND it and its neighbours along the rail point the same way).
  function railCloud(geoms, spacingPx) {
    const cloud = [];
    const step = spacingPx > 0 ? spacingPx : 4;
    for (const geom of geoms) {
      if (!geom || !(geom.total > EPS) || geom.A.length < 2) continue;
      const steps = Math.max(2, Math.ceil(geom.total / step));
      for (let t = 0; t <= steps; t++) {
        const s = (t / steps) * geom.total;
        const a = interpAt(geom.A, geom.cum, s), b = interpAt(geom.B, geom.cum, s);
        let vx = a.x - b.x, vy = a.y - b.y; const L = Math.hypot(vx, vy);
        if (!(L > EPS)) continue;
        vx /= L; vy /= L;
        cloud.push({ x: a.x, y: a.y, nx: vx, ny: vy });
        cloud.push({ x: b.x, y: b.y, nx: -vx, ny: -vy });
      }
    }
    return cloud;
  }
  function counterGap(x, y, nx, ny, cloud, windowPx) {
    let best = Infinity;
    for (const q of cloud) {
      const dx = q.x - x, dy = q.y - y;
      const ahead = dx * nx + dy * ny;
      if (ahead <= EPS || ahead >= best) continue;
      if (q.nx * nx + q.ny * ny > -0.3) continue;   // not facing us
      if (Math.abs(dx * ny - dy * nx) > windowPx) continue;   // not straight ahead
      best = ahead;
    }
    return best;
  }
  // How far each rail of one station moves outward: the fabric's pull comp
  // in full on both (that is physics, gate 1's, untouched), plus the weight
  // — in full on an outside edge, and across a counter no more than the gap
  // can spare after the pull with the floor kept: both sides move, so each
  // takes half of what the gap can absorb. A gap already under the floor at
  // normal weight gets no weight at all — bold widens the stroke's outside
  // instead of closing the counter further. `guard` null = legacy: one
  // shared offset, the pre-guard stream byte for byte.
  function stationPush(ax, ay, bx, by, pullPx, weightPx, guard, count) {
    const half = (pullPx + weightPx) / 2;
    if (!guard || !(weightPx > 0)) return { a: half, b: half, apply: half > 0 };
    let vx = ax - bx, vy = ay - by; const L = Math.hypot(vx, vy) || 1; vx /= L; vy /= L;
    const room = (gap) => {
      if (!isFinite(gap)) return weightPx;
      const allowed = Math.max(0, Math.min(weightPx, gap - pullPx - guard.floorPx));
      if (count && guard.stats && allowed < weightPx) guard.stats.counterHeld += 1;
      return allowed;
    };
    const wa = room(counterGap(ax, ay, vx, vy, guard.cloud, guard.windowPx));
    const wb = room(counterGap(bx, by, -vx, -vy, guard.cloud, guard.windowPx));
    return { a: pullPx / 2 + wa / 2, b: pullPx / 2 + wb / 2, apply: true };
  }

  // ---- Short stitches (Law 53; fine-lettering review item 6, 2026-09-03) --
  // On the inside of a bend the rail is shorter than the centerline, so the
  // penetrations along it bunch up closer than the station spacing; under
  // `atPx` the needle starts re-entering the hole it just made and the edge
  // frays. Every OTHER cross has its crowded penetration pulled back along
  // the cross toward the far rail — the Python engine's `_short_stitch_guard`
  // and `_pull_short`, mirrored with its numbers: a fraction of the cross
  // (0.35) capped at an absolute distance (0.6 mm — clearing a hole takes the
  // same few tenths whatever the column width; uncapped, 0.35 of a 2.78 mm
  // cross moved a point 0.97 mm and read as two 1 mm same-rail gaps), and
  // never past the point where the cross itself would fall under the cross
  // floor (1.01x, so float rounding cannot hand it to the drop check). That
  // last bound is the width gate Law 53 demands: the pull fades to nothing
  // as the column narrows toward the floor, so narrow lettering — Melco's
  // own documented trap for this feature — never gets an "excessively small
  // stitch" out of it. Off (no `opts.shortStitch`) is byte-identical.
  function pullShort(p, toward, ss, minCrossPx) {
    const cross = Math.hypot(toward.x - p.x, toward.y - p.y);
    let f = ss.pull;
    if (cross > 1e-9) {
      if (ss.maxPx > 0) f = Math.min(f, ss.maxPx / cross);
      f = Math.min(f, Math.max(0, 1 - 1.01 * minCrossPx / cross));
    }
    return { x: p.x + (toward.x - p.x) * f, y: p.y + (toward.y - p.y) * f };
  }

  // Turn corresponded pairs into zig-zag satin at the given density.
  // opts = { spacingMm, pxPerMm, pullCompMm=0, weightMm=0, slantDeg=0,
  //          minCrossMm=0, counterGuard=null, shortStitch=null }.
  // `shortStitch` = { atMm, pull, maxMm, stats } — see pullShort above.
  // `weightMm` is the bold/thin preset's share of the widening, kept apart
  // from `pullCompMm` so the counter guard can hold it back per rail while
  // the fabric's pull comp stays whole; absent, the two were one number and
  // still add up to the same offset. `counterGuard` = { cloud, floorPx,
  // windowPx, stats } from railCloud — see stationPush.
  //
  // slantDeg (Font editing abilities Round 1, italic-style lean): 0 keeps
  // the cross-stitch perpendicular to the column (today's behavior,
  // byte-identical). A nonzero value samples rail A AHEAD of the centerline
  // target and rail B BEHIND it (or vice versa) by halfWidth*tan(slantDeg) —
  // the same "shift the far-rail contact point along the column" trick a
  // real italic satin lean uses — verified analytically before this task was
  // written: on a synthetic straight column this produces a cross-stitch
  // angle of EXACTLY 90+slantDeg degrees away from the column's clamped end
  // stations (where the shifted target runs off the column and clamps back
  // toward perpendicular — an intentional, graceful taper, not a bug).
  function emitZigzag(A, B, opts) {
    const denom = (opts.spacingMm || 0.4) * (opts.pxPerMm || 1);
    const pullPx = (opts.pullCompMm || 0) * (opts.pxPerMm || 1);
    const weightPx = (opts.weightMm || 0) * (opts.pxPerMm || 1);
    const guard = weightPx > 0 && opts.counterGuard && opts.counterGuard.cloud ? opts.counterGuard : null;
    const ss = opts.shortStitch && opts.shortStitch.atMm > 0 ? {
      atPx: opts.shortStitch.atMm * (opts.pxPerMm || 1),
      pull: opts.shortStitch.pull == null ? 0.35 : opts.shortStitch.pull,
      maxPx: (opts.shortStitch.maxMm || 0) * (opts.pxPerMm || 1),
      stats: opts.shortStitch.stats || null,
    } : null;
    let prevA = null, prevB = null;
    // Cross floor (Law 47 / 51, 2026-09-03). A cross shorter than
    // `opts.minCrossMm` is not a satin stitch: the two rails have pinched
    // together (a tapered tip, a hairline stroke) and sewing it piles thread
    // on a point — the Python engine drops the same cross at
    // `machine.SATIN_MIN_CROSS_MM`. Before this option existed the only guard
    // was 0.3 DESIGN PIXELS (0.04 mm at the lettering default), so the browser
    // path sewed every pinched cross the other engine refuses. Absent or 0
    // keeps exactly that legacy guard, so every caller that never asks is
    // byte-identical; satinfont passes the floor pre-divided by the fit scale.
    const minCrossPx = Math.max(0.3, (opts.minCrossMm || 0) * (opts.pxPerMm || 1));
    const slantRad = ((opts.slantDeg || 0) * Math.PI) / 180;
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
      if (slantRad) {
        const halfW = Math.hypot(ax - bx, ay - by) / 2;
        const shift = halfW * Math.tan(slantRad);
        const clampS = (s) => Math.max(0, Math.min(total, s));
        const pA1 = interpAt(A, cum, clampS(target + shift));
        const pB1 = interpAt(B, cum, clampS(target - shift));
        ax = pA1.x; ay = pA1.y; bx = pB1.x; by = pB1.y;
      }
      const push = stationPush(ax, ay, bx, by, pullPx, weightPx, guard, true);
      if (push.apply) {
        let vx = ax - bx, vy = ay - by; const L = Math.hypot(vx, vy) || 1; vx /= L; vy /= L;
        ax += vx * push.a; ay += vy * push.a; bx -= vx * push.b; by -= vy * push.b;
      }
      let pA = { x: ax, y: ay }, pB = { x: bx, y: by };
      // Short stitches: on every other station, a penetration that landed
      // under `atPx` from the previous one on its rail is pulled back along
      // the cross. The comparison is against the previous station AS PLACED
      // (even stations are never pulled), the same way the Python guard
      // reads its unpulled rail lists; and the second rail is pulled toward
      // the first rail's already-pulled point, as there.
      if (ss && prevA && t % 2 === 1) {
        if (Math.hypot(pA.x - prevA.x, pA.y - prevA.y) < ss.atPx) { pA = pullShort(pA, pB, ss, minCrossPx); if (ss.stats) ss.stats.shortStitches += 1; }
        if (Math.hypot(pB.x - prevB.x, pB.y - prevB.y) < ss.atPx) { pB = pullShort(pB, pA, ss, minCrossPx); if (ss.stats) ss.stats.shortStitches += 1; }
      }
      prevA = { x: ax, y: ay }; prevB = { x: bx, y: by };
      if (Math.hypot(pA.x - pB.x, pA.y - pB.y) < minCrossPx) continue;
      if (t % 2 === 0) { out.push(pA, pB); } else { out.push(pB, pA); }
    }
    return out;
  }

  // Split a satin span [lo,hi] (fractions, lo < hi) into SATIN and HAIRLINE
  // segments by the cross length at each zigzag station — the same stations,
  // the same pull-comp widening and the same floor emitZigzag applies, so a
  // segment classed satin here keeps its crosses there.
  //
  // Why a split and not a per-cross drop: on a column that hovers around the
  // floor (a hand-authored outline face, a script's thick-thin stroke) the
  // crosses that survive a per-cross drop are SCATTERED, and the zigzag joins
  // survivor to survivor with a straight chord — across the glyph's interior
  // on an outline letter (measured 2026-09-03 on cooper_marif: a diagonal
  // through the F). Classing whole stretches instead sews the thick parts as
  // satin and the thin stretches as a run, which is what a digitizer does by
  // hand with a stroke that changes weight.
  //
  // Minimum segment: two stations (`minSeg`), or one bean stitch if that is
  // longer. A run shorter than that is absorbed into its longer neighbour
  // until every segment clears it, so a single wobble under the floor stays
  // satin (emitZigzag drops that one cross — a chord ONE station long, along
  // the column) and a lone surviving cross inside a hairline stays a run.
  //
  // Returns [{ f0, f1, thin }] in lo -> hi order, covering [lo,hi] exactly.
  // With no floor (`opts.minCrossMm` absent/0) it is one satin segment, so
  // legacy callers see no change.
  function splitByCrossFloor(geom, lo, hi, opts) {
    const o = opts || {};
    const one = [{ f0: lo, f1: hi, thin: false }];
    if (!geom || !(geom.total > EPS) || !(hi > lo)) return one;
    const pxPerMm = o.pxPerMm || 1;
    const minCrossPx = (o.minCrossMm || 0) * pxPerMm;
    if (!(minCrossPx > 0)) return one;
    const spacingPx = (o.spacingMm || 0.4) * pxPerMm;
    // The same widening emitZigzag will apply at this station — pull comp
    // plus weight, the weight held back by the counter guard where it holds
    // it back there — so a stretch classed satin here keeps its crosses.
    const pullPx = (o.pullCompMm || 0) * pxPerMm, weightPx = (o.weightMm || 0) * pxPerMm;
    const guard = weightPx > 0 && o.counterGuard && o.counterGuard.cloud ? o.counterGuard : null;
    const s0 = lo * geom.total, len = (hi - lo) * geom.total;
    if (!(len > EPS)) return one;
    const steps = Math.max(2, Math.ceil(len / (spacingPx > 0 ? spacingPx : 4)));
    let runs = [];
    for (let t = 0; t <= steps; t++) {
      const s = s0 + (t / steps) * len;
      const a = interpAt(geom.A, geom.cum, s), b = interpAt(geom.B, geom.cum, s);
      const push = stationPush(a.x, a.y, b.x, b.y, pullPx, weightPx, guard, false);
      const compPx = push.apply ? push.a + push.b : 0;
      const thin = Math.hypot(a.x - b.x, a.y - b.y) + compPx < minCrossPx;
      const last = runs[runs.length - 1];
      if (last && last.thin === thin) last.end = t; else runs.push({ thin, start: t, end: t });
    }
    const beanPx = (o.beanStepMm || 0.73) * pxPerMm;
    const minSeg = Math.max(2, Math.ceil(beanPx / (spacingPx > 0 ? spacingPx : 4)));
    // A hairline run sews as a bean only past the run tier's own floor —
    // three bean stations of centerline, under which the needle re-enters
    // its own holes. Shorter, it is a tapered tip or a dip, and it stays
    // what the floor alone makes it: dropped, the zigzag hopping the gap
    // along the column. (A satin island inside a hairline only has to
    // clear minSeg to stay satin; under that it joins the run.)
    const beanSeg = Math.max(minSeg, Math.ceil((2 * beanPx) / (spacingPx > 0 ? spacingPx : 4)));
    const count = (r) => r.end - r.start + 1;
    const need = (i) => (runs[i].thin ? beanSeg : minSeg);
    // Absorb the shortest under-length run into its longer neighbour, then
    // coalesce, until every run clears its floor (or one run remains).
    while (runs.length > 1) {
      let idx = -1, best = Infinity;
      for (let i = 0; i < runs.length; i++) if (count(runs[i]) < need(i) && count(runs[i]) < best) { best = count(runs[i]); idx = i; }
      if (idx < 0) break;
      const prev = runs[idx - 1], next = runs[idx + 1];
      const into = prev && (!next || count(prev) >= count(next)) ? idx - 1 : idx + 1;
      runs[idx].thin = runs[into].thin;
      const merged = [];
      for (const r of runs) {
        const last = merged[merged.length - 1];
        if (last && last.thin === r.thin) last.end = r.end; else merged.push({ thin: r.thin, start: r.start, end: r.end });
      }
      runs = merged;
    }
    // One run left: the whole span is satin, or the whole span is a hairline
    // — which still has to clear the three-station floor to sew as one.
    if (runs.length === 1) return [{ f0: lo, f1: hi, thin: runs[0].thin && count(runs[0]) >= beanSeg }];
    // Segment boundaries sit halfway between the last station of one run and
    // the first of the next; the outer ends are the span's own.
    const at = (t) => lo + (t / steps) * (hi - lo);
    return runs.map((r, i) => ({
      f0: i === 0 ? lo : at(r.start - 0.5),
      f1: i === runs.length - 1 ? hi : at(r.end + 0.5),
      thin: r.thin,
    }));
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

  // ---- STRUCTURAL UNDERLAY (Law 50) --------------------------------------
  //
  // These emit the stitches that go UNDER a satin column to stabilise it: they
  // are sewn before the satin over the SAME span and end up hidden by it.
  //
  // They are NOT the same thing as the Euler-walk travel that satinfont's
  // router lays between satin spans. That travel is `underpath` — it exists to
  // get the needle somewhere without a trim, it follows the centerline because
  // the centerline is the hideable place to walk, and it appears only on spans
  // the walk visits more than once. Structural underlay is chosen by cap
  // height, applies to EVERY satin span, and is a stitch-quality decision.
  // The two used to share the tag `kind: "underlay"`, which is precisely why
  // nobody noticed lettering had no real underlay for as long as it didn't.
  //
  // Published constants these are built to (Law 50): center walk 2 repeats at
  // 3 mm stitch length, 50% position; contour 3 mm length, 0.4 mm inset each
  // side. All mm here are in the CALLER's mm — satinfont pre-divides by the
  // downstream fit scale exactly the way it already does for spacingMm.

  // Total ABSOLUTE turning of a polyline, in radians. Absolute (not signed) so
  // an S-curve counts both bends — that errs toward more subdivision, which is
  // the safe direction here.
  function chainTurn(chain) {
    let t = 0;
    for (let i = 1; i + 1 < chain.length; i++) {
      const ax = chain[i].x - chain[i - 1].x, ay = chain[i].y - chain[i - 1].y;
      const bx = chain[i + 1].x - chain[i].x, by = chain[i + 1].y - chain[i].y;
      const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
      if (la < EPS || lb < EPS) continue;
      let c = (ax * bx + ay * by) / (la * lb);
      t += Math.acos(c < -1 ? -1 : c > 1 ? 1 : c);
    }
    return t;
  }

  // Resample `chain` so no emitted segment exceeds stepPx AND no emitted
  // segment CHORDS more than maxDevPx away from the curve it replaces.
  // Returns null when the chain is shorter than minPx — a span too short to
  // carry one stitch at the minimum length gets no underlay at all, rather
  // than a needle stab in place that rounds to a zero-delta DST record
  // (Law 51: the min-stitch floor is real, but it must never be applied as a
  // global 1 mm cull).
  //
  // The chord bound is the part that is easy to forget and impossible to miss
  // once rendered. A running stitch is a straight line between two points on a
  // curve, so on a tightly curved column a 3 mm underlay stitch cuts across
  // the bend and can leave the column entirely — a 4.5 mm-tall "o" has a
  // centerline radius near 2.2 mm, where a 3 mm chord sags 0.57 mm off the
  // curve while the column's own half-width is only about 0.45 mm. The
  // underlay would sit outside the satin that is supposed to cover it.
  //
  // For a segment of arc length s on a curve of radius R the sag is s^2/(8R),
  // and R = len/turn over the span, so bounding the sag by `maxDevPx` gives
  // nSeg >= sqrt(len*turn / (8*maxDevPx)). Straight columns have turn ~ 0 and
  // are untouched by this; only curves subdivide, and only as much as their
  // own curvature demands.
  //
  // nSeg is then capped at len/minPx, which both stops a doubling-back cursive
  // span from exploding and makes "every segment >= minPx" true by
  // construction rather than by cleanup.
  function walkChain(chain, stepPx, minPx, maxDevPx) {
    if (!chain || chain.length < 2) return null;
    const len = chainLength(chain);
    if (!(len > 0) || len < minPx) return null;
    let nSeg = stepPx > 0 ? Math.max(1, Math.ceil(len / stepPx)) : 1;
    if (maxDevPx > 0) {
      const turn = chainTurn(chain);
      if (turn > EPS) nSeg = Math.max(nSeg, Math.ceil(Math.sqrt((len * turn) / (8 * maxDevPx))));
    }
    if (minPx > 0) nSeg = Math.min(nSeg, Math.max(1, Math.floor(len / minPx)));
    return resampleChain(chain, nSeg + 1);
  }

  // Narrowest half-width across a corresponded span, in px. Used to size the
  // chord tolerance above: how far the underlay may stray from the centerline
  // is a question about how much room the column has.
  function minHalfWidth(As, Bs) {
    let m = Infinity;
    const n = Math.min(As.length, Bs.length);
    for (let i = 0; i < n; i++) m = Math.min(m, Math.hypot(As[i].x - Bs[i].x, As[i].y - Bs[i].y) / 2);
    return isFinite(m) ? m : 0;
  }

  // Append `leg` onto `out`, dropping leg's first point (it duplicates out's
  // last). Skips the whole leg if it is degenerate.
  function appendLeg(out, leg) {
    if (!leg || leg.length < 2) return out;
    for (let i = out.length ? 1 : 0; i < leg.length; i++) out.push(leg[i]);
    return out;
  }

  // Drop points that would emit a stitch shorter than minPx (Law 51's filter,
  // applied LOCALLY to an underlay path rather than globally to the design —
  // a global 1 mm cull is what shreds small satin).
  //
  // walkChain alone cannot guarantee the floor once legs are joined: an edge
  // run's cross-over at a tapered column tip is only as long as the column is
  // wide there, which can round to a zero-delta DST record — a needle stab in
  // place. The path's LAST point is preserved exactly even when it is culled
  // (the previous kept point is moved onto it instead), because the whole
  // point of these closed walks is that they finish where the satin starts.
  function cullShort(pts, minPx) {
    if (!pts || pts.length < 2) return [];
    if (!(minPx > 0)) return pts;
    const near = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) < minPx;
    const out = [pts[0]];
    for (let i = 1; i < pts.length - 1; i++) if (!near(out[out.length - 1], pts[i])) out.push(pts[i]);
    // The endpoint is non-negotiable, so make room for it rather than snapping
    // an already-kept point onto it — dropping points until the last survivor
    // clears the floor is what keeps "every segment >= minPx" true. (Snapping
    // instead leaves a segment of |P - last|, which can be arbitrarily small.)
    const last = pts[pts.length - 1];
    while (out.length > 1 && near(out[out.length - 1], last)) out.pop();
    if (near(out[out.length - 1], last)) return [];
    out.push(last);
    return out;
  }

  // Slice the geom's arrays to the span, oriented in the TRAVERSAL direction
  // f0 -> f1 (which may run backward along the column). Orientation matters:
  // the underlay has to hand the needle back to wherever the satin starts.
  function spanArrays(geom, arrs, f0, f1) {
    const lo = Math.min(f0, f1), hi = Math.max(f0, f1);
    const out = sliceParallel(arrs, geom.cum, lo * geom.total, hi * geom.total);
    return f0 > f1 ? out.map((a) => a.slice().reverse()) : out;
  }

  // CENTER-WALK underlay over traversal span f0 -> f1 of a precomputed
  // columnGeom. Walks the column centerline (the 50% position) `repeats`
  // times, alternating direction. The published default of 2 repeats is not
  // just Ink/Stitch's number — it is also what the router needs: an even
  // repeat count ends the walk back at f0, which is exactly where the satin
  // for this span begins, so real underlay costs ZERO extra travel.
  // opts = { stepMm=3, repeats=2, minStitchMm=0.5, pxPerMm=1 }.
  function centerUnderlayFromGeom(geom, f0, f1, opts) {
    if (!geom || geom.total <= EPS || geom.C.length < 2) return [];
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 1;
    const [Cs, As, Bs] = spanArrays(geom, [geom.C, geom.A, geom.B], f0, f1);
    const minPx = (o.minStitchMm == null ? 0.5 : o.minStitchMm) * pxPerMm;
    // A center walk has the whole half-width to play with; spend at most a
    // third of it on chord error, and never let a pinched-to-nothing tip drive
    // the tolerance to zero (walkChain's min-stitch cap is the real backstop).
    const devPx = Math.max(0.05 * pxPerMm, 0.35 * minHalfWidth(As, Bs));
    const fwd = walkChain(Cs, (o.stepMm == null ? 3 : o.stepMm) * pxPerMm, minPx, devPx);
    if (!fwd) return [];
    const repeats = Math.max(1, Math.round(o.repeats == null ? 2 : o.repeats));
    const out = fwd.slice();
    for (let r = 1; r < repeats; r++) appendLeg(out, r % 2 === 1 ? fwd.slice().reverse() : fwd.slice());
    return cullShort(out, (o.minStitchMm == null ? 0.5 : o.minStitchMm) * pxPerMm);
  }

  // BEAN RUN over traversal span f0 -> f1 of a precomputed columnGeom: the
  // light tier for a span whose satin came back empty under the cross floor
  // (every cross under `minCrossMm` — a hairline stroke). Walks the
  // centerline `passes` times, alternating direction, at `stepMm`; an ODD
  // pass count ends at f1, where the glyph's traversal continues, so the
  // fallback costs no extra travel. Same generator as the center-walk
  // underlay — a bean IS a center walk, sewn as the visible stitch instead of
  // under one — kept under its own name so a reader of the router does not
  // have to know that. The constants (0.73 mm, 3 passes) come from satinfont,
  // which mirrors the Python engine's corpus-measured run tier.
  // opts = { stepMm, passes=3, minStitchMm=0.5, pxPerMm=1 }.
  function beanFromGeom(geom, f0, f1, opts) {
    const o = opts || {};
    return centerUnderlayFromGeom(geom, f0, f1, {
      pxPerMm: o.pxPerMm, stepMm: o.stepMm, minStitchMm: o.minStitchMm,
      repeats: o.passes == null ? 3 : o.passes,
    });
  }

  // Move each corresponded rail pair inward along its OWN cross-line by
  // `insetPx`. Because A[i] and B[i] are the two ends of one cross-stitch, an
  // offset along A->B is "inset N mm per side" measured across the column,
  // which is the measurement Embrilliance's 0.4 mm ("half a needle width or
  // slightly more") actually refers to.
  //
  // The inset is capped at 40% of the LOCAL column width so the two inset
  // rails can never cross: in a hairline column an edge run collapses toward
  // the centerline instead of turning inside out. This also makes "the
  // underlay lies inside its column" true by construction, not by luck.
  function insetPair(As, Bs, insetPx) {
    const Ai = [], Bi = [];
    const n = Math.min(As.length, Bs.length);
    for (let i = 0; i < n; i++) {
      const ax = As[i].x, ay = As[i].y, bx = Bs[i].x, by = Bs[i].y;
      const dx = bx - ax, dy = by - ay, w = Math.hypot(dx, dy);
      if (!(w > EPS)) { Ai.push({ x: ax, y: ay }); Bi.push({ x: bx, y: by }); continue; }
      const d = Math.min(insetPx, 0.4 * w), ux = dx / w, uy = dy / w;
      Ai.push({ x: ax + ux * d, y: ay + uy * d });
      Bi.push({ x: bx - ux * d, y: by - uy * d });
    }
    return [Ai, Bi];
  }

  // EDGE / CONTOUR underlay over traversal span f0 -> f1: a closed outline
  // just inside both rails. Runs down inset-rail A, crosses the column, comes
  // back along inset-rail B, and closes across — so like the center walk it
  // finishes at the f0 end where the satin starts.
  // opts = { stepMm=3, insetMm=0.4, minStitchMm=0.5, pxPerMm=1 }.
  function edgeUnderlayFromGeom(geom, f0, f1, opts) {
    if (!geom || geom.total <= EPS || geom.A.length < 2) return [];
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 1;
    const stepPx = (o.stepMm == null ? 3 : o.stepMm) * pxPerMm;
    const minPx = (o.minStitchMm == null ? 0.5 : o.minStitchMm) * pxPerMm;
    const [As, Bs] = spanArrays(geom, [geom.A, geom.B], f0, f1);
    const insetPx = (o.insetMm == null ? 0.4 : o.insetMm) * pxPerMm;
    const [Ai, Bi] = insetPair(As, Bs, insetPx);
    // An inset rail has LESS room than the centerline does: chord error always
    // pulls toward the centre of curvature, and on the inside rail of a bowl
    // that direction is straight out of the column, with only the inset itself
    // standing in the way. So bound by the inset as well as by the half-width.
    const devPx = Math.max(0.05 * pxPerMm, Math.min(0.35 * minHalfWidth(As, Bs), 0.5 * insetPx));
    const legA = walkChain(Ai, stepPx, minPx, devPx);
    const legB = walkChain(Bi.slice().reverse(), stepPx, minPx, devPx);
    if (!legA || !legB) return [];
    const out = legA.slice();
    // cross at the far end, back along B, then close across at the near end.
    // The crossings are only as long as the column is wide, so they can fall
    // under the min stitch (or to nothing at all, at a tapered tip) — cullShort
    // below removes those rather than emitting a stab in place.
    const cross = (from, to) => walkChain([from, to], stepPx, 0) || [from, to];
    appendLeg(out, cross(out[out.length - 1], legB[0]));
    appendLeg(out, legB);
    appendLeg(out, cross(out[out.length - 1], legA[0]));
    return cullShort(out, minPx);
  }

  // Main entry: explicit rails (+optional rungs) -> satin zig-zag point list.
  function satinFromRails(railA, railB, rungs, opts) {
    if (!railA || !railB || railA.length < 2 || railB.length < 2) return [];
    const { A, B } = correspond(railA, railB, rungs || [], (opts && opts.samplesPerSection) || 12);
    return emitZigzag(A, B, opts || {});
  }

  // Whole-column convenience form of centerUnderlayFromGeom, for callers that
  // hold raw rails rather than a precomputed columnGeom.
  //
  // This function existed before this commit and had never run: zero callers
  // anywhere in the tree. It was also not usable as written, for three
  // reasons worth recording so it is not "fixed" back:
  //   1. it asked resampleChain for `ceil(len/step)` POINTS while meaning that
  //      many SEGMENTS, so emitted stitches ran up to 2x the requested length;
  //   2. it walked the column once, leaving the needle at the FAR end, so
  //      every column would have paid a full-column travel before its satin;
  //   3. it took raw rails, so it could not serve satinfont's router at all —
  //      that router works in fraction spans of an already-corresponded
  //      columnGeom and would have had to re-run `correspond` per column.
  // It is now a wrapper over the geom form, which fixes all three.
  // opts = { stepMm=3, repeats=2, minStitchMm=0.5, pxPerMm=1 }.
  function centerRun(railA, railB, rungs, opts) {
    if (!railA || !railB || railA.length < 2 || railB.length < 2) return [];
    const o = opts || {};
    const geom = columnGeom(railA, railB, rungs || [], o.samplesPerSection || 12);
    return centerUnderlayFromGeom(geom, 0, 1, o);
  }

  return {
    satinFromRails, centerRun, correspond, columnGeom, satinFromGeom, centerFromGeom,
    centerUnderlayFromGeom, edgeUnderlayFromGeom, beanFromGeom, splitByCrossFloor,
    railCloud, counterGap, stationPush, pullShort,
  };
});
