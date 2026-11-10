// The launch starter pack (app/public/starter/, docs/starter-pack-2026-11-10.md).
// Three guards on what ships to customers: every design's licence is on Kent's
// strict allowlist (2026-11-10), every file is the exact one the manifest
// recorded, and every DST decodes with our own importer to the recorded stitch
// count.
const assert = require("node:assert");
const { test } = require("node:test");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { decodeDST } = require("../src/dstimport.js");

const DIR = path.join(__dirname, "..", "app", "public", "starter");
const manifest = JSON.parse(fs.readFileSync(path.join(DIR, "manifest.json"), "utf8"));
// Kent's ruling 2026-11-10: CC0 or a public-domain mark on the art's own page.
// CC-BY, CC-BY-SA, NC, ND, "personal use" and unknown terms are all excluded.
const ALLOWED = new Set(["CC0", "Public domain", "Public Domain Mark"]);

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(path.join(DIR, file))).digest("hex");
}

test("starter pack has 12 designs with unique ids", () => {
  assert.strictEqual(manifest.designs.length, 12);
  assert.strictEqual(new Set(manifest.designs.map((d) => d.id)).size, 12);
});

test("every starter design's licence is on the strict allowlist", () => {
  for (const d of manifest.designs) {
    assert.ok(ALLOWED.has(d.license), `${d.id}: licence "${d.license}" is not allowed`);
    assert.match(d.source_page_url, /^https:\/\//, `${d.id}: no source page`);
    assert.ok(d.author && d.checked, `${d.id}: author and check date are required`);
  }
});

test("every starter file matches its recorded sha256", () => {
  for (const d of manifest.designs) {
    assert.strictEqual(sha256(d.art), d.art_sha256, `${d.id}: ${d.art} changed`);
    assert.strictEqual(sha256(d.dst), d.dst_sha256, `${d.id}: ${d.dst} changed`);
  }
});

test("every starter DST decodes to the recorded stitch and colour counts", () => {
  for (const d of manifest.designs) {
    const decoded = decodeDST(new Uint8Array(fs.readFileSync(path.join(DIR, d.dst))));
    assert.strictEqual(decoded.stitchCount, d.stitches, `${d.id}: stitch count`);
    assert.strictEqual(decoded.colorCount, d.colors, `${d.id}: colour count`);
    // Fits a 4x4 in (100 mm) hoop.
    assert.ok(decoded.widthMM <= 100 && decoded.heightMM <= 100, `${d.id}: larger than 100 mm`);
  }
});
