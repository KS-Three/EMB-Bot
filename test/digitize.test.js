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

// ---- Phase 2: fabric-driven pull compensation + underlay styles ----

const shoelace = (p) => { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j].x * p[i].y - p[i].x * p[j].y); return Math.abs(a) / 2; };
const fab = (o) => Object.assign({ pullCompMm: 0.4, fillUnderlay: "edge_lattice", satinUnderlay: "center_run", densityAdjust: 1.0, trimAtMm: 3.0 }, o);
const extentOf = (d) => {
  const s = d.stitches.filter((x) => x.type === "stitch");
  let mnx = Infinity, mxx = -Infinity, mny = Infinity, mxy = -Infinity;
  for (const p of s) { if (p.x < mnx) mnx = p.x; if (p.x > mxx) mxx = p.x; if (p.y < mny) mny = p.y; if (p.y > mxy) mxy = p.y; }
  return { w: mxx - mnx, h: mxy - mny };
};

test("offsetRing: outward grows area, inward shrinks, concave spike clamped", () => {
  const s = sq(0, 0, 10);
  const grown = DG.offsetRing(s, 1, true);
  const shrunk = DG.offsetRing(s, 1, false);
  assert.ok(shoelace(grown) > shoelace(s), "outward offset should grow area");
  assert.ok(shoelace(shrunk) < shoelace(s), "inward offset should shrink area");
  // a sharp inward notch: offsetting must not fling any vertex past the miter clamp (3*d)
  const concave = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 50, y: 5 }, { x: 0, y: 100 }];
  const d = 5;
  const off = DG.offsetRing(concave, d, true);
  for (let i = 0; i < concave.length; i++) {
    const dist = Math.hypot(off[i].x - concave[i].x, off[i].y - concave[i].y);
    assert.ok(dist <= 3 * d + 1e-6, "vertex " + i + " moved " + dist + " beyond miter clamp");
  }
});

test("offsetRing: reversed (CW) winding still grows outward, shrinks inward", () => {
  // sq() winds one way; reverse it to get the opposite winding. offsetRing uses
  // signed area to pick the outward sense, so both windings must behave the same.
  const cw = sq(0, 0, 10).slice().reverse();
  const grown = DG.offsetRing(cw, 1, true);
  const shrunk = DG.offsetRing(cw, 1, false);
  assert.ok(shoelace(grown) > shoelace(cw), "CW outward offset should grow area");
  assert.ok(shoelace(shrunk) < shoelace(cw), "CW inward offset should shrink area");
});

test("buildQualityDesign: fabric pull comp grows fill extents", () => {
  const outer = sq(0, 0, 100);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const e0 = extentOf(DG.buildQualityDesign(region, Object.assign({ fabric: fab({ pullCompMm: 0 }) }, base)));
  const e5 = extentOf(DG.buildQualityDesign(region, Object.assign({ fabric: fab({ pullCompMm: 0.5 }) }, base)));
  assert.ok(e5.w > e0.w && e5.h > e0.h, "pull comp should grow fill extents: w " + e0.w + "->" + e5.w);
  // grew by ~pull on each side (≈2*0.5mm in DST 0.1mm units ≈ 10, corners diagonal)
  assert.ok(e5.w - e0.w >= 4 && e5.w - e0.w <= 30, "growth magnitude in range, got " + (e5.w - e0.w));
});

test("buildQualityDesign: fabric pull comp shrinks holes (fill reaches inward)", () => {
  const outer = sq(0, 0, 100), hole = sq(30, 30, 40); // hole centered on design center
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [hole] }] }];
  const minR = (d) => Math.min.apply(null, d.stitches.filter((s) => s.type === "stitch").map((s) => Math.hypot(s.x, s.y)));
  const r0 = minR(DG.buildQualityDesign(region, Object.assign({ fabric: fab({ pullCompMm: 0 }) }, base)));
  const r5 = minR(DG.buildQualityDesign(region, Object.assign({ fabric: fab({ pullCompMm: 0.6 }) }, base)));
  assert.ok(r5 < r0, "shrunk hole lets fill reach nearer center: " + r0 + " -> " + r5);
});

test("offsetRing/signedArea: over-inset thin hole flips winding (collapse guard fires)", () => {
  // A hole only 2px wide. Inset for pull comp by 3px (> half width) crosses its
  // walls: the ring inverts and its signed area flips sign — a self-intersecting
  // boundary the miter clamp can't prevent. This is exactly what the fill guard
  // detects. Pre-fix, this inverted ring was fed straight to the fill.
  const thinHole = [{ x: 49, y: 10 }, { x: 51, y: 10 }, { x: 51, y: 50 }, { x: 49, y: 50 }];
  const a0 = DG.signedArea(thinHole);
  const off = DG.offsetRing(thinHole, 3, false);
  const a1 = DG.signedArea(off);
  assert.notStrictEqual(Math.sign(a0), Math.sign(a1),
    "sanity: over-inset thin hole must invert (sign flip): " + a0 + " -> " + a1);
  // The guard condition used in buildQualityDesign: sign flip OR near-zero area.
  const guardTriggers = Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6;
  assert.ok(guardTriggers, "collapse guard must trigger for the inverted thin hole");
});

test("buildQualityDesign: thin hole + large pull comp does not produce runaway fill (guard)", () => {
  // Guard-invariant test. A thin hole with pull comp big enough to collapse it
  // must NOT yield a self-crossing fill boundary. Practical checks: the region
  // still fills (stitchCount > 0), and fill stitches stay within the (outset)
  // outer ring's bounds — i.e. no runaway crossing from an inverted hole.
  const outer = sq(0, 0, 100);
  const thinHole = [{ x: 49, y: 20 }, { x: 51, y: 20 }, { x: 51, y: 80 }, { x: 49, y: 80 }];
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [thinHole] }] }];
  const d = DG.buildQualityDesign(region, Object.assign({ fabric: fab({ pullCompMm: 1.0 }) }, base));
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.ok(sew.length > 0, "region still fills despite the collapsing hole");
  // Compare against the same design with NO hole: the outer outset is identical,
  // so a well-behaved fill must not exceed that extent by more than a stitch.
  const noHole = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }],
    Object.assign({ fabric: fab({ pullCompMm: 1.0 }) }, base)
  );
  const eHole = extentOf(d), eNone = extentOf(noHole);
  // Allow a small margin for tatami row-segmentation rounding (a few DST 0.1mm
  // units). A runaway from an inverted, self-crossing hole would blow the extent
  // far past this; the guard keeps it hole-free and bounded.
  assert.ok(eHole.w <= eNone.w + 12 && eHole.h <= eNone.h + 12,
    "fill must stay within the outer outset bounds (no runaway): " +
    JSON.stringify(eHole) + " vs " + JSON.stringify(eNone));
});

test("buildQualityDesign: underlay style controls underlay stitch volume", () => {
  const outer = sq(0, 0, 100);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, satinMaxWidthMm: 3, underlay: true };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const count = (style) => DG.buildQualityDesign(region, Object.assign({ fabric: fab({ fillUnderlay: style, pullCompMm: 0 }) }, base)).stitchCount;
  const none = count("none"), edge = count("edge_run"), dbl = count("double_lattice");
  assert.ok(none < edge, "edge_run adds underlay over none: " + none + " < " + edge);
  assert.ok(dbl > edge, "double_lattice emits more underlay than edge_run: " + dbl + " > " + edge);
});

test("buildQualityDesign: fabric densityAdjust loosens fill (fewer stitches)", () => {
  // large square + pxPerMm 8 keeps row spacing above the 0.8px floor so the
  // density multiplier actually changes the row count.
  const outer = sq(0, 0, 700);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const c10 = DG.buildQualityDesign(region, Object.assign({ fabric: fab({ densityAdjust: 1.0, pullCompMm: 0 }) }, base)).stitchCount;
  const c12 = DG.buildQualityDesign(region, Object.assign({ fabric: fab({ densityAdjust: 1.2, pullCompMm: 0 }) }, base)).stitchCount;
  assert.ok(c12 < c10, "densityAdjust 1.2 loosens rows: " + c10 + " -> " + c12);
});

test("buildQualityDesign: fabric trimAtMm gates a mid-distance travel trim", () => {
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 1 };
  const anchor = { outer: sq(0, 0, 700), holes: [] };
  const shapes = [anchor, { outer: sq(760, 340, 16), holes: [] }, { outer: sq(800, 340, 16), holes: [] }];
  const region = [{ rgb: [0, 0, 0], shapes }];
  const t3 = DG.buildQualityDesign(region, Object.assign({ fabric: fab({ trimAtMm: 3.0, fillUnderlay: "none", satinUnderlay: "none" }) }, base))._debug.nTrims;
  const t5 = DG.buildQualityDesign(region, Object.assign({ fabric: fab({ trimAtMm: 5.0, fillUnderlay: "none", satinUnderlay: "none" }) }, base))._debug.nTrims;
  assert.strictEqual(t3, 2, "at 3mm the dot->dot travel trims (2 total)");
  assert.strictEqual(t5, 1, "at 5mm the same travel is a plain jump (1 total)");
});

test("buildQualityDesign: no-fabric output is byte-identical to pre-Phase-2 (snapshot)", () => {
  const outer = sq(0, 0, 100), hole = sq(20, 20, 60);
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 20, 30], shapes: [{ outer, holes: [hole] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: true, satinMaxWidthMm: 3 }
  );
  assert.strictEqual(d.stitches.length, 3176, "total record count frozen");
  assert.strictEqual(d.stitchCount, 3076, "stitch count frozen");
  const first20 = [
    { x: -504, y: 504, type: "jump" }, { x: -504, y: 504, type: "stitch" }, { x: -463, y: 504, type: "stitch" },
    { x: -422, y: 504, type: "stitch" }, { x: -382, y: 504, type: "stitch" }, { x: -341, y: 504, type: "stitch" },
    { x: -301, y: 504, type: "stitch" }, { x: -260, y: 504, type: "stitch" }, { x: -219, y: 504, type: "stitch" },
    { x: -179, y: 504, type: "stitch" }, { x: -138, y: 504, type: "stitch" }, { x: -97, y: 504, type: "stitch" },
    { x: -57, y: 504, type: "stitch" }, { x: -16, y: 504, type: "stitch" }, { x: 25, y: 504, type: "stitch" },
    { x: 65, y: 504, type: "stitch" }, { x: 106, y: 504, type: "stitch" }, { x: 146, y: 504, type: "stitch" },
    { x: 187, y: 504, type: "stitch" }, { x: 228, y: 504, type: "stitch" },
  ];
  assert.deepStrictEqual(d.stitches.slice(0, 20), first20, "first 20 records unchanged");
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
