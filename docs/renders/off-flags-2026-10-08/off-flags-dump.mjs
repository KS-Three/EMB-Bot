// Dumps the image lane's designs for the off-flags contact sheet: one JSON per
// fixture (stitch records + colours), built the way tools/fill-columns-lanes.mjs
// builds them (image lane, left_chest, 4 colours), with fillColumns ON.
//   node tools/off-flags-dump.mjs --src <engine dir> [--checked] --out dir [--only name,...]
// --checked sets globalThis.__CHECKED (the candidate patch's switch).
import { writeFileSync, mkdirSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opt = (n) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : undefined; };
globalThis.window = globalThis;
const SRC = resolve(opt("--src") || join(ROOT, "src"));
if (args.includes("--checked")) globalThis.__CHECKED = true;
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(join(SRC, f + ".js"));
const DG = require(join(SRC, "digitize.js")), FAB = require(join(SRC, "fabrics.js")), GAR = require(join(SRC, "garments.js"));
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
const { decodePNG, downscale } = await import(pathToFileURL(join(ROOT, "tools", "png.mjs")).href);
const OUT = resolve(opt("--out")); mkdirSync(OUT, { recursive: true });
const ART = opt("--only") ? opt("--only").split(",") : [
  "art/logo_golke_roofing.png", "art/logo_hotel_fremont_patch.png", "art/logo_mfab_hat.png", "art/logo_mfab_lc.png",
  "art/logo_toat_beanie.png", "art/logo_toat_machine.png", "becker_marine_logo.png", "logo_alpha.png",
  "logo_whitebg.png", "logo_script_tires.png", "photo/enthusiast_logo.png", "photo/summit_badge.png",
  "photo/logo_drone_thermal_badge.png", "photo/logo_gaulke_roofing.png"];
const gid = opt("--garment") || "left_chest", nColors = 4;
for (const rel of ART) {
  let img = decodePNG(join(ROOT, "digitizer", "testdata", rel));
  if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
  const rgba = Uint8ClampedArray.from(img.rgba);
  for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
  const reg = flatToRegions(flattenRGBA(rgba, img.width, img.height, { nColors, removeBg: true }));
  if (!reg.regions.length) continue;
  const regions = JSON.parse(JSON.stringify(reg.regions));
  regions.forEach((r, ri) => r.shapes.forEach((s, si) => { s.id = `r${ri}s${si}`; }));
  const d = DG.buildQualityDesign(regions, { garment: GAR.getGarment(gid), fabric: FAB.getFabric(FAB.fabricForGarment(gid)), pxPerMm: reg.pxPerMm, satinMaxWidthMm: 3.0, underlay: true, offsetXMm: 0, offsetYMm: 0, fillColumns: true });
  const n = (t) => d.stitches.filter((s) => s.type === t).length;
  console.log(rel, "stitches", n("stitch"), "trims", n("trim"), "colour", n("color"));
  writeFileSync(join(OUT, rel.replace(/\//g, "_").replace(/\.\w+$/, "") + ".json"), JSON.stringify({ stitches: d.stitches, colors: d.colors }));
}

