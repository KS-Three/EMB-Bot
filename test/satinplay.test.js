const assert = require("node:assert");
const { test } = require("node:test");
const satinplay = require("../src/satinplay.js");
const { correspond, columnGeom, satinFromGeom } = satinplay;

// A straight 40mm-wide (px units, pxPerMm=10 elsewhere in this codebase so
// 400 units == 40mm), 40mm-long synthetic column — same fixture shape used
// to verify this math before writing this test.
function straightColumn(lengthPx, widthPx, n) {
  const railA = [], railB = [];
  for (let i = 0; i <= n; i++) {
    const y = (i * lengthPx) / n;
    railA.push({ x: -widthPx / 2, y });
    railB.push({ x: widthPx / 2, y });
  }
  return { railA, railB };
}

function crossAngleDeg(p0, p1) {
  // Angle of the cross vector from the column's own axis (+y here), oriented
  // consistently from the smaller-x (rail A) point to the larger-x (rail B)
  // point. emitZigzag's output alternates which point of a cross-stitch pair
  // it pushes first (leading edge alternates per station, so consecutive
  // crosses share a side) — orienting by x rather than trusting pts[i]/[i+1]
  // array order keeps this measurement invariant to that alternation.
  const [pA, pB] = p0.x <= p1.x ? [p0, p1] : [p1, p0];
  return Math.atan2(pB.x - pA.x, pB.y - pA.y) * 180 / Math.PI;
}

test("satinFromGeom: slantDeg 0 (absent) is byte-identical to today's perpendicular cross output", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const { A, B } = correspond(railA, railB, [], 12);
  const geom = columnGeom(railA, railB, [], 12);
  const noField = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10 });
  const explicit0 = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, slantDeg: 0 });
  assert.deepStrictEqual(explicit0, noField);
});

test("satinFromGeom: slantDeg leans the cross-stitch by exactly that many degrees away from perpendicular, at interior stations", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const geom = columnGeom(railA, railB, [], 12);
  const opts = { spacingMm: 4, pxPerMm: 10 }; // coarse spacing -> few, easy-to-inspect stations
  const pts15 = satinFromGeom(geom, 0, 1, Object.assign({ slantDeg: 15 }, opts));
  const ptsM15 = satinFromGeom(geom, 0, 1, Object.assign({ slantDeg: -15 }, opts));
  // Interior cross pairs (skip the first/last, which taper toward
  // perpendicular as the shifted sample clamps against the column end).
  for (let i = 2; i + 1 < pts15.length - 2; i += 2) {
    const ang = Math.abs(crossAngleDeg(pts15[i], pts15[i + 1]));
    assert.ok(Math.abs(ang - 105) < 1, `slantDeg=15 interior cross should be ~105deg from column axis, got ${ang}`);
  }
  for (let i = 2; i + 1 < ptsM15.length - 2; i += 2) {
    const ang = Math.abs(crossAngleDeg(ptsM15[i], ptsM15[i + 1]));
    assert.ok(Math.abs(ang - 75) < 1, `slantDeg=-15 interior cross should be ~75deg from column axis, got ${ang}`);
  }
});

// ---- STRUCTURAL UNDERLAY (Law 50) --------------------------------------
// Pure geometry, on the synthetic straight column above: a center walk sits on
// the column axis and an edge run sits just inside both rails. Both are closed
// walks that hand the needle back to the span's START, which is what lets
// satinfont emit them with zero extra travel.

const { centerUnderlayFromGeom, edgeUnderlayFromGeom, centerRun } = satinplay;
const PPM = 10;                    // px per mm, matching straightColumn's units
const segLensMm = (pts) => { const o = []; for (let i = 0; i + 1 < pts.length; i++) o.push(Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y) / PPM); return o; };
const same = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) < 1e-9;

test("centerUnderlay: walks the column AXIS — every point is inside the rails, never outside", () => {
  const { railA, railB } = straightColumn(400, 40, 20);   // 40mm long, 4mm wide
  const geom = columnGeom(railA, railB, [], 12);
  const pts = centerUnderlayFromGeom(geom, 0, 1, { stepMm: 3, pxPerMm: PPM });
  assert.ok(pts.length > 4, "a 40mm column at 3mm step must emit real points");
  for (const p of pts) {
    assert.ok(Math.abs(p.x) < 1e-6, `center run must sit on the column axis, got x=${p.x}`);
    assert.ok(Math.abs(p.x) < 20, "and therefore strictly inside the +/-20px rails");
    assert.ok(p.y >= -1e-6 && p.y <= 400 + 1e-6, "and within the column's own length");
  }
});

test("centerUnderlay: 2 repeats (the published default) return the needle to the span's START", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const geom = columnGeom(railA, railB, [], 12);
  const pts = centerUnderlayFromGeom(geom, 0, 1, { stepMm: 3, pxPerMm: PPM, repeats: 2 });
  assert.ok(same(pts[0], pts[pts.length - 1]), "a 2-repeat walk must end where it began");
  // out and back: it reaches the far end exactly once, in the middle
  const far = pts.findIndex((p) => Math.abs(p.y - 400) < 1e-6);
  assert.ok(far > 0 && far < pts.length - 1, "the far end is reached mid-path, not at an end");
  const one = centerUnderlayFromGeom(geom, 0, 1, { stepMm: 3, pxPerMm: PPM, repeats: 1 });
  assert.ok(!same(one[0], one[one.length - 1]), "1 repeat, by contrast, leaves the needle at the far end");
  assert.strictEqual(pts.length, one.length * 2 - 1, "2 repeats is the 1-repeat path plus its reverse");
});

test("centerUnderlay: honors the TRAVERSAL direction so it ends where its satin starts", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const geom = columnGeom(railA, railB, [], 12);
  const fwd = centerUnderlayFromGeom(geom, 0, 1, { stepMm: 3, pxPerMm: PPM });
  const rev = centerUnderlayFromGeom(geom, 1, 0, { stepMm: 3, pxPerMm: PPM });
  assert.ok(Math.abs(fwd[0].y - 0) < 1e-6, "f0=0 -> starts and ends at y=0");
  assert.ok(Math.abs(rev[0].y - 400) < 1e-6, "f0=1 -> starts and ends at y=400");
  assert.ok(same(rev[0], rev[rev.length - 1]));
});

test("centerUnderlay: every emitted stitch clears the 0.5mm floor and the 3mm step", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const geom = columnGeom(railA, railB, [], 12);
  for (const [f0, f1] of [[0, 1], [0.1, 0.37], [0.5, 0.52]]) {
    for (const L of segLensMm(centerUnderlayFromGeom(geom, f0, f1, { stepMm: 3, minStitchMm: 0.5, pxPerMm: PPM }))) {
      assert.ok(L >= 0.5 - 1e-9, `stitch ${L}mm is under the 0.5mm floor`);
      assert.ok(L <= 3 + 1e-9, `stitch ${L}mm exceeds the 3mm step`);
    }
  }
});

test("centerUnderlay: a span too short to carry one minimum stitch emits nothing at all", () => {
  const { railA, railB } = straightColumn(400, 40, 20);   // 400px = 40mm
  const geom = columnGeom(railA, railB, [], 12);
  // 0.1% of a 40mm column = 0.04mm, well under the 0.5mm floor
  assert.deepStrictEqual(centerUnderlayFromGeom(geom, 0, 0.001, { stepMm: 3, minStitchMm: 0.5, pxPerMm: PPM }), []);
  // and just over the floor, it does emit
  assert.ok(centerUnderlayFromGeom(geom, 0, 0.02, { stepMm: 3, minStitchMm: 0.5, pxPerMm: PPM }).length >= 2);
});

test("edgeUnderlay: sits INSIDE both rails at exactly the requested inset, and closes back to the start", () => {
  const { railA, railB } = straightColumn(400, 40, 20);   // rails at x = -20 / +20 px (4mm wide)
  const geom = columnGeom(railA, railB, [], 12);
  const pts = edgeUnderlayFromGeom(geom, 0, 1, { stepMm: 3, insetMm: 0.4, pxPerMm: PPM });
  assert.ok(pts.length > 8);
  // inset 0.4mm = 4px, and 0.4*width(40px) = 16px, so the cap does not bite:
  // the two inset rails must land at x = -16 and +16.
  for (const p of pts) {
    assert.ok(Math.abs(p.x) <= 16 + 1e-6, `edge run must stay inside the rails, got x=${p.x}`);
    assert.ok(Math.abs(p.x) < 20, "strictly inside, never on or past the rail");
  }
  const xs = pts.map((p) => p.x);
  assert.ok(Math.min(...xs) < -15.9 && Math.max(...xs) > 15.9, "it must actually reach both inset rails");
  assert.ok(same(pts[0], pts[pts.length - 1]), "a contour underlay is a closed loop");
  assert.ok(Math.abs(pts[0].y) < 1e-6, "and it closes at the f0 end, where the satin starts");
});

test("edgeUnderlay: the inset is capped at 40% of column width so hairline columns never invert", () => {
  // 0.6mm-wide column; a naive 0.4mm-per-side inset would push each rail PAST
  // the centerline and turn the loop inside out.
  const { railA, railB } = straightColumn(400, 6, 20);
  const geom = columnGeom(railA, railB, [], 12);
  const pts = edgeUnderlayFromGeom(geom, 0, 1, { stepMm: 3, insetMm: 0.4, pxPerMm: PPM });
  for (const p of pts) assert.ok(Math.abs(p.x) <= 3 + 1e-6, `still inside the +/-3px rails, got x=${p.x}`);
  const xs = pts.map((p) => p.x);
  // capped at 40% of 6px = 2.4px inset -> rails land at +/-0.6px, still apart
  assert.ok(Math.min(...xs) < -0.5 && Math.max(...xs) > 0.5, "the two inset rails must stay on their own sides");
});

test("edgeUnderlay: every emitted stitch clears the 0.5mm floor and the DST record ceiling", () => {
  for (const widthPx of [6, 20, 40, 90]) {
    const { railA, railB } = straightColumn(400, widthPx, 20);
    const geom = columnGeom(railA, railB, [], 12);
    for (const L of segLensMm(edgeUnderlayFromGeom(geom, 0, 1, { stepMm: 3, insetMm: 0.4, minStitchMm: 0.5, pxPerMm: PPM }))) {
      assert.ok(L >= 0.5 - 1e-9, `width ${widthPx}px: stitch ${L}mm is under the 0.5mm floor`);
      assert.ok(L <= 12.1, `width ${widthPx}px: stitch ${L}mm exceeds the 12.1mm DST record ceiling`);
    }
  }
});

test("centerRun (previously dead code) now walks 2 repeats at the requested step, not 2x it", () => {
  const { railA, railB } = straightColumn(400, 40, 20);
  const pts = centerRun(railA, railB, [], { stepMm: 3, pxPerMm: PPM });
  assert.ok(pts.length > 4);
  for (const p of pts) assert.ok(Math.abs(p.x) < 1e-6, "on the axis");
  for (const L of segLensMm(pts)) assert.ok(L <= 3 + 1e-9, `stitch ${L}mm exceeds the requested 3mm step`);
  assert.ok(same(pts[0], pts[pts.length - 1]), "ends where it began");
  assert.deepStrictEqual(pts, centerUnderlayFromGeom(columnGeom(railA, railB, [], 12), 0, 1, { stepMm: 3, pxPerMm: PPM }));
});

// ---- Width guards (2026-09-03): the cross floor, the span split, the bean ---
//
// Every number below is in px at pxPerMm 10, so "5 px" is the 0.5 mm floor.
// The columns are synthetic and straight; what is under test is the floor's
// arithmetic and the split's run-length logic, not correspondence.

// A straight column whose width goes linearly from w0 to w1 over its length.
function taperedColumn(lengthPx, w0, w1, n) {
  const railA = [], railB = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, y = t * lengthPx, w = w0 + (w1 - w0) * t;
    railA.push({ x: -w / 2, y });
    railB.push({ x: w / 2, y });
  }
  return { railA, railB };
}
function crossLengths(pts) {
  const out = [];
  for (let i = 0; i + 1 < pts.length; i += 2) out.push(Math.hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y));
  return out;
}

test("emitZigzag: minCrossMm absent or 0 is byte-identical to the legacy 0.3 px guard", () => {
  const { railA, railB } = taperedColumn(400, 30, 0, 40);
  const geom = columnGeom(railA, railB, [], 12);
  const legacy = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10 });
  const zero = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0 });
  assert.deepStrictEqual(zero, legacy);
  // and the legacy stream really does carry sub-floor crosses at the taper
  assert.ok(crossLengths(legacy).some((c) => c < 5), "the fixture tapers under 0.5 mm, or this test proves nothing");
});

test("emitZigzag: minCrossMm 0.5 drops every cross under the floor and keeps every cross over it", () => {
  const { railA, railB } = taperedColumn(400, 30, 0, 40);
  const geom = columnGeom(railA, railB, [], 12);
  const legacy = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10 });
  const floored = satinFromGeom(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 });
  const kept = crossLengths(floored);
  assert.ok(kept.length > 0);
  assert.ok(kept.every((c) => c >= 5 - 1e-9), `a cross under 0.5 mm survived: ${Math.min(...kept)}`);
  const over = crossLengths(legacy).filter((c) => c >= 5 - 1e-9).length;
  assert.strictEqual(kept.length, over, "the floor must drop only what is under it");
});

test("splitByCrossFloor: with no floor a span is one satin segment", () => {
  const { railA, railB } = taperedColumn(400, 30, 0, 40);
  const geom = columnGeom(railA, railB, [], 12);
  assert.deepStrictEqual(satinplay.splitByCrossFloor(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10 }), [{ f0: 0, f1: 1, thin: false }]);
  assert.deepStrictEqual(satinplay.splitByCrossFloor(geom, 0.2, 0.7, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0 }), [{ f0: 0.2, f1: 0.7, thin: false }]);
});

test("splitByCrossFloor: a column that narrows from 2 mm to 0.3 mm halfway splits into satin then hairline at the step", () => {
  // 2 mm wide for the first half, 0.3 mm for the second — a stroke that
  // changes weight, the script-connector case.
  const railA = [], railB = [];
  for (let i = 0; i <= 200; i++) {
    const y = i * 2, w = i < 100 ? 20 : 3;
    railA.push({ x: -w / 2, y }); railB.push({ x: w / 2, y });
  }
  const geom = columnGeom(railA, railB, [], 12);
  const segs = satinplay.splitByCrossFloor(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 });
  assert.strictEqual(segs.length, 2, JSON.stringify(segs));
  assert.strictEqual(segs[0].thin, false);
  assert.strictEqual(segs[1].thin, true);
  assert.strictEqual(segs[0].f0, 0);
  assert.strictEqual(segs[1].f1, 1);
  assert.strictEqual(segs[0].f1, segs[1].f0, "segments must tile the span");
  assert.ok(Math.abs(segs[0].f1 - 0.5) < 0.03, `boundary at ${segs[0].f1}, expected ~0.5`);
});

test("splitByCrossFloor: pull compensation counts — a 0.3 mm column under 0.3 mm of comp is satin", () => {
  const { railA, railB } = taperedColumn(400, 3, 3, 40);
  const geom = columnGeom(railA, railB, [], 12);
  const bare = satinplay.splitByCrossFloor(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 });
  const comped = satinplay.splitByCrossFloor(geom, 0, 1, { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5, pullCompMm: 0.3 });
  assert.deepStrictEqual(bare, [{ f0: 0, f1: 1, thin: true }]);
  assert.deepStrictEqual(comped, [{ f0: 0, f1: 1, thin: false }]);
});

test("splitByCrossFloor: a one-station wobble under the floor stays satin, and a lone wide station inside a hairline stays a run", () => {
  const dip = [], bump = [];
  for (let i = 0; i <= 400; i++) {
    const y = i; // 1 px per rail point, so a one-point feature is well under one 4 px station
    const wd = i === 200 ? 2 : 20, wb = i === 200 ? 20 : 2;
    dip.push([{ x: -wd / 2, y }, { x: wd / 2, y }]);
    bump.push([{ x: -wb / 2, y }, { x: wb / 2, y }]);
  }
  const g1 = columnGeom(dip.map((p) => p[0]), dip.map((p) => p[1]), [], 12);
  const g2 = columnGeom(bump.map((p) => p[0]), bump.map((p) => p[1]), [], 12);
  const opts = { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 };
  assert.deepStrictEqual(satinplay.splitByCrossFloor(g1, 0, 1, opts), [{ f0: 0, f1: 1, thin: false }]);
  assert.deepStrictEqual(satinplay.splitByCrossFloor(g2, 0, 1, opts), [{ f0: 0, f1: 1, thin: true }]);
});

test("beanFromGeom: three passes over the span, ending at f1, every stitch at or over the minimum", () => {
  const { railA, railB } = taperedColumn(100, 3, 3, 10);   // a 10 mm hairline
  const geom = columnGeom(railA, railB, [], 12);
  const pts = satinplay.beanFromGeom(geom, 0, 1, { pxPerMm: 10, stepMm: 0.73, passes: 3, minStitchMm: 0.5 });
  assert.ok(pts.length >= 4);
  const start = pts[0], end = pts[pts.length - 1];
  assert.ok(Math.abs(start.y - 0) < 1e-6 && Math.abs(end.y - 100) < 1e-6, "an odd pass count ends at the far end");
  let path = 0;
  for (let i = 1; i < pts.length; i++) {
    const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    assert.ok(d >= 5 - 1e-9, `stitch ${i} is ${d} px, under the 0.5 mm minimum`);
    path += d;
  }
  assert.ok(Math.abs(path - 300) < 1e-6, `three passes over 100 px should walk 300 px, walked ${path}`);
  // traversal order is honoured: f1 -> f0 ends at f0
  const back = satinplay.beanFromGeom(geom, 1, 0, { pxPerMm: 10, stepMm: 0.73, passes: 3, minStitchMm: 0.5 });
  assert.ok(Math.abs(back[back.length - 1].y - 0) < 1e-6);
});

// ---- Counter guard (fine-lettering review item 4, 2026-09-03) --------------
// Bold widens a column by pushing its rails apart. Where two rails face each
// other across a counter, the guard holds the weight so the gap never goes
// under the cross floor, and holds it entirely where the gap is already under
// the floor: enlarge, never close. Outside edges always get the full weight.

function twoStems(gapPx, wPx = 18, hPx = 60) {
  // Two vertical columns `wPx` wide, inner rails `gapPx` apart, in px.
  const col = (x0) => satinplay.columnGeom(
    [{ x: x0, y: 0 }, { x: x0, y: hPx }],
    [{ x: x0 + wPx, y: 0 }, { x: x0 + wPx, y: hPx }], [], 12);
  return [col(0), col(wPx + gapPx)];
}

test("counterGap: a rail sees the rail that faces it across the gap, and nothing on an outside edge", () => {
  const geoms = twoStems(10);
  const cloud = satinplay.railCloud(geoms, 4);
  // Left column's inner rail (x = 18, outward normal +x) faces the right
  // column's inner rail at x = 28: gap 10 px.
  assert.ok(Math.abs(satinplay.counterGap(18, 30, 1, 0, cloud, 6) - 10) < 1e-6);
  // Its outer rail (x = 0, outward normal -x) faces nothing.
  assert.strictEqual(satinplay.counterGap(0, 30, -1, 0, cloud, 6), Infinity);
  // The right column's inner rail sees the same gap from the other side.
  assert.ok(Math.abs(satinplay.counterGap(28, 30, -1, 0, cloud, 6) - 10) < 1e-6);
});

test("stationPush: the weight is whole on an open edge, capped at the floor across a counter, and withheld where the counter is already under it", () => {
  const cloud = satinplay.railCloud(twoStems(10), 4);
  const guard = { cloud, floorPx: 5, windowPx: 6, stats: { counterHeld: 0 } };
  // Left column, a station at y = 30: rail A is the inner rail (x = 18), B the outer (x = 0).
  const wide = satinplay.stationPush(18, 30, 0, 30, 0, 3, guard, true);        // gap 10 px, weight 3 px, floor 5
  assert.ok(Math.abs(wide.a - 1.5) < 1e-9 && Math.abs(wide.b - 1.5) < 1e-9, "10 px can spare 3: full half-weight on both rails");
  assert.strictEqual(guard.stats.counterHeld, 0);
  const tight = { cloud: satinplay.railCloud(twoStems(6), 4), floorPx: 5, windowPx: 6, stats: { counterHeld: 0 } };
  const capped = satinplay.stationPush(18, 30, 0, 30, 0, 3, tight, true);       // gap 6 px: only 1 px to spare
  assert.ok(Math.abs(capped.a - 0.5) < 1e-9, `inner rail takes half of the 1 px the gap can spare, got ${capped.a}`);
  assert.ok(Math.abs(capped.b - 1.5) < 1e-9, "outer rail still takes the full half-weight");
  assert.strictEqual(tight.stats.counterHeld, 1);
  const closed = { cloud: satinplay.railCloud(twoStems(4), 4), floorPx: 5, windowPx: 6, stats: { counterHeld: 0 } };
  const held = satinplay.stationPush(18, 30, 0, 30, 0, 3, closed, true);        // gap 4 px < floor: nothing toward it
  assert.strictEqual(held.a, 0, "a counter already under the floor gets no weight at all");
  assert.ok(Math.abs(held.b - 1.5) < 1e-9);
  // Fabric pull comp is never held: it rides whole on both rails.
  const pulled = satinplay.stationPush(18, 30, 0, 30, 2, 3, closed, false);
  assert.ok(Math.abs(pulled.a - 1) < 1e-9 && Math.abs(pulled.b - 2.5) < 1e-9, `pull 2 px -> 1 px each rail, weight held on the inner one; got ${pulled.a}, ${pulled.b}`);
  // No guard: one shared offset, the legacy stream.
  const legacy = satinplay.stationPush(18, 30, 0, 30, 2, 3, null, true);
  assert.deepStrictEqual(legacy, { a: 2.5, b: 2.5, apply: true });
});

test("emitZigzag: weightMm adds to pullCompMm exactly as when they were one number, so the legacy stream is byte-identical", () => {
  const [g] = twoStems(10);
  const one = satinplay.satinFromGeom(g, 0, 1, { spacingMm: 0.4, pxPerMm: 10, pullCompMm: 0.5 });
  const split = satinplay.satinFromGeom(g, 0, 1, { spacingMm: 0.4, pxPerMm: 10, pullCompMm: 0.2, weightMm: 0.3 });
  assert.deepStrictEqual(split, one);
  const thinOne = satinplay.satinFromGeom(g, 0, 1, { spacingMm: 0.4, pxPerMm: 10, pullCompMm: 0.05 });
  const thinSplit = satinplay.satinFromGeom(g, 0, 1, { spacingMm: 0.4, pxPerMm: 10, pullCompMm: 0.2, weightMm: -0.15 });
  assert.deepStrictEqual(thinSplit, thinOne);
});

// ---- Short stitches (Law 53; fine-lettering review item 6, 2026-09-03) ----
// On the inside of a bend the rail is shorter than the centerline, so its
// penetrations bunch under the station spacing. Every other crowded
// penetration is pulled back along the cross: 0.35 of it, at most 0.6 mm,
// never under the cross floor. The Python engine's _short_stitch_guard,
// mirrored with its numbers.

function bentColumn(rIn, rOut, ppm = 10) {
  // A 180-degree bend, inner radius rIn mm, outer rOut mm, sampled finely.
  const A = [], B = [];
  for (let i = 0; i <= 90; i++) {
    const th = Math.PI * i / 90;
    A.push({ x: rIn * ppm * Math.cos(th), y: rIn * ppm * Math.sin(th) });
    B.push({ x: rOut * ppm * Math.cos(th), y: rOut * ppm * Math.sin(th) });
  }
  return satinplay.columnGeom(A, B, [], 12);
}
// JS zigzag order alternates (A,B then B,A): station t has its rail-A point at
// index 2t + (t % 2) and its rail-B point at 2t + 1 - (t % 2).
function railsOf(pts) { const A = [], B = []; for (let t = 0; 2 * t + 1 < pts.length; t++) { A.push(pts[2 * t + (t % 2)]); B.push(pts[2 * t + 1 - (t % 2)]); } return { A, B }; }
const SS = { atMm: 0.3, pull: 0.35, maxMm: 0.6 };

test("short stitches: on a tight bend the inner rail's crowded penetrations are pulled back on every other station, never under 0.3 mm from the last, never under the floor, and the outer rail is untouched", () => {
  const g = bentColumn(1.0, 3.0);          // 2 mm wide; inner rail steps 0.2 mm per 0.4 mm station
  const base = { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 };
  const off = satinplay.satinFromGeom(g, 0, 1, base);
  const stats = { shortStitches: 0 };
  const on = satinplay.satinFromGeom(g, 0, 1, { ...base, shortStitch: { ...SS, stats } });
  assert.strictEqual(on.length, off.length, "the guard moves penetrations, it never adds or drops any");
  const ro = railsOf(off), rn = railsOf(on);
  let pulled = 0;
  for (let t = 0; t < rn.A.length; t++) {
    const dA = Math.hypot(rn.A[t].x - ro.A[t].x, rn.A[t].y - ro.A[t].y);
    assert.ok(Math.hypot(rn.B[t].x - ro.B[t].x, rn.B[t].y - ro.B[t].y) < 1e-9, `outer rail station ${t} must not move`);
    if (t % 2 === 0) { assert.ok(dA < 1e-9, `even station ${t} must not move`); continue; }
    if (dA > 1e-9) {
      pulled++;
      assert.ok(Math.abs(dA - 6.0) < 1e-6, `pull is the 0.6 mm cap on a 2 mm cross, got ${dA / 10} mm`);
      assert.ok(Math.hypot(rn.A[t].x - rn.A[t - 1].x, rn.A[t].y - rn.A[t - 1].y) >= 3.0, "the pulled penetration clears the previous hole by 0.3 mm");
    }
    assert.ok(Math.hypot(rn.A[t].x - rn.B[t].x, rn.A[t].y - rn.B[t].y) >= 5.0, "no cross ends up under the floor");
  }
  assert.ok(pulled >= 7, `a 6.3 mm centerline is 16 stations, 8 of them odd; expected them all pulled, got ${pulled}`);
  assert.strictEqual(stats.shortStitches, pulled);
});

test("short stitches: a straight column and a gentle bend are byte-identical with the guard on, and the legacy stream (no option) never sees it", () => {
  const straight = satinplay.columnGeom([{ x: 0, y: 0 }, { x: 0, y: 100 }], [{ x: 20, y: 0 }, { x: 20, y: 100 }], [], 12);
  const gentle = bentColumn(6.0, 8.0);   // inner rail steps 0.34 mm per station, over the 0.3 mm trip
  for (const g of [straight, gentle]) {
    const base = { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 };
    assert.deepStrictEqual(satinplay.satinFromGeom(g, 0, 1, { ...base, shortStitch: SS }), satinplay.satinFromGeom(g, 0, 1, base));
  }
  const legacy = satinplay.satinFromGeom(bentColumn(1.0, 3.0), 0, 1, { spacingMm: 0.4, pxPerMm: 10 });
  assert.deepStrictEqual(legacy, satinplay.satinFromGeom(bentColumn(1.0, 3.0), 0, 1, { spacingMm: 0.4, pxPerMm: 10, shortStitch: null }));
});

test("short stitches: the width gate — on a column near the cross floor the pull fades to nothing rather than making a stitch under it (Law 53)", () => {
  // 0.55 mm wide, bent tightly: the inner rail bunches, but a 0.35 pull
  // would take the cross to 0.36 mm, under the 0.5 floor. The bound keeps it
  // at 1.01 x the floor, so the pull is 0.045 mm instead of 0.19.
  const g = bentColumn(0.6, 1.15);
  const base = { spacingMm: 0.4, pxPerMm: 10, minCrossMm: 0.5 };
  const off = satinplay.satinFromGeom(g, 0, 1, base);
  const on = satinplay.satinFromGeom(g, 0, 1, { ...base, shortStitch: SS });
  assert.strictEqual(on.length, off.length);
  const rn = railsOf(on);
  for (let t = 0; t < rn.A.length; t++) {
    const cross = Math.hypot(rn.A[t].x - rn.B[t].x, rn.A[t].y - rn.B[t].y);
    assert.ok(cross >= 5.05 - 1e-6, `cross ${t} must stay at or above 1.01 x the floor, got ${cross / 10} mm`);
  }
  // And a column AT the floor is not touched at all.
  const atFloor = bentColumn(0.6, 1.1);
  assert.deepStrictEqual(satinplay.satinFromGeom(atFloor, 0, 1, { ...base, shortStitch: SS }), satinplay.satinFromGeom(atFloor, 0, 1, base));
});
