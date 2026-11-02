# Do the pro-pair figures agree with Kent's eye? Pooled over every labelled pair with a pro file - 2026-11-01

ROADMAP phase 1 exits on *"the metric's ranking agrees with Kent's visual
ranking, and nothing he judges better ever scores worse."*
`docs/yardstick-vs-kents-eye-2026-10-11.md` pooled his 144 labelled
before | after pairs and found that no fidelity instrument (`lost_frac`,
`lost_elements`, `ragged_mm`, `uncovered_ink_frac`, ARTFID, the preflight
grade) clears chance against his picks; only the trim count does. The
instruments that actually decide the flips he accepts are different ones:
one reader on OUR machine file and on the PRO'S for the same job (cuts,
needle-up moves and mm, the stitch-type kappa, the word-legibility cc, the
Column-lane column count: `digitizer/tools/pro_baseline.py`,
`lettering_board.py`, `word_legibility.py`), and those had never been tested
against his picks. This does, with the 10-11 method, on every labelled pair
whose design has a professional's file. Gate 4 holds throughout: **no raw
agreement figure appears below or is computed by the tool** - only Cohen's
kappa, its bootstrap interval, and the n it rests on.

## The answer

**Closer to his eye than the fidelity scorecard was, and still not the
exit.** Of the 144 judged pairs, 100 are on a design that has a
professional's file; both arms of every one were drawn again on the
sitting's tree at the pro's width and garment and read beside the pro's DST,
so the reachable pool is **100 pairs, 41 where Kent chose a side** (29 after,
12 before), and no instrument is silent for want of a design. Three
instruments land above chance against his picks with ties counted:
needle-up **hops** +0.24 [+0.10, +0.39] over pairs and [+0.11, +0.34] over
fixtures (n = 100), **cuts** +0.23 [+0.08, +0.38] / [+0.08, +0.36], and
needle-up **mm** +0.17 [+0.03, +0.31] / [+0.01, +0.33]. Only hops also clears
on the pairs where he chose a side, and only just: +0.33 [+0.02, +0.64] /
[+0.07, +0.72] on 32 pairs, an interval that crosses zero again once the
three tires pairs are left out (+0.23 [-0.10, +0.56]). The stitch-type kappa
(+0.02 [-0.10, +0.15], n = 100), the word-legibility cc (+0.15 [-0.05,
+0.37], n = 49) and the Column-lane column count (+0.09 [-0.10, +0.27],
n = 64) show no evidence either way. **The exit's second clause fails for
every instrument**: hops scores his pick farther from the pro on 10 of the 32
decided pairs, cuts on 11 of 32, needle-up mm on 13 of 36, the stitch-type
kappa on 21 of 36, and four pairs he chose do it on five instruments at once
(section 4). And the pro reference adds almost nothing to the three that
clear: ours has more cuts than the pro on 187 of the 200 designs, more hops
on 188 and more needle-up mm on 198, so "closer to the pro" and "fewer" are
the same pick on 97 or more of the 100 pairs. Those three are the 10-11
doc's trim family (`trims` +0.28 [+0.12, +0.43] then) read a second time on
re-drawn designs, not a new signal; the two instruments whose reading
genuinely depends on the pro's own figure, word cc and columns, are among
those with no evidence. No phase marker moves on this. What it would and
would not support is in section 6; the call is Kent's.

## 1. Inventory - every labelled pair with a pro file

Of the 144 judged pairs, **100 are on a design that has a professional's
file**: becker, bridge, drone, fremont, golden_tee and tires. Enthusiast has
no pro file; screenshot and gaulke are off the comparison by Kent's own word
(the 10-11 scope). Kent chose a side on **41** of the 100 (29 after, 12
before), saw no difference on 39 and called both bad on 20. MFab, ProSeal and
To a T have pro files but were never on a labelled page, so they contribute
nothing here.

`before` / `after` are the page's LEFT / RIGHT, as in the 10-11 pool: shipped /
flag for every arm except the two old-engine arms (`ref_0827`, `ref_0930am`),
where `before` is the OLD engine.

| sitting | tree the pairs were drawn on | pairs | after | before | same | both_bad | fixtures | arms |
|---|---|---|---|---|---|---|---|---|
| `flags-0918-0928` | `a5d78449` (the 09-18 render; Kent judged its 09-20 cloud twin) | 49 | 12 | 5 | 20 | 12 | becker, bridge, drone, fremont, golden_tee, tires | `area_weighted`, `design_angle`, `directional_comp`, `lettering_column`, `per_stroke`, `phantom_dissolve`, `polygon_axis`, `rail_comp`, `rails_follow_edge`, `ref_0827` (= `25da2fe`), `wide_columns` |
| `envelope-0930` | `e54b5963` | 5 | 2 | 0 | 2 | 1 | becker, bridge, drone, golden_tee, tires | `rail_envelope` |
| `evening-0930` | `0803a7b2` | 8 | 1 | 2 | 4 | 1 | becker, bridge, drone, golden_tee, tires | `phantom_dissolve`, `ref_0930am` (= `1e5f8fe2`) |
| `texture-0930` | `7cc76370` | 7 | 0 | 1 | 6 | 0 | becker, bridge, drone, golden_tee, tires | `rails_symmetric`, `split_7mm` |
| `off-flags-1003` | `82c9838d` + `satin_crown_cover` ON (its README's base) | 15 | 2 | 3 | 7 | 3 | becker, bridge, drone, fremont, golden_tee, tires | `bean_letters`, `cap_recentre`, `split_off` |
| `density-1007` | `2a87ba89` (kent-notes: #660's `1cbef252` cherry-picked on main) | 4 | 2 | 1 | 0 | 1 | becker, bridge, drone, fremont | `lettering_columns` |
| `letterform-1007` | `95c7eb07` | 2 | 1 | 0 | 0 | 1 | becker, bridge | `letterform_priors` |
| `columns-flip-1008` | `f08f49e4` (its README: `d17c5f7e` + #814) | 5 | 4 | 0 | 0 | 1 | becker, bridge, drone, fremont, golden_tee | `columns_words` |
| `full-density-1008` | `62676060` (scope-history: main + #667) | 5 | 5 | 0 | 0 | 0 | becker, bridge, drone, fremont, golden_tee | `lettering_columns` |

**Every design was drawn again.** No labelled sitting's render directory
survives on Kent's laptop (searched 2026-11-01 under the live checkout, its
lanes, the duplicate clone and `%TEMP%`: the 09-18 `eye_pairs_out`, the
`columns-sitting` and `letterform-priors` lanes are gone; only pytest's
fixtures answer to the name). The committed price tables hold stitches and
trims as the Design records them, which is not one reader on two DSTs. So
`tools/eye_pairs/pro_pooled_build.py render` checked each sitting's tree out
detached (outside the repository, the primary checkout's venv and rembg venv
linked in) and digitized both arms of every pair there - the sitting's own
`base_cfg` (the Studio's six colours plus the arm's one change) - **at the
pro's width and garment**, so ours and the pro's file are the same job:

| fixture | pro job (`pro_baseline.JOBS`) | garment, width | the sitting drew it at | pro: cuts | pro: needle-up hops | pro: needle-up mm | pro: stitches |
|---|---|---|---|---|---|---|---|
| becker | `becker_hat_large` | hat_front, 101.9 mm | left_chest, 100 mm | 10 | 13 | 416 | 12,356 |
| bridge | `bridge_lc` | left_chest, 76.6 mm | left_chest, 80 mm | 20 | 23 | 214 | 8,535 |
| drone | `precision_drone` | hat_front, 62.6 mm | left_chest, 80 mm | 59 | 80 | 901 | 14,552 |
| fremont | `hotel_fremont_patch` | patch, 92.5 mm | patch, 92.5 mm | 21 | 28 | 533 | 15,458 |
| golden_tee | `goldentee_hat` | hat_front, 74.9 mm | left_chest, 80 mm | 10 | 15 | 289 | 5,973 |
| tires | `tires_hat_3d` | hat_front, 114.3 mm | left_chest, 80 mm | 10 | 10 | 273 | 5,555 |

Becker's hat was taken over its left-chest pro file because it is the job
`word_legibility` pins words on; tires' pro file is 3D puff, a construction
ours never sews, and the sensitivity table leaves it out. The pro's figures
are read by the same code as ours: `pro_pair.pro_counts` (TRIM records,
pystitch, on the DST never the PES), `pro_baseline.needle_up`.

**What this means for the labels.** Kent judged a picture at the sitting's
size and garment; the figures below are from the same engine and the same
flag at the pro's. Where a flag's effect depends on size or fabric preset
the re-drawn pair can differ from the one he saw. Two sittings carry a
further caveat the 10-11 doc already had: the 77-pair flags sitting was
judged on a 09-20 cloud render matching the laptop's to platform rounding,
and the Column lane at `2a87ba89` broke ties from OS entropy (seeded one
commit later), so its `density-1007` arm is a sample of that engine. Each design's
`measure.json` (engine tag, render time, every figure) is in the run
directory on Kent's laptop; the inputs carry the figures and the engine tag
per side.

## 2. The method

Tool: `digitizer/tools/eye_pairs/pro_pooled.py`
(`python -m tools.eye_pairs.pro_pooled report --markdown`); inputs
`docs/eye-pairs-2026-11-01/pro-pair-inputs.json`, built once by
`pro_pooled_build.py` (`render`, `measure`, `build`). Tests:
`tests/test_eye_pairs_pro_pooled.py` (a synthetic sitting: the distance
transform, the textbook kappa on a hand-made 10-row table, the builder's
pairing of designs, the refusals).

- **Each instrument is read as a distance to the pro.** A count or a length
  (`cuts`, `hops`, `needle_up_mm`, `columns`): |ours - pro|. The stitch-type
  kappa: 1 - kappa (the pro against his own file is 1; the scorecard's
  clamp at the chance floor is removed, so an arm below chance still ranks).
  The word cc: |cc_ours - cc_pro| over the words both files read. Lower is
  closer; the instrument says *after* when after's distance is the smaller,
  and tie when the two are equal.
- **Readers**, the same code on ours.dst and on the pro's DST:
  `pro_pair.pro_counts` (cuts), `pro_baseline.needle_up` (hops, mm),
  `pro_parity.scorecard.score_design` over `prep_all.decode` of both files
  (stitch-type kappa on the shared solid area), `lettering_board.read_pair`
  (columns per pinned line via `column_harness.census`, word cc via
  `word_legibility` with tesseract 5.4) on the four jobs that have lines
  pinned (becker, fremont, drone, tires; bridge and golden_tee have none).
  The pro's board figures are read in a frame registered to OUR file, so
  each side carries the pro reading taken beside it.
- **Kent's pick**, the two statistics, chance, the intervals and the
  reading floor are `pooled.py`'s, unchanged: sides-only 2x2 kappa on the
  pairs where he chose a side and the instrument did; ties-in 3x3
  linear-weighted kappa over every judged pair; percentile bootstrap, 10,000
  resamples, over pairs and over fixtures; *above chance* needs both
  intervals clear of zero; nothing is read under 10 pairs.
- **Sensitivities**: `both_bad` dropped instead of folded into the tie (as
  10-11); tires left out (the 3D puff pro file); and **the signed cost
  reading** - each figure as a plain cost with no pro in it (fewer cuts /
  hops / mm / columns better, higher kappa / cc better), which is how the
  10-11 doc read trims - so the table shows what the pro reference adds.

## 3. Results - each instrument against Kent's pick

Every pair in the pool has both designs, so *n scored* is the pool itself
(100) wherever the instrument reads the job: the word cc and the column
count read only the four jobs with pinned lines (becker, drone, fremont,
tires), and the column count is silent on a line the lane did not reach.
*Instrument silent there* counts the decided pairs on which the two arms tie
exactly (a flag that touched nothing the instrument sees); the sides-only
kappa drops them, the 3-way kappa keeps them as the instrument's tie.

| instrument (distance to the pro) | n scored | n Kent chose a side | instrument silent there | n decided | kappa, sides only (2x2) | 95% CI pairs | 95% CI fixtures | kappa, ties in (3-way, weighted) | 95% CI pairs | 95% CI fixtures | pairs scoring Kent's pick farther from the pro | reading |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `cuts` | 100 | 41 | 9 | 32 | +0.24 | [-0.10, +0.57] | [-0.03, +0.65] | +0.23 | [+0.08, +0.38] | [+0.08, +0.36] | 11 | sides: no evidence either way; with ties: above chance |
| `hops` | 100 | 41 | 9 | 32 | +0.33 | [+0.02, +0.64] | [+0.07, +0.72] | +0.24 | [+0.10, +0.39] | [+0.11, +0.34] | 10 | sides: above chance; with ties: above chance |
| `needle_up_mm` | 100 | 41 | 5 | 36 | +0.26 | [-0.04, +0.55] | [-0.06, +0.65] | +0.17 | [+0.03, +0.31] | [+0.01, +0.33] | 13 | sides: no evidence either way; with ties: above chance |
| `sttype_kappa` | 100 | 41 | 5 | 36 | +0.01 | [-0.24, +0.24] | [-0.27, +0.33] | +0.02 | [-0.10, +0.15] | [-0.13, +0.21] | 21 | sides: no evidence either way; with ties: no evidence either way |
| `word_cc` | 49 | 22 | 6 | 16 | -0.03 | [-0.43, +0.38] | [-0.43, +0.67] | +0.15 | [-0.05, +0.37] | [-0.11, +0.61] | 9 | sides: no evidence either way; with ties: no evidence either way |
| `columns` | 64 | 29 | 5 | 24 | -0.06 | [-0.41, +0.33] | [-0.30, +0.17] | +0.09 | [-0.10, +0.27] | [-0.06, +0.24] | 11 | sides: no evidence either way; with ties: no evidence either way |

Reading it by the two clauses of the exit:

- **Above chance on both intervals, ties counted**: `hops`, `cuts`,
  `needle_up_mm` - the trim family, in that order of strength. The
  needle-up mm interval over fixtures clears by a hundredth (+0.01), so read
  it as the weakest of the three.
- **Above chance on both intervals, sides only**: `hops` alone
  (+0.33, [+0.02, +0.64] over pairs), and 3.1 shows the pairs interval
  depends on three tires pairs. `cuts` (+0.24, [-0.10, +0.57]) and
  `needle_up_mm` (+0.26, [-0.04, +0.55]) point the same way and do not clear.
- **No evidence either way**: `sttype_kappa` (point estimate at zero, 36
  decided pairs), `word_cc` (16 decided pairs; its sides-only estimate is
  -0.03) and `columns` (24 decided pairs; sides-only -0.06). These are the
  three readings shaped like fidelity - what the stitches are, whether the
  words read, how the letters are built - and include the two that use the
  pro's own figure rather than a count of ours.
- **The second clause** ("nothing he judges better ever scores worse") fails
  on every row: the twelfth column. Section 4 lists the pairs with margins.

### 3.1 Sensitivities

| variant | instrument | n scored | n decided | kappa, sides only | kappa, ties in (3-way) | pairs scoring Kent's pick worse |
|---|---|---|---|---|---|---|
| `both_bad` pairs dropped, not folded into the tie | `cuts` | 80 | 32 | +0.24 [-0.09, +0.57] | +0.26 [+0.09, +0.44] | - |
| `both_bad` pairs dropped, not folded into the tie | `hops` | 80 | 32 | +0.33 [+0.02, +0.64] | +0.30 [+0.12, +0.47] | - |
| `both_bad` pairs dropped, not folded into the tie | `needle_up_mm` | 80 | 36 | +0.26 [-0.04, +0.55] | +0.21 [+0.04, +0.38] | - |
| `both_bad` pairs dropped, not folded into the tie | `sttype_kappa` | 80 | 36 | +0.01 [-0.23, +0.23] | +0.03 [-0.12, +0.18] | - |
| `both_bad` pairs dropped, not folded into the tie | `word_cc` | 43 | 16 | -0.03 [-0.43, +0.38] | +0.17 [-0.05, +0.40] | - |
| `both_bad` pairs dropped, not folded into the tie | `columns` | 57 | 24 | -0.06 [-0.41, +0.33] | +0.07 [-0.13, +0.28] | - |
| tires (3D puff pro file) left out | `cuts` | 85 | 29 | +0.12 [-0.21, +0.45] | +0.21 [+0.05, +0.38] | - |
| tires (3D puff pro file) left out | `hops` | 85 | 29 | +0.23 [-0.10, +0.56] | +0.24 [+0.09, +0.39] | - |
| tires (3D puff pro file) left out | `needle_up_mm` | 85 | 32 | +0.16 [-0.15, +0.47] | +0.14 [-0.01, +0.28] | - |
| tires (3D puff pro file) left out | `sttype_kappa` | 85 | 34 | -0.01 [-0.27, +0.23] | +0.02 [-0.11, +0.15] | - |
| tires (3D puff pro file) left out | `word_cc` | 49 | 16 | -0.03 [-0.43, +0.38] | +0.15 [-0.05, +0.37] | - |
| tires (3D puff pro file) left out | `columns` | 49 | 21 | +0.02 [-0.35, +0.42] | +0.15 [-0.06, +0.37] | - |
| plain cost, no pro reference (the 10-11 reading) | `cuts` | 100 | 32 | +0.20 [-0.12, +0.52] | +0.20 [+0.05, +0.35] | 12 |
| plain cost, no pro reference (the 10-11 reading) | `hops` | 100 | 32 | +0.29 [-0.02, +0.59] | +0.22 [+0.07, +0.36] | 11 |
| plain cost, no pro reference (the 10-11 reading) | `needle_up_mm` | 100 | 36 | +0.22 [-0.06, +0.50] | +0.15 [+0.01, +0.29] | 14 |
| plain cost, no pro reference (the 10-11 reading) | `sttype_kappa` | 100 | 36 | +0.01 [-0.24, +0.24] | +0.02 [-0.10, +0.15] | 21 |
| plain cost, no pro reference (the 10-11 reading) | `word_cc` | 49 | 16 | -0.03 [-0.43, +0.38] | +0.15 [-0.05, +0.37] | 9 |
| plain cost, no pro reference (the 10-11 reading) | `columns` | 64 | 24 | +0.09 [-0.23, +0.40] | +0.11 [-0.06, +0.28] | 12 |

- **Dropping `both_bad`** (the 10-11 variant) moves the ties-in kappas by
  at most 0.06 and no sides-only figure at all: the "both bad" pairs sit in
  the tie column and nowhere else.
- **Leaving tires out** costs the trim family its sides-only clearance
  (hops +0.33 -> +0.23, interval [-0.10, +0.56]) and leaves the ties-in
  readings of hops and cuts clear. Tires is the one job where ours sits at
  the pro's own trim count (9-10 against his 10), so its pairs are the ones
  on which "closer to the pro" can say *before*; the 3D puff file makes it
  the job to trust least. Read the sides-only clearance of hops as resting
  on three pairs.
- **The plain-cost reading** (no pro; fewer cuts, hops, mm and columns
  better, higher kappa and cc better) gives the same picks as the distance
  reading on 97 of 100 pairs for cuts, 98 for hops, 99 for needle-up mm, and
  on every pair for the stitch-type kappa and the word cc (ours reads below
  the pro's cc on 88 of 100 design readings and above on 2). Only the column
  count changes its pick when the pro is in the reading (28 pairs: ours has
  fewer columns than the pro on 89 of 128 design readings and more on 39),
  and it clears chance under neither. **So the pro reference did not create
  the signal; the 10-11 trim result reproduced on designs re-drawn at the
  pro's size.** The ten pairs on which `hops` scores his pick farther from
  the pro are the same ten the cost reading scores as costing more hops; the
  cost reading adds an eleventh, `ref_0827:tires`, the one decided pair
  where the engine he chose lies *under* the pro's count, which the distance
  reading rightly scores his way. The same single pair separates the two
  readings for `cuts` and `needle_up_mm`.

## 4. Pairs on which the instrument scores Kent's pick farther from the pro

The exit clause read directly. 35 of the 41 decided pairs are
scored farther from the pro by at least one instrument; the four at the top
by five of six. Two of those four are lettering-construction flips he
accepted (the Column lane on drone, `letterform_priors` on becker), one is
`directional_comp` on drone, and one is the old-engine arm on becker. That
arm, `ref_0827`, fills three more of the next six rows: he chose the 09-18
engine over the 08-27 one on becker, bridge, drone and fremont although the
old engine lay 12-71 hops nearer the pro's count (and 3-57 cuts on three of
them). On those pairs he is trading trims for construction, and the trim
family can only see the trims. Take the five `ref_0827` pairs out and
`hops` still scores his pick farther from the pro on 6 of the 27 decided
pairs it separates, `cuts` on 8 of 27, `needle_up_mm` on 10 of 31.

| pair | Kent | instruments |
|---|---|---|
| `flags-0918-0928:directional_comp:drone` | after | 5: cuts, hops, needle_up_mm, word_cc, columns |
| `flags-0918-0928:ref_0827:becker` | after | 5: cuts, hops, needle_up_mm, sttype_kappa, word_cc |
| `full-density-1008:lettering_columns:drone` | after | 5: cuts, hops, needle_up_mm, sttype_kappa, columns |
| `letterform-1007:letterform_priors:becker` | after | 5: cuts, hops, sttype_kappa, word_cc, columns |
| `density-1007:lettering_columns:drone` | after | 4: cuts, hops, needle_up_mm, sttype_kappa |
| `flags-0918-0928:lettering_column:fremont` | before | 4: cuts, hops, needle_up_mm, columns |
| `flags-0918-0928:ref_0827:bridge` | after | 3: cuts, hops, needle_up_mm |
| `flags-0918-0928:ref_0827:drone` | after | 3: cuts, hops, needle_up_mm |
| `flags-0918-0928:ref_0827:fremont` | after | 3: hops, sttype_kappa, columns |
| `flags-0918-0928:wide_columns:becker` | before | 3: sttype_kappa, word_cc, columns |
| `columns-flip-1008:columns_words:becker` | after | 2: sttype_kappa, word_cc |
| `columns-flip-1008:columns_words:fremont` | after | 2: needle_up_mm, sttype_kappa |
| `density-1007:lettering_columns:fremont` | before | 2: hops, columns |
| `envelope-0930:rail_envelope:becker` | after | 2: sttype_kappa, columns |
| `evening-0930:phantom_dissolve:golden_tee` | before | 2: needle_up_mm, sttype_kappa |
| `flags-0918-0928:rail_comp:becker` | after | 2: sttype_kappa, columns |
| `flags-0918-0928:rail_comp:fremont` | after | 2: needle_up_mm, word_cc |
| `full-density-1008:lettering_columns:becker` | after | 2: sttype_kappa, word_cc |
| `full-density-1008:lettering_columns:fremont` | after | 2: cuts, needle_up_mm |
| `off-flags-1003:bean_letters:fremont` | before | 2: cuts, needle_up_mm |
| `columns-flip-1008:columns_words:bridge` | after | 1: needle_up_mm |
| `density-1007:lettering_columns:becker` | after | 1: word_cc |
| `envelope-0930:rail_envelope:golden_tee` | after | 1: sttype_kappa |
| `evening-0930:phantom_dissolve:bridge` | after | 1: sttype_kappa |
| `flags-0918-0928:design_angle:tires` | before | 1: columns |
| `flags-0918-0928:directional_comp:fremont` | before | 1: cuts |
| `flags-0918-0928:directional_comp:tires` | before | 1: columns |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 1: sttype_kappa |
| `flags-0918-0928:rail_comp:bridge` | after | 1: sttype_kappa |
| `flags-0918-0928:ref_0827:tires` | after | 1: sttype_kappa |
| `full-density-1008:lettering_columns:bridge` | after | 1: sttype_kappa |
| `full-density-1008:lettering_columns:golden_tee` | after | 1: sttype_kappa |
| `off-flags-1003:bean_letters:drone` | before | 1: word_cc |
| `off-flags-1003:cap_recentre:becker` | after | 1: sttype_kappa |
| `texture-0930:rails_symmetric:golden_tee` | before | 1: sttype_kappa |

Per instrument, with the margin (Kent's pick's distance to the pro minus the
other side's; the unit is the instrument's own):

### `cuts` (11 pairs) - cuts: TRIM records, pystitch on both DSTs (pro_pair.pro_counts)

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:drone` | after | 5 | 62 | 57 |
| `flags-0918-0928:ref_0827:becker` | after | 10 | 30 | 20 |
| `flags-0918-0928:directional_comp:drone` | after | 62 | 77 | 15 |
| `full-density-1008:lettering_columns:drone` | after | 51 | 61 | 10 |
| `flags-0918-0928:directional_comp:fremont` | before | 51 | 45 | 6 |
| `density-1007:lettering_columns:drone` | after | 51 | 56 | 5 |
| `letterform-1007:letterform_priors:becker` | after | 49 | 54 | 5 |
| `off-flags-1003:bean_letters:fremont` | before | 33 | 29 | 4 |
| `full-density-1008:lettering_columns:fremont` | after | 33 | 37 | 4 |
| `flags-0918-0928:ref_0827:bridge` | after | 85 | 88 | 3 |
| `flags-0918-0928:lettering_column:fremont` | before | 51 | 50 | 1 |

### `hops` (10 pairs) - needle-up moves: gaps the needle flies with the thread up (pro_baseline.needle_up)

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:drone` | after | 20 | 91 | 71 |
| `flags-0918-0928:directional_comp:drone` | after | 91 | 125 | 34 |
| `flags-0918-0928:ref_0827:becker` | after | 8 | 29 | 21 |
| `flags-0918-0928:ref_0827:fremont` | after | 177 | 192 | 15 |
| `flags-0918-0928:ref_0827:bridge` | after | 118 | 130 | 12 |
| `flags-0918-0928:lettering_column:fremont` | before | 192 | 185 | 7 |
| `full-density-1008:lettering_columns:drone` | after | 93 | 99 | 6 |
| `density-1007:lettering_columns:drone` | after | 93 | 98 | 5 |
| `letterform-1007:letterform_priors:becker` | after | 47 | 52 | 5 |
| `density-1007:lettering_columns:fremont` | before | 174 | 171 | 3 |

### `needle_up_mm` (13 pairs) - needle-up travel, mm, summed over those gaps

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:drone` | after | 112.9 | 988.9 | 876 |
| `flags-0918-0928:ref_0827:becker` | after | 74.7 | 354.6 | 279.9 |
| `flags-0918-0928:directional_comp:drone` | after | 988.9 | 1171.6 | 182.7 |
| `flags-0918-0928:ref_0827:bridge` | after | 1025.2 | 1181.6 | 156.4 |
| `flags-0918-0928:lettering_column:fremont` | before | 392.5 | 344.1 | 48.4 |
| `off-flags-1003:bean_letters:fremont` | before | 353.6 | 310.4 | 43.2 |
| `full-density-1008:lettering_columns:fremont` | after | 353.6 | 396.2 | 42.6 |
| `full-density-1008:lettering_columns:drone` | after | 939.7 | 969.8 | 30.1 |
| `evening-0930:phantom_dissolve:golden_tee` | before | 244.2 | 221.1 | 23.1 |
| `columns-flip-1008:columns_words:bridge` | after | 998.1 | 1016.5 | 18.4 |
| `density-1007:lettering_columns:drone` | after | 939.7 | 953.1 | 13.4 |
| `flags-0918-0928:rail_comp:fremont` | after | 392.5 | 403.1 | 10.6 |
| `columns-flip-1008:columns_words:fremont` | after | 443.9 | 450.5 | 6.6 |

### `sttype_kappa` (21 pairs) - stitch-type kappa over the shared solid area, both DSTs decoded alike (pro_parity.scorecard)

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:fremont` | after | 0.552448 | 0.811659 | 0.259211 |
| `columns-flip-1008:columns_words:becker` | after | 1.11135 | 1.23156 | 0.120212 |
| `evening-0930:phantom_dissolve:bridge` | after | 0.682746 | 0.756654 | 0.073908 |
| `envelope-0930:rail_envelope:becker` | after | 1.01911 | 1.09034 | 0.071228 |
| `full-density-1008:lettering_columns:becker` | after | 1.16326 | 1.21561 | 0.052341 |
| `density-1007:lettering_columns:drone` | after | 0.719361 | 0.760417 | 0.041056 |
| `letterform-1007:letterform_priors:becker` | after | 1.11691 | 1.15714 | 0.040233 |
| `flags-0918-0928:wide_columns:becker` | before | 1.03422 | 1.00157 | 0.032648 |
| `evening-0930:phantom_dissolve:golden_tee` | before | 1.02941 | 1 | 0.029412 |
| `envelope-0930:rail_envelope:golden_tee` | after | 1 | 1.02857 | 0.028571 |
| `flags-0918-0928:rail_comp:bridge` | after | 0.661818 | 0.687161 | 0.025343 |
| `flags-0918-0928:ref_0827:becker` | after | 1.01812 | 1.03422 | 0.016099 |
| `texture-0930:rails_symmetric:golden_tee` | before | 1.02941 | 1.01562 | 0.013787 |
| `full-density-1008:lettering_columns:golden_tee` | after | 0.940299 | 0.953846 | 0.013547 |
| `full-density-1008:lettering_columns:bridge` | after | 0.776965 | 0.789762 | 0.012797 |
| `flags-0918-0928:rail_comp:becker` | after | 1.03422 | 1.04688 | 0.01266 |
| `full-density-1008:lettering_columns:drone` | after | 0.719858 | 0.730496 | 0.010638 |
| `columns-flip-1008:columns_words:fremont` | after | 0.759939 | 0.765957 | 0.006018 |
| `flags-0918-0928:ref_0827:tires` | after | 0.995608 | 1 | 0.004392 |
| `off-flags-1003:cap_recentre:becker` | after | 1.11297 | 1.11691 | 0.003939 |
| `flags-0918-0928:phantom_dissolve:bridge` | after | 0.661818 | 0.662162 | 0.000344 |

### `word_cc` (9 pairs) - word-legibility cc, letter-weighted over the pinned words both files read (word_legibility)

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:becker` | after | 0 | 0.5 | 0.5 |
| `flags-0918-0928:wide_columns:becker` | before | 0.5 | 0 | 0.5 |
| `columns-flip-1008:columns_words:becker` | after | 0.397 | 0.897 | 0.5 |
| `full-density-1008:lettering_columns:becker` | after | 0.397 | 0.88 | 0.483 |
| `density-1007:lettering_columns:becker` | after | 0.397 | 0.5505 | 0.1535 |
| `off-flags-1003:bean_letters:drone` | before | 0.5468 | 0.4254 | 0.1214 |
| `letterform-1007:letterform_priors:becker` | after | 0.397 | 0.434 | 0.037 |
| `flags-0918-0928:rail_comp:fremont` | after | 0.0972 | 0.1212 | 0.024 |
| `flags-0918-0928:directional_comp:drone` | after | 0.4617 | 0.4686 | 0.0069 |

### `columns` (11 pairs) - satin columns over the pinned lines of lettering (column_harness.census via lettering_board)

| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |
|---|---|---|---|---|
| `flags-0918-0928:ref_0827:fremont` | after | 44 | 60 | 16 |
| `density-1007:lettering_columns:fremont` | before | 49 | 39 | 10 |
| `flags-0918-0928:lettering_column:fremont` | before | 60 | 51 | 9 |
| `flags-0918-0928:wide_columns:becker` | before | 20 | 11 | 9 |
| `flags-0918-0928:design_angle:tires` | before | 8 | 4 | 4 |
| `flags-0918-0928:directional_comp:tires` | before | 8 | 4 | 4 |
| `envelope-0930:rail_envelope:becker` | after | 43 | 45 | 2 |
| `letterform-1007:letterform_priors:becker` | after | 51 | 53 | 2 |
| `full-density-1008:lettering_columns:drone` | after | 6 | 8 | 2 |
| `flags-0918-0928:directional_comp:drone` | after | 2 | 3 | 1 |
| `flags-0918-0928:rail_comp:becker` | after | 20 | 21 | 1 |

## 5. Caveats

1. **The designs are not the pictures he judged.** Each pair was drawn again
   at the pro's width and garment (becker 101.9 mm on a hat, drone 62.6 mm
   on a hat, tires 114.3 mm, where the sittings showed 80-100 mm on a left
   chest), so a flag whose effect depends on size or fabric preset may not
   have done here what it did on his screen. The labels are his; the figures
   are from a sibling of what he saw. The cheap check, re-rendering one
   sitting at its own size and diffing the picks, was not run.
2. **Ours lies on one side of the pro.** More cuts on 187 of 200 designs,
   more hops on 188, more needle-up mm on 198. On this corpus the distance
   to the pro and the plain count rank the arms the same way; a pro
   reference only starts to matter once the engine can overshoot, which is
   where tires already is.
3. **Six logos, and the lettering jobs dominate.** Pairs from one logo share
   its art; the fixture interval is the honest one. The word cc and the
   column count read four jobs, and becker pins two words, so its cc moves
   in coarse steps (its distance to the pro's 1.0 reads 0, 0.397 or 0.5 on
   31 of 36 design readings): a word-cc margin of 0.5 there is one word read
   or not read.
4. **Tires' pro file is 3D puff**, a construction ours never sews; its
   stitch-type kappa against the pro is near its floor on every arm, and
   3.1 shows the sides-only hops clearance rests on its three decided pairs.
5. **Two trees carry the 10-11 doc's caveats forward**: the 77-pair flags
   sitting was judged on a 09-20 cloud render that matched the 09-18 laptop
   render to platform rounding, and `density-1007`'s Column lane at
   `2a87ba89` broke ties from OS entropy, so that arm's designs are a draw
   from the engine he saw, not a replay of it.
6. **`both_bad` is not `same`**; folding both into a tie or dropping
   `both_bad` changes no reading (3.1).
7. **Kappa moves with prevalence**, which is why the ties-in and sides-only
   figures are both shown and neither is a quality percentage. No raw
   agreement figure is computed by the tool or appears here (gate 4).
8. **Nothing here flips a flag, moves a gate, or proposes a phase advance.**

## 6. Reading for the Phase 1 exit

Two readings fit the table, and which to take is Kent's. **(a) Adopt the
trim family read against the pro - `hops` first, `cuts` beside it - as the
Phase 1 yardstick.** It is the only instrument that has tracked his picks
on either pool (trims on 10-11, hops and cuts here), and reading it as a
distance gives it a destination (the pro's 10-59 cuts per job) instead of
"fewer, forever". The exit as written cannot be met by it, though: it scores
his pick farther from the pro on 10 of 32 decided pairs, 6 of them not the
old-engine arm, and the misses are legible (he trades trims for lettering
construction and for the new engine). Adopting it therefore means rewriting
the exit's second clause as a tolerance he sets, for example *"the ties-in
kappa against his picks clears zero on both intervals, and the instrument
scores his pick farther from the pro on no more than one decided pair in
five"* (hops is at 10 of 32 today), with the understanding that it reads the
trims and nothing else, and that word cc and columns, the two instruments
built to read what he writes about, are not yet with him. **(b) Report that
the exit condition cannot be met by any instrument this corpus supports**:
the three that clear chance are one family and one dimension, the three
shaped like fidelity do not clear, the two whose reading actually uses the
pro's figure do not clear, and "never scores worse" fails everywhere. Under
(b) the next sitting should be built from the section 4 tally - the pairs
where the trim family and his eye disagree are the ones that would teach an
instrument what he weighs against trims - and the instrument to build is one
for flow, density and construction, which is what his notes name. Either way
no phase marker moves on this document.

## What would move it

A sitting on the nine new lettering logos at the pro's size, so the label
and the figure are on the same picture; pairs where ours is under the pro's
trim count, so the distance reading can disagree with the cost reading
somewhere other than tires; and a reader for construction - how a letter is
built, where a cut lands - since that is what he picked over trims on the
pairs the trim family gets wrong.

*(measured 2026-11-01 - `digitizer/tools/eye_pairs/pro_pooled.py` over
`docs/eye-pairs-2026-11-01/pro-pair-inputs.json`; designs re-drawn on their
sittings' trees by `pro_pooled_build.py render` and read with
`pro_pooled_build.py measure` on Kent's laptop, Windows, the primary venv;
labels from `docs/eye-pairs-2026-10-11/pooled-inputs.json`)*
