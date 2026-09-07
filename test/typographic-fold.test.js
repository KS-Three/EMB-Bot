// A customer types an apostrophe. Their phone substitutes U+2019 for it.
//
// 26 of the 85 shipped fonts have no glyph for that codepoint, so the
// character was dropped SILENTLY: measured 2026-09-07 in the shipped app,
// "Fritsch's Stitches" gave 1,354 stitches with the straight apostrophe and
// 1,326 with the curly one, and the note explaining it named a character that
// looks exactly like the one they typed, inside quotation marks made of the
// same mark — then advised switching fonts, when the real difference was one
// invisible codepoint.
//
// At thread resolution a curly apostrophe and a straight one are the same
// mark, so `satinfont.js` stitches the twin when — and only when — the font
// has no glyph for the typographic form. Measured across the library, that
// rescues 367 font x character combinations.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const SF = require("../src/satinfont.js");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const loadFont = (key) => fb.decodeFontBin(new Uint8Array(fs.readFileSync(path.join(BIN, key + ".embf"))));
const OPTS = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, letterSpacingMm: 0, underlay: false };
const lay = (font, text) => SF.layoutText(font, text, OPTS);

test("the fold map is exported, and every entry maps to a plain-ASCII twin", () => {
  const fold = SF.TYPOGRAPHIC_FOLD;
  assert.ok(fold && typeof fold === "object", "TYPOGRAPHIC_FOLD must be exported — fontCoverage.js reads it off EMB");
  const entries = Object.entries(fold);
  assert.ok(entries.length >= 20, `expected the punctuation set, got ${entries.length}`);
  for (const [from, to] of entries) {
    assert.equal(to.length, 1, `${JSON.stringify(from)} -> ${JSON.stringify(to)} must be one character`);
    assert.ok(to.codePointAt(0) < 128, `${JSON.stringify(to)} is not ASCII — the twin must be the plain form`);
    assert.ok(from.codePointAt(0) !== to.codePointAt(0), "a character must not fold to itself");
    // Only marks whose ASCII twin is the SAME mark. No letters: an accented
    // letter is a different letter to someone whose name carries it.
    assert.ok(!/[A-Za-z0-9]/.test(from), `${JSON.stringify(from)} looks like a letter or digit — out of scope`);
  }
});

test("a curly apostrophe stitches identically to a straight one where the font lacks it", () => {
  // medium_font is the Studio default and has no U+2019.
  const font = loadFont("medium_font");
  assert.ok(!font.glyphs["’"], "medium_font gained a U+2019 glyph — pick another font for this case");
  assert.ok(font.glyphs["'"], "medium_font must have the plain apostrophe for the fold to have anywhere to go");

  const straight = lay(font, "Fritsch's");
  const curly = lay(font, "Fritsch’s");
  assert.deepEqual(curly.unsupported, [], "the curly form must no longer be reported as unstitchable");
  // Full geometry, not run counts: counts coincide between DIFFERENT glyphs
  // (alchemy's two apostrophes do), so a count comparison passes against the
  // defect. The claim here is that the two spellings sew the SAME thread.
  const geom = (l) => JSON.stringify(l.runs.map((r) => r.pts));
  assert.equal(geom(curly), geom(straight), "the two spellings must sew identically");
});

test("an em dash folds; a curly quote the same font OWNS does not", () => {
  // Both halves of the rule on one font, which is the clearest statement of
  // it: medium_font lacks U+2014 and has U+201C, so the dash folds to a
  // hyphen and the quote keeps its own glyph. Written as a pair after the
  // first draft asserted the quote folded too and failed — correctly.
  const font = loadFont("medium_font");
  const geom = (l) => JSON.stringify(l.runs.map((r) => r.pts));

  assert.ok(!font.glyphs["—"], "medium_font gained an em dash — this case needs a font without one");
  const dash = lay(font, "Mom — 2026");
  assert.deepEqual(dash.unsupported, [], "the em dash must no longer be reported as unstitchable");
  assert.equal(geom(dash), geom(lay(font, "Mom - 2026")), "the em dash must sew as a hyphen");

  assert.ok(font.glyphs["“"], "medium_font lost its curly quote — this case needs a font that has one");
  assert.notEqual(
    geom(lay(font, "“Best”")), geom(lay(font, '"Best"')),
    "medium_font owns the curly quotes, so they must keep sewing as themselves"
  );
});

test("a font that HAS the typographic glyph keeps using it — the fold never downgrades", () => {
  // Find a shipped font that owns U+2019 and whose two glyphs differ.
  const keys = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf")).map((f) => f.replace(/\.embf$/, ""));
  let font = null, key = null;
  for (const k of keys) {
    const f = loadFont(k);
    if (f.glyphs["’"] && f.glyphs["'"] &&
        JSON.stringify(f.glyphs["’"]) !== JSON.stringify(f.glyphs["'"])) { font = f; key = k; break; }
  }
  assert.ok(font, "no shipped font has DISTINCT glyphs for U+2019 and U+0027 — this guard has nothing to check");
  const curly = lay(font, "a’b");
  const plain = lay(font, "a'b");
  // Geometry, not run counts: two distinct glyphs routed at the same spacing
  // can land on the same NUMBER of points while sewing different shapes, which
  // is exactly what alchemy does — a count comparison here passes against the
  // defect it is meant to catch.
  const geom = (l) => JSON.stringify(l.runs.map((r) => r.pts));
  assert.notEqual(
    geom(curly), geom(plain),
    `${key} owns both glyphs, so the two spellings must still sew differently — the fold fired where it should not have`
  );
});

test("a character with no twin is still reported, so the message survives", () => {
  const font = loadFont("medium_font");
  const out = lay(font, "Emb 日本");   // Japanese: nothing folds to ASCII
  assert.deepEqual(out.unsupported, ["日", "本"],
    "characters outside the fold must still reach the customer-facing message");
});
