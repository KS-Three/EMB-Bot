const assert = require("node:assert");
const { test } = require("node:test");
const m = require("../src/stitchModel.js");

const two = [
  { rgb:[255,0,0], polygons:[[{x:0,y:0},{x:100,y:0},{x:100,y:100},{x:0,y:100}]] },
  { rgb:[0,0,255], polygons:[[{x:120,y:0},{x:200,y:0},{x:200,y:80},{x:120,y:80}]] },
];

test("builds a design with 2 colors and one color change", () => {
  const d = m.buildDesign(two, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, outline:false, pxPerMm:10 });
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.colors.length, 2);
  assert.strictEqual(d.stitches.filter(s=>s.type==="color").length, 1);
  assert.strictEqual(d.stitches[d.stitches.length-1].type, "end");
  assert.ok(d.stitchCount > 0);
});
test("design fits inside garment box", () => {
  const d = m.buildDesign(two, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, outline:false, pxPerMm:10 });
  assert.ok(d.widthMM <= 4*25.4 + 1e-6 && d.heightMM <= 4*25.4 + 1e-6);
});
test("coordinates centered near origin", () => {
  const d = m.buildDesign(two, { garment:{widthIn:12,heightIn:12}, densityMm:0.5, outline:false, pxPerMm:10 });
  const xs = d.stitches.filter(s=>s.type==="stitch").map(s=>s.x);
  const mid = (Math.max(...xs)+Math.min(...xs))/2;
  assert.ok(Math.abs(mid) < 30); // roughly centered (DST units)
});
