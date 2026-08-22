// Stunted-glyph guard (2026-08-22).
//
// qc-font's stitchability test asks "does this letter produce stitches?", which
// a glyph can pass while rendering as a stub. Terminus exposed the gap: QC
// reported 1/52 letters broken, but rendering the alphabet showed FOUR — q
// stitched nothing (the one QC caught) while B, M and t emitted a fraction of
// their geometry and passed. Upstream had left paths in those glyphs untagged,
// so only part of each letter became a satin column.
//
// Applying the same check to the SHIPPED library found the defect already in
// it, in four fonts: mimosa_large (D, E), mimosa_medium (D, E), apesplit (A)
// and initials_medium (A). mimosa_large's "D" sewed 6,193 stitches into
// 40.0 x 0.0 mm — a needle hammering one line.
//
// ALL FOUR ARE FIXED, by one root cause (2026-08-22, Kent's call to fix rather
// than pull): build-font applied SVG transforms only for the ltr/-directory
// layout, so every single-ltr.svg font silently dropped them. A glyph that
// places repeated geometry BY transform — mimosa_large's "D" is one dot with 38
// different transforms — collapsed onto a single point. See tools/build-font.mjs.
//
// KNOWN_STUNTED is therefore EMPTY, and that is the point: the list is a debt
// register, not a suppression list. The test still fails in both directions, so
// a regression that reintroduces a stunted glyph fails here, and an entry added
// to the register that is not actually stunted fails too.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const RATIO = 0.45; // mirrors tools/qc-font.mjs
// src/fonts/bin/ is COMMITTED, so this guard should never fire in a real
// checkout. It is written to fail loud on CI anyway, because a test that
// returns early asserts NOTHING and still reports green — the exact shape that
// has bitten this suite repeatedly (see test/crossval-stitch-formats.test.js,
// which throws on CI for the same reason). A missing font library on CI means
// the build did not run, not that there is nothing to check.
function binDirOrSkip() {
  if (fs.existsSync(BIN)) return true;
  if (process.env.CI) throw new Error(
    "src/fonts/bin is missing on CI — the font library did not build, so this " +
    "check would have passed without asserting anything");
  return false;
}


// Empty by design — the 2026-08-22 debt was fixed at its root, not suppressed.
// Add an entry ONLY with a rendered image showing why the glyph is acceptable
// as-is; a ratio alone is how three of the original four got mistaken for
// cosmetic when one was a machine hazard.
const KNOWN_STUNTED = {};

function stuntedLetters(font) {
  const height = (g) => {
    let mn = Infinity, mx = -Infinity;
    for (const c of g.cols || [])
      for (const r of [c.railA, c.railB])
        for (const p of r || []) { if (p[1] < mn) mn = p[1]; if (p[1] > mx) mx = p[1]; }
    return mx > -Infinity ? mx - mn : null;
  };
  const out = [];
  for (const set of ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"]) {
    const vs = [];
    for (const c of set) {
      const g = font.glyphs[c];
      if (!g) continue;
      const v = height(g);
      if (v > 0) vs.push([c, v]);
    }
    if (vs.length < 8) continue;
    const sorted = vs.map((v) => v[1]).sort((a, b) => a - b);
    const med = sorted[Math.floor(sorted.length / 2)];
    for (const [c, v] of vs) if (v / med < RATIO) out.push(c);
  }
  return out;
}

test("no shipped font has a letter far shorter than its case median", () => {
  if (!binDirOrSkip()) return;
  const bins = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"));
  // Iterating an empty list asserts nothing and still reports green — the same
  // vacuous pass as the early return above, one level down. The library is
  // committed and is 85 fonts; a handful would mean something is badly wrong.
  assert.ok(bins.length > 50, `only ${bins.length} .embf files — the library did not build`);
  for (const f of bins) {
    const key = f.replace(/\.embf$/, "");
    const font = fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)));
    const found = stuntedLetters(font);
    const allowed = new Set(KNOWN_STUNTED[key] || []);
    const fresh = found.filter((c) => !allowed.has(c));
    assert.deepStrictEqual(fresh, [],
      `${key} has letter(s) under ${RATIO}x their case median that are not recorded ` +
      `debt: ${fresh.map((c) => JSON.stringify(c)).join(", ")}. These stitch, so ` +
      `qc-font's stitchability check passes them, but they render as stubs — look at ` +
      `the glyph before adding it to KNOWN_STUNTED.`);
  }
});

test("the recorded debt is real — a fixed or pulled font must be removed from the list", () => {
  if (!binDirOrSkip()) return;
  for (const [key, letters] of Object.entries(KNOWN_STUNTED)) {
    const p = path.join(BIN, key + ".embf");
    if (!fs.existsSync(p)) continue; // pulled from the library; nothing to check
    const found = new Set(stuntedLetters(fb.decodeFontBin(fs.readFileSync(p))));
    const stale = letters.filter((c) => !found.has(c));
    assert.deepStrictEqual(stale, [],
      `${key}: ${stale.map((c) => JSON.stringify(c)).join(", ")} no longer stunted — ` +
      `drop them from KNOWN_STUNTED so the list keeps meaning something.`);
  }
});
