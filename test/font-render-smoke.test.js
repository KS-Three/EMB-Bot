// Every shipped font actually renders, and none of them is a machine hazard
// (2026-08-22).
//
// This is the check that would have caught the defect this branch opened with,
// in the terms that actually matter. mimosa_large's "D" sewed 6,193 stitches
// into 40.0 x 0.0 mm — a needle hammering one line thousands of times — and
// every static check in the repo called the font healthy: the glyph kept its
// full column count and all its rail points; only their PLACEMENT had
// collapsed. Nothing was measuring "how much thread goes into how much area".
//
// So this one renders each font through the real lettering path and asks three
// questions a broken font cannot answer well: did it throw, did it put any
// thread down, and did it put a lot of thread into no space.
//
// The threshold has enormous measured headroom, which is the point — it is a
// hazard tripwire, not a quality metric, and it must never be the thing that
// fails on a merely unusual font. Measured across all 85 shipped fonts at
// emMm 20 / pxPerMm 8: the smallest rendered HEIGHT is heavenly at 62.7px and
// the smallest WIDTH is montecarlo at 247.0px. MIN_EXTENT_PX is 10 — six times
// below the smallest real font, and a collapsed glyph renders at ~0.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");
for (const m of ["units", "garments", "fabrics", "fill", "geometry", "satin",
                 "satinplay", "satinfont", "fontbin", "dst", "fonts", "digitize"])
  require("../src/" + m + ".js");
const EMB = globalThis.EMB;

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const MIN_EXTENT_PX = 10;
const HAZARD_STITCHES = 50; // below this, "no area" is a dot, not a hazard

// src/fonts/bin/ is COMMITTED. A missing library on CI means the build did not
// run — not that there is nothing to check — and a test that returns early
// asserts nothing while reporting green.
function library() {
  if (!fs.existsSync(BIN)) {
    if (process.env.CI) throw new Error("src/fonts/bin missing on CI — the font library did not build");
    return null;
  }
  const files = fs.readdirSync(BIN).filter((f) => f.endsWith(".embf"));
  assert.ok(files.length > 50, `only ${files.length} .embf files — the library did not build`);
  return files.map((f) => [f.replace(/\.embf$/, ""), fb.decodeFontBin(fs.readFileSync(path.join(BIN, f)))]);
}

// The font's OWN first few letters, whatever the script — a fixed "ABCDE"
// would silently test nothing on the Hebrew faces, which is the Latin
// assumption this branch spent the day removing from everything else.
const sampleFor = (font) =>
  Object.keys(font.glyphs)
    .filter((k) => [...k].length === 1 && k !== " " && /^\p{L}$/u.test(k))
    .slice(0, 5).join("");

function render(font) {
  const chars = sampleFor(font);
  const lay = EMB.layoutText(font, chars, { emMm: 20, pxPerMm: 8 });
  let stitches = 0;
  for (const r of lay.runs || []) stitches += (r.pts || r.points || []).length;
  return {
    chars, stitches,
    w: lay.bbox.x1 - lay.bbox.x0,
    h: lay.bbox.y1 - lay.bbox.y0,
  };
}

test("every shipped font renders its own letters without throwing", () => {
  const all = library();
  if (!all) return;
  const failures = [];
  for (const [key, font] of all) {
    const chars = sampleFor(font);
    if (!chars) { failures.push(`${key}: no letter glyphs at all`); continue; }
    try { render(font); } catch (e) { failures.push(`${key}: ${e.message}`); }
  }
  assert.deepStrictEqual(failures, []);
});

test("no shipped font renders as zero stitches", () => {
  const all = library();
  if (!all) return;
  const dead = [];
  for (const [key, font] of all) {
    const r = render(font);
    if (r.stitches === 0) dead.push(`${key} (sample ${JSON.stringify(r.chars)})`);
  }
  assert.deepStrictEqual(dead, [],
    "a font that produces no stitches for its own letters ships as an empty design");
});

test("no shipped font packs stitches into no area — the mimosa_large hazard", () => {
  const all = library();
  if (!all) return;
  const hazards = [];
  for (const [key, font] of all) {
    const r = render(font);
    if (r.stitches > HAZARD_STITCHES && (r.w < MIN_EXTENT_PX || r.h < MIN_EXTENT_PX))
      hazards.push(`${key}: ${r.stitches} stitches into ${r.w.toFixed(1)}x${r.h.toFixed(1)}px`);
  }
  assert.deepStrictEqual(hazards, [],
    "this is a needle hammering one line — do NOT relax the threshold to make it pass, " +
    "and do not ship the font until the geometry is understood");
});
