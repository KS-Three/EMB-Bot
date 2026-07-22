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
