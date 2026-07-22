const assert = require("node:assert");
const { test } = require("node:test");
const FL = require("../src/flatten.js");

const U8 = (...xs) => Uint8Array.from(xs);
const count = (arr, v) => { let n = 0; for (const x of arr) if (x === v) n++; return n; };
const T = 255; // transparent index

// ---------------------------------------------------------------------------
// modeFilter
// ---------------------------------------------------------------------------

test("modeFilter: a single stray pixel becomes the surrounding field color", () => {
  const idx = U8(0, 0, 0, 0, 1, 0, 0, 0, 0); // 3x3, stray 1 at the center
  const out = FL.modeFilter(idx, 3, 3); // default iterations
  assert.strictEqual(out[4], 0);
  assert.deepStrictEqual(out, U8(0, 0, 0, 0, 0, 0, 0, 0, 0));
});

test("modeFilter: a transparent center stays transparent", () => {
  const idx = U8(0, T, 0); // 3x1
  const out = FL.modeFilter(idx, 3, 1, { iterations: 1 });
  assert.strictEqual(out[1], T);
  assert.deepStrictEqual(out, U8(0, T, 0));
});

test("modeFilter: transparent neighbors are excluded from voting", () => {
  // Center is opaque, all 8 neighbors transparent: if 255 voted it would flip
  // the center to transparent, but transparent is excluded so it keeps its color.
  const idx = U8(T, T, T, T, 0, T, T, T, T);
  const out = FL.modeFilter(idx, 3, 3, { iterations: 1 });
  assert.strictEqual(out[4], 0);
  assert.deepStrictEqual(out, U8(T, T, T, T, 0, T, T, T, T));
});

test("modeFilter: a tie keeps the center's own value", () => {
  // value 0 has count 4, value 1 has count 4 (tie), center value 2 -> keep 2
  const idx = U8(0, 0, 0, 0, 2, 1, 1, 1, 1);
  const out = FL.modeFilter(idx, 3, 3, { iterations: 1 });
  assert.strictEqual(out[4], 2);
});

test("modeFilter: iterations:2 applies the filter twice", () => {
  // 3x3 solid block of 1 inside a 5x5 field of 0
  const img = U8(
    0, 0, 0, 0, 0,
    0, 1, 1, 1, 0,
    0, 1, 1, 1, 0,
    0, 1, 1, 1, 0,
    0, 0, 0, 0, 0
  );
  const one = FL.modeFilter(img, 5, 5, { iterations: 1 });
  const two = FL.modeFilter(img, 5, 5, { iterations: 2 });
  // Two passes == one pass applied to the result of the first pass.
  assert.deepStrictEqual(two, FL.modeFilter(one, 5, 5, { iterations: 1 }));
  // Block erodes: 9 -> plus(5) -> single(1).
  assert.strictEqual(count(one, 1), 5);
  assert.strictEqual(count(two, 1), 1);
  assert.strictEqual(two[2 * 5 + 2], 1); // center survives
});

// ---------------------------------------------------------------------------
// absorbSmallRegions
// ---------------------------------------------------------------------------

test("absorbSmallRegions: a 3px island below threshold is absorbed by its neighbor", () => {
  const w = 7, h = 5;
  const idx = new Uint8Array(w * h).fill(0);
  idx[2 * w + 2] = 1; idx[2 * w + 3] = 1; idx[2 * w + 4] = 1; // 3px island of 1
  const out = FL.absorbSmallRegions(idx, w, h, 5);
  assert.strictEqual(count(out, 1), 0);
  assert.strictEqual(count(out, 0), w * h);
});

test("absorbSmallRegions: a patch at/above threshold survives", () => {
  const w = 10, h = 10;
  const idx = new Uint8Array(w * h).fill(0);
  for (let y = 2; y < 8; y++) for (let x = 2; x < 7; x++) idx[y * w + x] = 1; // 6x5 = 30px
  const out = FL.absorbSmallRegions(idx, w, h, 5);
  assert.strictEqual(count(out, 1), 30);
});

test("absorbSmallRegions: an island bordering only transparent is left unchanged", () => {
  const w = 5, h = 5;
  const idx = new Uint8Array(w * h).fill(T);
  idx[2 * w + 1] = 1; idx[2 * w + 2] = 1; idx[2 * w + 3] = 1;
  const before = Uint8Array.from(idx);
  const out = FL.absorbSmallRegions(idx, w, h, 5);
  assert.strictEqual(count(out, 1), 3); // still there
  assert.deepStrictEqual(out, before); // unchanged
});

test("absorbSmallRegions: two small islands of different colors both absorb", () => {
  const w = 9, h = 5;
  const idx = new Uint8Array(w * h).fill(0);
  idx[2 * w + 1] = 1; idx[2 * w + 2] = 1; // island of 1 (2px)
  idx[2 * w + 6] = 2; idx[2 * w + 7] = 2; // island of 2 (2px)
  const out = FL.absorbSmallRegions(idx, w, h, 5);
  assert.strictEqual(count(out, 1), 0);
  assert.strictEqual(count(out, 2), 0);
  assert.strictEqual(count(out, 0), w * h);
});

test("absorbSmallRegions: smallest-first lets an absorbed speck grow a region past threshold", () => {
  // 7x7 field of 0 with a 3x3 block of 1 whose center pixel is a speck of 2.
  // minPx=9: the 1px speck (2) is smallest, so it is absorbed first into the
  // ring of 1 (its only neighbor), growing that region to a solid 9px block
  // that then meets the threshold and survives. Largest-first ordering would
  // erase the ring into 0 first, then the speck, leaving all 0 -- so a passing
  // result proves smallest-first processing.
  const w = 7, h = 7;
  const idx = new Uint8Array(w * h).fill(0);
  for (let y = 2; y <= 4; y++) for (let x = 2; x <= 4; x++) idx[y * w + x] = 1;
  idx[3 * w + 3] = 2; // center speck
  const out = FL.absorbSmallRegions(idx, w, h, 9);
  assert.strictEqual(count(out, 2), 0); // speck absorbed
  assert.strictEqual(count(out, 1), 9); // grew to a full 3x3 and survived
  assert.strictEqual(out[3 * w + 3], 1);
});

test("absorbSmallRegions: many scattered specks all absorb and it terminates", () => {
  const w = 9, h = 9;
  const idx = new Uint8Array(w * h).fill(0);
  const specks = [[1, 1], [1, 4], [3, 6], [5, 2], [6, 6], [7, 4]];
  for (const [y, x] of specks) idx[y * w + x] = 1;
  const out = FL.absorbSmallRegions(idx, w, h, 5);
  assert.strictEqual(count(out, 1), 0);
  assert.strictEqual(count(out, 0), w * h);
});

// ---------------------------------------------------------------------------
// mergeColors
// ---------------------------------------------------------------------------

test("mergeColors: merges two entries into a population-weighted color and remaps", () => {
  const palette = [[10, 10, 10], [20, 20, 20], [200, 0, 0]];
  const indices = U8(0, 0, 0, 1, 2, 2, T); // 3x idx0, 1x idx1, 2x idx2, 1 transparent
  const res = FL.mergeColors(palette, indices, [0, 1]);
  assert.strictEqual(res.palette.length, 2);
  assert.deepStrictEqual(res.palette[0], [13, 13, 13]); // (10*3 + 20*1)/4 = 12.5 -> 13
  assert.deepStrictEqual(res.palette[1], [200, 0, 0]);
  assert.deepStrictEqual(res.indices, U8(0, 0, 0, 0, 1, 1, T));
});

test("mergeColors: the merged entry replaces the lowest index when merging higher ones", () => {
  const palette = [[10, 10, 10], [20, 20, 20], [200, 0, 0]];
  const indices = U8(0, 0, 0, 1, 2, 2);
  const res = FL.mergeColors(palette, indices, [1, 2]);
  assert.strictEqual(res.palette.length, 2);
  assert.deepStrictEqual(res.palette[0], [10, 10, 10]);
  // r = (20*1 + 200*2)/3 = 140 ; g,b = (20*1 + 0*2)/3 = 6.67 -> 7
  assert.deepStrictEqual(res.palette[1], [140, 7, 7]);
  assert.deepStrictEqual(res.indices, U8(0, 0, 0, 1, 1, 1));
});

test("mergeColors: falls back to a plain average when merged indices have zero population", () => {
  const palette = [[0, 0, 0], [100, 100, 100], [200, 200, 200]];
  const indices = U8(2, 2, T); // idx0 and idx1 have zero pixels
  const res = FL.mergeColors(palette, indices, [0, 1]);
  assert.strictEqual(res.palette.length, 2);
  assert.deepStrictEqual(res.palette[0], [50, 50, 50]); // plain average of black & grey
  assert.deepStrictEqual(res.palette[1], [200, 200, 200]);
  assert.deepStrictEqual(res.indices, U8(1, 1, T));
});

// ---------------------------------------------------------------------------
// indicesToRGBA
// ---------------------------------------------------------------------------

test("indicesToRGBA: opaque indices map to palette color + alpha 255, transparent to alpha 0", () => {
  const palette = [[10, 20, 30], [200, 100, 50]];
  const idx = U8(0, T, 1);
  const out = FL.indicesToRGBA(idx, palette, 3, 1);
  assert.ok(out instanceof Uint8ClampedArray);
  assert.deepStrictEqual(out, Uint8ClampedArray.from([10, 20, 30, 255, 0, 0, 0, 0, 200, 100, 50, 255]));
});

// ---------------------------------------------------------------------------
// paletteShares
// ---------------------------------------------------------------------------

test("paletteShares: fractions of opaque pixels per index, ignoring transparent", () => {
  const idx = U8(0, 0, 1, T, 2, 0); // opaque: idx0 x3, idx1 x1, idx2 x1 (total 5)
  const s = FL.paletteShares(idx, 3);
  assert.strictEqual(s.length, 3);
  assert.ok(Math.abs(s[0] - 0.6) < 1e-9);
  assert.ok(Math.abs(s[1] - 0.2) < 1e-9);
  assert.ok(Math.abs(s[2] - 0.2) < 1e-9);
  assert.ok(Math.abs(s.reduce((a, b) => a + b, 0) - 1) < 1e-9);
});

test("paletteShares: all zeros when there are no opaque pixels", () => {
  const idx = U8(T, T, T);
  const s = FL.paletteShares(idx, 2);
  assert.deepStrictEqual(s, [0, 0]);
});

// ---------------------------------------------------------------------------
// purity: no function mutates its inputs
// ---------------------------------------------------------------------------

test("purity: inputs are never mutated", () => {
  // modeFilter
  const mfIdx = U8(0, 1, 0, 0, 0, 0, 0, 0, 0);
  const mfSnap = Array.from(mfIdx);
  FL.modeFilter(mfIdx, 3, 3, { iterations: 2 });
  assert.deepStrictEqual(Array.from(mfIdx), mfSnap);

  // absorbSmallRegions
  const abIdx = U8(0, 0, 0, 0, 1, 0, 0, 0, 0);
  const abSnap = Array.from(abIdx);
  FL.absorbSmallRegions(abIdx, 3, 3, 5);
  assert.deepStrictEqual(Array.from(abIdx), abSnap);

  // mergeColors -- input palette (incl. inner arrays) and indices untouched,
  // and the result must not share inner arrays with the input palette.
  const mcPal = [[10, 10, 10], [20, 20, 20], [200, 0, 0]];
  const mcPalSnap = mcPal.map((c) => c.slice());
  const mcIdx = U8(0, 0, 0, 1, 2, 2);
  const mcIdxSnap = Array.from(mcIdx);
  const mcRes = FL.mergeColors(mcPal, mcIdx, [0, 1]);
  assert.deepStrictEqual(mcPal, mcPalSnap);
  assert.deepStrictEqual(Array.from(mcIdx), mcIdxSnap);
  mcRes.palette[1][0] = 999; // mutate result
  assert.strictEqual(mcPal[2][0], 200); // input unaffected

  // indicesToRGBA
  const irIdx = U8(0, T, 1);
  const irPal = [[1, 2, 3], [4, 5, 6]];
  const irIdxSnap = Array.from(irIdx);
  const irPalSnap = irPal.map((c) => c.slice());
  FL.indicesToRGBA(irIdx, irPal, 3, 1);
  assert.deepStrictEqual(Array.from(irIdx), irIdxSnap);
  assert.deepStrictEqual(irPal, irPalSnap);

  // paletteShares
  const psIdx = U8(0, 0, 1, T);
  const psSnap = Array.from(psIdx);
  FL.paletteShares(psIdx, 2);
  assert.deepStrictEqual(Array.from(psIdx), psSnap);
});
