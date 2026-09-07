// Builds src/fonts/coverage.json — which characters each SHIPPED font can
// actually stitch — from the committed .embf binaries.
//
// Why this exists: a customer who types a Russian, Greek or Hebrew name in the
// default font is told "This font can't stitch «Р», «у», «с». Try a different
// font, or different text." — true, and a dead end. Three shipped fonts cover
// Cyrillic (`cyrillic` alone carries 271 glyphs), three cover Greek and two
// cover Hebrew, and finding them meant opening up to 85 fonts by hand. This
// repo's own convention, applied five times over in the preflight findings
// (THREAD_MATCH_POOR names a loaded better spool, COLOR_STOPS_HEAVY names the
// cheapest merge, STITCHES_TOO_SHORT names the shapes), is that a finding
// names the fix.
//
// Read from the BINARIES, not from the sources build-embf.mjs consumes. Two
// reasons, both practical:
//   - `scratch_ink/` is gitignored and supplies 68 of the 85 fonts, so a cloud
//     checkout cannot rebuild the manifest at all. It has every .embf.
//   - The binaries are what SHIPS. A coverage index derived from them cannot
//     disagree with the font the customer actually gets.
// test/font-coverage.test.js re-derives it and fails on any drift, so the
// committed file is checkable rather than trusted.
//
// Shape: { version, fonts: { <key>: [cp | [lo, hi], ...] } } — code points,
// sorted, runs collapsed into [lo, hi] pairs. 16 KB for all 85 fonts (3.4 KB
// gzipped), which is why it is exact coverage rather than a per-script
// summary: a font that has SOME Greek but not the letters typed would be a
// worse answer than none.
import { readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const fb = require(join(root, "src", "fontbin.js"));

// Mirrors build-embf.mjs's own --personal switch: a personal build writes a
// gitignored sibling so a sale build can never serve ShareAlike fonts.
const PERSONAL = process.argv.includes("--personal");
const BIN_DIR = join(root, "src", "fonts", PERSONAL ? "bin-personal" : "bin");
// NAME MATTERS. `src/fonts/` holds font SOURCES, and both this repo's build
// (tools/build-embf.mjs) and its guard (test/embf-guard.test.js) enumerate
// `*.json` there as fonts, excluding only names starting with "manifest" —
// embf-guard states the invariant outright: "static JSON here => shipped".
// A file called coverage.json lands inside that invariant and breaks four
// tests plus the font build, which is exactly what it did on the first cut.
// The "manifest" prefix is the existing, tested way to say "an artifact ABOUT
// the fonts, not one of them", and this is one: manifest.json says which fonts
// ship, this says what each of them covers.
const OUT = join(root, "src", "fonts",
  PERSONAL ? "manifest-coverage-personal.json" : "manifest-coverage.json");

// Multi-code-point keys (ligatures, combining sequences) are deliberately
// dropped: this index answers "can this font stitch this CHARACTER", and the
// layout engine looks glyphs up per character.
export function coverageRanges(font) {
  const cps = Object.keys(font.glyphs || {})
    .filter((c) => [...c].length === 1)
    .map((c) => c.codePointAt(0))
    .sort((a, b) => a - b);
  const ranges = [];
  for (const cp of cps) {
    const last = ranges[ranges.length - 1];
    if (last && cp === last[1] + 1) last[1] = cp;
    else ranges.push([cp, cp]);
  }
  return ranges.map(([a, b]) => (a === b ? a : [a, b]));
}

export function buildCoverage(binDir) {
  const fonts = {};
  for (const f of readdirSync(binDir).filter((n) => n.endsWith(".embf")).sort()) {
    fonts[f.replace(/\.embf$/, "")] = coverageRanges(fb.decodeFontBin(readFileSync(join(binDir, f))));
  }
  return { version: 1, fonts };
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  if (!existsSync(BIN_DIR)) {
    console.error(`no font binaries at ${BIN_DIR} — run tools/build-embf.mjs first`);
    process.exit(1);
  }
  const out = buildCoverage(BIN_DIR);
  writeFileSync(OUT, JSON.stringify(out));
  const n = Object.keys(out.fonts).length;
  console.log(`wrote ${OUT} — ${n} fonts, ${JSON.stringify(out).length} bytes`);
}
