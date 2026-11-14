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

// ---- spurs: a bar is one column at every angle ----
// A bar `len` x `w` mm turned `deg` about its corner.
function bar(len, w, deg) {
  const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t);
  return [[0, 0], [len, 0], [len, w], [0, w]].map(([x, y]) => ({ x: 400 + (x * c - y * s) * S, y: 400 + (x * s + y * c) * S }));
}
test("a bar 1.5 to 2.9 mm wide, 6 to 25 mm long, is one stroke at every angle in 3 degree steps (720 bars)", () => {
  // Was 94 of these 720 in two or more strokes, with jumps between them: the
  // corner twigs at a turned bar's ends survived the spur pruning. A 6 x 2 mm
  // bar at 18 degrees sewed three strokes and two jumps, +32% thread.
  const split = [];
  for (const w of [1.5, 2, 2.5, 2.9]) for (const len of [6, 12, 25]) for (let deg = 0; deg < 180; deg += 3) {
    const pts = satin.medialSatin(bar(len, w, deg), { spacingMm: 0.4, pxPerMm: S, smallShapes: true });
    if (pts.some((p) => p.travel)) split.push(`${len}x${w}@${deg}`);
  }
  assert.deepStrictEqual(split, []);
});
test("an upright bar sews the bytes it sewed before the spur change (no twigs to prune)", () => {
  const crypto = require("node:crypto");
  const up = (len, w, deg) => [[0, 0], [len, 0], [len, w], [0, w]].map(([x, y]) => (deg ? [w - y, x] : [x, y])).map(([x, y]) => ({ x: x * S + 400, y: y * S + 400 }));
  // md5 of medialSatin's points on main before 2026-11-13 (x, y in 1/1000 px, travel)
  const PINS = {
    "6x2@0": "6881d43bddc83e60a2811b709f9aa770", "6x2@90": "e91107c599b450207225015773bda021",
    "12x3@0": "e46ef94eacbd61338220626e97c5dad3", "12x3@90": "61a5ba1d0afc9a426e5983d7eb01d965",
    "25x1.5@0": "eaae938d341c660449a16b1011902bb8", "25x1.5@90": "b2426485c0ab0b708cdee92ee368275d",
    "6x2.9@0": "bcd06103ca9b1a9aefeed692d7e1c666", "6x2.9@90": "46faa4baf4a2d9a7a47d62efe307847a",
  };
  for (const key of Object.keys(PINS)) {
    const [len, w, deg] = key.split(/[x@]/).map(Number);
    const pts = satin.medialSatin(up(len, w, deg), { spacingMm: 0.4, pxPerMm: S, smallShapes: true });
    const md5 = crypto.createHash("md5").update(JSON.stringify(pts.map((p) => [Math.round(p.x * 1000), Math.round(p.y * 1000), p.travel ? 1 : 0]))).digest("hex");
    assert.strictEqual(md5, PINS[key], key);
  }
});
