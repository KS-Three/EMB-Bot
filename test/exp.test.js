const assert = require("node:assert");
const { test } = require("node:test");
const exp = require("../src/exp.js");
test("stitch deltas signed", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:5,y:-3,type:"stitch"}], colors:[{r:0,g:0,b:0,name:"a"}] });
  // first record from (0,0) is [0,0]; second is [5, -3 => 0xFD]
  assert.deepStrictEqual(Array.from(out.slice(0,4)), [0,0,5,0xFD]);
});
test("trim emits Melco 4-byte trim control 0x80 0x80 0x07 0x00", () => {
  // The 2-byte 0x80 0x03 form is not a control code standard (pyembroidery-
  // convention) readers know -- see docs/pes-crossval-verdict-2026-08-04.md
  // section 4. 0x80-prefixed records are fixed 4 bytes.
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"trim"}], colors:[{r:0,g:0,b:0,name:"a"}] });
  const arr = Array.from(out);
  let found=false;
  for(let i=0;i<arr.length-3;i++){
    if(arr[i]===0x80&&arr[i+1]===0x80&&arr[i+2]===0x07&&arr[i+3]===0x00) found=true;
  }
  assert.ok(found, "expected 0x80 0x80 0x07 0x00 trim control");
});
test("trim tracks position; delta sum correct after trim", () => {
  // trim moves +40,-20 then a stitch to (50,-20): stitch delta must be +10,0
  const out = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:40,y:-20,type:"trim"},
    {x:50,y:-20,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  const arr = Array.from(out);
  // last record is the stitch: 2 bytes [dx, dy]. dx=10, dy=0.
  assert.deepStrictEqual(arr.slice(-2), [10, 0]);
});
test("color change bytes present", () => {
  const out = exp.encodeEXP({ stitches:[{x:0,y:0,type:"stitch"},{x:0,y:0,type:"color"},{x:1,y:0,type:"stitch"}], colors:[{},{}] });
  const arr = Array.from(out);
  // contains 0x80,0x01 sequence
  let found=false; for(let i=0;i<arr.length-1;i++){ if(arr[i]===0x80&&arr[i+1]===0x01) found=true; }
  assert.ok(found);
});
