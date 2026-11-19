# MFab top line: the nine prime-grader faults sorted, and one flag built OFF (2026-11-19)

**Not a flip candidate: `satin_overlap_run` leaves the picture identical to OFF.** It is built OFF and stays OFF.

Scorecard `docs/prime-grader/scorecard-2026-11-18.md`, `L_mfab_hat` (105.3 x 40.5 mm, hat_front). The
small AND WELDING LLC line is `docs/mfab-bottom-line-2026-11-18.md` (#1673) and is not reopened.
Measured on main `e4b0428e`: `mfab_hat` at 104.9 mm, `pro_pair.digitize`, 20,564 stitches, 25 trims.

**Conclusion (2026-11-19, after reading the pro file).** The first version of this note, and my message to the director,
said the pro's stems are about twice as dense as ours (0.2 mm pitch, 3+ deep over 0.81 of the area against 0.35). **That is
withdrawn: it was a measurement error.** The 0.2 mm I read was the step between stitch MIDPOINTS (half the same-side pitch, ours is
0.2 too), and the 0.81 / 0.35 shares came from windows that held different amounts of letter. Like for like, the pro's per-pass density
is about ours. The B stem is sewn in two passes by both of us (the pro by design; ours because the ladder re-sews it, which
`satin_overlap_run` thins). What differs at the junctions is the top of the stack: at F4 ours reaches 15 layers (mean 4.8) where his
reaches 9 (mean 3.6), at F3 they match, and F8 cannot be compared (he has 2.8 mm2 of thread within 2.5 mm of our F8, ours 10.4).
So this is **not** a satin-density (gate 1) question on this evidence, and the junction construction is still open. Any junction
build needs a satin-piece census of his file first (his runs are long, 6 needle-down runs for all the white; his F arm is groups of 5-6
stitches 2.5-3.5 mm long at about 20 degrees, which a chain heuristic did not segment).

| window | | mean layers | 3+ deep | max layers | covered mm2 |
|---|---|---|---|---|---|
| B left stem (clean, x 78.3-80.3, y 12-21) | pro | 5.3 | 82% | 20 | 18.0 |
| | ours | 4.9 | 94% | 8 | 17.3 |
| M left stem (x 3.4-5.3, y 11-19) | pro | 3.4 | 66% | 7 | 5.8 (window misses part of his stem) |
| | ours | 2.5 | 39% | 5 | 14.7 |
| F3 junction (r 2.5 at 37, 7.5) | pro | 4.5 | 69% | 13 | 8.9 |
| | ours | 4.0 | 67% | 12 | 12.9 |
| F4 junction (r 2.5 at 44, 11.5) | pro | 3.6 | 82% | 9 | 19.6 |
| | ours | 4.8 | 79% | 15 | 11.5 |
| F5 junction (r 2.5 at 34.5, 16.5) | pro | 4.7 | 80% | 15 | 17.3 |
| | ours | 4.0 | 64% | 14 | 14.2 |
| F8 junction (r 2.5 at 88, 18.5) | pro | 2.7 | 38% | 6 | 2.8 (not comparable) |
| | ours | 5.7 | 94% | 14 | 10.4 |

Layers = 0.4 mm lines over the stitches at 20 px/mm, pro read with pystitch from `mf4b logo hat.PES` (104.9 x 40.2 mm), both frames from the
top-left of the stitch extents (they can be 0.3-0.5 mm apart). Numbers only; nothing from the zip is rendered or committed. `mfab_lc` was not measured.

**One dense pass or two?** Counted by the stitches that cross a stem's centreline, by pass (a run of consecutive stitches), per mm of stem:
- B left stem, centreline x 79.3, y 10-23: **pro** 128 crossings = 9.8 per mm, in passes of 49 (7.2 per mm, toward +y), 13 (5.6 per mm, +y) and 31 (5.3 per mm, -y) crossings, plus small ones;
  **ours** 133 = 10.2 per mm, in two passes of 65 (5.1 per mm), one up and one down.
- M left stem: **pro** 36 crossings over 5.7 mm (6.4 per mm, one pass up) plus 10 more (2.2 per mm); **ours** 56 over 10.9 mm (5.2 per mm, one pass).
So his pitch is **two passes at about 5-7 crossings per mm each, i.e. a same-side pitch of 0.3-0.4 mm**, not one pass at 0.2 mm; ours is 5.1-5.2 per mm per pass
(0.4 mm same-side pitch). What to sew: if density is ever tried, it is one more pass or a 0.3 mm pitch, tried on cloth first (gate 1).

**What sews the top line.** The white letters are one enclosed-white field (`S1a1cc475`, `sew_enclosed_white: field`)
sewn by the ordinary satin ladder, not the Column lane: one satin run per walk (M 563 points, F 252 + 310, A 426,
B 532), thread 0015. The black notch and counters are small black regions sewn after. The Column lane
only sews the black small letters.

"Pile" = share of the white thread's covered area that is covered 3 or more deep (0.4 mm lines, 20 px/mm); a clean
stem is 35%, with at most 5 layers.

| # | mm | grader's words | plan and measurement | sort |
|---|---|---|---|---|
| 1 | 16, 18.5 | notch under the M lumpy | black off-line mark `Sb189ad6d` (#1656), fill tier, 12.39 mm2 against the art notch 12.1 mm2, 2.6 mm wide; sits where the white sews fill and satin runs, up to 13 layers | the black is thread-width plus round-cap render; the white under it is the junction construction of 3 and 4 |
| 2 | 16, 10 | crossing stitches at the V | pile 38% against 35% clean | grader misread |
| 3 | 35, 6 | fanning, piling at the upright / F bar | pile 53%, 12 layers; two satin runs meet at a corner and fan | real, junction construction |
| 4 | 45, 12.5 | doubled blocks, stepped joint | satin 252 (bar) and 310 (stem) stack two 1.9 mm bars 0.5 mm apart, 3.3 mm of block; the art's block there is about 3.0 mm; pile 61%, 15 layers | real, junction construction |
| 5 | 36, 17 | stray diagonal in the dash counter | the run is one satin stitch of the F stem (36.11, 16.26) from (34.28, 17.91), 2.46 mm, bridging a 1.65 mm gap in the stem where the dash's bars join; no travel crosses the counter (the 4-point travel at y 18.0 lies in the bar) | junction construction, not a stray; `lettering_columns_connectors_buried` leaves MFab byte-identical |
| 6 | 70, 16 | A triangle crowded and ragged | fill, 143 stitches; the 5.0 mm satin ceiling refuses `counter_fan_satin` at 104.9 mm; region 17.9 mm2 against the art 24.1 | gate 1, sew-out row 16 |
| 7 | 91, 11.5 | B upper slot a short lumpy sausage | region 12.39 mm2 against art 12.9; satin width 1.48 against 1.56 | faithful: thread width and the round-capped 11-18 kit |
| 8 | 89, 18.5 | B lower slot's left end lumpy | the slot's bar meets the leg's fan wedge | real, junction construction |
| 9 | 100, 14.5 | B right outline kinks at the notch | pile equals a clean stem; the art itself has a 0.5 mm notch there | grader misread |

So the top line is mostly faithful: three misreads/limits (2, 7, 9), one gate-1 (6), and the rest (1, 3, 4, 5, 8) one
cause, how the satin ladder sews a corner where strokes of different widths meet: two bars stacked and fanned where the
art has one block. That is **not** fixed here.

## What was built: `cfg.extra["satin_overlap_run"]` (OFF)

`digitizer_core/column_overlap.py`, called from `stage7_sequence` right after `stitch_one`. The satin ladder re-sews
stretches of a stroke that a later walk of the same shape covers (MFab's F diagonal: 35 stitches over 6.5 mm; the B's left
stem 86 stitches over 17 mm). A satin stitch that lies wholly inside the cover of satin sewn **after** it adds thread
height and no cover. Such a stretch of 8 or more stitches becomes a 2 mm-step running path through the stitches'
midpoints. The list is walked last run first and only satin that is still sewn counts as cover, so two stretches cannot
remove each other. No satin floor, pull compensation or cover tolerance is read; the half-thread 0.2 mm is the figure
`columns.satin_cover` already uses.

| arm | OFF | ON | bare after (raster, 0.4 mm lines) |
|---|---|---|---|
| `mfab_hat` 104.9 | 20,564 st / 25 trims | 20,438 / 25 | 1.28 mm2 of 1,137, speckle only (largest piece 0.02 mm2) |
| `mfab_lc` 97 | 17,726 / 20 | 17,517 / 20 | 1.7 mm2 of 1,050, speckle only |
| `mfab_hat` 30 | 2,996 / 12 | 2,966 / 12 | 0.19 mm2, speckle only |

Pile at the B stem 18.2 -> 7.1 mm2 (3 deep or more); at the F diagonal 21.1 -> 19.5; whole top line 890 -> 867.
**The picture does not change.** The layer that was hidden is the one dropped, so the top layer is the same stitches:
`docs/renders/satin-overlap-run-2026-11-19/` (ORIGINAL | BEFORE | AFTER, both placements, whole and close-ups) shows
the same F, the same stepped joint. It saves 126-209 stitches of hidden thread and nothing the grader sees, so it is
**not a candidate to flip** on the grader's evidence and stays OFF. The full `tools.flag_sweep` was not run for the
same reason; the three MFab arms above were.

Pictures: the original at 20 and 40 px/mm is the committed `testdata/art/logo_mfab_*.png`; no professional's file is
rendered. The art in the close-ups is cropped from its own ink box and sits about 0.3 mm off our frame.

## Next, if someone takes the junction

Faults 1, 3, 4, 5, 8 share one construction: the ladder sews a thick junction (art 3.0 mm) as two 1.9 mm bars
offset 0.5 mm, with fan wedges. A fix would sew the junction as one satin block (or butt the second bar to the first's
edge) as `lettering_columns_block_butt` does in the Column lane for Becker's MARINE; it is a satin-tier change in
`stage6_satin`, and it needs the dash/F corner (36, 17) and the B's left end (89, 18.5) in the same pass.
