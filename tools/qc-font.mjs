// Versioned font QC — the tier gate, in the repo, with tests.
// Encodes every failure mode this project has hit:
//   - medium_font: null advances collapsed glyphs
//   - ondulamarif_XL: letter glyphs runs-only (zero satin columns) -> 0
//     stitches; the old classifier counted satin per FILE, this counts per
//     LETTER GLYPH, which is what buildLetteringDesign actually stitches
//   - dropped fonts: broken metrics / degenerate geometry
// Usage: node tools/qc-font.mjs <font.json> [...more]
import { readFileSync } from "node:fs";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const LOWER = "abcdefghijklmnopqrstuvwxyz";
const DIGITS = "0123456789";

function finiteRing(r) {
  return Array.isArray(r) && r.every((p) => Array.isArray(p) && p.length >= 2 &&
    Number.isFinite(p[0]) && Number.isFinite(p[1]));
}

export function qcFont(font) {
  const findings = [];
  let hardFail = false;
  const fail = (msg) => { findings.push(msg); hardFail = true; };
  const warn = (msg) => { findings.push(msg); };

  if (!font || typeof font !== "object" || !font.glyphs) return { pass: false, findings: ["not a font object"] };
  if (!(font.sizeMm > 0)) fail("missing/invalid sizeMm");
  if (!(font.unitsPerEm > 0)) fail("missing/invalid unitsPerEm");

  // Coverage, script-aware (2026-08-22). Every check below used to be scoped to
  // the Latin alphabet, which meant a font with no Latin at all HARD-FAILED with
  // "no uppercase letter glyphs" — hebrew_font_large did, and shipped anyway
  // only because build-embf never runs qcFont on scratch_ink/_out sources. So
  // the tier gate both rejected a perfectly good font and was not actually
  // gating the fonts that reach the library that way.
  //
  // A font's alphabet is whatever single-character letter glyphs it HAS. Latin
  // is still preferred when present, so nothing changes for the 83 Latin fonts;
  // the fallback only engages when there is no Latin to look at.
  const present = (chars) => [...chars].filter((c) => font.glyphs[c]);
  const upper = present(LETTERS), lower = present(LOWER), digits = present(DIGITS);
  // \p{L} — actual LETTERS, not merely "not ASCII and not a digit". Hebrew
  // ships ׳ (geresh) and ״ (gershayim), which are punctuation and legitimately
  // short; counting them as letters made them "stunted" against a median they
  // were never part of, exactly as an apostrophe would be in a Latin font.
  const nonLatin = (upper.length || lower.length) ? [] :
    Object.keys(font.glyphs).filter((k) => [...k].length === 1 &&
      /^\p{L}$/u.test(k) && !/^[\x00-\x7f]$/.test(k));
  if (!upper.length && !nonLatin.length) fail("no letter glyphs at all");
  else if (!upper.length && nonLatin.length)
    warn(`coverage: no Latin alphabet (${nonLatin.length} non-Latin letter glyphs)`);
  if (upper.length && lower.length === 0) warn("coverage: no lowercase glyphs (caps-only font)");
  if (digits.length === 0) warn("coverage: no digit glyphs");

  // Per-LETTER-GLYPH stitchability. The real question is not "does this letter
  // have satin columns" but "does it produce ANY stitches" — those were the same
  // question while the lettering path was satin-only, and stopped being the same
  // when bean/running-stitch fonts became stitchable (2026-08-21).
  //
  // A run stitches only if the FONT authored a stitch length for it: build-font
  // attaches {pts, lenMm} and ROADMAP gate 1 bars us from inventing a length, so
  // a run without one is skipped by satinfont.routeRuns and contributes nothing.
  // paquerette is exactly this trap — 1641 runs, but only 72 carry a length, so
  // 31 of its 52 letters stitch as NOTHING while a naive "has runs" check calls
  // it healthy. Count only what will actually sew.
  const letterGlyphs = (upper.length || lower.length) ? [...upper, ...lower] : nonLatin;
  const stitchable = (c) => {
    const g = font.glyphs[c];
    if ((g.cols || []).length) return true;
    // A cross-stitch region stitches when the font has a measured grid to fill
    // it on; without one crossfill emits nothing, so the grid is part of the
    // test rather than assumed.
    if (font.crossGrid && (g.runs || []).some((r) => r && r.fill === "cross" && r.pts)) return true;
    return (g.runs || []).some((r) => r && r.pts && r.lenMm > 0);
  };
  const empty = letterGlyphs.filter((c) => !stitchable(c));
  const runsOnly = letterGlyphs.length && letterGlyphs.every((c) => !(font.glyphs[c].cols || []).length);
  const kind = runsOnly ? "run" : "satin";
  if (letterGlyphs.length && empty.length === letterGlyphs.length)
    fail("every letter glyph is unstitchable (no satin columns, and no run carries an authored stitch length -> 0 stitches through the lettering path)");
  else if (empty.length > letterGlyphs.length * 0.10)
    fail(`${kind}: ${empty.length}/${letterGlyphs.length} letter glyphs stitch as nothing`);
  else if (empty.length > 0)
    warn(`${kind}: ${empty.length}/${letterGlyphs.length} letter glyphs stitch as nothing`);

  // Advances: zero/null/negative on any present letter glyph or digit is a hard fail.
  const badAdv = [...letterGlyphs, ...digits].filter((c) => !(font.glyphs[c].adv > 0));
  if (badAdv.length) fail(`advance: ${badAdv.length} glyphs with missing/zero advance (e.g. "${badAdv[0]}")`);

  // Geometry: every rail/rung/run point must be finite.
  outer:
  for (const [ch, g] of Object.entries(font.glyphs)) {
    for (const col of g.cols || []) {
      for (const ring of [col.railA, col.railB, ...(col.rungs || [])]) {
        if (ring && !finiteRing(ring)) { fail(`geometry: non-finite point in glyph "${ch}"`); break outer; }
      }
    }
    for (const run of g.runs || []) {
      const pts = run.pts || run;
      if (pts && !finiteRing(pts)) { fail(`geometry: non-finite point in glyph "${ch}" run`); break outer; }
    }
  }

  // Detached-accent / runaway-bbox check (cyrillic, 2026-08-21). The lettering
  // path derives its line box from the font's glyph extents, so ONE glyph with
  // geometry far outside the em box shrinks every string that font can render
  // — cyrillic's "u" is 71 units tall but its "u-acute" is 725, the accent
  // marooned ~650 units from the letter body, which clamped "Emb" to 19.8 mm
  // against a 40 mm target while the Cyrillic glyphs it exists for were fine.
  // Zero stitches are never produced, so every other check here passes it.
  // Scoped to single-character glyph names: multi-char names are deliberate
  // non-letters (art_nouveau's "frame1", montecarlo's "C.alt6", ".notdef")
  // that legitimately dwarf the letters and must not trip this.
  // Threshold 4x calibrated against the shipping library, whose worst
  // single-char ratio is small_font's "&" at 3.11x.
  const glyphHeight = (g) => {
    let mn = Infinity, mx = -Infinity;
    for (const col of g.cols || [])
      for (const ring of [col.railA, col.railB])
        for (const p of ring || []) { if (p[1] < mn) mn = p[1]; if (p[1] > mx) mx = p[1]; }
    return mx > -Infinity ? mx - mn : null;
  };
  const letterHeights = letterGlyphs
    .map((c) => glyphHeight(font.glyphs[c])).filter((v) => v > 0).sort((a, b) => a - b);
  if (letterHeights.length) {
    const median = letterHeights[Math.floor(letterHeights.length / 2)];
    const outliers = [];
    for (const [ch, g] of Object.entries(font.glyphs)) {
      if ([...ch].length !== 1) continue;
      const h = glyphHeight(g);
      if (h && h / median > 4) outliers.push(`"${ch}" ${(h / median).toFixed(1)}x`);
    }
    if (outliers.length)
      warn(`bbox: ${outliers.length} glyph(s) far taller than the median letter ` +
        `(${outliers.slice(0, 6).join(", ")}${outliers.length > 6 ? ", …" : ""}) ` +
        `— inflates the line box and caps how large short text can scale`);
  }

  // Stunted-glyph check (2026-08-22). The stitchability test above asks "does
  // this letter produce stitches", which a glyph can pass while rendering as a
  // stub. Terminus is what exposed it: QC called it 1/52 broken, but LOOKING at
  // the rendered alphabet found FOUR broken letters — q stitched nothing (the
  // one QC caught) while B, M and t emitted a fraction of their geometry and
  // sailed through. In its source those glyphs carry paths that were never
  // tagged inkstitch:satin_column, so only part of each letter became a column.
  //
  // Compared WITHIN case: lowercase is legitimately shorter than uppercase, so
  // one library-wide median would flag every x-height letter in every font.
  // Threshold 0.45 of the case median, and scoped to single-char A-Z/a-z names
  // — the letters that must render — so decorative alternates and multi-char
  // ornament glyphs stay out of it.
  //
  // This is a WARN, not a hard fail: it found four fonts ALREADY SHIPPING with
  // the defect (mimosa_large D 0.11x, mimosa_medium D 0.22x, apesplit A 0.23x,
  // initials_medium A 0.28x — the first two verified by rendering, D as a bare
  // dash, A as a tiny mark floating off the baseline). Failing the build on
  // those is Kent's call, not this tool's; test/font-stunted.test.js pins the
  // known set so a NEW font with the defect is caught while these stay visible
  // as debt.
  for (const set of ((upper.length || lower.length) ? [LETTERS, LOWER] : [nonLatin.join("")])) {
    const vs = [];
    for (const c of set) {
      const g = font.glyphs[c];
      if (!g) continue;
      const v = glyphHeight(g);
      if (v > 0) vs.push([c, v]);
    }
    if (vs.length < 8) continue; // too few to have a trustworthy median
    const sorted = vs.map((v) => v[1]).sort((a, b) => a - b);
    const med = sorted[Math.floor(sorted.length / 2)];
    const stunted = vs.filter(([, v]) => v / med < 0.45)
      .map(([c, v]) => `"${c}" ${(v / med).toFixed(2)}x`);
    if (stunted.length)
      warn(`stunted: ${stunted.length} letter(s) far shorter than the case median ` +
        `(${stunted.join(", ")}) — these stitch, so the stitchability check passes ` +
        `them, but they render as stubs`);
  }

  return { pass: !hardFail, findings };
}

// CLI
if (process.argv[1] && process.argv[1].replace(/\\/g, "/").endsWith("tools/qc-font.mjs")) {
  const files = process.argv.slice(2);
  if (!files.length) { console.error("usage: node tools/qc-font.mjs <font.json> [...]"); process.exit(1); }
  let anyFail = false;
  for (const f of files) {
    const key = f.replace(/\\/g, "/").split("/").pop().replace(/\.json$/, "");
    if (key === "manifest") { console.log("manifest: SKIP (not a font)"); continue; }
    let result;
    try {
      const font = JSON.parse(readFileSync(f, "utf8"));
      result = qcFont(font);
    } catch (e) {
      result = { pass: false, findings: ["invalid JSON: " + e.message] };
    }
    if (!result.pass) anyFail = true;
    console.log(`${key}: ${result.pass ? "PASS" : "FAIL"}${result.findings.length ? " — " + result.findings.join("; ") : ""}`);
  }
  process.exit(anyFail ? 1 : 0);
}
