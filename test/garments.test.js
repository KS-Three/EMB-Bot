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
