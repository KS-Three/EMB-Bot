import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const srcDir = join(here, "..", "..", "src");
const outDir = join(here, "..", "public", "engine");
// Dependency order MUST match EMB-Bot.html.
export const ENGINE_FILES = [
  "units.js", "garments.js", "fabrics.js", "fill.js", "geometry.js",
  "quantize.js", "flatten.js", "satin.js", "satinplay.js", "satinfont.js",
  "dst.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js",
  "fonts.js", "digitize.js", "render.js", "pdfsheet.js",
  "fonts/satin-fonts.js",
];
mkdirSync(join(outDir, "fonts"), { recursive: true });
for (const f of ENGINE_FILES) {
  const from = join(srcDir, f);
  if (!existsSync(from)) throw new Error("missing engine file: " + f);
  copyFileSync(from, join(outDir, f));
}
console.log("copied", ENGINE_FILES.length, "engine files to", outDir);
