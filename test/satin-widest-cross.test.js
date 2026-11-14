const assert = require("node:assert");
const { test } = require("node:test");
const digitize = require("../src/digitize.js");

// The auto-routed satin obeys `satinMaxWidthMm` at its WIDEST cross, not on
// its mean width (2026-11-13, Kent's approval that day; the catch accepted:
// "tapered shapes that sew as satin today become fill").

const S = 8; // px per mm
const build = (ring, extra) => {
  const xs = ring.map((p) => p.x);
  return digitize.buildQualityDesign([{ rgb: [10, 10, 10], shapes: [Object.assign({ outer: ring, holes: [] }, extra)] }],
    { pxPerMm: S, garment: { widthIn: 10, heightIn: 10 }, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / S, satinMaxWidthMm: 3 });
};
const kinds = (d) => [...new Set(d.runs.map((r) => r.kind))];
function longestSatin(d) {
  let m = 0;
  for (const r of d.runs) if (r.kind === "satin") for (let i = r.i0 + 1; i <= r.i1; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (b.type === "stitch") m = Math.max(m, Math.hypot(b.x - a.x, b.y - a.y) / 10);
  }
  return m;
}
// A 100 x 2 mm stick with a round head of radius 7 mm: mean width 2.90 mm.
function lollipop() {
  const hw = 1, r = 7, a0 = Math.asin(hw / r), cx = 100 + r * Math.cos(a0), pts = [{ x: 0, y: -hw }, { x: 100, y: -hw }];
  for (let k = 1; k < 64; k++) { const a = Math.PI + a0 + (k * (2 * Math.PI - 2 * a0)) / 64; pts.push({ x: cx + r * Math.cos(a), y: r * Math.sin(a) }); }
  pts.push({ x: 100, y: hw }, { x: 0, y: hw });
  return pts.map((p) => ({ x: (p.x + 5) * S, y: (p.y + 50) * S }));
}
const bar = (len, w) => [[0, 0], [len, 0], [len, w], [0, w]].map(([x, y]) => ({ x: (x + 5) * S, y: (y + 5) * S }));

test("a stick with a 14 mm head (mean width 2.90 mm) is fill, not one satin with 14 mm crosses", () => {
  // Was satin: 30 crosses over 12.1 mm, the widest 14.2.
  const d = build(lollipop());
  assert.deepStrictEqual(kinds(d).includes("satin"), false, `kinds ${kinds(d)}`);
  assert.ok(kinds(d).includes("fill"));
});
test("a 45 x 6 mm wedge (mean width 2.81 mm) is fill", () => {
  const d = build([{ x: 0, y: 0 }, { x: 45, y: 3 }, { x: 0, y: 6 }].map((p) => ({ x: (p.x + 5) * S, y: (p.y + 5) * S })));
  assert.deepStrictEqual(kinds(d).includes("satin"), false);
});
test("uniform bars up to 3.0 mm wide stay satin, and sew what they sewed", () => {
  for (const [len, w] of [[30, 2], [30, 3], [60, 3], [12, 2.5]]) {
    const d = build(bar(len, w));
    assert.ok(kinds(d).includes("satin"), `${len} x ${w}`);
    assert.ok(longestSatin(d) <= w + 0.5, `${len} x ${w}: ${longestSatin(d).toFixed(2)} mm`);
  }
});
test("a shape the user set to satin is satin however wide it is (tierOverride is a human's choice)", () => {
  const d = build(lollipop(), { tierOverride: "satin" });
  assert.ok(kinds(d).includes("satin"));
});
