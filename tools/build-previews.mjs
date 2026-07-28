// Renders one preview PNG per manifest font: the font's display name set in
// the font itself (or a glyph-aware fallback sample), dark thread on white.
// These are the ONLY images the Stage B font browser grid loads — no font
// binary is fetched for browsing, which is the fix for the Stage A
// open-dropdown-fetches-30MB problem.
// Usage: node tools/build-previews.mjs
import { readFileSync, writeFileSync, mkdirSync, readdirSync, unlinkSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","fonts","digitize"])
  require("../src/" + f + ".js");
const EMB = globalThis.EMB;

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const PREV_DIR = join(FONT_DIR, "previews");
mkdirSync(PREV_DIR, { recursive: true });

// Sample: the font's own name where its glyphs allow, else uppercase, else
// the first few of the glyphs it actually has (pictogram packs show symbols
// — that IS their honest preview).
function sampleFor(font) {
  const has = (ch) => ch === " " || !!(font.glyphs && font.glyphs[ch]);
  const name = String(font.name || "Sample");
  if ([...name].every(has)) return name;
  const caseFixed = name.replace(/[a-z]/g, (c) => c.toUpperCase());
  if ([...caseFixed].every(has)) return caseFixed;
  const own = Object.keys(font.glyphs || {}).filter((k) => /^[A-Za-z0-9]$/.test(k)).slice(0, 6).join("");
  return own || "?";
}

const man = JSON.parse(readFileSync(join(FONT_DIR, "manifest.json"), "utf8"));
const wanted = new Set(man.fonts.map((f) => f.key));

// Clean orphans so a demoted font's preview can't linger (same lesson as the
// orphan-.embf guard).
for (const f of readdirSync(PREV_DIR)) {
  if (f.endsWith(".png") && !wanted.has(f.replace(/\.png$/, ""))) {
    unlinkSync(join(PREV_DIR, f));
    console.log("removed orphan", f);
  }
}

let made = 0;
for (const entry of man.fonts) {
  const font = EMB.decodeFontBin(readFileSync(join(FONT_DIR, "bin", entry.key + ".embf")));
  const text = sampleFor(font);
  const design = EMB.buildLetteringDesign(font, text, {
    garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5,
    underlay: false, targetWidthMm: 80,
  });
  if (!design.stitchCount) { console.error("EMPTY preview for " + entry.key + " — investigate"); process.exitCode = 1; continue; }
  const tmp = join(PREV_DIR, "_tmp.dst");
  writeFileSync(tmp, Buffer.from(EMB.encodeDST(design)));
  execFileSync("node", [join(root, "tools", "render-dst.mjs"), tmp, join(PREV_DIR, entry.key + ".png"), "4"]);
  made++;
}
if (existsSync(join(PREV_DIR, "_tmp.dst"))) unlinkSync(join(PREV_DIR, "_tmp.dst"));
console.log("previews:", made, "of", man.fonts.length);
