// "Join touching strokes" (pen + auto-branch spec 2026-11-13 §3 and §4).
//
// With the drawing's tick on, hand-drawn Columns of one colour that touch
// arrive as ONE region whose shapes carry `sewAs.join`, and the engine sews
// them as one needle-down path: satinfont's routeColumnGroup lays the travel
// first, along a column's own spine, and the satin over it. Built OFF (Kent,
// 2026-11-13): with the tick off nothing here is read.
//
// The measuring is tools/join-strokes.mjs (FIXTURES, build, measure): the
// bars below are on the stitches as emitted.
const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const SF = require("../src/satinfont.js");
const DG = require("../src/digitize.js");
const FAB = require("../src/fabrics.js");

const tool = () => import(pathToFileURL(path.join(__dirname, "..", "tools", "join-strokes.mjs")).href);
const studio = () => import(pathToFileURL(path.join(__dirname, "..", "app", "src", "lib", "manualShapes.js")).href);

const P = (x, y) => ({ x, y });
// A straight column's rails, by hand: spine a -> b, `w` wide.
function rails(a, b, w) {
  const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy), nx = (-dy / L) * (w / 2), ny = (dx / L) * (w / 2);
  const at = (t, s) => P(a.x + dx * t + nx * s, a.y + dy * t + ny * s);
  return { railA: [at(0, 1), at(0.5, 1), at(1, 1)], railB: [at(0, -1), at(0.5, -1), at(1, -1)] };
}

// ---- what touches -------------------------------------------------------------
test("joinComponents: an end inside another column's body joins; one outside it does not", () => {
  const bar = rails(P(0, 0), P(300, 0), 24);          // body: 12 either side of y = 0
  const inside = rails(P(150, 11), P(150, 200), 24);  // end 11 from the spine
  const outside = rails(P(150, 13), P(150, 200), 24); // end 13 from the spine
  assert.deepStrictEqual(SF.joinComponents([bar, inside]), [[0, 1]]);
  assert.deepStrictEqual(SF.joinComponents([bar, outside]), []);
});

test("joinComponents: the test is each column's OWN half width, not the group's widest", () => {
  // A 6 px stroke's end 9 px off a 6 px bar's spine: outside its 3 px half
  // width, however wide the third stroke in the drawing is.
  const thin = rails(P(0, 0), P(300, 0), 6);
  const near = rails(P(150, 9), P(150, 200), 6);
  const wide = rails(P(0, 300), P(300, 300), 48);
  assert.deepStrictEqual(SF.joinComponents([thin, near, wide]), []);
});

test("joinComponents: spines that cross join, though neither has an end there", () => {
  const a = rails(P(0, 0), P(300, 200), 6), b = rails(P(0, 200), P(300, 0), 6);
  assert.deepStrictEqual(SF.joinComponents([a, b]), [[0, 1]]);
});

test("joinComponents: a stem landing in the last few percent of a long bar still joins", () => {
  // 4% from the bar's end: the glyph rule (no cut outside 6%..94%) would
  // leave these two unconnected.
  const bar = rails(P(0, 0), P(1000, 0), 6), stem = rails(P(960, 0), P(960, 200), 6);
  assert.deepStrictEqual(SF.joinComponents([bar, stem]), [[0, 1]]);
});

test("joinComponents: sets come back apart, lone columns in none", () => {
  const cols = [
    rails(P(0, 0), P(100, 0), 6), rails(P(100, 0), P(100, 100), 6),         // an L
    rails(P(400, 0), P(500, 0), 6),                                          // alone
    rails(P(300, 300), P(400, 300), 6), rails(P(350, 300), P(350, 400), 6),  // a T
  ];
  assert.deepStrictEqual(SF.joinComponents(cols), [[0, 1], [3, 4]]);
  assert.deepStrictEqual(SF.joinComponents([]), []);
  assert.deepStrictEqual(SF.joinComponents([cols[2]]), []);
});

// ---- the router ---------------------------------------------------------------
test("routeColumnGroup: one needle-down path, every run tagged with its column", () => {
  const cols = [rails(P(0, 0), P(300, 0), 24), rails(P(150, 0), P(150, 200), 24)];
  const runs = SF.routeColumnGroup(cols, { pxPerMm: 6, spacingMm: 0.4, pullCompMm: 0.2, underlay: "center" });
  assert.ok(runs.length >= 3);
  assert.strictEqual(runs.filter((r) => r.jump).length, 1, "only the first run is reached needle-up");
  assert.strictEqual(runs[0].jump, true);
  for (const r of runs) assert.ok(r.col === 0 || r.col === 1, "col on every run");
  assert.deepStrictEqual([...new Set(runs.filter((r) => r.kind === "satin").map((r) => r.col))].sort(), [0, 1]);
  // every span's last visit is its satin: no underpath after the last satin
  assert.strictEqual(runs[runs.length - 1].kind, "satin");
});

// ---- the hand-off --------------------------------------------------------------
test("tick off, or no engine function handed in: the regions are what they always were", async () => {
  const MS = await studio(), T = await tool();
  for (const make of Object.values(T.FIXTURES)) {
    const { shapes } = make(24);
    const plain = MS.shapesToRegions(shapes);
    assert.deepStrictEqual(MS.shapesToRegions(shapes, undefined), plain);
    assert.deepStrictEqual(MS.shapesToRegions(shapes, { joinStrokes: false, joinComponents: SF.joinComponents }), plain);
    assert.deepStrictEqual(MS.shapesToRegions(shapes, { joinStrokes: true }), plain);
    assert.ok(!JSON.stringify(plain).includes("\"join\""));
  }
});

test("tick off sews byte for byte what no tick sews", async () => {
  const T = await tool();
  const { shapes } = T.FIXTURES.T(24);
  const MS = await studio();
  const opts = { garment: { widthIn: 8, heightIn: 8 }, fabric: FAB.getFabric("pique_knit"), pxPerMm: MS.PX_PER_MM, darkOnTop: false, fillColumns: true, cutFloats: true, underlay: true, targetWidthMm: 54 };
  const a = DG.buildQualityDesign(MS.shapesToRegions(shapes).regions, opts);
  const b = DG.buildQualityDesign(MS.shapesToRegions(shapes, { joinStrokes: false, joinComponents: SF.joinComponents }).regions, opts);
  assert.strictEqual(JSON.stringify(b), JSON.stringify(a));
});

test("a group is one region of its members, where the last of them was drawn", async () => {
  const MS = await studio();
  const col = (id, pts, rgb) => ({ id, kind: "column", points: pts, curves: {}, widthPx: 24, colorRgb: rgb || [20, 20, 20] });
  const shapes = [
    col("s1", [P(100, 100), P(400, 100)]),
    { id: "s2", points: [P(50, 250), P(150, 250), P(150, 350), P(50, 350)], curves: {}, stitchType: "fill", colorRgb: [200, 0, 0], angleDeg: null },
    col("s3", [P(250, 100), P(250, 300)]),                       // touches s1
    col("s4", [P(250, 200), P(450, 200)], [0, 0, 200]),          // touches s3, another colour
    { id: "s5", kind: "run", points: [P(100, 100), P(100, 300)], curves: {}, colorRgb: [20, 20, 20] },   // a Line on s1's end
    col("s6", [P(500, 300), P(580, 380)]),                       // touches nothing
  ];
  const { regions } = MS.shapesToRegions(shapes, { joinStrokes: true, joinComponents: SF.joinComponents });
  const ids = regions.map((r) => r.shapes.map((s) => s.id));
  assert.deepStrictEqual(ids, [["s2"], ["s1", "s3"], ["s4"], ["s5"], ["s6"]]);
  const group = regions[1];
  assert.deepStrictEqual(group.rgb, [20, 20, 20]);
  for (const s of group.shapes) { assert.strictEqual(s.sewAs.kind, "column"); assert.strictEqual(s.sewAs.join, true); assert.ok(s.outer.length >= 3); }
  for (const r of [regions[0], regions[2], regions[3], regions[4]]) assert.ok(!r.shapes[0].sewAs || !r.shapes[0].sewAs.join);
});

// ---- the instrument's bars (§4) -------------------------------------------------
test("every fixture, at 1 mm and at 4 mm: no jump, no trim, nothing on bare cloth", async () => {
  const T = await tool();
  for (const [name, make] of Object.entries(T.FIXTURES)) {
    for (const mm of T.WIDTHS_MM) {
      const fx = make(mm * 6), tag = `${name} ${mm} mm`;
      const off = T.build(fx.shapes, false), on = T.build(fx.shapes, true);
      for (const ids of fx.groups) {
        const m = T.measure(on.design, ids);
        assert.strictEqual(m.jumps + m.trims, 0, tag + ": jumps + trims inside the group");
        assert.strictEqual(m.satinSpans >= ids.length, true, tag + ": a satin span per member at least");
        assert.ok(m.travelMm > 10, tag + ": there is travel to measure");
        assert.strictEqual(m.bareMm, 0, tag + ": travel on bare cloth");
        assert.strictEqual(m.exposedMm, 0, tag + ": travel no later satin covers");
        // every member is still its own shape on the hoop
        for (const id of ids) {
          assert.ok(on.design.runs.some((sp) => sp.shape === id && sp.kind === "satin"), tag + ": satin span tagged " + id);
          const o = on.design.shapeOutlines.find((e) => e.id === id);
          assert.ok(o && !o.dropped && o.points.length >= 3, tag + ": outline for " + id);
        }
      }
      const tOff = T.totals(off.design), tOn = T.totals(on.design);
      assert.ok(tOn.trims < tOff.trims, tag + ": fewer trims joined");
      assert.strictEqual(tOn.colorStops, fx.groups.length - 1, tag + ": one colour block per group");
    }
  }
});

// ---- the instrument itself -------------------------------------------------------
// Two earlier builds of `measure` read 0.00 for the wrong reason and then
// 11 mm for the wrong reason (a body polygon built on stitch parity, then one
// of stitch triangles). So it is held to three cases whose answer is known:
// a 30 mm column, 4 mm wide, sewn by the real zigzag, and 30 mm of travel
// (a) under it, sewn first, (b) on top of it, sewn after, (c) beside it.
test("measure: travel under later satin is covered, on earlier satin is exposed, beside it is bare", async () => {
  const T = await tool();
  const SP = require("../src/satinplay.js");
  const A = [], B = [];
  for (let x = 0; x <= 300; x += 10) { A.push(P(x, 20)); B.push(P(x, -20)); }
  const satin = SP.satinFromRails(A, B, [], { spacingMm: 0.4, pxPerMm: 10, pullCompMm: 0 }).map((p) => ({ x: Math.round(p.x), y: Math.round(p.y), type: "stitch" }));
  assert.ok(satin.length > 100);
  // The satin runs x = 0 -> 300. The walk runs 300 -> 0, so it ends where the
  // satin begins (and, sewn after it, begins where the satin ended): the step
  // between the two is a couple of mm, not the column's length.
  const walk = (y) => { const out = []; for (let x = 300; x >= 0; x -= 20) out.push({ x, y, type: "stitch" }); return out; };
  const design = (first, firstKind, second, secondKind) => {
    const stitches = [{ x: first[0].x, y: first[0].y, type: "jump" }, ...first, ...second, { x: 0, y: 0, type: "end" }];
    return { stitches, runs: [
      { i0: 1, i1: first.length, kind: firstKind, shape: "s1" },
      { i0: first.length + 1, i1: first.length + second.length, kind: secondKind, shape: "s1" },
    ] };
  };
  const under = T.measure(design(walk(0), "travel", satin, "satin"), ["s1"]);
  assert.ok(Math.abs(under.travelMm - 30) < 2.5, "about 30 mm of travel, got " + under.travelMm);   // + the step onto the first cross
  assert.strictEqual(under.exposedMm, 0);
  assert.strictEqual(under.bareMm, 0);
  const onTop = T.measure(design(satin, "satin", walk(0), "travel"), ["s1"]);
  assert.ok(onTop.exposedMm >= 30, "all of it exposed, got " + onTop.exposedMm);
  assert.ok(onTop.bareMm < 2.5, "and on satin, not cloth, got " + onTop.bareMm);
  const beside = T.measure(design(walk(26), "travel", satin, "satin"), ["s1"]);   // 0.6 mm outside the rail
  assert.ok(beside.exposedMm >= 30 && beside.bareMm >= 30, "all of it bare, got " + beside.exposedMm + " / " + beside.bareMm);
  // and close in to the rail, still inside: 0.3 mm from it
  const inRail = T.measure(design(walk(17), "travel", satin, "satin"), ["s1"]);
  assert.strictEqual(inRail.exposedMm, 0);
});

test("the tuck: without it an L of two 4 mm strokes leaves about 2 mm across the finished corner; with it, none", async () => {
  const T = await tool();
  const fx = T.FIXTURES["two sets"](24);
  const worst = (extra) => Math.max(...fx.groups.map((ids) => T.measure(T.build(fx.shapes, true, extra).design, ids).exposedMm));
  const off = worst({ joinTuck: false });
  assert.ok(off > 1.5 && off < 2.6, "measured 2.10 mm on 2026-11-14, got " + off.toFixed(2));
  assert.strictEqual(worst(), 0);
  // never on bare cloth either way
  for (const ids of fx.groups) assert.strictEqual(T.measure(T.build(fx.shapes, true, { joinTuck: false }).design, ids).bareMm, 0);
});

test("a fabric whose satin underlay is zigzag: the group still sews as one path", async () => {
  const T = await tool();
  const fx = T.FIXTURES.T(24);
  const { design } = T.build(fx.shapes, true, { fabric: FAB.getFabric("fleece_sweatshirt") });
  const m = T.measure(design, fx.groups[0]);
  assert.strictEqual(m.jumps + m.trims, 0);
  assert.strictEqual(m.bareMm, 0);
  assert.ok(design.runs.some((sp) => sp.kind === "underlay"));
});

test("underlay off: no underlay span, still one path", async () => {
  const T = await tool();
  const fx = T.FIXTURES.Y(24);
  const { design } = T.build(fx.shapes, true, { underlay: false });
  assert.ok(!design.runs.some((sp) => sp.kind === "underlay"));
  const m = T.measure(design, fx.groups[0]);
  assert.strictEqual(m.jumps + m.trims, 0);
  assert.strictEqual(m.bareMm, 0);
});
