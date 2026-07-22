const assert = require("node:assert");
const { test } = require("node:test");
const u = require("../src/units.js");

test("inch to mm", () => assert.strictEqual(u.inToMm(1), 25.4));
test("mm to inch", () => assert.ok(Math.abs(u.mmToInch(25.4) - 1) < 1e-9));
test("mm to dst units rounds to 0.1mm", () => {
  assert.strictEqual(u.mmToDstUnits(1), 10);
  assert.strictEqual(u.mmToDstUnits(2.54), 25); // 25.4 -> 25
});
test("dst units to mm", () => assert.strictEqual(u.dstUnitsToMm(10), 1));
test("constants", () => {
  assert.strictEqual(u.MM_PER_INCH, 25.4);
  assert.strictEqual(u.DST_UNITS_PER_MM, 10);
});
