---
name: column-corner-folds-2026-10-23
description: The pro folds ONE satin column round every L corner (E arm into stem, L foot, a P's stem into its bowl, an arm tip into its serif) and cuts only where two concave corners face each other (T junctions); read on 57 corners of four DSTs. Built as `lettering_columns_corner_fold` (OFF): a post-pass over the cut's columns that drops the corner square's crosses and joins the two legs with crosses from the inside corner round the apex. Layout, ON-eligible from renders.
metadata:
  type: project
---

2026-10-23, lane `pull-comp-by-stroke-61868c` after #1051. Renders and the
census: `docs/renders/column-corner-folds-2026-10-23/` (README, table.md,
six corner crops before | after | pro, one needle-path sheet per word).

**How the pro turns a corner** (`tools/pro_corner_folds.py` over his hat
DSTs: Fremont 25 folds, Drone 13, MFab 18, Proseal 1): the column keeps
going. The crosses pivot on the INSIDE corner, their outer ends walk the
outline round the apex at the satin pitch (outer arc 2.2-4.2 mm, two sides
of the corner square), the inner ends spread 0.4-0.8 mm along the crosses
(his short stitching; his stagger is progressive, ours alternates), and the
two legs' sewn widths are 1.0-1.3x of each other (one 1.7, a serif). He
folds the slab-serif Fremont E's arm tip into its serif, and the P's stem
into its bowl top. He CUTS where two concave corners face each other -- a T
junction, a slab serif's root, an E's middle arm -- exactly `find_cuts`'
"through" pairs. So the rule is geometric, not a width or angle rule: one
reflex corner + an apex across it = fold; two facing reflex corners = cut.

**What ours did:** every L corner was a "mitre" cut (two straight columns
each fanning to the apex, a butt and a travel), an "ext" (the stem runs
through, the arm butts square) or an E's "slot" line. 156 columns / 242
butts over 38 letters to his 134 / 195 (`lettering-5-10mm-band-2026-10-23`).

**Built:** `outline_cut._fold_corners` runs AFTER the cut and
`_absorb_serifs`, under a contextvar like `small_bold`. At each lone reflex
corner (turn 35-110, not a through pair, exactly two column pieces filling
a 0.3 W disc round it) `_fold_pair` turns each column to end at the corner,
drops the stations whose either end has reached the corner (refusing a
column that runs on PAST the apex -- a stem the arm butts), checks the legs'
widths within 1.6x, and joins them with crosses from the corner to the
outline arc that passes the apex, one per pitch. Kind `"folded"`; the walk
gets two fixes for such letters only: an arm butting a folded column does
not start the walk (`prefer`), and `_span_graph` merges two ends into one
node only through the letter (the radius alone fused an E's top and middle
arm TIPS across the slot).

**Measured (harness, same reader on ours and his):** see the README table.
Drone PRECISION 29 -> 18 columns (pro 24), in-letter jumps 3 -> 0; Fremont
67 -> 57 (pro 63); MFab 32 -> 24; Proseal 18 -> 15; 36 letters 146 -> 114
columns, butts 26 -> 22, gaps 2 -> 1 (pro 141 / 65 / 0 by this reader,
whose butt excludes an end meeting an END). The legs' crosses are OFF's,
station for station. The E's routed under-paths grow (the walk must end at
the stem for the next letter), which the per-letter `travel_mm` shows and
"travel on cloth" does not. A chamfered apex (Drone's C) sits short of the
corner square: the trim limit is the OTHER column's far cross, not the apex.

**Traps:** a mitre end's fan pivots a hair SHORT of the corner on the inside
and reaches the apex on the outside -- trim by either end, not the inner
one. A butting column's first cross sits half a pitch off its cut: "reaches
the corner" must allow a pitch. `_ring_arc`'s `avoid` needs the avoided
point ON the ring; a P's corner is on the counter ring while the apex is on
the exterior -- pick the arc by the apex instead. A band letters file holds
the design's OTHER letters too (MFab's 18 mm MFAB): filter before sewing.
`tasklist` hangs in this shell; `Get-CimInstance Win32_Process` works.

**Why:** the construction gap at 5-10 mm is corners, not width. **How to
apply:** render both files' needle paths (`column_harness --job X --fold`)
before touching a corner rule; the pro's rule is read off the corner's
topology, so look for facing corners, not angles.

Related: [[lettering-5-10mm-band-2026-10-23]], [[narrow-columns-2026-10-23]],
[[lettering-architecture-2026-10-07]], [[envelope-junction-escapes-2026-09-30]],
[[layout-judged-in-preview-2026-10-22]].
