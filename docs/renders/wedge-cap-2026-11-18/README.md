# `lettering_columns_stem_wedge_cap`, flag OFF vs ON (2026-11-18, built OFF, not flipped)

Prime-grader fault: Toat Machine's "h" stem "built from offset segments with visible steps"
(`docs/toat-machine-h-stem-diagnosis-2026-11-18.md`). The flag, `cfg.extra["lettering_columns_stem_wedge_cap"]`,
does two things to a script word's columns:

1. the THICKER column gives a junction wedge (the ink where a thinner stroke merges into it) back to a THINNER
   sibling column that already covers that ground, so the stem sews at its own width;
2. the rail points around each wedge's ends are re-spaced evenly, which clears the notch the skeleton's join kink left
   there (the grader's seam at y 35.0 and y 39.5).

**Moved: 2 of 35 runs. Pictured: 2 of 2.** 9 committed pro jobs at their own sizes plus the 26
`corpus_scorecard.FIXTURES` at the Studio request (80 mm, `left_chest`), stitch md5 of OFF against ON. The other 33
are byte-identical, the beanie and both Tires jobs included. Bare artwork is 0 -> 0 mm2 on both movers.

Every picture is ORIGINAL | BEFORE (flag OFF) | AFTER (flag ON), same size and frame (the word view stacks them).
No professional's file is rendered. Files: `<name>_overview.png` (whole design), `<name>_close1.png` (the changed
spot), `toat_machine_hat_word.png` (the word "achine", the three stacked).

## Movers, worst first, each with what changed in the plan

| design | by eye | plan change | plan's own measure (shape, OFF -> ON) |
|---|---|---|---|
| `fx_photo_logo_bridge_bar` (80 mm left chest) | mixed: the e's right bowl, a pile of crossing stitches before, is now a clean arc of parallel crosses; the long diagonal stitches that link the g to the e were already there and a few more now cross that spot | in the script word `S80a42266`, two columns trimmed from their wider side: 16 of 82 stations (max 1.93 mm) and 5 of 22 (max 0.76), rails re-spaced at the run ends; the word's runs 53 -> 61 (the walk re-cut), points 1,010 -> 995, stitches 10,877 -> 10,853 | `satin_cover` 0.9924 -> 0.9929, bare artwork 0 -> 0 mm2 |
| `toat_machine_hat` (89.5 mm hat) | better: the h is one smooth column from the top to the foot, no step, no seam, the c's tail joins it cleanly. Left as it was: the stem's top cap is still irregular (a separate pin) | in the word `S038da90f`, the h stem column (61 stations): 13 trimmed (mean over the run 0.25 mm, max 0.98), rails re-spaced at both ends of the wedge. The c-tail/arch column (63 stations) is untouched. The two one-cross notches that were 1.9 mm against 2.9-3.0 neighbours, at y 35.2 and y 38.9, are now 3.01 and 3.10. Stitches 17,155 -> 17,153 | `satin_cover` 0.9954 -> 0.9957, bare artwork 0 -> 0 mm2 |

`satin_thin_arm_stop` is neutral on this fault (it changes the stem's top cap only).

## Rule history, so the next reader does not rebuild the loose versions

- The first rule (a column gives its wedge to ANY covering sibling) moved 5 of 35, both Tires jobs and the beanie too
  (cuts up to 2.4 mm), with nothing to see, and on the h it was wrong: the thin c-tail column, taken first, gave ITS
  ground across the stem to the stem, so the stem found nothing to hand over and kept its wedge.
- The final rule: a column gives a wedge only to a sibling whose median cross is under 0.85 of its own, and each column
  reads the siblings as already capped. The Tires pair and the beanie then do not move.
- The wedge cut alone left the seam: rail points trimmed onto the slanted cross line shifted along the column and
  bunched two penetrations; they now go on the chord. The skeleton's join kink still left one rail point 0.1-0.2 mm
  off its pitch at each wedge end, so the next stage shortened that cross into a notch; the even re-spacing clears it.
- A push ramp in `stage6_satin._push_rails` (the first guess at the seam, the held push easing in over four stations)
  was built and DROPPED: the re-spacing alone clears the h, and the ramp reached every lane column, moving 18 of 35
  runs with cover losses of up to 0.046 (Gaulke's `S93841276` 1.0000 -> 0.9537, Drone's `S95978c7e` bare 1.109 -> 1.337 mm2).
