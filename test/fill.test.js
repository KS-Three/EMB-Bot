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

test("columns: the way round an edge has a budget, which decides where the walk can afford to go", () => {
  // Two slits 3 thick, cut in from either side between two rows that are 5
  // apart, leaving a neck 10 wide in the middle. The turn from one row to the
  // next is 5 long and crosses a slit's mouth at EITHER end; the way round a
  // slit's closed end to the start of the next row is 95. The budget is the
  // larger of `travelBudget` and four times the straight line (as the Python
  // engine's is). Under 2000 the walk takes that way and sews on downward.
  // Under 40 it cannot: 95 of travel for a move of 5. But the FAR end of what
  // is left is 45 away, which allows 180, and round the slit and down the
  // edge is 135: so it goes there and sews the rest from the bottom up.
  // Either way nothing is cut and no slit is crossed.
  const slits = [{x:0,y:0},{x:100,y:0},{x:100,y:51},{x:55,y:51},{x:55,y:54},{x:100,y:54},{x:100,y:100},{x:0,y:100},{x:0,y:54},{x:45,y:54},{x:45,y:51},{x:0,y:51}];
  const under = { rowSpacing:5, angleDeg:0, maxStitch:8, markConnectors:true, columns:true, openTol:1 };
  const tight = fill.tatamiFill([slits], Object.assign({}, under, { travelBudget: 40 }));
  const loose = fill.tatamiFill([slits], Object.assign({}, under, { travelBudget: 2000 }));
  // the first stitch laid ALONG row y
  const sewn = (pts, y) => pts.findIndex((p, i) => i > 0 && Math.abs(p.y - y) < 1e-6 && Math.abs(pts[i - 1].y - y) < 1e-6);
  assert.ok(sewn(tight, 95) < sewn(tight, 55), "tight budget: the rest is sewn from the bottom up");
  assert.ok(sewn(loose, 55) < sewn(loose, 95), "loose budget: the rest is sewn on downward");
  for (const pts of [tight, loose]) {
    assert.strictEqual(cutsOf(pts), 0);
    for (const mouth of [{ x0:55, y0:51, x1:100, y1:54 }, { x0:0, y0:51, x1:45, y1:54 }]) {
      assert.deepStrictEqual(threadThrough(pts, mouth, 1), { sewn:0, floats:0 });
    }
    noLongStitch(pts, 8, "slits");
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

test("columns: the run to a strip's far end is laid BEFORE the strip, under its own row ends", () => {
  // Either way the hole costs no cut: run up the strip's side first and sew
  // back down, or sew up it and then find a way back down its side. The
  // second lays the run ON TOP of the row ends it passes. Every long move
  // along a side of the square or of the hole must come before the rows of
  // its own strip that it runs past.
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS);
  assert.strictEqual(cutsOf(pts), 0);
  let sideRuns = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (Math.abs(a.x - b.x) > 1e-6 || Math.abs(b.y - a.y) < 2 * PITCH + 1e-6) continue;   // along a side, past more than one row
    sideRuns++;
    const strip = a.x <= 20 ? [0, 20] : [80, 100], y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
    for (let j = 0; j < i; j++) {
      const p = pts[j];
      assert.ok(!(p.y > y0 + 1e-6 && p.y < y1 - 1e-6 && p.x >= strip[0] - 1e-6 && p.x <= strip[1] + 1e-6 && Math.abs(p.x - a.x) > 1e-6),
        "the run at " + i + " (" + a.x + "," + a.y + " to " + b.y + ") passes a row already sewn: point " + j + " at " + p.x + "," + p.y);
    }
  }
  assert.ok(sideRuns >= 5, "this ring is sewn with a run up one strip; without one the test proves nothing: " + sideRuns);
});

test("columns: found by the second audit, on direct calls", () => {
  // The center-out reposition is cut only when connectors are marked. A
  // caller that does not mark them had it SEWN, across whatever it crossed:
  // 23 units through the corner of an L, 10.8 deep.
  const l = [{x:0,y:0},{x:100,y:0},{x:100,y:35},{x:35,y:35},{x:35,y:100},{x:0,y:100}];
  const unmarked = fill.tatamiFill([l], { rowSpacing:5, angleDeg:0, maxStitch:8, columns:true, centerOut:true });
  assert.deepStrictEqual(threadThrough(unmarked, { x0:35, y0:35, x1:100, y1:100 }, 5.5), { sewn:0, floats:0 }, "center-out, connectors not marked");
  // A slit 0.06 wide under a tolerance of 0.005: the move was sampled no
  // finer than a 4000th of its length, and the slit fell between two samples.
  const bar = [{x:0,y:0},{x:400,y:0},{x:400,y:60},{x:0,y:60}];
  const slit = [{x:200.0455,y:10},{x:200.1055,y:10},{x:200.1055,y:50},{x:200.0455,y:50}];
  const fine = fill.tatamiFill([bar, slit], { rowSpacing:5, angleDeg:0, maxStitch:40, markConnectors:true, columns:true, openTol:0.005 });
  assert.deepStrictEqual(threadThrough(fine, { x0:200.0455, y0:10, x1:200.1055, y1:50 }, 0.006), { sewn:0, floats:0 }, "a slit thinner than the old sampling step");
  // A tolerance far over the row pitch, and a float that left the shape
  // between two samples of ITS length.
  const stairs = [{x:0,y:0},{x:75,y:0},{x:75,y:75},{x:150,y:75},{x:150,y:150},{x:225,y:150},{x:225,y:225},{x:300,y:225},{x:300,y:300},{x:0,y:300}];
  const loose = fill.tatamiFill([stairs], { rowSpacing:21.2241, angleDeg:90, maxStitch:40, markConnectors:true, columns:true, openTol:42.4483 });
  assert.strictEqual(floatsOffShape(loose, [stairs]), 0, "a float outside under a loose tolerance");
});

test("columns: `ground` is where thread may lie, when that is not the pass's own outline", () => {
  // An underlay is sewn to the drawn outline, but the fill over it reaches 3
  // further into every hole. Rows 8 apart turn round a round hole by clipping
  // it by more than the 0.3 allowed -- and by far less than the 3 the fill
  // covers. Judged against the underlay's own outline that is open ground:
  // the column is cut in two at every such turn and the thread goes round the
  // rim instead, 212 points and 1,555 of thread. Told the ground, the turn is
  // one stitch: 180 points and 1,322.
  const circle = (r) => Array.from({ length: 48 }, (_, i) => ({ x: 50 + r * Math.cos(2 * Math.PI * i / 48), y: 50 + r * Math.sin(2 * Math.PI * i / 48) }));
  const grown = [{x:-3,y:-3},{x:103,y:-3},{x:103,y:103},{x:-3,y:103}];
  const under = { rowSpacing:8, angleDeg:0, maxStitch:8, markConnectors:true, columns:true, openTol:0.3 };
  const own = fill.tatamiFill([SQ, circle(20)], under);
  const told = fill.tatamiFill([SQ, circle(20)], Object.assign({ ground: [grown, circle(17)] }, under));
  assert.ok(told.length <= own.length - 20, "points: told the ground " + told.length + ", own outline " + own.length);
  for (const pts of [own, told]) assert.strictEqual(cutsOf(pts), 0);
  // and told, no thread goes deeper than the tolerance past what the fill covers
  for (let i = 1; i < told.length; i++) {
    if (told[i].trim) continue;
    for (let s = 1; s < 20; s++) {
      const x = told[i - 1].x + (told[i].x - told[i - 1].x) * s / 20, y = told[i - 1].y + (told[i].y - told[i - 1].y) * s / 20;
      assert.ok(Math.hypot(x - 50, y - 50) > 17 - 0.3 - 1e-6, "thread " + (17 - Math.hypot(x - 50, y - 50)).toFixed(2) + " past the cover at " + i);
    }
  }
});

test("columns: the way round a curve does not put a stitch on every point it was traced with", () => {
  // A round hole drawn with 200 points, 0.63 apart. A way round its rim that
  // keeps every vertex is a stitch every 0.63: 2,561 stitches under 0.3 mm in
  // the underlay of one 60 mm shape traced with 3,000 points. A vertex is
  // kept only where skipping it would take the thread more than the tolerance
  // off the ring. (The Python engine met the same thing and floors it too.)
  const round = Array.from({ length: 200 }, (_, i) => ({ x: 50 + 20 * Math.cos(2 * Math.PI * i / 200), y: 50 + 20 * Math.sin(2 * Math.PI * i / 200) }));
  for (const opts of [COLS, { rowSpacing:5, angleDeg:0, maxStitch:8, markConnectors:true, columns:true, openTol:1 }]) {
    const pts = fill.tatamiFill([SQ, round], opts);
    let short = 0;
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].travel || pts[i].trim) continue;
      const a = pts[i - 1], b = pts[i], d = Math.hypot(b.x - a.x, b.y - a.y);
      // off the rows: a row turn is one pitch long by design
      if (d < 0.9 && Math.abs(Math.abs(b.y - a.y) - opts.rowSpacing) > 1e-6) short++;
    }
    assert.ok(short <= 8, "stitches under 0.9 long, rows " + opts.rowSpacing + " apart: " + short);
    assert.strictEqual(cutsOf(pts), 0);
    // and the thinned way round still keeps out of the hole: 1 deep at most
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].trim) continue;
      const a = pts[i - 1], b = pts[i];
      for (let s = 1; s < 20; s++) {
        const x = a.x + (b.x - a.x) * s / 20, y = a.y + (b.y - a.y) * s / 20;
        assert.ok(Math.hypot(x - 50, y - 50) > 20 - 1 - 1e-6, "thread " + (20 - Math.hypot(x - 50, y - 50)).toFixed(2) + " deep in the hole at " + i);
      }
    }
  }
});

test("columns: a run along a strip's side does not cut across a corner of the edge it follows", () => {
  // Found by the random shapes below, at 9,000 of them; kept here because 150
  // do not happen to contain one. The run to a strip's far end goes from row
  // end to row end, as far as one stitch reaches while it stays within the
  // tolerance of every row end it passes. Past several rows that is not
  // enough: the edge of this round hole turns between two rows, and a leg
  // 3.5 long went 0.39 into the hole on a tolerance of 0.3.
  const P = (a) => a.map(([x, y]) => ({ x, y }));
  const polys = [
    P([[25.659,74.07],[44.272,44.383],[73.922,25.711],[108.737,21.753],[141.822,33.293],[166.623,58.045],[178.229,91.106],[174.341,125.93],[155.728,155.617],[126.078,174.289],[91.263,178.247],[58.178,166.707],[33.377,141.955],[21.771,108.894]]),
    P([[101.948,154.014],[98.148,158.004],[92.863,159.56],[87.507,158.265],[83.516,154.466],[81.96,149.18],[83.255,143.824],[87.055,139.834],[92.34,138.277],[97.696,139.573],[101.687,143.372],[103.243,148.658]]),
    P([[146.443,142.717],[128.565,130.137],[141.144,112.259],[159.023,124.839]]),
    P([[135.469,64.762],[136.03,62.858],[135.39,60.52],[137.063,59.069],[139.046,58.439],[140.903,58.353],[142.756,57.481],[144.387,58.614],[145.405,60.123],[147.388,60.9],[147.438,62.869],[147.27,64.641],[146.938,66.407],[146.774,68.783],[145.057,70.242],[142.877,70.83],[140.741,70.186],[139.386,68.423],[137.373,68.152],[136.103,66.647]]),
    P([[37.232,112.128],[40.885,115.517],[39.776,120.374],[35.015,121.842],[31.363,118.454],[32.472,113.596]]),
    P([[89.012,61.543],[92.984,63.615],[95.388,67.396],[95.579,71.873],[93.507,75.845],[89.726,78.249],[85.25,78.44],[81.277,76.367],[78.874,72.587],[78.682,68.11],[80.755,64.138],[84.536,61.734]]),
  ];
  const pts = fill.tatamiFill(polys, { rowSpacing:1, angleDeg:282.32, maxStitch:12, markConnectors:true, columns:true, openTol:0.3 });
  const edges = [];
  for (const p of polys) for (let i = 0; i < p.length; i++) edges.push([p[i], p[(i + 1) % p.length]]);
  let deepest = 0;
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].trim) continue;
    const a = pts[i - 1], b = pts[i], n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.y - a.y) / 0.05));
    for (let k = 0; k < n; k++) {
      const p = { x: a.x + (b.x - a.x) * (k + 0.5) / n, y: a.y + (b.y - a.y) * (k + 0.5) / n };
      let inside = false, d = Infinity;
      for (const [u, v] of edges) {
        if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) inside = !inside;
        const dx = v.x - u.x, dy = v.y - u.y, t = Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / (dx * dx + dy * dy)));
        d = Math.min(d, Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)));
      }
      if (!inside) deepest = Math.max(deepest, d);
    }
  }
  assert.ok(deepest <= 0.3 * 1.2, "deepest thread in open ground: " + deepest.toFixed(3));
});

// --- shapes nobody chose -------------------------------------------------------
//
// Every fixture above was drawn by whoever wrote the code it tests, and that
// is how two builds of this walk passed their tests and failed an audit. These
// are drawn by a seeded generator: stars and staircase blobs, up to five holes
// each, any row angle, rows 1 to 5 apart, tolerances from a quarter of the
// pitch up. What must hold on every one of them is what must hold on any
// shape. (It has already paid: a check taken out as "unreachable" was put back
// when 1 case in 3,000 went 1.4 deep on a tolerance of 1. The 150 here are what
// the suite can afford; 9,000 were run by hand before this was written.)
test("columns: 150 shapes nobody chose -- no thread in open ground, no float off the shape, every row sewn", () => {
  let seed = 20261003;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const star = (cx, cy, r, n, rough) => {
    const ph = rnd() * Math.PI * 2, pts = [];
    for (let i = 0; i < n; i++) {
      const a = ph + (2 * Math.PI * i) / n, rr = r * (1 - rough * rnd());
      pts.push({ x: cx + rr * Math.cos(a), y: cy + rr * Math.sin(a) });
    }
    return pts;
  };
  const stairs = (w, h) => {
    const steps = 2 + Math.floor(rnd() * 4), top = [], bottom = [];
    let x = 0;
    for (let i = 0; i < steps; i++) {
      const nx = i === steps - 1 ? w : x + (w - x) * (0.2 + 0.5 * rnd());
      const y0 = h * 0.4 * rnd(), y1 = h * (0.6 + 0.4 * rnd());
      top.push({ x, y: y0 }, { x: nx, y: y0 });
      bottom.push({ x, y: y1 }, { x: nx, y: y1 });
      x = nx;
    }
    return top.concat(bottom.reverse());
  };
  const edgesOf = (polys) => { const e = []; for (const p of polys) for (let i = 0; i < p.length; i++) e.push([p[i], p[(i + 1) % p.length]]); return e; };
  const inside = (p, edges) => { let c = false; for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c; return c; };
  const depth = (p, edges) => {
    let m = Infinity;
    for (const [u, v] of edges) {
      const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
      const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
      m = Math.min(m, Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)));
    }
    return m;
  };
  let cuts = 0;
  for (let t = 0; t < 150; t++) {
    const outer = rnd() < 0.67 ? star(100, 100, 60 + 40 * rnd(), 5 + Math.floor(rnd() * 30), pick([0, 0.2, 0.5])) : stairs(160 + 60 * rnd(), 120 + 80 * rnd());
    const polys = [outer], outerEdges = edgesOf([outer]), placed = [];
    for (let h = Math.floor(rnd() * 6); h > 0; h--) {
      for (let tries = 0; tries < 20; tries++) {
        const c = { x: 20 + 180 * rnd(), y: 20 + 180 * rnd() }, r = 4 + 16 * rnd();
        if (!inside(c, outerEdges) || depth(c, outerEdges) < r + 4) continue;
        if (placed.some((q) => Math.hypot(q.c.x - c.x, q.c.y - c.y) < q.r + r + 3)) continue;
        polys.push(star(c.x, c.y, r, pick([4, 4, 6, 12, 20]), pick([0, 0, 0.3])));
        placed.push({ c, r });
        break;
      }
    }
    const pitch = pick([1, 1, 2.5, 5]), maxStitch = pick([8, 8, 12]), tol = pick([pitch, pitch, 1, 0.3]);
    const opts = { rowSpacing: pitch, angleDeg: pick([0, 90, 30, 45, 137, 360 * rnd()]), maxStitch, markConnectors: true, columns: true, openTol: tol, centerOut: rnd() < 0.3 };
    const label = "shape " + t + " " + JSON.stringify(opts);
    const edges = edgesOf(polys);
    const pts = fill.tatamiFill(polys, opts);
    cuts += cutsOf(pts);
    for (let i = 1; i < pts.length; i++) {
      const a = pts[i - 1], b = pts[i];
      assert.ok(isFinite(b.x) && isFinite(b.y), label);
      if (b.trim) continue;
      const len = Math.hypot(b.x - a.x, b.y - a.y);
      if (!b.travel) assert.ok(len <= maxStitch + 1e-6, label + ": a stitch " + len.toFixed(2) + " long at " + i);
      const n = Math.max(1, Math.ceil(len / (tol / 3)));
      for (let k = 0; k < n; k++) {
        const p = { x: a.x + (b.x - a.x) * (k + 0.5) / n, y: a.y + (b.y - a.y) * (k + 0.5) / n };
        if (inside(p, edges)) continue;
        const d = depth(p, edges);
        // the walk samples at a quarter of the tolerance, so it sees to about 1.2 of it
        assert.ok(d <= tol * 1.3 + 1e-6, label + ": thread " + d.toFixed(3) + " deep at " + i);
        if (b.travel) assert.ok(d <= 1e-4, label + ": a float " + d.toFixed(4) + " outside at " + i);
      }
    }
    // every row's spans are sewn: the thread laid along scanlines adds up to them
    const th = (opts.angleDeg * Math.PI) / 180, cn = Math.cos(-th), sn = Math.sin(-th);
    const rot = (p) => ({ x: p.x * cn - p.y * sn, y: p.x * sn + p.y * cn });
    const turned = edges.map(([u, v]) => [rot(u), rot(v)]);
    let minY = Infinity, maxY = -Infinity, want = 0, got = 0;
    for (const [u] of turned) { minY = Math.min(minY, u.y); maxY = Math.max(maxY, u.y); }
    for (let y = minY; y <= maxY + 1e-9; y += pitch) {
      const xs = [];
      for (const [u, v] of turned) {
        if (u.y === v.y) continue;
        if (y >= Math.min(u.y, v.y) && y < Math.max(u.y, v.y)) xs.push(u.x + ((y - u.y) / (v.y - u.y)) * (v.x - u.x));
      }
      xs.sort((p, q) => p - q);
      for (let i = 0; i + 1 < xs.length; i += 2) want += xs[i + 1] - xs[i];
    }
    for (let i = 1; i < pts.length; i++) {
      if (pts[i].travel || pts[i].trim) continue;
      const a = rot(pts[i - 1]), b = rot(pts[i]);
      if (Math.abs(a.y - b.y) < 1e-6) got += Math.abs(b.x - a.x);
    }
    assert.ok(got >= want - 1e-3 * Math.max(1, want), label + ": rows sewn " + got.toFixed(1) + " of " + want.toFixed(1));
  }
  // and what the travel is for: the cuts left are nearly all center-out's own
  assert.ok(cuts <= 12, "cuts over the 150 shapes: " + cuts);
});
