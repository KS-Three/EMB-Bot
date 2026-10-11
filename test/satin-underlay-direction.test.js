const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");

// THE UNDERLAY'S DIRECTION (defect 57, 2026-10-11; `underlayDirection`; built OFF in PR #822, default ON 2026-10-11).
//
// A satin bar's centre-run underlay runs the bar from one end to the other,
// and its column began wherever the medial walk began -- the same end the
// underlay started from. So between the two the machine lifted the needle
// and travelled back the length of the bar. With the flag the column starts
// at the end nearer where the underlay ENDS (chosen by that end point, not
// flipped: a zigzag underlay already ends near the column's start and keeps
// it). Measured in the emitted stream, in mm (0.1 mm records / 10), not px.

const measure = () => import(pathToFileURL(path.join(__dirname, "..", "tools", "underlay-direction-measure.mjs")).href);

test("with underlayDirection, a bar's column starts where its centre-run underlay ends", async () => {
  const { SHAPES, build, gapMm } = await measure();
  for (const [name, pts] of Object.entries(SHAPES)) {
    const off = build(pts, "left_chest", false), on = build(pts, "left_chest", true);
    const lengthMm = Math.max(off.widthMM, off.heightMM);
    // off: the needle-up move is (nearly) the bar's length -- the defect, pinned
    assert.ok(gapMm(off) > 0.8 * lengthMm, `${name}: off, needle-up ${gapMm(off).toFixed(2)} mm on a bar ${lengthMm.toFixed(1)} mm long`);
    // on: under one stitch (the builder's 4 mm maximum). What is left is the
    // underlay stopping a step short of the end, and the column's first cross
    // starting on a rail: 1.8 to 2.4 mm on these bars, under their own cross.
    assert.ok(gapMm(on) < 4, `${name}: on, needle-up ${gapMm(on).toFixed(2)} mm`);
    assert.ok(gapMm(on) < gapMm(off) / 8, `${name}: on ${gapMm(on).toFixed(2)} mm against off ${gapMm(off).toFixed(2)} mm`);
    // the same stitches, sewn the other way: none added or lost
    assert.strictEqual(on.stitchCount, off.stitchCount, `${name}: stitch count`);
  }
});

test("a zigzag underlay that already ends by the column's start keeps it", async () => {
  const { SHAPES, build, gapMm } = await measure();
  for (const [name, pts] of Object.entries(SHAPES)) {
    const off = build(pts, "full_back", false), on = build(pts, "full_back", true);
    assert.ok(gapMm(on) <= gapMm(off) + 1e-9, `${name}: on ${gapMm(on).toFixed(2)} mm, off ${gapMm(off).toFixed(2)} mm`);
  }
});

test("the flag defaults ON: not passing it is byte-identical to underlayDirection: true, and differs from false", async () => {
  const { SHAPES, build } = await measure();
  const { shapesToRegions } = await import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", "manualShapes.js")).href);
  for (const pts of Object.values(SHAPES)) {
    const on = build(pts, "left_chest", true), off = build(pts, "left_chest", false);
    // build() always passes the key; without it at all (default ON since 2026-10-11):
    const digitize = require("../src/digitize.js"), garments = require("../src/garments.js"), fabrics = require("../src/fabrics.js");
    const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points: pts, curves: {}, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null }]);
    const xs = pts.map((p) => p.x);
    const bare = digitize.buildQualityDesign(regions, {
      garment: garments.getGarment("left_chest"), fabric: fabrics.getFabric(fabrics.fabricForGarment("left_chest")), pxPerMm,
      darkOnTop: false, underlay: true, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / pxPerMm, offsetXMm: 0, offsetYMm: 0,
    });
    assert.deepStrictEqual(on.stitches, bare.stitches);
    assert.deepStrictEqual(on.runs, bare.runs);
    assert.notDeepStrictEqual(off.stitches, bare.stitches, "explicit false still gives the old order");
  }
});

test("startNear turns a column round, and its needle-up jumps go with it", () => {
  // two strokes, the second entered by a jump (travel on its first point)
  const pts = [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }, { x: 10, y: 0, travel: true }, { x: 11, y: 0 }];
  assert.strictEqual(satin.startNear(pts, { x: -1, y: 0 }), pts, "already starts at the nearer end: the same array");
  assert.strictEqual(satin.startNear(pts, null), pts, "nothing before it: unchanged");
  const back = satin.startNear(pts, { x: 12, y: 0 });
  // the jump was 2 -> 10; reversed it is 10 -> 2, so the flag is on the 2
  assert.deepStrictEqual(back, [{ x: 11, y: 0 }, { x: 10, y: 0 }, { x: 2, y: 0, travel: true }, { x: 1, y: 0 }, { x: 0, y: 0 }]);
  assert.deepStrictEqual(pts[3], { x: 10, y: 0, travel: true }, "the input is not changed");
  // a tie: unchanged
  assert.strictEqual(satin.startNear(pts, { x: 5.5, y: 0 }), pts);
});
