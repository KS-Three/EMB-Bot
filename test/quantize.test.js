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

// ---- transparent corner (2026-10-11, PR #829 gate side finding) ----
// A transparent corner used to be sampled as its COLOUR (0,0,0 for a canvas
// cleared to transparent), so any near-black mark was keyed out with it.
function markOnTransparent(rgb) {
  const W = 8, H = 8, px = new Uint8ClampedArray(W * H * 4); // all 0,0,0,0
  for (let y = 2; y < 6; y++) for (let x = 2; x < 6; x++) {
    const o = (y * W + x) * 4;
    px[o] = rgb[0]; px[o + 1] = rgb[1]; px[o + 2] = rgb[2]; px[o + 3] = 255;
  }
  return { px, W, H };
}
const opaqueCount = (a) => { let n = 0; for (let i = 3; i < a.length; i += 4) if (a[i] !== 0) n++; return n; };

for (const [name, rgb] of [["#000000", [0, 0, 0]], ["#141414", [20, 20, 20]], ["#231F20", [35, 31, 32]], ["red", [220, 30, 30]]]) {
  test(`knockoutBackground: ${name} mark on a transparent background survives (default options)`, () => {
    const { px, W, H } = markOnTransparent(rgb);
    const out = q.knockoutBackground(px, W, H);
    assert.strictEqual(opaqueCount(out), 16, "all 16 mark pixels stay opaque");
    assert.strictEqual(opaqueCount(px), 16, "input not mutated");
  });
}
test("knockoutBackground: transparent corner still knocks out a near-white mark pixel (white rule unchanged)", () => {
  const { px, W, H } = markOnTransparent([250, 250, 250]);
  assert.strictEqual(opaqueCount(q.knockoutBackground(px, W, H)), 0);
});
test("knockoutBackground: transparent corner + black mark survives medianCut downstream", () => {
  const { px, W, H } = markOnTransparent([0, 0, 0]);
  const { palette } = q.medianCut(q.knockoutBackground(px, W, H), 4);
  assert.strictEqual(palette.length, 1);
});

// Frozen copy of knockoutBackground as it was before the transparent-corner
// change. Opaque-corner inputs must give the byte-identical result.
function legacyKnockout(rgba, w, h, opts) {
  const options = opts || {};
  const tolerance = options.tolerance === undefined ? 24 : options.tolerance;
  const sampleCorner = options.sampleCorner === undefined ? true : options.sampleCorner;
  const out = new Uint8ClampedArray(rgba.length); out.set(rgba);
  const count = w * h, whiteThreshold = 255 - tolerance;
  let cR = 0, cG = 0, cB = 0;
  if (sampleCorner && count > 0) { cR = rgba[0]; cG = rgba[1]; cB = rgba[2]; }
  for (let i = 0; i < count; i++) {
    const o = i * 4, r = rgba[o], g = rgba[o + 1], b = rgba[o + 2];
    const nw = r >= whiteThreshold && g >= whiteThreshold && b >= whiteThreshold;
    const nc = sampleCorner && Math.abs(r - cR) <= tolerance && Math.abs(g - cG) <= tolerance && Math.abs(b - cB) <= tolerance;
    if (nw || nc) out[o + 3] = 0;
  }
  return out;
}
// Since 2026-11-13 this pins the OFF arm (`connected: false`): the per-pixel
// test is what `legacyKnockout` froze, and the default now floods from the
// border instead (tests below).
test("knockoutBackground: opaque-corner inputs are byte-identical to the pre-change function (connected: false)", () => {
  let seed = 12345; const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
  const W = 16, H = 16;
  for (const corner of [[255, 255, 255], [0, 0, 0], [10, 120, 10], [240, 240, 240], [35, 31, 32]]) {
    const px = new Uint8ClampedArray(W * H * 4);
    for (let i = 0; i < W * H; i++) {
      const base = rnd() < 0.5 ? corner : [rnd() * 255, rnd() * 255, rnd() * 255];
      px[i * 4] = base[0] + (rnd() * 8 - 4); px[i * 4 + 1] = base[1] + (rnd() * 8 - 4); px[i * 4 + 2] = base[2] + (rnd() * 8 - 4);
      px[i * 4 + 3] = rnd() < 0.1 ? 0 : (rnd() < 0.2 ? 128 : 255);
    }
    px.set([corner[0], corner[1], corner[2], 255], 0); // opaque corner
    for (const o of [{}, { tolerance: 5 }, { sampleCorner: false }]) {
      const off = Object.assign({ connected: false }, o);
      assert.deepStrictEqual(Array.from(q.knockoutBackground(px, W, H, off)), Array.from(legacyKnockout(px, W, H, o)));
    }
  }
});

// ---- only background that reaches the border (2026-11-13, Kent's approval) ----
// Each pixel used to be judged on its own, so an enclosed white detail was
// keyed out with the page and sewed as bare garment.
function badge(bg, ring, inner) {
  const W = 60, H = 60, px = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const o = (y * W + x) * 4, inDisc = (x - 30) ** 2 + (y - 30) ** 2 <= 24 ** 2;
    const c = !inDisc ? bg : (Math.abs(x - 30) <= 8 && Math.abs(y - 30) <= 8) ? inner : ring;
    px[o] = c[0]; px[o + 1] = c[1]; px[o + 2] = c[2]; px[o + 3] = 255;
  }
  return { px, W, H };
}
const keyedIn = (out, W, inside) => { let n = 0; for (let i = 3; i < out.length; i += 4) { const p = (i - 3) / 4; if (out[i] === 0 && inside(p % W, Math.floor(p / W))) n++; } return n; };
const inDisc = (x, y) => (x - 30) ** 2 + (y - 30) ** 2 <= 24 ** 2;
test("knockoutBackground: a white square inside a red badge on white keeps its 289 pixels; the page goes", () => {
  const { px, W, H } = badge([255, 255, 255], [200, 20, 30], [255, 255, 255]);
  const out = q.knockoutBackground(px, W, H, {});
  assert.strictEqual(keyedIn(out, W, inDisc), 0);
  assert.strictEqual(keyedIn(out, W, (x, y) => !inDisc(x, y)), W * H - 1793);
  assert.strictEqual(q.medianCut(out, 4).palette.length, 2, "white is a sewn colour now");
  // the off arm is the old answer: all 289 keyed out
  assert.strictEqual(keyedIn(q.knockoutBackground(px, W, H, { connected: false }), W, inDisc), 289);
});
test("knockoutBackground: a corner-coloured detail inside the badge keeps its colour", () => {
  const navy = [20, 30, 90];
  const { px, W, H } = badge(navy, [250, 200, 0], navy);
  assert.strictEqual(keyedIn(q.knockoutBackground(px, W, H), W, inDisc), 0);
});
test("knockoutBackground: each test floods only through itself (black on a white band on a black page)", () => {
  // a black page, a full-width white band, a black square on the band: the
  // band reaches the border through white, the square reaches the page only
  // through the band, so it is art.
  const W = 30, H = 30, px = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const o = (y * W + x) * 4, band = y >= 10 && y < 20, sq = band && y >= 13 && y < 17 && x >= 13 && x < 17;
    const v = band && !sq ? 255 : 0; px[o] = px[o + 1] = px[o + 2] = v; px[o + 3] = 255;
  }
  const out = q.knockoutBackground(px, W, H);
  assert.strictEqual(opaqueCount(out), 16);
  assert.strictEqual(out[(15 * W + 15) * 4 + 3], 255);
});
test("knockoutBackground: a one-pixel diagonal ring closes what it encloses (4-connected background)", () => {
  // a diamond outline drawn 8-connected: background reaches its inside only
  // through the diagonal corners
  const W = 21, H = 21, px = new Uint8ClampedArray(W * H * 4).fill(255);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (Math.abs(x - 10) + Math.abs(y - 10) === 7) { const o = (y * W + x) * 4; px[o] = 200; px[o + 1] = 0; px[o + 2] = 0; }
  const out = q.knockoutBackground(px, W, H);
  assert.strictEqual(out[(10 * W + 10) * 4 + 3], 255, "the white inside the diamond is kept");
  assert.strictEqual(out[3], 0, "the page outside is keyed out");
});
test("knockoutBackground: a white halo round a mark on a transparent page still goes", () => {
  const { px, W, H } = markOnTransparent([0, 0, 0]);
  for (let y = 1; y < 7; y++) for (let x = 1; x < 7; x++) { const o = (y * W + x) * 4; if (px[o + 3] === 0) { px[o] = px[o + 1] = px[o + 2] = 250; px[o + 3] = 255; } }
  const out = q.knockoutBackground(px, W, H);
  assert.strictEqual(opaqueCount(out), 16, "the 16 black pixels stay; the 20 halo pixels go");
});
