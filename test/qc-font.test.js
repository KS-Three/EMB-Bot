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
