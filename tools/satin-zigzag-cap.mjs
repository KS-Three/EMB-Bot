// The satin zigzag's width cap (Kent's ruling 2026-10-14): one script for the
// numbers and the pictures, so "before" and "after" are the same harness run
// on two trees.
//
//   node tools/satin-zigzag-cap.mjs                    # stitch counts + small-text md5s, JSON on stdout
//   node tools/satin-zigzag-cap.mjs --opts '{"satinZigzag":false}'
//   node tools/satin-zigzag-cap.mjs --render <dir> --tag before
//
// The big-text rows are PR #904's own measurement, the call in
// test/wide-columns.test.js: manga_impact "AB" on a full_back, pxPerMm 8,
// emMm 18, pullCompMm 0.2. "auto" is the Studio auto-fit (198 mm wide since
// the hoop cap of 2026-10-13); 1e4 asks for the full Full Back and the engine
// clamps it to 304.8 mm. The small-text rows are tools/small-cap-census.mjs's
// call at a calibrated cap height.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { encodePNG } from "./png.mjs";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
global.window = global;
const DG = require("../src/digitize.js");
const fontbin = require("../src/fontbin.js");
const garments = require("../src/garments.js");

const BIN = path.join(ROOT, "src", "fonts", "bin");
export const loadFont = (name) => fontbin.decodeFontBin(fs.readFileSync(path.join(BIN, name + ".embf")));

export const BIG_TEXT = "AB";
export const BIG_FONT = "manga_impact";
export const BIG_WIDTHS = { "5 mm": 5, "50 mm": 50, auto: undefined, "Full Back": 1e4 };
export function buildBig(font, targetWidthMm, extra) {
  return DG.buildLetteringDesign(font, BIG_TEXT, Object.assign({
    garment: garments.getGarment("full_back"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25], pullCompMm: 0.2,
  }, targetWidthMm === undefined ? {} : { targetWidthMm }, extra || {}));
}

export const SMALL_TEXT = "Hamburgefonstiv 0123";
export const SMALL_FONTS = ["alchemy", "montecarlo", "manga_impact"];
export const SMALL_CAPS = [3, 4.5, 6];
const TRIAL_WIDTH_MM = 30;
function buildSmall(font, targetWidthMm, extra) {
  return DG.buildLetteringDesign(font, SMALL_TEXT, Object.assign({
    garment: garments.getGarment("full_back"), pxPerMm: 8,
    rgb: [20, 20, 20], weightPreset: "normal", targetWidthMm,
  }, extra || {}));
}
// -> the design at a cap height of `capMm`, calibrated the census's way.
export function buildAtCap(font, capMm, extra) {
  const trialCap = buildSmall(font, TRIAL_WIDTH_MM, extra).lettering.capMm;
  return buildSmall(font, TRIAL_WIDTH_MM * capMm / trialCap, extra);
}
export const streamMd5 = (design) => crypto.createHash("md5").update(JSON.stringify(design.stitches)).digest("hex");

const r1 = (x) => Math.round(x * 10) / 10;
function row(d) {
  const L = d.lettering || {};
  return { widthMm: r1(d.widthMM), heightMm: r1(d.heightMM), capMm: r1(L.capMm || 0), stitches: d.stitchCount,
    splitPenetrations: L.splitPenetrations, zigzagColumns: L.zigzagColumns, zigzagCapped: L.zigzagCapped };
}

// ---- pictures ----------------------------------------------------------------
// Each sewn segment drawn as a 0.4 mm thread, anti-aliased, dark on cream.
function draw(design, pxPerMm, win) {
  const st = design.stitches;
  const sewn = st.filter((s) => s.type === "stitch");
  let x0 = Math.min(...sewn.map((s) => s.x)), x1 = Math.max(...sewn.map((s) => s.x));
  let y0 = Math.min(...sewn.map((s) => s.y)), y1 = Math.max(...sewn.map((s) => s.y));
  if (win) { const cx = (x0 + x1) / 2 + win.dx * 10, cy = (y0 + y1) / 2 + win.dy * 10; x0 = cx - win.mm * 5; x1 = cx + win.mm * 5; y0 = cy - win.mm * 5; y1 = cy + win.mm * 5; }
  const pad = Math.round(pxPerMm), k = pxPerMm / 10;
  const W = Math.ceil((x1 - x0) * k) + 2 * pad, H = Math.ceil((y1 - y0) * k) + 2 * pad;
  const buf = new Float32Array(W * H * 3);
  for (let i = 0; i < W * H; i++) { buf[i * 3] = 244; buf[i * 3 + 1] = 238; buf[i * 3 + 2] = 224; }
  const hw = Math.max(0.6, 0.2 * pxPerMm), ink = [30, 30, 40], alpha = 0.55;
  const X = (x) => (x - x0) * k + pad, Y = (y) => (y1 - y) * k + pad;
  let prev = null, pws = false;
  for (const s of st) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && pws) {
        const ax = X(prev.x), ay = Y(prev.y), bx = X(s.x), by = Y(s.y);
        const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1;
        const xa = Math.max(0, Math.floor(Math.min(ax, bx) - hw - 1)), xb = Math.min(W - 1, Math.ceil(Math.max(ax, bx) + hw + 1));
        const ya = Math.max(0, Math.floor(Math.min(ay, by) - hw - 1)), yb = Math.min(H - 1, Math.ceil(Math.max(ay, by) + hw + 1));
        for (let y = ya; y <= yb; y++) for (let x = xa; x <= xb; x++) {
          const t = Math.max(0, Math.min(1, ((x + 0.5 - ax) * dx + (y + 0.5 - ay) * dy) / L2));
          const dd = Math.hypot(x + 0.5 - (ax + t * dx), y + 0.5 - (ay + t * dy));
          const cov = Math.max(0, Math.min(1, hw - dd + 0.5)) * alpha;
          if (cov <= 0) continue;
          const o = (y * W + x) * 3;
          for (let c = 0; c < 3; c++) buf[o + c] += (ink[c] - buf[o + c]) * cov;
        }
      }
      prev = s; pws = true;
    } else { if (s.type !== "color") prev = s; pws = false; }
  }
  const out = new Uint8Array(W * H * 4);
  for (let i = 0; i < W * H; i++) { out[i * 4] = buf[i * 3]; out[i * 4 + 1] = buf[i * 3 + 1]; out[i * 4 + 2] = buf[i * 3 + 2]; out[i * 4 + 3] = 255; }
  return { W, H, png: encodePNG(W, H, out) };
}

// Whole design at a size that fits ~800 px, plus a 16 px/mm close-up where
// the stitch order is readable.
export const RENDERS = [
  { name: "5mm", width: 5, pxPerMm: 120 },
  { name: "50mm", width: 50, pxPerMm: 16 },
  { name: "50mm-closeup", width: 50, pxPerMm: 40, win: { mm: 12, dx: -12, dy: 0 } },
  { name: "198mm", width: undefined, pxPerMm: 4 },
  { name: "198mm-closeup", width: undefined, pxPerMm: 16, win: { mm: 30, dx: -55, dy: 0 } },
];

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const argv = process.argv.slice(2);
  const flag = (n, d) => { const i = argv.indexOf("--" + n); return i >= 0 ? argv[i + 1] : d; };
  const extra = JSON.parse(flag("opts", "{}"));
  const big = loadFont(BIG_FONT);
  if (flag("render", null)) {
    const dir = flag("render"), tag = flag("tag", "now");
    fs.mkdirSync(dir, { recursive: true });
    for (const r of RENDERS) {
      const d = buildBig(big, r.width, extra);
      const { W, H, png } = draw(d, r.pxPerMm, r.win);
      const f = path.join(dir, `${tag}-${r.name}.png`);
      fs.writeFileSync(f, png);
      console.log(`${f}: ${W}x${H}, ${d.stitchCount} stitches, ${r1(d.widthMM)} x ${r1(d.heightMM)} mm`);
    }
  } else {
    const out = { big: {}, small: {} };
    for (const [label, w] of Object.entries(BIG_WIDTHS)) out.big[label] = row(buildBig(big, w, extra));
    for (const name of SMALL_FONTS) {
      const f = loadFont(name);
      for (const cap of SMALL_CAPS) {
        const d = buildAtCap(f, cap, extra);
        out.small[`${name} ${cap}`] = { capMm: Math.round(d.lettering.capMm * 100) / 100, stitches: d.stitchCount, md5: streamMd5(d) };
      }
    }
    console.log(JSON.stringify(out, null, 1));
  }
}
