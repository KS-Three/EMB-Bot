(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const EPS = 1e-9;

  function rotate(p, cos, sin) {
    return { x: p.x * cos - p.y * sin, y: p.x * sin + p.y * cos };
  }

  // Principal-axis angle (degrees) of a set of polygons — the angle a fill's
  // rows run at when nothing overrides them. Lived in digitize.js until the
  // lettering lane needed the same rule for a wide column (quality review
  // item 10); it is here so there is ONE definition rather than two that can
  // drift. digitize.js still calls it under its own name.
  function pcaAngleDeg(polys) {
    let n = 0, mx = 0, my = 0;
    for (const p of polys) for (const q of p) { mx += q.x; my += q.y; n++; }
    if (!n) return 45;
    mx /= n; my /= n;
    let sxx = 0, syy = 0, sxy = 0;
    for (const p of polys) for (const q of p) { const dx = q.x - mx, dy = q.y - my; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
    return 0.5 * Math.atan2(2 * sxy, sxx - syy) * 180 / Math.PI;
  }

  // --- opts.columns: a fill that never carries thread across a hole -----------
  //
  // The plain walk below sews row by row, so on a row the shape splits (a
  // hole, or the mouth of a U) it goes from one span straight to the next:
  // a float when the gap is longer than a stitch, a STITCH when it is not.
  // Measured 2026-10-02 on a 40 mm manual fill with two cut-outs: 76 untrimmed
  // floats across the 12 mm one, 912 mm of thread, and 20 stitches sewn
  // across the 3 mm one. Quality review 2026-09-08 section 4 names it.
  //
  // The cure is the Python engine's (stage6_fill.py, "Where the rows go"): cut
  // the rows into monotone COLUMNS -- a strip of consecutive rows that each
  // contribute exactly one span -- sew each column as its own boustrophedon,
  // and make the move between two columns an explicit decision.
  const COLUMN_OVERLAP_EPS = 1e-6;   // pure touching is a corner, not a passage
  const ON_EDGE_EPS = 1e-6;

  // rows: [{ ri, y, spans: [[x0, x1], ...], spanEdges: [[e0, e1], ...] }] in
  // scanline order, empty scanlines absent. -> { columns, above }: each column
  // is [{ ri, y, x0, x1, e0, e1 }, ...] top-down (e0, e1: the edge each end of
  // the row sits on), and above[i] lists the columns whose last row sits
  // directly over column i's first (what it forked from, or what merged into
  // it).
  // A port of `_columns`: a column continues into the next row only when the
  // correspondence is one-to-one, and only into the row physically next to it.
  function cutColumns(rows) {
    const columns = [], above = [];
    const overlaps = (a, b) => Math.min(a[1], b[1]) - Math.max(a[0], b[0]) > COLUMN_OVERLAP_EPS;
    let open = {};          // span index on the previous row -> its column
    let prevSpans = [];
    let prevRi = -2;
    for (const row of rows) {
      const contiguous = row.ri === prevRi + 1;
      const nowOpen = {};
      row.spans.forEach((sp, si) => {
        let parent = -1;
        const hits = [];
        if (contiguous) {
          prevSpans.forEach((psp, pi) => { if (overlaps(sp, psp)) hits.push(pi); });
          if (hits.length === 1) {
            // one-to-one only: the row above must not fan into two here
            const fan = row.spans.filter((s2) => overlaps(s2, prevSpans[hits[0]])).length;
            if (fan === 1 && open[hits[0]] !== undefined) parent = open[hits[0]];
          }
        }
        if (parent < 0) {
          columns.push([]);
          above.push(hits.map((pi) => open[pi]).filter((c) => c !== undefined));
          parent = columns.length - 1;
        }
        const on = row.spanEdges ? row.spanEdges[si] : [null, null];
        columns[parent].push({ ri: row.ri, y: row.y, x0: sp[0], x1: sp[1], e0: on[0], e1: on[1] });
        nowOpen[si] = parent;
      });
      open = nowOpen;
      prevSpans = row.spans;
      prevRi = row.ri;
    }
    return { columns, above };
  }

  function distToSegment(p, u, v) {
    const dx = v.x - u.x, dy = v.y - u.y, len2 = dx * dx + dy * dy;
    const t = len2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / len2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy));
  }

  // THE question every move of the column walk is asked: does the straight
  // move a -> b lay thread deeper than `tol` into ground the polygons do not
  // fill (even-odd: a hole, a notch, anything outside)?
  //
  // Depth, not crossing. A row end sits ON the boundary, so the ordinary
  // next-row move runs along it; and a row turn round a hole's corner clips
  // that corner by up to its own row pitch. At a fill's 0.15 mm that is under
  // a thread's width. At an underlay's 2 to 2.5 mm it is a stitch through the
  // hole, which is what an independent audit of the first build measured
  // (12 mm sewn 1.7 mm inside a cut-out). So `tol` is the caller's number,
  // not this pass's own pitch, and the row turns are asked too.
  //
  // The move is first cut where it crosses the boundary, exactly; only the
  // stretches that lie OUTSIDE are then sampled for depth, at tol/4, so
  // anything deeper than about 1.1 tol is seen and a slot narrower than 2 tol
  // is treated as closed. (It used to sample the whole move for inside and
  // outside as well: 1,600 point-in-polygon tests for one 60 mm run, and
  // nearly all of a hole-heavy design's time.) `slack` is ignored at either
  // end: a run of ANOTHER pass may begin a hair off the edge (digitize.js,
  // between runs).
  //
  // There is a third answer, and it matters for one kind of move only. A move
  // can run OUTSIDE the polygons without ever being deep: the turn from the
  // last row of a T's bar to the first of its stem runs the length of the
  // bar's underside, under a pitch out. Sewn, that is the fill's own edge.
  // FLOATED -- which is what the plain walk does with any turn longer than a
  // stitch -- it is a loose thread nothing will ever cover (28 mm of it on a
  // 35 mm T). So: INSIDE may be floated, ON_RIM must be sewn, OPEN must be cut.
  //
  // `wantRim`: only one caller needs INSIDE told from ON_RIM. Without it, a
  // sample is done as soon as ANY edge is within `tol`, and anything that is
  // not OPEN comes back INSIDE.
  const INSIDE = 0, ON_RIM = 1, OPEN = 2;
  function groundUnder(a, b, edges, tol, slack, wantRim) {
    const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy);
    const lo = slack || 0, hi = len - lo;
    if (!(hi > lo)) return INSIDE;
    const reach = Math.max(tol, ON_EDGE_EPS);
    const near = wantRim ? ON_EDGE_EPS : reach;   // close enough to stop looking
    // Where the LINE through a and b crosses the boundary, as a distance from
    // a. Half-open on which side of the line a corner is, so a corner lying
    // exactly on it counts once: the scanline rule, turned to this line.
    const cross = [];
    for (const [u, v] of edges) {
      const su = dx * (u.y - a.y) - dy * (u.x - a.x), sv = dx * (v.y - a.y) - dy * (v.x - a.x);
      if ((su > 0) === (sv > 0)) continue;
      const k = su / (su - sv);
      cross.push(((u.x + k * (v.x - u.x) - a.x) * dx + (u.y + k * (v.y - u.y) - a.y) * dy) / len);
    }
    cross.sort((p, q) => p - q);
    const stops = [lo];
    for (const c of cross) if (c > lo && c < hi) stops.push(c);
    stops.push(hi);
    let worst = INSIDE, behind = 0;
    let last = 0;   // the edge the last sample was nearest: the next one usually is too
    for (let i = 0; i + 1 < stops.length; i++) {
      const s0 = stops[i], s1 = stops[i + 1];
      while (behind < cross.length && cross[behind] <= (s0 + s1) / 2) behind++;
      // even-odd along the line: inside when an odd number of crossings lie ahead
      if ((cross.length - behind) % 2 === 1) continue;
      const n = Math.min(4000, Math.max(1, Math.ceil((s1 - s0) / (reach / 4))));
      for (let k = 0; k < n; k++) {
        const s = s0 + (s1 - s0) * (k + 0.5) / n;
        const p = { x: a.x + dx * s / len, y: a.y + dy * s / len };
        let d = distToSegment(p, edges[last][0], edges[last][1]);
        for (let e = 0; d > near && e < edges.length; e++) {
          const de = distToSegment(p, edges[e][0], edges[e][1]);
          if (de < d) { d = de; last = e; }
        }
        if (d > reach) return OPEN;
        if (wantRim && d > ON_EDGE_EPS) worst = ON_RIM;
      }
    }
    return worst;
  }

  // "Is it cut": with no slack both ends are on the boundary, and a move no
  // longer than 2 tol cannot be deeper than tol.
  function leavesShape(a, b, edges, tol, slack) {
    if (!slack && Math.hypot(b.x - a.x, b.y - a.y) <= 2 * tol) return false;
    return groundUnder(a, b, edges, tol, slack) === OPEN;
  }

  // The same question for digitize.js, which asks it of the move between two
  // RUNS of one shape. That move is a FLOAT whatever its length, so it gets
  // the float's answer: it must be cut when it goes deep into open ground, and
  // also when it is longer than `maxFloat` and leaves the polygons AT ALL --
  // a loose thread on the rim that nothing will cover. (Without `maxFloat`,
  // only the first.)
  function crossesOpenGround(a, b, polygons, tol, slack, maxFloat) {
    return openGroundTest(polygons)(a, b, tol, slack, maxFloat);
  }
  // The same, for a caller with many moves to ask about over one set of
  // polygons: the edge list is built once.
  function openGroundTest(polygons) {
    const edges = [];
    for (const poly of polygons) for (let i = 0; i < poly.length; i++) edges.push([poly[i], poly[(i + 1) % poly.length]]);
    return (a, b, tol, slack, maxFloat) => {
      if (!(maxFloat > 0) || Math.hypot(b.x - a.x, b.y - a.y) <= maxFloat) return leavesShape(a, b, edges, tol, slack);
      return groundUnder(a, b, edges, tol, slack, true) !== INSIDE;
    };
  }

  // Sew the columns from wherever the last one ended, entering each by one of
  // its four corners (top-down or bottom-up, first row either way).
  //
  // ORDER. A column waits until every column directly above it is sewn, so
  // the walk finishes a level before it descends. Without that the nearest
  // reachable column after the first strip beside a row of holes is the band
  // BELOW them, the other strips are stranded, and each costs a cut to get
  // back to: 3 for three holes in a row, 64 to 126 on a 36-hole badge. (Run
  // bottom-up -- see "where the walk starts" -- it is the columns BELOW.)
  //
  // THE MOVE to the next column, in order of preference:
  //   1. one stitch, inside the shape;
  //   2. a run ALONG THE ROW, inside the shape, however long -- from the foot
  //      of one strip to the foot of the next along the hole's own edge. It
  //      runs with the rows and on the rim, so it reads as the fill's edge;
  //   3. the way ROUND THE RING both ends sit on -- a hole's edge, or the
  //      outline -- corner to corner, within a budget. This is the move an
  //      underlay needs: its rows are 2 mm apart, so the run along the row
  //      would lie 2 mm inside the hole;
  //   4. a way through the columns' own corners, made of moves 1 to 3 and of
  //      runs along a column's side ("the last resort", below);
  //   5. otherwise the thread is CUT, and the nearest column taken. With 1 to
  //      4 that is two shapes that do not touch, or a way round that is over
  //      the budget.
  // A row turn inside a column is asked the same question: sewn, taken round
  // the ring, or cut. A cut point is where the frame goes, not a penetration,
  // so the same spot follows it as a plain point: the row starts on its own
  // start.
  //
  // WHICH END a column is entered by. Sewn down one strip beside a hole and up
  // the other, the walk ends at the TOP of the second with the band below
  // still to sew, and there is nothing for it but a cut: one per hole, which
  // is what the first rebuild cost wherever the holes did not line up with
  // the rows. So before a column is sewn the walk looks ONE move ahead: if
  // leaving from this column's far end would strand it, it first runs to the
  // other end -- along the column's own side, row end to row end -- and sews
  // back. That run is laid before the column and lies under the ends of the
  // column's own rows. It is the half of "travel under rows still to sew"
  // that needs no knowledge of anything but the column itself.
  const RING_TRIES = 8;   // how many of the nearest starts are tried round a ring
  const START_TRIES = 8;  // how many of the nearest corners a pass may start from
  function sewColumns(cols, above, geo, o) {
    const edges = geo.edges, maxStitch = o.maxStitch, tol = o.tol, pitch = o.pitch, cosP = o.cosP, sinP = o.sinP;
    const tooLong = (d) => !!(maxStitch && maxStitch > 0 && d > maxStitch);
    const dist = (a, b) => Math.hypot(b.x - a.x, b.y - a.y);
    // Variant j of a column: bit 1 = from the bottom, bit 0 = first row sewn
    // right to left. So j ^ 1 starts at the other end of the same row, and
    // j ^ 2 at the other end of the column on the same side.
    const walk = (col, fromBottom, firstReversed) => {
      const seq = fromBottom ? col.slice().reverse() : col;
      const key = [];
      seq.forEach((r, k) => {
        const rev = (k % 2 === 1) !== firstReversed;
        const lo = { x: r.x0, y: r.y, e: r.e0 }, hi = { x: r.x1, y: r.y, e: r.e1 };
        key.push(rev ? hi : lo, rev ? lo : hi);
      });
      return key;
    };
    const variants = cols.map((c) => [walk(c, false, false), walk(c, false, true), walk(c, true, false), walk(c, true, true)]);
    const remaining = cols.map((_, i) => i);   // creation order: highest first, then leftmost
    const out = [];
    const cutTo = (p) => {
      const frame = rotate(p, cosP, sinP);
      frame.travel = true;
      frame.trim = true;
      out.push(frame, rotate(p, cosP, sinP));
    };
    const sewTo = (a, b) => {
      const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy);
      if (tooLong(dist)) {
        const steps = Math.ceil(dist / maxStitch);
        for (let s = 1; s < steps; s++) out.push(rotate({ x: a.x + dx * s / steps, y: a.y + dy * s / steps }, cosP, sinP));
      }
      out.push(rotate(b, cosP, sinP));
    };
    const sewAlong = (from, pts) => {
      let p = from;
      for (const q of pts) { sewTo(p, q); p = q; }
    };

    // The way from a to b round the ring both sit on, the shorter way: the
    // ring's own corners, so that no corner is cut (stage6_fill `_ring_route`).
    // null when they are on different rings, or when it is over budget: the
    // larger of `o.budget` and four times the straight line, as the Python
    // engine's is. Its legs are not asked what ground they run over. Under
    // even-odd every edge of every ring has filled ground on exactly one
    // side, so a ring's edge IS the rim. (Asking anyway cost 60% of a
    // 36-hole design's time: a point on an edge reads as outside half the
    // time, and then every edge is measured to find the one it is on.)
    const arcs = {};
    const arcOf = (ri) => {
      if (!arcs[ri]) {
        const ring = geo.rings[ri], cum = [0];
        for (let k = 1; k <= ring.length; k++) cum.push(cum[k - 1] + dist(ring[k - 1], ring[k % ring.length]));
        arcs[ri] = { cum, total: cum[ring.length] };
      }
      return arcs[ri];
    };
    const ringRoute = (a, b) => {
      if (a.e == null || b.e == null || geo.ringOf[a.e] !== geo.ringOf[b.e]) return null;
      const ring = geo.rings[geo.ringOf[a.e]], n = ring.length, arc = arcOf(geo.ringOf[a.e]);
      const i = geo.posOf[a.e], j = geo.posOf[b.e];
      const wrap = (s) => ((s % arc.total) + arc.total) % arc.total;
      const sa = arc.cum[i] + dist(ring[i], a), sb = arc.cum[j] + dist(ring[j], b);
      const ahead = wrap(sb - sa) <= arc.total / 2;
      const span = ahead ? wrap(sb - sa) : wrap(sa - sb);
      if (span > Math.max(o.budget, 4 * dist(a, b))) return null;
      const pts = [];
      for (let k = 1; k <= n; k++) {
        // ahead: the corner at the END of a's edge first; back: at its start
        const v = ahead ? (i + k) % n : (((i - k + 1) % n) + n) % n;
        const off = ahead ? wrap(arc.cum[v] - sa) : wrap(sa - arc.cum[v]);
        if (off >= span - ON_EDGE_EPS) break;
        if (off > ON_EDGE_EPS) pts.push({ x: ring[v].x, y: ring[v].y });
      }
      pts.push(b);
      return { pts, len: span };
    };

    // The way from `cur` to the start of some column in `ready`: -> { ci, j,
    // how, route }, `route` ending on that start.
    const byDistance = (p, q) => p.d - q.d || p.ci - q.ci || p.j - q.j;
    const moveTo = (cur, ready) => {
      const all = [];
      for (const ci of ready) variants[ci].forEach((v, j) => all.push({ ci, j, d: Math.round(dist(cur, v[0]) * 1e6) / 1e6 }));
      all.sort(byDistance);
      const start = (c) => variants[c.ci][c.j][0];
      for (const how of ["stitch", "run"]) {
        for (const c of all) {
          const fits = how === "stitch" ? !tooLong(c.d) : (tooLong(c.d) && Math.abs(start(c).y - cur.y) <= pitch * 1.0001);
          if (fits && !leavesShape(cur, start(c), edges, tol)) return { ci: c.ci, j: c.j, how, route: [start(c)] };
        }
      }
      let best = null;
      for (const c of all.slice(0, RING_TRIES)) {
        const r = ringRoute(cur, start(c));
        if (r && (!best || r.len < best.len)) best = { ci: c.ci, j: c.j, how: "ring", route: r.pts, len: r.len };
      }
      return best || { ci: all[0].ci, j: all[0].j, how: "cut", route: [start(all[0])] };
    };

    // What leaving column `ci` at `exit` would cost the NEXT move: 0 a stitch
    // or a run (or nothing is left to sew), 1 the way round a ring, 2 a cut.
    // The move it found is kept: it is the very move the walk makes next.
    const done = cols.map(() => false);
    let waits = above;         // what each column waits for: see "where the walk starts"
    let planned = new Map();   // exit point -> the move from it
    const afterwards = (ci, exit) => {
      const rest = remaining.filter((c) => c !== ci);
      if (!rest.length) return 0;
      let ready = rest.filter((c) => waits[c].every((a) => done[a] || a === ci));
      if (!ready.length) ready = rest;
      const move = moveTo(exit, ready);
      planned.set(exit, move);
      return move.how === "cut" ? 2 : move.how === "ring" ? 1 : 0;
    };

    // The run along a column's own side from the start of variant j to the
    // start of variant j ^ 2: row end to row end, each leg one stitch at most
    // and within `tol` of every row end it passes, so it stays on the column's
    // edge. null when a leg would go deep into open ground.
    const sideRun = (ci, j) => {
      const seq = (j & 2) ? cols[ci].slice().reverse() : cols[ci];
      const side = seq.map((r) => ((j & 1) ? { x: r.x1, y: r.y, e: r.e1 } : { x: r.x0, y: r.y, e: r.e0 }));
      const hugs = (a, b) => {
        for (let m = a + 1; m < b; m++) if (distToSegment(side[m], side[a], side[b]) > tol) return false;
        return true;
      };
      const pts = [];
      let a = 0;
      while (a < side.length - 1) {
        let b = a + 1;
        while (b + 1 < side.length && !tooLong(dist(side[a], side[b + 1])) && hugs(a, b + 1)) b++;
        if (groundUnder(side[a], side[b], edges, tol) === OPEN) return null;
        pts.push(side[b]);
        a = b;
      }
      return pts;
    };
    // How the needle gets from the start of variant `from` to the start of
    // variant `to` of one column before any of it is sewn; null if it cannot.
    const preRun = (ci, from, to) => {
      if (from === to) return [];
      const acrossRow = [variants[ci][to][0]];          // the other end of a row: inside by construction
      if ((from ^ to) === 1) return acrossRow;
      const side = sideRun(ci, from);
      if (!side) return null;
      return (from ^ to) === 2 ? side : side.concat(acrossRow);
    };

    // THE LAST RESORT BEFORE A CUT. Looking one move ahead does not stop a
    // column being left behind and the walk ending far from it with nothing in
    // reach: a 36-hole badge sewn at 30 degrees still cost 8 cuts that way.
    // The columns tile the shape, so their corners are a map of it, joined by
    // moves the walk already allows: along a column's side (the rim), along its
    // first or last row, and from a corner to the next one on the same or the
    // neighbouring row (straight, or round the ring where straight is open
    // ground). The shortest way through that map, if it is within the budget,
    // is sewn instead of cutting. Corner c of a column is where its variant c
    // starts.
    let web = null;
    const cornerOf = (ci, c) => variants[ci][c][0];
    const lengthOf = (from, pts) => { let s = 0, p = from; for (const q of pts) { s += dist(p, q); p = q; } return s; };
    const buildWeb = () => {
      const adj = cols.map(() => [[], [], [], []]);
      const link = (ci, c, cj, d, there, back) => {
        adj[ci][c].push({ ci: cj, c: d, pts: there, len: lengthOf(cornerOf(ci, c), there) });
        adj[cj][d].push({ ci, c, pts: back, len: lengthOf(cornerOf(cj, d), back) });
      };
      const rowsAt = new Map();   // row index -> the corners on it, left to right
      cols.forEach((col, ci) => {
        const n = col.length;
        link(ci, 0, ci, 1, [cornerOf(ci, 1)], [cornerOf(ci, 0)]);
        link(ci, 2, ci, 3, [cornerOf(ci, 3)], [cornerOf(ci, 2)]);
        for (const s of [0, 1]) {
          const down = n > 1 ? sideRun(ci, s) : [], up = n > 1 ? sideRun(ci, s + 2) : [];
          if (down && up) link(ci, s, ci, s + 2, down, up);
        }
        for (const c of [0, 1, 2, 3]) {
          const ri = col[c < 2 ? 0 : n - 1].ri;
          if (!rowsAt.has(ri)) rowsAt.set(ri, []);
          rowsAt.get(ri).push({ ci, c, p: cornerOf(ci, c) });
        }
      });
      const join = (a, b) => {
        if (a.ci === b.ci) return;
        if (!leavesShape(a.p, b.p, edges, tol)) { link(a.ci, a.c, b.ci, b.c, [b.p], [a.p]); return; }
        const there = ringRoute(a.p, b.p), back = ringRoute(b.p, a.p);
        if (there && back) link(a.ci, a.c, b.ci, b.c, there.pts, back.pts);
      };
      for (const row of rowsAt.values()) row.sort((p, q) => p.p.x - q.p.x);
      for (const [ri, here] of rowsAt) {
        for (let k = 0; k + 1 < here.length; k++) join(here[k], here[k + 1]);
        const below = rowsAt.get(ri + 1) || [];
        for (const a of here) {
          // the nearest corner on the next row, either side
          let right = below.findIndex((b) => b.p.x >= a.p.x);
          if (right < 0) right = below.length;
          if (right < below.length) join(a, below[right]);
          if (right > 0) join(a, below[right - 1]);
        }
      }
      return adj;
    };
    const webRoute = (from, ready) => {
      if (!web) web = buildWeb();
      const here = cornerOf(from.ci, from.c);
      const allowed = (ci, c) => Math.max(o.budget, 4 * dist(here, cornerOf(ci, c)));
      let cap = 0;
      for (const ci of ready) for (const c of [0, 1, 2, 3]) cap = Math.max(cap, allowed(ci, c));
      const goal = new Set(ready), N = cols.length * 4;
      const best = new Array(N).fill(Infinity), via = new Array(N).fill(null), seen = new Array(N).fill(false);
      best[from.ci * 4 + from.c] = 0;
      for (;;) {
        let u = -1;
        for (let k = 0; k < N; k++) if (!seen[k] && best[k] <= cap && (u < 0 || best[k] < best[u])) u = k;
        if (u < 0) return null;
        const ci = u >> 2, c = u & 3;
        if (goal.has(ci)) {
          if (best[u] > allowed(ci, c)) return null;
          const route = [];
          for (let k = u; via[k]; k = via[k].from) route.unshift(...via[k].pts);
          return { ci, j: c, how: "web", route };
        }
        seen[u] = true;
        for (const e of web[ci][c]) {
          const v = e.ci * 4 + e.c;
          if (best[u] + e.len < best[v]) { best[v] = best[u] + e.len; via[v] = { from: u, pts: e.pts }; }
        }
      }
    };
    // which corner variant j ends on: the far end of the column, and the side
    // its last row finishes at
    const exitCorner = (ci, j) => {
      const lastReversed = ((cols[ci].length - 1) % 2 === 1) !== !!(j & 1);
      return ((j & 2) ? 0 : 2) + (lastReversed ? 0 : 1);
    };

    // WHERE THE WALK STARTS, and which way it runs. A pass begins with a float
    // from wherever the last one ended, and the caller cuts that float if it
    // crosses open ground. Told where the thread is (`o.from`) and which
    // floats are left uncut (`o.clear`), the walk starts at the nearest corner
    // the thread can float to -- and if that corner is at the bottom, it runs
    // bottom-up: a column then waits for the columns BELOW it. Told nothing, it
    // starts at the top left and runs top-down, as it always has.
    //
    // And when the thread can float to NO corner the walk could start from --
    // it is beside a hole in the middle of the shape, and both ends of the
    // walk are behind other holes -- it floats to the nearest corner of ANY
    // column it can reach, and from there the walk TRAVELS to its start like
    // any other move: round a ring, or along rims and rows. That travel is
    // laid before the pass, and lies under it.
    let first = null, cur = null, curNode = null;
    if (o.from) {
      const below = cols.map(() => []);
      above.forEach((ups, ci) => ups.forEach((u) => below[u].push(ci)));
      const cands = [];
      for (const deps of [above, below]) {
        let free = remaining.filter((ci) => !deps[ci].length);
        if (!free.length) free = remaining;
        for (const ci of free) for (const j of [0, 1, 2, 3]) cands.push({ deps, ci, j, d: dist(o.from, cornerOf(ci, j)) });
      }
      const nearer = (p, q) => p.d - q.d || (p.deps === above ? 0 : 1) - (q.deps === above ? 0 : 1) || p.ci - q.ci || p.j - q.j;
      cands.sort(nearer);
      const clear = (ci, j) => !o.clear || o.clear(o.from, cornerOf(ci, j));
      const hit = cands.slice(0, START_TRIES).find((c) => clear(c.ci, c.j));
      const at = hit || cands[0];
      waits = at.deps;
      const others = [0, 1, 2, 3].filter((j) => j !== at.j && (!hit || clear(at.ci, j)))
        .sort((p, q) => dist(o.from, cornerOf(at.ci, p)) - dist(o.from, cornerOf(at.ci, q)) || p - q);
      first = { ci: at.ci, order: [at.j].concat(others) };
      if (!hit) {
        const any = [];
        cols.forEach((_, ci) => [0, 1, 2, 3].forEach((j) => any.push({ ci, j, d: dist(o.from, cornerOf(ci, j)) })));
        const landing = any.sort((p, q) => p.d - q.d || p.ci - q.ci || p.j - q.j).slice(0, 2 * START_TRIES).find((c) => clear(c.ci, c.j));
        if (landing) {
          cur = cornerOf(landing.ci, landing.j);
          curNode = { ci: landing.ci, c: landing.j };
          out.push(rotate(cur, cosP, sinP));
          first = null;
        }
      }
    }

    while (remaining.length) {
      // every column it waits for is sewn (the first waits for none)
      let ready = remaining.filter((ci) => waits[ci].every((a) => done[a]));
      if (!ready.length) ready = remaining;
      const startAt = first ? first.ci : ready[0];
      let m = !cur ? { ci: startAt, j: first ? first.order[0] : 0, how: "start", route: [] }
        : (planned.get(cur) || moveTo(cur, ready));
      if (m.how === "cut") m = webRoute(curNode, ready) || m;
      planned = new Map();
      const exitOf = (j) => variants[m.ci][j][variants[m.ci][j].length - 1];
      // Which corner to sew from. Arriving by a cut (or first of all) any of
      // the four is free -- first of all, any the thread can float to; arriving
      // by thread, the other three cost a run laid under the column's own
      // rows. Taken in that order of cost, the first that leaves the walk best
      // placed for the move after this column.
      const landed = m.how === "cut" || m.how === "start";
      const order = (m.how === "start" && first) ? first.order
        : landed ? [0, 1, 2, 3].sort((p, q) => (cur ? dist(cur, variants[m.ci][p][0]) - dist(cur, variants[m.ci][q][0]) : 0) || p - q)
        : [m.j, m.j ^ 1, m.j ^ 2, m.j ^ 3];
      let pick = null;
      for (const j of order) {
        const cost = afterwards(m.ci, exitOf(j));
        if (pick && cost >= pick.cost) continue;
        const pre = landed ? [] : preRun(m.ci, m.j, j);
        if (pre) pick = { j, cost, pre };
        if (pick && pick.cost === 0) break;
      }
      const key = variants[m.ci][pick.j];
      remaining.splice(remaining.indexOf(m.ci), 1);
      done[m.ci] = true;
      if (landed) {
        if (m.how === "cut") cutTo(key[0]); else out.push(rotate(key[0], cosP, sinP));
      } else {
        sewAlong(cur, m.route);
        sewAlong(variants[m.ci][m.j][0], pick.pre);
      }
      for (let i = 1; i < key.length; i++) {
        // odd i runs along a row, inside by construction; even i is the turn
        // to this column's next row.
        if (i % 2 === 0 && leavesShape(key[i - 1], key[i], edges, tol)) {
          const round = ringRoute(key[i - 1], key[i]);
          if (round) sewAlong(key[i - 1], round.pts); else cutTo(key[i]);
        } else sewTo(key[i - 1], key[i]);
      }
      cur = key[key.length - 1];
      curNode = { ci: m.ci, c: exitCorner(m.ci, pick.j) };
    }
    return out;
  }

  // Tatami scan-line fill across one or more polygons.
  // polygons: Array<Array<{x,y}>>; even-odd parity across ALL polygons (holes respected).
  // opts: { rowSpacing, angleDeg=0, maxStitch }
  //   `columns` (default off): a shape whose rows fork (a hole, a notch), or
  //   whose row turns go deep into open ground (the step of a T under rows
  //   2 mm apart), is sewn column by column, see above. A plain shape keeps the
  //   walk below, `centerOut` included; the one thing that changes in it is a
  //   turn longer than a stitch that runs outside the shape, which is sewn
  //   along the rim instead of floated.
  //   `openTol` (with `columns`): how deep into unfilled ground a move may lay
  //   thread, in the polygons' units. Defaults to this pass's own row pitch,
  //   which a FILL's row turns never exceed; an underlay pass, with rows 2 mm
  //   apart, must be given the fill's.
  function tatamiFill(polygons, opts) {
    const rowSpacing = opts.rowSpacing;
    const angleDeg = opts.angleDeg || 0;
    const maxStitch = opts.maxStitch;
    const theta = (angleDeg * Math.PI) / 180;

    // Rotate all points by -angleDeg about the origin so scanlines are horizontal.
    const cosN = Math.cos(-theta);
    const sinN = Math.sin(-theta);
    // Rotate back by +angleDeg.
    const cosP = Math.cos(theta);
    const sinP = Math.sin(theta);

    // Collect rotated edges and compute bbox. For opts.columns: which ring
    // each edge belongs to and where in it, so a move can go round a ring.
    const edges = [];
    const rings = [], ringOf = [], posOf = [];
    let minY = Infinity;
    let maxY = -Infinity;
    for (const poly of polygons) {
      const n = poly.length;
      if (n < 2) continue;
      const rp = poly.map((p) => rotate(p, cosN, sinN));
      for (const p of rp) {
        if (p.y < minY) minY = p.y;
        if (p.y > maxY) maxY = p.y;
      }
      for (let i = 0; i < n; i++) {
        const a = rp[i];
        const b = rp[(i + 1) % n];
        edges.push([a, b]);
        ringOf.push(rings.length);
        posOf.push(i);
      }
      rings.push(rp);
    }

    if (!isFinite(minY) || !isFinite(maxY)) return [];

    // Collect ordered span endpoints (in rotated space) following the
    // boustrophedon path across all rows. Points are grouped per emitted row so
    // that opts.centerOut can reorder whole rows (each row keeps its own
    // boustrophedon scan direction, which is keyed to its spatial rowIndex).
    const rowGroups = [];
    const rowSpans = [];   // the same rows as bare spans, for opts.columns
    let rowIndex = 0;
    for (let y = minY; y <= maxY + EPS; y += rowSpacing) {
      // Gather x-intersections with all edges using the half-open rule, each
      // with the edge it is on (`e`, for opts.columns).
      const xs = [];
      for (let e = 0; e < edges.length; e++) {
        const a = edges[e][0], b = edges[e][1];
        const y0 = a.y;
        const y1 = b.y;
        if (y0 === y1) continue; // horizontal edge: skip (parity preserved)
        // Half-open: count edge if min(y0,y1) <= y < max(y0,y1).
        const lo = Math.min(y0, y1);
        const hi = Math.max(y0, y1);
        if (y >= lo && y < hi) {
          const t = (y - y0) / (y1 - y0);
          xs.push({ x: a.x + t * (b.x - a.x), e });
        }
      }
      if (xs.length >= 2) {
        xs.sort((p, q) => p.x - q.x);
        // Pair spans (even-odd).
        const spans = [], spanEdges = [];
        for (let i = 0; i + 1 < xs.length; i += 2) {
          spans.push([xs[i].x, xs[i + 1].x]);
          spanEdges.push([xs[i].e, xs[i + 1].e]);
        }
        // Boustrophedon: reverse span order and endpoints on odd rows.
        const rev = rowIndex % 2 === 1;
        const ordered = rev ? spans.slice().reverse() : spans;
        const grp = [];
        for (const span of ordered) {
          const start = rev ? span[1] : span[0];
          const end = rev ? span[0] : span[1];
          grp.push({ x: start, y });
          grp.push({ x: end, y });
        }
        rowGroups.push(grp);
        rowSpans.push({ ri: rowIndex, y, spans, spanEdges });
      }
      rowIndex++;
    }

    // Row emission order. Default (sequential) flattens groups top-to-bottom —
    // byte-identical to before. With opts.centerOut, emit rows in TWO sweeps that
    // each run from the center OUTWARD over ADJACENT rows, so fabric push still
    // radiates symmetrically from the center but connectors stay small.
    //
    //   Upper sweep: mid, mid-1, …, 0    (adjacent each step)
    //   Lower sweep: mid+1, mid+2, …, last (adjacent each step)
    //
    // Each row's boustrophedon scan direction is keyed to its ABSOLUTE spatial
    // rowIndex (set above), so adjacent rows always have opposite scan parity:
    // one ends where the next begins → the inter-row connector is short, exactly
    // like normal boustrophedon. The ONLY long reposition is the single
    // sweep-to-sweep move (top edge → back near center). This replaces the old
    // interleaved order [mid, mid-1, mid+1, mid-2, …], whose non-adjacent, same-
    // parity hops (e.g. mid-1 → mid+1) were nearly all full-width travel jumps.
    //
    // Each group has an even length (span start/end pairs), so concatenation
    // preserves the connector-marking parity below and every inter-row move lands
    // on an even (connector) index.
    let orderedGroups = rowGroups;
    // Index (into `key`) of the FIRST point of the lower sweep — the destination
    // of the single sweep-to-sweep reposition (top edge → back near center).
    // That one long move is a needle-up float; tag its destination point with
    // trim:true so the encoder cuts the thread there instead of leaving a bare
    // jump. -1 when there is no lower sweep (≤1 row group, or n where the lower
    // sweep is empty), so no trim is emitted for tiny fills.
    let lowerSweepStartIdx = -1;
    if (opts.centerOut && rowGroups.length > 1) {
      const n = rowGroups.length;
      const mid = Math.floor(n / 2);
      orderedGroups = [];
      for (let i = mid; i >= 0; i--) orderedGroups.push(rowGroups[i]); // upper sweep
      if (mid + 1 < n) {
        // count upper-sweep points; that offset is where the lower sweep begins.
        let upperCount = 0;
        for (let i = mid; i >= 0; i--) upperCount += rowGroups[i].length;
        lowerSweepStartIdx = upperCount;
      }
      for (let i = mid + 1; i < n; i++) orderedGroups.push(rowGroups[i]); // lower sweep
    }
    const key = [];
    for (const grp of orderedGroups) for (const p of grp) key.push(p);

    // With `columns`, a shape is PLAIN -- and keeps the walk it has always
    // had, center-out included -- only when every row is a single span AND no
    // turn from one row to the next goes deep into open ground. Anything else
    // is sewn column by column. Three things that test is not:
    //  - the column count. At a pointed corner two consecutive single-span
    //    rows can fail to overlap, which `cutColumns` rightly calls a break,
    //    and that is not a reason to change a plain rotated rectangle.
    //  - "some row forks". No row of a T or an L is split, and the old walk's
    //    turn from the bar's last row to the stem's first is still a float
    //    outside the outline (found by audit: 22 mm, 2 mm out).
    //  - the turns of the rows taken top-down. Center-out sews its upper half
    //    from the middle UP, and those turns are the other diagonal of each
    //    pair of rows. The ones asked about are the ones in `key`, all but
    //    the center-out reposition, which is cut whatever it crosses.
    // A plain shape changes in one way: a turn longer than a stitch that runs
    // outside the shape is sewn along the rim, where the walk below floats it.
    let rimTurn = null;
    if (opts.columns) {
      const tol = opts.openTol > 0 ? opts.openTol : rowSpacing;
      const floated = (d) => !!(maxStitch && maxStitch > 0 && d > maxStitch);
      let plain = rowSpans.every((r) => r.spans.length === 1);
      rimTurn = {};
      for (let i = 2; plain && i < key.length; i += 2) {
        if (i === lowerSweepStartIdx) continue;
        const d = Math.hypot(key[i].x - key[i - 1].x, key[i].y - key[i - 1].y);
        if (d <= 2 * tol && !floated(d)) continue;   // cannot be deep, and is sewn anyway
        const ground = groundUnder(key[i - 1], key[i], edges, tol, 0, true);
        if (ground === OPEN) plain = false;
        else if (ground === ON_RIM && floated(d)) rimTurn[i] = true;
      }
      if (!plain) {
        const cut = cutColumns(rowSpans);
        const budget = opts.travelBudget > 0 ? opts.travelBudget : (maxStitch > 0 ? 5 * maxStitch : Infinity);
        // the walk works in the rotated frame; the caller's `clear` does not
        const from = opts.from ? rotate(opts.from, cosN, sinN) : null;
        const clear = opts.clear ? ((a, b) => opts.clear(rotate(a, cosP, sinP), rotate(b, cosP, sinP))) : null;
        return sewColumns(cut.columns, cut.above, { edges, rings, ringOf, posOf },
          { maxStitch, tol, pitch: rowSpacing, cosP, sinP, budget, from, clear });
      }
    }

    // Densify: ensure no two consecutive points exceed maxStitch (this also
    // splits the inter-row travel stitches). Then rotate back by +angleDeg.
    //
    // With opts.markConnectors: key indices alternate span-start/span-end, so
    // the move INTO key[i] for even i (i>0) is a connector (span-to-span
    // travel), which may legally cross a hole. Long connectors are then
    // emitted as a single point tagged {travel:true} — needle-up move, not
    // sewn — instead of being densified into fake stitches across the gap.
    const markConnectors = !!opts.markConnectors;
    const out = [];
    if (key.length === 0) return out;
    out.push(rotate(key[0], cosP, sinP));
    for (let i = 1; i < key.length; i++) {
      const a = key[i - 1];
      const b = key[i];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.hypot(dx, dy);
      const isConnector = i % 2 === 0;
      const isSweepBoundary = i === lowerSweepStartIdx;
      if (markConnectors && isConnector && maxStitch && dist > maxStitch && !(rimTurn && rimTurn[i])) {
        const p = rotate(b, cosP, sinP);
        p.travel = true;
        if (isSweepBoundary) p.trim = true; // cut the sweep-to-sweep float
        out.push(p);
        continue;
      }
      if (maxStitch && maxStitch > 0 && dist > maxStitch) {
        const steps = Math.ceil(dist / maxStitch);
        for (let s = 1; s < steps; s++) {
          const t = s / steps;
          out.push(rotate({ x: a.x + dx * t, y: a.y + dy * t }, cosP, sinP));
        }
      }
      const pb = rotate(b, cosP, sinP);
      if (isSweepBoundary) pb.trim = true; // cut the sweep-to-sweep float
      out.push(pb);
    }
    return out;
  }

  // Walk the polygon perimeter emitting a point every stitchLen of arc length.
  function runningOutline(polygon, opts) {
    const stitchLen = opts.stitchLen;
    const out = [];
    const n = polygon.length;
    if (n === 0) return out;
    if (n === 1) return [{ x: polygon[0].x, y: polygon[0].y }];

    out.push({ x: polygon[0].x, y: polygon[0].y });
    let carry = 0; // distance accumulated since last emitted point

    for (let i = 0; i < n; i++) {
      const a = polygon[i];
      const b = polygon[(i + 1) % n]; // closed loop back to start
      const segDx = b.x - a.x;
      const segDy = b.y - a.y;
      const segLen = Math.hypot(segDx, segDy);
      if (segLen <= EPS) continue;
      const ux = segDx / segLen;
      const uy = segDy / segLen;
      // Position along this segment (from a) of the next point to emit.
      let dist = stitchLen - carry;
      while (dist <= segLen + EPS) {
        const d = Math.min(dist, segLen);
        out.push({ x: a.x + ux * d, y: a.y + uy * d });
        dist += stitchLen;
      }
      carry = segLen - (dist - stitchLen);
    }
    return out;
  }

  return {
    tatamiFill,
    runningOutline,
    pcaAngleDeg,
    crossesOpenGround,
    openGroundTest,
  };
});
