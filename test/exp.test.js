const assert = require("node:assert");
const { test } = require("node:test");
const exp = require("../src/exp.js");
test("stitch deltas signed", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:5,y:-3,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] });
  // first record from (0,0) is [0,0]; second is [5, -3 => 0xFD]
  assert.deepStrictEqual(Array.from(out.slice(0,4)), [0,0,5,0xFD]);
});
test("color change bytes present", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"color"},{x:1,y:0,type:"stitch"}], colors:[{},{}] });
  const arr = Array.from(out);
  // contains 0x80,0x01 sequence
  let found=false; for(let i=0;i<arr.length-1;i++){ if(arr[i]===0x80&&arr[i+1]===0x01) found=true; }
  assert.ok(found);
});
