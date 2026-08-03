---
name: add-font
description: Evaluate and import a new satin embroidery font into EMB-Bot's font library. Use when asked to add, import, vet, or license-check a candidate font for the Studio's font browser.
---

# Adding a font to EMB-Bot

## What qualifies

- **Must be Ink/Stitch-style**: real hand-authored `<path inkstitch:satin_column>`
  rails+rungs satin data, not an auto-traced outline font. This is a settled
  decision (COOKBOOK.md) — outline-font auto-tracing was already rejected as
  lower quality than hand-authored satin columns; don't relitigate it.
  Canonical source: the upstream Ink/Stitch embroidery-fonts collection
  (github.com/inkstitch/embroidery-fonts) — any font with genuine satin-column
  paths from that ecosystem or an equivalent source qualifies.
- **License must be permissive**: `tools/build-embf.mjs`'s `ALLOWED_LICENSES`
  is exactly `OFL-1.1`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC0`. GPL is hard-excluded
  (`precious` is the existing example). Anything else — commercial/all-rights-
  reserved, an aggregator-only license claim with no traceable source, an
  ad-hoc "see license file" grant — is not eligible for a *new* font. Don't
  add it; flag it the way `docs/font-license-audit-2026-07-31.md` flagged
  `tt_directors`/`tt_masters` (OFL claim traceable only to a listing site,
  while the foundry sells the family commercially) and read that doc for what
  an ambiguous case looks like.
- Check the license **before** doing any import work — reading `font.json` /
  `LICENSE` first is cheaper than running the whole pipeline on a font that
  turns out ineligible.

## Pipeline

1. `scratch_ink/<key>/` needs `font.json` + `LICENSE` + either `ltr.svg` or
   `ltr/*.svg` (the multi-file variant layout). `scratch_ink/` is gitignored;
   recreate or extend it from the upstream Ink/Stitch embroidery-fonts clone
   (see COOKBOOK.md's "Binary font library" section).
2. Parse it to a trial import:
   ```
   node tools/build-font.mjs scratch_ink/<key> scratch_ink/_out/<key>.json
   ```
3. Run the QC gate:
   ```
   node tools/qc-font.mjs scratch_ink/_out/<key>.json
   ```
   Must not hard-fail. Hard-fail = 100% of letter glyphs have zero satin
   columns. >10% satinless letter glyphs is also a fail; ≤10% is a warning —
   surface it, don't silently treat it as a pass.
4. **Stop here and report to Kent** — do not add the font to
   `scratch_ink/_tiers.json` as `tier:"verified"` yourself. Tiering is Kent's
   decision (COOKBOOK.md: "only `tier:\"verified\"` ships... unverified =
   internal work queue with a concrete reason per font"). Report back: the QC
   findings, the detected license, and anything the license-audit's per-font
   table would flag (aggregator-only claims, truncated/mojibake attribution
   text, a Reserved Font Name in the source).
5. Once Kent approves, add `{"pack": "<key>", "tier": "verified"}` to
   `scratch_ink/_tiers.json`, then:
   ```
   node tools/build-embf.mjs      # builds .embf + manifest.json; re-derives
                                   # licenseId from the license text and
                                   # re-enforces ALLOWED_LICENSES regardless
                                   # of the tier approval
   node tools/build-previews.mjs  # regenerates font-browser grid PNGs,
                                   # orphan-cleans stale ones
   node --test                    # confirms test/embf-guard.test.js and the
                                   # rest of the suite stay green
   ```

## Pitfalls this project has already hit

- QC/tier classification runs **per letter glyph**, not per file — a font can
  have satin columns somewhere in the file while its actual letters are
  runs-only and stitch as nothing (`ondulamarif_XL`). If a font produces 0
  stitches, check per-glyph `cols` first, not the file-level classification.
- Upstream license text often uses bare-CR (old-Mac) line endings. Splitting
  naively on `\n` turns the whole blob into "line one" and mangles
  attribution (dropped names, truncated clauses, mojibake). Split on
  `/\r\n|\r|\n/`.
- Never let a Reserved Font Name surface as the primary font name in the
  UI/manifest/metadata (e.g. Sortefax, Grand Hotel, Kaushan Script) — rename
  it the way the existing library already does (Grand Hotel → Auberge,
  Kaushan Script → MAM Script, etc.), and keep the "with Reserved Font Name
  X" notice in the shipped credit.
- The Studio's engine-file lists live in **three places** and must stay in
  sync: `app/scripts/copy-engine.mjs` (`ENGINE_FILES`), `app/src/lib/emb.js`
  (`ENGINE_KEYS`), and the `<script>` tags in `app/index.html`. Missing the
  third one broke fonts only in the live browser once — tests preload
  differently and stayed green, so `node --test` passing is not sufficient
  proof a new font actually works in the Studio.

## Compliance note

Shipping a new font needs more than the right `licenseId` —
`docs/font-license-audit-2026-07-31.md` found the existing 69-font library
isn't fully compliant yet (missing full license text on disk for 48 fonts,
several truncated attribution strings). Don't add to that backlog: save the
font's full `LICENSE` text as a sidecar in `src/fonts/` next to its source
JSON from the start, and write a complete, untruncated attribution line
rather than letting it get cut off mid-clause.
