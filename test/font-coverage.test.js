// The committed coverage index must describe the committed font binaries.
//
// `src/fonts/manifest-coverage.json` answers "which shipped font can stitch this
// character", and the Studio turns that into a sentence a customer acts on
// ("Кирилиця, Egyptian and Egyptian Small can — switch fonts and it will
// stitch"). A stale index is worse than none: it sends someone to a font that
// cannot set their name.
//
// This is the same seam guard the repo already runs between the engine and the
// Studio (test/embf-guard.test.js, digitizer/tests/test_code_wires.py,
// test_fabric_wire.py): re-derive the artifact from its source and compare.
// It is cheap — the derivation is a key walk over 85 already-decoded fonts.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
// "manifest-" prefixed, because src/fonts/*.json is enumerated as font
// SOURCES by both the build and embf-guard, which exclude exactly that prefix.
const COVERAGE = path.join(__dirname, "..", "src", "fonts", "manifest-coverage.json");

// Re-derived here rather than imported from tools/build-font-coverage.mjs on
// purpose: importing the builder would let a bug in the builder agree with
// itself. This is a second, independent expression of the same rule.
function rangesOf(font) {
  const cps = Object.keys(font.glyphs || {})
    .filter((c) => [...c].length === 1)
    .map((c) => c.codePointAt(0))
    .sort((a, b) => a - b);
  const out = [];
  for (const cp of cps) {
    const last = out[out.length - 1];
    if (last && cp === last[1] + 1) last[1] = cp;
    else out.push([cp, cp]);
  }
  return out.map(([a, b]) => (a === b ? a : [a, b]));
}

function covers(ranges, cp) {
  for (const r of ranges) {
    if (typeof r === "number") { if (r === cp) return true; continue; }
    if (cp >= r[0] && cp <= r[1]) return true;
  }
  return false;
}

let _lib;
function library() {
  if (_lib !== undefined) return _lib;
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return (_lib = null);
  }
  return (_lib = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf")).sort()
    .map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))]));
}

test("coverage.json names exactly the fonts that ship", () => {
  const all = library();
  if (!all) return;
  const cov = JSON.parse(fs.readFileSync(COVERAGE, "utf8"));
  assert.deepStrictEqual(
    Object.keys(cov.fonts).sort(),
    all.map(([k]) => k),
    "run `node tools/build-font-coverage.mjs` — the index and src/fonts/bin/ disagree on WHICH fonts exist"
  );
});

test("every font's ranges are exactly its own glyphs — no drift, in either direction", () => {
  const all = library();
  if (!all) return;
  const cov = JSON.parse(fs.readFileSync(COVERAGE, "utf8")).fonts;
  const drifted = [];
  for (const [key, font] of all) {
    const want = JSON.stringify(rangesOf(font));
    if (JSON.stringify(cov[key]) !== want) drifted.push(key);
  }
  assert.deepStrictEqual(drifted, [],
    "run `node tools/build-font-coverage.mjs` — these fonts' coverage no longer matches their binary");
});

test("the index answers the questions the Studio actually asks it", () => {
  // Not a re-derivation: these are the scripts a customer types, checked
  // against the shipped library as a whole. They are allowed to move when the
  // library does — what must never happen is the index saying a font covers a
  // script the binary cannot set, which is what the two tests above pin.
  const all = library();
  if (!all) return;
  const cov = JSON.parse(fs.readFileSync(COVERAGE, "utf8")).fonts;
  const fontsFor = (text) => Object.keys(cov)
    .filter((k) => [...text].every((c) => covers(cov[k], c.codePointAt(0)))).sort();

  // Latin is the floor: essentially the whole library, or something is wrong
  // with the index rather than with the fonts.
  assert.ok(fontsFor("Sam").length > 50, "Latin: " + fontsFor("Sam").length);
  // Measured 2026-09-07 — the three scripts the library DOES cover, and the
  // ones it does not. Asserted as non-empty/empty rather than as a count, so
  // adding a Cyrillic font is not a test failure.
  assert.ok(fontsFor("Иван").length > 0, "no Cyrillic font — the suggestion has nothing to offer");
  assert.ok(fontsFor("Δοκιμή").length > 0, "no Greek font");
  assert.ok(fontsFor("שלום").length > 0, "no Hebrew font");
  assert.strictEqual(fontsFor("日本語").length, 0,
    "a font now covers Japanese — good, but the 'no font can stitch this' message needs re-checking");
  // The trap this test also exists for: `caffeine_KOR`/`magnolia_KOR` are
  // named for their designer's origin, not their script. They hold ASCII and
  // Latin-1 and no Hangul at all, so a customer who picks one to type Korean
  // gets nothing — and the suggestion must not send them there.
  assert.strictEqual(fontsFor("한국어").length, 0, "a font now covers Hangul — see above");
  for (const k of ["caffeine_KOR", "magnolia_KOR"]) {
    if (cov[k]) assert.ok(!covers(cov[k], "한".codePointAt(0)), k + " unexpectedly covers Hangul");
  }
});
