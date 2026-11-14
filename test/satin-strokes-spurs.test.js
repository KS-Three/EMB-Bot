const assert = require("node:assert");
const { test } = require("node:test");
const satin = require("../src/satin.js");
const digitize = require("../src/digitize.js");

// The browser's medial satin, 2026-11-13 (Kent's approval that day): what it
// does with a skeleton of many strokes, and with the spurs at a bar's end.

const S = 8; // px per mm
// A 2 mm spine with `n` 2 x 6 mm teeth on both sides, 5 mm apart: thin enough
// for the image lane to send it to satin (mean width 2 mm), branchy enough to
// have 3n strokes.
function fishbone(n) {
  const top = [], bot = [];
  for (let k = 0; k < n; k++) { const x = k * 5; top.push([x + 1.5, -1], [x + 1.5, -7], [x + 3.5, -7], [x + 3.5, -1]); }
  for (let k = n - 1; k >= 0; k--) { const x = k * 5; bot.push([x + 3.5, 1], [x + 3.5, 7], [x + 1.5, 7], [x + 1.5, 1]); }
  return [[0, -1]].concat(top, [[n * 5, -1], [n * 5, 1]], bot, [[0, 1]]).map(([x, y]) => ({ x: (x + 10) * S, y: (y + 20) * S }));
}
function inside(ring, p) {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if ((a.y > p.y) !== (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) c = !c;
  }
  return c;
}
function edgeDist(ring, p) {
  let m = Infinity;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i], b = ring[(i + 1) % ring.length], dx = b.x - a.x, dy = b.y - a.y, L = dx * dx + dy * dy;
    const t = L ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L)) : 0;
    m = Math.min(m, Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy));
  }
  return m;
}
// Sewn segments (a point entered by a jump starts a new run), in mm.
function sewn(pts) {
  const out = [];
  for (let i = 1; i < pts.length; i++) if (!pts[i].travel) out.push([pts[i - 1], pts[i]]);
  return out;
}

for (const n of [12, 16, 20]) {
  test(`a ${n}-tooth fishbone (${3 * n}+ strokes) is sewn whole: no stitch along the spine, none outside it`, () => {
    // Until 2026-11-13 ringToSpines kept the 24 longest strokes and dropped
    // the rest, and the satin raked across the gaps: 60.2, 80.2 and 100.2 mm
    // stitches, 87 to 122 outside the outline.
    const ring = fishbone(n);
    const pts = satin.medialSatin(ring, { spacingMm: 0.4, pxPerMm: S, smallShapes: true });
    let longest = 0, outside = 0;
    for (const [a, b] of sewn(pts)) {
      longest = Math.max(longest, Math.hypot(b.x - a.x, b.y - a.y) / S);
      const m = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
      if (!inside(ring, m) && edgeDist(ring, m) / S > 0.3) outside++;
    }
    assert.ok(longest < 3.5, `longest sewn stitch ${longest.toFixed(1)} mm`);
    assert.strictEqual(outside, 0, "stitches with their middle more than 0.3 mm outside");
  });
}

test("the 12-tooth fishbone through the image lane's builder is satin, and its longest stitch is a tooth's width", () => {
  const ring = fishbone(12), xs = ring.map((p) => p.x);
  const d = digitize.buildQualityDesign([{ rgb: [10, 90, 10], shapes: [{ outer: ring, holes: [] }] }],
    { pxPerMm: S, garment: { widthIn: 10, heightIn: 10 }, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / S, satinMaxWidthMm: 3, fillColumns: true });
  assert.ok(d.runs.some((r) => r.kind === "satin"));
  let longest = 0;
  for (let i = 1; i < d.stitches.length; i++) {
    const a = d.stitches[i - 1], b = d.stitches[i];
    if (a.type === "stitch" && b.type === "stitch") longest = Math.max(longest, Math.hypot(b.x - a.x, b.y - a.y) / 10);
  }
  assert.ok(longest < 3.5, `longest ${longest.toFixed(1)} mm (was 60.2)`);
});
