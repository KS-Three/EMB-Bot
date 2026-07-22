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
test("max stitch length honored in final physical mm regardless of fit scale", () => {
  // Small 20x20 px square (pxPerMm:10 => 2mm) scaled UP into a 4in garment (fit.scale ~= 5x).
  const small = [
    { rgb:[0,0,0], polygons:[[{x:0,y:0},{x:20,y:0},{x:20,y:20},{x:0,y:20}]] },
  ];
  const d = m.buildDesign(small, { garment:{widthIn:4,heightIn:4}, densityMm:0.5, maxStitchMm:4.0, outline:false, pxPerMm:10 });
  // maxStitch honored in FINAL space within 5% tolerance (DST units = 0.1mm).
  const limit = 4.0 * 10 * 1.05;
  const s = d.stitches;
  for (let i = 1; i < s.length; i++) {
    const a = s[i-1], b = s[i];
    // Only consecutive real stitches; skip color/jump/end and pairs spanning a jump.
    if (a.type !== "stitch" || b.type !== "stitch") continue;
    const gap = Math.hypot(b.x - a.x, b.y - a.y);
    assert.ok(gap <= limit, `gap ${gap.toFixed(1)} DST exceeds ${limit.toFixed(1)}`);
  }
  // Design still fits the garment box (unchanged).
  assert.ok(d.widthMM <= 4*25.4 + 1e-6 && d.heightMM <= 4*25.4 + 1e-6);
});
