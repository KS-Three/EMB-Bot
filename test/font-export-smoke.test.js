// Every shipped font survives the export path (2026-08-22).
//
// The cross-validation tests pin the PES/EXP/DST encoders against pystitch, but
// they do it on synthetic fixtures — no font has ever gone through an encoder
// in a test. That was defensible while the library was uniformly satin, since
// every font produced the same SHAPE of stitch stream.
//
// It stopped being defensible on this branch. The library now ships 19
// runs-only (bean/running-stitch) faces whose streams are structurally
// different from satin output — different jump and trim patterns, different
// stitch density — plus two Hebrew faces laid out right-to-left. None of that
// geometry had ever reached an encoder outside a browser.
//
// So: build a real design from each font and put it through all three formats.
// This is a smoke test, deliberately. It asserts the encoders do not throw and
// that DST round-trips its own stitch count; it does NOT assert byte content,
// which is crossval-stitch-formats.test.js's job against pystitch.
//
// Note DST here is EMB-Bot's own codec, which is transposed against the
// Tajima convention and is EMB-Bot-internal only (CLAUDE.md, and
// .claude/memory/dst-codec-axis-discrepancy). A self round-trip is still the
// right check: it detects the encoder breaking, which is what this guards.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");
for (const m of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                 "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp",
                 "pes", "fonts", "digitize"])
  require("../src/" + m + ".js");
const EMB = globalThis.EMB;

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const OPTS = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };

// src/fonts/bin/ is COMMITTED; a missing library on CI means the build did not
// run, which is not the same as there being nothing to check.
// Also memoised — decoding 85 binaries is not free either.
let _lib;
function library() {
  if (_lib !== undefined) return _lib;
  return (_lib = libraryUncached());
}
function libraryUncached() {
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return null;
  }
  const files = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"));
  assert.ok(files.length > 50, `only ${files.length} .embf files — the library did not build`);
  return files.map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))]);
}

// The font's own first few letters, whatever the script — a fixed "ABC" would
// silently test nothing on the Hebrew faces.
//
// Memoised: building 85 designs costs about three seconds and all three tests
// below need the same ones, so without this the file pays it three times.
const _designs = new Map();
const designFor = (font) => {
  if (_designs.has(font)) return _designs.get(font);
  const chars = Object.keys(font.glyphs)
    .filter((k) => [...k].length === 1 && k !== " " && /^\p{L}$/u.test(k))
    .slice(0, 3).join("");
  const d = chars ? EMB.buildLetteringDesign(font, chars, OPTS) : null;
  _designs.set(font, d);
  return d;
};

test("every shipped font encodes to DST, EXP and PES without throwing", () => {
  const all = library();
  if (!all) return;
  const failures = [];
  for (const [key, font] of all) {
    const d = designFor(font);
    if (!d || !d.stitches || !d.stitches.length) { failures.push(`${key}: produced no design`); continue; }
    for (const [fmt, enc] of [["DST", EMB.encodeDST], ["EXP", EMB.encodeEXP], ["PES", EMB.encodePES]]) {
      try {
        const bytes = enc(d);
        if (!bytes || !bytes.length) failures.push(`${key}: ${fmt} encoded to nothing`);
      } catch (e) {
        failures.push(`${key}: ${fmt} threw ${e.message}`);
      }
    }
  }
  assert.deepStrictEqual(failures, []);
});

test("DST round-trips each font's own stitch count", () => {
  const all = library();
  if (!all) return;
  const drift = [];
  for (const [key, font] of all) {
    const d = designFor(font);
    if (!d) continue;
    const back = EMB.decodeDST(EMB.encodeDST(d));
    const before = d.stitches.filter((s) => s.type === "stitch").length;
    const after = (back.stitches || []).filter((s) => s.type === "stitch").length;
    // One stitch of slack: the terminal "end" record's handling differs by a
    // single stitch in this codec, a known and deliberately unfixed quirk
    // (see crossval-stitch-formats.test.js and the DST axis verdict).
    if (Math.abs(before - after) > 1) drift.push(`${key}: ${before} -> ${after}`);
  }
  assert.deepStrictEqual(drift, []);
});

// The reason this file exists, asserted rather than assumed: if the runs-only
// faces stopped being in the library, or stopped producing bean-stitch output,
// this whole file would go back to testing only what crossval already covers.
test("the runs-only faces are really in this sample — they are why it exists", () => {
  const all = library();
  if (!all) return;
  const runsOnly = all.filter(([, font]) =>
    !Object.values(font.glyphs).some((g) => (g.cols || []).length));
  assert.ok(runsOnly.length >= 10,
    `only ${runsOnly.length} runs-only fonts reached the export path — this file was ` +
    `written because 19 of them ship, and without them it duplicates crossval`);
  for (const [key, font] of runsOnly) {
    const d = designFor(font);
    assert.ok(d && d.stitchCount > 0, `${key} is runs-only and produced no stitches to export`);
  }
});
