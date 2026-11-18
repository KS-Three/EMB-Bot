# Toat Beanie: the e of "Machine" and its eye (2026-11-18)

**Verdict: no fix built. The eye is as open as thread at 83 mm allows, and the
professional's file closes it entirely.** Prime-grader scorecard 2026-11-17,
`L_toat_beanie`, pin (69.0, 32.5) mm, "the loop of the e is filled by a clumsy cross
patch so its counter is nearly closed".

Picture (original | ours, same patch, current main `8051f118`):
[`renders/toat-e-eye-2026-11-18/original_vs_ours_B3.png`](renders/toat-e-eye-2026-11-18/original_vs_ours_B3.png)
(the e is the top right of the tile). No picture of the professional's file is
committed (`tests/test_no_new_pro_renders`); what it shows is stated below from a
local render.

## What is sewn

The whole "ne" is two satin runs of one shape (`S4de77012`): run 152 (the n and the
e's entry and loop) and run 155 (the e's bottom curve and the swash), each with an
underlay. No junction patch, no "uncovered artwork" cover patch and no fill is laid
across the eye: the 305 ground-fill stitches near it belong to the white fill, and
the black there is those two satin runs only. The "cross patch" the grader saw at
about (66-68, 31-34) is the start of run 155, a short horizontal-stitched hook where
the bottom curve turns up the loop's left side, overlapping the end of run 152. It
sits at the eye's lower-left end, not across it.

## The eye, measured (dark-thread mask at 30 px/mm, art fitted by the grader's register)

| | eye area | length x width |
|---|---|---|
| art | 4.8 mm2 | 5.8 x 1.08 mm |
| ours | 2.3 mm2 (47% of the art's) | 4.5 x 0.73 mm |
| professional's file (local render, centroid-aligned) | below 0.3 mm2: closed to a sliver | none found |

Ours is half-open and reads as an eye; the professional's thread closes it. The loss
from 1.08 to 0.73 mm is the satin's own spread on both sides of a 1 mm slit (about
0.17 mm a side), and the 1.3 mm lost in length is the hook's overlap. Narrowing that
spread is pull/push compensation, which only a sew-out settles (ROADMAP gate 1), so
this stops here.

## The two flags that went ON 11-17

`satin_thin_arm_stop` and `lettering_columns_cover_hops`: the stitches in x 62-76,
y 26-38 mm are identical with each forced OFF, and with both OFF. Neither touched
this spot (the design's stitch totals move, 17293 vs 17265-17451, elsewhere).

## Not done

The hook's overlap with run 152 (the lumpy lower-left of the e) is real and could be
a later clean-up of how a stroke's start meets the previous column; it is not the
counter fault the pin names and no flag was built for it.
