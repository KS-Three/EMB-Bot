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

## 7. Hand-off: matching the pro's MARINE (for the next worker)

Kent, 2026-11-18, ruling the flip: "Flip on, but make sure the MARINE strokes match the pros. These letters need to
be perfect." This section is what I know, so you do not re-derive it. Everything about the pro below is from
`docs/big-letter-construction-2026-10-24.md` (his MARINE at 76.5 and 101.9 mm, read stitch by stitch) and
`docs/renders/big-letter-construction-2026-10-24/`; everything about ours is from the 101.9 mm render and the
per-column plan on the flag-ON tree. His file is gitignored: do not commit a render of it.

### What he does, in one paragraph

Every MARINE letter's top ~28% is a **slab**: a parallelogram sheared to the left (the art's own shape, a notch on
the left edge at 22-30% of the cap). He sews the slab as its own piece, crosses along its sheared edge (about
-63 to -77 deg, near vertical), and the stem or stroke below it as a separate piece at 0 deg (horizontal crosses),
10 mm tall, butted under the slab. Strokes meet in **butts**, with small patch pieces at the junctions; he fans only
where a slab turns into a stroke. No length cap on a piece. That slab is what the apex family tried to build
(`apex_pro`, `apex_pro_joints`, `corner_fold_cap_flared`, OFF since #1659: caps that overhung the letter, wrong
depth). Kent ruled that family off; the flip does not use it.

### Per letter: what still differs (flag ON, 101.9 mm)

| letter | pro | ours ON | gap |
|---|---|---|---|
| M | slab + left diagonal one piece; stems 9.9 mm below the slab at 0 deg; right diagonal 3 pieces, all level crosses; V = 3 patches | stems full height; diagonals one column each, the right one's slanted end now square (was fanned); no slab | no slab; the V is not patched; diagonal crosses are slanted, his level |
| A | slab/apex piece with vertical crosses, left leg 10.4 mm at 0 deg under it, right leg from the apex fanning 82 deg; crossbar 5.6 mm, vertical crosses, butts both legs | three columns (two legs + crossbar), no slab; legs at +15/-10 deg; crossbar 7.4 mm at 74 deg. **The A counter is open (5.93 vs art 5.61 mm2): leave it.** | no slab; leg and crossbar angles |
| R | slab + bowl ONE 33.7 mm piece, the slab's crosses turning radially round the bowl; stem 10.1 mm under the slab; leg its own 4.7 mm piece at 0 deg, 5 patches at the bowl-leg-stem junction | stem full height (0 deg); bowl + leg ONE straight column whose crosses are **horizontal, i.e. parallel to the top bar and the bowl's upper stroke, not across it** | no slab; the bowl's crosses should turn across the stroke (radial round the curve); leg not its own piece; no junction patches; counter 4.06 of 6.63 mm2 |
| I | stem + slab one piece, the slab fanning into the stem | one 0-deg column, no slab | no slab fan |
| N | slab + diagonal one piece, the slab fanning into the diagonal (median -32 deg); stems 9.8 mm under the slab; diagonal cut again where it joins the right stem | left stem 37 deg wedge piece at the top left (fan sweep 37, under the 45 cutoff, still there), diagonal with square ends, right stem | left top wedge still fans; no slab |
| E | slab + top arm one piece across the whole top, crosses -77 deg; stem + bottom arm ONE piece folded round the foot; middle arm its own piece, vertical crosses, butts the stem, 2 junction pieces | stem full height, three arms butted, vertical crosses; the top-left corner above the top slot **still fans at 80 mm** | slab; he folds stem + bottom arm (we butt, the flip replaces Kent's 11-14 fold); top-left fan at 80 mm; the bottom arm's slanted end has crowded crosses |

Measure with `tools/letter_pieces.py` (his DST vs ours) and `tools/apex_pro.py measure` (angle error per mm2); picture
with `tools/pro_pair.py --band`. Kent wants the WHOLE WORD at print size, not close-ups (`docs/apex-family-revert-2026-11-17.md`).

### Which functions build each letter's columns (`digitizer/digitizer_core/`)

- Entry: `columns.lettering_columns_shape` (stage 7 calls it per letter) -> `outline_cut.letter_columns` ->
  `_letter_columns`. Order inside it: `find_cuts` (junction cuts: `through`, `mitre`, `ext`, `again`...) ->
  `_butt_mitres` (flag) -> `slot_cuts` (E/F stem line, `slot`) -> `split` -> a small-piece clean-up loop -> per piece
  `_refine` (the fold look; `_fold_refine`, judged by `columns.sewn_knots`) -> `build_column` / `_build_column`.
- One column: `straight_axis` + `scan_stations` (crosses square to an axis) with `_cap_square_ends`, `_fan_ends`
  (fans a slanted end; the flag skips it past 45 deg), `_mitre_ends`; else `rails` + `pair_rails` (curved/ring);
  `_straight_rescan` (the small-bold fallback the flag now uses for a block letter) stations a piece along its
  `_long_axis`. `ring_rails` makes the R's bowl a ring when there is no butt.
- After the columns: `_fold_corners` / `_fold_pair` / `_fold_join` (L folds; `_FOLD_APEX_SIDE` and the flag's slot skip),
  `_absorb_serifs`, `_drop_stalls`. Sewing order and links: `columns.column_runs`.
- Apex family (OFF): `_apex_pro_cuts`, `_apex_pro_split`, `_apex_pro_column`, `_apex_pro_joint_cuts`,
  `_cap_flared_cuts`, `_apex_pro_cap_column`. Slab-like geometry lives there.
- The flag: `outline_cut._BLOCK_BUTT`, `BUTT_MIN_W_MM`, `_butt_mitres`, `_butt_piece`, `_bare_area`; scope in
  `pipeline._plan_stitches`, key in `shape_memo._AMBIENT`.

### What I tried and dropped

- **Rescan and fan-skip on every letter**: 22 of 46 runs moved and the A's crossbar broke at 80 mm (rule split:
  rescan alone wrecks the A; fan-skip alone moves 15 designs, MFab W gains 0.21 mm2 bare). Hence the heavy-stroke
  gate and "a letter with a butt or slot cut".
- **Skipping `_fan_ends` always** (the first N fix): `test_no_more_thread_on_bare_fabric_than_today[mfab97_W]`
  0.21 mm2 and `test_the_crotch_stays_covered` rose. Now only past 45 deg and only if the square end leaves <= 0.05 mm2.
- **The R butt at 76.5, 79.8 and 114 mm: built, then dropped by the fold look.** `_butt_mitres` makes the `butt` cut
  (verified at 114 mm: W 5.9, edge 3.4 mm, hit 5.6 mm up), but the final `LetterCut.cuts` is `[]` and the letter is one
  `folded` column of sweep 106: `_refine`/`piece_judge` prefers a fold candidate once the bowl, rescanned along a
  horizontal long axis (vertical crosses over a 12 mm wide piece), sews worse. At 80 and 102 mm the bowl's long axis is
  vertical, the rescan gives horizontal crosses and the butt survives. Forcing the rescan axis to the stem's direction
  (horizontal crosses) did not change 114 mm: the drop is not (only) the axis. Not diagnosed further; print
  `lc.cuts` and each column's `kind` from `letter_columns` on the stage-7 polygons (capture them by wrapping
  `columns.lettering_columns_shape`, see `testdata/marine102_*` for the 102 mm polygons).
- **The E top-left at 80 mm**: the corner above the top slot is a piece with a 37-105 deg fan that `_fan_ends` and the
  rescan do not reach; I stopped at the flag's scope.
- **`outline_cut.slot_cuts` as the E's whole fix** (cut the stem line) is what rule 1 leans on; a folded stem + bottom
  arm like his needs `_fold_pair` to accept the slot tip, which is exactly `corner_fold_apex_side` (what the flag
  turns off on heavy strokes). If you want his fold back for the E's bottom, that is the place.

### Traps

- A new `outline_cut` ContextVar must be in `shape_memo._AMBIENT`; `(_MEMO.get() or {})` is a throwaway when the memo is
  `{}` (empty dict is falsy: test `is not None`).
- Tests that call `outline_cut.letter_columns` or `columns.lettering_columns_shape` directly never see the config
  default (the ContextVar defaults False): they test the OFF arm unless they enter `block_butt_scope(True)`.
- `testdata/marine102_EN_letters.json` and `marine102_R_letter.json` are the E, N and R polygons at 101.9 mm for unit tests.

## 8. The flip (Kent 2026-11-18) and its sweep

Kent, shown the MARINE word at all five Becker placements and told the flag replaces his 11-14 E corner fold on
heavy block letters: "Flip on, but make sure the MARINE strokes match the pros. These letters need to be perfect,
release another agent if needed." `lettering_columns_block_butt` is now a typed `PipelineConfig` field defaulting
True (precedent #1668); `tests/engine_2026_10_27.json` keeps it false and `tests/conftest.py` PRE_FLIP carries
`BLOCK_BUTT_2026_11_18_OFF`. Caveats are in the field's comment in `config.py`.

`python -m tools.flag_sweep --flag lettering_columns_block_butt` on the flip branch (18 tripwire placements + 26
corpus fixtures; stitch md5 as pystitch reads the written DST): **6 moved, 38 unchanged, 0 errored.** Movers: the five
Becker placements and the corpus fixture `becker_marine_logo.png` (the same art at the Studio request, 80 mm hat).

| run | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|
| becker_hat_large | 16,246 -> 15,820 | 18 | 52 -> 53 | 489.6 -> 508.6 |
| becker_lc_large | 14,802 -> 14,291 | 12 -> 13 | 26 -> 30 | 213.8 -> 236.8 |
| becker_hat_small | 10,319 -> 10,165 | 9 | 35 | 306.3 -> 304.4 |
| becker_chest_small | 10,156 -> 10,039 | 8 -> 7 | 34 -> 33 | 303.5 -> 300.6 |
| becker_beanie | 13,653 -> 13,619 | 11 -> 12 | 41 | 385.0 -> 376.8 |
| corpus becker_marine_logo (80 mm hat) | 11,373 -> 11,145 | 14 | 40 -> 41 | 350.8 -> 361.0 |

Every other placement and fixture is byte-identical. (These stitch/trim/jump counts are the DST's; section 4 and 6
used the design's own, so the jump and trim columns differ by that definition.) Pictures: section 4 and 6 folders.

Tests: the 169 test files that mention Becker or MARINE pass under the new default (1 red: the known local-only
`enthusiast_logo` golden). The two feature tests are rewritten to assert both arms:
`test_kents_pin_14_e_at_hat_large_size` keeps the apex-side fold (block_butt OFF, the PRE_FLIP arm) and asserts the
default's four straight columns; `test_on_an_m_with_an_acute_tip_is_not_read_as_an_e` keeps the M's fan and asserts the
squared end under `block_butt_scope(True)`. The ten OFF-byte pins call `letter_columns` directly, so they never saw
the config default and pass unchanged (they do not need the PRE_FLIP arm).
