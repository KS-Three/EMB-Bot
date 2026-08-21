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
