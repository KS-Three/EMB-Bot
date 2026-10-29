---
name: stage7-scene-speed-2026-10-29
description: the kept-frame scenes' 349-2,100 s was two processes on a loaded laptop -- 90-250 s quiet, md5 identical; two concurrent digitizes cost 4.1x EACH; stage 2 split_tonal_regions bincount + stage 6 prepared covers / vectorised threaded angle search, exact
metadata:
  type: project
---

2026-10-29, worker lane after PR #1182 named stage 7's rank-only second pass
as the next measurement (the six refused scenes read 349-2,100 s at
`--procs 2` on Kent's loaded laptop; the Studio stops waiting at 600 s).

**The time is real but the number was load.** Quiet box (Ryzen 7 4700U,
8 cores, nothing else running, the corpus tool's env), one process, stage 0-4
result pickled and `plan_stitches` replayed: plan 64-104 s per scene, stages
0-4 26-147 s (stained_glass the 147). Three in-process reps of night_skyline
85.3 / 78.3 / 78.9 s, same md5. TWO processes replaying it at once: 326 s
EACH (4.1x) and `process_time` inflated the same, md5 identical across
processes (no hash-order or tie dependence). Stage 7 is GEOS, so not IPP.
**Rule: time a row at `--procs 1` on a quiet box; a `wall s` from a 2-proc
capture beside other sessions is a load reading** (the sxs page now says so
and prints each run's procs).

**Where plan time went (cProfile, six scenes agree):** stage 6 fill
emission inside the lane-OFF pass -- `best_fill_angle_deg` 25-30% (17
candidates x one GEOS overlay per scanline), `travel_path` via the two
reorder walks ~40%, inset-ring `buffer` ~15%, `covers` ~8%, `_ring_route`
~5%. The lane-ON pass adds only 5-15 s (shape_memo). On stained_glass stage
2's `split_tonal_regions` was the other half: 130 s of 34,370 `.sum()`
calls, one full-crop pass per connected component.

**Built, all exact (Kent: "A + B + C(1)(2)"):** `_large_components`
counts every label with one `np.bincount` (integer counts, same double
product, same order); `_row_spans` makes one `shapely.intersection(poly,
lines)` call per angle (the same GEOS op per row). Kent: "no pool, rows
only" -- a thread pool over the 17 candidates was exact but read 239-253 s
against 277-318 serial on one scene, inside the drift. After: AFTER_TBD. DST
md5 byte-identical on the six scenes and 14 repo fixtures (flat + gradient).

**Measured FALSE and dropped (C1):** `shapely.prepared.prep(slack).covers(
line)` in `travel_path` / `_reorder_for_cover` is NOT the plain predicate:
it re-chose one travel route on underwater_reef (34,324 -> 34,334 st) and
moved owl_kent's md5; toggled alone it was the whole difference (threads and
the vectorised rows each left the md5). A prepared predicate cannot stand in
where the design is pinned byte for byte. `test_travel_path_asks_the_plain_
covers_not_a_prepared_one` guards it.

**Not built:** numpy `_ring_route` (C3, ~5%), a travel memo between the
cover walk and `emit` (~8%), skipping the lane-OFF pass on photo classes
(changes the sew order = the design).
