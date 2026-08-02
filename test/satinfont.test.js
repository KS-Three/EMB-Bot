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

// NOTE (lettering underlay commit): this snapshot used to pass `underlay: true`
// — which was the same thing as `underlay: false`, because routeGlyph never
// read the option. Now that it does, `underlay: false` is the setting that
// carries the byte-identity guarantee, so that is what this pins. The values
// below are UNCHANGED from the pre-refactor capture. The `underlay: true`
// output is pinned separately, and deliberately, in the underlay tests further
// down this file.
test("layoutText: straight single-line 'AB' is byte-identical to the pre-refactor snapshot", () => {
  const opts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, letterSpacingMm: 0, underlay: false };
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

// Same note as the layoutText snapshot above: `underlay: false` is now what
// carries byte-identity, and 701 is the unchanged pre-refactor number. With
// underlay ON (the default) this same design is 855 stitches — see
// "underlay ladder: default-on is a real, intended output change" below.
test("buildLetteringDesign: straight 'AB' targetWidthMm 40 matches the pre-refactor snapshot", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40, underlay: false };
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
  // Expected angles derived from the documented arc contract (arc-tilt fix,
  // 2026-07-28): the line's INK span (rail x-extents, not the advance span —
  // advance carries invisible side bearings + a trailing letter-spacing gap
  // that used to tilt the whole arch) maps onto arcDeg, and each glyph is
  // positioned AND pivoted by its own ink center: phi = (inkCenter - inkMid)
  // / R with R = inkSpanPx / arcRad. For three identical glyphs the ink
  // centers are spaced exactly one advance apart, so this is symmetric by
  // construction — [-a, 0, +a] with the middle glyph upright at the apex.
  const H = font.glyphs["H"];
  let inkMin = Infinity, inkMax = -Infinity;
  for (const col of H.cols) {
    for (const p of col.railA) { if (p[0] < inkMin) inkMin = p[0]; if (p[0] > inkMax) inkMax = p[0]; }
    for (const p of col.railB) { if (p[0] < inkMin) inkMin = p[0]; if (p[0] > inkMax) inkMax = p[0]; }
  }
  const arcRad = 120 * Math.PI / 180;
  const spanU = (2 * H.adv + inkMax) - inkMin;       // ink of "HHH" in font units
  const inkMidU = (inkMin + 2 * H.adv + inkMax) / 2;
  const phiDeg = (k) => ((k * H.adv + (inkMin + inkMax) / 2 - inkMidU) / (spanU / arcRad)) * 180 / Math.PI;
  const expectedDeg = [phiDeg(0), phiDeg(1), phiDeg(2)];
  closeTo(expectedDeg[1], 0, 1e-9, "middle glyph must sit upright at the arc apex");
  closeTo(expectedDeg[0], -expectedDeg[2], 1e-9, "end glyphs must be symmetric about the apex");
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

// ---- Multi-line justification (align) ----

test("layoutText: align left/center/right position a short second line correctly against the widest", () => {
  const opts = (align) => ({ emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2, underlay: false, align });
  // "HHH" over "H": line 2 has 2 advances of slack.
  const minX = (lay, charIdx) => {
    let m = Infinity;
    for (const r of lay.runs) if (r.charIdx === charIdx) for (const p of r.pts) if (p.x < m) m = p.x;
    return m;
  };
  const text = "HHH\nH";
  const L = SF.layoutText(font, text, opts("left"));
  const C = SF.layoutText(font, text, opts("center"));
  const R = SF.layoutText(font, text, opts("right"));
  const D = SF.layoutText(font, text, opts(undefined)); // default = center
  // charIdx 4 is the lone H on line 2 ("HHH"=0,1,2, "\n"=3, "H"=4).
  const lLeft = minX(L, 4), lCenter = minX(C, 4), lRight = minX(R, 4);
  // left: flush with line 1s left edge (same min x as the first H).
  closeTo(lLeft, minX(L, 0), 1e-6, "left-aligned line 2 starts at line 1s left edge");
  // right: flush with line 1s right end -- shifted by exactly 2 advances.
  const advPx = font.glyphs["H"].adv * (18 / font.unitsPerEm) * 8;
  closeTo(lRight - lLeft, 2 * advPx, 1e-6, "right-aligned line 2 sits 2 advances right of left-aligned");
  // center: exactly halfway between.
  closeTo(lCenter, (lLeft + lRight) / 2, 1e-6, "centered line 2 is midway");
  // default is center (back-compat).
  closeTo(minX(D, 4), lCenter, 1e-6, "align absent = center");
});

// ---- Lettering parity round: two-line circular badge layout (circleLayout) ----
// Contract (documented in src/satinfont.js): the FIRST line arcs along the
// TOP of a circle, the LAST line arcs along the BOTTOM (upright, reading
// left-to-right — not upside-down), both baselines on ONE shared circle;
// middle lines (3+ line input) stack straight through the center; single-line
// input arcs the top only. R derives from |arcDeg| (default 180) applied to
// the widest arc'd line's ink span, or is pinned by { radiusMm }.

const circOpts = { emMm: 18, pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0, underlay: true };

// Ink x-span (design px) of one line of text, replicated from the documented
// ink contract (advance+kerning pen walk; rail x-extents) — the same
// derivation the arc tests above already use.
function lineInkSpanPx(lineText, emMm, pxPerMm) {
  const u2px = (emMm / font.unitsPerEm) * pxPerMm;
  let penX = 0, prev = null, minU = Infinity, maxU = -Infinity;
  for (const ch of Array.from(lineText)) {
    if (ch === " " || ch === "\t") { penX += (font.advSpace || font.advDefault); prev = null; continue; }
    const g = font.glyphs[ch] || font.glyphs[ch.toUpperCase()] || font.glyphs[ch.toLowerCase()];
    if (!g) { penX += font.advDefault; prev = null; continue; }
    if (prev != null && font.kerning) { const k = font.kerning[prev + ch]; if (k) penX += k; }
    let mn = Infinity, mx = -Infinity;
    for (const col of g.cols) for (const arr of [col.railA, col.railB]) for (const p of arr) { if (p[0] < mn) mn = p[0]; if (p[0] > mx) mx = p[0]; }
    if (penX + mn < minU) minU = penX + mn;
    if (penX + mx > maxU) maxU = penX + mx;
    penX += g.adv; prev = ch;
  }
  return (maxU - minU) * u2px;
}

// All of a layout's points grouped by source character index.
function groupPtsByChar(lay) {
  const m = new Map();
  for (const r of lay.runs) { if (!m.has(r.charIdx)) m.set(r.charIdx, []); for (const p of r.pts) m.get(r.charIdx).push(p); }
  return m;
}

// Recover the rigid motion (rotation + translation) that maps a glyph's
// straight-layout points onto its circle-layout points. routeGlyph's output
// is placement-independent, so index i is the SAME stitch in both layouts —
// two index-matched correspondences pin the motion exactly.
function rigidMotion(S, C) {
  const i = 0, j = Math.floor(S.length / 2);
  let delta = Math.atan2(C[j].y - C[i].y, C[j].x - C[i].x) - Math.atan2(S[j].y - S[i].y, S[j].x - S[i].x);
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;
  const cos = Math.cos(delta), sin = Math.sin(delta);
  return { deg: delta * 180 / Math.PI, cos, sin, tx: C[i].x - (S[i].x * cos - S[i].y * sin), ty: C[i].y - (S[i].x * sin + S[i].y * cos) };
}

test("layoutText: circleLayout falsy (absent/false/null) is byte-identical to today's multi-line output", () => {
  const a = SF.layoutText(font, "AB\nCD", circOpts);
  const b = SF.layoutText(font, "AB\nCD", { ...circOpts, circleLayout: false });
  const c = SF.layoutText(font, "AB\nCD", { ...circOpts, circleLayout: null });
  assert.deepStrictEqual(b, a);
  assert.deepStrictEqual(c, a);
});

test("layoutText: circleLayout on SINGLE-line text arcs that one line along the top — exactly a plain arcDeg layout at the derived span", () => {
  // Derived-R contract: R = inkSpan/arcRad, |arcDeg| default 180 — for one
  // line that is the plain-arc formula verbatim, so the outputs must be
  // IDENTICAL, not merely close.
  assert.deepStrictEqual(
    SF.layoutText(font, "KENT", { ...circOpts, circleLayout: true }),
    SF.layoutText(font, "KENT", { ...circOpts, arcDeg: 180 }));
  assert.deepStrictEqual(
    SF.layoutText(font, "KENT", { ...circOpts, circleLayout: true, arcDeg: 120 }),
    SF.layoutText(font, "KENT", { ...circOpts, arcDeg: 120 }));
  // arcDeg's SIGN is ignored in badge mode (top/bottom arch directions are
  // what define a badge): -120 behaves as 120, not as a valley.
  assert.deepStrictEqual(
    SF.layoutText(font, "KENT", { ...circOpts, circleLayout: true, arcDeg: -120 }),
    SF.layoutText(font, "KENT", { ...circOpts, arcDeg: 120 }));
});

test("layoutText: circleLayout 'SCHAEFER\\nEMBROIDERY' — line 1 upright on the top arc, line 2 upright on the bottom arc, concentric, baseline radial spread < 0.2mm", () => {
  const TEXT = "SCHAEFER\nEMBROIDERY";
  const straight = SF.layoutText(font, TEXT, circOpts);
  const circ = SF.layoutText(font, TEXT, { ...circOpts, circleLayout: true });
  // Derived geometry per the documented contract: R from the widest line's
  // ink span over 180 deg; shared center at (0, R) (top apex at y=0).
  const R = Math.max(lineInkSpanPx("SCHAEFER", 18, 8), lineInkSpanPx("EMBROIDERY", 18, 8)) / Math.PI;
  const center = { x: 0, y: R };
  const gs = groupPtsByChar(straight), gc = groupPtsByChar(circ);
  // "SCHAEFER"=0..7, "\n"=8, "EMBROIDERY"=9..18.
  const lineOf = (ci) => (ci <= 7 ? 0 : 1);
  // Shared baseline per line, measured in straight-layout space: the median
  // of per-glyph ink bottoms (pullCompMm 0 in circOpts, so stitch max-y IS
  // the rail bottom) — same median rule as the engine's baseline pivot.
  const bottoms = { 0: [], 1: [] };
  const bottomIdx = new Map(); // per glyph: index of its max-y point (for the side check below)
  for (const [ci, S] of gs) {
    let by = -Infinity, bi = 0;
    S.forEach((p, i) => { if (p.y > by) { by = p.y; bi = i; } });
    bottoms[lineOf(ci)].push(by);
    bottomIdx.set(ci, bi);
  }
  const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };
  const baseY = { 0: median(bottoms[0]), 1: median(bottoms[1]) };
  const perLine = { 0: [], 1: [] };
  for (const [ci, S] of gs) {
    const C = gc.get(ci);
    assert.strictEqual(C.length, S.length, `circle layout must not change point count (char ${ci})`);
    const m = rigidMotion(S, C);
    // Where did this glyph's stretch of the SHARED BASELINE go? Map two
    // points of the straight-space baseline line (y = baseY) through the
    // recovered motion; the perpendicular distance from the shared center
    // to that mapped line is the baseline's radial position — free of the
    // tangential offset a single stitch-point probe would carry.
    let mnx = Infinity, mxx = -Infinity;
    for (const p of S) { if (p.x < mnx) mnx = p.x; if (p.x > mxx) mxx = p.x; }
    const by = baseY[lineOf(ci)];
    const A = { x: mnx * m.cos - by * m.sin + m.tx, y: mnx * m.sin + by * m.cos + m.ty };
    const B = { x: mxx * m.cos - by * m.sin + m.tx, y: mxx * m.sin + by * m.cos + m.ty };
    const ex = B.x - A.x, ey = B.y - A.y, L = Math.hypot(ex, ey);
    const radial = Math.abs((center.x - A.x) * ey - (center.y - A.y) * ex) / L;
    perLine[lineOf(ci)].push({ ci, rot: m.deg, radial, meanX: (() => { let s = 0; for (const p of C) s += p.x; return s / C.length; })() });
  }
  // (a) Baselines sit ON the shared circle: every glyph of BOTH lines within
  // 0.1mm of R, i.e. total spread < 0.2mm (0.2mm = 1.6px at pxPerMm 8) —
  // one radius, one center: concentric by measurement, not assumption.
  for (const ln of [0, 1]) for (const g of perLine[ln]) {
    assert.ok(Math.abs(g.radial - R) < 0.8, `line ${ln} char ${g.ci}: baseline radial ${g.radial.toFixed(3)}px vs R ${R.toFixed(3)}px`);
  }
  for (const ln of [0, 1]) {
    const glyphs = perLine[ln].sort((a, b) => a.ci - b.ci);
    // (b) Upright: some glyph near the line's angular middle stands nearly
    // unrotated, and NO glyph is past 90 deg (nothing upside-down).
    assert.ok(Math.min(...glyphs.map((g) => Math.abs(g.rot))) < 15, `line ${ln}: middle glyph should stand upright`);
    for (const g of glyphs) assert.ok(Math.abs(g.rot) < 90, `line ${ln} char ${g.ci}: rotation ${g.rot.toFixed(1)} deg must stay below 90 (readable, not upside-down)`);
    // (c) Reads left-to-right: successive characters land at increasing x.
    for (let i = 1; i < glyphs.length; i++) assert.ok(glyphs[i].meanX > glyphs[i - 1].meanX, `line ${ln}: char ${glyphs[i].ci} must sit right of char ${glyphs[i - 1].ci}`);
    // (d) Tangent rotation follows the arc: the top line's glyph angles
    // INCREASE left-to-right (lean left before the apex, right after), the
    // bottom line's DECREASE (opposite curvature).
    for (let i = 1; i < glyphs.length; i++) {
      if (ln === 0) assert.ok(glyphs[i].rot > glyphs[i - 1].rot, `top line: rotation must increase left-to-right at char ${glyphs[i].ci}`);
      else assert.ok(glyphs[i].rot < glyphs[i - 1].rot, `bottom line: rotation must decrease left-to-right at char ${glyphs[i].ci}`);
    }
    // (e) Right side of the circle: the top line's upright glyph sits near
    // the circle's topmost point, the bottom line's near its bottommost
    // (y-down font space: top = small y).
    const mid = glyphs.reduce((a, b) => (Math.abs(a.rot) <= Math.abs(b.rot) ? a : b));
    const bp = gc.get(mid.ci)[bottomIdx.get(mid.ci)]; // that glyph's baseline stitch, circle layout
    if (ln === 0) assert.ok(bp.y < center.y - 0.9 * R, `top line's upright glyph baseline (y=${bp.y.toFixed(1)}) must sit near the circle top`);
    else assert.ok(bp.y > center.y + 0.9 * R, `bottom line's upright glyph baseline (y=${bp.y.toFixed(1)}) must sit near the circle bottom`);
  }
});

test("layoutText: circleLayout { radiusMm } pins the baseline circle radius regardless of text width", () => {
  const TEXT = "AB\nCD";
  const R = 40 * 8; // radiusMm 40 at pxPerMm 8 -> 320px; center (0, 320)
  const center = { x: 0, y: R };
  const straight = SF.layoutText(font, TEXT, circOpts);
  const circ = SF.layoutText(font, TEXT, { ...circOpts, circleLayout: { radiusMm: 40 } });
  const gs = groupPtsByChar(straight), gc = groupPtsByChar(circ);
  const lineOf = (ci) => (ci <= 1 ? 0 : 1);
  const bottoms = { 0: [], 1: [] };
  for (const [ci, S] of gs) { let by = -Infinity; for (const p of S) if (p.y > by) by = p.y; bottoms[lineOf(ci)].push(by); }
  const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s[s.length >> 1]; };
  const baseY = { 0: median(bottoms[0]), 1: median(bottoms[1]) };
  for (const [ci, S] of gs) {
    const m = rigidMotion(S, gc.get(ci));
    let mnx = Infinity, mxx = -Infinity;
    for (const p of S) { if (p.x < mnx) mnx = p.x; if (p.x > mxx) mxx = p.x; }
    const by = baseY[lineOf(ci)];
    const A = { x: mnx * m.cos - by * m.sin + m.tx, y: mnx * m.sin + by * m.cos + m.ty };
    const B = { x: mxx * m.cos - by * m.sin + m.tx, y: mxx * m.sin + by * m.cos + m.ty };
    const ex = B.x - A.x, ey = B.y - A.y, L = Math.hypot(ex, ey);
    const radial = Math.abs((center.x - A.x) * ey - (center.y - A.y) * ex) / L;
    assert.ok(Math.abs(radial - R) < 0.8, `char ${ci}: baseline radial ${radial.toFixed(3)}px must sit on the pinned 320px circle`);
  }
});

test("layoutText: circleLayout on 3+ lines arcs first and last, stacks the middle line straight and centered on the circle", () => {
  const TEXT = "AAA\nBB\nCCC"; // AAA=0..2, \n=3, BB=4..5, \n=6, CCC=7..9
  const straight = SF.layoutText(font, TEXT, circOpts);
  const circ = SF.layoutText(font, TEXT, { ...circOpts, circleLayout: true });
  const R = Math.max(lineInkSpanPx("AAA", 18, 8), lineInkSpanPx("CCC", 18, 8)) / Math.PI;
  const gs = groupPtsByChar(straight), gc = groupPtsByChar(circ);
  // Middle line "BB": pure TRANSLATE (no rotation), so index-matched segment
  // vectors must be identical between the straight and circle layouts.
  for (const ci of [4, 5]) {
    const S = gs.get(ci), C = gc.get(ci);
    assert.strictEqual(C.length, S.length);
    for (let i = 1; i < S.length; i++) {
      closeTo(C[i].x - C[i - 1].x, S[i].x - S[i - 1].x, 1e-9, `middle line char ${ci} seg ${i} dx`);
      closeTo(C[i].y - C[i - 1].y, S[i].y - S[i - 1].y, 1e-9, `middle line char ${ci} seg ${i} dy`);
    }
  }
  // ...its baseline sits AT the circle center height (single middle line:
  // vertically centered on the center; pullCompMm 0 makes stitch max-y the
  // exact rail bottom = baseline)...
  let maxY = -Infinity, mnx = Infinity, mxx = -Infinity;
  for (const ci of [4, 5]) for (const p of gc.get(ci)) { if (p.y > maxY) maxY = p.y; if (p.x < mnx) mnx = p.x; if (p.x > mxx) mxx = p.x; }
  closeTo(maxY, R, 1e-6, "middle line baseline must sit at the circle center height (cy = R)");
  // ...and its ink is centered on the circle's vertical axis.
  assert.ok(Math.abs((mnx + mxx) / 2) < 2, `middle line ink must center on x=0, got ${((mnx + mxx) / 2).toFixed(2)}`);
  // First and last lines still arc: their glyphs are genuinely rotated.
  const rotOf = (ci) => Math.abs(rigidMotion(gs.get(ci), gc.get(ci)).deg);
  assert.ok(rotOf(0) > 10, "first line's first glyph must be arc-rotated");
  assert.ok(rotOf(9) > 10, "last line's last glyph must be arc-rotated");
});

test("buildLetteringDesign: circleLayout absent/false is byte-identical; truthy reaches BOTH layout passes and yields a badge-shaped design", () => {
  const base = { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4 };
  const a = DG.buildLetteringDesign(font, "SCHAEFER\nEMBROIDERY", base);
  const b = DG.buildLetteringDesign(font, "SCHAEFER\nEMBROIDERY", { ...base, circleLayout: false });
  assert.deepStrictEqual(b, a);
  const c = DG.buildLetteringDesign(font, "SCHAEFER\nEMBROIDERY", { ...base, circleLayout: true });
  // Threading guard: the option must reach BOTH layoutText calls (probe +
  // final) — a straight probe with a circular final (or vice versa) would
  // mis-fit the badge badly and break the aspect assertion below.
  assert.notStrictEqual(c.heightMM, a.heightMM, "circleLayout must change the design bbox");
  const ratio = c.widthMM / c.heightMM;
  assert.ok(ratio > 0.8 && ratio < 1.4, `badge should be roughly circular, got aspect ${ratio.toFixed(2)}`);
});

// ---- STRUCTURAL UNDERLAY: Law 50's ladder ------------------------------
//
// Before this commit `layoutText` computed `doUnderlay` and passed it to
// `routeGlyph`, which never read it. Every satin letter this engine produced
// went down bare, and the app shipped an underlay switch that changed nothing.
// The runs tagged `kind: "underlay"` were Euler-walk TRAVEL between satin
// spans — they are now `kind: "underpath"`, and `"underlay"` means the real
// thing. These tests pin all of it.

// geneva_simple's cap/em is 0.600 (measured off its own H), so emMm*0.6 = cap.
const emForCap = (mm) => mm / 0.6;
const kinds = (lay) => lay.runs.reduce((m, r) => (m[r.kind] = (m[r.kind] || 0) + 1, m), {});
const UL_OPTS = { pxPerMm: 8, spacingMm: 0.4, pullCompMm: 0.2 };
// Rebuild a satin run's two rails: emitZigzag pushes (pA,pB) at even stations
// and (pB,pA) at odd ones, so the leading edge alternates.
function railsOfSatin(pts) {
  const A = [], B = [];
  for (let k = 0; 2 * k + 1 < pts.length; k++) {
    const a = pts[2 * k], b = pts[2 * k + 1];
    if (k % 2 === 0) { A.push(a); B.push(b); } else { A.push(b); B.push(a); }
  }
  return { A, B };
}
// Where a point sits across the nearest cross-stitch: 0 = on rail A, 1 = on
// rail B, 0.5 = the column axis. Plus its distance off that cross-line.
function acrossColumn(p, A, B) {
  let best = Infinity, bt = 0;
  for (let k = 0; k < A.length; k++) {
    const a = A[k], b = B[k];
    const ex = b.x - a.x, ey = b.y - a.y, L2 = ex * ex + ey * ey;
    let t = L2 > 1e-12 ? ((p.x - a.x) * ex + (p.y - a.y) * ey) / L2 : 0;
    const tc = t < 0 ? 0 : t > 1 ? 1 : t;
    const d = Math.hypot(p.x - (a.x + ex * tc), p.y - (a.y + ey * tc));
    if (d < best) { best = d; bt = tc; }
  }
  return { d: best, t: bt };
}

test("underlay ladder: a 4mm cap gets none, an 8mm cap gets a center run, a 12mm cap gets an edge run", () => {
  const at = (capMm) => SF.layoutText(font, "FRITSCH", { ...UL_OPTS, emMm: emForCap(capMm), underlay: true });
  const small = at(4), mid = at(8), big = at(12);
  closeTo(small.cap.finalMm, 4, 0.01, "measured cap at the small size");
  closeTo(mid.cap.finalMm, 8, 0.01, "measured cap at the mid size");
  closeTo(big.cap.finalMm, 12, 0.01, "measured cap at the large size");
  assert.strictEqual(small.cap.underlay, null, "under 5mm: lettering under 5mm should not have underlay");
  assert.strictEqual(mid.cap.underlay, "center", "5-10mm: center run");
  assert.strictEqual(big.cap.underlay, "edge", "over 10mm: edge run");
  assert.strictEqual(kinds(small).underlay, undefined, "a 4mm cap emits ZERO underlay runs");
  assert.ok(kinds(mid).underlay > 0, "an 8mm cap emits underlay runs");
  assert.ok(kinds(big).underlay > 0, "a 12mm cap emits underlay runs");
  // the boundaries themselves
  assert.strictEqual(SF.underlayModeForCapMm(4.99), null);
  assert.strictEqual(SF.underlayModeForCapMm(5), "center");
  assert.strictEqual(SF.underlayModeForCapMm(10), "center");
  assert.strictEqual(SF.underlayModeForCapMm(10.01), "edge");
});

test("underlay ladder: center rides the column axis, edge rides both rails at 0.4mm inset", () => {
  for (const [capMm, mode] of [[8, "center"], [12, "edge"]]) {
    const lay = SF.layoutText(font, "FRITSCH", { ...UL_OPTS, emMm: emForCap(capMm), underlay: true });
    assert.strictEqual(lay.cap.underlay, mode);
    const ts = [];
    for (let i = 0; i < lay.runs.length; i++) {
      if (lay.runs[i].kind !== "underlay") continue;
      const sat = lay.runs[i + 1];
      const { A, B } = railsOfSatin(sat.pts);
      if (A.length < 2) continue;
      for (const p of lay.runs[i].pts) ts.push(acrossColumn(p, A, B).t);
    }
    assert.ok(ts.length > 50, "enough sample points to be meaningful");
    if (mode === "center") {
      // 0.06 rather than 0.5-exact: `t` is measured against the NEAREST satin
      // cross-stitch, and on a curved column that cross-line sits at a
      // slightly different station than the centerline sample. Measured worst
      // case across this string is 0.039 — an order below the edge run's 0.36.
      for (const t of ts) assert.ok(Math.abs(t - 0.5) < 0.06, `center run should ride the axis, got t=${t.toFixed(3)}`);
    } else {
      const nearRails = ts.filter((t) => t < 0.35 || t > 0.65).length;
      assert.ok(nearRails / ts.length > 0.8, `edge run should ride the rails, only ${(100 * nearRails / ts.length).toFixed(0)}% did`);
      assert.ok(ts.some((t) => t < 0.35) && ts.some((t) => t > 0.65), "and reach BOTH rails");
    }
  }
});

test("underlay lies INSIDE its column and is sewn BEFORE the satin that covers it", () => {
  const lay = SF.layoutText(font, "Hamburgefonstiv Fritsch", { ...UL_OPTS, emMm: emForCap(12), underlay: true });
  let checked = 0;
  for (let i = 0; i < lay.runs.length; i++) {
    const r = lay.runs[i];
    if (r.kind !== "underlay") continue;
    const sat = lay.runs[i + 1];
    assert.ok(sat && sat.kind === "satin", `underlay run ${i} must be immediately followed by its satin`);
    assert.strictEqual(r.charIdx, sat.charIdx, "and belong to the same source glyph");
    const { A, B } = railsOfSatin(sat.pts);
    if (A.length < 2) continue;
    for (const p of r.pts) {
      const { d, t } = acrossColumn(p, A, B);
      checked++;
      // t strictly between the rails, and sitting ON the cross-line family
      assert.ok(t > 0.001 && t < 0.999, `underlay point escaped its rails (t=${t})`);
      assert.ok(d / UL_OPTS.pxPerMm < 0.45, `underlay point is ${(d / UL_OPTS.pxPerMm).toFixed(3)}mm off its own column`);
    }
  }
  assert.ok(checked > 500, `expected a real sample, checked ${checked}`);
  // most satin spans should be underlaid (the exceptions are spans too short
  // to carry even one minimum-length stitch)
  const sats = lay.runs.filter((r) => r.kind === "satin").length;
  const unders = lay.runs.filter((r) => r.kind === "underlay").length;
  assert.ok(unders / sats > 0.8, `most satin spans should be underlaid, got ${unders}/${sats}`);
});

test("every underlay stitch clears the 0.5mm minimum and the 12.1mm DST record ceiling", () => {
  const names = ["geneva_simple", "emilio_20_bold", "chicken_scratch", "mam_script"];
  let n = 0, longest = 0;
  for (const name of names) {
    const f = JSON.parse(fs.readFileSync(`${__dirname}/../src/fonts/${name}.json`, "utf8"));
    for (const emMm of [12, 18, 30, 60]) {
      const lay = SF.layoutText(f, "Hamburgefonstiv 8@", { ...UL_OPTS, emMm, underlay: true });
      for (const r of lay.runs) {
        if (r.kind !== "underlay") continue;
        for (let k = 0; k + 1 < r.pts.length; k++) {
          const L = Math.hypot(r.pts[k + 1].x - r.pts[k].x, r.pts[k + 1].y - r.pts[k].y) / UL_OPTS.pxPerMm;
          n++; if (L > longest) longest = L;
          assert.ok(L >= 0.5 - 1e-9, `${name}@${emMm}: ${L.toFixed(4)}mm is under the 0.5mm floor (Law 51)`);
          assert.ok(L <= 12.1, `${name}@${emMm}: ${L.toFixed(4)}mm exceeds the DST record ceiling`);
        }
      }
    }
  }
  assert.ok(n > 10000, `expected a real corpus sweep, measured ${n} stitches`);
  assert.ok(longest <= 4, `underlay should also respect the 4mm max stitch, longest was ${longest.toFixed(3)}mm`);
});

test("cap height is MEASURED from the font's own H, not assumed equal to the em (Law 46)", () => {
  const emilio = JSON.parse(fs.readFileSync(`${__dirname}/../src/fonts/emilio_20_bold.json`, "utf8"));
  const gen = SF.capHeightMm(font, 18), emi = SF.capHeightMm(emilio, 18);
  assert.strictEqual(gen.ref, "H"); assert.strictEqual(gen.proxy, false);
  assert.strictEqual(emi.ref, "H"); assert.strictEqual(emi.proxy, false);
  closeTo(gen.mm, 10.8, 0.05, "geneva_simple cap/em is 0.600");
  closeTo(emi.mm, 16.47, 0.05, "emilio_20_bold cap/em is 0.915");
  // Same nominal em, different real cap -> DIFFERENT rungs. Gating on emMm
  // would have put both of these on the same one.
  const a = SF.layoutText(font, "AB", { ...UL_OPTS, emMm: 15, underlay: true });
  const b = SF.layoutText(emilio, "AB", { ...UL_OPTS, emMm: 15, underlay: true });
  closeTo(a.cap.finalMm, 9.0, 0.05); closeTo(b.cap.finalMm, 13.7, 0.05);
  assert.strictEqual(a.cap.underlay, "center");
  assert.strictEqual(b.cap.underlay, "edge");
});

test("fitScale moves the ladder, because the ladder is keyed to FINAL SEWN cap height", () => {
  const em = emForCap(12);       // 12mm cap at fitScale 1 -> edge
  const opts = { ...UL_OPTS, emMm: em, underlay: true };
  assert.strictEqual(SF.layoutText(font, "AB", opts).cap.underlay, "edge");
  assert.strictEqual(SF.layoutText(font, "AB", { ...opts, fitScale: 0.7 }).cap.underlay, "center"); // 8.4mm
  assert.strictEqual(SF.layoutText(font, "AB", { ...opts, fitScale: 0.3 }).cap.underlay, null);     // 3.6mm
  // and the ladder's own mm constants scale with it, so the 3mm step lands at
  // 3mm on the GARMENT rather than 3mm in layout space
  const lay = SF.layoutText(font, "AB", { ...opts, fitScale: 0.5 });
  const u = lay.runs.find((r) => r.kind === "underlay");
  let longest = 0;
  for (let k = 0; k + 1 < u.pts.length; k++) longest = Math.max(longest, Math.hypot(u.pts[k + 1].x - u.pts[k].x, u.pts[k + 1].y - u.pts[k].y));
  const finalMm = longest * 0.5 / UL_OPTS.pxPerMm;
  assert.ok(finalMm <= 3 + 1e-6, `final sewn stitch should be <=3mm, got ${finalMm.toFixed(3)}mm`);
});

test("underlay:false emits ZERO underlay runs at EVERY size, and travel is tagged underpath", () => {
  for (const capMm of [3, 4, 6, 8, 12, 20, 40]) {
    const lay = SF.layoutText(font, "Fritsch Stitches", { ...UL_OPTS, emMm: emForCap(capMm), underlay: false });
    const k = kinds(lay);
    assert.strictEqual(k.underlay, undefined, `cap ${capMm}mm: underlay:false must emit no underlay`);
    assert.strictEqual(lay.cap.underlay, null);
    assert.ok(k.satin > 0, "but still emits satin");
    assert.ok(k.underpath > 0, "and still emits needle-down travel, now tagged underpath");
    for (const r of lay.runs) assert.ok(r.kind === "satin" || r.kind === "underpath", `unexpected kind ${r.kind}`);
  }
});

test("underlay can be forced to a rung, overriding the ladder", () => {
  const at = (u) => SF.layoutText(font, "AB", { ...UL_OPTS, emMm: emForCap(4), underlay: u });
  assert.strictEqual(at(true).cap.underlay, null, "the ladder says none at a 4mm cap");
  assert.strictEqual(at("none").cap.underlay, null);
  assert.strictEqual(at("center").cap.underlay, "center", "but it can be forced on");
  assert.strictEqual(at("edge").cap.underlay, "edge");
  assert.ok(kinds(at("center")).underlay > 0);
  assert.deepStrictEqual(at("none").runs, at(false).runs, "none and false are the same output");
});

test("underlay ladder: default-on is a real, intended output change — pinned deliberately", () => {
  // The companion to the two `underlay: false` byte-identity snapshots at the
  // top of this file. `underlay` has ALWAYS defaulted to true and has always
  // done nothing; now that it works, the DEFAULT output of every lettering
  // design changes. These are the new numbers for the same AB design.
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const off = DG.buildLetteringDesign(font, "AB", { ...base, underlay: false });
  const on = DG.buildLetteringDesign(font, "AB", base);
  assert.strictEqual(off.stitchCount, 701, "underlay off: the unchanged pre-fix number");
  assert.strictEqual(on.stitchCount, 855, "underlay on (the default): +154 stitches, +22.0%");
  assert.strictEqual(on._debug.nTrims, off._debug.nTrims, "underlay must not add a single trim");
  closeTo(on.widthMM, off.widthMM, 1e-9, "and must not move the design bbox");
  closeTo(on.heightMM, off.heightMM, 1e-9, "or its height");
  assert.deepStrictEqual(on.colors, off.colors, "or its color sequence");
  // The ladder ran on the FINAL sewn size, not the nominal em. At 40mm wide
  // this AB fits to a 22.2mm cap (edge rung); squeeze the SAME nominal emMm
  // down to 8mm wide and the cap lands at 4.4mm, under the floor, and the
  // default-on design becomes byte-identical to the default-off one again.
  const tinyOn = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 8 });
  const tinyOff = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 8, underlay: false });
  assert.deepStrictEqual(tinyOn, tinyOff, "an 8mm-wide AB fits to a 4.4mm cap — under the floor, so no underlay at all");
  assert.strictEqual(tinyOn.stitchCount, 189);
});
