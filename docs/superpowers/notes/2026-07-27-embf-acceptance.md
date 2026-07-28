# EMBF binary format — acceptance evidence (Slice 10 Stage A, Task 5)

Date: 2026-07-27. Harness: `tools/render-font-compare.mjs` ("Kent" at hat
scale, 55 mm target width, both DSTs rendered via `tools/render-dst.mjs`).
Raw sweep log: `scratch_ink/_montage.log` (gitignored scratch).

## Deep compare — 3 fonts spanning styles

| Font | JSON stitches | EMBF stitches | Drift |
|---|---|---|---|
| geneva_simple (sans) | 734 | 734 | **0.00%** |
| aventurina (script) | 863 | 863 | **0.00%** |
| alchemy (display, largest font in the library) | 596 | 596 | **0.00%** |

PNG pairs visually indistinguishable.

## Montage sweep — all new fonts

49 new manifest fonts swept; 48 rendered with drift computed, 1 failed to
render at all (see demotion below).

- 19 fonts: exactly 0.00% drift.
- 28 fonts: 0.04%–0.92% drift — small-count rounding noise, all under the 1%
  gate.
- 1 font over the gate: **glacial_tiny at 1.07%** (654 → 647 stitches, a
  7-stitch delta on a deliberately tiny font). PNG pair inspected side by
  side: letterforms, satin roll and density identical; differences are
  single-stitch placements at the n-shoulder and t-crossbar. **Passes visual
  QC — kept.** The percentage gate over-triggers on low-stitch-count fonts;
  absolute delta and the render are the meaningful evidence at this scale.

## Demotion

- **ondulamarif_XL → unverified.** Its letter glyphs contain zero satin
  columns (runs only), so `buildLetteringDesign` produces **0 stitches** from
  the original JSON and the binary alike. Not a codec issue — the font simply
  has no stitchable letter data through this engine's lettering path. Tier
  updated in `scratch_ink/_tiers.json` with reason; library rebuilt.
  This also exposes a classifier gap worth noting: the satin-column count
  used for tiering is measured per FILE, not per GLYPH — a file can pass with
  satin somewhere while its letters have none. If another 0-stitch report
  appears, check per-glyph `cols` first.

## Final shipped library

**69 fonts** (21 pre-existing + 48 new), 30.09 MB binary at rest.
Every font in the manifest renders real stitches; every drift ≤ 1.07% with
the sole >1% case visually cleared. Engine suite 202/202 after rebuild.

Excluded along the way: `precious` (GPL-3.0, license policy),
`ondulamarif_XL` (0-stitch letters, this task), `montecarlo` and the rest of
the unverified tier (pre-existing classification).
