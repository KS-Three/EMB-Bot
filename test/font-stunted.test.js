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
//
// ─────────────────────────────────────────────────────────────────────────────
// COVERAGE FIX, same day. The first version of this file measured height from
// `cols` only and scanned the two Latin cases only, so it silently measured
// NOTHING for 21 of the 85 shipped fonts — 19 runs-only (bean/running-stitch)
// faces plus the two Hebrew ones — and still reported green. That is the exact
// vacuous-pass shape this branch spent the day hunting, in a test written the
// same day to hunt it. `everyFontIsMeasured` below now fails loud on any font
// this check cannot see, so the blind spot cannot silently reopen.
//
// The channel is chosen PER FONT, not merged: a satin font's `runs` are
// accents (a crossbar, a serif tick) and are not even stitched — see
// stripRunParamsIfSatin in tools/build-font.mjs — so their heights are
// meaningless against a letter median, and measuring cols+runs together would
// let a full-height accent MASK a collapsed column, which is the original
// mimosa defect exactly. So: cols if the font has any, else runs.
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

// One per script whose letters share a common height, since the test is a
// ratio against that script's own median. Hebrew is listed without its
// punctuation (geresh, gershayim) because those sit at 0.34-0.37 of the letter
// median by design and are not letters. Yod is the shortest real letter at
// 0.58 — comfortably clear of RATIO, and the reason a Hebrew set can use the
// same threshold as Latin at all.
const SETS = [
  ["uppercase", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"],
  ["lowercase", "abcdefghijklmnopqrstuvwxyz"],
  ["hebrew", "אבגדהוזחטיכךלמםנןסעפףצץקרשת"],
];

// null means "this glyph has no geometry on this channel at all"; 0 means "it
// has geometry that spans no height", i.e. collapsed onto a line. Those are
// NOT the same thing and the first version of this file conflated them: it
// filtered on `v > 0`, so a glyph flattened to exactly zero height dropped out
// of the measurement and could never be flagged — the machine-hazard case
// (mimosa_large's "D" sewed 6,193 stitches into 40.0 x 0.0 mm) slipping
// through the guard written for it. Found 2026-08-22 by collapsing a glyph on
// purpose and watching this file report green.
const yOf = (pts) => {
  let mn = Infinity, mx = -Infinity, n = 0;
  for (const p of pts) {
    if (!p || !Number.isFinite(p[1])) continue;
    n++;
    if (p[1] < mn) mn = p[1];
    if (p[1] > mx) mx = p[1];
  }
  return n ? mx - mn : null;
};
const colHeight = (g) => {
  const pts = [];
  for (const c of g.cols || []) for (const r of [c.railA, c.railB]) for (const p of r || []) pts.push(p);
  return yOf(pts);
};
// Runs arrive in two shapes — a bare point array, or {pts, lenMm} when the
// digitizer authored a stitch length. See runFrom in tools/build-font.mjs.
const runHeight = (g) => {
  const pts = [];
  for (const r of g.runs || []) for (const p of (Array.isArray(r) ? r : (r && r.pts) || [])) pts.push(p);
  return yOf(pts);
};
const heightFn = (font) =>
  Object.values(font.glyphs).some((g) => (g.cols || []).length) ? colHeight : runHeight;

// Returns [] for a font with no measurable set — measuredSets() is what
// distinguishes that from "measured and clean".
// Split a set's letters into measurable heights and VOIDS — glyphs that exist
// in the font but carry nothing on its skeleton channel. A void in a satin
// font means a letter lost all its columns, which is the mimosa defect at its
// limit; measured 2026-08-22 there are none in the library, and a `continue`
// there would have hidden one silently.
function partition(font, set) {
  const height = heightFn(font);
  const vs = [], voids = [];
  for (const c of set) {
    const g = font.glyphs[c];
    if (!g) continue; // the font simply does not have this letter
    const v = height(g);
    if (v === null) voids.push(c); else vs.push([c, v]);
  }
  return { vs, voids };
}

function stuntedLetters(font) {
  const out = [];
  for (const [, set] of SETS) {
    const { vs, voids } = partition(font, set);
    if (vs.length + voids.length < 8) continue; // too few letters for a median
    out.push(...voids);
    if (!vs.length) continue;
    const sorted = vs.map((v) => v[1]).sort((a, b) => a - b);
    const med = sorted[Math.floor(sorted.length / 2)];
    if (!(med > 0)) continue; // whole set collapsed; the voids above say so
    for (const [c, v] of vs) if (v / med < RATIO) out.push(c);
  }
  return out;
}

function measuredSets(font) {
  return SETS.filter(([, set]) => {
    const { vs, voids } = partition(font, set);
    return vs.length + voids.length >= 8;
  }).map(([name]) => name);
}

// Memoised — every test here needs the whole library, and decoding 85 binaries
// once per test is pure overhead.
let _all;
const loadAll = () => (_all !== undefined ? _all : (_all =
  fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"))
    .map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))])));

test("every shipped font is actually measured by this check", () => {
  if (!binDirOrSkip()) return;
  const all = loadAll();
  assert.ok(all.length > 50, `only ${all.length} .embf files — the library did not build`);
  const blind = all.filter(([, font]) => measuredSets(font).length === 0).map(([k]) => k);
  assert.deepStrictEqual(blind, [],
    `this check can see nothing in: ${blind.join(", ")}. A font it cannot measure is a ` +
    `font it silently passes — add its script to SETS, or work out why its glyphs have ` +
    `no measurable height, but do not leave it invisible.`);
});

test("no shipped font has a letter far shorter than its script median", () => {
  if (!binDirOrSkip()) return;
  const all = loadAll();
  // Iterating an empty list asserts nothing and still reports green — the same
  // vacuous pass as the early return above, one level down. The library is
  // committed and is 85 fonts; a handful would mean something is badly wrong.
  assert.ok(all.length > 50, `only ${all.length} .embf files — the library did not build`);
  for (const [key, font] of all) {
    const found = stuntedLetters(font);
    const allowed = new Set(KNOWN_STUNTED[key] || []);
    const fresh = found.filter((c) => !allowed.has(c));
    assert.deepStrictEqual(fresh, [],
      `${key} has letter(s) that are stunted and not recorded debt: ` +
      `${fresh.map((c) => JSON.stringify(c)).join(", ")}. Either they measure under ` +
      `${RATIO}x their script median, or they carry NO geometry at all on this font's ` +
      `skeleton channel. Both still stitch something, so qc-font's stitchability check ` +
      `passes them while they render as stubs — look at the glyph before adding it to ` +
      `KNOWN_STUNTED.`);
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

// The margin is thin on purpose-built display faces, so record where it
// actually sits rather than leaving the next person to rediscover it: measured
// 2026-08-22, the closest legitimate case in the whole library is
// digory_doodles_bean's lowercase "r" at 0.454 — four thousandths clear. Its
// cols span 25.8 against an "o" of 31.8, and the lowercase median is inflated
// by ascenders ("l" 67.5), which is the real weakness of a per-case median.
// If that one starts failing after a rebuild, look at the glyph before
// assuming a regression, and do NOT move RATIO to make it pass.
test("the tight-margin case is still the one on record", () => {
  if (!binDirOrSkip()) return;
  const p = path.join(BIN, "digory_doodles_bean.embf");
  if (!fs.existsSync(p)) return; // font pulled; the note above is then history
  const font = fb.decodeFontBin(fs.readFileSync(p));
  const height = heightFn(font);
  const vs = [..."abcdefghijklmnopqrstuvwxyz"]
    .map((c) => font.glyphs[c] && height(font.glyphs[c]))
    .filter((v) => v > 0).sort((a, b) => a - b);
  const med = vs[Math.floor(vs.length / 2)];
  const r = height(font.glyphs["r"]) / med;
  assert.ok(r > RATIO && r < 0.5,
    `"r" now measures ${r.toFixed(3)}x the lowercase median, not the ~0.454 on record. ` +
    `Above 0.5 the note here is stale and should be rewritten; at or below ${RATIO} ` +
    `the previous test is already failing and this is telling you why.`);
});
