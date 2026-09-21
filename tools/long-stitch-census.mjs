// Long-stitch census for the BROWSER lettering lane (quality review item 10).
//
// The engine emits satin crosses no machine can sew. DOCTRINE 2026-09-07
// measured the damage on the encoder side and left the engine side to Kent:
// "18 fonts produce stitches over one DST record, worst 32.8 mm ... a
// two-letter monogram on a Full Back gives 1,933 of 5,828, worst 44.9 mm."
// This walks the same 85 shipped fonts and re-measures it from the STITCH
// STREAM, so the numbers item 10's build is judged against are this tree's
// own, not a quote.
//
// What it counts, per (font, text, garment):
//   sewn      consecutive stitch->stitch segments (the chain rule DOCTRINE's
//             encoder fix uses: a move is sewn only when this record is a
//             stitch AND the last emitted one was — a jump/trim/colour cuts
//             the chain, and the move to a run's first point is travel)
//   over12    sewn segments past one DST record. A record carries +-121 units
//             PER AXIS, so the test is max(|dx|,|dy|) > 12.1 mm, not the
//             segment's length — and that is the rule that reproduces
//             DOCTRINE's own count (see --doctrine below). Euclidean length
//             counts 53 more on the same design and calls the worst 51.1 mm
//             instead of 44.9.
//   maxax     the worst axis delta of any sewn segment (DOCTRINE's "worst")
//   over5     sewn segments whose LENGTH is past machine.SPLIT_SATIN_ABOVE_MM
//             — the corpus threshold the Python engine splits at, and what an
//             engine-side split would fire on. Length, not axis: a 7 mm cross
//             floats on the fabric whichever way it points.
//   maxmm     the longest sewn segment
//
// Usage:
//   node tools/long-stitch-census.mjs                 # the three-text sweep
//   node tools/long-stitch-census.mjs --doctrine      # the two monogram rows
//   node tools/long-stitch-census.mjs --font manga_impact --text AB --garment full_back
//   node tools/long-stitch-census.mjs --json out.json
import { createRequire } from "module";
import fs from "node:fs";
import path from "node:path";
const require = createRequire(import.meta.url);
global.window = global;
const DG = require("../src/digitize.js");
const fontbin = require("../src/fontbin.js");
const garments = require("../src/garments.js");

const BIN_DIR = path.resolve(process.argv[1], "../../src/fonts/bin");
const DST_MM = 12.1;                 // src/dst.js MAX_DELTA 121 @ 10 units/mm
const SPLIT_ABOVE_MM = 5.0;          // machine.SPLIT_SATIN_ABOVE_MM

function loadFont(name) {
  return fontbin.decodeFontBin(fs.readFileSync(path.join(BIN_DIR, name + ".embf")));
}
function fontNames() {
  return fs.readdirSync(BIN_DIR).filter((f) => f.endsWith(".embf"))
    .map((f) => f.slice(0, -5)).sort();
}
function garment(id) {
  const g = garments.getGarment ? garments.getGarment(id) : null;
  if (g) return g;
  throw new Error("unknown garment " + id);
}

// One design -> its census row. Segment lengths come off the DST-unit stitch
// coordinates the encoders actually see, so "over one record" here is the
// same comparison `encodeDST` makes.
function census(design) {
  const st = design.stitches || [];
  let sewn = 0, over12 = 0, over5 = 0, maxmm = 0, maxax = 0;
  let prev = null, prevWasStitch = false;
  for (const s of st) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && prevWasStitch) {
        const dx = Math.abs(s.x - prev.x) / 10, dy = Math.abs(s.y - prev.y) / 10;
        const ax = Math.max(dx, dy), mm = Math.hypot(dx, dy);
        sewn += 1;
        if (ax > DST_MM) over12 += 1;
        if (mm > SPLIT_ABOVE_MM) over5 += 1;
        if (mm > maxmm) maxmm = mm;
        if (ax > maxax) maxax = ax;
      }
      prev = s; prevWasStitch = true;
    } else {
      // jump / trim / colour: the needle comes up, the chain is cut.
      if (s.type !== "color") prev = s;
      prevWasStitch = false;
    }
  }
  return { stitches: design.stitchCount, sewn, over12, over5, maxmm, maxax,
           wmm: design.widthMM, hmm: design.heightMM };
}

// `arm` selects which of item 10's two answers is on: "off" (today),
// "split" (cfg.splitSatin), "fill" (cfg.wideColumnFill), "both".
// `off` says splitSatin:false EXPLICITLY, not `{}`. `splitSatin` went default
// ON on 2026-09-11 (Kent's ruling), so an empty arm would silently become the
// split arm and every before/after in this tool would read as no change.
const ARMS = {
  off: { splitSatin: false },
  split: { splitSatin: true },
  fill: { splitSatin: false, wideColumnFill: true },
  both: { splitSatin: true, wideColumnFill: true },
};

function run(fontName, text, garmentId, emMm, arm) {
  const font = loadFont(fontName);
  const design = DG.buildLetteringDesign(font, text, Object.assign({
    garment: garment(garmentId), pxPerMm: 8, emMm: emMm || 18,
    rgb: [25, 25, 25], pullCompMm: 0.2,
  }, ARMS[arm || "off"]));
  const L = design.lettering || {};
  return Object.assign({ font: fontName, text, garment: garmentId, arm: arm || "off",
                         trims: design._debug.nTrims,
                         splits: L.splitPenetrations || 0, wideSpans: L.wideSpans || 0 },
                       census(design));
}

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf("--" + name); return i >= 0 ? argv[i + 1] : dflt; };
const has = (name) => argv.includes("--" + name);

const rows = [];
const arm = flag("arm", "off");
if (!ARMS[arm]) throw new Error("--arm must be one of " + Object.keys(ARMS).join(", "));
if (flag("font", null)) {
  rows.push(run(flag("font"), flag("text", "AB"), flag("garment", "full_back"), +flag("em", 18), arm));
} else if (has("doctrine")) {
  // The two rows DOCTRINE 2026-09-07 states, on the font it states them for.
  rows.push(run("manga_impact", "A", "left_chest", 18, arm));
  rows.push(run("manga_impact", "AB", "full_back", 18, arm));
} else {
  // Two sweeps. `--big` is the regime the defect lives in — DOCTRINE's own
  // finding is that the quick starts are clean and "it starts when letters
  // get big", and Full Back is a shipped garment the product offers today.
  const texts = has("big")
    ? [["AB", "full_back"], ["Yours", "full_back"], ["A", "left_chest"]]
    : [["YOUR NAME", "hat_front"], ["Your Name", "left_chest"], ["Yours", "left_chest"]];
  for (const name of fontNames()) {
    for (const [text, g] of texts) {
      try { rows.push(run(name, text, g, 18, arm)); }
      catch (e) { rows.push({ font: name, text, garment: g, error: String(e.message || e) }); }
    }
  }
}

const jsonOut = flag("json", null);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(rows, null, 1));

const bad = rows.filter((r) => r.over12 > 0);
const errs = rows.filter((r) => r.error);
console.log("font                      text        garment       stitches  sewn  >rec  worst ax  >5mm   max mm");
for (const r of rows) {
  if (r.error) { console.log(`${r.font.padEnd(25)} ${String(r.text).padEnd(11)} ${r.garment.padEnd(13)} ERROR ${r.error}`); continue; }
  if (!has("all") && !r.over12) continue;
  console.log(`${r.font.padEnd(25)} ${String(r.text).padEnd(11)} ${r.garment.padEnd(13)} ${String(r.stitches).padStart(8)} ${String(r.sewn).padStart(5)} ${String(r.over12).padStart(5)} ${r.maxax.toFixed(1).padStart(9)} ${String(r.over5).padStart(5)} ${r.maxmm.toFixed(1).padStart(8)}`);
}
const fontsOver = new Set(bad.map((r) => r.font));
const worstAx = rows.reduce((a, r) => (r.maxax > a ? r.maxax : a), 0);
const worst = rows.reduce((a, r) => (r.maxmm > a ? r.maxmm : a), 0);
const sewnAll = rows.reduce((a, r) => a + (r.sewn || 0), 0);
const o5 = rows.reduce((a, r) => a + (r.over5 || 0), 0);
console.log(`\n${rows.length} rows, ${errs.length} errors; ${fontsOver.size} fonts of ${new Set(rows.map((r) => r.font)).size} produce a stitch over one DST record; worst axis delta ${worstAx.toFixed(1)} mm, longest sewn segment ${worst.toFixed(1)} mm`);
console.log(`${o5} of ${sewnAll} sewn segments are past the ${SPLIT_ABOVE_MM} mm split threshold (${(100 * o5 / (sewnAll || 1)).toFixed(1)}%)`);
const st = rows.reduce((a, r) => a + (r.stitches || 0), 0);
const tr = rows.reduce((a, r) => a + (r.trims || 0), 0);
console.log(`arm "${arm}": ${st} stitches, ${tr} trims, ${rows.reduce((a, r) => a + (r.splits || 0), 0)} split penetrations, ${rows.reduce((a, r) => a + (r.wideSpans || 0), 0)} stretches re-routed to fill`);
for (const key of [...new Set(rows.map((r) => r.text + " @ " + r.garment))]) {
  const sub = rows.filter((r) => r.text + " @ " + r.garment === key && !r.error);
  if (!sub.length) continue;
  const nOver = sub.filter((r) => r.over12 > 0).length;
  console.log(`  "${key}": ${sub.reduce((a, r) => a + r.over12, 0)} of ${sub.reduce((a, r) => a + r.sewn, 0)} sewn segments over one record, in ${nOver} of ${sub.length} fonts; ` +
    `${sub.reduce((a, r) => a + r.over5, 0)} past ${SPLIT_ABOVE_MM} mm`);
}
