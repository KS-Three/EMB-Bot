# `lettering_columns_stem_wedge_cap`, flag OFF vs ON (2026-11-18, built OFF, not flipped)

Prime-grader fault: Toat Machine's "h" stem "built from offset segments with visible steps"
(`docs/toat-machine-h-stem-diagnosis-2026-11-18.md`). The flag, `cfg.extra["lettering_columns_stem_wedge_cap"]`,
lets a script word's THICKER column give back a junction wedge (the ink where a thinner stroke merges into it)
to a THINNER sibling column that already covers that ground, so the stem sews at its own width.

**Moved: 2 of 35 runs. Pictured: 2 of 2.** 9 committed pro jobs at their own sizes plus the 26
`corpus_scorecard.FIXTURES` at the Studio request (80 mm, `left_chest`), stitch md5 of OFF against ON.
The other 33 are byte-identical. None is worse by eye; one improves; one shows no visible change.

Every picture is ORIGINAL | BEFORE (flag OFF) | AFTER (flag ON), same size and frame. No professional's file is
rendered. Files: `<name>_overview.png` (whole design), `<name>_close1.png` (the changed spot).

## Movers, worst first, each with what changed in the plan

| design | by eye | plan change | plan's own measure (shape, OFF -> ON) |
|---|---|---|---|
| `fx_photo_logo_bridge_bar` (80 mm left chest) | no visible change | in the script word `S80a42266`, two columns trimmed from their wider side: 14 of 82 stations (mean 1.56 mm, max 1.92) and 5 of 22 (mean 0.66, max 0.83); each trimmed station's removed ink lies inside a thinner sibling column's piece. Stitch count 10,877 both ways (points moved, none added or dropped) | `satin_cover` 0.9924 -> 0.9924, bare artwork 0 -> 0 mm2 |
| `toat_machine_hat` (89.5 mm hat) | better, not complete | in the word `S038da90f`, the h stem column (61 stations): 13 trimmed, mean 0.71 mm, max 0.99. Cross width over the junction ran 3.1-3.4 against 2.3-2.5 either side with a step at each end; now 2.5-2.7 across it. The c-tail/arch column (63 stations) is untouched. Stitches 17,262 -> 17,260 | `satin_cover` 0.9954 -> 0.9955, bare artwork 0 -> 0 mm2 |

**The hat's h** (`toat_machine_hat_close1.png`): the stem is now one smooth column from top to the junction. The
wider middle chunk and the wedge on the right edge are gone and the left edge runs straight. What is NOT gone: a
white seam low on the stem, where the lower end of the c-tail column meets it, and a small notch beside the c's tail.
`satin_thin_arm_stop` is neutral on this fault (it changes the stem's top cap only).

## Rule history, so the next reader does not rebuild the loose versions

The first rule (a column gives its wedge to ANY covering sibling) moved 5 of 35: both Tires jobs and the Toat
beanie as well, with cuts up to 2.4 mm on Tires' heavy letters. By eye there was nothing to see on them, and on the h
it was wrong: the thin c-tail column, taken first, gave ITS ground across the stem to the stem, so the stem found
nothing to hand over and kept its wedge. The final rule: a column gives a wedge only to a sibling whose median cross
is under 0.85 of its own, and each column reads the siblings as already capped. The Tires pair and the beanie then
do not move (byte-identical). The beanie answers option C: the final rule does not fire on it (byte-identical), so
the flag does nothing there at its size. Why (a different wedge shape, or a sibling that is not thinner) was not traced.
