const assert = require("node:assert");
const { test } = require("node:test");
const f = require("../src/fabrics.js");

const ALLOWED_UNDERLAY = new Set([
  "none",
  "edge_run",
  "center_run",
  "edge_zigzag",
  "edge_lattice",
  "double_lattice",
  "zigzag",
]);

test("FABRICS has 7 entries with all 8 fields of correct types", () => {
  assert.strictEqual(f.FABRICS.length, 7);
  for (const fab of f.FABRICS) {
    assert.ok(typeof fab.id === "string" && fab.id.length > 0, "id");
    assert.ok(typeof fab.label === "string" && fab.label.length > 0, "label");
    assert.ok(typeof fab.notes === "string" && fab.notes.length > 0, "notes");
    assert.strictEqual(typeof fab.pullCompMm, "number", "pullCompMm");
    assert.strictEqual(typeof fab.densityAdjust, "number", "densityAdjust");
    assert.strictEqual(typeof fab.trimAtMm, "number", "trimAtMm");
    assert.ok(ALLOWED_UNDERLAY.has(fab.fillUnderlay), "fillUnderlay");
    assert.ok(ALLOWED_UNDERLAY.has(fab.satinUnderlay), "satinUnderlay");
  }
});

test("getFabric returns presets and undefined for unknown", () => {
  assert.strictEqual(f.getFabric("structured_cap").pullCompMm, 0.4);
  assert.strictEqual(f.getFabric("terry_towel").fillUnderlay, "double_lattice");
  assert.strictEqual(f.getFabric("nope"), undefined);
});

test("fabricForGarment maps known garments and falls back", () => {
  assert.strictEqual(f.fabricForGarment("hat_front"), "structured_cap");
  assert.strictEqual(f.fabricForGarment("towel"), "terry_towel");
  assert.strictEqual(f.fabricForGarment("left_chest"), "pique_knit");
  assert.strictEqual(f.fabricForGarment("who_knows"), "pique_knit");
});

test("every garment maps to a valid fabric id", () => {
  const garmentIds = [
    "hat_front",
    "beanie",
    "left_chest",
    "full_back",
    "sleeve",
    "tote",
    "jacket_back",
    "patch",
    "towel",
    "blanket",
  ];
  for (const gid of garmentIds) {
    const fid = f.fabricForGarment(gid);
    assert.ok(f.getFabric(fid), `${gid} -> ${fid} must be a valid fabric`);
  }
});

test("dual-mode: require exposes the api in Node", () => {
  assert.strictEqual(typeof f.getFabric, "function");
  assert.strictEqual(typeof f.fabricForGarment, "function");
  assert.ok(Array.isArray(f.FABRICS));
});

// --- Calibration profiles (2026-09-30) --------------------------------------
// The arithmetic is a hand-port of fabrics.py's; digitizer/tests/
// test_fabric_wire.py RUNS this module against Python and compares. These
// pin the contract the Studio relies on: off is the same object, a profile
// adjusts and records itself, the clamp is the table's span.

test("applyFabricProfile: no profile or a no-op returns the SAME preset object", () => {
  const polo = f.getFabric("pique_knit");
  assert.strictEqual(f.applyFabricProfile(polo, null), polo);
  assert.strictEqual(f.applyFabricProfile(polo, {}), polo);
  assert.strictEqual(f.applyFabricProfile(polo, { pull_comp_delta_mm: 0, density_scale: 1 }), polo);
  assert.strictEqual(f.normalizeFabricProfile({ trim_at_delta_mm: 0 }), null);
});

test("applyFabricProfile adjusts pull comp, density and trim, and leaves the preset untouched", () => {
  const polo = f.getFabric("pique_knit");
  const g = f.applyFabricProfile(polo, { pull_comp_delta_mm: 0.15, density_scale: 0.9, trim_at_delta_mm: 0.5 });
  assert.deepStrictEqual([g.pullCompMm, g.densityAdjust, g.trimAtMm], [0.45, 0.9, 3.5]);
  assert.deepStrictEqual(g.profile, { pull_comp_delta_mm: 0.15, density_scale: 0.9, trim_at_delta_mm: 0.5 });
  assert.strictEqual(g.fillUnderlay, polo.fillUnderlay);
  assert.strictEqual(g.assumedBacking, polo.assumedBacking);
  assert.strictEqual(polo.pullCompMm, 0.3);
  assert.strictEqual(polo.profile, undefined);
});

test("the clamp is the shipped table's span, derived not written", () => {
  const c = f.profileClamps();
  assert.deepStrictEqual(c.pullCompMm, [0.2, 0.6]);
  assert.deepStrictEqual(c.densityAdjust, [0.85, 1.0]);
  assert.deepStrictEqual(c.trimAtMm, [3.0, 4.0]);
  const polo = f.getFabric("pique_knit");
  const hi = f.applyFabricProfile(polo, { pull_comp_delta_mm: 5, density_scale: 3, trim_at_delta_mm: 9 });
  const lo = f.applyFabricProfile(polo, { pull_comp_delta_mm: -5, density_scale: 0.01, trim_at_delta_mm: -9 });
  assert.deepStrictEqual([hi.pullCompMm, hi.densityAdjust, hi.trimAtMm], [0.6, 1.0, 4.0]);
  assert.deepStrictEqual([lo.pullCompMm, lo.densityAdjust, lo.trimAtMm], [0.2, 0.85, 3.0]);
});

test("a malformed profile throws by name rather than sewing something", () => {
  const polo = f.getFabric("pique_knit");
  assert.throws(() => f.applyFabricProfile(polo, [0.1]), /must be an object/);
  assert.throws(() => f.applyFabricProfile(polo, { pull_comp_mm: 0.1 }), /unknown field/);
  assert.throws(() => f.applyFabricProfile(polo, { density_scale: "0.9" }), /finite number/);
  assert.throws(() => f.applyFabricProfile(polo, { density_scale: NaN }), /finite number/);
});
