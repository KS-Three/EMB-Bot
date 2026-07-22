const assert = require("node:assert");
const { test } = require("node:test");
const { designToSVG } = require("../src/svgexport.js");
const design = { stitches:[{x:-50,y:50,type:"stitch"},{x:50,y:50,type:"stitch"},{x:50,y:-50,type:"stitch"},{x:0,y:0,type:"end"}], colors:[{r:200,g:0,b:0,name:"Color 1"}], widthMM:10, heightMM:10, stitchCount:3, colorCount:1 };

test("SVG has svg root and a stroke color", () => {
  const s = designToSVG(design);
  assert.ok(s.startsWith("<svg"));
  assert.ok(s.includes("stroke"));
  assert.ok(s.includes("viewBox"));
});
