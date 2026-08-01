// Sew-out card bridge: design JSON (from digitizer/tools/sewout_card.py, via
// the Python adapter) -> EMBBOT_SEWOUT_CARD.dst written by the BROWSER encoder.
//
// The export path is load-bearing: src/dst.js is the codec with sew evidence
// on Kent's machine, and it disagrees with pyembroidery on axis convention
// (docs/dst-axis-verdict-2026-07-31.md) — so the machine file for this card
// must come from HERE, not from the service's pyembroidery exporter.
//
// Steps: read design JSON -> strip "end" records (encodeDST would sew a stray
// one as a real stitch back at the origin; see app/src/lib/combine.js) ->
// encodeDST -> decode back with decodeDST and assert stitch count, color
// count and extents round-trip -> render a preview PNG of the actual DST
// bytes with the existing tools/render-dst.mjs.
//
// Usage (from the repo root):
//   node tools/sewout_bridge.mjs [design.json] [out.dst]
import { createRequire } from "module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const D = require("../src/dst.js");
const DI = require("../src/dstimport.js");

const here = path.dirname(fileURLToPath(import.meta.url));
const OUTDIR = path.join(here, "..", "digitizer", "debug_out", "sewout");
const inPath = process.argv[2] || path.join(OUTDIR, "EMBBOT_SEWOUT_CARD.design.json");
const dstPath = process.argv[3] || path.join(OUTDIR, "EMBBOT_SEWOUT_CARD.dst");
const colorsPath = inPath.replace(/\.design\.json$/, ".colors.json");
const pngPath = dstPath.replace(/\.dst$/i, ".preview.png");

const design = JSON.parse(fs.readFileSync(inPath, "utf8"));

// The adapter appends a trailing {x:0,y:0,type:"end"}; encodeDST has no "end"
// branch and would encode it as a stitch flying back to the origin. Strip it
// exactly the way combineDesigns does, and appendix its own end record instead
// (encodeDST always writes one).
const stitches = (design.stitches || []).filter((s) => s.type !== "end");
const stripped = design.stitches.length - stitches.length;
const enc = {
  stitches,
  colors: design.colors || [],
  label: String(design.name || "EMBBOT CARD").slice(0, 16),
};

const byType = {};
let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
for (const s of stitches) {
  byType[s.type] = (byType[s.type] || 0) + 1;
  if (s.type === "stitch") {
    if (s.x < minX) minX = s.x;
    if (s.x > maxX) maxX = s.x;
    if (s.y < minY) minY = s.y;
    if (s.y > maxY) maxY = s.y;
  }
}
const inW = (maxX - minX) / 10, inH = (maxY - minY) / 10;

const bytes = D.encodeDST(enc);
fs.writeFileSync(dstPath, Buffer.from(bytes));

// --- round-trip with the browser decoder ---------------------------------
const dec = DI.decodeDST(new Uint8Array(fs.readFileSync(dstPath)));
const problems = [];
if (dec.stitchCount !== (byType.stitch || 0)) {
  problems.push(`stitch count: encoded ${byType.stitch} decoded ${dec.stitchCount}`);
}
const decColors = dec.stitches.filter((s) => s.type === "color").length;
if (decColors !== (byType.color || 0)) {
  problems.push(`color changes: encoded ${byType.color} decoded ${decColors}`);
}
if (Math.abs(dec.widthMM - inW) > 0.05 || Math.abs(dec.heightMM - inH) > 0.05) {
  problems.push(`extents: in ${inW.toFixed(1)}x${inH.toFixed(1)} decoded ${dec.widthMM}x${dec.heightMM}`);
}
if (problems.length) {
  console.error("ROUND-TRIP FAILED:\n  " + problems.join("\n  "));
  process.exit(1);
}

// --- preview of the actual DST bytes via the existing render tooling ------
execFileSync(process.execPath,
  [path.join(here, "render-dst.mjs"), dstPath, pngPath, "8",
   ...(fs.existsSync(colorsPath) ? [colorsPath] : [])],
  { stdio: "inherit" });

console.log(JSON.stringify({
  dst: dstPath,
  bytes: bytes.length,
  records: (bytes.length - 512) / 3,
  strippedEndRecords: stripped,
  encodedByType: byType,
  decoded: {
    stitches: dec.stitchCount,
    jumps: dec.jumpCount,
    trims: dec.trimCount,
    colorChanges: decColors,
    sizeMM: [dec.widthMM, dec.heightMM],
    label: dec.label,
  },
  preview: pngPath,
}, null, 2));
