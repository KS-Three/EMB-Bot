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

## The size guards the font path did not have (2026-09-03)

From the fine-lettering design review
(`docs/design-review-fine-lettering-2026-09-03.md`, items 2 and 4). Until
this the font path's only width guard was **0.3 design pixels** in
`satinplay.emitZigzag` — 0.04 mm at the lettering default — so every pinched
cross the Python engine refuses at `SATIN_MIN_CROSS_MM` sewed anyway, and the
Studio could not say how tall a text element's letters were or how much of
them sat under the needle floors.

- **The 0.5 mm cross floor, on the fabric.** `layoutText` passes
  `SATIN_MIN_CROSS_MM / fitScale`, so the floor is 0.5 mm whatever the fit
  did. `crossFloor: false` is the legacy stream, kept byte-identical for
  `test/run-fonts.test.js`'s run-support pins.
- **A hairline STRETCH sews as a bean run, not nothing.** A satin span is
  split by its width profile (`satinplay.splitByCrossFloor`, the same
  stations, comp and floor `emitZigzag` applies): stretches over the floor
  sew as satin; stretches under it of three bean stations or more sew as a
  3 × 0.73 mm bean down the centreline (`beanFromGeom`). A per-cross drop
  alone left survivors joined by chords across the glyph on an outline face
  (cooper_marif: a diagonal through the F); a stretch that sews nothing is
  walked as underpath so the Euler circuit stays continuous. This goes one
  step past the review's approved wording ("warn only") — the warn-only
  version left the chords, which is worse than what it replaced.
- **`lettering` on every design**, empty ones included: final cap height,
  stroke length and how much of it runs under 1.0 / 0.5 mm
  (length-weighted — a script glyph is one long column that runs
  thin-thick-thin), hairline stretches sewn as run, and the floors applied.
  `generate.letteringNote` formats one line; the field shows it beside the
  hoop and unsupported notes. Warn only, no clamp — sizing is the user's.
- **Every number mirrors a Python constant** (`SATIN_MIN_CROSS_MM`,
  `BEAN_STITCH_MM`/`BEAN_PASSES`, `MIN_STITCH_MM`, `MIN_LETTER_EXTENT_MM`);
  none is new, so ROADMAP gate 1 is untouched. Constants live in
  `satinfont.LETTERING_GUARDS`.

Measured, 83 fonts × "Fritsch" × three widths against the pre-change tree:
at 50 mm (13 mm median cap) 46 fonts move at all and 4 by more than 5%, all
hairline-authored (cooper_marif −39%, mai_en_fleur −33%, cats −7%,
montecarlo −6%); at 100 mm (26 mm cap) 35 move, one over 5% (mai_en_fleur
−15%, a font whose columns are authored under 1 mm). The two "AB" snapshots
in `test/satinfont.test.js` did not move. Rendered before/after:
cooper_marif's outline sews as one clean line, montecarlo keeps its shape with
thin connectors as runs, mai_en_fleur at an 11 mm cap fragments — 78% of it
is under 0.5 mm there, which is what the note now says.
*(measured 2026-09-03 — commit `0a67171`; `test/satinplay.test.js`,
`test/satinfont.test.js`, `app/src/lib/generate.spec.js`)*

**The Bold counter guard (2026-09-03, review item 4, Kent's pick).** Bold
widened every column by pushing its rails 0.3 mm apart and closed every
counter by the same amount — a 0.72 mm eye went to 0.42, a 0.36 mm one to
0.06. The weight now travels apart from the fabric's pull comp
(`weightMm`) and is held per rail station where the rail faces another rail
of the same glyph across a gap: whole on an outside edge, across a counter
only what the gap can spare with `SATIN_MIN_CROSS_MM` kept, nothing where
the gap is already under that floor (`satinplay.railCloud` /
`counterGap` / `stationPush`). Pull comp is never held. Normal and thin are
byte-identical; `lettering.counterHeld` / `weightMm` report it; no Studio
note, because junctions that nearly touch hold too. Library sweep, "Fritsch"
bold at 25 mm: 60 of 83 fonts hold somewhere, 70,162 stitches guarded
against 73,183 unguarded and 67,276 normal; mai_en_fleur's hairline
connectors stay bean runs instead of becoming dense satin (1,393 vs 3,043).
The full account, with the two-stem table, is §9 of
`docs/design-review-fine-lettering-2026-09-03.md`.
*(measured 2026-09-03 — `test/satinplay.test.js` +3, `test/satinfont.test.js` +2, `test/digitize.test.js` +1)*

**Short stitches on the inside of bends (2026-09-03, review item 6, Law 53,
Kent's pick).** The Python engine's `_short_stitch_guard`, mirrored with its
numbers (`SHORT_STITCH_AT_MM` 0.3 / `_PULL` 0.35 / `_MAX_MM` 0.6 — move both
or neither): on every other station a penetration under 0.3 mm from the
last on its rail is pulled back along the cross, at most 0.6 mm and never
under the cross floor — the bound that gates it off on a narrow column, the
trap Law 53 names. On with the cross floor only, so the legacy stream is
untouched. geneva "S": 43% of same-rail advances under the trip → 0%;
library sweep at 25 mm: 59 of 83 fonts pulled somewhere, stitch counts
identical, mean under-trip share 5.6% → 3.5% (50 mm: 2.7% → 1.0%); faces at
the floor at a 5.5 mm cap (jersey_15, pixel10, mai_en_fleur) keep most of
their bunching because the gate refuses the pull. §10 of the review doc.
*(measured 2026-09-03 — `test/satinplay.test.js` +3, `test/satinfont.test.js` +1, `test/digitize.test.js` +1)*

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
- The 3 Arabic fonts stay out, and **a shaping engine would not change that**.
  Arabic letters take initial/medial/final/isolated forms and must join, but all
  three fonts carry ONLY base-block Arabic (`computer` 45 glyphs, `malika` 36)
  and **zero presentation forms** (U+FB50–FDFF, U+FE70–FEFF) — the joined glyphs
  a shaper would select do not exist in them. This is a property of the fonts,
  not a gap waiting on engine work.
  *(measured 2026-08-22 — font.json glyph blocks)*
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

## The tier gate (fixed 2026-08-22)

`tools/qc-font.mjs` calls itself "the tier gate, in the repo, with tests". Two
things were wrong with that, both surfaced by shipping one Hebrew font.

**It was not run.** `build-embf.mjs` never called `qcFont`. The only enforcement
was `test/embf-guard.test.js`, which reads `src/fonts/<key>.json` — the 17 STATIC
sources. The other 68 fonts arrive through `scratch_ink/_out` and were QC'd by
nothing on the way in. The builder now runs it: a hard fail EXCLUDES the font
from the sellable build, the same treatment as a PULLED font or a licence
outside policy; `--personal` warns and keeps, since that build is "every font on
hand" by definition. Closing it changed nothing today — the 85 pass with zero
exclusions — which is exactly the point.

**It was Latin-only.** Every coverage check was scoped to A–Z, so a font with no
Latin HARD-FAILED on "no uppercase letter glyphs at all". `hebrew_font_large`
did, and shipped regardless because of the first hole. A font's alphabet is now
whatever single-character letter glyphs it has, Latin preferred when present.

The alphabet test is `\p{L}`, and that precision earns its keep twice:

- Hebrew ships `׳` (geresh) and `״` (gershayim) — punctuation, legitimately
  short. Counting them as letters made them "stunted" against a median they were
  never part of, exactly as an apostrophe would be in a Latin font.
- `circular_3letters_monogram` and `invercelia` name their glyphs `A.medi` /
  `A.init` — contextual variants the lettering path can never address, since it
  looks up `font.glyphs[ch]` for a plain character. Their only single-character
  glyphs are punctuation, which under a looser test vouched for a font whose
  actual letters are unreachable — the ondulamarif_XL trap the gate exists for.
  `\p{L}` drops both and keeps `ellenika` (69 Greek) and `honoka` (501 Japanese).

*(confirmed 2026-08-22 — `test/qc-font.test.js`, verified to fail against the
pre-fix gate)*

## Deferred / not done

- **Condensed/expanded width and mixed per-letter size** — both risk uneven
  satin distortion. Minor, not blocking.
- **`cyrillic`** — held. Dropping 6 broken glyphs would salvage it but kills
  `ñ`.

## What now guards the library (2026-08-22)

**Why this matters to the area's score.** MASTER_SCOPE has rated this area
High (tech) for a while, and the rating did not move on 2026-08-22 — but what
it rests on did. It used to rest on a green suite that could not see a machine
hazard: `mimosa_large` shipped a glyph sewing 6,193 stitches into 40.0 x 0.0 mm
with every check in the repo calling the font healthy. It now rests on guards
whose COVERAGE is itself asserted. A score with the same value and a sounder
basis is worth saying out loud, because "High, and here is what would catch it
being wrong" is a different claim from "High".

Seven checks, each verified by breaking the thing it guards and watching it go
red. Listed because the gap between them is where the next defect will live.

| guard | what it would catch | population |
|---|---|---|
| `test/font-render-smoke.test.js` | a font that throws, renders zero stitches, or packs stitches into no area — **the mimosa_large hazard, in the terms that make it dangerous** | 85/85, rendered through the real lettering path |
| `test/font-stunted.test.js` | a letter far shorter than its script median, or with no skeleton geometry | 85/85, and a separate test fails if any font is unmeasured |
| `test/font-dead-glyphs.test.js` | a glyph present in the font that puts no thread down | 85/85, all single-character glyphs |
| `test/embf-guard.test.js` (tier gate) | any qc-font hard failure, plus any defect-class warning | 85/85 **binaries**, not the 17 committed JSONs |
| `test/font-license.test.js` | sidecar/manifest licence drift, and a cross-family derivative whose credit line omits its base | 85/85, and it now names the one font that reaches the cross-family assert |
| `test/font-export-smoke.test.js` | a font whose geometry breaks an encoder, or loses stitches through DST | 85/85 × DST/EXP/PES — **no font had ever reached an encoder in a test** |
| `test/font-sample.test.js` | a browser tile that shows something other than the font — a defect with no natural alarm, since nothing fails | 85/85 must be name-derived, and today all are |

The hazard tripwire has deliberate headroom rather than tightness: measured at
emMm 20 / pxPerMm 8, the smallest rendered height in the library is `heavenly`
at 62.7px and the smallest width is `montecarlo` at 247.0px, against a 10px
threshold. It is there to catch a collapse, which renders at ~0 — not to
grade fonts. *(measured 2026-08-22 — all 85 rendered via EMB.layoutText)*

**The one runtime behaviour change on this branch changes no stitches**, which
was asserted in a commit message and then actually measured: eight designs
across the six fonts with dead glyphs plus three controls, hashed before and
after `layoutText` gained its `sewsSomething` check, are **byte-identical** —
same stitch stream, same counts, same dimensions. The change adds a report and
nothing else, so no existing design moves. *(measured 2026-08-22 — sha256 of
the stitch stream, pre-change tree at `e56ff13^` vs HEAD)*

**The lesson these encode, which cost more than any of them:** breaking a guard
on purpose does not prove it is not blind. The stunted guard passed that ritual
and was still measuring nothing in 21 of 85 fonts. Ask what fraction of the
population a guard actually measures, and assert that — full account in
`.claude/memory/font-pipeline-silent-failures.md`.

## Looked at, not just measured (2026-08-22)

Everything else on this branch was verified numerically. These four were
verified by rendering them and looking, because the numbers cannot answer the
question being asked.

- **Hebrew reads correctly, in the right direction.** `hebrew_font_large`'s
  preview sets א ב ג ד ה — the first five letters in LOGICAL order — and the
  aleph lands **rightmost**, which is what `dir: "rtl"` is for. The letterforms
  are square-script Hebrew with satin fill across each stroke. A coordinate test
  can show that index 0 has the largest x; it cannot tell a reader who does not
  read Hebrew that the result is Hebrew.
- **`mimosa_large`'s "D" is a D.** Rendered "ABCDE" at 80 mm: five uniform,
  legible letters, the D the same weight and height as its neighbours. That is
  the glyph that shipped sewing 6,193 stitches into 40.0 × 0.0 mm — 38 dots
  stacked on a point by the dropped transforms.
- **`noble`** — cross-stitch letters whose X's sit on one shared lattice across
  the whole word, which is what measuring `crossGrid` font-wide (rather than
  per glyph) exists to produce.
- **`jaquarda_bastarda_9`** — ornate blackletter in single-cell cross chains,
  matching upstream's own preview. Worth re-stating because this font *looks*
  broken when inspected numerically (13 rings, 34 sparse cells for an H) and is
  simply drawn that way.
- **`cyrillic`'s detached accent is really gone** — this was the branch's
  weakest claim, an inference ("that defect WAS the transform bug") standing in
  for a measurement. Both now agree: `ú` measures **101.3 units** against the
  bare `u`'s 71.5, where the original complaint was 725 with the accent
  marooned ~650 units from the letter body. Rendering "Дúжé" shows both acutes
  sitting directly on their letters and correct Д and ж forms. The font is
  shipping on evidence now, not on a plausible story.
- **`apesplit`'s "ABCDE" is five uniform letters**, which is what its −43.91%
  stitch drop means. Before the transform fix the A was a tiny mark beside four
  oversized overlapping ones; the stitches that disappeared were geometry being
  sewn twice, not detail being lost. A large negative delta on a rebuild is
  worth looking at rather than accepting — this one is the fix working.

**Layout timing is unchanged** by the `sewsSomething` check, with the noise
floor established rather than assumed: repeated runs of the same build vary
`medium_font` between 3.63 and 4.42 ms/layout, and the before/after difference
sits inside that. `mimosa_large` is the expensive one at ~25 ms, and that is
satin routing, not the new check. *(measured 2026-08-22 — 40 layouts per
sample, pre-change tree at `e56ff13^`)*

## What looking found that measuring could not (2026-08-22)

The systematic checks above all passed while three of the 85 browser tiles
were showing something other than the font. Nothing failed, because nothing
was asking — a tile that says less is not an error, it is just a worse tile.

`sampleFor` accepted the font's name only if EVERY character rendered, so one
missing glyph dropped it to "first six alphanumerics in glyph-key order":
`fold_inkstitch` ("Fold Ink/Stitch", no `/` glyph) read **012345**, and both
Hebrew faces ("חוכמה Large", no Latin) read **אבגדה**. Two of the three were
this branch's own doing — the any-script fallback added here stopped them
rendering nothing and stopped there.

Now unrenderable characters are dropped and the rest of the name kept, so the
tiles read **FOLD INKSTITCH** and **חוכמה**. Whichever spelling survives
better wins: stripping the original in a caps-only font leaves "FIS", while
stripping the case-fixed spelling keeps all but the slash.

**A second defect fell out of writing the test.** The alphanumeric fallback
returned `123ABC`, not `ABC123`, because `Object.keys` puts integer-like keys
first whatever the insertion order — so it preferred DIGITS over letters for
every font, not just unlucky ones. That is the actual reason fold_inkstitch's
tile read "012345" and not "ABCDEF". Letters come first explicitly now.
*(measured 2026-08-22 — 85/85 name-derived, verified by disabling the rule)*

## 26 glyphs that sew nothing — needs Kent, and needs his machine (2026-08-22)

Six shipped fonts contain single-character glyphs that are PRESENT, take their
advance, look selectable in every UI, and put no thread down. Register and
per-font list: `test/font-dead-glyphs.test.js`, which fails in both directions
so a new one is caught and a fixed one must come off.

| font | dead glyphs |
|---|---|
| `roaring_twenties_KOR` / `_small` | `+ - / < = > \ _ ¯ °` (10 each) |
| `western_light` | `4`, `ç` |
| `ondulamarif_XL` | `:`, `º` |
| `ondulamarif_Medium` / `_S` | `'` |

The user-facing half is CLOSED: `layoutText` reports them (`unsupported`) and
the Studio shows "This font can't stitch …", so typing "2024" in
`western_light` now says the 4 is missing instead of quietly dropping it.
*(confirmed 2026-08-22 — test/font-dead-glyphs.test.js pins the three classes)*

**The candidate cause is proven as a MECHANISM and unproven as an instance.**
`build-font`'s `stripRunParamsIfSatin` is font-wide: if any glyph has satin
columns, every glyph's authored run parameters are stripped — including a glyph
with NO columns, whose runs are the entire character. That is exactly the shape
here (`roaring_twenties_KOR`'s "-" is one 2-point run; its letters are satin).
The strip exists for a good reason — honouring authored run params on satin
fonts would add construction stitches to every already-shipped satin font, a
change Kent deliberately deferred — but its blast radius includes glyphs where
the run is not construction, it IS the glyph.

Whether upstream authored a stitch length that was stripped, or never authored
one, **cannot be told from the built JSON**: both produce a bare point array.
Deciding it needs the Ink/Stitch SVG sources in `scratch_ink/`, which exist on
Kent's machine and not in a cloud checkout.
*(suspected 2026-08-22 — mechanism read from tools/build-font.mjs:377; instance
not verifiable in this checkout)*

**WHICH CAUSE APPLIES TO WHICH FONT — SETTLED 2026-08-28, from the shipped
binaries, with no SVG source needed.** This section previously said telling the
two candidates apart required Kent's machine. It did not: decoding
`src/fonts/bin/<key>.embf` and counting glyphs that carry satin columns answers
it, because `stripRunParamsIfSatin` fires if and only if the font has any satin
at all.

| font | glyphs with satin | strip fires | dead | cause |
|---|---|---|---|---|
| `roaring_twenties_KOR` | 146 / 156 | yes | 10 | the strip |
| `roaring_twenties_KOR_small` | 146 / 156 | yes | 10 | the strip |
| `western_light` | 0 / 164 | **no** | 2 | no authored length |
| `ondulamarif_XL` | 0 / 108 | **no** | 2 | no authored length |
| `ondulamarif_Medium` | 0 / 108 | **no** | 1 | no authored length |
| `ondulamarif_S` | 0 / 108 | **no** | 1 | no authored length |

The four zero-satin fonts are the decisive half. The strip cannot have touched
them, yet every dead glyph's runs are bare arrays — and `runFrom` returns a
bare array only when `!(lenMm > 0)`. So upstream authored no length for those
six glyphs, and **defaulting one is a gate-1 refusal already enforced by
`test/run-fonts.test.js:44`** ("gate 1: a run with NO authored length is
skipped, not defaulted"). Those six are not work; they are a standing ruling.

For the twenty in `roaring_twenties_KOR`/`_small` the strip IS the mechanism —
those glyphs are runs-only (`cols=0`) inside a 94%-satin font. What the binary
cannot say is whether upstream authored a length that the strip then discarded,
because the discard happened at build time. That is one grep, not a session:
count `running_stitch_length_mm` in `<ink-stitch>/src/roaring_twenties_KOR/
ltr.svg`. Zero would mean these twenty are the same gate-1 case as the other
six and no fix exists at all. *(measured 2026-08-28 — `.embf` decode)*

**What the narrow fix would be, if the sources confirm it:** scope the strip to
glyphs that HAVE columns. It cannot regress any glyph — the ones it affects
produce zero stitches today — but it is not free: a glyph that starts producing
ink changes the design's bbox, and therefore its auto-scaling, so "A-B" in
`roaring_twenties_KOR` would render at a different size than it does now. That
is a change to existing output, which is why it is Kent's call and not taken
here.

## Supply

**Upstream is effectively exhausted, and there is no external supply.**
`inkstitch/embroidery-fonts` is a monoculture: across all of GitHub the
`horiz_adv_x_space` key returns 16 files, of which the non-upstream remainder
is four `font.json` files, none viable. Independent non-satin Ink/Stitch
lettering fonts: zero. Full method and per-candidate verdicts in
[`../font-hunt-external-2026-08-21.md`](../font-hunt-external-2026-08-21.md)
and [`../font-expansion-research-2026-08-21.md`](../font-expansion-research-2026-08-21.md).
*(measured 2026-08-21 — GitHub-wide code search, 20 agents / 9 search angles)*
