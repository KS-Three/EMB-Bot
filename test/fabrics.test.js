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
