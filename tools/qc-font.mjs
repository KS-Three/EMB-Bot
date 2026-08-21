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

  const present = (chars) => [...chars].filter((c) => font.glyphs[c]);
  const upper = present(LETTERS), lower = present(LOWER), digits = present(DIGITS);
  if (upper.length === 0) fail("no uppercase letter glyphs at all");
  if (lower.length === 0) warn("coverage: no lowercase glyphs (caps-only font)");
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
  const letterGlyphs = [...upper, ...lower];
  const stitchable = (c) => {
    const g = font.glyphs[c];
    if ((g.cols || []).length) return true;
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
