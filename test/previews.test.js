const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");

const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
const PREV_DIR = path.join(FONT_DIR, "previews");

test("every manifest font has a committed preview PNG", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  for (const f of man.fonts) {
    const p = path.join(PREV_DIR, f.key + ".png");
    assert.ok(fs.existsSync(p), "missing preview: " + f.key);
    const buf = fs.readFileSync(p);
    assert.ok(buf.length > 200, "suspiciously tiny preview (blank?): " + f.key);
    assert.strictEqual(buf.readUInt32BE(0), 0x89504e47, "not a PNG: " + f.key);
  }
});

test("no orphan previews", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const keys = new Set(man.fonts.map((f) => f.key));
  for (const f of fs.readdirSync(PREV_DIR)) {
    if (!f.endsWith(".png")) continue;
    assert.ok(keys.has(f.replace(/\.png$/, "")), "orphan preview: " + f);
  }
});
