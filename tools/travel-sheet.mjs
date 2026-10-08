// A design's three files, drawn from what a third-party reader makes of each:
// where the needle goes down, what is sewn and what is travelled.
//
//   node tools/travel-sheet.mjs out.svg [--against otherSrc]
//
// Four designs whose stream holds a stitch that FOLLOWS travel from more than
// one record away (the chain rule, src/dst.js):
//   a hand-drawn T set to satin and a thin four-point star off the shape
//     tool, whose satin floats to a far arm and sews back where it was;
//   a stitch file whose first record is a stitch, imported and placed off the
//     middle of the hoop;
//   lettering, then that stitch file as the project's second element.
// Each is written as DST, PES and EXP, read back by pystitch
// (tools/crossval_decode.py) and drawn: thread, in blue, between two stitches
// in a row; a grey dashed line for every other move; a dot for each needle
// hole; a red ring round a hole the DST of the same design has not (none of
// its holes on it or within 0.1 mm).
//
// --against: a fourth panel, the EXP as another engine's writer lays it. The
// writer before 2026-10-07 is the one to see: it sewed along such a move.
import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";
import os from "node:os";
import { pyDecode, resolvePython } from "./crossval-stitch-formats.mjs";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const AGAINST = args.includes("--against") ? args.splice(args.indexOf("--against"), 2)[1] : null;
const OUT = args[0];
if (!OUT) { console.error("usage: node tools/travel-sheet.mjs out.svg [--against otherSrc]"); process.exit(2); }

const SRC = join(ROOT, "src");
for (const f of ["units.js", "sewtime.js", "garments.js", "fabrics.js", "fill.js", "geometry.js", "quantize.js", "flatten.js", "satin.js", "satinplay.js", "crossfill.js", "satinfont.js", "fontbin.js", "svgpath.js", "svgimport.js", "dst.js", "dstimport.js", "exp.js", "pes.js", "svgexport.js", "stitchModel.js"]) require(join(SRC, f));
const DG = require(join(SRC, "digitize.js")), EMB = globalThis.EMB;
// The writers by what their own files hand back, never off the global: every
// writer also puts itself there, so the last one loaded is the one found
// there, and a file loaded once is not run again. (The first draft of this
// sheet drew the other engine's EXP in both EXP panels that way.)
const WRITE = { dst: require(join(SRC, "dst.js")).encodeDST, pes: require(join(SRC, "pes.js")).encodePES, exp: require(join(SRC, "exp.js")).encodeEXP };
const OTHER_EXP = AGAINST ? (() => {
  const mine = Object.assign({}, EMB), other = require(join(resolve(AGAINST), "exp.js")).encodeEXP;
  Object.assign(EMB, mine);
  return other;
})() : null;
if (OTHER_EXP === WRITE.exp) { console.error("--against is this engine"); process.exit(2); }
const lib = (f) => import(pathToFileURL(join(ROOT, "app", "src", "lib", f)).href);
const { shapePresetPoints } = await lib("shapePresets.js");
const { shapesToRegions } = await lib("manualShapes.js");
const { combineDesigns } = await lib("combine.js");

const chest = EMB.getGarment("left_chest");
const star = (() => {
  const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points: shapePresetPoints("star", { points: 4, innerRatio: 0.15 }, 20), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null }]);
  return DG.buildQualityDesign(regions, { garment: chest, fabric: EMB.getFabric(EMB.fabricForGarment(chest.id)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: 20, offsetXMm: 0, offsetYMm: 0 });
})();
// A T as a person draws one on the side canvas, its stitch type set to Satin.
const drawnT = (() => {
  const points = [[100, 60], [300, 60], [300, 100], [220, 100], [220, 260], [180, 260], [180, 100], [100, 100]].map(([x, y]) => ({ x, y }));
  const { regions, pxPerMm } = shapesToRegions([{ id: "s", points, curves: {}, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null }]);
  return DG.buildQualityDesign(regions, { garment: chest, fabric: EMB.getFabric(EMB.fabricForGarment(chest.id)), pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: 40, offsetXMm: 0, offsetYMm: 0 });
})();
const file = EMB.decodeDSTStandard(new Uint8Array(readFileSync(join(ROOT, "test", "fixtures", "standard-tajima.dst"))));
const placed = EMB.buildImportedDesign(file, { garment: chest, offsetXMm: 30, offsetYMm: -20, blockColors: {} });
const fonts = JSON.parse(readFileSync(join(SRC, "fonts", "manifest.json"), "utf8")).fonts;
const font = EMB.decodeFontBin(readFileSync(join(SRC, "fonts", "bin", fonts[0].key + ".embf")));
const text = DG.buildLetteringDesign(font, "KENT", { garment: chest, pxPerMm: 8, underlay: true, rgb: [20, 20, 20], colorRanges: [], weightPreset: "normal", slantDeg: 0, targetWidthMm: 40, offsetXMm: 0, offsetYMm: 15, letterSpacingMm: 0, arcDeg: 0, rotationDeg: 0, align: "center" });
const pair = combineDesigns([text, EMB.buildImportedDesign(file, { garment: chest, offsetXMm: 0, offsetYMm: -15, blockColors: {} })]);
const DESIGNS = [
  ["A hand-drawn T set to satin, 40 mm", drawnT],
  ["A four-point star, 20 mm, off the shape tool", star],
  ["A stitch file that opens with a stitch, placed 30 mm right of the hoop's middle and 20 mm down", placed],
  ["Lettering, then that stitch file as the second element", pair],
];

const python = resolvePython();
if (!python) { console.error("no python with pystitch (see tools/crossval-stitch-formats.mjs)"); process.exit(1); }
const tmp = mkdtempSync(join(os.tmpdir(), "travel-sheet-"));
const WRITERS = [["dst", "DST", WRITE.dst], ["pes", "PES", WRITE.pes], ["exp", "EXP", WRITE.exp]];
if (OTHER_EXP) WRITERS.push(["exp", "EXP, the other writer", OTHER_EXP]);
const rows = [];
try {
  DESIGNS.forEach(([title, des], d) => {
    const files = WRITERS.map(([ext, , write], w) => { const f = join(tmp, `d${d}w${w}.${ext}`); writeFileSync(f, Buffer.from(write(des))); return f; });
    const got = pyDecode(python, files);
    const sewn = des.stitches.filter((s) => s.type === "stitch"), last = sewn[sewn.length - 1];
    const panels = WRITERS.map(([ext, label], w) => {
      // pystitch's frame is +y down; a PES is read from where its block starts,
      // not from the design's origin, so it is laid on the design's last stitch.
      let cmds = got[`d${d}w${w}.${ext}`].stitches.map(([x, y, kind]) => ({ x, y: -y, kind }));
      if (ext === "pes") {
        const end = cmds.filter((c) => c.kind === "STITCH").pop();
        cmds = cmds.map((c) => ({ x: c.x + last.x - end.x, y: c.y + last.y - end.y, kind: c.kind }));
      }
      return { label, cmds, holes: cmds.filter((c) => c.kind === "STITCH") };
    });
    const dst = new Map();
    for (const h of panels[0].holes) dst.set(h.x + "," + h.y, (dst.get(h.x + "," + h.y) || 0) + 1);
    // A hole the DST has not: none of the DST's is on it or one unit (0.1 mm)
    // from it. The unit is the PES writer's: where a SEWN move over 12.1 mm
    // is split, its split point can sit one unit from the other two's (it
    // splits with y pointing down, and a half rounds the other way).
    for (const p of panels) {
      const left = new Map(dst);
      const take = (k) => { const n = left.get(k) || 0; if (n) left.set(k, n - 1); return n > 0; };
      p.extra = p.holes.filter((h) => !take(h.x + "," + h.y));
      p.extra = p.extra.filter((h) => ![-1, 0, 1].some((dx) => [-1, 0, 1].some((dy) => take((h.x + dx) + "," + (h.y + dy)))));
    }
    rows.push({ title, panels, stream: sewn.length });
  });
} finally { rmSync(tmp, { recursive: true, force: true }); }

// ---- the drawing ---------------------------------------------------------------
// Every style is an attribute of its own element: not every reader of an SVG
// reads a style sheet, and one that does not paints each box solid black.
const W = 340, H = 250, PAD = 18, HEAD = 34, FOOT = 34;
const T = `font-size="13" font-weight="600" fill="#1a1a1a"`, C = `font-size="11" fill="#333333"`;
const BOX = `fill="#fafaf7" stroke="#d8d8d0"`, SEWN = `fill="none" stroke="#1f4e79" stroke-width="1.1" stroke-linecap="round"`;
const TRAVEL = `fill="none" stroke="#9a9a92" stroke-width="0.7" stroke-dasharray="3 2.5"`, HOLE = `fill="none" stroke="#10283f" stroke-width="2.2" stroke-linecap="round"`;
const EXTRA = `fill="none" stroke="#d1242f" stroke-width="1.4"`, ORIGIN = `fill="none" stroke="#555555" stroke-width="1"`;
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
let y0 = 0;
const out = [];
for (const row of rows) {
  const all = row.panels.flatMap((p) => p.cmds).concat([{ x: 0, y: 0 }]);
  const x0 = Math.min(...all.map((c) => c.x)), x1 = Math.max(...all.map((c) => c.x)), yMin = Math.min(...all.map((c) => c.y)), yMax = Math.max(...all.map((c) => c.y));
  const k = Math.min((W - 2 * PAD) / Math.max(1, x1 - x0), (H - 2 * PAD) / Math.max(1, yMax - yMin));
  const X = (x) => PAD + (W - 2 * PAD - k * (x1 - x0)) / 2 + k * (x - x0), Y = (y) => PAD + (H - 2 * PAD - k * (yMax - yMin)) / 2 + k * (yMax - y);
  out.push(`<text x="8" y="${y0 + 22}" ${T}>${esc(row.title)} (${row.stream.toLocaleString("en-US")} stitches in the stream)</text>`);
  row.panels.forEach((p, i) => {
    const gx = i * W, gy = y0 + HEAD;
    const g = [`<rect x="${gx + 4}" y="${gy}" width="${W - 8}" height="${H}" ${BOX}/>`];
    let prev = { x: 0, y: 0, kind: "START" };
    const sewn = [], travel = [];
    for (const c of p.cmds) {
      if (c.kind === "STITCH" || c.kind === "JUMP") {
        const seg = `M${(gx + X(prev.x)).toFixed(1)} ${(gy + Y(prev.y)).toFixed(1)}L${(gx + X(c.x)).toFixed(1)} ${(gy + Y(c.y)).toFixed(1)}`;
        if (c.x !== prev.x || c.y !== prev.y) (c.kind === "STITCH" && prev.kind === "STITCH" ? sewn : travel).push(seg);
      } else if (c.kind !== "TRIM" && c.kind !== "COLOR_CHANGE" && c.kind !== "END" && c.kind !== "STOP") continue;
      prev = { x: c.kind === "STITCH" || c.kind === "JUMP" ? c.x : prev.x, y: c.kind === "STITCH" || c.kind === "JUMP" ? c.y : prev.y, kind: c.kind };
    }
    if (travel.length) g.push(`<path d="${travel.join("")}" ${TRAVEL}/>`);
    if (sewn.length) g.push(`<path d="${sewn.join("")}" ${SEWN}/>`);
    g.push(`<circle cx="${(gx + X(0)).toFixed(1)}" cy="${(gy + Y(0)).toFixed(1)}" r="4" ${ORIGIN}/>`);
    // every hole in ONE path, a round-capped speck each: a circle apiece is most of the file
    g.push(`<path d="${p.holes.map((h) => `M${(gx + X(h.x)).toFixed(1)} ${(gy + Y(h.y)).toFixed(1)}h.01`).join("")}" ${HOLE}/>`);
    for (const h of p.extra) g.push(`<circle cx="${(gx + X(h.x)).toFixed(1)}" cy="${(gy + Y(h.y)).toFixed(1)}" r="5" ${EXTRA}/>`);
    g.push(`<text x="${gx + 8}" y="${gy + H + 16}" ${C}>${esc(p.label)}: ${p.holes.length.toLocaleString("en-US")} needle holes${i ? `, ${p.extra.length} the DST has not` : ""}</text>`);
    out.push(g.join(""));
  });
  y0 += HEAD + H + FOOT;
}
const width = W * rows[0].panels.length;
const legend = [
  "Each file as pystitch reads it. Blue: thread between two stitches in a row. Grey, dashed: every other move. Dot: a needle hole.",
  "Red ring: a hole with no hole of the same design's DST on it or within 0.1 mm of it. Open circle: where the file starts.",
].map((line, i) => `<text x="8" y="${y0 + 14 + 16 * i}" ${C}>${esc(line)}</text>`).join("\n");
writeFileSync(resolve(OUT), `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${y0 + 42}" width="${width}" height="${y0 + 42}" font-family="Arial, Helvetica, sans-serif">
<rect width="${width}" height="${y0 + 42}" fill="#ffffff"/>
${out.join("\n")}
${legend}
</svg>
`);
for (const row of rows) console.log(`${row.title}\n  ${row.panels.map((p, i) => `${p.label} ${p.holes.length}${i ? ` (${p.extra.length} the DST has not)` : ""}`).join("; ")}`);
console.log(`\n${resolve(OUT)}`);
