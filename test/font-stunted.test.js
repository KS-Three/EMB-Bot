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
// it, in four fonts. Two were confirmed by rendering rather than by the metric:
// mimosa_large's "D" sews as a bare dash, and apesplit's / initials_medium's
// "A" as a tiny mark floating off the baseline.
//
// Those four are recorded here rather than quietly fixed or pulled — which
// fonts ship is Kent's call. The test's job is to stop the set GROWING: a new
// import with a stunted letter fails, while the existing debt stays listed and
// visible. Removing a name from KNOWN_STUNTED (by fixing or pulling the font)
// must also pass, so the list cannot rot into a rubber stamp.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const RATIO = 0.45; // mirrors tools/qc-font.mjs

// Pre-existing debt, measured 2026-08-22. Values are the ratios found then.
const KNOWN_STUNTED = {
  mimosa_large: ["D", "E"],
  mimosa_medium: ["D", "E"],
  apesplit: ["A"],
  initials_medium: ["A"],
};

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

test("no font gains a stunted letter beyond the recorded 2026-08-22 debt", () => {
  if (!fs.existsSync(BIN)) return;
  for (const f of fs.readdirSync(BIN)) {
    if (!f.endsWith(".embf")) continue;
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
  if (!fs.existsSync(BIN)) return;
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
