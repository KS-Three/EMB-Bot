---
name: round-dot-ring-2026-11-18
description: "Prime grader Tires pins 11-18: the i dot is tatami row ends; round_dot_ring (ON, Kent 'Flip ON (Recommended)') rings round dots from 4 mm; the stroke end at (21.5, 37) is NOT cured"
metadata:
  type: project
---

**Dot.** Tires' i dot (5.7 mm) is over the hat satin ceiling (5.0), sews tatami; the row ends make flat top and
bottom and a jutting last stitch. `round_dot_ring`: `border_by_size` reads a round no-hole solid
(circularity >= 0.9) from 4 mm (`machine.ROUND_DOT_MIN_DIM_MM`) so it gets the 1.5 mm ring. 1 of 35 runs
moves (Tires, +106 stitches, trims/jumps 7/7, the T bar re-linked and sewn last). Kent flipped ON 11-18
over the written caveat that a 1.5 mm ring on a 5.7 mm dot is untested on cloth (gate 1). PR #1655,
pictures `docs/renders/round-dot-ring-2026-11-18/`.

**Stroke end (21.5, 37.0): not cured.** Polygon end is within 0.25 mm of a circle (rms 0.08) and the thread
covers all the art; the slant is the last column cross. Tried and reverted: parallel cap crosses (no change),
crosses square to the end's axis (no change, a gap), circle-fit polygon cap (worse, a straight cut);
`curve_chord_stage4` also leaves it. The pro's end at this size was not examined.

**How to apply:** do not retry those three; a fix needs the column's end face (`columns.py` terminal faces),
not the polygon or cross direction. Related: [[prime-grader-2026-11-17]].
