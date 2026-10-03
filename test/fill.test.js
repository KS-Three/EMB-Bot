const assert = require("node:assert");
const { test } = require("node:test");
const fill = require("../src/fill.js");
const rect = [[{x:0,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}]];

test("tatami fills rows across a square", () => {
  const pts = fill.tatamiFill(rect, { rowSpacing:10, angleDeg:0, maxStitch:1000 });
  assert.ok(pts.length >= 18);            // ~10 rows * 2 endpoints
  assert.ok(pts.every(p => p.x>=-1 && p.x<=101 && p.y>=-1 && p.y<=101));
});
test("tatami respects maxStitch splitting", () => {
  const pts = fill.tatamiFill(rect, { rowSpacing:50, angleDeg:0, maxStitch:20 });
  // longest gap between consecutive same-row points <= 20 (+epsilon)
  for(let i=1;i<pts.length;i++){ const d=Math.hypot(pts[i].x-pts[i-1].x, pts[i].y-pts[i-1].y); assert.ok(d <= 20.5); }
});
test("running outline spaces points", () => {
  const pts = fill.runningOutline(rect[0], { stitchLen:25 });
  assert.ok(pts.length >= 16); // perimeter 400 / 25
});

test("markConnectors: no sew points laid across a hole", () => {
  // annulus: outer 100x100, hole 20..80 (even-odd)
  const outer = [{x:0,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}];
  const hole  = [{x:20,y:20},{x:80,y:20},{x:80,y:80},{x:20,y:80}];
  const pts = fill.tatamiFill([outer, hole], { rowSpacing:5, angleDeg:0, maxStitch:4, markConnectors:true });
  // no non-travel point strictly inside the hole interior
  const inHole = pts.filter(p => !p.travel && p.x>21 && p.x<79 && p.y>21 && p.y<79);
  assert.strictEqual(inHole.length, 0, "sew points inside hole: "+inHole.length);
  // travel points exist (the cross-hole connectors)
  assert.ok(pts.some(p => p.travel === true), "expected travel-flagged connectors");
  // non-travel consecutive gaps still respect maxStitch
  for (let i=1;i<pts.length;i++){
    if (pts[i].travel || pts[i-1].travel) continue;
    const d = Math.hypot(pts[i].x-pts[i-1].x, pts[i].y-pts[i-1].y);
    assert.ok(d <= 4.5, "gap "+d);
  }
});

test("markConnectors default off keeps old dense behavior", () => {
  const pts = fill.tatamiFill(rect, { rowSpacing:50, angleDeg:0, maxStitch:20 });
  assert.ok(pts.every(p => p.travel === undefined));
});

test("centerOut: same rows as sequential but interleaved-from-center emission order", () => {
  // tall rectangle 40 wide x 200 tall, horizontal rows every 10 → 21 rows.
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:1000 };
  const seq = fill.tatamiFill(tall, opts);
  const ctr = fill.tatamiFill(tall, Object.assign({ centerOut:true }, opts));
  // identical coverage: same point count and same SET of row y-values
  assert.strictEqual(ctr.length, seq.length, "point count must match sequential");
  const yset = (pts) => [...new Set(pts.map(p => Math.round(p.y * 1000)))].sort((a,b)=>a-b);
  assert.deepStrictEqual(yset(ctr), yset(seq), "same set of row y-values (no row dropped)");
  // same number of distinct rows
  assert.strictEqual(yset(ctr).length, yset(seq).length, "row count identical");
  // DIFFERENT emission order
  const asStr = (pts) => pts.map(p => p.x.toFixed(3)+","+p.y.toFixed(3)).join(";");
  assert.notStrictEqual(asStr(ctr), asStr(seq), "emission order must differ");
  // sequential's first emitted row is near an edge (minY = 0)
  assert.ok(Math.abs(seq[0].y - 0) <= 10 + 1e-6, "sequential starts near top edge, got y=" + seq[0].y);
  // center-out's first emitted row is within ~1 row spacing of the mid-y (100)
  assert.ok(Math.abs(ctr[0].y - 100) <= 10 + 1e-6, "center-out starts near mid-y, got y=" + ctr[0].y);
});

test("centerOut: two-sweep keeps inter-row repositions small (few long travels)", () => {
  // tall rectangle 40 wide x 200 tall, horizontal rows every 10 → 21 rows.
  // Each row is one span (x: 0..40); bbox width is 40. Big maxStitch so no
  // densification — inter-row connector moves stay as single points.
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:1000 };
  const ctr = fill.tatamiFill(tall, Object.assign({ centerOut:true }, opts));
  const xs = ctr.map(p => p.x);
  const bboxW = Math.max(...xs) - Math.min(...xs);
  const thresh = 0.6 * bboxW; // "long" reposition = > 60% of fill width
  // Connector (inter-row) moves land on EVEN indices (span-start arrivals);
  // within-row spans land on odd indices. Count only long inter-row moves.
  let longReposition = 0;
  for (let i = 2; i < ctr.length; i += 2) {
    const d = Math.hypot(ctr[i].x - ctr[i-1].x, ctr[i].y - ctr[i-1].y);
    if (d > thresh) longReposition++;
  }
  // Two-sweep: only the single sweep-to-sweep move is long (top edge → center).
  // The OLD interleaved order made nearly HALF the ~20 inter-row hops long
  // (full-width, same-parity jumps like mid-1 → mid+1), so this FAILS on
  // interleaved (~19) and PASSES on two-sweep (1).
  assert.ok(longReposition <= 2, "expected <=2 long inter-row repositions, got " + longReposition);
});

test("centerOut: exactly ONE trim flag, at the lower-sweep start (center reposition)", () => {
  // tall rectangle 40 wide x 200 tall, rows every 10 → 21 row groups.
  // Two-sweep: upper mid..0, lower mid+1..last. The single sweep-to-sweep move
  // (top edge → back near center) is the only long float and must be tagged trim.
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:1000, markConnectors:true, centerOut:true };
  const ctr = fill.tatamiFill(tall, opts);
  const trims = ctr.map((p,i)=>({p,i})).filter(({p}) => p.trim === true);
  assert.strictEqual(trims.length, 1, "exactly one trim flag in two-sweep output");
  const { p: tp, i: ti } = trims[0];
  // the trim point is the lower-sweep start → near shape vertical center (y≈100)
  assert.ok(Math.abs(tp.y - 100) <= 10 + 1e-6, "trim point near shape center, got y=" + tp.y);
  // it follows the last upper-sweep point, which is near an edge (y≈0)
  assert.ok(Math.abs(ctr[ti-1].y - 0) <= 10 + 1e-6, "point before trim near top edge, got y=" + ctr[ti-1].y);
});

test("centerOut: single row group (no lower sweep) has ZERO trim flags", () => {
  // short rectangle → only one row group at rowSpacing 10; no sweep-to-sweep move.
  const shortRect = [[{x:0,y:0},{x:40,y:0},{x:40,y:5},{x:0,y:5}]];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:1000, markConnectors:true, centerOut:true };
  const ctr = fill.tatamiFill(shortRect, opts);
  assert.ok(ctr.length > 0, "expected some points");
  assert.strictEqual(ctr.filter(p => p.trim === true).length, 0, "no trim flag when there is no lower sweep");
});

test("centerOut default off is byte-identical to sequential", () => {
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:1000 };
  const a = fill.tatamiFill(tall, opts);
  const b = fill.tatamiFill(tall, Object.assign({ centerOut:false }, opts));
  assert.deepStrictEqual(a, b, "centerOut:false must equal no-option");
});

// --- opts.columns: no thread across a hole or a notch ------------------------
//
// Measured 2026-10-02 on a 40 mm manual fill with two cut-outs: 76 untrimmed
// floats across the 12 mm one (912 mm of thread) and 20 stitches sewn straight
// across the 3 mm one. The needle never lands inside either, which is all
// "no sew points laid across a hole" above can see. These read the THREAD:
// every move from one point to the next is thread on the cloth unless the
// point it arrives at carries `trim`.
//
// The claim is "no thread DEEPER THAN ONE ROW PITCH into open ground", and the
// margin below is that pitch. Two things legitimately sit inside it: a row
// turn round a hole's corner, and the run the walk makes along a hole's top or
// bottom edge to get from one strip to the next, which lies on the last split
// row -- under a pitch from the rim. On a real fill the pitch is 0.15 mm.
const PITCH = 1;

// How many moves lay thread through the open interior of an axis-aligned box,
// taken `margin` in from its rim. `sewn` arrives at a plain point; `floats`
// arrives at a travel point that was not cut.
function threadThrough(pts, box, margin) {
  const e = margin == null ? PITCH : margin;
  const inside = (x, y) => x > box.x0 + e && x < box.x1 - e && y > box.y0 + e && y < box.y1 - e;
  let sewn = 0, floats = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (b.trim) continue;
    let hit = false;
    for (let s = 1; s < 40 && !hit; s++) {
      const t = s / 40;
      hit = inside(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
    }
    if (!hit) continue;
    if (b.travel) floats++; else sewn++;
  }
  return { sewn, floats };
}

const SQ = [{x:0,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}];
const WIDE_HOLE = [{x:20,y:20},{x:80,y:20},{x:80,y:80},{x:20,y:80}];
// Row pitch WELL UNDER the longest stitch, and holes well over it, as every
// real caller has it (0.15 mm rows, 4 mm stitches, holes of millimetres). With
// the pitch over the stitch a plain row turn is already too long to sew; with
// a hole under two pitches the engine treats it as closed. Either way the
// tests below would be measuring the fixture.
const COLS = { rowSpacing:PITCH, angleDeg:0, maxStitch:8, markConnectors:true, columns:true };

test("columns: no float is left across a hole wider than a stitch", () => {
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS);
  assert.deepStrictEqual(threadThrough(pts, { x0:20, y0:20, x1:80, y1:80 }), { sewn:0, floats:0 });
});

test("columns: a hole narrower than a stitch is not sewn across", () => {
  // 3 wide against maxStitch 8: today the connector is short enough to be a
  // plain stitch, so the hole is closed with thread on every row.
  const slot = [{x:48,y:20},{x:51,y:20},{x:51,y:80},{x:48,y:80}];
  const pts = fill.tatamiFill([SQ, slot], COLS);
  assert.deepStrictEqual(threadThrough(pts, { x0:48, y0:20, x1:51, y1:80 }), { sewn:0, floats:0 });
});

test("columns: no thread is carried across the open mouth of a U", () => {
  // Not a hole at all: a notch from the top edge. The rows fork into two arms
  // and the move between them runs over bare cloth outside the shape.
  const u = [{x:0,y:0},{x:30,y:0},{x:30,y:60},{x:70,y:60},{x:70,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}];
  const pts = fill.tatamiFill([u], COLS);
  assert.deepStrictEqual(threadThrough(pts, { x0:30, y0:0, x1:70, y1:60 }), { sewn:0, floats:0 });
});

test("columns: the hole stays clear whatever angle the rows run at", () => {
  // Real fills take their angle from the shape (PCA), so 0 is the rare case.
  // At an angle the rows meet the hole on a slant and the columns are wedges.
  //
  // This is where the one-pitch margin is earned: a row turn inside ONE
  // column joins two row ends that sit on adjacent edges of the hole, and the
  // chord between them clips the corner by less than the pitch -- as it always
  // has, and as the Python engine's does.
  for (const angleDeg of [30, 45, 90, 137]) {
    const pts = fill.tatamiFill([SQ, WIDE_HOLE], Object.assign({}, COLS, { angleDeg }));
    assert.deepStrictEqual(threadThrough(pts, { x0:20, y0:20, x1:80, y1:80 }), { sewn:0, floats:0 }, "angle " + angleDeg);
  }
});

test("columns: an island inside a hole is sewn, and the moat round it stays clear", () => {
  // Even-odd: outer, hole, island. Rows through the middle have THREE spans.
  const island = [{x:40,y:40},{x:60,y:40},{x:60,y:60},{x:40,y:60}];
  const pts = fill.tatamiFill([SQ, WIDE_HOLE, island], COLS);
  for (const moat of [{ x0:20, y0:20, x1:40, y1:80 }, { x0:60, y0:20, x1:80, y1:80 }, { x0:40, y0:20, x1:60, y1:40 }, { x0:40, y0:60, x1:60, y1:80 }]) {
    assert.deepStrictEqual(threadThrough(pts, moat), { sewn:0, floats:0 }, "moat " + JSON.stringify(moat));
  }
  const onIsland = pts.filter((p) => !p.travel && !p.trim && p.x >= 40 && p.x <= 60 && p.y >= 40 && p.y < 60);
  assert.ok(onIsland.length >= 40, "island rows sewn: " + onIsland.length);   // 20 rows x 2 ends at least
});

test("columns: a comb is sewn tooth by tooth, with nothing across the gaps", () => {
  // Three teeth off one spine: two notches, each 15 wide and 60 deep.
  const comb = [{x:0,y:0},{x:20,y:0},{x:20,y:60},{x:35,y:60},{x:35,y:0},{x:55,y:0},{x:55,y:60},{x:70,y:60},{x:70,y:0},{x:90,y:0},{x:90,y:100},{x:0,y:100}];
  const pts = fill.tatamiFill([comb], COLS);
  for (const gap of [{ x0:20, y0:0, x1:35, y1:60 }, { x0:55, y0:0, x1:70, y1:60 }]) {
    assert.deepStrictEqual(threadThrough(pts, gap), { sewn:0, floats:0 }, "gap " + JSON.stringify(gap));
  }
});

test("columns: a ring costs at most one cut", () => {
  // Four columns round a hole. Three joins are next-row moves along the outer
  // edge; the last has to get past the hole and is cut. Trimming every
  // hole-crossing would pass the three tests above and cost a cut per row.
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS);
  const cuts = pts.filter((p) => p.trim === true).length;
  assert.ok(cuts <= 1, "cuts round one hole: " + cuts);
});

test("columns: a row of holes costs one cut at most, not one per hole", () => {
  // Three holes side by side split their rows into four strips. Taking the
  // nearest reachable column next -- which is the band BELOW the holes --
  // strands three of the strips, and each then needs a cut to get back to:
  // 3 cuts measured here, 9 on the grid below, 64 to 126 on a 36-hole badge.
  // Finishing the level first, and stepping from strip to strip along a
  // hole's own top or bottom edge, leaves at most one: the last strip can end
  // at the wrong end for the band below.
  const hole = (x0) => [{x:x0,y:40},{x:x0+12,y:40},{x:x0+12,y:60},{x:x0,y:60}];
  const pts = fill.tatamiFill([SQ, hole(14), hole(44), hole(74)], COLS);
  const cuts = pts.filter((p) => p.trim === true).length;
  assert.ok(cuts <= 1, "cuts round a row of three holes: " + cuts);
  for (const x0 of [14, 44, 74]) {
    assert.deepStrictEqual(threadThrough(pts, { x0, y0:40, x1:x0 + 12, y1:60 }), { sewn:0, floats:0 }, "hole at " + x0);
  }
  // The step along a hole's edge is SEWN, so it obeys the stitch length too.
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].travel || pts[i].trim) continue;
    const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    assert.ok(d <= 8 + 1e-6, "stitch " + d + " at " + i);
  }
});

test("columns: a grid of holes costs a cut per ROW of holes at most", () => {
  const grid = [SQ];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const x = 12 + c * 30, y = 12 + r * 30;
    grid.push([{x, y}, {x:x + 12, y}, {x:x + 12, y:y + 12}, {x, y:y + 12}]);
  }
  const pts = fill.tatamiFill(grid, COLS);
  const cuts = pts.filter((p) => p.trim === true).length;
  assert.ok(cuts <= 3, "cuts on a 3 x 3 grid of holes: " + cuts);
  for (const h of grid.slice(1)) {
    assert.deepStrictEqual(threadThrough(pts, { x0:h[0].x, y0:h[0].y, x1:h[2].x, y1:h[2].y }), { sewn:0, floats:0 });
  }
});

test("columns: the first stitch after a cut lands on the span's own start", () => {
  // A trim point is where the frame goes, not a penetration. Without a plain
  // point on the same spot the row begins one stitch late. Two squares that
  // do not touch: nothing but a cut gets from one to the other.
  const far = [{x:200,y:0},{x:260,y:0},{x:260,y:60},{x:200,y:60}];
  const pts = fill.tatamiFill([SQ, far], COLS);
  const cutAt = pts.map((p, i) => (p.trim ? i : -1)).filter((i) => i >= 0);
  assert.ok(cutAt.length > 0, "two separate shapes need a cut; without one the test proves nothing");
  for (const i of cutAt) {
    const next = pts[i + 1];
    assert.ok(next && !next.trim && !next.travel, "point after the cut at " + i + " is not a plain stitch");
    assert.deepStrictEqual({ x: next.x, y: next.y }, { x: pts[i].x, y: pts[i].y });
  }
});

test("columns: every span of every row is sewn end to end, its own start included", () => {
  // Rows at y = 0, 1, ... 99 (the scanline at 100 meets no edge). Rows 20..79
  // are split by the hole into [0,20] and [80,100]; the rest run [0,100].
  // Today the far span of a split row is reached by a float, and the point the
  // float lands on is a frame move, not a penetration: that span is sewn from
  // one stitch in (measured with rows 5 apart: [80,100] sewed 86.7..100).
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS).filter((p) => !p.travel && !p.trim);
  for (let y = 0; y <= 99; y += PITCH) {
    const spans = y >= 20 && y < 80 ? [[0, 20], [80, 100]] : [[0, 100]];
    for (const [x0, x1] of spans) {
      const xs = pts.filter((p) => Math.abs(p.y - y) < 1e-6 && p.x >= x0 - 1e-6 && p.x <= x1 + 1e-6)
        .map((p) => p.x).sort((a, b) => a - b);
      assert.ok(xs.length >= 2, "row " + y + " span " + x0 + ".." + x1 + " has no stitches");
      assert.ok(Math.abs(xs[0] - x0) < 1e-6 && Math.abs(xs[xs.length - 1] - x1) < 1e-6,
        "row " + y + " span " + x0 + ".." + x1 + " sewn only " + xs[0] + ".." + xs[xs.length - 1]);
      for (let i = 1; i < xs.length; i++) assert.ok(xs[i] - xs[i - 1] <= 8 + 1e-6, "row " + y + " gap " + (xs[i] - xs[i - 1]));
    }
  }
});

test("columns: a plain shape sews exactly as it does today", () => {
  // Every row one span and every row turn inside the shape: there is nothing
  // to decide and nothing may move -- center-out included, which the column
  // walk does not do. At 30 degrees the rectangle's pointed corners make
  // consecutive rows that do not overlap, which is a column break and is not
  // a reason to change it.
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  for (const centerOut of [false, true]) {
    const base = { rowSpacing:10, angleDeg:30, maxStitch:12, markConnectors:true, centerOut };
    assert.deepStrictEqual(fill.tatamiFill(tall, Object.assign({ columns:true }, base)), fill.tatamiFill(tall, base));
  }
});

test("columns: rows that never fork are still cut where a row turn leaves the shape", () => {
  // No row of a T is split, so "does any row fork" sends it down the old walk,
  // whose turn from the bar's last row to the stem's first is a float outside
  // the outline. Rows 10 apart, as an underlay's are, with the tolerance a
  // fill's pitch: the turn runs 9 units outside the stem.
  const t = [{x:0,y:0},{x:120,y:0},{x:120,y:35},{x:75,y:35},{x:75,y:120},{x:45,y:120},{x:45,y:35},{x:0,y:35}];
  const opts = { rowSpacing:10, angleDeg:90, maxStitch:40, markConnectors:true, columns:true, openTol:1 };
  const pts = fill.tatamiFill([t], opts);
  // open ground either side of the stem, below the bar
  for (const side of [{ x0:0, y0:35, x1:45, y1:120 }, { x0:75, y0:35, x1:120, y1:120 }]) {
    assert.deepStrictEqual(threadThrough(pts, side, 1), { sewn:0, floats:0 }, JSON.stringify(side));
  }
});

// How many FLOATS (a travel point that was not cut) leave the shape at all:
// any point of the move outside the even-odd region and off its boundary.
function floatsOffShape(pts, polys) {
  const edges = [];
  for (const poly of polys) for (let i = 0; i < poly.length; i++) edges.push([poly[i], poly[(i + 1) % poly.length]]);
  const inside = (p) => {
    let c = false;
    for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c;
    return c;
  };
  const onEdge = (p) => edges.some(([u, v]) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
    const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)) <= 1e-6;
  });
  let n = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (!b.travel || b.trim) continue;
    let off = false;
    for (let s = 1; s < 400 && !off; s++) {
      const p = { x: a.x + (b.x - a.x) * s / 400, y: a.y + (b.y - a.y) * s / 400 };
      off = !inside(p) && !onEdge(p);
    }
    if (off) n++;
  }
  return n;
}

test("columns: a row turn longer than a stitch is not floated along the outside of the shape", () => {
  // A T with its rows along the bar. No row forks, and the turn from the bar's
  // last row (y 30) to the stem's first (y 31) runs 40 along the bar's
  // underside, half of it outside the outline -- by half a pitch, so it is not
  // "deep" and the walk is left alone. But the old walk FLOATS a turn that
  // long, and a float nothing covers is a loose thread along the edge: 28 mm
  // of it measured on a 35 mm T. On the rim it is sewn instead.
  const t = [{x:0,y:0},{x:100,y:0},{x:100,y:30.5},{x:60,y:30.5},{x:60,y:100},{x:40,y:100},{x:40,y:30.5},{x:0,y:30.5}];
  for (const centerOut of [false, true]) {
    const off = fill.tatamiFill([t], { rowSpacing:PITCH, angleDeg:0, maxStitch:8, markConnectors:true, centerOut });
    assert.ok(floatsOffShape(off, [t]) >= 1, "the fixture must float outside without columns, centerOut " + centerOut);
    const pts = fill.tatamiFill([t], Object.assign({}, COLS, { centerOut }));
    assert.strictEqual(floatsOffShape(pts, [t]), 0, "centerOut " + centerOut);
    // and what replaced the float is stitches no longer than a stitch
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].travel || pts[i].trim) continue;
      const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
      assert.ok(d <= 8 + 1e-6, "stitch " + d + " at " + i + ", centerOut " + centerOut);
    }
  }
});

test("columns: no float leaves the shape, forked or not", () => {
  const u = [{x:0,y:0},{x:30,y:0},{x:30,y:60},{x:70,y:60},{x:70,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}];
  const stairs = [{x:0,y:0},{x:30,y:0},{x:30,y:30.5},{x:60,y:30.5},{x:60,y:60.5},{x:100,y:60.5},{x:100,y:100},{x:0,y:100}];
  const cases = { ring: [SQ, WIDE_HOLE], u: [u], stairs: [stairs] };
  for (const name of Object.keys(cases)) {
    for (const angleDeg of [0, 90, 30]) {
      for (const centerOut of [false, true]) {
        const pts = fill.tatamiFill(cases[name], Object.assign({}, COLS, { angleDeg, centerOut }));
        assert.strictEqual(floatsOffShape(pts, cases[name]), 0, name + " at " + angleDeg + ", centerOut " + centerOut);
      }
    }
  }
});

test("columns: with center-out, the row turns asked about are the ones the walk makes", () => {
  // Center-out sews its upper half from the middle UP, so its turns are the
  // other diagonal of each pair of rows. An L with one step: taken top-down
  // the turn at the step runs down the left edge; taken bottom-up it runs from
  // the wide row's far end back to the narrow one, 4 units deep over open
  // ground. Asking about the top-down turns passed it as plain.
  const l = [{x:0,y:0},{x:35,y:0},{x:35,y:35},{x:120,y:35},{x:120,y:200},{x:0,y:200}];
  const opts = { rowSpacing:10, angleDeg:0, maxStitch:40, markConnectors:true, columns:true, openTol:1, centerOut:true };
  const pts = fill.tatamiFill([l], opts);
  assert.deepStrictEqual(threadThrough(pts, { x0:35, y0:0, x1:120, y1:35 }, 1), { sewn:0, floats:0 });
});

// --- travel: getting the cuts back -------------------------------------------
//
// A cut leaves two thread ends, and nothing in the browser lanes locks them.
// The walk above cut whenever the next column could not be reached by one
// stitch or a run along the row. Measured on the first rebuild: one cut per
// HOLE in the fill wherever the holes did not line up with the rows (nine
// round holes at the angle the engine picks: nine), and one per strip in an
// underlay, whose rows are too far apart for the run along the row to stay on
// the hole's rim (a 36-hole badge at 30 degrees: 59 to 105 cuts).
const cutsOf = (pts) => pts.filter((p) => p.trim === true).length;
const noLongStitch = (pts, max, label) => {
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].travel || pts[i].trim) continue;
    const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    assert.ok(d <= max + 1e-6, label + ": stitch " + d + " at " + i);
  }
};

test("columns: a hole costs no cut -- the last strip is entered from its far end", () => {
  // The band above, a strip either side of the hole, the band below. Sewn
  // down one strip and up the other, the walk ends at the TOP of the second
  // strip with the band below still to sew. Run along that strip's own edge
  // to its top first, and sewn back DOWN, it ends beside the band instead.
  // The run lies on the strip's edge, under the ends of its own rows.
  for (const angleDeg of [0, 30, 45, 90, 137]) {
    const pts = fill.tatamiFill([SQ, WIDE_HOLE], Object.assign({}, COLS, { angleDeg }));
    assert.strictEqual(cutsOf(pts), 0, "angle " + angleDeg);
    assert.deepStrictEqual(threadThrough(pts, { x0:20, y0:20, x1:80, y1:80 }), { sewn:0, floats:0 }, "angle " + angleDeg);
    assert.strictEqual(floatsOffShape(pts, [SQ, WIDE_HOLE]), 0, "angle " + angleDeg);
    noLongStitch(pts, 8, "angle " + angleDeg);
  }
});

test("columns: holes cost no cut whether or not they line up with the rows", () => {
  const grid = [SQ];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const x = 12 + c * 30, y = 12 + r * 30;
    grid.push([{x, y}, {x:x + 12, y}, {x:x + 12, y:y + 12}, {x, y:y + 12}]);
  }
  for (const angleDeg of [0, 15, 30, 60]) {
    const pts = fill.tatamiFill(grid, Object.assign({}, COLS, { angleDeg }));
    assert.strictEqual(cutsOf(pts), 0, "angle " + angleDeg);
    for (const h of grid.slice(1)) {
      assert.deepStrictEqual(threadThrough(pts, { x0:h[0].x, y0:h[0].y, x1:h[2].x, y1:h[2].y }), { sewn:0, floats:0 }, "angle " + angleDeg);
    }
    assert.strictEqual(floatsOffShape(pts, grid), 0, "angle " + angleDeg);
    noLongStitch(pts, 8, "angle " + angleDeg);
  }
});

test("columns: rows far apart go round a hole's rim -- not through it, and not by a cut", () => {
  // An underlay: rows 5 apart, allowed 1 into open ground. The run along the
  // row to the next strip would lie up to 5 inside the hole, so the first
  // rebuild cut there, once per strip. The hole's own edge is the way round.
  const under = { rowSpacing:5, angleDeg:0, maxStitch:8, markConnectors:true, columns:true, openTol:1 };
  const hole = (x0) => [{x:x0,y:40},{x:x0+12,y:40},{x:x0+12,y:62},{x:x0,y:62}];
  const cases = { ring: [SQ, WIDE_HOLE], row: [SQ, hole(14), hole(44), hole(74)] };
  for (const name of Object.keys(cases)) {
    for (const angleDeg of [0, 90, 30]) {
      const pts = fill.tatamiFill(cases[name], Object.assign({}, under, { angleDeg }));
      assert.strictEqual(cutsOf(pts), 0, name + " at " + angleDeg);
      for (const h of cases[name].slice(1)) {
        assert.deepStrictEqual(threadThrough(pts, { x0:h[0].x, y0:h[0].y, x1:h[2].x, y1:h[2].y }, 1), { sewn:0, floats:0 }, name + " at " + angleDeg);
      }
      assert.strictEqual(floatsOffShape(pts, cases[name]), 0, name + " at " + angleDeg);
      noLongStitch(pts, 8, name + " at " + angleDeg);
    }
  }
});

test("columns: the way round an edge has a budget, and past it the thread is cut", () => {
  // A slit 3 thick and 90 deep, cut in from the right edge between two rows
  // that are 5 apart. The turn from one row to the next is 5 long and crosses
  // the slit's mouth; the way round the slit's edge is 185. The budget is the
  // larger of `travelBudget` and four times the straight line (as the Python
  // engine's is): 185 of travel to save one cut is over 40, and under 2000.
  const slit = [{x:0,y:0},{x:100,y:0},{x:100,y:51},{x:10,y:51},{x:10,y:54},{x:100,y:54},{x:100,y:100},{x:0,y:100}];
  const under = { rowSpacing:5, angleDeg:0, maxStitch:8, markConnectors:true, columns:true, openTol:1 };
  const tight = fill.tatamiFill([slit], Object.assign({}, under, { travelBudget: 40 }));
  const loose = fill.tatamiFill([slit], Object.assign({}, under, { travelBudget: 2000 }));
  assert.strictEqual(cutsOf(tight), 1, "tight budget");
  assert.strictEqual(cutsOf(loose), 0, "loose budget");
  for (const pts of [tight, loose]) {
    assert.deepStrictEqual(threadThrough(pts, { x0:10, y0:51, x1:100, y1:54 }, 1), { sewn:0, floats:0 });
    noLongStitch(pts, 8, "slit");
  }
});

test("columns: told where the thread is, the walk starts from a corner it can reach without a cut", () => {
  // A pass begins with a float from wherever the last one ended, and the
  // caller cuts that float if it crosses a hole. The walk always began at the
  // top left, so a pass entered from below the hole cost a cut before its
  // first stitch. `from` is where the thread is; `clear(a, b)` is the caller's
  // own test of a float. From the bottom edge the walk sews bottom-up.
  const shape = [SQ, WIDE_HOLE];
  const clear = (a, b) => !fill.crossesOpenGround(a, b, shape, PITCH, 0);
  for (const from of [{ x:50, y:100 }, { x:100, y:90 }, { x:0, y:0 }, { x:50, y:0 }]) {
    assert.strictEqual(clear(from, fill.tatamiFill(shape, COLS)[0]), from.y < 20, "the fixture: only from above is the old start clear");
    const pts = fill.tatamiFill(shape, Object.assign({}, COLS, { from, clear }));
    assert.ok(clear(from, pts[0]), "from " + JSON.stringify(from) + " it starts at " + JSON.stringify({ x: pts[0].x, y: pts[0].y }));
    assert.strictEqual(cutsOf(pts), 0, "from " + JSON.stringify(from));
    assert.deepStrictEqual(threadThrough(pts, { x0:20, y0:20, x1:80, y1:80 }), { sewn:0, floats:0 });
    // and every row is still sewn end to end
    const sewn = pts.filter((p) => !p.travel && !p.trim);
    for (let y = 0; y <= 99; y += 7) {
      const spans = y >= 20 && y < 80 ? [[0, 20], [80, 100]] : [[0, 100]];
      for (const [x0, x1] of spans) {
        const xs = sewn.filter((p) => Math.abs(p.y - y) < 1e-6 && p.x >= x0 - 1e-6 && p.x <= x1 + 1e-6).map((p) => p.x);
        assert.ok(Math.abs(Math.min(...xs) - x0) < 1e-6 && Math.abs(Math.max(...xs) - x1) < 1e-6, "row " + y + " span " + x0 + ".." + x1);
      }
    }
  }
});
