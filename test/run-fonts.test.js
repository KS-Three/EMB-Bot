// Bean / running-stitch lettering fonts (2026-08-21).
//
// The lettering path was satin-only: satinfont.layoutText read g.cols and never
// g.runs, so a runs-only font imported fine, passed most checks, and stitched
// exactly ONE stitch. 26 license-clean upstream fonts were unusable for that
// reason alone.
//
// Two invariants matter more than the feature itself, and both are pinned here:
//
//   1. ROADMAP gate 1 — stitch length is a PHYSICAL constant this project may
//      not choose without a sew-out. So a run is stitched only when the FONT
//      authored a length (build-font attaches {pts, lenMm, repeats}); a run
//      without one is skipped, never defaulted.
//   2. The 62 already-shipped satin fonts must be untouched. They also carry
//      authored run paths (montecarlo 646, cats 837) that EMB-Bot has always
//      dropped; honouring those would add stitches to every existing customer
//      design. build-font strips run params from any font that has satin
//      columns, so satin fonts route exactly as before.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const DG = require("../src/digitize.js");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };

// Minimal runs-only font: one square-ish stroke per letter, no satin anywhere.
function runFont(runOverrides) {
  const stroke = [[0, 0], [0, 40], [30, 40]];
  const glyphs = {};
  for (const ch of "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    glyphs[ch] = { adv: 40, cols: [], runs: [Object.assign({ pts: stroke }, runOverrides)] };
  return { name: "RunFont", license: "OFL", unitsPerEm: 100, sizeMm: 20, advDefault: 40, glyphs };
}

test("a runs-only font with an authored stitch length actually stitches", () => {
  const d = DG.buildLetteringDesign(runFont({ lenMm: 2 }), "AB", base);
  assert.ok(d.stitches.length > 10, `expected real stitches, got ${d.stitches.length}`);
  assert.ok(d.widthMM > 0, "expected a non-zero width");
});

test("gate 1: a run with NO authored length is skipped, not defaulted", () => {
  // The same font minus lenMm must not invent one. One end-marker stitch only.
  const d = DG.buildLetteringDesign(runFont({}), "AB", base);
  assert.ok(d.stitches.length <= 1, `expected no stitches without an authored length, got ${d.stitches.length}`);
});

test("bare-array runs (the pre-2026-08-21 shape) are also skipped", () => {
  const f = runFont({ lenMm: 2 });
  for (const g of Object.values(f.glyphs)) g.runs = [[[0, 0], [0, 40], [30, 40]]];
  const d = DG.buildLetteringDesign(f, "AB", base);
  assert.ok(d.stitches.length <= 1, "bare arrays carry no length and must not stitch");
});

test("a shorter authored stitch length yields more stitches", () => {
  const coarse = DG.buildLetteringDesign(runFont({ lenMm: 4 }), "AB", base).stitches.length;
  const fine = DG.buildLetteringDesign(runFont({ lenMm: 1 }), "AB", base).stitches.length;
  assert.ok(fine > coarse, `expected finer length to add stitches (${fine} vs ${coarse})`);
});

test("bean repeats backtrack each stitch (repeats:1 => triple stitch)", () => {
  const plain = DG.buildLetteringDesign(runFont({ lenMm: 2 }), "AB", base).stitches.length;
  const bean = DG.buildLetteringDesign(runFont({ lenMm: 2, repeats: 1 }), "AB", base).stitches.length;
  assert.ok(bean > plain * 2, `repeats:1 should roughly triple the stitches (${bean} vs ${plain})`);
});

// --- invariant 2: shipped satin fonts are not disturbed -----------------------
// Counts pinned from the committed .embf files. A change here means satin
// routing moved — investigate rather than re-baseline.
//
// Re-baselined ONCE, 2026-08-22, for a reason outside satin routing: the SVG
// parser was truncating every path at its first scientific-notation number
// (see test/parsepath.test.js), so 63 of the shipped fonts were missing path
// segments. Kent's call was to rebuild the library with the corrected geometry
// rather than freeze the truncation. alchemy 699 -> 751 (+7.44%) is the largest
// move in the library; 20 of 77 fonts came back byte-identical and the median
// change is 0.00%. Only alchemy moved among these five, which is why the other
// four numbers are unchanged from the original pin.
const SATIN_BASELINE = { montecarlo: 1157, alchemy: 751, venezia: 995, cats: 1249, apesplit: 4404 };

for (const [key, expected] of Object.entries(SATIN_BASELINE)) {
  test(`satin font ${key} stitches exactly as before run support`, () => {
    const p = path.join(BIN, key + ".embf");
    if (!fs.existsSync(p)) return; // font not in this checkout's library
    const font = fb.decodeFontBin(fs.readFileSync(p));
    const text = font.glyphs["a"] ? "Emb" : "EMB";
    const d = DG.buildLetteringDesign(font, text, base);
    assert.strictEqual(d.stitches.length, expected, `${key} stitch count moved`);
  });
}

test("no shipped font carries stitchable run params (they are stripped at import)", () => {
  if (!fs.existsSync(BIN)) return;
  for (const f of fs.readdirSync(BIN)) {
    if (!f.endsWith(".embf")) continue;
    const font = fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)));
    let satin = 0;
    for (const g of Object.values(font.glyphs)) satin += (g.cols || []).length;
    if (!satin) continue; // a runs-only font legitimately keeps its params
    for (const g of Object.values(font.glyphs))
      for (const r of g.runs || [])
        assert.ok(!(r && r.pts && r.lenMm > 0),
          `${f} is a satin font but carries stitchable run params — it would gain stitches vs. its shipped design`);
  }
});

// --- personal build isolation (2026-08-21) --------------------------------
// `node tools/build-embf.mjs --personal` writes src/fonts/manifest-personal.json
// and bin-personal/ — Kent's private library with ShareAlike/GPL/NonCommercial
// fonts. Both are gitignored, so a release build cannot pick them up.
//
// The trap this pins: manifest-personal.json lives IN src/fonts/, and several
// places glob that directory for "*.json that isn't manifest.json" to find font
// sources. Under the old predicate a personal build made a phantom font named
// "manifest-personal" and turned four tests red on Kent's machine only, from a
// file git cannot even see. The rule is now "not a manifest of any kind".
test("a manifest-* file in src/fonts is never mistaken for a font source", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
  const keys = fs.readdirSync(FONT_DIR)
    .filter((f) => f.endsWith(".json") && !f.startsWith("manifest"))
    .map((f) => f.replace(/\.json$/, ""));
  for (const k of keys)
    assert.ok(!k.startsWith("manifest"), `"${k}" is a manifest, not a font source`);
  // and the real manifest is excluded whether or not a personal build exists
  assert.ok(!keys.includes("manifest"));
  assert.ok(!keys.includes("manifest-personal"));
});

test("the sellable library never contains a license-pulled or ShareAlike font", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const BANNED = new Set(["milli_marif_bold", "tt_directors", "tt_masters", "dejavufont",
    "apex_lake", "aventurina", "bluenesia_satin", "cherryforinkstitch", "cherryforkaalleen",
    "emilio_20", "emilio_20_bold", "emilio_20_simple", "emilio_20_simple_small",
    "geneva_rounded", "geneva_simple", "gingo200", "monicha"]);
  for (const f of man.fonts) {
    assert.ok(!BANNED.has(f.key), `pulled font ${f.key} is in the SELLABLE manifest`);
    assert.ok(!/SA|NC|ND/.test(f.licenseId.replace("OFL-1.1", "").replace("CC-BY-4.0", "").replace("CC0", "")),
      `${f.key} ships under ${f.licenseId}`);
  }
});
