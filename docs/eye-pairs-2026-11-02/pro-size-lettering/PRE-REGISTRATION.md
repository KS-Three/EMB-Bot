# Pro-sized lettering sitting (`pro-lettering-1102`): pre-registration, 2026-11-02

**Committed BEFORE anything is rendered or measured.** Its twin is `spec.json`
beside it; the kit builder reads the spec, and a test fails if a name here and
there drift apart. **When Kent sits it is his. This file judges nothing and
flips nothing.** It **supersedes the wok42-1013 kit** (`docs/eye-pairs-2026-10-13/wok42/`),
which was built and never sat, and whose render directory is gone.

## Why

Kent ruled 2026-11-02 "My eye stands" on the 17 pairs where cuts, needle-up hops
and needle-up mm scored his pick farther from the pro
(`docs/yardstick-pro-pair-vs-kents-eye-2026-11-01.md` sections 4 and 6): the
trim family is not his eye on construction flips. This sitting puts his labels
and the pro-pair figures on the SAME picture. Every population-A design is
drawn at the professional's own garment and width and read beside the pro's DST,
and every arm changes how a letter is built or where a cut lands, so an
instrument can learn what he weighs against trims.

## What was run before this was written

Nothing on these logos. No design was drawn, no identity spike, no count. Which
arms move which logos is not known; `prepare`'s manipulation check reads it from
the designs alone and the manifest reports only pass or fail per arm.

## Two decisions the brief got wrong, and what was done

1. **Gaulke is out (three jobs).** The brief listed `gaulke_roofing_hat`,
   `gaulke_roofing_lc` and `gaulke_roofing_beanie` as never judged. Their artwork
   (`testdata/photo/logo_gaulke_roofing.png`) is byte-for-byte the `gaulke` of
   `thin_strokes.REAL_ART`, one of the nine logos Kent judged in 2026-09; the
   blinding guard refuses it (a test pins this) and `pooled.select` drops the
   `gaulke` fixture as one he ruled off the page. Not replaced: seven
   pro-paired jobs remain.
2. **`lettering_columns_small_bold` is out.** `python -m tools.flag_ledger`'s
   classifier reads its comment as FABRIC (it sets the pull as a fraction of the
   stroke width), and the brief says to keep LAYOUT only. Two arms are
   FABRIC-classified by the same regex and kept, because the brief names them:
   `lane_off` ("gate 1" appears in its comment) and `exit_next_off` ("underlay").
   Both turn a flag that is ON today to OFF; **the sitting flips nothing, and
   whatever it reads about those two cannot flip a FABRIC flag (ROADMAP gate 1).**

## The base

Today's `main` defaults with no override (`base_flags` is empty). Every arm is
**one flag, ON today, turned OFF.** Kent sees LEFT and RIGHT; which is the base
is shuffled under seed 20261102 with the arm on the left in half the live pairs.

## The logos: sixteen, two populations, none judged

**Population A, pro-paired** (`pro_baseline.JOBS` row, drawn at that row's
garment and width; read beside the pro's DST). The loader resolves the
artwork through the job, so none is copied into the repository (proseal's lives
under gitignored `scratch_kent/`). One artwork at several jobs is several logos
for pairing and ONE where the analysis says "over designs":

| logo | job: garment, width | design (cluster) |
|---|---|---|
| `mfab_hat` | hat_front 104.9 mm | `mfab` |
| `mfab_lc` | left_chest 96.7 mm | `mfab` |
| `proseal_hat` | hat_front 85.9 mm | `proseal` |
| `proseal_beanie` | beanie 75.0 mm | `proseal` |
| `toat_machine_hat` | hat_front 89.5 mm | `toat` |
| `toat_machine_beanie` | beanie 81.0 mm | `toat` |
| `toat_beanie` | beanie 82.3 mm | `toat` |

**Population B, Commons lettering, cost figures only, no pro** (the nine files
of `testdata/art/commons_lettering/`, public domain, provenance in
`docs/asset-provenance.json`): `bukit_asam`, `but_seriously`, `hed_p_e`,
`jakarta`, `k_line`, `ahora`, `dot_music`, `n_sync`, `and_pizza`. **Drawn
hat_front at 100 mm**, a choice the manifest names none for: the nine are
1920 px wide and 20 to 42 mm tall at 100 mm, inside the 64 mm cap frame
(`pro-size` settled 2026-10-26), and 100 mm is the middle of the hat jobs'
85.9 to 114.2 mm. A test pins that every one fits.

## The eight arms

Expected pick is **base** for every arm: the flag is ON because Kent flipped it
on numbers against the pro, not on his eye, and OFF is the older construction.
"Moves" and "holds" are enforced by the manipulation check; where a construction
arm has none, its movement is a measurement, not an expectation.

| arm | flag turned OFF | stratum | variable | moves | holds | expected pick |
|---|---|---|---|---|---|---|
| `corner_fold_off` | `lettering_columns_corner_fold` | construction | an L corner: one folded column, or two butted | none | none | **base** |
| `italic_lean_off` | `lettering_columns_italic_lean` | construction | crosses on slanted bars: along the slant, or square | none | none | **base** |
| `text_lean_off` | `lettering_columns_text_lean` | construction | crosses in letters 10 mm and up: diagonals like stems, or square | none | none | **base** |
| `inside_stagger_off` | `lettering_columns_inside_stagger` | construction | where cuts land at a pivot: staggered, or piled in one hole | none | none | **base** |
| `script_strokes_off` | `script_strokes` | construction | script: one column per pen stroke, or ordinary letters | none | none | **base** |
| `fold_slivers_off` | `keyline_fold_slivers` | construction | an outlined letter: slivers folded in, or each its own piece | none | none | **base** |
| `lane_off` | `lettering_columns` | construction | the whole Column lane against the pre-lane skeleton tier | `trims_per_1000` up | none | **base** |
| `exit_next_off` | `satin_exit_toward_next` | **trims, the control** | cuts only: where the walk ends | `trims_per_1000` up | `flow_circvar`, `long_share` | **base** |

`exit_next_off` is the one arm built so the trim family has pairs it SHOULD
win. If cuts, hops and needle-up mm do not track his pick there either, they
cannot be read anywhere else in this sitting; if they do, the earlier "My eye
stands" is specific to construction.

## The manipulation check, and the budget

An arm passes when it changes the stitch stream on at least `min_live_logos` (3)
logos and, on at least half of those, every `moves` metric moves as stated by its
threshold and every `holds` metric moves by less (thresholds as wok42 after its
Amendment 1: `trims_per_1000` 0.5, `flow_circvar` 0.02, `long_share` 0.02,
`thread_density_whole` 5%). A logo where an arm is byte-identical to the base is
not a pair. There are no reserves: a failing arm stays, flagged `passes: false`
(wok42 Amendment 2), and the analysis reads every lead on all live pairs and on
the passing arms alone. The old "identical on 4 of 6 logos" rule is replaced by
`min_live_logos` because sixteen logos make "4 identical" the normal case for
an arm that only touches script or outlined art.

**Target 40 to 60 live pairs, plus 4 identical and 4 repeat controls.** If the
check leaves more than 60, duplicate jobs are dropped first, in the order fixed
now and by identity counts alone, never by a picture or a figure:
`toat_beanie`, `toat_machine_beanie`, `proseal_beanie`, `mfab_lc` (so one `mfab`,
one `proseal`, one `toat` job survive), then population B logos with the fewest
live arms, then arms by fewest live logos. Any drop is an amendment to this file
written before a pick exists.

## What is hidden, and what is committed

The picker serves opaque ids; the sealed key (`arms.json`) stays in
`digitizer/eye_pairs_out/pro-lettering-1102/` and is committed only after the
sitting, with `picks.jsonl`. What is committed now is `manifest.json`: the sealed
map's SHA-256, design hashes, counts and commands, and no arm-to-pair mapping.
Nobody opens `arms.json`, `features.json`, `manipulation.json` or `designs/`
before `analyse`. The table of manipulation deltas is committed after the
sitting. Each design's DST (`designs/<logo>__<arm>.dst`) is kept so the pro
distance can be read; it holds a client's stitches and **is never copied under
`docs/`** (Kent 2026-10-27).

## Analysis plan, fixed now

**Population.** Live pairs. Identical and repeat pairs are controls.

**Kent's pick** is mapped LEFT / RIGHT / tie onto before / after / same by the
side shown. **Statistic:** Cohen's kappa in `pooled.py`'s two forms (sides only
2 x 2; ties in 3 x 3 linear-weighted), 95% percentile bootstrap, 10,000
resamples, seed 20261011, over pairs AND over designs (`design`, so `mfab`,
`proseal`, `toat` each count once). A reading needs both intervals clear of zero
and at least 10 pairs where he chose a side; else "n too small" or "no evidence
either way". **No raw agreement figure is computed or printed (ROADMAP gate 4).**

**Cost reading, every live pair, both populations.** The four leads wok42
registered, directions fixed: `flow_circvar` lower, `long_share` lower,
`thread_density` higher, and `trims_per_1000` lower, with the same secondary
three; the trims-held / trims-moved split; the passing arms alone; and the
pre-registration's own expected picks against his.

**Distance reading, population A only (new).** For `cuts`, `hops` and
`needle_up_mm`, each design's DST is read with `pro_pair.pro_counts` and
`pro_baseline.needle_up`, the same code as on the pro's file of its job. The
distance is |ours - pro| (`pro_pooled.distance`); the instrument says the closer
side is better. Reported beside the same three figures as a plain cost (fewer is
better, no pro in it), over all population-A pairs and again per stratum, so the
`trims` control stands apart from the six construction arms, with kappa, both
intervals, n, and the count of pairs where his pick is farther from the pro.

**Controls**, reported as counts of his own answers: identical pairs called a
tie, repeats answered differently, and the left/right split.

## Honest limits, written before the data

- This reads pairs on 7 population-A jobs of 3 artworks. The interval over
  designs is wide; a clear reading is possible only for a large effect.
- Population B has no pro: it can say what Kent weighs on a Commons logo, not
  whether the pro agrees.
- Four of the seven construction arms only move letters of a certain kind
  (`text_lean_off` 10 mm and up, `italic_lean_off` slanted bars, `script_strokes_off`
  script, `fold_slivers_off` outlined art); few pairs each is expected.
- `mfab` is photo-class and routes through the photo-prep venv, linked from the
  primary checkout; another machine's render could differ at the margins.
- An arm whose OFF side is simply worse will be picked against, and that proves
  the instrument sees a gross defect, not that a flag is right.
