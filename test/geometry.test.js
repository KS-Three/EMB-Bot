const assert = require("node:assert");
const { test } = require("node:test");
const geo = require("../src/geometry.js");
const fill = require("../src/fill.js");

function rectMask(w,h,x0,y0,x1,y1){ const m=new Uint8Array(w*h); for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)m[y*w+x]=1; return m; }

// --- helpers for hole-aware region tracing tests ---
function discMask(w,h,cx,cy,r){ const m=new Uint8Array(w*h); for(let y=0;y<h;y++)for(let x=0;x<w;x++){const dx=x-cx,dy=y-cy; if(dx*dx+dy*dy<=r*r) m[y*w+x]=1;} return m; }
function annulusMask(w,h,cx,cy,rOuter,rInner){ const m=discMask(w,h,cx,cy,rOuter); for(let y=0;y<h;y++)for(let x=0;x<w;x++){const dx=x-cx,dy=y-cy; if(dx*dx+dy*dy<=rInner*rInner) m[y*w+x]=0;} return m; }
function bbox(pts){ let minx=Infinity,miny=Infinity,maxx=-Infinity,maxy=-Infinity; for(const p of pts){ if(p.x<minx)minx=p.x; if(p.y<miny)miny=p.y; if(p.x>maxx)maxx=p.x; if(p.y>maxy)maxy=p.y;} return {minx,miny,maxx,maxy,cx:(minx+maxx)/2,cy:(miny+maxy)/2}; }

test("traces a single rectangle blob", () => {
  const w=10,h=10; const m=rectMask(w,h,2,2,8,7);
  const cs = geo.traceContours(m,w,h);
  assert.strictEqual(cs.length, 1);
  assert.ok(cs[0].length >= 4);
});
test("simplify reduces a straight run", () => {
  const pts=[{x:0,y:0},{x:1,y:0},{x:2,y:0},{x:3,y:0},{x:3,y:3}];
  const s=geo.simplify(pts,0.5);
  assert.ok(s.length < pts.length);
});
test("polygon area of 6x5 rect ~30", () => {
  const a=geo.polygonArea([{x:0,y:0},{x:6,y:0},{x:6,y:5},{x:0,y:5}]);
  assert.strictEqual(a,30);
});

test("diagonal staircase is one 8-connected blob, one clean contour", () => {
  const w=10,h=10; const m=new Uint8Array(w*h);
  for(let i=0;i<8;i++) m[i*w+i]=1;
  const cs = geo.traceContours(m,w,h);
  assert.strictEqual(cs.length, 1, "expected exactly 1 contour");
  // Not self-overlapping in the pathological (zero-area) way.
  assert.ok(geo.polygonArea(cs[0]) > 0, "contour must have positive area");
  // No absurd revisiting: length bounded well under the pixel budget.
  assert.ok(cs[0].length <= w*h, "contour length must be bounded");
});

test("area is strictly monotonic in blob size", () => {
  const w=12,h=12;
  const areaOf = (n) => {
    const m=rectMask(w,h,1,1,1+n,1+n);
    const cs = geo.traceContours(m,w,h);
    assert.strictEqual(cs.length, 1);
    return geo.polygonArea(cs[0]);
  };
  const a1=areaOf(1), a2=areaOf(2), a3=areaOf(3), a4=areaOf(4);
  assert.ok(a1 > 0, "1x1 area must be > 0");
  assert.ok(a1 < a2, `expected a1(${a1}) < a2(${a2})`);
  assert.ok(a2 < a3, `expected a2(${a2}) < a3(${a3})`);
  assert.ok(a3 < a4, `expected a3(${a3}) < a4(${a4})`);
});

test("two disjoint rectangles yield two contours", () => {
  const w=20,h=10;
  const m=new Uint8Array(w*h);
  const paint=(x0,y0,x1,y1)=>{for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)m[y*w+x]=1;};
  paint(1,1,4,4);
  paint(10,5,14,9);
  const cs = geo.traceContours(m,w,h);
  assert.strictEqual(cs.length, 2, "expected exactly 2 contours");
});

// ---------------------------------------------------------------------------
// traceRegions: hole-aware region tracing
// ---------------------------------------------------------------------------

test("traceRegions: solid disc has no holes", () => {
  const w=30,h=30;
  const m=discMask(w,h,15,15,10);
  const regions = geo.traceRegions(m,w,h);
  assert.strictEqual(regions.length, 1, "expected exactly 1 shape");
  assert.strictEqual(regions[0].holes.length, 0, "solid disc must have 0 holes");
  assert.ok(geo.polygonArea(regions[0].outer) > 0, "outer must have positive area");
});

test("traceRegions: annulus (ring) has exactly one centered hole", () => {
  const w=30,h=30;
  const m=annulusMask(w,h,15,15,12,6);
  const regions = geo.traceRegions(m,w,h);
  assert.strictEqual(regions.length, 1, "expected exactly 1 shape");
  const shape = regions[0];
  assert.strictEqual(shape.holes.length, 1, "ring must have exactly 1 hole");
  const holeArea = geo.polygonArea(shape.holes[0]);
  const outerArea = geo.polygonArea(shape.outer);
  assert.ok(holeArea > 0, `hole area must be > 0 (got ${holeArea})`);
  assert.ok(shape.holes[0].length >= 4, "hole ring must have >= 4 points");
  // Hole is clearly smaller than the outer boundary.
  assert.ok(holeArea < outerArea * 0.6, `hole area (${holeArea}) should be clearly < outer area (${outerArea})`);
  // Hole is roughly centered on (15,15) -> center of corner-space bbox ~ (15.5,15.5).
  const bb = bbox(shape.holes[0]);
  assert.ok(Math.abs(bb.cx - 15.5) <= 2.0, `hole center x (${bb.cx}) should be ~15.5`);
  assert.ok(Math.abs(bb.cy - 15.5) <= 2.0, `hole center y (${bb.cy}) should be ~15.5`);
});

test("traceRegions: two disjoint solid squares -> two shapes, no holes", () => {
  const w=30,h=15;
  const m=new Uint8Array(w*h);
  const paint=(x0,y0,x1,y1)=>{for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)m[y*w+x]=1;};
  paint(2,2,8,8);
  paint(18,4,26,12);
  const regions = geo.traceRegions(m,w,h);
  assert.strictEqual(regions.length, 2, "expected exactly 2 shapes");
  for (const r of regions) assert.strictEqual(r.holes.length, 0, "each solid square has 0 holes");
});

test("traceRegions: square with two separate square holes -> one shape, two holes", () => {
  const w=30,h=30;
  const m=rectMask(w,h,4,4,26,26); // solid square
  // Carve two separate holes, both fully enclosed and separated by foreground.
  const carve=(x0,y0,x1,y1)=>{for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)m[y*w+x]=0;};
  carve(8,8,12,12);
  carve(16,16,20,20);
  const regions = geo.traceRegions(m,w,h);
  assert.strictEqual(regions.length, 1, "expected exactly 1 shape");
  assert.strictEqual(regions[0].holes.length, 2, "expected exactly 2 holes");
  for (const hole of regions[0].holes) {
    assert.ok(hole.length >= 4, "each hole ring has >= 4 points");
    assert.ok(geo.polygonArea(hole) > 0, "each hole has positive area");
  }
});

test("traceRegions: even-odd fill respects the hole end-to-end (no stitches in the hole)", () => {
  const w=30,h=30;
  const m=annulusMask(w,h,15,15,12,6);
  const regions = geo.traceRegions(m,w,h);
  assert.strictEqual(regions.length, 1);
  const shape = regions[0];
  assert.strictEqual(shape.holes.length, 1);
  const pts = fill.tatamiFill([shape.outer, ...shape.holes], {rowSpacing:2, angleDeg:0, maxStitch:100});
  assert.ok(pts.length > 0, "fill must produce stitches in the ring body");
  // No stitch point may land inside the inner hole. Center in corner-space is ~(15.5,15.5).
  // If the hole were ignored, the fill would cover the center (dist ~0); respecting it
  // keeps every point on/outside the hole ring (dist ~>=6 from center).
  const cxf=15.5, cyf=15.5, innerR=6;
  for (const p of pts) {
    const d = Math.hypot(p.x - cxf, p.y - cyf);
    assert.ok(d >= innerR - 2, `stitch point (${p.x.toFixed(2)},${p.y.toFixed(2)}) at dist ${d.toFixed(2)} landed inside the hole`);
  }
});
