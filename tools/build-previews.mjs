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

// --personal renders the PERSONAL library instead (2026-08-22). Its 37
// personal-only fonts had no preview tile at all, so the font browser showed
// them blank in the build Kent actually uses.
//
// Output goes to a SEPARATE gitignored directory. src/fonts/previews/ is
// committed, and a preview is a RENDER OF THE FONT — publishing one for a
// ShareAlike or NonCommercial face is precisely the distribution the
// sellable/personal build split exists to prevent. Writing them alongside the
// committed previews would also make the orphan-clean below delete every
// sellable preview on a personal run, and vice versa.
const PERSONAL = process.argv.includes("--personal");
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const PREV_DIR = join(FONT_DIR, PERSONAL ? "previews-personal" : "previews");
const BIN_DIR = join(FONT_DIR, PERSONAL ? "bin-personal" : "bin");
const MANIFEST = join(FONT_DIR, PERSONAL ? "manifest-personal.json" : "manifest.json");
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
  if (own) return own;
  // Non-Latin fonts (Hebrew, 2026-08-22). Every fallback above assumes Latin
  // glyph names, so a Hebrew font fell through to "?" — which it does not
  // contain either — and rendered ZERO stitches. Both Hebrew faces shipped with
  // no preview tile at all, and the guard test caught it. Take the font's own
  // first few single-character glyphs whatever the script; layoutText handles
  // RTL ordering from font.dir, so the tile reads correctly.
  const any = Object.keys(font.glyphs || {})
    .filter((k) => [...k].length === 1 && k !== " " && k !== ".notdef")
    .slice(0, 5).join("");
  return any || "?";
}

const man = JSON.parse(readFileSync(MANIFEST, "utf8"));
const wanted = new Set(man.fonts.map((f) => f.key));

// Clean orphans so a demoted font's preview can't linger (same lesson as the
// orphan-.embf guard).
for (const f of readdirSync(PREV_DIR)) {
  if (f.endsWith(".png") && !wanted.has(f.replace(/\.png$/, ""))) {
    unlinkSync(join(PREV_DIR, f));
    console.log("removed orphan", f);
  }
}

// Sidecar of thread colors so previews match the dark live-tile thread color
// (FontBrowser's live "your text" tiles render with colorOverride [45,45,50]
// -- committed previews were using render-dst's default red/blue palette
// instead, which looked wrong next to a live tile of the same font).
const colorsPath = join(PREV_DIR, "_tmp_colors.json");
writeFileSync(colorsPath, JSON.stringify([[45, 45, 50]]));

let made = 0;
for (const entry of man.fonts) {
  // A personal run only needs the fonts the committed set does not already
  // cover; copy-engine overlays the two directories.
  if (PERSONAL && existsSync(join(FONT_DIR, "previews", entry.key + ".png"))) continue;
  const font = EMB.decodeFontBin(readFileSync(join(BIN_DIR, entry.key + ".embf")));
  const text = sampleFor(font);
  const design = EMB.buildLetteringDesign(font, text, {
    garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5,
    underlay: false, targetWidthMm: 80,
  });
  if (!design.stitchCount) {
    // An empty preview is a real defect in the SELLABLE library and fails the
    // run. The personal library deliberately holds marginal fonts (paquerette
    // has 31 of 52 letters carrying no authored stitch length), so there it is
    // a warning: failing the run would train Kent to ignore the exit code.
    console.error("EMPTY preview for " + entry.key + (PERSONAL ? " (personal build — skipped)" : " — investigate"));
    if (!PERSONAL) process.exitCode = 1;
    continue;
  }
  const tmp = join(PREV_DIR, "_tmp.dst");
  writeFileSync(tmp, Buffer.from(EMB.encodeDST(design)));
  execFileSync("node", [join(root, "tools", "render-dst.mjs"), tmp, join(PREV_DIR, entry.key + ".png"), "4", colorsPath]);
  made++;
}
if (existsSync(join(PREV_DIR, "_tmp.dst"))) unlinkSync(join(PREV_DIR, "_tmp.dst"));
if (existsSync(colorsPath)) unlinkSync(colorsPath);
console.log(PERSONAL ? "personal-only previews: " + made : "previews: " + made + " of " + man.fonts.length);
