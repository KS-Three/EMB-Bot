const assert = require("node:assert");
const { test } = require("node:test");
const geo = require("../src/geometry.js");

function rectMask(w,h,x0,y0,x1,y1){ const m=new Uint8Array(w*h); for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)m[y*w+x]=1; return m; }

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
