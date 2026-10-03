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

// How many moves lay thread through the open interior of an axis-aligned box.
// `sewn` arrives at a plain point; `floats` arrives at a travel point that was
// not cut.
function threadThrough(pts, box, margin) {
  const e = margin == null ? 0.25 : margin;
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
// Row pitch UNDER the longest stitch, as every real caller has it (0.15 mm rows
// against 4 mm). The other way round, a plain row turn is already too long to
// sew and every test below would be measuring that instead.
const COLS = { rowSpacing:5, angleDeg:0, maxStitch:8, markConnectors:true, columns:true };

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
  // The margin is one row pitch, and that is the honest size of the claim. A
  // row turn inside ONE column joins two row ends that sit on adjacent edges
  // of the hole, and the chord between them clips the corner by less than the
  // pitch -- as it always has, and as the Python engine's does. That is 0.15 mm
  // on a real fill; here the rows are 5 apart, so it is 5.
  for (const angleDeg of [30, 45, 90, 137]) {
    const pts = fill.tatamiFill([SQ, WIDE_HOLE], Object.assign({}, COLS, { angleDeg }));
    assert.deepStrictEqual(threadThrough(pts, { x0:20, y0:20, x1:80, y1:80 }, COLS.rowSpacing), { sewn:0, floats:0 }, "angle " + angleDeg);
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
  assert.ok(onIsland.length >= 8, "island rows sewn: " + onIsland.length);   // 4 rows x 2 ends at least
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

test("columns: the first stitch after a cut lands on the span's own start", () => {
  // A trim point is where the frame goes, not a penetration. Without a plain
  // point on the same spot the row begins one stitch late.
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS);
  const cutAt = pts.map((p, i) => (p.trim ? i : -1)).filter((i) => i >= 0);
  assert.ok(cutAt.length > 0, "this ring needs a cut; without one the test proves nothing");
  for (const i of cutAt) {
    const next = pts[i + 1];
    assert.ok(next && !next.trim && !next.travel, "point after the cut at " + i + " is not a plain stitch");
    assert.deepStrictEqual({ x: next.x, y: next.y }, { x: pts[i].x, y: pts[i].y });
  }
});

test("columns: every span of every row is sewn end to end, its own start included", () => {
  // Rows at y = 0, 5, ... 95 (the scanline at 100 meets no edge). Rows 20..75
  // are split by the hole into [0,20] and [80,100]; the rest run [0,100].
  // Today the far span of a split row is reached by a float, and the point the
  // float lands on is a frame move, not a penetration: that span is sewn from
  // one stitch in (measured: [80,100] sews 84..100).
  const pts = fill.tatamiFill([SQ, WIDE_HOLE], COLS).filter((p) => !p.travel && !p.trim);
  for (let y = 0; y <= 95; y += 5) {
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

test("columns: a shape whose rows never fork sews exactly as it does today", () => {
  // One column is the whole shape, so there is no join to decide and nothing
  // may move -- center-out included, which the column walk does not do.
  const tall = [[{x:0,y:0},{x:40,y:0},{x:40,y:200},{x:0,y:200}]];
  for (const centerOut of [false, true]) {
    const base = { rowSpacing:10, angleDeg:30, maxStitch:12, markConnectors:true, centerOut };
    assert.deepStrictEqual(fill.tatamiFill(tall, Object.assign({ columns:true }, base)), fill.tatamiFill(tall, base));
  }
});
