// Row stagger for the tatami fill: `tatamiFill({ stagger, minStitch })`, default
// off, and the builder flag that turns it on for a shape's cover fill
// (`buildQualityDesign({ fillStagger })`, default off).
//
// Without it every row is divided evenly from its own end, so on any shape
// with straight sides the needle holes of one row stand exactly under the
// holes of the row before, and light runs down the line they make. The Python
// engine has always shifted each row's holes along a shared grid
// (`stage6_fill._row_points_at_phase`); this is that rule, read off the points
// the fill returns.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fill = require("../src/fill.js");
const DG = require("../src/digitize.js");

const P = 4, MIN = 1, PITCH = 0.4;            // a stitch, the shortest stitch, a row: think mm
const ON = { stagger: 4, minStitch: MIN };
const SLOTS = [0, 2, 1, 3];
const rect = (x, y, w, h) => [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
const RECT = [rect(0, 0, 40, 20)];
const FRAME = [rect(0, 0, 60, 60), rect(20, 20, 20, 20)];   // a square with a square hole
const ngon = (cx, cy, r, n, turn) => Array.from({ length: n }, (_, i) => {
  const a = turn + (2 * Math.PI * i) / n;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
});
const star = (cx, cy, r, n, spike, turn) => Array.from({ length: 2 * n }, (_, i) => {
  const a = turn + (Math.PI * i) / n, rr = i % 2 ? r * (1 - spike) : r;
  return { x: cx + rr * Math.cos(a), y: cy + rr * Math.sin(a) };
});
const mulberry = (seed) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const turned = (p, deg) => {
  const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
  return { x: p.x * c - p.y * s, y: p.x * s + p.y * c };
};

// The rows of a fill, cut by this file's own scanline and not the engine's:
// from the top of the shape in the rows' frame, one pitch apart, even-odd.
function rowsOf(polys, pitch, angleDeg) {
  const rings = polys.map((ring) => ring.map((p) => turned(p, -angleDeg)));
  let minY = Infinity, maxY = -Infinity;
  for (const ring of rings) for (const p of ring) { minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y); }
  const rows = [];
  for (let y = minY; y <= maxY + 1e-9; y += pitch) {
    const xs = [];
    for (const ring of rings) for (let i = 0; i < ring.length; i++) {
      const u = ring[i], v = ring[(i + 1) % ring.length];
      if (u.y === v.y) continue;
      if (y >= Math.min(u.y, v.y) && y < Math.max(u.y, v.y)) xs.push(u.x + ((y - u.y) / (v.y - u.y)) * (v.x - u.x));
    }
    xs.sort((p, q) => p - q);
    const spans = [];
    for (let i = 0; i + 1 < xs.length; i += 2) spans.push({ x0: xs[i], x1: xs[i + 1], holes: [] });
    rows.push({ y, spans });
  }
  return { rows, minY };
}

// Every needle hole BETWEEN the two ends of a row, by row and by span, as a
// place along the row. A float's landing is where the frame goes, not a hole.
function holesOf(pts, polys, pitch, angleDeg) {
  const { rows, minY } = rowsOf(polys, pitch, angleDeg);
  for (const p of pts) {
    if (p.travel || p.trim) continue;
    const q = turned(p, -angleDeg), k = (q.y - minY) / pitch, ri = Math.round(k);
    if (Math.abs(k - ri) * pitch > 1e-6 || !rows[ri]) continue;        // not on a row: a turn's own stitch
    const span = rows[ri].spans.find((s) => q.x > s.x0 + 1e-6 && q.x < s.x1 - 1e-6);
    if (span) span.holes.push(q.x);
  }
  for (const row of rows) for (const s of row.spans) s.holes.sort((p, q) => p - q);
  return rows;
}
const allHoles = (row) => [].concat(...row.spans.map((s) => s.holes));

// Of those holes, how many have a hole of the NEXT row within `near` of them
// along the row (`pairs`), and how many have one on each of the next TWO rows
// (`threes`). Three in a line is the start of a channel. Two is not: a long
// step cut in half lands near the next row's grid point by the rule itself
// (see the grid test), once, with nothing above or below it.
function inLine(rows, near) {
  let n = 0, pairs = 0, threes = 0;
  for (let ri = 0; ri + 2 < rows.length; ri++) {
    const next = allHoles(rows[ri + 1]), after = allHoles(rows[ri + 2]);
    for (const h of allHoles(rows[ri])) {
      n++;
      if (!next.some((g) => Math.abs(g - h) <= near)) continue;
      pairs++;
      if (after.some((g) => Math.abs(g - h) <= near)) threes++;
    }
  }
  return { n, pairs, threes };
}

// A walk with the holes between a row's ends taken out: what is left is where
// each row starts and ends, every turn, every run along a rim, every float and
// every cut, in the order they are sewn.
function skeleton(pts, angleDeg) {
  const q = pts.map((p) => turned(p, -angleDeg));
  const sewn = (i) => !pts[i].travel && !pts[i].trim;
  return pts.filter((p, i) => {
    if (i === 0 || i === pts.length - 1 || !sewn(i) || !sewn(i + 1)) return true;
    const onRow = Math.abs(q[i].y - q[i - 1].y) < 1e-7 && Math.abs(q[i].y - q[i + 1].y) < 1e-7;
    const between = (q[i].x - q[i - 1].x) * (q[i + 1].x - q[i].x) > 0;
    return !(onRow && between);
  }).map((p) => ({ x: p.x, y: p.y, travel: !!p.travel, trim: !!p.trim }));
}
const stitchLengths = (pts) => {
  const out = [];
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].travel || pts[i].trim) continue;
    out.push(Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  }
  return out;
};
const base = (extra) => Object.assign({ rowSpacing: PITCH, angleDeg: 0, maxStitch: P, markConnectors: true }, extra || {});

test("staggerSlots: the order the Python engine gives its rows, for every cycle it could be asked for", () => {
  // `stage6_fill._stagger_slots(n)` for n = 1..8, printed by the Python engine
  const python = { 1: [0], 2: [0, 1], 3: [0, 2, 1], 4: [0, 2, 1, 3], 5: [0, 3, 2, 4, 1], 6: [0, 3, 2, 5, 1, 4], 7: [0, 4, 2, 6, 1, 5, 3], 8: [0, 4, 2, 6, 1, 5, 3, 7] };
  for (const n of Object.keys(python)) assert.deepStrictEqual(fill.staggerSlots(Number(n)), python[n], "a cycle of " + n);
  assert.deepStrictEqual(fill.staggerSlots(0), [0], "no cycle is one slot");
});

test("stagger: a rectangle's holes stand in line from row to row without it, and nowhere with it", () => {
  const off = inLine(holesOf(fill.tatamiFill(RECT, base()), RECT, PITCH, 0), 0.3);
  assert.ok(off.n > 400, "fixture: " + off.n + " holes between the ends of 50 rows");
  assert.strictEqual(off.threes, off.n, "the defect: every hole has one straight under it, and one under that");
  const on = inLine(holesOf(fill.tatamiFill(RECT, base(ON)), RECT, PITCH, 0), 0.3);
  assert.ok(on.n > 400, "fixture: the staggered fill still has its holes, " + on.n);
  assert.strictEqual(on.pairs, 0, "staggered: " + on.pairs + " of " + on.n + " holes still in line");
  // turned, the rows end at a slant and no two are cut alike, so the defect is
  // partial -- and the stagger still leaves no three in a line
  for (const angleDeg of [30, 45]) {
    const was = inLine(holesOf(fill.tatamiFill(RECT, base({ angleDeg })), RECT, PITCH, angleDeg), 0.3);
    const is = inLine(holesOf(fill.tatamiFill(RECT, base(Object.assign({ angleDeg }, ON))), RECT, PITCH, angleDeg), 0.3);
    assert.ok(was.threes > 0.1 * was.n, "angle " + angleDeg + " the defect: " + was.threes + " of " + was.n + " holes are the head of three in a line");
    assert.strictEqual(is.threes, 0, "angle " + angleDeg + " staggered: three in a line");
    assert.ok(is.pairs < 0.1 * is.n, "angle " + angleDeg + " staggered: " + is.pairs + " of " + is.n + " holes with one under them");
  }
});

test("stagger: a row's holes are a quarter of a stitch or more from the holes of the row before", () => {
  const rows = holesOf(fill.tatamiFill(RECT, base(ON)), RECT, PITCH, 0);
  let nearest = Infinity;
  for (let ri = 0; ri + 1 < rows.length; ri++) {
    for (const h of allHoles(rows[ri])) for (const g of allHoles(rows[ri + 1])) nearest = Math.min(nearest, Math.abs(g - h));
  }
  assert.ok(nearest >= P / 4 - 1e-6, "the nearest two holes on neighbouring rows are " + nearest.toFixed(3) + " apart");
  // and the cycle closes: four rows on, the holes are back where they were
  for (let ri = 0; ri + 4 < rows.length; ri++) {
    const a = allHoles(rows[ri]), b = allHoles(rows[ri + 4]);
    assert.strictEqual(a.length, b.length, "row " + ri + " and row " + (ri + 4));
    a.forEach((h, k) => assert.ok(Math.abs(h - b[k]) < 1e-6, "row " + ri + " hole " + k));
  }
});

test("stagger: every hole is on its row's grid, or halves a step the grid left too long", () => {
  // The grid is one for the whole fill: a stitch apart, shifted by the row's
  // slot in the cycle. A grid point is kept when it is a real stitch from both
  // ends of the row. Skipping one can leave a step longer than a stitch, and
  // that step is halved.
  const shapes = [RECT, [ngon(31.7, 22.3, 18, 7, 0.3)], [ngon(5, -40, 26, 40, 0)], [rect(3.3, 7.7, 9.5, 30)]];
  let onGrid = 0, halves = 0;
  for (const polys of shapes) for (const angleDeg of [0, 30, 90, 137, 282.32]) {
    const rows = holesOf(fill.tatamiFill(polys, base(Object.assign({ angleDeg }, ON))), polys, PITCH, angleDeg);
    rows.forEach((row, ri) => {
      const phase = (SLOTS[ri % 4] / 4) * P;
      for (const s of row.spans) {
        const label = "angle " + angleDeg + " row " + ri + " span " + s.x0.toFixed(3) + ".." + s.x1.toFixed(3);
        const seq = [s.x0].concat(s.holes, [s.x1]);
        const gridded = (x) => Math.abs((x - phase) / P - Math.round((x - phase) / P)) * P < 1e-6;
        for (let k = 1; k + 1 < seq.length; k++) {
          if (gridded(seq[k])) { onGrid++; continue; }
          assert.ok(Math.abs(seq[k] - (seq[k - 1] + seq[k + 1]) / 2) < 1e-6, label + ": a hole at " + seq[k].toFixed(4) + " is neither on the grid nor half way");
          halves++;
        }
        // every grid point with room on both sides is sewn
        if (s.x1 - s.x0 < 2 * MIN) { assert.strictEqual(s.holes.length, 0, label + ": a row under two stitches' worth is one stitch"); continue; }
        for (let g = Math.ceil((s.x0 - phase) / P) * P + phase; g < s.x1; g += P) {
          if (g - s.x0 < MIN + 1e-6 || s.x1 - g < MIN + 1e-6) continue;
          assert.ok(s.holes.some((h) => Math.abs(h - g) < 1e-6), label + ": no hole on the grid at " + g.toFixed(4));
        }
      }
    });
  }
  assert.ok(onGrid > 5000 && halves > 100, "fixture: " + onGrid + " holes on the grid, " + halves + " halving a long step");
});

test("stagger: take the holes between a row's ends out, and it is the same walk", () => {
  // Nothing else moves: not a row's two ends (they are the shape's edge), not
  // a turn, not a run along a rim, not a float, not a cut.
  const rnd = mulberry(20261003);
  const pick = (list) => list[Math.floor(rnd() * list.length)];
  let walks = 0, columnWalks = 0;
  for (let t = 0; t < 60; t++) {
    const outer = rnd() < 0.5 ? star(50, 50, 30 + 20 * rnd(), 3 + Math.floor(rnd() * 9), pick([0, 0, 0.3, 0.6]), rnd() * 6) : rect(0, 0, 30 + 60 * rnd(), 20 + 50 * rnd());
    const polys = [outer];
    if (rnd() < 0.5) polys.push(ngon(50, 50, 4 + 6 * rnd(), pick([4, 4, 12]), rnd() * 6));
    const opts = base({ angleDeg: pick([0, 90, 30, 45, 137, 360 * rnd()]), rowSpacing: pick([PITCH, 1, 2.5]), columns: rnd() < 0.6, centerOut: rnd() < 0.4 });
    const label = "shape " + t + " " + JSON.stringify(opts);
    const off = fill.tatamiFill(polys, opts), on = fill.tatamiFill(polys, Object.assign({}, opts, ON));
    assert.deepStrictEqual(skeleton(on, opts.angleDeg), skeleton(off, opts.angleDeg), label);
    assert.strictEqual(!!on.columnWalk, !!off.columnWalk, label + ": the same walk is chosen");
    walks++;
    if (on.columnWalk) columnWalks++;
  }
  assert.ok(columnWalks >= 10 && walks - columnWalks >= 10, "fixture: " + columnWalks + " column walks of " + walks);
});

test("stagger: no stitch is longer than a stitch, and none it adds is shorter than the shortest", () => {
  const rnd = mulberry(4242);
  const pick = (list) => list[Math.floor(rnd() * list.length)];
  let rowStitches = 0, shortest = Infinity;
  for (let t = 0; t < 60; t++) {
    const polys = [rnd() < 0.5 ? star(0, 0, 25 + 25 * rnd(), 3 + Math.floor(rnd() * 9), pick([0, 0.3, 0.6]), rnd() * 6) : rect(-20, -10, 20 + 60 * rnd(), 10 + 50 * rnd())];
    if (rnd() < 0.4) polys.push(ngon(0, 0, 3 + 5 * rnd(), pick([4, 12]), rnd() * 6));
    const opts = base({ angleDeg: pick([0, 90, 30, 45, 360 * rnd()]), columns: rnd() < 0.6, centerOut: rnd() < 0.4 });
    const label = "shape " + t + " " + JSON.stringify(opts);
    const off = stitchLengths(fill.tatamiFill(polys, opts)), on = stitchLengths(fill.tatamiFill(polys, Object.assign({}, opts, ON)));
    for (const d of on) assert.ok(d <= P + 1e-6, label + ": a stitch " + d.toFixed(4) + " long");
    // a turn, or a row shorter than a stitch, is as short with the stagger as without
    const short = (list) => list.filter((d) => d < MIN - 1e-6).length;
    assert.strictEqual(short(on), short(off), label + ": stitches under " + MIN);
    // between a row's ends the shortest is the shortest stitch, and that is met
    const rows = holesOf(fill.tatamiFill(polys, Object.assign({ columns: false }, opts, ON, { columns: false })), polys, PITCH, opts.angleDeg);
    for (const row of rows) for (const s of row.spans) {
      if (!s.holes.length) continue;
      const seq = [s.x0].concat(s.holes, [s.x1]);
      for (let k = 1; k < seq.length; k++) { rowStitches++; shortest = Math.min(shortest, seq[k] - seq[k - 1]); }
    }
  }
  assert.ok(rowStitches > 10000, "fixture: " + rowStitches + " stitches along rows");
  assert.ok(shortest >= MIN - 1e-6, "the shortest stitch along a row is " + shortest.toFixed(4));
});

test("stagger: with the column walk a shape with a hole gets the same shift, and not one more cut", () => {
  for (const angleDeg of [0, 30]) {
    const opts = base({ angleDeg, columns: true, openTol: PITCH });
    const off = fill.tatamiFill(FRAME, opts), on = fill.tatamiFill(FRAME, Object.assign({}, opts, ON));
    assert.ok(off.columnWalk && on.columnWalk, "fixture: the hole makes it a column walk");
    const flags = (pts) => pts.filter((p) => p.travel || p.trim).map((p) => ({ x: p.x, y: p.y, travel: !!p.travel, trim: !!p.trim }));
    assert.deepStrictEqual(flags(on), flags(off), "angle " + angleDeg + ": the floats and the cuts");
    const was = inLine(holesOf(off, FRAME, PITCH, angleDeg), 0.3), is = inLine(holesOf(on, FRAME, PITCH, angleDeg), 0.3);
    assert.ok(was.n > 1000 && is.n > 1000, "fixture: holes, " + was.n + " and " + is.n);
    assert.ok(was.threes > 0.1 * was.n, "angle " + angleDeg + " the defect: " + was.threes + " of " + was.n + " holes are the head of three in a line");
    // (one, at 30 degrees: a run along the hole's rim lays a stitch on a row)
    assert.ok(is.threes <= 2, "angle " + angleDeg + " staggered: " + is.threes + " threes in a line");
    assert.ok(is.pairs < 0.1 * is.n, "angle " + angleDeg + " staggered: " + is.pairs + " of " + is.n + " holes with one under them");
  }
});

test("stagger: the thread still covers every row, end to end", () => {
  for (const polys of [RECT, FRAME, [star(0, 0, 40, 5, 0.5, 0.2)]]) for (const columns of [false, true]) for (const angleDeg of [0, 45]) {
    const pts = fill.tatamiFill(polys, base(Object.assign({ angleDeg, columns, openTol: PITCH }, ON)));
    const { rows } = rowsOf(polys, PITCH, angleDeg);
    let want = 0, got = 0;
    for (const row of rows) for (const s of row.spans) want += s.x1 - s.x0;
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].travel || pts[i].trim) continue;
      const a = turned(pts[i - 1], -angleDeg), b = turned(pts[i], -angleDeg);
      if (Math.abs(a.y - b.y) < 1e-6) got += Math.abs(b.x - a.x);
    }
    assert.ok(got >= want - 1e-3 * want, "columns " + columns + " angle " + angleDeg + ": rows sewn " + got.toFixed(1) + " of " + want.toFixed(1));
  }
});

test("stagger: off, zero and absent are one fill, and the shortest stitch alone changes nothing", () => {
  for (const polys of [RECT, FRAME, [star(0, 0, 40, 5, 0.5, 0.2)]]) for (const columns of [false, true]) for (const centerOut of [false, true]) for (const angleDeg of [0, 45]) {
    const opts = base({ angleDeg, columns, centerOut, openTol: PITCH });
    const plain = fill.tatamiFill(polys, opts);
    for (const extra of [{ stagger: 0 }, { stagger: 0, minStitch: MIN }, { minStitch: MIN }, { stagger: false }, { stagger: null }]) {
      assert.deepStrictEqual(fill.tatamiFill(polys, Object.assign({}, opts, extra)), plain, JSON.stringify(Object.assign({}, opts, extra)));
    }
  }
});

test("stagger: a cycle is 64 rows at most, whatever is asked for", () => {
  // the table of slots is built whole; a number with nine noughts would be built too
  const asked = fill.tatamiFill(RECT, base({ stagger: 3e6, minStitch: MIN }));
  assert.deepStrictEqual(asked, fill.tatamiFill(RECT, base({ stagger: 64, minStitch: MIN })));
  assert.deepStrictEqual(fill.tatamiFill(RECT, base({ stagger: 1e9, minStitch: MIN })), asked);
  assert.deepStrictEqual(fill.tatamiFill(RECT, base({ stagger: Infinity, minStitch: MIN })), asked);
});

test("stagger: a cycle is a number of rows, and anything else is no stagger", () => {
  // (off the grid's own origin, or a cycle of ONE row is the even cut by accident)
  const polys = [rect(0.5, 0, 39, 20)];
  const four = fill.tatamiFill(polys, base(ON)), none = fill.tatamiFill(polys, base());
  assert.notDeepStrictEqual(fill.tatamiFill(polys, base({ stagger: 1, minStitch: MIN })), none, "fixture: a cycle of one row is a fill of its own");
  assert.deepStrictEqual(fill.tatamiFill(polys, base({ stagger: 4.9, minStitch: MIN })), four, "a fraction is the whole number in it");
  // under one row there is no cycle
  for (const stagger of [0.5, -4, NaN]) assert.deepStrictEqual(fill.tatamiFill(polys, base({ stagger, minStitch: MIN })), none, String(stagger));
  // `true` is not a cycle of one row (one grid with NO shift, every hole in
  // line again), and text is not a number: a caller who passes a flag where a
  // count belongs gets the fill as shipped, not a third fill
  for (const stagger of [true, "4", [4], {}]) assert.deepStrictEqual(fill.tatamiFill(polys, base({ stagger, minStitch: MIN })), none, JSON.stringify(stagger));
});

test("stagger: a step a micron over a stitch is a stitch, not two halves", () => {
  // `stitches.split_long_moves`: a step is cut only when it is over a stitch
  // by more than the split tolerance, which the caller gives in its own units
  // (`splitTol`; a micron). This row starts half a micron left of a grid
  // point, so its first step is 4.0000005, and the Python fill sews it whole.
  const near = [rect(-5e-7, 0, 30 + 5e-7, 1)];
  const opts = base({ stagger: 4, minStitch: MIN, splitTol: 1e-6 });
  const first = (polys) => allHoles(holesOf(fill.tatamiFill(polys, opts), polys, PITCH, 0)[0]);
  assert.deepStrictEqual(first(near), [4, 8, 12, 16, 20, 24, 28]);
  // five microns left of it, the step is over by more than the tolerance and is cut
  const far = [rect(-5e-6, 0, 30 + 5e-6, 1)];
  assert.strictEqual(first(far).length, 8);
  assert.ok(Math.abs(first(far)[0] - 2) < 1e-5, "the first hole halves the step: " + first(far)[0]);
});

test("stagger: a long step is cut from the end the thread comes from", () => {
  // `split_long_moves` cuts a PATH: prev + (cur - prev) * s / steps. On a row
  // sewn right to left that is from the high end, and the two ends do not
  // always give the same double. Row 1 of this rectangle runs right to left,
  // its grid point 0.998 from the left end is skipped, and the step from 2
  // down to the left end is cut in half.
  const x0 = 0.302 - 3.3;   // -2.9979999999999998: one ulp off -2.998, and that ulp is the case
  const polys = [[{ x: x0, y: 0 }, { x: 17.139, y: 0 }, { x: 17.139, y: 1 }, { x: x0, y: 1 }]];
  const pts = fill.tatamiFill(polys, base({ stagger: 4, minStitch: MIN, splitTol: 1e-6 }));
  const row1 = pts.filter((p) => Math.abs(p.y - PITCH) < 1e-9).map((p) => p.x);
  assert.strictEqual(row1[0], 17.139, "fixture: the row is sewn from the right");
  const fromHigh = 2 + (x0 - 2) * 0.5, fromLow = x0 + (2 - x0) * 0.5;
  assert.notStrictEqual(fromHigh, fromLow, "fixture: the two ends give different doubles");
  assert.strictEqual(row1[row1.length - 2], fromHigh, "the half is counted from where the thread was");
});

test("stagger: where a stitch is under two shortest stitches, the clearance is kept and the floor is half a stitch", () => {
  // Found by audit: a step between one stitch and one stitch plus the shortest
  // is halved, so where a stitch is under two shortest stitches the halves are
  // under the shortest (a builder asked for a stitch under 2 mm). They are
  // never under HALF a stitch, which is as far down as an even cut goes too.
  // The clearance at a row's ends stays what the caller gave. Lowering it to
  // half a stitch was tried as a fix and failed its own audit: the floor did
  // not move, and a third more short stitches were made.
  const polys = [rect(0, 0, 400, 100)];
  const P15 = 15, M10 = 10, opts = { rowSpacing: 1.5, angleDeg: 0, maxStitch: P15, markConnectors: true };
  const rowsOfFill = (extra) => holesOf(fill.tatamiFill(polys, Object.assign({}, opts, extra)), polys, 1.5, 0);
  const steps = (rows) => {
    const out = [];
    for (const row of rows) for (const s of row.spans) {
      const seq = [s.x0].concat(s.holes, [s.x1]);
      for (let k = 1; k < seq.length; k++) out.push(seq[k] - seq[k - 1]);
    }
    return out;
  };
  const on = rowsOfFill({ stagger: 4, minStitch: M10 }), off = rowsOfFill({});
  assert.ok(steps(on).length > 1500, "fixture: stitches along rows, " + steps(on).length);
  for (const [name, list] of [["staggered", steps(on)], ["as shipped", steps(off)]]) {
    assert.ok(Math.min(...list) >= P15 / 2 - 1e-9, name + ": the shortest stitch along a row is " + Math.min(...list));
    assert.ok(Math.max(...list) <= P15 + 1e-9, name + ": the longest is " + Math.max(...list));
  }
  assert.ok(steps(on).some((d) => d < M10 - 1e-9), "fixture: the stagger does make stitches under the shortest here");
  // every hole that is ON the grid keeps the clearance the caller asked for
  let onGrid = 0;
  on.forEach((row, ri) => {
    const phase = (SLOTS[ri % 4] / 4) * P15;
    for (const s of row.spans) for (const h of s.holes) {
      if (Math.abs((h - phase) / P15 - Math.round((h - phase) / P15)) * P15 > 1e-6) continue;
      onGrid++;
      assert.ok(Math.min(h - s.x0, s.x1 - h) >= M10 - 1e-9, "row " + ri + ": a grid hole " + Math.min(h - s.x0, s.x1 - h).toFixed(3) + " from a row's end, under the " + M10 + " asked for");
    }
  });
  assert.ok(onGrid > 1000, "fixture: holes on the grid, " + onGrid);
});

test("stagger: with no shortest stitch given, a grid point is still never sewn ON a row's end", () => {
  // Nothing, a negative, not a number: no clearance at all, so a hole can sit
  // any distance from an end short of on it. (The builder always gives one.)
  for (const minStitch of [undefined, 0, -1, NaN]) {
    const pts = fill.tatamiFill(RECT, base({ stagger: 4, minStitch }));
    for (const d of stitchLengths(pts)) assert.ok(d > 1e-6, "minStitch " + minStitch + ": a stitch of no length");
    const rows = holesOf(pts, RECT, PITCH, 0);
    // a row whose slot is 0 has a grid point ON each end of this rectangle, and it is not sewn twice
    assert.deepStrictEqual(allHoles(rows[0]).map((x) => Math.round(x)), [4, 8, 12, 16, 20, 24, 28, 32, 36], "minStitch " + minStitch);
  }
});

test("stagger: a fill with no stitch length has nothing to stagger", () => {
  const opts = { rowSpacing: PITCH, angleDeg: 0 };
  assert.deepStrictEqual(fill.tatamiFill(RECT, Object.assign({}, opts, ON)), fill.tatamiFill(RECT, opts));
});

// ---- the builder ----------------------------------------------------------

const fingerprint = (d) => d.stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";");
const count = (d, k) => d.stitches.filter((s) => s.type === k).length;
const build = (extra) => DG.buildQualityDesign(
  [{ rgb: [10, 10, 10], shapes: [{ outer: rect(0, 0, 400, 200), holes: [], tierOverride: "fill" }, { outer: rect(600, 0, 300, 300), holes: [rect(700, 100, 100, 100)], tierOverride: "fill" }] },
   { rgb: [200, 30, 30], shapes: [{ outer: rect(0, 400, 250, 250), holes: [], tierOverride: "fill" }] }],
  Object.assign({ garment: { widthIn: 6, heightIn: 6 }, pxPerMm: 10, darkOnTop: false, underlay: true }, extra || {}));
// Every tatami pass the builder asks the fill module for, with what it asked
// and what it got. The builder looks the function up when it calls it.
function passes(extra) {
  const real = fill.tatamiFill, seen = [];
  fill.tatamiFill = (polys, opts) => { const pts = real(polys, opts); seen.push({ polys, opts, pts }); return pts; };
  try { return { design: build(extra), seen }; } finally { fill.tatamiFill = real; }
}

test("fillStagger (shapes): OFF by default, and the flag off is byte-identical to omitting it", () => {
  const omitted = build(), explicitOff = build({ fillStagger: false });
  assert.strictEqual(fingerprint(omitted), fingerprint(explicitOff));
  assert.deepStrictEqual(omitted.runs, explicitOff.runs);
  for (const p of passes().seen) assert.ok(!p.opts.stagger, "no pass is asked to stagger with the flag off");
});

test("fillStagger (shapes): ON staggers the cover fill of every shape, by the Python engine's cycle and shortest stitch", () => {
  const { seen } = passes({ fillStagger: true });
  const cover = seen.filter((p) => p.opts.stagger);
  assert.strictEqual(cover.length, 3, "fixture: three fill shapes, one cover pass each");
  for (const p of cover) {
    assert.strictEqual(p.opts.stagger, 4, "machine.FILL_STAGGERS");
    assert.ok(Math.abs(p.opts.minStitch / p.opts.maxStitch - 1.0 / 4) < 1e-12, "machine.MIN_STITCH_MM, in the fill's own units: " + p.opts.minStitch + " against a stitch of " + p.opts.maxStitch);
    assert.ok(Math.abs(p.opts.splitTol / p.opts.minStitch / 1e-6 - 1) < 1e-9, "stitches.SPLIT_TOLERANCE_MM, a micron in the fill's own units: " + p.opts.splitTol);
    const lined = inLine(holesOf(p.pts, p.polys, p.opts.rowSpacing, p.opts.angleDeg), 0.3 * p.opts.minStitch);
    assert.ok(lined.n > 200, "fixture: holes between the ends of the rows, " + lined.n);
    assert.strictEqual(lined.threes, 0, "three holes in a line, of " + lined.n);
    assert.ok(lined.pairs < 0.1 * lined.n, lined.pairs + " of " + lined.n + " holes with one under them");
  }
  for (const p of passes().seen.filter((q) => q.opts.rowSpacing === cover[0].opts.rowSpacing)) {
    const lined = inLine(holesOf(p.pts, p.polys, p.opts.rowSpacing, p.opts.angleDeg), 0.3 * cover[0].opts.minStitch);
    assert.ok(lined.threes > 0.9 * lined.n, "the defect, flag off: " + lined.threes + " of " + lined.n + " holes are the head of three in a line");
  }
  // the underlay is not a cover: its rows are far apart and hidden, and the
  // Python engine does not stagger them either (`_underlay_paths`, staggers=1)
  const under = seen.filter((p) => !p.opts.stagger);
  assert.ok(under.length >= 3, "fixture: underlay passes, " + under.length);
  const offUnder = passes().seen.filter((p) => p.opts.rowSpacing !== cover[0].opts.rowSpacing);
  assert.deepStrictEqual(under.map((p) => p.pts), offUnder.map((p) => p.pts), "every underlay pass is the one sewn with the flag off");
});

test("fillStagger: the split tolerance is the Python engine's, to the digit", () => {
  // `test_machine_wire.py` reads plain decimals and cannot see 1e-6, so this
  // one is held here: the number in stitches.py against the number in
  // digitize.js, both read off the source.
  const read = (file, re) => {
    const m = re.exec(fs.readFileSync(path.join(__dirname, "..", file), "utf8"));
    assert.ok(m, "no SPLIT_TOLERANCE_MM in " + file);
    return Number(m[1]);
  };
  const py = read("digitizer/digitizer_core/stitches.py", /^SPLIT_TOLERANCE_MM\s*=\s*([0-9.eE+-]+)/m);
  const js = read("src/digitize.js", /\bconst SPLIT_TOLERANCE_MM\s*=\s*([0-9.eE+-]+)/);
  assert.ok(py > 0 && py < 1e-3, "fixture: stitches.py says " + py);
  assert.strictEqual(js, py);
});

test("fillStagger (shapes): the design keeps its size, its colours, its cuts and its runs", () => {
  const off = build(), on = build({ fillStagger: true });
  assert.notStrictEqual(fingerprint(on), fingerprint(off), "the flag does something");
  assert.strictEqual(on.widthMM, off.widthMM);
  assert.strictEqual(on.heightMM, off.heightMM);
  for (const k of ["trim", "color", "jump", "end"]) assert.strictEqual(count(on, k), count(off, k), k + " records");
  assert.deepStrictEqual(on.runs.map((r) => r.kind + "/" + r.shape + "/" + r.block), off.runs.map((r) => r.kind + "/" + r.shape + "/" + r.block));
  assert.strictEqual(on.stitchCount, count(on, "stitch"), "the stitch count is the staggered stream's");
  const more = on.stitchCount / off.stitchCount - 1;
  assert.ok(more > -0.02 && more < 0.15, "stitches: " + off.stitchCount + " -> " + on.stitchCount);
});

test("fillStagger (shapes): with the column walk too", () => {
  const off = build({ fillColumns: true }), on = build({ fillColumns: true, fillStagger: true });
  assert.notStrictEqual(fingerprint(on), fingerprint(off));
  for (const k of ["trim", "color", "jump", "end"]) assert.strictEqual(count(on, k), count(off, k), k + " records");
  const { seen } = passes({ fillColumns: true, fillStagger: true });
  const holed = seen.find((p) => p.opts.stagger && p.polys.length === 2);
  assert.ok(holed && holed.pts.columnWalk, "fixture: the shape with a hole is sewn by the column walk");
  const lined = inLine(holesOf(holed.pts, holed.polys, holed.opts.rowSpacing, holed.opts.angleDeg), 0.3 * holed.opts.minStitch);
  assert.ok(lined.n > 200, "fixture: holes between the ends of the rows, " + lined.n);
  assert.strictEqual(lined.threes, 0, "three holes in a line, of " + lined.n);
  assert.ok(lined.pairs < 0.1 * lined.n, lined.pairs + " of " + lined.n + " holes with one under them");
});
