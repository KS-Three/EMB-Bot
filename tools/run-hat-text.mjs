// Build the PRECISION / THERMAL / AND DRONE stacked hat text as flat lettering.
import { createRequire } from "module";
import fs from "node:fs";
const require = createRequire(import.meta.url);
global.window = global;
const opentype = require("../scratch_opentype.js");
globalThis.opentype = opentype;
const F = require("../src/fonts.js");
const DG = require("../src/digitize.js");
const D = require("../src/dst.js");

async function loadFamily(family) {
  const e = F.FONTS.find((f) => f.family === family);
  const cache = "scratch_font_" + family.replace(/\W+/g, "_") + ".ttf";
  if (!fs.existsSync(cache)) {
    const res = await fetch(e.url);
    fs.writeFileSync(cache, Buffer.from(await res.arrayBuffer()));
  }
  return opentype.parse(fs.readFileSync(cache).buffer.slice(0));
}

const SILVER = [176, 180, 186], ORANGE = [240, 125, 10];
const LINES = [
  { text: "PRECISION", family: "Archivo Black", sizePx: 190, rgb: SILVER, gapBelow: 40 },
  { text: "THERMAL", family: "Archivo Black", sizePx: 150, rgb: ORANGE, gapBelow: 36 },
  { text: "AND DRONE", family: "Oswald", sizePx: 92, rgb: SILVER, gapBelow: 0 },
];

const fonts = {};
for (const L of LINES) if (!fonts[L.family]) fonts[L.family] = await loadFamily(L.family);

function ringsBBox(rings) {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const r of rings) for (const q of r) { if (q.x < minX) minX = q.x; if (q.x > maxX) maxX = q.x; if (q.y < minY) minY = q.y; if (q.y > maxY) maxY = q.y; }
  return { minX, minY, maxX, maxY, w: maxX - minX, h: maxY - minY };
}

// build each line's shapes, then center-stack them
const built = [];
for (const L of LINES) {
  const regions = F.textToRegions(fonts[L.family], L.text, { sizePx: L.sizePx });
  const rings = regions[0].polygons;
  const bb = ringsBBox(rings);
  built.push({ L, rings, bb });
}
let y = 0;
const colorMap = new Map(); // rgb key -> {rgb, shapes}
for (const b of built) {
  const dx = -b.bb.minX - b.bb.w / 2; // center x at 0
  const dy = y - b.bb.minY;           // stack downward
  const moved = b.rings.map((r) => r.map((q) => ({ x: q.x + dx, y: q.y + dy })));
  const shapes = DG.groupRingsIntoShapes(moved, 4);
  const key = b.L.rgb.join(",");
  if (!colorMap.has(key)) colorMap.set(key, { rgb: b.L.rgb, shapes: [] });
  colorMap.get(key).shapes.push(...shapes);
  y += b.bb.h + b.L.gapBelow;
}
const regionsQ = [...colorMap.values()];
console.error("colors:", regionsQ.length, "shapes:", regionsQ.reduce((a, r) => a + r.shapes.length, 0));

const design = DG.buildQualityDesign(regionsQ, {
  garment: { widthIn: +(process.env.GW || 5), heightIn: +(process.env.GH || 2.25) },
  pxPerMm: 8, densityMm: 0.4, satinMaxWidthMm: 3.0, underlay: true, outline: false, darkOnTop: false,
});
console.error(`design ${design.stitchCount} stitches, satin ${design._debug.nSatin} fill ${design._debug.nFill}, ${design.widthMM.toFixed(1)}x${design.heightMM.toFixed(1)}mm`);
fs.writeFileSync("scratch_hattext.dst", Buffer.from(D.encodeDST(design)));
fs.writeFileSync("scratch_hattext_colors.json", JSON.stringify(design.colors.map((c) => [c.r, c.g, c.b])));
console.log(JSON.stringify({ stitches: design.stitchCount, colors: design.colorCount, sizeMM: [+design.widthMM.toFixed(1), +design.heightMM.toFixed(1)] }));
