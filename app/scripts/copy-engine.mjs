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
  "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "fonts.js", "digitize.js", "render.js", "pdfsheet.js",
];
mkdirSync(outDir, { recursive: true });
for (const f of ENGINE_FILES) {
  const from = join(srcDir, f);
  if (!existsSync(from)) throw new Error("missing engine file: " + f);
  copyFileSync(from, join(outDir, f));
}
console.log("copied", ENGINE_FILES.length, "engine files to", outDir);

// Font binaries + manifest -> public/fonts (served at /fonts/*)
const fontsOut = join(here, "..", "public", "fonts");
mkdirSync(join(fontsOut, "bin"), { recursive: true });
copyFileSync(join(srcDir, "fonts", "manifest.json"), join(fontsOut, "manifest.json"));
for (const f of readdirSync(join(srcDir, "fonts", "bin")))
  if (f.endsWith(".embf"))
    copyFileSync(join(srcDir, "fonts", "bin", f), join(fontsOut, "bin", f));
console.log("copied font manifest + binaries to", fontsOut);

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
