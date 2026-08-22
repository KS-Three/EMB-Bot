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

**80 fonts in the sellable build** *(confirmed 2026-08-22 —
`src/fonts/manifest.json`, engine suite)*. Two builds are produced from one
source tree:

| Build | Command | Contents |
|---|---|---|
| Sellable | `node tools/build-embf.mjs` | 80 fonts, all inside `ALLOWED_LICENSES` |
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

**Cross-family derivatives.** 71 of the 80 fonts declare a derivative base, but
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

## Known defects

**Stunted glyphs in four shipped fonts** — `mimosa_large` (D 0.11x, E 0.22x),
`mimosa_medium` (D 0.22x, E 0.44x), `apesplit` (A 0.23x), `initials_medium`
(A 0.28x), as a ratio of their case median height. These stitch, so the
stitchability check passes them, but they render as stubs: `mimosa_large`'s D
sews as a bare dash and both "initials" fonts' A as a tiny mark floating off
the baseline. Confirmed by rendering, not by the ratio.
*(confirmed 2026-08-22 — `test/font-stunted.test.js`, render inspection)*

Whether to fix or pull them is Kent's call; the test records them as named
debt so the set cannot grow silently.

## Deferred / not done

- **Condensed/expanded width and mixed per-letter size** — both risk uneven
  satin distortion. Minor, not blocking.
- **`cyrillic`** — held. Dropping 6 broken glyphs would salvage it but kills
  `ñ`.
- **Personal-build previews** — `tools/build-previews.mjs` reads the sellable
  manifest, so the 40 personal-only fonts have no preview tile. Cosmetic, and
  fixing it must NOT write those previews into `src/fonts/previews/` (that
  directory is committed, and these are NC/ShareAlike fonts).
  *(confirmed 2026-08-22 — `git check-ignore`)*

## Supply

**Upstream is effectively exhausted, and there is no external supply.**
`inkstitch/embroidery-fonts` is a monoculture: across all of GitHub the
`horiz_adv_x_space` key returns 16 files, of which the non-upstream remainder
is four `font.json` files, none viable. Independent non-satin Ink/Stitch
lettering fonts: zero. Full method and per-candidate verdicts in
[`../font-hunt-external-2026-08-21.md`](../font-hunt-external-2026-08-21.md)
and [`../font-expansion-research-2026-08-21.md`](../font-expansion-research-2026-08-21.md).
*(measured 2026-08-21 — GitHub-wide code search, 20 agents / 9 search angles)*
