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
test("terminal end record is not encoded as a stitch (2026-08-06 fix)", () => {
  // stitchModel.js always appends {type:"end"} as the last stitches-array
  // entry -- a design-list sentinel, not a real stitch. Before this fix
  // encodeEXP fell through to the generic stitch path for any type it didn't
  // recognize, writing "end" as a real zero-delta [0,0] record that standard
  // readers decode as one extra phantom stitch. pes.js's own encoder already
  // stops at "end" the same way (src/pes.js, both its CSewSeg loop and its
  // decoder). See docs/pes-crossval-verdict-2026-08-04.md section 4.
  const withEnd = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"stitch"},
    {x:5,y:-3,type:"end"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  const withoutEnd = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  // "end" must produce byte-identical output to simply omitting it -- not
  // one more [0,0] stitch record appended.
  assert.deepStrictEqual(Array.from(withEnd), Array.from(withoutEnd));
  assert.strictEqual(withEnd.length, 4, "two 2-byte stitch records, nothing more");
});
test("a record after end is never encoded (end is terminal, matching pes.js)", () => {
  const out = exp.encodeEXP({ stitches:[
    {x:0,y:0,type:"stitch"},
    {x:5,y:-3,type:"end"},
    {x:9,y:9,type:"stitch"},
  ], colors:[{r:0,g:0,b:0,name:"a"}] });
  // Only the one real stitch before "end" -- the trailing stitch after it
  // (which should never occur in practice, but pes.js's loop unconditionally
  // breaks rather than trusting that) must not appear either.
  assert.strictEqual(out.length, 2);
  assert.deepStrictEqual(Array.from(out), [0, 0]);
});
