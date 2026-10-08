const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");
const digitize = require("../src/digitize.js");
const garments = require("../src/garments.js");
const fabrics = require("../src/fabrics.js");

// A BAR'S SPINE ON ITS OWN EDGE (defect 57, `skeletonPad`, built OFF).
//
// `thin` never erodes the grid's first row or column, and `ringToSpines` laid
// the shape's own top and left edges onto exactly those. A plain bar thinned
// to its top edge and its left end, not its centre line: the crosses were
// right along the top (the rays still reach the far side), then turned with
// the spine down the left end, and the last was one stitch the length of the
// bar. `skeletonPad` gives the grid the same margin on its near side that it
// already had on its far side.

// The longest needle-down stitch of a run (px), and of a design (mm).
function longestRun(pts) {
  let m = 0;
  for (let i = 1; i < pts.length; i++) if (!pts[i].travel) m = Math.max(m, Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  return m;
}
function longestDesignMm(d) {
  let m = 0;
  for (let i = 1; i < d.stitches.length; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (a.type === "stitch" && b.type === "stitch") m = Math.max(m, Math.hypot(b.x - a.x, b.y - a.y));
  }
  return m / 10;
}

const ppm = 10;
const bar = [{ x: 0, y: 0 }, { x: 30 * ppm, y: 0 }, { x: 30 * ppm, y: 3 * ppm }, { x: 0, y: 3 * ppm }];
const opts = { spacingMm: 0.4, pxPerMm: ppm, pullCompMm: 0.2 };

test("medialSatin: a 30 x 3 mm bar's longest stitch is the bar's width, not its length, with skeletonPad", () => {
  const before = longestRun(satin.medialSatin(bar, opts)) / ppm;
  const after = longestRun(satin.medialSatin(bar, Object.assign({ skeletonPad: true }, opts))) / ppm;
  assert.ok(before > 25, `the defect as measured: ${before.toFixed(2)} mm`);
  assert.ok(after < 3.5, `a cross is the bar's 3 mm plus the pull: ${after.toFixed(2)} mm`);
});

test("medialSatin: with skeletonPad the bar's spine is its centre line", () => {
  globalThis.__DBG_SPINE = 1;
  try {
    satin.medialSatin(bar, Object.assign({ skeletonPad: true }, opts));
    const ys = globalThis.__spine.map((p) => p.y);
    for (const y of ys) assert.ok(Math.abs(y - 15) < 2, `spine y ${y.toFixed(2)} px, centre 15`);
  } finally { delete globalThis.__DBG_SPINE; delete globalThis.__spine; }
});

const lib = (name) => import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", name)).href);
async function studio(kind, params, sizeMm, extra) {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const { regions, pxPerMm } = shapesToRegions([
    { id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  const g = "left_chest";
  return digitize.buildQualityDesign(regions, Object.assign({
    garment: garments.getGarment(g), fabric: fabrics.getFabric(fabrics.fabricForGarment(g)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  }, extra));
}

test("buildQualityDesign: the Studio's 30 x 3 mm bar sews no stitch longer than 4 mm with skeletonPad", async () => {
  const off = await studio("rect", { heightMm: 3, cornerRadiusMm: 0 }, 30);
  const on = await studio("rect", { heightMm: 3, cornerRadiusMm: 0 }, 30, { skeletonPad: true });
  assert.ok(longestDesignMm(off) > 25, `off: ${longestDesignMm(off)} mm`);
  assert.ok(longestDesignMm(on) < 4, `on: ${longestDesignMm(on)} mm`);
});

test("buildQualityDesign: skeletonPad false is the design with no option at all", async () => {
  for (const [kind, params, size] of [["rect", { heightMm: 3, cornerRadiusMm: 0 }, 30], ["star", { points: 10, innerRatio: 0.15 }, 20], ["circle", {}, 20]]) {
    const none = await studio(kind, params, size);
    const off = await studio(kind, params, size, { skeletonPad: false });
    assert.deepStrictEqual(off.stitches, none.stitches, kind);
  }
});
