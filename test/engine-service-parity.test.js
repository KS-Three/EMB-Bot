// Browser engine vs digitizer service on the same simple shapes (2026-10-08
// parity sweep; the full divergence table is in that PR's body). What the
// sweep found that is a plain bug and not a constant choice is pinned here.
const assert = require("node:assert");
const { test } = require("node:test");
const S = require("../src/satin.js");

const PX = 10; // px per mm
const bar = (L, w) => [[0, 0], [L, 0], [L, w], [0, w]].map(([x, y]) => ({ x: x * PX, y: y * PX }));

// A plain 30 x 2.5 mm bar through medialSatin: the skeleton it rails from
// traces the bar's OUTLINE, not its centre line (spine y spans 0.06..2.48 mm
// on a 2.5 mm bar), so the column ends in stitches up to 30 mm long and
// lands up to 0.8 mm outside the drawn edge. The service's satin on the same
// polygon has no stitch over 3.1 mm. Every axis-aligned bar tried (10, 20,
// 30 mm long; 2.5 and 5 mm wide) does the same. Not fixed in that PR: a
// distance clamp on the rail rays hides it only by collapsing the column,
// because the spine itself is wrong — the root is in ringToSpines.
test("medialSatin on a plain bar: no stitch longer than the bar is wide", { todo: "skeleton traces the outline of a rectangle (ringToSpines)" }, () => {
  const pts = S.medialSatin(bar(30, 2.5), { spacingMm: 0.4, pxPerMm: PX, pullCompMm: 0.3 });
  let longest = 0;
  for (let i = 1; i < pts.length; i++) {
    if (pts[i].travel) continue;
    longest = Math.max(longest, Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y) / PX);
  }
  assert.ok(longest <= 2.5 + 0.3 + 0.1, `longest stitch ${longest.toFixed(2)} mm on a 2.5 mm bar`);
});

// The one place the two lanes already agree on a satin's width, held so the
// table's "JS: pullCompMm in TOTAL" row stays true until Kent rules on it.
test("medialSatin widens a column by pullCompMm in total (half per rail)", () => {
  const a = S.medialSatin(bar(30, 2.5), { spacingMm: 0.4, pxPerMm: PX, pullCompMm: 0 });
  const b = S.medialSatin(bar(30, 2.5), { spacingMm: 0.4, pxPerMm: PX, pullCompMm: 0.6 });
  const mid = (pts) => { const m = pts.filter((p) => Math.abs(p.x / PX - 15) < 2); return (Math.max(...m.map((p) => p.y)) - Math.min(...m.map((p) => p.y))) / PX; };
  assert.ok(Math.abs((mid(b) - mid(a)) - 0.6) < 0.05, `grew ${(mid(b) - mid(a)).toFixed(3)} mm`);
});
