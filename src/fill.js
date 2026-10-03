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

  // The rows the columns are cut from: the scanlines' own, without the spans
  // that have NO LENGTH.
  //
  // A scanline that runs exactly through a corner pointing up the rows finds
  // both of that corner's edges (the half-open rule) and pairs them. The first
  // scanline sits on the topmost point, so any shape whose top is a single
  // corner has such a span; so does a drawing on whole numbers, wherever a
  // corner lands on a row. The plain walk sews it on its way past, two
  // penetrations in one hole, and always has. As a COLUMN it is joined to
  // nothing (`overlaps`), so the walk travelled to it like any other, and cut
  // to it when it was left for last with no way round: a cut, two penetrations
  // in one hole, and the end of the pass. 18 such threads in a 12,880-design
  // sweep (the audit of the lock stitches, 2026-10-03).
  //
  // It sews no thread and joins no two columns, so it is left out, and a
  // scanline with nothing else on it is absent like an empty one. (The Python
  // engine's `_row_spans` does the same: `g.length <= 0`.) "No length" is
  // `overlaps`' own measure: a span no longer than that can be the neighbour
  // of nothing, and the corner's two edges do not always meet to the last bit.
  //
  // Not this: two spans that TOUCH (a scanline exactly along the wall of a
  // hole, through a corner of one, or across a slit). Each has a length and
  // is a column. It is the move from one to the other that has none, and
  // that is `sewTo`'s.
  function spansWithLength(rows) {
    const out = [];
    for (const row of rows) {
      const keep = [];
      row.spans.forEach((sp, si) => { if (sp[1] - sp[0] > COLUMN_OVERLAP_EPS) keep.push(si); });
      if (keep.length === row.spans.length) out.push(row);
      else if (keep.length) out.push({ ri: row.ri, y: row.y, spans: keep.map((si) => row.spans[si]), spanEdges: row.spanEdges && keep.map((si) => row.spanEdges[si]) });
    }
    return out;
  }

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

  // A column is rows that FOLLOW one another, which is not the same as rows
  // the thread can get between. Where the turn from one row to the next goes
  // deep into open ground -- a lattice at 45 degrees, round the corner of a
  // square hole -- the column is cut in two there, and getting from one piece
  // to the other becomes the walk's business like any other move. Left whole,
  // that turn could only be cut: its two ends sit on different rings.
  // (A fill's own turns are one pitch long and never deep, so only passes with
  // rows far apart are split.) Changes `cut` in place.
  function splitAtOpenTurns(cut, edges, tol) {
    const { columns, above } = cut;
    const whole = columns.length;
    for (let ci = 0; ci < whole; ci++) {
      const col = columns[ci], at = [];
      for (let k = 0; k + 1 < col.length; k++) {
        const a = col[k], b = col[k + 1];
        if (leavesShape({ x: a.x0, y: a.y }, { x: b.x0, y: b.y }, edges, tol) ||
            leavesShape({ x: a.x1, y: a.y }, { x: b.x1, y: b.y }, edges, tol)) at.push(k + 1);
      }
      if (!at.length) continue;
      const before = columns.length;
      let last = ci;
      at.push(col.length);
      for (let s = 0; s + 1 < at.length; s++) {
        columns.push(col.slice(at[s], at[s + 1]));
        above.push([last]);
        last = columns.length - 1;
      }
      columns[ci] = col.slice(0, at[0]);
      // whatever hung below the column now hangs below its last piece
      for (let j = 0; j < before; j++) {
        if (above[j].indexOf(ci) >= 0) above[j] = above[j].map((u) => (u === ci ? last : u));
      }
    }
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
  // is treated as closed. (At most 4,000 samples to a stretch: one outside for
  // more than 1,000 tol -- 150 mm at a fill's tolerance -- is sampled more
  // coarsely than that.) (It used to sample the whole move for inside and
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
    const enough = wantRim ? ON_EDGE_EPS : reach;   // close enough to stop looking
    const near = nearEdges(edges);
    // Where the ground under the move can CHANGE, as a distance from a: where
    // it crosses an edge, and at every corner that lies ON its line, whichever
    // side that corner's edges go off to. (The scanline's half-open rule was
    // here first: a corner on the line belongs to the side its edge leaves by.
    // That counts crossings and does not find them. Along the tops of a U's
    // two arms, right to left, both walls of the mouth leave by the far side,
    // neither was a crossing, and the mouth read as filled ground; the same
    // two points left to right read as open. Third audit.)
    const stops = [lo], onLine = ON_EDGE_EPS * len;
    const stopAt = (p) => {
      const t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / len;
      if (t > lo && t < hi) stops.push(t);
    };
    near(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.max(a.x, b.x), Math.max(a.y, b.y), (e) => {
      const u = edges[e][0], v = edges[e][1];
      const su = dx * (u.y - a.y) - dy * (u.x - a.x), sv = dx * (v.y - a.y) - dy * (v.x - a.x);
      // (v is the next edge's u, so every corner of a ring is asked once)
      if (Math.abs(su) <= onLine) stopAt(u);
      else if ((su > 0) !== (sv > 0)) {
        const k = su / (su - sv);
        stopAt({ x: u.x + k * (v.x - u.x), y: u.y + k * (v.y - u.y) });
      }
      return false;
    });
    stops.push(hi);
    stops.sort((p, q) => p - q);
    const filled = (p) => {   // even-odd, by a ray to the right
      let c = false;
      near(p.x, p.y, Infinity, p.y, (e) => {
        const u = edges[e][0], v = edges[e][1];
        if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c;
        return false;
      });
      return c;
    };
    const at = (s) => ({ x: a.x + dx * s / len, y: a.y + dy * s / len });
    let worst = INSIDE;
    for (let i = 0; i + 1 < stops.length; i++) {
      const s0 = stops[i], s1 = stops[i + 1];
      if (!(s1 > s0) || filled(at((s0 + s1) / 2))) continue;
      const n = Math.min(4000, Math.max(1, Math.ceil((s1 - s0) / (reach / 4))));
      for (let k = 0; k < n; k++) {
        const p = at(s0 + (s1 - s0) * (k + 0.5) / n);
        let d = Infinity;
        near(p.x - reach, p.y - reach, p.x + reach, p.y + reach, (e) => {
          const de = distToSegment(p, edges[e][0], edges[e][1]);
          if (de < d) d = de;
          return d <= enough;
        });
        if (d > reach) return OPEN;
        if (wantRim && d > ON_EDGE_EPS) worst = ON_RIM;
      }
    }
    return worst;
  }

  // The edges near a box, without looking at all of them: -> near(x0, y0, x1,
  // y1, fn), which calls fn(edge index) once for every edge that could touch
  // the box, until fn returns true. A grid, built once for an edge list and
  // kept on it; a short list is simply scanned. Every move the walk considers
  // is asked what ground it runs over, and with 2,000 holes that is 8,000
  // edges looked at per move, which took a 100 mm design to 94 seconds.
  const GRID_MIN_EDGES = 64, GRID_MAX_SIDE = 160;
  function nearEdges(edges) {
    if (edges._near) return edges._near;
    let near = (x0, y0, x1, y1, fn) => { for (let e = 0; e < edges.length; e++) if (fn(e)) return; };
    if (edges.length >= GRID_MIN_EDGES) {
      let gx0 = Infinity, gy0 = Infinity, gx1 = -Infinity, gy1 = -Infinity;
      for (const [u, v] of edges) {
        gx0 = Math.min(gx0, u.x, v.x); gx1 = Math.max(gx1, u.x, v.x);
        gy0 = Math.min(gy0, u.y, v.y); gy1 = Math.max(gy1, u.y, v.y);
      }
      const side = Math.min(GRID_MAX_SIDE, Math.ceil(Math.sqrt(edges.length)));
      const w = Math.max(gx1 - gx0, 1e-9) / side, h = Math.max(gy1 - gy0, 1e-9) / side;
      const col = (x) => Math.max(0, Math.min(side - 1, Math.floor((x - gx0) / w)));
      const row = (y) => Math.max(0, Math.min(side - 1, Math.floor((y - gy0) / h)));
      const cells = new Array(side * side);
      edges.forEach((uv, e) => {
        const c0 = col(Math.min(uv[0].x, uv[1].x)), c1 = col(Math.max(uv[0].x, uv[1].x));
        const r0 = row(Math.min(uv[0].y, uv[1].y)), r1 = row(Math.max(uv[0].y, uv[1].y));
        for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) (cells[r * side + c] || (cells[r * side + c] = [])).push(e);
      });
      // An edge is in every cell it crosses, so it is marked with the query it
      // was last seen by. (`pass` would outrun what the array holds after 2^31
      // queries of ONE edge list. A list lives for one pass of one shape: that
      // many queries is minutes of nothing else, and the slowest shape
      // measured builds in three seconds.)
      const seen = new Int32Array(edges.length);
      let pass = 0;
      near = (x0, y0, x1, y1, fn) => {
        pass++;
        const c0 = col(x0), c1 = col(x1), r0 = row(y0), r1 = row(y1);
        for (let r = r0; r <= r1; r++) {
          for (let c = c0; c <= c1; c++) {
            const cell = cells[r * side + c];
            if (!cell) continue;
            for (const e of cell) {
              if (seen[e] === pass) continue;
              seen[e] = pass;
              if (fn(e)) return;
            }
          }
        }
      };
    }
    Object.defineProperty(edges, "_near", { value: near });
    return near;
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
  // A row turn INSIDE a column is never one of these: a column whose turn
  // would go deep is cut in two there first (splitAtOpenTurns), so that every
  // hard move is a move between columns. A cut point is where the frame goes,
  // not a penetration, so the same spot follows it as a plain point: the row
  // starts on its own start.
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
    if (!cols.length) return [];   // every span of the pass was a point (spansWithLength)
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
    // A move of NO LENGTH lays no stitch: the needle is already there. Two
    // spans of one scanline can meet at a point -- the scanline runs along a
    // wall of a hole or a notch that a quarter turn left a hair off level, or
    // through a corner of one, or across a notch the pull compensation has
    // closed to a slit -- and the move from the end of one column to the
    // start of the other is then to the point the walk is on. So is the first
    // move of a pass that landed on a corner of the very column it begins
    // with, and so can be one leg of a way through the columns' corners
    // (webRoute). Each was a second penetration of one hole: 159 on 8,255
    // designs, and along a slit one to every row that crosses it. "The same
    // point" is to within ON_EDGE_EPS, as it is round a ring: in 73 of those
    // 159 the two corners differed in their last bits. (A row is never that
    // short: spansWithLength. And `cutTo` puts a plain point on its own frame
    // move on purpose; it does not come this way.)
    const sewTo = (a, b) => {
      const dx = b.x - a.x, dy = b.y - a.y, dist = Math.hypot(dx, dy);
      if (dist <= ON_EDGE_EPS) return;
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
    // A row of the fill, end to end. With `o.rowHoles` the holes between its
    // ends are the caller's (the row stagger); without, it is cut like any move.
    const sewRow = (a, b) => {
      if (!o.rowHoles) return sewTo(a, b);
      for (const h of o.rowHoles(a, b)) out.push(rotate(h, cosP, sinP));
      out.push(rotate(b, cosP, sinP));
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
    //
    // NOT every vertex, though. A traced curve has one every few tenths of a
    // millimetre, and a penetration on each is a stitch that short: 2,561 of
    // them under 0.3 mm in the underlay of one 60 mm shape traced with 3,000
    // points. A vertex is kept only where skipping it would take the thread
    // more than `tol` off the ring -- so a real corner always is. (The Python
    // engine met the same thing; it floors the spacing.)
    const thinned = (from, pts) => {
      const seq = [from].concat(pts), kept = [];
      const hugs = (i, j) => {
        for (let m = i + 1; m < j; m++) if (distToSegment(seq[m], seq[i], seq[j]) > tol) return false;
        return true;
      };
      let i = 0;
      while (i < seq.length - 1) {
        let j = i + 1;
        while (j + 1 < seq.length && hugs(i, j + 1)) j++;
        kept.push(seq[j]);
        i = j;
      }
      return kept;
    };
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
      return { pts: thinned(a, pts), len: span };
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
        // Nearest first, so once a run along a row has met open ground, every
        // start further along that same row, that same way, lies behind it:
        // not asked. (Asking them all was 83% of a 196-hole design's time.)
        const shut = {};
        for (const c of all) {
          const to = start(c);
          const fits = how === "stitch" ? !tooLong(c.d) : (tooLong(c.d) && Math.abs(to.y - cur.y) <= pitch * 1.0001);
          if (!fits) continue;
          const lane = how === "run" ? (to.x < cur.x ? "L" : "R") + Math.round(to.y / pitch * 1e3) : null;
          if (lane && shut[lane]) continue;
          if (!leavesShape(cur, to, edges, tol)) return { ci: c.ci, j: c.j, how, route: [to] };
          if (lane) shut[lane] = true;
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
    // edge. From one row end to the NEXT is never deep: a column whose turn is
    // has been cut in two there (splitAtOpenTurns). A leg past SEVERAL rows
    // can be -- the edge may turn a corner between two rows, and the leg
    // strays from the row ends besides -- so a leg stops growing where it
    // would go deep. (Found by fuzzing, after this check had been taken out
    // as unreachable: 1.4 deep on a tolerance of 1.)
    const sideRun = (ci, j) => {
      const seq = (j & 2) ? cols[ci].slice().reverse() : cols[ci];
      const side = seq.map((r) => ((j & 1) ? { x: r.x1, y: r.y, e: r.e1 } : { x: r.x0, y: r.y, e: r.e0 }));
      const hugs = (a, b) => {
        for (let m = a + 1; m < b; m++) if (distToSegment(side[m], side[a], side[b]) > tol) return false;
        return groundUnder(side[a], side[b], edges, tol) !== OPEN;
      };
      const pts = [];
      let a = 0;
      while (a < side.length - 1) {
        let b = a + 1;
        while (b + 1 < side.length && !tooLong(dist(side[a], side[b + 1])) && hugs(a, b + 1)) b++;
        pts.push(side[b]);
        a = b;
      }
      return pts;
    };
    // How the needle gets from the start of variant `from` to the start of
    // variant `to` of one column before any of it is sewn.
    const preRun = (ci, from, to) => {
      if (from === to) return [];
      const acrossRow = [variants[ci][to][0]];          // the other end of a row: inside by construction
      if ((from ^ to) === 1) return acrossRow;
      const side = sideRun(ci, from);
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
        for (const s of [0, 1]) link(ci, s, ci, s + 2, n > 1 ? sideRun(ci, s) : [], n > 1 ? sideRun(ci, s + 2) : []);
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
      // The nearest corner not yet settled comes off a heap of [distance,
      // corner]; of two equally near, the lower-numbered. That is the corner a
      // scan of all of them for the minimum picks, which is what this was, and
      // was 90% of the 14 seconds a 2,025-hole grid took with its rows at 30
      // degrees. An entry whose distance has since been bettered is stale.
      const heap = [[0, from.ci * 4 + from.c]];
      const before = (p, q) => p[0] < q[0] || (p[0] === q[0] && p[1] < q[1]);
      const push = (item) => {
        let i = heap.length;
        heap.push(item);
        while (i > 0) {
          const up = (i - 1) >> 1;
          if (!before(heap[i], heap[up])) break;
          [heap[i], heap[up]] = [heap[up], heap[i]];
          i = up;
        }
      };
      const pop = () => {
        const top = heap[0], last = heap.pop();
        if (heap.length) {
          heap[0] = last;
          for (let i = 0; ;) {
            const l = 2 * i + 1, r = l + 1;
            let m = i;
            if (l < heap.length && before(heap[l], heap[m])) m = l;
            if (r < heap.length && before(heap[r], heap[m])) m = r;
            if (m === i) break;
            [heap[i], heap[m]] = [heap[m], heap[i]];
            i = m;
          }
        }
        return top;
      };
      for (;;) {
        let u = -1;
        while (heap.length && u < 0) {
          const [d, k] = pop();
          if (!seen[k] && d === best[k]) u = k;
        }
        if (u < 0 || best[u] > cap) return null;
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
          if (best[u] + e.len < best[v]) { best[v] = best[u] + e.len; via[v] = { from: u, pts: e.pts }; push([best[v], v]); }
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
    //
    // Only the nearest are asked: START_TRIES starts, then twice that many
    // corners of any column. A corner the thread could float to further off
    // than those is not looked for, and the caller cuts (third audit: on a
    // thin eight-pointed star the one such corner was the farthest of 64).
    let first = null, cur = null, curNode = null, unlanded = null;
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
          unlanded = first;
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
      // Landed, and the only way on is a cut: the landing was one stray
      // penetration. The pass starts where that cut was going instead, so it
      // is the same walk without the stitch, and the cut is the caller's, on
      // the float in. (Not at the walk's own nearest start: that is another
      // walk, and it cost a cut more on 4 of the 12 passes this fired on.)
      if (m.how === "cut" && unlanded) {
        out.length = 0;
        m = { ci: m.ci, j: m.j, how: "start", route: [] };
      }
      unlanded = null;
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
        pick = { j, cost, pre: landed ? [] : preRun(m.ci, m.j, j) };
        if (cost === 0) break;
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
      // Odd i runs along a row, inside by construction. Even i is the turn to
      // this column's next row, and never deep: a column is cut in two where
      // it would be (splitAtOpenTurns).
      for (let i = 1; i < key.length; i++) (i % 2 ? sewRow : sewTo)(key[i - 1], key[i]);
      cur = key[key.length - 1];
      curNode = { ci: m.ci, c: exitCorner(m.ci, pick.j) };
    }
    return out;
  }

  // ROW STAGGER (`opts.stagger`, default off).
  //
  // Cut evenly from its own end, every row of a shape with straight sides puts
  // its needle holes straight under the holes of the row before, and light
  // runs down the line they make: the mark of a naive scanline fill
  // (stage6_fill's docstring; quality review 2026-09-08, section 4). With
  // `stagger` the holes BETWEEN a row's two ends sit on one grid for the whole
  // fill instead, a stitch apart, shifted row by row through a cycle of
  // `stagger` rows. A port of `_stagger_slots` and `_row_points_at_phase`, and
  // of the `split_long_moves` the Python fill then runs over its rows.
  //
  // Which slot each row of the cycle takes: the row's number with its bits
  // reversed, ranked (a van der Corput order). 4 -> [0, 2, 1, 3]. Not 0, 1, 2,
  // 3: a shift that walks one notch a row lines the holes up along a diagonal,
  // and the channel is still there, tilted.
  function staggerSlots(n) {
    n = Math.max(1, Math.floor(n) || 1);
    if (n === 1) return [0];
    const bits = Math.max(1, 32 - Math.clz32(n - 1));
    const rev = (i) => {
      let r = 0;
      for (let b = 0; b < bits; b++) if (i & (1 << b)) r |= 1 << (bits - 1 - b);
      return r;
    };
    const slots = new Array(n);
    Array.from({ length: n }, (_, i) => i).sort((p, q) => rev(p) - rev(q) || p - q)
      .forEach((row, slot) => { slots[row] = slot; });
    return slots;
  }

  // The holes between the two ends of one row, a -> b, in the rows' frame.
  // `phase` is the row's shift along the grid, `stitch` the grid's pitch, and
  // `minStitch` how near an end a grid point may be and still be sewn.
  //  - The two ends stay where they are, on the outline. That is the edge.
  //  - A grid point is kept only when it is a real stitch from BOTH ends. The
  //    grid is the fill's and not the row's, so the first point inside a row
  //    is any fraction of a stitch past the edge, and kept it would put the
  //    needle down beside the hole it has just made.
  //  - Skipping one can leave a step longer than a stitch. That step is cut
  //    into equal parts, as every move longer than a stitch is: counted from
  //    the end the thread comes from, which on a row sewn right to left is the
  //    high end (`split_long_moves` cuts a path, not an interval, and the two
  //    ends do not always give the same double).
  //  - A row with no room for a point that clears both ends is the one stitch
  //    between them, as it was.
  // NOT ported: a row shorter than `machine.TINY_STITCH_MM` collapsing to its
  // middle. That moves a row's ends, and the walks are built on them.
  //
  // "Longer than a stitch" has a tolerance, `splitTol`, in the caller's units:
  // the Python engine's is a micron (`stitches.SPLIT_TOLERANCE_MM`, its defect
  // 25: a step a few ulp over a stitch was halved, and which rows were turned
  // on the row angle's cosine). A caller that gives none gets a billionth of a
  // stitch, which is over float noise near the origin and nothing more.
  //
  // THE FLOOR. No stitch along a row is under `minStitch` -- where a stitch is
  // at least two of them. A step between one stitch and one stitch plus
  // `minStitch` is halved, so with a stitch under two shortest stitches the
  // halves come out under the shortest (found by audit, on a builder asked
  // for a 1.5 mm stitch; the Python fill's 1 mm against 3 never meets it).
  // They are never under HALF a stitch, and an even cut goes that far down as
  // it is. The clearance stays what the caller gave: taking it as half a
  // stitch there was tried, moved no floor, and made a third more short
  // stitches (second audit).
  //
  // With NO `minStitch` there is no clearance: a hole can sit any distance
  // from a row's end short of on it. The builder always gives one.
  //
  // A grid point EXACTLY `minStitch` from an end falls either way on the last
  // bit, here as in Python. It falls the same way all along a straight edge.
  const STAGGER_EPS = 1e-9;
  // The longest cycle. The table of slots is built whole, so a cycle is not
  // whatever number it is handed; and at any row pitch 64 rows without two
  // alike is past anything a cycle is for.
  const STAGGER_MAX = 64;
  function staggeredRow(a, b, phase, stitch, minStitch, splitTol) {
    const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x);
    const min = Math.max(minStitch || 0, stitch * STAGGER_EPS);
    const xs = [x0];
    if (x1 - x0 >= 2 * min) {
      for (let x = Math.ceil((x0 - phase) / stitch) * stitch + phase; x < x1; x += stitch) {
        if (x - xs[xs.length - 1] >= min && x1 - x >= min) xs.push(x);
      }
    }
    xs.push(x1);
    if (a.x > b.x) xs.reverse();   // the way the thread runs
    const tol = splitTol > 0 ? splitTol : stitch * STAGGER_EPS;
    const holes = [];
    for (let k = 1; k < xs.length; k++) {
      const p = xs[k - 1], q = xs[k], d = Math.abs(q - p);
      if (d > stitch + tol) {
        const steps = Math.ceil((d - tol) / stitch);
        for (let s = 1; s < steps; s++) holes.push(p + (q - p) * (s / steps));
      }
      if (k + 1 < xs.length) holes.push(q);
    }
    return holes.map((x) => ({ x, y: a.y }));
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
  //   `ground` (with `columns`): the polygons that count as filled ground for
  //   that question, when they are not `polygons` themselves. An underlay is
  //   given the rings the FILL is sewn to.
  //   `from`, `clear`, `travelBudget` (with `columns`): see sewColumns.
  //   `stagger` (default off), `minStitch`, `splitTol`: the row stagger above.
  //   `stagger` is the rows in a cycle, a NUMBER (a flag or text is no
  //   stagger); the grid's pitch is `maxStitch`; `minStitch` and `splitTol`
  //   (in the polygons' units) are the shortest stitch a row may open or close
  //   on and how far over a stitch a step may be before it is cut.
  //   Either walk, any row order: a row's holes turn on its place among the
  //   scanlines and on nothing else.
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

    // The row stagger: the holes between the ends of the row a -> b. A row's
    // number is read off its height, so it is the same row whichever walk
    // sews it and in whatever order.
    const cycle = typeof opts.stagger === "number" && maxStitch > 0 ? Math.min(Math.floor(opts.stagger), STAGGER_MAX) : 0;
    const stagger = cycle >= 1 ? cycle : 0;
    const slots = stagger ? staggerSlots(stagger) : null;
    const rowHoles = !stagger ? null : (a, b) => {
      const ri = Math.round((a.y - minY) / rowSpacing);
      return staggeredRow(a, b, (slots[ri % stagger] / stagger) * maxStitch, maxStitch, opts.minStitch, opts.splitTol);
    };

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
    //    pair of rows. The ones asked about are the ones in `key`. The
    //    center-out reposition is left out only where it will be CUT: a caller
    //    that does not mark connectors has it sewn, across whatever it crosses.
    // A plain shape changes in one way: a turn longer than a stitch that runs
    // outside the shape is sewn along the rim, where the walk below floats it.
    const markConnectors = !!opts.markConnectors;
    let rimTurn = null;
    if (opts.columns) {
      const tol = opts.openTol > 0 ? opts.openTol : rowSpacing;
      const floated = (d) => !!(maxStitch && maxStitch > 0 && d > maxStitch);
      // What every move is measured against. An underlay pass is SEWN to the
      // drawn outline, but where its thread may lie is what the fill will
      // cover, which the caller knows and this pass's own outline is not.
      let ground = edges;
      if (opts.ground) {
        ground = [];
        for (const poly of opts.ground) {
          const rp = poly.map((p) => rotate(p, cosN, sinN));
          for (let i = 0; i < rp.length; i++) ground.push([rp[i], rp[(i + 1) % rp.length]]);
        }
      }
      let plain = rowSpans.every((r) => r.spans.length === 1);
      rimTurn = {};
      for (let i = 2; plain && i < key.length; i += 2) {
        const d = Math.hypot(key[i].x - key[i - 1].x, key[i].y - key[i - 1].y);
        if (i === lowerSweepStartIdx && (markConnectors || !floated(d))) continue;
        if (d <= 2 * tol && !floated(d)) continue;   // cannot be deep, and is sewn anyway
        const under = groundUnder(key[i - 1], key[i], ground, tol, 0, true);
        if (under === OPEN) plain = false;
        else if (under === ON_RIM && floated(d)) rimTurn[i] = true;
      }
      if (!plain) {
        const cut = cutColumns(spansWithLength(rowSpans));
        splitAtOpenTurns(cut, ground, tol);
        const budget = opts.travelBudget > 0 ? opts.travelBudget : (maxStitch > 0 ? 5 * maxStitch : Infinity);
        // the walk works in the rotated frame; the caller's `clear` does not
        const from = opts.from ? rotate(opts.from, cosN, sinN) : null;
        const clear = opts.clear ? ((a, b) => opts.clear(rotate(a, cosP, sinP), rotate(b, cosP, sinP))) : null;
        const walked = sewColumns(cut.columns, cut.above, { edges: ground, rings, ringOf, posOf },
          { maxStitch, tol, pitch: rowSpacing, cosP, sinP, budget, from, clear, rowHoles });
        // for a caller that counts which walk it got (center-out is the other one)
        Object.defineProperty(walked, "columnWalk", { value: true });
        return walked;
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
      if (rowHoles && !isConnector) {
        // a row, staggered: its holes are the grid's, not an even division
        for (const h of rowHoles(a, b)) out.push(rotate(h, cosP, sinP));
      } else if (maxStitch && maxStitch > 0 && dist > maxStitch) {
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

  // A running stitch round a closed ring that KEEPS ITS CORNERS: no stitch
  // longer than `stitchLen`, and none whose chord strays more than `hug` from
  // the ring. `runningOutline` above steps a fixed distance along the ring and
  // lands where it lands, so it chords across every corner sharper than its
  // step: outside an inside corner of the outline, and INTO a hole at each of
  // the hole's corners (0.6 mm deep, with 2 mm stitches round a 4 mm hole).
  // Starts on polygon[0] and ends on it -- or, with `opts.open`, runs along
  // the points as a path and ends on the last.
  function huggingOutline(polygon, opts) {
    const n = polygon.length, stitchLen = opts.stitchLen, hug = opts.hug;
    if (n === 0) return [];
    const out = [{ x: polygon[0].x, y: polygon[0].y }];
    if (n === 1) return out;
    const end = opts.open ? n - 1 : n;   // index of the last point: n is polygon[0] again
    const at = (k) => polygon[k % n];
    const hugs = (a, b) => {
      for (let m = a + 1; m < b; m++) if (distToSegment(at(m), at(a), at(b)) > hug) return false;
      return true;
    };
    let a = 0;
    while (a < end) {
      // as far round as the chord from here still hugs every corner it skips
      let b = a + 1;
      while (b < end && hugs(a, b + 1)) b++;
      const p = at(a), q = at(b);
      const steps = Math.max(1, Math.ceil(Math.hypot(q.x - p.x, q.y - p.y) / stitchLen));
      for (let s = 1; s <= steps; s++) out.push({ x: p.x + (q.x - p.x) * s / steps, y: p.y + (q.y - p.y) * s / steps });
      a = b;
    }
    return out;
  }

  return {
    tatamiFill,
    runningOutline,
    huggingOutline,
    pcaAngleDeg,
    crossesOpenGround,
    openGroundTest,
    staggerSlots,
  };
});
