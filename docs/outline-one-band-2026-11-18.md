# `outline_one_band` — one border band, a column per stem (2026-11-18)

Built OFF. Prime-grader fault `L_becker_hat_large`, pin x 21.0 y 8.5 mm (the outline
between the B and the E) and the E/R join near x 78-81, y 4-5; Kent pinned this border
on 11-10 and 11-14 ("The border around this logo should be smooth", "notice how the pro
makes a nice corner with the thread and continues the stitch to the right"). Follows
`outline_loop_split_shared` (#1657, OFF), which butted the two face loops at the line the
faces share and left a seam down each stem. The director ruled that one a record, not a
flip, and asked for the pro's construction.

## What the professional's Becker file does (numbers and words only)

Source: his hat PES, read 2026-11-18 with `design_from_file` and `tools/study_pro.py`
(y runs UP in the file: the renderer flips it; a window read without the flip lands on the
bottom of MARINE, which is how an earlier note went wrong). 12,356 stitches, 5 colour
blocks, 57 trims; `study_pro`: 7 satin runs, width median 3.8 mm (max 4.8), density
0.40 mm.

* BECKER is blocks 1-4. Blocks 1 and 3 (B, E, C and K, E, R) are ONE tatami fill (rows
  about 3.5 mm, angle 22 deg) under each group's whole silhouette, stems and letters
  together: no fill boundary at a stem.
* Blocks 2 and 4 are the satin on top. At the B/E dip (block 2, x 14-30, y 0-26 mm in our
  frame):
  1. ONE border column along the top (94 stitch pairs plus a thin second pass, x 14.1-29.9,
     y 4.1-7.2, 3.1 mm tall). It crosses the V at x about 21 as one band. Cross angle 79 deg
     at the left end to 93 deg at the right: the crosses stay near-square to the band, no
     fan, no mitre.
  2. A separate STEM column (122 pairs, x 20.4-22.9, y 7.2-26.0, 19 mm long, cross length
     median 3.4 mm). It starts exactly on the band's lower edge (y 7.2), its first crosses
     at 80 deg (following the band), square to the stem (173 deg) as it runs down.
  3. Order: the stem first, then the top band over the stem's top end.

## Ours before

`border_from_outline` (stage 7) sews an outline as one satin loop per face hole
(`stage6_border.keyline_runs`), crosses at one width (2.57 mm here) and never into a hole.
The outline of BECKER is one region (5 face holes). Where two faces stand under two loop
widths apart the stem between them (2.7-3.0 mm wide at the pin, faithful to the art) is
covered by both loops: two columns side by side, both fanning into the V.

## The build

`digitizer_core/outline_band.py`, hooked in stage 7 before the loops, behind
`cfg.outline_one_band` (default OFF, OFF byte-identical on all 35 runs). Gate: the band
has two or more holes and at least one stem; otherwise the old loops sew.

* STEM = a piece of band where the distance to one face plus the distance to the other
  is under two loop widths (across a stem of gap g the sum is g everywhere; wide black
  between letters reads more), outside the zone the outer loop sews, at least two of its
  own widths long. Each is sewn by the existing satin tier (`satin_shape`).
* ONE LOOP on the band's outer ring (`keyline_runs` on the exterior ring: crosses cast
  inward at the band width, cut where they reach a hole), sewn LAST so it covers each
  stem's top, as the pro does.
* What neither reaches near a hole keeps that hole's loop, its crosses cut at the zone and
  the stems, run first; the walks between its arcs go under the outer loop
  (`_centre_walk`), else the needle lifts.
* No new constant: the width is the outline's own (`outline_holes`), "stem" is a
  geometric test (the two-widths sum, two of its own widths long), the walk bound is the one
  `_bury_walks` keeps.

## Evidence

See `docs/renders/outline-one-band-2026-11-18/README.md`.
