const assert = require("node:assert");
const { test } = require("node:test");

function goodFont() {
  const col = { railA: [[0, 0], [0, 10]], railB: [[2, 0], [2, 10]], rungs: [] };
  const glyphs = {};
  for (const ch of "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    glyphs[ch] = { adv: 10, cols: [col], runs: [] };
  return { name: "Good", license: "OFL", unitsPerEm: 100, sizeMm: 20, advDefault: 10, glyphs };
}

test("qcFont passes a well-formed font", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const r = qcFont(goodFont());
  assert.strictEqual(r.pass, true);
  assert.deepStrictEqual(r.findings, []);
});

test("flags letter glyphs with zero satin columns (the ondulamarif_XL case)", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  for (const ch of "ABCDEFGHIJ") f.glyphs[ch] = { adv: 10, cols: [], runs: [[[0,0],[1,1]]] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /satin/i.test(s)), r.findings.join("; "));
});

test("flags missing or degenerate advances", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["A"].adv = 0;
  f.glyphs["B"].adv = null;
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /advance/i.test(s)));
});

test("flags NaN coordinates", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["A"].cols[0] = { railA: [[NaN, 0], [0, 10]], railB: [[2, 0], [2, 10]], rungs: [] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /NaN|finite/i.test(s)));
});

test("flags missing basic Latin coverage as a warning-level finding but still passes", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  for (const ch of "abcdefghijklmnopqrstuvwxyz") delete f.glyphs[ch];
  const r = qcFont(f);
  assert.strictEqual(r.pass, true); // caps-only fonts are legitimate
  assert.ok(r.findings.some((s) => /coverage/i.test(s)));
});

test("flags missing sizeMm/unitsPerEm", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  delete f.sizeMm;
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /sizeMm/i.test(s)));
});

test("a small fraction of satinless letters warns but passes", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["z"] = { adv: 10, cols: [], runs: [[[0,0],[1,1]]] }; // 1/52 ≈ 2%
  const r = qcFont(f);
  assert.strictEqual(r.pass, true);
  assert.ok(r.findings.some((s) => /satin/i.test(s)));
});

test("zero advance on a digit is caught", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["7"].adv = 0;
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /advance/i.test(s)));
});

// --- detached-accent / runaway-bbox (the cyrillic case, 2026-08-21) ----------
// cyrillic's "ú" measured 725 units tall against a 71-unit "u" — the accent
// sat ~650 units from the letter body. Stitches still generated, every other
// check passed, but the inflated line box clamped "Emb" to 19.8 mm against a
// 40 mm target. Warning-level: the font is renderable, just size-limited.
test("flags a glyph whose bbox dwarfs the median letter (the cyrillic case)", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  // letters are 10 units tall; a detached accent puts this one at 80
  f.glyphs["ú"] = {
    adv: 10,
    cols: [{ railA: [[0, 0], [0, 80]], railB: [[2, 0], [2, 80]], rungs: [] }],
    runs: [],
  };
  const r = qcFont(f);
  assert.strictEqual(r.pass, true, "renderable — must not hard-fail");
  assert.ok(r.findings.some((s) => /bbox/i.test(s)), r.findings.join("; "));
});

test("bbox check ignores multi-character glyph names (art_nouveau's frame1)", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  // a deliberate decorative non-letter, 80 units tall — must NOT trip the check
  f.glyphs["frame1"] = {
    adv: 10,
    cols: [{ railA: [[0, 0], [0, 80]], railB: [[2, 0], [2, 80]], rungs: [] }],
    runs: [],
  };
  const r = qcFont(f);
  assert.strictEqual(r.pass, true);
  assert.ok(!r.findings.some((s) => /bbox/i.test(s)), r.findings.join("; "));
});

// --- script awareness (2026-08-22) -------------------------------------------
// Every coverage check here was scoped to the Latin alphabet, so a font with no
// Latin HARD-FAILED with "no uppercase letter glyphs at all". hebrew_font_large
// did exactly that — and shipped anyway, because build-embf never ran qcFont on
// scratch_ink/_out sources. The tier gate was simultaneously rejecting a good
// font and not gating the 68 fonts that reach the library that way. Both are
// fixed; these pin the behaviour so neither can quietly come back.
function nonLatinFont(chars) {
  const col = { railA: [[0, 0], [0, 10]], railB: [[2, 0], [2, 10]], rungs: [] };
  const glyphs = {};
  for (const ch of chars) glyphs[ch] = { adv: 10, cols: [col], runs: [] };
  return { name: "NonLatin", license: "OFL", unitsPerEm: 100, sizeMm: 20, advDefault: 10, glyphs };
}

test("a font with no Latin alphabet passes on its own script", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const r = qcFont(nonLatinFont("אבגדהוזחטיכלמנסעפצקרשת"));
  assert.strictEqual(r.pass, true, r.findings.join("; "));
  assert.ok(r.findings.some((s) => /no Latin alphabet/.test(s)),
    "it should still SAY it has no Latin — that is coverage information, not a failure");
});

test("a font with no letter glyphs of ANY script still hard-fails", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  // Punctuation and symbols only — nothing anyone can set text with.
  const r = qcFont(nonLatinFont(".,!?()"));
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /no letter glyphs at all/.test(s)), r.findings.join("; "));
});

test("punctuation does not count as a letter in a non-Latin font", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  // Hebrew ships ׳ (geresh) and ״ (gershayim). They are punctuation and are
  // legitimately much shorter than the letters; counting them as letters made
  // them "stunted" against a median they were never part of — the same way an
  // apostrophe would be in a Latin font.
  const f = nonLatinFont("אבגדהוזחטיכלמנסעפצקרשת");
  const short = { railA: [[0, 0], [0, 2]], railB: [[1, 0], [1, 2]], rungs: [] };
  f.glyphs["׳"] = { adv: 4, cols: [short], runs: [] };
  f.glyphs["״"] = { adv: 4, cols: [short], runs: [] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, true, r.findings.join("; "));
  assert.ok(!r.findings.some((s) => s.startsWith("stunted")),
    "punctuation must not be measured against the letter median: " + r.findings.join("; "));
});

test("a Latin font is judged exactly as before — the fallback must not engage", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  // Adding a non-Latin glyph must not change how the Latin font is assessed.
  f.glyphs["א"] = { adv: 10, cols: [{ railA: [[0, 0], [0, 1]], railB: [[1, 0], [1, 1]], rungs: [] }], runs: [] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, true);
  assert.ok(!r.findings.some((s) => /no Latin alphabet/.test(s)));
});

// --- runs-only fonts were invisible to the height-based checks (2026-08-22) ---
//
// glyphHeight measured `cols` only, so on the 19 runs-only (bean/running-
// stitch) faces every height came back null and BOTH height checks — the
// runaway-bbox one and the stunted one — silently measured nothing while
// qc-font reported the font clean. Verified against the pre-fix tool: a glyph
// flattened onto a line and a run marooned 900 units off the letter both came
// back with no finding at all.
//
// The channels are chosen per font, never merged: a satin font's runs are
// accents and are not even stitched, so merging would let a full-height accent
// mask a collapsed column — which is the mimosa_large defect exactly.
function runsOnlyFont() {
  const glyphs = {};
  // A plain vertical stroke per letter, with the authored length that makes a
  // run actually stitch (see runFrom in tools/build-font.mjs).
  for (const ch of "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    glyphs[ch] = { adv: 10, cols: [], runs: [{ pts: [[0, 0], [0, 10]], lenMm: 2 }] };
  return { name: "Runs Only", license: "OFL", unitsPerEm: 100, sizeMm: 20, advDefault: 10, glyphs };
}

test("a healthy runs-only font is clean", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const r = qcFont(runsOnlyFont());
  assert.strictEqual(r.pass, true);
  assert.deepStrictEqual(r.findings, [], "a well-formed runs-only font must not warn");
});

test("a collapsed glyph in a RUNS-ONLY font is caught, not skipped", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = runsOnlyFont();
  f.glyphs["E"].runs = [{ pts: [[0, 5], [3, 5]], lenMm: 2 }]; // zero height
  const r = qcFont(f);
  assert.ok(r.findings.some((s) => /stunted/.test(s) && /"E"/.test(s)),
    `expected a stunted finding naming "E"; got: ${r.findings.join("; ") || "(nothing)"}`);
});

test("a letter with NO geometry at all is a finding, not a silent skip", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["E"] = { adv: 10, cols: [], runs: [{ pts: [[0, 0], [0, 10]], lenMm: 2 }] };
  const r = qcFont(f);
  // It still stitches (the run carries a length), so the stitchability check
  // passes it — which is the whole reason the height check has to say something.
  assert.ok(r.findings.some((s) => /stunted/.test(s) && /"E"/.test(s) && /no geometry/.test(s)),
    `expected a "no geometry" stunted finding for "E"; got: ${r.findings.join("; ") || "(nothing)"}`);
});

test("a marooned run in a RUNS-ONLY font trips the bbox check", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = runsOnlyFont();
  f.glyphs["F"].runs = [{ pts: [[0, 0], [0, 10], [0, -900]], lenMm: 2 }];
  const r = qcFont(f);
  assert.ok(r.findings.some((s) => /bbox/.test(s) && /"F"/.test(s)),
    `expected a bbox finding naming "F"; got: ${r.findings.join("; ") || "(nothing)"}`);
});

test("a satin font's runs are NOT measured as its skeleton", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  // Every letter keeps its full-height column; add a short accent run to each.
  // Measuring runs here would call the whole alphabet stunted.
  for (const ch of "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    f.glyphs[ch] = { adv: 10, cols: f.glyphs[ch].cols, runs: [[[0, 9], [1, 9.2]]] };
  const r = qcFont(f);
  assert.ok(!r.findings.some((s) => /stunted/.test(s)),
    `accents must not be mistaken for the letter skeleton; got: ${r.findings.join("; ")}`);
});
