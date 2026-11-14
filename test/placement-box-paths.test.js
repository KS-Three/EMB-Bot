// Pins the box each size path clamps to, per garment x placement, so changing
// one is a deliberate act (docs/placement-box-paths-2026-11-14.md,
// tools/placement-box-paths.mjs).
//
// Two kinds of "box" exist and agree everywhere except the DEFAULT placement of
// the left chest and the beanie:
//   - the PLACEMENTS box (`placementBoxMm`): auto-fit, the Studio's typed-width
//     and drag clamps, the outline-lettering width;
//   - the clamp box (`clampBoxMm`): `buildImportedDesign` (stitch file,
//     digitized result, outline lettering), the engine's typed-width clamp in
//     digitize.js, preview, the worksheet, node-edit. It is the garment's inch
//     pair unless the garment carries `clampBox`.
//
// KENT'S RULING 2026-11-14, "Hat front only": the hat front's clamp box is its
// PLACEMENTS box, 113.5 x 64.0 (before, 127.0 x 57.15, so a square logo
// auto-fitted at 64.0 was drawn at 57.2). The LEFT CHEST (101.6 x 101.6 vs 96 x
// 76.5) and the BEANIE (114.3 x 63.5 vs 94.5 x 56) are LEFT SPLIT ON PURPOSE and
// pinned below. Do not "fix" them without a new ruling from Kent: unifying them
// makes the beanie worse and shrinks 5 of the 12 starters on the default left
// chest (docs/placement-box-paths-2026-11-14.md).
//
// Each number is MEASURED by a probe on the engine, not read off a table.
const assert = require("node:assert");
const { test } = require("node:test");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const g = require("../src/garments.js");

const TOOL = pathToFileURL(path.resolve(__dirname, "..", "tools", "placement-box-paths.mjs")).href;
// engine output is rounded to 0.1 mm stitch units
const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 0.25, `${msg}: ${a} vs ${b}`);

test("every garment x placement the code offers has a row", async () => {
  const { pathRows } = await import(TOOL);
  const pairs = [];
  for (const garment of g.GARMENTS) {
    for (const pid of g.GARMENT_PLACEMENTS[garment.id] || [garment.id]) pairs.push(`${garment.id}/${pid}`);
  }
  assert.deepStrictEqual(pathRows().map((r) => `${r.garmentId}/${r.placementId}`), pairs);
  assert.strictEqual(pairs.length, 28);
});

test("the paths disagree on exactly two placements: the left chest and the beanie (Kent 2026-11-14, hat front only)", async () => {
  const { pathRows } = await import(TOOL);
  const dis = pathRows().filter((r) => r.disagree).map((r) => `${r.garmentId}/${r.placementId}`);
  assert.deepStrictEqual(dis, ["left_chest/left_chest", "beanie/beanie"]);
});

test("the hat front clamps to its PLACEMENTS box on every path (Kent 2026-11-14)", async () => {
  const { pathRows } = await import(TOOL);
  const r = pathRows().find((x) => x.garmentId === "hat_front" && x.isDefault);
  assert.deepStrictEqual(g.CLAMP_ON_PLACEMENT_BOX, ["hat_front"]);
  assert.deepStrictEqual([r.entry.w, r.entry.h], [113.5, 64.0]);
  near(r.importBox.w, 113.5, "import w"); near(r.importBox.h, 64.0, "import h");
  near(r.engineTyped.w, 113.5, "engine typed w"); near(r.engineTyped.h, 64.0, "engine typed h");
  near(r.appBox.w, 113.5, "app w"); near(r.appBox.h, 64.0, "app h");
  near(r.autoFit.w, 113.5, "auto-fit w"); near(r.autoFit.h, 64.0, "auto-fit h");
  assert.deepStrictEqual(g.clampBoxMm(g.getGarment("hat_front")), { w: 113.5, h: 64.0 });
  // the inch pair itself is untouched: `{ proSized: false }` is still "the round-inch box as it was"
  assert.strictEqual(g.getGarment("hat_front").widthIn, 5.0);
  assert.strictEqual(g.getGarment("hat_front").heightIn, 2.25);
});

test("a square logo auto-fitted on the hat front is DRAWN at the 64.0 mm it was fitted (it was drawn at 57.2)", async () => {
  const { pathRows } = await import(TOOL);
  const hat = pathRows().find((r) => r.placementId === "hat_front" && r.isDefault);
  assert.strictEqual(hat.square.fitted, 64);
  near(hat.square.drawn, 64, "drawn side");
  assert.ok(hat.square.drawn > 63.9, `drawn ${hat.square.drawn}`);
  // left chest (76.2, area cap) and beanie (56) sit inside their inch box: not resized
  for (const id of ["left_chest", "beanie"]) {
    const r = pathRows().find((x) => x.placementId === id && x.isDefault);
    near(r.square.drawn, r.square.fitted, `${id} drawn side`);
  }
});

test("the hat front's non-default placements keep their own box, not the hat front's", () => {
  for (const pid of ["hat_front_left", "hat_front_right", "hat_side_left", "hat_side_right", "hat_rear"]) {
    const placed = g.resolvePlacement("hat_front", pid);
    assert.strictEqual(placed.clampBox, undefined, pid);
    const want = g.getPlacement(pid).box;
    const got = g.clampBoxMm(placed);
    assert.ok(Math.abs(got.w - want.w) < 1e-9 && Math.abs(got.h - want.h) < 1e-9, pid);
  }
});

test("today's boxes on the two split placements, per path (left chest, beanie)", async () => {
  const { pathRows } = await import(TOOL);
  const rows = new Map(pathRows().filter((r) => r.isDefault).map((r) => [r.placementId, r]));
  // [PLACEMENTS entry, clamp box (the inch pair)] in mm
  const want = {
    left_chest: { entry: [96.0, 76.5], inch: [4 * 25.4, 4 * 25.4] },
    beanie: { entry: [94.5, 56.0], inch: [4.5 * 25.4, 2.5 * 25.4] },
  };
  for (const [id, w] of Object.entries(want)) {
    const r = rows.get(id);
    assert.deepStrictEqual([r.entry.w, r.entry.h], w.entry, `${id} PLACEMENTS entry`);
    near(r.importBox.w, w.inch[0], `${id} import clamp w`);
    near(r.importBox.h, w.inch[1], `${id} import clamp h`);
    near(r.engineTyped.w, w.inch[0], `${id} engine typed clamp w`);
    near(r.engineTyped.h, w.inch[1], `${id} engine typed clamp h`);
    // the Studio's typed/drag clamp and the auto-fit read the PLACEMENTS box
    near(r.appBox.w, w.entry[0], `${id} app typed/drag clamp w`); near(r.appBox.h, w.entry[1], `${id} app typed/drag clamp h`);
    near(r.autoFit.w, w.entry[0], `${id} auto-fit w`); near(r.autoFit.h, w.entry[1], `${id} auto-fit h`);
    assert.strictEqual(g.getGarment(id).clampBox, undefined, `${id} carries no clampBox`);
  }
  // the left chest's area cap rides auto-fit only, never the import clamp
  assert.strictEqual(rows.get("left_chest").autoFit.area, 5800);
});

test("everywhere else every path reads the one PLACEMENTS box (auto-fit capped to the 198 mm hoop field)", async () => {
  const { pathRows } = await import(TOOL);
  const hoop = g.HOOPS[g.HOOPS.length - 1];
  const cap = hoop.widthMm - 2 * g.HOOP_FIT_MARGIN_MM;
  let n = 0;
  for (const r of pathRows()) {
    if (r.disagree) continue;
    n++;
    const where = `${r.garmentId}/${r.placementId}`;
    near(r.importBox.w, r.entry.w, `${where} import w`);
    near(r.importBox.h, r.entry.h, `${where} import h`);
    near(r.engineTyped.w, r.entry.w, `${where} engine typed w`);
    near(r.engineTyped.h, r.entry.h, `${where} engine typed h`);
    near(r.appBox.w, r.entry.w, `${where} app w`); near(r.appBox.h, r.entry.h, `${where} app h`);
    near(r.autoFit.w, Math.min(r.entry.w, cap), `${where} auto-fit w`);
    near(r.autoFit.h, Math.min(r.entry.h, cap), `${where} auto-fit h`);
  }
  assert.strictEqual(n, 26);
});

test("the 12 starters at the 75% stop: 77 overflowing combinations before the ruling, 76 now (Shamrock fits the hat front)", async () => {
  const { loadStarters, overflowRows } = await import(TOOL);
  const starters = loadStarters();
  assert.strictEqual(starters.length, 12);
  const count = (variant) => {
    const by = {};
    for (const r of overflowRows(starters, variant)) if (r.overflows) by[r.placement] = (by[r.placement] || 0) + 1;
    return by;
  };
  const before = count("inch");
  assert.strictEqual(Object.values(before).reduce((a, b) => a + b, 0), 77);
  assert.strictEqual(before.hat_front, 5);
  const now = count("current");
  assert.strictEqual(Object.values(now).reduce((a, b) => a + b, 0), 76);
  assert.deepStrictEqual(now, {
    hat_front: 4, hat_front_left: 12, hat_front_right: 12, hat_side_left: 11, hat_side_right: 11,
    hat_rear: 11, beanie: 4, beanie_cuff: 11,
  });
});

test("the ruling moved the hat front and nothing else: 1 now fits, 4 better, none worse", async () => {
  const { loadStarters, overflowDiff, verdictOf } = await import(TOOL);
  const d = overflowDiff(loadStarters(), "inch", "current");
  const tally = {};
  for (const c of d.changed) tally[verdictOf(c)] = (tally[verdictOf(c)] || 0) + 1;
  assert.deepStrictEqual(tally, { "now fits": 1, better: 4 });
  for (const c of d.changed) assert.strictEqual(c.before.placement, "hat_front");
  // and no other row is drawn differently
  for (const c of d.rescaled) assert.strictEqual(c.before.placement, "hat_front");
});

test("the PLACEMENTS-box what-if (left chest, beanie too) is only a comparison: it changes those two, nothing else", async () => {
  const { loadStarters, overflowDiff } = await import(TOOL);
  const d = overflowDiff(loadStarters(), "current", "placements");
  assert.ok(d.changed.length > 0);
  for (const c of [...d.changed, ...d.rescaled]) assert.ok(["left_chest", "beanie"].includes(c.before.placement), c.before.placement);
});
