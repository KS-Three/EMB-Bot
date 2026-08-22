// Right-to-left lettering (2026-08-22).
//
// Five upstream fonts ship their glyphs in `rtl.svg` rather than `ltr.svg`.
// build-font looked only for ltr.svg, so all five failed to import with ENOENT
// and the whole script was absent from the product.
//
// Two of them are pure Hebrew and are now supported. Hebrew needs nothing
// beyond right-to-left PLACEMENT: it has no contextual letter forms, so the
// glyph for a letter is the same wherever it sits in a word.
//
// Arabic is deliberately NOT enabled by this work, and that is the point of the
// last test here. Arabic letters take initial/medial/final/isolated forms and
// must join; on RTL placement alone they render as separate isolated letters,
// which is WRONG TEXT rather than merely plain-looking text.
//
// And a shaping engine would not rescue THESE fonts: measured 2026-08-22, all
// three carry only base-block Arabic (computer 45 glyphs, malika 36) and ZERO
// presentation forms (U+FB50-FDFF, U+FE70-FEFF), so the joined glyphs a shaper
// would select simply do not exist in them. Excluding them is not a temporary
// gap waiting on engine work — it is a property of the fonts.
const assert = require("node:assert");
const { test } = require("node:test");
require("../src/units.js"); require("../src/geometry.js"); require("../src/satin.js");
require("../src/satinplay.js"); require("../src/satinfont.js");
const EMB = globalThis.EMB;

// Minimal three-glyph font. Advances differ so position is unambiguous.
function font(dir) {
  const box = (w) => ({
    adv: w,
    cols: [{ railA: [[0, 0], [0, 40]], railB: [[w - 10, 0], [w - 10, 40]], rungs: [] }],
    runs: [],
  });
  return {
    name: "RTL Fixture", license: "OFL", unitsPerEm: 100, sizeMm: 20,
    advDefault: 50, advSpace: 30, kerning: {},
    glyphs: { A: box(50), B: box(60), C: box(70) },
    ...(dir ? { dir } : {}),
  };
}

// Canvas x-extent per source character, keyed by the charIdx the layout reports.
function spansByCharIdx(f, text) {
  const lay = EMB.layoutText(f, text, { emMm: 20, pxPerMm: 8 });
  const out = new Map();
  for (const r of lay.runs) {
    const pts = r.pts || r.points || [];
    if (!pts.length || r.charIdx == null) continue;
    const xs = pts.map((p) => (p.x != null ? p.x : p[0]));
    const cur = out.get(r.charIdx) || { min: Infinity, max: -Infinity };
    cur.min = Math.min(cur.min, ...xs);
    cur.max = Math.max(cur.max, ...xs);
    out.set(r.charIdx, cur);
  }
  return out;
}
const leftToRight = (f, text) =>
  [...spansByCharIdx(f, text).entries()].sort((a, b) => a[1].min - b[1].min).map(([i]) => i);

test("an RTL font places the FIRST character rightmost", () => {
  assert.deepStrictEqual(leftToRight(font("rtl"), "ABC"), [2, 1, 0],
    "expected C,B,A across the canvas — the first logical character must sit on the right");
});

test("an LTR font is completely unaffected", () => {
  assert.deepStrictEqual(leftToRight(font(null), "ABC"), [0, 1, 2]);
});

test("charIdx stays LOGICAL under RTL, so per-letter colour targets the right letter", () => {
  // charIdx exists so a <textarea> selection can be mapped onto glyphs, and a
  // selection is logical, not visual. If reversing the layout also reversed
  // charIdx, selecting the first letter would colour the last one — a silent
  // wrong-answer bug with nothing to catch it.
  const spans = spansByCharIdx(font("rtl"), "ABC");
  assert.deepStrictEqual([...spans.keys()].sort(), [0, 1, 2]);
  const a = spans.get(0), c = spans.get(2);
  assert.ok(a.min > c.min, "charIdx 0 is the first character and must be laid out rightmost");
});

test("RTL multi-line keeps each line's own order and global char indices", () => {
  const spans = spansByCharIdx(font("rtl"), "AB\nCA");
  // "AB\nCA": indices 0,1 then the newline at 2, then 3,4.
  assert.deepStrictEqual([...spans.keys()].sort((x, y) => x - y), [0, 1, 3, 4],
    "index 2 is the newline and must consume exactly one position");
});

test("a shipped RTL font carries dir and its glyphs are Hebrew, not Arabic", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const fb = require("../src/fontbin.js");
  const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
  // src/fonts/bin/ is COMMITTED, so this should never fire in a real checkout.
  // It throws on CI anyway: a test that returns early asserts NOTHING and still
  // reports green, which is the exact shape that has bitten this suite before
  // (test/crossval-stitch-formats.test.js throws on CI for the same reason). A
  // missing font library on CI means the build did not run — not that there is
  // nothing to check.
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return;
  }
  const rtl = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"))
    .map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))])
    .filter(([, font]) => font.dir === "rtl");
  assert.ok(rtl.length > 0,
    "no shipped font is marked dir:rtl — the Hebrew faces are the reason this check exists, " +
    "so an empty set means it is asserting nothing");
  for (const [key, font] of rtl) {
    const chars = Object.keys(font.glyphs).filter((c) => [...c].length === 1);
    const arabic = chars.filter((c) => c.codePointAt(0) >= 0x0600 && c.codePointAt(0) <= 0x06ff);
    assert.strictEqual(arabic.length, 0,
      `${key} ships Arabic glyphs, but EMB-Bot has no letter-joining engine — ` +
      `its letters would render unjoined, which is wrong text, not plain text`);
    assert.ok(chars.some((c) => c.codePointAt(0) >= 0x0590 && c.codePointAt(0) <= 0x05ff),
      `${key} is marked rtl but carries no Hebrew glyphs`);
  }
});
