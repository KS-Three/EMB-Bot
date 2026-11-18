# How the pro sews MARINE, letter by letter, and how ours differs (2026-11-18)

Worker session for the director, after Kent's 2026-11-18 ruling on `lettering_columns_block_butt`: "Flip on, but make
sure the MARINE strokes match the pros. These letters need to be perfect." Built on #1683's head (it had not merged).

**Numbers and words only.** Nothing of the pro's file is rendered or committed here (`tests/test_no_new_pro_renders`,
public repo). Reader: `digitizer/tools/marine_construct.py` (new; one rule on the pro's DST and on ours written by
`digitizer_core.export`), on `tools/letter_pieces.py`. Six letters found in all five Becker placements.
Placements: hat large 101.9, LC large 95.7, hat small 76.5, chest small 76.5 (same file as hat small, moved), beanie 79.8.
Ours = main with `lettering_columns_block_butt` ON ("ours ON", built on #1683 before it landed; Kent flipped it in #1684); OFF is in the JSON too.
`python -m tools.marine_construct --out DIR` regenerates every number.

Conventions: y down; cross angle in degrees from the line of text (0 = level cross, square to an upright stem, +/-90 =
upright cross); span = the column's spine (cross midpoints) in mm; crosses per mm = 1 / pitch; counters = thread-free
pockets of the letter's colour block at 24 px/mm, 0.4 mm thread, underlay included.

## 1. What the pro does, in rules (all five placements agree; hat small = chest small)

1. **Stems are level and uncut.** Cross angle 0 +/- 2 over 10-14 mm, 5.0 crosses/mm, cross 5.2 mm at 101.9 (3.9-4.1 at
   76.5). Ours match on angle and density; ours are 0.3-0.6 mm LONGER (5.5-5.8 at 101.9) because they follow the art's
   edge where his are drawn a little inside it.
2. **A sheared slab across the top of the letter** (near-vertical crosses, -77 to -90 deg, cross 4.5-5.4 mm) sewn as its own
   column that overlaps the stem top by 1.0-1.5 mm: the A's two cap pieces (4.6 + 12.4 mm), the R's 13.2 mm slab, the E's
   12.2 mm top arm, the M's slab-plus-left-diagonal (9.1 mm, fan 31 deg). Ours has none (apex family OFF, Kent 11-17).
3. **Diagonals and the V sew LEVEL,** in short pieces cut at each junction: the M's V is four level pieces of 3-5 mm,
   cross 7.4-7.7 mm; the N's tips are level. Ours sews the M's two V diagonals at +22 and -20 deg and meets them at the
   notch (clashing angles).
4. **The R is stem + radial bowl + leg:** stem 10-12.6 mm level; the bowl is ONE column of 31.9 mm (101.9) / 33.7 mm
   (76.5) whose crosses turn radially round the counter (angle -49 -> +21 -> +85, fan 134-176 deg), cross 4.4 mm (thinner
   than the stem's 5.2); leg 7.3 mm level at the foot; plus two patches. **Counter 9.85 mm2 at 101.9 (art 6.63 measured
   on the art itself earlier today, by a different method), 4.5 at 76.5.**
5. **The A's crossbar is a horizontal column** (6.2 mm span at 101.9, crosses upright, constant 4.5-4.7 mm long) that
   butts both legs square. The legs are level, left 13.1 mm, right 19.4 mm; the right leg fans 37 deg at the apex into the
   cap. Counter 6.2 (101.9), 5.2 (95.7), 2.4 (76.5).
6. **The E: stem level, three arms upright-crossed and butted, top arm full width.** Stem 12.7 mm from the bottom corner
   to just under the top arm; top arm 12.2 mm (x full width, crosses -79 deg, 5.3 long); middle arm 6.2 mm (cross 3.9);
   bottom arm 8.1 mm; **the lower-left corner is three small fan pieces** (10-12 crosses each, turning -71 -> -27 deg)
   between the stem and the bottom arm. At 76.5 the E has 5 columns (4.3, 4.8, 4.2, 24.1 fan-90, 9.2).
7. **The I** is a 17 mm column (23 mm at 76.5 with the slab fanned into it) plus slab patches (4 at 101.9).
8. **Density 5.0 crosses/mm** (pitch 0.2) everywhere except the slab, A and bowl cuts at 4.4-6.7. **No cut is longer than
   the column;** the longest is the R bowl (31.9-35.5 mm).
9. **Order and underlay.** The satin is one run per letter with underlay and top interleaved column by column (the
   reader sees short walks of 1.5 mm stitches between 5 mm satin windows); ours lays the letter's whole underlay first
   (a 2.8 mm zigzag/walk of ~200 stitches) and then the tops. Stitches per cross (all stitches of the letter / crosses
   read): pro 1.5-2.1, ours 1.3-3.0 (101.9: ours 2.3-3.0 against 1.6-2.1). Ours carries ~35% more non-top stitches at the
   large size. Not a visible difference (buried); not touched.


## 2. Ours ON against the pro, per letter, ranked by what shows at print size

Ranking is by eye on the whole word at the five placements (`docs/renders/block-butt-2026-11-18/*_word.png`), then by
the numbers. The counters: A pro 6.2 / 5.2 / 2.4 against ours 6.47 / 6.35 / 4.2: the A's counter is fine (larger at
small size). R pro 9.85 / 8.06 / 4.5 against ours 4.59 / 4.57 / 2.2.

| rank | letter | pro | ours ON | visible at print size? |
|---|---|---|---|---|
| 1 | **R** (all sizes) | stem + one radial bowl column + leg + slab; counter 9.85 / 8.06 / 4.5 mm2 | 101.9 and 95.7: 5 straight columns (6.6, 7.4, 5.5, 4.6, 17.6 mm), bowl crosses 6-8.9 mm long, counter 4.6; **76.5 / 79.8: 2 columns, one 34-37 mm piece (fan: counter's corner) and a 7.4 mm piece, counter 2.2** | yes: at 76.5 and 79.8 the fan is the worst thing in the word; at 101.9 the counter is half closed and the bowl's top edge is ragged |
| 2 | **E** | stem + full-width top arm + mid + bottom arm + three-piece corner fan | 101.9 ON: 4 columns, top arm 9.0 mm butts the stem; **76.5 and 79.8: ON = OFF**, the folded 24 mm piece and a 23.6 mm fan (fan 85-90 deg) survive | yes at 76.5 / 79.8 (top-left fan, tapered arm ends); at 101.9 ours is a clean square E, the pro's differences are a corner and an overlap |
| 3 | **A crossbar** | horizontal column 6.2 mm, crosses upright, 4.5-4.7 long, butts both legs | a slanted column, 8.2 mm, crosses 78 deg, **1.2-5.0 mm long (tapered)** at 101.9; 76.5: three columns, no bar read at all | yes: reads as a slanted patch at 101.9 |
| 4 | **M's V** | four level pieces 3-5 mm, cross 7.4-7.7 | two diagonals at +22 / -20 deg, 11.5-12.4 mm, crosses 1-4.7 mm (tapered), meeting at the notch | moderately: the notch is visibly two directions |
| 5 | **N** | stem 13.1, diagonal 24.7 mm fanned 78 deg from the slab, stem; tips level | ON: 3 columns, diagonal level -12 deg, no fan | no: it already reads clean; the pro's fan is the slab |
| 6 | **Slabs on the top of M, A, R, I, N, E** | near-vertical sheared slab, 4-5 mm deep, overlaps the stem 1-1.5 mm | none | on the art the sheared top-left corner is visible; on the sewn word the lack of slab reads as plain stems (what #1659 left). A new narrow in-letter cap is a later question |
| 7 | **I** | 17 mm + slab patches | 1 column 17.2 mm | no |

## 3. What was built: four flags, all built OFF (`cfg.extra["lettering_columns_<name>"]`)

None is flipped. Each is layout only: no satin floor, pull compensation, cover tolerance, density or fabric number
changes (ROADMAP gate 1). OFF is byte-identical to `lettering_columns_block_butt` alone on every run below; each has a
`flag_sweep` over all 18 tripwire placements and 26 fixtures (`docs/renders/marine-match-2026-11-18/flag-sweeps/`).
**Only Becker moves, for every flag: 44 runs, 6 movers (the five placements and `fx_becker_marine_logo` = Becker at 80 mm),
38 byte-identical, 0 errors.** MFab hat at 30 mm: identical under all four (2,996 stitches, 10 trims, 17 jumps, grade B 76).

| flag | what it does | pro rule (section 1) |
|---|---|---|
| `lettering_columns_r_bowl` | on a block letter with one counter and a stem-head butt (R): cut a slab across the top (stem top + bowl top, upright crosses), the stem below it, the leg (level crosses), and sew the bowl as ONE column whose crosses start normal to each edge of the counter and pivot on its corners (`outline_cut._bowl_cuts`, `_bowl_column_normal`) | 2, 4 |
| `lettering_columns_block_butt_small` | block_butt's heavy-stroke gate 3.5 -> 3.0 mm: Becker MARINE at 76.5-79.8 mm measures 3.46 (E), so block_butt did nothing to its E, A and N there. No other committed job has a letter over 1.7 mm | 6 |
| `lettering_columns_a_bar` | a flat-topped block A: the lane's level cut at the counter's bottom (left foot + bar as one fanned piece) becomes the leg's inner edge, so both legs run uncut and the bar is its own column of upright crosses (`_a_bar_cuts`) | 5 |
| `lettering_columns_block_lean` | on a heavy block letter the satin convention's lean cap (30 deg) is 50 deg where that lets the house (level) cross through: the M's V diagonals and the N's diagonal cross level, as his do. An arm's near-upright cross keeps today's fade (`column_lean.cross_direction`) | 3 |

### Figures, every placement (stitches / trims / jumps / needle-up mm; base = main, block_butt ON since #1684; preflight grade and score equal on every row)

| design | base | r_bowl | block_butt_small | a_bar | block_lean | all four |
|---|---|---|---|---|---|---|
| Becker hat large 101.9 | 15,820 / 18 / 53 / 508.6 | 15,919 / 18 / 53 / 500.4 | = base | 15,800 / 18 / 53 / 508.6 | 15,796 / 18 / 53 / 508.6 | 15,856 / 18 / 53 / 504.6 |
| Becker LC large 95.7 | 14,291 / 13 / 30 / 236.8 | 14,331 / 13 / 30 / 243.8 | = base | 14,296 / 14 / 32 / 244.6 | = base | 14,336 / 14 / 32 / 251.7 |
| Becker hat small 76.5 | 10,165 / 9 / 35 / 304.4 | 10,071 / 9 / 35 / 304.4 | 9,999 / 10 / 36 / 309.2 | 10,144 / 9 / 35 / 304.4 | 10,152 / 8 / 34 / 303.6 | 9,871 / 9 / 35 / 308.4 |
| Becker chest small 76.5 | 10,039 / 7 / 33 / 300.6 | 9,890 / 7 / 33 / 300.6 | 9,877 / 8 / 34 / 305.8 | 10,018 / 7 / 33 / 300.6 | 10,071 / 7 / 33 / 300.6 | 9,739 / 8 / 34 / 305.8 |
| Becker beanie 79.8 | 13,619 / 12 / 41 / 376.8 | 13,575 / 11 / 40 / 375.3 | 13,473 / 13 / 43 / 380.5 | 13,589 / 12 / 42 / 369.4 | 13,612 / 12 / 41 / 376.8 | 13,392 / 12 / 43 / 371.6 |
| Becker 114 (hat large art) | 19,621 / 17 / 67 / 641.4 | 19,616 / 17 / 67 / 641.4 | = base | 19,710 / 17 / 67 / 640.6 | 19,559 / 18 / 68 / 642.8 | 19,643 / 18 / 68 / 642.0 |
| MFab hat 30 mm | 2,996 / 10 / 17 / 92.1 | = | = | = | = | = |

**What got worse (all small).** Trims: +1 at LC large (a_bar), hat small and chest small and beanie (block_butt_small), +1 at 114
mm (block_lean); the worst single row is one extra trim and 2 more jumps. Needle-up travel: +15 mm at LC large (all four),
+4-5 mm at the 76.5/79.8 placements. Preflight (`run_preflight`, 38 metrics, grade and score unchanged everywhere): bare artwork,
cover, coverage, uncovered, legibility and element-drop figures do not move on any of the 7 designs x 6 arms; the only
figures that move are `satin_short_fraction` (+0.001 to +0.003, two rows -0.001), `coverage_p95` +0.01 at hat small and
`trims_per_1000` +0.1 at five rows. No bare-fabric, cover or coverage figure moved the wrong way.

### Related tests with the four flags forced ON (with block_butt; measured before #1684 landed, the 11 below are the flags' own)

35 files, 579 tests (`test_column_*`, `test_lettering_*`, `test_outline_cut_units`, `test_a_cap_centered`, `test_apex_is_real`,
`test_edge_walk_keeps_cut`): flags OFF, 578 passed 1 xfailed. block_butt forced ON alone: 12 fail (#1683's list). All five
forced ON: 23 fail; the 11 added by these flags, none a bare-fabric, travel-guard or connector guard:
- OFF-byte pins on MARINE letters: `test_off_sews_exactly_what_main_sewed[marine102_A]`,
  `test_off_the_left_leg_below_the_bar_sews_steep` (A, `a_bar`), `test_off_is_byte_for_byte[marine102_M]`,
  `test_travel_per_job_within_today[marine102]` (M: 23.63 against 22.68 mm; `block_lean`),
  `test_past_the_cap_the_lean_fades_toward_the_pieces_own_normal` (pins the 30 deg cap, `block_lean`),
  `test_off_is_the_lane_before_the_flag[mfab105_band_letters]`.
- Assert the E's fold exists (Kent's 11-14 ruling, now also at 76.5-79.8 mm, `block_butt_small`):
  `test_the_e_folds_round_both_corners`, `test_only_the_e_moves`, `test_the_folded_e_needs_no_trim`.
- Edge-walk fixtures: `test_production_lane_buried_clean_at_offs_trims` (13 against 12 trims),
  `test_the_n_and_the_a_need_no_cut`.

**One to read:** `mfab105_band_letters` is MFab's 105 mm outline-band letters, heavy enough (>= 3.5 mm) for `block_lean`'s gate when
the lane is driven directly. The pipeline does not send them through `lean_columns` (MFab hat is byte-identical under the
flag), but the gate is stroke width alone, so a heavy-stroked design that does reach `lean_columns` would take it.
New tests: `tests/test_r_bowl.py` (7), `tests/test_marine_match.py` (10), on `testdata/marine102_*_letter(s).json`.

## 4. Per letter: matches the pro / differs / cannot match

Pictures: `docs/renders/marine-match-2026-11-18/<placement>_word.jpg` (ORIGINAL / BEFORE / AFTER at one frame) and `_letters.jpg`
(each letter, 2x), all five placements and 114 mm; ours only. BEFORE = main (block_butt ON since #1684), AFTER = all four flags.

| letter | status | detail |
|---|---|---|
| **M** | **matches** the V's cross direction; differs in the cuts | the V's diagonals cross level (0 +/- 3 deg, his 0) under `block_lean`. Differs: his V is four 3-5 mm pieces whose crosses run 7.4-7.7 mm, plus a slab-and-left-diagonal piece fanning 31 deg; ours is two diagonals of 11.7-11.9 mm cut at the stems' edges, crosses 2.8-3.6 mm median, and no slab |
| **A** | **matches** the bar and the legs; differs at the apex | `a_bar`: bar 3.9 mm span, crosses 87 deg (his 86), 4.9 mm long (his 4.6-4.7), butting both legs; legs level and uncut (18.3 and 18.6 mm; his 13.1 and 19.4). Differs: his bar tucks 1.5 mm under each leg (ours butts, overlap 0.5-1.0), his right leg fans 37 deg into a two-piece cap (we have none, apex family OFF) |
| **R** | **matches** the construction, **cannot match the counter** | slab upright (89 deg, his 78-90), stem level, leg level, bowl one column (30 crosses, 19.5 mm; his 101 crosses, 31.9 mm: his slab ends at the counter's right edge and the bowl takes the top-right corner, ours takes it with the slab). Counter 3.2 mm2 at 101.9 (his 9.85, art 6.63, block_butt alone 4.59) and 1.7 at 76.5 (his 4.5): normal crosses push the pull into the counter on all four sides where block_butt's level crosses push only into two. **Needs the pull's counter hold-off (gate 1): sew-out row 14.** Also: the bowl's outer edge steps 0.4 mm where horizontal crosses clip the arc |
| **I** | unchanged, differs | one 17.2 mm column; his has a 5 mm slab piece and 3-4 junction patches |
| **N** | **matches** the diagonal's cross; differs at the head | diagonal level (-1.6 to -1.4 deg), 19.5 mm; his fans 78 deg from the slab at the head and sews level at the foot. The slab is not built |
| **E** | **matches** the arms at 76.5-79.8 now; differs at the corners | `block_butt_small`: stem and three butted arms at 76.5 and 79.8 (before: a 24 mm folded fan and a 23.6 mm fan). Differs: his top arm is one 12.2 mm piece over the stem's top, his lower-left corner three small fans (we butt square) |
| **Slabs** (top of M A R I N E) | **not built** | the pro's sheared top band; #1659's apex family put ours on and Kent turned it off at the whole word. A narrow in-letter cap is possible (his is 4-5 mm deep and inside the outline), but the A, R and E now read well at the whole word without it; left for the director's call |

## 5. Data

Piece-level tables for hat large (every column in sewing order), then a per-letter line for the other four. `ends` is
what the column's end meets (`free` nothing, `butt` another column's body, `corner` / `straight` another column's end,
at more / less than 30 deg of axis turn). The full per-piece JSON is regenerated by the tool; it holds no stitch
coordinates beyond each column's two end points.

#### becker_hat_large

**M**

*pro*: 7 columns + 1 patches; counters none mm2; 2.06 stitches per cross; overlaps >= 0.3 mm: [2.15, 1.6, 0.56, 0.65, 0.45, 1.03, 0.72, 0.47, 1.53, 0.48]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 13.7 | 1.8 / 2.4 / 1.5 | 5.2 / 5.2 / 5.22 | 5.0 | free, butt |
| 2 | diagonal | 2.84 | -46.8 / -46.8 / -46.8 | 4.33 / 4.53 / 4.79 | - | patch, butt |
| 3 | curve | 9.11 | -74.5 / -67.3 / -43.5 | 5.0 / 5.39 / 5.81 | 6.67 | corner, butt |
| 4 | patch | 0.7 | -38.2 / -38.4 / -38.4 | 5.12 / 5.17 / 5.2 | - | patch |
| 5 | upright | 4.97 | -3.4 / -1.6 / -1.1 | 1.7 / 4.85 / 7.7 | 4.46 | free, corner |
| 6 | diagonal | 4.08 | -1.2 / -1.1 / -1.1 | 7.2 / 7.4 / 7.71 | 4.0 | corner, straight |
| 7 | diagonal | 3.97 | -1.4 / -1.6 / -1.0 | 6.1 / 7.7 / 9.11 | 4.85 | straight, straight |
| 8 | upright | 13.7 | -1.5 / -1.8 / -1.5 | 5.2 / 5.2 / 5.22 | 5.0 | corner, free |

*ours ON*: 4 columns + 0 patches; counters none mm2; 1.95 stitches per cross; overlaps >= 0.3 mm: [2.46, 2.51, 2.58]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 17.03 | -1.6 / -2.5 / -1.6 | 5.5 / 5.61 / 5.71 | 5.0 | free, straight |
| 2 | upright | 12.4 | 28.9 / 22.1 / 31.1 | 1.08 / 3.01 / 4.74 | 4.85 | straight, corner |
| 3 | upright | 11.46 | -25.6 / -19.9 / -22.9 | 1.04 / 2.73 / 3.81 | 5.0 | corner, straight |
| 4 | upright | 17.34 | 1.5 / 2.4 / 1.6 | 5.5 / 5.8 / 7.11 | 5.0 | straight, free |

**A**

*pro*: 5 columns + 0 patches; counters [6.2] mm2; 1.76 stitches per cross; overlaps >= 0.3 mm: [1.71, 1.55, 0.47, 0.35, 0.63]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | horizontal | 6.21 | -81.4 / 86.5 / 76.0 | 4.52 / 4.61 / 4.68 | 6.67 | butt, butt |
| 2 | upright | 19.45 | -1.8 / -10.8 / -38.4 | 3.51 / 5.39 / 5.87 | 6.33 | corner, corner |
| 3 | horizontal | 12.41 | -46.1 / -66.6 / -88.2 | 3.83 / 4.57 / 6.42 | 4.46 | corner, straight |
| 4 | horizontal | 4.6 | -76.6 / -83.9 / -89.8 | 5.2 / 5.23 / 5.39 | 6.67 | corner, straight |
| 5 | upright | 13.08 | 1.5 / 2.3 / 1.4 | 5.21 / 5.41 / 5.8 | 4.85 | butt, free |

*ours ON*: 3 columns + 1 patches; counters [6.47] mm2; 2.4 stitches per cross; overlaps >= 0.3 mm: [1.66, 0.91, 0.5, 0.89, 1.31]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 18.6 | -1.3 / -2.4 / -1.9 | 4.6 / 5.81 / 7.21 | 4.85 | butt, straight |
| 2 | diagonal | 8.19 | 83.8 / 78.3 / 78.9 | 1.24 / 3.3 / 4.97 | 4.0 | straight, butt |
| 3 | patch | 1.21 | 76.5 / 76.5 / 74.9 | 1.24 / 1.26 / 1.65 | - | patch |
| 4 | upright | 18.61 | 0.0 / -1.7 / -1.6 | 1.75 / 5.6 / 6.3 | 4.85 | straight, free |

**R**

*pro*: 4 columns + 2 patches; counters [9.85] mm2; 1.71 stitches per cross; overlaps >= 0.3 mm: [1.33, 0.45, 0.75, 0.38, 0.76]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | diagonal | 7.29 | -1.9 / -1.8 / -4.2 | 2.47 / 5.95 / 6.61 | 5.56 | free, butt |
| 2 | horizontal | 13.2 | -88.0 / -82.8 / -63.5 | 3.61 / 5.23 / 5.56 | 5.0 | corner, patch |
| 3 | patch | 1.44 | -56.4 / -54.3 / -54.3 | 3.74 / 4.64 / 5.54 | - | patch |
| 4 | curve | 31.94 | -48.6 / 20.6 / 85.0 | 3.61 / 4.43 / 5.52 | 4.72 | patch, patch |
| 5 | patch | 0.7 | -89.7 / -89.7 / -89.7 | 4.3 / 4.3 / 4.31 | - | patch |
| 6 | upright | 12.6 | -1.5 / -2.4 / -1.5 | 5.2 / 5.2 / 5.22 | 5.0 | free, butt |

*ours ON*: 5 columns + 1 patches; counters [4.59] mm2; 2.96 stitches per cross; overlaps >= 0.3 mm: [0.32, 0.6, 0.52, 0.84]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | horizontal | 6.64 | 27.6 / 19.0 / 15.4 | 1.66 / 3.88 / 6.36 | 5.0 | patch, patch |
| 2 | patch | 0.83 | 12.3 / 12.3 / 12.3 | 6.33 / 7.38 / 7.47 | - | patch |
| 3 | diagonal | 7.39 | 4.3 / 1.4 / 2.3 | 5.91 / 7.51 / 8.91 | 4.85 | patch, straight |
| 4 | upright | 5.55 | 1.1 / 1.8 / 1.4 | 6.3 / 7.51 / 8.7 | 4.93 | straight, corner |
| 5 | diagonal | 4.57 | -1.5 / -1.5 / -1.2 | 5.71 / 6.2 / 6.7 | 4.85 | free, corner |
| 6 | upright | 17.59 | -1.6 / -2.3 / -1.5 | 5.4 / 6.0 / 7.01 | 5.0 | free, patch |

**I**

*pro*: 3 columns + 3 patches; counters none mm2; 1.58 stitches per cross; overlaps >= 0.3 mm: [0.48, 0.44, 0.53, 0.5, 0.47]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | curve | 5.03 | 88.7 / -84.2 / -70.4 | 3.63 / 4.57 / 5.73 | 4.44 | patch, patch |
| 2 | patch | 1.12 | -61.4 / -61.4 / -61.4 | 3.72 / 4.52 / 5.44 | - | patch |
| 3 | upright | 2.88 | -54.0 / -50.7 / -48.7 | 3.5 / 5.06 / 7.07 | 3.31 | patch, patch |
| 4 | patch | 1.39 | -42.4 / -42.4 / -42.4 | 4.46 / 5.4 / 6.23 | - | patch |
| 5 | patch | 2.18 | -35.6 / -33.1 / -33.1 | 3.85 / 4.15 / 5.58 | - | patch |
| 6 | upright | 17.04 | -25.6 / -1.5 / -2.0 | 3.81 / 5.2 / 5.87 | 5.0 | patch, free |

*ours ON*: 1 columns + 0 patches; counters none mm2; 2.46 stitches per cross; overlaps >= 0.3 mm: none

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 17.16 | -1.6 / -2.5 / -1.6 | 5.5 / 5.61 / 6.61 | 5.0 | free, free |

**N**

*pro*: 4 columns + 0 patches; counters none mm2; 1.83 stitches per cross; overlaps >= 0.3 mm: [2.21, 0.52, 2.35, 0.48]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 13.1 | 1.5 / 1.5 / 1.5 | 5.2 / 5.2 / 5.22 | 5.0 | free, butt |
| 2 | curve | 24.67 | -77.0 / -32.5 / 0.6 | 3.61 / 4.87 / 5.69 | 5.56 | corner, straight |
| 3 | upright | 5.13 | -1.7 / -1.2 / -1.1 | 5.2 / 6.5 / 7.8 | 5.0 | free, straight |
| 4 | upright | 12.3 | -1.5 / -1.5 / -1.7 | 5.5 / 5.5 / 5.51 | 5.0 | straight, free |

*ours ON*: 3 columns + 0 patches; counters none mm2; 2.5 stitches per cross; overlaps >= 0.3 mm: [1.57, 1.54]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | upright | 16.17 | 1.7 / 2.4 / 9.6 | 1.2 / 5.4 / 6.2 | 5.0 | free, butt |
| 2 | diagonal | 19.18 | -12.2 / -12.0 / -12.2 | 5.49 / 6.1 / 6.32 | 4.46 | straight, straight |
| 3 | upright | 16.85 | 9.9 / 2.5 / 1.6 | 1.1 / 5.41 / 5.81 | 5.0 | straight, free |

**E**

*pro*: 7 columns + 0 patches; counters none mm2; 1.7 stitches per cross; overlaps >= 0.3 mm: [1.13, 0.43, 0.5, 0.54, 0.45, 1.06]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | horizontal | 6.19 | 88.8 / -88.0 / -88.0 | 1.26 / 3.9 / 3.92 | 6.67 | free, butt |
| 2 | curve | 8.12 | -88.0 / -88.0 / -78.2 | 3.51 / 5.2 / 5.39 | 5.0 | free, corner |
| 3 | diagonal | 2.95 | -71.1 / -64.9 / -61.4 | 3.49 / 4.69 / 6.07 | 2.8 | corner, straight |
| 4 | curve | 3.08 | -53.6 / -48.1 / -45.5 | 4.0 / 5.39 / 7.0 | 4.0 | straight, straight |
| 5 | diagonal | 4.3 | -39.2 / -32.2 / -27.0 | 3.72 / 4.58 / 5.61 | 4.0 | straight, straight |
| 6 | upright | 12.71 | -18.4 / 2.7 / 2.0 | 3.14 / 5.1 / 5.12 | 5.0 | straight, butt |
| 7 | horizontal | 12.15 | -77.9 / -79.3 / -79.3 | 5.25 / 5.32 / 5.36 | 5.0 | corner, free |

*ours ON*: 4 columns + 0 patches; counters none mm2; 2.29 stitches per cross; overlaps >= 0.3 mm: [1.7, 1.96, 0.87]

| # | role | span mm | cross angle start / mid / end | cross len min / med / max | per mm | ends |
|---|---|---|---|---|---|---|
| 1 | horizontal | 7.84 | -77.7 / 86.8 / 87.6 | 3.2 / 4.1 / 4.52 | 5.0 | free, butt |
| 2 | horizontal | 9.0 | -89.3 / -88.2 / -78.8 | 3.49 / 5.12 / 6.31 | 5.0 | butt, free |
| 3 | upright | 17.22 | -1.3 / -2.4 / -1.6 | 5.6 / 5.8 / 6.81 | 5.0 | corner, butt |
| 4 | curve | 10.39 | -78.4 / -69.2 / -68.3 | 1.21 / 5.41 / 5.55 | 5.0 | butt, free |
#### becker_lc_large

**M**

*pro*: 6 columns + 2 patches; counters none mm2; 2.08 stitches per cross; overlaps >= 0.3 mm: [2.15, 1.31, 0.46, 0.61, 0.47, 0.97, 0.73, 0.47, 1.51, 0.49]

*ours ON*: 4 columns + 0 patches; counters none mm2; 2.99 stitches per cross; overlaps >= 0.3 mm: [0.9, 0.78]

**A**

*pro*: 3 columns + 0 patches; counters [5.18] mm2; 1.73 stitches per cross; overlaps >= 0.3 mm: [1.53, 1.64, 1.48]

*ours ON*: 3 columns + 0 patches; counters [6.35] mm2; 2.14 stitches per cross; overlaps >= 0.3 mm: [0.74, 0.93, 1.41]

**R**

*pro*: 3 columns + 1 patches; counters [8.06] mm2; 1.73 stitches per cross; overlaps >= 0.3 mm: [1.19, 0.92, 0.77]

*ours ON*: 5 columns + 0 patches; counters [4.57] mm2; 2.67 stitches per cross; overlaps >= 0.3 mm: [0.56, 0.52, 0.65]

**I**

*pro*: 3 columns + 1 patches; counters none mm2; 1.53 stitches per cross; overlaps >= 0.3 mm: [1.53, 0.59, 0.54, 0.54]

*ours ON*: 1 columns + 0 patches; counters none mm2; 2.28 stitches per cross; overlaps >= 0.3 mm: none

**N**

*pro*: 5 columns + 0 patches; counters none mm2; 1.8 stitches per cross; overlaps >= 0.3 mm: [2.0, 0.53, 2.22, 2.19, 0.49]

*ours ON*: 3 columns + 0 patches; counters none mm2; 2.28 stitches per cross; overlaps >= 0.3 mm: [1.15, 1.07]

**E**

*pro*: 4 columns + 0 patches; counters none mm2; 1.76 stitches per cross; overlaps >= 0.3 mm: [1.05, 0.34, 1.06]

*ours ON*: 4 columns + 0 patches; counters none mm2; 2.09 stitches per cross; overlaps >= 0.3 mm: [1.72, 1.36, 0.93]
#### becker_hat_small

**M**

*pro*: 6 columns + 3 patches; counters none mm2; 2.13 stitches per cross; overlaps >= 0.3 mm: [1.45, 1.02, 0.58, 1.21, 0.57, 0.45, 0.35, 0.64, 0.32, 0.56, 0.3, 0.78, 0.7, 0.47, 1.3, 0.49]

*ours ON*: 4 columns + 0 patches; counters none mm2; 1.56 stitches per cross; overlaps >= 0.3 mm: [1.8, 2.3, 2.65]

**A**

*pro*: 6 columns + 2 patches; counters [2.43] mm2; 1.7 stitches per cross; overlaps >= 0.3 mm: [2.35, 2.4, 0.37, 0.87, 0.96, 1.57, 1.26, 1.51, 1.4, 1.16, 0.98, 0.31, 0.67]

*ours ON*: 3 columns + 0 patches; counters [4.17] mm2; 1.68 stitches per cross; overlaps >= 0.3 mm: [1.65, 1.63, 0.81]

**R**

*pro*: 4 columns + 5 patches; counters [4.49] mm2; 1.73 stitches per cross; overlaps >= 0.3 mm: [1.07, 1.19, 0.93, 1.54, 0.46, 0.88, 0.97, 0.88, 0.72, 1.39, 0.79, 1.48, 1.01, 1.09, 0.8, 1.51]

*ours ON*: 2 columns + 0 patches; counters [2.2] mm2; 2.28 stitches per cross; overlaps >= 0.3 mm: [1.06]

**I**

*pro*: 1 columns + 1 patches; counters none mm2; 1.51 stitches per cross; overlaps >= 0.3 mm: [1.45]

*ours ON*: 1 columns + 0 patches; counters none mm2; 2.26 stitches per cross; overlaps >= 0.3 mm: none

**N**

*pro*: 5 columns + 1 patches; counters none mm2; 1.77 stitches per cross; overlaps >= 0.3 mm: [1.26, 0.35, 1.21, 0.43, 1.97, 2.88, 0.52, 2.02, 0.49]

*ours ON*: 3 columns + 0 patches; counters none mm2; 1.85 stitches per cross; overlaps >= 0.3 mm: [1.46, 1.43]

**E**

*pro*: 5 columns + 0 patches; counters none mm2; 1.72 stitches per cross; overlaps >= 0.3 mm: [1.33, 1.93, 1.67, 2.37, 1.1, 0.99]

*ours ON*: 3 columns + 0 patches; counters none mm2; 2.15 stitches per cross; overlaps >= 0.3 mm: [1.01, 0.49, 1.24]
#### becker_chest_small

**M**

*pro*: 6 columns + 3 patches; counters none mm2; 2.13 stitches per cross; overlaps >= 0.3 mm: [1.45, 1.02, 0.58, 1.21, 0.57, 0.45, 0.35, 0.64, 0.32, 0.56, 0.3, 0.78, 0.7, 0.47, 1.3, 0.49]

*ours ON*: 4 columns + 0 patches; counters none mm2; 1.58 stitches per cross; overlaps >= 0.3 mm: [1.54, 1.76, 1.92]

**A**

*pro*: 6 columns + 2 patches; counters [2.43] mm2; 1.7 stitches per cross; overlaps >= 0.3 mm: [2.35, 2.4, 0.37, 0.87, 0.96, 1.57, 1.26, 1.51, 1.4, 1.16, 0.98, 0.31, 0.67]

*ours ON*: 3 columns + 0 patches; counters [4.21] mm2; 1.29 stitches per cross; overlaps >= 0.3 mm: [1.42, 1.37, 0.67]

**R**

*pro*: 4 columns + 5 patches; counters [4.49] mm2; 1.73 stitches per cross; overlaps >= 0.3 mm: [1.07, 1.19, 0.93, 1.54, 0.46, 0.88, 0.97, 0.88, 0.72, 1.39, 0.79, 1.48, 1.01, 1.09, 0.8, 1.51]

*ours ON*: 2 columns + 0 patches; counters [2.15] mm2; 2.28 stitches per cross; overlaps >= 0.3 mm: [0.9]

**I**

*pro*: 1 columns + 1 patches; counters none mm2; 1.51 stitches per cross; overlaps >= 0.3 mm: [1.45]

*ours ON*: 1 columns + 0 patches; counters none mm2; 1.26 stitches per cross; overlaps >= 0.3 mm: none

**N**

*pro*: 5 columns + 1 patches; counters none mm2; 1.77 stitches per cross; overlaps >= 0.3 mm: [1.26, 0.35, 1.21, 0.43, 1.97, 2.88, 0.52, 2.02, 0.49]

*ours ON*: 3 columns + 0 patches; counters none mm2; 1.61 stitches per cross; overlaps >= 0.3 mm: [1.2, 1.08]

**E**

*pro*: 5 columns + 0 patches; counters none mm2; 1.72 stitches per cross; overlaps >= 0.3 mm: [1.33, 1.93, 1.67, 2.37, 1.1, 0.99]

*ours ON*: 3 columns + 0 patches; counters none mm2; 2.14 stitches per cross; overlaps >= 0.3 mm: [0.98, 0.49, 1.27]
#### becker_beanie

**M**

*pro*: 6 columns + 3 patches; counters none mm2; 2.05 stitches per cross; overlaps >= 0.3 mm: [1.49, 1.0, 0.57, 1.19, 0.58, 0.42, 0.3, 0.68, 0.3, 0.6, 0.79, 0.72, 0.47, 1.34, 0.5]

*ours ON*: 4 columns + 1 patches; counters none mm2; 1.78 stitches per cross; overlaps >= 0.3 mm: [1.73, 1.92, 2.08]

**A**

*pro*: 7 columns + 2 patches; counters [2.29] mm2; 1.63 stitches per cross; overlaps >= 0.3 mm: [1.13, 2.28, 2.37, 0.38, 0.9, 0.97, 1.69, 1.36, 1.78, 0.69, 1.51, 1.45, 1.12, 1.19, 0.38, 0.64]

*ours ON*: 3 columns + 1 patches; counters [4.41] mm2; 2.09 stitches per cross; overlaps >= 0.3 mm: [1.47, 0.8, 0.55, 0.95, 1.37]

**R**

*pro*: 4 columns + 5 patches; counters [4.44] mm2; 1.69 stitches per cross; overlaps >= 0.3 mm: [0.97, 1.2, 0.3, 0.81, 1.45, 0.49, 0.91, 0.98, 0.96, 0.72, 1.18, 0.76, 1.54, 0.9, 1.15, 0.75, 1.47]

*ours ON*: 2 columns + 0 patches; counters [2.15] mm2; 2.36 stitches per cross; overlaps >= 0.3 mm: [0.91]

**I**

*pro*: 1 columns + 0 patches; counters none mm2; 1.52 stitches per cross; overlaps >= 0.3 mm: none

*ours ON*: 1 columns + 0 patches; counters none mm2; 2.25 stitches per cross; overlaps >= 0.3 mm: none

**N**

*pro*: 4 columns + 1 patches; counters none mm2; 1.79 stitches per cross; overlaps >= 0.3 mm: [1.3, 1.26, 2.0, 0.51, 1.99, 0.49]

*ours ON*: 3 columns + 0 patches; counters none mm2; 1.85 stitches per cross; overlaps >= 0.3 mm: [1.27, 1.56]

**E**

*pro*: 5 columns + 2 patches; counters none mm2; 1.64 stitches per cross; overlaps >= 0.3 mm: [1.41, 1.95, 0.45, 1.05, 1.13, 0.89, 1.74, 1.18, 1.0, 1.37]

*ours ON*: 4 columns + 0 patches; counters none mm2; 2.09 stitches per cross; overlaps >= 0.3 mm: [3.04, 1.03, 0.49, 1.23]
