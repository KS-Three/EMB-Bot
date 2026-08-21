// Builds the binary font library + manifest from source JSONs.
//   node tools/build-embf.mjs
// Inputs:  src/fonts/<key>.json           (the 21 shipped fonts)
//          scratch_ink/_out/<key>.json    (trial imports of new fonts)
//          scratch_ink/_tiers.json        (tier classification, Kent-approved)
//          tools/font-categories.json     (display groups)
// Outputs: src/fonts/bin/<key>.embf   (VERIFIED tier only)
//          src/fonts/manifest.json
// Idempotent; safe to re-run. scratch_ink/ is gitignored source material —
// the committed artifacts are the .embf files and the manifest.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, unlinkSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import assert from "node:assert";
const require = createRequire(import.meta.url);
const fb = require("../src/fontbin.js");

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const BIN_DIR = join(FONT_DIR, "bin");
const GROUPS = JSON.parse(readFileSync(join(root, "tools", "font-categories.json"), "utf8"));

// License id detection + attribution extraction live in tools/font-license.mjs,
// SHARED with tools/patch-embf-licenses.mjs so a scratch_ink rebuild and an
// in-place patch can never derive different notices from the same text.
// (Audit item 4: the old first-line extraction truncated credits mid-sentence
// and dropped names that sat past a bare-CR line break.)
import { licenseId, deriveLicenseFields } from "./font-license.mjs";

// docs/font-license-audit-2026-07-31.md, action checklist items 1-3: these 4
// fonts are PULLED from the shipping library regardless of grandfathered
// status. Skipped unconditionally below, before the license-policy check.
//   - milli_marif_bold: standing PULL decision (§4) — the sidecar LICENSE.txt
//     is an ad-hoc French permission email plus an appended full OFL-1.1
//     text, but no written confirmation on file that the grant covers
//     commercial embroidery distribution. Revisit if that confirmation is
//     obtained.
//   - tt_directors, tt_masters: the OFL-1.1 claim is traceable only to a
//     1001fonts aggregator listing while the TypeType foundry sells these
//     families commercially on MyFonts — no verifiable primary source.
//   - dejavufont: labeled CC-BY-SA-4.0, but the upstream LICENSE (fetched
//     2026-08-04 from github.com/inkstitch/embroidery-fonts/src/dejavufont/
//     LICENSE, sourced from fontsquirrel.com/license/dejavu-serif) is
//     actually the Bitstream Vera Fonts License v1.00 + Arev Fonts License —
//     neither is CC-BY-SA, neither is in ALLOWED_LICENSES below, and both
//     forbid selling the font typeface by itself (only "as part of a larger
//     software package"). The digitizer's own CC-BY-SA claim only covers
//     their embroidery adaptation, not the underlying Bitstream/Arev
//     copyright — and licenseId() below would keep mislabeling it CC-BY-SA
//     on any rebuild, since the CC-BY-SA regex matches the adapter's header
//     line before ever reaching the real license text further down the same
//     blob. Pulled rather than relabeled until that detection gap is fixed
//     and/or Kent decides whether Bitstream-Vera-derived fonts should join
//     the allowed policy set.
const PULLED = new Set(["milli_marif_bold", "tt_directors", "tt_masters", "dejavufont"]);
// 2026-08-04 (second wave, Kent's explicit call): every ShareAlike font is
// pulled — all 13 then in the library (11 CC-BY-SA-4.0 + the 2 CC-BY-SA-2.5
// Geneva fonts; the audit's "14" included dejavufont, pulled above for its
// own reasons). Not a defect in the fonts: the open legal question
// (docs/lawyer-brief-cc-by-sa-2026-08-04.md) is whether ShareAlike attaches
// to compiled .embf binaries and propagates onto CUSTOMER stitch files —
// removal makes the paid launch unambiguous without waiting on counsel.
// Deliberately reversible: restore any of these by removing them here and
// re-adding their manifest/bin/preview/sidecar artifacts (git history has
// them all), should a legal opinion clear ShareAlike later.
for (const k of ["apex_lake", "aventurina", "bluenesia_satin",
                 "cherryforinkstitch", "cherryforkaalleen", "emilio_20",
                 "emilio_20_bold", "emilio_20_simple", "emilio_20_simple_small",
                 "geneva_rounded", "geneva_simple", "gingo200", "monicha"]) {
  PULLED.add(k);
}

// Fix 2: license policy — only these ids may ship for NEW (non-grandfathered)
// fonts. CC-BY-SA-4.0 removed 2026-08-04 with the ShareAlike pull above: no
// new ShareAlike font may enter the library while the propagation question
// is unresolved.
const ALLOWED_LICENSES = new Set(["OFL-1.1", "CC-BY-4.0", "CC0"]);
const GRANDFATHERED = new Set(
  readdirSync(FONT_DIR)
    .filter((f) => f.endsWith(".json") && f !== "manifest.json")
    .map((f) => f.replace(/\.json$/, ""))
);
// (A geneva_rounded grandfather entry lived here until 2026-08-04 — moot
// now that every ShareAlike font is in PULLED, which is checked first.)

// 1. Shipped fonts: every src/fonts/<key>.json is verified by definition
//    (they are the 21 Kent already ships).
const sources = [];
for (const f of readdirSync(FONT_DIR)) {
  if (f.endsWith(".json") && f !== "manifest.json")
    sources.push({ key: f.replace(/\.json$/, ""), path: join(FONT_DIR, f), tier: "verified" });
}

// 2. New fonts: verified tier per _tiers.json, data from the trial imports.
const tiersPath = join(root, "scratch_ink", "_tiers.json");
if (existsSync(tiersPath)) {
  const tiers = JSON.parse(readFileSync(tiersPath, "utf8"));
  const have = new Set(sources.map((s) => s.key));
  for (const t of tiers) {
    if (t.tier !== "verified" || have.has(t.pack)) continue;
    const p = join(root, "scratch_ink", "_out", t.pack + ".json");
    if (!existsSync(p)) { console.warn("SKIP (no trial import):", t.pack); continue; }
    sources.push({ key: t.pack, path: p, tier: "verified" });
  }
} else if (process.argv.includes("--shipped-only")) {
  console.warn("scratch_ink/_tiers.json absent — building shipped fonts only (--shipped-only)");
} else {
  // Without the tier data this build would write a 21-font manifest while
  // leaving the other ~48 .embf files in place — bin/ and manifest would go
  // silently inconsistent. Refuse instead; see COOKBOOK for recreating
  // scratch_ink/, or pass --shipped-only to accept the reduced build.
  console.error("ERROR: scratch_ink/_tiers.json absent. Refusing to build an " +
    "inconsistent library. Recreate scratch_ink/ (see COOKBOOK.md) or pass --shipped-only.");
  process.exit(1);
}

mkdirSync(BIN_DIR, { recursive: true });
const manifest = [];
for (const s of sources.sort((a, b) => a.key.localeCompare(b.key))) {
  // font-license-audit-2026-07-31.md items 1-3: pulled regardless of
  // grandfathered status — see the PULLED comment above for per-font reasons.
  if (PULLED.has(s.key)) {
    console.warn("PULLED (license audit):", s.key);
    const stale = join(BIN_DIR, s.key + ".embf");
    if (existsSync(stale)) unlinkSync(stale);
    continue;
  }

  const font = JSON.parse(readFileSync(s.path, "utf8"));
  // Audit items 5+8: the sidecar src/fonts/<key>.LICENSE.txt is the license
  // text of record (full upstream text, reconstructed 2026-08-04 for all 68
  // fonts). Embed the FULL text in the binary's license field — the OFL
  // requires the complete license + copyright notice to travel with every
  // copy, and machine-readable metadata is an explicitly blessed channel
  // (~4.5 KB per font). A font with no sidecar falls back to whatever its
  // source JSON carried, and the guard test will flag the missing file.
  const licPath = join(FONT_DIR, s.key + ".LICENSE.txt");
  const fullLicense = existsSync(licPath)
    ? readFileSync(licPath, "utf8").trim()
    : String(font.license || "");
  font.license = fullLicense;
  // Trim the EMBEDDED name too, not just the manifest entry below. The audit
  // fixed initials_medium's trailing space ("Initials Medium ") in place via
  // patch-embf-licenses.mjs, which trims font.name before re-encoding — but
  // this build did not, so any scratch_ink rebuild silently reverted the
  // binary to the untrimmed name while the manifest stayed clean. Keep the
  // two writers in agreement; see patch-embf-licenses.mjs.
  font.name = String(font.name || s.key).trim();
  const id = licenseId(fullLicense);

  // Fix 2: enforce license policy on NEW (non-grandfathered) fonts.
  if (!GRANDFATHERED.has(s.key) && !ALLOWED_LICENSES.has(id)) {
    console.warn("EXCLUDED (license " + id + "):", s.key);
    const stale = join(BIN_DIR, s.key + ".embf");
    if (existsSync(stale)) unlinkSync(stale);
    continue;
  }

  const bytes = fb.encodeFontBin(font, 4);
  // self-check every font on every build — cheap, and catches codec drift
  const back = fb.decodeFontBin(bytes);
  const want = fb.quantizeFont(font, 4);
  try {
    assert.deepStrictEqual(back, want);
  } catch (e) {
    throw new Error("round-trip mismatch: " + s.key + " — " + e.message);
  }
  writeFileSync(join(BIN_DIR, s.key + ".embf"), bytes);
  // User-visible attribution: first paragraph of the license text plus the
  // upstream copyright notice — see extractAttribution in font-license.mjs
  // for the full rules (and ATTRIBUTION_OVERRIDES for the hand-checked
  // exceptions like the Geneva/Hershey credit).
  const attribution = deriveLicenseFields(s.key, fullLicense).attribution
    || (font.name + " — see license inside the font binary");
  manifest.push({
    key: s.key,
    // .trim(): initials_medium shipped as "Initials Medium " (audit §2)
    name: (font.name || s.key).trim(),
    tier: s.tier,
    group: GROUPS[s.key] || "More",
    licenseId: id,
    sizeMm: font.sizeMm || 0,
    glyphCount: Object.keys(font.glyphs || {}).length,
    bytes: bytes.length,
    attribution,
    source: font.source || "Ink/Stitch embroidery-fonts",
  });
}
writeFileSync(join(FONT_DIR, "manifest.json"),
  JSON.stringify({ version: 1, fonts: manifest }, null, 1));
const total = manifest.reduce((a, f) => a + f.bytes, 0);
console.log("built", manifest.length, "fonts,", (total / 1048576).toFixed(2), "MB binary");
