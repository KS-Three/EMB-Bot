---
name: satin-fill-oracle-2026-11-06
description: C3 oracle ground-splitter (measurement only): cutting our regions along the pro's 10+ cell blobs lifts mean cell kappa 0.381 -> 0.482 over 21 jobs, no verdict; the floor decides (5 cells 0.561, 20 cells 0.427). Reads the pro, a maximum.
metadata:
  type: project
---

2026-11-06, lagging-areas C3, `satin_fill_census.py oracle-split` (+ unit tests in
`tests/test_satin_fill_census.py`). Doc `docs/satin-fill-oracle-split-2026-11-06.md`.
No flag, no engine file, no default moved.

**Number.** Re-digitized the OFF arm on main `5caccdc8` (10-29 runs gone). Mean
sttype kappa over 21 jobs: routing 0.381, per-region oracle 0.365 (reproduces
10-29 exactly), **oracle-split 0.482**, ceiling 0.649. Beats routing on 17 of 21.
Closes 0.377 of the gap from routing to the ceiling (kappa-based). Cut: 14
grounds, 38 blobs, 3,268 mm2; 9 jobs have no 10+ blob and equal the plain oracle.

**Verdict: none** (rule: >= 0.55 design, <= 0.45 close). The floor decides it:
5 cells 0.561, 10 cells 0.482, 20 cells 0.427. Which floor defines "a layer" is
Kent's call (put as a question in the PR; no default picked).

**Why it matters.** The gain sits entirely in the big grounds (Fremont patch
0.52 -> 0.85, MFab 0.56 -> 0.72, To a T 0.3-0.4 -> 0.5). It READS the pro's blobs:
a maximum, not what inference from flat art reaches.

**Trap.** Tie-break for a region's majority type must be row-major first-met
(Counter.most_common), not lowest id, or the plain oracle drifts 0.002-0.05 from
`cell_census`'s on five jobs. Chance-corrected kappa can fall when labels get more
accurate if the label mix rises the floor (Gaulke, ProSeal hat), per 10-29.

Related: [[satin-fill-remeasure-2026-10-29]], [[layering-census-2026-10-26]], [[mfab-underfill-panels-2026-10-25]].
