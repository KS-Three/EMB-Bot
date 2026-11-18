---
name: outline-one-band-2026-11-18
description: Becker's border built the pro's way, `outline_one_band` (OFF): stem columns + ONE outer-ring loop; 2 of 35 runs move; costs trims +12 and two guard figures (coverage cell 6.71, cap BORDER role) with it ON
metadata:
  type: project
---

Director 11-18 after #1657 (`outline_loop_split_shared`) read as a seam, not a fix. The pro's Becker file, read by
stitch data (y runs UP in the file: flip it, or the window lands on MARINE): one tatami fill under each letter
group, then the satin: stem column first, then ONE border band over the top across the V (79-93 deg crosses, no
fan). `digitizer_core/outline_band.py`: stems (sum of distances to two faces under two widths, outside the outer
zone, elongated), hole loops for the leftover strips (arcs, walks under the outer loop), ONE outer-ring loop last.
Doc `docs/outline-one-band-2026-11-18.md`, pictures `docs/renders/outline-one-band-2026-11-18/`.
35 runs: 2 move (becker_hat_large, fx_becker_marine_logo), OFF byte-identical. Final: Becker large trims 20 -> 21 (first build 19 -> 31), 80 mm 14 -> 20. The band ends where the replaced loops ended
(`_loops_exit`), else MARINE's letter order changes (coverage_max 6.71 over the 6.667 line, back to 6.39). The walks
between pieces must not cross a finished stem (thin lines on top). `test_run_spans` asserts the satin-arc emitter only
with the flag OFF. ON tests: 4 fail, all known (golden, forced default, two md5 pins). A raster `_sum_mask_polys`
finds stems; do NOT take stems as band minus outer zone (those merge into 60-150 mm2 blobs). Related:
[[outline-loop-split-shared-2026-11-18]], [[border-from-outline-2026-10-24]].
