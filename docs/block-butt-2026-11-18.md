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
