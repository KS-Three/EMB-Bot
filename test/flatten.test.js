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

test("absorbSmallRegions: handed `stats`, it counts what it absorbed and its walks over the whole image", () => {
  const w = 9, h = 5;
  const idx = new Uint8Array(w * h).fill(0);
  idx[2 * w + 1] = 1; idx[2 * w + 2] = 1; // island of 1 (2px)
  idx[2 * w + 6] = 2; idx[2 * w + 7] = 2; // island of 2 (2px)
  const stats = { absorbed: 0, imageWalks: 0 };
  const out = FL.absorbSmallRegions(idx, w, h, 5, { stats });
  assert.strictEqual(stats.absorbed, 2);
  assert.ok(stats.imageWalks >= 1, `walked the image ${stats.imageWalks} times`);
  // Counting changes nothing it returns.
  assert.deepStrictEqual(out, FL.absorbSmallRegions(idx, w, h, 5));
});

// --- the work it does, counted without a clock ------------------------------
//
// The Studio runs this on the main thread, on whatever a customer uploads. A
// photograph cut to a few colours hands it thousands of specks, and with the
// background removed thousands of islands with nothing but transparent beside
// them. Neither may cost a walk over the whole image apiece.

function walked(idx, w, h, minPx) {
  const stats = { absorbed: 0, imageWalks: 0 };
  FL.absorbSmallRegions(idx, w, h, minPx, { stats });
  return stats;
}

test("absorbSmallRegions: 400 specks cost no more walks over the image than one", () => {
  const w = 60, h = 60;
  const one = new Uint8Array(w * h).fill(0);
  one[1 * w + 1] = 1;
  const many = new Uint8Array(w * h).fill(0);
  for (let y = 1; y < h; y += 3) for (let x = 1; x < w; x += 3) many[y * w + x] = 1; // 20 x 20 of them
  const a = walked(one, w, h, 5), b = walked(many, w, h, 5);
  assert.strictEqual(a.absorbed, 1);
  assert.strictEqual(b.absorbed, 400);
  assert.strictEqual(b.imageWalks, a.imageWalks);
});

test("absorbSmallRegions: an island that can never be absorbed is not asked again at every absorb", () => {
  // Transparent ground. On the left a 20 x 24 block of 0 holding ten 2px specks
  // of 1. On the right, in the second image only, thirty 1px islands of 2 with
  // transparent all round: smaller than every speck, so first in line each time.
  const w = 40, h = 24;
  const bare = new Uint8Array(w * h).fill(T);
  for (let y = 0; y < h; y++) for (let x = 0; x < 20; x++) bare[y * w + x] = 0;
  for (let k = 0; k < 10; k++) { bare[(2 + 2 * k) * w + 2] = 1; bare[(2 + 2 * k) * w + 3] = 1; }
  const islands = Uint8Array.from(bare);
  for (let j = 0; j < 5; j++) for (let i = 0; i < 6; i++) islands[(1 + 2 * j) * w + 22 + 2 * i] = 2;
  const a = walked(bare, w, h, 5), b = walked(islands, w, h, 5);
  assert.strictEqual(a.absorbed, 10);
  assert.strictEqual(b.absorbed, 10);
  assert.strictEqual(count(FL.absorbSmallRegions(islands, w, h, 5), 2), 30); // and they are still there
  assert.strictEqual(b.imageWalks, a.imageWalks);
});

// --- against the rule written the slow way ----------------------------------
//
// absorbSmallRegions as the engine ran it until 2026-10-04, word for word:
// label the whole image, take the smallest component under the threshold that
// has a neighbour to vote for (of two the same size, the one a raster scan
// meets first), repaint it in the index most of its outside neighbours carry
// (of two with the same votes, the lower), and start again from a fresh
// labelling. That is the DEFINITION of which component goes into which
// neighbour and in what order. The engine reaches the same grid without
// labelling again, and this is what holds it to that.

function absorbSlowly(indices, w, h, minPx) {
  const labelComponents = (grid) => {
    const n = w * h;
    const label = new Int32Array(n).fill(-1);
    const sizes = [];
    const stack = [];
    let count = 0;
    for (let start = 0; start < n; start++) {
      if (grid[start] === T || label[start] !== -1) continue;
      const val = grid[start];
      const id = count++;
      label[start] = id;
      stack.length = 0;
      stack.push(start);
      let size = 0;
      while (stack.length) {
        const p = stack.pop();
        size++;
        const px = p % w;
        const py = (p / w) | 0;
        if (px > 0 && label[p - 1] === -1 && grid[p - 1] === val) { label[p - 1] = id; stack.push(p - 1); }
        if (px < w - 1 && label[p + 1] === -1 && grid[p + 1] === val) { label[p + 1] = id; stack.push(p + 1); }
        if (py > 0 && label[p - w] === -1 && grid[p - w] === val) { label[p - w] = id; stack.push(p - w); }
        if (py < h - 1 && label[p + w] === -1 && grid[p + w] === val) { label[p + w] = id; stack.push(p + w); }
      }
      sizes.push(size);
    }
    return { label, sizes, count };
  };
  const majorityNeighbor = (grid, label, comp) => {
    const n = w * h;
    const votes = new Map();
    for (let i = 0; i < n; i++) {
      if (label[i] !== comp) continue;
      const px = i % w;
      const py = (i / w) | 0;
      const check = (q) => {
        if (label[q] === comp) return; // inside the component
        const v = grid[q];
        if (v === T) return;
        votes.set(v, (votes.get(v) || 0) + 1);
      };
      if (px > 0) check(i - 1);
      if (px < w - 1) check(i + 1);
      if (py > 0) check(i - w);
      if (py < h - 1) check(i + w);
    }
    let best = -1;
    let bestCount = -1;
    for (const [v, c] of votes) {
      if (c > bestCount || (c === bestCount && v < best)) {
        bestCount = c;
        best = v;
      }
    }
    return best;
  };
  const cur = Uint8Array.from(indices);
  for (;;) {
    const { label, sizes, count } = labelComponents(cur);
    const candidates = [];
    for (let c = 0; c < count; c++) if (sizes[c] < minPx) candidates.push(c);
    candidates.sort((a, b) => sizes[a] - sizes[b]);

    let chosen = -1;
    let target = -1;
    for (const c of candidates) {
      const maj = majorityNeighbor(cur, label, c);
      if (maj !== -1) { chosen = c; target = maj; break; }
    }
    if (chosen === -1) break;

    for (let i = 0; i < cur.length; i++) if (label[i] === chosen) cur[i] = target;
  }
  return cur;
}

// The first pixel where two grids part, as text for a failure message.
function parting(got, want, w) {
  if (got.length !== want.length) return `length ${got.length}, wanted ${want.length}`;
  for (let i = 0; i < want.length; i++) {
    if (got[i] !== want[i]) return `pixel (${i % w}, ${(i / w) | 0}) is ${got[i]}, the slow rule leaves ${want[i]}`;
  }
  return null;
}

test("absorbSmallRegions: 600 images nobody chose come out as the slow rule leaves them", () => {
  let seed = 20261004;
  const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const pick = (xs) => xs[Math.floor(rnd() * xs.length)];
  let absorbedSomething = 0;
  for (let n = 0; n < 600; n++) {
    const w = 1 + Math.floor(rnd() * 18), h = 1 + Math.floor(rnd() * 18);
    const colours = 1 + Math.floor(rnd() * 6);
    const holes = pick([0, 0, 0.1, 0.35, 0.6]); // share of transparent pixels
    const idx = new Uint8Array(w * h);
    for (let i = 0; i < idx.length; i++) idx[i] = rnd() < holes ? T : Math.floor(rnd() * colours);
    // Noise alone is all specks. Let pixels copy a neighbour for a few rounds
    // and components of every size appear, with ragged edges between them.
    for (let round = Math.floor(rnd() * 4) * w * h; round > 0; round--) {
      const x = Math.floor(rnd() * w), y = Math.floor(rnd() * h);
      const x2 = Math.min(w - 1, Math.max(0, x + pick([-1, 0, 1]))), y2 = Math.min(h - 1, Math.max(0, y + pick([-1, 0, 1])));
      idx[y * w + x] = idx[y2 * w + x2];
    }
    const minPx = pick([0, 1, 2, 2, 2.5, 3, 3, 4, 6, 10, 25, w * h + 1]);

    const want = absorbSlowly(idx, w, h, minPx);
    const stats = { absorbed: 0, imageWalks: 0 };
    const got = FL.absorbSmallRegions(idx, w, h, minPx, { stats });
    const where = parting(got, want, w);
    assert.strictEqual(where, null, `image ${n} (${w} x ${h}, ${colours} colours, minPx ${minPx}): ${where}`);
    if (stats.absorbed) absorbedSomething++;
  }
  // The sweep is not allowed to pass by absorbing nothing.
  assert.ok(absorbedSomething >= 350, `only ${absorbedSomething} of 600 images had anything absorbed`);
});

test("absorbSmallRegions: grids where everything ties come out as the slow rule leaves them", () => {
  // Every pixel its own component and every vote level: the order is all ties
  // (which speck goes first, which neighbour takes it), so this is where a
  // different order shows.
  const patterns = {
    checker: (x, y) => (x + y) % 2,
    "three in a diagonal": (x, y) => (x + 2 * y) % 3,
    "four in a knight's move": (x, y) => (x + 2 * y) % 4,
    "five across": (x, y) => (2 * x + y) % 5,
    stripes: (x, y) => y % 3,
    "checker with holes": (x, y) => ((x * 7 + y * 3) % 5 === 0 ? T : (x + y) % 2),
    "islands in a transparent sea": (x, y) => (x % 3 === 2 || y % 3 === 2 ? T : (x + y) % 3),
  };
  for (const [name, at] of Object.entries(patterns)) {
    for (const [w, h] of [[1, 9], [9, 1], [7, 7], [12, 9], [16, 16]]) {
      const idx = new Uint8Array(w * h);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) idx[y * w + x] = at(x, y);
      for (const minPx of [2, 3, 5, 12, w * h + 1]) {
        const where = parting(FL.absorbSmallRegions(idx, w, h, minPx), absorbSlowly(idx, w, h, minPx), w);
        assert.strictEqual(where, null, `${name}, ${w} x ${h}, minPx ${minPx}: ${where}`);
      }
    }
  }
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
