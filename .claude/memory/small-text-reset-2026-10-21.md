---
name: small-text-reset-2026-10-21
description: Small text RE-SET like the pro (`small_text_cap_letter_gap_mm`, `small_text_cap_bold_scale`, OFF) -- column width was already the pro's under #1025; the gap was SPACING (letters fused). Five traps found on the way, each a downstream stage undoing the layout
metadata:
  type: project
---

2026-10-21, follow-on to [[small-bold-columns-2026-10-21]] and
[[card-v4-sewout-letter-size-2026-10-20]]; rule R4 of the pro-rules doc.

**Measured first (tools/small_text_columns.py, both files as DST, each in
its own frame):** #1024 cap 4.0 / width 1.05 + #1025 `small_bold` already
sewed Fremont's columns at the pro's width (median 0.89-0.90 vs 0.90, p10
0.70 vs 0.70-0.74). What was wrong was SPACING: condensed growth keeps the
art's gaps and buffers every stroke into them, so EAT/STAY/PLAY and 1895
sewed letter into letter (visible gap 0), and Drone's AND DRONE, 5% wider,
hit its dashes and was not grown at all (`no_room`).

**Built (OFF):** re-set each line -- letters scaled about their own centres,
laid left to right at the polygon gap that sews the asked visible gap
(`SEWN_EDGE_MM` 0.17, read off our own DST), word spaces kept, bars moved to
the middle of their room, line as wide as room allows (letters 0.8-s x), a
lone line slides at most 0.25 cap sideways. Stroke target = max(floor, 1.45
x art stroke x height scale) -- the pro's 1.36-1.60 across three jobs.

**Traps, all "a later stage undoes the layout":** (1) widening falls back
to half when it would close a counter -- the A's 0.3 mm counter left its
legs 0.6 mm and the lane sewed one as travel; now counters shrink only to
0.4 mm. (2) `regularize_text_clusters` redraws hole-free letters at the
grown cluster radius: L grew 0.37 mm a side, crossed the 5 mm `_small` line
and fused with P -- re-set letters now skip it. (3) Drone's first A is
traced in another thread, outside the cluster; it is joined at the line end.
(4) the placement took the first dy that fit at ANY dx (2.75 mm slide).
(5) `small_bold`'s 0.06 simplify cut the A's legs; a coverage retry (0.9)
recuts at 0.12 / plain construction -- it also changes #1025's EST E.

**Open:** the 5 and the S close their bays (1895 reads "1898"); the pro
draws those digits ~15% wider. Bay carving was tried and cut slits -- reverted.
Drone grows only 1.32x (room) vs the pro's 1.57, so its columns sew 0.90 vs
1.26. Curved letters cost 15-30 s each in the lane's `fold_cuts` judge.
