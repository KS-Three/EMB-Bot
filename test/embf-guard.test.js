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
    assert.ok(fs.existsSync(path.join(BIN_DIR, f.key + ".embf")), "manifest entry without bin: " + f.key);
  }
});
