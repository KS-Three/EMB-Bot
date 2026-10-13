// tools/crossstitch-arm-census.mjs pins (2026-10-13). Measure-only tool: these pin
// MEASUREMENTS of the engine as it stands, so a change to crossfill or the cap
// fit shows up here as a number to look at.
import { test } from "node:test";
import assert from "node:assert";

const T = await import("../tools/crossstitch-arm-census.mjs");

test("limits are the census's own", () => {
  assert.strictEqual(T.DST_MM, 12.1);
  assert.strictEqual(T.SPLIT_MM, 5.0);
});

test("an arm is a 45-degree segment: axis delta is length / sqrt2", () => {
  const r = T.measureFont("noble", [25, 60]);
  for (const c of r.cells) {
    assert.ok(c.arms > 0, "cross arms found");
    assert.ok(Math.abs(c.armAx - c.armMm / Math.SQRT2) < 0.15);
    assert.strictEqual(c.capMiss, false, "the cap lands on the target");
  }
});

test("the lattice is in glyph units: arm length scales with cap", () => {
  const r = T.measureFont("noble", [25, 60]);
  assert.ok(r.linearity < 0.05, "arm/cap spread " + r.linearity);
  assert.ok(r.cells[1].armMm / r.cells[0].armMm > 2.2 && r.cells[1].armMm / r.cells[0].armMm < 2.6);
  // 5.0 mm is crossed well before the record, and both far above Studio caps
  assert.ok(r.startsOver5Mm > 30 && r.startsOver5Mm < 60, "" + r.startsOver5Mm);
  assert.ok(r.startsOver12Mm > r.startsOver12LenMm && r.startsOver12LenMm > r.startsOver5Mm);
});

test("reproduces long-stitch-census's hoop rows: jersey_15 'A' at left chest", () => {
  const r = T.hoopRow("jersey_15", "A", "left_chest");
  assert.strictEqual(+r.maxMm.toFixed(1), 9.6);
  assert.strictEqual(+r.maxAx.toFixed(1), 6.8);
  assert.strictEqual(r.over12, 0);
  // 17.0 before the arm split (crossfill maxSegPx, 2026-10-13); the 24.0 mm arm is now two 12.0 mm halves
  assert.strictEqual(+T.hoopRow("noble", "AB", "full_back").maxAx.toFixed(1), 8.5);
});
