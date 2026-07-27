const assert = require("node:assert");
const { test } = require("node:test");
const fb = require("../src/fontbin.js");

const FONT = {
  name: "T", license: "L", unitsPerEm: 100, sizeMm: 20,
  advDefault: 50, kerning: { AV: -3 },
  glyphs: {
    A: {
      adv: 40,
      cols: [{
        railA: [[0, 0], [10.26, 5.13], [20.5, 10.24]],
        railB: [[0, 4], [10.3, 9.1]],
        rungs: [[[0, 0], [0, 4]], [[20.5, 10.24], [10.3, 9.1]]],
      }],
      runs: [{ pts: [[1.111, 2.222], [3.333, 4.444]], jump: true }],
    },
    B: { adv: 30, cols: [], runs: [] },
  },
};

test("quantizeFont snaps ring coords to the Q grid and copies everything else", () => {
  const q = fb.quantizeFont(FONT, 4);
  assert.strictEqual(q.glyphs.A.cols[0].railA[1][0], 10.25); // round(10.26*4)=41 -> 10.25
  assert.strictEqual(q.glyphs.A.cols[0].railA[1][1], 5.25);  // round(5.13*4)=21 -> 5.25
  assert.strictEqual(q.name, "T");
  assert.strictEqual(q.glyphs.A.runs[0].jump, true);
  assert.notStrictEqual(q.glyphs.A.cols[0].railA, FONT.glyphs.A.cols[0].railA); // copy, not alias
  assert.strictEqual(FONT.glyphs.A.cols[0].railA[1][0], 10.26); // input untouched
});

test("encode/decode round-trips to exactly the quantized font", () => {
  const bytes = fb.encodeFontBin(FONT, 4);
  assert.ok(bytes instanceof Uint8Array);
  assert.deepStrictEqual(fb.decodeFontBin(bytes), fb.quantizeFont(FONT, 4));
});

test("header carries magic and version", () => {
  const b = fb.encodeFontBin(FONT, 4);
  assert.strictEqual(String.fromCharCode(b[0], b[1], b[2], b[3]), "EMBF");
  assert.strictEqual(b[4], 1);
  assert.strictEqual(b[5], 4);
});

test("binary is materially smaller than JSON for point-heavy data", () => {
  const big = { glyphs: { X: { adv: 1, cols: [{ railA:
    Array.from({ length: 4000 }, (_, i) => [i * 0.62, Math.sin(i / 9) * 40]) }] } } };
  const ratio = JSON.stringify(big).length / fb.encodeFontBin(big, 4).length;
  assert.ok(ratio > 3, "expected >3x, got " + ratio.toFixed(2));
});

test("empty arrays and negative/large coords survive", () => {
  const f = { glyphs: { Y: { adv: 0, cols: [], runs: [],
    weird: [[-800.25, 4000.75], [-799, 4001]] } } };
  assert.deepStrictEqual(fb.decodeFontBin(fb.encodeFontBin(f, 4)), fb.quantizeFont(f, 4));
});

test("decode rejects garbage", () => {
  assert.throws(() => fb.decodeFontBin(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9])), /EMBF/);
});

test("encode rejects fonts containing the reserved __r key", () => {
  const f = { glyphs: { A: { meta: { __r: 5 }, cols: [{ railA: [[0, 0], [1, 1], [2, 2]] }] } } };
  assert.throws(() => fb.encodeFontBin(f, 4), /__r/);
});
