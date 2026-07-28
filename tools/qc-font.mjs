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

  // Per-LETTER-GLYPH satin check: a letter with zero satin columns stitches
  // as nothing through buildLetteringDesign.
  const letterGlyphs = [...upper, ...lower];
  const satinless = letterGlyphs.filter((c) => !(font.glyphs[c].cols || []).length);
  if (letterGlyphs.length && satinless.length === letterGlyphs.length)
    fail("every letter glyph has zero satin columns (runs-only font -> 0 stitches through the lettering path)");
  else if (satinless.length > letterGlyphs.length * 0.10)
    fail(`satin: ${satinless.length}/${letterGlyphs.length} letter glyphs have no satin columns`);
  else if (satinless.length > 0)
    warn(`satin: ${satinless.length}/${letterGlyphs.length} letter glyphs have no satin columns`);

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
