// Pins the box each size path clamps to, per garment x placement, so changing
// one is a deliberate act (docs/placement-box-paths-2026-11-14.md,
// tools/placement-box-paths.mjs).
//
// Two kinds of "box" exist today and agree everywhere except the DEFAULT
// placement of the three garments the pro measured:
//   - the PLACEMENTS box (`placementBoxMm`): auto-fit, the Studio's typed-width
//     and drag clamps, the outline-lettering width;
//   - the inch pair (`widthIn x heightIn` of the garment as placed): the clamp
//     inside `buildImportedDesign` (stitch file, digitized result, outline
//     lettering) and the engine's typed-width clamp in digitize.js.
// Each number here is MEASURED by a probe on the engine, not read off a table.
// Kent decides which box wins (docs/placement-box-paths-2026-11-14.md); until he
// does, this file is today's behaviour. If you meant to unify the boxes, change
// the expectations below in the same PR and say so.
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

test("the paths disagree on exactly three placements: the default of each pro-measured garment", async () => {
  const { pathRows } = await import(TOOL);
  const dis = pathRows().filter((r) => r.disagree).map((r) => `${r.garmentId}/${r.placementId}`);
  assert.deepStrictEqual(dis, ["hat_front/hat_front", "left_chest/left_chest", "beanie/beanie"]);
});

test("today's boxes on the three disagreeing placements, per path", async () => {
  const { pathRows } = await import(TOOL);
  const rows = new Map(pathRows().filter((r) => r.isDefault).map((r) => [r.placementId, r]));
  // [PLACEMENTS entry, import clamp (inch pair)] in mm
  const want = {
    hat_front: { entry: [113.5, 64.0], inch: [5 * 25.4, 2.25 * 25.4] },
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
  assert.strictEqual(n, 25);
});

test("a square logo auto-fitted on the hat front is drawn 10.7% smaller than it was fitted (64 mm fit, 57.15 mm clamp)", async () => {
  const { pathRows } = await import(TOOL);
  const hat = pathRows().find((r) => r.placementId === "hat_front" && r.isDefault);
  assert.strictEqual(hat.square.fitted, 64);
  near(hat.square.drawn, 2.25 * 25.4, "drawn side");
  // left chest (76.2, area cap) and beanie (56) sit inside the inch box: not resized
  for (const id of ["left_chest", "beanie"]) {
    const r = pathRows().find((x) => x.placementId === id && x.isDefault);
    near(r.square.drawn, r.square.fitted, `${id} drawn side`);
  }
});

test("the 12 starters at the 75% stop overflow 77 combinations under the inch pair (the 2026-11-14 table)", async () => {
  const { loadStarters, overflowRows } = await import(TOOL);
  const starters = loadStarters();
  assert.strictEqual(starters.length, 12);
  const over = overflowRows(starters, "inch").filter((r) => r.overflows);
  assert.strictEqual(over.length, 77);
  const by = {};
  for (const r of over) by[r.placement] = (by[r.placement] || 0) + 1;
  assert.deepStrictEqual(by, {
    hat_front: 5, hat_front_left: 12, hat_front_right: 12, hat_side_left: 11, hat_side_right: 11,
    hat_rear: 11, beanie: 4, beanie_cuff: 11,
  });
});

test("the PLACEMENTS-box what-if is only a comparison: it changes the hat front and the beanie, nothing else overflows differently", async () => {
  const { loadStarters, overflowDiff } = await import(TOOL);
  const d = overflowDiff(loadStarters());
  assert.ok(d.changed.length > 0);
  for (const c of d.changed) assert.ok(["hat_front", "beanie"].includes(c.before.placement), c.before.placement);
});
