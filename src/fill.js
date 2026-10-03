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

  // rows: [{ ri, y, spans: [[x0, x1], ...] }] in scanline order, empty
  // scanlines absent. -> { columns, above }: each column is
  // [{ y, x0, x1 }, ...] top-down, and above[i] lists the columns whose last
  // row sits directly over column i's first (what it forked from, or what
  // merged into it).
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
        columns[parent].push({ y: row.y, x0: sp[0], x1: sp[1] });
        nowOpen[si] = parent;
      });
      open = nowOpen;
      prevSpans = row.spans;
      prevRi = row.ri;
    }
    return { columns, above };
  }

  function insideEvenOdd(p, edges) {
    let inside = false;
    for (const [u, v] of edges) {
      if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) inside = !inside;
    }
    return inside;
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
  // Sampled at tol/4, so anything deeper than about 1.1 tol is seen; a slot
  // narrower than 2 tol is, by the same token, treated as closed. `slack` is
  // ignored at either end: a run of ANOTHER pass may begin a hair off the edge
  // (digitize.js, between runs).
  //
  // There is a third answer, and it matters for one kind of move only. A move
  // can run OUTSIDE the polygons without ever being deep: the turn from the
  // last row of a T's bar to the first of its stem runs the length of the
  // bar's underside, under a pitch out. Sewn, that is the fill's own edge.
  // FLOATED -- which is what the plain walk does with any turn longer than a
  // stitch -- it is a loose thread nothing will ever cover (28 mm of it on a
  // 35 mm T). So: INSIDE may be floated, ON_RIM must be sewn, OPEN must be cut.
  const INSIDE = 0, ON_RIM = 1, OPEN = 2;
  function groundUnder(a, b, edges, tol, slack) {
    const len = Math.hypot(b.x - a.x, b.y - a.y);
    const lo = slack || 0, hi = len - lo;
    if (!(hi > lo)) return INSIDE;
    const reach = Math.max(tol, ON_EDGE_EPS);
    const step = Math.max(reach / 4, (hi - lo) / 4000);
    let worst = INSIDE;
    for (let s = lo + step / 2; s < hi; s += step) {
      const p = { x: a.x + (b.x - a.x) * s / len, y: a.y + (b.y - a.y) * s / len };
      if (insideEvenOdd(p, edges)) continue;
      let d = Infinity;
      for (const [u, v] of edges) {
        d = Math.min(d, distToSegment(p, u, v));
        if (d <= ON_EDGE_EPS) break;
      }
      if (d > reach) return OPEN;
      if (d > ON_EDGE_EPS) worst = ON_RIM;
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
  // RUNS of one shape (made with the thread attached).
  function crossesOpenGround(a, b, polygons, tol, slack) {
    const edges = [];
    for (const poly of polygons) for (let i = 0; i < poly.length; i++) edges.push([poly[i], poly[(i + 1) % poly.length]]);
    return leavesShape(a, b, edges, tol, slack);
  }

  // Sew the columns from wherever the last one ended, entering each by one of
  // its four corners (top-down or bottom-up, first row either way).
  //
  // ORDER. A column waits until every column directly above it is sewn, so
  // the walk finishes a level before it descends. Without that the nearest
  // reachable column after the first strip beside a row of holes is the band
  // BELOW them, the other strips are stranded, and each costs a cut to get
  // back to: 3 for three holes in a row, 64 to 126 on a 36-hole badge.
  //
  // THE MOVE to the next column, in order of preference:
  //   1. one stitch, inside the shape;
  //   2. a run ALONG THE ROW, inside the shape, however long -- from the foot
  //      of one strip to the foot of the next along the hole's own edge. It
  //      runs with the rows and on the rim, so it reads as the fill's edge;
  //   3. otherwise the thread is CUT, and the nearest column taken.
  // A row turn inside a column is asked the same question and cut the same
  // way. A cut point is where the frame goes, not a penetration, so the same
  // spot follows it as a plain point: the row starts on its own start.
  //
  // What this does not do: travel ACROSS rows under cover. A ring therefore
  // still costs one cut, and a row of holes can cost one where its last strip
  // ends at the wrong end for the band below. The Python engine runs under
  // rows still to sew.
  function sewColumns(cols, above, edges, maxStitch, tol, pitch, cosP, sinP) {
    const tooLong = (d) => !!(maxStitch && maxStitch > 0 && d > maxStitch);
    const walk = (col, fromBottom, firstReversed) => {
      const seq = fromBottom ? col.slice().reverse() : col;
      const key = [];
      seq.forEach((r, k) => {
        const rev = (k % 2 === 1) !== firstReversed;
        key.push({ x: rev ? r.x1 : r.x0, y: r.y }, { x: rev ? r.x0 : r.x1, y: r.y });
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
    const done = cols.map(() => false);
    const byDistance = (p, q) => p.d - q.d || p.ci - q.ci || p.j - q.j;
    let cur = null;
    while (remaining.length) {
      // every column directly above it is sewn (the first has none above)
      let ready = remaining.filter((ci) => above[ci].every((a) => done[a]));
      if (!ready.length) ready = remaining;
      let chosen = { ci: ready[0], j: 0 }, how = "start";
      if (cur) {
        let nearest = null;
        const oneStitch = [], alongRow = [];
        for (const ci of ready) {
          variants[ci].forEach((v, j) => {
            const c = { ci, j, d: Math.round(Math.hypot(v[0].x - cur.x, v[0].y - cur.y) * 1e6) / 1e6 };
            if (!nearest || byDistance(c, nearest) < 0) nearest = c;
            if (!tooLong(c.d)) oneStitch.push(c);
            else if (Math.abs(v[0].y - cur.y) <= pitch * 1.0001) alongRow.push(c);
          });
        }
        const reach = (list) => list.sort(byDistance).find((c) => !leavesShape(cur, variants[c.ci][c.j][0], edges, tol));
        chosen = reach(oneStitch);
        how = "stitch";
        if (!chosen) { chosen = reach(alongRow); how = "run"; }
        if (!chosen) { chosen = nearest; how = "cut"; }
      }
      const key = variants[chosen.ci][chosen.j];
      remaining.splice(remaining.indexOf(chosen.ci), 1);
      done[chosen.ci] = true;
      if (how === "cut") cutTo(key[0]);
      else if (how === "run") sewTo(cur, key[0]);
      else out.push(rotate(key[0], cosP, sinP));
      for (let i = 1; i < key.length; i++) {
        // odd i runs along a row, inside by construction; even i is the turn
        // to this column's next row.
        if (i % 2 === 0 && leavesShape(key[i - 1], key[i], edges, tol)) cutTo(key[i]);
        else sewTo(key[i - 1], key[i]);
      }
      cur = key[key.length - 1];
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

    // Collect rotated edges and compute bbox.
    const edges = [];
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
      }
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
      // Gather x-intersections with all edges using the half-open rule.
      const xs = [];
      for (const [a, b] of edges) {
        const y0 = a.y;
        const y1 = b.y;
        if (y0 === y1) continue; // horizontal edge: skip (parity preserved)
        // Half-open: count edge if min(y0,y1) <= y < max(y0,y1).
        const lo = Math.min(y0, y1);
        const hi = Math.max(y0, y1);
        if (y >= lo && y < hi) {
          const t = (y - y0) / (y1 - y0);
          xs.push(a.x + t * (b.x - a.x));
        }
      }
      if (xs.length >= 2) {
        xs.sort((p, q) => p - q);
        // Pair spans (even-odd).
        const spans = [];
        for (let i = 0; i + 1 < xs.length; i += 2) {
          spans.push([xs[i], xs[i + 1]]);
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
        rowSpans.push({ ri: rowIndex, y, spans });
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
        const ground = groundUnder(key[i - 1], key[i], edges, tol);
        if (ground === OPEN) plain = false;
        else if (ground === ON_RIM && floated(d)) rimTurn[i] = true;
      }
      if (!plain) {
        const cut = cutColumns(rowSpans);
        return sewColumns(cut.columns, cut.above, edges, maxStitch, tol, rowSpacing, cosP, sinP);
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
  };
});
