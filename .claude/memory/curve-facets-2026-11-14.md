---
name: curve-facets-2026-11-14
description: Kent's 18 facet pins — lettering's chords are made by the Column lane's own simplify (max(0.12, W/16)), not stage 4; `curve_chord_mm` (lane) + `curve_chord_stage4` built OFF; Tires #0 cured by the stage-4 site, the 15 lettering pins not measurably
metadata:
  type: project
---

Director's brief 2026-11-14 ("exactly like the pros"): the 18 (b) pins of
[[jag-source-2026-11-13]], a clean curve sewn as chords. Doc:
`docs/curve-facets-2026-11-14.md`; tool `digitizer/tools/curve_facets.py`
(`stages`, `pins`, `sheets`); sheets in the primary's
`eye_pairs_out/facets-1114/sheets/`.

**Where the chords come from.** On lettering (15 of 18: and_pizza 14,
dot_music 1) the satin's rails come from `outline_cut._letter_columns`, which
re-simplifies each letter at max(0.12 mm, W/16): and_pizza's bowls reach the
rails as 2.0-2.6 mm chords, p95 turn 41.5 deg, 0.25 mm off the stage-4
polygon. Stage 4's refinement (18 deg p95) never reaches a lettering rail,
which is why `outline_redraw_native` and a stage-4 densify move the polygon
and not the bowls' satin. Fill/satin-tier edges under 20 px/mm keep stage 4's
gated 1-3 mm chords (Tires #0, Gaulke #3).

**The pro**, Bridge and Gaulke: one satin end every 0.36-0.41 mm on a curve,
ends on a circle to 0.02-0.03 mm RMS (his file's 0.1 mm quantization floor).
Read OUR needle points from the plan's float runs: the 0.1 mm design file
alone reads as 14-18 deg turns at 0.4 mm spacing.

**Built (both OFF):** `curve_chord_mm` (0.4 measured) densifies each lane
piece's OUTER outline before its rails are built (cuts unchanged), and
`curve_chord_stage4` does stage 4's rings. Counters are excluded: densified,
stage 7's counter clearance re-cut and_pizza's "p" into a wedge.

**Measured:** the lane flag is not measurable at the 15 lettering pins
(turn max better 7, worse 8). It sews the "a" unsplit (one over-long
junction cross had tripped the split comb). The stage-4 flag cures Tires #0
(turn max 23 -> 8 deg) but moves the lane's cuts on lettering.

**How to apply:** don't propose another polygon fix for lettering bowls. The
satin's end jitter (6 deg std an end, both arms) is the lever, in the
stations. A stage-4 densify safe to flip must skip text-tagged regions: a
post-pass after text tagging.
