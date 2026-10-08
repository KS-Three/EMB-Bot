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

// --- opts.fillColumns: the hole stays empty of THREAD, not only of needle ----
//
// The test above counts penetrations inside the hole and has always passed.
// What it cannot see is the thread between two penetrations either side of
// it: today every fill row crosses the hole, as a float when the hole is wider
// than a stitch and as a stitch when it is not (fill.js, `opts.columns`).

// Thread laid through the open interior of a centred square, read off the
// stream the encoders get. A move lays thread unless the thread has been cut
// since the last penetration.
function threadAcross(d, half) {
  return threadAcrossBox(d, { x0: -half, y0: -half, x1: half, y1: half });
}

// The same reading through any box, in design units (0.1 mm, centred, y up).
function threadAcrossBox(d, b) {
  const inside = (x, y) => x > b.x0 && x < b.x1 && y > b.y0 && y < b.y1;
  let sewn = 0, floats = 0, cut = true, prev = null;
  for (const s of d.stitches) {
    if (s.type === "end") break;   // the sentinel at the origin is not a move (dst.js stops on it)
    if (s.type === "trim") { cut = true; prev = s; continue; }
    if (prev && !cut) {
      let hit = false;
      for (let k = 1; k < 40 && !hit; k++) hit = inside(prev.x + (s.x - prev.x) * k / 40, prev.y + (s.y - prev.y) * k / 40);
      if (hit) { if (s.type === "stitch") sewn++; else floats++; }
    }
    if (s.type === "stitch") cut = false;
    prev = s;
  }
  return { sewn, floats };
}

// The annulus of the test above: hole edges land near +-305 units, so 290 is
// well inside it.
const ANNULUS = [{ rgb: [10, 10, 10], shapes: [{ outer: sq(0, 0, 100), holes: [sq(20, 20, 60)] }] }];
const ANNULUS_OPTS = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, densityMm: 0.5, satinMaxWidthMm: 3 };

test("fillColumns: a fill lays no thread across its hole", () => {
  const d = DG.buildQualityDesign(ANNULUS, Object.assign({ underlay: false, fillColumns: true }, ANNULUS_OPTS));
  assert.ok(d.stitches.filter((s) => s.type === "stitch").length > 100);
  assert.deepStrictEqual(threadAcross(d, 290), { sewn: 0, floats: 0 });
});

test("fillColumns: the underlay under a holed fill stays out of the hole too", () => {
  // Both underlay routes that lay tatami rows: the no-fabric lattice, and a
  // fabric preset's named style. A float there is the worst kind -- it is the
  // one thread in the hole nothing will ever cover.
  for (const extra of [{}, { fabric: fab({ fillUnderlay: "double_lattice", pullCompMm: 0 }) }, { fabric: fab({ fillUnderlay: "edge_zigzag", pullCompMm: 0 }) }]) {
    const d = DG.buildQualityDesign(ANNULUS, Object.assign({ underlay: true, fillColumns: true }, ANNULUS_OPTS, extra));
    assert.deepStrictEqual(threadAcross(d, 290), { sewn: 0, floats: 0 },
      "underlay route: " + (extra.fabric ? extra.fabric.fillUnderlay : "no fabric"));
  }
});

// A shape is several RUNS -- an underlay round the outside, one round each
// hole, then the fill -- and the frame moves from the end of one to the start
// of the next with the thread still attached. Under the fill that float is
// hidden. Across a hole, or across the mouth of a U, nothing ever covers it.
// 10 px/mm and a target width equal to the drawing's, so 1 px is 1 unit and
// the boxes below are the drawing's own, centred, y flipped.
const MANUAL = (widthMm) => ({ garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: widthMm,
  darkOnTop: false, underlay: true, fabric: fab({ fillUnderlay: "edge_run" }) });
const boxPx = (x0, y0, x1, y1) => [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }];

test("fillColumns: the move between two runs of one shape is cut where it would cross a hole", () => {
  // 26 x 36 mm with two counters. Centre (130, 180); each hole box is taken
  // 1 mm in from its rim, because the fill's pull comp and the hole's own
  // edge run both legitimately sit just inside it.
  const shape = { outer: boxPx(0, 0, 260, 360), holes: [boxPx(80, 60, 180, 140), boxPx(80, 200, 200, 300)], tierOverride: "fill" };
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [shape] }], Object.assign({ fillColumns: true }, MANUAL(26)));
  assert.deepStrictEqual(threadAcrossBox(d, { x0: -40, y0: 50, x1: 40, y1: 110 }), { sewn: 0, floats: 0 }, "upper counter");
  assert.deepStrictEqual(threadAcrossBox(d, { x0: -40, y0: -110, x1: 60, y1: -30 }), { sewn: 0, floats: 0 }, "lower counter");
});

test("fillColumns: nor is it carried across the open mouth of a U", () => {
  // 36 x 36 mm, a 14 mm notch 24 mm deep from the top edge. Centre (180, 180).
  // The outline is drawn from the RIGHT arm's corner, so the edge run under
  // the fill ends there while the fill begins on the left arm: the move
  // between them is straight across the mouth.
  const u = { outer: [{ x: 250, y: 0 }, { x: 360, y: 0 }, { x: 360, y: 360 }, { x: 0, y: 360 }, { x: 0, y: 0 }, { x: 110, y: 0 }, { x: 110, y: 240 }, { x: 250, y: 240 }], holes: [], tierOverride: "fill" };
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [u] }], Object.assign({ fillColumns: true }, MANUAL(36)));
  assert.deepStrictEqual(threadAcrossBox(d, { x0: -60, y0: -50, x1: 60, y1: 180 }), { sewn: 0, floats: 0 });
});

test("fillColumns: a satin shape is sewn exactly as it is without it", () => {
  // The flag is about FILLS. A thin C forced satin has the same kind of move
  // (its underlay ends on one arm, the satin starts on the other), and cutting
  // that is a separate call with its own bill on satin-heavy art. Three
  // underlay styles, because two of them lay tatami rows that fork.
  const c = [{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 20 }, { x: 20, y: 20 }, { x: 20, y: 180 }, { x: 200, y: 180 }, { x: 200, y: 200 }, { x: 0, y: 200 }];
  for (const satinUnderlay of ["edge_run", "zigzag", "edge_zigzag"]) {
    const build = (fillColumns) => DG.buildQualityDesign(
      [{ rgb: [0, 0, 0], shapes: [{ outer: c, holes: [], tierOverride: "satin" }] }],
      { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 20, darkOnTop: false, underlay: true, fabric: fab({ satinUnderlay }), fillColumns });
    assert.deepStrictEqual(build(true).stitches, build(false).stitches, "satin underlay " + satinUnderlay);
  }
});

// --- what an independent audit of the first build found (2026-10-03) ---------
//
// The boxes above sit well inside each hole, on two shapes, and that is how
// they passed while UNDERLAY rows -- 2 to 2.5 mm apart -- still put thread 1.7
// to 2.2 mm into a cut-out and outside an outline. "A row turn clips a corner
// by under one pitch" is harmless at 0.15 mm and visible at 2. These measure
// the thing itself: mm of thread lying over ground the shape does not fill,
// deeper than `tolMm` from every edge. 10 px/mm and a target width equal to
// the drawing's, so the stream is the drawing's own px, centred, y flipped.
const FABRICS = require("../src/fabrics.js");

function openGroundMm(d, shape, tolMm, skipRun) {
  // `skipRun`: leave out one run (an index into `d.runs`). The edge run under
  // a fill is not a tatami pass and is not what the flag governs.
  const skip = skipRun == null ? null : d.runs[skipRun];
  const rings = [shape.outer].concat(shape.holes || []);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of shape.outer) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, tol = tolMm * 10;
  const edges = [];
  for (const r of rings) for (let i = 0; i < r.length; i++) edges.push([r[i], r[(i + 1) % r.length]]);
  const inside = (p) => {
    let c = false;
    for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c;
    return c;
  };
  const nearEdge = (p) => edges.some(([u, v]) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
    const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)) <= tol;
  });
  let sewn = 0, floats = 0, attached = false, prev = null;
  for (let i = 0; i < d.stitches.length; i++) {
    const s = d.stitches[i];
    if (s.type === "end") break;
    if (s.type === "trim") { attached = false; prev = s; continue; }
    if (prev && attached && !(skip && i > skip.i0 && i <= skip.i1)) {
      const a = { x: prev.x + cx, y: cy - prev.y }, b = { x: s.x + cx, y: cy - s.y };
      const len = Math.hypot(b.x - a.x, b.y - a.y), n = Math.max(1, Math.ceil(len / 0.5));
      let open = 0;
      for (let k = 0; k < n; k++) {
        const p = { x: a.x + (b.x - a.x) * (k + 0.5) / n, y: a.y + (b.y - a.y) * (k + 0.5) / n };
        if (!inside(p) && !nearEdge(p)) open += len / n;
      }
      if (s.type === "stitch") sewn += open; else floats += open;
    }
    if (s.type === "stitch") attached = true;
    prev = s;
  }
  return { sewn: Math.round(sewn) / 10, floats: Math.round(floats) / 10 };
}

const drawn = (shape, widthPx, extra) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [Object.assign({ tierOverride: "fill" }, shape)] }],
  Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: widthPx / 10, darkOnTop: false, underlay: true, fillColumns: true }, extra || {}));
const ring = (pts) => pts.map(([x, y]) => ({ x, y }));

test("fillColumns: underlay rows 2 mm apart do not sew through the corner of a cut-out", () => {
  // The cap preset's zigzag underlay. One of its rows lands on the cut-out's
  // wall, the spans either side chain into one column, and the row turn inside
  // that column ran 12 mm through the hole, 1.7 mm from its wall.
  const badge = { outer: boxPx(0, 0, 400, 400), holes: [boxPx(60, 140, 180, 260), boxPx(285, 185, 315, 215)] };
  const d = drawn(badge, 400, { garment: { id: "hat_front", widthIn: 4, heightIn: 4 }, fabric: FABRICS.getFabric("structured_cap") });
  assert.deepStrictEqual(openGroundMm(d, badge, 1.0), { sewn: 0, floats: 0 });
});

test("fillColumns: a shape whose rows never fork still does not float outside its own outline", () => {
  // No row of a T is split, so the first build left it to the old walk, whose
  // turn from the bar's last underlay row to the stem's first is a 22 mm float
  // 2 mm outside the stem. A wide U with no fabric does the same.
  const t = { outer: ring([[0, 0], [350, 0], [350, 105], [227.5, 105], [227.5, 350], [122.5, 350], [122.5, 105], [0, 105]]), holes: [] };
  assert.deepStrictEqual(openGroundMm(drawn(t, 350), t, 1.0), { sewn: 0, floats: 0 }, "T");
  const u = { outer: ring([[0, 0], [140, 0], [140, 180], [300, 180], [300, 0], [440, 0], [440, 280], [0, 280]]), holes: [] };
  assert.deepStrictEqual(openGroundMm(drawn(u, 440), u, 1.0), { sewn: 0, floats: 0 }, "wide U");
});

test("fillColumns: thread is not carried across the inside corner of an L", () => {
  // Rows forced along the leg, so the underlay's rows run across it: the turn
  // from the last row under the bar to the first under the leg crossed the
  // open corner, 20 mm of float. No fabric, so no pull compensation sits
  // outside the outline and the tolerance can be tight.
  //
  // Every run counts, the EDGE run included. Without the flag that run steps
  // 2 mm at a time round the inset outline and chords across this same corner
  // (0.9 mm of stitch, 0.6 mm out); with it, the run keeps its corners.
  const l = { outer: ring([[0, 0], [300, 0], [300, 100], [100, 100], [100, 335], [0, 335]]), holes: [boxPx(210, 87, 250, 97)], angleOverride: 90 };
  const d = drawn(l, 300);
  assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "underlay", "fill"]);
  assert.deepStrictEqual(openGroundMm(d, l, 0.3), { sewn: 0, floats: 0 });
  const off = drawn(l, 300, { fillColumns: false });
  assert.ok(openGroundMm(off, l, 0.3).sewn > openGroundMm(off, l, 0.3, 0).sewn,
    "without the flag the edge run (run 0) does lay thread over this corner, or the line above proves nothing");
});

test("fillColumns: the edge run round a hole lies in the fill, not in the hole", () => {
  // It was inset "toward the ring's own centre", which for a hole is INTO the
  // hole: 0.2 mm, under a preset whose fill covers 0.2 mm into it or (a hole
  // too thin to shrink) not at all. No underlay stitch may land in a hole.
  const fabric = FABRICS.getFabric("canvas_tote");
  const holes = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) holes.push(boxPx(60 + c * 100, 60 + r * 100, 100 + c * 100, 100 + r * 100));
  const badge = { outer: boxPx(0, 0, 360, 360), holes: holes.concat([boxPx(20, 20, 26, 200)]) };
  const inHole = (d) => {
    let n = 0;
    for (const run of d.runs) {
      if (run.kind !== "underlay") continue;
      for (let i = run.i0; i <= run.i1; i++) {
        const s = d.stitches[i];
        if (s.type !== "stitch") continue;
        const p = { x: s.x + 180, y: 180 - s.y };
        if (badge.holes.some((h) => p.x > h[0].x + 0.7 && p.x < h[2].x - 0.7 && p.y > h[0].y + 0.7 && p.y < h[2].y - 0.7)) n++;
      }
    }
    return n;
  };
  assert.strictEqual(inHole(drawn(badge, 360, { fabric })), 0);
  assert.ok(inHole(drawn(badge, 360, { fabric, fillColumns: false })) > 20, "without the flag it does, or the line above proves nothing");
});

// How many FLOATS longer than a stitch (4 mm) leave the ground the fill
// covers: the drawing's own rings, or under a fabric preset the
// pull-compensated ones the fill is sewn to (rebuilt here the way
// buildQualityDesign builds them). A float is a move made with the thread
// attached and no penetration. 0.08 mm: a stitch is rounded to 0.1.
function floatsOffCover(d, shape, pullMm) {
  let rings = [shape.outer].concat(shape.holes || []);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of shape.outer) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  if (pullMm > 0) {
    const holes = rings.slice(1).map((hh) => {
      const off = DG.offsetRing(hh, pullMm * 10, false), a0 = DG.signedArea(hh), a1 = DG.signedArea(off);
      return (Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6) ? hh : off;
    });
    rings = [DG.offsetRing(rings[0], pullMm * 10, true)].concat(holes);
  }
  const edges = [];
  for (const r of rings) for (let i = 0; i < r.length; i++) edges.push([r[i], r[(i + 1) % r.length]]);
  const inside = (p) => {
    let c = false;
    for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c;
    return c;
  };
  const nearEdge = (p) => edges.some(([u, v]) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
    const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)) <= 0.8;
  });
  let n = 0, attached = false, prev = null, from = null;
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "trim") { attached = false; from = null; prev = s; continue; }
    if (s.type === "jump") { if (attached && !from) from = prev; prev = s; continue; }
    if (from) {
      const a = { x: from.x + cx, y: cy - from.y }, b = { x: s.x + cx, y: cy - s.y };
      const len = Math.hypot(b.x - a.x, b.y - a.y);
      if (len > 40) {
        const k = Math.ceil(len / 0.25);
        let off = false;
        for (let j = 0; j < k && !off; j++) {
          const p = { x: a.x + (b.x - a.x) * (j + 0.5) / k, y: a.y + (b.y - a.y) * (j + 0.5) / k };
          off = !inside(p) && !nearEdge(p);
        }
        if (off) n++;
      }
      from = null;
    }
    attached = true;
    prev = s;
  }
  return n;
}

// mm of thread, sewn and floated, lying deeper than `tolMm` outside the ground
// the fill covers (the same rings as floatsOffCover). `openGroundMm` above
// measures against the DRAWN outline, which is the wrong yardstick under a
// preset: the fill is sewn up to 0.6 mm outside it on purpose.
function offCoverMm(d, shape, pullMm, tolMm) {
  let rings = [shape.outer].concat(shape.holes || []);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const p of shape.outer) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  if (pullMm > 0) {
    const holes = rings.slice(1).map((hh) => {
      const off = DG.offsetRing(hh, pullMm * 10, false), a0 = DG.signedArea(hh), a1 = DG.signedArea(off);
      return (Math.sign(a0) !== Math.sign(a1) || Math.abs(a1) < 1e-6) ? hh : off;
    });
    rings = [DG.offsetRing(rings[0], pullMm * 10, true)].concat(holes);
  }
  const edges = [];
  for (const r of rings) for (let i = 0; i < r.length; i++) edges.push([r[i], r[(i + 1) % r.length]]);
  const inside = (p) => {
    let c = false;
    for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c;
    return c;
  };
  const reach = (tolMm + 0.08) * 10;
  const nearEdge = (p) => edges.some(([u, v]) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
    const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy)) <= reach;
  });
  let sewn = 0, floats = 0, attached = false, prev = null;
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "trim") { attached = false; prev = s; continue; }
    if (prev && attached) {
      const a = { x: prev.x + cx, y: cy - prev.y }, b = { x: s.x + cx, y: cy - s.y };
      const len = Math.hypot(b.x - a.x, b.y - a.y), n = Math.max(1, Math.ceil(len / 0.5));
      let open = 0;
      for (let k = 0; k < n; k++) {
        const p = { x: a.x + (b.x - a.x) * (k + 0.5) / n, y: a.y + (b.y - a.y) * (k + 0.5) / n };
        if (!inside(p) && !nearEdge(p)) open += len / n;
      }
      if (s.type === "stitch") sewn += open; else floats += open;
    }
    if (s.type === "stitch") attached = true;
    prev = s;
  }
  return { sewn: Math.round(sewn) / 10, floats: Math.round(floats) / 10 };
}

test("fillColumns: no float longer than a stitch is left along the outside of a fill", () => {
  // A row turn at the step of a T, an L or a U runs along the step's own
  // edge, under one fill row outside it: not deep, so nothing is cut. But the
  // plain walk FLOATS any turn longer than a stitch, and this one lies where
  // no later row covers it -- a loose thread on the rim, 6 to 28 mm long, on
  // 35 of 165 designs measured (nine of them at the angle the engine picks for
  // the shape). With the flag it is sewn along the rim instead.
  const shapes = {
    T: [ring([[0, 0], [350, 0], [350, 105], [227.5, 105], [227.5, 350], [122.5, 350], [122.5, 105], [0, 105]]), 350],
    invertedT: [ring([[122.5, 0], [227.5, 0], [227.5, 245], [350, 245], [350, 350], [0, 350], [0, 245], [122.5, 245]]), 350],
    L: [ring([[0, 0], [100, 0], [100, 235], [300, 235], [300, 335], [0, 335]]), 300],
    tallU: [ring([[0, 0], [100, 0], [100, 300], [200, 300], [200, 0], [300, 0], [300, 400], [0, 400]]), 300],
    H: [ring([[0, 0], [90, 0], [90, 120], [210, 120], [210, 0], [300, 0], [300, 300], [210, 300], [210, 180], [90, 180], [90, 300], [0, 300]]), 300],
  };
  let without = 0;
  for (const fabricId of [null, "pique_knit", "structured_cap"]) {
    const fabric = fabricId ? FABRICS.getFabric(fabricId) : null;
    const extra = fabric ? { fabric } : {};
    for (const name of Object.keys(shapes)) {
      for (const angleOverride of [null, 0, 90]) {
        const shape = { outer: shapes[name][0], holes: [] };
        if (angleOverride != null) shape.angleOverride = angleOverride;
        const pull = fabric ? fabric.pullCompMm : 0;
        const label = name + ", " + (fabricId || "no fabric") + ", angle " + (angleOverride == null ? "auto" : angleOverride);
        assert.strictEqual(floatsOffCover(drawn(shape, shapes[name][1], extra), shape, pull), 0, label);
        without += floatsOffCover(drawn(shape, shapes[name][1], Object.assign({ fillColumns: false }, extra)), shape, pull);
      }
    }
  }
  assert.ok(without >= 20, "these shapes must float outside WITHOUT the flag, or this proves nothing: " + without);
});

test("fillColumns: a plain shape under a fabric preset is sewn exactly as it is without it", () => {
  // The cut between two runs was tested against the TRUE outline while the
  // fill covers the pull-compensated one, so the move to the fill's first
  // point -- a hair outside the true corner -- read as open ground and a plain
  // square went from one cut to two.
  const square = { outer: boxPx(0, 0, 300, 300), holes: [] };
  const fabric = FABRICS.getFabric("pique_knit");
  assert.deepStrictEqual(drawn(square, 300, { fabric }).stitches, drawn(square, 300, { fabric, fillColumns: false }).stitches);
  // The same for every preset, a round shape and one at an angle: a shape with
  // no hole and no inside corner has nothing for the flag to do. (An audit
  // checked 4,928 such designs. The edge run would differ if the flag moved it
  // on every shape, which is why it does so only where a ring has a hole or an
  // inside corner to chord across.)
  const round = { outer: roundPx(150, 150, 150, 48), holes: [] };
  const tilted = { outer: ring([[60, 0], [300, 80], [240, 300], [0, 220]]), holes: [] };
  for (const f of FABRICS.FABRICS) {
    for (const shape of [square, round, tilted]) {
      assert.deepStrictEqual(drawn(shape, 300, { fabric: f }).stitches, drawn(shape, 300, { fabric: f, fillColumns: false }).stitches, f.id);
    }
  }
  // and the count of center-out fills says which walk each got
  assert.strictEqual(drawn(square, 300, { fabric })._debug.nCenterOut, 1, "a plain 30 mm square is still center-out");
  const holed = { outer: boxPx(0, 0, 300, 300), holes: [boxPx(100, 100, 200, 200)] };
  assert.strictEqual(drawn(holed, 300, { fabric })._debug.nCenterOut, 0, "a holed one is sewn by the column walk, which is not");
  assert.strictEqual(drawn(holed, 300, { fabric, fillColumns: false })._debug.nCenterOut, 1);
});

// --- what the cuts cost, and getting them back -------------------------------
//
// Where a design's cuts are: inside the fill, inside an underlay run, or
// between two runs of the shape.
function cutsBy(d) {
  const out = { all: 0, fill: 0, underlay: 0, between: 0 };
  d.stitches.forEach((s, i) => {
    if (s.type !== "trim") return;
    out.all++;
    const run = d.runs.find((r) => i > r.i0 && i <= r.i1);
    if (run) out[run.kind === "fill" ? "fill" : "underlay"]++; else out.between++;
  });
  return out;
}

test("fillColumns: the edge runs round the holes are entered where the thread already is", () => {
  // An edge-run underlay sews a ring round each hole. Each ring began at its
  // own first corner and stopped a stitch short of it, so the move to the next
  // ring started part-way down a hole's side and crossed that hole: one cut
  // per hole (36 on a 36-hole badge, on the preset a left chest uses). Taken
  // nearest-first, entered at the corner the thread is nearest to and closed
  // back onto that corner, the move runs along the hole's own edge instead.
  const fabric = FABRICS.getFabric("pique_knit");
  const row = { outer: boxPx(0, 0, 400, 400), holes: [boxPx(40, 180, 80, 220), boxPx(130, 180, 170, 220), boxPx(230, 180, 270, 220), boxPx(320, 180, 360, 220)], angleOverride: 0 };
  assert.deepStrictEqual(cutsBy(drawn(row, 400, { fabric })).between, 0, "a row of four holes");
  const holes = [];
  for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) holes.push(boxPx(40 + c * 95, 40 + r * 95, 80 + c * 95, 80 + r * 95));
  const badge = { outer: boxPx(0, 0, 600, 600), holes, angleOverride: 0 };
  const d = drawn(badge, 600, { fabric });
  assert.ok(cutsBy(d).between <= 3, "36 holes: " + JSON.stringify(cutsBy(d)));
  // and no cut was traded for a float: none in a hole, none off the fill
  assert.strictEqual(openGroundMm(d, badge, 0.5).floats, 0);
  assert.strictEqual(floatsOffCover(d, badge, fabric.pullCompMm), 0);
  // every hole still gets its ring: 37 edge runs, then the fill
  assert.deepStrictEqual(d.runs.map((r) => r.kind).join(" ").replace(/(underlay ?)+/, (m) => m.trim().split(" ").length + "u "), "37u fill");
});

const roundPx = (cx, cy, r, n) => Array.from({ length: n }, (_, i) => ({ x: cx + r * Math.cos(2 * Math.PI * i / n), y: cy + r * Math.sin(2 * Math.PI * i / n) }));
const eachCase = (shapes, fn) => {
  for (const fabricId of [null, "pique_knit", "structured_cap"]) {
    const fabric = fabricId ? FABRICS.getFabric(fabricId) : null;
    for (const name of Object.keys(shapes)) {
      for (const angleOverride of [null, 0, 30, 82]) {
        const shape = Object.assign({}, shapes[name][0]);
        if (angleOverride != null) shape.angleOverride = angleOverride;
        const label = name + ", " + (fabricId || "no fabric") + ", angle " + (angleOverride == null ? "auto" : angleOverride);
        fn(shape, shapes[name][1], fabric, label);
      }
    }
  }
};

test("fillColumns: a shape with holes, in one piece, is sewn without a cut", () => {
  // The first rebuild kept thread out of holes by cutting it: 35 to 122 cuts
  // on a 36-hole badge, depending on the preset and on the angle the rows
  // happened to run at, and nothing in this lane locks a cut. With the walk
  // able to go round a ring, enter a strip from its far end, find a way along
  // rims and rows when it is stranded, and start each pass where the thread
  // already is, a holed shape in one piece needs none: 48 designs, none.
  //
  // (Where one can still remain is BETWEEN two edge runs, when every straight
  // way to the hole still to be sewn round lies across one already done: up
  // to four, on a 2,025-hole stress shape under an edge-run preset.)
  const holes = [];
  for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) holes.push(boxPx(40 + c * 95, 40 + r * 95, 80 + c * 95, 80 + r * 95));
  const round = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) round.push(roundPx(100 + c * 150, 100 + r * 150, 35, 24));
  eachCase({
    badge16: [{ outer: boxPx(0, 0, 410, 410), holes }, 410],
    B: [{ outer: boxPx(0, 0, 260, 360), holes: [boxPx(70, 50, 190, 140), boxPx(70, 210, 190, 310)] }, 260],
    annulus: [{ outer: roundPx(200, 200, 200, 64), holes: [roundPx(200, 200, 110, 48)] }, 400],
    nineRound: [{ outer: boxPx(0, 0, 500, 500), holes: round }, 500],
  }, (shape, widthPx, fabric, label) => {
    const d = drawn(shape, widthPx, fabric ? { fabric } : {});
    assert.deepStrictEqual(cutsBy(d), { all: 0, fill: 0, underlay: 0, between: 0 }, label);
    // and no cut was traded for thread off the fill: checked at the angle the engine picks
    if (shape.angleOverride == null) {
      const pull = fabric ? fabric.pullCompMm : 0;
      assert.deepStrictEqual(offCoverMm(d, shape, pull, 0.15), { sewn: 0, floats: 0 }, label);
      assert.strictEqual(floatsOffCover(d, shape, pull), 0, label);
    }
  });
});

test("fillColumns: a lattice underlay at 45 degrees to a grid of holes is not cut either", () => {
  // The two lattice passes of the terry and fleece presets run at 45 degrees
  // to the fill. Round the corner of a square hole the turn from one lattice
  // row to the next crosses the hole, and its two ends sit on different
  // rings, so there was no way round: the column was cut there (one on this
  // badge, seven on a 196-hole one). A column is now cut in TWO at a turn it
  // cannot make, and the walk finds its way from one piece to the other.
  const holes = [];
  for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) holes.push(boxPx(40 + c * 95, 40 + r * 95, 80 + c * 95, 80 + r * 95));
  const badge = { outer: boxPx(0, 0, 600, 600), holes, angleOverride: 0 };
  for (const fabricId of ["terry_towel", "fleece_sweatshirt"]) {
    const fabric = FABRICS.getFabric(fabricId);
    const d = drawn(badge, 600, { fabric });
    assert.deepStrictEqual(cutsBy(d), { all: 0, fill: 0, underlay: 0, between: 0 }, fabricId);
    assert.deepStrictEqual(offCoverMm(d, badge, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, fabricId);
  }
});

test("fillColumns: an underlay turn that only clips what the fill covers is a stitch, not a way round", () => {
  // Terry: the fill covers 0.6 mm into every hole. Lattice rows 2.5 mm apart
  // turn round a 7 mm round hole by clipping it 0.2 to 0.6 mm, all of it under
  // the fill. Each underlay pass is told that ground. Judged against the drawn
  // outline instead, every such turn is open ground and the thread goes round
  // the rim: 957 underlay stitches where 842 do.
  const fabric = FABRICS.getFabric("terry_towel");
  const holes = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) holes.push(roundPx(100 + c * 150, 100 + r * 150, 35, 48));
  const shape = { outer: boxPx(0, 0, 500, 500), holes };
  const d = drawn(shape, 500, { fabric });
  let underlay = 0;
  for (const run of d.runs) if (run.kind === "underlay") for (let i = run.i0; i <= run.i1; i++) if (d.stitches[i].type === "stitch") underlay++;
  assert.ok(underlay < 900, "underlay stitches: " + underlay);
  assert.deepStrictEqual(offCoverMm(d, shape, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 });
});

test("fillColumns: a notched shape is not cut inside its underlay, and its fill only where center-out cuts", () => {
  // Rows that never fork keep the walk they have always had, center-out and
  // its one cut included. What the flag may add to such a shape is a cut on
  // the way INTO a pass, where that float would have crossed the notch.
  eachCase({
    T: [{ outer: ring([[0, 0], [350, 0], [350, 105], [227.5, 105], [227.5, 350], [122.5, 350], [122.5, 105], [0, 105]]), holes: [] }, 350],
    L: [{ outer: ring([[0, 0], [100, 0], [100, 235], [300, 235], [300, 335], [0, 335]]), holes: [] }, 300],
    U: [{ outer: ring([[0, 0], [140, 0], [140, 180], [300, 180], [300, 0], [440, 0], [440, 280], [0, 280]]), holes: [] }, 440],
    E: [{ outer: ring([[0, 0], [260, 0], [260, 60], [80, 60], [80, 130], [220, 130], [220, 190], [80, 190], [80, 260], [260, 260], [260, 320], [0, 320]]), holes: [] }, 260],
  }, (shape, widthPx, fabric, label) => {
    const d = drawn(shape, widthPx, fabric ? { fabric } : {});
    const cuts = cutsBy(d);
    assert.strictEqual(cuts.underlay, 0, label + " " + JSON.stringify(cuts));
    assert.ok(cuts.fill <= 1 && cuts.between <= 2, label + " " + JSON.stringify(cuts));
    assert.strictEqual(floatsOffCover(d, shape, fabric ? fabric.pullCompMm : 0), 0, label);
  });
});

// --- what the second audit found (2026-10-03, on the rebuild) ----------------
//
// The rebuild cleared every failure of the first audit and four more turned
// up, each from a shape or a scale the tests did not have. The repros below
// are the auditor's own.

test("fillColumns: an underlay does not sew across a slot the fill leaves open", () => {
  // A cut-out 1 mm wide, under a preset whose pull compensation is 0.6 mm.
  // Shrunk by that, the hole folds through itself, so the fill is sewn to the
  // hole AS DRAWN. But the underlay was allowed "as deep as the pull
  // compensation, since the fill covers that far": 0.6 mm each side of a 1 mm
  // slot is all of it, and twelve underlay stitches went straight across. The
  // ground is what the fill covers, measured, not the outline plus a number.
  const slot = { outer: boxPx(0, 0, 300, 300), holes: [boxPx(145, 60, 155, 240)] };
  const notch = { outer: ring([[0, 0], [177, 0], [177, 240], [183, 240], [183, 0], [360, 0], [360, 360], [0, 360]]), holes: [] };
  for (const fabricId of ["terry_towel", "fleece_sweatshirt", "structured_cap"]) {
    const fabric = FABRICS.getFabric(fabricId);
    assert.deepStrictEqual(offCoverMm(drawn(slot, 300, { fabric }), slot, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, "1 mm slot, " + fabricId);
    assert.deepStrictEqual(offCoverMm(drawn(notch, 360, { fabric }), notch, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, "0.6 mm notch, " + fabricId);
  }
});

// A drawing in the helpers' own units (0.1 mm), for a design not built at 10
// px per mm: the same shape scaled so that one px is one stitch unit.
const inUnits = (shape, widthPx, widthMm) => {
  const k = (widthMm * 10) / widthPx, sc = (r) => r.map((p) => ({ x: p.x * k, y: p.y * k }));
  return { outer: sc(shape.outer), holes: (shape.holes || []).map(sc) };
};

test("fillColumns: an enlarged design keeps its underlay out of the holes too", () => {
  // The edge run was inset "2 px, at most 0.6 mm", toward the ring's own
  // centre: for a hole, INTO the hole. At 10 px per mm that is 0.2 mm and the
  // fill's pull compensation covers it. Enlarged to 2 px per mm it is 0.6 mm,
  // past the cover, and every float that starts there starts in the hole.
  const fabric = FABRICS.getFabric("pique_knit");
  const big = { garment: { id: "left_chest", widthIn: 40, heightIn: 40 }, fabric };
  const o = { outer: roundPx(150, 180, 1, 64).map((p) => ({ x: 150 + (p.x - 150) * 150, y: 180 + (p.y - 180) * 180 })),
              holes: [roundPx(150, 180, 1, 64).map((p) => ({ x: 150 + (p.x - 150) * 70, y: 180 + (p.y - 180) * 100 }))] };
  const dO = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [Object.assign({ tierOverride: "fill" }, o)] }],
    Object.assign({ pxPerMm: 10, targetWidthMm: 150, darkOnTop: false, underlay: true, fillColumns: true }, big));
  const oU = inUnits(o, 300, 150);
  assert.deepStrictEqual(offCoverMm(dO, oU, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, "an O at 2 px per mm");
  assert.strictEqual(floatsOffCover(dO, oU, fabric.pullCompMm), 0, "an O at 2 px per mm");
  const holes = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) holes.push(boxPx(35 + 105 * i, 35 + 105 * j, 105 + 105 * i, 105 + 105 * j));
  const nine = { outer: boxPx(0, 0, 350, 350), holes };
  const d9 = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [Object.assign({ tierOverride: "fill" }, nine)] }],
    Object.assign({ pxPerMm: 10, targetWidthMm: 175, darkOnTop: false, underlay: true, fillColumns: true }, big));
  const nineU = inUnits(nine, 350, 175);
  assert.deepStrictEqual(offCoverMm(d9, nineU, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, "nine holes at 2 px per mm");
  assert.strictEqual(floatsOffCover(d9, nineU, fabric.pullCompMm), 0, "nine holes at 2 px per mm");
});

test("fillColumns: a float between two runs that only grazes the rim is cut as well", () => {
  // Not deep, so it was left: 16.7 mm of float, 13.2 mm of it outside the
  // drawn shape and 0.1 mm out. 306 like it on 239 of 8,278 designs. A float
  // is loose thread; on the rim nothing covers it.
  const blob = { outer: ring([[246.7, 198], [125.6, 300.9], [117.1, 268.4], [84.5, 240.8], [72.5, 239.2], [121.4, 175.8], [61.1, 170.7], [116.5, 161.1], [96.3, 143.7], [87.9, 117.8], [134.9, 134.5], [138.7, 130], [126.9, 109.7], [170.7, 63.7], [186.1, 24.6], [260.8, 87.3], [271, 134.4], [301.7, 174.7]]), holes: [], angleOverride: 90 };
  assert.strictEqual(floatsOffCover(drawn(blob, 240.6), blob, 0), 0, "a float along an edge");
  const plus = { outer: ring([[122.5, 0], [227.5, 0], [227.5, 122.5], [350, 122.5], [350, 227.5], [227.5, 227.5], [227.5, 350], [122.5, 350], [122.5, 227.5], [0, 227.5], [0, 122.5], [122.5, 122.5]]), holes: [], angleOverride: 30 };
  const cap = FABRICS.getFabric("structured_cap");
  assert.strictEqual(floatsOffCover(drawn(plus, 350, { fabric: cap }), plus, cap.pullCompMm), 0, "a float across an inside corner");
});

// --- what the third audit found (2026-10-03, on the third build) --------------
//
// One thing that mattered, and it was in the question the walk asks of every
// move (fill.js `groundUnder`; test/fill.test.js has it bare). Here it is as a
// customer would have met it. Every sweep of mine had run no fabric, pique and
// cap. The auditor ran all seven presets, and the shape was the sheet's own.

test("fillColumns: the sheet's own shapes keep their thread on the cover under EVERY preset", () => {
  // The wide U under terry: its underlay ends at the bottom, so the fill is
  // sewn upward and finishes on top of one arm with the other still to sew.
  // The way there runs along the arms' tops, across the mouth. Asked right to
  // left, that move read as filled ground, and 14.8 mm of fill thread was
  // sewn across the notch, 7 mm from either wall.
  const ellipse = (rx, ry) => roundPx(0, 0, 1, 64).map((p) => ({ x: 150 + p.x * rx, y: 180 + p.y * ry }));
  const shapes = {
    "badge, two cut-outs": [{ outer: boxPx(0, 0, 400, 400), holes: [boxPx(60, 140, 180, 260), boxPx(285, 185, 315, 215)] }, 400],
    "ring": [{ outer: ellipse(150, 180), holes: [ellipse(70, 100)] }, 300],
    "two counters": [{ outer: boxPx(0, 0, 260, 360), holes: [boxPx(80, 60, 180, 140), boxPx(80, 200, 200, 300)] }, 260],
    "wide U": [{ outer: ring([[0, 0], [140, 0], [140, 180], [300, 180], [300, 0], [440, 0], [440, 280], [0, 280]]), holes: [] }, 440],
  };
  for (const fabric of [null].concat(FABRICS.FABRICS)) {
    for (const name of Object.keys(shapes)) {
      const [shape, widthPx] = shapes[name], pull = fabric ? fabric.pullCompMm : 0;
      const label = name + ", " + (fabric ? fabric.id : "no fabric");
      const d = drawn(shape, widthPx, fabric ? { fabric } : {});
      assert.deepStrictEqual(offCoverMm(d, shape, pull, 0.15), { sewn: 0, floats: 0 }, label);
      assert.strictEqual(floatsOffCover(d, shape, pull), 0, label);
    }
  }
});

test("fillColumns: a ring inside a hole is an island, and its edge run lies on the island", () => {
  // `holes` carries every ring inside the outline, and a ring inside a hole is
  // filled ground again: `groupRingsIntoShapes` hands a bullseye over as the
  // outline plus [hole, island]. The edge run was moved "out from a hole" for
  // every ring in that list, which for the island is INTO the moat: 33.6 mm of
  // underlay 0.2 mm inside the cut-out, on a ring whose flag-off run lies on
  // the island.
  const island = boxPx(160, 160, 240, 240);
  const eye = { outer: boxPx(0, 0, 400, 400), holes: [boxPx(80, 80, 320, 320), island] };
  // mm of thread in the moat, between 0.15 and 1 mm past a line `past` px
  // OUTSIDE the island's own ring: of one kind of run, or (no `kind`) of all
  const besideIsland = (d, past, kind) => {
    let mm = 0, attached = false, prev = null;
    for (let i = 0; i < d.stitches.length; i++) {
      const s = d.stitches[i];
      if (s.type === "end") break;
      if (s.type === "trim") { attached = false; prev = s; continue; }
      if (prev && attached && (!kind || d.runs.some((r) => r.kind === kind && i > r.i0 && i <= r.i1))) {
        const a = { x: prev.x + 200, y: 200 - prev.y }, b = { x: s.x + 200, y: 200 - s.y };
        const len = Math.hypot(b.x - a.x, b.y - a.y), n = Math.max(1, Math.ceil(len / 0.5));
        for (let k = 0; k < n; k++) {
          const x = a.x + (b.x - a.x) * (k + 0.5) / n, y = a.y + (b.y - a.y) * (k + 0.5) / n;
          const out = Math.max(160 - x, x - 240, 160 - y, y - 240);   // > 0: outside the island, by about this much
          if (out > past + 1.5 && out < past + 10) mm += len / n / 10;
        }
      }
      if (s.type === "stitch") attached = true;
      prev = s;
    }
    return Math.round(mm * 10) / 10;
  };
  for (const fabricId of ["pique_knit", "terry_towel", "structured_cap", "fleece_sweatshirt"]) {
    const fabric = FABRICS.getFabric(fabricId), d = drawn(eye, 400, { fabric });
    // no UNDERLAY comes that near the island from the moat side
    assert.strictEqual(besideIsland(d, 0, "underlay"), 0, fabricId);
    // The island's FILL does, and is meant to: it is sewn past the ring by
    // the preset's pull compensation, as the outline's is (the tests below).
    // Past what the fill covers, the moat is clear of every kind of thread.
    assert.strictEqual(besideIsland(d, fabric.pullCompMm * 10), 0, fabricId + ", past the island's fill");
    // (flag off, the old walk's floats cross that band on every row: the
    // fixture can see thread there)
    assert.ok(besideIsland(drawn(eye, 400, { fabric, fillColumns: false }), 0) > 50, fabricId + ", flag off");
  }
});

// --- a ring inside a hole is an ISLAND, to every reader (2026-10-03) ----------
//
// The fill is even-odd: a ring inside a hole is filled ground again, and a
// ring inside THAT is a hole again. Two readers in buildQualityDesign took
// every ring in `holes` for a hole. Both are older than `fillColumns` and
// neither asks it, so each test here runs the flag off and on.

// Where the FILL's needle went on the rows through the middle of a square
// drawing `size` px wide, as x in the drawing's own px, sorted. With the rows
// forced level (angleOverride 0) these are those rows' own stitches, so the
// first and last inside a window are where a span of the fill begins and
// ends: the edge it was sewn to.
function fillOnMiddleRows(d, size) {
  const xs = [];
  for (const run of d.runs) {
    if (run.kind !== "fill") continue;
    for (let i = run.i0; i <= run.i1; i++) {
      const s = d.stitches[i];
      if (s.type === "stitch" && Math.abs(s.y) <= 2) xs.push(s.x + size / 2);
    }
  }
  return xs.sort((a, b) => a - b);
}
const firstIn = (xs, lo, hi) => xs.find((x) => x > lo && x < hi);
const lastIn = (xs, lo, hi) => xs.filter((x) => x > lo && x < hi).pop();
const level = (shape) => Object.assign({ angleOverride: 0 }, shape);
const bothWalks = (fn) => { for (const fillColumns of [false, true]) fn(fillColumns, fillColumns ? ", fillColumns" : ""); };

test("buildQualityDesign: three nested rings are sewn, the innermost as filled ground", () => {
  // A 40 mm box, a hole 4 mm in, a ring 4 mm inside that. Taken for a second
  // hole, the innermost ring had its area SUBTRACTED: 1600 - 1024 - 576 =
  // 0 mm2, and a shape with no area is dropped. No stitch, with or without a
  // preset, and nothing said: a concentric-ring logo through the text tools
  // (`groupRingsIntoShapes`) sewed nothing.
  const [nested] = DG.groupRingsIntoShapes([boxPx(0, 0, 400, 400), boxPx(40, 40, 360, 360), boxPx(80, 80, 320, 320)]);
  assert.strictEqual(nested.holes.length, 2, "one shape: the outline and both rings inside it");
  for (const fabricId of [null, "pique_knit", "terry_towel"]) {
    for (const tierOverride of ["fill", undefined]) {
      bothWalks((fillColumns, walk) => {
        const label = (fabricId || "no fabric") + ", tier " + (tierOverride || "auto") + walk;
        const d = drawn(Object.assign({}, nested, { tierOverride }), 400, Object.assign({ fillColumns }, fabricId ? { fabric: FABRICS.getFabric(fabricId) } : {}));
        assert.strictEqual(d.shapeOutlines[0].dropped, false, label);
        // how far out from the centre each fill stitch lands, in px: the band
        // is 160 to 200 out, the moat 120 to 160, the island all inside 120
        const out = [];
        for (const run of d.runs) {
          if (run.kind !== "fill") continue;
          for (let i = run.i0; i <= run.i1; i++) if (d.stitches[i].type === "stitch") out.push(Math.max(Math.abs(d.stitches[i].x), Math.abs(d.stitches[i].y)));
        }
        assert.ok(out.filter((m) => m > 170).length > 100, "the band is sewn, " + label);
        assert.ok(out.filter((m) => m < 110).length > 100, "the island is sewn, " + label);
        assert.strictEqual(out.filter((m) => m > 130 && m < 150).length, 0, "the moat is not, " + label);
      });
    }
  }
});

test("buildQualityDesign: pull compensation grows an island, as it grows the outline", () => {
  // A fill is sewn past its edge by the preset's pull compensation, so that it
  // pulls in to true size: the outline grown, each hole shrunk. Every ring in
  // `holes` was shrunk, and for an island that is the fill made SMALLER: on
  // terry (0.6 mm) the outline's fill was sewn -6..406 px, right, and the
  // island drawn 160..240 was sewn 166..234, wrong by twice the compensation.
  const island = boxPx(160, 160, 240, 240), hole = boxPx(80, 80, 320, 320);
  for (const fabric of FABRICS.FABRICS) {
    const q = fabric.pullCompMm * 10;   // the compensation, in px
    // (and whichever of the two rings is listed first)
    for (const holes of [[hole, island], [island, hole]]) {
      bothWalks((fillColumns, walk) => {
        const label = fabric.id + (holes[0] === island ? ", island listed first" : "") + walk;
        const xs = fillOnMiddleRows(drawn(level({ outer: boxPx(0, 0, 400, 400), holes }), 400, { fabric, fillColumns }), 400);
        // (a stitch is rounded to 0.1 mm, and jersey's compensation is 0.35)
        const sewnAt = (got, want, what) => assert.ok(Math.abs(got - want) <= 0.5, what + ", " + label + ": sewn at " + got + ", not " + want);
        sewnAt(xs[0], 0 - q, "the outline's edge");
        sewnAt(lastIn(xs, 0, 120), 80 + q, "the hole's wall");
        sewnAt(firstIn(xs, 120, 200), 160 - q, "the island's left edge");
        sewnAt(lastIn(xs, 200, 280), 240 + q, "the island's right edge");
        sewnAt(firstIn(xs, 280, 400), 320 - q, "the hole's far wall");
      });
    }
  }
});

test("buildQualityDesign: an island's underlay stays under its own fill", () => {
  // The underlay is sewn to the ring as DRAWN. With the island's fill 0.6 mm
  // small on every side (terry), its lattice underlay lay 0.6 mm outside the
  // fill all round: sewn, and never covered.
  const eye = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(80, 80, 320, 320), boxPx(160, 160, 240, 240)] });
  // the x and y reach of one kind of run over the island and the moat round it
  const reach = (d, kind) => {
    const r = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
    for (const run of d.runs) {
      if (run.kind !== kind) continue;
      for (let i = run.i0; i <= run.i1; i++) {
        const s = d.stitches[i];
        if (s.type !== "stitch" || Math.max(Math.abs(s.x), Math.abs(s.y)) > 80) continue;
        r.x0 = Math.min(r.x0, s.x); r.x1 = Math.max(r.x1, s.x); r.y0 = Math.min(r.y0, s.y); r.y1 = Math.max(r.y1, s.y);
      }
    }
    return r;
  };
  for (const fabric of FABRICS.FABRICS) {
    bothWalks((fillColumns, walk) => {
      const d = drawn(eye, 400, { fabric, fillColumns });
      const under = reach(d, "underlay"), fill = reach(d, "fill");
      const label = fabric.id + walk + ": underlay " + JSON.stringify(under) + ", fill " + JSON.stringify(fill);
      assert.ok(under.x1 > under.x0, "the island has an underlay, " + label);
      // level rows: the fill's ends are its edge. Top and bottom it reaches to
      // within a row of its edge, and a row is 0.15 mm.
      assert.ok(under.x0 >= fill.x0 && under.x1 <= fill.x1, "across the rows, " + label);
      assert.ok(under.y0 >= fill.y0 - 1 && under.y1 <= fill.y1 + 1, "along them, " + label);
    });
  }
});

test("buildQualityDesign: a hole inside an island is a hole again, and is shrunk", () => {
  // Four rings: band, moat, a ring of island, and a hole in the middle of it.
  // The count that says which is which is how many rings of the list a ring
  // lies inside: even a hole, odd an island. (Subtracting all three areas left
  // this one less than nothing, and it was dropped like the one above.)
  const four = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(40, 40, 360, 360), boxPx(80, 80, 320, 320), boxPx(120, 120, 280, 280)] });
  for (const fabricId of ["pique_knit", "structured_cap", "terry_towel"]) {
    const fabric = FABRICS.getFabric(fabricId), q = Math.round(fabric.pullCompMm * 10);
    bothWalks((fillColumns, walk) => {
      const label = fabricId + walk;
      const xs = fillOnMiddleRows(drawn(four, 400, { fabric, fillColumns }), 400);
      assert.strictEqual(lastIn(xs, 0, 60), 40 + q, "the outer hole's wall, " + label);
      assert.strictEqual(firstIn(xs, 60, 100), 80 - q, "the island's outer edge, grown, " + label);
      assert.strictEqual(lastIn(xs, 100, 150), 120 + q, "the inner hole's wall, shrunk, " + label);
      assert.strictEqual(firstIn(xs, 150, 250), undefined, "nothing in the inner hole, " + label);
    });
  }
});

test("buildQualityDesign: an island too near the hole round it to grow is sewn as drawn", () => {
  // Grown, an island moves TOWARD the wall of its hole while that wall moves
  // toward it, and two rings that cross are a fill sewn where neither was
  // drawn. A hole too thin to shrink is sewn as drawn; so is an island with a
  // moat too thin to grow into. Terry, 0.6 mm: a 1 mm moat takes the hole's
  // 0.6 and leaves the island where it is.
  const fabric = FABRICS.getFabric("terry_towel");
  const eye = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(80, 80, 320, 320), boxPx(90, 90, 310, 310)] });
  bothWalks((fillColumns, walk) => {
    const xs = fillOnMiddleRows(drawn(eye, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(lastIn(xs, 0, 88), 86, "the hole's wall, shrunk as ever" + walk);
    assert.strictEqual(firstIn(xs, 88, 200), 90, "the island's edge, as drawn" + walk);
    assert.strictEqual(lastIn(xs, 200, 312), 310, "and its far edge" + walk);
    assert.strictEqual(firstIn(xs, 312, 400), 314, "the hole's far wall" + walk);
  });
});

test("buildQualityDesign: where a shrunk hole would still meet its island, both are sewn as drawn", () => {
  // A 0.4 mm moat on terry: the hole's wall alone, moved 0.6 mm, is past the
  // island's edge.
  const fabric = FABRICS.getFabric("terry_towel");
  const eye = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(80, 80, 320, 320), boxPx(84, 84, 316, 316)] });
  bothWalks((fillColumns, walk) => {
    const xs = fillOnMiddleRows(drawn(eye, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(xs[0], -6, "the outline is still grown" + walk);
    assert.strictEqual(lastIn(xs, 0, 82), 80, "the hole's wall, as drawn" + walk);
    assert.strictEqual(firstIn(xs, 82, 200), 84, "the island's edge, as drawn" + walk);
    assert.strictEqual(lastIn(xs, 200, 318), 316, "and its far edge" + walk);
    assert.strictEqual(firstIn(xs, 318, 400), 320, "the hole's far wall" + walk);
  });
});

test("buildQualityDesign: two islands too near each other to grow are both sewn as drawn", () => {
  // Side by side in one hole, 0.8 mm apart: each grown 0.6 mm, they overlap.
  const fabric = FABRICS.getFabric("terry_towel");
  const pair = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(60, 60, 340, 340), boxPx(100, 150, 196, 250), boxPx(204, 150, 300, 250)] });
  bothWalks((fillColumns, walk) => {
    const xs = fillOnMiddleRows(drawn(pair, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(lastIn(xs, 0, 80), 66, "the hole's wall, shrunk as ever" + walk);
    assert.strictEqual(firstIn(xs, 80, 150), 100, "the left island's outer edge" + walk);
    assert.strictEqual(lastIn(xs, 150, 200), 196, "its inner edge" + walk);
    assert.strictEqual(firstIn(xs, 200, 250), 204, "the right island's inner edge" + walk);
    assert.strictEqual(lastIn(xs, 250, 320), 300, "its outer edge" + walk);
  });
});

// --- what an independent audit of the island fix found (2026-10-03) -----------
//
// Its claims were handed over as claims and read with the auditor's own
// clipper. Two of the three things below are the fix reaching further than it
// should; the third is its cost on a shape with no island at all, and has no
// test here because it is a time (islandsAmong, the box test).

test("buildQualityDesign: an island that would cross ITSELF grown is sewn as drawn", () => {
  // An island with a slit of its own, 0.1 mm wide. Grown, the slit's two
  // walls pass each other, and a ring that crosses itself is a fill with a
  // gap where neither wall was drawn: on terry 0.5 mm of the island bare on
  // each bank of the slit. (An outline with such a slit has always done that,
  // and still does.) The guard asked only whether an island met ANOTHER ring.
  const fabric = FABRICS.getFabric("terry_towel");
  const slit = ring([[130, 130], [199.5, 130], [199.5, 230], [200.5, 230], [200.5, 130], [270, 130], [270, 270], [130, 270]]);
  const shape = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(80, 80, 320, 320), slit] });
  bothWalks((fillColumns, walk) => {
    const xs = fillOnMiddleRows(drawn(shape, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(lastIn(xs, 0, 100), 86, "the hole's wall, shrunk as ever" + walk);
    assert.strictEqual(firstIn(xs, 100, 150), 130, "the island's outer edge, as drawn" + walk);
    // (the banks are drawn at 199.5 and 200.5, and a stitch is rounded to 0.1 mm)
    assert.ok(Math.abs(lastIn(xs, 150, 200.4) - 199.5) <= 0.5, "the slit's left bank is sewn" + walk + ": " + lastIn(xs, 150, 200.4));
    assert.ok(Math.abs(firstIn(xs, 200.4, 250) - 200.5) <= 0.5, "and its right bank" + walk + ": " + firstIn(xs, 200.4, 250));
    assert.strictEqual(lastIn(xs, 250, 300), 270, "the island's far edge" + walk);
  });
});

test("buildQualityDesign: a ring with no area inside a hole is not an island to grow", () => {
  // Three points in a line, lying in a cut-out. It is wholly inside a hole,
  // so by the count it is an island; grown by the compensation it became a
  // sliver 1.2 mm wide and was FILLED, in the middle of the hole. A ring with
  // no area is no island: it is what it always was, to every reader.
  //
  // And "no area" is not "exactly none". The audit's re-check moved the
  // middle point a millionth of a micron off the line, and that ring was
  // grown and filled again: the first cure had asked for the float to be 0.
  const fabric = FABRICS.getFabric("terry_towel");
  for (const [name, line] of [["three points in a line", [[90, 120], [120, 120], [150, 120]]], ["a hair off the line", [[90, 120], [120, 120.000000001], [150, 120]]]]) {
    const shape = level({ outer: boxPx(0, 0, 240, 240), holes: [boxPx(60, 60, 180, 180), ring(line)] });
    bothWalks((fillColumns, walk) => {
      const d = drawn(shape, 240, { fabric, fillColumns });
      let inHole = 0;   // fill stitches more than 1 mm inside the cut-out
      for (const run of d.runs) {
        if (run.kind !== "fill") continue;
        for (let i = run.i0; i <= run.i1; i++) if (d.stitches[i].type === "stitch" && Math.abs(d.stitches[i].x) < 50 && Math.abs(d.stitches[i].y) < 50) inHole++;
      }
      assert.strictEqual(inHole, 0, name + ": fill stitches in the cut-out" + walk);
    });
  }
});

test("buildQualityDesign: a ring thinner than the needle can address is no island either", () => {
  // The second cure put "no area" at a float (1e-6 px2), and the audit marked
  // the spot: a ring 6 mm long and 4e-8 px wide was an island still, grown to
  // 6 x 1.2 mm and filled. The needle moves in steps of 0.1 mm. A ring
  // narrower than one step (its area over half its perimeter) holds no thread
  // to compensate, and is left as it always was.
  const fabric = FABRICS.getFabric("terry_towel");
  // 6 mm long and 0.05 mm wide: as drawn it holds one fill row at most, grown it held nine
  const shape = level({ outer: boxPx(0, 0, 240, 240), holes: [boxPx(60, 60, 180, 180), boxPx(90, 119.75, 150, 120.25)] });
  bothWalks((fillColumns, walk) => {
    const d = drawn(shape, 240, { fabric, fillColumns });
    const rows = new Set();   // the fill rows with a stitch more than 1 mm inside the cut-out
    for (const run of d.runs) {
      if (run.kind !== "fill") continue;
      for (let i = run.i0; i <= run.i1; i++) if (d.stitches[i].type === "stitch" && Math.abs(d.stitches[i].x) < 50 && Math.abs(d.stitches[i].y) < 50) rows.add(d.stitches[i].y);
    }
    assert.ok(rows.size <= 1, "fill rows in the cut-out" + walk + ": " + rows.size);
  });
});

test("buildQualityDesign: a hole touching another's wall is not inside it, whichever way the wall runs", () => {
  // Rings that meet are not nested, and a corner ON a wall meets it. The
  // meeting test sweeps its edges along a slanted axis, and the audit found
  // the one wall that hid from it: a wall running exactly across that slant
  // has every point at one place along it, to the last bit of a float, and a
  // corner touching it could round to just outside. Never tried against the
  // wall, the touching ring read as INSIDE it: an island, and both rings were
  // sewn as drawn where both had always been shrunk (3 of 31,200 exact
  // touches in the auditor's search). The same ring pushed a millionth of a
  // px THROUGH the wall plainly crosses it, and has to sew the same.
  //
  // (Rows forced level, or the engine's own angle turns with the ring's
  // millionth. And the old walk only: with `fillColumns` the edge run asks
  // its own question of that one corner, and a corner on a wall is where it
  // has no answer.)
  const fabric = FABRICS.getFabric("terry_towel");
  const wall = ring([[284.5494909398258, 450.4658115329221], [796.5494909398258, 450.4658115329221], [717.4411403862257, 578.4658115329221], [205.44114038622575, 578.4658115329221]]);
  const touching = [[244.99531566302576, 514.4658115329221], [334.59531566302576, 490.1458115329221], [404.99531566302574, 514.4658115329221], [334.59531566302576, 538.7858115329221]];
  const through = touching.map(([x, y], i) => (i === 0 ? [x - 1e-6, y] : [x, y]));
  const build = (pts) => drawn(level({ outer: boxPx(165, 410, 837, 619), holes: [wall, ring(pts)] }), 672, { fabric, fillColumns: false });
  assert.ok(build(through).stitchCount > 2000, "the design sews");
  assert.deepStrictEqual(build(touching).stitches, build(through).stitches, "touching sews as crossing does");
});

test("buildQualityDesign: two holes that cross are still two holes", () => {
  // An island is a ring wholly inside a hole. Two cut-outs that overlap, or
  // one laid across the notch of another, are not that, whichever corner of
  // either happens to lie inside the other: both are shrunk, as they always
  // were. (Asking one corner calls the first of these an island; asking every
  // corner calls the second one.)
  const fabric = FABRICS.getFabric("terry_towel");
  const overlap = level({ outer: boxPx(0, 0, 400, 400), holes: [boxPx(180, 180, 300, 300), boxPx(100, 100, 220, 220)] });
  const u = ring([[80, 80], [320, 80], [320, 320], [240, 320], [240, 160], [160, 160], [160, 320], [80, 320]]);
  const across = level({ outer: boxPx(0, 0, 400, 400), holes: [u, boxPx(120, 170, 280, 230)] });
  bothWalks((fillColumns, walk) => {
    let xs = fillOnMiddleRows(drawn(overlap, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(lastIn(xs, 0, 150), 106, "overlap: the second hole's wall" + walk);
    assert.strictEqual(firstIn(xs, 150, 200), 186, "overlap: the first hole's wall, shrunk" + walk);
    assert.strictEqual(lastIn(xs, 200, 250), 214, "overlap: the second hole's far wall" + walk);
    assert.strictEqual(firstIn(xs, 250, 400), 294, "overlap: the first hole's far wall" + walk);
    xs = fillOnMiddleRows(drawn(across, 400, { fabric, fillColumns }), 400);
    assert.strictEqual(lastIn(xs, 0, 100), 86, "across: the U's outer wall" + walk);
    assert.strictEqual(firstIn(xs, 100, 140), 126, "across: the box's wall, shrunk" + walk);
    assert.strictEqual(lastIn(xs, 140, 200), 154, "across: the U's inner wall" + walk);
  });
});

test("buildQualityDesign: island shapes nobody chose leave no drawn ground unsewn", () => {
  // The tests above are concentric boxes. These are seeded: an outline (a box,
  // a round, a blob), a hole in it, and in the hole either rings nested one
  // inside the next or two or three islands side by side, with gaps from a
  // hair to several mm. One question, asked of the STITCHES with nothing of
  // the engine's: is every part of the drawn ground within a row of fill
  // thread? Shrunk, an island's rim was not; grown with no thought for the
  // ring beside it, a hair-thin moat ate into both its banks.
  const rnd = (seed) => { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  const shapeOf = (seed) => {
    const r = rnd(seed), about = (pts, k) => pts.map((p) => ({ x: 200 + (p.x - 200) * k, y: 200 + (p.y - 200) * k }));
    const kind = r(), n = 7 + Math.floor(r() * 9);
    const outer = kind < 0.35 ? boxPx(0, 0, 400, 400) : kind < 0.6 ? roundPx(200, 200, 200, 12 + Math.floor(r() * 36))
      : Array.from({ length: n }, (_, i) => { const k = 0.8 + 0.2 * r(); return { x: 200 + 200 * k * Math.cos(2 * Math.PI * i / n), y: 200 + 200 * k * Math.sin(2 * Math.PI * i / n) }; });
    // a gap, px: a third of them a hair (under any preset's compensation), a third under twice terry's, a third wide
    const gap = () => { const u = r(); return u < 0.33 ? 1 + 2 * r() : u < 0.66 ? 6 + 6 * r() : 14 + 40 * r(); };
    let k = 0.55 + 0.3 * r();
    const holes = [about(outer, k)];
    if (r() < 0.6) {
      for (let deep = 1 + Math.floor(r() * 3); deep > 0 && k > 0.2; deep--) { k -= gap() / 200; holes.push(about(outer, k)); }
    } else {
      const half = 200 * k * 0.55, count = 2 + Math.floor(r() * 2), g = gap(), w = (2 * half - g * (count - 1)) / count, h = half * (0.5 + 0.8 * r());
      for (let i = 0; i < count && w > 12; i++) {
        const x0 = 200 - half + i * (w + g);
        holes.push(r() < 0.5 ? boxPx(x0, 200 - h / 2, x0 + w, 200 + h / 2) : roundPx(x0 + w / 2, 200, Math.min(w, h) / 2, 8 + Math.floor(r() * 16)));
      }
    }
    return { outer, holes: holes.map((ring) => (r() < 0.4 ? ring.slice().reverse() : ring)).reverse() };
  };
  const toSegment = (p, u, v) => {
    const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy;
    const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0;
    return Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy));
  };
  for (let seed = 1; seed <= 24; seed++) {
    const shape = shapeOf(seed);
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const p of shape.outer) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); }
    const edges = [];
    for (const r of [shape.outer].concat(shape.holes)) for (let i = 0; i < r.length; i++) edges.push([r[i], r[(i + 1) % r.length]]);
    // drawn ground, on a 3 px grid, more than 0.1 mm in from every edge
    const ground = [];
    for (let y = y0 + 1.5; y < y1; y += 3) for (let x = x0 + 1.5; x < x1; x += 3) {
      const p = { x, y };
      let inside = false;
      for (const [u, v] of edges) if ((u.y > y) !== (v.y > y) && u.x + ((y - u.y) / (v.y - u.y)) * (v.x - u.x) > x) inside = !inside;
      if (inside && !edges.some(([u, v]) => toSegment(p, u, v) <= 1)) ground.push(p);
    }
    const asked = ground.filter((_, i) => i % Math.ceil(ground.length / 200) === 0);
    for (const fabricId of ["terry_towel", "pique_knit"]) {
      const fabric = FABRICS.getFabric(fabricId), label = "seed " + seed + ", " + fabricId;
      // the drawing's own width, so that a px is a stitch unit as in every test here
      const d = drawn(shape, x1 - x0, { fabric, fillColumns: false });
      assert.strictEqual(d.shapeOutlines[0].dropped, false, label);
      const sewn = [];
      for (const run of d.runs) {
        if (run.kind !== "fill") continue;
        let prev = null;
        for (let i = run.i0; i <= run.i1; i++) {
          const s = d.stitches[i];
          if (s.type === "trim") { prev = null; continue; }
          const p = { x: s.x + (x0 + x1) / 2, y: (y0 + y1) / 2 - s.y };
          if (s.type === "stitch" && prev) sewn.push([prev, p]);
          prev = p;
        }
      }
      const reach = 1.5 * fabric.densityAdjust + 1;   // a fill row, and a stitch's rounding
      const bare = asked.filter((p) => !sewn.some(([u, v]) => toSegment(p, u, v) <= reach));
      assert.strictEqual(bare.length, 0, label + ": " + bare.length + " of " + asked.length + " points of drawn ground have no fill thread within a row, the first at " + JSON.stringify(bare[0]));
    }
  }
});

test("fillColumns: left off, every stitch is the one it has always been", () => {
  for (const underlay of [false, true]) {
    const base = Object.assign({ underlay }, ANNULUS_OPTS);
    assert.deepStrictEqual(
      DG.buildQualityDesign(ANNULUS, Object.assign({ fillColumns: false }, base)).stitches,
      DG.buildQualityDesign(ANNULUS, base).stitches);
  }
});

// --- what the audit of the lock stitches found (2026-10-03, PR #609) ----------
//
// 18 threads in a 12,880-design sweep were a stub: a cut, two penetrations in
// one hole, and the end of the design. A scanline that passes exactly through
// a corner pointing up the rows finds a span of no length there (fill.js,
// above `cutColumns`; test/fill.test.js has it bare). The column walk made a
// column of it, and when that column was left for last with no way round to
// it, cut to it.

// The threads of a design: the penetrations between one cut (or the start, or
// a colour change) and the next.
function threadsOf(d) {
  const out = [[]];
  for (const s of d.stitches) {
    if (s.type === "end") break;
    if (s.type === "trim" || s.type === "color") { out.push([]); continue; }
    if (s.type === "stitch") out[out.length - 1].push(s);
  }
  return out.filter((t) => t.length);
}
const holesOf = (thread) => new Set(thread.map((s) => s.x + "," + s.y)).size;
// Two penetrations in one hole, one straight after the other.
function doubledAt(d) {
  const at = [];
  for (let i = 1; i < d.stitches.length; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (a.type === "stitch" && b.type === "stitch" && a.x === b.x && a.y === b.y) at.push([b.x, b.y]);
  }
  return at;
}

test("fillColumns: no cut is made to reach a corner that only happens to lie on a scanline", () => {
  // The audit's comb, as it found it. Its fill rows run along the teeth, 0.15
  // mm apart, and two of them run exactly along the side of a tooth: each
  // finds the tooth's top corner as a span of no length. The stream ended
  // `trim(37,175) stitch(37,175) stitch(37,175) end`.
  const comb = { outer: ring([[0, 0], [28, 0], [28, 245], [45.5, 245], [45.5, 0], [73.5, 0], [73.5, 245], [91, 245], [91, 0], [119, 0], [119, 245], [136.5, 245], [136.5, 0], [164.5, 0], [164.5, 245], [182, 245], [182, 0], [210, 0], [210, 245], [227.5, 245], [227.5, 0], [255.5, 0], [255.5, 245], [273, 245], [273, 0], [301, 0], [301, 245], [318.5, 245], [318.5, 0], [346.5, 0], [346.5, 350], [0, 350]]), holes: [] };
  const d = drawn(comb, 346.5);
  const threads = threadsOf(d);
  assert.deepStrictEqual(threads.filter((t) => holesOf(t) < 2).map((t) => [t.length, t[0].x, t[0].y]), [], "threads that never leave one hole");
  assert.ok(threads[threads.length - 1].length > 2, "the design ends on a thread of " + threads[threads.length - 1].length + " penetrations");
  assert.deepStrictEqual(doubledAt(d), [], "two penetrations in one hole");
  // and the thread still stays out of the gaps between the teeth
  assert.deepStrictEqual(openGroundMm(d, comb, 0.3), { sewn: 0, floats: 0 });
  // (without the flag the plain walk meets the same two corners on its way and
  // never cuts for one: the stub is the flag's own)
  const off = drawn(comb, 346.5, { fillColumns: false });
  assert.deepStrictEqual(threadsOf(off).filter((t) => holesOf(t) < 2), []);
});

test("fillColumns: the tip of a holed shape gets one penetration at most, not two in one hole", () => {
  // A house with a window, rows level: the first scanline of the fill IS the
  // point of the roof. With no underlay the walk began there, with two
  // penetrations in the tip; with one, it went there whenever it was nearest.
  // The lattice underlays of terry and fleece run at 45 degrees and did the
  // same at the eaves, which are the top of THEIR rows.
  //
  // (The window's walls lie ON the underlay's rows: x = 200 is one of the cap
  // preset's, 2 mm apart. Two spans meet at that wall's corner and the move
  // from one to the other has no length, which was a second penetration of
  // (50, 0) until such a move laid no stitch: test/fill.test.js has it bare.)
  const house = { outer: ring([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), holes: [boxPx(100, 150, 200, 250)], angleOverride: 0 };
  for (const fabric of [null].concat(FABRICS.FABRICS)) {
    for (const underlay of [false, true]) {
      const label = (fabric ? fabric.id : "no fabric") + ", underlay " + underlay;
      const d = drawn(house, 300, Object.assign({ underlay }, fabric ? { fabric } : {}));
      assert.deepStrictEqual(doubledAt(d), [], label);
      assert.deepStrictEqual(threadsOf(d).filter((t) => holesOf(t) < 2), [], label);
      assert.deepStrictEqual(cutsBy(d), { all: 0, fill: 0, underlay: 0, between: 0 }, label);
    }
  }
});

// --- where a pass ends (2026-10-03, after the corner fix's re-measure) ---------
//
// The move between two runs of a shape is cut where it leaves the ground the
// fill covers. Each tatami pass was told where the thread was, and never
// where it had to go next: an underlay sewn by the column walk ended wherever
// its last column ended, and when the run after it begins at a point of its
// own -- a fill or a lattice pass the plain walk sews -- the float between
// them was cut. 2,261 such cuts on 45,416 designs (the re-measure's own
// drawings, option on): the most of any kind the walk could do anything about.
// With the corner fix 388 of those designs gained a cut, 330 of the 404 here.
//
// A pass the plain walk sews begins where it begins, wherever the thread is.
// So it is BUILT first, and the pass before it is told (`to`, fill.js "where
// the walk ends"; test/fill.test.js has it bare).

test("fillColumns: an underlay ends where the thread can float on to the pass after it", () => {
  const cases = {
    // The re-measure's own drawing. The cap preset's zigzag ended on a barb
    // of the arrow, and the fill begins at the middle of its tail.
    "an arrow, the cap preset's zigzag": [ring([[300, 120], [180, 240], [180, 168], [0, 168], [0, 72], [180, 72], [180, 0]]), 300, "structured_cap", null],
    // Two lattice passes, and the fill after them.
    "an L under terry, rows at 45": [ring([[240, 0], [240, 60], [60, 60], [60, 180], [0, 180], [0, 0]]), 240, "terry_towel", 45],
    // No preset: the one tatami underlay, across the fill's rows.
    "a T, no preset, rows level": [ring([[0, 0], [240, 0], [240, 60], [150, 60], [150, 240], [90, 240], [90, 60], [0, 60]]), 240, null, 0],
    // The FIRST lattice pass into the second, which is the one the plain walk sews here.
    "two tips under terry, rows at 135": [ring([[0, 300], [25, 0], [50, 280], [75, 0], [100, 300]]), 100, "terry_towel", 135],
  };
  for (const name of Object.keys(cases)) {
    const [outer, widthPx, fabricId, angleOverride] = cases[name];
    const fabric = fabricId ? FABRICS.getFabric(fabricId) : null, pull = fabric ? fabric.pullCompMm : 0;
    const shape = { outer, holes: [] };
    if (angleOverride != null) shape.angleOverride = angleOverride;
    const d = drawn(shape, widthPx, fabric ? { fabric } : {});
    const cuts = cutsBy(d);
    assert.strictEqual(cuts.between, 0, name + ": " + JSON.stringify(cuts));
    assert.strictEqual(cuts.underlay, 0, name + ": " + JSON.stringify(cuts));
    assert.ok(cuts.fill <= 1, name + ": only center-out's own cut is left, " + JSON.stringify(cuts));
    // and the cut was not traded for thread off the fill
    assert.deepStrictEqual(offCoverMm(d, shape, pull, 0.15), { sewn: 0, floats: 0 }, name);
    assert.strictEqual(floatsOffCover(d, shape, pull), 0, name);
    // every run is still there, in the order it was
    const kinds = d.runs.map((r) => r.kind).join(" ");
    assert.ok(/^(underlay )+fill$/.test(kinds), name + ": " + kinds);
  }
});

test("fillColumns: a fill the plain walk sews is the fill it was, asked where it begins or not", () => {
  // The underlay asks where the fill begins before the fill is sewn, and the
  // asking must not move a stitch of it: where the plain walk begins and what
  // it sews do not turn on where the thread is. The fill of each drawing
  // above, record for record, against the same fill with the option off --
  // where nothing is asked -- on a shape whose plain fill the option leaves
  // alone (no turn of it runs outside the shape).
  const fillOf = (d) => { const r = d.runs.find((x) => x.kind === "fill"); return d.stitches.slice(r.i0, r.i1 + 1); };
  const l = { outer: ring([[240, 0], [240, 60], [60, 60], [60, 180], [0, 180], [0, 0]]), holes: [], angleOverride: 45 };
  for (const fabricId of [null, "structured_cap", "terry_towel", "fleece_sweatshirt"]) {
    const extra = fabricId ? { fabric: FABRICS.getFabric(fabricId) } : {};
    const on = drawn(l, 240, extra), off = drawn(l, 240, Object.assign({ fillColumns: false }, extra));
    assert.deepStrictEqual(fillOf(on), fillOf(off), fabricId || "no preset");
    assert.strictEqual(on._debug.nFill, 1);
    assert.strictEqual(on._debug.nCenterOut, off._debug.nCenterOut, fabricId || "no preset");
  }
});

test("fillColumns: the re-measure's two combs are one thread each -- a pass that comes out cut is walked again", () => {
  // The two drawings on which the corner fix's re-measure showed a design
  // GAINING cuts, and more than one. Neither is a float between two passes:
  // the walk itself strands a column. What a walk costs turns on its first
  // column, so a pass that comes out with a cut is walked again from the other
  // first columns the thread can float to, and the better walk is kept: here,
  // the one with no cut (fill.js, "which column first"; test/fill.test.js has
  // it bare).
  const fabric = FABRICS.getFabric("terry_towel"), pull = fabric.pullCompMm;
  const cases = {
    // No cut before the corner fix and three after it, all inside the second
    // lattice pass: threads of 315, 3, 3 and 1,756 penetrations.
    "four teeth 1.1 mm wide, rows at 61.3": [{ outer: ring([[321.56, 0], [321.56, 11.42], [70.94, 11.42], [70.94, 30.17], [321.56, 30.17], [321.56, 41.59], [70.94, 41.59], [70.94, 60.34], [321.56, 60.34], [321.56, 71.76], [70.94, 71.76], [70.94, 90.51], [321.56, 90.51], [321.56, 101.93], [0, 101.93], [0, 0]]), holes: [], angleOverride: 61.3 }, 321.56],
    // None before and two after: one on the float into the first lattice pass,
    // one inside it, and between them a thread of two penetrations. (Before,
    // "no cut" was 292 mm more thread, 99 mm of it travel round the outline.)
    "three teeth 4 mm wide pointing down": [{ outer: ring([[0, 333], [41.7, 333], [41.7, 89.78], [49.85, 89.78], [49.85, 333], [91.55000000000001, 333], [91.55000000000001, 89.78], [99.70000000000002, 89.78], [99.7, 333], [141.4, 333], [141.4, 0], [0, 0]]), holes: [] }, 141.4],
  };
  for (const name of Object.keys(cases)) {
    const [shape, widthPx] = cases[name];
    const d = drawn(shape, widthPx, { fabric });
    assert.deepStrictEqual(cutsBy(d), { all: 0, fill: 0, underlay: 0, between: 0 }, name);
    assert.deepStrictEqual(threadsOf(d).map((t) => t.length), [d.stitchCount], name + ": one thread");
    // and no cut was traded for thread off the fill
    assert.deepStrictEqual(offCoverMm(d, shape, pull, 0.15), { sewn: 0, floats: 0 }, name);
    assert.strictEqual(floatsOffCover(d, shape, pull), 0, name);
    assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "underlay", "underlay", "fill"], name);
  }
});

test("fillColumns: the float into a fill is not cut where a start further off can be floated to", () => {
  // The preset a left chest uses has no tatami underlay: an edge run, then
  // the fill. An eight-pointed star with its rows upright. The edge run ends
  // on the star's top point, and the corners the fill's walk could begin at
  // are out on the side points: of the eight nearest the thread can float to
  // none, an inside corner of the star being in the way of each. The walk
  // began at the nearest all the same, and the builder cut. A corner further
  // off, across the body, CAN be floated to. A walk that comes out cut is
  // walked again from the starts it had not looked at, and the cut on the
  // float in is one of the cuts it counts.
  const star = { outer: ring([[150, 0], [178.5, 80.5], [256, 44], [219.5, 121.5], [300, 150], [219.5, 178.5], [256, 256], [178.5, 219.5], [150, 300], [121.5, 219.5], [44, 256], [80.5, 178.5], [0, 150], [80.5, 121.5], [44, 44], [121.5, 80.5]]), holes: [], angleOverride: 90 };
  for (const fabricId of ["pique_knit", "canvas_tote"]) {
    const fabric = FABRICS.getFabric(fabricId);
    const d = drawn(star, 300, { fabric });
    assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "fill"], fabricId);
    assert.deepStrictEqual(cutsBy(d), { all: 0, fill: 0, underlay: 0, between: 0 }, fabricId);
    assert.deepStrictEqual(offCoverMm(d, star, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 }, fabricId);
    assert.strictEqual(floatsOffCover(d, star, fabric.pullCompMm), 0, fabricId);
  }
});

test("fillColumns: a comb whose second lattice pass needs the FIFTH other first column", () => {
  // Why a walk that comes out cut is walked from eight other first columns
  // and not from one or two. Twelve teeth 1.5 mm wide and 30 mm long under
  // fleece, rows at 61.3: the second lattice pass crosses every tooth on a
  // slant. Walked from the nearest first column it is cut twelve times, and
  // so it is from each of the next four, which all sew upward from one tooth
  // or another. The fifth sews downward from the first column of all, and is
  // cut once. (On a sweep of 9,084 designs four tries left 18 cuts, on three
  // combs, that eight do not; with no limit at all not one design differs.)
  const comb = [];
  for (let k = 0; k < 12; k++) comb.push([0, 30 * k], [0, 30 * k + 15], [k < 11 ? 300 : 360, 30 * k + 15], ...(k < 11 ? [[300, 30 * k + 30]] : []));
  comb.push([360, 0]);
  const shape = { outer: ring(comb), holes: [], angleOverride: 61.3 };
  const fabric = FABRICS.getFabric("fleece_sweatshirt");
  const d = drawn(shape, 360, { fabric });
  assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "underlay", "underlay", "fill"]);
  assert.deepStrictEqual(cutsBy(d), { all: 1, fill: 0, underlay: 1, between: 0 });
  assert.deepStrictEqual(offCoverMm(d, shape, fabric.pullCompMm, 0.15), { sewn: 0, floats: 0 });
  assert.strictEqual(floatsOffCover(d, shape, fabric.pullCompMm), 0);
});

test("fillColumns: a pass walked again is not left with a one-stitch thread for the cut it saves", () => {
  // What the independent re-measure of "where a pass ends" found (2026-10-04).
  // Its maze, a corridor 1.4 mm wide wound through a block 15 mm by 22 mm,
  // under fleece. The first lattice pass comes out with three cuts; walked
  // again it came out with two, and between them one row: a thread of two
  // penetrations, cut to and cut from. A stitch like that holds nothing, so
  // the cut it "saved" bought an underlay row that is as good as not sewn.
  // A walk is judged by its cuts and by its threads of fewer than four
  // penetrations (fill.js, "which column first"; test/fill.test.js has it bare).
  const maze = ring([[0, 0], [41.81, 0], [41.81, 13.69], [13.69, 13.69], [13.69, 27.84], [55.96, 27.84], [55.96, 0], [125.61, 0], [125.61, 27.84], [139.76, 27.84], [139.76, 0], [153.73, 0], [153.73, 41.53], [111.92, 41.53], [111.92, 13.69], [97.77, 13.69], [97.77, 99.54], [55.96, 99.54], [55.96, 85.85], [83.8, 85.85], [83.8, 71.7], [41.81, 71.7], [41.81, 143.86], [55.96, 143.86], [55.96, 116.02], [97.77, 116.02], [97.77, 143.86], [111.92, 143.86], [111.92, 85.85], [139.76, 85.85], [139.76, 71.7], [111.92, 71.7], [111.92, 58.01], [153.73, 58.01], [153.73, 99.54], [125.61, 99.54], [125.61, 157.55], [83.8, 157.55], [83.8, 129.71], [69.65, 129.71], [69.65, 157.55], [27.84, 157.55], [27.84, 58.01], [83.8, 58.01], [83.8, 13.69], [69.65, 13.69], [69.65, 41.53], [13.69, 41.53], [13.69, 201.87], [27.84, 201.87], [27.84, 174.03], [125.61, 174.03], [125.61, 201.87], [139.76, 201.87], [139.76, 116.02], [153.73, 116.02], [153.73, 215.56], [55.96, 215.56], [55.96, 201.87], [111.92, 201.87], [111.92, 187.72], [41.81, 187.72], [41.81, 215.56], [0, 215.56]]);
  const fleece = FABRICS.getFabric("fleece_sweatshirt");
  for (const angleOverride of [0, 90]) {
    const shape = { outer: maze, holes: [], angleOverride };
    const d = drawn(shape, 153.73, { fabric: fleece });
    const lens = threadsOf(d).map((t) => t.length), name = "the maze, rows at " + angleOverride;
    assert.deepStrictEqual(lens.filter((n) => n < 4), [], name + ": threads " + JSON.stringify(lens));
    assert.strictEqual(cutsBy(d).all, 3, name + ": the first walk's three, " + JSON.stringify(lens));
    assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "underlay", "underlay", "fill"], name);
    assert.strictEqual(floatsOffCover(d, shape, fleece.pullCompMm), 0, name);
  }
  // And of two walks with as many cuts, the one with fewer such threads.
  // Eight teeth 1 mm wide and 20 mm long under terry (the corner fix's
  // re-measure, its `pcomb-229`): seven cuts either way, and the first
  // lattice pass kept a walk with a thread of two penetrations in it where a
  // later walk, cut as often, has none.
  const comb = [];
  for (let k = 0; k < 8; k++) comb.push([16.71 * k, 278.11], [16.71 * k + 9.58, 278.11], ...(k < 7 ? [[16.71 * k + 9.58, 72.96], [16.71 * (k + 1), 72.96]] : []));
  comb.push([126.55, 0], [0, 0]);
  const terry = FABRICS.getFabric("terry_towel");
  const shape = { outer: ring(comb), holes: [] };
  const d = drawn(shape, 126.55, { fabric: terry });
  const lens = threadsOf(d).map((t) => t.length);
  assert.deepStrictEqual(lens.filter((n) => n < 4), [], "eight teeth: threads " + JSON.stringify(lens));
  assert.strictEqual(cutsBy(d).all, 7, "eight teeth: " + JSON.stringify(lens));
  assert.strictEqual(floatsOffCover(d, shape, terry.pullCompMm), 0);
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

// --- a ring handed over CLOSED (2026-10-03) ----------------------------------
//
// `[p0, p1, ..., pn, p0]`: the first point said again at the end. The repeat
// is an edge of no length, so it has no direction and no normal. offsetRing
// gave each of its two ends the normal of the one real edge beside it: the
// first was moved THREE times the distance along one (the mitre clamp), the
// last once along the other, and the corner between them became a wedge.
// Under a fabric preset the fill is sewn to the offset rings, so the wedge was
// sewn: on terry (0.6 mm), 1.8 mm outside a 40 mm box at its first corner.
// Found by the independent audit of the island fix (PR #613). It is older
// than every flag and it is every ring's: the outline, a hole, an island.
const closedRing = (r) => r.concat([{ x: r[0].x, y: r[0].y }]);
const fillRunsOf = (d) => d.runs.filter((s) => s.kind === "fill").map((s) => d.stitches.slice(s.i0, s.i1 + 1));
const lShape = () => ring([[0, 0], [400, 0], [400, 150], [150, 150], [150, 400], [0, 400]]);
// 10 px per mm and a target width equal to the drawing's: 1 px is 1 unit, the
// drawing centred on (200, 200), y up. The angle is fixed because the auto
// angle is read off the POINTS, and a point said twice is one more of them.
const sewnTo = (shape, fabricId, extra) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [Object.assign({ tierOverride: "fill", angleOverride: 0 }, shape)] }],
  Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 40, darkOnTop: false, underlay: true },
    fabricId ? { fabric: FABRICS.getFabric(fabricId) } : {}, extra || {}));

test("offsetRing: a ring that says its first point again at the end is moved as the same ring said once", () => {
  const rings = { "a box": boxPx(0, 0, 400, 400), "an L": lShape(), "a 24-gon": roundPx(200, 200, 200, 24) };
  for (const [name, open] of Object.entries(rings)) {
    for (const wound of [open, open.slice().reverse()]) {
      for (const outward of [true, false]) {
        assert.deepStrictEqual(DG.offsetRing(closedRing(wound), 6, outward), DG.offsetRing(wound, 6, outward),
          name + (wound === open ? "" : ", wound the other way") + (outward ? ", grown" : ", shrunk"));
      }
    }
  }
  // The thing itself: every corner of the box 6 px out on both axes. The first
  // corner used to come back twice, at (0, -18) and at (-6, 0).
  const grown = DG.offsetRing(closedRing(boxPx(0, 0, 400, 400)), 6, true);
  assert.strictEqual(grown.length, 4);
  boxPx(-6, -6, 406, 406).forEach((want, i) => {
    assert.ok(Math.hypot(grown[i].x - want.x, grown[i].y - want.y) < 1e-9, "corner " + i + " at " + JSON.stringify(grown[i]));
  });
});

test("offsetRing: a point said twice running anywhere in the ring is one corner", () => {
  const open = lShape(), want = DG.offsetRing(open, 6, true);
  const again = (p) => ({ x: p.x, y: p.y });
  for (let i = 0; i < open.length; i++) {
    const twice = open.slice(0, i + 1).concat([again(open[i])], open.slice(i + 1));
    assert.deepStrictEqual(DG.offsetRing(twice, 6, true), want, "corner " + i + " said twice");
  }
  assert.deepStrictEqual(DG.offsetRing(closedRing(closedRing(open)), 6, true), want, "the first point said three times");
  assert.deepStrictEqual(DG.offsetRing(open.flatMap((p) => [p, again(p)]), 6, true), want, "every corner said twice");
  // A closing point that was COMPUTED rarely lands exactly on the first: a
  // hair off it is the same corner, not an edge with a direction of its own.
  const hair = open.concat([{ x: open[0].x + 1e-12, y: open[0].y - 1e-12 }]);
  assert.deepStrictEqual(DG.offsetRing(hair, 6, true), want, "closed to within a hair");
});

test("offsetRing: a ring with fewer than three corners once the repeats are out is handed back as it was", () => {
  // Nothing to grow: no area, so no outward side. (An outline like this never
  // gets as far as its fill, a shape with no area being dropped first. A ring
  // in `holes` can, as an island: three points, two of them the same.)
  const a = { x: 0, y: 0 }, b = { x: 10, y: 0 };
  for (const flat of [[a, a, b, b], [a, b, b], [a, a, a]]) {
    assert.deepStrictEqual(DG.offsetRing(flat, 2, true), flat);
    assert.deepStrictEqual(DG.offsetRing(flat, 2, false), flat);
  }
});

test("offsetRing: a short edge is still an edge", () => {
  // What is taken out is a point said TWICE, to within rounding. A corner a
  // third of a pixel from the next one is a corner: the basic shapes' own
  // rings come that close (0.35 px), and a ring that says no point twice has
  // to come back point for point. (Widen the tolerance and every other test
  // here still passes: this is the one that holds it.)
  const box = boxPx(0, 0, 400, 400);
  for (const gap of [1e-6, 1e-3, 0.3]) {
    const chamfered = [{ x: gap, y: 0 }].concat(box.slice(1), [{ x: 0, y: gap }]);   // the first corner, cut off by `gap`
    assert.strictEqual(DG.offsetRing(chamfered, 6, true).length, 5, "a chamfer of " + gap + " px keeps both its corners");
  }
});

test("buildQualityDesign: under a fabric preset a closed outline gets the fill the same outline gets open", () => {
  // The audit's measure: a 40 mm box, left chest, terry. As five points its
  // fill reached 21.8 mm above the centre at the first corner; as four, 20.6
  // (the box's 20 and terry's 0.6).
  const terry = fillRunsOf(sewnTo({ outer: closedRing(boxPx(0, 0, 400, 400)), holes: [] }, "terry_towel")).flat().filter((s) => s.type === "stitch");
  assert.ok(terry.length > 1000, "the box is filled");
  // (within a row of 206, the box's 200 and terry's 6, and never past it)
  const top = Math.max(...terry.map((s) => s.y));
  assert.ok(top > 203 && top <= 206, "the top of the fill is 0.6 mm above the box and no more: " + top);
  for (const open of [boxPx(0, 0, 400, 400), lShape(), roundPx(200, 200, 200, 24)]) {
    for (const f of FABRICS.FABRICS) {
      assert.deepStrictEqual(fillRunsOf(sewnTo({ outer: closedRing(open), holes: [] }, f.id)), fillRunsOf(sewnTo({ outer: open, holes: [] }, f.id)),
        open.length + " corners on " + f.id);
    }
  }
});

test("buildQualityDesign: and a closed hole is shrunk as the same hole is open", () => {
  // A 20 mm hole in the 40 mm box. Terry's fill goes 0.6 mm into it on every
  // side: in units, to 94 from the centre. The wedge took it 1.8 mm in along
  // the top of the hole, from the first corner.
  const outer = boxPx(0, 0, 400, 400), hole = boxPx(100, 100, 300, 300);
  const terry = fillRunsOf(sewnTo({ outer, holes: [closedRing(hole)] }, "terry_towel")).flat().filter((s) => s.type === "stitch");
  assert.ok(terry.length > 1000, "the box is filled");
  assert.strictEqual(terry.filter((s) => Math.abs(s.x) < 93 && Math.abs(s.y) < 93).length, 0, "no fill stitch past the hole's compensation");
  for (const f of FABRICS.FABRICS) {
    for (const [name, shape] of [["the hole closed", { outer, holes: [closedRing(hole)] }], ["both closed", { outer: closedRing(outer), holes: [closedRing(hole)] }]]) {
      assert.deepStrictEqual(fillRunsOf(sewnTo(shape, f.id)), fillRunsOf(sewnTo({ outer, holes: [hole] }, f.id)), name + " on " + f.id);
    }
  }
});

test("buildQualityDesign: and a closed island is grown as the same island is open", () => {
  // A ring inside a hole is filled ground and grows, as the outline does: an
  // 8 mm island in a 24 mm hole in the 40 mm box. On terry its fill is sewn to
  // 4.6 mm from the centre on every side. The wedge took it to 5.7 at the
  // island's first corner, into the moat.
  const outer = boxPx(0, 0, 400, 400), hole = boxPx(80, 80, 320, 320), island = boxPx(160, 160, 240, 240);
  const terry = fillRunsOf(sewnTo({ outer, holes: [hole, closedRing(island)] }, "terry_towel")).flat().filter((s) => s.type === "stitch");
  const onIsland = terry.filter((s) => Math.abs(s.x) < 100 && Math.abs(s.y) < 100);   // the band round the moat starts at 114
  assert.ok(onIsland.length > 100, "the island is filled");
  // (the island's last row lies where the shape's rows fall: within one of them of 46, never past it)
  const top = Math.max(...onIsland.map((s) => Math.abs(s.y)));
  assert.ok(top > 43 && top <= 46, "the island's fill is 0.6 mm past its ring and no more: " + top);
  const cases = [
    ["the island closed", [hole, closedRing(island)], [hole, island]],
    ["island and hole closed, the island listed first", [closedRing(island), closedRing(hole)], [island, hole]],
  ];
  for (const f of FABRICS.FABRICS) {
    for (const [name, closed, open] of cases) {
      assert.deepStrictEqual(fillRunsOf(sewnTo({ outer, holes: closed }, f.id)), fillRunsOf(sewnTo({ outer, holes: open }, f.id)), name + " on " + f.id);
    }
  }
});

test("fillColumns: a closed ring's edge run lies where the same ring's does open", () => {
  // With the flag the edge run of a shape with a hole or an inside corner is
  // sewn on the ring moved 0.2 mm into the filled side (edgeRunRing), which is
  // offsetRing again: the first corner of a closed ring went 0.6 mm in instead.
  // With that gone these two come out stitch for stitch as they do open,
  // fabric or none. (Not every closed ring does: see the next test, and the
  // angle is fixed here.)
  const outer = boxPx(0, 0, 400, 400), hole = boxPx(100, 100, 300, 300);
  const cases = [
    ["an L", { outer: closedRing(lShape()), holes: [] }, { outer: lShape(), holes: [] }],
    ["a box with a hole", { outer: closedRing(outer), holes: [closedRing(hole)] }, { outer, holes: [hole] }],
  ];
  for (const [name, closed, open] of cases) {
    for (const fabricId of [null].concat(FABRICS.FABRICS.map((f) => f.id))) {
      assert.deepStrictEqual(sewnTo(closed, fabricId, { fillColumns: true }).stitches, sewnTo(open, fabricId, { fillColumns: true }).stitches,
        name + " on " + (fabricId || "no fabric"));
    }
  }
});

test("fillColumns: a ring closed at its only inside corner still has an inside corner", () => {
  // Which path the edge run takes is asked of the ring (isConvexRing), corner
  // by corner, and a corner with a side of no length was stepped over. Closed
  // AT its one inside corner, an arrowhead read as convex: its edge run went
  // toward the centroid as a convex ring's does, which for a ring that is not
  // convex can leave the drawing, and every run after it began somewhere
  // else. Found by the audit of the wedge fix, which had made the other path
  // right and could not reach it.
  const arrow = ring([[100, 200], [0, 400], [0, 0], [300, 0], [300, 400]]);   // 30 mm, the notch first
  const again = (p) => ({ x: p.x, y: p.y });
  const said = [["closed at the notch", closedRing(arrow)], ["every corner said twice", arrow.flatMap((p) => [p, again(p)])]];
  for (const [name, outer] of said) {
    for (const fabricId of [null, "pique_knit", "terry_towel"]) {
      assert.deepStrictEqual(sewnTo({ outer, holes: [] }, fabricId, { fillColumns: true, targetWidthMm: 30 }).stitches,
        sewnTo({ outer: arrow, holes: [] }, fabricId, { fillColumns: true, targetWidthMm: 30 }).stitches, name + " on " + (fabricId || "no fabric"));
    }
  }
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

test("cross_tatami underlay: one sparse pass across the fill, 1 mm rows, 4 mm stitches, no edge run", () => {
  // The recipe read off Kent's commissioned files (docs/underlay-audit-2026-10-05.md),
  // the Python engine's `cross_tatami` in the browser. A choice, not a default:
  // no preset in src/fabrics.js names it.
  assert.ok(FABRICS.FABRICS.every((f) => f.fillUnderlay !== "cross_tatami" && f.satinUnderlay !== "cross_tatami"));
  const box = { outer: boxPx(0, 0, 400, 300), holes: [], angleOverride: 0 };
  const build = (fillUnderlay) => drawn(box, 400, { fillColumns: false, fabric: fab({ fillUnderlay, pullCompMm: 0 }) });
  const d = build("cross_tatami");
  // edge_lattice is an edge walk and then a pass: two underlay runs. This is the pass alone.
  assert.deepStrictEqual(build("edge_lattice").runs.map((r) => r.kind), ["underlay", "underlay", "fill"]);
  assert.deepStrictEqual(d.runs.map((r) => r.kind), ["underlay", "fill"]);
  const segs = (kind) => {
    const out = [];
    for (const run of d.runs) {
      if (run.kind !== kind) continue;
      for (let i = run.i0 + 1; i <= run.i1; i++) {
        const a = d.stitches[i - 1], b = d.stitches[i];
        if (b.type !== "stitch") continue;
        const dx = (b.x - a.x) / 10, dy = (b.y - a.y) / 10;   // 0.1 mm units
        out.push({ len: Math.hypot(dx, dy), dir: ((Math.round(Math.atan2(dy, dx) * 180 / Math.PI) % 180) + 180) % 180, x: a.x / 10, y: a.y / 10 });
      }
    }
    return out;
  };
  const dominant = (list) => {
    const n = {};
    for (const s of list) if (s.len > 1.5) n[s.dir] = (n[s.dir] || 0) + 1;
    return +Object.keys(n).sort((p, q) => n[q] - n[p])[0];
  };
  const under = segs("underlay"), fillDir = dominant(segs("fill")), underDir = dominant(under);
  assert.strictEqual(Math.abs(fillDir - underDir), 90, "fill rows at " + fillDir + ", pass rows at " + underDir);
  const longest = Math.max(...under.map((s) => s.len));
  assert.ok(longest <= 4.0 + 0.15 && longest > 3.0, "longest underlay stitch " + longest + " mm");
  const across = underDir === 90 ? "x" : "y";
  const rows = [...new Set(under.filter((s) => s.dir === underDir && s.len > 1.5).map((s) => Math.round(s[across] * 10) / 10))].sort((p, q) => p - q);
  assert.ok(rows.length > 20, "rows: " + rows.length);
  const gaps = rows.slice(1).map((r, i) => r - rows[i]);
  assert.ok(gaps.every((g) => Math.abs(g - 1.0) < 0.15), "row gaps " + JSON.stringify(gaps.slice(0, 8)));
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
  // +1 each (2026-10-08): the edge-run underlay now closes on its start
  // corner instead of stopping up to one stitch short of it.
  assert.strictEqual(d.stitches.length, 4924, "total record count frozen");
  assert.strictEqual(d.stitchCount, 4773, "stitch count frozen (resize-density re-freeze, + the edge run's closing stitch)");
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
  // Measured on the THREAD, not the stitch count, since `splitSatin` went
  // default ON on 2026-09-11. A thresholded split makes the raw count
  // sensitive to exactly the sub-millimetre nudge described above — a cross
  // crossing 5.0 mm changes `k = ceil(cross / 3.0)` by a whole segment, and
  // the diff here reads 2 with the split off and 257 with it on. Total sewn
  // path is exactly invariant under splitting (every split point lies ON the
  // segment it divides), so it is both split-proof and a TIGHTER claim than
  // the count ever was: a 15 deg lean stretches each cross by at most
  // 1/cos(15 deg) = 1.0353, and nothing else about the column moves.
  const threadPath = (d) => {
    let sum = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type !== "stitch") { prev = null; continue; }
      if (prev) sum += Math.hypot(s.x - prev.x, s.y - prev.y);
      prev = s;
    }
    return sum;
  };
  const ratio = threadPath(dSlant) / threadPath(d0);
  assert.ok(ratio > 1 && ratio <= 1 / Math.cos((15 * Math.PI) / 180),
    `slant must stretch the crosses and nothing else — thread ratio ${ratio.toFixed(4)}`);
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

// ---- Fill row vs satin spacing: two physical choices (2026-09-04) ----------
//
// Until 2026-09-04 one `densityMm` option drove BOTH the tatami row pitch and
// the satin cross pitch, defaulting to 0.45 here and 0.4 for lettering. Kent's
// 2026-09-03 ruling (DOCTRINE "Fill row spacing is settled") moved the Python
// engine's machine.FILL_ROW_MM to 0.15, and fabrics.py's rule is that this
// engine makes the same physical choices. Satin is a same-rail pitch (Law 19)
// and stays at machine.SATIN_SPACING_MM = 0.4 — so the option had to split
// before the fill default could move without dragging satin to 0.15 with it.
// Fixtures: a 700 px square at pxPerMm 8 (87.5 mm, a plain fill) and a 400x8
// px bar (1 mm wide, a satin column), each alone so the tier is unambiguous.

const splitSquare = { outer: sq(0, 0, 700), holes: [] };
const splitBar = { outer: [{ x: 0, y: 0 }, { x: 400, y: 0 }, { x: 400, y: 8 }, { x: 0, y: 8 }], holes: [] };
const splitBase = { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 8, underlay: false, satinMaxWidthMm: 3 };
const splitRun = (shapes, extra) => DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes }], Object.assign({}, splitBase, extra));

// Read a constant straight out of the Python engine's machine.py, so the two
// engines cannot drift apart silently (fabrics.py's rule, enforced).
function machinePy(name) {
  const src = fs.readFileSync(__dirname + "/../digitizer/digitizer_core/machine.py", "utf8");
  const m = src.match(new RegExp("^" + name + "\\s*=\\s*([0-9.]+)", "m"));
  assert.ok(m, name + " not found in digitizer/digitizer_core/machine.py");
  return +m[1];
}

test("engine parity: FILL_ROW_MM and SATIN_SPACING_MM equal the Python engine's machine.py", () => {
  assert.strictEqual(DG.FILL_ROW_MM, 0.15, "the professional's pitch — Kent's ruling 2026-09-03");
  assert.strictEqual(DG.SATIN_SPACING_MM, 0.4, "the same-rail satin pitch, which did not move");
  assert.strictEqual(DG.FILL_ROW_MM, machinePy("FILL_ROW_MM"), "both engines make the same physical choice (fabrics.py)");
  assert.strictEqual(DG.SATIN_SPACING_MM, machinePy("SATIN_SPACING_MM"));
  // Not a geometry constant — it changes what the shopping list says, never
  // where a needle goes — but it has to agree for the same reason: a name and
  // a logo in one project must be priced on one basis. The browser lane quotes
  // metres for lettering/manual/shape designs, which never reach the service.
  assert.strictEqual(DG.THREAD_LENGTH_FACTOR, 1.35, "machine.py's operator-estimate rule of thumb");
  assert.strictEqual(DG.THREAD_LENGTH_FACTOR, machinePy("THREAD_LENGTH_FACTOR"));
});

test("buildQualityDesign: the fill default is FILL_ROW_MM (0.15), three times the rows of the old 0.45", () => {
  const dflt = splitRun([splitSquare], {});
  const named = splitRun([splitSquare], { fillRowMm: 0.15 });
  const old = splitRun([splitSquare], { densityMm: 0.45 });
  assert.strictEqual(dflt._debug.nFill, 1);
  assert.strictEqual(dflt._debug.nSatin, 0);
  assert.deepStrictEqual(dflt.stitches, named.stitches, "no option at all == fillRowMm 0.15");
  // 0.45 / 0.15 = 3x the rows, same stitches per row: measured 6101 -> 18305.
  const ratio = dflt.stitchCount / old.stitchCount;
  assert.ok(ratio > 2.8 && ratio < 3.2, "fill stitches ~3x the old default: " + old.stitchCount + " -> " + dflt.stitchCount);
});

test("buildQualityDesign: satin did NOT follow the fill row — the default is byte-identical to the old 0.4", () => {
  const dflt = splitRun([splitBar], {});
  // What the Studio passed for every image/manual/shape element until 2026-09-04.
  const studioBefore = splitRun([splitBar], { densityMm: 0.4 });
  const named = splitRun([splitBar], { satinSpacingMm: 0.4 });
  assert.strictEqual(dflt._debug.nSatin, 1);
  assert.strictEqual(dflt._debug.nFill, 0);
  assert.deepStrictEqual(dflt.stitches, studioBefore.stitches, "satin at the default == satin at the old explicit 0.4");
  assert.deepStrictEqual(dflt.stitches, named.stitches, "== satinSpacingMm 0.4");
  // The case the split exists to prevent: the fill pitch applied to satin
  // would pile ~2.7x the crosses onto every column.
  const atFillPitch = splitRun([splitBar], { satinSpacingMm: 0.15 });
  assert.ok(atFillPitch.stitchCount > 2.4 * dflt.stitchCount,
    "0.15 on satin would be " + atFillPitch.stitchCount + " crosses against " + dflt.stitchCount);
  // And the fill row does not reach a satin column at all.
  const fillOnly = splitRun([splitBar], { fillRowMm: 0.15 });
  assert.deepStrictEqual(fillOnly.stitches, dflt.stitches, "fillRowMm is not a satin input");
});

test("buildQualityDesign: legacy densityMm still drives BOTH spacings, and the split names win over it", () => {
  // Every snapshot pinned in this file passes an explicit densityMm (0.4 or
  // 0.5) and relies on this: the pre-split option is fill AND satin at that
  // number, exactly as before.
  const region = [splitSquare, splitBar];
  const legacy = splitRun(region, { densityMm: 0.5 });
  const spelled = splitRun(region, { fillRowMm: 0.5, satinSpacingMm: 0.5 });
  assert.strictEqual(legacy._debug.nFill, 1);
  assert.strictEqual(legacy._debug.nSatin, 1);
  assert.deepStrictEqual(legacy.stitches, spelled.stitches, "densityMm 0.5 == fillRowMm 0.5 + satinSpacingMm 0.5");
  const mixed = splitRun(region, { densityMm: 0.5, fillRowMm: 0.15 });
  const ref = splitRun(region, { fillRowMm: 0.15, satinSpacingMm: 0.5 });
  assert.deepStrictEqual(mixed.stitches, ref.stitches, "fillRowMm overrides densityMm for the fill, satin keeps densityMm");
  assert.notDeepStrictEqual(mixed.stitches, legacy.stitches);
});

test("buildQualityDesign: fabric densityAdjust scales the satin pitch as well as the fill row (parity with stage7_sequence.py)", () => {
  // The Python engine multiplies BOTH row_mm and satin_spacing_mm by the
  // preset's density_adjust because this engine already did (its own comment
  // cites digitize.js); the split must not have quietly dropped satin's share.
  const fabricAt = (adj) => fab({ densityAdjust: adj, pullCompMm: 0, fillUnderlay: "none", satinUnderlay: "none" });
  const satin10 = splitRun([splitBar], { fabric: fabricAt(1.0) }).stitchCount;
  const satin085 = splitRun([splitBar], { fabric: fabricAt(0.85) }).stitchCount;
  const fill10 = splitRun([splitSquare], { fabric: fabricAt(1.0) }).stitchCount;
  const fill085 = splitRun([splitSquare], { fabric: fabricAt(0.85) }).stitchCount;
  assert.ok(satin085 > satin10, "pile (0.85) tightens satin crosses: " + satin10 + " -> " + satin085);
  assert.ok(fill085 > fill10, "and fill rows: " + fill10 + " -> " + fill085);
});

test("buildLetteringDesign: satinSpacingMm names the satin pitch; default, named and legacy densityMm are one design", () => {
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40, underlay: false };
  const dflt = DG.buildLetteringDesign(font, "AB", base);
  const named = DG.buildLetteringDesign(font, "AB", { ...base, satinSpacingMm: 0.4 });
  const legacy = DG.buildLetteringDesign(font, "AB", { ...base, densityMm: 0.4 });
  assert.deepStrictEqual(dflt, named);
  assert.deepStrictEqual(dflt, legacy);
  assert.strictEqual(dflt.stitchCount, 703, "the number satinfont.test.js pins — lettering never moved");
  // Lettering has no fill, so the fill ruling is invisible from here.
  const withFillRow = DG.buildLetteringDesign(font, "AB", { ...base, fillRowMm: 0.15 });
  assert.deepStrictEqual(withFillRow, dflt, "fillRowMm is not a lettering option and changes nothing");
});

// ---- The reported size IS the sewn size ----------------------------------
//
// Both builders used to report `fitScale`'s target box — the glyph outline (or
// the traced polygons) scaled to the garment placement box. That box is the
// INPUT to routing: pull compensation and the weight preset then push the
// satin rails outward, so the thread lands outside the number describing it.
//
// The measurement that opened this (2026-09-07, 10 garments x 85 shipped fonts
// x 3 texts x 3 weights = 7,470 lettering designs): 4,898 of them — 65.6% —
// put thread outside the placement box they had just been fit to, by up to
// 9.6 mm, and 4 of them told the hoop ceiling check "fits" when the actual
// thread needs the hoop rotated. Meanwhile SizePanel showed the honest number
// (combine.js bboxMmFromStitches), so ONE design displayed two widths at once:
// 127.0 mm in the field caption and 5.05 in = 128.3 mm in the size field,
// whose own max was 5.00.
//
// These pin the invariant, not any particular number — the sizes here move
// whenever routing does, and that is fine; what must never come back is a
// reported size that is not the extent of the thread.
const bboxOfStitches = (stitches) => {
  const geo = stitches.filter((s) => s.type !== "color" && s.type !== "end");
  const xs = geo.map((s) => s.x), ys = geo.map((s) => s.y);
  return { w: (Math.max(...xs) - Math.min(...xs)) / 10, h: (Math.max(...ys) - Math.min(...ys)) / 10 };
};

test("buildLetteringDesign: widthMM/heightMM are the stitch bbox, not the width that was asked for", () => {
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, underlay: false };
  for (const targetWidthMm of [20, 40, 80]) {
    const d = DG.buildLetteringDesign(font, "AB", { ...base, targetWidthMm });
    const bb = bboxOfStitches(d.stitches);
    assert.ok(Math.abs(d.widthMM - bb.w) < 1e-9, `w@${targetWidthMm}: reported ${d.widthMM} vs sewn ${bb.w}`);
    assert.ok(Math.abs(d.heightMM - bb.h) < 1e-9, `h@${targetWidthMm}: reported ${d.heightMM} vs sewn ${bb.h}`);
    // And it is genuinely WIDER than the request — the gap this closes.
    assert.ok(d.widthMM > targetWidthMm, `pull comp widens ${targetWidthMm} to ${d.widthMM}`);
  }
});

test("buildLetteringDesign: the sewn extent is reported unrotated too, not only when rotationDeg is set", () => {
  // The recompute used to be gated on rotationDeg, on the reasoning that only
  // rotation moves the axis-aligned box. Rotation is the largest such move,
  // not the only one.
  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const base = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40, underlay: false };
  for (const rotationDeg of [0, 90]) {
    const d = DG.buildLetteringDesign(font, "AB", { ...base, rotationDeg });
    const bb = bboxOfStitches(d.stitches);
    assert.ok(Math.abs(d.widthMM - bb.w) < 1e-9, `rot ${rotationDeg}: ${d.widthMM} vs ${bb.w}`);
    assert.ok(Math.abs(d.heightMM - bb.h) < 1e-9, `rot ${rotationDeg}: ${d.heightMM} vs ${bb.h}`);
  }
});

test("buildQualityDesign: widthMM/heightMM are the stitch bbox, and the end record at the origin does not stretch it", () => {
  // A square placed well away from the design origin — if the trailing
  // {x:0,y:0,type:"end"} were counted, the reported size would blow up to the
  // distance from the origin instead of the size of the square.
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 10, 10], shapes: [{ outer: sq(200, 200, 100), holes: [] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, underlay: false, satinMaxWidthMm: 3 }
  );
  assert.ok(d.stitches.some((s) => s.type === "end"), "this builder does append an end record");
  const bb = bboxOfStitches(d.stitches);
  assert.ok(Math.abs(d.widthMM - bb.w) < 1e-9, `reported ${d.widthMM} vs sewn ${bb.w}`);
  assert.ok(Math.abs(d.heightMM - bb.h) < 1e-9, `reported ${d.heightMM} vs sewn ${bb.h}`);
});

test("designExtentMm falls back to the fit target when a build emits no geometry at all", () => {
  // An empty region list returns the documented empty design (0x0) rather than
  // an Infinity-derived NaN from an empty bbox.
  const d = DG.buildQualityDesign([], { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1 });
  assert.strictEqual(d.widthMM, 0);
  assert.strictEqual(d.heightMM, 0);
  assert.strictEqual(d.stitchCount, 0);
});

test("engine parity: travel records never widen a design, so the JS and Python size rules agree", () => {
  // The two engines define "how big is this design" with DIFFERENT record sets
  // and must still return the same number:
  //   - JS (app/src/lib/combine.js bboxMmFromStitches, and designExtentMm here)
  //     takes stitch + jump + trim, skipping color and end — matching
  //     preview.js's fitTransform, so the preview frames what it measures.
  //   - Python (digitizer_core/adapter.design_bbox_units) takes sewn
  //     penetrations ONLY: "jump/trim/color records mark where the needle
  //     travels, not where thread lands".
  // They agree because of an invariant neither file states: a jump is emitted
  // at the first point of the run it travels to, and a trim at the PREVIOUS
  // sewn position — both are already sewn points, so neither can sit outside
  // the sewn hull. Measured 2026-09-07 over 249 lettering designs (85 shipped
  // fonts x 3 texts) plus the image path: zero disagreements, worst gap 0.000
  // mm. If that ever stops holding, one engine starts reporting a size the
  // other does not, and this is where it shows up.
  const withTravel = (s) => s.type !== "color" && s.type !== "end";
  const sewnOnly = (s) => s.type === "stitch";
  const span = (st, pred) => {
    const pts = st.filter(pred);
    const xs = pts.map((s) => s.x), ys = pts.map((s) => s.y);
    return [Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
  };

  // Two squares far apart: forces real trims and jumps between them.
  const d = DG.buildQualityDesign(
    [{ rgb: [10, 10, 10], shapes: [{ outer: sq(0, 0, 60), holes: [] }, { outer: sq(200, 200, 60), holes: [] }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 1, underlay: true, satinMaxWidthMm: 3 }
  );
  const types = new Set(d.stitches.map((s) => s.type));
  assert.ok(types.has("jump") && types.has("trim") && types.has("end"),
    "fixture must actually contain travel records: " + [...types].join(","));
  assert.deepStrictEqual(span(d.stitches, withTravel), span(d.stitches, sewnOnly));

  const font = JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
  const lt = DG.buildLetteringDesign(font, "A B", { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8, targetWidthMm: 40 });
  assert.deepStrictEqual(span(lt.stitches, withTravel), span(lt.stitches, sewnOnly));
});

// ---- Lock stitches on the lettering lane (ported 2026-09-14) ----------------
// Until this port ZERO tie/lock records existed anywhere in src/ — the only
// lock/tie match in the whole browser lane was the brand name "Baby Lock" in a
// garments.js comment — while the Python lane has always tied every block
// unconditionally (stitches.apply_ties, no config flag). A lettering file
// exported from the Studio could start or end its thread with nothing holding
// it. Default OFF: it changes every .dst/.pes a customer exports, so the flip
// is Kent's, and with the flag off output must be byte-identical to before.

const _tieFont = () => JSON.parse(fs.readFileSync(__dirname + "/../test/fixtures/fonts/geneva_simple.json", "utf8"));
const _tieBase = { garment: { widthIn: 5, heightIn: 2.25 }, pxPerMm: 8 };
const _fingerprint = (d) => d.stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";");
const _count = (d, k) => d.stitches.filter((s) => s.type === k).length;

test("ties: OFF by default, and the flag off is byte-identical to omitting it", () => {
  const font = _tieFont();
  const omitted = DG.buildLetteringDesign(font, "Fritsch's", { ..._tieBase });
  const explicitOff = DG.buildLetteringDesign(font, "Fritsch's", { ..._tieBase, ties: false });
  assert.strictEqual(_fingerprint(omitted), _fingerprint(explicitOff));
  assert.strictEqual((omitted._debug || {}).nTies || 0, 0, "no ties emitted with the flag off");
});

test("ties: ON adds lock stitches and NOT ONE trim", () => {
  // The half of the dossier's estimate that reproduced exactly. A tie is sewn
  // thread at a point the needle already occupies, so it can never create a
  // travel long enough to cut — if this ever fails, ties are being emitted
  // somewhere other than on top of an existing penetration.
  const font = _tieFont();
  const off = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: false });
  const on = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: true });
  assert.ok(_count(on, "stitch") > _count(off, "stitch"), "ties add stitches");
  assert.strictEqual(_count(on, "trim"), _count(off, "trim"), "ties must add no trims");
  assert.strictEqual(_count(on, "jump"), _count(off, "jump"), "ties must add no jumps");
  assert.strictEqual(_count(on, "color"), _count(off, "color"), "ties must add no colour changes");
});

test("ties: the count follows apply_ties' own rule — one in at the start, one either side of every cut", () => {
  // Python ties the first run, both sides of every trim, and the last run:
  // 2 + 2*trims. Pinning the RULE rather than a number, so a font whose
  // fragmentation changes does not silently rewrite the expectation.
  const font = _tieFont();
  for (const text of ["A", "AB", "Fritsch's Stitches"]) {
    const on = DG.buildLetteringDesign(font, text, { ..._tieBase, ties: true });
    const trims = _count(on, "trim");
    assert.strictEqual(on._debug.nTies, 2 + 2 * trims, `"${text}": ${on._debug.nTies} ties against ${trims} trims`);
  }
});

test("ties: each lock costs exactly TIE_STITCHES+1 stitches, so the bill is arithmetic", () => {
  const font = _tieFont();
  const off = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: false });
  const on = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: true });
  // tieRun returns [at, inner, at, inner, at] for TIE_STITCHES=3 and the
  // leading `at` is dropped (the needle is already standing there), so 4.
  assert.strictEqual(_count(on, "stitch") - _count(off, "stitch"), on._debug.nTies * 4);
});

test("ties: a lock never reaches PAST the point it is laid toward", () => {
  // Python's tie_run earns this the hard way — its first smoke run put the
  // design's bounding box 0.8 mm outside its own artwork, and on a garment an
  // overshooting tie reads as a stray stitch someone has to trim off. So the
  // tied design's extents must not grow beyond the untied one's.
  const font = _tieFont();
  const box = (d) => {
    const pts = d.stitches.filter((s) => s.type === "stitch");
    return { x0: Math.min(...pts.map((p) => p.x)), x1: Math.max(...pts.map((p) => p.x)),
             y0: Math.min(...pts.map((p) => p.y)), y1: Math.max(...pts.map((p) => p.y)) };
  };
  for (const text of ["A", "Fritsch's Stitches"]) {
    const a = box(DG.buildLetteringDesign(font, text, { ..._tieBase, ties: false }));
    const b = box(DG.buildLetteringDesign(font, text, { ..._tieBase, ties: true }));
    assert.ok(b.x0 >= a.x0 && b.y0 >= a.y0 && b.x1 <= a.x1 && b.y1 <= a.y1,
      `"${text}": tied box ${JSON.stringify(b)} escaped untied box ${JSON.stringify(a)}`);
  }
});

test("ties: every lock lands on a penetration that was already there", () => {
  // The structural claim behind "no added trims": a tie bounces between an
  // existing point and a point INTO the shape, so it introduces no new travel.
  // Every tie stitch must therefore sit within one leg (0.8mm, ~8 DST units at
  // this scale) of its anchor — checked as "no tie stitch is a long move".
  const font = _tieFont();
  const on = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: true });
  const off = DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties: false });
  const longest = (d) => {
    let m = 0, prev = null;
    for (const s of d.stitches) {
      if (s.type === "stitch" && prev) m = Math.max(m, Math.hypot(s.x - prev.x, s.y - prev.y));
      prev = (s.type === "stitch" || s.type === "jump") ? s : prev;
    }
    return m;
  };
  assert.ok(longest(on) <= longest(off) + 1e-9,
    `ties introduced a longer sewn move (${longest(on)}) than the untied design had (${longest(off)})`);
});

test("tieRun: on a path SHORTER than one leg, the lock stops at the far point", () => {
  // The guard `leg = min(TIE_STITCH_MM, d)`. Unreachable through
  // buildLetteringDesign on ordinary text — every run there opens with a cross
  // wider than 0.8 mm — so a mutation deleting the min() passed the entire
  // suite. Tested directly instead of hoping a fixture wanders into it.
  const at = { x: 0, y: 0 };
  const near = { x: 0.3, y: 0 };            // 0.3 mm: shorter than the 0.8 leg
  const pts = DG.tieRun(at, near);
  for (const p of pts) {
    assert.ok(p.x <= near.x + 1e-9, `tie reached x=${p.x}, past the point it was laid toward (${near.x})`);
  }
  assert.ok(pts.some((p) => Math.abs(p.x - near.x) < 1e-9), "the lock should reach the far point exactly");
});

test("tieRun: on a long path the leg is exactly TIE_STITCH_MM, and it starts and ends at the anchor", () => {
  const at = { x: 0, y: 0 };
  const pts = DG.tieRun(at, { x: 100, y: 0 });
  assert.strictEqual(pts.length, DG.TIE_STITCHES + 2, "3 legs bouncing between two points, closing back at the anchor");
  assert.deepStrictEqual(pts[0], at);
  assert.deepStrictEqual(pts[pts.length - 1], at);
  const inner = pts[1];
  assert.ok(Math.abs(inner.x - DG.TIE_STITCH_MM) < 1e-9, `leg is ${inner.x}, expected ${DG.TIE_STITCH_MM}`);
  // it really bounces: odd indices are the inner point, even ones the anchor
  pts.forEach((p, i) => assert.deepStrictEqual(p, i % 2 === 0 ? at : inner, `point ${i}`));
});

test("tieRun: a zero-length path yields no bounce rather than a NaN direction", () => {
  const at = { x: 5, y: 5 };
  assert.deepStrictEqual(DG.tieRun(at, { x: 5, y: 5 }), [at]);
});

// ---- Lock stitches on the SHAPE lane, and one rule for both (2026-10-03) ----
// The 09-14 port reached buildLetteringDesign only. buildQualityDesign -- manual
// draw, basic shapes, SVG import, the flatten lane -- still tied nothing: every
// trim there left two loose ends. `ties: true` now means the same thing in both
// builders, and it is asked of the FINISHED record stream, which is in DST
// units: the two things the lettering port got wrong were both about where it
// asked. Its leg was 0.8 PIXELS (0.2 to 2.0 mm, by resolution and size), and
// its tie-in sat in front of the run's own first stitch, so that stitch became
// a second penetration of the same hole.
const _same = (p, q) => p.x === q.x && p.y === q.y;
// A lock is a bounce between exactly two places (Python's `strip_ties` finds
// them the same way): a, b, a, b. -> the leg of each, in DST units.
const _lockLegs = (d) => {
  const s = d.stitches, out = [];
  for (let i = 0; i + 3 < s.length; i++) {
    if (![0, 1, 2, 3].every((k) => s[i + k].type === "stitch")) continue;
    if (!_same(s[i], s[i + 2]) || !_same(s[i + 1], s[i + 3]) || _same(s[i], s[i + 1])) continue;
    out.push(Math.hypot(s[i + 1].x - s[i].x, s[i + 1].y - s[i].y));
    i += 3;
  }
  return out;
};
// The stream cut into threads: the records between two cuts.
const _threads = (d) => {
  const out = [[]];
  for (const s of d.stitches) {
    if (s.type === "trim" || s.type === "color" || s.type === "end") out.push([]);
    else out[out.length - 1].push(s);
  }
  return out.filter((t) => t.length);
};
// The two ends of a thread's sewing: its first and last pair of penetrations
// that follow one another and are not the same place. null when it has none.
const _sewnEnds = (thread) => {
  const pairs = [];
  for (let k = 0; k + 1 < thread.length; k++) {
    if (thread[k].type === "stitch" && thread[k + 1].type === "stitch" && !_same(thread[k], thread[k + 1])) pairs.push(k);
  }
  return pairs.length ? { first: pairs[0], last: pairs[pairs.length - 1] + 1 } : null;
};
const _zeroLength = (d) => {
  let n = 0;
  for (let i = 1; i < d.stitches.length; i++) {
    if (d.stitches[i].type === "stitch" && d.stitches[i - 1].type === "stitch" && _same(d.stitches[i], d.stitches[i - 1])) n++;
  }
  return n;
};
// Two colours, three shapes far apart, one of them with a hole: a colour
// change, a trim between shapes, floats across the hole, and center-out's cut.
const _tieShapes = (extra) => DG.buildQualityDesign(
  [{ rgb: [10, 10, 10], shapes: [{ outer: sq(0, 0, 200), holes: [sq(60, 60, 50)], tierOverride: "fill" }, { outer: sq(600, 600, 180), holes: [], tierOverride: "fill" }] },
   { rgb: [200, 30, 30], shapes: [{ outer: sq(300, 0, 160), holes: [], tierOverride: "fill" }] }],
  Object.assign({ garment: { widthIn: 6, heightIn: 6 }, pxPerMm: 10, darkOnTop: false, underlay: true }, extra || {}));

test("ties (shapes): OFF by default, and the flag off is byte-identical to omitting it", () => {
  const omitted = _tieShapes(), explicitOff = _tieShapes({ ties: false });
  assert.strictEqual(_fingerprint(omitted), _fingerprint(explicitOff));
  assert.deepStrictEqual(omitted.runs, explicitOff.runs);
  assert.strictEqual((omitted._debug || {}).nTies || 0, 0, "no ties emitted with the flag off");
  assert.strictEqual(_lockLegs(omitted).length, 0, "and nothing in the untied design reads as a lock");
});

test("ties (shapes): ON locks every thread where it starts and where it is cut", () => {
  // `apply_ties`' question: is the thread starting here, or being cut here.
  // Not "did the needle lift": a float that is not cut leaves the thread whole.
  const off = _tieShapes(), on = _tieShapes({ ties: true });
  const threads = _threads(on);
  assert.ok(_count(on, "trim") >= 3, "fixture: a colour change, a trim between shapes, a cut inside a fill");
  assert.ok(threads.some((t) => t.some((s, k) => k > 0 && s.type === "jump")), "fixture: a float inside a thread");
  for (const [ti, t] of threads.entries()) {
    const ends = _sewnEnds(t);
    assert.ok(ends, `thread ${ti} sews nothing`);
    // in: at, inner, at, inner, at -- then on along the stitch it lies on
    const a = t.slice(ends.first, ends.first + 5);
    assert.ok(_same(a[0], a[2]) && _same(a[2], a[4]) && _same(a[1], a[3]), `thread ${ti} does not open with a lock`);
    // off: the same bounce closing the thread, back on its last penetration
    const z = t.slice(ends.last - 4, ends.last + 1);
    assert.ok(_same(z[0], z[2]) && _same(z[2], z[4]) && _same(z[1], z[3]), `thread ${ti} does not close with a lock`);
  }
  assert.strictEqual(on._debug.nTies, 2 * threads.length);
  assert.strictEqual(_count(on, "stitch") - _count(off, "stitch"), 4 * on._debug.nTies, "a lock is four stitches");
  assert.strictEqual(on.stitchCount, _count(on, "stitch"), "and the design's stitch count is the tied stream's");
  // rows at 45 degrees: a leg of 8 units is 5.66 across and 5.66 up
  const slanted = _tieShapes({ ties: true, perRegionAngle: false });
  assert.ok(_lockLegs(slanted).length >= 2 && slanted.stitches.every((s) => Number.isInteger(s.x) && Number.isInteger(s.y)),
    "the stream stays in whole DST units");
  for (const k of ["trim", "jump", "color", "end"]) assert.strictEqual(_count(on, k), _count(off, k), `ties must add no ${k}`);
});

test("ties (shapes): take the locks out and the design is the untied one, record for record", () => {
  // Nothing else moves. Each lock is the four records after its anchor.
  const off = _tieShapes(), on = _tieShapes({ ties: true });
  const s = on.stitches, kept = [];
  for (let i = 0; i < s.length; i++) {
    kept.push(s[i]);
    const w = s.slice(i, i + 5);
    if (w.length === 5 && w.every((r) => r.type === "stitch") && _same(w[0], w[2]) && _same(w[2], w[4]) && _same(w[1], w[3]) && !_same(w[0], w[1])) i += 4;
  }
  assert.strictEqual(kept.map((r) => `${r.x},${r.y},${r.type}`).join(";"), _fingerprint(off));
});

test("ties: a lock's leg is 0.8 mm, whatever the resolution and whatever the size -- both builders", () => {
  // In DST units (0.1 mm): never over 8, and 8 wherever the stitch it lies on
  // has room. The lettering port measured 0.3, 0.5, 2.0 and 0.2 mm on these.
  const font = _tieFont();
  const want = DG.TIE_STITCH_MM * 10;
  const check = (name, d) => {
    const legs = _lockLegs(d);
    assert.ok(legs.length >= 2, `${name}: no lock found`);
    const longest = Math.max(...legs);
    assert.ok(Math.abs(longest - want) <= 0.75, `${name}: longest lock leg is ${(longest / 10).toFixed(2)} mm, not ${DG.TIE_STITCH_MM}`);
  };
  for (const o of [{ pxPerMm: 8 }, { pxPerMm: 8, targetWidthMm: 40 }, { pxPerMm: 2 }, { pxPerMm: 20 }]) {
    check("lettering " + JSON.stringify(o), DG.buildLetteringDesign(font, "AB", Object.assign({ garment: { widthIn: 5, heightIn: 2.25 }, ties: true }, o)));
  }
  for (const o of [{ pxPerMm: 10 }, { pxPerMm: 2 }, { pxPerMm: 40 }, { pxPerMm: 10, targetWidthMm: 30 }]) {
    check("shapes " + JSON.stringify(o), _tieShapes(Object.assign({ ties: true }, o)));
  }
});

test("ties: a lock adds no second penetration of the same hole -- both builders", () => {
  // The lettering port put its tie-in in FRONT of the run's own first stitch:
  // inner, at, inner, at, and then `at` again. The writers do not dedupe.
  const font = _tieFont();
  const lt = (ties) => DG.buildLetteringDesign(font, "Fritsch's Stitches", { ..._tieBase, ties });
  assert.strictEqual(_zeroLength(lt(true)), _zeroLength(lt(false)), "lettering");
  assert.strictEqual(_zeroLength(_tieShapes({ ties: true })), _zeroLength(_tieShapes()), "shapes");
});

test("ties (shapes): a lock never reaches past the stitch it lies on, and no sewn move gets longer", () => {
  const box = (d) => {
    const pts = d.stitches.filter((s) => s.type === "stitch");
    return [Math.min(...pts.map((p) => p.x)), Math.min(...pts.map((p) => p.y)), Math.max(...pts.map((p) => p.x)), Math.max(...pts.map((p) => p.y))];
  };
  const longest = (d) => {
    let m = 0;
    for (let i = 1; i < d.stitches.length; i++) {
      const s = d.stitches[i], p = d.stitches[i - 1];
      if (s.type === "stitch" && (p.type === "stitch" || p.type === "jump")) m = Math.max(m, Math.hypot(s.x - p.x, s.y - p.y));
    }
    return m;
  };
  for (const extra of [{}, { fillColumns: true }, { fabric: FABRICS.getFabric("pique_knit") }]) {
    const off = _tieShapes(extra), on = _tieShapes(Object.assign({ ties: true }, extra));
    assert.deepStrictEqual(box(on), box(off), JSON.stringify(Object.keys(extra)) + ": the sewn box moved");
    assert.ok(longest(on) <= longest(off) + 1e-9, "a lock made a longer sewn move than the untied design has");
    assert.strictEqual(on.widthMM, off.widthMM);
    assert.strictEqual(on.heightMM, off.heightMM);
  }
});

test("ties (shapes): a lock belongs to the run it protects", () => {
  // `design.runs` says what each stitch IS. Python folds a tie into the run it
  // ties; here its records sit inside that run's span, so every span still
  // ends on a record that exists and every stitch is still in exactly one.
  for (const ties of [false, true]) {
    const d = _tieShapes({ ties });
    const owner = new Array(d.stitches.length).fill(0);
    for (const r of d.runs) {
      assert.ok(r.i0 >= 0 && r.i1 < d.stitches.length && r.i0 <= r.i1, `ties ${ties}: span ${r.i0}..${r.i1} of ${d.stitches.length}`);
      for (let i = r.i0; i <= r.i1; i++) owner[i]++;
    }
    d.stitches.forEach((s, i) => {
      if (s.type === "stitch") assert.strictEqual(owner[i], 1, `ties ${ties}: stitch ${i} is in ${owner[i]} spans`);
    });
  }
  const kinds = (d) => d.runs.map((r) => r.kind + ":" + r.shape).join(",");
  assert.strictEqual(kinds(_tieShapes({ ties: true })), kinds(_tieShapes()), "the runs themselves are the same runs");
});

// applyTies, asked directly: the rules below only bite on streams no ordinary
// fixture produces (the same reason tieRun is exported).
const _rec = (type, x, y) => ({ x, y, type });
const _show = (s) => s.map((r) => `${r.type[0]}${r.x},${r.y}`).join(" ");

test("applyTies: a float does not cut the thread, a trim and a colour change do", () => {
  const stream = [
    _rec("jump", 0, 0), _rec("stitch", 0, 0), _rec("stitch", 30, 0),
    _rec("jump", 100, 0), _rec("stitch", 100, 0), _rec("stitch", 130, 0),   // floated to: same thread
    _rec("trim", 130, 0),
    _rec("jump", 200, 0), _rec("stitch", 200, 0), _rec("stitch", 230, 0),
    _rec("color", 230, 0),                                                  // a stop with no trim before it
    _rec("jump", 300, 0), _rec("stitch", 300, 0), _rec("stitch", 330, 0),
    _rec("end", 0, 0),
  ];
  const r = DG.applyTies(stream, []);
  assert.strictEqual(r.nTies, 6, "three threads, locked at both ends");
  assert.strictEqual(_show(r.stitches),
    "j0,0 s0,0 s8,0 s0,0 s8,0 s0,0 s30,0 j100,0 s100,0 s130,0 s122,0 s130,0 s122,0 s130,0 t130,0 " +
    "j200,0 s200,0 s208,0 s200,0 s208,0 s200,0 s230,0 s222,0 s230,0 s222,0 s230,0 c230,0 " +
    "j300,0 s300,0 s308,0 s300,0 s308,0 s300,0 s330,0 s322,0 s330,0 s322,0 s330,0 e0,0");
});

test("applyTies: a doubled hole is stepped over, a short stitch is the whole leg, and one penetration is not a thread", () => {
  const stream = [
    _rec("jump", 50, 0), _rec("stitch", 50, 0), _rec("stitch", 50, 0), _rec("stitch", 53, 4),   // a doubled hole, then 0.5 mm
    _rec("stitch", 90, 4), _rec("stitch", 90, 4),          // ... and a doubled hole at the end
    _rec("trim", 90, 4),
    _rec("jump", 200, 0), _rec("stitch", 200, 0),          // a thread of one penetration
    _rec("trim", 200, 0),
    _rec("jump", 300, 0), _rec("stitch", 300, 0), _rec("stitch", 300, 0),   // two penetrations, one hole
    _rec("end", 0, 0),
  ];
  const r = DG.applyTies(stream, []);
  assert.strictEqual(r.nTies, 2, "a thread that penetrates in one place only sews nothing, so nothing holds a lock");
  assert.strictEqual(_show(r.stitches),
    "j50,0 s50,0 s50,0 s53,4 s50,0 s53,4 s50,0 s53,4 s90,4 s82,4 s90,4 s82,4 s90,4 s90,4 t90,4 j200,0 s200,0 t200,0 j300,0 s300,0 s300,0 e0,0",
    "the 0.5 mm stitch is shorter than a leg, so the lock stops on its far end");
});

test("applyTies: a thread that ends on a float and one stitch is locked AT that stitch, not where it last sewed two in a row", () => {
  // Found by audit. The first rule looked for "two stitch records in a row".
  // A thread can end in a float and a single penetration (a short row after a
  // float is one record: the float lands on its start), or begin with one and
  // float away. The lock then sat at the last real sewing, up-thread, and the
  // tail was loose: 6.1% of tie-offs in shape designs, by as much as 371 mm.
  // A lock belongs where the thread ends. It is laid toward the place the
  // frame was last (or goes next), which is along the row the stitch closes.
  const stream = [
    _rec("jump", 0, 0), _rec("stitch", 0, 0), _rec("stitch", 30, 0),
    _rec("jump", 100, 50), _rec("stitch", 140, 50),                    // a float, then one penetration, then the cut
    _rec("trim", 140, 50),
    _rec("jump", 300, 0), _rec("stitch", 300, 0),                      // one penetration at a thread's START,
    _rec("jump", 300, 40), _rec("stitch", 340, 40), _rec("stitch", 380, 40),   // a float, and then the sewing
    _rec("end", 0, 0),
  ];
  const r = DG.applyTies(stream, []);
  assert.strictEqual(r.nTies, 4);
  assert.strictEqual(_show(r.stitches),
    "j0,0 s0,0 s8,0 s0,0 s8,0 s0,0 s30,0 j100,50 s140,50 s132,50 s140,50 s132,50 s140,50 t140,50 " +
    "j300,0 s300,0 s300,8 s300,0 s300,8 s300,0 j300,40 s340,40 s380,40 s372,40 s380,40 s372,40 s380,40 e0,0");
});

test("applyTies: one stitch after a cut, then a float -- the lock lies back along the row that stitch closed", () => {
  // Center-out's lower sweep opens so on a shape with a hole: the cut carries
  // the frame to a row's start, the row is shorter than a stitch and so is ONE
  // record, at the hole's rim, and the next move is a float across the hole.
  // Laid toward that float the lock's inner point was 0.8 mm into the hole.
  // The row began where the frame was just before the stitch: lay it there.
  const stream = [
    _rec("jump", 0, 0), _rec("stitch", 0, 0), _rec("stitch", 30, 0),
    _rec("trim", 100, 50),                                   // the cut: the frame is on the next row's start
    _rec("stitch", 130, 50),                                 // that row, one record, ending on a hole's rim
    _rec("jump", 200, 50), _rec("stitch", 230, 50), _rec("stitch", 260, 50),   // a float over the hole, then the next span
    _rec("end", 0, 0),
  ];
  assert.strictEqual(_show(DG.applyTies(stream, []).stitches),
    "j0,0 s0,0 s8,0 s0,0 s8,0 s0,0 s30,0 s22,0 s30,0 s22,0 s30,0 t100,50 " +
    "s130,50 s122,50 s130,50 s122,50 s130,50 j200,50 s230,50 s260,50 s252,50 s260,50 s252,50 s260,50 e0,0");
  // Only then. A first stitch that is followed by a stitch is locked on that
  // stitch, wherever the cut landed (a long row after center-out's cut)...
  const sewsOn = [_rec("trim", 100, 50), _rec("stitch", 130, 50), _rec("stitch", 160, 50)];
  assert.strictEqual(_show(DG.applyTies(sewsOn, []).stitches),
    "t100,50 s130,50 s138,50 s130,50 s138,50 s130,50 s160,50 s152,50 s160,50 s152,50 s160,50");
  // ... and a colour change is not where a row began: it marks the place the
  // LAST thread ended. There the float is all there is to lay the lock along.
  const newColour = [_rec("color", 100, 50), _rec("stitch", 130, 50), _rec("jump", 200, 50), _rec("stitch", 230, 50)];
  assert.strictEqual(_show(DG.applyTies(newColour, []).stitches),
    "c100,50 s130,50 s138,50 s130,50 s138,50 s130,50 j200,50 s230,50 s222,50 s230,50 s222,50 s230,50");
  // Nor is a cut that was left ON the last thread's final stitch: it carried
  // the frame nowhere. (No builder writes this; the audit wrote it by hand.)
  const stale = [_rec("stitch", 0, 0), _rec("stitch", 50, 0), _rec("trim", 50, 0),
    _rec("stitch", 200, 100), _rec("jump", 260, 100), _rec("stitch", 300, 100), _rec("stitch", 340, 100)];
  assert.strictEqual(_show(DG.applyTies(stale, []).stitches),
    "s0,0 s8,0 s0,0 s8,0 s0,0 s50,0 s42,0 s50,0 s42,0 s50,0 t50,0 " +
    "s200,100 s208,100 s200,100 s208,100 s200,100 j260,100 s300,100 s340,100 s332,100 s340,100 s332,100 s340,100");
});

test("ties (shapes): with the column flag off, a lock adds no sewn thread to a hole", () => {
  // The same thing in whole designs, where it was found: a frame, a thin ring
  // and a grid of nine holes, no fabric (so that what the fill covers is what
  // was drawn), rows at four angles.
  const frame = { outer: boxPx(0, 0, 400, 400), holes: [boxPx(30, 30, 370, 370)] };
  const thin = { outer: roundPx(175, 175, 175, 96), holes: [roundPx(175, 175, 161, 96)] };
  const holes = [];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) holes.push(boxPx(35 + 105 * i, 35 + 105 * j, 105 + 105 * i, 105 + 105 * j));
  const nine = { outer: boxPx(0, 0, 350, 350), holes };
  let locks = 0;
  for (const [name, shape, widthPx] of [["frame", frame, 400], ["thin ring", thin, 350], ["nine holes", nine, 350]]) {
    for (const angleOverride of [null, 0, 30, 90]) {
      const sh = Object.assign({}, shape);
      if (angleOverride != null) sh.angleOverride = angleOverride;
      const off = drawn(sh, widthPx, { fillColumns: false }), on = drawn(sh, widthPx, { fillColumns: false, ties: true });
      locks += on._debug.nTies;
      assert.strictEqual(openGroundMm(on, shape, 0.15).sewn, openGroundMm(off, shape, 0.15).sewn, name + ", angle " + angleOverride);
    }
  }
  assert.ok(locks >= 48, "every design here is cut by center-out, so it has four locks: " + locks);
});

test("ties (shapes): every lock sits on its thread's first or last penetration", () => {
  // The same thing asked of whole designs: an inverted U whose arms are
  // narrower than a stitch (so the last rows are one record each, after a
  // float across the mouth), an L whose column walk opens a thread with a
  // doubled hole and a 35 mm float, and the three-shape fixture above.
  const arch = { outer: ring([[0, 0], [400, 0], [400, 300], [370, 300], [370, 60], [30, 60], [30, 300], [0, 300]]), holes: [] };
  const ell = { outer: ring([[0, 0], [122.5, 0], [122.5, 227.5], [350, 227.5], [350, 350], [0, 350]]), holes: [], angleOverride: 90 };
  const designs = {
    "arch, flag off": (ties) => drawn(arch, 400, { fillColumns: false, ties }),
    "arch, flag on": (ties) => drawn(arch, 400, { ties }),
    "L, flag on": (ties) => drawn(ell, 350, { ties }),
    "three shapes": (ties) => _tieShapes({ ties }),
    "three shapes, columns": (ties) => _tieShapes({ ties, fillColumns: true }),
  };
  let loneEnds = 0;
  for (const [name, build] of Object.entries(designs)) {
    const off = build(false).stitches, on = build(true).stitches;
    // the locks, by diff: where the tied stream leaves the untied one, the
    // record before is the anchor and the next four are its lock
    const anchors = new Set();
    for (let i = 0, j = 0; j < on.length;) {
      if (i < off.length && off[i].type === on[j].type && _same(off[i], on[j])) { i++; j++; continue; }
      anchors.add(j - 1);
      j += 4;
    }
    let from = 0;
    on.forEach((s, k) => {
      if (s.type !== "trim" && s.type !== "color" && s.type !== "end") return;
      const pens = [];
      for (let m = from; m < k; m++) if (on[m].type === "stitch") pens.push(m);
      from = k + 1;
      const places = new Set(pens.map((m) => on[m].x + "," + on[m].y));
      if (places.size < 2) return;   // sews nothing
      const first = on[pens[0]], last = on[pens[pens.length - 1]];
      const locked = pens.filter((m) => anchors.has(m));
      assert.strictEqual(locked.length, 2, `${name}: thread ending at record ${k} has ${locked.length} locks`);
      assert.ok(_same(on[locked[0]], first), `${name}: the tie-in at record ${locked[0]} is not on the thread's first penetration`);
      assert.ok(_same(on[locked[1]], last), `${name}: the tie-off at record ${locked[1]} is not on the thread's last penetration`);
      // a lone end: the thread floats on straight after its tie-in, or floated in to its tie-off
      if (on[locked[0] + 5].type === "jump" || on[locked[1] - 1].type === "jump") loneEnds++;
    });
  }
  assert.ok(loneEnds >= 2, "the fixtures must have a thread that starts or ends on a lone penetration: " + loneEnds);
});

test("applyTies: the spans move with the records, and a lock stays in its run's span", () => {
  const stream = [
    _rec("jump", 0, 0), _rec("stitch", 0, 0), _rec("stitch", 30, 0),      // run A: 0..2
    _rec("jump", 0, 10), _rec("stitch", 0, 10), _rec("stitch", 30, 10),   // run B: 3..5
    _rec("end", 0, 0),
  ];
  const spans = [{ i0: 0, i1: 2, kind: "underlay" }, { i0: 3, i1: 5, kind: "fill" }];
  const r = DG.applyTies(stream, spans);
  // A gains its tie-in (4 after record 1); B moves by 4 and gains its tie-off
  assert.deepStrictEqual(spans.map((s) => [s.i0, s.i1]), [[0, 6], [7, 13]]);
  assert.strictEqual(r.stitches.length, 15);
  assert.strictEqual(stream.length, 7, "the stream handed in is not changed");
});

test("ties (lettering): the locks are inside the runs they protect too", () => {
  // The lettering port pushed its ties between two spans, where the renderer
  // draws a strand as if spans had never existed.
  const font = _tieFont();
  const outside = (ties) => {
    const d = DG.buildLetteringDesign(font, "AB", { ..._tieBase, ties });
    const inSpan = new Array(d.stitches.length).fill(false);
    for (const r of d.runs) {
      assert.ok(r.i0 >= 0 && r.i1 < d.stitches.length && r.i0 <= r.i1, `ties ${ties}: span ${r.i0}..${r.i1} of ${d.stitches.length}`);
      for (let i = r.i0; i <= r.i1; i++) inSpan[i] = true;
    }
    return d.stitches.filter((s, i) => s.type === "stitch" && !inSpan[i]).length;
  };
  assert.strictEqual(outside(true), outside(false), "stitches that belong to no run");
});

// ---- shapeOutlines (2026-09-29 spec: click a shape on the canvas) ---------
// Additive field: where each input shape landed, in FIELD mm (+y up, the
// stitches' own space, T() without the integer rounding). The Studio draws
// these over a hand-drawn/preset element so it can be clicked; nothing about
// the stitches may move for it.
test("buildQualityDesign: shapeOutlines land on the stitches, in field mm, ids kept", () => {
  const rect = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect, holes: [], id: "s7", tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, underlay: false,
      targetWidthMm: 40, offsetXMm: 5, offsetYMm: -3 }
  );
  assert.strictEqual(d.shapeOutlines.length, 1);
  const o = d.shapeOutlines[0];
  assert.strictEqual(o.id, "s7");
  assert.strictEqual(o.dropped, false);
  assert.deepStrictEqual(o.holes, []);
  const xs = o.points.map((p) => p[0]), ys = o.points.map((p) => p[1]);
  const near = (a, b) => Math.abs(a - b) <= 1e-6;
  assert.ok(near(Math.max(...xs) - Math.min(...xs), 40), "outline width = targetWidthMm");
  assert.ok(near(Math.max(...ys) - Math.min(...ys), 20), "outline height keeps the 2:1 aspect");
  assert.ok(near((Math.max(...xs) + Math.min(...xs)) / 2, 5), "centred on offsetXMm");
  assert.ok(near((Math.max(...ys) + Math.min(...ys)) / 2, -3), "centred on offsetYMm");
  // The stitches (DST units, 10 per mm) sit inside the outline, give or take
  // the engine's default 0.2 mm pull compensation.
  const sew = d.stitches.filter((s) => s.type === "stitch");
  assert.ok(sew.length > 50);
  for (const s of sew) {
    assert.ok(s.x / 10 >= Math.min(...xs) - 0.5 && s.x / 10 <= Math.max(...xs) + 0.5, "x inside outline");
    assert.ok(s.y / 10 >= Math.min(...ys) - 0.5 && s.y / 10 <= Math.max(...ys) + 0.5, "y inside outline");
  }
});

test("buildQualityDesign: shapeOutlines keep INPUT order across the light-to-dark sort, and flag dropped shapes", () => {
  const sq = (x0, s) => [{ x: x0, y: 0 }, { x: x0 + s, y: 0 }, { x: x0 + s, y: s }, { x: x0, y: s }];
  const d = DG.buildQualityDesign(
    [
      // light colour first: darkOnTop (default true) sews it FIRST anyway, but
      // a dark region listed first would be re-ordered — the outlines must not be.
      { rgb: [10, 10, 10], shapes: [{ outer: sq(0, 40), holes: [], id: "dark" }] },
      { rgb: [240, 240, 240], shapes: [
        { outer: sq(60, 40), holes: [], id: "light" },
        { outer: [{ x: 0, y: 0 }, { x: 1, y: 0 }], holes: [], id: "degenerate" },
      ] },
    ],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, underlay: false }
  );
  assert.deepStrictEqual(d.shapeOutlines.map((o) => o.id), ["dark", "light", "degenerate"]);
  assert.deepStrictEqual(d.shapeOutlines.map((o) => o.dropped), [false, false, true]);
  // The sew order is still light first — proving the outlines did not follow the sort.
  assert.strictEqual(d.colors[0].r, 240);
});

test("buildQualityDesign: a shape with no id gets '' and the legacy polygons input still gets outlines", () => {
  const ring = [{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], polygons: [ring] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 4, underlay: false });
  assert.strictEqual(d.shapeOutlines.length, 1);
  assert.strictEqual(d.shapeOutlines[0].id, "");
  assert.strictEqual(d.shapeOutlines[0].points.length, 4);
});

test("buildQualityDesign: an empty design carries an empty shapeOutlines", () => {
  const d = DG.buildQualityDesign([], { garment: { widthIn: 4, heightIn: 4 } });
  assert.deepStrictEqual(d.shapeOutlines, []);
});

// Spec §3: shapeOutlines is additive — the stitches must be byte-identical to
// the same call before it existed.
test("buildQualityDesign: stitches are byte-identical to main's on the shapeOutlines fixture", () => {
  const crypto = require("node:crypto");
  const rect = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect, holes: [], id: "s7", tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, underlay: false,
      targetWidthMm: 40, offsetXMm: 5, offsetYMm: -3 }
  );
  const hash = crypto.createHash("sha256").update(JSON.stringify(d.stitches)).digest("hex");
  // hash taken from main at 5371b120 on 2026-09-29; a change here means a
  // stitch moved — spec §2 forbids that for this feature.
  assert.strictEqual(hash, "54ae2fb3e4d18ceccbe591e9fe322d3147a92a69a0be6b7c78d00b06c162d532");
});

test("buildQualityDesign: design.fit reproduces shapeOutlines from the input geometry", () => {
  const rect = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }, { x: 0, y: 50 }];
  const d = DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect, holes: [], id: "s7", tierOverride: "fill" }] }],
    { garment: { widthIn: 4, heightIn: 4 }, pxPerMm: 6, underlay: false, targetWidthMm: 40, offsetXMm: 5, offsetYMm: -3 }
  );
  const f = d.fit;
  assert.ok(f && typeof f.cxPx === "number" && typeof f.mmPerPx === "number");
  assert.strictEqual(f.pxPerMm, 6);
  // the offsets AS APPLIED: rounded to a DST unit (0.1 mm) like T() does
  assert.strictEqual(f.offsetXMm, 5);
  assert.strictEqual(f.offsetYMm, -3);
  const fwd = (q) => [(q.x - f.cxPx) * f.mmPerPx + f.offsetXMm, (f.cyPx - q.y) * f.mmPerPx + f.offsetYMm];
  const out = d.shapeOutlines[0].points;
  rect.forEach((q, i) => {
    assert.ok(Math.abs(fwd(q)[0] - out[i][0]) < 1e-9 && Math.abs(fwd(q)[1] - out[i][1]) < 1e-9, "point " + i);
  });
  // 100 px wide at pxPerMm 6 fitted to 40 mm -> mmPerPx = 0.4
  assert.ok(Math.abs(f.mmPerPx - 0.4) < 1e-12);
});

test("buildQualityDesign: an empty design carries fit null", () => {
  const d = DG.buildQualityDesign([], { garment: { widthIn: 4, heightIn: 4 } });
  assert.strictEqual(d.fit, null);
});

test("buildQualityDesign: a 3-point hole cuts, like a 4-point one (manual A's counter)", () => {
  const sq = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }];
  const tri = [{ x: 100, y: 200 }, { x: 200, y: 200 }, { x: 150, y: 100 }];
  const box = [{ x: 100, y: 100 }, { x: 200, y: 100 }, { x: 200, y: 200 }, { x: 100, y: 200 }];
  const run = (holes, underlay) => DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: sq, holes, id: "s", tierOverride: "fill" }] }],
    { garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 6, underlay, targetWidthMm: 50 });
  const solid = run([], false).stitches.length;
  const withTri = run([tri], false).stitches.length;
  const withBox = run([box], false).stitches.length;
  assert.ok(withBox < solid, "a 4-point hole already cuts");
  assert.ok(withTri < solid, "a 3-point hole must cut too: " + withTri + " vs " + solid);
  // the triangle is half the box's area, so it removes less than the box does
  assert.ok(withTri > withBox, "and removes less than the bigger hole");
  // the underlay reader has the same floor: with underlay on, the hole still cuts
  assert.ok(run([tri], true).stitches.length < run([], true).stitches.length);
});

test("underlayRuns: a 3-point hole gets its own edge run and joins the lattice's rings (the underlay floor alone)", () => {
  // The design-level assert above also passes when ONLY the region loop's floor
  // is fixed (the fill cuts the hole either way), so it cannot tell whether
  // underlayRuns' own floor moved. This reads underlayRuns directly with an
  // identity ctx: each ring it keeps comes back as one run / one ring.
  const sq = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 300 }, { x: 0, y: 300 }];
  const tri = [{ x: 100, y: 200 }, { x: 200, y: 200 }, { x: 150, y: 100 }];
  const ctx = {
    pxPerFinalMm: 6, fillAngle: 0, underlayStitchPx: 12, underlayRowPx: 15, maxStitch: 40,
    insetRing: (ring) => ring,
    runningOutline: (ring) => ring,
    tatamiFill: (rings) => rings,
    pcaAngleDeg: () => 0,
  };
  const edge = DG.underlayRuns({ outer: sq, holes: [tri] }, "edge_run", ctx);
  assert.strictEqual(edge.length, 2, "outer + the triangle's own edge run");
  assert.deepStrictEqual(edge[1], tri);
  const zig = DG.underlayRuns({ outer: sq, holes: [tri] }, "zigzag", ctx);
  assert.strictEqual(zig[0].length, 2, "the zigzag fill sees the triangle as a ring to stay out of");
  // and the floor still drops a degenerate 2-point "hole"
  assert.strictEqual(DG.underlayRuns({ outer: sq, holes: [tri.slice(0, 2)] }, "edge_run", ctx).length, 1);
});

// --- dedupeHoles: no second stitch in the hole the needle is in (2026-10-03) --
//
// The builder rounds every point to the stitch file's unit, 0.1 mm, so two
// penetrations nearer than that can become two `stitch` records on one point:
// a scanline through a corner, a row at a tip, the move across the mouth of a
// notch. The writers keep such a record, so the needle goes down twice in one
// hole (docs/sub-unit-stitches-2026-10-03.md: 16,575 of them on 8,255 designs
// with every flag absent). `dedupeHoles: true` lays the first and not the
// second, in every run of the shape builder. Built OFF.
//
// "The second" is a stitch whose record comes straight after a stitch on the
// same point, and nothing wider. After a jump or a cut the stitch is laid,
// whatever point it is on: a writer lays a cut as three jump records, so a
// reader takes three jumps in a row for one, and taking the stitch out from
// between two jumps could make a cut that was not there.
const _holeStar = [[180, 0], [227, 115], [351, 124], [256, 205], [286, 326], [180, 260], [74, 326], [104, 205], [9, 124], [133, 115]].map(([x, y]) => ({ x, y }));
const _holeTaper = [{ x: 0, y: 0 }, { x: 300, y: 10 }, { x: 0, y: 20 }];
const _holeRun = (shape, widthMm, extra) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [Object.assign({ holes: [] }, shape)] }],
  Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: widthMm, darkOnTop: false }, extra));
// Each a design that, with the flag off, puts two stitches on one point in the
// kind of run named: [name, the run kind the pair is in, how it is built].
const _holeCases = [
  ["plain walk, fill and underlay", "fill", (extra) => _holeRun({ outer: _holeStar, tierOverride: "fill" }, 34.2, extra)],
  ["plain walk under a preset", "fill", (extra) => _holeRun({ outer: _holeStar, tierOverride: "fill" }, 34.2, Object.assign({ fabric: FABRICS.getFabric("pique_knit") }, extra))],
  ["column walk under a preset", "fill", (extra) => _holeRun({ outer: _holeStar, holes: [sq(160, 160, 40)], tierOverride: "fill" }, 34.2, Object.assign({ fabric: FABRICS.getFabric("terry_towel"), fillColumns: true }, extra))],
  ["satin", "satin", (extra) => _holeRun({ outer: _holeTaper, tierOverride: "satin" }, 30, extra)],
];
// The stitches on a point the stitch before them is on, by the kind of run.
const _secondByKind = (d) => {
  const out = {};
  for (const r of d.runs) {
    for (let i = r.i0 + 1; i <= r.i1; i++) {
      if (d.stitches[i].type === "stitch" && d.stitches[i - 1].type === "stitch" && _same(d.stitches[i], d.stitches[i - 1])) out[r.kind] = (out[r.kind] || 0) + 1;
    }
  }
  return out;
};
// What the flag is to leave of a stream, written out here and not asked of
// the builder: every record but a stitch on the point of the stitch that is
// the record before it. Three on one point leave one.
const _withoutSecond = (stitches) => {
  const out = [];
  let hole = null;
  for (const s of stitches) {
    if (s.type !== "stitch") hole = null;
    else if (hole && _same(hole, s)) continue;
    else hole = s;
    out.push(s);
  }
  return out;
};
const _records = (stitches) => stitches.map((s) => `${s.x},${s.y},${s.type}`).join(";");
// Two squares; the second's first row begins on the corner the first's last
// row ends on, (35, -34) in the file. One colour: the frame does not move
// between them and the thread is not cut. Two colours: it is cut there.
const _holeSquares = (twoColours, extra) => {
  const a = { outer: sq(0, 0, 100), holes: [], tierOverride: "fill", angleOverride: 0 };
  const b = { outer: [{ x: 100, y: 99 }, { x: 130, y: 99 }, { x: 130, y: 130 }, { x: 100, y: 130 }], holes: [], tierOverride: "fill", angleOverride: 0 };
  const regions = twoColours ? [{ rgb: [0, 0, 0], shapes: [a] }, { rgb: [200, 0, 0], shapes: [b] }] : [{ rgb: [0, 0, 0], shapes: [a, b] }];
  return DG.buildQualityDesign(regions, Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 13, darkOnTop: false, underlay: false }, extra));
};

test("dedupeHoles: OFF by default, and the flag off is byte-identical to omitting it", () => {
  for (const [name, kind, build] of _holeCases) {
    const omitted = build(), off = build({ dedupeHoles: false });
    assert.strictEqual(_fingerprint(off), _fingerprint(omitted), name);
    assert.deepStrictEqual(off.runs, omitted.runs, name);
    assert.ok(_secondByKind(omitted)[kind] > 0, `fixture, ${name}: left off, a ${kind} run has two stitches on one point`);
  }
});

test("dedupeHoles: ON, no run lays two stitches in a row on one point", () => {
  for (const [name, , build] of _holeCases) {
    const on = build({ dedupeHoles: true });
    assert.deepStrictEqual(_secondByKind(on), {}, name);
    assert.strictEqual(_zeroLength(on), 0, name);
  }
});

test("dedupeHoles: the stream is the one without it less those stitches, and nothing else moves", () => {
  for (const [name, , build] of _holeCases) {
    const off = build(), on = build({ dedupeHoles: true });
    assert.strictEqual(_records(on.stitches), _records(_withoutSecond(off.stitches)), name);
    assert.ok(on.stitches.length < off.stitches.length, name);
    for (const k of ["trim", "jump", "color", "end"]) assert.strictEqual(_count(on, k), _count(off, k), `${name}: the flag must take out no ${k}`);
    assert.strictEqual(on.stitchCount, _count(on, "stitch"), `${name}: the design's stitch count is the stream's`);
  }
});

test("dedupeHoles: every run still has its span, and the spans still hold every stitch", () => {
  for (const [name, , build] of _holeCases) {
    const off = build(), on = build({ dedupeHoles: true });
    assert.deepStrictEqual(on.runs.map((r) => r.kind), off.runs.map((r) => r.kind), name);
    let covered = 0, next = 0;
    for (const r of on.runs) {
      assert.ok(r.i0 >= next && r.i1 >= r.i0, `${name}: spans in order, none inside another`);
      assert.strictEqual(on.stitches[r.i0].type, "jump", `${name}: a span opens on its run's jump`);
      assert.strictEqual(on.stitches[r.i0 + 1].type, "stitch", `${name}: and the run's first stitch follows it`);
      for (let i = r.i0; i <= r.i1; i++) if (on.stitches[i].type === "stitch") covered++;
      next = r.i1 + 1;
    }
    assert.strictEqual(covered, _count(on, "stitch"), name);
  }
});

test("dedupeHoles: three stitches in a row on one point leave one", () => {
  // A triangle and a second ring that share the triangle's top corner. The
  // first scanline finds the corner twice, a span of no length, and then the
  // span that starts on it: the corner is sewn three times.
  const shape = {
    outer: [{ x: 100, y: 0 }, { x: 150, y: 100 }, { x: 50, y: 100 }],
    holes: [[{ x: 100, y: 0 }, { x: 180, y: 0 }, { x: 180, y: 50 }, { x: 130, y: 50 }]],
    tierOverride: "fill", angleOverride: 0,
  };
  const off = _holeRun(shape, 10, { underlay: false }), on = _holeRun(shape, 10, { underlay: false, dedupeHoles: true });
  assert.strictEqual(_show(off.stitches.slice(0, 5)), "j0,50 s0,50 s0,50 s0,50 s40,50", "fixture");
  assert.strictEqual(_show(on.stitches.slice(0, 3)), "j0,50 s0,50 s40,50");
  assert.strictEqual(_records(on.stitches), _records(_withoutSecond(off.stitches)));
});

test("dedupeHoles: a run's first stitch is laid even where the last run ended", () => {
  // The corner is sewn twice, with the second run's own jump between the two.
  // That stitch stays: taken out, a run that laid nothing would leave its jump
  // beside the next run's, and jumps in a row are how a file says "cut".
  const off = _holeSquares(false), on = _holeSquares(false, { dedupeHoles: true });
  const seam = (d) => _show(d.stitches.slice(d.runs[1].i0 - 1, d.runs[1].i0 + 3));
  assert.strictEqual(seam(off), "s35,-34 j35,-34 s35,-34 s65,-34", "fixture: the corner twice, a jump between");
  assert.strictEqual(seam(on), seam(off));
  assert.strictEqual(_fingerprint(on), _fingerprint(off), "nothing in this design is a second stitch");
});

test("dedupeHoles: the stitch after a float is laid, even back on the point the thread left", () => {
  // A three-armed star forced to satin: the column floats 9 mm across to the
  // next arm and comes back to sew where it was. A float that long is two
  // jump records and the way back a third, which a machine takes for a cut;
  // the stitch after it would then be what holds the thread.
  const star = [];
  for (let i = 0; i < 6; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 3, r = i % 2 ? 30 : 100;
    star.push({ x: Math.round(100 + r * Math.cos(a)), y: Math.round(100 + r * Math.sin(a)) });
  }
  const build = (extra) => _holeRun({ outer: star, tierOverride: "satin" }, 17.4, Object.assign({ underlay: false }, extra));
  const off = build(), on = build({ dedupeHoles: true });
  const back = (d) => d.stitches.findIndex((s, i, st) => i >= 2 && s.type === "stitch" && st[i - 1].type === "jump" && !_same(s, st[i - 1]) && st[i - 2].type === "stitch" && _same(s, st[i - 2]));
  assert.ok(back(off) >= 2, "fixture: a stitch, a float away, and a stitch back on the same point");
  assert.strictEqual(_show(off.stitches.slice(back(off) - 2, back(off) + 2)), "s-46,-30 j46,-30 s-46,-30 s-42,-26", "fixture");
  assert.ok(back(on) >= 2, "with the flag the stitch back is still there");
  assert.strictEqual(_show(on.stitches.slice(back(on) - 2, back(on) + 2)), "s-46,-30 j46,-30 s-46,-30 s-42,-26");
  assert.strictEqual(_records(on.stitches), _records(_withoutSecond(off.stitches)));
});

test("dedupeHoles: the stitch after a float is laid, even on the point the float went to", () => {
  // A prong and a spike on one bar. The row just under the spike's tip is
  // 0.004 mm long and is reached by a float from the prong: the float's point
  // and the stitch after it are one point of the file. That stitch is the
  // only penetration the row gets, and the record before it is a jump.
  const outer = [[0, 0], [30, 0], [30, 60], [100, 60], [110, 2.9], [120, 60], [120, 80], [0, 80]].map(([x, y]) => ({ x, y }));
  const build = (extra) => _holeRun({ outer, tierOverride: "fill", angleOverride: 0 }, 12, Object.assign({ underlay: false }, extra));
  const off = build(), on = build({ dedupeHoles: true });
  assert.strictEqual(_show(off.stitches.slice(6, 11)), "s-30,37 j50,37 s50,37 s50,36 s50,36", "fixture: a float, a stitch on its point, and the next row sewn twice on one point");
  assert.strictEqual(_show(on.stitches.slice(6, 10)), "s-30,37 j50,37 s50,37 s50,36");
  assert.strictEqual(_records(on.stitches), _records(_withoutSecond(off.stitches)));
});

test("dedupeHoles: the stitch after a float is laid, even when the float went nowhere", () => {
  // A three-point needle forced to satin, with no pull compensation. At the
  // tip the column floats to a point that rounds onto the one it left and sews
  // there: a stitch, a jump and a stitch, all three on one point. The stitch
  // after the float is the first of its thread and stays; the two after it are
  // seconds. Found by the independent re-measure, 2026-10-04: no other test
  // here holds a float that does not move.
  const outer = [[0, 108.1], [144.9, 0], [6.9, 116.8]].map(([x, y]) => ({ x, y }));
  const build = (extra) => _holeRun({ outer, tierOverride: "satin" }, 5.8, Object.assign({ pxPerMm: 25, pullCompMm: 0, underlay: false, satinSpacingMm: 0.3 }, extra));
  const off = build(), on = build({ dedupeHoles: true });
  assert.strictEqual(_show(off.stitches.slice(-6)), "s26,21 j26,21 s26,21 s26,21 s26,21 e0,0", "fixture: a stitch, a float that goes nowhere, and three stitches on its point");
  assert.strictEqual(_show(on.stitches.slice(-4)), "s26,21 j26,21 s26,21 e0,0");
  assert.strictEqual(_records(on.stitches), _records(_withoutSecond(off.stitches)));
});

test("dedupeHoles: a cut inside a run starts a new thread too", () => {
  // The column walk cuts to reach an island, and lays a stitch on the very
  // point it cut to: the record before that stitch is the cut, not a stitch.
  const box = (x0, y0, x1, y1) => [{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }];
  const island = (extra) => _holeRun({ outer: box(0, 0, 80, 80), holes: [box(20, 20, 60, 60), box(30, 30, 50, 50)], tierOverride: "fill", angleOverride: 0 },
    8, Object.assign({ underlay: false, fillColumns: true }, extra));
  const cut = (d) => d.stitches.findIndex((s) => s.type === "trim");
  const off = island(), on = island({ dedupeHoles: true });
  assert.strictEqual(_show(off.stitches.slice(cut(off) - 1, cut(off) + 3)), "s40,-39 t10,-9 s10,-9 s-10,-9", "fixture: a cut, and a stitch on the cut point");
  assert.strictEqual(_show(on.stitches.slice(cut(on) - 1, cut(on) + 3)), "s40,-39 t10,-9 s10,-9 s-10,-9");
  // And where the cut lands on the point the thread has just left: a moat
  // under the unit wide, rows 0.02 mm apart. Stitch, cut, stitch, one point.
  const moat = (extra) => _holeRun({ outer: box(0, 0, 109.68, 109.68), holes: [box(48.37, 44.72, 94.05, 90.91), box(48.97, 45.32, 93.6, 90.51)], tierOverride: "fill", angleOverride: 90 },
    10.968, Object.assign({ underlay: false, fillColumns: true, fillRowMm: 0.02 }, extra));
  const spot = (d) => d.stitches.findIndex((s, i, st) => s.type === "trim" && i > 0 && i + 1 < st.length && st[i - 1].type === "stitch" && st[i + 1].type === "stitch" && _same(st[i - 1], st[i + 1]));
  const offMoat = moat(), onMoat = moat({ dedupeHoles: true });
  assert.ok(spot(offMoat) > 0, "fixture: a cut with a stitch on one point either side of it");
  assert.strictEqual(_show(offMoat.stitches.slice(spot(offMoat) - 1, spot(offMoat) + 2)), "s39,10 t39,10 s39,10", "fixture");
  assert.ok(spot(onMoat) > 0, "with the flag the stitch after that cut is still there");
  assert.strictEqual(_records(onMoat.stitches), _records(_withoutSecond(offMoat.stitches)));
});

test("dedupeHoles: a cut starts a new thread, and its first stitch is laid even on the spot", () => {
  // The same two squares in two colours. The thread is cut on the corner, and
  // the stitch after the cut is what holds the new thread: it stays.
  const off = _holeSquares(true), on = _holeSquares(true, { dedupeHoles: true });
  const seam = (d) => _show(d.stitches.slice(d.runs[1].i0 - 3, d.runs[1].i0 + 2));
  assert.strictEqual(seam(off), "s35,-34 t35,-34 c35,-34 j35,-34 s35,-34", "fixture");
  assert.strictEqual(seam(on), seam(off));
  assert.strictEqual(_fingerprint(on), _fingerprint(off), "nothing in this design is a second stitch");
});

test("dedupeHoles: with ties, every lock is still laid and none of them doubles a hole", () => {
  const star = (extra) => _holeRun({ outer: _holeStar, tierOverride: "fill" }, 34.2, extra);
  const tied = star({ ties: true }), both = star({ ties: true, dedupeHoles: true });
  assert.ok(tied._debug.nTies >= 2 && _zeroLength(tied) > 0, "fixture: locks, and stitches on one point");
  assert.strictEqual(both._debug.nTies, tied._debug.nTies, "a lock for every thread end, as without the flag");
  assert.strictEqual(_lockLegs(both).length, both._debug.nTies);
  assert.strictEqual(_zeroLength(both), 0);
});

// --- cutFloats: the builder cuts where the DST writer would lay three jumps (2026-10-04) --
//
// A DST has no cut. dst.js writes a `trim` as three or more jump records, and
// any needle-up move over 12.1 mm an axis as several. So a float over 24.2 mm
// is three jump records too, and a machine set to cut at three cuts there
// with no `trim` in the stream: no lock from `ties`, and nothing in the trim
// count (docs/dst-float-cuts-2026-10-04.md: 109,561 of them on 8,270 Studio
// shapes with every flag absent). `cutFloats: true` puts the `trim` in the
// stream wherever the writer would lay three. It moves no stitch. Built OFF.
const _cfDst = require("../src/dst.js");
const { decodeDST: _cfDecode } = require("../src/dstimport.js");
const _cfPts = (a) => a.map(([x, y]) => ({ x, y }));
const _cfRun = (shape, widthMm, extra) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [Object.assign({ holes: [] }, shape)] }],
  Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: widthMm, darkOnTop: false }, extra));
// Two prongs on a bar, sewn in rows: the plain walk floats from one prong to
// the other across the gap on every row. `gap` in px, ten to the millimetre.
const _cfProngs = (gap, extra) => _cfRun(
  { outer: _cfPts([[0, 0], [150, 0], [150, 150], [150 + gap, 150], [150 + gap, 0], [300 + gap, 0], [300 + gap, 200], [0, 200]]), tierOverride: "fill", angleOverride: 0 },
  (300 + gap) / 10, Object.assign({ underlay: false }, extra));
// A bar 60 x 15 mm with its underlay: the edge run ends a bar's length from
// where the next pass begins.
const _cfBar = (extra) => _cfRun({ outer: _cfPts([[0, 0], [600, 0], [600, 150], [0, 150]]), tierOverride: "fill" }, 60, Object.assign({ underlay: true }, extra));
// A four-point star 20 mm across, which the builder sews as satin: a column
// floats to the far arm and sews back where it was.
const _cfStar = (extra) => {
  const star = [];
  for (let i = 0; i < 8; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 4, r = i % 2 ? 15 : 100;
    star.push({ x: Math.round((100 + r * Math.cos(a)) * 100) / 100, y: Math.round((100 + r * Math.sin(a)) * 100) / 100 });
  }
  return _cfRun({ outer: star }, 20, Object.assign({ underlay: false }, extra));
};
const _cfCases = [
  ["a fill across a gap", (x) => _cfProngs(300, x)],
  ["an underlay and its fill", _cfBar],
  ["a satin star", _cfStar],
  ["a fill across a gap, column walk", (x) => _cfProngs(300, Object.assign({ fillColumns: true }, x))],
  ["a hole, two colours, three shapes", _tieShapes],
];
// Every float with the thread on: the jump records between two stitches, and
// how many records the writer lays in a row for it. The move to the stitch
// after a jump is written as jump records up to its last.
const _cfFloats = (st) => {
  const out = [];
  for (let i = 1; i < st.length; i++) {
    if (st[i].type !== "jump" || st[i - 1].type !== "stitch") continue;
    let j = i, n = 0;
    for (; j < st.length && st[j].type === "jump"; j++) n += _cfDst.jumpRecords(st[j].x - st[j - 1].x, st[j].y - st[j - 1].y);
    if (!st[j] || st[j].type !== "stitch") continue;
    out.push({ i0: i, i1: j - 1, records: n + _cfDst.jumpRecords(st[j].x - st[j - 1].x, st[j].y - st[j - 1].y) - 1 });
  }
  return out;
};
const _cfLong = (d) => _cfFloats(d.stitches).filter((f) => f.records >= 3);
const _cfFileCuts = (d) => _cfDecode(_cfDst.encodeDST(d)).trimCount;

test("cutFloats: OFF by default, and the flag off is byte-identical to omitting it", () => {
  for (const [name, build] of _cfCases) {
    const omitted = build(), off = build({ cutFloats: false });
    assert.strictEqual(_fingerprint(off), _fingerprint(omitted), name);
    assert.deepStrictEqual(off.runs, omitted.runs, name);
  }
  assert.strictEqual(_cfLong(_cfProngs(300)).length, 100, "fixture: every row floats 30 mm across the gap, and the flag off leaves them");
});

test("cutFloats: ON, no float is left that the writer lays as three jump records", () => {
  for (const [name, build] of _cfCases.slice(0, 3)) assert.ok(_cfLong(build()).length > 0, `fixture: ${name} has one without the flag`);
  for (const [name, build] of _cfCases) assert.strictEqual(_cfLong(build({ cutFloats: true })).length, 0, name);
});

test("cutFloats: the stream is the one without it with the cuts put in, and nothing else moves", () => {
  // A cut is a jump turned into a trim where it stands, or a trim on the spot
  // before a jump. Every other record is the same one, in the same place.
  for (const [name, build] of _cfCases) {
    const off = build(), on = build({ cutFloats: true });
    const A = off.stitches, B = on.stitches;
    let i = 0, k = 0, inPlace = 0, before = 0;
    while (i < A.length || k < B.length) {
      const a = A[i], b = B[k];
      if (a && b && a.type === "jump" && b.type === "trim" && i > 0 && _same(b, A[i - 1]) && B[k + 1] && B[k + 1].type === "jump" && _same(B[k + 1], a)) { before++; k++; continue; }
      if (a && b && a.type === "jump" && b.type === "trim" && _same(a, b)) { inPlace++; i++; k++; continue; }
      if (a && b && a.type === b.type && _same(a, b)) { i++; k++; continue; }
      assert.fail(`${name}: the streams part at ${i} and ${k}: ${_show(A.slice(Math.max(0, i - 1), i + 2))} | ${_show(B.slice(Math.max(0, k - 1), k + 3))}`);
    }
    assert.strictEqual(inPlace + before, _cfLong(off).length, `${name}: one cut for each such float`);
    assert.strictEqual(on._debug.nTrims, off._debug.nTrims + inPlace + before, name);
    assert.strictEqual(_count(on, "trim"), on._debug.nTrims, name);
    assert.strictEqual(on.stitchCount, off.stitchCount, name);
    assert.deepStrictEqual([on.widthMM, on.heightMM], [off.widthMM, off.heightMM], name);
  }
});

test("cutFloats: every run still has its span, opening on its own jump and holding the same stitches", () => {
  const sewn = (d, r) => d.stitches.slice(r.i0, r.i1 + 1).filter((q) => q.type === "stitch").map((q) => `${q.x},${q.y}`).join(" ");
  for (const [name, build] of _cfCases) {
    const off = build(), on = build({ cutFloats: true });
    assert.strictEqual(on.runs.length, off.runs.length, name);
    on.runs.forEach((r, n) => {
      const was = off.runs[n];
      assert.deepStrictEqual([r.kind, r.shape, r.role, r.block], [was.kind, was.shape, was.role, was.block], `${name}: run ${n}`);
      assert.strictEqual(on.stitches[r.i0].type, "jump", `${name}: run ${n} opens on its jump`);
      assert.ok(_same(on.stitches[r.i0], off.stitches[was.i0]), `${name}: run ${n} opens where it did`);
      assert.strictEqual(sewn(on, r), sewn(off, was), `${name}: run ${n} holds the stitches it held`);
    });
  }
});

test("cutFloats: a float inside a run becomes the cut where it stands", () => {
  const off = _cfProngs(300), on = _cfProngs(300, { cutFloats: true });
  assert.strictEqual(_show(off.stitches.slice(5, 8)), "s150,0 j-150,0 s-187,0", "fixture: 30 mm across the gap, three jump records");
  assert.strictEqual(_cfDst.jumpRecords(-300, 0), 3);
  assert.strictEqual(_show(on.stitches.slice(5, 8)), "s150,0 t-150,0 s-187,0");
  assert.strictEqual(on.stitches.length, off.stitches.length, "no record is added inside a run");
  assert.strictEqual(_count(on, "trim"), _count(off, "trim") + 100);
});

test("cutFloats: at a run's opening jump the cut goes on the spot before it, outside the run", () => {
  const off = _cfBar(), on = _cfBar({ cutFloats: true });
  assert.strictEqual(_show(off.stitches.slice(76, 79)), "s-298,75 j300,75 s300,75", "fixture: the underlay's edge run ends 60 mm from where the next pass opens");
  assert.strictEqual(off.runs.filter((r) => r.i0 === 77).length, 1, "fixture: that jump opens a run");
  assert.strictEqual(_show(on.stitches.slice(76, 80)), "s-298,75 t-298,75 j300,75 s300,75");
  assert.strictEqual(on.runs.filter((r) => r.i0 === 78).length, 1, "the run opens on its jump, one record on");
  assert.ok(!on.runs.some((r) => r.i0 <= 77 && r.i1 >= 77), "and the cut is in no run");
  assert.strictEqual(on.stitches.length, off.stitches.length + 1);
});

test("cutFloats: a float of two jump records is left a float", () => {
  const off = _cfProngs(200), on = _cfProngs(200, { cutFloats: true });
  assert.strictEqual(_show(off.stitches.slice(5, 8)), "s100,0 j-100,0 s-137,0", "fixture: 20 mm across the gap");
  assert.strictEqual(_cfFloats(off.stitches).filter((f) => f.records === 2).length, 100, "fixture: two jump records each");
  assert.strictEqual(_fingerprint(on), _fingerprint(off));
});

test("cutFloats: the move to the stitch after the float counts, as the writer lays it in jumps", () => {
  // The column floats 19 mm to the far arm, two jump records, and the stitch
  // after it is 20 mm back the other way: the writer lays that move as a jump
  // record and a stitch. Three jumps in a row.
  const off = _cfStar(), on = _cfStar({ cutFloats: true });
  assert.strictEqual(_show(off.stitches.slice(92, 95)), "s-93,2 j98,0 s-98,0", "fixture");
  assert.deepStrictEqual([_cfDst.jumpRecords(98 + 93, 0 - 2), _cfDst.jumpRecords(-98 - 98, 0)], [2, 2], "fixture: two records out, and two back of which the last is the stitch");
  assert.strictEqual(_show(on.stitches.slice(92, 95)), "s-93,2 t98,0 s-98,0");
  // one record out and two back is two jumps in a row: left
  assert.strictEqual(_show(off.stitches.slice(236, 239)), "s-2,-93 j98,0 s-98,0", "fixture");
  assert.strictEqual(_show(on.stitches.slice(236, 239)), "s-2,-93 j98,0 s-98,0");
  assert.strictEqual(_count(on, "trim") - _count(off, "trim"), 3);
});

test("cutFloats: nothing is cut where no thread is attached", () => {
  // The file's first move, the move after a colour change and the move after
  // the builder's own cut are each 30 mm or more, and none has thread on it.
  const square = (x0) => ({ outer: _cfPts([[x0, 0], [x0 + 100, 0], [x0 + 100, 100], [x0, 100]]), holes: [], tierOverride: "fill" });
  const build = (regions) => (extra) => DG.buildQualityDesign(regions, Object.assign({ garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 60, darkOnTop: false, underlay: false }, extra));
  const colours = build([{ rgb: [0, 0, 0], shapes: [square(0)] }, { rgb: [200, 0, 0], shapes: [square(500)] }]);
  const shapes = build([{ rgb: [0, 0, 0], shapes: [square(0), square(500)] }]);
  const k = colours().stitches.findIndex((s) => s.type === "color");
  assert.strictEqual(_show(colours().stitches.slice(k - 2, k + 3)), "s-200,-49 t-200,-49 c-200,-49 j200,50 s200,50", "fixture: 40 mm after a colour change");
  const t = shapes().stitches.findIndex((s) => s.type === "trim");
  assert.strictEqual(_show(shapes().stitches.slice(t - 1, t + 3)), "s-200,-49 t-200,-49 j200,50 s200,50", "fixture: 40 mm after the builder's own cut");
  for (const design of [colours, shapes]) {
    const off = design(), on = design({ cutFloats: true });
    assert.strictEqual(_show(off.stitches.slice(0, 2)), "j-300,50 s-300,50", "fixture: the file's first move is three jump records");
    assert.strictEqual(_fingerprint(on), _fingerprint(off));
  }
});

test("cutFloats: the cuts a DST reader finds are the ones it found before", () => {
  // The machine already cut at each of these floats. Written and read back,
  // the file has the cuts it had; what changes is that the stream says so.
  for (const [name, build] of _cfCases) {
    const off = build(), on = build({ cutFloats: true });
    assert.strictEqual(_cfFileCuts(on), _cfFileCuts(off), name);
  }
  const off = _cfProngs(300), on = _cfProngs(300, { cutFloats: true });
  assert.deepStrictEqual([_count(off, "trim"), _cfFileCuts(off)], [1, 102], "fixture: one cut asked for, 102 in the file");
  assert.deepStrictEqual([_count(on, "trim"), _cfFileCuts(on)], [101, 102], "all but the file's first move are in the stream now");
});

test("cutFloats: with ties, the thread is locked either side of each cut", () => {
  const tied = _cfProngs(300, { ties: true }), both = _cfProngs(300, { ties: true, cutFloats: true });
  const threads = _threads(both);
  assert.strictEqual(threads.length, _threads(tied).length + 100, "a hundred more threads");
  for (const [ti, t] of threads.entries()) {
    const ends = _sewnEnds(t);
    assert.ok(ends, `thread ${ti} sews nothing`);
    const a = t.slice(ends.first, ends.first + 5), z = t.slice(ends.last - 4, ends.last + 1);
    assert.ok(_same(a[0], a[2]) && _same(a[2], a[4]) && _same(a[1], a[3]), `thread ${ti} does not open with a lock`);
    assert.ok(_same(z[0], z[2]) && _same(z[2], z[4]) && _same(z[1], z[3]), `thread ${ti} does not close with a lock`);
  }
  assert.strictEqual(both._debug.nTies, 2 * threads.length);
  assert.strictEqual(_cfLong(both).length, 0, "and the locks make no new float");
});

// `cutLongFloats` on streams written out by hand: the cases no small design
// makes on its own. It changes `stitches` and `spans` in place and returns
// how many cuts it made.
const _cfHand = (text, spans) => {
  const stitches = text.split(" ").map((w) => { const [x, y] = w.slice(1).split(",").map(Number); return _rec({ s: "stitch", j: "jump", t: "trim", c: "color", e: "end" }[w[0]], x, y); });
  const made = DG.cutLongFloats(stitches, spans || []);
  return { made, text: _show(stitches), spans };
};

test("cutLongFloats: a float of several jumps is cut at its first", () => {
  // three jump records of 10 mm each: one record apiece, three in a row
  assert.deepStrictEqual(_cfHand("s0,0 j100,0 j200,0 j300,0 s300,0"), { made: 1, text: "s0,0 t100,0 j200,0 j300,0 s300,0", spans: undefined });
  // two of them, and a stitch on the spot: two in a row, left
  assert.strictEqual(_cfHand("s0,0 j100,0 j200,0 s200,0").text, "s0,0 j100,0 j200,0 s200,0");
  // two of them, and a stitch 13 mm on: its move is a jump record and a stitch
  assert.strictEqual(_cfHand("s0,0 j100,0 j200,0 s330,0").text, "s0,0 t100,0 j200,0 s330,0");
  // a jump that goes nowhere is a record all the same
  assert.strictEqual(_cfHand("s0,0 j0,0 j0,0 j0,0 s0,0").text, "s0,0 t0,0 j0,0 j0,0 s0,0");
});

test("cutLongFloats: only a float between two stitches of one thread is cut", () => {
  for (const left of [
    "j300,0 s300,0 s310,0",                 // the stream's first move
    "s0,0 t0,0 j300,0 s300,0",              // after a cut
    "s0,0 t0,0 c0,0 j300,0 s300,0",         // after a colour change
    "s0,0 j300,0 t300,0 s300,0",            // a float that ends in a cut already
    "s0,0 j300,0 c300,0 j300,0 s300,0",     // or in a colour change
    "s0,0 s10,0 j300,0",                    // or at the stream's end
    "s0,0 j300,0 e0,0",
  ]) assert.deepStrictEqual([_cfHand(left).made, _cfHand(left).text], [0, left]);
  // and each float is asked on its own: two of them, one long
  assert.strictEqual(_cfHand("s0,0 j200,0 s200,0 j500,0 s500,0 s510,0").text, "s0,0 j200,0 s200,0 t500,0 s500,0 s510,0");
});

test("cutLongFloats: at a run's opening jump the cut goes in before it and the spans after it move up", () => {
  const spans = [{ i0: 0, i1: 2, kind: "underlay" }, { i0: 3, i1: 5, kind: "fill" }, { i0: 6, i1: 8, kind: "run" }];
  const got = _cfHand("j0,0 s0,0 s10,0 j300,0 s300,0 s310,0 j320,0 s320,0 s330,0", spans);
  assert.strictEqual(got.text, "j0,0 s0,0 s10,0 t10,0 j300,0 s300,0 s310,0 j320,0 s320,0 s330,0");
  assert.strictEqual(got.made, 1);
  assert.deepStrictEqual(spans.map((r) => [r.i0, r.i1]), [[0, 2], [4, 6], [7, 9]], "the cut at 3 is in no span");
  // a float inside a span that runs on into the next span's opening jump: cut where the float starts
  const two = [{ i0: 0, i1: 3, kind: "fill" }, { i0: 4, i1: 6, kind: "fill" }];
  const run = _cfHand("j0,0 s0,0 s10,0 j150,0 j300,0 s300,0 s310,0", two);
  assert.strictEqual(run.text, "j0,0 s0,0 s10,0 t150,0 j300,0 s300,0 s310,0");
  assert.deepStrictEqual(two.map((r) => [r.i0, r.i1]), [[0, 3], [4, 6]], "no record went in, so no span moves");
});

test("cutLongFloats: a stream with nothing to cut is left the very array it was", () => {
  const stitches = [_rec("jump", 0, 0), _rec("stitch", 0, 0), _rec("jump", 200, 0), _rec("stitch", 200, 0)], first = stitches[0];
  assert.strictEqual(DG.cutLongFloats(stitches, []), 0);
  assert.strictEqual(stitches.length, 4);
  assert.strictEqual(stitches[0], first);
});

// --- cutFloats: what the independent re-measure's mutants got past (2026-10-06) --
//
// Twelve edits to the rule passed every test above: the rule narrowed to some
// builds and not others, a long float or a far stitch left out, a record with
// a key too many, the lettering builder taught the flag. Each has a test here
// that the edit fails. And the claim the re-measure broke is pinned as it
// really is: in the DST the stitches are the same, but a float of one or two
// jump records that becomes the `trim` is laid as three.
const _cfParse = (text) => text.split(" ").map((w) => { const [x, y] = w.slice(1).split(",").map(Number); return _rec({ s: "stitch", j: "jump", t: "trim", c: "color", e: "end" }[w[0]], x, y); });
const _cfBarMm = (wMm, hMm, extra) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [{ outer: _cfPts([[0, 0], [wMm * 10, 0], [wMm * 10, hMm * 10], [0, hMm * 10]]), holes: [], tierOverride: "fill" }] }],
  Object.assign({ garment: { id: "full_back", widthIn: 12, heightIn: 12 }, pxPerMm: 10, targetWidthMm: wMm, darkOnTop: false, underlay: true }, extra));
// Built without the flag the design has such floats; with it, none, and one more cut for each.
const _cfBothWays = (build, name) => {
  const off = build({}), on = build({ cutFloats: true });
  assert.ok(_cfLong(off).length > 0, `fixture: ${name} has such a float without the flag`);
  assert.strictEqual(_cfLong(on).length, 0, `${name}: a float is left`);
  assert.strictEqual(on._debug.nTrims, off._debug.nTrims + _cfLong(off).length, name);
};
// The DST's records, read from the file: where each lands and whether it is a jump.
const _cfFileRecords = (d) => {
  const bytes = _cfDst.encodeDST(d), out = [];
  const bit = (b, m, v) => (b & m ? v : 0);
  let x = 0, y = 0;
  for (let i = 512; i + 2 < bytes.length; i += 3) {
    const b0 = bytes[i], b1 = bytes[i + 1], b2 = bytes[i + 2];
    if ((b2 & 0xf3) === 0xf3) break;
    x += bit(b0, 0x01, 1) - bit(b0, 0x02, 1) + bit(b0, 0x04, 9) - bit(b0, 0x08, 9) + bit(b1, 0x01, 3) - bit(b1, 0x02, 3) + bit(b1, 0x04, 27) - bit(b1, 0x08, 27) + bit(b2, 0x04, 81) - bit(b2, 0x08, 81);
    y += bit(b0, 0x80, 1) - bit(b0, 0x40, 1) + bit(b0, 0x20, 9) - bit(b0, 0x10, 9) + bit(b1, 0x80, 3) - bit(b1, 0x40, 3) + bit(b1, 0x20, 27) - bit(b1, 0x10, 27) + bit(b2, 0x20, 81) - bit(b2, 0x10, 81);
    out.push({ x, y, jump: (b2 & 0xc3) === 0x83 });
  }
  return out;
};

test("cutFloats: it cuts whatever else is asked of the build", () => {
  _cfBothWays((x) => _cfBarMm(60, 15, Object.assign({ fillColumns: true }, x)), "the column walk");
  // a bar 120 x 40 mm with a hole 35 mm wide, rows along it, under a fabric preset
  _cfBothWays((x) => DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: _cfPts([[0, 0], [1200, 0], [1200, 400], [0, 400]]), holes: [_cfPts([[400, 100], [750, 100], [750, 300], [400, 300]])], angleOverride: 0 }] }],
    Object.assign({ garment: { id: "full_back", widthIn: 12, heightIn: 12 }, pxPerMm: 10, targetWidthMm: 120, darkOnTop: false, underlay: true, fabric: FABRICS.getFabric("pique_knit") }, x)), "a fabric preset");
  _cfBothWays((x) => _cfBarMm(60, 15, Object.assign({ garment: { id: "hat_front", widthIn: 5, heightIn: 2.25 } }, x)), "a cap");
  _cfBothWays((x) => _cfBarMm(60, 15, Object.assign({ outline: true }, x)), "a finishing outline");
  assert.ok(_cfBarMm(100, 100).stitches.length > 10000, "fixture: a design of over 10,000 records");
  _cfBothWays((x) => _cfBarMm(100, 100, x), "a design of over 10,000 records");
});

test("cutFloats: a float of ten jump records and more is cut like any other", () => {
  const most = Math.max(..._cfFloats(_cfBarMm(150, 15).stitches).map((f) => f.records));
  assert.ok(most >= 10, `fixture: a float of ten jump records, got ${most}`);
  _cfBothWays((x) => _cfBarMm(150, 15, x), "a 150 mm bar");
});

test("cutFloats: the caller's options are left as they were, and work twice", () => {
  const o = { garment: { id: "full_back", widthIn: 12, heightIn: 12 }, pxPerMm: 10, targetWidthMm: 60, darkOnTop: false, underlay: true, cutFloats: true };
  const was = JSON.stringify(o);
  const regions = () => [{ rgb: [0, 0, 0], shapes: [{ outer: _cfPts([[0, 0], [600, 0], [600, 150], [0, 150]]), holes: [], tierOverride: "fill" }] }];
  const a = DG.buildQualityDesign(regions(), o), b = DG.buildQualityDesign(regions(), o);
  assert.strictEqual(JSON.stringify(o), was);
  assert.strictEqual(_fingerprint(b), _fingerprint(a));
  assert.strictEqual(_cfLong(b).length, 0);
});

test("cutFloats: the lettering builder does not read it, even where it has such a float", () => {
  // Lettering cuts every hop over `trimAtMm` itself, so it has no such float
  // unless that is set past 24.2 mm. Given one, the flag still does nothing
  // there: the lettering builder has no such rule.
  const o = { garment: { id: "full_back", widthIn: 12, heightIn: 12 }, pxPerMm: 8, targetWidthMm: 250, trimAtMm: 1000 };
  const off = DG.buildLetteringDesign(_tieFont(), "I I", o), on = DG.buildLetteringDesign(_tieFont(), "I I", Object.assign({}, o, { cutFloats: true }));
  assert.ok(_cfLong(off).length > 0, "fixture: lettering with a float of three jump records");
  assert.deepStrictEqual(on, off);
});

test("cutLongFloats: a float of five jumps is cut once, and the stitch after may be any distance off", () => {
  let got = _cfHand("s0,0 j100,0 j200,0 j300,0 j400,0 s400,0");
  assert.deepStrictEqual([got.made, got.text], [1, "s0,0 t100,0 j200,0 j300,0 j400,0 s400,0"]);
  // one jump record, then 39 mm to the stitch: three jump records and the stitch
  got = _cfHand("s0,0 j10,0 s400,0");
  assert.deepStrictEqual([got.made, got.text], [1, "s0,0 t10,0 s400,0"]);
});

test("cutLongFloats: a new trim is a plain record, x y type and nothing more", () => {
  const stitches = _cfParse("j0,0 s0,0 s10,0 j300,0 s300,0 s310,0 j600,0 s640,0");
  DG.cutLongFloats(stitches, [{ i0: 0, i1: 2 }, { i0: 3, i1: 7 }]);
  assert.deepStrictEqual(stitches[3], { x: 10, y: 0, type: "trim" }, "the one put in before a run's opening jump");
  assert.deepStrictEqual(stitches[7], { x: 600, y: 0, type: "trim" }, "the jump inside a run, turned");
  assert.ok(_cfBar({ cutFloats: true }).stitches.every((s) => Object.keys(s).join() === "x,y,type"));
});

test("cutFloats: in the DST every stitch is where it was, and a short float made the trim is laid as three records", () => {
  // The star's column floats two jump records out and sews a jump record and
  // a stitch back. As a `trim` the writer lays the float as three records, so
  // the frame stops at thirds of the same line and not at its half. Every
  // stitch record lands where it did; the file is three jump records longer.
  const off = _cfFileRecords(_cfStar()), on = _cfFileRecords(_cfStar({ cutFloats: true }));
  const sewn = (recs) => recs.filter((r) => !r.jump).map((r) => `${r.x},${r.y}`).join(" ");
  assert.strictEqual(sewn(on), sewn(off));
  assert.strictEqual(on.length - off.length, 3, "three floats of two records, each laid as three");
  const stops = (recs) => new Set(recs.filter((r) => r.jump).map((r) => `${r.x},${r.y}`));
  const onlyOn = [...stops(on)].filter((p) => !stops(off).has(p)), onlyOff = [...stops(off)].filter((p) => !stops(on).has(p));
  assert.deepStrictEqual([onlyOn.length, onlyOff.length], [6, 3], "the frame stops at thirds where it stopped at the half");
  // a float that was three records already is the same bytes as a trim: the prongs' file does not change
  assert.deepStrictEqual(_cfFileRecords(_cfProngs(300, { cutFloats: true })), _cfFileRecords(_cfProngs(300)));
});
