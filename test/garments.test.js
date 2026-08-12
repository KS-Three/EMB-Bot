const assert = require("node:assert");
const { test } = require("node:test");
const g = require("../src/garments.js");

test("garment list has left_chest default 4x4", () => {
  const lc = g.getGarment("left_chest");
  assert.deepStrictEqual([lc.widthIn, lc.heightIn], [4.0, 4.0]);
  assert.strictEqual(g.GARMENTS.length, 10);
});
test("fit scales down to fit box, aspect preserved", () => {
  // bbox 100x50mm into left_chest (4in=101.6mm square)
  const r = g.fitScale(100, 50, g.getGarment("left_chest"));
  assert.ok(r.scale > 1.0 && r.scale < 1.02); // width-limited ~1.016
  assert.ok(Math.abs(r.targetWmm - 101.6) < 0.5);
  assert.ok(Math.abs(r.targetHmm - 50 * r.scale) < 1e-6);
});
test("fit scales large design down", () => {
  const r = g.fitScale(400, 400, g.getGarment("left_chest"));
  assert.ok(r.scale < 1);
  assert.ok(r.targetWmm <= 101.6 + 1e-6);
});
test("exceedsHoop", () => {
  assert.strictEqual(g.exceedsHoop(400, 100), true);
  assert.strictEqual(g.exceedsHoop(100, 100), false);
});

// ---- Hoop presets (launch checklist item 2) --------------------------------

test("hoop presets: the four home-machine sizes, smallest first", () => {
  assert.deepStrictEqual(
    g.HOOPS.map((h) => [h.id, h.widthMm, h.heightMm]),
    [
      ["4x4", 100, 100],
      ["5x7", 130, 180],
      ["6x10", 160, 250],
      ["8x8", 200, 200],
    ]
  );
  for (const h of g.HOOPS) assert.ok(h.label && h.label.includes("in"));
});

test("getHoop finds a preset by id, undefined otherwise", () => {
  assert.strictEqual(g.getHoop("5x7").widthMm, 130);
  assert.strictEqual(g.getHoop("9x9"), undefined);
  assert.strictEqual(g.getHoop(null), undefined);
});

test("hoopFit is orientation-aware: a 170x120 design goes into a 130x180 hoop rotated", () => {
  const h57 = g.getHoop("5x7");
  assert.strictEqual(g.hoopFit(120, 170, h57), "fits");
  assert.strictEqual(g.hoopFit(170, 120, h57), "rotated");
  assert.strictEqual(g.hoopFit(170, 190, h57), "exceeds");
  // exact-fit boundary counts as fitting
  assert.strictEqual(g.hoopFit(130, 180, h57), "fits");
});

test("suggestHoop picks the smallest preset that admits the placement box", () => {
  // sleeve 3x3in (76.2mm sq) -> 4x4; hat_front 5x2.25in (127x57.15) -> 5x7
  assert.strictEqual(g.suggestHoop(g.getGarment("sleeve")).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("patch")).id, "4x4");
  assert.strictEqual(g.suggestHoop(g.getGarment("hat_front")).id, "5x7");
  assert.strictEqual(g.suggestHoop(g.getGarment("towel")).id, "6x10");
});

test("suggestHoop falls back to the largest hoop for over-size placements (and no garment)", () => {
  // full_back 12x12in (304.8mm sq) exceeds every preset
  assert.strictEqual(g.suggestHoop(g.getGarment("full_back")).id, "8x8");
  assert.strictEqual(g.suggestHoop(null).id, "8x8");
});

test("exceedsHoop against a chosen hoop is the orientation-aware ceiling", () => {
  const h44 = g.getHoop("4x4");
  assert.strictEqual(g.exceedsHoop(120, 80, h44), true);
  assert.strictEqual(g.exceedsHoop(99, 99, h44), false);
  // rotated fit is NOT an excess — the message layer tells the user to rotate
  assert.strictEqual(g.exceedsHoop(170, 120, g.getHoop("5x7")), false);
});
