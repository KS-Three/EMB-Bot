// Kerning lookup + sign, per Ink/Stitch's lib/lettering/font.py: pair keys are
// "A V" (space-separated; older fonts concatenate "AV"), and the value is
// SUBTRACTED from the advance. Before this test, layoutText looked up only the
// concatenated key — missing every pair in 58 of the 66 kerned shipped fonts —
// and added the value, pushing the remaining fonts' kerned pairs apart.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");
for (const m of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                 "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
  require("../src/" + m + ".js");
const EMB = globalThis.EMB;
const load = (n) => fb.decodeFontBin(fs.readFileSync(path.join(__dirname, "..", "src", "fonts", "bin", n + ".embf")));
const width = (font, text) => { const b = EMB.layoutText(font, text, { emMm: 30, pxPerMm: 10 }).bbox; return b.x1 - b.x0; };
const unkerned = (font) => Object.assign({}, font, { kerning: {} });

for (const [name, key] of [["roman_ags", "A V"], ["sunset", "AV"]]) {
  test(`${name}: positive "${key}" kerning pulls A and V together`, () => {
    const font = load(name);
    assert.ok(font.kerning[key] > 0, `fixture: ${name} should carry a positive ${key} pair`);
    const kerned = width(font, "AV"), plain = width(unkerned(font), "AV");
    const expectPx = font.kerning[key] * (30 / font.unitsPerEm) * 10;
    assert.ok(Math.abs((plain - kerned) - expectPx) < 1e-6,
      `AV should be ${expectPx.toFixed(2)}px narrower with kerning; got ${(plain - kerned).toFixed(2)}`);
  });
}

