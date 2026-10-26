# Column reach census: which labelled letters reach the Column lane, and why not (2026-10-25)

W3-06. Engine 4fcdb4e6 (`origin/main` when measured). Tool
`digitizer/tools/column_reach_census.py`; labels `digitizer/testdata/lettering_truth.json`.

**Question.** The Column lettering lane (`cfg.lettering_columns`) carries the week's
construction gains (folds, lean, the inside stagger, small_bold), but only for letters
`columns.is_lettering` admits AND stage 7 hands to `lettering_columns_shape`. At the pro's
widths, which hand-labelled letters of the paired jobs get there, and why do the rest not?

**Answer.** 178 of 296 labelled letters reach the lane. Of the 118 misses, **two reasons
hold 100 (85%), and neither is the text tagger**: the stage-7 route (80, of which 76 are
small-text letters the bean rung takes ahead of the lane under `small_text_true_size`) and
BECKER's white faces, which are never sewn (20, `sew_enclosed_white` OFF). The tagger-level
misses are 18 and scattered: pieces of letters segmentation split, a script word, a
half-height "+", one N at a height ratio of 0.798. No textcluster ratio rescue raises
leave-one-job-out kappa. Under the small-text re-set flags already built OFF (#1029,
#1066), the bean letters reach the lane: 54 -> 133 of 144 letters on the five pairs with lines under 4 mm, reach kappa 0.462 -> 0.934.

## Labels (gate: labels first, committed before anything else)

- The label carry from the unmerged `claude/tagger-size-floor` lane
  (`word_tagger_eval.transfer_labels`, `--sizes`) is in `word_tagger_eval.py`. At the corpus
  width it gives the hand labels back EXACTLY on becker, tires, enthusiast, fremont and drone
  (`column_reach_census check`; `tests/test_column_reach_census.py` pins Tires).
- `fixtures.gaulke` is STALE on today's engine: one id, the F of ROOFING, moved since
  b7d63ae. `relabels.gaulke` (a NEW key) is the same labels with that one id; the old entry is
  untouched. `bridge` (4 ids) and `screenshot` (2) are stale too; neither is a census pair
  (Bridge's pro file is not on this machine).
- `pairs` (NEW keys, agent-labelled by eye on the drawn region map, each with its width and
  garment): `proseal_hat` (85.9 mm: PROSEAL 7, SPRAY FOAM + COATINGS 18), `proseal_beanie`
  (carried from the hat), `mfab_hat` (104.9 mm) and `mfab_lc` (96.7 mm), both on the rembg
  path. MFab's touching letters (AN, WE, IN, LL on the hat) are one letter each; its hyphen
  and the small keyline-cut pieces of letters are `ignore`.
- Golden Tee is digitized and left unscored: the truth file's own call (its bevel has no
  honest letter / non-letter split).

## The census at the pro's widths (OFF = main's defaults)

| pair | job | width mm | letters | detected | reached | detect kappa | reach kappa | false + | aspect | height_ratio | other_thread | cluster_of_one | stage7_route | (of which bean) | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | fremont | 92.6 | 33 | 33 | 12 | 0.338 | 0.478 | 58 | 0 | 0 | 0 | 0 | 21 | 21 | 0 |
| hotel_fremont_patch | fremont | 92.5 | 33 | 33 | 12 | 0.338 | 0.478 | 58 | 0 | 0 | 0 | 0 | 21 | 21 | 0 |
| precision_drone | drone | 62.6 | 28 | 16 | 16 | 0.602 | 0.602 | 3 | 6 | 0 | 1 | 0 | 3 | 0 | distance 1, stroke_cv 1 |
| proseal_hat | proseal | 85.9 | 25 | 24 | 7 | 0.969 | 0.335 | 0 | 0 | 1 | 0 | 0 | 17 | 17 | 0 |
| proseal_beanie | proseal | 75.0 | 25 | 24 | 7 | 0.969 | 0.335 | 0 | 0 | 1 | 0 | 0 | 17 | 16 | 0 |
| mfab_hat | mfab | 104.9 | 16 | 15 | 15 | 0.955 | 0.955 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| mfab_lc | mfab | 96.7 | 18 | 16 | 15 | 0.704 | 0.850 | 7 | 1 | 1 | 0 | 0 | 1 | 1 | 0 |
| becker_hat_large | becker | 101.9 | 11 | 11 | 6 | 1.000 | 0.459 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | unsewn 5 |
| becker_lc_large | becker | 95.7 | 11 | 11 | 6 | 1.000 | 0.459 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | unsewn 5 |
| becker_hat_small | becker | 76.5 | 11 | 11 | 6 | 1.000 | 0.459 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | unsewn 5 |
| becker_chest_small | becker | 76.5 | 11 | 11 | 6 | 1.000 | 0.459 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | unsewn 5 |
| gaulke_roofing_hat | gaulke | 114.2 | 35 | 35 | 35 | 0.914 | 0.914 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaulke_roofing_lc | gaulke | 95.2 | 35 | 35 | 35 | 0.917 | 0.917 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tires_hat_3d | tires | 114.3 | 4 | 0 | 0 | 0.000 | 0.000 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| **all** | | | 296 | 275 | 178 | 0.653 [0.428, 0.928] | 0.650 [0.456, 0.823] | 130 | 10 | 5 | 1 | 0 | 80 | 76 | distance 1, stroke_cv 1, unsewn 20 |

Not scored: goldentee_hat (no hand labels: its bevel has no honest letter call).

Brackets: a 95% bootstrap over JOBS. Detection kappa is "labelled letter" against `is_lettering` over every scored region;
reach kappa the same against "built by the lane" (ROADMAP gate 4: chance-corrected, never
raw agreement). Fremont's detection kappa is 0.338 because the house-angle group admits 58
pieces of its rope border; **none of them is built by the lane** (reach kappa on the re-set
arm is 1.000), so they cost nothing in stitches. Gaulke's 2 false positives are the house's
window panes, tagged as a 2x2 word and built.

### Every miss that is not the bean rung or a white face

| pair | line | shape | h x w mm | reason | value / threshold | partner | house | split |
|---|---|---|---|---|---|---|---|---|
| precision_drone | THERMAL | S07b6b7d7 | 4.52 x 6.39 | aspect | 1.415 / 1.400 |  | aspect |  |
| precision_drone | THERMAL | S99b02b06 | 4.52 x 5.56 | guard:ink_stray |  |  |  |  |
| precision_drone | AND DRONE | S0e857405 | 2.32 x 3.34 | other_thread | 18.200 / 0.000 |  |  |  |
| precision_drone | THERMAL | S3fa78778 | 4.48 x 5.29 | guard:ink_stray |  |  |  |  |
| precision_drone | THERMAL | S755bef70 | 2.13 x 5.29 | aspect | 2.486 / 1.400 |  | aspect | 1 of 2 |
| precision_drone | THERMAL | Sb2de8c40 | 2.2 x 4.77 | aspect | 2.170 / 1.400 |  | aspect | 1 of 2 |
| precision_drone | THERMAL | S023dfb17 | 2.53 x 4.15 | aspect | 1.644 / 1.400 |  | aspect | 1 of 2 |
| precision_drone | THERMAL | S6bc433a5 | 2.61 x 1.55 | distance | 30.733 / 13.554 | S99b02b06 | group_of_1 | 1 of 2 |
| precision_drone | THERMAL | S885001f8 | 3.09 x 5.38 | aspect | 1.738 / 1.400 |  | aspect | 1 of 2 |
| precision_drone | THERMAL | S95978c7e | 3.68 x 5.07 | guard:ink_stray |  |  |  | 1 of 2 |
| precision_drone | THERMAL | S4c4c677f | 2.13 x 6.11 | aspect | 2.867 / 1.400 |  | aspect | 1 of 2 |
| precision_drone | THERMAL | S4ba0c4f5 | 4.48 x 4.88 | stroke_cv | 0.749 / 0.550 |  | group_of_1 | 1 of 2 |
| proseal_hat | SPRAY FOAM + COATINGS | Sbcb723b0 | 1.52 x 1.52 | height_ratio | 0.483 / 0.800 | S497fc370 | group_of_1 |  |
| proseal_beanie | SPRAY FOAM + COATINGS | S324e0b95 | 1.33 x 1.33 | height_ratio | 0.483 / 0.800 | S40dc3e40 | group_of_1 |  |
| proseal_beanie | SPRAY FOAM + COATINGS | S1ea08cef | 2.75 x 2.28 | rung:run_outline |  |  |  |  |
| mfab_hat | M-FAB | Sfa7f5274 | 6.52 x 17.62 | aspect | 2.704 / 1.400 |  | aspect |  |
| mfab_lc | M-FAB | Sa8d5d460 | 6.12 x 16.27 | aspect | 2.659 / 1.400 |  | aspect |  |
| mfab_lc | AND WELDING LLC | S81d1d4a6 | 7.9 x 6.25 | height_ratio | 0.798 / 0.800 | Sbd0d3e9f | group_of_1 |  |
| tires_hat_3d | Tires | S396ab4ae | 24.6 x 93.25 | aspect | 3.790 / 1.400 |  | aspect |  |
| tires_hat_3d | Tires | S667dbd3b | 19.43 x 64.98 | aspect | 3.345 / 1.400 |  | aspect |  |
| tires_hat_3d | Tires | Sdab4587a | 32.7 x 31.73 | height_ratio | 0.168 / 0.800 | S91cf86bf | group_of_1 |  |
| tires_hat_3d | Tires | S91cf86bf | 5.5 x 5.72 | height_ratio | 0.168 / 0.800 | Sdab4587a | group_of_1 |  |

(The 76 `rung:bean_letter` rows and the 20 BECKER `unsewn:white` rows are left out here. `other_thread` on Drone's A reads ΔE 18.2 against a threshold of IDENTITY: `small_text._core`.)

- **Drone's THERMAL at 62.6 mm**: E, R, A and L each come out of segmentation as two
  same-thread pieces split through the middle (`split`, "1 of 2"); a half letter is too wide
  or too blotchy for the door, and T and H, left a line of two, are house-group-only and
  refused by the ink guard (no text letter shares their orange). M is whole at aspect 1.415.
- **Drone's A of AND** IS tagged (wide-letter adoption, aspect 1.436), then stripped by
  true-size restore as a stray: `small_text._core` (small_text.py:294-310) reads a line as
  ONE thread by identity, and the A is 2564 against the line's 1972, ΔE 18.2, inside the
  tagger's own one-ink tolerance (20).
- **MFab's F**: the art's keyline cuts the F's top bar off as its own region (aspect 2.7).
- **MFab LC's N of AND**: height ratio 0.798 against `LETTER_HEIGHT_RATIO` 0.8 (its
  diagonal's spike makes it 7.9 mm against the line's 6.3).
- **ProSeal's "+"**: 1.5 mm against 3.15 mm caps, ratio 0.48. The pro sews it.
- **Tires**: a whole-word script region and its dot; no grouping tagger finds them.

## Tagger rescues: in-sample only (held-out = today)

Each textcluster constant moved for one census call (`grid`, `@NAME`; nothing shipped), on
every labelled pair. Held-out: each JOB is scored at the value the OTHER jobs prefer.

| pair | off det/letters, fp, kappa | h078 det/letters, fp, kappa | h075 det/letters, fp, kappa | h070 det/letters, fp, kappa | a150 det/letters, fp, kappa | a180 det/letters, fp, kappa | m2 det/letters, fp, kappa | de30 det/letters, fp, kappa |
|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 59, 0.331 | 33/33, 59, 0.331 | 33/33, 60, 0.324 | 33/33, 58, 0.338 |
| hotel_fremont_patch | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 58, 0.338 | 33/33, 59, 0.331 | 33/33, 59, 0.331 | 33/33, 60, 0.324 | 33/33, 58, 0.338 |
| precision_drone | 16/28, 3, 0.602 | 16/28, 3, 0.602 | 16/28, 3, 0.602 | 16/28, 3, 0.602 | 16/28, 3, 0.602 | 16/28, 3, 0.602 | 16/28, 5, 0.561 | 18/28, 3, 0.664 |
| proseal_hat | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 |
| proseal_beanie | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 | 24/25, 0, 0.969 |
| mfab_hat | 15/16, 0, 0.955 | 15/16, 0, 0.955 | 15/16, 0, 0.955 | 15/16, 0, 0.955 | 15/16, 0, 0.955 | 14/15, 0, 0.953 | 15/16, 2, 0.870 | 15/16, 0, 0.955 |
| mfab_lc | 16/18, 7, 0.704 | 17/18, 7, 0.741 | 17/18, 7, 0.741 | 17/18, 7, 0.741 | 16/18, 7, 0.704 | 16/18, 7, 0.704 | 16/18, 7, 0.704 | 16/18, 7, 0.704 |
| becker_hat_large | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 |
| becker_lc_large | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 |
| becker_hat_small | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 |
| becker_chest_small | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 | 11/11, 0, 1.000 |
| gaulke_roofing_hat | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 | 35/35, 2, 0.914 |
| gaulke_roofing_lc | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 | 35/35, 2, 0.917 |
| tires_hat_3d | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 | 0/4, 0, 0.000 |

| | off | h078 | h075 | h070 | a150 | a180 | m2 | de30 |
|---|---|---|---|---|---|---|---|---|
| pooled kappa, in-sample | 0.653 | 0.655 | 0.655 | 0.655 | 0.649 | 0.648 | 0.636 | 0.658 |

Best in-sample: de30. Held-out (leave one JOB out, the value best on the other jobs): 0.653 against today's 0.653. Picks: becker -> de30, drone -> h078, fremont -> de30, gaulke -> de30, mfab -> de30, proseal -> de30, tires -> de30


`h078` admits MFab LC's N; `de30` admits Drone's T and H only by merging THERMAL's orange
into PRECISION's grey cluster, the split `TEXT_CLUSTER_DELTA_E_MAX`'s own comment keeps on
purpose. Each wins its own job; held-out stays 0.653 for all. **Reported, not built.**

## The top reason is stage 7: file:line and the rule

- `digitizer_core/stage7_sequence.py:2960`: the bean-letter rung
  (`p.region.meta.get(BEAN_LETTER_KEY)`) runs ahead of the Column lane
  (`stage7_sequence.py:3184`). Its tags come from `beanletters.tag_bean_letters`
  (`beanletters.py:89-95`, gated by `cfg.bean_letter_max_stroke_mm`), which
  `small_text_true_size` (ON, Kent WoK 56) sets to 0.5 (`config.py:95-97`,
  `SMALL_TEXT_TRUE_SIZE`). 76 of the 80 stage-7 misses are this rung.
- The pro sews every one of those lines as satin columns at about 4 mm
  (`pro-rules-across-jobs`, `small-text-floor-2026-10-24`).
- **Proposed rule: no new rule; it is built.** A line the small-text re-set raises
  (`small_text_cap_mm` 4.0 and its set, #1029; `small_text_cap_reach_edges`, #1066; both OFF)
  is left out of the bean tagger and sews on the Column lane. Measured, the re-set arm:

**OFF** (main), the five pairs with lines under 4 mm:

| pair | job | width mm | letters | detected | reached | detect kappa | reach kappa | false + | aspect | height_ratio | other_thread | cluster_of_one | stage7_route | (of which bean) | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | fremont | 92.6 | 33 | 33 | 12 | 0.338 | 0.478 | 58 | 0 | 0 | 0 | 0 | 21 | 21 | 0 |
| hotel_fremont_patch | fremont | 92.5 | 33 | 33 | 12 | 0.338 | 0.478 | 58 | 0 | 0 | 0 | 0 | 21 | 21 | 0 |
| precision_drone | drone | 62.6 | 28 | 16 | 16 | 0.602 | 0.602 | 3 | 6 | 0 | 1 | 0 | 3 | 0 | distance 1, stroke_cv 1 |
| proseal_hat | proseal | 85.9 | 25 | 24 | 7 | 0.969 | 0.335 | 0 | 0 | 1 | 0 | 0 | 17 | 17 | 0 |
| proseal_beanie | proseal | 75.0 | 25 | 24 | 7 | 0.969 | 0.335 | 0 | 0 | 1 | 0 | 0 | 17 | 16 | 0 |
| **all** | | | 144 | 130 | 54 | 0.509 [0.338, 0.969] | 0.462 [0.335, 0.602] | 119 | 6 | 2 | 1 | 0 | 79 | 75 | distance 1, stroke_cv 1 |

**Re-set ON** (`small_text_cap_mm` 4.0, `_max_width_scale` 1.05, `_min_stroke_mm` 0.85, `_letter_gap_mm` 0.25, `_bold_scale` 1.45, `lettering_columns_small_bold`, `small_text_cap_reach_edges`: the flip sheet's set, #1029 + #1066):

| pair | job | width mm | letters | detected | reached | detect kappa | reach kappa | false + | aspect | height_ratio | other_thread | cluster_of_one | stage7_route | (of which bean) | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | fremont | 92.6 | 33 | 33 | 33 | 0.338 | 1.000 | 58 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hotel_fremont_patch | fremont | 92.5 | 33 | 33 | 33 | 0.338 | 1.000 | 58 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| precision_drone | drone | 62.6 | 28 | 19 | 19 | 0.694 | 0.694 | 3 | 6 | 0 | 0 | 0 | 2 | 0 | stroke_cv 1 |
| proseal_hat | proseal | 85.9 | 25 | 24 | 24 | 0.969 | 0.969 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| proseal_beanie | proseal | 75.0 | 25 | 24 | 24 | 0.969 | 0.969 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **all** | | | 144 | 133 | 133 | 0.522 [0.338, 0.969] | 0.934 [0.694, 1.000] | 119 | 6 | 2 | 0 | 0 | 2 | 0 | stroke_cv 1 |

  That flip is Kent's (layout from renders, 2026-10-22). Crops below. Stroke weight of the
  re-set columns is gate 1 (0.70-0.85 mm against his 1.1-1.26: `small-text-floor`).
- `stage7_sequence.py` and `columns.py` are in open PRs and were not edited.
- The white faces (`sew_enclosed_white`, `config.py:1566`, held OFF 2026-10-24) are their own
  packet (`white-rerule-packet-2026-10-25`); not touched here.
- `small_text._core` (not in an open PR, not this lane's file): reading the line's ink
  through the tagger's `_same_ink` instead of thread identity would keep Drone's A of AND
  at main's defaults. Proposed, not built; under the re-set arm the A reaches the lane anyway.

## Rescued letters: letter_pieces, off / re-set / pro

`tools/letter_pieces.py` on each letter the re-set brings to the lane, in our OFF file, our
re-set file and the pro's (registered, `small_text_floor_census.register`), each read at
`MIN_CROSS` 0.5 mm (its 1.0 mm skips every cross of our 0.7-0.85 mm small columns; one
reader on all three). OFF reads n/a by construction: those letters sew as bean runs, which
have no satin crosses. A letter that joins its neighbour in a file's cross coverage, or
that the registration cannot place (IoU under 0.3), is n/a for that file.

Medians per line over the letters each file could read:

| pair | line | letters rescued | file | read | pieces | patches | crosses | max cross mm | same hole |
|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | THE | 3 | off | 1/3 | 1 | 2 | 32 | 2.1 | 0.207 |
| hotel_fremont_hat | THE | 3 | reset | 3/3 | 3 | 0 | 63 | 1.99 | 0.102 |
| hotel_fremont_hat | THE | 3 | pro | 2/3 | 3 | 3 | 86 | 2.6 | 0.037 |
| hotel_fremont_hat | EAT STAY PLAY | 11 | off | 0/11 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_hat | EAT STAY PLAY | 11 | reset | 6/11 | 1.5 | 1.5 | 42 | 1.565 | 0.079 |
| hotel_fremont_hat | EAT STAY PLAY | 11 | pro | 0/11 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_hat | EST 1895 | 7 | off | 0/7 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_hat | EST 1895 | 7 | reset | 2/7 | 0.5 | 7 | 60.5 | 1.69 | 0.0375 |
| hotel_fremont_hat | EST 1895 | 7 | pro | 0/7 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_patch | THE | 3 | off | 0/3 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_patch | THE | 3 | reset | 2/3 | 2 | 2 | 58.5 | 1.525 | 0.0665 |
| hotel_fremont_patch | THE | 3 | pro | 3/3 | 2 | 1 | 50 | 1.6 | 0.043 |
| hotel_fremont_patch | EAT STAY PLAY | 11 | off | 0/11 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_patch | EAT STAY PLAY | 11 | reset | 4/11 | 3.5 | 3.5 | 92.5 | 1.71 | 0.067 |
| hotel_fremont_patch | EAT STAY PLAY | 11 | pro | 7/11 | 3 | 8 | 110 | 1.6 | 0.04 |
| hotel_fremont_patch | EST 1895 | 7 | off | 0/7 | n/a | n/a | n/a | n/a | n/a |
| hotel_fremont_patch | EST 1895 | 7 | reset | 2/7 | 1.5 | 0.5 | 44 | 1.695 | 0.115 |
| hotel_fremont_patch | EST 1895 | 7 | pro | 1/7 | 2 | 2 | 44 | 1.8 | 0.025 |
| precision_drone | AND DRONE | 1 | off | 1/1 | 1 | 1 | 33 | 2.5 | 0.194 |
| precision_drone | AND DRONE | 1 | reset | 1/1 | 2 | 0 | 36 | 2.83 | 0.088 |
| precision_drone | AND DRONE | 1 | pro | 1/1 | 5 | 1 | 107 | 1.46 | 0.04 |
| precision_drone | THERMAL | 2 | off | 2/2 | 8 | 2 | 200 | 4.6 | 0.053 |
| precision_drone | THERMAL | 2 | reset | 1/2 | 3 | 0 | 71 | 3.5 | 0.044 |
| precision_drone | THERMAL | 2 | pro | 2/2 | 3.5 | 0.5 | 108.5 | 2.335 | 0.0405 |
| proseal_hat | SPRAY FOAM + COATINGS | 17 | off | 0/17 | n/a | n/a | n/a | n/a | n/a |
| proseal_hat | SPRAY FOAM + COATINGS | 17 | reset | 14/17 | 1 | 3 | 45 | 0.99 | 0.0645 |
| proseal_hat | SPRAY FOAM + COATINGS | 17 | pro | 15/17 | 2 | 1 | 67 | 1.56 | 0.039 |
| proseal_beanie | SPRAY FOAM + COATINGS | 17 | off | 0/17 | n/a | n/a | n/a | n/a | n/a |
| proseal_beanie | SPRAY FOAM + COATINGS | 17 | reset | 8/17 | 1 | 2 | 39 | 1.11 | 0.0815 |
| proseal_beanie | SPRAY FOAM + COATINGS | 17 | pro | 14/17 | 2 | 2.5 | 64 | 1.63 | 0.0355 |

Ours under the re-set sews these letters as satin pieces, as the pro does, where OFF has none. Our crosses are shorter (ProSeal median max cross 0.99 mm against his 1.56): the stroke-weight half, gate 1.

<details><summary>Every rescued letter, every file</summary>

| pair | line | letter | file | pieces | patches | flat_share | drift_p90 | long_share | max_cross | same_hole | crosses | iou |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | THE | Safd5df52 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.23 |
| hotel_fremont_hat | THE | Safd5df52 | reset | 3 | 2 | 0.441 | 83.0 | 0.0 | 1.99 | 0.056 | 76 | 0.57 |
| hotel_fremont_hat | THE | Safd5df52 | pro | 3 | 3 | 0.667 | 28.3 | 0.0 | 2.6 | 0.037 | 86 | 0.41 |
| hotel_fremont_hat | THE | S3ddcec6c | off | 1 | 2 | 1.0 | 0.0 | 0.0 | 2.1 | 0.207 | 32 | 0.49 |
| hotel_fremont_hat | THE | S3ddcec6c | reset | 4 | 0 | 0.286 | 24.8 | 0.0 | 2.42 | 0.102 | 63 | 0.51 |
| hotel_fremont_hat | THE | S3ddcec6c | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.02 |
| hotel_fremont_hat | THE | S42e426b8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | THE | S42e426b8 | reset | 2 | 0 | 0.652 | 26.1 | 0.0 | 1.75 | 0.146 | 43 | 0.52 |
| hotel_fremont_hat | THE | S42e426b8 | pro | 3 | 3 | 0.667 | 28.3 | 0.0 | 2.6 | 0.037 | 86 | 0.35 |
| hotel_fremont_hat | EAT STAY PLAY | S177d120f | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.1 |
| hotel_fremont_hat | EAT STAY PLAY | S177d120f | reset | 1 | 1 | 0.531 | 55.7 | 0.0 | 1.33 | 0.0 | 41 | 0.48 |
| hotel_fremont_hat | EAT STAY PLAY | S177d120f | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | EAT STAY PLAY | S5c2d8e5a | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S5c2d8e5a | reset | 3 | 6 | 0.574 | 42.1 | 0.0 | 1.9 | 0.079 | 98 | 0.39 |
| hotel_fremont_hat | EAT STAY PLAY | S5c2d8e5a | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S050ca08b | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.12 |
| hotel_fremont_hat | EAT STAY PLAY | S050ca08b | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.08 |
| hotel_fremont_hat | EAT STAY PLAY | S050ca08b | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | EAT STAY PLAY | Sfb387a73 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.08 |
| hotel_fremont_hat | EAT STAY PLAY | Sfb387a73 | reset | 3 | 6 | 0.574 | 42.1 | 0.0 | 1.9 | 0.079 | 98 | 0.46 |
| hotel_fremont_hat | EAT STAY PLAY | Sfb387a73 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S47b1a317 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.09 |
| hotel_fremont_hat | EAT STAY PLAY | S47b1a317 | reset | 1 | 2 | 0.545 | 33.3 | 0.0 | 1.26 | 0.15 | 43 | 0.5 |
| hotel_fremont_hat | EAT STAY PLAY | S47b1a317 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | Sb18dbd63 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.1 |
| hotel_fremont_hat | EAT STAY PLAY | Sb18dbd63 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.03 |
| hotel_fremont_hat | EAT STAY PLAY | Sb18dbd63 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S793ddbbb | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.11 |
| hotel_fremont_hat | EAT STAY PLAY | S793ddbbb | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.03 |
| hotel_fremont_hat | EAT STAY PLAY | S793ddbbb | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | EAT STAY PLAY | Sa2e2f98e | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.11 |
| hotel_fremont_hat | EAT STAY PLAY | Sa2e2f98e | reset | 1 | 1 | 0.524 | 21.8 | 0.0 | 1.3 | 0.0 | 28 | 0.48 |
| hotel_fremont_hat | EAT STAY PLAY | Sa2e2f98e | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | EAT STAY PLAY | Sd3e6b4c8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.11 |
| hotel_fremont_hat | EAT STAY PLAY | Sd3e6b4c8 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.05 |
| hotel_fremont_hat | EAT STAY PLAY | Sd3e6b4c8 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S77bf5723 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.02 |
| hotel_fremont_hat | EAT STAY PLAY | S77bf5723 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.09 |
| hotel_fremont_hat | EAT STAY PLAY | S77bf5723 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EAT STAY PLAY | S83a2afe8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.1 |
| hotel_fremont_hat | EAT STAY PLAY | S83a2afe8 | reset | 2 | 0 | 0.605 | 40.4 | 0.0 | 1.8 | 0.083 | 38 | 0.48 |
| hotel_fremont_hat | EAT STAY PLAY | S83a2afe8 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_hat | EST 1895 | S8093c5d6 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S8093c5d6 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.08 |
| hotel_fremont_hat | EST 1895 | S8093c5d6 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | Sc16f1a33 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | Sc16f1a33 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.08 |
| hotel_fremont_hat | EST 1895 | Sc16f1a33 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S549f2371 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S549f2371 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.08 |
| hotel_fremont_hat | EST 1895 | S549f2371 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | Sfed26d33 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | Sfed26d33 | reset | 1 | 6 | n/a | 29.4 | 0.0 | 1.1 | 0.019 | 59 | 0.56 |
| hotel_fremont_hat | EST 1895 | Sfed26d33 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.02 |
| hotel_fremont_hat | EST 1895 | S88c1806e | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S88c1806e | reset | 0 | 8 | n/a | n/a | 0.0 | 2.28 | 0.056 | 62 | 0.55 |
| hotel_fremont_hat | EST 1895 | S88c1806e | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S3d895b56 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S3d895b56 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.07 |
| hotel_fremont_hat | EST 1895 | S3d895b56 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.03 |
| hotel_fremont_hat | EST 1895 | S9c2c82e9 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_hat | EST 1895 | S9c2c82e9 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.05 |
| hotel_fremont_hat | EST 1895 | S9c2c82e9 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | THE | S666da526 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | THE | S666da526 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | THE | S666da526 | pro | 1 | 3 | 0.632 | 29.1 | 0.0 | 1.7 | 0.043 | 50 | 0.43 |
| hotel_fremont_patch | THE | S3ddcec6c | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | THE | S3ddcec6c | reset | 3 | 1 | 0.562 | 26.6 | 0.0 | 1.5 | 0.048 | 66 | 0.54 |
| hotel_fremont_patch | THE | S3ddcec6c | pro | 3 | 1 | 0.562 | 33.6 | 0.0 | 1.4 | 0.104 | 52 | 0.4 |
| hotel_fremont_patch | THE | S42e426b8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | THE | S42e426b8 | reset | 1 | 3 | 0.5 | 26.6 | 0.0 | 1.55 | 0.085 | 51 | 0.58 |
| hotel_fremont_patch | THE | S42e426b8 | pro | 2 | 0 | 0.632 | 26.3 | 0.0 | 1.6 | 0.03 | 35 | 0.38 |
| hotel_fremont_patch | EAT STAY PLAY | S177d120f | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S177d120f | reset | 1 | 3 | 0.5 | 31.7 | 0.0 | 1.36 | 0.073 | 45 | 0.49 |
| hotel_fremont_patch | EAT STAY PLAY | S177d120f | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2 |
| hotel_fremont_patch | EAT STAY PLAY | S5c2d8e5a | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S5c2d8e5a | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S5c2d8e5a | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.24 |
| hotel_fremont_patch | EAT STAY PLAY | S050ca08b | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S050ca08b | reset | 5 | 4 | 0.429 | 102.7 | 0.0 | 1.71 | 0.061 | 140 | 0.35 |
| hotel_fremont_patch | EAT STAY PLAY | S050ca08b | pro | 3 | 8 | 0.583 | 32.8 | 0.0 | 2.51 | 0.04 | 110 | 0.38 |
| hotel_fremont_patch | EAT STAY PLAY | Sfb387a73 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | Sfb387a73 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | EAT STAY PLAY | Sfb387a73 | pro | 2 | 6 | 0.639 | 26.3 | 0.0 | 1.5 | 0.04 | 83 | 0.56 |
| hotel_fremont_patch | EAT STAY PLAY | S47b1a317 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S47b1a317 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | EAT STAY PLAY | S47b1a317 | pro | 5 | 8 | 0.603 | 33.7 | 0.0 | 1.6 | 0.033 | 135 | 0.32 |
| hotel_fremont_patch | EAT STAY PLAY | Sb18dbd63 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | Sb18dbd63 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.29 |
| hotel_fremont_patch | EAT STAY PLAY | Sb18dbd63 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.3 |
| hotel_fremont_patch | EAT STAY PLAY | S793ddbbb | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S793ddbbb | reset | 5 | 4 | 0.429 | 102.7 | 0.0 | 1.71 | 0.061 | 140 | 0.41 |
| hotel_fremont_patch | EAT STAY PLAY | S793ddbbb | pro | 3 | 8 | 0.583 | 32.8 | 0.0 | 2.51 | 0.04 | 110 | 0.39 |
| hotel_fremont_patch | EAT STAY PLAY | Sa2e2f98e | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | Sa2e2f98e | reset | 2 | 0 | 0.571 | 46.8 | 0.0 | 2.06 | 0.091 | 35 | 0.48 |
| hotel_fremont_patch | EAT STAY PLAY | Sa2e2f98e | pro | 3 | 8 | 0.583 | 32.8 | 0.0 | 2.51 | 0.04 | 110 | 0.31 |
| hotel_fremont_patch | EAT STAY PLAY | Sd3e6b4c8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | Sd3e6b4c8 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | Sd3e6b4c8 | pro | 2 | 6 | 0.639 | 26.3 | 0.0 | 1.5 | 0.04 | 83 | 0.33 |
| hotel_fremont_patch | EAT STAY PLAY | S77bf5723 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S77bf5723 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S77bf5723 | pro | 5 | 8 | 0.603 | 33.7 | 0.0 | 1.6 | 0.033 | 135 | 0.34 |
| hotel_fremont_patch | EAT STAY PLAY | S83a2afe8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EAT STAY PLAY | S83a2afe8 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.02 |
| hotel_fremont_patch | EAT STAY PLAY | S83a2afe8 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.24 |
| hotel_fremont_patch | EST 1895 | S8093c5d6 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S8093c5d6 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S8093c5d6 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2 |
| hotel_fremont_patch | EST 1895 | Sc16f1a33 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | Sc16f1a33 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | EST 1895 | Sc16f1a33 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.27 |
| hotel_fremont_patch | EST 1895 | S549f2371 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S549f2371 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.01 |
| hotel_fremont_patch | EST 1895 | S549f2371 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.18 |
| hotel_fremont_patch | EST 1895 | Sfed26d33 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | Sfed26d33 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | Sfed26d33 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.15 |
| hotel_fremont_patch | EST 1895 | S88c1806e | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S88c1806e | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S88c1806e | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.23 |
| hotel_fremont_patch | EST 1895 | S3d895b56 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S3d895b56 | reset | 2 | 0 | 0.652 | 122.7 | 0.0 | 1.55 | 0.13 | 56 | 0.54 |
| hotel_fremont_patch | EST 1895 | S3d895b56 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.23 |
| hotel_fremont_patch | EST 1895 | S9c2c82e9 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| hotel_fremont_patch | EST 1895 | S9c2c82e9 | reset | 1 | 1 | 0.63 | 29.0 | 0.0 | 1.84 | 0.1 | 32 | 0.44 |
| hotel_fremont_patch | EST 1895 | S9c2c82e9 | pro | 2 | 2 | 0.472 | 43.4 | 0.0 | 1.8 | 0.025 | 44 | 0.37 |
| precision_drone | AND DRONE | S0e857405 | off | 1 | 1 | n/a | 23.1 | 0.0 | 2.5 | 0.194 | 33 | 0.62 |
| precision_drone | AND DRONE | S0e857405 | reset | 2 | 0 | 0.917 | 22.7 | 0.0 | 2.83 | 0.088 | 36 | 0.53 |
| precision_drone | AND DRONE | S0e857405 | pro | 5 | 1 | 0.588 | 21.9 | 0.0 | 1.46 | 0.04 | 107 | 0.42 |
| precision_drone | THERMAL | S99b02b06 | off | 8 | 2 | 1.0 | 34.8 | 0.0 | 4.6 | 0.053 | 200 | 0.49 |
| precision_drone | THERMAL | S99b02b06 | reset | 3 | 0 | 0.96 | 13.4 | 0.0 | 3.5 | 0.044 | 71 | 0.68 |
| precision_drone | THERMAL | S99b02b06 | pro | 3 | 1 | 0.976 | 13.5 | 0.0 | 2.3 | 0.047 | 68 | 0.7 |
| precision_drone | THERMAL | S95978c7e | off | 8 | 2 | 1.0 | 34.8 | 0.0 | 4.6 | 0.053 | 200 | 0.39 |
| precision_drone | THERMAL | S95978c7e | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2 |
| precision_drone | THERMAL | S95978c7e | pro | 4 | 0 | 0.2 | 134.6 | 0.0 | 2.37 | 0.034 | 149 | 0.47 |
| proseal_hat | SPRAY FOAM + COATINGS | S8b97b810 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S8b97b810 | reset | 2 | 2 | 0.585 | 33.7 | 0.0 | 1.08 | 0.123 | 69 | 0.53 |
| proseal_hat | SPRAY FOAM + COATINGS | S8b97b810 | pro | 4 | 7 | 0.549 | 20.0 | 0.0 | 2.1 | 0.039 | 138 | 0.49 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7bc7c59 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7bc7c59 | reset | 2 | 5 | 0.118 | 106.5 | 0.0 | 0.91 | 0.062 | 72 | 0.59 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7bc7c59 | pro | 1 | 0 | 0.25 | 144.0 | 0.0 | 1.43 | 0.0 | 68 | 0.59 |
| proseal_hat | SPRAY FOAM + COATINGS | Sef34328d | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sef34328d | reset | 2 | 1 | 0.525 | 33.3 | 0.0 | 1.03 | 0.02 | 52 | 0.5 |
| proseal_hat | SPRAY FOAM + COATINGS | Sef34328d | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.2 |
| proseal_hat | SPRAY FOAM + COATINGS | S7d45a1d4 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S7d45a1d4 | reset | 0 | 12 | n/a | n/a | 0.0 | 0.92 | 0.011 | 101 | 0.42 |
| proseal_hat | SPRAY FOAM + COATINGS | S7d45a1d4 | pro | 3 | 3 | 0.344 | 95.6 | 0.0 | 2.1 | 0.017 | 124 | 0.46 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb12674e1 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb12674e1 | reset | 0 | 8 | n/a | n/a | 0.0 | 0.89 | 0.067 | 68 | 0.58 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb12674e1 | pro | 1 | 0 | 0.246 | 147.7 | 0.0 | 1.43 | 0.015 | 69 | 0.53 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa5d4a236 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa5d4a236 | reset | 1 | 2 | n/a | 69.0 | 0.0 | 0.95 | 0.0 | 40 | 0.42 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa5d4a236 | pro | 2 | 0 | 0.178 | 124.2 | 0.0 | 1.5 | 0.0 | 107 | 0.48 |
| proseal_hat | SPRAY FOAM + COATINGS | Sdfefde46 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sdfefde46 | reset | 1 | 3 | 0.529 | 27.8 | 0.0 | 1.1 | 0.103 | 43 | 0.51 |
| proseal_hat | SPRAY FOAM + COATINGS | Sdfefde46 | pro | 4 | 7 | 0.549 | 20.0 | 0.0 | 2.1 | 0.039 | 138 | 0.35 |
| proseal_hat | SPRAY FOAM + COATINGS | S40ff16e7 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S40ff16e7 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.27 |
| proseal_hat | SPRAY FOAM + COATINGS | S40ff16e7 | pro | 1 | 0 | 0.149 | 131.7 | 0.0 | 1.36 | 0.076 | 67 | 0.52 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa862c243 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa862c243 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.3 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa862c243 | pro | 2 | 2 | 0.625 | 20.0 | 0.0 | 2.1 | 0.074 | 58 | 0.4 |
| proseal_hat | SPRAY FOAM + COATINGS | S21e0ed28 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S21e0ed28 | reset | 0 | 12 | n/a | n/a | 0.0 | 0.92 | 0.011 | 101 | 0.39 |
| proseal_hat | SPRAY FOAM + COATINGS | S21e0ed28 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.19 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb43e95d3 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb43e95d3 | reset | 1 | 2 | n/a | 78.4 | 0.0 | 0.91 | 0.0 | 35 | 0.46 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb43e95d3 | pro | 2 | 3 | 0.529 | 25.1 | 0.0 | 2.04 | 0.05 | 65 | 0.33 |
| proseal_hat | SPRAY FOAM + COATINGS | S497fc370 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S497fc370 | reset | 0 | 7 | n/a | n/a | 0.0 | 0.81 | 0.0 | 45 | 0.57 |
| proseal_hat | SPRAY FOAM + COATINGS | S497fc370 | pro | 1 | 0 | 0.151 | 132.0 | 0.0 | 1.43 | 0.0 | 53 | 0.56 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb5118d17 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb5118d17 | reset | 0 | 6 | n/a | n/a | 0.0 | 2.0 | 0.077 | 45 | 0.46 |
| proseal_hat | SPRAY FOAM + COATINGS | Sb5118d17 | pro | 2 | 1 | 0.947 | 46.0 | 0.0 | 1.56 | 0.07 | 46 | 0.54 |
| proseal_hat | SPRAY FOAM + COATINGS | S02d93c73 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S02d93c73 | reset | 0 | 3 | n/a | n/a | 0.0 | 1.1 | 0.235 | 37 | 0.47 |
| proseal_hat | SPRAY FOAM + COATINGS | S02d93c73 | pro | 2 | 1 | 0.742 | 15.9 | 0.0 | 1.46 | 0.128 | 42 | 0.52 |
| proseal_hat | SPRAY FOAM + COATINGS | S35d3fe62 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | S35d3fe62 | reset | 1 | 1 | 0.435 | 56.3 | 0.0 | 1.71 | 0.118 | 36 | 0.39 |
| proseal_hat | SPRAY FOAM + COATINGS | S35d3fe62 | pro | 2 | 2 | 0.625 | 20.0 | 0.0 | 2.1 | 0.074 | 58 | 0.38 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7559187 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7559187 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.25 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa7559187 | pro | 2 | 0 | 0.474 | 20.4 | 0.0 | 1.36 | 0.0 | 38 | 0.57 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa2014a25 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa2014a25 | reset | 1 | 1 | 0.065 | 15.0 | 0.0 | 2.16 | 0.2 | 42 | 0.51 |
| proseal_hat | SPRAY FOAM + COATINGS | Sa2014a25 | pro | 3 | 3 | 0.344 | 95.6 | 0.0 | 2.1 | 0.017 | 124 | 0.4 |
| proseal_beanie | SPRAY FOAM + COATINGS | S40dc3e40 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S40dc3e40 | reset | 3 | 0 | 0.566 | 33.4 | 0.0 | 1.08 | 0.08 | 53 | 0.49 |
| proseal_beanie | SPRAY FOAM + COATINGS | S40dc3e40 | pro | 5 | 5 | 0.578 | 22.0 | 0.0 | 1.8 | 0.043 | 127 | 0.37 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sd4d4a3c8 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sd4d4a3c8 | reset | 1 | 4 | 0.5 | 153.4 | 0.0 | 1.4 | 0.085 | 52 | 0.51 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sd4d4a3c8 | pro | 3 | 3 | 0.364 | 92.0 | 0.0 | 1.9 | 0.028 | 115 | 0.47 |
| proseal_beanie | SPRAY FOAM + COATINGS | S82c742f7 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S82c742f7 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S82c742f7 | pro | 1 | 0 | 0.266 | 150.7 | 0.0 | 1.34 | 0.016 | 64 | 0.37 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sadd61f74 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sadd61f74 | reset | 2 | 1 | 0.645 | 29.6 | 0.0 | 1.03 | 0.0 | 40 | 0.46 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sadd61f74 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.18 |
| proseal_beanie | SPRAY FOAM + COATINGS | S4a556caf | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S4a556caf | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S4a556caf | pro | 1 | 0 | 0.266 | 149.5 | 0.0 | 1.33 | 0.016 | 64 | 0.64 |
| proseal_beanie | SPRAY FOAM + COATINGS | S790660f0 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S790660f0 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S790660f0 | pro | 2 | 0 | 0.176 | 121.6 | 0.0 | 1.42 | 0.01 | 102 | 0.43 |
| proseal_beanie | SPRAY FOAM + COATINGS | S99842088 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S99842088 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S99842088 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.3 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sfbaa9b76 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sfbaa9b76 | reset | 1 | 4 | 0.5 | 153.4 | 0.0 | 0.95 | 0.0 | 38 | 0.43 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sfbaa9b76 | pro | 3 | 3 | 0.364 | 92.0 | 0.0 | 1.9 | 0.028 | 115 | 0.33 |
| proseal_beanie | SPRAY FOAM + COATINGS | S12a0d4e2 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S12a0d4e2 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S12a0d4e2 | pro | 5 | 5 | 0.578 | 22.0 | 0.0 | 1.8 | 0.043 | 127 | 0.44 |
| proseal_beanie | SPRAY FOAM + COATINGS | S2ec94bd2 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S2ec94bd2 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | S2ec94bd2 | pro | 5 | 4 | 0.302 | 130.2 | 0.0 | 1.94 | 0.058 | 199 | 0.31 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sf6a2965b | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sf6a2965b | reset | 1 | 2 | 0.533 | 26.6 | 0.0 | 1.08 | 0.0 | 30 | 0.45 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sf6a2965b | pro | 2 | 2 | 0.583 | 21.8 | 0.0 | 1.9 | 0.08 | 54 | 0.37 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb6fff7e0 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb6fff7e0 | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.04 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb6fff7e0 | pro | 1 | 0 | 0.16 | 131.6 | 0.0 | 1.33 | 0.0 | 50 | 0.66 |
| proseal_beanie | SPRAY FOAM + COATINGS | S8c8a3ad5 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S8c8a3ad5 | reset | 0 | 5 | n/a | n/a | 0.0 | 1.6 | 0.083 | 41 | 0.41 |
| proseal_beanie | SPRAY FOAM + COATINGS | S8c8a3ad5 | pro | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.29 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sc5bdca84 | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sc5bdca84 | reset | 1 | 1 | 0.632 | 29.7 | 0.0 | 1.14 | 0.276 | 31 | 0.41 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sc5bdca84 | pro | 0 | 3 | n/a | n/a | 0.0 | 1.46 | 0.143 | 38 | 0.36 |
| proseal_beanie | SPRAY FOAM + COATINGS | S3dfed7ad | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S3dfed7ad | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.12 |
| proseal_beanie | SPRAY FOAM + COATINGS | S3dfed7ad | pro | 2 | 2 | 0.583 | 21.8 | 0.0 | 1.9 | 0.08 | 54 | 0.5 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb30889ca | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb30889ca | reset | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.02 |
| proseal_beanie | SPRAY FOAM + COATINGS | Sb30889ca | pro | 2 | 0 | 0.684 | 25.1 | 0.0 | 1.26 | 0.0 | 36 | 0.81 |
| proseal_beanie | SPRAY FOAM + COATINGS | S1ea08cef | off | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0.0 |
| proseal_beanie | SPRAY FOAM + COATINGS | S1ea08cef | reset | 1 | 2 | 0.533 | 19.4 | 0.0 | 1.36 | 0.219 | 35 | 0.42 |
| proseal_beanie | SPRAY FOAM + COATINGS | S1ea08cef | pro | 0 | 3 | n/a | n/a | 0.0 | 1.46 | 0.143 | 38 | 0.38 |

</details>

Crops, off | re-set (ON) | pro, 40 px/mm, stitches only (no artwork tile):
`docs/renders/column-reach-census-2026-10-25/`.

- `hotel_fremont_hat_EAT_STAY_PLAY.jpg`
- `hotel_fremont_hat_EST_1895.jpg`
- `hotel_fremont_hat_THE.jpg`
- `hotel_fremont_patch_EAT_STAY_PLAY.jpg`
- `hotel_fremont_patch_EST_1895.jpg`
- `hotel_fremont_patch_THE.jpg`
- `precision_drone_AND_DRONE.jpg`
- `precision_drone_THERMAL.jpg`
- `proseal_beanie_SPRAY_FOAM___COATINGS.jpg`
- `proseal_hat_SPRAY_FOAM___COATINGS.jpg`
