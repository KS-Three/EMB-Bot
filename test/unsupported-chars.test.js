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
