# `script_strokes_drawn_width` (built OFF 2026-10-27)

Kent, 2026-10-27, on the Bridge width numbers with pull counted: **"Build it OFF
(Recommended)"** (his first ruling, on the numbers before pull, was "Record it, no
build (Recommended)").

What it does: with `script_strokes` ON a cross reaches the traced polygon plus the
pull. On a word that lays more of its thread twice than the pro does anywhere
(`CROWD_WORD_SHARE`, 10.5 %), a cross side whose thread would run more than
`CROWD_DEPTH_MM` (1.0 mm, the pro's median overlap depth) into another stroke's stops
at the art's drawn half-width, with the pull on top as today. Patches are only laid
where no column's thread, pull included, reaches. No width or pull constant moves.

Pictures are ours only: **OFF** = main (`script_strokes` ON with #1135's flow) |
**ON** = this flag. Planned from one cached trace per job (engine of this branch),
rendered by `stitchviz`. The pro's numbers are below; his files are not rendered here.

- `bridge_hat_off_on.jpg`, `bridge_lc_off_on.jpg` (25 / 22 px/mm), `crops40_*.jpg`
  (40 px/mm, the "dge" end).
- `tires_off_on.jpg`: identical. Tires is under the gate and its DST is byte-identical.
- `machine_hat_off_on.jpg`: To a T's "Machine".

## Measured (read off the DSTs, ours and the pro's alike)

Thread laid twice = the summed pairwise overlap of the word's satin chains
(`tools/script_flow.py`'s columns, half a thread wide) over their summed area.
Deepest = the widest circle inside any piece two columns share. In columns =
`tools/satin_columns.py`'s share of the word block's penetrations. Bare = the word's
traced polygon that no needle-down segment (half a thread each side) covers.

| word | arm | laid twice | deepest mm | in columns | bare mm² | split crosses | word stitches / trims | design stitches / trims |
|---|---|---|---|---|---|---|---|---|
| Bridge hat | main | 24.9 % | 2.33 | 83.0 % | 1.30 | 0.9 % | 694 / 1 | 9,419 / 30 |
| | **ON** | **19.3 %** | **1.89** | 78.5 % | 2.64 | 0 % | 701 / 1 | 9,433 / 30 |
| | pro | 10.5 % | 1.26 | 90.7 % | | | | |
| Bridge LC | main | 18.5 % | 2.63 | 76.1 % | 6.76 | 3.0 % | 888 / 0 | 14,861 / 38 |
| | **ON** | **15.4 %** | **1.82** | 81.1 % | 7.66 | 0 % | 837 / 1 | 14,825 / 39 |
| | pro | 7.9 % | 1.37 | 91.6 % | | | | |
| Tires | main = ON | 6.8 % | 4.91 | 6.6 % | 5.39 | 67.4 % | 2,854 / 1 | 4,624 / 6 |
| | pro | 3.1 % | 2.56 | 98.5 % | | | | |
| To a T "Machine" | main | 13.5 % | 4.44 | 77.0 % | 2.23 | 0 % | 1,744 / 1 | 22,821 / 58 |
| | **ON** | **11.5 %** | 4.44 | 78.7 % | 2.26 | 0 % | 1,658 / 1 | 22,722 / 59 |
| | pro | 3.4 % | 1.48 | 94.7 % | | | | |

Earlier arms on the same reader: `script_strokes` OFF laid 63.5 / 74.7 / 20.5 / 39.6 %
twice (Bridge hat / LC / Tires / Machine); ON as #1119 merged laid 28.3 / 25.9 / 10.5 /
16.0 %.

**Counters** the trace closed: 0.01 → 0.09 mm² open on Bridge hat (of 2.83), 0 → 0.15
on LC (of 1.41).

**Costs.** Bare polygon +1.3 mm² on Bridge hat and +0.9 on LC. It shows as small
white specks at a few joins in the renders. Bridge hat's in-columns share drops
4.5 points.

**Tires, held off.** Tires' strokes do not crowd: at 6.7 % on the plan they sit
under the gate. With the cut forced on, it left 8.8 mm² more of the word bare
(5.39 → 14.16) and laid no less thread twice (6.8 → 7.1 %). Its split satin is
unchanged: the crosses are ~5.13 mm, past `SPLIT_SATIN_ABOVE_MM` 5.0, and 6.6 % of
its penetrations read as columns against the pro's 98.5 %. Ending them at the drawn
width everywhere (4.93 mm) would land under the ceiling, but it bares 26 mm² of the
strokes. Not built.

**Plan-level sweeps** (the word alone, scratch): the depth between 0.2 and 1.3 mm
moves the strokes' overlap by under 1.5 points. The patch test against the pulled
thread cut Bridge hat's patches from 9 to 2. Against the crosses alone it re-laid the
gap the pull already covers, and the read-off overlap rose (24.9 → 27.8 %).
