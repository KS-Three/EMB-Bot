# Becker MARINE: the R, N and E fans, and the A counter (2026-11-18)

Prime-grader scorecard 2026-11-18, `L_becker_hat_large`. Tree `ea4257d0`. Worker session for the director.

## 1. Is it new? No.

Renders of the MARINE band at `a5a61d0b` (parent of #1583), `50713b25` (#1583) and main
(`docs/renders/marine-fan-2026-11-18/marine_pre1583_1583_main.png`): the R, N and E fans are in all three.
#1583 capped the letters' tops and moved nothing else; the revert (#1659) took the caps back and left the
fans. They are older than the apex family, not the revert's cost.

## 2. Per fault: real, artefact or limit?

Thread-free hole area, mm2, measured on a bare render at 24 px/mm (enclosed holes of one colour of thread;
art measured on the registered original):

| counter | art | pro's file | ours OFF | ours ON |
|---|---|---|---|---|
| A | 5.61 | 5.77 | 5.93 | 5.93 |
| R | 6.63 | 9.30 | 3.18 | 4.06 |

- **A counter "filled with thread" (27, 54): not real.** It is as open as the art and the pro's. The reader
  took the crossbar slab under it for fill. Nothing to fix.
- **R counter: real, half closed (3.18 of 6.63).** Fan stitches from the counter's top-left corner cross it.
- **R, N, E fans (48.5,52 / 72,54 / 90,56): real in the plan.** Read per column (`letter_columns` run
  on the stage-7 polygons): the R's top-left is a `mitre` cut from the counter's corner to the letter's corner,
  so the stem's head and the bar share one fanned column (sweep 108 deg); the E's pointed-slot fold
  (`lettering_columns_corner_fold_apex_side`, ON since 11-14) is one column that sweeps the whole spine
  (sweep 105 deg); the N's diagonal ends are fanned by `_fan_ends` (58 and 57 deg).
- **A crossbar and M notch angles (27,61 / 13,55): nitpicks, left alone.** Both are the junction pieces
  the pro cuts the same way.

## 3. The fix: `cfg.extra["lettering_columns_block_butt"]` (built OFF, not flipped)

`outline_cut._BLOCK_BUTT`, entered in `pipeline._plan_stitches`, in `shape_memo._AMBIENT`. Heavy strokes only
(`BUTT_MIN_W_MM` = 3.5 mm stroke width). Three rules:

1. `_fold_corners`: a pointed slot's tip is left cut, so the E's arms butt the stem.
2. `_butt_mitres`: where a stem's edge runs up from a `through` cut to a counter corner and a `mitre` cut slants
   on to the letter's corner, the mitre becomes a `butt` straight up the stem's edge. The stem sews to its top;
   the bar and bowl sew as their own straight column. Fanned pieces of such a letter (and of an E with slot
   cuts) are stationed straight along their long axis (`_straight_rescan`, the small-bold fallback).
3. A straight piece's slanted end is not fanned when the fan sweeps past 45 deg and the square end leaves
   at most 0.05 mm2 of the piece bare (`_bare_area`).

The first version of rule 2's rescan and of rule 3 applied to every letter and moved 22 of 46 runs, and wrecked
the A's crossbar at 80 mm. Narrowed as above, only Becker moves.

## 4. Evidence

OFF is byte-identical to main (`ea4257d0`) on Becker hat large (md5 of `design["stitches"]`). 46 runs: the 9
committed pro jobs at their own size and at the Studio request (80 mm, hat), the 26
`corpus_scorecard.FIXTURES` at the Studio request, MFab hat at 30 mm, Becker at 114 mm. **Moved: 4 runs, 3
distinct digitizes. The other 43 are byte-identical.**

| run | stitches | trims | jumps | needle-up travel mm | preflight |
|---|---|---|---|---|---|
| Becker hat large 101.9 | 16,246 -> 15,820 | 19 -> 19 | 20 -> 20 | 489.6 -> 508.6 | A 100 -> A 100 |
| Becker 80 (= `fx_becker_marine_logo`) | 10,953 -> 10,791 | 12 -> 13 | 14 -> 14 | 370.7 -> 378.4 | A 100 -> A 100 |
| Becker 114 | 19,955 -> 19,621 | 18 -> 18 | 20 -> 20 | 629.5 -> 641.4 | A 100 -> A 100 |

Bare artwork, coverage and uncovered figures do not move; `satin_short_fraction` rises 0.001-0.002. Plan change
at 101.9: the R is two straight columns (stem + bowl) in place of a folded one and a curved one; the E is a stem
and three arms in place of one folded column and one arm; the N's diagonal ends are square. Cost: about 8-19 mm
more needle-up travel, one more trim at 80 mm.

Pictures: `docs/renders/block-butt-2026-11-18/`.

## 5. What it does NOT fix, and the catch

- **R counter** is 4.06 of 6.63 mm2: the fan is gone but the bowl's crosses still crowd the counter.
- **R at 114 mm is unchanged**: the butt cut is built but the fold look drops it (one folded column), left as
  OFF. E and N do move at 114.
- **E's top-left still fans at 80 mm.** The stem and arms are straight; the corner above the top slot is not.
- **It undoes Kent's 11-14 "nice corner" E** (`corner_fold_apex_side` ON): the E no longer folds round its
  corners, where the pro does fan some L corners. The whole word is clearly better at all three sizes by eye,
  but that is his call; the flip question needs these pictures.
- Related tests with the flag forced ON: 12 of 494 fail, all OFF-byte pins or "the fan exists" feature tests
  (`test_off_is_byte_for_byte`, `test_kents_pin_14_e_at_hat_large_size`, ...); no bare-fabric, travel or
  connector guard fails.

## 6. Director's follow-up (same day): all 18 committed tripwire jobs, the other Becker placements, test split, the 3.5 mm number

**18 committed jobs at their own size and garment, OFF vs ON** (`tools.flag_sweep` had not landed; extended the
sweep script). 5 move (all Becker), 13 are byte-identical. Preflight grade and bare/coverage/uncovered figures do
not move on any.

| job | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|
| becker_hat_large 101.9 | 16,246 -> 15,820 | 19 -> 19 | 20 -> 20 | 489.6 -> 508.6 |
| becker_lc_large 95.7 | 14,802 -> 14,291 | 13 -> 14 | 14 -> 15 | 213.8 -> 236.8 |
| becker_hat_small 76.5 | 10,319 -> 10,165 | 10 -> 10 | 14 -> 14 | 306.3 -> 304.4 |
| becker_chest_small 76.5 | 10,156 -> 10,039 | 9 -> 8 | 13 -> 12 | 303.5 -> 300.6 |
| becker_beanie 79.8 | 13,653 -> 13,619 | 13 -> 14 | 15 -> 16 | 385.0 -> 376.8 |

Not moved: gaulke hat / lc / beanie, goldentee, hotel_fremont hat / patch, mfab hat / lc, precision_drone,
tires_hat_3d, toat_machine hat / beanie, toat_beanie.

**Word pictures** `docs/renders/block-butt-2026-11-18/<job>_word.png`, ORIGINAL | BEFORE | AFTER, for every
Becker placement. By eye: clear gain at 95.7 and 101.9 mm (R, E, N and the M's top-left clean); at 76.5 and 79.8 mm
the gain is smaller: the N's diagonal is clean and the E's arms butt, **the R keeps its fan** (the butt is built, then
the fold look drops it, as at 114 mm) and the E's top-left still fans. No letter is worse. **The M at 80 mm**
(and at 76.5, 95.7): its right diagonal's slanted top end sews square crosses where OFF fans it, so the small
tabs OFF leaves at the M's top right are gone; V and stems unchanged. A visible change on a letter the grader did
not flag; the OFF M fan is what `test_on_an_m_with_an_acute_tip_is_not_read_as_an_e` pins.

**The 12 failing flag-ON tests, split** (related files, flag forced ON, 494 run):
- *Asserts the E fold fan exists (Kent's 11-14 `corner_fold_apex_side` ruling), 1:*
  `test_column_corner_fold_apex_side.py::test_kents_pin_14_e_at_hat_large_size` (ON gives 4 straight columns, no
  `folded`).
- *Asserts the M's fan exists, 1:* `test_column_apex_cut.py::test_on_an_m_with_an_acute_tip_is_not_read_as_an_e`
  (fan sweep 27.9 deg ON against > 75).
- *Pins OFF bytes or today's crosses, 10:* `test_column_apex_cut.py::test_off_sews_exactly_what_main_sewed`
  [marine76_M, marine76_N, marine96_M]; `test_column_apex_walk.py::test_off_is_byte_for_byte` [marine76_M,
  marine80_M, marine96_M] and `::test_the_crosses_are_todays[marine96_M]`;
  `test_column_connectors_buried.py::test_off_leaves_running_stitch_on_finished_satin`;
  `test_column_italic_lean.py::test_off_is_the_lane_before_the_flag[becker80_lane_letters]` and
  `::test_on_an_upright_word_is_byte_identical[becker80_lane_letters]`.
  All ten run Becker MARINE letters, the only heavy ones in the suite.

**"Heavy strokes only" as a number:** `BUTT_MIN_W_MM = 3.5`, against `outline_cut.stroke_width(letter polygon)` in
mm. Measured widest letter per job (own size): Becker 4.0 (76.5 mm) to 5.3 (101.9 mm); every other committed
job is 0.8 to 1.7 (gaulke 1.5-1.7, goldentee 1.2, hotel_fremont 0.8, mfab 1.1-1.3, drone 1.6, toat 1.6-1.7;
tires_hat_3d has no lettering-lane letters). **So no other design has a single letter within 1.8 mm of the gate,
which is why none moved: today the flag is a Becker-only change, and the gate has not been tested against any
other heavy block lettering.** A letter above 3.5 mm on other art would be taken by it.
