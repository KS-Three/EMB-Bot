# Area 2 — Font library & lettering

**Part of [`MASTER_SCOPE.md`](../../MASTER_SCOPE.md)** — this is the detail
for one capability area. The live one-line verdict (Status / Confidence /
what is next) is in MASTER_SCOPE; this file is the supporting record.

**Claim discipline:** a claim here should carry a `(verb date — source)`
pointer — `confirmed` = checked against code or a passing test, `measured` =
a number was produced, `suspected` = neither. Much of this file predates that
rule and is **not yet annotated**; anything unannotated is unverified until
someone checks it. Test counts, stitch counts and corpus grades written here
were snapshots when written — do not quote one as a current baseline.
Dated narrative belongs in [`../scope-history.md`](../scope-history.md).

---

The pre-digitized font library, browser UI, EMBF binary format, the add-font
QC/tier pipeline, and Text mode. Expandable — but every addition is gated by
the licence rule below (Kent: don't risk copyright infringement if this ever
sells).

## What the library is

**85 fonts in the sellable build** *(confirmed 2026-08-22 —
`src/fonts/manifest.json`, engine suite)*. Two builds are produced from one
source tree:

| Build | Command | Contents |
|---|---|---|
| Sellable | `node tools/build-embf.mjs` | 85 fonts, all inside `ALLOWED_LICENSES` |
| Personal | `node tools/build-embf.mjs --personal` | 120 fonts, adds ShareAlike / NC / GPL / pulled |

Personal artifacts (`src/fonts/bin-personal/`, `manifest-personal.json`) are
gitignored, so a fresh clone or CI cannot produce a build containing them.

## Stitch types the lettering path supports

Three, all added 2026-08-21/22 — before that the path was satin-only, so a
runs-only font imported fine, passed most checks and stitched exactly ONE
stitch.

1. **Satin columns** — the original path.
2. **Bean / running stitch** — `satinfont.routeRuns` resamples a run at the
   length the FONT authored, and backtracks per stitch for bean repeats. A run
   with no authored length is skipped, never defaulted (gate 1).
   *(confirmed 2026-08-21 — `test/run-fonts.test.js`)*
3. **Cross-stitch fill** — `src/crossfill.js`, written from first principles
   rather than ported: Ink/Stitch's `cross_stitch.py` is GPL-3.0 and this
   product is sold. The grid is MEASURED from the pixel-art outlines
   (`detectLattice`), in glyph units, so it scales with the letterform like
   satin width and no physical constant is chosen.
   *(confirmed 2026-08-21 — `test/crossfill.test.js`)*

A font whose outlines do not actually lie on one grid is **refused, not
guessed at** — the threshold is 0.9 fit. Eleven upstream picture-fonts fit
26.2%–87.5% and are excluded on that basis; two of them (`handkerchief` 87.5%,
`nautical` 83.6%) sit close to the line and are still refused.
*(measured 2026-08-22 — `tools/build-font.mjs` import run)*

## Licence position

**ShareAlike is permanently closed, and NC/ND/GPL are excluded.**
`ALLOWED_LICENSES = {OFL-1.1, CC-BY-4.0, CC0}` gates the sellable build; guard
tests pin that no pulled or ShareAlike font reaches the sellable manifest.
*(confirmed 2026-08-22 — `test/run-fonts.test.js`, `test/font-license.test.js`)*

Full licence texts ship three ways — sidecar file, served at
`/fonts/<key>.LICENSE.txt`, and embedded in each `.embf`. Attributions are
complete notices, not first lines. The three-way shipping is what discharges
the OFL's requirement that the notice travel with every copy, and it is load
bearing for more than the OFL: see `roman_ags` below.

**Cross-family derivatives.** Most of the library declares a derivative base, but
for all but one that base is itself OFL, so shipping the OFL text discharges
everything. `roman_ags` is the exception — OFL-1.1 over Latin Modern Roman,
which is under the GUST e-foundry Licence (LPPL 1.3c). The relicensing is
legitimate: LPPL 1.3c clause 10a expressly permits a Derived Work under a
different licence, and clause 6d ("information sufficient to obtain a complete,
unmodified copy of the Work") is met by the fontsquirrel URL in the licence
text. GUST's rename request is itself "requested, but not legally required",
and is honoured anyway. What was wrong until 2026-08-22 was only the CREDIT:
`extractAttribution` takes the first paragraph, and the provenance sat in the
second, so the chain depended on a reader opening the linked file.
*(confirmed 2026-08-22 — LPPL 1.3c primary text; `ATTRIBUTION_OVERRIDES`)*

The 13 pulled ShareAlike fonts remain pulled. The lawyer consult
(`docs/lawyer-brief-cc-by-sa-2026-08-04.md`) is optional and only gates
restoring them.

## Fixed — the transform bug (2026-08-22)

`build-font.mjs` had two path walks: a transform-aware one, and a simpler one
that read each path's `d` and ignored transforms entirely. The simple one ran
for every font in the standard single-`ltr.svg` layout — most of the library.

Harmless for a glyph whose coordinates are baked into its `d`; destructive for
one that places repeated geometry BY transform. `mimosa_large` is a dot-matrix
face that does both: its "A" carries 38 distinct `d` values and no transforms
and imported perfectly, while its "D" carries ONE `d` — a single dot — repeated
38 times with 38 different transforms. Those were dropped, so all 38 dots
stacked on one point:

| | stitches | rendered size |
|---|---|---|
| `mimosa_large` "D" before | **6,193** | 40.0 × **0.0 mm** |
| `mimosa_large` "D" after | 1,000 | 40.0 × 60.0 mm |
| `mimosa_large` "A" (never broken) | 996 | 40.0 × 60.1 mm |

A glyph collapsed to zero height carrying six times a healthy glyph's stitch
count is a needle hammering one line thousands of times — a machine hazard, and
it shipped. Kent's call was to fix rather than pull.

Four fonts were affected — `mimosa_large`, `mimosa_medium`, `apesplit`,
`initials_medium` — and one fix cleared all four. **The library now has zero
letters under 0.45x their case median, and QC reports 0 failures and 0
stitchability/geometry warnings across all 80 fonts.**
*(confirmed 2026-08-22 — `test/font-transforms.test.js`, full-library QC sweep)*

Dead ends worth not re-walking: it was NOT upstream under-tagging (the source
tagging ratio is uniform across healthy and broken glyphs — `mimosa_large` A
76 paths/38 tagged, D 76/38), and NOT the transform math, which verifies
correct in isolation. The tell was that broken glyphs kept their full column
and rail-point count while landing on one spot.

**Library-wide impact of the fix:** 25 of 80 byte-identical; of the 55 that
changed, the great majority moved 0.00% in stitch count. Four real movers, all
verified by rendering: `apesplit` −43.91%, `initials_medium` −31.75%,
`mimosa_medium` −19.59%, `pixel10` +1.72%. The large drops are geometry that
was being stitched twice and now is not, so DOWN is correct here — `apesplit`
and `initials_medium` now set "ABCDE" as five uniform letters where before the
A was a tiny mark beside four oversized overlapping ones.
*(measured 2026-08-22 — full rebuild against a pre-fix baseline)*

A second bug in the same walk was found and fixed with it: the stack pop fired
on ANY closing tag while only `<g>` ever pushes, so a non-self-closed
`</path>` popped a frame it never pushed and silently un-applied its parent
group's transform for every following sibling. Dormant across the whole upstream
library (every file self-closes its paths) — confirmed by rebuilding and getting
a byte-identical library — and fixed rather than left as a trap for the next
font that does not. Guarded by a fixture case, verified to fail without the fix.

## The post-fix re-census (2026-08-22)

The original upstream census had judged every font on geometry the importer was
collapsing, so all 142 upstream fonts were re-imported and re-QC'd after the fix.
137 imported; the 5 failures are RTL-only fonts (`rtl.svg`, no `ltr.svg`).

**Yield: exactly two, both OFL-1.1.**

- **`cyrillic`** — 466 glyphs, 252 of them Cyrillic, derived from Roboto. This
  font was previously HELD because its accents sat ~650 units from their letter
  bodies and inflated the line box. That defect *was* the transform bug: the
  accents were placed by transform. It now measures zero bbox outliers.
  Cyrillic coverage was called out as a real gap in the external hunt.
- **`inkstitch_masego`** — heavy slab display face, 76 glyphs. Verified against
  upstream's own preview rather than by eye alone.
- **`fold_inkstitch`** — origami-outline caps face, 40 glyphs. It was excluded
  by a FILENAME, not a licence: 141 of 142 upstream fonts name the file
  `LICENSE` and this one names it `license`. The importer looked for the
  uppercase spelling only, which resolves on Kent's case-insensitive Windows
  filesystem and silently read NOTHING on Linux, so the font imported with an
  empty licence — and `licenseId("")` returns `SEE-LICENSE-FILE`, outside
  `ALLOWED_LICENSES`. It is OFL-1.1. Failed safe, but by luck: the same silence
  would exclude any legitimately-licensed font.
  *(fixed 2026-08-22 — `tools/build-font.mjs`, guarded in font-transforms.test.js)*

**Rejected, with reasons, so they are not re-proposed:**

- `sacramarif` — QC-passes but renders as a bare single-thread line with the E
  absent; 100 stitches for 80 mm of text.
- `roman_ags_bicolor` — QC-passes and renders correctly, but EMB-Bot's
  single-colour pipeline stacks its two colour layers: 79 satin columns for A-H
  against the mono cut's 57, and 53% more stitches for visually identical output.
  That is thread buildup for nothing. A prior decision had already recorded this
  and `test/embf-guard.test.js` pins it — the test caught the re-addition, which
  QC could not, because QC cannot see redundant overlapping satin.
- The 11 refused cross-stitch fonts re-refuse at the same lattice fits.
- The 3 Arabic fonts stay out. RTL *placement* now ships, but Arabic letters
  take initial/medial/final/isolated forms and must join; without a shaping
  engine they render unjoined, which is wrong text rather than plain text.
  The 2 Hebrew fonts ARE now shipped — Hebrew has no contextual forms, so
  right-to-left placement is the whole requirement.

## Right-to-left lettering (2026-08-22)

Five upstream fonts ship their glyphs in `rtl.svg` rather than `ltr.svg`;
`build-font` looked only for `ltr.svg`, so all five failed to import with ENOENT
and the script was absent from the product entirely.

A font imported from `rtl.svg` now carries `dir: "rtl"` (emitted only for RTL
fonts, so every existing font.json stays byte-identical), and
`satinfont.layoutText` walks that line's characters in reverse. Everything
downstream — arc, badge, per-letter colour, underlay — works unchanged, because
it keys off each glyph's `ox` rather than off character order.

`charIdx` deliberately keeps pointing at the LOGICAL string position, not the
visual one: it exists so the UI can map a `<textarea>` selection onto glyphs,
and a selection is logical. Reversing it too would silently colour the wrong
letters, with nothing to catch it.
*(confirmed 2026-08-22 — `test/rtl-lettering.test.js`, verified to fail without
the fix)*

Shipped: `hebrew_font_large`, `hebrew_font_medium` (29 glyphs each, OFL-1.1).

**Three Latin assumptions surfaced when a non-Latin font arrived**, each silent:

1. `build-previews`' sample-text fallback assumed Latin glyph names, so both
   Hebrew fonts rendered ZERO stitches and shipped with no preview tile.
2. `sewsAnything()` — the personal build's stitchability gate — only looked at
   A-Z, so it answered "no" for a font with no Latin alphabet. Both Hebrew
   faces were dropped from the personal build while the SELLABLE build shipped
   them: the two libraries disagreed about the same font. Fixing it also
   recovered `ellenika`, `honoka`, `invercelia` and the two
   `hebrew_simple_rounded` faces; personal went 119 → 127, sellable unchanged.
3. The lettering path skipped characters a font has no glyph for **silently**,
   so picking a Hebrew font and typing Latin produced a valid-looking 0-stitch
   design with no explanation. `buildLetteringDesign` now reports `unsupported`
   (source order, deduplicated), `generateAll` carries it per element, and the
   field surfaces it — as a replacement for the generic empty-field hint when
   NOTHING stitched, and on the stats line when only part did.
   *(confirmed 2026-08-22 — `test/unsupported-chars.test.js`, and driven in a
   real browser across Latin-only / Hebrew-only / mixed)*

Two of those three were invisible to the unit suite and were found by driving
the Studio in a browser; the third was caught by a guard test.

## Deferred / not done

- **Condensed/expanded width and mixed per-letter size** — both risk uneven
  satin distortion. Minor, not blocking.
- **`cyrillic`** — held. Dropping 6 broken glyphs would salvage it but kills
  `ñ`.

## Supply

**Upstream is effectively exhausted, and there is no external supply.**
`inkstitch/embroidery-fonts` is a monoculture: across all of GitHub the
`horiz_adv_x_space` key returns 16 files, of which the non-upstream remainder
is four `font.json` files, none viable. Independent non-satin Ink/Stitch
lettering fonts: zero. Full method and per-candidate verdicts in
[`../font-hunt-external-2026-08-21.md`](../font-hunt-external-2026-08-21.md)
and [`../font-expansion-research-2026-08-21.md`](../font-expansion-research-2026-08-21.md).
*(measured 2026-08-21 — GitHub-wide code search, 20 agents / 9 search angles)*
