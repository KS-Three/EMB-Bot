// buildLetteringDesign reports `fitMm`: the extent the width/hoop fit sized the
// lettering to ({ w, h }, in the element's own rotation). The Studio's "Rotate
// to fit" (app/src/lib/hoop.js) turns lettering 90 degrees and has to ask for
// the width the turned lettering will have WITHOUT rescaling it. The sewn
// height cannot say: it is the fit extent plus a fixed pull-comp margin, so
// handing it back as the new width grew 150 mm lettering to 153 mm (first
// try, 2026-11-13). The fit extent swaps exactly under a quarter turn.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const DG = require("../src/digitize.js");
const fb = require("../src/fontbin.js");

const font = fb.decodeFontBin(fs.readFileSync(path.join(__dirname, "..", "src", "fonts", "bin", "medium_font.embf")));
const GARMENT = { widthIn: 12, heightIn: 12 }; // roomy: nothing clamps
const build = (extra) => DG.buildLetteringDesign(font, "ROTATE ME", { garment: GARMENT, pxPerMm: 8, ...extra });

test("fitMm is the fit extent: close to, and never past, the sewn size", () => {
  const d = build({ targetWidthMm: 150 });
  assert.ok(d.fitMm && d.fitMm.w > 0 && d.fitMm.h > 0);
  assert.ok(Math.abs(d.fitMm.w - 150) < 1e-6, "the asked width is the fit width");
  // the margin is a hair, on each axis
  assert.ok(d.widthMM >= d.fitMm.w - 0.01 && d.widthMM - d.fitMm.w < 2, `${d.widthMM} vs ${d.fitMm.w}`);
  assert.ok(d.heightMM >= d.fitMm.h - 0.01 && d.heightMM - d.fitMm.h < 2, `${d.heightMM} vs ${d.fitMm.h}`);
});

test("fitMm.w0/h0 is the fit extent unturned: the upright fit, and |cos|/|sin| of it gives w/h", () => {
  const up = build({ targetWidthMm: 150 });
  for (const rot of [0, 30, 45, 90, 200]) {
    const d = build({ targetWidthMm: 150, rotationDeg: rot });
    const r = (rot * Math.PI) / 180, c = Math.abs(Math.cos(r)), s = Math.abs(Math.sin(r));
    assert.ok(Math.abs(d.fitMm.w - (d.fitMm.w0 * c + d.fitMm.h0 * s)) < 1e-6, `rot ${rot}: w`);
    assert.ok(Math.abs(d.fitMm.h - (d.fitMm.w0 * s + d.fitMm.h0 * c)) < 1e-6, `rot ${rot}: h`);
    // the aspect is the lettering's own, whatever the angle
    assert.ok(Math.abs(d.fitMm.h0 / d.fitMm.w0 - up.fitMm.h / up.fitMm.w) < 1e-9, `rot ${rot}: aspect`);
  }
});

test("asking a turned lettering for the old fit height keeps its scale: same stitches, swapped size", () => {
  for (const rot of [0, 90, 180, 270]) {
    const a = build({ targetWidthMm: 150, rotationDeg: rot });
    const b = build({ targetWidthMm: a.fitMm.h, rotationDeg: (rot + 90) % 360 });
    assert.strictEqual(b.stitchCount, a.stitchCount, `rot ${rot}: stitches`);
    assert.ok(Math.abs(b.widthMM - a.heightMM) < 0.1, `rot ${rot}: width ${b.widthMM} vs ${a.heightMM}`);
    assert.ok(Math.abs(b.heightMM - a.widthMM) < 0.1, `rot ${rot}: height ${b.heightMM} vs ${a.widthMM}`);
    assert.ok(Math.abs(b.fitMm.w - a.fitMm.h) < 1e-6 && Math.abs(b.fitMm.h - a.fitMm.w) < 1e-6, `rot ${rot}: fit extent swaps`);
  }
});
