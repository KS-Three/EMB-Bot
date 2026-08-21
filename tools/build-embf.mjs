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

// --personal: Kent's own local build, with EVERY font — ShareAlike, GPL,
// NonCommercial, the license-audit pulls, all of it. Licences govern
// DISTRIBUTION, not private use, so using any font on his own machine is
// unrestricted; what must never happen is one of them reaching a build that
// ships. Kent's framing (2026-08-21) was "all of them for me, questionable ones
// off on the user's end" — a runtime toggle cannot do that, because by the time
// a viewer could flip it the bytes have already been distributed. So the split
// is at BUILD time and the excluded fonts are simply never packaged.
//
// Two properties make this fail-safe rather than merely careful:
//   1. Personal artifacts go to their own paths (bin-personal/,
//      manifest-personal.json), which .gitignore covers — they cannot be
//      committed, so they cannot reach a release by accident.
//   2. A fresh clone and CI have no bin-personal/ at all, so the sale build is
//      clean BY CONSTRUCTION, not by remembering to rebuild.
const PERSONAL = process.argv.includes("--personal");

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const BIN_DIR = join(FONT_DIR, PERSONAL ? "bin-personal" : "bin");
const MANIFEST_PATH = join(FONT_DIR, PERSONAL ? "manifest-personal.json" : "manifest.json");
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
// fonts. CC-BY-SA-4.0 removed 2026-08-04 with the ShareAlike pull above.
// PERMANENT as of 2026-08-21 (Kent): ShareAlike is not coming back. The open
// question was whether SA propagates through the compiled .embf onto the
// stitch files CUSTOMERS generate — if it does, every paying customer's design
// inherits a copyleft obligation. Unbounded liability on the product's core
// output, so it is closed by decision rather than by legal opinion; the
// docs/lawyer-brief-cc-by-sa-2026-08-04.md restore path is retired.
//
// Note what this set does NOT protect against on its own: licenseId() derives
// these ids from license TEXT, and it has been wrong twice — NonCommercial and
// NoDerivatives both resolved to plain "CC-BY-4.0" until 2026-08-21, and a
// non-CC license body under an OFL/CC header claim still mislabels today
// (roman_ags, GUST/LPPL). Adding a font is a text-reading job, not an id-
// trusting one. See docs/font-expansion-research-2026-08-21.md §5 and §9.
const ALLOWED_LICENSES = new Set(["OFL-1.1", "CC-BY-4.0", "CC0"]);
const GRANDFATHERED = new Set(
  readdirSync(FONT_DIR)
    .filter((f) => f.endsWith(".json") && !f.startsWith("manifest"))
    .map((f) => f.replace(/\.json$/, ""))
);
// (A geneva_rounded grandfather entry lived here until 2026-08-04 — moot
// now that every ShareAlike font is in PULLED, which is checked first.)

// 1. Shipped fonts: every src/fonts/<key>.json is verified by definition
//    (they are the 21 Kent already ships).
const sources = [];
for (const f of readdirSync(FONT_DIR)) {
  if (f.endsWith(".json") && !f.startsWith("manifest"))
    sources.push({ key: f.replace(/\.json$/, ""), path: join(FONT_DIR, f), tier: "verified" });
}

// 1b. --personal: take EVERY trial import in scratch_ink/_out, not just the
//     tier-approved ones. _tiers.json is Kent's SALE approval list and must
//     keep that meaning — adding fonts to it to get them into a personal build
//     would quietly promote them into the sellable library too, which is
//     exactly the kind of silent widening this file has been bitten by before.
//     "Personal" means every font on hand; "verified" still means shippable.
if (PERSONAL) {
  const outDir = join(root, "scratch_ink", "_out");
  if (existsSync(outDir)) {
    const have = new Set(sources.map((s) => s.key));
    for (const f of readdirSync(outDir)) {
      if (!f.endsWith(".json")) continue;
      const key = f.replace(/\.json$/, "");
      if (have.has(key)) continue;
      sources.push({ key, path: join(outDir, f), tier: "verified" });
      have.add(key);
    }
  }
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

// Would this font sew anything at all? Same predicate qc-font.mjs uses: a
// letter glyph stitches if it has satin columns, or a run carrying an authored
// stitch length. --personal sweeps in every trial import, and 26 of them are
// cross-stitch/fill fonts the lettering path cannot stitch yet — listing 26
// dead entries in the font browser is worse than omitting them. Deliberately a
// STITCHABILITY gate, not a license one, so those fonts light up on their own
// the day a fill/cross-stitch lettering path exists, with no change here.
const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
function sewsAnything(font) {
  const gs = font.glyphs || {};
  for (const c of LETTERS) {
    const g = gs[c];
    if (!g) continue;
    if ((g.cols || []).length) return true;
    if ((g.runs || []).some((r) => r && r.pts && r.lenMm > 0)) return true;
  }
  return false;
}

mkdirSync(BIN_DIR, { recursive: true });
const manifest = [];
const skippedDead = [];
for (const s of sources.sort((a, b) => a.key.localeCompare(b.key))) {
  // font-license-audit-2026-07-31.md items 1-3: pulled regardless of
  // grandfathered status — see the PULLED comment above for per-font reasons.
  // --personal keeps them: private use is not distribution.
  if (PULLED.has(s.key) && !PERSONAL) {
    console.warn("PULLED (license audit):", s.key);
    const stale = join(BIN_DIR, s.key + ".embf");
    if (existsSync(stale)) unlinkSync(stale);
    continue;
  }

  const font = JSON.parse(readFileSync(s.path, "utf8"));

  // Personal-only stitchability gate (see sewsAnything above). Never applied to
  // the sellable build, whose contents are tier-approved by Kent and must not
  // change shape because of a predicate here.
  if (PERSONAL && !sewsAnything(font)) {
    skippedDead.push(s.key);
    const stale = join(BIN_DIR, s.key + ".embf");
    if (existsSync(stale)) unlinkSync(stale);
    continue;
  }

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
  // --personal skips the policy entirely — it is a private build.
  if (!PERSONAL && !GRANDFATHERED.has(s.key) && !ALLOWED_LICENSES.has(id)) {
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
writeFileSync(MANIFEST_PATH,
  JSON.stringify({ version: 1, personal: PERSONAL || undefined, fonts: manifest }, null, 1));
if (PERSONAL) {
  if (skippedDead.length)
    console.warn("skipped " + skippedDead.length + " font(s) that stitch nothing yet (cross-stitch/fill — " +
      "no lettering path for them): " + skippedDead.join(" "));
  console.warn("\n*** PERSONAL BUILD — NOT FOR DISTRIBUTION ***");
  console.warn("Includes ShareAlike / GPL / NonCommercial / license-pulled fonts.");
  console.warn("Written to src/fonts/bin-personal/ + manifest-personal.json (both gitignored).");
  console.warn("Run `node tools/build-embf.mjs` with no flag for the sellable library.\n");
}
const total = manifest.reduce((a, f) => a + f.bytes, 0);
console.log("built", manifest.length, "fonts,", (total / 1048576).toFixed(2), "MB binary");
