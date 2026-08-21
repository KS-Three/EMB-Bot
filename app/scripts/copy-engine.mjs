import { copyFileSync, mkdirSync, existsSync, readdirSync, unlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const srcDir = join(here, "..", "..", "src");
const outDir = join(here, "..", "public", "engine");
// Dependency order MUST match EMB-Bot.html.
export const ENGINE_FILES = [
  "units.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "satinfont.js",
  "fontbin.js",
  "svgpath.js", "svgimport.js",
  "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "digitize.js", "render.js", "pdfsheet.js",
];
mkdirSync(outDir, { recursive: true });
for (const f of ENGINE_FILES) {
  const from = join(srcDir, f);
  if (!existsSync(from)) throw new Error("missing engine file: " + f);
  copyFileSync(from, join(outDir, f));
}
console.log("copied", ENGINE_FILES.length, "engine files to", outDir);

// Font binaries + manifest -> public/fonts (served at /fonts/*)
//
// If a PERSONAL build exists (node tools/build-embf.mjs --personal), serve that
// instead — it is Kent's local library with every font, including ShareAlike /
// GPL / NonCommercial ones that must never ship. This is safe by construction
// rather than by discipline: `src/fonts/bin-personal/` is gitignored and a
// fresh clone or CI simply does not have it, so a release build cannot pick it
// up no matter what. It is served under the ordinary /fonts/* paths so the app
// needs no personal-build awareness at all.
const fontsOut = join(here, "..", "public", "fonts");
const personalManifest = join(srcDir, "fonts", "manifest-personal.json");
const personalBin = join(srcDir, "fonts", "bin-personal");
const usePersonal = existsSync(personalManifest) && existsSync(personalBin);
const binSrc = usePersonal ? personalBin : join(srcDir, "fonts", "bin");
const manifestSrc = usePersonal ? personalManifest : join(srcDir, "fonts", "manifest.json");

mkdirSync(join(fontsOut, "bin"), { recursive: true });
copyFileSync(manifestSrc, join(fontsOut, "manifest.json"));
const wantBins = new Set(readdirSync(binSrc).filter((f) => f.endsWith(".embf")));
// Orphan-clean FIRST: switching between personal and sellable builds must not
// leave the previous build's binaries being served. Without this, one personal
// build would keep serving ShareAlike fonts from every later sale build too.
for (const f of readdirSync(join(fontsOut, "bin")))
  if (f.endsWith(".embf") && !wantBins.has(f)) unlinkSync(join(fontsOut, "bin", f));
for (const f of wantBins) copyFileSync(join(binSrc, f), join(fontsOut, "bin", f));
if (usePersonal) {
  console.warn("*** serving the PERSONAL font build (" + wantBins.size + " fonts) — NOT FOR DISTRIBUTION ***");
  console.warn("    delete src/fonts/bin-personal/ + manifest-personal.json to go back to the sellable library");
} else {
  console.log("copied font manifest +", wantBins.size, "binaries to", fontsOut);
}

// License texts -> public/fonts/<key>.LICENSE.txt (served at
// /fonts/<key>.LICENSE.txt, linked from the credits dialog).
// font-license-audit-2026-07-31.md item 6: the OFL requires the full license
// text + copyright notice to accompany every copy as (among other options)
// stand-alone text files — before this, zero license files shipped in the
// built app. Stale files are deleted, same reasoning as the previews below.
const srcLic = new Set(readdirSync(join(srcDir, "fonts")).filter((f) => f.endsWith(".LICENSE.txt")));
for (const f of readdirSync(fontsOut))
  if (f.endsWith(".LICENSE.txt") && !srcLic.has(f)) unlinkSync(join(fontsOut, f));
for (const f of srcLic) copyFileSync(join(srcDir, "fonts", f), join(fontsOut, f));
console.log("copied", srcLic.size, "font license files");

// Preview PNGs -> public/fonts/previews (served at /fonts/previews/*).
// Stale files are DELETED from the dest, not just overwritten: a demoted
// font's preview lingering in a dirty local tree is the same trap as the
// orphan-.embf case the guard test closes.
const prevSrc = join(srcDir, "fonts", "previews");
const prevOut = join(fontsOut, "previews");
mkdirSync(prevOut, { recursive: true });
const srcPngs = new Set(readdirSync(prevSrc).filter((f) => f.endsWith(".png")));
for (const f of readdirSync(prevOut))
  if (f.endsWith(".png") && !srcPngs.has(f)) unlinkSync(join(prevOut, f));
for (const f of srcPngs) copyFileSync(join(prevSrc, f), join(prevOut, f));
console.log("copied", srcPngs.size, "font previews");
