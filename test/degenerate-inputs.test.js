// Degenerate geometry fed to the fill / outline / satin / cross-fill / digitize
// entry points: zero-area, collinear, spike, near-duplicate and non-finite
// vertices. Each case must RETURN (the per-test timeout is the hang guard) with
// no NaN/Infinity coordinate. Cases test/engine-edge-cases.test.js already
// covers (doubled-back line, exact collinear, identical points, bowtie, ...)
// are deliberately not repeated here.

const assert = require("node:assert");
const { test } = require("node:test");
const fill = require("../src/fill.js");
const satin = require("../src/satin.js");
const crossfill = require("../src/crossfill.js");
const DG = require("../src/digitize.js");

const P = (...a) => a.map(([x, y]) => ({ x, y }));
const finite = (pts) => pts.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
const HANG_MS = 20000;

const RINGS = {
  "near-duplicate vertices (1e-12 apart)": P([0, 0], [1e-12, 0], [10, 0], [10, 10], [10, 10 + 1e-13], [0, 10]),
  "2000 duplicates of one point plus a segment": Array.from({ length: 2000 }, () => ({ x: 3, y: 3 })).concat(P([20, 0], [20, 20])),
  "a whole ring 1e-9 across": P([0, 0], [1e-9, 0], [1e-9, 1e-9], [0, 1e-9]),
  "a spike (0.0001 thick) with a vertex off the line": P([0, 0], [100, 0], [100, 0.0001], [0, 0.0001], [50, 0.0002]),
};
const NONFINITE = {
  "a NaN vertex": P([0, 0], [10, 0], [NaN, 5], [0, 10]),
  "an Infinity vertex": P([0, 0], [10, 0], [Infinity, 5], [0, 10]),
  "a -Infinity vertex": P([0, 0], [10, 0], [10, -Infinity], [10, 10], [0, 10]),
};

for (const [name, ring] of Object.entries(RINGS)) {
  test(`tatamiFill / outlines: ${name} returns finite points`, { timeout: HANG_MS }, () => {
    for (const markConnectors of [false, true]) {
      assert.ok(finite(fill.tatamiFill([ring], { rowSpacing: 5, angleDeg: 30, maxStitch: 20, markConnectors })));
    }
    assert.ok(finite(fill.runningOutline(ring, { stitchLen: 3 })));
    assert.ok(finite(fill.huggingOutline(ring, { stitchLen: 3, hug: 0.2 })));
  });

  test(`satin / medialSatin / crossFill: ${name} returns finite points`, { timeout: HANG_MS }, () => {
    for (const fn of [satin.satinColumn, satin.medialSatin]) {
      assert.ok(finite(fn(ring, { spacingMm: 0.4, pxPerMm: 8 }) || []));
    }
    assert.ok(finite(crossfill.crossFill([ring], { step: 2 }) || []));
  });

  test(`buildQualityDesign: ${name} yields finite stitches`, { timeout: HANG_MS }, () => {
    const d = DG.buildQualityDesign([{ rgb: [10, 10, 10], shapes: [{ outer: ring, holes: [] }] }],
      { pxPerMm: 8, garment: { widthIn: 4, heightIn: 4 } });
    assert.ok(finite(d.stitches));
    assert.ok(Number.isFinite(d.widthMM) && Number.isFinite(d.heightMM));
  });
}

for (const [name, ring] of Object.entries(NONFINITE)) {
  test(`buildQualityDesign: ${name} is dropped, not sewn as NaN`, { timeout: HANG_MS }, () => {
    const good = P([0, 0], [40, 0], [40, 40], [0, 40]);
    const d = DG.buildQualityDesign(
      [{ rgb: [10, 10, 10], shapes: [{ outer: ring, holes: [P([1, 1], [2, 1], [NaN, 2])] }, { outer: good, holes: [] }] },
       { rgb: [200, 0, 0], polygons: [ring] }],
      { pxPerMm: 8, garment: { widthIn: 4, heightIn: 4 } });
    assert.ok(finite(d.stitches), "non-finite stitch in output");
    assert.ok(Number.isFinite(d.widthMM) && Number.isFinite(d.heightMM));
    assert.ok(d.stitchCount > 0, "the finite shape beside it is still sewn");
  });
}

test("buildQualityDesign: finite input regions are passed through untouched", () => {
  const region = { rgb: [10, 10, 10], shapes: [{ outer: P([0, 0], [40, 0], [40, 40], [0, 40]), holes: [] }] };
  const outer = region.shapes[0].outer;
  DG.buildQualityDesign([region], { pxPerMm: 8, garment: { widthIn: 4, heightIn: 4 } });
  assert.strictEqual(region.shapes[0].outer, outer);
});
