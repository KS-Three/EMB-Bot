const assert = require("node:assert");
const { test } = require("node:test");
const DG = require("../src/digitize.js");

const sq = (x0, y0, s) => [{ x: x0, y: y0 }, { x: x0 + s, y: y0 }, { x: x0 + s, y: y0 + s }, { x: x0, y: y0 + s }];

test("groupRingsIntoShapes: side-by-side letters stay separate shapes", () => {
  // two 'letters' side by side, second has a counter (hole)
  const A = sq(0, 0, 50);
  const B = sq(70, 0, 50);
  const Bhole = sq(85, 15, 20);
  const shapes = DG.groupRingsIntoShapes([A, B, Bhole]);
  assert.strictEqual(shapes.length, 2);
  const withHole = shapes.find((s) => s.holes.length === 1);
  assert.ok(withHole, "expected one shape with a hole");
  // the other has none
  assert.ok(shapes.some((s) => s.holes.length === 0));
});

test("groupRingsIntoShapes: left neighbor is NOT swallowed by right ring (ray-cast regression)", () => {
  const small = sq(0, 0, 30);        // left, smaller
  const big = sq(50, -10, 60);       // right, bigger, overlapping y-band
  const shapes = DG.groupRingsIntoShapes([big, small]);
  assert.strictEqual(shapes.length, 2, "left shape must not become a hole of right shape");
});

test("buildQualityDesign: annulus keeps hole empty (no sew points inside)", () => {
  const outer = sq(0, 0, 100);
  const hole = sq(20, 20, 60);
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 10, 10], shapes: [{ outer, holes: [hole] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 }
  );
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.ok(sew.length > 100);
  // hole interior in DST units: px 20..80 of 100 → roughly |x|,|y| < 295 after centering+scale(≈10.16)
  const inHole = sew.filter((p) => Math.abs(p.x) < 290 && Math.abs(p.y) < 290);
  assert.strictEqual(inHole.length, 0, "sew stitches inside hole: " + inHole.length);
});

test("buildQualityDesign: thin solid bar goes satin, branched shape goes fill", () => {
  // thin bar 200x8 px at pxPerMm 8 → ~1mm wide final (fits 4in garment, scale>1 but still thin)
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 8 }, { x: 0, y: 8 }];
  const d1 = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer: bar, holes: [] }] }],
    { garment: { widthIn: 1, heightIn: 1 }, pxPerMm: 8, densityMm: 0.4, underlay: false, satinMaxWidthMm: 3 });
  assert.strictEqual(d1._debug.nSatin, 1, "bar should be satin");
  // branched T-shape (two joined bars) — farthest-pair chains are asymmetric → fill
  const tee = [
    { x: 0, y: 0 }, { x: 90, y: 0 }, { x: 90, y: 12 }, { x: 51, y: 12 },
    { x: 51, y: 90 }, { x: 39, y: 90 }, { x: 39, y: 12 }, { x: 0, y: 12 },
  ];
  const d2 = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer: tee, holes: [] }] }],
    { garment: { widthIn: 1, heightIn: 1 }, pxPerMm: 8, densityMm: 0.4, underlay: false, satinMaxWidthMm: 3 });
  assert.strictEqual(d2._debug.nSatin, 0, "tee should NOT be satin");
  assert.strictEqual(d2._debug.nFill, 1);
});

test("buildQualityDesign: outline option adds finishing edge run", () => {
  const outer = sq(0, 0, 100);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const noOutline = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }], base);
  const withOutline = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }], Object.assign({ outline: true }, base));
  assert.ok(withOutline.stitchCount > noOutline.stitchCount + 50, "outline should add perimeter stitches");
});

test("buildQualityDesign: multi-color design sequences color changes", () => {
  const d = DG.buildQualityDesign(
    [
      { rgb: [200, 0, 0], shapes: [{ outer: sq(0, 0, 40), holes: [] }] },
      { rgb: [0, 0, 200], shapes: [{ outer: sq(60, 0, 40), holes: [] }] },
    ],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, densityMm: 0.5, underlay: false }
  );
  assert.strictEqual(d.colorCount, 2);
  assert.strictEqual(d.stitches.filter((s) => s.type === "color").length, 1);
  assert.strictEqual(d.stitches[d.stitches.length - 1].type, "end");
});
