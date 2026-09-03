const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
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

// ---- Manual stitch-type override (manual digitizing mode) -----------------
// shape.tierOverride is an ADDITIVE, opt-in field: absent (every Image/Text
// caller) leaves the auto classification above byte-identical (already
// proven by every other test in this file passing unchanged). These tests
// pin the override's own behavior using the exact bar/tee fixtures above.
test("buildQualityDesign: shape.tierOverride='fill' forces an otherwise-thin bar to fill", () => {
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 8 }, { x: 0, y: 8 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: bar, holes: [], tierOverride: "fill" }] }],
    { garment: { widthIn: 1, heightIn: 1 }, pxPerMm: 8, densityMm: 0.4, underlay: false, satinMaxWidthMm: 3 }
  );
  assert.strictEqual(d._debug.nSatin, 0, "override should route the thin bar to fill");
  assert.strictEqual(d._debug.nFill, 1);
});

test("buildQualityDesign: shape.tierOverride='satin' forces a branched shape to satin, bypassing the branch guard", () => {
  const tee = [
    { x: 0, y: 0 }, { x: 90, y: 0 }, { x: 90, y: 12 }, { x: 51, y: 12 },
    { x: 51, y: 90 }, { x: 39, y: 90 }, { x: 39, y: 12 }, { x: 0, y: 12 },
  ];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: tee, holes: [], tierOverride: "satin" }] }],
    { garment: { widthIn: 1, heightIn: 1 }, pxPerMm: 8, densityMm: 0.4, underlay: false, satinMaxWidthMm: 3 }
  );
  assert.strictEqual(d._debug.nSatin, 1, "manual override should force satin despite the branch guard");
  assert.strictEqual(d._debug.nFill, 0);
});

test("buildQualityDesign: shape.tierOverride='satin' still falls back to fill when the shape has holes", () => {
  const outer = sq(0, 0, 100);
  const hole = sq(20, 20, 20);
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [hole], tierOverride: "satin" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 }
  );
  assert.strictEqual(d._debug.nSatin, 0, "satinColumn can't represent a hole — override must not bypass this");
  assert.strictEqual(d._debug.nFill, 1);
});

test("buildQualityDesign: a bare 3-point triangle (manual digitizing mode's simplest shape) sews real stitches, not zero", () => {
  // Regression: buildQualityDesign used to require outer.length >= 4, which
  // real Image/Text-mode geometry always satisfies (raster traces and font
  // glyphs never emit an exactly-3-point ring) but silently zeroed out any
  // manually-drawn triangle — a perfectly valid, minimal closed polygon.
  const tri = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 100, y: 200 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: tri, holes: [], tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, densityMm: 0.4, underlay: false }
  );
  assert.ok(d.stitchCount > 20, "a 3-point polygon must still generate real fill stitches: " + d.stitchCount);
  assert.strictEqual(d._debug.nFill, 1);
});

test("buildQualityDesign: an unrecognized/absent tierOverride is a no-op (auto classification unchanged)", () => {
  const bar = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 8 }, { x: 0, y: 8 }];
  const base = { garment: { widthIn: 1, heightIn: 1 }, pxPerMm: 8, densityMm: 0.4, underlay: false, satinMaxWidthMm: 3 };
  const withoutField = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer: bar, holes: [] }] }], base);
  const withGarbage = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer: bar, holes: [], tierOverride: "auto" }] }], base);
  assert.strictEqual(withoutField._debug.nSatin, 1);
  assert.strictEqual(withGarbage._debug.nSatin, 1);
  assert.deepStrictEqual(withGarbage.stitches, withoutField.stitches);
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
  // The 700px anchor is a large fill → sews center-out and cuts its one
  // sweep-to-sweep reposition (a trim), so every count below is +1 vs pre-Phase-4.
  assert.strictEqual(near._debug.nTrims, 2, "anchor center-out trim + the anchor->dot travel trim");
  assert.strictEqual(far._debug.nTrims, 3, "far dot adds one more trim between the two dots");
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
  // + 1 center-out reposition trim (the 700px anchor is a large center-out fill).
  assert.strictEqual(d._debug.nTrims, 3, "expected exactly 3 trims (1 color change + 1 within-block + 1 center-out), got " + d._debug.nTrims);
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
  // +1 in each: the 700px anchor is a large center-out fill → one reposition trim.
  assert.strictEqual(t3, 3, "at 3mm the dot->dot travel trims (2) + anchor center-out trim");
  assert.strictEqual(t5, 2, "at 5mm the dot->dot is a plain jump (1) + anchor center-out trim");
});

// Snapshot: a SINGLE-shape region. Phase 3 changed the default from one
// per-COLOR angle to one per-SHAPE angle, but for a region with a single shape
// the per-shape PCA (outer+hole rings) equals the old per-color PCA, so this
// snapshot is invariant across the Phase 3 change and stays frozen at the same
// values. (The per-shape divergence is exercised by the two-shape test below.)
test("buildQualityDesign: no-fabric single-shape output frozen (snapshot, Phase-3-invariant)", () => {
  const outer = sq(0, 0, 100), hole = sq(20, 20, 60);
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 20, 30], shapes: [{ outer, holes: [hole] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, underlay: true, satinMaxWidthMm: 3 }
  );
  // RE-FREEZE (resize-density fix, 2026-07-27): this fixture has pxPerMm:1
  // with a ~100mm shape against a 101.6mm (4in) hoop, so sc≈1 and
  // pxPerFinalMm≈1 — meaning underlayStitchPx (2.0mm requested) and rowPx
  // (0.5mm requested) both used to land BELOW the old fixed px floors
  // (4px, 0.8px) and get silently overridden by them. The floor was meant
  // as loop-safety only but doubled as an unintended density ceiling (see
  // PX_LOOP_EPS comment in buildQualityDesign) — this fixture's old frozen
  // numbers were pinning that bug (underlay stepping ~4.1mm instead of the
  // requested 2.0mm). Post-fix, underlay steps a clean 20 DST-units (2.0mm,
  // matches request) instead of the old ~41-unit (4.1mm, floor-clamped)
  // step, and total record/stitch counts rose (finer fill rows too, from
  // rowPx no longer floor-clamped either). nCenterOut/large-fill sweep
  // structure is unaffected by this fix, so that invariant stays.
  assert.strictEqual(d._debug.nCenterOut, 1, "fixture shape is a large fill → center-out");
  assert.strictEqual(d.stitches.length, 4923, "total record count frozen");
  assert.strictEqual(d.stitchCount, 4772, "stitch count frozen (resize-density re-freeze)");
  const first20 = [
    { x: -504, y: 504, type: "jump" }, { x: -504, y: 504, type: "stitch" }, { x: -484, y: 504, type: "stitch" },
    { x: -464, y: 504, type: "stitch" }, { x: -444, y: 504, type: "stitch" }, { x: -424, y: 504, type: "stitch" },
    { x: -404, y: 504, type: "stitch" }, { x: -384, y: 504, type: "stitch" }, { x: -364, y: 504, type: "stitch" },
    { x: -344, y: 504, type: "stitch" }, { x: -324, y: 504, type: "stitch" }, { x: -304, y: 504, type: "stitch" },
    { x: -284, y: 504, type: "stitch" }, { x: -264, y: 504, type: "stitch" }, { x: -244, y: 504, type: "stitch" },
    { x: -224, y: 504, type: "stitch" }, { x: -204, y: 504, type: "stitch" }, { x: -184, y: 504, type: "stitch" },
    { x: -164, y: 504, type: "stitch" }, { x: -144, y: 504, type: "stitch" },
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

// ---- Phase 3: per-shape auto stitch angle + per-color angle override ----

// A horizontal fill runs its long stitches along x (big |dx|, small |dy|);
// a vertical fill runs them along y. Classify a run of sew stitches by which
// half of the design (x<0 or x>0 in DST) it lands in, then sum |dx|/|dy| per
// group. Returns {left:{sx,sy}, right:{sx,sy}} — orientation of each shape.
const orientHalves = (d) => {
  const sew = d.stitches.filter((s) => s.type === "stitch");
  const acc = { left: { sx: 0, sy: 0 }, right: { sx: 0, sy: 0 } };
  for (let i = 1; i < sew.length; i++) {
    const a = sew[i - 1], b = sew[i];
    const side = (a.x < 0 && b.x < 0) ? "left" : (a.x > 0 && b.x > 0) ? "right" : null;
    if (!side) continue; // skip the cross-design travel between the two shapes
    acc[side].sx += Math.abs(b.x - a.x);
    acc[side].sy += Math.abs(b.y - a.y);
  }
  return acc;
};

// One region, two shapes of opposite orientation, well separated in x so each
// occupies its own half of the (centered) design: a WIDE-horizontal bar on the
// left, a TALL-vertical bar on the right. Forcing fill (satinMaxWidthMm ~ 0) so
// both are tatami. pxPerMm 8, big garment.
const twoShapeRegion = (extra) => {
  const wide = { outer: [{ x: 0, y: 0 }, { x: 240, y: 0 }, { x: 240, y: 60 }, { x: 0, y: 60 }], holes: [] };
  const tall = { outer: [{ x: 1000, y: 0 }, { x: 1060, y: 0 }, { x: 1060, y: 240 }, { x: 1000, y: 240 }], holes: [] };
  return Object.assign({ rgb: [0, 0, 0], shapes: [wide, tall] }, extra || {});
};
const twoShapeOpts = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };

test("buildQualityDesign: per-shape auto angle — wide vs tall shapes fill at DIFFERENT angles", () => {
  const d = DG.buildQualityDesign([twoShapeRegion()], twoShapeOpts);
  const o = orientHalves(d);
  // wide bar (left): stitches run horizontally → |dx| dominates
  assert.ok(o.left.sx > o.left.sy * 2, "wide shape fills horizontally: " + JSON.stringify(o.left));
  // tall bar (right): stitches run vertically → |dy| dominates
  assert.ok(o.right.sy > o.right.sx * 2, "tall shape fills vertically: " + JSON.stringify(o.right));
  // Pre-Phase-3 (single shared per-color angle) both would match; now they differ.
});

test("buildQualityDesign: angleOverride 0 forces BOTH shapes horizontal", () => {
  const d = DG.buildQualityDesign([twoShapeRegion({ angleOverride: 0 })], twoShapeOpts);
  const o = orientHalves(d);
  assert.ok(o.left.sx > o.left.sy * 2, "left horizontal at 0deg: " + JSON.stringify(o.left));
  assert.ok(o.right.sx > o.right.sy * 2, "right (naturally tall) forced horizontal at 0deg: " + JSON.stringify(o.right));
});

test("buildQualityDesign: angleOverride 90 forces BOTH shapes vertical", () => {
  const d = DG.buildQualityDesign([twoShapeRegion({ angleOverride: 90 })], twoShapeOpts);
  const o = orientHalves(d);
  assert.ok(o.left.sy > o.left.sx * 2, "left (naturally wide) forced vertical at 90deg: " + JSON.stringify(o.left));
  assert.ok(o.right.sy > o.right.sx * 2, "right vertical at 90deg: " + JSON.stringify(o.right));
});

test("buildQualityDesign: per-SHAPE angleOverride controls each shape independently", () => {
  // Force each shape AGAINST its natural orientation to prove per-shape control:
  // the wide-left bar forced vertical, the tall-right bar forced horizontal.
  const wide = { outer: [{ x: 0, y: 0 }, { x: 240, y: 0 }, { x: 240, y: 60 }, { x: 0, y: 60 }], holes: [], angleOverride: 90 };
  const tall = { outer: [{ x: 1000, y: 0 }, { x: 1060, y: 0 }, { x: 1060, y: 240 }, { x: 1000, y: 240 }], holes: [], angleOverride: 0 };
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [wide, tall] }], twoShapeOpts);
  const o = orientHalves(d);
  assert.ok(o.left.sy > o.left.sx * 2, "wide shape forced VERTICAL per-shape: " + JSON.stringify(o.left));
  assert.ok(o.right.sx > o.right.sy * 2, "tall shape forced HORIZONTAL per-shape: " + JSON.stringify(o.right));
});

test("buildQualityDesign: opts.angleOverrides keyed by ORIGINAL region index (survives light→dark sort)", () => {
  // Two colors given light-first; the internal sort reorders them dark-first.
  // The override map is keyed by the ORIGINAL input order, so index 1 (the dark
  // wide bar) must be the one forced vertical regardless of sew order.
  const light = { rgb: [240, 240, 240], shapes: [{ outer: [{ x: 0, y: 0 }, { x: 240, y: 0 }, { x: 240, y: 60 }, { x: 0, y: 60 }], holes: [] }] };
  const dark = { rgb: [10, 10, 10], shapes: [{ outer: [{ x: 0, y: 400 }, { x: 240, y: 400 }, { x: 240, y: 460 }, { x: 0, y: 460 }], holes: [] }] };
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };
  // original index 1 = dark → force vertical (90); index 0 = light → auto
  const d = DG.buildQualityDesign([light, dark], Object.assign({ angleOverrides: { 1: 90 } }, base));
  // Both bars are wide-horizontal, so auto → horizontal. The dark one is forced
  // vertical. Split sew stitches by color block and check orientation.
  const recs = d.stitches;
  const ci = recs.findIndex((s) => s.type === "color");
  // darkOnTop sorts LIGHT first, dark last: block A = light (orig idx 0),
  // block B = dark (orig idx 1, the one forced vertical).
  const blockA = recs.slice(0, ci).filter((s) => s.type === "stitch"); // first block (light)
  const blockB = recs.slice(ci).filter((s) => s.type === "stitch");    // second block (dark)
  const orient = (arr) => { let sx = 0, sy = 0; for (let i = 1; i < arr.length; i++) { sx += Math.abs(arr[i].x - arr[i - 1].x); sy += Math.abs(arr[i].y - arr[i - 1].y); } return { sx, sy }; };
  const oA = orient(blockA), oB = orient(blockB);
  // light bar (orig idx 0) → auto → horizontal (its natural axis)
  assert.ok(oA.sx > oA.sy * 2, "light bar (orig idx 0) auto-horizontal: " + JSON.stringify(oA));
  // dark bar (orig idx 1) → forced vertical by the override map
  assert.ok(oB.sy > oB.sx * 2, "dark bar (orig idx 1) forced vertical: " + JSON.stringify(oB));
});

test("buildQualityDesign: null angleOverride falls back to per-shape auto", () => {
  const d = DG.buildQualityDesign([twoShapeRegion({ angleOverride: null })], twoShapeOpts);
  const o = orientHalves(d);
  assert.ok(o.left.sx > o.left.sy * 2, "null override → auto: wide horizontal");
  assert.ok(o.right.sy > o.right.sx * 2, "null override → auto: tall vertical");
});

// ---- Phase 4: center-out large fills + background-first + minimizeColorChanges ----

test("buildQualityDesign: large fill (>15mm) sews center-out; first row near shape center", () => {
  // Single large square that fills a 4in garment → final bbox ~100mm both dims,
  // well above the 15mm large-fill threshold. Square PCA angle is 0 (rows
  // horizontal) so the first emitted row's DST y is meaningful. Center-out puts
  // the first row near the shape center (DST y ~ 0), not the top/bottom edge.
  const outer = sq(0, 0, 800);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }], base);
  assert.ok(d._debug.nCenterOut >= 1, "large fill must sew center-out, got nCenterOut=" + d._debug.nCenterOut);
  const first = d.stitches.filter((s) => s.type === "stitch")[0];
  // shape spans roughly DST y ±500; center-out first row must be within ~1 row
  // spacing of center (0), an edge start would be near ±500.
  assert.ok(Math.abs(first.y) < 150, "center-out first fill row near shape center, got y=" + first.y);
});

test("buildQualityDesign: center-out fill cuts its sweep reposition (one trim per center-out fill)", () => {
  // Single large square → one center-out fill, no color change, no other travel.
  const outer = sq(0, 0, 800);
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }], base);
  assert.ok(d._debug.nCenterOut >= 1, "fixture is a large center-out fill");
  // exactly one trim, inside the fill run, matching the center-out count.
  assert.strictEqual(d._debug.nTrims, d._debug.nCenterOut, "one trim per center-out fill");
  assert.ok(d.stitches.some((s) => s.type === "trim"), "a type:'trim' record exists in the fill run");
  // trims are excluded from stitchCount (Phase 1 invariant preserved).
  assert.strictEqual(d.stitchCount, d.stitches.filter((s) => s.type === "stitch").length);
  assert.strictEqual(d.stitches.filter((s) => s.type === "trim").length, d._debug.nTrims);
});

test("buildQualityDesign: small fill (<15mm) is NOT center-out", () => {
  // Two tiny squares far apart fix a large design bbox that downscales each
  // shape to ~2mm final — below the 15mm threshold → no center-out.
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: sq(0, 0, 40), holes: [] }, { outer: sq(2000, 0, 40), holes: [] }] }],
    base
  );
  assert.strictEqual(d._debug.nCenterOut, 0, "small fills must not center-out, got " + d._debug.nCenterOut);
});

test("buildQualityDesign: background-first — largest-area shape in a color emits first", () => {
  // smallA sits at the design center (nearest-neighbor-from-center would pick it
  // first); the big shape is far to the right (largest area). Background-first
  // must emit the BIG shape first regardless of proximity to center.
  const big = { outer: sq(2000, 900, 200), holes: [] };   // area 40000, far right
  const smallA = { outer: sq(1000, 950, 40), holes: [] }; // near design center
  const smallB = { outer: sq(0, 950, 40), holes: [] };    // far left
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };
  const run = (shapes) => DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes }], base).stitches.filter((s) => s.type === "stitch");
  const first = run([smallA, big, smallB])[0];
  // big is the rightmost shape → its stitches carry the largest positive DST x.
  // If NN-from-center had won, smallA (center) would be first with x ~ 0.
  assert.ok(first.x > 200, "largest shape (far right) must emit first, got x=" + first.x);
  // order independence: same first shape regardless of input order
  const first2 = run([smallB, smallA, big])[0];
  assert.strictEqual(first.x, first2.x, "background-first is input-order independent");
});

test("buildQualityDesign: minimizeColorChanges groups identical-rgb regions into one thread", () => {
  // three regions: two share the EXACT rgb, one differs.
  const rgbA = [50, 50, 50], rgbB = [200, 10, 10];
  const regions = [
    { rgb: rgbA, shapes: [{ outer: sq(0, 0, 60), holes: [] }] },
    { rgb: rgbB, shapes: [{ outer: sq(200, 0, 60), holes: [] }] },
    { rgb: rgbA, shapes: [{ outer: sq(400, 0, 60), holes: [] }] },
  ];
  const base = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, densityMm: 0.5, underlay: false, satinMaxWidthMm: 0.05 };
  const off = DG.buildQualityDesign(regions, base);
  const on = DG.buildQualityDesign(regions, Object.assign({ minimizeColorChanges: true }, base));
  const nColor = (d) => d.stitches.filter((s) => s.type === "color").length;
  assert.strictEqual(nColor(off), 2, "default: three blocks → 2 color changes");
  assert.strictEqual(nColor(on), 1, "minimize: two identical-rgb blocks share a thread → 1 color change");
  assert.strictEqual(on.colorCount, 2, "minimize: only 2 distinct thread colors");
  assert.strictEqual(off.colorCount, 3, "default: 3 color records");
});

// ---- Slice 3 Task 1: explicit size (targetWidthMm) + offset (offsetXMm/offsetYMm) ----

const expect_close = (a, b, tol) => assert.ok(Math.abs(a - b) <= tol, `expected ${a} close to ${b} (tol ${tol})`);

test("buildLetteringDesign: targetWidthMm sets the final width (clamped to hoop)", () => {
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8 };
  const d40 = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 40 });
  expect_close(d40.widthMM, 40, 1.5);
  const dHuge = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm: 500 });
  assert.ok(dHuge.widthMM <= 5 * 25.4 + 1, "clamped to hoop width");
});

test("buildLetteringDesign: offsets translate all stitches", () => {
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 };
  const d0 = DG.buildLetteringDesign(font, "AB", base);
  const d10 = DG.buildLetteringDesign(font, "AB", { ...base, offsetXMm: 10, offsetYMm: -5 });
  const s0 = d0.stitches.find((s) => s.type === "stitch");
  const s1 = d10.stitches.find((s) => s.type === "stitch");
  assert.strictEqual(s1.x - s0.x, 100); // 10mm = 100 DST units
  assert.strictEqual(s1.y - s0.y, -50); // -5mm = -50 DST units
});

test("buildLetteringDesign: opts absent (no targetWidthMm/offsets) stays back-compat", () => {
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8 };
  const a = DG.buildLetteringDesign(font, "AB", base);
  const b = DG.buildLetteringDesign(font, "AB", { ...base });
  assert.deepStrictEqual(a, b);
});

test("buildLetteringDesign: rotationDeg 180 negates every stitch point relative to unrotated (upside-down = point negation about center)", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "AB", base);
  const d180 = DG.buildLetteringDesign(font, "AB", Object.assign({ rotationDeg: 180 }, base));
  assert.strictEqual(d180.stitches.length, d0.stitches.length, "rotation must not add/remove stitch records");
  for (let i = 0; i < d0.stitches.length; i++) {
    assert.strictEqual(d180.stitches[i].type, d0.stitches[i].type, `type mismatch at record ${i}`);
    assert.ok(Math.abs(d180.stitches[i].x - -d0.stitches[i].x) <= 1, `x mismatch at record ${i}: ${d180.stitches[i].x} vs ${-d0.stitches[i].x}`);
    assert.ok(Math.abs(d180.stitches[i].y - -d0.stitches[i].y) <= 1, `y mismatch at record ${i}: ${d180.stitches[i].y} vs ${-d0.stitches[i].y}`);
  }
  // 180 preserves the bounding box dimensions exactly (a rectangle rotated
  // 180 about its own center has the same axis-aligned bbox).
  assert.ok(Math.abs(d180.widthMM - d0.widthMM) < 0.5, "width should be unchanged at 180deg");
  assert.ok(Math.abs(d180.heightMM - d0.heightMM) < 0.5, "height should be unchanged at 180deg");
});

test("buildLetteringDesign: rotationDeg 90 swaps the reported width/height orientation and rotationDeg 0/absent is byte-identical to today", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "SD WHEEL", base);
  const dExplicit0 = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: 0 }, base));
  assert.deepStrictEqual(dExplicit0, d0, "rotationDeg:0 must be byte-identical to omitting it");
  const d90 = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: 90 }, base));
  // "SD WHEEL" is much wider than tall unrotated; rotated 90 it must become
  // much taller than wide.
  assert.ok(d0.widthMM > d0.heightMM * 2, "fixture assumption: unrotated text is landscape");
  assert.ok(d90.heightMM > d90.widthMM * 2, "rotated 90deg text must report portrait dimensions");
});

test("buildLetteringDesign: auto-fit (no targetWidthMm) stays within the hoop after a non-180 rotation, on a non-square hoop", () => {
  // Regression test (MASTER_SCOPE area 3): a design that auto-fits BEFORE a
  // rotation must still fit AFTER it. The fit-to-hoop scale used to be
  // computed from the UNROTATED glyph bbox while rotation was applied only
  // as a post-transform on the emitted stitches -- so on a non-square hoop,
  // rotating a design that auto-fit at 0deg to something other than a
  // multiple of 180 could blow the actual (correctly reported) rotated
  // bbox straight through the hoop bounds with nothing left to reclamp it.
  // hat_front-shaped hoop: wide and short (5in x 2.25in), matching the real
  // garment in src/garments.js, so this reproduces the exact real-world case.
  const garment = { widthIn: 5.0, heightIn: 2.25 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const hoopWmm = 5.0 * 25.4, hoopHmm = 2.25 * 25.4;

  const d0 = DG.buildLetteringDesign(font, "SD WHEEL", base);
  // Sanity: unrotated auto-fit actually uses (most of) the hoop -- otherwise
  // this fixture wouldn't be exercising the fit path at all.
  assert.ok(d0.widthMM > hoopWmm * 0.9, "fixture assumption: unrotated auto-fit is width-bound near the hoop edge");
  assert.ok(d0.widthMM <= hoopWmm + 0.5 && d0.heightMM <= hoopHmm + 0.5, "unrotated auto-fit must already fit the hoop");

  for (const rot of [90, 45, 270, -30]) {
    const d = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: rot }, base));
    assert.ok(
      d.widthMM <= hoopWmm + 0.5,
      `rotationDeg ${rot}: auto-fit width ${d.widthMM}mm must stay within the hoop's ${hoopWmm}mm width`
    );
    assert.ok(
      d.heightMM <= hoopHmm + 0.5,
      `rotationDeg ${rot}: auto-fit height ${d.heightMM}mm must stay within the hoop's ${hoopHmm}mm height`
    );
  }
});

test("buildLetteringDesign: an explicit targetWidthMm (manual size, post-rotation convention) stays within the hoop after a non-180 rotation", () => {
  // Same failure mode as the auto-fit test above, but for a design the user
  // has manually resized (sizeMm set, auto-fit off) -- targetWidthMm is
  // documented (matching buildImportedDesign) as the desired width AFTER
  // rotation, so a manually-sized design rotated to a new angle must also
  // still respect that same post-rotation width/hoop contract.
  const garment = { widthIn: 5.0, heightIn: 2.25 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, targetWidthMm: 100 };
  const hoopWmm = 5.0 * 25.4, hoopHmm = 2.25 * 25.4;

  for (const rot of [0, 90, 45, 270]) {
    const d = DG.buildLetteringDesign(font, "SD WHEEL", Object.assign({ rotationDeg: rot }, base));
    assert.ok(d.widthMM <= hoopWmm + 0.5, `rotationDeg ${rot}: width ${d.widthMM}mm must stay within the hoop`);
    assert.ok(d.heightMM <= hoopHmm + 0.5, `rotationDeg ${rot}: height ${d.heightMM}mm must stay within the hoop`);
  }
});

test("buildLetteringDesign: colorRanges absent/empty is byte-identical to today's single-color output", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, rgb: [10, 20, 30] };
  const dNoField = DG.buildLetteringDesign(font, "AB", base);
  const dEmpty = DG.buildLetteringDesign(font, "AB", Object.assign({ colorRanges: [] }, base));
  assert.deepStrictEqual(dEmpty, dNoField);
  assert.strictEqual(dNoField.colors.length, 1);
  assert.ok(!dNoField.stitches.some((s) => s.type === "color"), "no color-change record when there's only one color");
});

test("buildLetteringDesign: a colorRange covering only the first character inserts exactly one trim+color pair at the glyph boundary", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const d = DG.buildLetteringDesign(font, "AB", {
    garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false,
    rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 1, colorRgb: [200, 30, 30] }],
  });
  assert.strictEqual(d.colors.length, 2, "range color + base color");
  assert.strictEqual(d.colorCount, 2, "colorCount matches colors.length");
  assert.deepStrictEqual([d.colors[0].r, d.colors[0].g, d.colors[0].b], [200, 30, 30], "the FIRST-used color is the range's, since char 0 sews first");
  assert.deepStrictEqual([d.colors[1].r, d.colors[1].g, d.colors[1].b], [10, 20, 30]);
  const colorChangeIdxs = d.stitches.map((s, i) => (s.type === "color" ? i : -1)).filter((i) => i >= 0);
  assert.strictEqual(colorChangeIdxs.length, 1, "exactly one color-change boundary for one range covering one of two characters");
  // Every "color" record is immediately preceded by a "trim" record at the same point.
  const ci = colorChangeIdxs[0];
  assert.strictEqual(d.stitches[ci - 1].type, "trim");
  assert.strictEqual(d.stitches[ci - 1].x, d.stitches[ci].x);
  assert.strictEqual(d.stitches[ci - 1].y, d.stitches[ci].y);
});

test("buildLetteringDesign: a colorRange spanning the WHOLE string produces only one color and no color-change records", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const d = DG.buildLetteringDesign(font, "AB", {
    garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false,
    rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 2, colorRgb: [200, 30, 30] }],
  });
  assert.strictEqual(d.colors.length, 1);
  assert.ok(!d.stitches.some((s) => s.type === "color"));
});

test("buildLetteringDesign: weightPreset 'normal' (or absent) is byte-identical to today's output", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const dNoField = DG.buildLetteringDesign(font, "Kent", base);
  const dNormal = DG.buildLetteringDesign(font, "Kent", Object.assign({ weightPreset: "normal" }, base));
  assert.deepStrictEqual(dNormal, dNoField);
});

test("buildLetteringDesign: weightPreset 'bold' widens satin cross-stitches vs 'thin', measured on the same glyph", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  function avgCrossWidth(design) {
    // Consecutive "stitch" records alternate rail-A/rail-B in a satin run;
    // the width-spanning crosses are adjacent pairs. Average the distance
    // between EVERY adjacent stitch pair as a coarse but monotonic proxy for
    // "how wide is this column" -- sufficient to confirm bold > thin without
    // needing to reconstruct which pairs are crosses vs connectors.
    let sum = 0, n = 0, prev = null;
    for (const s of design.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) { sum += Math.hypot(s.x - prev.x, s.y - prev.y); n++; }
      prev = s;
    }
    return n ? sum / n : 0;
  }
  const thin = DG.buildLetteringDesign(font, "H", Object.assign({ weightPreset: "thin" }, base));
  const bold = DG.buildLetteringDesign(font, "H", Object.assign({ weightPreset: "bold" }, base));
  assert.ok(avgCrossWidth(bold) > avgCrossWidth(thin), `bold avg spacing (${avgCrossWidth(bold)}) should exceed thin's (${avgCrossWidth(thin)})`);
});

test("buildLetteringDesign: slantDeg absent/0 is byte-identical to today's output; a nonzero value changes the generated geometry", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "H", base);
  const dExplicit0 = DG.buildLetteringDesign(font, "H", Object.assign({ slantDeg: 0 }, base));
  assert.deepStrictEqual(dExplicit0, d0);
  const dSlant = DG.buildLetteringDesign(font, "H", Object.assign({ slantDeg: 15 }, base));
  // At the layoutText level, slant re-samples the same stations and never
  // adds/removes any for a FIXED spacingMm (verified exactly in
  // satinfont.test.js). Here, though, buildLetteringDesign's two-pass
  // fit-to-width scaling sits in between: slant nudges the glyph bbox by a
  // fraction of a mm (the clamped-end taper moves the outermost rail contact
  // very slightly), which nudges the fit scale by the same tiny amount,
  // which can push one column's step count across a Math.ceil() rounding
  // boundary. A few stitches' difference here is expected numerical noise,
  // not a functional regression -- assert "close", not byte-identical.
  const countDiff = Math.abs(dSlant.stitches.length - d0.stitches.length);
  assert.ok(countDiff <= 10, `slant should re-sample roughly the same station count, not add/remove stitches wholesale (diff ${countDiff})`);
  const anyDiffer = d0.stitches.some((s, i) => Math.abs(s.x - dSlant.stitches[i].x) > 1 || Math.abs(s.y - dSlant.stitches[i].y) > 1);
  assert.ok(anyDiffer, "slantDeg:15 must produce visibly different stitch positions");
});

test("buildQualityDesign: targetWidthMm sets the final width (clamped to hoop)", () => {
  // 400x400 px square at pxPerMm 8 -> 50x50mm natural bbox (square, so width and
  // height scale identically, making the expected result easy to reason about).
  const outer = sq(0, 0, 400);
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const d40 = DG.buildQualityDesign(region, { ...base, targetWidthMm: 40 });
  expect_close(d40.widthMM, 40, 1.5);
  const dHuge = DG.buildQualityDesign(region, { ...base, targetWidthMm: 500 });
  assert.ok(dHuge.widthMM <= 5 * 25.4 + 1, "clamped to hoop width");
});

test("buildQualityDesign: offsets translate all stitches", () => {
  const outer = sq(0, 0, 400);
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3, targetWidthMm: 40 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const d0 = DG.buildQualityDesign(region, base);
  const d10 = DG.buildQualityDesign(region, { ...base, offsetXMm: 10, offsetYMm: -5 });
  const s0 = d0.stitches.find((s) => s.type === "stitch");
  const s1 = d10.stitches.find((s) => s.type === "stitch");
  assert.strictEqual(s1.x - s0.x, 100); // 10mm = 100 DST units
  assert.strictEqual(s1.y - s0.y, -50); // -5mm = -50 DST units
});

test("buildQualityDesign: opts absent (no targetWidthMm/offsets) stays back-compat", () => {
  const outer = sq(0, 0, 400);
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, densityMm: 0.5, underlay: false, satinMaxWidthMm: 3 };
  const region = [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [] }] }];
  const a = DG.buildQualityDesign(region, base);
  const b = DG.buildQualityDesign(JSON.parse(JSON.stringify(region)), { ...base });
  assert.deepStrictEqual(a, b);
});

// ---- Cap center-out lettering (crown-distortion-safe sew order) ------------
// On cap garments (hat_front / beanie — the same capMode predicate the image
// pipeline uses) lettering glyphs sew bottom-line-first and center-out within
// each line. Everywhere else (including every garment object without an `id`,
// like all the fixtures above) the order is untouched.

test("buildLetteringDesign: cap garment sews the middle glyph first (center-out)", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const flat = DG.buildLetteringDesign(font, "AVA", Object.assign({ garment: { widthIn: 5, heightIn: 2.25 } }, base));
  const cap = DG.buildLetteringDesign(font, "AVA", Object.assign({ garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 } }, base));
  const firstStitch = (d) => d.stitches.find((s) => s.type === "stitch");
  const halfW = (d) => (d.widthMM * 10) / 2; // DST units
  // Non-cap: text order — the leading "A" sews first, well left of center.
  assert.ok(firstStitch(flat).x < -halfW(flat) / 3, "non-cap first stitch is in the left third");
  // Cap: the middle "V" sews first — first stitch lands in the central third.
  assert.ok(Math.abs(firstStitch(cap).x) < halfW(cap) / 3, "cap first stitch is in the central third");
  // Same glyphs, same geometry: stitch COUNT is preserved (order-only change
  // aside from connector/trim differences, sewn-stitch totals stay close).
  assert.ok(Math.abs(cap.stitchCount - flat.stitchCount) <= flat.stitchCount * 0.1, "reorder must not meaningfully change stitch count");
});

test("buildLetteringDesign: cap garment sews the bottom line before the top line", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const flat = DG.buildLetteringDesign(font, "AAA\nVVV", Object.assign({ garment: { widthIn: 5, heightIn: 2.25 } }, base));
  const cap = DG.buildLetteringDesign(font, "AAA\nVVV", Object.assign({ garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 } }, base));
  const firstStitch = (d) => d.stitches.find((s) => s.type === "stitch");
  // DST +y is UP and the design is centered: top line has y > 0, bottom < 0.
  assert.ok(firstStitch(flat).y > 0, "non-cap starts on the TOP line (text order)");
  assert.ok(firstStitch(cap).y < 0, "cap starts on the BOTTOM line (bill toward crown)");
});

test("buildLetteringDesign: cap reorder is deterministic and never drops glyph stitches", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const a = DG.buildLetteringDesign(font, "SD WHEEL\nJR", base);
  const b = DG.buildLetteringDesign(font, "SD WHEEL\nJR", base);
  assert.deepStrictEqual(a, b, "same input, same output");
  assert.ok(a.stitchCount > 0);
});

test("buildLetteringDesign: garment without an id (all pre-cap fixtures) is untouched by capMode", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d = DG.buildLetteringDesign(font, "AB", base);
  const firstStitch = d.stitches.find((s) => s.type === "stitch");
  assert.ok(firstStitch.x < 0, "no-id garment still sews in text order (left glyph first)");
});

// ---- Lettering parity round: mirrorX / mirrorY --------------------------
// Mirror is a pure post-transform on the generated DST-space stitches,
// applied about the element's bbox center in the documented order
// center -> MIRROR -> ROTATE -> offset (see buildLetteringDesign). The
// record STREAM (types, counts, order) must be untouched — only positions
// reflect.

test("buildLetteringDesign: mirrorX/mirrorY absent or false is byte-identical to today's output", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4 };
  const d0 = DG.buildLetteringDesign(font, "Kent", base);
  const dFalse = DG.buildLetteringDesign(font, "Kent", { ...base, mirrorX: false, mirrorY: false });
  assert.deepStrictEqual(dFalse, d0);
});

test("buildLetteringDesign: mirrorX on 'Kent' is an exact reflection — x negated about center, y untouched, every record's type preserved index-for-index", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  // underlay ON and a colorRange so the stream really contains trims, jumps
  // AND a color-change record — the per-record loop below then pins that a
  // mirror moves none of them and mirrors all their positions exactly.
  const base = {
    garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4,
    rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 1, colorRgb: [200, 30, 30] }],
  };
  const d0 = DG.buildLetteringDesign(font, "Kent", base);
  const dX = DG.buildLetteringDesign(font, "Kent", { ...base, mirrorX: true });
  assert.strictEqual(dX.stitches.length, d0.stitches.length, "mirror must not add/remove records");
  for (let i = 0; i < d0.stitches.length; i++) {
    assert.strictEqual(dX.stitches[i].type, d0.stitches[i].type, `record type at ${i}`);
    // Math.round(-v) vs -Math.round(v) differ by at most 1 (the exact-.5 case).
    assert.ok(Math.abs(dX.stitches[i].x - -d0.stitches[i].x) <= 1, `x at ${i}: ${dX.stitches[i].x} vs ${-d0.stitches[i].x}`);
    assert.strictEqual(dX.stitches[i].y, d0.stitches[i].y, `y at ${i} must be untouched by mirrorX`);
  }
  // The fixture actually exercises what the loop pins.
  const count = (d, t) => d.stitches.filter((s) => s.type === t).length;
  assert.ok(count(d0, "trim") > 0, "fixture must contain trims");
  assert.ok(count(d0, "jump") > 0, "fixture must contain jumps");
  assert.strictEqual(count(d0, "color"), 1, "fixture must contain a color change");
  for (const t of ["trim", "jump", "color", "stitch"]) assert.strictEqual(count(dX, t), count(d0, t), t + " count preserved");
  // bbox is symmetric about the very center being mirrored across:
  // reported dims unchanged, exactly.
  assert.strictEqual(dX.widthMM, d0.widthMM);
  assert.strictEqual(dX.heightMM, d0.heightMM);
  assert.strictEqual(dX.stitchCount, d0.stitchCount);
});

test("buildLetteringDesign: mirrorY negates y about center and leaves x untouched", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4 };
  const d0 = DG.buildLetteringDesign(font, "Kent", base);
  const dY = DG.buildLetteringDesign(font, "Kent", { ...base, mirrorY: true });
  assert.strictEqual(dY.stitches.length, d0.stitches.length);
  for (let i = 0; i < d0.stitches.length; i++) {
    assert.strictEqual(dY.stitches[i].type, d0.stitches[i].type, `record type at ${i}`);
    assert.strictEqual(dY.stitches[i].x, d0.stitches[i].x, `x at ${i} must be untouched by mirrorY`);
    assert.ok(Math.abs(dY.stitches[i].y - -d0.stitches[i].y) <= 1, `y at ${i}: ${dY.stitches[i].y} vs ${-d0.stitches[i].y}`);
  }
  assert.strictEqual(dY.widthMM, d0.widthMM);
  assert.strictEqual(dY.heightMM, d0.heightMM);
});

test("buildLetteringDesign: mirror composes with rotation in the documented order — mirror about the bbox center FIRST, then rotationDeg", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false };
  const d0 = DG.buildLetteringDesign(font, "Kent", base);
  const dMR = DG.buildLetteringDesign(font, "Kent", { ...base, mirrorX: true, rotationDeg: 90 });
  // Documented order on a point (x,y): mirrorX -> (-x,y), then rotate 90
  // (T()'s convention: (px,py) -> (-py,px)) -> (-y,-x).
  // The REVERSE order (rotate then mirror) would give (y,x) instead — the
  // loop below distinguishes the two on every record.
  assert.strictEqual(dMR.stitches.length, d0.stitches.length);
  let distinguishes = false;
  for (let i = 0; i < d0.stitches.length; i++) {
    const a = d0.stitches[i], b = dMR.stitches[i];
    assert.strictEqual(b.type, a.type, `record type at ${i}`);
    assert.ok(Math.abs(b.x - -a.y) <= 1, `x at ${i}: expected ~${-a.y}, got ${b.x}`);
    assert.ok(Math.abs(b.y - -a.x) <= 1, `y at ${i}: expected ~${-a.x}, got ${b.y}`);
    if (Math.abs(b.x - a.y) > 2 || Math.abs(b.y - a.x) > 2) distinguishes = true;
  }
  assert.ok(distinguishes, "fixture must actually distinguish mirror-then-rotate from rotate-then-mirror");
});

test("buildLetteringDesign: cap garment's bottom-up sew order follows where lines ACTUALLY land after mirrorY", () => {
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  // Line 1 "AAA" tagged red via colorRanges; base color for "VVV". On a cap,
  // the FIRST-SEWN line's color is colors[0]: without mirror the bottom line
  // is VVV (base), with mirrorY the AAA line lands at the bottom and must
  // sew first — the reorder uses post-mirror final-space centroids.
  const base = {
    garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, emMm: 18, densityMm: 0.4,
    underlay: false, rgb: [10, 20, 30], colorRanges: [{ startIdx: 0, endIdx: 3, colorRgb: [200, 0, 0] }],
  };
  const capPlain = DG.buildLetteringDesign(font, "AAA\nVVV", base);
  const capMirY = DG.buildLetteringDesign(font, "AAA\nVVV", { ...base, mirrorY: true });
  assert.deepStrictEqual([capPlain.colors[0].r, capPlain.colors[0].g, capPlain.colors[0].b], [10, 20, 30], "no mirror: bottom line VVV (base color) sews first");
  assert.deepStrictEqual([capMirY.colors[0].r, capMirY.colors[0].g, capMirY.colors[0].b], [200, 0, 0], "mirrorY: AAA (red) is now the bottom line and sews first");
});

test("buildLetteringDesign: the counter guard holds bold where a real font's counters and junctions would close, and thin is untouched by it", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, targetWidthMm: 8 };
  // 2.6 mm caps: the counters of e, n and t are under or near the 0.5 mm
  // floor once bold's 0.3 mm is asked for. The guard holds rail stations,
  // the stitch count barely moves (the crosses are shorter, not fewer).
  const bold = DG.buildLetteringDesign(font, "Kent", { ...base, weightPreset: "bold" });
  const boldOff = DG.buildLetteringDesign(font, "Kent", { ...base, weightPreset: "bold", counterGuard: false });
  assert.ok(bold.lettering.counterHeld > 0, "expected held stations on 2.6 mm bold lettering");
  assert.strictEqual(bold.lettering.weightMm, 0.3);
  assert.ok(Math.abs(bold.stitchCount - boldOff.stitchCount) <= Math.ceil(0.01 * boldOff.stitchCount));
  assert.notDeepStrictEqual(bold.stitches, boldOff.stitches, "the guard must actually move rails");
  // Thin narrows; nothing to hold, and the guard flag changes nothing.
  const thin = DG.buildLetteringDesign(font, "Kent", { ...base, weightPreset: "thin" });
  const thinOff = DG.buildLetteringDesign(font, "Kent", { ...base, weightPreset: "thin", counterGuard: false });
  assert.deepStrictEqual(thin, thinOff);
  assert.strictEqual(thin.lettering.counterHeld, 0);
  // Normal never reports a weight or a hold.
  const normal = DG.buildLetteringDesign(font, "Kent", base);
  assert.strictEqual(normal.lettering.weightMm, 0);
  assert.strictEqual(normal.lettering.counterHeld, 0);
});

test("buildLetteringDesign: short stitches move penetrations on the inside of bends and never change the stitch count", () => {
  const garment = { widthIn: 8, heightIn: 8 };
  const font = require("../test/fixtures/fonts/geneva_simple.json");
  const base = { garment, pxPerMm: 8, emMm: 18, densityMm: 0.4, underlay: false, targetWidthMm: 30 };
  const on = DG.buildLetteringDesign(font, "SOC", base);
  const off = DG.buildLetteringDesign(font, "SOC", { ...base, shortStitch: false });
  assert.strictEqual(on.stitchCount, off.stitchCount);
  assert.ok(on.lettering.shortStitches > 0);
  assert.strictEqual(off.lettering.shortStitches, 0);
  assert.notDeepStrictEqual(on.stitches, off.stitches);
  // Every penetration the guard moved travelled at most 0.6 mm (6 DST units).
  let moved = 0;
  for (let i = 0; i < on.stitches.length; i++) {
    const a = on.stitches[i], b = off.stitches[i];
    if (a.type !== "stitch") continue;
    const d = Math.hypot(a.x - b.x, a.y - b.y);
    if (d > 0) { moved++; assert.ok(d <= 6 + 1, `a short stitch moved ${d / 10} mm, over the 0.6 mm cap`); }
  }
  assert.ok(moved > 0 && moved <= on.lettering.shortStitches + 2);
});
