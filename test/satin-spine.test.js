const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");
const digitize = require("../src/digitize.js");
const garments = require("../src/garments.js");
const fabrics = require("../src/fabrics.js");

// THE SPINE OF A BAR (2026-10-04).
//
// `thin` never deletes a pixel on the grid's own border, and `ringToSpines`
// laid the shape against the grid's top and left: no spare cell there. So the
// top row and the left column of every shape were never thinned, and a plain
// bar's "skeleton" was its top edge and its left edge, an L. The crosses were
// cast from it to the outline and so came out right along the top edge, and
// along the left edge they turned: the last of them ran the length of the
// bar. 185 of the 276 sharp-cornered satin bars the shape tool makes on left
// chest carried a stitch as long as the bar.
//
// With the spare cell the skeleton is the centre line, and a centre line
// stops short of a bar's end by about half the bar's height. So a free end is
// run out to the outline, along the spine's own direction.

// medialSatin's points come in pairs, one cross each.
function crossesOf(pts) {
  const out = [];
  for (let i = 0; i + 1 < pts.length; i += 2) {
    const a = pts[i], b = pts[i + 1];
    out.push({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, dx: Math.abs(a.x - b.x), dy: Math.abs(a.y - b.y), len: Math.hypot(a.x - b.x, a.y - b.y) });
  }
  return out;
}
// 30 x 3 mm at 6 px per mm, the scale the shape tool draws at; and one stood on end.
const bar = [{ x: 210, y: 191 }, { x: 390, y: 191 }, { x: 390, y: 209 }, { x: 210, y: 209 }];
const post = bar.map((p) => ({ x: p.y, y: p.x }));
const OPTS = { spacingMm: 0.4, pxPerMm: 6, pullCompMm: 0 };

test("every cross of a bar runs across it: none along it", () => {
  const crosses = crossesOf(satin.medialSatin(bar, OPTS));
  assert.ok(crosses.length > 60, `${crosses.length} crosses on a 30 mm bar at 0.4 mm`);
  const along = crosses.filter((c) => c.dx > 1);
  assert.deepStrictEqual(along.map((c) => `${(c.len / 6).toFixed(1)} mm long at x ${((c.x - 210) / 6).toFixed(1)} mm`), [],
    "a cross of a level bar is upright");
  for (const c of crosses) assert.ok(Math.abs(c.len - 18) < 0.5, `a cross is the bar's height, 18 px: got ${c.len.toFixed(1)}`);
});

test("the same bar stood on end is sewn the same way: the left edge is not a spine either", () => {
  const crosses = crossesOf(satin.medialSatin(post, OPTS));
  assert.deepStrictEqual(crosses.filter((c) => c.dy > 1).length, 0, "a cross of an upright bar is level");
  for (const c of crosses) assert.ok(Math.abs(c.len - 18) < 0.5, `got ${c.len.toFixed(1)}`);
});

test("a bar's column runs from one end of the bar to the other", () => {
  // The centre line of a 180 x 18 px bar stops about 9 px short of each end,
  // and the free-end trim takes a little more. Run out to the outline, the
  // first and last cross stand on the bar's two ends.
  const xs = crossesOf(satin.medialSatin(bar, OPTS)).map((c) => c.x).sort((p, q) => p - q);
  assert.ok(xs[0] - 210 < 0.5, `the first cross is ${((xs[0] - 210) / 6).toFixed(2)} mm in from the bar's end`);
  assert.ok(390 - xs[xs.length - 1] < 0.5, `the last cross is ${((390 - xs[xs.length - 1]) / 6).toFixed(2)} mm in from the bar's end`);
});

// ---- through the Studio's own modules --------------------------------------
const lib = (name) => import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", name)).href);
async function studioShape(kind, params, sizeMm, garmentId = "left_chest") {
  const { shapePresetPoints } = await lib("shapePresets.js");
  const { shapesToRegions } = await lib("manualShapes.js");
  const { regions, pxPerMm } = shapesToRegions([
    { id: "shape", points: shapePresetPoints(kind, params, sizeMm), curves: {}, stitchType: "auto", colorRgb: [20, 20, 20], angleDeg: null },
  ]);
  return digitize.buildQualityDesign(regions, {
    garment: garments.getGarment(garmentId), fabric: fabrics.getFabric(fabrics.fabricForGarment(garmentId)), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: sizeMm, offsetXMm: 0, offsetYMm: 0,
  });
}
const longestStitchMm = (d) => {
  let m = 0;
  for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i].type === "stitch") m = Math.max(m, Math.hypot(d.stitches[i].x - d.stitches[i - 1].x, d.stitches[i].y - d.stitches[i - 1].y) / 10);
  return m;
};

test("a 30 x 3 mm bar off the shape tool is sewn 30 x 3 mm, and no stitch is longer than it is tall", async () => {
  // Before: reported 30.3 x 4.2 mm, with one stitch 30.2 mm long. Pique's
  // pull compensation is 0.3 mm and widens the crosses by that, no more
  // (0.15 mm a side, each rounded to the file's 0.1 mm: 3.4 mm sewn).
  const d = await studioShape("rect", { heightMm: 3, cornerRadiusMm: 0 }, 30);
  assert.strictEqual(d._debug.nSatin, 1);
  assert.ok(longestStitchMm(d) < 3.5, `longest stitch ${longestStitchMm(d).toFixed(1)} mm on a bar 3 mm tall`);
  assert.ok(Math.abs(d.widthMM - 30) < 0.15, `sewn ${d.widthMM.toFixed(1)} mm long`);
  assert.ok(Math.abs(d.heightMM - 3.3) < 0.15, `sewn ${d.heightMM.toFixed(1)} mm tall`);
});

test("a round-ended bar is sewn end to end too, with no stitch longer than it is tall", async () => {
  // Before: 30.2 x 3.6 mm with a 30.2 mm stitch at this size, 15.1 mm for 16.
  for (const size of [16, 30]) {
    const d = await studioShape("rect", { heightMm: 3, cornerRadiusMm: 1.5 }, size);
    assert.ok(longestStitchMm(d) < 3.5, `${size} mm: longest stitch ${longestStitchMm(d).toFixed(1)} mm`);
    assert.ok(Math.abs(d.widthMM - size) < 0.15, `${size} mm: sewn ${d.widthMM.toFixed(1)} mm long`);
  }
});

// ---- a curved stroke, and the walk that traces it -------------------------
//
// The two rules above were measured on the shape tool's shapes and on logos,
// and an independent re-measure then drew a C by hand and set it to satin:
// 447 stitches on main, 6,047 with the two rules, the mouth of the C sewn
// solid. Two causes. `skeletonEdges` stepped into the corner filler of a
// staircase and ended its edge there, and the pixels it left were walked as
// "rings" and closed with a chord across the mouth (the wrong skeleton had
// been hiding it: its border row and column gave every curve real nodes).
// And a cross cast from an end run out ONTO the outline can leave the stroke
// through its end and land on the far side of the mouth.

test("skeletonEdges walks a staircase past its corner filler: one edge, end to end", () => {
  // (4,2) is the filler: it touches (4,1), (5,1) and (3,2) and leads nowhere.
  // The walk from (6,1) took it before (2,3), came back to (6,1) the way it
  // went, and the stroke was laid twice: once out and back, once in full
  // from the other end.
  const rows = ["........", "....###.", "...##...", ".##.....", "........"];
  const h = rows.length, w = rows[0].length, mask = new Uint8Array(w * h);
  rows.forEach((row, y) => { for (let x = 0; x < w; x++) if (row[x] === "#") mask[y * w + x] = 1; });
  const edges = satin.skeletonEdges(mask, w, h);
  assert.deepStrictEqual(edges.map((e) => e.pts), [[[6, 1], [5, 1], [4, 1], [3, 2], [2, 3], [1, 3]]]);
  assert.ok(edges[0].freeStart && edges[0].freeEnd && !edges[0].closed);
});

// An arc `w` mm wide whose outer edge has radius `R`, sweeping `sweep` degrees,
// the mouth of the C turned to `turn`: drawn by hand and set to satin.
async function studioArc(R, w, sweep, turn) {
  const { shapesToRegions, PX_PER_MM, CANVAS_W, CANVAS_H } = await lib("manualShapes.js");
  const a0 = turn + (360 - sweep) / 2, a1 = turn + 360 - (360 - sweep) / 2, n = Math.max(12, Math.round(sweep / 6));
  const arc = (r, p, q) => Array.from({ length: n + 1 }, (_, i) => {
    const a = (p + (q - p) * i / n) * Math.PI / 180;
    return { x: CANVAS_W / 2 + PX_PER_MM * r * Math.cos(a), y: CANVAS_H / 2 + PX_PER_MM * r * Math.sin(a) };
  });
  const points = [...arc(R, a0, a1), ...arc(R - w, a1, a0)];
  const xs = points.map((p) => p.x);
  const { regions, pxPerMm } = shapesToRegions([{ id: "shape", points, curves: {}, stitchType: "satin", colorRgb: [20, 20, 20], angleDeg: null }]);
  return digitize.buildQualityDesign(regions, {
    garment: garments.getGarment("left_chest"), fabric: fabrics.getFabric(fabrics.fabricForGarment("left_chest")), pxPerMm,
    darkOnTop: false, underlay: true, targetWidthMm: (Math.max(...xs) - Math.min(...xs)) / pxPerMm, offsetXMm: 0, offsetYMm: 0,
  });
}

test("a C drawn by hand and set to satin is one column, end to end: nothing is sewn across its mouth", async () => {
  for (const [R, w, sweep, turn] of [[12, 3, 330, 270], [12, 3, 270, 0], [8, 3, 300, 315]]) {
    const d = await studioArc(R, w, sweep, turn), name = `${sweep} degrees of radius ${R}`;
    assert.strictEqual(d._debug.nSatin, 1);
    // one cross every 0.4 mm of its centre line is two stitch records, and an underlay under them
    const centreLineMm = (R - w / 2) * sweep * Math.PI / 180;
    assert.ok(d.stitchCount < 1.5 * 2 * centreLineMm / 0.4, `${name}: ${d.stitchCount} stitches on ${centreLineMm.toFixed(0)} mm of stroke`);
    // a cross is the stroke's width and its pull compensation; a stitch much longer does not lie across the stroke
    assert.ok(longestStitchMm(d) < w + 2, `${name}: a stitch ${longestStitchMm(d).toFixed(1)} mm long on a stroke ${w} mm wide`);
  }
});

// ---- thinning, on the diagonal --------------------------------------------
//
// The second re-measure turned an L exactly 45 degrees: one arm bare. `thin`
// was textbook Zhang-Suen, which deletes the end pixel of a line two pixels
// wide on the anti-diagonal, then the next, and so eats the whole line. The
// grid's border pixels had been anchoring it.

// a bar `wMm` x `lMm` at 6 px per mm, turned about (300, 300)
function turnedBar(wMm, lMm, deg) {
  const c = Math.cos(deg * Math.PI / 180), s = Math.sin(deg * Math.PI / 180), w = wMm * 6, l = lMm * 6;
  return [[-l / 2, -w / 2], [l / 2, -w / 2], [l / 2, w / 2], [-l / 2, w / 2]].map(([x, y]) => ({ x: 300 + x * c - y * s, y: 300 + x * s + y * c }));
}
// the skeleton of a ring, on the grid `ringToSpines` lays it on (its scale, a spare cell on every side)
function skeletonOf(ring) {
  const xs = ring.map((p) => p.x), ys = ring.map((p) => p.y);
  const scale = Math.min(1.5, 260 / Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)));
  const minX = Math.min(...xs) - 1 / scale, minY = Math.min(...ys) - 1 / scale;
  const w = Math.ceil((Math.max(...xs) - minX) * scale) + 3, h = Math.ceil((Math.max(...ys) - minY) * scale) + 3;
  const mask = satin.thin(satin.rasterize([ring], scale, minX, minY, w, h), w, h);
  const on = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (mask[y * w + x]) on.push([x, y]);
  const neighbours = (p) => on.filter((q) => q !== p && Math.abs(q[0] - p[0]) <= 1 && Math.abs(q[1] - p[1]) <= 1).length;
  return { on, neighbours, scale };
}

test("thin leaves a bar on either diagonal its skeleton: it does not eat the line from its end", () => {
  for (const deg of [45, 135]) {
    const { on, scale } = skeletonOf(turnedBar(2, 30, deg));
    const xs = on.map((p) => p[0]), span = on.length ? (Math.max(...xs) - Math.min(...xs)) / scale : 0;
    // a 180 px bar on a diagonal spans 127 px across, less a bar's width at its two ends
    assert.ok(span > 110, `turned ${deg}: the skeleton spans ${span.toFixed(0)} px across, ${on.length} pixels in all`);
  }
});

test("thin leaves a skeleton one pixel wide: the corners of its staircases are taken out", () => {
  // A pixel of a line has two neighbours; a staircase corner has three or
  // four. What is left with more than two is the fork at each end of the
  // bar, where the skeleton runs into its corners (the spur pass takes
  // those): a handful. With the corners kept, a bar turned 20 degrees had
  // 287 such pixels in 323.
  for (const deg of [0, 20, 45, 70, 135]) {
    const { on, neighbours } = skeletonOf(turnedBar(2, 30, deg));
    const thick = on.filter((p) => neighbours(p) > 2).length;
    assert.ok(thick * 20 < on.length, `turned ${deg}: ${thick} of ${on.length} skeleton pixels touch more than two others`);
  }
});

test("an L turned exactly 45 degrees is sewn along both arms", () => {
  // 15 x 15 mm, arms 1 mm wide at 12 px per mm, as the re-measure drew it
  const c = Math.SQRT1_2, PX = 6, a = 2, s = 30;
  const turned = [[0, 0], [a, 0], [a, s - a], [s, s - a], [s, s], [0, s]].map(([x, y]) => [x * c - y * c, x * c + y * c]);
  const ring = turned.map(([x, y]) => ({ x: 300 + x * PX, y: 200 + y * PX }));
  const pts = satin.medialSatin(ring, { spacingMm: 0.4, pxPerMm: 12, pullCompMm: 0 });
  const centres = [];
  for (let i = 0; i + 1 < pts.length; i += 2) centres.push({ x: (pts[i].x + pts[i + 1].x) / 2, y: (pts[i].y + pts[i + 1].y) / 2 });
  // the middle of each arm, on its centre line
  const mid = (p, q) => ({ x: 300 + (p[0] + q[0]) / 2 * PX, y: 200 + (p[1] + q[1]) / 2 * PX });
  const arms = { "the arm from the corner up": mid(turned[0], turned[2]), "the arm along the foot": mid(turned[3], turned[5]) };
  for (const [name, m] of Object.entries(arms)) {
    const nearest = Math.min(...centres.map((q) => Math.hypot(q.x - m.x, q.y - m.y)));
    assert.ok(nearest < 6, `${name}: the nearest cross is ${(nearest / 12).toFixed(1)} mm from its middle`);
  }
});

test("a fill is not touched: the shape tool's default rectangle sews what it sewed", async () => {
  // 50 x 30 mm is a fill; medialSatin never sees it. Counted on f887e27d.
  const d = await studioShape("rect", { heightMm: 30, cornerRadiusMm: 0 }, 50);
  assert.strictEqual(d._debug.nFill, 1);
  assert.strictEqual(d.stitchCount, 2935);
});
