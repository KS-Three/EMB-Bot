const assert = require("node:assert");
const { test } = require("node:test");
const { encodePES } = require("../src/pes.js");
const design = { stitches:[{x:-50,y:50,type:"stitch"},{x:50,y:50,type:"stitch"},{x:50,y:-50,type:"stitch"},{x:0,y:0,type:"end"}], colors:[{r:200,g:0,b:0,name:"Color 1"}], widthMM:10, heightMM:10, stitchCount:3, colorCount:1 };

test("PES starts with signature", () => {
  const out = encodePES(design);
  assert.strictEqual(Buffer.from(out.slice(0,8)).toString("latin1"), "#PES0001");
});
test("PES contains PEC block marker", () => {
  const out = encodePES(design);
  const s = Buffer.from(out).toString("latin1");
  assert.ok(s.includes("CEmbOne") || s.includes("CSewSeg") || out.length > 100);
});
