---
name: reset-room-floor-2026-10-25
description: W3-11 -- ProSeal's re-set columns sew under the 0.85 floor because the re-set widens RETRACED letters by an amount computed from the tagger's stale/fat stroke tag (small_text.py:759 vs :749); the pro grows a line AWAY from its nearer neighbour (past the design edge on ProSeal) and re-lays no bar
metadata:
  type: project
---

2026-10-25, W3-11, follow-on to [[small-text-floor-2026-10-24]] and
[[small-text-reset-2026-10-21]]. Doc: `docs/reset-room-2026-10-25.md`. Tools:
`tools/small_text_floor_census.py steps` (the stroke at each re-set step) and
`tools/reset_room_census.py` (the pro's line moves, room, neighbours).

**Floor (b): a mechanism bug, not the reader.** `_reset_word` widens by
`(target - min(s,f) x it["stroke"]) / 2` (`small_text.py:437`), and
`it["stroke"]` (`:759`) is the tagger's `text_cluster_stroke_mm` x 2, measured
on polygons that are NOT the `_retrace`d letters being widened (`:749-750`).
Two ways it goes stale: the stage-4 tracer polygons are fatter than a
half-threshold retrace of a coarse JPEG (ProSeal hat, 9.2 px/mm), or
`restore_small_text` already swapped in retraced polygons and kept the old tag
(`:1283-1290`; beanie, Drone). Traced over tag: 0.67-0.91 on ProSeal and Drone,
0.92-1.03 on Fremont (27 px/mm). So drawn = target - min(s,f)(tag - traced):
ProSeal sews 0.70-0.78 and Drone 0.81, where Fremont sews 0.87-0.98. The plan's
crosses equal the DST reader to 0.02. The fix belongs to `small_text.py` (the
W3-02 lane, #1085).

**The fix alone is a trap:** a what-if replay with the tag set to the traced
stroke sends the ProSeal BEANIE tagline to `no_room` (a bigger widening means a
bigger halo). It must land with a placement change.

**Room (a), his rule:** he grows the line away from its nearer neighbour (art
gap under ~2 mm). The edge facing it moves at most 0.46 mm, and 63-94% of the
growth goes the other way, past the design edge on ProSeal (baseline +0.8). He
re-lays no bar or badge (moves 0.0-0.4). Contradicting rows: the Fremont hat's
EST 1895 moved down 2.07 mm whole (he sews no rope there), and the patch's THE
(equal room both sides) moved up 0.48. Ours scales about the centre and takes
the smallest slide, so ProSeal grows UP into the bar's halo, and the beanie
stops at x1.15 (his x1.49).

**Traps:**
- `small_text_floor_census.read_element` drops a letter more than
  `max(1.5, cap)` off the art line's centre, so a MOVED line reads DROPPED.
  That was the "known misread" of Fremont's EST 1895. It now takes `reach=`.
- The census's Drone box leaves out the first A of AND (its own thread).
- On the beanie the x-extent registration scale is not the content's: his
  width includes his knockdown. Take the scale from the big word (0.9645).
- `seg_kinds` cached by `id(runs)` alone read a freed list's flags.

**Gate 1, reported only:** his ProSeal and Drone columns are 1.10-1.26. On the
traced strokes his bold factor reads 1.7-3.0, where the 1.45 candidate came
from the fat tags.
