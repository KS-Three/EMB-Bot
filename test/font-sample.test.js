// What a font's preview tile says (2026-08-22).
//
// The grid of tiles in the font browser is the only thing a customer sees
// before picking a font, and when the sample picks badly NOTHING FAILS — the
// tile just quietly says less. That is a defect class with no natural alarm,
// so it gets a test.
//
// It had already happened to three of the 85. `sampleFor` accepted the font's
// name only if EVERY character rendered, so one missing glyph dropped it all
// the way to "first six alphanumerics in glyph-key order":
//
//   fold_inkstitch      "Fold Ink/Stitch" — no "/" glyph — tile read "012345"
//   hebrew_font_large   "חוכמה Large"     — no Latin      — tile read "אבגדה"
//   hebrew_font_medium  ditto
//
// Two of those are from this same branch. The any-script fallback added here
// stopped the Hebrew faces rendering nothing at all, and stopped there — "the
// first five letters of the alphabet" beats an empty tile and loses to the
// font's own name.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");

// src/fonts/bin/ is COMMITTED; a missing library on CI means the build did not
// run, not that there is nothing to check.
function library() {
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return null;
  }
  const files = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"));
  assert.ok(files.length > 50, `only ${files.length} .embf files — the library did not build`);
  return files.map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))]);
}

// A sample is "name-derived" when every character in it also appears in the
// font's name. That is the property worth holding: a tile should show the
// font, not an arbitrary slice of its glyph table.
const derivedFromName = (sample, name) => {
  const pool = new Set([...String(name).toUpperCase()]);
  return sample.length > 0 && [...sample.toUpperCase()].every((c) => pool.has(c));
};

test("every shipped font's tile is derived from its own name", async () => {
  const { sampleFor } = await import("../tools/font-sample.mjs");
  const all = library();
  if (!all) return;
  const arbitrary = [];
  for (const [key, font] of all) {
    const s = sampleFor(font);
    if (!derivedFromName(s, font.name || ""))
      arbitrary.push(`${key}: name ${JSON.stringify(font.name)} but tile shows ${JSON.stringify(s)}`);
  }
  // Measured 2026-08-22: 85 of 85 are name-derived, zero fall through. If a
  // font legitimately cannot show its own name — a pictogram pack whose name
  // is Latin and whose glyphs are symbols — that is a real exception and
  // belongs here with a note, not a widened assertion.
  assert.deepStrictEqual(arbitrary, []);
});

test("the three fonts this was found on show their names", async () => {
  const { sampleFor } = await import("../tools/font-sample.mjs");
  const all = library();
  if (!all) return;
  const byKey = new Map(all);
  for (const [key, want] of [
    ["fold_inkstitch", "FOLD INKSTITCH"],   // was "012345" — the name has a "/" the font lacks
    ["hebrew_font_large", "חוכמה"],          // was "אבגדה"  — the name has Latin the font lacks
    ["hebrew_font_medium", "חוכמה"],
  ]) {
    const font = byKey.get(key);
    if (!font) continue; // pulled from the library
    assert.strictEqual(sampleFor(font), want, `${key}'s tile changed`);
  }
});

// The fallbacks below the name are not dead code — they are what a pictogram
// pack gets — so exercise them rather than letting them rot untested.
test("a font that truly cannot set its name still falls back, in order", async () => {
  const { sampleFor } = await import("../tools/font-sample.mjs");
  const glyphsOf = (chars) => Object.fromEntries([...chars].map((c) => [c, { adv: 10 }]));

  // Nothing of the name is renderable, but it has alphanumerics: those —
  // LETTERS FIRST. Object.keys puts integer-like keys ahead of everything
  // regardless of insertion order, so an unordered fallback returns "123ABC",
  // and a tile of digits says almost nothing about a typeface. This assertion
  // caught that while being written.
  assert.strictEqual(
    sampleFor({ name: "!!!", glyphs: glyphsOf("ABC123XYZ") }), "ABCXYZ",
    "letters must come before digits in the alphanumeric fallback");

  // No alphanumerics at all — a symbol pack shows its symbols, which IS its
  // honest preview.
  assert.strictEqual(
    sampleFor({ name: "Pictograms", glyphs: glyphsOf("★☂☃☘☔☕") }), "★☂☃☘☔",
    "a symbol pack should show its own symbols");

  // Two characters of a name is not a tile; it must fall through, not be
  // accepted by the partial-name rule.
  assert.strictEqual(
    sampleFor({ name: "AB!!!!", glyphs: glyphsOf("AB1234567") }), "AB1234",
    "a 2-character survivor is below the floor and must fall through to the " +
    "alphanumerics — which, letters first, start AB");
});

test("a font whose name renders is untouched by the partial rule", async () => {
  const { sampleFor } = await import("../tools/font-sample.mjs");
  const all = library();
  if (!all) return;
  const byKey = new Map(all);
  // medium_font's name contains a "/" too — and it HAS that glyph, so it must
  // come through whole. This is the control that stops the partial rule from
  // quietly trimming names it should leave alone.
  const font = byKey.get("medium_font");
  if (!font) return;
  assert.strictEqual(sampleFor(font), font.name);
  assert.ok(String(font.name).includes("/"), "medium_font's name should still contain the slash this pins");
});
