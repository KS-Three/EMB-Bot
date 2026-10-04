const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");
const digitize = require("../src/digitize.js");
const garments = require("../src/garments.js");
const fabrics = require("../src/fabrics.js");

// THE SPINE OF A BAR (2026-10-04).
//
// `thin` never deletes a pixel on the grid's own border, and `ringToSpines`
// laid the shape against the grid's top and left: no spare cell there. So the
// top row and the left column of every shape were never thinned, and a plain
// bar's "skeleton" was its top edge and its left edge, an L. The crosses were
// cast from it to the outline and so came out right along the top edge, and
// along the left edge they turned: the last of them ran the length of the
// bar. 185 of the 276 sharp-cornered satin bars the shape tool makes on left
// chest carried a stitch as long as the bar.
//
// With the spare cell the skeleton is the centre line, and a centre line
// stops short of a bar's end by about half the bar's height. So a free end is
// run out to the outline, along the spine's own direction.

// medialSatin's points come in pairs, one cross each.
function crossesOf(pts) {
  const out = [];
  for (let i = 0; i + 1 < pts.length; i += 2) {
    const a = pts[i], b = pts[i + 1];
    out.push({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, dx: Math.abs(a.x - b.x), dy: Math.abs(a.y - b.y), len: Math.hypot(a.x - b.x, a.y - b.y) });
  }
  return out;
}
// 30 x 3 mm at 6 px per mm, the scale the shape tool draws at; and one stood on end.
const bar = [{ x: 210, y: 191 }, { x: 390, y: 191 }, { x: 390, y: 209 }, { x: 210, y: 209 }];
const post = bar.map((p) => ({ x: p.y, y: p.x }));
const OPTS = { spacingMm: 0.4, pxPerMm: 6, pullCompMm: 0 };

test("every cross of a bar runs across it: none along it", () => {
  const crosses = crossesOf(satin.medialSatin(bar, OPTS));
  assert.ok(crosses.length > 60, `${crosses.length} crosses on a 30 mm bar at 0.4 mm`);
  const along = crosses.filter((c) => c.dx > 1);
  assert.deepStrictEqual(along.map((c) => `${(c.len / 6).toFixed(1)} mm long at x ${((c.x - 210) / 6).toFixed(1)} mm`), [],
    "a cross of a level bar is upright");
  for (const c of crosses) assert.ok(Math.abs(c.len - 18) < 0.5, `a cross is the bar's height, 18 px: got ${c.len.toFixed(1)}`);
});

test("the same bar stood on end is sewn the same way: the left edge is not a spine either", () => {
  const crosses = crossesOf(satin.medialSatin(post, OPTS));
  assert.deepStrictEqual(crosses.filter((c) => c.dy > 1).length, 0, "a cross of an upright bar is level");
  for (const c of crosses) assert.ok(Math.abs(c.len - 18) < 0.5, `got ${c.len.toFixed(1)}`);
});

test("a bar's column runs from one end of the bar to the other", () => {
  // The centre line of a 180 x 18 px bar stops about 9 px short of each end,
  // and the free-end trim takes a little more. Run out to the outline, the
  // first and last cross stand on the bar's two ends.
  const xs = crossesOf(satin.medialSatin(bar, OPTS)).map((c) => c.x).sort((p, q) => p - q);
  assert.ok(xs[0] - 210 < 0.5, `the first cross is ${((xs[0] - 210) / 6).toFixed(2)} mm in from the bar's end`);
  assert.ok(390 - xs[xs.length - 1] < 0.5, `the last cross is ${((390 - xs[xs.length - 1]) / 6).toFixed(2)} mm in from the bar's end`);
});

// ---- through the Studio's own modules --------------------------------------
const lib = (name) => import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", name)).href);
async function studioShape(kind, params, sizeMm, garmentId = "left_chest") {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const { regions, pxPerMm } = shapesToRegions([
    { id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  return digitize.buildQualityDesign(regions, {
    garment: garments.getGarment(garmentId), fabric: fabrics.getFabric(fabrics.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  });
}
const longestStitchMm = (d) => {
  let m = 0;
  for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i].type === "stitch") m = Math.max(m, Math.hypot(d.stitches[i].x - d.stitches[i - 1].x, d.stitches[i].y - d.stitches[i - 1].y) / 10);
  return m;
};

test("a 30 x 3 mm bar off the shape tool is sewn 30 x 3 mm, and no stitch is longer than it is tall", async () => {
  // Before: reported 30.3 x 4.2 mm, with one stitch 30.2 mm long. Pique's
  // pull compensation is 0.3 mm and widens the crosses by that, no more
  // (0.15 mm a side, each rounded to the file's 0.1 mm: 3.4 mm sewn).
  const d = await studioShape("rect", { heightMm: 3, cornerRadiusMm: 0 }, 30);
  assert.strictEqual(d._debug.nSatin, 1);
  assert.ok(longestStitchMm(d) < 3.5, `longest stitch ${longestStitchMm(d).toFixed(1)} mm on a bar 3 mm tall`);
  assert.ok(Math.abs(d.widthMM - 30) < 0.15, `sewn ${d.widthMM.toFixed(1)} mm long`);
  assert.ok(Math.abs(d.heightMM - 3.3) < 0.15, `sewn ${d.heightMM.toFixed(1)} mm tall`);
});

test("a round-ended bar is sewn end to end too, with no stitch longer than it is tall", async () => {
  // Before: 30.2 x 3.6 mm with a 30.2 mm stitch at this size, 15.1 mm for 16.
  for (const size of [16, 30]) {
    const d = await studioShape("rect", { heightMm: 3, cornerRadiusMm: 1.5 }, size);
    assert.ok(longestStitchMm(d) < 3.5, `${size} mm: longest stitch ${longestStitchMm(d).toFixed(1)} mm`);
    assert.ok(Math.abs(d.widthMM - size) < 0.15, `${size} mm: sewn ${d.widthMM.toFixed(1)} mm long`);
  }
});

test("a fill is not touched: the shape tool's default rectangle sews what it sewed", async () => {
  // 50 x 30 mm is a fill; medialSatin never sees it. Counted on f887e27d.
  const d = await studioShape("rect", { heightMm: 30, cornerRadiusMm: 0 }, 50);
  assert.strictEqual(d._debug.nFill, 1);
  assert.strictEqual(d.stitchCount, 2935);
});
