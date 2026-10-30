---
name: satin-fill-remeasure-2026-10-29
description: Defect 5 re-measured on main 44ecf1cb, 22 jobs. Routing kappa 0.387; a per-region oracle 0.365 (wins 10/21): no router left to build. Pro vs himself 0.5 mm off 0.650 is the cell ceiling. satin_per_stroke a wash, buries the drone's crosshair; proposed stay OFF.
metadata:
  type: project
---

2026-10-29, defect 5, branch `claude/defect5-satin-fill-remeasure`. Tool
`digitizer/tools/satin_fill_census.py` (+ `tests/test_satin_fill_census.py`):
one digitize per job per arm feeds `pro_baseline.kappas`, a cell oracle, the
straddle anatomy and `tier_census`. Doc `docs/satin-fill-remeasure-2026-10-29.md`.
No engine change.

**Routing.** Mean sttype kappa 0.387 over 21 jobs (Tires is degenerate: the
pro sews one type). The oracle (each of OUR regions given the pro's majority)
scores 0.365, below us. One label per region collapses the mix, so the floor
rises (Fremont patch 0.43 → 0.61). August's 76.6-vs-55.4 headroom is gone. The
oracle needs the SMALLEST sewn region to own a cell: in list order a ground
(Fremont's 2,137 mm² field) claimed everything.

**Ceiling.** The pro's map against itself 0.5 mm off reads 0.650, 1.0 mm off
0.415. Quote our cell kappa against that, not against 1.

**Per shape.** `tier_census`'s reader scores our own known plan 0.22 by count
and 0.80 by area, so read shape kappa by AREA only: plan vs pro 0.77
(lettering 0.87, the rest 0.73), grounds excluded.

**Segmentation.** Still 96% "speckle" by `splitprobe`, but 33% of minority
cells sit in blobs of 10+ cells, all in ~12 ground regions (Fremont field,
To a T field, MFab silhouette, Becker slab): layering, not grid noise.
Region splitter still not worth building.

**satin_per_stroke** OFF | ON: 13/22 byte-identical, kappa +0.002, bare
identical on all 22 (Becker 100 mm 14.4/14.4; the 10-20 "8.3 vs 6.8" is
gone). Renders: MFab N and a ProSeal hex move toward the pro; Becker's bowl
fans; the drone sews two ground pieces as wide satin OVER the crosshair arm.
Proposed: keep OFF (sent to the director, Kent's call).

Related: [[layering-census-2026-10-26]], [[satin-gate-attribution]].
