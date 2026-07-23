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
