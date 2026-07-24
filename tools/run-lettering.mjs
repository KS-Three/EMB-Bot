// Full pre-digitized lettering pipeline in Node: font library -> layoutText ->
// buildLetteringDesign -> DST. Then render with tools/render-dst.mjs to verify.
// Usage: TEXT="SD WHEEL" FONT=src/fonts/geneva_simple.json GW=5 GH=2.25 node tools/run-lettering.mjs out.dst colors.json
import { createRequire } from "module";
import fs from "node:fs";
const require = createRequire(import.meta.url);
global.window = global;
const DG = require("../src/digitize.js");
const D = require("../src/dst.js");

const TEXT = process.env.TEXT || "SD WHEEL";
const FONT = process.env.FONT || "src/fonts/geneva_simple.json";
const GW = +(process.env.GW || 5), GH = +(process.env.GH || 2.25);
const EMMM = +(process.env.EMMM || 18);
const font = JSON.parse(fs.readFileSync(FONT, "utf8"));

const design = DG.buildLetteringDesign(font, TEXT, {
  garment: { widthIn: GW, heightIn: GH }, pxPerMm: 8, emMm: EMMM,
  rgb: [25, 25, 25], densityMm: +(process.env.DENSITY || 0.4), pullCompMm: 0.2,
});
console.error(`design ${design.stitchCount} stitches, cols ${design._debug.nSatin} trims ${design._debug.nTrims}, ${design.widthMM.toFixed(1)}x${design.heightMM.toFixed(1)}mm`);
fs.writeFileSync(process.argv[2] || "scratch_lettering.dst", Buffer.from(D.encodeDST(design)));
fs.writeFileSync(process.argv[3] || "scratch_lettering_colors.json", JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
console.log(JSON.stringify({ stitches: design.stitchCount, cols: design._debug.nSatin, trims: design._debug.nTrims, wmm: +design.widthMM.toFixed(1), hmm: +design.heightMM.toFixed(1) }));
