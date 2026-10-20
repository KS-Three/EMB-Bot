// Where the image lane's `fillColumns` stitches go: the price taken apart.
//
//   node tools/fill-columns-price.mjs [--src engineDir] [--colors 4]
//
// Each real logo of tools/fill-columns-lanes.mjs is built off and on, as
// app/src/lib/generate.js's image branch builds it, and every stitch is put
// down to the run it belongs to (`design.runs`: fill, underlay, satin). For
// fill and underlay it also counts the LANDINGS with the option off: a stitch
// whose record before it is a jump. Off, a split row reaches each span after
// the first by a jump, and the jump's end is no penetration -- the thread
// floats from the last span straight to the second point of the next. On,
// that span is reached by thread and its first point IS a penetration. So a
// landing turned into a stitch is not overhead: it is the float being taken
// away. What the option adds beyond the landings is the part a fix could go
// after.
import "./_help.mjs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const SRC = opt("--src") ? resolve(opt("--src")) : join(ROOT, "src");
const COLORS = opt("--colors") ? opt("--colors").split(",").map(Number) : [2, 4, 6];
globalThis.window = globalThis;
for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "svgpath", "svgimport", "dst", "dstimport", "exp", "pes", "svgexport", "stitchModel"]) require(join(SRC, f + ".js"));
const DG = require(join(SRC, "digitize.js")), FAB = require(join(SRC, "fabrics.js")), GAR = require(join(SRC, "garments.js"));
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF } = await lib("flatten.js");
const { flatToRegions } = await lib("imageRegions.js");
const { decodePNG, downscale } = await import(pathToFileURL(join(ROOT, "tools", "png.mjs")).href);

// the same fourteen logos as tools/fill-columns-lanes.mjs
const ART = [
  "art/logo_golke_roofing.png", "art/logo_hotel_fremont_patch.png", "art/logo_mfab_hat.png", "art/logo_mfab_lc.png",
  "art/logo_toat_beanie.png", "art/logo_toat_machine.png", "becker_marine_logo.png", "logo_alpha.png",
  "logo_whitebg.png", "logo_script_tires.png", "photo/enthusiast_logo.png", "photo/summit_badge.png",
  "photo/logo_drone_thermal_badge.png", "photo/logo_gaulke_roofing.png",
];
const tot = {};
const add = (k, v) => { tot[k] = (tot[k] || 0) + v; };
let designs = 0;
for (const rel of ART) {
  let img = decodePNG(join(ROOT, "digitizer", "testdata", rel));
  if (Math.max(img.width, img.height) > WORK_MAX_PX) img = downscale(img, WORK_MAX_PX);
  for (const nColors of COLORS) {
    const rgba = Uint8ClampedArray.from(img.rgba);
    for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
    const reg = flatToRegions(flattenRGBA(rgba, img.width, img.height, { nColors, removeBg: true }));
    if (!reg.regions.length) continue;
    for (const gid of ["left_chest", "hat_front", "full_back"]) {
      designs++;
      for (const on of [false, true]) {
        const arm = on ? "on" : "off";
        const regions = JSON.parse(JSON.stringify(reg.regions));
        regions.forEach((r, ri) => r.shapes.forEach((s, si) => { s.id = `r${ri}s${si}`; }));
        const d = DG.buildQualityDesign(regions, { garment: GAR.getGarment(gid), fabric: FAB.getFabric(FAB.fabricForGarment(gid)), pxPerMm: reg.pxPerMm, satinMaxWidthMm: 3.0, underlay: true, offsetXMm: 0, offsetYMm: 0, fillColumns: on });
        add(`${arm} all`, d.stitches.filter((s) => s.type === "stitch").length);
        add(`${arm} cuts`, d.stitches.filter((s) => s.type === "trim").length);
        for (const r of d.runs) {
          let prev = null;
          for (let i = r.i0; i <= r.i1; i++) {
            const t = d.stitches[i].type;
            if (t === "stitch") add(`${arm} ${r.kind}`, 1);
            if (t === "stitch" && prev === "jump") add(`${arm} ${r.kind} landings`, 1);
            prev = t;
          }
        }
      }
    }
  }
}
const pc = (n) => `${((100 * n) / tot["off all"]).toFixed(1)}%`;
const n = (x) => (x || 0).toLocaleString("en-US");
console.log(`${designs} designs: ${n(tot["off all"])} stitches off, ${n(tot["on all"])} on (+${n(tot["on all"] - tot["off all"])}, ${pc(tot["on all"] - tot["off all"])}); cuts ${n(tot["off cuts"])} -> ${n(tot["on cuts"])}\n`);
console.log("| run | off | on | added | landings off (now penetrated) | added beyond the landings | of the whole design |");
console.log("|---|---|---|---|---|---|---|");
let floor = 0;
for (const k of ["fill", "underlay", "satin"]) {
  const added = (tot[`on ${k}`] || 0) - (tot[`off ${k}`] || 0), land = Math.max(0, (tot[`off ${k} landings`] || 0) - (tot[`on ${k} landings`] || 0));
  floor += Math.min(added, land);
  console.log(`| ${k} | ${n(tot[`off ${k}`])} | ${n(tot[`on ${k}`])} | +${n(added)} | ${n(land)} | +${n(added - land)} | ${pc(added - land)} |`);
}
console.log(`\nThe landings alone, the floor any fix that keeps the floats away still pays: +${n(floor)} (${pc(floor)}).`);
