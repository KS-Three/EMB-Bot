// Spec §4.1a guard: for every currently-shipped font, the binary round-trip
// must equal the quantized reference EXACTLY, and lettering built from the
// decoded font must be structurally sound. This test must be green before
// satin-fonts.js leaves the Studio pipeline (Task 3).
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
const BIN_DIR = path.join(FONT_DIR, "bin");
const keys = fs.readdirSync(FONT_DIR)
  .filter((f) => f.endsWith(".json") && f !== "manifest.json")
  .map((f) => f.replace(/\.json$/, ""));

test("all 21 shipped fonts have a committed .embf", () => {
  assert.ok(keys.length >= 21, "expected >=21 font JSONs, found " + keys.length);
  for (const k of keys)
    assert.ok(fs.existsSync(path.join(BIN_DIR, k + ".embf")), "missing bin for " + k);
});

for (const k of keys) {
  test("decoder guard: " + k, () => {
    const ref = JSON.parse(fs.readFileSync(path.join(FONT_DIR, k + ".json"), "utf8"));
    const bin = fs.readFileSync(path.join(BIN_DIR, k + ".embf"));
    assert.deepStrictEqual(fb.decodeFontBin(bin), fb.quantizeFont(ref, 4));
  });
}

test("manifest lists every shipped font exactly once, verified tier only", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const manKeys = man.fonts.map((f) => f.key);
  assert.strictEqual(new Set(manKeys).size, manKeys.length, "duplicate keys");
  for (const k of keys) assert.ok(manKeys.includes(k), "manifest missing " + k);
  for (const f of man.fonts) {
    assert.strictEqual(f.tier, "verified");
    assert.ok(f.name && f.licenseId && f.sizeMm > 0 && f.glyphCount > 0, "bad entry " + f.key);
    assert.ok(typeof f.attribution === "string" && f.attribution.length > 0 && f.attribution.length <= 200,
      "missing/oversized attribution: " + f.key);
    assert.ok(typeof f.source === "string" && f.source.length > 0, "missing source: " + f.key);
    assert.ok(fs.existsSync(path.join(BIN_DIR, f.key + ".embf")), "manifest entry without bin: " + f.key);
  }
});

test("category coverage: known groups only, More is a small remainder", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const KNOWN = new Set(["Sans", "Serif", "Script", "Display", "Small", "More"]);
  for (const f of man.fonts) assert.ok(KNOWN.has(f.group), `unknown group ${f.group} on ${f.key}`);
  const more = man.fonts.filter((f) => f.group === "More");
  assert.ok(more.length <= 5, "More is a dumping ground: " + more.map((f) => f.key).join(", "));
});

test("no orphan .embf files — every binary has a manifest entry", () => {
  // The reverse direction of the entry-has-bin check above. Without it, a
  // demoted or license-excluded font's stale binary could linger in bin/ and
  // ship from a dirty tree (this exact thing happened with ondulamarif_XL).
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const manKeys = new Set(man.fonts.map((f) => f.key));
  for (const f of fs.readdirSync(BIN_DIR)) {
    if (!f.endsWith(".embf")) continue;
    const key = f.replace(/\.embf$/, "");
    assert.ok(manKeys.has(key), "orphan binary with no manifest entry: " + f);
  }
});

test("every verified-tier font is in the manifest or explicitly excluded by license", () => {
  const tiersPath = path.join(__dirname, "..", "scratch_ink", "_tiers.json");
  if (!fs.existsSync(tiersPath)) return; // scratch material absent in some checkouts
  const tiers = JSON.parse(fs.readFileSync(tiersPath, "utf8"));
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const manKeys = new Set(man.fonts.map((f) => f.key));
  const ALLOWED_MISSING = new Set(["precious"]); // GPL-3.0 — outside license policy
  for (const t of tiers.filter((x) => x.tier === "verified"))
    if (!manKeys.has(t.pack))
      assert.ok(ALLOWED_MISSING.has(t.pack), "verified font missing from manifest: " + t.pack);
});

test("no shipped NEW font has a license outside the allowed policy set", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const ALLOWED = new Set(["OFL-1.1", "CC-BY-4.0", "CC-BY-SA-4.0", "CC0"]);
  const grandfathered = new Set(fs.readdirSync(FONT_DIR)
    .filter((f) => f.endsWith(".json") && f !== "manifest.json")
    .map((f) => f.replace(/\.json$/, "")));
  // geneva_rounded ships from scratch_ink (a trial import, not a static
  // src/fonts/<key>.json) but is the same grandfathered CC-BY-SA-2.5 grant
  // as its geneva_simple sibling — see build-embf.mjs's licenseId() comment.
  grandfathered.add("geneva_rounded");
  for (const f of man.fonts)
    if (!grandfathered.has(f.key))
      assert.ok(ALLOWED.has(f.licenseId), f.key + " ships with disallowed license " + f.licenseId);
});
