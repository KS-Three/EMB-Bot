const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");
const digitize = require("../src/digitize.js");
const garments = require("../src/garments.js");
const fabrics = require("../src/fabrics.js");

// A WALK THAT NEVER ENDS (2026-10-03).
//
// `skeletonEdges` follows skeleton pixels from a node until it meets the next
// node. Three pixels that all touch each other (the corner of an L) are none
// of them a node, and a walk that steps into them with nothing new ahead goes
// round them for ever: only its guard, one step per grid cell, stopped it. The
// edge that came back was as long as the grid has cells, and the satin emitter
// sewed it: a 20 mm star from the Studio's own shape tool came out at 48,645
// stitches, the 24 mm one at 128,239.

// A skeleton from rows of text, '#' on.
function maskOf(rows) {
  const h = rows.length, w = rows[0].length;
  const mask = new Uint8Array(w * h);
  rows.forEach((row, y) => { for (let x = 0; x < w; x++) if (row[x] === "#") mask[y * w + x] = 1; });
  return { mask, w, h };
}

test("skeletonEdges: a walk that goes round in circles ends where it first turned back on itself", () => {
  // The smallest skeleton that trapped the node walk, found by trying every
  // connected one up to seven pixels: a line with a one-pixel hook. (3,1) is
  // its only node. The hook's three pixels all touch, so the walk went
  // (1,1) (1,2) (2,1) (1,1) (1,2) ... until the guard.
  const { mask, w, h } = maskOf([
    ".......",
    ".###...",
    ".#.....",
    ".......",
  ]);
  const edges = satin.skeletonEdges(mask, w, h);
  assert.strictEqual(edges.length, 1);
  assert.deepStrictEqual(edges[0].pts, [[3, 1], [2, 1], [1, 1], [1, 2]],
    `the edge is the line and its hook, once; got ${edges[0].pts.length} points`);
  assert.strictEqual(edges[0].freeStart, true);
  assert.strictEqual(edges[0].freeEnd, false);
});

test("skeletonEdges: a ring walk that never comes back to where it began has found no ring", () => {
  // The smallest skeleton that trapped the LOOP walk: a line hooked at both
  // ends has no node at all, so the scan for rings starts on it, at (4,1),
  // and goes round the far hook for ever. It is not a ring. (ringToSpines
  // then takes its longest path, as it does for any skeleton with no edge.)
  const { mask, w, h } = maskOf([
    ".......",
    "....#..",
    ".####..",
    ".#.....",
    ".......",
  ]);
  const edges = satin.skeletonEdges(mask, w, h);
  assert.deepStrictEqual(edges.map((e) => e.pts.length), [],
    "a walk that did not close is not a closed edge");
});

test("skeletonEdges still walks a ring with no node as one closed edge", () => {
  // The rule above must not cost a real ring: this one is walked as before.
  const { mask, w, h } = maskOf([
    ".......",
    "..###..",
    ".#...#.",
    ".#...#.",
    "..###..",
    ".......",
  ]);
  const edges = satin.skeletonEdges(mask, w, h);
  assert.strictEqual(edges.length, 1);
  assert.strictEqual(edges[0].closed, true);
  assert.strictEqual(new Set(edges[0].pts.map((p) => p.join(","))).size, 10, "all ten pixels, once each");
});

// ---- the star itself, through the Studio's own modules ---------------------
//
// The ring is the one `app/src/lib/generate.js` makes for a `shape` element,
// and the options are the ones it passes: the defect is an accident of how
// one outline lands on the raster, so a re-typed star would test another.
const lib = (name) => import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", name)).href);
async function studioStar(points, innerRatio, sizeMm, garmentId = "left_chest") {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const ring = shapePresetPoints("star", { points, innerRatio }, sizeMm);
  const { regions, pxPerMm } = shapesToRegions([
    { id: "shape", points: ring, curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  return digitize.buildQualityDesign(regions, {
    garment: garments.getGarment(garmentId), fabric: fabrics.getFabric(fabrics.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  });
}
const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };

// Every size of one star, each against the middle of the run: a satin star's
// stitches grow with its size, so stitches per mm is what its neighbours in
// size predict, and the median of twenty-one sizes is not moved by six bad ones.
async function outOfLine(points, innerRatio, sizes) {
  const rows = [];
  for (const size of sizes) {
    const d = await studioStar(points, innerRatio, size);
    assert.strictEqual(d._debug.nSatin, 1, `${size} mm: this test is about a star the classifier sends to satin`);
    rows.push({ size, stitches: d.stitchCount, perMm: d.stitchCount / size });
  }
  const mid = median(rows.map((r) => r.perMm));
  return rows.filter((r) => r.perMm > 2 * mid).map((r) => `${r.size} mm: ${r.stitches} stitches, ${(r.perMm / mid).toFixed(1)}x its neighbours`);
}

test("a 12-point star at inner ratio 0.15 sews in line with its size, 10 to 30 mm (20 mm was 48,645 stitches)", async () => {
  const sizes = []; for (let s = 10; s <= 30; s++) sizes.push(s);
  assert.deepStrictEqual(await outOfLine(12, 0.15, sizes), []);
});

test("the 20 mm, 12-point star the finding was made on is a few hundred stitches, not tens of thousands", async () => {
  // 18 and 23 mm are the nearest sizes either side with no walk that ran to
  // its guard (19 to 22 mm all had one), so they are what it is read against.
  const d = await studioStar(12, 0.15, 20);
  const near = [await studioStar(12, 0.15, 18), await studioStar(12, 0.15, 23)].map((x) => x.stitchCount);
  assert.ok(d.stitchCount < 2 * Math.max(...near),
    `20 mm: ${d.stitchCount} stitches; 18 mm and 23 mm: ${near.join(" and ")}`);
});

test("a 6-point star at inner ratio 0.40 sews in line with its size at 15 mm (the ring walk ran away there)", async () => {
  const sizes = []; for (let s = 10; s <= 17; s++) sizes.push(s);   // from 18 mm it is a fill
  const bad = await outOfLine(6, 0.4, sizes);
  assert.deepStrictEqual(bad.filter((line) => line.startsWith("15 mm")), []);
});

test("a small round shape whose ring walks all ran away is sewn once, across itself", async () => {
  // Found by the independent re-measure: where the skeleton has no node at
  // all, every edge was a ring walk at the guard. A 6 mm near-round star
  // (12 points, ratio 0.9) sewed 377 stitches, a knot fifteen deep. With no
  // edge left, ringToSpines takes the skeleton's longest path, and the shape
  // is one column across itself, as the 6 mm circle beside it is.
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const build = (kind, params) => {
    const { regions, pxPerMm } = shapesToRegions([
      { id: "shape", points: shapePresetPoints(kind, params, 6), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
    ]);
    return digitize.buildQualityDesign(regions, {
      garment: garments.getGarment("left_chest"), fabric: fabrics.getFabric(fabrics.fabricForGarment("left_chest")), pxPerMm,
      darkOnTop: false, underlay: true, targetWidthMm: 6, offsetXMm: 0, offsetYMm: 0,
    });
  };
  const blob = build("star", { points: 12, innerRatio: 0.9 }), circle = build("circle", {});
  assert.strictEqual(blob._debug.nSatin, 1);
  assert.ok(blob.stitchCount < 2 * circle.stitchCount, `${blob.stitchCount} stitches; the 6 mm circle sews ${circle.stitchCount}`);
  assert.ok(blob.widthMM > 3 && blob.heightMM > 3, `sewn ${blob.widthMM.toFixed(1)} x ${blob.heightMM.toFixed(1)} mm of a 6 mm shape`);
});

test("a star none of whose walks ran to the guard sews exactly what it sewed", async () => {
  // Counts measured on origin/main at f887e27d, before the walk was touched.
  // (Not every star beside the 20 mm one qualifies: the 30 mm one and the
  // ratio-0.3 one had walks at the guard too, whose edges the emitter's
  // smoothing happened to fold to a point, and those two do move.)
  // Re-pinned 2026-10-08 when the skeleton stopped sticking to the grid's top
  // row and left column (`ringToSpines`): 444 / 713 / 999 / 592 before. The
  // walk is not what moved them; every medial-axis satin moved.
  assert.strictEqual((await studioStar(12, 0.15, 12)).stitchCount, 462);
  assert.strictEqual((await studioStar(12, 0.15, 18)).stitchCount, 751);
  assert.strictEqual((await studioStar(12, 0.15, 23)).stitchCount, 1025);
  assert.strictEqual((await studioStar(8, 0.15, 20)).stitchCount, 594);
});
