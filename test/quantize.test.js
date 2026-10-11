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

// ---- gap coverage (2026-10-08) ----
test("medianCut: empty and all-transparent input give empty palette", () => {
  assert.deepStrictEqual(q.medianCut([], 4).palette, []);
  const r = q.medianCut([1,2,3,0, 4,5,6,0], 4);
  assert.deepStrictEqual(r.palette, []);
  assert.deepStrictEqual(Array.from(r.indices), [255, 255]);
});
test("medianCut: single flat color collapses to one entry (n larger than true colors)", () => {
  const px = []; for (let i = 0; i < 20; i++) px.push(40, 90, 200, 255);
  const { palette, indices } = q.medianCut(px, 8);
  assert.deepStrictEqual(palette, [[40, 90, 200]]);
  assert.ok(Array.from(indices).every((i) => i === 0));
});
test("medianCut: n=1 yields the mean colour", () => {
  const px = [0,0,0,255, 100,50,200,255];
  const { palette } = q.medianCut(px, 1);
  assert.deepStrictEqual(palette, [[50, 25, 100]]);
});
test("medianCut: near-duplicate colours (distance < 16) merge, distinct ones stay", () => {
  const px = [];
  for (let i = 0; i < 10; i++) px.push(100,100,100,255);
  for (let i = 0; i < 10; i++) px.push(105,100,100,255);
  for (let i = 0; i < 10; i++) px.push(250,0,0,255);
  const { palette } = q.medianCut(px, 3);
  assert.strictEqual(palette.length, 2);
});
test("medianCut: indices are valid palette indices; partial alpha counts as opaque", () => {
  const px = [255,0,0,1, 0,0,255,128, 9,9,9,0];
  const { palette, indices } = q.medianCut(px, 2);
  assert.strictEqual(indices[2], 255);
  assert.ok(indices[0] < palette.length && indices[1] < palette.length);
  assert.notStrictEqual(indices[0], indices[1]);
});
test("knockoutBackground: corner sampling removes a non-white background", () => {
  const px = new Uint8ClampedArray([10,120,10,255, 12,118,9,255, 200,0,0,255]);
  const out = q.knockoutBackground(px, 3, 1);
  assert.strictEqual(out[3], 0);
  assert.strictEqual(out[7], 0);
  assert.strictEqual(out[11], 255);
});
test("knockoutBackground: tolerance option and input is not mutated", () => {
  const px = new Uint8ClampedArray([240,240,240,255, 0,0,0,255]);
  const copy = Array.from(px);
  assert.strictEqual(q.knockoutBackground(px, 2, 1, { sampleCorner: false, tolerance: 5 })[3], 255);
  assert.strictEqual(q.knockoutBackground(px, 2, 1, { sampleCorner: false, tolerance: 20 })[3], 0);
  assert.deepStrictEqual(Array.from(px), copy);
});
test("knockoutBackground: zero-size image returns empty", () => {
  assert.strictEqual(q.knockoutBackground(new Uint8ClampedArray(0), 0, 0).length, 0);
});
