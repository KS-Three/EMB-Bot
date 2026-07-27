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
