# Native-read corners: where the Becker reversals start (2026-10-11)

Kent's ruling today: leave `subpixel_edges_min_px_per_mm` unset and fix the
Becker outline reversals where they start, in the native-resolution edge
read. This is that fix, built OFF as `cfg.subpixel_corner_runs`.

Evidence and scripts: `docs/renders/native-read-corners-2026-10-11/`.
Follows #826 (`docs/subpixel-res-gate-2026-10-11.md`) and #818
(`docs/tracer-head-to-head-2026-10-10.md` §3). A reversal is a vertex that
turns back more than 120 degrees. Right-angle turns (60 to 120 degrees) per
100 mm stand in for the staircase, which the reversal count cannot see.

## Diagnosis

The 129 reversal vertices on Becker at 80 mm (1.81 px/mm, upscale x4) were
traced back to the read point under each one and its flags
(`scripts/worst_reversals.py`, `scripts/categorise.py`; all 129 are in
`worst-before.txt`). The 10 worst, one per location, are rendered with the
source pixels, the mask trace, the read points by flag, and the output
polygon in `becker-1.8-worst10-before.png`.

| vertex at the reversal | count |
|---|---|
| a corner moved by the side-line fit (`_fit_corners`) | 60 |
| an unread corner kept at its pixel centre | 17 |
| a corner placed by its two profile reads | 17 |
| a plain read vertex beside a fitted corner | 16 |
| other (plain reads, rejected vertices, refinement inserts) | 19 |

118 of 129 have a corner-flagged vertex at or beside them. 86 have a fitted
corner. Three mechanisms:

1. **Needles from the per-vertex corner fit.** A corner is a *run* of
   flagged vertices: every vertex within about a corner-step (3 source px
   at x4) sees the turn. `_fit_corners` fits two side lines *per vertex*.
   On a sharp corner every vertex gets the same meet. On a round turn of 2
   to 3 source pixels (most of Becker's letters at 1.8 px/mm), each vertex
   gets a different pair of short tangent lines, and their meets land out
   past the arc and out of order. The polygon goes out to a meet and back
   again: a needle. Panels 1, 4, 6, 8 and 9 of the before render show this.
2. **Notches from unread vertices.** A vertex the read could not place stays
   at its pixel centre, half a pixel inside the edge where every read
   neighbour sits. An unread corner, or a short rejected run, between two
   read vertices is a notch whose sides turn back past 120 degrees. With the
   fit off, these are the largest class (21 of 58).
3. **Crossings.** Neighbours read along normals that disagree can swap
   order along the edge, which gives a small hook.

`_refine_curves` mostly carries these forward rather than starting them.
With curve refinement off, reversals are 4.8 instead of 7.1. With the
corner fit off, they are 3.3. Neither alone reaches 1.0.

## The fix (`cfg.subpixel_corner_runs`, default OFF)

Only the native read (`subpixel_edges_upscaled`) is touched. All of it lives
in `digitizer_core/subpixel.py`; the note above `CORNER_RUN_FOLD_PX`
documents it.

- **One fit per corner run** (`_fit_corner_runs`). Side lines come from the
  read vertices before the run's first vertex and after its last. The whole
  run goes to that one meet. The meet is refused when:
  - it falls behind either side's nearest point, which would fold the ring;
  - it lies more than 1 px from every point the profile read placed in the
    run (a round turn's reads sit on the arc);
  - it lies more than 1.6 px from the run's own trace. The ladder's eroded
    rectangle corners sit 1.48 to 1.61 px away, so they are kept.
- **Unread vertices take their read neighbours' offset**
  (`_inherit_offsets`). The vertex moves out along its own normal, weighted
  by nearness, but only when there is a read within 2 corner-steps *on
  both sides*. A one-sided version dragged long, unreadable gradient-lane
  boundaries off their truth: hotel_fremont at 1.8 px/mm went 0.072 to
  0.084 mm, and 0.070 with that part off.
- **Fold drop** (`drop_folds`, in stage 4). A vertex that lands behind the
  last one kept, measured along the trace's own direction, is dropped.

## Done-test

Bare stage 4 on the same masks, the #826 harness (`scripts/truth_table.py`
wraps `gate_table.py`). `results.json` and `results.txt` hold the table.

**Becker, reversals and right-angle turns per 100 mm, today → ON:**

| px/mm | reversals | right angles |
|---|---|---|
| 1.8 | **7.1 → 0.9** | 26.5 → 20.1 |
| 3 | 5.6 → 1.3 | 30.6 → 24.3 |
| 5 | 3.1 → 1.4 | 33.0 → 29.6 |

**Four truth cases, median edge error mm (today → ON) and reversals:**

| case | 1.8 | 3 | 5 |
|---|---|---|---|
| golden_tee logo | 0.1081 → 0.1109 · 6.8 → 5.2 | 0.0513 → 0.0524 · 6.3 → 5.4 | 0.0330 → 0.0332 · 4.0 → 3.7 |
| hotel_fremont logo | 0.0717 → 0.0739 · 3.2 → 2.4 | 0.0640 → 0.0629 · 2.8 → 1.9 | 0.0210 → 0.0226 · 7.6 → 6.9 |
| golden_tee one-ink cutout | 0.1142 → 0.1136 · 2.7 → 2.0 | 0.0623 → 0.0588 · 2.5 → 2.3 | 0.0417 → 0.0413 · 3.6 → 3.6 |
| hotel_fremont one-ink cutout | 0.1200 → 0.1210 · 1.9 → 1.2 | 0.0616 → 0.0580 · 6.5 → 5.6 | 0.0491 → 0.0497 · 9.8 → 9.1 |

The worst edge-error move is +0.0028 mm (golden_tee, 1.8), inside the 0.005
mm budget. Reversals fall in all twelve rows. Right-angle turns fall in ten
and rise by 0.3 in two.

The "today" numbers are re-measured on this tree. Some differ from #826's
table (hotel_fremont at 1.8 read 0.116 there and 0.072 here), because main
has moved since. Compare columns within one table, not across the two docs.

**Synthetic ladder** (`tools/edge_truth_ladder.py`, `scripts/ladder.py`,
`ladder.json`): the rectangles are identical at 1.8, 3 and 5 px/mm. The ring
at 1.8 improves from 0.357 to 0.295 mm RMS. Everything else is equal within
0.001.

**Renders:** `becker-1.8-before-after.png` (whole design, reversals ringed),
`becker-1.8-marine-before-after.png` (the MARINE line at 3x), and
`becker-1.8-worst10-after.png` (the 10 worst that remain).

## What it does not do

- Becker at 1.8 still has 16 reversal vertices (0.9 per 100 mm). 11 of them
  sit at fitted corners that turn between 120 and 141 degrees.
- A fitted corner can still overshoot by a fraction of a source pixel
  without reversing: see the small outward tooth at the M's inner right
  corner in the MARINE render.
- At 3 and 5 px/mm, Becker's reversals are 1.3 and 1.4, not under 1.0. The
  done-test asked only for 1.8.
- No stitches, no sew-out. One run each, two logos, two derived cases and
  one real file, so read gaps under about 0.01 mm as nothing.
