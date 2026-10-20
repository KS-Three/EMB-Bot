// Open runs in the manual lane (spec 2026-09-30 §7, plan
// docs/superpowers/plans/2026-10-11-manual-open-runs.md, Task 1).
//
// A hand-drawn line arrives as a region whose `outer` is a hairline-stroked
// PROXY ring (for hit-testing, the bbox and the sew order) and whose
// `sewAs: { kind: "run", path, passes, stitchLenMm }` carries the path it was
// drawn along. The engine sews `runAlongPath(path)` and NOTHING else of the
// shape — ruling 1's three gates: no underlay, no finishing outline, and the
// run as the top stitch instead of a fill of the proxy ring.
const assert = require("node:assert");
const { test } = require("node:test");
const crypto = require("node:crypto");
const DG = require("../src/digitize.js");
const FILL = require("../src/fill.js");
const SF = require("../src/satinfont.js");
const FAB = require("../src/fabrics.js");

const G = SF.LETTERING_GUARDS;
// `ties`, `fillStagger` and `dedupeHoles` went ON by default on 2026-10-20
// (Kent); a pin below taken before that, on another subject, builds with them OFF.
const TRIO_OFF = { ties: false, fillStagger: false, dedupeHoles: false };

// ---- the no-run pin ----------------------------------------------------------
// A design with no run must sew exactly what it sewed before runs existed.
// Built through the Studio's own shapesToRegions (a fill rectangle, a satin
// shape and a column), underlay on, on a real fabric. The hash was printed by
// THIS file run against origin/main 9e005c49's own src/ — before any engine
// edit in this lane — and pasted here.
const NO_RUN_SHA = "9bede0995e78287a2e1f6d99eadfaee51faa62ff42b19d2ed17237287439ae32";
test("no run: a design of closed shapes and a column is byte-identical to main", async () => {
  const MS = await import("../app/src/lib/manualShapes.js");
  const shapes = [
    { id: "s1", points: [{ x: 40, y: 60 }, { x: 220, y: 60 }, { x: 220, y: 300 }, { x: 40, y: 300 }], curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null },
    { id: "s2", points: [{ x: 260, y: 80 }, { x: 290, y: 80 }, { x: 290, y: 320 }, { x: 260, y: 320 }], curves: {}, stitchType: "satin", colorRgb: [200, 0, 0], angleDeg: null },
    { id: "s3", kind: "column", points: [{ x: 330, y: 100 }, { x: 450, y: 180 }, { x: 560, y: 120 }], curves: { 1: { x: 520, y: 240 } }, widthPx: 24, colorRgb: [0, 0, 200] },
  ];
  const { regions, pxPerMm } = MS.shapesToRegions(shapes);
  const d = DG.buildQualityDesign(regions, { garment: { widthIn: 8, heightIn: 8 }, pxPerMm, targetWidthMm: 80, underlay: true, fabric: FAB.getFabric("jersey_tee"), darkOnTop: false, ...TRIO_OFF });
  const hash = crypto.createHash("sha256").update(JSON.stringify(d.stitches)).digest("hex");
  assert.strictEqual(d.stitchCount, 2579);
  assert.strictEqual(hash, NO_RUN_SHA);
});

// ---- runAlongPath ------------------------------------------------------------
const P = (x, y) => ({ x, y });
const near = (a, b, eps = 1e-9) => Math.abs(a.x - b.x) <= eps && Math.abs(a.y - b.y) <= eps;
function distToPath(p, path) {
  let best = Infinity;
  for (let i = 0; i < path.length - 1; i++) {
    const a = path[i], b = path[i + 1];
    const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy;
    const t = L2 ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2)) : 0;
    best = Math.min(best, Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy)));
  }
  return best;
}

test("runAlongPath: one pass lands a station every step and one on the last vertex exactly", () => {
  const out = FILL.runAlongPath([P(0, 0), P(100, 0)], { stitchLenPx: 10, passes: 1 });
  assert.strictEqual(out.length, 11);
  out.forEach((p, i) => assert.ok(near(p, P(10 * i, 0), 1e-9), "station " + i + " " + JSON.stringify(p)));
  assert.deepStrictEqual(out[out.length - 1], P(100, 0));
});

test("runAlongPath: a short remainder moves the last station onto the end rather than adding a stub", () => {
  const out = FILL.runAlongPath([P(0, 0), P(104, 0)], { stitchLenPx: 10, passes: 1 });
  assert.deepStrictEqual(out[out.length - 1], P(104, 0));
  for (let i = 1; i < out.length; i++) {
    const s = Math.hypot(out[i].x - out[i - 1].x, out[i].y - out[i - 1].y);
    assert.ok(s >= 5 - 1e-9 && s <= 15 + 1e-9, "stitch " + i + " is " + s);
  }
  // a remainder of half a step or more gets its own stitch
  const out2 = FILL.runAlongPath([P(0, 0), P(106, 0)], { stitchLenPx: 10, passes: 1 });
  assert.strictEqual(out2.length, 12);
  assert.deepStrictEqual(out2[out2.length - 1], P(106, 0));
});

test("runAlongPath: three passes are a true bean — forward, back and forward over the SAME stations", () => {
  const path = [P(0, 0), P(60, 0), P(60, 45)];
  const one = FILL.runAlongPath(path, { stitchLenPx: 7, passes: 1 });
  const three = FILL.runAlongPath(path, { stitchLenPx: 7, passes: 3 });
  const n = one.length;
  assert.strictEqual(three.length, 3 * n - 2);
  assert.deepStrictEqual(three.slice(0, n), one);
  assert.deepStrictEqual(three.slice(n - 1, 2 * n - 1), one.slice().reverse());
  assert.deepStrictEqual(three.slice(2 * n - 2), one);
  assert.deepStrictEqual(three[three.length - 1], P(60, 45));
  for (const p of one) assert.ok(distToPath(p, path) < 1e-9, "on the path: " + JSON.stringify(p));
});

test("runAlongPath: degenerate input sews nothing; odd pass counts fall back to 1 or 3", () => {
  assert.deepStrictEqual(FILL.runAlongPath([], { stitchLenPx: 5, passes: 3 }), []);
  assert.deepStrictEqual(FILL.runAlongPath([P(3, 3), P(3, 3)], { stitchLenPx: 5, passes: 3 }), []);
  const path = [P(0, 0), P(50, 0)];
  assert.deepStrictEqual(FILL.runAlongPath(path, { stitchLenPx: 5, passes: 0 }), FILL.runAlongPath(path, { stitchLenPx: 5, passes: 1 }));
  assert.deepStrictEqual(FILL.runAlongPath(path, { stitchLenPx: 5, passes: 5 }), FILL.runAlongPath(path, { stitchLenPx: 5, passes: 3 }));
});

test("RUN_MIN_LOOP_MM mirrors machine.py's 2.2", () => {
  assert.strictEqual(FILL.RUN_MIN_LOOP_MM, 2.2);
});

// ---- the engine: a region with sewAs.kind "run" ------------------------------
// The proxy ring: the path stroked 1 px wide, as shapesToRegions builds it.
async function hairline(path) {
  const { railsFromSpine } = await import("../app/src/lib/spineRails.js");
  return railsFromSpine(path, 1).ring;
}
const runOpts = (extra) => Object.assign({ garment: { widthIn: 8, heightIn: 8 }, pxPerMm: 6, targetWidthMm: 50, underlay: false }, extra);
async function runShape(path, sewExtra, id = "r1") {
  return { id, outer: await hairline(path), holes: [], tierOverride: "fill", angleOverride: null,
    sewAs: Object.assign({ kind: "run", path, passes: null, stitchLenMm: null }, sewExtra) };
}
const spanStitches = (d, kind, id) => {
  const out = [];
  for (const sp of d.runs) if (sp.kind === kind && sp.shape === id) {
    for (let i = sp.i0; i <= sp.i1; i++) if (d.stitches[i].type === "stitch") out.push({ x: d.stitches[i].x, y: d.stitches[i].y });
  }
  return out;
};

test("sewAs run: the path sews as a bean and NOTHING else of the shape sews (no underlay, no outline, no fill)", async () => {
  const path = [P(0, 0), P(300, 0)];
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [await runShape(path)] }],
    runOpts({ underlay: true, fabric: FAB.getFabric("jersey_tee"), outline: true, ...TRIO_OFF }));
  assert.deepStrictEqual(d.runs.map((r) => r.kind), ["run"]);
  assert.strictEqual(d._debug.nFill, 0);
  assert.strictEqual(d._debug.nSatin, 0);
  const st = spanStitches(d, "run", "r1");
  // 300 px at 50 mm wide is 50 mm; a bean at 0.73 mm is ~3 x 50 / 0.73 stitches.
  const lenMm = 300 * d.fit.mmPerPx;
  const want = 3 * lenMm / G.BEAN_STITCH_MM;
  assert.ok(Math.abs(st.length - want) <= 4, st.length + " stitches vs ~" + want.toFixed(1));
  // every stitch is on the line (one DST unit of rounding)
  const ys = new Set(st.map((p) => p.y));
  assert.strictEqual(ys.size, 1, "a horizontal line sews on one row: " + [...ys]);
});

test("sewAs run: absent or garbage passes / stitch length fall back to the engine's bean defaults", async () => {
  const path = [P(0, 0), P(200, 40), P(300, 0)];
  const build = async (extra) => DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [await runShape(path, extra)] }], runOpts()).stitches;
  const dflt = await build({});
  assert.deepStrictEqual(await build({ passes: 2, stitchLenMm: -1 }), dflt);
  assert.deepStrictEqual(await build({ passes: "x", stitchLenMm: NaN }), dflt);
  assert.deepStrictEqual(await build({ passes: G.BEAN_PASSES, stitchLenMm: G.BEAN_STITCH_MM }), dflt);
  const single = await build({ passes: 1 });
  assert.ok(single.length < dflt.length / 2, single.length + " vs " + dflt.length);
});

test("sewAs run: a line shorter than RUN_MIN_LOOP_MM sews nothing and its outline is dropped", async () => {
  const rect = [P(0, 0), P(300, 0), P(300, 200), P(0, 200)];
  const tiny = [P(100, 250), P(110, 250)];   // 10 px at 1/6 mm per px: 1.7 mm
  const d = DG.buildQualityDesign([
    { rgb: [0, 0, 0], shapes: [{ id: "s1", outer: rect, holes: [], tierOverride: "fill" }] },
    { rgb: [200, 0, 0], shapes: [await runShape(tiny)] },
  ], runOpts());
  assert.ok(10 * d.fit.mmPerPx < FILL.RUN_MIN_LOOP_MM);
  assert.strictEqual(d.runs.filter((r) => r.shape === "r1").length, 0);
  assert.strictEqual(d.shapeOutlines.find((o) => o.id === "r1").dropped, true);
  // the same line long enough sews
  const ok = DG.buildQualityDesign([
    { rgb: [0, 0, 0], shapes: [{ id: "s1", outer: rect, holes: [], tierOverride: "fill" }] },
    { rgb: [200, 0, 0], shapes: [await runShape([P(100, 250), P(130, 250)])] },
  ], runOpts());
  assert.strictEqual(ok.runs.filter((r) => r.shape === "r1").length, 1);
});

test("sewAs run: a hairpin that doubles back on itself still sews along its path", async () => {
  const path = [P(0, 0), P(200, 0), P(0, 0)];
  const d = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [await runShape(path)] }], runOpts());
  const st = spanStitches(d, "run", "r1");
  assert.ok(st.length > 100, String(st.length));
  assert.strictEqual(new Set(st.map((p) => p.y)).size, 1);
});

test("sewAs run without a path is not a run: it sews the plain fill it always did", async () => {
  const path = [P(0, 0), P(300, 0), P(300, 60)];
  const ring = await hairline(path);
  const plain = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ id: "r1", outer: ring, holes: [], tierOverride: "fill" }] }], runOpts());
  const noPath = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ id: "r1", outer: ring, holes: [], tierOverride: "fill", sewAs: { kind: "run" } }] }], runOpts());
  const onePoint = DG.buildQualityDesign([{ rgb: [0, 0, 0], shapes: [{ id: "r1", outer: ring, holes: [], tierOverride: "fill", sewAs: { kind: "run", path: [P(0, 0)] } }] }], runOpts());
  assert.deepStrictEqual(noPath.stitches, plain.stitches);
  assert.deepStrictEqual(onePoint.stitches, plain.stitches);
});
