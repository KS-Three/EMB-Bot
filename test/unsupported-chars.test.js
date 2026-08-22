// Characters a font has no glyph for (2026-08-22).
//
// The lettering path advances the pen past a character it cannot render and
// stitches nothing for it, silently. That was survivable while every font in
// the library was Latin — you would have to type an unusual accent to hit it.
// Adding Hebrew made it reachable in one click: pick a Hebrew font, type "Emb",
// and buildLetteringDesign returns a structurally valid design of 0 stitches at
// 0x0mm, with nothing anywhere saying why.
//
// The engine cannot decide what the UI should SAY about that, but it can stop
// hiding it. `unsupported` lists the characters that were dropped, and it is
// reported on the empty-design early returns too — which is the case that
// actually needs explaining.
const assert = require("node:assert");
const { test } = require("node:test");
for (const m of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                 "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
  require("../src/" + m + ".js");
const EMB = globalThis.EMB;

const OPTS = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
const glyph = (w) => ({
  adv: w,
  cols: [{ railA: [[0, 0], [0, 40]], railB: [[w - 10, 0], [w - 10, 40]], rungs: [] }],
  runs: [],
});
const fontOf = (chars, dir) => ({
  name: "Fixture", license: "OFL", unitsPerEm: 100, sizeMm: 20,
  advDefault: 50, advSpace: 30, kerning: {},
  glyphs: Object.fromEntries([...chars].map((c) => [c, glyph(50)])),
  ...(dir ? { dir } : {}),
});

test("a font that renders every character reports nothing unsupported", () => {
  const d = EMB.buildLetteringDesign(fontOf("ABC"), "ABC", OPTS);
  assert.ok(d.stitchCount > 0);
  assert.deepStrictEqual(d.unsupported, []);
});

test("dropped characters are reported", () => {
  const d = EMB.buildLetteringDesign(fontOf("ABC"), "AXBY", OPTS);
  assert.deepStrictEqual(d.unsupported, ["X", "Y"]);
});

test("an EMPTY design still reports why — the case that needs explaining", () => {
  // Nothing in "XYZ" exists in the font, so the design is 0 stitches at 0x0mm.
  // This goes through an early return that used to hand back a bare `empty`
  // object, which is how the Hebrew case failed silently.
  const d = EMB.buildLetteringDesign(fontOf("ABC"), "XYZ", OPTS);
  assert.strictEqual(d.stitchCount, 0);
  assert.deepStrictEqual(d.unsupported, ["X", "Y", "Z"],
    "an empty design must say which characters it could not render");
});

test("the report is deduplicated and in SOURCE order, including for RTL", () => {
  // An RTL line is laid out in reverse, so collecting characters as they are
  // placed would report "Emb" as b,m,E — the order they were positioned in, and
  // useless in a message to a person.
  const ltr = EMB.buildLetteringDesign(fontOf("A"), "AXXY", OPTS);
  assert.deepStrictEqual(ltr.unsupported, ["X", "Y"], "duplicates must collapse");
  const rtl = EMB.buildLetteringDesign(fontOf("A", "rtl"), "AXXY", OPTS);
  assert.deepStrictEqual(rtl.unsupported, ["X", "Y"],
    "RTL must still report in source order, not layout order");
});

test("empty text is not an unsupported-character problem", () => {
  const d = EMB.buildLetteringDesign(fontOf("ABC"), "", OPTS);
  assert.strictEqual(d.stitchCount, 0);
  assert.deepStrictEqual(d.unsupported, [], "no text means nothing was dropped");
});

test("a space is never reported — it is laid out, not missing", () => {
  const d = EMB.buildLetteringDesign(fontOf("AB"), "A B", OPTS);
  assert.deepStrictEqual(d.unsupported, []);
});

// --- glyphs that EXIST but sew nothing (2026-08-22) ---
//
// The report above covers characters the font has no glyph for. A glyph that
// is present but produces no stitches leaves exactly the same hole in the
// stitched text, and reporting one while staying silent about the other makes
// the note read as a promise it does not keep.
//
// It is reachable in the SELLABLE library, not just in theory: measured across
// all 85 shipped fonts there are two such glyphs — western_light's "ç" and
// ondulamarif_XL's "º" — so typing "façade" in western_light drops the ç with
// nothing said. The personal build is where it bites hardest: paquerette has
// 52 of its 82 letter glyphs in this state — 31 of the 52 A-Za-z ones, which
// is the figure this repo usually quotes — because only 72 of its 1,641 runs
// carry an authored stitch length and a run without one is never sewn.
const deadGlyph = { adv: 50, cols: [], runs: [[[0, 0], [0, 40]]] }; // bare array: no lenMm, never sewn

test("a glyph that exists but sews nothing is reported, like a missing one", () => {
  const f = fontOf("AB");
  f.glyphs["C"] = deadGlyph;
  const lay = EMB.layoutText(f, "ABC", { emMm: 20, pxPerMm: 8 });
  assert.deepStrictEqual(lay.unsupported, ["C"],
    "a present-but-unstitchable glyph leaves the same hole as a missing one");
});

test("a run WITH an authored stitch length is not reported", () => {
  const f = fontOf("AB");
  f.glyphs["C"] = { adv: 50, cols: [], runs: [{ pts: [[0, 0], [0, 40]], lenMm: 2 }] };
  const lay = EMB.layoutText(f, "ABC", { emMm: 20, pxPerMm: 8 });
  assert.deepStrictEqual(lay.unsupported, [],
    "runs-only fonts are stitchable and must not be reported as holes");
});

test("a cross-stitch region counts as stitchable only with a grid to fill it", () => {
  const cross = { adv: 50, cols: [], runs: [{ pts: [[0, 0], [0, 40], [40, 40]], fill: "cross" }] };
  const noGrid = fontOf("AB"); noGrid.glyphs["C"] = cross;
  assert.deepStrictEqual(EMB.layoutText(noGrid, "ABC", { emMm: 20, pxPerMm: 8 }).unsupported, ["C"],
    "without font.crossGrid crossFill emits nothing, so the glyph is a hole");
  const withGrid = fontOf("AB");
  withGrid.glyphs["C"] = cross;
  withGrid.crossGrid = { step: 10, offX: 0, offY: 0, method: "simple_cross" };
  assert.deepStrictEqual(EMB.layoutText(withGrid, "ABC", { emMm: 20, pxPerMm: 8 }).unsupported, [],
    "with a grid the region fills, so it is not a hole");
});

test("an unstitchable glyph keeps its OWN advance, not the font default", () => {
  // A hole of the right width beats collapsing the text — the letters around
  // it must not shift. font.advDefault is 50 here, so a 90-unit dead glyph
  // proves the glyph's own advance is what was used.
  //
  // This one passes both before and after the change, deliberately: the old
  // code reached the same width by a different route (it pushed the dead glyph
  // into the layout and let `penX += g.adv` run). It is here to PIN that width
  // now that the glyph takes an early exit, where `font.advDefault` would have
  // been the easy and wrong thing to write.
  const f = fontOf("AB");
  f.glyphs["C"] = { adv: 90, cols: [], runs: [[[0, 0], [0, 40]]] };
  const wide = EMB.layoutText(f, "ACB", { emMm: 20, pxPerMm: 8 });
  const f2 = fontOf("AB");
  f2.glyphs["C"] = { adv: 50, cols: [], runs: [[[0, 0], [0, 40]]] };
  const narrow = EMB.layoutText(f2, "ACB", { emMm: 20, pxPerMm: 8 });
  const width = (l) => l.bbox.x1 - l.bbox.x0;
  assert.ok(width(wide) > width(narrow),
    `a 90-unit dead glyph must leave a wider hole than a 50-unit one ` +
    `(got ${width(wide).toFixed(1)} vs ${width(narrow).toFixed(1)})`);
});

test("the real library case: western_light's ç is reported", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const fb = require("../src/fontbin.js");
  const p = path.join(__dirname, "..", "src", "fonts", "bin", "western_light.embf");
  // src/fonts/bin/ is COMMITTED; on CI a missing library means the build did
  // not run, which is not the same as "nothing to check".
  if (!fs.existsSync(p)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return;
  }
  const font = fb.decodeFontBin(fs.readFileSync(p));
  assert.ok(font.glyphs["ç"], "western_light must still HAVE a ç glyph — that is the whole point");
  const lay = EMB.layoutText(font, "façade", { emMm: 20, pxPerMm: 8 });
  assert.deepStrictEqual(lay.unsupported, ["ç"],
    "the one letter in this font that sews nothing must be named, and nothing else");
});
