# MFab top line: the ladder's stacked bars as one wide column, built OFF (2026-11-20)

`cfg.extra["satin_junction_block"]` (OFF). **As shipped (`True`) it fixes none of the 5 top-line faults and is pile-neutral; the
variant `"short"` fixes 1 of 5 (fault 4, F4's doubled blocks) at a pile cost.** Both are built OFF for Kent's call.
Faults 1, 3, 5 and 8 are not stacked bars and are untouched; fault 6 (the A counter) is gate 1 and was left out.
Source of the five: `docs/mfab-top-line-faults-2026-11-19.md`.

## Census: the pro's satin pieces against ours (F4 block, x 43-49, y 10-14 from the top-left of the extents)

The pro is `mf4b logo hat.PES` (pystitch; nothing from the zip is committed or rendered into the repo). A piece is a run of
stitches whose consecutive steps alternate direction (a zigzag), 0.6-7 mm long.

| | columns in the block | stitch length (width) | cross direction | what it is |
|---|---|---|---|---|
| pro | **1** (42 stitches over a 7.9 mm spine) plus a 12-stitch fan at the right end | **3.5 median, 3.8 for the long ones** | 81-83 deg | one block, as wide as the art's 3.0-3.4 mm plus pull |
| ours OFF | **2** (the arm's run, 26 stitches, and the stem's run, 28, in this box) | **1.71 median**, 2.06 p90 | 96 deg | two ~1.9 mm bars offset 0.5-1.5 mm across the stitch, fanning into each other at both ends |
| ours, `"short"` | 1 wide block plus the original end fans | 1.97 median, 3.39 p90, 3.72 max | 96 deg | one block, as the pro's |

Whole F window: the pro's arm is 51 stitches at 1.9 mm (cross 118 deg), then the one 3.8 mm block of 42 stitches (cross 83 deg); his
stem is 79 stitches at 2.6 mm. He sews a junction of unequal strokes as ONE column at the wider width.

## What the flag does

`digitizer_core/column_junction.py`, called from `stage7_sequence` after `overlap_run`. A stitch of a later satin run of the shape
that has a partner in an earlier satin run (same station within 0.3 mm, cross direction within 30 deg, extents that overlap by 0.2 mm
or more and are 0.3 mm or more offset, union at most 4.4 mm) is stretched across the union of the two, never more than 0.35 mm past
the shape's polygon. A stretch of 8 or more such stitches counts and each end ramps in over 16 stitches. The earlier bar's partner
stitches become a 2 mm running path (the `column_overlap` construction), so the needle path stays unbroken, and only where the widened
stitch reaches the union to within 0.35 mm (else the thread under it would be bare). No satin floor, pull or cover figure is read or changed.

## Pile: found, fixed for `True`, and the price of `"short"`

First build (ramp 4): at F4b the share of the covered area 3 or more deep went 0.51 to 0.71. Causes found: widened stitches over
earlier-bar stitches that were NOT removed (partners in a lap under 3 stitches), and ramps too short. Measured on the captured
stage-7 runs (0.4 mm lines, 20 px/mm, satin only):

| window | OFF | first build | `True` as shipped | `"short"` |
|---|---|---|---|---|
| F4 (x 41.5-46.5, y 9-14): 3+ deep, max layers | 0.43, 13 | 0.57, 13 | 0.44, 13 | 0.51, 13 |
| F4b (x 44.5-49.5, y 10-15) | 0.51, 10 | 0.71, 8 | 0.51, 10 | 0.54, 8 |
| F4 whole (x 41-52, y 8.5-15) | 0.42, 13 | 0.59, 13 | 0.42, 13 | 0.45, 13 |

`True` is pile-neutral because it does not touch F4: the F4 stretch is about 20 stitches, shorter than two 16-stitch ramps, so no
stitch there reaches the whole union and none of the earlier bar may go. `"short"` ramps a short stretch over a third of its length,
merges F4 into one block (rendered in the pack), and pays +0.08 / +0.03 / +0.03. I could not merge F4 and keep the pile at OFF: with the
merge, the extra 3-deep area (1.0 mm2 net) sits along the arm's diagonal and the block's left end (x 37.7-45.8), where the new wide
stitch lies over the fan of the neighbouring run; every ramp from 1 to 24 stitches and every miss tolerance tried leaves it at +0.05 to +0.09.

What `True` does change in MFab is the B's left stem, which two bars sew in two passes: ON sews it as one pass (80 mm: -32 to -38
stitches; 104.9 mm: -59), same trims.

## Why faults 3, 5 and 8 are the next fix, and are not this

They do not change OFF to ON. In each the two satin pieces meet at an ANGLE, so no partner passes the 30 deg cross-direction test:
- **3 (35, 6)**: two satin runs meet at a corner and fan; their cross directions differ by the corner's angle.
- **5 (36, 17)**: one satin stitch of the F stem bridges a 1.65 mm gap where the dash's bars join (a gap, not an overlap).
- **8 (88.5, 18.5)**: the slot's bar meets the leg's fan wedge, again a corner.

They are corner fans and wedges. The lead for the next fix: the pro's F arm is groups of 5-6 stitches 2.5-3.5 mm long at about
20 deg that turn the corner in one piece, where ours fans two runs into a point. A corner builder belongs beside this one in
`stage7_sequence`, on the same earlier / later run pair, with an angle test in place of the parallel test. Fault 1 (the M notch) is the black
mark plus the white under it, also a corner.

## Regression (26 `corpus_scorecard` FIXTURES, `commons_lettering/*.png`, `testdata/art/logo_*.png` at 80 mm left_chest and hat_front, and MFab hat at 104.9; OFF against `True`)

`tools/flip_guard.py` was not on main. 47 placements. Only the MFab logos move; every other placement is byte-identical.

| placement | OFF to ON stitches | trims | verdict (I looked at the 104.9 hat, the 80 hat of `mfab_hat` and the 80 left_chest of `mfab_lc`; the other two share the geometry) |
|---|---|---|---|
| `logo_mfab_hat` 104.9 hat | 20,516 to 20,457 | 26 / 26 | BETTER (small): B stem one pass, F4 unchanged |
| `logo_mfab_hat` 80 hat / left_chest | 13,646 to 13,608 / 13,647 to 13,609 | same | BETTER (small), same stem |
| `logo_mfab_lc` 80 hat / left_chest | 13,622 to 13,590 / 13,423 to 13,391 | same | BETTER (small), same stem |
| the other 40 | identical | identical | SAME |

An earlier build (before the partner and polygon limits) moved Becker, K Line, N-Sync and the Toat beanie; on the beanie it left a
bare spike where a 3.4 mm earlier-bar stitch was removed under a half-widened one. The limits above fix that, and those placements are
now identical to OFF.
