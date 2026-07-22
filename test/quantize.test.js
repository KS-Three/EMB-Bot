const assert = require("node:assert");
const { test } = require("node:test");
const q = require("../src/quantize.js");

test("median cut on two colors yields 2 palette entries", () => {
  // 4 red, 4 blue pixels
  const px = []; for(let i=0;i<4;i++) px.push(255,0,0,255); for(let i=0;i<4;i++) px.push(0,0,255,255);
  const { palette, indices } = q.medianCut(px, 2);
  assert.strictEqual(palette.length, 2);
  assert.notStrictEqual(indices[0], indices[7]); // first red vs last blue differ
});
test("transparent pixels get index 255", () => {
  const px = [10,10,10,0, 200,50,50,255];
  const { indices } = q.medianCut(px, 2);
  assert.strictEqual(indices[0], 255);
});
test("knockout white background", () => {
  const px = new Uint8ClampedArray([255,255,255,255, 12,34,56,255]);
  const out = q.knockoutBackground(px, 2, 1, { sampleCorner:false });
  assert.strictEqual(out[3], 0);   // white -> transparent
  assert.strictEqual(out[7], 255); // colored kept
});
