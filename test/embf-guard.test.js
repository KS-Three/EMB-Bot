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
  .filter((f) => f.endsWith(".json") && !f.startsWith("manifest"))
  .map((f) => f.replace(/\.json$/, ""));

test("every static shipped font has a committed .embf", () => {
  // Was ">= 21" (the original static library). License-audit pulls shrank
  // the static set: items 1-3 removed milli_marif_bold + tt_masters
  // (2026-08-04), and the same-day ShareAlike removal (audit §9) pulled
  // aventurina, emilio_20, emilio_20_bold, geneva_simple, monicha —
  // geneva_simple and emilio_20_bold live on as test fixtures under
  // test/fixtures/fonts/, deliberately OUTSIDE this directory so the
  // "static JSON here ⇒ shipped" invariant this file pins stays true.
  assert.ok(keys.length >= 14, "expected >=14 font JSONs, found " + keys.length);
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
    // <= 500: attributions are COMPLETE notices now (first paragraph +
    // upstream copyright line — font-license-audit-2026-07-31.md item 4;
    // longest real one is caesarus_SC_FI at ~350). The cap still catches a
    // whole-license-blob regression, which starts at ~4 KB.
    assert.ok(typeof f.attribution === "string" && f.attribution.length > 0 && f.attribution.length <= 500,
      "missing/oversized attribution: " + f.key);
    // no truncation artifacts: a credit must not end mid-clause (ellipsis,
    // dangling "by"/colon) — the exact defect class the audit's §2 table lists
    assert.ok(!/…$|\bby\s*$|:$/.test(f.attribution.trim()), "truncated attribution: " + f.key);
    assert.strictEqual(f.name, f.name.trim(), "name has stray whitespace: " + f.key);
    assert.ok(typeof f.source === "string" && f.source.length > 0, "missing source: " + f.key);
    assert.ok(fs.existsSync(path.join(BIN_DIR, f.key + ".embf")), "manifest entry without bin: " + f.key);
    // audit item 5: the full license text of record must exist on disk for
    // EVERY shipped font (OFL condition 2 — full text with every copy)
    assert.ok(fs.existsSync(path.join(FONT_DIR, f.key + ".LICENSE.txt")),
      "missing LICENSE.txt sidecar: " + f.key);
  }
});

test("every shipped binary embeds the full license text (bare-binary hole)", () => {
  // font-license-audit-2026-07-31.md item 8: the credits screen offers a
  // direct .embf download, so each binary must carry the complete license +
  // copyright notice in its metadata (OFL condition 2 explicitly blesses
  // machine-readable metadata fields). The embedded text must BE the sidecar
  // text — not a summary of it. Aggregated failures, same reasoning as the
  // qc-gate test below.
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const failures = [];
  for (const f of man.fonts) {
    const sidecar = fs.readFileSync(path.join(FONT_DIR, f.key + ".LICENSE.txt"), "utf8").trim();
    const bin = fb.decodeFontBin(fs.readFileSync(path.join(BIN_DIR, f.key + ".embf")));
    if (String(bin.license || "").trim() !== sidecar) failures.push(f.key);
  }
  assert.deepStrictEqual(failures, [], "binaries whose embedded license != sidecar");
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
  // Mirrors the PULLED set in tools/build-embf.mjs (the source of truth —
  // not importable here: that script runs the whole build at import time).
  // Pulled fonts are legitimately absent from the manifest despite their
  // verified tier: audit items 1-3 (2026-08-04, first four) plus the same-day
  // ShareAlike pull (audit §9, the rest). Keep in sync with build-embf.mjs.
  const PULLED = new Set(["milli_marif_bold", "tt_directors", "tt_masters",
    "dejavufont", "apex_lake", "aventurina", "bluenesia_satin",
    "cherryforinkstitch", "cherryforkaalleen", "emilio_20", "emilio_20_bold",
    "emilio_20_simple", "emilio_20_simple_small", "geneva_rounded",
    "geneva_simple", "gingo200", "monicha"]);
  const ALLOWED_MISSING = new Set(["precious", ...PULLED]); // precious: GPL-3.0 — outside license policy
  for (const t of tiers.filter((x) => x.tier === "verified"))
    if (!manKeys.has(t.pack))
      assert.ok(ALLOWED_MISSING.has(t.pack), "verified font missing from manifest: " + t.pack);
});

test("qc gate: every committed font JSON passes the tier gate", async () => {
  // The ltr/-dir import (mai_en_fleur wave) made committed JSONs the shipping
  // path for new fonts again, so the tier gate has to hold for ALL of them,
  // not just at import time. Aggregate failures into one assert — per-entry
  // asserts over 24 multi-MB fonts have blown test timeouts before.
  const { qcFont } = await import("../tools/qc-font.mjs");
  const failures = [];
  for (const k of keys) {
    const font = JSON.parse(fs.readFileSync(path.join(FONT_DIR, k + ".json"), "utf8"));
    const r = qcFont(font);
    if (!r.pass) failures.push(k + ": " + r.findings.join("; "));
  }
  assert.deepStrictEqual(failures, []);
});

test("ltr/-dir layout imports: shipped set is exactly the license+QC survivors", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const byKey = Object.fromEntries(man.fonts.map((f) => [f.key, f]));
  // The five ltr/-directory fonts in scratch_ink: three shipped...
  const want = { ags_garamond_latin_grec: 255, mai_en_fleur: 67, sunset: 150 };
  const got = {};
  for (const k of Object.keys(want)) if (byKey[k]) got[k] = byKey[k].glyphCount;
  assert.deepStrictEqual(got, want, "shipped ltr/-dir fonts drifted");
  for (const k of Object.keys(want)) {
    assert.strictEqual(byKey[k].licenseId, "OFL-1.1", k + " license drifted");
    assert.ok(fs.existsSync(path.join(FONT_DIR, k + ".LICENSE.txt")), "missing LICENSE.txt for " + k);
    assert.ok(fs.existsSync(path.join(FONT_DIR, "previews", k + ".png")), "missing preview for " + k);
  }
  // ...and two dropped: honoka (QC hard fail — no Latin letter glyphs) and
  // roman_ags_bicolor (single-color pipeline stacks its two color layers as
  // doubled satin; its mono variant would just duplicate shipped roman_ags).
  for (const k of ["honoka", "roman_ags_bicolor"])
    assert.ok(!byKey[k], k + " must not ship (dropped by the ltr/ import)");
});

test("no shipped NEW font has a license outside the allowed policy set", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const ALLOWED = new Set(["OFL-1.1", "CC-BY-4.0", "CC-BY-SA-4.0", "CC0"]);
  const grandfathered = new Set(fs.readdirSync(FONT_DIR)
    .filter((f) => f.endsWith(".json") && !f.startsWith("manifest"))
    .map((f) => f.replace(/\.json$/, "")));
  // geneva_rounded ships from scratch_ink (a trial import, not a static
  // src/fonts/<key>.json) but is the same grandfathered CC-BY-SA-2.5 grant
  // as its geneva_simple sibling — see build-embf.mjs's licenseId() comment.
  grandfathered.add("geneva_rounded");
  for (const f of man.fonts)
    if (!grandfathered.has(f.key))
      assert.ok(ALLOWED.has(f.licenseId), f.key + " ships with disallowed license " + f.licenseId);
});
