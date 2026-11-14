const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const digitize = require("../src/digitize.js");

// An auto-routed satin whose sewn stitch would be longer than the longest
// single stitch the engine writes (12.1 mm, dst.js MAX_DELTA) is a fill
// (2026-11-13, Kent: "Narrow it to the stitch limit"). Nothing narrower moves:
// satinMaxWidthMm and the mean-width test are as they were.

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

test("a stick with a 14 mm head (mean width 2.90 mm) is fill, not one satin with 14 mm stitches", () => {
  // Was satin: 30 crosses over 12.1 mm, the widest 14.2.
  const d = build(lollipop());
  assert.strictEqual(kinds(d).includes("satin"), false, `kinds ${kinds(d)}`);
  assert.ok(kinds(d).includes("fill"));
});
test("a 45 x 6 mm wedge (mean width 2.81 mm, crosses to about 6 mm) is still satin: under the stitch limit", () => {
  const d = build([{ x: 0, y: 0 }, { x: 45, y: 3 }, { x: 0, y: 6 }].map((p) => ({ x: (p.x + 5) * S, y: (p.y + 5) * S })));
  assert.ok(kinds(d).includes("satin"), `kinds ${kinds(d)}`);
  assert.ok(longestSatin(d) < 12.1, `${longestSatin(d).toFixed(2)} mm`);
});
test("a shape the user set to satin is satin however wide it is (tierOverride is a human's choice)", () => {
  assert.ok(kinds(build(lollipop(), { tierOverride: "satin" })).includes("satin"));
});
test("the shape tool's 6 mm dot, 6 mm square and 10 mm star stay satin and sew main's bytes", async () => {
  // md5 (tools/satin-small-shapes.mjs md5Of, default options) on origin/main
  // 0a0c3603, before this gate: the shapes the 2026-10-20 satinSmallShapes
  // ruling made satin.
  const MAIN = { dot6: "3d759edfae49a16d0e260543a881a033", square6: "6134bd14f5c08e60e8e18a01d2343f83", star5: "315abb071909fdc21a2c49b54c48a311" };
  const T = await import(pathToFileURL(path.join(__dirname, "..", "tools", "satin-small-shapes.mjs")).href);
  for (const [id, md5] of Object.entries(MAIN)) {
    const d = await T.buildShape(T.SHAPES.find((s) => s.id === id), true);
    assert.strictEqual(d._debug.nSatin, 1, id);
    assert.strictEqual(T.md5Of(d), md5, id);
  }
});
