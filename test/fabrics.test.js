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

// --- Hooping advice (2026-10-01) ---------------------------------------------
// What the operator hoops: stabilizer, topper, needle. One function, read by
// the Studio's hooping card AND the PDF worksheet, so the two cannot disagree.
// Advice only — nothing here is read by a stitch planner.

test("every preset carries a needle: 75/11, ballpoint on knits, sharp on wovens and caps", () => {
  // Playbook Law 21 [P — Tajima, Madeira, Groz-Beckert, A&E]. The split is the
  // goods' construction, so it is asserted per preset rather than by pattern.
  const want = {
    structured_cap: "75/11 sharp",
    pique_knit: "75/11 ballpoint",
    jersey_tee: "75/11 ballpoint",
    fleece_sweatshirt: "75/11 ballpoint",
    canvas_tote: "75/11 sharp",
    terry_towel: "75/11 sharp",
    woven_dress: "75/11 sharp",
  };
  const got = Object.fromEntries(f.FABRICS.map((fab) => [fab.id, fab.needle]));
  assert.deepStrictEqual(got, want);
});

test("hoopingAdvice states stabilizer, topper and needle for a garment we ship", () => {
  const a = f.hoopingAdvice("left_chest", 4321);
  assert.strictEqual(a.fabricId, "pique_knit");
  assert.strictEqual(a.backing, "cutaway");
  assert.strictEqual(a.escalated, false);
  assert.strictEqual(a.topper, false);
  assert.strictEqual(a.needle, "75/11 ballpoint");
  assert.deepStrictEqual(a.rows, [
    { label: "Stabilizer", value: "cutaway", note: "" },
    { label: "Topper", value: "no", note: "" },
    { label: "Needle", value: "75/11 ballpoint", note: f.NEEDLE_BASIS },
  ]);
  assert.deepStrictEqual(a.rows.map(f.hoopingLine), [
    "Stabilizer: cutaway",
    "Topper: no",
    "Needle: 75/11 ballpoint (standard for 40wt thread)",
  ]);
  assert.strictEqual(f.hoopingAdvice("towel", 100).topper, true);
  assert.strictEqual(f.hoopingAdvice("hat_front", 100).rows[0].value, "cap buckram");
});

test("past 25,000 stitches anything lighter than cutaway escalates and says why", () => {
  assert.strictEqual(f.CUTAWAY_STITCHES, 25000);
  const edge = f.hoopingAdvice("tote", 25000);
  assert.deepStrictEqual([edge.backing, edge.escalated], ["tearaway", false]);
  const heavy = f.hoopingAdvice("tote", 26676);
  assert.deepStrictEqual([heavy.backing, heavy.escalated], ["cutaway", true]);
  assert.strictEqual(
    f.hoopingLine(heavy.rows[0]),
    "Stabilizer: cutaway (escalated - 26,676 stitches; tear-away releases under this much thread)"
  );
  // Already cutaway: nothing to escalate, and it is not told twice.
  assert.strictEqual(f.hoopingAdvice("left_chest", 30000).escalated, false);
  // The worksheet has escalated a cap since 2026-09-20; moving the rule here
  // must not change what it prints.
  assert.strictEqual(f.hoopingAdvice("hat_front", 30000).escalated, true);
});

test("an unknown garment gets no advice rather than the pique fallback", () => {
  assert.strictEqual(f.hoopingAdvice("no_such_garment", 5000), null);
  assert.strictEqual(f.hoopingAdvice("", 5000), null);
  assert.strictEqual(f.hoopingAdvice(null, 5000), null);
  // A missing stitch count is "not heavy", not a crash.
  assert.strictEqual(f.hoopingAdvice("tote").backing, "tearaway");
});
