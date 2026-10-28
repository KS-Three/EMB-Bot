---
name: shape-memo-2026-10-28
description: forced-flat owl_kent at Studio size is 137 s on a quiet 4-core box, 94% stage 6/7, and 79 s of it is the Column lane's second (lane-OFF, rank-only) stage-7 pass; shape_memo answers that pass's pure emitters from the first, 137 -> 113 s flat, 123 -> 97 s gradient, md5-identical
metadata:
  type: project
---

2026-10-28, foreman's lane after Kent's "new lane after this wave": the
FLAT lane on a photo at Studio size (owl forced flat hit the Studio's 600 s
stop twice on Kent's loaded laptop; automatic took 376 s).

**Measured, quiet 4-core cloud box, `studio_request(80.0)` left_chest,
build + finish + plan + plan_to_design, before the change:** owl forced flat
136.7 s wall / 137.0 process (318 regions, 45,616 st); owl automatic
(gradient) 123.4 / 124.2 (105 regions, 35,665 st); photo_owl_pale 11.1 flat
/ 8.9 auto; logo_whitebg 2.6 / 3.3. So on a quiet box flat is only 11%
slower than gradient on the owl; Kent's 600 s is his machine's load (his
process_time inflates ~2.6x, memory `digitize-speed-2026-10-26`).

**Where the 137 s go (clean wrapper timing, not cProfile):** stage 0-5
7.6 s; stage 7 `sequence` 134 s, of which the Column lane's lane-OFF pass
(run first for its sew ORDER only, `stage7_sequence.py` ~2588) is 78.7 s
(55%) because `is_lettering` admits 33 small photo regions. Inside both
passes: `travel_path` 33.5 s (9,211 calls), `best_fill_angle_deg` 22.3 s
(52 shapes x 17 angles, one GEOS overlay per scanline), `_reorder_for_cover`
21.1 s, `_bury_trims_under_later` 16.7 s (`_bury_route` rasters, 252 calls),
`keyline_runs` 12.1 s (`_exact_cross`, 23,108 GEOS overlays), `satin_shape`
11.8 s. No per-pixel Python callback and no O(n^2) region pass: it is
geometry work driven from Python loops, and 2x of it.

**Built (default ON, exact):** `digitizer_core/shape_memo.py`. Inside a
per-job `scope()` (opened by `_plan_stitches` only when `lettering_columns
and satin`), `stitch_shape`, `satin_shape` and `underfill_rim_runs` memoize
on the pickle of (args, every ContextVar knob); a hit is the stored pickle
re-loaded, so fresh objects. Census on owl flat: the ON pass repeated 26/27
fill shapes (19.7 s), 85/108 satin (5.3 s), 275/315 rim calls (6.2 s).
After: owl flat 112.9 s (-17%), owl gradient 97.0 s (-21%), both md5 the
same; pale and whitebg within noise, same md5 (overhead table in PR body).

**Tried, exact, too small:** early-abort in `best_fill_angle_deg` (column
count is monotone in rows, so a candidate past the best can stop): 21.1 ->
19.5 s on the 52 captured searches. Not shipped.

**Next exact candidates:** skip `_bury_trims_under_later` in the lane-OFF
pass (it inserts a TRAVEL run carrying the following run's shape_id, so the
first-appearance rank cannot move; ~8 s); the rank pass's edge cap and ties
need the same proof per pass. Output-changing: fewer angle candidates, a
probe cap on `_reorder_for_cover` (both Kent's, `docs/photo-cold-profile-
2026-10-13.md`).
