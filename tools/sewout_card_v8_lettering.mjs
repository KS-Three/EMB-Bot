// Sew-out card v8, block J: one typed name through the BROWSER lettering
// builder with `cutEveryJump` OFF and ON (src/digitize.js cutOrBuryJumps,
// built OFF 2026-10-27, #1133), written as the JSON the Python card tool
// reads (digitizer/tools/sewout_card_v8.py --cut lettering). Kent, 2026-10-26:
// the JS flag and the Python lane's `cut_every_jump` go on card v8 as an
// OFF-beside-ON arm each; neither flips alone.
//
//   node tools/sewout_card_v8_lettering.mjs [out.json]
//
// The name, font, width and garment are fixed here, not arguments: the card's
// committed cut is what the test regenerates the card from, and a pin that
// takes arguments is not a pin. medium_font is the Studio's default
// (app/src/lib/project.js `fontKey`); the garment is the flat box the
// lettering test uses (test/lettering-cut-every-jump.test.js `FLAT`: no id,
// so no cap centre-out order and no fabric preset), where this name at 44 mm
// leaves 15 floats -- on a cap it leaves 3, at 60 mm flat 6 (measured
// 2026-11-01 with tools/lettering-uncut-jumps.mjs). Every flag the lane reads
// is spread at its 2026-10-27 value (`FROZEN`, the test's), so a later flip
// moves neither arm; the width is explicit, so nothing rides the garment's
// auto-fit (#1118).
//
// Like tools/sewout_bridge.mjs, this is how a browser-engine arm reaches a
// card: the stream, in DST units (y up), goes across as JSON and the card's
// one DST is written by pystitch on the Python side. Each arm's own browser
// DST (src/dst.js) is read back here by tools/lettering-uncut-jumps.mjs's
// reader for the float count and its md5, and ON is judged by that tool's
// oracle (a 0.01 mm raster of the OFF file's thread): both numbers travel in
// the JSON so the README can quote them.
import "./_help.mjs";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DG = require(join(ROOT, "src", "digitize.js"));
const fb = require(join(ROOT, "src", "fontbin.js"));
const dst = require(join(ROOT, "src", "dst.js"));
const O = await import("./lettering-uncut-jumps.mjs");

export const FONT = "medium_font";
export const TEXT = "Fritsch's Stitches";
export const WIDTH_MM = 44;
export const GARMENT = { widthIn: 5, heightIn: 2.25 };
export const FROZEN = { underlay: true, counterGuard: true, shortStitch: true, underlayShortColumns: true, crossFloor: true, satinZigzag: true, ties: true, dedupeHoles: true, underlayDirection: false, splitSatin: false, wideColumnFill: false };
//: arm -> cutEveryJump; the card's teeth: (a) 1 tooth OFF, what ships; (b) 2 teeth ON
export const ARMS = { a: false, b: true };

const out = process.argv[2] || join(ROOT, "docs", "sewout", "card-v8-2026-11-01", "cuts", "lettering.json");
const font = fb.decodeFontBin(readFileSync(join(ROOT, "src", "fonts", "bin", FONT + ".embf")));
const md5 = (bytes) => createHash("md5").update(bytes).digest("hex");

const result = { font: FONT, text: TEXT, width_mm: WIDTH_MM, garment: GARMENT, frozen: FROZEN, units_per_mm: 10, y_up: true, arms: {} };
const recsOf = {};
for (const [arm, on] of Object.entries(ARMS)) {
  const d = DG.buildLetteringDesign(font, TEXT, { ...FROZEN, garment: GARMENT, pxPerMm: 8, targetWidthMm: WIDTH_MM, cutEveryJump: on });
  if (!d || !d.stitchCount) throw new Error(`arm ${arm}: empty design`);
  const bytes = dst.encodeDST(d);
  const recs = O.readDSTRecords(bytes);
  recsOf[arm] = recs;
  result.arms[arm] = {
    cutEveryJump: on,
    width_mm: +d.widthMM.toFixed(2), height_mm: +d.heightMM.toFixed(2),
    stitches: d.stitchCount, trims: d.stitches.filter((s) => s.type === "trim").length,
    uncut_moves_in_dst: O.uncutMoves(recs).length,
    cut_every_jump: d._debug.cutEveryJump || null,
    dst_md5: md5(bytes), dst_bytes: bytes.length,
    stream: d.stitches.map((s) => ({ x: s.x, y: s.y, type: s.type })),
    runs: d.runs || [],
  };
}
const { fresh, bare } = O.bareNewSegments(recsOf.b, recsOf.a);
result.oracle = { on_new_segments: fresh.length, of_them_locks: fresh.filter((s) => s.lock).length, bare_segments: bare.length };
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(result));
const brief = Object.fromEntries(Object.entries(result.arms).map(([k, a]) => [k, { ...a, stream: a.stream.length + " records", runs: a.runs.length + " spans" }]));
console.log(JSON.stringify({ out, arms: brief, oracle: result.oracle }, null, 1));
