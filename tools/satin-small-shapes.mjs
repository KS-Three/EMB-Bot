// What the browser's medial satin does to SMALL SHAPES, with `satinSmallShapes`
// off beside on (MASTER_SCOPE defect 57's remainder: a star's centre, a round
// end's last cross, squares and dots; built 2026-10-20, OFF by default).
//
//   node tools/satin-small-shapes.mjs                 the table: every design off and on
//   node tools/satin-small-shapes.mjs --json out.json the same as JSON (counts, md5s, measures)
//   node tools/satin-small-shapes.mjs --svg <dir>     one SVG per design and arm (src/svgexport.js)
//   node tools/satin-small-shapes.mjs --sheet out.png one row per design, OFF on the left, ON on the right
//   node tools/satin-small-shapes.mjs --pins          print the OFF md5 of the pinned set, as the test wants them
//
// A design is built exactly as `app/src/lib/generate.js` builds a `shape`
// element (the Studio's own ring, `shapesToRegions`, `buildQualityDesign` on
// left chest with its pique preset, underlay on), and a word as it builds a
// `text` element (`buildLetteringDesign` on a library font). The T is a
// hand-drawn joint set to satin, as `tools/satin-walk-census.mjs --kind joint
// --satin` draws one. Nothing here is sewn: every number is of the stitch plan.
//
// Per design: the tier, the stitch count, the longest stitch, how far outside
// its own outline a needle of the satin lands (the plan's thread width is not
// counted), the needle-up distance between its runs, the share of the drawn
// shape under thread (0.1 mm cells, thread drawn 0.4 mm wide, the preview's
// THREAD_WIDTH_MM) and the md5 of its stitch stream (x, y, type of every
// record). The md5 is what `test/satin-small-shapes.test.js` pins: with the
// option off it must not move.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(path.join(ROOT, "src", "digitize.js"));
const DG = require(path.join(ROOT, "src/digitize.js"));
const GAR = require(path.join(ROOT, "src/garments.js"));
const FAB = require(path.join(ROOT, "src/fabrics.js"));
const SVG = require(path.join(ROOT, "src/svgexport.js"));
const FB = require(path.join(ROOT, "src/fontbin.js"));
const lib = (name) => import(pathToFileURL(path.join(ROOT, "app", "src", "lib", name)).href);

const argv = process.argv.slice(2);
const flag = (name) => argv.includes(name);
const opt = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : null; };

const GARMENT = "left_chest";
const garment = GAR.getGarment(GARMENT), fabric = FAB.getFabric(FAB.fabricForGarment(GARMENT));

// ---- the designs ------------------------------------------------------------
// The four the lane was asked for come first and are the pinned set with the
// two words; the rest widen the evidence (an even-pointed star, which the
// classifier sends to satin at every size; a joint; the 6 mm square and dot
// the defect text names).
export const SHAPES = [
  { id: "star5", label: "5-point star, 10 mm, inner ratio 0.45", kind: "star", params: { points: 5, innerRatio: 0.45 }, sizeMm: 10, pinned: true },
  { id: "round", label: "10 x 2 mm stroke, round ends", kind: "rect", params: { heightMm: 2, cornerRadiusMm: 1 }, sizeMm: 10, pinned: true },
  { id: "square", label: "1.5 mm square", kind: "rect", params: { heightMm: 1.5, cornerRadiusMm: 0 }, sizeMm: 1.5, pinned: true },
  { id: "dot", label: "1 mm dot", kind: "circle", params: {}, sizeMm: 1, pinned: true },
  { id: "star6", label: "6-point star, 10 mm, inner ratio 0.45", kind: "star", params: { points: 6, innerRatio: 0.45 }, sizeMm: 10 },
  { id: "tee", label: "T, arms 10 x 2 mm, drawn and set to satin", kind: "joint", params: { shape: "T", arm: 2, size: 10 }, sizeMm: 10, tier: "satin" },
  { id: "square6", label: "6 mm square", kind: "rect", params: { heightMm: 6, cornerRadiusMm: 0 }, sizeMm: 6 },
  { id: "dot6", label: "6 mm dot", kind: "circle", params: {}, sizeMm: 6 },
];
export const WORDS = [
  { id: "word_barstitch", label: "\"Fritsch\" in barstitch_regular, 12 mm", font: "barstitch_regular", text: "Fritsch", emMm: 12, pinned: true },
  { id: "word_venezia", label: "\"Stitches\" in venezia, 10 mm", font: "venezia", text: "Stitches", emMm: 10, pinned: true },
];

// A joint as a user draws one (tools/satin-walk-census.mjs, `jointPoints`).
function jointPoints(manual, { shape, arm: a, size: s }) {
  const PX = manual.PX_PER_MM, cx = manual.CANVAS_W / 2, cy = manual.CANVAS_H / 2, h = a / 2, e = s / 2;
  const pts = shape === "L" ? [[0, 0], [a, 0], [a, s - a], [s, s - a], [s, s], [0, s]]
    : shape === "T" ? [[-e, 0], [e, 0], [e, a], [h, a], [h, s], [-h, s], [-h, a], [-e, a]]
    : [[-h, -e], [h, -e], [h, -h], [e, -h], [e, h], [h, h], [h, e], [-h, e], [-h, h], [-e, h], [-e, -h], [-h, -h]];
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  return pts.map(([x, y]) => ({ x: cx + (x - (x0 + x1) / 2) * PX, y: cy + (y - (y0 + y1) / 2) * PX }));
}

let mods = null;
async function studio() {
  if (!mods) mods = { presets: await lib("shapePresets.js"), manual: await lib("manualShapes.js") };
  return mods;
}
// `extra`: more builder options (a test pins `ties` and the rest OFF with it).
export async function buildShape(spec, on, extra) {
  const { presets, manual } = await studio();
  const points = spec.kind === "joint" ? jointPoints(manual, spec.params) : presets.shapePresetPoints(spec.kind, spec.params, spec.sizeMm);
  const { regions, pxPerMm } = manual.shapesToRegions([
    { id: spec.id, points, curves: {}, stitchType: spec.tier || "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  let x0 = Infinity, x1 = -Infinity;
  for (const p of points) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); }
  return DG.buildQualityDesign(regions, {
    garment, fabric, pxPerMm, darkOnTop: false, underlay: true, targetWidthMm: spec.kind === "joint" ? (x1 - x0) / pxPerMm : spec.sizeMm,
    offsetXMm: 0, offsetYMm: 0, satinSmallShapes: !!on, ...extra,
  });
}
const fonts = new Map();
export function buildWord(spec, on, extra) {
  if (!fonts.has(spec.font)) fonts.set(spec.font, FB.decodeFontBin(fs.readFileSync(path.join(ROOT, "src", "fonts", "bin", spec.font + ".embf"))));
  return DG.buildLetteringDesign(fonts.get(spec.font), spec.text, { garment, fabric, emMm: spec.emMm, pxPerMm: 8, satinSmallShapes: !!on, ...extra });
}

// ---- measures ---------------------------------------------------------------
export const md5Of = (design) => {
  const h = createHash("md5");
  for (const s of design.stitches) h.update(s.x + "," + s.y + "," + s.type + ";");
  return h.digest("hex");
};
const inside = (x, y, poly) => { let c = false; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const a = poly[i], b = poly[j]; if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; };
const toSeg = (x, y, a, b) => { const ex = b[0] - a[0], ey = b[1] - a[1], l2 = ex * ex + ey * ey; let u = l2 ? ((x - a[0]) * ex + (y - a[1]) * ey) / l2 : 0; u = Math.max(0, Math.min(1, u)); return Math.hypot(x - a[0] - ex * u, y - a[1] - ey * u); };
const outBy = (x, y, poly) => { if (inside(x, y, poly)) return 0; let d = Infinity; for (let i = 0; i < poly.length; i++) d = Math.min(d, toSeg(x, y, poly[i], poly[(i + 1) % poly.length])); return d; };
const CELL_MM = 0.1, THREAD_MM = 0.4;

export function measure(design) {
  const st = design.stitches;
  let longest = 0, up = 0, sewing = false, nStitch = 0, trims = 0;
  for (let i = 1; i < st.length; i++) {
    const s = st[i], d = Math.hypot(s.x - st[i - 1].x, s.y - st[i - 1].y) / 10;
    if (s.type === "trim") trims++;
    if (s.type === "jump" && sewing) up += d;
    if (s.type !== "stitch") continue;
    sewing = true; nStitch++;
    if (d > longest) longest = d;
  }
  const out = { tier: design._debug.nSatin ? "satin" : design._debug.nFill ? "fill" : "none", stitches: design.stitchCount, longestMm: longest, upMm: up, trims,
    wMm: design.widthMM, hMm: design.heightMM, md5: md5Of(design) };
  // the one shape's outline (a word has none): thread over it, and the needle farthest outside it
  const outline = (design.shapeOutlines || [])[0];
  if (!outline || !outline.points.length) return out;
  const poly = outline.points;
  let far = 0, satinPts = 0;
  for (const run of design.runs || []) {
    if (run.kind !== "satin") continue;
    for (let i = run.i0; i <= run.i1; i++) if (st[i].type === "stitch") { satinPts++; far = Math.max(far, outBy(st[i].x / 10, st[i].y / 10, poly)); }
  }
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of poly) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
  x0 -= 1; y0 -= 1; x1 += 1; y1 += 1;
  const gw = Math.ceil((x1 - x0) / CELL_MM), gh = Math.ceil((y1 - y0) / CELL_MM);
  const thread = new Uint8Array(gw * gh), R = THREAD_MM / 2 / CELL_MM;
  const stamp = (mx, my) => {
    const cx = (mx - x0) / CELL_MM, cy = (my - y0) / CELL_MM;
    for (let j = Math.floor(cy - R); j <= Math.ceil(cy + R); j++) for (let i = Math.floor(cx - R); i <= Math.ceil(cx + R); i++) {
      if (i < 0 || j < 0 || i >= gw || j >= gh) continue;
      if ((i + 0.5 - cx) ** 2 + (j + 0.5 - cy) ** 2 <= R * R) thread[j * gw + i] = 1;
    }
  };
  for (let i = 1; i < st.length; i++) {
    if (st[i].type !== "stitch") continue;
    const ax = st[i - 1].x / 10, ay = st[i - 1].y / 10, bx = st[i].x / 10, by = st[i].y / 10;
    const steps = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / (CELL_MM / 2)));
    for (let k = 0; k <= steps; k++) stamp(ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps);
  }
  let area = 0, under = 0;
  for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
    if (!inside(x0 + (i + 0.5) * CELL_MM, y0 + (j + 0.5) * CELL_MM, poly)) continue;
    area++; if (thread[j * gw + i]) under++;
  }
  return Object.assign(out, { farOutMm: far, cover: area ? under / area : null, satinPts });
}

// ---- drawing ----------------------------------------------------------------
function png(W, H, px) {
  const raw = Buffer.alloc(H * (1 + W * 4));
  for (let r = 0; r < H; r++) px.copy(raw, r * (1 + W * 4) + 1, r * W * 4, (r + 1) * W * 4);
  const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (b) => { let c = 0xffffffff; for (const v of b) c = crcTable[(c ^ v) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}
function canvas(W, H) {
  const px = Buffer.alloc(W * H * 4, 255);
  const dot = (ix, iy, c, alpha) => {
    if (ix < 0 || iy < 0 || ix >= W || iy >= H) return;
    const o = (iy * W + ix) * 4;
    for (let k = 0; k < 3; k++) px[o + k] = Math.round(px[o + k] * (1 - alpha) + c[k] * alpha);
  };
  const line = (ax, ay, bx, by, c, alpha) => {
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) * 1.5));
    for (let i = 0; i <= n; i++) dot(Math.round(ax + (bx - ax) * i / n), Math.round(ay + (by - ay) * i / n), c, alpha);
  };
  const fill = (poly, c, alpha) => {
    let y0 = Infinity, y1 = -Infinity;
    for (const p of poly) { y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }
    for (let y = Math.max(0, Math.floor(y0)); y <= Math.min(H - 1, Math.ceil(y1)); y++) {
      const xs = [];
      for (let k = 0; k < poly.length; k++) { const a = poly[k], b = poly[(k + 1) % poly.length]; if ((a[1] <= y + 0.5 && b[1] > y + 0.5) || (b[1] <= y + 0.5 && a[1] > y + 0.5)) xs.push(a[0] + (b[0] - a[0]) * ((y + 0.5 - a[1]) / (b[1] - a[1]))); }
      xs.sort((p, q) => p - q);
      for (let m = 0; m + 1 < xs.length; m += 2) for (let x = Math.max(0, Math.ceil(xs[m])); x <= Math.min(W - 1, Math.floor(xs[m + 1])); x++) dot(x, y, c, alpha);
    }
  };
  // 3x5 digits and a few letters, for labels
  const GLYPH = { "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111", "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001", "8": "111101111101111", "9": "111101111001111",
    ".": "000000000000010", " ": "000000000000000", "m": "000000111111101", "O": "111101101101111", "N": "101111111111101", "F": "111100110100100", "x": "000101010101000", "s": "011100010001110", "t": "010111010010011" };
  const text = (x, y, s, scale, c) => {
    for (const ch of s) { const g = GLYPH[ch] || GLYPH[" "]; for (let r = 0; r < 5; r++) for (let q = 0; q < 3; q++) if (g[r * 3 + q] === "1") for (let dy = 0; dy < scale; dy++) for (let dx = 0; dx < scale; dx++) dot(x + q * scale + dx, y + r * scale + dy, c, 1); x += 4 * scale; }
  };
  return { line, fill, text, save: (file) => fs.writeFileSync(file, png(W, H, px)) };
}
// One design, drawn into the canvas with its outline grey, its thread black and
// its needle-up moves red; `s` px per mm, (ox, oy) where the design's field
// origin lands, y up as the field is.
function draw(cv, design, s, ox, oy) {
  for (const o of design.shapeOutlines || []) {
    if (!o.points.length) continue;
    cv.fill(o.points.map(([x, y]) => [ox + x * s, oy - y * s]), [205, 205, 205], 1);
    for (const h of o.holes || []) cv.fill(h.map(([x, y]) => [ox + x * s, oy - y * s]), [255, 255, 255], 1);
  }
  const st = design.stitches;
  let sewing = false;
  for (let i = 1; i < st.length; i++) {
    const a = st[i - 1], b = st[i];
    if (b.type === "stitch") { cv.line(ox + a.x / 10 * s, oy - a.y / 10 * s, ox + b.x / 10 * s, oy - b.y / 10 * s, [0, 0, 0], 0.85); sewing = true; }
    else if (b.type === "jump" && sewing) cv.line(ox + a.x / 10 * s, oy - a.y / 10 * s, ox + b.x / 10 * s, oy - b.y / 10 * s, [220, 30, 30], 0.9);
  }
}
export async function sheet(file, rows) {
  // rows: [{ label, off: design, on: design }]; every row at one scale, the design's bbox centred in its panel
  const PANEL = 300, GAP = 20, HEADER = 24;
  let maxMm = 0;
  for (const r of rows) for (const d of [r.off, r.on]) maxMm = Math.max(maxMm, d.widthMM, d.heightMM);
  const s = (PANEL - 2 * GAP) / Math.max(maxMm, 1);
  const W = 2 * PANEL + 3 * GAP, H = HEADER + rows.length * (PANEL + GAP);
  const cv = canvas(W, H);
  cv.text(GAP + PANEL / 2 - 6, 6, "OFF", 3, [0, 0, 0]); cv.text(2 * GAP + PANEL + PANEL / 2 - 6, 6, "ON", 3, [0, 0, 0]);
  rows.forEach((r, k) => {
    [r.off, r.on].forEach((d, side) => {
      const px0 = GAP + side * (PANEL + GAP), py0 = HEADER + k * (PANEL + GAP);
      // the field extent of what is drawn: outlines and stitches
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const o of d.shapeOutlines || []) for (const [x, y] of o.points) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      for (const q of d.stitches) if (q.type === "stitch") { x0 = Math.min(x0, q.x / 10); x1 = Math.max(x1, q.x / 10); y0 = Math.min(y0, q.y / 10); y1 = Math.max(y1, q.y / 10); }
      const ox = px0 + PANEL / 2 - (x0 + x1) / 2 * s, oy = py0 + PANEL / 2 + (y0 + y1) / 2 * s;
      draw(cv, d, s, ox, oy);
      cv.text(px0 + 4, py0 + PANEL - 12, String(d.stitchCount), 2, [60, 60, 60]);
    });
    // scale rule: 1 mm, bottom left of the row
    const rx = GAP + 4, ry = HEADER + k * (PANEL + GAP) + PANEL - 22;
    cv.line(rx, ry, rx + s, ry, [40, 90, 220], 1); cv.line(rx, ry - 2, rx, ry + 2, [40, 90, 220], 1); cv.line(rx + s, ry - 2, rx + s, ry + 2, [40, 90, 220], 1);
  });
  cv.save(file);
}

// ---- main -------------------------------------------------------------------
async function main() {
  const rows = [];
  for (const spec of SHAPES) rows.push({ spec, off: await buildShape(spec, false), on: await buildShape(spec, true) });
  for (const spec of WORDS) rows.push({ spec, off: buildWord(spec, false), on: buildWord(spec, true) });
  const table = rows.map((r) => ({ id: r.spec.id, label: r.spec.label, pinned: !!r.spec.pinned, off: measure(r.off), on: measure(r.on) }));
  const jsonOut = opt("--json");
  if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify({ garment: GARMENT, rows: table }, null, 1));
  const svgDir = opt("--svg");
  if (svgDir) {
    fs.mkdirSync(svgDir, { recursive: true });
    for (const r of rows) for (const side of ["off", "on"]) fs.writeFileSync(path.join(svgDir, `${r.spec.id}-${side}.svg`), SVG.designToSVG(r[side]));
  }
  const sheetOut = opt("--sheet");
  if (sheetOut) await sheet(sheetOut, rows.filter((r) => r.spec.kind));
  if (flag("--pins")) {
    for (const t of table) if (t.pinned) console.log(`  ${t.id}: "${t.off.md5}",`);
    return;
  }
  const f = (v, n = 2) => (v == null ? "-" : typeof v === "number" ? v.toFixed(n) : String(v));
  console.log("design                                   | tier  | stitches off -> on | longest mm   | out mm       | up mm        | cover        | md5 moved");
  for (const t of table) {
    const o = t.off, n = t.on;
    console.log(`${t.label.padEnd(40)} | ${o.tier.padEnd(5)} | ${String(o.stitches).padStart(5)} -> ${String(n.stitches).padEnd(8)} | ${f(o.longestMm).padStart(5)} -> ${f(n.longestMm).padEnd(5)}| ${f(o.farOutMm).padStart(5)} -> ${f(n.farOutMm).padEnd(5)}| ${f(o.upMm, 1).padStart(5)} -> ${f(n.upMm, 1).padEnd(5)}| ${f(o.cover == null ? null : o.cover * 100, 0).padStart(5)} -> ${f(n.cover == null ? null : n.cover * 100, 0).padEnd(5)}| ${o.md5 === n.md5 ? "no" : "yes"}`);
  }
}
if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) await main();
