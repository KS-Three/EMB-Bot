// Full text pipeline in Node: font TTF -> textToRegions -> buildQualityDesign -> DST.
import { createRequire } from "module";
import fs from "node:fs";
const require = createRequire(import.meta.url);
global.window = global; // some UMD builds look for window
const opentype = require("../scratch_opentype.js");
globalThis.opentype = opentype;
const F = require("../src/fonts.js");
const G = require("../src/geometry.js");
const DG = require("../src/digitize.js");
const D = require("../src/dst.js");

const TEXT = process.env.TEXT || "PRECISION";
const FAMILY = process.env.FAMILY || "Archivo Black";
const GW = +(process.env.GW || 5), GH = +(process.env.GH || 2.25);

const fontEntry = F.FONTS.find((f) => f.family === FAMILY);
if (!fontEntry) { console.error("no font " + FAMILY); process.exit(1); }
const cache = "scratch_font_" + FAMILY.replace(/\W+/g, "_") + ".ttf";
if (!fs.existsSync(cache)) {
  const res = await fetch(fontEntry.url);
  fs.writeFileSync(cache, Buffer.from(await res.arrayBuffer()));
}
const font = opentype.parse(fs.readFileSync(cache).buffer.slice(0));
console.error("font loaded: " + FAMILY);

const regions = F.textToRegions(font, TEXT, { sizePx: 300 });
console.error("glyph polygons: " + regions[0].polygons.length);

const shapes = DG.groupRingsIntoShapes(regions[0].polygons, 4);
console.error(`shapes ${shapes.length}, holes ${shapes.reduce((a, s) => a + s.holes.length, 0)}`);

const design = DG.buildQualityDesign(
  [{ rgb: [30, 30, 30], shapes }],
  { garment: { widthIn: GW, heightIn: GH }, pxPerMm: 8, densityMm: +(process.env.DENSITY || 0.4), satinMaxWidthMm: +(process.env.SATINMAX || 3.0), underlay: process.env.UNDERLAY !== "0" }
);
console.error(`design ${design.stitchCount} stitches, satin ${design._debug.nSatin} fill ${design._debug.nFill}, ${design.widthMM.toFixed(1)}x${design.heightMM.toFixed(1)}mm`);
fs.writeFileSync(process.argv[2] || "scratch_text.dst", Buffer.from(D.encodeDST(design)));
fs.writeFileSync(process.argv[3] || "scratch_text_colors.json", JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
console.log(JSON.stringify({ stitches: design.stitchCount, satin: design._debug.nSatin, fill: design._debug.nFill }));
