// Quality auto-digitize orchestrator: turns ColorRegions (from raster tracing
// OR SVG import) into a Design with underlay, satin-for-thin-shapes,
// fill-with-per-region-angle, and pull compensation. Dual-mode (Node + browser).
(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  const _node = typeof module !== "undefined" && module.exports;
  const dep = _node ? require : null;
  const units = _node ? dep("./units.js") : root.EMB;
  const garments = _node ? dep("./garments.js") : root.EMB;
  const fillmod = _node ? dep("./fill.js") : root.EMB;
  const satinmod = _node ? dep("./satin.js") : root.EMB;
  const satinfontmod = _node ? dep("./satinfont.js") : root.EMB;

  // Physical constants this engine shares with the Python digitizer
  // (`digitizer/digitizer_core/machine.py`). fabrics.py's rule: until a
  // sew-out says otherwise the two engines make the SAME physical choices, or
  // a design digitized here and one built there would need different tuning
  // on the same garment. When a sew-out moves one of these, move it in both
  // places — test/digitize.test.js reads machine.py and fails if they drift.
  //
  // Tatami row spacing — `machine.FILL_ROW_MM`. Kent's ruling 2026-09-03
  // (DOCTRINE "Fill row spacing is settled"): his first sew-out at 0.40 showed
  // cloth between every fill row, and the professional's commissioned files
  // read as ROWS lay their fills at 0.141-0.169 mm. This engine defaulted to
  // 0.45 until 2026-09-04. Fabric presets still scale it (densityAdjust).
  const FILL_ROW_MM = 0.15;
  // Satin cross spacing along the stroke — `machine.SATIN_SPACING_MM`. A
  // SEPARATE physical choice from the fill row: it is a same-rail pitch (Law
  // 19 — Hatch, Melco's 4 pt, Madeira 40wt all put it at 0.40, and the sew-out
  // called satin "the one thing that looks right"), so it did NOT follow the
  // fill row to 0.15. One `densityMm` used to feed both; see
  // buildQualityDesign for the split.
  const SATIN_SPACING_MM = 0.4;
  // Thread consumed per mm of stitch PATH — `machine.THREAD_LENGTH_FACTOR`.
  // The top thread goes down and back through the fabric, so the cone gives up
  // more than the path measures. Explicitly a rule of thumb for the
  // operator-facing estimate ("nothing geometric", machine.py's own words) and
  // NOT a geometry constant: it changes what the shopping list says, never
  // where a needle goes.
  //
  // Hand-ported for the same reason `fabrics.js` is: the browser lane has to
  // quote the same metres the Python lane would for the same path, or a name
  // and a logo in one project would be priced on two different bases.
  // test/digitize.test.js reads machine.py and fails if they drift.
  const THREAD_LENGTH_FACTOR = 1.35;

  // Lock stitches — `machine.TIE_STITCH_MM` / `machine.TIE_STITCHES`, ported
  // 2026-09-14. Until then ZERO tie/lock records existed anywhere in `src/`:
  // the only `lock`/`tie` match in the whole browser lane was the brand name
  // "Baby Lock" in a `garments.js` comment. The Python lane has always tied
  // every block unconditionally (`stitches.apply_ties`, no config flag), so
  // this was a straight parity gap, not a technique the two lanes disagreed
  // about — a lettering file exported from the Studio could start or end its
  // thread with nothing holding it, and unravel from the first wash.
  //
  // These are hand-ported across the language boundary for exactly the reason
  // `fabrics.js` and THREAD_LENGTH_FACTOR are, and carry the same risk law 26
  // proved real. `digitizer/tests/test_machine_wire.py` scans BOTH trees for
  // every `const NAME = <number>` and fails when a name declared in more than
  // one file stops agreeing, so these two are covered the moment they exist —
  // no registration step, and no way to drift quietly.
  const TIE_STITCH_MM = 0.8;
  const TIE_STITCHES = 3;

  // Row stagger for a cover fill (`fillStagger`, built OFF) —
  // `machine.FILL_STAGGERS` rows to a cycle, and `machine.MIN_STITCH_MM`
  // between a row's end and the first needle hole after it. The Python fill's
  // own two numbers, hand-ported like the pair above and held by the same wire
  // test. The grid's pitch is NOT ported: it is this lane's own stitch length
  // (`maxStitchMm`, 4), where the Python fill's is `FILL_STITCH_MM`, 3. See
  // fill.js, "ROW STAGGER".
  const FILL_STAGGERS = 4;
  const MIN_STITCH_MM = 1.0;
  // How far over a stitch a step along a row may be before it is cut in two —
  // `stitches.SPLIT_TOLERANCE_MM`, a micron. The wire test reads plain
  // decimals and cannot see this one; test/fill-stagger.test.js holds it.
  const SPLIT_TOLERANCE_MM = 1e-6;

  // A lock stitch at `at`, laid along the path toward `toward` — the exact
  // shape of `stitches.tie_run`, including the two rules its docstring earns:
  //
  //  1. The legs NEVER reach past `toward` (`leg = min(TIE_STITCH_MM, d)`). A
  //     tie that overshoots leaves a whisker of thread outside the shape's
  //     edge, which on a finished garment reads as a stray stitch someone has
  //     to trim off. Python measured this on its first smoke run, where
  //     tie-offs pushed the design's bounding box 0.8 mm outside its own
  //     artwork — so the browser must not re-learn it.
  //  2. The run both STARTS and ENDS at `at`, so splicing it in front of a run
  //     (or behind one) leaves the sewn path continuous and moves no
  //     penetration that was already there.
  //
  // Returns the bounce points including both endpoints, in the caller's own
  // units. `legLen` is one leg IN THOSE UNITS; left out, the caller is working
  // in millimetres. (Until 2026-10-03 there was no `legLen`, and the one caller
  // passed pixels: a lettering lock's leg was 0.8 PIXELS -- 0.5 mm on a default
  // design, 0.3 mm on one fitted to 40 mm, 2.0 mm at 2 px per mm.)
  function tieRun(at, toward, legLen) {
    const dx = toward.x - at.x, dy = toward.y - at.y;
    const d = Math.hypot(dx, dy);
    if (d < 1e-9) return [at];
    const leg = Math.min(legLen > 0 ? legLen : TIE_STITCH_MM, d);
    const inner = { x: at.x + (dx / d) * leg, y: at.y + (dy / d) * leg };
    const pts = [at];
    for (let i = 0; i < TIE_STITCHES; i++) pts.push(i % 2 === 0 ? inner : at);
    // Value comparison, not `!== at`: Python compares tuples, and an identity
    // check here would happen to agree only because the same object is pushed
    // each time. It would then diverge silently the moment anyone rebuilt the
    // point — which is the whole failure mode this port is guarding against.
    const tail = pts[pts.length - 1];
    if (tail.x !== at.x || tail.y !== at.y) pts.push(at);
    return pts;
  }

  // Lock the thread wherever it starts and wherever it gets cut: the rule of
  // `stitches.apply_ties`, for BOTH builders (`ties: true`, default off).
  //
  // It is asked of the FINISHED record stream, not of the runs on their way
  // into it, for two reasons the lettering port (2026-09-14, inline, in px)
  // paid for:
  //  - the stream is in DST units, so a leg is `TIE_STITCH_MM` and nothing
  //    else. In px it was whatever a pixel happened to be worth.
  //  - "where the thread starts" is a fact about the stream. A run can open
  //    with a float, a fill has a cut in the middle of it (center-out's, the
  //    column walk's), and the first penetration after a cut is not always the
  //    first point of anything.
  //
  // A THREAD is the records between two cuts (`trim`, `color`, either end of
  // the stream; `end` sews nothing and needs no rule). A `jump` is not a cut:
  // the question is "is the thread starting here, or being cut here", not
  // "did the needle lift".
  //
  // Each thread is locked AT ITS ENDS: on its first penetration and on its
  // last, by `tieRun`'s bounce put straight after its anchor -- at, [inner,
  // at, inner, at], and on, the sequence Python sews at both ends. (The
  // lettering port put the tie-in in FRONT of the run's own first stitch
  // instead, which made that stitch a second penetration of the same hole.)
  // The bounce is laid toward the nearest other place the frame goes on that
  // side: the next stitch, nearly always, and then the lock lies on that
  // stitch. Where the thread's end is ONE penetration with a float beside it,
  // the lock is laid along the row that stitch closed: toward where the
  // frame was just before it (a short row after a float or a cut is one
  // record, because the float or the cut lands on the row's start). Along a
  // float is the last choice: a float may cross a hole. (A lock laid toward a
  // jump's end can lie up to a leg outside the box of the stitches, if that
  // end is outside it. A builder's jump ends on a row's start, and in 29,050
  // audited builds no box grew; a stream written by hand can do it.)
  //
  // The first version looked for "two stitch records in a row" instead, and
  // an audit found what that costs: where a thread ends in a float and one
  // stitch the lock sat up-thread at the last real sewing, with the tail
  // loose behind it -- 6.1% of tie-offs in shape designs, by up to 371 mm.
  //
  // A doubled hole at either end is stepped over, so the lock still goes
  // between it and the rest of the thread. A thread that goes down in one
  // place only sews nothing and gets no lock.
  //
  // -> { stitches, nTies }: a new array (the records in it are the caller's
  // own). `spans` (i0/i1 into the old one) are moved in place, and a lock
  // stays inside the span its anchor is in.
  function applyTies(stitches, spans) {
    const leg = TIE_STITCH_MM * units.DST_UNITS_PER_MM;
    const cut = (s) => s.type === "trim" || s.type === "color";
    const same = (p, q) => p.x === q.x && p.y === q.y;
    // somewhere the frame goes that is not `at`
    const elsewhere = (k, at) => (stitches[k].type === "stitch" || stitches[k].type === "jump") && !same(stitches[k], stitches[at]);
    const toward = new Map();   // anchor record -> the record its lock is laid toward
    for (let i = 0; i < stitches.length;) {
      if (cut(stitches[i])) { i++; continue; }
      let j = i;
      while (j < stitches.length && !cut(stitches[j])) j++;   // the thread is [i, j)
      let first = -1, last = -1, places = false;
      for (let k = i; k < j; k++) {
        if (stitches[k].type !== "stitch") continue;
        if (first < 0) first = k;
        last = k;
        if (!same(stitches[k], stitches[first])) places = true;
      }
      if (places) {
        let next = first + 1, a = first;
        while (!elsewhere(next, first)) { if (stitches[next].type === "stitch") a = next; next++; }
        // One penetration and then a float: that stitch closed a row which
        // began where the frame was just before it. Center-out's lower sweep
        // opens so on a shape with a hole -- the cut lands on a row's start,
        // the row is one record at the hole's rim, and the next move floats
        // across the hole. Laid toward the float, the lock's inner point was
        // 0.8 mm into the hole. It is laid back along the row.
        // (A cut left ON the old thread's last stitch carried the frame
        // nowhere, so it is not where a row began. No builder writes one.)
        const before = first - 1;
        let back = stitches[next].type === "jump" && before >= 0 &&
          (stitches[before].type === "trim" || stitches[before].type === "jump") && !same(stitches[before], stitches[first]);
        if (back && stitches[before].type === "trim") {
          let p = before - 1;
          while (p >= 0 && stitches[p].type !== "stitch") p--;
          if (p >= 0 && same(stitches[p], stitches[before])) back = false;
        }
        toward.set(a, back ? before : next);
        let prev = last - 1, z = last;
        while (!elsewhere(prev, last)) { if (stitches[prev].type === "stitch") z = prev; prev--; }
        toward.set(z, prev);
      }
      i = j;
    }
    const out = [], start = new Array(stitches.length), end = new Array(stitches.length);
    stitches.forEach((s, k) => {
      start[k] = out.length;
      out.push(s);
      if (toward.has(k)) {
        const bounce = tieRun(s, stitches[toward.get(k)], leg);
        const inner = { x: Math.round(bounce[1].x), y: Math.round(bounce[1].y) };
        for (let b = 1; b < bounce.length; b++) out.push({ x: b % 2 ? inner.x : s.x, y: b % 2 ? inner.y : s.y, type: "stitch" });
      }
      end[k] = out.length - 1;
    });
    for (const sp of spans || []) { sp.i0 = start[sp.i0]; sp.i1 = end[sp.i1]; }
    return { stitches: out, nTies: toward.size };
  }

  // The size of a design is the size of its THREAD — measured from the records
  // that actually carry geometry, never from the shape the design was fit to.
  //
  // Both builders below used to report `fitScale`'s target box: the glyph
  // outline (or the traced region polygons) scaled to the garment's placement
  // box. That box is the INPUT to routing. Satin rails are then pushed apart
  // by pull compensation and the weight preset, and underlay reaches past the
  // outline too, so the thread lands outside the box the number describes.
  //
  // Measured 2026-09-07 across 7,470 lettering designs (10 garments x 85
  // shipped fonts x 3 texts x 3 weights): 4,898 of them (65.6%) put thread
  // outside the placement box they had just been fit to, by up to 9.6 mm, and
  // the reported number could not show it because it WAS the box. On the
  // image path (buildQualityDesign, enthusiast_logo at hat_front) the same gap
  // is +1.6 mm of width. It runs the other way too — that logo's height reads
  // 0.2 mm SMALLER than the polygons it was traced from, because the fill
  // never reaches the outermost point.
  //
  // Two things downstream were reading the box as if it were the thread:
  //   - the Studio's field caption and its hoop CEILING check (hoop.js:
  //     "a warning, not a silent resize") — on 4 of those 7,470 the ceiling
  //     check said "fits" where the actual thread needs the hoop rotated;
  //   - the printed worksheet's design-size line (pdfsheet.js).
  // And SizePanel already showed the honest number, via combine.js's
  // bboxMmFromStitches — so one design displayed two different widths at once
  // (127.0 mm in the caption, 5.05 in = 128.3 mm in the size field, with the
  // field's own max at 5.00). Same rule here as there, deliberately: skip
  // `color` (a marker at wherever the last record happened to be) and `end`
  // (buildQualityDesign's is at the absolute origin), keep stitch/jump/trim.
  //
  // `fallback` is what to report when nothing geometric was emitted at all.
  function designExtentMm(stitches, fallbackWmm, fallbackHmm) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const s of stitches) {
      if (s.type === "color" || s.type === "end") continue;
      if (s.x < minX) minX = s.x;
      if (s.x > maxX) maxX = s.x;
      if (s.y < minY) minY = s.y;
      if (s.y > maxY) maxY = s.y;
    }
    if (!isFinite(minX)) return { widthMM: fallbackWmm, heightMM: fallbackHmm };
    return {
      widthMM: (maxX - minX) / units.DST_UNITS_PER_MM,
      heightMM: (maxY - minY) / units.DST_UNITS_PER_MM,
    };
  }

  function polyArea(p) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j].x * p[i].y - p[i].x * p[j].y); return Math.abs(a) / 2; }
  // SIGNED shoelace area (sign encodes winding). Do NOT confuse with polyArea (abs).
  function signedArea(p) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j].x * p[i].y - p[i].x * p[j].y); return a / 2; }
  function polyPerim(p) { let L = 0; for (let i = 0; i < p.length; i++) { const q = p[(i + 1) % p.length]; L += Math.hypot(q.x - p[i].x, q.y - p[i].y); } return L; }
  function centroid(p) { let x = 0, y = 0; for (const q of p) { x += q.x; y += q.y; } return { x: x / p.length, y: y / p.length }; }
  // principal-axis angle (degrees) of a set of polygons. Moved into fill.js
  // 2026-09-11 so the lettering lane's wide-column fill runs its rows at the
  // same angle this lane's fills already do, from one definition.
  const pcaAngleDeg = fillmod.pcaAngleDeg;
  // inset a ring toward its centroid by `d` px (crude but fine for underlay)
  function insetRing(ring, d) {
    const c = centroid(ring);
    return ring.map((q) => {
      const dx = c.x - q.x, dy = c.y - q.y, L = Math.hypot(dx, dy) || 1;
      const t = Math.min(d, L * 0.4);
      return { x: q.x + dx / L * t, y: q.y + dy / L * t };
    });
  }

  // A ring's corners with no point said twice running (a ring handed over
  // closed says its first point again at the end; to within a billionth of a
  // px, since a closing point that was computed rarely lands exactly).
  function distinctCorners(ring) {
    return ring.filter((p, i) => { const q = ring[(i + 1) % ring.length]; return Math.abs(p.x - q.x) > 1e-9 || Math.abs(p.y - q.y) > 1e-9; });
  }

  // Offset a polygon ring by `dPx` along per-vertex OUTWARD normals (miter join).
  // outward=true grows the ring, outward=false shrinks it — correct regardless of
  // winding (signed area picks the outward sense). Miter displacement is clamped
  // at 3*dPx so sharp concave vertices don't produce spikes. Returns a fresh ring.
  //
  // It is the ring's corners SAID ONCE that are moved (distinctCorners), so a
  // ring handed over closed comes back as the same ring handed over open does,
  // one point shorter. A point said twice running is an edge of no length: it
  // has no direction and so no normal, and its two ends were each moved along
  // the one real edge beside them -- the first by the whole mitre clamp, three
  // times the distance -- which made a wedge of the corner. A ring that says
  // no point twice is moved exactly as it always was; one with fewer than
  // three corners left has no outward side and is handed back as it came.
  function offsetRing(ring, dPx, outward) {
    const copy = ring ? ring.map((q) => ({ x: q.x, y: q.y })) : [];
    if (copy.length < 3 || !(Math.abs(dPx) > 1e-9)) return copy;
    const pts = distinctCorners(ring), n = pts.length;
    if (n < 3) return copy;
    // signed area (shoelace): >0 and <0 pick opposite outward-normal senses.
    let area2 = 0;
    for (let i = 0; i < n; i++) { const a = pts[i], b = pts[(i + 1) % n]; area2 += a.x * b.y - b.x * a.y; }
    const sgn = area2 >= 0 ? 1 : -1;      // winding sign
    const dir = outward ? 1 : -1;         // grow vs shrink
    const maxDisp = 3 * dPx;              // miter clamp
    const out = [];
    for (let i = 0; i < n; i++) {
      const prev = pts[(i - 1 + n) % n], cur = pts[i], next = pts[(i + 1) % n];
      let e1x = cur.x - prev.x, e1y = cur.y - prev.y;
      let e2x = next.x - cur.x, e2y = next.y - cur.y;
      const L1 = Math.hypot(e1x, e1y) || 1, L2 = Math.hypot(e2x, e2y) || 1;
      e1x /= L1; e1y /= L1; e2x /= L2; e2y /= L2;
      // outward unit normal of an edge (dx,dy) is sgn*(dy,-dx)
      const n1x = sgn * e1y, n1y = -sgn * e1x;
      const n2x = sgn * e2y, n2y = -sgn * e2x;
      let bx = n1x + n2x, by = n1y + n2y;
      const bl = Math.hypot(bx, by);
      let dispx, dispy;
      if (bl < 1e-6) { dispx = n1x * dPx; dispy = n1y * dPx; }  // ~180° cusp
      else {
        bx /= bl; by /= bl;
        const cosH = bx * n1x + by * n1y;         // cos(half exterior angle)
        let m = dPx / Math.max(cosH, 1e-3);       // miter length = d/cos(halfAngle)
        if (m > maxDisp) m = maxDisp;             // clamp spikes at sharp vertices
        dispx = bx * m; dispy = by * m;
      }
      out.push({ x: cur.x + dir * dispx, y: cur.y + dir * dispy });
    }
    return out;
  }

  // How many of the nearest corners an edge run tries before it settles for a
  // cut (`fillColumns` only). Each try is one walk of a move over the shape.
  const EDGE_RUN_TRIES = 8;
  // How many corners round the ring it is on it will leave from instead.
  const EDGE_RUN_EXITS = 16;
  // How far inside the fill an edge run lies, with `fillColumns`. 0.2 mm is
  // what the engine without the flag gives at the Studio's own 10 px per mm
  // ("2 px"); there it grows with the design, to 0.6 mm on one enlarged five
  // times. A length on cloth should not depend on the drawing's resolution.
  const EDGE_RUN_INSET_MM = 0.2;

  // The ring an edge-run underlay is sewn on, with `fillColumns`: the drawn
  // ring moved `insetPx` into the FILLED side -- in from the outline, OUT from
  // a hole. Without the flag it is `insetRing`, toward the ring's own centre,
  // which for a hole is INTO the hole: covered by the fill's pull compensation
  // at 0.2 mm, and past it at 0.6. A ring that folds when moved is used as
  // drawn.
  function edgeRunRing(ring, isHole, insetPx) {
    const moved = offsetRing(ring, insetPx, isHole);
    const a0 = signedArea(ring), a1 = signedArea(moved);
    if (Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6) return ring.map((q) => ({ x: q.x, y: q.y }));
    return moved;
  }
  // A shape with no hole and no inside corner. Its edge run cannot leave it
  // -- a chord of a convex ring is inside the ring -- so `fillColumns` leaves
  // that run exactly as it is without the flag.
  function isConvexRing(ring) {
    let sign = 0;
    for (let i = 0; i < ring.length; i++) {
      const a = ring[i], b = ring[(i + 1) % ring.length], c = ring[(i + 2) % ring.length];
      const z = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
      if (Math.abs(z) < 1e-9) continue;
      if (sign && Math.sign(z) !== sign) return false;
      sign = Math.sign(z);
    }
    return true;
  }

  // Build underlay point-runs for a shape under a named style. Returns an array
  // of runs (each becomes one pushRun). ctx: { fillAngle, pxPerFinalMm, maxStitch,
  // underlayStitchPx, underlayRowPx, runningOutline, tatamiFill, insetRing,
  // pcaAngleDeg }. Styles: none | edge_run | center_run | zigzag | edge_zigzag |
  // edge_lattice | double_lattice.
  // With `fillColumns`: also { columns, openTol, clear(a, b) } -- `clear` says
  // whether a float from a to b would be left uncut.
  function underlayRuns(shape, styleName, ctx) {
    const style = styleName || "none";
    if (style === "none") return [];
    const outer = shape.outer;
    const holes = (shape.holes || []).filter((hh) => hh && hh.length >= 3);
    const rings = [outer].concat(holes);
    const pxPerFinalMm = ctx.pxPerFinalMm;
    const fillAngle = ctx.fillAngle || 0;
    const edgeInset = Math.min(2, 0.6 * pxPerFinalMm);
    const edgeStitch = ctx.underlayStitchPx;
    const latticeRow = ctx.underlayRowPx;              // ~2.5mm sparse tatami
    const zigRow = Math.max(0.02, 2.0 * pxPerFinalMm); // ~2.0mm zig-zag rows (floor is loop-safety only -- see PX_LOOP_EPS note in buildQualityDesign)
    const maxStitch = ctx.maxStitch;

    function edgeRun() {
      if (!ctx.columns || (!holes.length && isConvexRing(outer))) {
        const r = [ctx.runningOutline(ctx.insetRing(outer, edgeInset), { stitchLen: edgeStitch })];
        for (const hh of holes) r.push(ctx.runningOutline(ctx.insetRing(hh, edgeInset), { stitchLen: edgeStitch }));
        return r;
      }
      // With `columns`, three things about the edge runs of a shape that has
      // a hole or an inside corner change.
      //
      // WHERE IT LIES. On the filled side of its ring (`edgeRunRing`), and
      // keeping its corners (`huggingOutline`): never in a hole, never across
      // an inside corner.
      //
      // THE ORDER. The move from one ring to the next is CUT when it crosses
      // a hole (buildQualityDesign, between runs). Taken in drawing order,
      // each ring began at its own first corner and stopped a stitch short of
      // it, so that move started part-way down a hole's side and crossed the
      // hole it had just sewn round: a cut per hole. Here the rings are taken
      // nearest-first, each entered at the corner the thread is nearest to
      // that it can reach without a cut (`ctx.clear`), and closed back onto
      // that corner.
      //
      // THE WAY OUT. When no ring can be reached from that corner -- a round
      // hole, whose own body is in the way of everything on its far side --
      // the thread runs on round the ring it is on, over the stitches just
      // laid, to the first corner one CAN be reached from.
      const clear = ctx.clear || (() => true);
      const trace = (ring) => ctx.huggingOutline(ring, { stitchLen: edgeStitch, hug: ctx.openTol });
      const r = [trace(edgeRunRing(outer, false, ctx.edgeInsetPx))];
      // `holes` is every ring inside the outline, and a ring inside a hole is
      // an ISLAND: filled ground again (even-odd), so its filled side is its
      // own inside. (Third audit: a bullseye's island had its run in the moat.)
      const isHole = (hh) => holes.filter((other) => other !== hh && pointInPoly(hh[0], other)).length % 2 === 0;
      const left = holes.map((hh) => edgeRunRing(hh, isHole(hh), ctx.edgeInsetPx));
      // the EDGE_RUN_TRIES corners of the rings still to sew that are nearest
      // to p, nearest first (kept by insertion: with 2,000 holes, sorting
      // every corner for every ring was most of the design's time)
      const nearestTo = (p) => {
        const best = [];
        const before = (a, b) => a.d - b.d || a.ri - b.ri || a.vi - b.vi;
        left.forEach((ring, ri) => ring.forEach((v, vi) => {
          const c = { ri, vi, d: Math.hypot(v.x - p.x, v.y - p.y) };
          if (best.length === EDGE_RUN_TRIES && before(c, best[best.length - 1]) >= 0) return;
          let k = best.length;
          while (k > 0 && before(c, best[k - 1]) < 0) k--;
          best.splice(k, 0, c);
          if (best.length > EDGE_RUN_TRIES) best.pop();
        }));
        return best;
      };
      const reachFrom = (p, cands) => cands.find((c) => clear(p, left[c.ri][c.vi]));
      // from ring[0] to ring[to] the shorter way round, sewn as the ring itself is
      const along = (ring, to) => {
        const n = ring.length;
        const path = to <= n - to ? ring.slice(0, to + 1) : [ring[0]].concat(ring.slice(to).reverse());
        return ctx.huggingOutline(path, { stitchLen: edgeStitch, hug: ctx.openTol, open: true }).slice(1);
      };
      let cur = r[0][r[0].length - 1], on = null;   // `on`: the hole ring the thread is on, from its entry corner
      while (left.length) {
        const cands = nearestTo(cur);
        let pick = reachFrom(cur, cands);
        if (!pick && on) {
          const n = on.length, stride = Math.max(1, Math.ceil(n / EDGE_RUN_EXITS));
          for (let k = stride; k <= n / 2 && !pick; k += stride) {
            for (const to of (k === n - k ? [k] : [k, n - k])) {
              const hit = reachFrom(on[to], nearestTo(on[to]));
              if (!hit) continue;
              r[r.length - 1].push(...along(on, to));
              pick = hit;
              break;
            }
          }
        }
        if (!pick) pick = cands[0];
        const ring = left.splice(pick.ri, 1)[0];
        const turned = ring.slice(pick.vi).concat(ring.slice(0, pick.vi));
        r.push(trace(turned));
        cur = turned[0];
        on = turned;
      }
      return r;
    }
    // With `columns`, a tatami pass is told where the thread is (`from`: the
    // end of the run before it) so that it starts from a corner the thread can
    // float to uncut, instead of always from the top left.
    const entry = (from) => (ctx.columns ? { columns: true, openTol: ctx.openTol, ground: ctx.ground || undefined, from: from || undefined, clear: ctx.clear || undefined } : {});
    function zigzag(from) {
      return [ctx.tatamiFill(rings, Object.assign({ rowSpacing: zigRow, angleDeg: fillAngle + 90, maxStitch, markConnectors: true }, entry(from)))];
    }
    function lattice(angleOff, from) {
      return [ctx.tatamiFill(rings, Object.assign({ rowSpacing: latticeRow, angleDeg: fillAngle + angleOff, maxStitch, markConnectors: true }, entry(from)))];
    }
    const then = (runs, next) => runs.concat(next(endOfRuns(runs)));
    // Single running stitch along the shape's PCA-major axis, clipped to the
    // interior (longest contiguous inside segment through the centroid).
    function centerRun() {
      const c = centroid(outer);
      const ang = ctx.pcaAngleDeg(rings) * Math.PI / 180;
      const dx = Math.cos(ang), dy = Math.sin(ang);
      let ext = 0;
      for (const q of outer) { const L = Math.hypot(q.x - c.x, q.y - c.y); if (L > ext) ext = L; }
      ext *= 1.1;
      const step = Math.max(2, edgeStitch);
      let best = [], cur = [];
      for (let t = -ext; t <= ext + 1e-9; t += step) {
        const p = { x: c.x + dx * t, y: c.y + dy * t };
        const inside = pointInPoly(p, outer) && !holes.some((hh) => pointInPoly(p, hh));
        if (inside) cur.push(p);
        else { if (cur.length > best.length) best = cur; cur = []; }
      }
      if (cur.length > best.length) best = cur;
      return best.length >= 2 ? [best] : [];
    }

    switch (style) {
      case "edge_run": return edgeRun();
      case "center_run": return centerRun();
      case "zigzag": return zigzag(null);
      case "edge_zigzag": return then(edgeRun(), zigzag);
      case "edge_lattice": return then(edgeRun(), (from) => lattice(90, from));
      case "double_lattice": return then(then(edgeRun(), (from) => lattice(45, from)), (from) => lattice(-45, from));
      default: return then(edgeRun(), (from) => lattice(90, from));
    }
  }

  // Where the thread is after `runs`: the last point of the last one that has any.
  function endOfRuns(runs) {
    for (let i = runs.length - 1; i >= 0; i--) if (runs[i] && runs[i].length) return runs[i][runs[i].length - 1];
    return null;
  }

  function pointInPoly(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i].x, yi = poly[i].y, xj = poly[j].x, yj = poly[j].y;
      if ((yi > pt.y) !== (yj > pt.y) && pt.x < (xj - xi) * (pt.y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  // Do the segments ab and cd meet: cross, touch, or lie along one another?
  function segmentsMeet(a, b, c, d) {
    const side = (p, q, r) => (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
    const within = (p, q, r) => Math.min(p.x, q.x) <= r.x && r.x <= Math.max(p.x, q.x) && Math.min(p.y, q.y) <= r.y && r.y <= Math.max(p.y, q.y);
    const d1 = side(c, d, a), d2 = side(c, d, b), d3 = side(a, b, c), d4 = side(a, b, d);
    if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return true;
    return (d1 === 0 && within(c, d, a)) || (d2 === 0 && within(c, d, b)) || (d3 === 0 && within(a, b, c)) || (d4 === 0 && within(a, b, d));
  }
  function ringBox(ring) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const q of ring) { if (q.x < x0) x0 = q.x; if (q.x > x1) x1 = q.x; if (q.y < y0) y0 = q.y; if (q.y > y1) y1 = q.y; }
    return { x0, y0, x1, y1 };
  }
  // How ring a lies against ring b: wholly "inside" it, "around" it, "apart"
  // from it, or the two "meet" (an edge of one crosses or touches an edge of
  // the other). `boxA`, `boxB`: their ringBox. Two rings can only meet inside
  // the box both reach into, so rings nowhere near each other -- the holes of
  // a badge -- cost one comparison, and only the edges that enter that box
  // are tried against each other.
  function ringsLie(a, b, boxA, boxB) {
    const x0 = Math.max(boxA.x0, boxB.x0), y0 = Math.max(boxA.y0, boxB.y0), x1 = Math.min(boxA.x1, boxB.x1), y1 = Math.min(boxA.y1, boxB.y1);
    if (x0 > x1 || y0 > y1) return "apart";
    const entering = (ring) => {
      const edges = [];
      for (let i = 0; i < ring.length; i++) {
        const p = ring[i], q = ring[(i + 1) % ring.length];
        if (Math.max(p.x, q.x) >= x0 && Math.min(p.x, q.x) <= x1 && Math.max(p.y, q.y) >= y0 && Math.min(p.y, q.y) <= y1) edges.push([p, q]);
      }
      return edges;
    };
    const ea = entering(a), eb = ea.length ? entering(b) : [];
    for (const [p, q] of ea) for (const [u, v] of eb) if (segmentsMeet(p, q, u, v)) return "meet";
    if (pointInPoly(a[0], b)) return "inside";
    return pointInPoly(b[0], a) ? "around" : "apart";
  }
  // Which rings of a shape's `holes` are ISLANDS. `holes` carries every ring
  // inside the outline, and the fill is even-odd: a ring inside a hole is
  // filled ground again, and a ring inside that is a hole again. So a ring
  // wholly inside an ODD number of the others is an island, and one inside an
  // even number (none, as a rule) is a hole. Rings that meet are not inside
  // one another: two cut-outs that overlap are two holes, as they always were.
  // -> one true/false per ring. (`groupRingsIntoShapes` hands a bullseye over
  // as the outline plus [hole, island]; so may any direct caller.)
  //
  // The `fillColumns` edge run (underlayRuns) asks its own, older question, of
  // one corner of the ring. The two agree on every ring that is wholly inside
  // another, and it is left as it is so that nothing it sews moves.
  function islandsAmong(holes) {
    const depth = holes.map(() => 0);
    if (holes.length > 1) {
      const boxes = holes.map(ringBox);
      for (let i = 0; i < holes.length; i++) {
        for (let j = i + 1; j < holes.length; j++) {
          const lie = ringsLie(holes[i], holes[j], boxes[i], boxes[j]);
          if (lie === "inside") depth[i]++;
          else if (lie === "around") depth[j]++;
        }
      }
    }
    return depth.map((n) => n % 2 === 1);
  }

  // Group a flat list of rings (e.g. glyph contours) into shapes with holes:
  // a ring whose centroid lies inside a larger ring becomes that ring's hole.
  // One level of grouping: EVERY ring inside an outline lands in its `holes`,
  // a ring inside a counter included (an island; `islandsAmong` above is how
  // buildQualityDesign tells the two apart).
  function groupRingsIntoShapes(rings, minArea) {
    const items = rings
      .filter((p) => p && p.length >= 4)
      .map((p) => ({ ring: p, area: polyArea(p) }))
      .filter((it) => it.area > (minArea || 0));
    items.sort((a, b) => b.area - a.area);
    const shapes = [];
    for (const it of items) {
      const c = centroid(it.ring);
      let parent = null;
      for (const s of shapes) if (s._area > it.area && pointInPoly(c, s.outer)) { parent = s; break; }
      if (parent) parent.holes.push(it.ring);
      else shapes.push({ outer: it.ring, holes: [], _area: it.area });
    }
    return shapes.map((s) => ({ outer: s.outer, holes: s.holes }));
  }

  // colorRegions: [{rgb:[r,g,b], polygons:[[{x,y}...]...]}] in PIXEL coords.
  // opts: { garment, pxPerMm, fillRowMm, satinSpacingMm, maxStitchMm, satinMaxWidthMm, underlay, pullCompMm, perRegionAngle, darkOnTop, angleOverrides, fillColumns, fillStagger }
  // (buildLetteringDesign additionally takes `splitSatin` and
  // `wideColumnFill` — the two wide-column answers, both default off; see
  // satinfont.js's constant block.)
  //   `densityMm` (legacy, pre-2026-09-04) is one number for BOTH fillRowMm
  //   and satinSpacingMm and is still honoured exactly as it was — see the
  //   two spacings just below for the split and the defaults.
  //
  // Stitch angle (Phase 3): by DEFAULT each fill SHAPE gets its OWN PCA angle
  // from its own rings (outer+holes) — long thin fills align to their length,
  // adjacent elements read separately. A fixed angle can be forced per COLOR two
  // ways (both keyed to the ORIGINAL caller region order, before the internal
  // light→dark sort): set `region.angleOverride` (number degrees, or null=auto)
  // on the input region, OR pass `opts.angleOverrides` as a map/array from the
  // original region index → degrees. region.angleOverride wins when both given.
  // When an override is present, ALL that region's shapes (fill + derived
  // underlay) use it; otherwise per-shape auto. `perRegionAngle:false` disables
  // auto entirely (fixed 45°).
  //
  // Manual stitch-type override (manual digitizing mode, additive): set
  // `shape.tierOverride` to "satin" or "fill" to force that shape's stitch
  // type outright, bypassing both the satinMaxWidthMm threshold and the
  // branch-guard geometry check below (see the `tierOv` block near
  // `thin`). Absent (every existing caller) is a no-op.
  function buildQualityDesign(colorRegions, opts) {
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 8;
    // Fabric preset (from getFabric) drives pull comp, density, trim, underlay.
    // When absent, every derived value falls back to the pre-fabric defaults and
    // the underlay code path stays byte-identical to before (see below).
    const fabric = o.fabric || null;
    const densityAdjust = (fabric && fabric.densityAdjust) ? fabric.densityAdjust : 1;
    // Two spacings, two physical choices (2026-09-04). `fillRowMm` is the
    // tatami row pitch (FILL_ROW_MM above), `satinSpacingMm` the satin cross
    // pitch (SATIN_SPACING_MM). `densityMm` is the pre-split option that drove
    // BOTH: a caller still passing it gets exactly what it always got — fill
    // AND satin at that number — so every snapshot pinned on an explicit
    // densityMm stays byte-identical, and the split names win where both are
    // given. Only a caller that passes neither picks up the engine defaults,
    // which is what moved: the fill default 0.45 -> 0.15; satin 0.4 as before.
    // Both scale by the fabric's densityAdjust, as the Python engine scales
    // both (stage7_sequence.py's row_mm and satin_spacing_mm).
    const fillRowMm = (o.fillRowMm || o.densityMm || FILL_ROW_MM) * densityAdjust;
    const satinSpacingMm = (o.satinSpacingMm || o.densityMm || SATIN_SPACING_MM) * densityAdjust;
    const maxStitchMm = o.maxStitchMm || 4;
    const satinMaxWidthMm = o.satinMaxWidthMm || 3.0;
    const pullCompMm = (fabric && fabric.pullCompMm != null) ? fabric.pullCompMm
      : (o.pullCompMm == null ? 0.2 : o.pullCompMm);
    const useUnderlay = o.underlay !== false;
    const perRegionAngle = o.perRegionAngle !== false;
    const garment = o.garment || { widthIn: 5, heightIn: 2.25 };

    // filter empty; accept {shapes:[{outer,holes}]} or legacy {polygons:[ring]}
    const regions = colorRegions.filter((r) => r && ((r.shapes && r.shapes.length) || (r.polygons && r.polygons.length)));
    for (const r of regions) if (!r.polygons) r.polygons = r.shapes.map((s) => s.outer);
    if (!regions.length) return { stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, shapeOutlines: [], fit: null, _debug: { nSatin: 0, nFill: 0, nTrims: 0 } };

    // Tag each region with its ORIGINAL caller index before we reorder, so
    // opts.angleOverrides (keyed by original index) survives the sort below.
    regions.forEach((r, i) => { r._origIdx = i; });
    // sequence: light colors first, dark last (dark sits on top) unless overridden
    if (o.darkOnTop !== false) regions.sort((a, b) => (b.rgb[0] + b.rgb[1] + b.rgb[2]) - (a.rgb[0] + a.rgb[1] + a.rgb[2]));

    // bbox in px across all polygons
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const r of regions) for (const p of r.polygons) for (const q of p) { if (q.x < minX) minX = q.x; if (q.x > maxX) maxX = q.x; if (q.y < minY) minY = q.y; if (q.y > maxY) maxY = q.y; }
    const bboxWmm = (maxX - minX) / pxPerMm, bboxHmm = (maxY - minY) / pxPerMm;
    const fit = garments.fitScale(bboxWmm || 1, bboxHmm || 1, garment);
    let sc = (fit.scale > 0 && isFinite(fit.scale)) ? fit.scale : 1;
    let designWmm = fit.targetWmm, designHmm = fit.targetHmm;
    // Explicit width override (Slice 3): replaces the auto garment fit. Clamp the
    // requested width into [1, hoopWmm], then ALSO clamp so height still fits the
    // hoop — same two-constraint min() fitScale itself uses, just seeded from the
    // requested width instead of the natural bbox. Reported widthMM/heightMM
    // become the actual design dims (bbox*sc), not the (unused) fit target.
    if (typeof o.targetWidthMm === "number" && isFinite(o.targetWidthMm) && o.targetWidthMm > 0) {
      const bw = bboxWmm || 1, bh = bboxHmm || 1;
      const hoopWmm = units.inToMm(garment.widthIn), hoopHmm = units.inToMm(garment.heightIn);
      const clampedTargetWmm = Math.min(Math.max(o.targetWidthMm, 1), hoopWmm);
      sc = Math.min(clampedTargetWmm / bw, hoopHmm / bh);
      designWmm = bw * sc;
      designHmm = bh * sc;
    }
    const scalePxToDst = sc * (1 / pxPerMm) * units.DST_UNITS_PER_MM;
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    // Explicit placement offset (Slice 3): applied AFTER the center transform, in
    // DST space — +x right, +y up (DST convention, already matches T()'s y-flip).
    const offXu = Math.round((o.offsetXMm || 0) * units.DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * units.DST_UNITS_PER_MM);
    const T = (q) => ({ x: Math.round((q.x - cx) * scalePxToDst) + offXu, y: Math.round((cy - q.y) * scalePxToDst) + offYu });

    const mmPerPxFinal = scalePxToDst / units.DST_UNITS_PER_MM; // final mm per source px
    const pxPerFinalMm = 1 / mmPerPxFinal;                       // source px per final mm
    // Per-shape OUTLINES (2026-09-29 spec §3): where each input shape lands,
    // in FIELD mm — the stitches' own space (+y up, offsets applied), i.e.
    // T(q) without the integer rounding, so the Studio can draw a
    // hand-drawn or preset shape over its stitching and hit-test it with the
    // same `toCanvas` it draws the design with. INPUT order, not sew order:
    // the caller's ids are what a click has to map back to, and the sort
    // above is this function's private business. Bookkeeping only — no
    // stitch, order or count changes with it (same posture as `spans`).
    const shapeOutlines = [];
    const outlineByRing = new Map(); // outer ring -> its entry, for dropped-marking below
    {
      const toFieldMm = (q) => [
        ((q.x - cx) * scalePxToDst + offXu) / units.DST_UNITS_PER_MM,
        ((cy - q.y) * scalePxToDst + offYu) / units.DST_UNITS_PER_MM,
      ];
      for (const r of regions.slice().sort((a, b) => a._origIdx - b._origIdx)) {
        const raw = r.shapes || r.polygons.map((p) => ({ outer: p, holes: [] }));
        for (const s of raw) {
          if (!s) continue;
          const outer = Array.isArray(s.outer) ? s.outer : [];
          const entry = {
            id: s.id == null ? "" : String(s.id),
            points: outer.map(toFieldMm),
            holes: (s.holes || []).filter((h) => h && h.length).map((h) => h.map(toFieldMm)),
            dropped: outer.length < 3,
          };
          shapeOutlines.push(entry);
          if (outer.length) outlineByRing.set(outer, entry);
        }
      }
    }
    // The fit itself, for callers that must map FIELD mm back to source px —
    // the Studio's node editor for hand-drawn shapes (2026-09-29 field-node-
    // edit spec §2). Same numbers T() uses; offsets are the ones APPLIED
    // (rounded to a DST unit), not the request. Additive bookkeeping.
    const fitOut = { // not `fit`: that name is the garment fitScale result above
      cxPx: cx, cyPx: cy, mmPerPx: mmPerPxFinal,
      offsetXMm: offXu / units.DST_UNITS_PER_MM, offsetYMm: offYu / units.DST_UNITS_PER_MM,
      pxPerMm,
    };
    const dropOutline = (ring) => { const e = outlineByRing.get(ring); if (e) e.dropped = true; };
    // PX_LOOP_EPS guards against a literal zero/degenerate loop step (rowPx=0
    // would spin fillmod.tatamiFill's `for (y=minY; y<=maxY; y+=rowSpacing)`
    // forever) -- NOT a functional minimum density. These four used to be
    // floored at 0.8/3/4/3 px, which LOOKS like a sane minimum but silently
    // broke resize: pxPerFinalMm shrinks as the design is scaled UP (bigger
    // targetWidthMm -> larger sc -> pxPerFinalMm=pxPerMm/sc smaller), so past
    // roughly 4-10x the design's native size the mm*pxPerFinalMm product fell
    // below those floors and got overridden -- the row/stitch spacing then
    // scaled with sc instead of staying fixed at the requested mm value,
    // i.e. exactly "spacing doesn't re-digitize, gaps open up when enlarged"
    // (Kent's report). A floor two orders of magnitude smaller still prevents
    // the degenerate case at any realistic resize while never engaging early.
    const PX_LOOP_EPS = 0.02;
    const rowPx = Math.max(PX_LOOP_EPS, fillRowMm * pxPerFinalMm);
    const maxPx = Math.max(PX_LOOP_EPS, maxStitchMm * pxPerFinalMm);
    const underlayStitchPx = Math.max(PX_LOOP_EPS, 2.0 * pxPerFinalMm);
    const underlayRowPx = Math.max(PX_LOOP_EPS, 2.5 * pxPerFinalMm);
    const pullCompPx = pullCompMm * pxPerFinalMm; // fill pull-comp offset (px)
    // Shared context for named underlay styles (used only in fabric mode).
    // `fillColumns` (default off): every tatami pass of a FILL shape whose
    // rows fork -- the fill and the underlay under it -- is sewn column by
    // column, so no thread is carried across a hole or a notch (fill.js,
    // `opts.columns`). Off, nothing reads it and every stitch is unchanged.
    // A satin shape is untouched either way: its own moves are a separate
    // call (`columns` is set per shape, where `thin` is known).
    //
    // Where thread may lie is ONE thing for every pass of a shape: THE GROUND
    // THE FILL COVERS (`fillRingsOf`), measured -- and how deep past it a move
    // may go is one number, the FILL's row pitch (`rowPx`), not each pass's
    // own. Two earlier rules, each found wanting by an audit:
    //  - "under one pitch", with the pass's own pitch. An underlay's rows are
    //    2 to 2.5 mm apart, and that was a stitch through the hole.
    //  - "the drawn outline, plus the pull compensation, since the fill covers
    //    that far". A hole thinner than twice the compensation is sewn AS
    //    DRAWN (shrunk, it folds through itself), so there the fill covers no
    //    further at all, and the underlay went straight across a 1 mm slot.
    const fillColumns = !!o.fillColumns;
    // `fillStagger` (default off): a shape's COVER fill puts the needle holes
    // between each row's ends on one grid, shifted row by row, where each row
    // now cuts itself evenly and the holes line up from row to row (fill.js,
    // "ROW STAGGER"). The underlay passes are left as they are: their rows are
    // 2 mm and more apart and lie under the cover, and the Python engine does
    // not stagger them either (`_underlay_paths`, staggers=1). Off, nothing
    // reads it and every stitch is unchanged.
    const staggerOpts = o.fillStagger ? { stagger: FILL_STAGGERS, minStitch: MIN_STITCH_MM * pxPerFinalMm, splitTol: SPLIT_TOLERANCE_MM * pxPerFinalMm } : null;
    // The rings a FILL is sewn to: the shape's own, or under a fabric preset
    // the pull-compensated ones (grow the outer, shrink the holes), so it sews
    // to true size on stretchy cloth. No-fabric fills stay unoffset.
    // `islands`: which of `holes` are islands (islandsAmong). An island is
    // filled ground, so it GROWS, as the outline does. Shrunk with the holes,
    // its fill was sewn small by the compensation on every side, and the
    // underlay, sewn to the ring as drawn, showed round it.
    function fillRingsOf(poly, holes, rings, islands) {
      if (!(fabric && pullCompPx > 0)) return rings;
      // Outer outset never inverts (growing). Hole insets can: a hole
      // thinner than ~2*pullCompPx collapses and flips winding (walls
      // cross), yielding a self-intersecting boundary the miter clamp
      // can't prevent. Per hole: if the inset flips signed-area sign vs
      // the original (winding inverted) or its area is ~0 (collapsed),
      // discard the offset and keep the ORIGINAL hole ring.
      const moved = holes.map((hh, i) => {
        if (islands[i]) return offsetRing(hh, pullCompPx, true);
        const off = offsetRing(hh, pullCompPx, false);
        const a0 = signedArea(hh), a1 = signedArea(off);
        if (Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6) return hh;
        return off;
      });
      // An island grown and the wall of the hole round it shrunk move TOWARD
      // each other, and so do two islands in one hole. Where the ground
      // between them is not more than twice the compensation the two rings
      // cross, and crossed rings are a fill sewn where neither was drawn. So,
      // as with the thin hole above, a ring that cannot be moved is sewn AS
      // DRAWN: an island that, grown, no longer lies against every other ring
      // the way it was drawn; and then any hole that, shrunk, still meets
      // such an island as drawn. (Putting a ring back never brings two
      // together: an island put back is smaller, a hole put back is larger.)
      if (islands.some(Boolean)) {
        const all = holes.map((_, i) => i), drawnBox = holes.map(ringBox), movedBox = moved.map(ringBox);
        // the rings that ring i, where it has been moved to, no longer lies against as it was drawn
        const upset = (i) => all.filter((j) => j !== i && ringsLie(moved[i], moved[j], movedBox[i], movedBox[j]) !== ringsLie(holes[i], holes[j], drawnBox[i], drawnBox[j]));
        const putBack = (i) => { moved[i] = holes[i]; movedBox[i] = drawnBox[i]; };
        const stuck = all.filter((i) => islands[i] && upset(i).length);
        stuck.forEach(putBack);
        for (const i of stuck) upset(i).forEach(putBack);
      }
      return [offsetRing(poly, pullCompPx, true)].concat(moved);
    }
    const edgeInsetPx = EDGE_RUN_INSET_MM * pxPerFinalMm;   // with `fillColumns`
    const underlayCtxBase = {
      pxPerFinalMm, maxStitch: maxPx, underlayStitchPx, underlayRowPx,
      runningOutline: fillmod.runningOutline, tatamiFill: fillmod.tatamiFill,
      huggingOutline: fillmod.huggingOutline, edgeInsetPx,
      insetRing, pcaAngleDeg,
    };

    // Trim policy: trim before any travel longer than trimAtMm (FINAL mm).
    const trimAtMm = (fabric && fabric.trimAtMm != null) ? fabric.trimAtMm
      : (o.trimAtMm == null ? 3.0 : o.trimAtMm);
    const trimAtPx = trimAtMm * pxPerFinalMm; // threshold in source px
    // Cap garments sew crown-distortion-safe: center-out per color block.
    const capMode = garment && (garment.id === "hat_front" || garment.id === "beanie");

    const stitches = [];
    const colors = [];
    let first = true, nSatin = 0, nFill = 0, nTrims = 0, nCenterOut = 0;
    // Large fills sew center-out (rows interleaved from the vertical center) so
    // fabric push radiates symmetrically. "Large" = both final-mm bbox dims over
    // this threshold; applies to the TOP fill only (underlay stays sequential).
    const centerOutMinMm = 15;
    const minimizeColorChanges = !!o.minimizeColorChanges;
    let lastPx = { x: cx, y: cy }; // last emitted point in px; origin = design center (DST 0,0)
    let started = false;           // no trim before the very first stitch of the design
    let justChangedColor = false;  // color change already cut the thread; skip the next per-shape travel-trim

    function pushRun(pts) {
      if (!pts || !pts.length) return;
      const f = T(pts[0]);
      stitches.push({ x: f.x, y: f.y, type: "jump" });
      for (const q of pts) {
        const d = T(q);
        // A point tagged q.trim (the center-out sweep-to-sweep reposition) emits
        // a trim so the long float is cut, not left as a bare needle-up jump.
        if (q.trim) { stitches.push({ x: d.x, y: d.y, type: "trim" }); nTrims++; }
        else stitches.push({ x: d.x, y: d.y, type: q.travel ? "jump" : "stitch" });
      }
      lastPx = pts[pts.length - 1];
    }
    // RUN SPANS (`design.runs`) — what each stitch IS, for the renderer.
    //
    // The design model downstream is a flat {x,y,type} stream in which satin,
    // tatami, underlay and a finishing outline are indistinguishable, so the
    // browser canvas drew them all the same way (Kent, 2026-09-15). A span is
    // recorded per RUN, at the moment it is emitted, from the classification
    // this function has already made — `thin` is the satin-vs-fill decision,
    // and the underlay/outline runs are named where they are built. It is
    // bookkeeping ONLY: no stitch, order or count changes with it, which is
    // what keeps every snapshot in the engine suite byte-identical.
    //
    // `role` is always "" here. This lane has no border concept — the borders
    // Kent cannot see come off the Python digitizer — and an outline run is
    // tagged for what it is, a running stitch, rather than promoted to a
    // border it was never asked to be.
    const spans = [];
    function pushSpan(i0, kind, shapeId) {
      if (!kind || stitches.length <= i0) return;
      spans.push({ i0, i1: stitches.length - 1, kind, shape: shapeId == null ? "" : String(shapeId),
                   role: "", block: Math.max(0, colors.length - 1) });
    }
    // Emit a trim command at the current (last) position — zero-travel; the
    // following jump carries the machine to the next shape.
    function emitTrimAtLast() {
      const tp = T(lastPx);
      stitches.push({ x: tp.x, y: tp.y, type: "trim" });
      nTrims++;
    }

    // Order a color block's shapes: cap center-out (unchanged, takes precedence),
    // else background-first — the LARGEST-area shape sews first (it's the
    // background), then greedy nearest-neighbor from there for the rest. Only the
    // FIRST pick changed from pure nearest-neighbor-from-previous-position; the
    // remaining picks still chain by centroid proximity for short travel.
    function orderShapes(list, startPx) {
      if (list.length <= 1) return list.slice();
      const cents = list.map((s) => centroid(s.outer));
      if (capMode) {
        const idx = list.map((_, i) => i);
        idx.sort((a, b) => {
          const da = Math.abs(cents[a].x - cx), db = Math.abs(cents[b].x - cx);
          if (da !== db) return da - db;          // |x - center| ascending
          return cents[b].y - cents[a].y;         // tiebreak y DESCENDING (bottom-up)
        });
        return idx.map((i) => list[i]);
      }
      const remaining = list.map((s, i) => ({ s, c: cents[i], a: polyArea(s.outer) }));
      const out = [];
      // Background-first: seed the walk at the LARGEST-area shape rather than the
      // one nearest the previous position, so wide background regions sew before
      // detail sitting on top of them. Deterministic (input-order independent):
      // area DESC, then nearest to startPx, then centroid x, then y.
      let seed = 0;
      for (let i = 1; i < remaining.length; i++) {
        const ri = remaining[i], rb = remaining[seed];
        if (ri.a !== rb.a) { if (ri.a > rb.a) seed = i; continue; }
        const di = Math.hypot(ri.c.x - startPx.x, ri.c.y - startPx.y);
        const db = Math.hypot(rb.c.x - startPx.x, rb.c.y - startPx.y);
        if (di !== db) { if (di < db) seed = i; continue; }
        if (ri.c.x !== rb.c.x) { if (ri.c.x < rb.c.x) seed = i; continue; }
        if (ri.c.y < rb.c.y) seed = i;
      }
      const pick0 = remaining.splice(seed, 1)[0];
      out.push(pick0.s);
      let cur = { x: pick0.c.x, y: pick0.c.y };
      while (remaining.length) {
        let best = 0, bd = Infinity;
        for (let i = 0; i < remaining.length; i++) {
          const d = Math.hypot(remaining[i].c.x - cur.x, remaining[i].c.y - cur.y);
          if (d < bd) { bd = d; best = i; }
        }
        const pick = remaining.splice(best, 1)[0];
        out.push(pick.s);
        cur = pick.c;
      }
      return out;
    }

    let prevRgb = null;
    for (const r of regions) {
      // minimizeColorChanges: when the current region's EXACT rgb matches the
      // previous emitted region's, keep sewing on the same thread — no color
      // change, no new color record. Same-rgb regions are contiguous after the
      // light→dark sort (identical brightness), so a same-as-previous test
      // groups them all. NOTE: with the flatten pipeline every palette color is
      // unique, so this is a no-op there; it only bites on repeated-color inputs
      // (e.g. future SVG import). Default (false) → strict light→dark, unchanged.
      const sameThread = minimizeColorChanges && prevRgb &&
        r.rgb[0] === prevRgb[0] && r.rgb[1] === prevRgb[1] && r.rgb[2] === prevRgb[2];
      if (!first && !sameThread) {
        // Always trim before a color change (thread must be cut), then change.
        emitTrimAtLast();
        const last = stitches[stitches.length - 1] || { x: 0, y: 0 };
        stitches.push({ x: last.x, y: last.y, type: "color" });
        justChangedColor = true; // thread already cut; don't double-trim the first shape of this block
      }
      first = false;
      prevRgb = r.rgb;
      if (!sameThread) colors.push({ r: r.rgb[0], g: r.rgb[1], b: r.rgb[2], name: "Color " + (colors.length + 1) });
      // shapes: [{outer, holes}] (hole-aware) — or bare polygons for back-compat
      const shapesRaw = r.shapes || r.polygons.map((p) => ({ outer: p, holes: [] }));
      // Minimum vertex count for a real closed polygon is 3 (a triangle), not
      // 4 — every other module downstream (geometry.js, satin.js) already
      // uses `< 3` as ITS reject threshold. This floor only ever mattered as
      // a defensive "not obviously garbage" check: raster-traced regions and
      // font-glyph outlines never produce exactly-3-point rings in practice,
      // so relaxing 4->3 changes nothing for Image/Text mode (whose real
      // shapes are unaffected either way) while fixing a real gap for manual
      // digitizing mode, where a plain user-drawn triangle IS exactly 3
      // points and was previously silently dropped to zero stitches here.
      const shapes0 = shapesRaw.filter((s) => s && s.outer && s.outer.length >= 3);
      // Resolve a fixed per-color angle override (degrees) if the caller set one.
      // region.angleOverride wins; else opts.angleOverrides[originalIndex]. A
      // finite number forces every shape in this color; null/absent → per-shape.
      let regionAngle = null;
      const ov = (r.angleOverride != null) ? r.angleOverride
        : (o.angleOverrides != null ? o.angleOverrides[r._origIdx] : null);
      if (ov != null && isFinite(ov)) regionAngle = ((ov % 180) + 180) % 180;
      const shapes = orderShapes(shapes0, lastPx);
      for (const shape of shapes) {
        const poly = shape.outer;
        if (!poly || poly.length < 3) { if (poly) dropOutline(poly); continue; } // see the shapes0 filter's comment above
        // Hole floor is 3 too, for the reason in the shapes0 comment above: it was missed when the outer floor was relaxed.
        const holes = (shape.holes || []).filter((hh) => hh && hh.length >= 3);
        // An island's area is ground the shape FILLS, so it is added back, not
        // taken off a second time: subtracted, three nested rings came to no
        // area at all and the whole shape was dropped. (The perimeter is every
        // ring's, island or hole.)
        const islands = islandsAmong(holes);
        const outerArea = polyArea(poly), holeArea = holes.reduce((a, hh, i) => a + (islands[i] ? -polyArea(hh) : polyArea(hh)), 0);
        const area = Math.max(0, outerArea - holeArea), perim = polyPerim(poly) + holes.reduce((a, hh) => a + polyPerim(hh), 0);
        if (area <= 0 || perim <= 0) { dropOutline(poly); continue; }
        const widthMmFinal = (2 * area / perim) * mmPerPxFinal;
        // satin only for genuinely thin SOLID strokes; ring-with-hole goes to
        // even-odd fill (satinColumn can't represent holes)
        let thin = widthMmFinal <= satinMaxWidthMm && holes.length === 0;
        // Manual stitch-type override (manual digitizing mode): a caller-set
        // shape.tierOverride ("satin"|"fill") is a human's explicit choice,
        // not a hint — it replaces BOTH the width threshold above and the
        // branch-guard geometry check below outright, so a manually-drawn
        // branched shape the user insists on satin-ing isn't silently routed
        // to fill. Holes still force fill either way (satinColumn can't
        // represent a hole — same rule the auto path already enforces).
        // Absent/unrecognized value is a no-op: falls through to today's
        // auto classification unchanged, so every existing caller (Image/
        // Text mode, which never set this field) is byte-identical.
        const tierOv = shape.tierOverride;
        if (tierOv === "satin" || tierOv === "fill") {
          thin = tierOv === "satin" && holes.length === 0;
        }
        // branch guard: a clean column splits into two side chains of similar
        // length; branched shapes (most letters, Y/T/E forms) don't — satin
        // would zigzag chaotically across them, so route those to fill.
        else if (thin && satinmod.farthestBoundaryPair) {
          try {
            const [bi, bj] = satinmod.farthestBoundaryPair(poly);
            const [ca, cb] = satinmod.splitBoundary(poly, bi, bj);
            const la = satinmod.chainLength(ca), lb = satinmod.chainLength(cb);
            const ratio = Math.max(la, lb) / Math.max(1e-6, Math.min(la, lb));
            if (ratio > 1.5) thin = false;
            // rung containment: in a true column every cross-stitch midpoint
            // lies inside the shape; on branched shapes (T, M, Y) the rungs
            // shortcut across concavities and land outside — reject those.
            if (thin) {
              const K = 9;
              const pa = satinmod.resampleChain(ca, K);
              const pb = satinmod.resampleChain(cb, K);
              let outside = 0;
              for (let k = 1; k < K - 1; k++) {
                const q = pb[K - 1 - k];
                const mid = { x: (pa[k].x + q.x) / 2, y: (pa[k].y + q.y) / 2 };
                if (!pointInPoly(mid, poly)) outside++;
              }
              if (outside > 0) thin = false;
            }
          } catch (e) { thin = false; }
        }
        const rings = [poly].concat(holes);
        // Per-SHAPE stitch angle: a fixed color override wins; otherwise this
        // shape's OWN PCA axis (outer+holes) so each element's stitches follow
        // its own length/axis. perRegionAngle:false disables auto (fixed 45°).
        // Precedence: per-shape override (e.g. per-letter) > region override >
        // per-shape auto PCA > fixed 45°.
        const shapeOv = (shape.angleOverride != null && isFinite(shape.angleOverride))
          ? (((shape.angleOverride % 180) + 180) % 180) : null;
        const angle = (shapeOv != null) ? shapeOv
          : (regionAngle != null) ? regionAngle
          : (perRegionAngle ? pcaAngleDeg(rings) : 45);
        // Satin slant (italic-style lean off perpendicular): per-shape wins, else
        // the design-wide default. 0 = perpendicular.
        const slantDeg = (shape.slantDeg != null && isFinite(shape.slantDeg))
          ? shape.slantDeg : (o.satinSlantDeg || 0);

        // Build this shape's runs in sew order; trim (if needed) is decided once
        // per shape so we never trim between a shape's own underlay and top.
        //
        // `runKinds` rides alongside `runs`, one entry per entry, pushed on the
        // same line so a throw inside any of the best-effort try blocks can
        // never leave the two out of step. It exists so the emitted spans
        // (`design.runs`, see pushSpan) say what each stitch IS — this lane
        // already KNOWS, since `thin` is the satin-vs-fill decision it just
        // made and the underlay/outline runs are named where they are built.
        // Nothing here is re-derived or guessed.
        const runs = [];
        const runKinds = [];
        // With `fillColumns`, on a FILL shape: would a float from a to b be
        // left uncut? Asked while the underlay is still being ordered, so it
        // needs the ground the fill WILL cover, before the fill is built.
        // `cover` is that ground: the true rings, or the pull-compensated ones
        // the fill is sewn to. `mustCut` is asked of every float of the shape.
        let clearFloat = null, cover = null, mustCut = null;
        if (fillColumns && !thin) {
          cover = rings;
          try { cover = fillRingsOf(poly, holes, rings, islands); } catch (e) { cover = rings; }
          const crosses = fillmod.openGroundTest(cover);
          mustCut = (a, b) => crosses(a, b, rowPx, 0, maxPx);
          clearFloat = (a, b) => !mustCut(a, b);
        }
        // What a tatami pass of this shape is told about where the thread is:
        // the end of the run before it. Nothing, without the flag.
        const entryOf = (before) => {
          const from = clearFloat ? endOfRuns(before) : null;
          return from ? { from, clear: clearFloat } : {};
        };
        if (useUnderlay) {
          if (fabric) {
            // Fabric mode: named underlay style per shape type.
            try {
              const style = thin ? (fabric.satinUnderlay || "center_run") : (fabric.fillUnderlay || "edge_lattice");
              const uctx = Object.assign({ fillAngle: angle, columns: fillColumns && !thin, openTol: rowPx, ground: cover, clear: clearFloat }, underlayCtxBase);
              for (const run of underlayRuns(shape, style, uctx)) if (run && run.length) { runs.push(run); runKinds.push("underlay"); }
            } catch (e) { /* underlay best-effort */ }
          } else {
            // No-fabric path: byte-identical to pre-Phase-2 behavior. (With
            // `fillColumns`, a fill shape's edge run lies where
            // underlayRuns' does: inside the fill, corners kept.)
            try {
              if (cover && (holes.length || !isConvexRing(poly))) {
                runs.push(fillmod.huggingOutline(edgeRunRing(poly, false, edgeInsetPx), { stitchLen: underlayStitchPx, hug: rowPx })); runKinds.push("underlay");
              } else {
                const inset = insetRing(poly, Math.min(2, 0.6 * pxPerFinalMm));
                runs.push(fillmod.runningOutline(inset, { stitchLen: underlayStitchPx })); runKinds.push("underlay");
              }
              // (no `ground` here: with no fabric the fill is sewn to these same rings)
              if (!thin) { runs.push(fillmod.tatamiFill(rings, Object.assign({ rowSpacing: underlayRowPx, angleDeg: angle + 90, maxStitch: maxPx, markConnectors: true, columns: fillColumns, openTol: rowPx }, entryOf(runs)))); runKinds.push("underlay"); }
            } catch (e) { /* underlay best-effort */ }
          }
        }
        // top stitching. Fills get pull compensation via polygon offset (grow
        // outer, shrink holes) so they sew to true size on stretchy fabric; this
        // applies in fabric mode only (no-fabric fills stay unoffset). Satin
        // compensates internally through pullCompMm (unchanged). Underlay/outline
        // trace the TRUE edge and are never offset.
        let pts = [];
        try {
          if (thin) {
            // Medial-axis satin (rail-based) — clean on curves/terminals; falls
            // back to the outline-split satin internally for tiny/degenerate rings.
            const sat = satinmod.medialSatin || satinmod.satinColumn;
            pts = sat(poly, { spacingMm: satinSpacingMm, pxPerMm: pxPerFinalMm, pullCompMm, slantDeg });
            nSatin++;
          }
          else {
            const fillRings = fillRingsOf(poly, holes, rings, islands);
            // Large-fill center-out: qualify by this shape's final-mm bbox.
            let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
            for (const q of poly) { if (q.x < bx0) bx0 = q.x; if (q.x > bx1) bx1 = q.x; if (q.y < by0) by0 = q.y; if (q.y > by1) by1 = q.y; }
            const wMm = (bx1 - bx0) * mmPerPxFinal, hMm = (by1 - by0) * mmPerPxFinal;
            const largeFill = wMm > centerOutMinMm && hMm > centerOutMinMm;
            pts = fillmod.tatamiFill(fillRings, Object.assign({ rowSpacing: rowPx, angleDeg: angle, maxStitch: maxPx, markConnectors: true, centerOut: largeFill, columns: fillColumns, openTol: rowPx }, staggerOpts, entryOf(runs))); nFill++;
            if (largeFill && !pts.columnWalk) nCenterOut++;   // the column walk is not center-out
          }
        } catch (e) { pts = []; }
        runs.push(pts); runKinds.push(thin ? "satin" : "fill");
        // finishing outline: running stitch along the outer edge (and holes)
        if (o.outline) {
          try {
            const edgeLen = Math.max(0.02, 1.8 * pxPerFinalMm); // loop-safety floor only, see PX_LOOP_EPS note above
            for (const ring of rings) { runs.push(fillmod.runningOutline(ring, { stitchLen: edgeLen })); runKinds.push("run"); }
          } catch (e) { /* best-effort */ }
        }

        const nonEmpty = [], nonEmptyKinds = [];
        for (let ri = 0; ri < runs.length; ri++) {
          if (runs[ri] && runs[ri].length) { nonEmpty.push(runs[ri]); nonEmptyKinds.push(runKinds[ri]); }
        }
        if (!nonEmpty.length) { dropOutline(poly); continue; }
        const entry = nonEmpty[0][0]; // first sewn point of this shape (px)
        if (started && !justChangedColor) {
          const d = Math.hypot(entry.x - lastPx.x, entry.y - lastPx.y);
          if (d > trimAtPx) emitTrimAtLast(); // long travel → trim at last pos before jump
        }
        justChangedColor = false; // only the first shape after a color change is exempt
        // A shape is several runs, and the frame goes from the end of one to
        // the start of the next with the thread attached. Under the fill that
        // float is hidden; across a hole or a notch nothing ever covers it.
        // With `fillColumns`, on a FILL shape, that move is cut when it lays
        // thread deeper than a fill row into ground the fill does not cover,
        // or is longer than a stitch and leaves that ground at all.
        // Measured against `cover`, NOT the true outline: the fill's first
        // point sits a pull compensation outside the true corner, and against
        // the true outline a plain square read as leaving itself and went
        // from one cut to two. No slack at either end: with the flag every run
        // of a fill shape starts and ends on that ground or its rim.
        // Not covered: `o.outline`, which no caller passes, is sewn AFTER the
        // fill, so a float to it lies on top of the fill and is not cut.
        for (let ri = 0; ri < nonEmpty.length; ri++) {
          if (mustCut && ri > 0 && mustCut(lastPx, nonEmpty[ri][0])) emitTrimAtLast();
          const spanI0 = stitches.length;
          pushRun(nonEmpty[ri]);
          pushSpan(spanI0, nonEmptyKinds[ri], shape.id);
        }
        started = true;
      }
    }
    stitches.push({ x: 0, y: 0, type: "end" });
    // Lock stitches, OFF by default (`ties`, 2026-10-03): until now this
    // builder tied nothing, on any lane it serves -- manual draw, basic shapes,
    // SVG import, the flatten lane -- so every trim left two loose ends. Off,
    // the stream below is the one built above, untouched. See applyTies.
    const tied = o.ties ? applyTies(stitches, spans) : null;
    const sewn = tied ? tied.stitches : stitches;
    const stitchCount = sewn.filter((s) => s.type === "stitch").length;
    // designWmm/designHmm is the traced-polygon box this was fit to; the sewn
    // extent is what the customer gets. See designExtentMm.
    const extent = designExtentMm(sewn, designWmm, designHmm);
    return { stitches: sewn, colors, widthMM: extent.widthMM, heightMM: extent.heightMM, stitchCount, colorCount: colors.length, runs: spans, shapeOutlines, fit: fitOut, _debug: { nSatin, nFill, nTrims, nCenterOut, nTies: tied ? tied.nTies : 0 } };
  }

  // Build a Design from a PRE-DIGITIZED satin font (src/satinfont.js) instead of
  // auto-tracing. `fontData` is a parsed glyph library (tools/build-font.mjs);
  // each glyph's authored satin columns are played and laid out, then fit to the
  // garment, centered, and Y-flipped into DST units — same coordinate convention
  // and return shape as buildQualityDesign, so DST/preview/PDF just work.
  // opts = { garment, pxPerMm=8, emMm=18, rgb=[20,20,20], satinSpacingMm
  //          (legacy spelling: densityMm), pullCompMm,
  //          letterSpacingMm, fabric, trimAtMm, mirrorX=false, mirrorY=false,
  //          circleLayout (see satinfont.js layoutText) }.
  function buildLetteringDesign(fontData, text, opts) {
    const o = opts || {};
    const pxPerMm = o.pxPerMm || 8;
    const garment = o.garment || { widthIn: 5, heightIn: 2.25 };
    const fabric = o.fabric || null;
    const emMm = o.emMm || 18;
    const rgb = o.rgb || [20, 20, 20];
    // Lettering is satin only, so its one spacing is the satin cross pitch
    // (SATIN_SPACING_MM, 0.4 — unchanged by the 2026-09-03 fill ruling).
    // `satinSpacingMm` is the name since 2026-09-04; `densityMm` is the legacy
    // spelling and is honoured unchanged. There is no fill row to set here.
    const satinSpacingMm = (o.satinSpacingMm || o.densityMm || SATIN_SPACING_MM) * ((fabric && fabric.densityAdjust) ? fabric.densityAdjust : 1);
    // Bold/thin (Font editing abilities Round 1): reuses the EXISTING,
    // already-tested pullCompMm column-widening mechanism (satinplay.js's
    // emitZigzag pushes the two rails apart by pullCompMm/2 each) instead of
    // any new geometry -- pullCompMm was built for fabric-pull compensation,
    // but geometrically "push the rails apart by N mm" is exactly what a
    // bolder stroke needs too. "normal" adds 0, so it's byte-identical to
    // today. These two constants are a starting point verified against the
    // default font's tightest letterforms in this task's own steps below;
    // if a different font's tightest glyph collapses a counter at "bold",
    // shrink WEIGHT_OFFSET_MM.bold rather than adding new mechanism.
    const WEIGHT_OFFSET_MM = { thin: -0.15, normal: 0, bold: 0.3 };
    const weightPreset = (o.weightPreset && WEIGHT_OFFSET_MM[o.weightPreset] != null) ? o.weightPreset : "normal";
    // Fabric pull comp and the weight preset's widening travel SEPARATELY
    // from here on (2026-09-03, fine-lettering review item 4): emitZigzag
    // still adds them, so normal and thin are byte-identical to when they
    // were one number, but bold's share can now be held back per rail where
    // it would close a counter — satinplay's counter guard, floor
    // SATIN_MIN_CROSS_MM. `o.counterGuard === false` is measurement only.
    const pullCompMm = (fabric && fabric.pullCompMm != null) ? fabric.pullCompMm : (o.pullCompMm == null ? 0.2 : o.pullCompMm);
    const weightMm = WEIGHT_OFFSET_MM[weightPreset];
    // Tatami row pitch for the wide-column fill fallback (item 10). Only
    // reached when `wideColumnFill` is asked for; the fabric preset scales it
    // exactly the way it scales the image lane's fill row, so a pile fabric
    // sews a wide letter at the same density as a pile fill.
    // Written as the image lane writes it — `(explicit || default) * adjust`,
    // not `explicit && adjust` — because scaling only an explicit value would
    // leave the DEFAULT unscaled, which is the common case and the one a pile
    // fabric actually needs.
    const letterFillRowMm = (o.fillRowMm || FILL_ROW_MM) *
      ((fabric && fabric.densityAdjust) ? fabric.densityAdjust : 1);
    // `unsupported` matters MOST on this path: an empty design is exactly the
    // case a user needs explained, and returning a bare `empty` here is what
    // made "pick a Hebrew font, type Emb" fail silently. Built as a function so
    // each early return reports whatever the layout managed to learn.
    // `lettering` rides the empty result too: a design that came back with
    // NOTHING because every column fell under the cross floor (a dot-matrix
    // face at a 1 mm cap) is exactly the case the report has to explain.
    const emptyWith = (chars, lettering) => ({ stitches: [{ x: 0, y: 0, type: "end" }], colors: [], widthMM: 0, heightMM: 0, stitchCount: 0, colorCount: 0, unsupported: chars || [], lettering: lettering || null, _debug: { nSatin: 0, nFill: 0, nTrims: 0 } });
    if (!fontData || !text) return emptyWith([]);

    const ls = o.letterSpacingMm || 0;
    // Pass 1: measure the glyph extent (bbox is spacing-independent) so we can
    // fit-to-garment. Coarse spacing keeps it cheap. `crossFloor: false`: the
    // probe only measures ink extent, and the floor must never decide whether
    // there is anything to measure.
    const probe = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: 2, pullCompMm: 0, letterSpacingMm: ls, underlay: false, crossFloor: false, arcDeg: o.arcDeg || 0, slantDeg: o.slantDeg || 0, align: o.align, circleLayout: o.circleLayout });
    if (!probe.runs.length) return emptyWith(probe.unsupported);
    const bb = probe.bbox;
    const bboxWmm = (bb.x1 - bb.x0) / pxPerMm, bboxHmm = (bb.y1 - bb.y0) / pxPerMm;
    // rotDeg is needed here (ahead of its other use below, near T()) because
    // the fit-to-hoop scale/clamp must be computed against the ROTATED
    // footprint, not the unrotated glyph bbox. Rotation is applied only as a
    // pure post-transform on the emitted stitches (T(), further down) — if
    // the scale were chosen from the unrotated bbox, a non-180 rotation could
    // (and did — Kent's report) push the actual, correctly-reported rotated
    // bbox outside the hoop with nothing left to reclamp it. 180 alone never
    // exposed this: a rectangle rotated 180 about its own center keeps the
    // same axis-aligned bbox, so the stale unrotated scale still happened to
    // fit. Mirrors buildImportedDesign's rotate-before-scale/clamp pattern
    // (dstimport.js, 2026-07-29) in spirit, but computed as the exact AABB of
    // the UNROTATED glyph bbox RECTANGLE rotated by rotDeg (the standard
    // |cos|+|sin| rotated-bounding-box formula), not by rotating the probe's
    // actual (coarsely-sampled) outline points. The glyph ink is always a
    // subset of its own bbox rectangle, so this bound can only be >= the
    // true rotated glyph bbox — guaranteed never to under-clamp (no overflow
    // risk), at the cost of being mildly conservative off quadrant angles
    // (e.g. 45deg) versus the glyph's exact rotated silhouette. Text's satin
    // routing itself stays entirely in the unrotated glyph frame — rotating
    // column geometry would change stitch quality, which this must not touch.
    const rotDeg = o.rotationDeg || 0;
    let fitBboxWmm = bboxWmm, fitBboxHmm = bboxHmm;
    if (rotDeg) {
      const fitRad = (rotDeg * Math.PI) / 180;
      const absCos = Math.abs(Math.cos(fitRad)), absSin = Math.abs(Math.sin(fitRad));
      fitBboxWmm = bboxWmm * absCos + bboxHmm * absSin;
      fitBboxHmm = bboxWmm * absSin + bboxHmm * absCos;
    }
    const fit = garments.fitScale(fitBboxWmm || 1, fitBboxHmm || 1, garment);
    let sc = (fit.scale > 0 && isFinite(fit.scale)) ? fit.scale : 1;
    let designWmm = fit.targetWmm, designHmm = fit.targetHmm;
    // Explicit width override (Slice 3): replaces the auto garment fit. Clamp the
    // requested width into [1, hoopWmm], then ALSO clamp so height still fits the
    // hoop — same two-constraint min() fitScale itself uses, just seeded from the
    // requested (POST-rotation, same convention as buildImportedDesign's
    // targetWidthMm) width instead of the natural bbox. Reported widthMM/heightMM
    // become the actual design dims (bbox*sc), not the (unused) fit target.
    if (typeof o.targetWidthMm === "number" && isFinite(o.targetWidthMm) && o.targetWidthMm > 0) {
      const bw = fitBboxWmm || 1, bh = fitBboxHmm || 1;
      const hoopWmm = units.inToMm(garment.widthIn), hoopHmm = units.inToMm(garment.heightIn);
      const clampedTargetWmm = Math.min(Math.max(o.targetWidthMm, 1), hoopWmm);
      sc = Math.min(clampedTargetWmm / bw, hoopHmm / bh);
      designWmm = bw * sc;
      designHmm = bh * sc;
    }
    const scalePxToDst = sc * (1 / pxPerMm) * units.DST_UNITS_PER_MM;
    const finalMmPerPx = sc / pxPerMm;
    // Pass 2: generate at fit-corrected density so the FINAL satin spacing and
    // pull-comp land at the requested mm regardless of the fit scale (short text
    // scaled up would otherwise sew too sparse).
    // `fitScale: sc` is what lets Law 50's underlay ladder work. The ladder is
    // keyed to FINAL SEWN cap height, and the fit scale is the only place that
    // is known — emMm is nominal, and `sc` can move a nominal 18 mm em by a
    // factor of two either way to land the text in the garment. Passing it
    // also puts the underlay's own mm constants (3 mm stitch, 0.4 mm inset)
    // through the same pre-division this line already does for spacing and
    // pull comp, so they land at their published values on the fabric.
    // `crossFloor` passes straight through (default on — see satinfont's
    // width guards); `false` is the pre-2026-09-03 stitch stream, kept
    // reachable for the byte-identity pins in test/run-fonts.test.js.
    const lay = satinfontmod.layoutText(fontData, text, { emMm, pxPerMm, spacingMm: satinSpacingMm / sc, pullCompMm: pullCompMm / sc, weightMm: weightMm / sc, counterGuard: o.counterGuard !== false, shortStitch: o.shortStitch !== false, letterSpacingMm: ls, underlay: o.underlay !== false, crossFloor: o.crossFloor !== false, fitScale: sc, arcDeg: o.arcDeg || 0, slantDeg: o.slantDeg || 0, align: o.align, circleLayout: o.circleLayout, splitSatin: o.splitSatin, wideColumnFill: o.wideColumnFill, fillRowMm: letterFillRowMm, fillStitchMm: o.fillStitchMm });
    if (!lay.runs.length) return emptyWith(lay.unsupported, lay.lettering);
    const cx = (bb.x0 + bb.x1) / 2, cy = (bb.y0 + bb.y1) / 2;
    // Explicit placement offset (Slice 3): applied AFTER the center transform, in
    // DST space — +x right, +y up (DST convention, already matches T()'s y-flip).
    const offXu = Math.round((o.offsetXMm || 0) * units.DST_UNITS_PER_MM);
    const offYu = Math.round((o.offsetYMm || 0) * units.DST_UNITS_PER_MM);
    // Whole-element rotation (Font editing abilities Round 1): a rigid rotation
    // of the ALREADY-centered, already-scaled point, applied BEFORE the
    // placement offset -- i.e. rotate the element about its own center, then
    // move the rotated result to its placed position. This never touches
    // column/satin geometry (routeGlyph/layoutText run identically regardless
    // of rotationDeg), so it carries zero stitch-quality risk -- same
    // reasoning as arcDeg/offsetXMm being pure placement, not generation,
    // concerns. rotationDeg=0 (absent) must be byte-identical to no rotation
    // at all: cosR=1/sinR=0 makes the rotated branch collapse to the original
    // px/py unchanged. (rotDeg itself is declared earlier, above the fit/
    // scale computation — it's needed there now too; see that comment.)
    const rotRad = (rotDeg * Math.PI) / 180;
    const cosR = Math.cos(rotRad), sinR = Math.sin(rotRad);
    // Mirror X / Mirror Y (Lettering parity round): reflect the ALREADY-
    // centered, already-scaled point about the element's own bbox-center axis
    // — mirrorX negates the centered x (left/right flip), mirrorY the
    // centered y (top/bottom flip). The transform order is fixed and
    // documented: center → MIRROR → ROTATE → placement offset. The mirror
    // happens in the element's own frame BEFORE rotationDeg spins it, so
    // "flip, then tilt" — flipping a rotated element reads as flipping the
    // artwork and re-applying the same tilt, which is what Hatch's Mirror
    // X/Y does (it flips the whole design INCLUDING the glyphs; the point is
    // flipping a design, e.g. for in-the-hoop back pieces — not per-letter
    // mirror-writing). Like rotationDeg this is a pure post-transform on the
    // generated DST-space stitches: layoutText/routeGlyph run identically,
    // the stitch/trim/jump/color RECORD sequence is untouched (a coordinate
    // map moves positions, never records), and widthMM/heightMM are
    // unchanged (the bbox is symmetric about the very center being mirrored
    // across). A mirror does flip each satin run's traversal direction in
    // space — that is exactly the reflected geometry a flipped design must
    // sew; start/end/trim positions are the mirrored images of today's.
    // mirrorX/mirrorY absent or false leave px/py untouched: byte-identical
    // to today's output (house back-compat law, snapshot-pinned in tests).
    const mirX = !!o.mirrorX, mirY = !!o.mirrorY;
    const T = (q) => {
      let px = (q.x - cx) * scalePxToDst, py = (cy - q.y) * scalePxToDst;
      if (mirX) px = -px;
      if (mirY) py = -py;
      const rx = rotDeg ? px * cosR - py * sinR : px;
      const ry = rotDeg ? px * sinR + py * cosR : py;
      return { x: Math.round(rx) + offXu, y: Math.round(ry) + offYu };
    };
    const trimAtMm = (fabric && fabric.trimAtMm != null) ? fabric.trimAtMm : (o.trimAtMm == null ? 3.0 : o.trimAtMm);

    // Cap garments sew crown-distortion-safe — the same rule the image
    // pipeline's capMode ordering applies (center-out per color block),
    // extended to LETTERING: lines sew bottom-up (bill toward crown) and each
    // line's glyphs sew center-out (middle letter first, working outward), so
    // fabric push radiates off the unstable crown seam instead of piling into
    // it. Grouping is by SOURCE GLYPH (charIdx): a glyph's own runs
    // (underlay + satin, already routed) keep their internal order — only the
    // order OF glyphs changes, so column geometry is byte-identical.
    // Ordering uses FINAL-space centroids (the same rotation T() applies,
    // offsets omitted — ordering is relative), so rotated/arc'd text still
    // sews bottom-up/center-out as the machine will actually see it. Line
    // membership comes from the source text's "\n" positions (charIdx counts
    // "\n" as one index, matching layoutText), not geometry guessing.
    // Reordering breaks the router's adjacent-glyph connector assumption, so
    // every relocated group's first run is forced to jump — the loop's
    // existing trim policy then cuts the long hops. Extra trims on caps are
    // the standard professional trade for crown control. Non-cap garments
    // take the `runsOrdered = lay.runs` identity path: byte-identical output.
    const capMode = garment && (garment.id === "hat_front" || garment.id === "beanie");
    let runsOrdered = lay.runs;
    if (capMode) {
      const groups = [];
      let cur = null;
      for (const run of lay.runs) {
        if (!cur || run.charIdx !== cur.charIdx) { cur = { charIdx: run.charIdx, runs: [] }; groups.push(cur); }
        cur.runs.push(run);
      }
      const lineOfChar = [];
      { let line = 0; for (const ch of String(text)) { lineOfChar.push(line); if (ch === "\n") line++; } }
      for (const g of groups) {
        let sx = 0, sy = 0, n = 0;
        for (const r of g.runs) for (const p of r.pts) { sx += p.x; sy += p.y; n++; }
        // px-space centroid -> final-space (mirror + rotation, same order as
        // T(): center → mirror → rotate — so cap bottom-up/center-out
        // ordering follows where glyphs ACTUALLY land after a flip).
        let px = (sx / n - cx), py = (cy - sy / n);
        if (mirX) px = -px;
        if (mirY) py = -py;
        g.x = rotDeg ? px * cosR - py * sinR : px;
        g.y = rotDeg ? px * sinR + py * cosR : py;
        g.line = lineOfChar[g.charIdx] || 0;
      }
      const acc = (map, key, v) => { const a = map.get(key) || { s: 0, n: 0 }; a.s += v; a.n++; map.set(key, a); };
      const lineY = new Map(), lineX = new Map();
      for (const g of groups) { acc(lineY, g.line, g.y); acc(lineX, g.line, g.x); }
      // Bottom-up: final-space +y is UP, so ascending mean y = lowest line first.
      const lineRank = new Map(
        [...lineY.entries()].sort((a, b) => a[1].s / a[1].n - b[1].s / b[1].n).map((e, i) => [e[0], i])
      );
      const sorted = groups.slice().sort((a, b) => {
        const lr = lineRank.get(a.line) - lineRank.get(b.line);
        if (lr) return lr;
        const mA = lineX.get(a.line), mB = lineX.get(b.line);
        const dA = Math.abs(a.x - mA.s / mA.n), dB = Math.abs(b.x - mB.s / mB.n);
        return dA - dB || a.charIdx - b.charIdx; // center-out; index tie-break for determinism
      });
      runsOrdered = [];
      sorted.forEach((g, gi) => {
        g.runs.forEach((r, ri) => {
          runsOrdered.push(gi > 0 && ri === 0 ? { ...r, jump: true } : r);
        });
      });
    }

    // Per-letter color (Font editing abilities Round 1): colorRanges is a
    // list of { startIdx, endIdx, colorRgb } over the ORIGINAL text string's
    // indices (startIdx inclusive, endIdx exclusive — matches
    // text.slice(startIdx,endIdx) / a <textarea>'s selectionStart/End, see
    // layoutText's charIdx tagging). A character not covered by any range
    // uses the element's base `rgb`. Overlapping ranges resolve to whichever
    // one appears FIRST in the array. colorRanges absent/empty means every
    // charIdx resolves to the base rgb, which reproduces today's exact
    // single-color output (colors.length stays 1, no "color" records).
    const colorRanges = Array.isArray(o.colorRanges) ? o.colorRanges : [];
    function colorForCharIdx(idx) {
      for (const r of colorRanges) { if (idx >= r.startIdx && idx < r.endIdx) return r.colorRgb; }
      return rgb;
    }
    let stitches = [];
    const colors = [];
    let curRgb = null;
    function ensureColor(targetRgb) {
      if (curRgb && targetRgb[0] === curRgb[0] && targetRgb[1] === curRgb[1] && targetRgb[2] === curRgb[2]) return;
      colors.push({ r: targetRgb[0], g: targetRgb[1], b: targetRgb[2], name: "Color " + (colors.length + 1) });
      curRgb = targetRgb;
    }
    const maxStitchMm = o.maxStitchMm || 4;
    const maxStepPx = maxStitchMm / finalMmPerPx;   // longest single stitch (px)
    let nTrims = 0, nSatin = 0, lastPt = null, forceJumpNext = false;

    // Lock stitches, OFF by default (2026-09-14). The Python lane ties every
    // block unconditionally and this lane tied nothing at all; `ties: true`
    // closes that gap. It ships default-OFF for the reason every other flag in
    // this repo did — it changes EVERY .dst/.pes a customer exports from
    // lettering, and this house makes Kent rule a flip like that with the
    // measurement in front of him. With the flag off the stream is the one
    // built below, untouched, which is what the snapshot pins assert.
    //
    // Ties are ordinary `stitch` records spliced into the sewn stream, exactly
    // where Python folds them into the run they protect, rather than runs of
    // their own — so nothing downstream has to special-case a two-millimetre
    // run that is not really stitching. They are put in once the stream is
    // finished (applyTies, 2026-10-03): until then they were pushed here as
    // each run went by, in px, and came out 0.2 to 2.0 mm long.
    const ties = !!o.ties;
    // RUN SPANS (`design.runs`) — what each stitch IS, for the renderer.
    //
    // The design model downstream is a flat {x,y,type} stream in which satin,
    // tatami, a bean run, underlay and needle-down travel are indistinguishable,
    // so the browser canvas drew them all the same way and a satin border
    // vanished into the fill beside it (Kent, 2026-09-15). This lane does not
    // have to GUESS any of that: satinfont's router already tags every run it
    // emits, and has since the kind rename that split real underlay from travel
    // (satinfont.js, "KIND RENAME"). So the spans below are a relabelling of
    // tags that already exist, not a second classification that could drift
    // from the first.
    //
    // Only the mapped kinds get a span. An unrecognised tag is left OUT rather
    // than guessed at: a strand inside no span renders exactly as it did before
    // spans existed, which is the right answer for "we do not know".
    const SPAN_KIND = { satin: "satin", fill: "fill", run: "run", underlay: "underlay", underpath: "travel" };
    const spans = [];
    function pushSpan(i0, kind, charIdx) {
      if (!kind || stitches.length <= i0) return;
      spans.push({ i0, i1: stitches.length - 1, kind, shape: charIdx == null ? "" : "c" + charIdx,
                   role: "", block: Math.max(0, colors.length - 1) });
    }
    // The router (satinfont) decides jump vs. underpath per run: jump=false means
    // travel as a needle-DOWN running connector (tucked at a junction, covered);
    // jump=true means lift the needle (and trim if the hop is long).
    // runsOrdered is lay.runs verbatim except on cap garments (see capMode above).
    for (const run of runsOrdered) {
      const pts = run.pts;
      if (!pts || pts.length < 2) continue;
      if (run.kind === "satin") nSatin++;
      const runRgb = colorForCharIdx(run.charIdx);
      if (curRgb === null) {
        ensureColor(runRgb);
      } else if (runRgb[0] !== curRgb[0] || runRgb[1] !== curRgb[1] || runRgb[2] !== curRgb[2]) {
        // Color-range boundary: trim (needle up) + color-change marker at the
        // last sewn point, same pattern app/src/lib/combine.js already uses
        // to splice separate elements together.
        if (lastPt) { const tp = T(lastPt); stitches.push({ x: tp.x, y: tp.y, type: "trim" }); stitches.push({ x: tp.x, y: tp.y, type: "color" }); nTrims++; }
        ensureColor(runRgb);
        forceJumpNext = true;
      }
      const start = pts[0];
      if (!lastPt) {
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
      } else if (run.jump || forceJumpNext) {
        const gapMm = Math.hypot(start.x - lastPt.x, start.y - lastPt.y) * finalMmPerPx;
        if (gapMm > trimAtMm && !forceJumpNext) { const tp = T(lastPt); stitches.push({ x: tp.x, y: tp.y, type: "trim" }); nTrims++; }
        const f = T(start); stitches.push({ x: f.x, y: f.y, type: "jump" });
        forceJumpNext = false;
      } else {
        const gap = Math.hypot(start.x - lastPt.x, start.y - lastPt.y);
        const steps = Math.max(1, Math.ceil(gap / maxStepPx));
        const ti0 = stitches.length;
        for (let s = 1; s <= steps; s++) { const t = s / steps; const d = T({ x: lastPt.x + (start.x - lastPt.x) * t, y: lastPt.y + (start.y - lastPt.y) * t }); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
        // These connector stitches are needle-DOWN travel, not stitching — the
        // renderer de-emphasises them so they stop reading as part of a glyph.
        pushSpan(ti0, "travel", run.charIdx);
      }
      const ri0 = stitches.length;
      for (const q of pts) { const d = T(q); stitches.push({ x: d.x, y: d.y, type: "stitch" }); }
      pushSpan(ri0, SPAN_KIND[run.kind], run.charIdx);
      lastPt = pts[pts.length - 1];
    }
    // A trim cuts the thread and a jump that was not trimmed does not, so the
    // locks go either side of every trim and at both ends of the stream — the
    // question `apply_ties` asks (`i == 0 or run.trim`), not "did the needle
    // lift". The stream's end is a cut too: the thread ends there.
    const tied = ties ? applyTies(stitches, spans) : null;
    const nTies = tied ? tied.nTies : 0;
    if (tied) stitches = tied.stitches;
    const stitchCount = stitches.filter((s) => s.type === "stitch").length;
    // widthMM/heightMM must reflect the ACTUAL sewn footprint — the field's
    // stats line, SizePanel, the hoop ceiling check and the printed worksheet
    // all trace back to this value for a single-element project (see
    // combine.js's bboxMmFromStitches for the identical rule used once
    // multiple elements are combined).
    //
    // This recompute used to be GATED on rotDeg, on the reasoning that only
    // rotation moves the axis-aligned box away from the glyph bbox (landscape
    // text rotated 90 becomes portrait). Rotation is the largest such move,
    // not the only one: pull compensation and the weight preset push the
    // satin rails outward at every angle including none, so the unrotated
    // case — the overwhelmingly common one — kept reporting the glyph box
    // while sewing wider than it. designExtentMm carries the measurement.
    const extent = designExtentMm(stitches, designWmm, designHmm);
    const outWmm = extent.widthMM, outHmm = extent.heightMM;
    // `unsupported`: characters this font has no glyph for. Carried out of the
    // layout so a caller can explain a design that came back empty or short —
    // before this, typing Latin into a Hebrew font returned a valid-looking
    // 0-stitch, 0x0mm design with nothing anywhere saying why. Always an array;
    // empty whenever every character rendered.
    // `lettering`: the width-guard report (final sewn cap height, columns
    // under the needle floors, hairline spans sewn as run) — see
    // satinfont.layoutText. Null only on the empty paths above.
    return { stitches, colors, widthMM: outWmm, heightMM: outHmm, stitchCount, colorCount: colors.length, runs: spans, unsupported: lay.unsupported || [], lettering: lay.lettering || null, _debug: { nSatin, nFill: 0, nTrims, nTies } };
  }

  // `tieRun` is exported for its own sake: its overshoot rule only fires when
  // the path is SHORTER than one leg, which no ordinary lettering fixture
  // produces — a mutation deleting `Math.min` passed the whole suite until
  // this was reachable directly. The rule is the expensive half of the port
  // (Python learned it from a smoke run that pushed the design's box 0.8 mm
  // outside its artwork), so it gets a test that can actually reach it.
  // `applyTies` likewise: which records it calls a cut, and what it does with
  // a thread that sews nothing, are asked of streams written out by hand.
  return { buildQualityDesign, buildLetteringDesign, groupRingsIntoShapes, offsetRing, signedArea, underlayRuns, tieRun, applyTies, FILL_ROW_MM, SATIN_SPACING_MM, THREAD_LENGTH_FACTOR, TIE_STITCH_MM, TIE_STITCHES };
});
