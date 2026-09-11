// Wide columns in the browser lettering engine — quality review item 10.
//
// The defect, in one sentence: the engine emits satin crosses no machine can
// sew. DOCTRINE 2026-09-07 measured it on the encoder side and left the
// engine side open — "a 17.9 mm satin crossing is unsewable however it is
// encoded, and what to do about it ... is a look-and-fabric decision".
//
// This file pins the two mechanisms that answer it (both DEFAULT OFF — the
// answer is Kent's, the machinery is not), the units bug the measurement
// turned up on the way, and the one trap the port introduces.
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const satinplay = require("../src/satinplay.js");
global.window = global;
const DG = require("../src/digitize.js");
const SF = require("../src/satinfont.js");
const fb = require("../src/fontbin.js");
const G = require("../src/garments.js");

const BIN = path.join(__dirname, "..", "src", "fonts", "bin");
const font = JSON.parse(fs.readFileSync(__dirname + "/fixtures/fonts/geneva_simple.json", "utf8"));

// A straight column `lenPx` long and `widPx` wide, in the y direction.
function straightColumn(lenPx, widPx) {
  const A = [], B = [];
  for (let i = 0; i <= 20; i++) { A.push({ x: (i * lenPx) / 20, y: 0 }); B.push({ x: (i * lenPx) / 20, y: widPx }); }
  return satinplay.columnGeom(A, B, [], 12);
}
const maxLegMm = (pts, pxPerMm) => {
  let m = 0;
  for (let i = 0; i + 1 < pts.length; i++) m = Math.max(m, Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y) / pxPerMm);
  return m;
};
// Sewn segments past one DST record. A record carries +-121 units PER AXIS,
// so the test is on the axis delta, not the segment's length — the rule that
// reproduces DOCTRINE's own count (see `the census reproduces DOCTRINE` below).
function overRecord(design) {
  let n = 0, worstAx = 0, prev = null, pws = false;
  for (const s of design.stitches) {
    if (s.type === "end") break;
    if (s.type === "stitch") {
      if (prev && pws) {
        const ax = Math.max(Math.abs(s.x - prev.x), Math.abs(s.y - prev.y)) / 10;
        if (ax > 12.1) n += 1;
        if (ax > worstAx) worstAx = ax;
      }
      prev = s; pws = true;
    } else { if (s.type !== "color") prev = s; pws = false; }
  }
  return { n, worstAx };
}

// ---- splitLeg: the mechanism, ported from stage6_satin._split_points -------

test("splitLeg leaves a leg at or under the threshold alone", () => {
  const a = { x: 0, y: 0 }, b = { x: 0, y: 40 };
  assert.deepStrictEqual(satinplay.splitLeg(a, b, 0, 40, 24), [], "exactly at the threshold is not over it");
  assert.deepStrictEqual(satinplay.splitLeg(a, b, 0, 50, 24), []);
  assert.deepStrictEqual(satinplay.splitLeg(a, a, 0, 1, 24), [], "a degenerate leg has nothing to split");
  assert.deepStrictEqual(satinplay.splitLeg(a, b, 0, 0, 24), [], "no threshold, no split — the default-off path");
});

test("splitLeg puts k-1 penetrations on the leg, at ceil(len / segment) segments", () => {
  const a = { x: 0, y: 0 }, b = { x: 0, y: 100 };
  // 100 / 24 -> k = 5 -> four interior points.
  assert.strictEqual(satinplay.splitLeg(a, b, 0, 40, 24).length, 4);
  // 50 / 24 -> k = 3 -> two.
  assert.strictEqual(satinplay.splitLeg(a, { x: 0, y: 50 }, 0, 40, 24).length, 2);
});

test("splitLeg's points are exact lerps, which is what makes them removable", () => {
  const a = { x: 3, y: -7 }, b = { x: 40, y: 51 };
  for (const q of satinplay.splitLeg(a, b, 1, 10, 12)) {
    const cross = (q.x - a.x) * (b.y - a.y) - (q.y - a.y) * (b.x - a.x);
    assert.ok(Math.abs(cross) < 1e-9, `off the segment by ${cross}`);
    const t = ((q.x - a.x) * (b.x - a.x) + (q.y - a.y) * (b.y - a.y)) /
      ((b.x - a.x) ** 2 + (b.y - a.y) ** 2);
    assert.ok(t > 0 && t < 1, `t=${t} is not strictly interior`);
  }
});

test("splitLeg's stagger has period 4 and shifts +-0.23 of one segment", () => {
  const a = { x: 0, y: 0 }, b = { x: 0, y: 100 };
  const at = (st) => satinplay.splitLeg(a, b, st, 40, 50).map((q) => q.y / 100);
  // k = 2 at a 50-unit segment, so one interior point per station: the
  // corpus's own k=2 case, offset |t - 0.5| = 0.23 / 2 = 0.115 of the cross.
  const f = [0, 1, 2, 3, 4, 5].map((st) => at(st)[0]);
  assert.deepStrictEqual(f.map((x) => +x.toFixed(4)),
    [0.615, 0.385, 0.5383, 0.4617, 0.615, 0.385], "the 4-station wave, repeating");
  assert.ok(Math.abs(Math.abs(f[0] - 0.5) - 0.115) < 1e-9, "the corpus's median k=2 offset");
  // Negative station indices are legal (nothing generates them today, but a
  // caller counting backwards must not index out of the wave and get NaN).
  assert.ok(isFinite(at(-1)[0]));
});

// ---- emitZigzag with the split on --------------------------------------

test("a split cross has no leg longer than one segment, and the whole stream reverses", () => {
  const geom = straightColumn(40, 60);          // 5 mm long, 7.5 mm wide @ 8 px/mm
  const off = satinplay.satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 8 });
  const on = satinplay.satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 8, splitAboveMm: 5.0 });
  assert.ok(maxLegMm(off, 8) > 7, `unsplit column should throw its full width, got ${maxLegMm(off, 8)}`);
  assert.ok(maxLegMm(on, 8) <= 3.0 * 1.24, `split legs must stay near the segment, got ${maxLegMm(on, 8)}`);
  assert.deepStrictEqual(satinplay.stripSplits(on), off,
    "stripSplits is the exact inverse — an instrument reading rail pairs calls it first");
});

test("THE PORT'S TRAP: the stagger must walk, and it does not if you split in traversal order", () => {
  // This module alternates the leading rail per station, so splitting the
  // cross lead->trail makes the direction flip cancel the wave's sign flip
  // and every station puts its penetrations at the SAME fractions — the
  // trenched line of holes the stagger exists to prevent. Measured when the
  // naive port was written: stations 0 and 1 both landed at 24.6 and 44.6 px
  // of a 60 px cross. The cross is split in the column's own A->B frame and
  // reversed for traversal instead.
  const geom = straightColumn(40, 60);
  const pts = satinplay.satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 8, splitAboveMm: 5.0 });
  const byStation = new Map();
  for (const q of pts) {
    const f = q.y / 60;
    if (f <= 1e-9 || f >= 1 - 1e-9) continue;     // rail penetrations, not split ones
    const k = q.x.toFixed(3);
    if (!byStation.has(k)) byStation.set(k, []);
    byStation.get(k).push(+f.toFixed(3));
  }
  const combs = [...byStation.values()].map((v) => JSON.stringify(v.sort((a, b) => a - b)));
  assert.ok(combs.length >= 4, "need at least one full wave period to judge");
  assert.notStrictEqual(combs[0], combs[1], "consecutive stations must not share a comb");
  assert.strictEqual(combs[0], combs[4], "and the wave must close after 4 stations");
});

// ---- the WIDE class and the fill fallback -------------------------------

test("splitByCrossFloor classes a past-ceiling stretch wide, and leaves a narrow one alone", () => {
  const wide = straightColumn(400, 60), narrow = straightColumn(400, 12);
  const opts = { spacingMm: 0.4, pxPerMm: 8, maxCrossMm: 3.0 };
  assert.deepStrictEqual(satinplay.splitByCrossFloor(wide, 0, 1, opts), [{ f0: 0, f1: 1, thin: false, wide: true }]);
  assert.deepStrictEqual(satinplay.splitByCrossFloor(narrow, 0, 1, opts), [{ f0: 0, f1: 1, thin: false, wide: false }]);
  assert.deepStrictEqual(satinplay.splitByCrossFloor(wide, 0, 1, { spacingMm: 0.4, pxPerMm: 8 }),
    [{ f0: 0, f1: 1, thin: false, wide: false }], "no ceiling asked for, no wide class");
});

test("a column that widens past the ceiling halfway splits into satin then fill", () => {
  const A = [], B = [];
  for (let i = 0; i <= 200; i++) { const w = i < 100 ? 12 : 60; A.push({ x: -w / 2, y: i * 2 }); B.push({ x: w / 2, y: i * 2 }); }
  const geom = satinplay.columnGeom(A, B, [], 12);
  const segs = satinplay.splitByCrossFloor(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 8, maxCrossMm: 3.0 });
  assert.strictEqual(segs.length, 2, JSON.stringify(segs));
  assert.strictEqual(segs[0].wide, false);
  assert.strictEqual(segs[1].wide, true);
  assert.strictEqual(segs[0].f1, segs[1].f0, "segments must tile the span");
  assert.ok(Math.abs(segs[0].f1 - 0.5) < 0.03, `boundary at ${segs[0].f1}, expected ~0.5`);
});

test("fillFromGeom tatamis the stretch at the caller's pitch, within its own rails", () => {
  const geom = straightColumn(400, 60);          // 50 x 7.5 mm @ 8 px/mm
  const segs = satinplay.fillFromGeom(geom, 0, 1, { pxPerMm: 8, fillRowMm: 0.15, fillStitchMm: 3.0 });
  assert.ok(segs.length >= 1, "a straight column fills in one piece");
  const pts = segs.flat();
  assert.ok(pts.length > 100, `expected a real fill, got ${pts.length} points`);
  for (const s of segs) assert.ok(maxLegMm(s, 8) <= 3.0 + 1e-6, `a fill stitch ran ${maxLegMm(s, 8)} mm`);
  for (const q of pts) {
    assert.ok(q.x >= -1e-6 && q.x <= 400 + 1e-6, `x ${q.x} outside the rails`);
    assert.ok(q.y >= -1e-6 && q.y <= 60 + 1e-6, `y ${q.y} outside the rails`);
  }
  assert.deepStrictEqual(satinplay.fillFromGeom(geom, 0, 1, { pxPerMm: 8, fillRowMm: 0, fillStitchMm: 3 }), [],
    "no pitch, no fill — the default-off path");
});

// ---- the units bug the measurement turned up ---------------------------

test("the Euler-walk underpath steps 2 mm ON THE FABRIC at any fit scale", () => {
  // It used to step 2 mm in the LAYOUT frame, i.e. 2 mm x the fit scale on
  // the fabric, while the underlay pitch three lines away in the same
  // function was correctly divided. Checked at scales an order of magnitude
  // apart, because ONE scale cannot tell a scaled pitch from a fixed one —
  // at fitScale 1 the bug is invisible.
  //
  // Measured on the underpath runs themselves, not on the design's longest
  // stitch: at 300 mm this font's satin crosses are 31 mm and would mask the
  // thing under test. That the crosses are that long is the OTHER half of
  // item 10, and the two knobs above are what answer it.
  const worstUnderpathMm = (fitScale) => {
    const lay = SF.layoutText(font, "AB", {
      emMm: 18, pxPerMm: 8, spacingMm: 0.4 / fitScale, pullCompMm: 0.2 / fitScale,
      fitScale, underlay: false, crossFloor: true });
    let m = 0;
    for (const r of lay.runs) {
      if (r.kind !== "underpath") continue;
      for (let i = 0; i + 1 < r.pts.length; i++) {
        m = Math.max(m, (Math.hypot(r.pts[i + 1].x - r.pts[i].x, r.pts[i + 1].y - r.pts[i].y) / 8) * fitScale);
      }
    }
    return m;
  };
  const scales = [0.5, 1, 8.47];
  const seen = scales.map(worstUnderpathMm);
  for (const [i, mm] of seen.entries()) {
    assert.ok(mm > 0, `no underpath at fitScale ${scales[i]} — the test would be vacuous`);
    // 2.05, not 2.00: `centerFromGeom` resamples to a POINT count, so the
    // realised pitch is len/(n-1) and overshoots the target by up to one
    // segment's worth on a short walk. Pre-existing, a few percent, and not
    // this change's to move.
    assert.ok(mm <= 2.1, `underpath stepped ${mm} mm on the fabric at fitScale ${scales[i]}`);
  }
  // The invariant the bug actually broke, stated as one: the pitch must not
  // TRACK the scale. Measured on this fixture against the pre-change tree,
  // these three read 1.02, 2.05 and 17.35 mm; they now read 2.05, 2.05, 2.04.
  assert.ok(Math.max(...seen) / Math.min(...seen) < 1.1,
    `underpath pitch tracks the fit scale: ${seen.map((x) => x.toFixed(2)).join(", ")} mm at ${scales.join(", ")}x`);
});

// ---- end to end, on the design DOCTRINE measured ------------------------

const MANGA = path.join(BIN, "manga_impact.embf");

test("the census reproduces DOCTRINE's own numbers, so the rest of this file means something", (t) => {
  if (!fs.existsSync(MANGA)) { t.skip("manga_impact.embf not built"); return; }
  const f = fb.decodeFontBin(fs.readFileSync(MANGA));
  // `splitSatin: false` because DOCTRINE's row was measured on the engine
  // before any of this; the split went default ON the same day this landed.
  const d = DG.buildLetteringDesign(f, "AB", {
    garment: G.getGarment("full_back"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25],
    pullCompMm: 0.2, splitSatin: false });
  // DOCTRINE 2026-09-07: "a two-letter monogram on a Full Back gives 1,933 of
  // 5,828, worst 44.9 mm", on a design it records as 304.9 x 146.2 mm. The
  // stitch count moved by 3 with the underpath units fix (5,830 -> 5,863) and
  // three of the over-record segments WERE those underpath steps, so 1,933 is
  // now 1,930 — a difference this test states rather than hides.
  closeTo(d.widthMM, 304.9, 0.1, "the design DOCTRINE measured");
  closeTo(d.heightMM, 146.2, 0.1, "…at the size it measured it");
  const { n, worstAx } = overRecord(d);
  assert.strictEqual(n, 1930, "DOCTRINE's 1,933, less the three underpath steps now fixed");
  closeTo(worstAx, 44.9, 0.05, "DOCTRINE's worst axis delta, unchanged — it is a satin cross");
});

test("split satin — the DEFAULT since Kent's ruling — takes that design to ZERO unsewable segments", (t) => {
  if (!fs.existsSync(MANGA)) { t.skip("manga_impact.embf not built"); return; }
  const f = fb.decodeFontBin(fs.readFileSync(MANGA));
  const base = { garment: G.getGarment("full_back"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25], pullCompMm: 0.2 };
  const on = DG.buildLetteringDesign(f, "AB", base);
  const { n, worstAx } = overRecord(on);
  assert.strictEqual(n, 0, "not one sewn segment past a DST record");
  assert.ok(worstAx <= 4.5, `worst sewn segment ${worstAx} mm — the split segment is 3.0`);
  assert.ok(on.lettering.splitPenetrations > 20000, "and it says how many penetrations that cost");
});

test("the wide-column fill takes it to zero too, at a very different price", (t) => {
  if (!fs.existsSync(MANGA)) { t.skip("manga_impact.embf not built"); return; }
  const f = fb.decodeFontBin(fs.readFileSync(MANGA));
  const base = { garment: G.getGarment("full_back"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25], pullCompMm: 0.2 };
  const off = DG.buildLetteringDesign(f, "AB", { ...base, splitSatin: false });
  const split = DG.buildLetteringDesign(f, "AB", base);   // split is the default
  const fill = DG.buildLetteringDesign(f, "AB", { ...base, splitSatin: false, wideColumnFill: true });
  assert.strictEqual(overRecord(fill).n, 0);
  assert.ok(fill.lettering.wideSpans > 0, "and it says how many stretches it re-routed");
  // The two are NOT the same trade. Pinned as an ordering, not as counts, so
  // the file does not go stale every time a glyph moves.
  assert.ok(split.stitchCount > off.stitchCount * 3, "the split multiplies penetrations");
  assert.ok(fill.stitchCount > split.stitchCount * 2, "and the fill multiplies them again");
  assert.ok(fill._debug.nTrims > off._debug.nTrims, "a fill on a curved column costs trims the satin did not");
});

test("a RUN font's authored pitch is a length on the fabric, not on the layout", (t) => {
  // The third source of unsewable stitches, and the one neither knob above
  // touches: `routeRuns` measured the font's authored `lenMm` in the layout
  // frame. 18 of the 85 shipped fonts are runs-only and were all affected.
  //
  // western_light's "A" at left chest is the clearest case: it sewed 92
  // stitches, 66 of which were past a DST record, worst 22.5 mm — a design
  // laying about a sixth of the stitches it needed, at seven times the pitch
  // its own font asked for.
  const p = path.join(BIN, "western_light.embf");
  if (!fs.existsSync(p)) { t.skip("western_light.embf not built"); return; }
  const f = fb.decodeFontBin(fs.readFileSync(p));
  const d = DG.buildLetteringDesign(f, "A", {
    garment: G.getGarment("left_chest"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25], pullCompMm: 0.2 });
  const { n, worstAx } = overRecord(d);
  assert.strictEqual(n, 0, "not one sewn segment past a DST record");
  assert.ok(worstAx <= 4.1, `worst sewn segment ${worstAx} mm`);
  assert.strictEqual(d.stitchCount, 560, "92 before the frame was fixed");
});

test("and it is wrong shrinking too, which is what makes it a units bug", () => {
  // Law 51's floor is the other end of the same line. A run font scaled DOWN
  // used to sew its authored pitch TIMES the scale, straight under the needle
  // minimum. Pinned as a bound on the realised pitch at two scales rather
  // than as counts, because the point is that the pitch does not move.
  const runFont = {
    unitsPerEm: 100, leading: 120,
    glyphs: { A: { adv: 100, cols: [], runs: [{ pts: [[0, 0], [100, 0]], lenMm: 1.0 }] } },
  };
  const pitch = (targetWidthMm) => {
    const d = DG.buildLetteringDesign(runFont, "A", {
      garment: { widthIn: 14, heightIn: 14 }, pxPerMm: 8, targetWidthMm, underlay: false });
    const sew = d.stitches.filter((x) => x.type === "stitch");
    let m = 0;
    for (let i = 1; i < sew.length; i++) m = Math.max(m, Math.hypot(sew[i].x - sew[i - 1].x, sew[i].y - sew[i - 1].y) / 10);
    return m;
  };
  const small = pitch(10), large = pitch(200);
  assert.ok(small > 0 && large > 0, "both arms must actually sew");
  for (const [mm, label] of [[small, "10 mm"], [large, "200 mm"]]) {
    assert.ok(mm >= 0.5, `${label}: pitch ${mm} mm is under Law 51's floor`);
    assert.ok(mm <= 1.05, `${label}: pitch ${mm} mm is over the font's authored 1.0`);
  }
});

test("a wide stretch's fill pieces are reached NEEDLE-UP, in either traversal direction", (t) => {
  // The pieces of one wide stretch are disconnected by construction: the gap
  // between them is exactly the travel `tatamiFill` refused to sew. Flagging
  // them where they are made and then reversing the span puts the flags on
  // the wrong pieces, so the walk sews a needle-down connector straight
  // across the gap. Measured against that version: `alchemy` at 8x laid one
  // such connector **11.8 mm** long over bare fabric and `excalibur_KOR` two
  // more. The flags are decided after the reversal instead.
  const p = path.join(BIN, "alchemy.embf");
  if (!fs.existsSync(p)) { t.skip("alchemy.embf not built"); return; }
  const f = fb.decodeFontBin(fs.readFileSync(p));
  const fitScale = 8;
  const lay = SF.layoutText(f, "AB", {
    emMm: 18, pxPerMm: 8, spacingMm: 0.4 / fitScale, pullCompMm: 0.2 / fitScale,
    fitScale, underlay: true, crossFloor: true, wideColumnFill: true });
  let pairs = 0;
  for (let i = 1; i < lay.runs.length; i++) {
    const a = lay.runs[i - 1], b = lay.runs[i];
    if (a.kind !== "fill" || b.kind !== "fill") continue;
    pairs += 1;
    const gap = (Math.hypot(b.pts[0].x - a.pts[a.pts.length - 1].x,
                            b.pts[0].y - a.pts[a.pts.length - 1].y) / 8) * fitScale;
    assert.ok(b.jump, `a fill piece is reached needle-down across ${gap.toFixed(1)} mm`);
  }
  assert.ok(pairs > 100, `only ${pairs} consecutive fill pieces — the test would be vacuous`);
});

test("split is ON by default and fill is OFF, and each says so both ways", () => {
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const dflt = DG.buildLetteringDesign(font, "AB", base);
  // The default IS the split: asking for it explicitly must not move a stitch.
  for (const explicit of [{ splitSatin: true }, { splitSatin: 5.0 }]) {
    assert.deepStrictEqual(DG.buildLetteringDesign(font, "AB", { ...base, ...explicit }).stitches, dflt.stitches,
      `${JSON.stringify(explicit)} moved the stream`);
  }
  // The fill is off, and asking for off explicitly must not move one either.
  assert.strictEqual(dflt.lettering.wideSpans, 0);
  for (const explicit of [{ wideColumnFill: false }, { wideColumnFill: 0 }]) {
    assert.deepStrictEqual(DG.buildLetteringDesign(font, "AB", { ...base, ...explicit }).stitches, dflt.stitches,
      `${JSON.stringify(explicit)} moved the stream`);
  }
  // And turning the split OFF is reachable, which is what every byte-identity
  // pin on this lane now leans on.
  const noSplit = DG.buildLetteringDesign(font, "AB", { ...base, splitSatin: false });
  assert.strictEqual(noSplit.lettering.splitPenetrations, 0);
  assert.deepStrictEqual(DG.buildLetteringDesign(font, "AB", { ...base, splitSatin: 0 }).stitches, noSplit.stitches,
    "0 is the same off switch as false");
});

test("a number overrides the mirrored threshold, in FINAL sewn mm", () => {
  // This is what the census tool sweeps with, so it is pinned rather than
  // left to the tool. The two arms differ because the ceiling differs, not
  // because the number happened to be read in the layout frame.
  const f = fs.existsSync(MANGA) ? fb.decodeFontBin(fs.readFileSync(MANGA)) : null;
  if (!f) return;
  const base = { garment: G.getGarment("full_back"), pxPerMm: 8, emMm: 18, rgb: [25, 25, 25], pullCompMm: 0.2 };
  const at5 = DG.buildLetteringDesign(f, "AB", { ...base, splitSatin: 5.0 });
  const at10 = DG.buildLetteringDesign(f, "AB", { ...base, splitSatin: 10.0 });
  assert.deepStrictEqual(at5.stitches, DG.buildLetteringDesign(f, "AB", base).stitches,
    "the mirrored 5.0 mm is what the default takes");
  assert.ok(at10.stitchCount < at5.stitchCount, "a higher threshold splits less");
  assert.ok(at10.lettering.splitPenetrations > 0 && at10.lettering.splitPenetrations < at5.lettering.splitPenetrations);
});

function closeTo(a, b, tol, msg) {
  assert.ok(Math.abs(a - b) <= tol, `${msg || ""}: expected ${a} close to ${b} (tol ${tol})`);
}
