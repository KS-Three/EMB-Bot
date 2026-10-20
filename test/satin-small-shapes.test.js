const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const satin = require("../src/satin.js");
const fabrics = require("../src/fabrics.js");

// SMALL SHAPES IN THE BROWSER'S MEDIAL SATIN (2026-10-20; MASTER_SCOPE
// defect 57's remainder, "Waiting on Kent" 26). Built behind
// `satinSmallShapes` OFF, and ON by default the same day (Kent's ruling: flip
// it whole); `satinSmallShapes: false` is the off arm, whose bytes the pins
// below are. The tool passes the option explicitly either way.
//
// What the skeleton satin did to a small shape on left chest, as the Studio's
// shape tool makes one (tools/satin-small-shapes.mjs measures every number):
//
//  - a 10 mm five-point star: five arms whose stations run in to the centre,
//    and from inside it a cross cast across an arm lands on another arm's
//    far wall -- the longest stitch is 8.0 mm, the centre is sewn five times;
//  - a 10 x 2 mm stroke with round ends: the last cross stands on the apex as
//    wide as the stroke a pitch back, 0.2 mm outside the curve on each side;
//  - a 1.5 mm square: two skeleton pixels, which happen to lie level, so the
//    column is level -- a 6 mm square's two lie on the diagonal (7.8 mm
//    stitches);
//  - a 1 mm dot: two skeleton pixels on the diagonal, three crosses as wide
//    as the dot whose ends stand 0.16 mm outside it; a 6 mm dot has no
//    skeleton at all and takes the outline-split column, 5.0 mm tall.
//
// ON: a cross's end outside the shape is pulled onto the outline (the cap);
// a shape with no stroke to the engine's own floor is sewn as the smallest
// column it already uses, along the ring's principal axis; a junction of
// three or more arms is cut at its inscribed disc and sewn once as one zone.
// OFF must not move a byte: the md5 pins below were taken on `main` before
// the option existed.

const tool = () => import(pathToFileURL(path.join(__dirname, "..", "tools", "satin-small-shapes.mjs")).href);
const GARMENT = "left_chest";
const pullCompMm = fabrics.getFabric(fabrics.fabricForGarment(GARMENT)).pullCompMm || 0;
// a needle outside the drawn shape by the preset's pull compensation (a side) and the file's 0.1 mm rounding
const OUT_ALLOWED_MM = pullCompMm / 2 + 0.05;

const spec = async (id) => { const T = await tool(); return T.SHAPES.find((s) => s.id === id) || T.WORDS.find((s) => s.id === id); };
// `ties`, `fillStagger` and `dedupeHoles` went ON by default on 2026-10-20
// (Kent). This file's pins and counts were taken with them OFF, and they are
// not its subject, so every design here is built with them OFF.
const TRIO_OFF = { ties: false, fillStagger: false, dedupeHoles: false };
const shape = async (id, on) => { const T = await tool(); return T.buildShape(await spec(id), on, TRIO_OFF); };
const word = async (id, on) => { const T = await tool(); return T.buildWord(await spec(id), on, TRIO_OFF); };
const longestStitchMm = (d) => {
  let m = 0;
  for (let i = 1; i < d.stitches.length; i++) if (d.stitches[i].type === "stitch") m = Math.max(m, Math.hypot(d.stitches[i].x - d.stitches[i - 1].x, d.stitches[i].y - d.stitches[i - 1].y) / 10);
  return m;
};

// ---- OFF: byte-identical to main of 2026-10-20 (0eb5e02) ------------------
const PINS = {
  star5: "52ec3113edbb326b446cb6fa7f393108",
  round: "92d9d1fec2dc684d2430dd75d655d796",
  square: "795d20f7a8ebba5d7e7d5c660492803d",
  dot: "4aeeb8a9eb16656b49c9e60712ea9d1f",
  word_barstitch: "5cb7310b4644edb28c192dfcd60d46c8",
  word_venezia: "f4f5e3f98be5396c7814d9b777c7622b",
};

test("OFF: the four shapes and two library-font words sew the bytes main sewed", async () => {
  const T = await tool();
  for (const id of ["star5", "round", "square", "dot"]) assert.strictEqual(T.md5Of(await shape(id, false)), PINS[id], id);
  for (const id of ["word_barstitch", "word_venezia"]) assert.strictEqual(T.md5Of(await word(id, false)), PINS[id], id);
});

test("a library-font word does not read the option: lettering never reaches medialSatin", async () => {
  const T = await tool();
  for (const id of ["word_barstitch", "word_venezia"]) assert.strictEqual(T.md5Of(await word(id, true)), PINS[id], id);
});

// ---- ON: the star's centre is one zone ---------------------------------------
test("ON: a 10 mm five-point star casts no stitch arm to arm, and its centre is sewn once", async () => {
  const off = await shape("star5", false), on = await shape("star5", true);
  assert.strictEqual(on._debug.nSatin, 1);
  // OFF's longest stitch runs from one arm's wall to another's across the centre
  assert.ok(longestStitchMm(off) > 7, `off: ${longestStitchMm(off).toFixed(2)} mm`);
  // ON no stitch is longer than the centre pentagon is wide (its circumdiameter, 2 x 0.45 x 5 mm)
  assert.ok(longestStitchMm(on) < 4.5 + 0.3, `on: ${longestStitchMm(on).toFixed(2)} mm`);
  // crosses through the centre: inside the disc inscribed in the pentagon, radius 0.45 x 5 x cos 36
  const o = on.shapeOutlines[0].points, cx = o.reduce((a, p) => a + p[0], 0) / o.length, cy = o.reduce((a, p) => a + p[1], 0) / o.length;
  const rIn = 0.45 * 5 * Math.cos(Math.PI / 5);
  const throughCentre = (d) => {
    let n = 0;
    for (let i = 1; i < d.stitches.length; i++) {
      const a = d.stitches[i - 1], b = d.stitches[i];
      if (b.type !== "stitch" || Math.hypot(b.x - a.x, b.y - a.y) < 20) continue;   // a cross, not a connector
      if (Math.hypot((a.x + b.x) / 20 - cx, (a.y + b.y) / 20 - cy) < rIn) n++;
    }
    return n;
  };
  assert.ok(throughCentre(on) > 0, "the zone is sewn");
  assert.ok(throughCentre(on) * 2 < throughCentre(off), `crosses through the centre: off ${throughCentre(off)}, on ${throughCentre(on)}`);
  // five arms and the zone: six columns, five needle-up moves between them
  const satinRun = on.runs.find((r) => r.kind === "satin");
  let jumps = 0;
  for (let i = satinRun.i0 + 1; i <= satinRun.i1; i++) if (on.stitches[i].type === "jump") jumps++;
  assert.strictEqual(jumps, 5);
  assert.ok((await tool()).measure(on).farOutMm <= OUT_ALLOWED_MM + 1e-9);
});

test("ON: a T drawn and set to satin sews no stitch along its bar from the stem", async () => {
  const off = await shape("tee", false), on = await shape("tee", true);
  assert.ok(longestStitchMm(off) > 10, `off: ${longestStitchMm(off).toFixed(2)} mm, the bar's length`);
  assert.ok(longestStitchMm(on) < 3, `on: ${longestStitchMm(on).toFixed(2)} mm on arms 2 mm wide`);
});

// ---- ON: the cap ---------------------------------------------------------------
test("ON: a round end's last cross is a chord of the cap, and the stroke keeps its length to within a thread", async () => {
  const T = await tool();
  const off = await shape("round", false), on = await shape("round", true);
  assert.ok(T.measure(off).farOutMm > OUT_ALLOWED_MM + 0.1, `off: ${T.measure(off).farOutMm.toFixed(2)} mm outside`);
  assert.ok(T.measure(on).farOutMm <= OUT_ALLOWED_MM + 1e-9, `on: ${T.measure(on).farOutMm.toFixed(2)} mm outside`);
  assert.ok(on.widthMM >= 10 - 2 * 0.4 && on.widthMM <= 10 + 0.1, `sewn ${on.widthMM.toFixed(1)} mm of a 10 mm stroke`);
  assert.ok(longestStitchMm(on) <= 2 + pullCompMm + 0.1 + 1e-9, `longest ${longestStitchMm(on).toFixed(2)} mm`);
  assert.ok(T.measure(on).cover >= T.measure(off).cover - 0.01, "no cover is lost at the ends");
});

// ---- ON: the smallest column -------------------------------------------------
test("ON: a 1.5 mm square was already the smallest column: the same bytes", async () => {
  const T = await tool();
  assert.strictEqual(T.md5Of(await shape("square", true)), PINS.square);
});

test("ON: a 1 mm dot is three crosses, none outside it, and is covered", async () => {
  const T = await tool();
  const on = await shape("dot", true), m = T.measure(on);
  assert.strictEqual(m.satinPts, 6, "three crosses");
  assert.ok(m.farOutMm <= OUT_ALLOWED_MM + 1e-9, `${m.farOutMm.toFixed(2)} mm outside`);
  assert.ok(m.cover >= 0.99, `${(m.cover * 100).toFixed(0)}% under thread (off: ${(T.measure(await shape("dot", false)).cover * 100).toFixed(0)}%)`);
});

test("ON: a 6 mm square is a level column the height of the square, not a diagonal one", async () => {
  const off = await shape("square6", false), on = await shape("square6", true);
  assert.ok(longestStitchMm(off) > 7, `off: ${longestStitchMm(off).toFixed(2)} mm on a 6 mm square`);
  for (let i = 1; i < on.stitches.length; i++) {
    const a = on.stitches[i - 1], b = on.stitches[i];
    if (b.type !== "stitch" || Math.hypot(b.x - a.x, b.y - a.y) < 30) continue;   // a cross
    assert.ok(Math.abs(b.x - a.x) <= 1, `a cross leans ${((b.x - a.x) / 10).toFixed(2)} mm`);
  }
  assert.ok(on.heightMM >= 6 && on.heightMM <= 6 + pullCompMm + 0.1 + 1e-9, `sewn ${on.heightMM.toFixed(1)} mm tall`);
  assert.ok(on.stitchCount < off.stitchCount);
});

test("ON: a 6 mm dot is sewn its full height, not 12% in from each end", async () => {
  const off = await shape("dot6", false), on = await shape("dot6", true);
  assert.ok(off.heightMM < 5.5, `off: ${off.heightMM.toFixed(1)} mm tall`);
  assert.ok(on.heightMM >= 6 && on.heightMM <= 6 + pullCompMm + 0.1 + 1e-9, `on: ${on.heightMM.toFixed(1)} mm tall`);
});

// ---- the pieces ----------------------------------------------------------------
test("ringAxis: a square and a circle have no axis and lie level; a rectangle's is its length", () => {
  const sq = [{ x: 10, y: 10 }, { x: 20, y: 10 }, { x: 20, y: 20 }, { x: 10, y: 20 }];
  const a = satin.ringAxis(sq);
  assert.ok(Math.abs(a.x - 15) < 1e-9 && Math.abs(a.y - 15) < 1e-9);
  assert.ok(Math.abs(a.uy) < 1e-9 && a.ux > 0, "level");
  const circle = Array.from({ length: 32 }, (_, i) => ({ x: 5 + 3 * Math.cos(i * Math.PI / 16), y: -2 + 3 * Math.sin(i * Math.PI / 16) }));
  const c = satin.ringAxis(circle);
  assert.ok(Math.abs(c.uy) < 1e-9, "level");
  const tall = [{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 2, y: 8 }, { x: 0, y: 8 }];
  assert.ok(Math.abs(Math.abs(satin.ringAxis(tall).uy) - 1) < 1e-9, "upright");
  const deg = 30, co = Math.cos(deg * Math.PI / 180), si = Math.sin(deg * Math.PI / 180);
  const turned = [[-8, -1], [8, -1], [8, 1], [-8, 1]].map(([x, y]) => ({ x: x * co - y * si, y: x * si + y * co }));
  const t = satin.ringAxis(turned);
  assert.ok(Math.abs(Math.atan2(t.uy, t.ux) * 180 / Math.PI - deg) < 1e-6, `turned ${deg}: axis at ${(Math.atan2(t.uy, t.ux) * 180 / Math.PI).toFixed(2)}`);
});

test("cutSpineAtDisc cuts a spine at the disc's edge from either end, and swallows one inside it", () => {
  const line = [{ x: 0, y: 0 }, { x: 4, y: 0 }, { x: 10, y: 0 }];
  const fromStart = satin.cutSpineAtDisc(line, false, { x: 0, y: 0, r: 3 });
  assert.deepStrictEqual(fromStart.map((p) => [p.x, p.y]), [[3, 0], [4, 0], [10, 0]]);
  const fromEnd = satin.cutSpineAtDisc(line, true, { x: 10, y: 0, r: 3 });
  assert.deepStrictEqual(fromEnd.map((p) => [p.x, p.y]), [[0, 0], [4, 0], [7, 0]]);
  assert.strictEqual(satin.cutSpineAtDisc(line, false, { x: 5, y: 0, r: 20 }), null);
  assert.strictEqual(satin.cutSpineAtDisc(line, false, { x: -10, y: 0, r: 3 }), line, "a spine that starts outside is left alone");
});

test("capToContours pulls a point outside the shape onto its outline and leaves one inside alone", () => {
  const sq = [[{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 }]];
  assert.deepStrictEqual(satin.capToContours(sq, { x: 2, y: 0.5 }), { x: 1, y: 0.5 });
  const inside = { x: 0.3, y: 0.6 };
  assert.strictEqual(satin.capToContours(sq, inside), inside);
});

test("smallestColumn on a level 6 x 2 bar runs its length with crosses its height, end to end", () => {
  const bar = [{ x: 0, y: 0 }, { x: 36, y: 0 }, { x: 36, y: 12 }, { x: 0, y: 12 }];   // 6 x 2 mm at 6 px/mm
  const pts = satin.smallestColumn([bar], bar, { spacingMm: 0.4, pxPerMm: 6, pullCompMm: 0 });
  const xs = [];
  for (let i = 0; i + 1 < pts.length; i += 2) {
    const a = pts[i], b = pts[i + 1];
    assert.ok(Math.abs(a.x - b.x) < 1e-6 && Math.abs(Math.abs(a.y - b.y) - 12) < 1e-6, `a cross ${Math.hypot(a.x - b.x, a.y - b.y).toFixed(2)} px, leaning ${Math.abs(a.x - b.x).toFixed(2)}`);
    xs.push(a.x);
  }
  assert.ok(Math.min(...xs) < 1e-6 && Math.max(...xs) > 36 - 1e-6, "the first and last cross stand on the bar's ends");
  for (const p of pts) assert.ok(p.x >= -1e-6 && p.x <= 36 + 1e-6 && p.y >= -1e-6 && p.y <= 12 + 1e-6, "nothing outside the bar");
});
