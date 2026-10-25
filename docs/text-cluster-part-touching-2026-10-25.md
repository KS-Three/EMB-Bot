# Letters the text tagger misses: touches and overshoots (2026-10-25)

`cfg.text_cluster_part_touching`, built OFF. Task 5 of the 2026-10-23 team
plan: "letters the text tagger misses (fused serifs, AND's N)". Code:
`digitizer_core/textcluster.py` (`_neck_splits(touching=True)`, `_spans`,
`_adopt_band`, `TOUCH_MAX_MM`, `HEIGHT_BAND_MIN`); test
`digitizer/tests/test_text_cluster_part_touching.py`. Renders:
`docs/renders/text-cluster-part-touching-2026-10-25/`.

## How it was read

Six paired jobs at the pro's widths, the Studio's request through
`tools.pro_pair.digitize` (main's defaults), with the main checkout's rembg
venv so the photo prep is the product's: Fremont hat 92.6 and patch, MFab hat
104.9 and left chest 96.7, Precision Drone 62.6, ProSeal hat 85.9. The regions
entering `detect_text_clusters` were captured per job, so the tagger could be
re-run OFF and ON on exactly the pipeline's input. Ours vs the pro's: the
lettering board (`tools/lettering_board.py`) per line; per letter and per word
a scratch reader on `tools.letter_pieces` pieces (cross chains), each file in
its own frame, the letter's own colour block, our letter polygon mapped into
the pro's frame by `small_text_floor_census.register` and then shifted locally
(within 1.5 mm) onto his crosses, because the whole-design fit leaves his
lettering up to ~0.8 mm off. Trims are read from the DST only.

## The premise, measured

**Fremont's OTE and NT are NOT a tagger miss.** On the hat and the patch all
12 letters of HOTEL FREMONT trace as 12 separate regions and every one is
`text_candidate` (the art leaves 0.45 mm between O and T, 0.77 mm between N
and T). The fusion the 5-10 mm band (#1051) saw is in the SEWN file: the board's
reader finds 11 components in ours (O and T are one, 14.25 mm wide) against
the pro's 12 (`fremont_hat_OTE_off_on_pro.png`). That is stitch geometry,
not the tagger, and it is not built here. NT is apart in both files at main's
defaults.

**Which: PULL, not serif reach.** The touch is the O's right flank against the
T's hanging left serif. The trace leaves 0.62 mm there; our needle paths (the
letters' own black block) come to 0.14 mm -- 0.48 mm closed, 0.40 of it the
pull compensation both letters carry (`stitch_width_pull_mm` 0.4, 0.2 a side),
and neither letter's needles reach more than 0.38 mm past its trace anywhere,
so no serif overshoots. The board's reader paints 0.3 mm of thread and closes
the last 0.14. The pro's needle paths stay 0.36 mm apart at the same place
(his letters fitted locally). Pull compensation is ROADMAP gate 1 (fabric): a
sew-out question, not a layout flip.

**MFab's AND N is real, and there is a second miss beside it.**

| job | letter | what the tagger does today | why |
|---|---|---|---|
| MFab hat | I+N of WELDING | ONE region, `text_candidate` as one glyph | the I's top touches the N's spike at a neck under 0.08 mm (an opening of r 0.02 mm parts them); 8.75 x 8.47 mm, aspect 1.03, so the letter door admits it and the wide pass (aspect > 1.4 only) never looks |
| MFab LC | N of AND | no tag at all | 7.90 mm tall beside A and D at 6.25-6.31: height ratio 0.79 < `LETTER_HEIGHT_RATIO` 0.8 |
| MFab LC | N, G of WELDING | `lettering_group` only (house angle), no text cluster | N 8.19 (0.77-0.79), G 9.15 (0.71) |
| MFab hat | A+N of AND, W+E of WELDING | split by `text_cluster_wide_letters` (ON) | aspect 1.76 and 2.55 |
| Fremont, Drone, ProSeal | every letter of every pinned line | tagged | -- |

The face's N carries a spike past the cap height and the G a tail below it:
each SPANS the line's cap band and overshoots it. That is what separates them
from a letter of another line, which sits above or below the band.

## The rules

1. **A touch narrower than `TOUCH_MAX_MM` (0.15 mm) between two letter-height
   pieces parts them** -- any letter-height region within reach of a line,
   whatever its aspect, not only a too-wide one. The region must part at an
   opening of r 0.075 mm (and never more than a quarter of its stroke), into
   as many pieces as the wide pass's own stroke-rule cut makes, and every
   piece must be at least 0.8 of the line's cap height (two letters, never a
   serif or a spike cut off one). Kept only when every piece is tagged, as
   the wide pass. Sized on all six jobs: the touches part at r 0.02-0.04 mm;
   no single letter parts below r 0.125 mm (ProSeal's 3 mm tagline, a 0.25 mm
   neck); 0.15 mm sits between.
2. **The height band**: a glyph TALLER than a line member it links to on every
   other `_linked` term (one ink, stroke within 0.5, reach), that spans the
   member's cap band (top and bottom within 0.1 of its height) and is at least
   `HEIGHT_BAND_MIN` (0.6) of the way to it, joins that line -- it never makes
   or bridges one. The overshooting letters measured 0.65 (hat G, already
   chained in) to 0.80; nothing that is not a letter spans a line's band on the
   six jobs at any ratio (`band.py` census: every other left-out candidate is
   offset or links to nothing).

### Rows that contradict them

- **Fremont O+T** fuse only when sewn (above). Neither rule sees it.
- **MFab hat LL** of LLC is ONE region joined by a full stroke, not a neck (no
  opening up to r 0.75 mm parts it), aspect 1.15: admitted as one letter and
  left so. The left chest's LL trace apart.
- **Drone THERMAL**: the orange gradient cuts each letter into a top and a
  bottom region (E: 2.20 mm over 3.68 mm, aspect 2.17 and 1.38) -- the opposite
  failure, one letter in two regions. Neither rule; THERMAL stays house-group
  only.
- **Drone `S0e857405`**, a glyph-height shape left of AND DRONE (ratio 0.98,
  spanning the line): the tagger DOES tag it, with its line; the small-text
  restore step strips it afterwards (`small_text_stray`). Downstream of the
  tagger, not a height question; not touched.
- **MFab LC AND, downstream**: ON tags the N correctly, but that cluster sews
  as BEAN letters under the true-size switch (`bean_letter_max_stroke_mm`
  0.5): the ink read (`beanletters`) gives the N 0.44 mm on a letter traced
  1.23 mm wide -- the art draws these letters as white faces in a thin black
  outline -- so the A is a hollow bean outline today (222 run points, no
  satin; ink 0.42 mm) and ON makes the N one too (`mfab_lc_AND_off_on_pro.png`).
  The D escapes: its read, 0.35 mm, disagrees with its shape (mean width 1.11
  over 3 x 0.35, `INK_SHAPE_MAX_RATIO`). The
  pro sews A, N and D as black satin. The rule is right; the bean tier on
  outlined lettering is the next defect, and it already costs the A.

## ON against OFF

Tagger alone, on each job's captured input (OFF is byte-identical to HEAD's
tagger on all six: every polygon's WKT and every meta key):

| job | ON changes |
|---|---|
| MFab hat | IN of WELDING -> I (6.80 mm) and N (8.47 mm), both tagged |
| MFab LC | AND's N, WELDING's N and G gain `text_candidate` |
| Fremont hat, patch, Drone, ProSeal | nothing |

Whole design, md5 of `[x, y, kind, jump, trim]` per stitch. "Branch OFF" is
the full pipeline with the flag off: on the branch for five jobs, and for MFab
hat on main at #1080's squash (`a6be6b78`) against its parent (`05270805`,
also `3673370d`), measured after the PR merged (2026-10-25).

| job | width mm | main (82b0bf28) | branch OFF | ON | stitches / trims main -> ON |
|---|---|---|---|---|---|
| Fremont hat | 92.6 | `6ff9803b` | `6ff9803b` | `6ff9803b` | 18,573 / 58, same |
| Fremont patch | 92.5 | `d2bcba27` | `d2bcba27` | `d2bcba27` | 20,733 / 49, same |
| MFab hat | 104.9 | `3673370d` | `3673370d` | `39d95f28` | 11,125 / 62 -> 11,138 / 62 |
| MFab LC | 96.7 | `f444ae5e` | `f444ae5e` | `288c3c5b` | 11,691 / 73 -> 11,822 / 73 |
| Drone | 62.6 | `6239342f` | `6239342f` | `6239342f` | 14,077 / 116, same |
| ProSeal hat | 85.9 | `7d89f371` | `7d89f371` | `7d89f371` | 7,760 / 56, same |

**Trap, hit twice measuring this table:** on a loaded laptop the rembg cutout
can run past `photo_prep_background_removal_timeout_s` (60 s). The pipeline
then drops the WHOLE photo prep (Kent's 2026-08-24 ruling) and sews the
classical route. MFab hat came out `7296b420` (11,855 / 67, 59 regions into the
tagger instead of 60) twice that way, and it looked like an OFF regression. It
was not: the plan's warnings read `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE`
instead of `PHOTO_BACKGROUND_REMOVED`. Re-run with the timeout raised
(`--set photo_prep_background_removal_timeout_s=600`), the same tree gives
`3673370d`. Read that warning before calling any md5 mismatch on a photo-path
job a regression.

The flat goldens (`logo_alpha`, `logo_whitebg`, `ribbon_curve`) are pinned
OFF and ON in the test: no touching or overshooting letter there.

Lettering board, line AND WELDING LLC (ours OFF -> ON, the pro):

| job | columns | trims inside letters | stitches |
|---|---|---|---|
| MFab hat | 38 -> 40 (30) | 8 -> 5 (0) | 1,365 -> 1,354 (1,366) |
| MFab LC | 44 -> 39 (30) | 16 -> 12 (0) | 1,948 -> 2,064 (1,272) |

Every other board cell is unchanged. Word legibility cc: MFab's words are not
located by `word_legibility` in either file (white keyline on the art's white
ground, the I3 tool's known limit: `n/loc`, never 0); Fremont and ProSeal
read +1.00 / +1.00 both ways (their files are md5-identical ON).

Per word (`letter_pieces` pieces / trims inside a letter / crosses; ours OFF ->
ON, the pro):

| job | word | pieces | trims | crosses |
|---|---|---|---|---|
| MFab hat | AND | 14 -> 14 (10) | 0 -> 0 (0) | 389 -> 389 (439) |
| MFab hat | WELDING | 24 -> 25 (24) | 4 -> 3 (0) | 716 -> 709 (703) |
| MFab LC | AND | 8 -> 4 (11) | 1 -> 1 (0) | 241 -> 118 (401) |
| MFab LC | WELDING | 24 -> 24 (24) | 3 -> 3 (0) | 652 -> 679 (614) |
| Fremont hat | HOTEL / FREMONT | 26 / 37, same (25 / 35) | 2 / 1, same (0 / 0) | 528 / 805, same (604 / 922) |

Per letter (pieces, ours OFF -> ON, the pro): MFab hat I of WELDING 1 -> 2
(1), its N 4 -> 4 (5) with its trim 1 -> 0; MFab LC AND's N 5 -> 1 (5), the
bean outline above; WELDING's G 4 -> 7 (3), N 3 -> 3 (5).

## Reading the crops

- `mfab_hat_ING_off_on_pro.png`: OFF the I of WELDING is one glyph with the N,
  its foot tangled into the N's stem; ON the I is a clean column of its own,
  as the pro's.
- `mfab_lc_NG_off_on_pro.png`: ON the G's bars cross square to the bar, as
  the pro's do, but the G is cut into more pieces (4 -> 7, the pro 3) and its
  travel grows from 4 to 82 stitch points: the Column lane's construction, not
  the tagger's.
- `mfab_lc_AND_off_on_pro.png`: ON the N goes hollow, like the A beside it.
- `fremont_hat_OTE_off_on_pro.png`, `fremont_hat_NT_off_on_pro.png`: OFF = ON;
  the O-T touch is in the stitches, not the trace.
- `mfab_*_tagger_regions_off.png`: the regions the tagger sees, OFF (blue
  `text_candidate`, green house group only, red neither, orange split).

## Verdict

Segmentation and tagging, not fabric: layout, ON-eligible from renders under
Kent's 2026-10-22 ruling. The tagging is right on every row it changes. But do
not flip it before the bean-letter ink read stops taking MFab LC's keyline as
ink: ON trades the hat's clean I (and three fewer trims inside letters) for
the left chest's AND N going hollow.
