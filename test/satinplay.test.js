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
