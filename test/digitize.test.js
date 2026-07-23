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

test("buildQualityDesign: trim inserted for long travel, not for short hop", () => {
  // fitScale upscales tiny-only designs, so a large anchor shape fixes the
  // overall scale; two small dots then have a controllable FINAL separation.
  // The anchor->dot travel always trims; the dot->dot travel trims only when far.
  const anchor = { outer: sq(0, 0, 700), holes: [] };
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 };
  const near = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [anchor, { outer: sq(760, 340, 16), holes: [] }, { outer: sq(784, 340, 16), holes: [] }] }], base);
  const far = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [anchor, { outer: sq(760, 340, 16), holes: [] }, { outer: sq(1100, 340, 16), holes: [] }] }], base);
  assert.strictEqual(near._debug.nTrims, 1, "close dots: only the anchor->dot travel trims");
  assert.strictEqual(far._debug.nTrims, 2, "far dot adds one more trim between the two dots");
});

test("buildQualityDesign: scrambled shapes emit in nearest-neighbor order (input-order independent)", () => {
  const A = { outer: sq(0, 0, 40), holes: [] };
  const B = { outer: sq(300, 0, 40), holes: [] };
  const C = { outer: sq(600, 20, 40), holes: [] };
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 };
  const seq = (shapes) => DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes }], base).stitches.filter((s) => s.type === "stitch").map((s) => s.x + "," + s.y).join(";");
  const p1 = seq([A, B, C]);
  const p2 = seq([C, A, B]);
  const p3 = seq([B, C, A]);
  assert.strictEqual(p1, p2, "output must not depend on input order (geometric NN)");
  assert.strictEqual(p1, p3);
  // NN from design center visits the middle shape (B, x~300) first: its first
  // stitch x is near 0 (centered), far from the +/- edges of A and C.
  const firstX = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [A, B, C] }], base).stitches.filter((s) => s.type === "stitch")[0].x;
  assert.ok(Math.abs(firstX) < 900, "first sewn shape is the one nearest center, got x=" + firstX);
});

test("buildQualityDesign: cap garment sews center shape first (center-out)", () => {
  const left = { outer: sq(0, 50, 30), holes: [] };
  const center = { outer: sq(200, 50, 30), holes: [] };
  const right = { outer: sq(400, 50, 30), holes: [] };
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [left, center, right] }],
    { garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 }
  );
  const first = d.stitches.filter((s) => s.type === "stitch")[0];
  // center shape is at the design center → its first stitch x is near 0; the
  // left/right shapes would start hundreds of DST units away.
  assert.ok(Math.abs(first.x) < 200, "cap should sew the center shape first, got x=" + first.x);
});

test("buildQualityDesign: trim emitted before every color change", () => {
  const d = DG.buildQualityDesign(
    [
      { rgb: [200, 0, 0], shapes: [{ outer: sq(0, 0, 40), holes: [] }] },
      { rgb: [0, 0, 200], shapes: [{ outer: sq(60, 0, 40), holes: [] }] },
    ],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 }
  );
  // the trim must be emitted immediately before the color-change record
  const ci = d.stitches.findIndex((s) => s.type === "color");
  assert.ok(ci > 0);
  assert.strictEqual(d.stitches[ci - 1].type, "trim", "a trim must precede the color change");
  assert.ok(d._debug.nTrims >= 1);
});

test("buildQualityDesign: no redundant trim right after a color change (color-change trim already cut)", () => {
  // Large anchor fixes overall scale; color 1 also has a far dot to force one
  // LEGITIMATE within-block travel-trim. Color 2's only shape is placed FAR
  // from where color 1 ended — on the buggy code this fired a SECOND trim
  // immediately after the color change (thread was already cut → redundant).
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 };
  const d = DG.buildQualityDesign(
    [
      { rgb: [200, 0, 0], shapes: [{ outer: sq(0, 0, 700), holes: [] }, { outer: sq(1100, 340, 16), holes: [] }] },
      { rgb: [0, 0, 200], shapes: [{ outer: sq(1100, -500, 16), holes: [] }] },
    ],
    base
  );
  const ci = d.stitches.findIndex((s) => s.type === "color");
  assert.ok(ci > 0, "expected a color-change record");
  // the record before the color change is always the color-change trim
  assert.strictEqual(d.stitches[ci - 1].type, "trim", "color change must be preceded by its trim");
  // after the color change, the next non-jump record must be a stitch (the
  // leading travel jump is allowed), NOT another trim — no double cut
  let k = ci + 1;
  while (k < d.stitches.length && d.stitches[k].type === "jump") k++;
  assert.strictEqual(d.stitches[k].type, "stitch", "no redundant trim after color change; got " + d.stitches[k].type);
  // total trims: 1 color-change trim + 1 legitimate within-block (color 1) trim
  assert.strictEqual(d._debug.nTrims, 2, "expected exactly 2 trims (1 color change + 1 within-block), got " + d._debug.nTrims);
});

test("buildQualityDesign: stitchCount excludes trim records", () => {
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: sq(0, 0, 700), holes: [] }, { outer: sq(760, 340, 16), holes: [] }, { outer: sq(1100, 340, 16), holes: [] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 }
  );
  assert.ok(d._debug.nTrims > 0, "expected some trims");
  const stitchOnly = d.stitches.filter((s) => s.type === "stitch").length;
  const trimOnly = d.stitches.filter((s) => s.type === "trim").length;
  assert.strictEqual(d.stitchCount, stitchOnly, "stitchCount counts only stitch records");
  assert.strictEqual(trimOnly, d._debug.nTrims, "trim records match nTrims and are excluded from stitchCount");
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
