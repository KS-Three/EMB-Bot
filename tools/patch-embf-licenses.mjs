// In-place license/attribution fix for the shipped font library — audit
// items 4, 8, 9 of docs/font-license-audit-2026-07-31.md, for checkouts
// WITHOUT scratch_ink/ (46 of the 68 shipped fonts have no local source
// JSON; a full `node tools/build-embf.mjs` rebuild is impossible here).
//
//   node tools/patch-embf-licenses.mjs
//
// For every font in src/fonts/manifest.json:
//   1. Reads the sidecar src/fonts/<key>.LICENSE.txt (the text of record).
//   2. Decodes src/fonts/bin/<key>.embf, replaces its embedded `license`
//      field with the FULL sidecar text (item 8: OFL condition 2 — the
//      complete license + copyright notice must travel with every copy;
//      machine-readable metadata fields are explicitly blessed), trims the
//      `name` field (initials_medium shipped with a trailing space), and
//      re-encodes. Round-trip is verified before writing.
//   3. Regenerates the manifest entry's attribution + licenseId + bytes via
//      the SAME tools/font-license.mjs logic build-embf.mjs now uses, so a
//      future scratch_ink rebuild produces identical output.
//   4. For fonts that DO have a static src/fonts/<key>.json, the JSON's
//      license/name fields are updated to match — test/embf-guard.test.js
//      pins decode(bin) == quantizeFont(srcJson), so binary and source must
//      move together.
//
// Idempotent: a second run is a no-op.
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import assert from "node:assert";
import { deriveLicenseFields } from "./font-license.mjs";

const require = createRequire(import.meta.url);
const fb = require("../src/fontbin.js");

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const BIN_DIR = join(FONT_DIR, "bin");

const manifestPath = join(FONT_DIR, "manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

let binPatched = 0, jsonPatched = 0, missing = 0;
for (const entry of manifest.fonts) {
  const licPath = join(FONT_DIR, entry.key + ".LICENSE.txt");
  if (!existsSync(licPath)) {
    console.error("NO SIDECAR (skipped, manifest untouched):", entry.key);
    missing++;
    continue;
  }
  const fullLicense = readFileSync(licPath, "utf8").trim();
  const { licenseId, attribution } = deriveLicenseFields(entry.key, fullLicense);

  // --- patch the binary ---------------------------------------------------
  const binPath = join(BIN_DIR, entry.key + ".embf");
  const bin = readFileSync(binPath);
  const q = bin[5]; // quantization from the EMBF header
  const font = fb.decodeFontBin(bin);
  const before = JSON.stringify([font.license, font.name]);
  font.license = fullLicense;
  font.name = String(font.name || entry.key).trim();
  if (JSON.stringify([font.license, font.name]) !== before) {
    const bytes = fb.encodeFontBin(font, q);
    // decode(encode(x)) == quantize(x); font is already quantized (it came
    // out of the decoder), so quantization is the identity here.
    assert.deepStrictEqual(fb.decodeFontBin(bytes), fb.quantizeFont(font, q),
      "round-trip mismatch after license patch: " + entry.key);
    writeFileSync(binPath, bytes);
    entry.bytes = bytes.length;
    binPatched++;
  }

  // --- keep static source JSONs in lockstep with their binaries -----------
  const jsonPath = join(FONT_DIR, entry.key + ".json");
  if (existsSync(jsonPath)) {
    const src = JSON.parse(readFileSync(jsonPath, "utf8"));
    if (src.license !== fullLicense || src.name !== String(src.name || "").trim()) {
      src.license = fullLicense;
      src.name = String(src.name || entry.key).trim();
      writeFileSync(jsonPath, JSON.stringify(src));
      jsonPatched++;
    }
  }

  // --- manifest fields ----------------------------------------------------
  entry.name = String(entry.name || entry.key).trim();
  entry.licenseId = licenseId;
  entry.attribution = attribution;
}

writeFileSync(manifestPath, JSON.stringify(manifest, null, 1));
console.log("patched", binPatched, "binaries,", jsonPatched, "source JSONs;",
  manifest.fonts.length, "manifest entries regenerated;", missing, "missing sidecars");
if (missing > 0) process.exit(1);
