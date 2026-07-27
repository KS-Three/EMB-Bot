// Slice 6 Task 1: ARC + MULTI-LINE support in satinfont's layoutText.
//
// Reference values for the back-compat snapshots below were captured by
// running the PRE-refactor code (git history: src/satinfont.js before this
// change) with the exact same inputs, then hard-coded here so any accidental
// change to the straight, single-line code path fails loudly.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const SF = require("../src/satinfont.js");
global.window = global; // digitize.js's UMD wrapper expects a browser-ish global
const DG = require("../src/digitize.js");

const font = JSON.parse(fs.readFileSync(__dirname + "/../src/fonts/geneva_simple.json", "utf8"));

const closeTo = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg || ""}: expected ${a} close to ${b} (tol ${tol})`);

// ---- Back-compat: straight single-line output must be BYTE-IDENTICAL to the
// pre-arc/multi-line refactor (captured before editing src/satinfont.js). ----

test("layoutText: straight single-line 'AB' is byte-identical to the pre-refactor snapshot", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, letterSpacingMm: 0, underlay: true };
  const lay = SF.layoutText(font, "AB", opts);
  assert.deepStrictEqual(lay.bbox, { x0: 23.2, y0: 61.6, x1: 180.3195335344653, y1: 152 });
  assert.strictEqual(lay.runs.length, 14, "run count frozen");
  const totalPts = lay.runs.reduce((n, r) => n + r.pts.length, 0);
  assert.strictEqual(totalPts, 351, "total stitch-point count frozen");
  assert.deepStrictEqual(lay.runs[0].pts[0], { x: 79.97699763999032, y: 128.2379669598646 });
  assert.strictEqual(lay.runs[0].kind, "satin");
  assert.strictEqual(lay.runs[0].jump, true);
  const last = lay.runs[lay.runs.length - 1];
  assert.deepStrictEqual(last.pts[last.pts.length - 1], { x: 157.06136346377406, y: 98.76715817738118 });
});

test("layoutText: each run carries the charIdx of its source character, matching the original string's index", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  const lay = SF.layoutText(font, "AB", opts);
  // "AB" — every run belongs to either char 0 ("A") or char 1 ("B").
  const idxs = new Set(lay.runs.map((r) => r.charIdx));
  assert.deepStrictEqual([...idxs].sort(), [0, 1]);
  // Runs for "A" all come before runs for "B" (glyphs are placed left to right).
  const firstBIdx = lay.runs.findIndex((r) => r.charIdx === 1);
  assert.ok(lay.runs.slice(0, firstBIdx).every((r) => r.charIdx === 0), "all runs before the first B-run belong to char 0");
});

test("layoutText: charIdx accounts for a skipped space and a newline exactly like the original string's indices", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  // "A B\nC" -> indices: A=0, space=1, B=2, \n=3, C=4
  const lay = SF.layoutText(font, "A B\nC", opts);
  const idxs = new Set(lay.runs.map((r) => r.charIdx));
  assert.deepStrictEqual([...idxs].sort((a, b) => a - b), [0, 2, 4], "space(1) and newline(3) produce no glyph runs, so their indices never appear");
});

test("buildLetteringDesign: straight 'AB' targetWidthMm 40 matches the pre-refactor snapshot", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const d = DG.buildLetteringDesign(font, "AB", base);
  assert.strictEqual(d.stitchCount, 701, "stitchCount frozen");
  closeTo(d.widthMM, 40, 0.2, "widthMM");
  closeTo(d.heightMM, 22.839506172839506, 0.2, "heightMM");
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.strictEqual(sew.length, 701);
  assert.deepStrictEqual(sew[0], { x: -56, y: -54, type: "stitch" });
  assert.deepStrictEqual(sew[sew.length - 1], { x: 142, y: 20, type: "stitch" });
});

test("buildLetteringDesign: arcDeg absent/0 is identical to not passing arcDeg at all", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const a = DG.buildLetteringDesign(font, "AB", base);
  const b = DG.buildLetteringDesign(font, "AB", { ...base, arcDeg: 0 });
  assert.deepStrictEqual(a, b);
});

// ---- Arc: rotation is exact (rigid isometry), and the visual contract is
// "arcDeg > 0 arches UP (rainbow: middle higher than the ends) in the
// rendered/sewn output" — verified numerically here (and by eye via the
// rendered PNGs the harness produces; see tools/render-dst.mjs). ----

// Group a layoutText() result's runs by glyph, given each glyph in "HHH"
// produces the SAME run count (identical glyph, so routeGlyph's output shape
// is identical up to the per-glyph affine) — verified below before relying on it.
function glyphGroups(lay, nGlyphs) {
  assert.strictEqual(lay.runs.length % nGlyphs, 0, "expected equal run-count split across identical glyphs");
  const per = lay.runs.length / nGlyphs;
  const groups = [];
  for (let k = 0; k < nGlyphs; k++) {
    const pts = [];
    for (const r of lay.runs.slice(k * per, (k + 1) * per)) for (const p of r.pts) pts.push(p);
    groups.push(pts);
  }
  return groups;
}
const cy = (pts) => { let mn = Infinity, mx = -Infinity; for (const p of pts) { if (p.y < mn) mn = p.y; if (p.y > mx) mx = p.y; } return (mn + mx) / 2; };

// Whole-glyph bounding-box CENTER (`cy` above) is a fine proxy when a glyph's
// ink is roughly symmetric about its own rotation pivot, but the baseline fix
// (see satinfont.js glyphBottomUnits) makes a glyph's ink sit almost entirely
// on ONE side of its pivot (a non-descending letter's ink runs from the
// baseline UP, never below it) — so at large rotation angles the far/near
// edges of that lopsided ink sweep unevenly and the bounding-box center stops
// tracking "where does this letter's baseline sit on the arc" reliably. The
// robust way to ask that exact question: routeGlyph's output order/count for
// a glyph is completely independent of arcDeg (only the later `place()`
// affine differs), so the SAME point index in a straight (arcDeg=0) layout
// and an arc'd layout is the SAME stitch. Find each glyph's baseline point
// (max-y = bottom-of-ink in this y-down font space) in the straight layout,
// then read that exact index back out of the arc'd layout.
function baselineYByIndex(font, text, arcDeg, opts) {
  const straightGroups = glyphGroups(SF.layoutText(font, text, { ...opts, arcDeg: 0 }), 3);
  const baseIdx = straightGroups.map((pts) => { let bi = 0, by = -Infinity; pts.forEach((p, i) => { if (p.y > by) { by = p.y; bi = i; } }); return bi; });
  const arcGroups = glyphGroups(SF.layoutText(font, text, { ...opts, arcDeg }), 3);
  return arcGroups.map((pts, k) => pts[baseIdx[k]].y);
}

test("layoutText: arcDeg rotates each glyph by an EXACT rigid rotation about its own position", () => {
  const opts = (arcDeg) => ({ emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: true, arcDeg });
  const lay0 = SF.layoutText(font, "HHH", opts(0));
  const layArc = SF.layoutText(font, "HHH", opts(120));
  const g0 = glyphGroups(lay0, 3), gArc = glyphGroups(layArc, 3);
  // 120deg swept symmetrically over 3 identical glyphs -> each glyph's own
  // angular position is arcDeg/3 apart: -40, 0, +40 degrees.
  const expectedDeg = [-40, 0, 40];
  for (let k = 0; k < 3; k++) {
    assert.strictEqual(g0[k].length, gArc[k].length, "arc must not change point count, glyph " + k);
    // Every segment vector must be the straight-layout vector rotated by the
    // SAME exact angle (rotation is a rigid isometry: lengths preserved, and
    // the angle shift is constant across every segment of the glyph).
    for (const j of [0, Math.floor(g0[k].length / 3), g0[k].length - 2]) {
      const v0 = { x: g0[k][j + 1].x - g0[k][j].x, y: g0[k][j + 1].y - g0[k][j].y };
      const vA = { x: gArc[k][j + 1].x - gArc[k][j].x, y: gArc[k][j + 1].y - gArc[k][j].y };
      const len0 = Math.hypot(v0.x, v0.y), lenA = Math.hypot(vA.x, vA.y);
      closeTo(lenA, len0, 1e-6, `glyph ${k} seg ${j} length preserved by rotation`);
      let d = (Math.atan2(vA.y, vA.x) - Math.atan2(v0.y, v0.x)) * 180 / Math.PI;
      while (d > 180) d -= 360; while (d < -180) d += 360;
      closeTo(d, expectedDeg[k], 0.05, `glyph ${k} seg ${j} rotation angle`);
    }
  }
});

test("layoutText: arcDeg>0 arches UP — middle glyph's BASELINE sits higher than the outer glyphs'", () => {
  // Font-space here is y-DOWN (see the big comment on glyphBottomUnits): a
  // SMALLER y is HIGHER on screen once the downstream DST T() flip is applied
  // (T().y = (center - q.y) * scale). So "arches up" means the middle glyph's
  // BASELINE y must be numerically LESS than the outer glyphs' (see
  // baselineYByIndex above for why the baseline point specifically, not a
  // whole-glyph bounding-box center, is the robust thing to compare).
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: true };
  const [bL, bM, bR] = baselineYByIndex(font, "HHH", 120, opts);
  assert.ok(bM < bL - 10, `middle baseline (${bM}) should be well above left (${bL})`);
  assert.ok(bM < bR - 10, `middle baseline (${bM}) should be well above right (${bR})`);
});

test("layoutText: arcDeg<0 flips to a valley — middle glyph's BASELINE sits LOWER than the outer glyphs'", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: true };
  const [bL, bM, bR] = baselineYByIndex(font, "HHH", -120, opts);
  assert.ok(bM > bL + 10, `middle baseline (${bM}) should be well below left (${bL})`);
  assert.ok(bM > bR + 10, `middle baseline (${bM}) should be well below right (${bR})`);
});

test("layoutText: two very different-height glyphs' baselines land at nearly the SAME radial position on the arc", () => {
  // The actual bug being fixed: the shared per-line pivot used to be the
  // AVERAGE of each glyph's own vertical CENTER, which varies hugely with a
  // glyph's own height (a cap-height "A" vs an x-height "n"/"a") — so every
  // letter's baseline floated off the intended curve by a different amount
  // (empirically ~50px / ~5mm at this emMm/pxPerMm, before the fix). Pinned
  // here directly: for two glyphs of very different heights ("A" cap-height,
  // "n" x-height), their baseline points must land at nearly the same
  // distance from the arc's circle center — not offset by a letter-dependent
  // amount. R and the circle center are computed the same way layoutText
  // derives them (exact measure pass, including kerning), not approximated.
  const TEXT = "AnAnAn";
  const emMm = 18, pxPerMm = 8, arcDeg = 90;
  const u2px = (emMm / font.unitsPerEm) * pxPerMm;
  let penX = 0, prev = null;
  for (const ch of Array.from(TEXT)) {
    const g = font.glyphs[ch];
    if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
    penX += g.adv; prev = ch;
  }
  const lineAdvPx = penX * u2px;
  const R = lineAdvPx / (Math.abs(arcDeg) * Math.PI / 180);
  const center = { x: 0, y: R }; // arcDeg>0 -> circle center at (0, +R), per satinfont.js

  const opts = { emMm, pxPerMm, spacingMm: 0.4, pullCompMm: 0.2, underlay: true, arcDeg };
  // "A" and "n" are different shapes with different per-glyph run counts, so
  // (unlike the all-"H" tests above) glyphGroups' equal-split assumption
  // doesn't hold. Determine each occurrence's run count from a solo layout of
  // that character, then partition the actual multi-glyph run array by that
  // per-character pattern (repeating "An" -> run-count pattern [nA, nN, nA, nN, ...]).
  const runsPerChar = { A: SF.layoutText(font, "A", { ...opts, arcDeg: 0 }).runs.length, n: SF.layoutText(font, "n", { ...opts, arcDeg: 0 }).runs.length };
  function splitByChars(lay, chars) {
    let i = 0; const groups = [];
    for (const ch of chars) { const n = runsPerChar[ch]; const pts = []; for (const r of lay.runs.slice(i, i + n)) for (const p of r.pts) pts.push(p); groups.push(pts); i += n; }
    return groups;
  }
  const chars = Array.from(TEXT);
  const groups = splitByChars(SF.layoutText(font, TEXT, opts), chars);
  const straightGroups = splitByChars(SF.layoutText(font, TEXT, { ...opts, arcDeg: 0 }), chars);
  const baseIdx = straightGroups.map((pts) => { let bi = 0, by = -Infinity; pts.forEach((p, i) => { if (p.y > by) { by = p.y; bi = i; } }); return bi; });
  const dists = groups.map((pts, k) => { const p = pts[baseIdx[k]]; return Math.hypot(p.x - center.x, p.y - center.y); });
  const spread = Math.max(...dists) - Math.min(...dists);
  assert.ok(spread < 10, `baseline radial spread across A/n should be small (was ~50px pre-fix), got ${spread.toFixed(2)}px`);
});

// Same contract, exercised through the FULL pipeline (buildLetteringDesign ->
// DST-space stitches), where the caller of this task actually consumes it.
// "HHH" is roughly 3 equal-width glyphs, so binning stitches into x-thirds of
// the design is a robust (if slightly imprecise at the glyph boundaries)
// proxy for "which glyph". DST convention: +y = up (see digitize.js's T()).
// Uses MEDIAN-y per bin, not a (min+max)/2 bounding-box center: post-fix, a
// non-descending glyph's ink runs almost entirely to ONE side of its own
// baseline, so at a large single-glyph rotation the bounding-box center can
// be pulled around by whichever edge of that lopsided ink sweeps furthest —
// the median of all sewn points in the bin is far less sensitive to that.
function thirdsMedianY(design) {
  const sew = design.stitches.filter((s) => s.type === "stitch");
  let minx = Infinity, maxx = -Infinity;
  for (const p of sew) { if (p.x < minx) minx = p.x; if (p.x > maxx) maxx = p.x; }
  const third = (maxx - minx) / 3;
  const bounds = [[minx, minx + third], [minx + third, minx + 2 * third], [minx + 2 * third, maxx + 1]];
  return bounds.map(([lo, hi]) => {
    const ys = sew.filter((p) => p.x >= lo && p.x < hi).map((p) => p.y).sort((a, b) => a - b);
    return ys[Math.floor(ys.length / 2)];
  });
}

test("buildLetteringDesign: arcDeg 120 arches UP in DST space (+y=up); -120 flips it", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 60 };
  const dPos = DG.buildLetteringDesign(font, "HHH", { ...base, arcDeg: 120 });
  const dNeg = DG.buildLetteringDesign(font, "HHH", { ...base, arcDeg: -120 });
  const [lP, mP, rP] = thirdsMedianY(dPos);
  // threshold in DST units (0.1mm) — comfortably below the gaps actually
  // observed for this font/arc combo (smallest observed margin ~13 units, on
  // the left side of the valley case: "HHH"'s kerning isn't perfectly
  // symmetric left/right, an existing property of this font/text combo
  // unrelated to the arc-baseline fix) — documents the "adjust to reality"
  // guidance rather than a razor-thin margin.
  assert.ok(mP > lP + 10, `arcDeg 120: middle (${mP}) should be above left (${lP}) in DST +y`);
  assert.ok(mP > rP + 10, `arcDeg 120: middle (${mP}) should be above right (${rP}) in DST +y`);
  const [lN, mN, rN] = thirdsMedianY(dNeg);
  assert.ok(mN < lN - 10, `arcDeg -120: middle (${mN}) should be below left (${lN}) in DST +y`);
  assert.ok(mN < rN - 10, `arcDeg -120: middle (${mN}) should be below right (${rN}) in DST +y`);
});

// ---- Multi-line ----

test("layoutText: '\\n' stacks a second line strictly BELOW the first (font-space y-down)", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: true };
  const layAB = SF.layoutText(font, "AB", opts);
  const layMulti = SF.layoutText(font, "AB\nCD", opts);
  const nLine0 = layAB.runs.length;
  const line0Runs = layMulti.runs.slice(0, nLine0);
  const line1Runs = layMulti.runs.slice(nLine0);
  assert.ok(line1Runs.length > 0, "second line produced runs");
  let maxY0 = -Infinity, minY1 = Infinity;
  for (const r of line0Runs) for (const p of r.pts) if (p.y > maxY0) maxY0 = p.y;
  for (const r of line1Runs) for (const p of r.pts) if (p.y < minY1) minY1 = p.y;
  assert.ok(maxY0 < minY1, `line 0 (max y ${maxY0}) must sit entirely above line 1 (min y ${minY1}) in font-space`);
});

test("buildLetteringDesign: 'AB\\nCD' is ~2x the height and a comparable width of single-line 'AB'", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const single = DG.buildLetteringDesign(font, "AB", base);
  const multi = DG.buildLetteringDesign(font, "AB\nCD", base);
  const ratio = multi.heightMM / single.heightMM;
  assert.ok(ratio > 1.4 && ratio < 2.6, `height ratio ${ratio} should be ~2x (+/-30%)`);
  const wRatio = multi.widthMM / single.widthMM;
  assert.ok(wRatio > 0.8 && wRatio < 1.2, `width ratio ${wRatio} should stay within 20% of single-line`);
});

test("digitize.buildLetteringDesign: arcDeg is threaded through both layoutText passes (probe + final)", () => {
  // A straight vs arced design must differ (arcDeg actually reached the
  // engine, not silently dropped by digitize.js's probe/final calls).
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 60 };
  const straight = DG.buildLetteringDesign(font, "HHH", base);
  const arced = DG.buildLetteringDesign(font, "HHH", { ...base, arcDeg: 120 });
  assert.notStrictEqual(straight.heightMM, arced.heightMM, "arcDeg must change the design's bbox height");
});

test("layoutText: slantDeg absent/0 is byte-identical to today's straight output; a nonzero value visibly leans a satin run's cross-stitches", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false };
  const lay0 = SF.layoutText(font, "H", opts);
  const layExplicit0 = SF.layoutText(font, "H", Object.assign({ slantDeg: 0 }, opts));
  assert.deepStrictEqual(layExplicit0, lay0);
  const layShear = SF.layoutText(font, "H", Object.assign({ slantDeg: 15 }, opts));
  // Same run/point COUNT (slant re-samples the same stations, doesn't add/remove any).
  assert.strictEqual(layShear.runs.length, lay0.runs.length);
  const totalPts0 = lay0.runs.reduce((s, r) => s + r.pts.length, 0);
  const totalPtsShear = layShear.runs.reduce((s, r) => s + r.pts.length, 0);
  assert.strictEqual(totalPtsShear, totalPts0);
  // But the actual point positions differ (the lean visibly changed the geometry).
  const flat0 = lay0.runs.flatMap((r) => r.pts);
  const flatShear = layShear.runs.flatMap((r) => r.pts);
  const anyDiffer = flat0.some((p, i) => Math.abs(p.x - flatShear[i].x) > 0.5 || Math.abs(p.y - flatShear[i].y) > 0.5);
  assert.ok(anyDiffer, "slantDeg:15 must produce visibly different point positions than slantDeg:0");
});
