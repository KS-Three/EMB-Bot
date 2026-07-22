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
test("flat 3-color image resolves to the 3 true colors, no muddy/duplicate entries", () => {
  const W=90,H=30, cols=[[210,30,30],[30,160,60],[30,80,210]];
  const px=[];
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const c=cols[Math.floor(x/30)];px.push(c[0],c[1],c[2],255);}
  const { palette } = q.medianCut(px, 4);
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
  for (const c of cols) assert.ok(palette.some(p=>dist(p,c)<20), "no palette entry near "+c);
  for (let i=0;i<palette.length;i++) for (let j=i+1;j<palette.length;j++)
    assert.ok(dist(palette[i],palette[j])>=12, "near-duplicate palette entries "+palette[i]+" & "+palette[j]);
});
