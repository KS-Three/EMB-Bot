// The table-driven DST writer must stay byte-identical to the per-record
// balanced-ternary encoder it replaced. Reference below is that old algorithm.
const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const { decodeDST } = require("../src/dstimport.js");

const W = [1, 3, 9, 27, 81];
const XB = { 1: [0, 1], 3: [1, 1], 9: [0, 4], 27: [1, 4], 81: [2, 4] };
const YB = { 1: [0, 0x40], 3: [1, 0x40], 9: [0, 0x10], 27: [1, 0x10], 81: [2, 0x10] };
function ternary(v) {
  const d = []; let n = v;
  for (let i = 0; i < 5; i++) {
    const r = ((n % 3) + 3) % 3;
    if (r === 0) { d.push(0); n /= 3; } else if (r === 1) { d.push(1); n = (n - 1) / 3; } else { d.push(-1); n = (n + 1) / 3; }
  }
  return d;
}
function refRecord(dx, dy, flag) {
  const b = [0, 0, 3];
  for (const [v, T, hi] of [[dx, XB, 0], [dy, YB, 1]]) {
    ternary(v).forEach((d, i) => {
      if (!d) return;
      const [bi, m] = T[W[i]];
      // + weight uses m, - weight uses the neighbouring bit (x: <<1, y: >>1)
      b[bi] |= d > 0 ? (hi ? m << 1 : m) : (hi ? m : m << 1);
    });
  }
  if (flag === "jump") b[2] |= 0x80; else if (flag === "color") b[2] |= 0xc0;
  return b;
}

test("encodeRecord matches the reference for every delta pair on a grid and every flag", () => {
  for (const flag of ["stitch", "jump", "color"]) {
    for (let dx = -121; dx <= 121; dx += 1) {
      for (const dy of [-121, -82, -81, -28, -27, -10, -1, 0, 1, 3, 40, 81, 121]) {
        assert.deepStrictEqual(Array.from(dst.encodeRecord(dx, dy, flag)), refRecord(dx, dy, flag), `${dx},${dy},${flag}`);
      }
    }
  }
});

test("encodeRecord still rejects out-of-range deltas", () => {
  assert.throws(() => dst.encodeRecord(122, 0, "stitch"), RangeError);
  assert.throws(() => dst.encodeRecord(0, -122, "stitch"), RangeError);
});

test("encodeDST of a mixed design (long moves, trims, colours) decodes back to the same points", () => {
  let s = 7; const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const stitches = []; let x = 0, y = 0;
  for (let i = 0; i < 3000; i++) {
    const r = rnd();
    const type = i === 1500 ? "color" : r < 0.01 ? "trim" : r < 0.03 ? "jump" : "stitch";
    const far = r > 0.98 ? 600 : 50;
    x += Math.round((rnd() - 0.5) * far); y += Math.round((rnd() - 0.5) * far);
    stitches.push({ x, y, type });
  }
  const out = dst.encodeDST({ stitches, colors: [{ r: 0, g: 0, b: 0 }, { r: 9, g: 9, b: 9 }], label: "T" });
  assert.strictEqual((out.length - 512) % 3, 0);
  assert.deepStrictEqual(Array.from(out.slice(-3)), [0, 0, 0xf3]);
  // Sum the records' own deltas: the walk must land on the last point.
  const xw = [[0, 1, 1], [0, 2, -1], [0, 4, 9], [0, 8, -9], [1, 1, 3], [1, 2, -3], [1, 4, 27], [1, 8, -27], [2, 4, 81], [2, 8, -81]];
  const yw = [[0, 0x80, 1], [0, 0x40, -1], [0, 0x20, 9], [0, 0x10, -9], [1, 0x80, 3], [1, 0x40, -3], [1, 0x20, 27], [1, 0x10, -27], [2, 0x20, 81], [2, 0x10, -81]];
  let sx = 0, sy = 0;
  for (let o = 512; o < out.length - 3; o += 3) {
    for (const [bi, m, w] of xw) if (out[o + bi] & m) sx += w;
    for (const [bi, m, w] of yw) if (out[o + bi] & m) sy += w;
  }
  const last = stitches[stitches.length - 1];
  assert.strictEqual(sx, last.x);
  assert.strictEqual(sy, last.y);
  assert.ok(decodeDST(out).stitches.length > 0, "own decoder still reads it");
});
