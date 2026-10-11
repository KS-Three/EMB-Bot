// Fuzz the importers (DST, SVG, EMBF font bin) with truncated, corrupt and
// random input. Contract under test: never hang, and either return a result
// or throw an ordinary Error -- never a non-Error throw, never a runaway loop.
// Seeded so a failure reproduces byte-for-byte.
const assert = require("node:assert");
const { test } = require("node:test");
const dst = require("../src/dst.js");
const { decodeDST, decodeDSTStandard } = require("../src/dstimport.js");
const { parseSVG } = require("../src/svgimport.js");
const { encodeFontBin, decodeFontBin } = require("../src/fontbin.js");

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const randBytes = (r, n) => Uint8Array.from({ length: n }, () => Math.floor(r() * 256));
const BUDGET_MS = 2000; // per call; every input here is tiny, so this is a hang tripwire

function survives(label, fn, input) {
  const t0 = Date.now();
  try {
    fn(input);
  } catch (e) {
    assert.ok(e instanceof Error, `${label}: threw a non-Error: ${String(e)}`);
    assert.ok(typeof e.message === "string" && e.message.length > 0, `${label}: empty error message`);
  }
  assert.ok(Date.now() - t0 < BUDGET_MS, `${label}: took ${Date.now() - t0} ms`);
}

function goodDst() {
  const stitches = [{ x: 0, y: 0, type: "jump" }];
  for (let i = 0; i < 40; i++) stitches.push({ x: i * 5, y: (i % 7) * 4, type: "stitch" });
  stitches.push({ x: 200, y: 0, type: "color" }, { x: 210, y: 5, type: "stitch" }, { x: 210, y: 5, type: "end" });
  return Uint8Array.from(dst.encodeDST({ stitches, colors: [{ r: 1, g: 2, b: 3 }, { r: 4, g: 5, b: 6 }], label: "FUZZ" }));
}

test("fuzz DST: every truncation of a valid file", () => {
  const good = goodDst();
  decodeDST(good); // control: the seed file is valid
  for (let n = 0; n <= good.length; n++) survives(`truncate@${n}`, decodeDST, good.subarray(0, n));
});

test("fuzz DST: bit flips, bad headers, random bytes, huge claimed counts", () => {
  const good = goodDst();
  const r = rng(0xd57);
  for (let i = 0; i < 400; i++) {
    const m = Uint8Array.from(good);
    for (let k = 0; k < 1 + Math.floor(r() * 8); k++) m[Math.floor(r() * m.length)] ^= 1 << Math.floor(r() * 8);
    survives(`flip#${i}`, decodeDST, m);
  }
  for (let i = 0; i < 100; i++) { // header zeroed / garbled
    const m = Uint8Array.from(good);
    m.set(randBytes(r, 512), 0);
    survives(`header#${i}`, decodeDST, m);
  }
  for (let i = 0; i < 200; i++) survives(`random#${i}`, decodeDST, randBytes(r, Math.floor(r() * 2000)));
  // Header claims 99999999 stitches; counts are recomputed from records, so this must not matter.
  const huge = Uint8Array.from(good);
  const hdr = new TextEncoder().encode("LA:HUGE\rST:99999999\rCO:99999\r+X:9999\r-X:9999\r+Y:9999\r-Y:9999\r");
  huge.fill(0x20, 0, 512);
  huge.set(hdr, 0);
  survives("huge-counts", decodeDST, huge);
  for (const bad of [null, undefined, [], new Uint8Array(0), new Uint8Array(514), new Uint8Array(515)])
    survives("degenerate", decodeDST, bad);
  assert.strictEqual(decodeDSTStandard, decodeDST);
});

test("fuzz DST: a large all-jump / all-color record stream finishes quickly and cleanly", () => {
  for (const b2 of [0x83, 0xc3, 0x03]) {
    const m = new Uint8Array(512 + 3 * 300000);
    m.set(goodDst().subarray(0, 512), 0);
    for (let i = 512; i < m.length; i += 3) { m[i] = 0x55; m[i + 1] = 0xaa; m[i + 2] = b2; }
    const t0 = Date.now();
    survives(`stream-0x${b2.toString(16)}`, decodeDST, m);
    assert.ok(Date.now() - t0 < 5000);
  }
});

const svgSeeds = [
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="#f00"/>' +
    '<path d="M10 10 C 20 20, 40 20, 50 10 S 80 0 90 10 Z" fill="#00f"/><circle cx="50" cy="50" r="20"/></svg>',
];
test("fuzz SVG: truncations, mutations, hostile numbers, random text", () => {
  const r = rng(0x5e6);
  const seed = svgSeeds[0];
  for (let n = 0; n <= seed.length; n++) survives(`svg-trunc@${n}`, parseSVG, seed.slice(0, n));
  const alphabet = '<>/="\' M L C Z 0123456789.-e#%()abcxyz\n';
  for (let i = 0; i < 300; i++) {
    const a = seed.split("");
    for (let k = 0; k < 1 + Math.floor(r() * 10); k++) a[Math.floor(r() * a.length)] = alphabet[Math.floor(r() * alphabet.length)];
    survives(`svg-mut#${i}`, parseSVG, a.join(""));
  }
  for (let i = 0; i < 100; i++) survives(`svg-rand#${i}`, parseSVG, String.fromCharCode(...randBytes(r, Math.floor(r() * 500))));
  const hostile = [
    '<svg viewBox="0 0 1e308 1e308"><rect width="1e308" height="1e308"/></svg>',
    '<svg viewBox="0 0 0 0"><rect width="10" height="10"/></svg>',
    '<svg viewBox="NaN NaN NaN NaN"><path d="M 1e999 1e999 L -1e999 5 Z"/></svg>',
    '<svg viewBox="0 0 100 100"><path d="M 0 0 A 1e-9 1e-9 0 1 1 100 100 Z"/></svg>',
    '<svg viewBox="0 0 100 100"><path d="M 0 0 A 1e9 1e9 0 1 1 100 100 Z"/></svg>',
    '<svg viewBox="0 0 100 100"><circle r="1e12" cx="0" cy="0"/></svg>',
    '<svg viewBox="0 0 100 100"><path d="M0 0 C 1e300 1e300 -1e300 1e300 5 5 Z"/></svg>',
    '<svg viewBox="0 0 100 100"><polygon points="1,2,3"/><polygon points=""/><polyline/></svg>',
    '<svg viewBox="0 0 100 100"><g transform="scale(1e308) rotate(NaN) matrix(1 2 3)"><rect width="5" height="5"/></g></svg>',
    "<svg>" + "<g>".repeat(5000) + '<rect width="5" height="5"/>' + "</g>".repeat(5000) + "</svg>",
    "<svg viewBox='0 0 100 100'>" + '<rect width="3" height="3"/>'.repeat(20000) + "</svg>",
    "<svg viewBox='0 0 100 100'><path d=\"" + "M 1 1 L 2 2 ".repeat(50000) + 'Z"/></svg>',
    "",
    null,
    undefined,
  ];
  hostile.forEach((s, i) => survives(`svg-hostile#${i}`, parseSVG, s));
});

test("fuzz EMBF font bin: truncations, corruption, huge counts, random bytes", () => {
  const font = { name: "F", glyphs: { A: { rings: [[[0, 0], [10, 0], [10, 10], [0, 10]]] } } };
  const good = encodeFontBin(font);
  const r = rng(0xf0);
  {
    decodeFontBin(good);
    for (let n = 0; n < good.length; n++) survives(`font-trunc@${n}`, decodeFontBin, good.subarray(0, n));
    for (let i = 0; i < 300; i++) {
      const m = Uint8Array.from(good);
      for (let k = 0; k < 1 + Math.floor(r() * 4); k++) m[Math.floor(r() * m.length)] = Math.floor(r() * 256);
      survives(`font-flip#${i}`, decodeFontBin, m);
    }
  }
  const head = (meta, q) => {
    const mb = new TextEncoder().encode(meta);
    const out = new Uint8Array(12 + mb.length + 64);
    out.set([69, 77, 66, 70, 1, q]);
    new DataView(out.buffer).setUint32(8, mb.length, true);
    out.set(mb, 12);
    return out;
  };
  survives("font-huge-ring", decodeFontBin, head('{"g":{"__r":4000000000}}', 10));
  survives("font-q0", decodeFontBin, head('{"g":{"__r":3}}', 0));
  survives("font-huge-meta", (b) => { const c = Uint8Array.from(b); new DataView(c.buffer).setUint32(8, 0xffffffff, true); decodeFontBin(c); }, head("{}", 10));
  survives("font-bad-json", decodeFontBin, head("{not json", 10));
  for (let i = 0; i < 200; i++) survives(`font-rand#${i}`, decodeFontBin, randBytes(r, Math.floor(r() * 300)));
  for (let i = 0; i < 100; i++) { const b = randBytes(r, 64); b.set([69, 77, 66, 70, 1], 0); survives(`font-magic#${i}`, decodeFontBin, b); }
  for (const bad of [null, undefined, "EMBF", 5]) survives("font-degenerate", decodeFontBin, bad);
});
