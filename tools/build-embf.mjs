// Builds the binary font library + manifest from source JSONs.
//   node tools/build-embf.mjs
// Inputs:  src/fonts/<key>.json           (the 21 shipped fonts)
//          scratch_ink/_out/<key>.json    (trial imports of new fonts)
//          scratch_ink/_tiers.json        (tier classification, Kent-approved)
//          tools/font-categories.json     (display groups)
// Outputs: src/fonts/bin/<key>.embf   (VERIFIED tier only)
//          src/fonts/manifest.json
// Idempotent; safe to re-run. scratch_ink/ is gitignored source material —
// the committed artifacts are the .embf files and the manifest.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const fb = require("../src/fontbin.js");

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const BIN_DIR = join(FONT_DIR, "bin");
const GROUPS = JSON.parse(readFileSync(join(root, "tools", "font-categories.json"), "utf8"));

// license id from the first line of the font's license text
function licenseId(text) {
  const t = String(text || "");
  if (/SIL Open Font License|OFL/i.test(t)) return "OFL-1.1";
  if (/CC-BY-SA/i.test(t)) return "CC-BY-SA-4.0";
  if (/CC-BY/i.test(t)) return "CC-BY-4.0";
  if (/public domain|CC0/i.test(t)) return "CC0";
  return "SEE-LICENSE-FILE";
}

// 1. Shipped fonts: every src/fonts/<key>.json is verified by definition
//    (they are the 21 Kent already ships).
const sources = [];
for (const f of readdirSync(FONT_DIR)) {
  if (f.endsWith(".json") && f !== "manifest.json")
    sources.push({ key: f.replace(/\.json$/, ""), path: join(FONT_DIR, f), tier: "verified" });
}

// 2. New fonts: verified tier per _tiers.json, data from the trial imports.
const tiersPath = join(root, "scratch_ink", "_tiers.json");
if (existsSync(tiersPath)) {
  const tiers = JSON.parse(readFileSync(tiersPath, "utf8"));
  const have = new Set(sources.map((s) => s.key));
  for (const t of tiers) {
    if (t.tier !== "verified" || have.has(t.pack)) continue;
    const p = join(root, "scratch_ink", "_out", t.pack + ".json");
    if (!existsSync(p)) { console.warn("SKIP (no trial import):", t.pack); continue; }
    sources.push({ key: t.pack, path: p, tier: "verified" });
  }
} else {
  console.warn("scratch_ink/_tiers.json absent — building shipped fonts only");
}

mkdirSync(BIN_DIR, { recursive: true });
const manifest = [];
for (const s of sources.sort((a, b) => a.key.localeCompare(b.key))) {
  const font = JSON.parse(readFileSync(s.path, "utf8"));
  const bytes = fb.encodeFontBin(font, 4);
  // self-check every font on every build — cheap, and catches codec drift
  const back = fb.decodeFontBin(bytes);
  const want = fb.quantizeFont(font, 4);
  if (JSON.stringify(back) !== JSON.stringify(want))
    throw new Error("round-trip mismatch: " + s.key);
  writeFileSync(join(BIN_DIR, s.key + ".embf"), bytes);
  manifest.push({
    key: s.key,
    name: font.name || s.key,
    tier: s.tier,
    group: GROUPS[s.key] || "More",
    licenseId: licenseId(font.license),
    sizeMm: font.sizeMm || 0,
    glyphCount: Object.keys(font.glyphs || {}).length,
    bytes: bytes.length,
  });
}
writeFileSync(join(FONT_DIR, "manifest.json"),
  JSON.stringify({ version: 1, fonts: manifest }, null, 1));
const total = manifest.reduce((a, f) => a + f.bytes, 0);
console.log("built", manifest.length, "fonts,", (total / 1048576).toFixed(2), "MB binary");
