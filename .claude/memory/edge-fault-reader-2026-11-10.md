---
name: edge-fault-reader-2026-11-10
description: First fault reader scored against Kent's defect-marks pins: edge_wobble flag locations hit 12/20 "should be smooth" pins vs chance 0.49 at 3 mm, CI [-0.04,+0.21] = not shown; harness tools/fault_reader_harness.py reusable; next = closed/merged letters
metadata:
  type: project
---

Built 2026-11-10 after [[defect-marks-sitting-2026-11-10]]. The brief: test
a "fault reader" against WHERE Kent pointed, not against a whole-design number.

**Harness** `digitizer/tools/fault_reader_harness.py`: a reader writes
`<item>.flags.json` (mm in the pins' frame, strength) + `<item>.mask.npz`
(thread pixels); `score` reports hits within `RADIUS_MM` 3.0 beside two nulls
(random points on stitched area; on its 1 mm edge band), 2,000 seeded draws,
pin-weighted pool with item bootstrap, strength AUC. Pin selection is a
written rule over NOTE + kind (`select_edge_pins`); the committed list
`docs/defect-marks-2026-11-10/edge-reader-pins.json` is pinned by a test.
Pre-registration committed before results: `edge-reader-preregistration.md`.

**Reader** `digitizer/tools/edge_fault_reader.py`: re-runs each job at
`--tree` (the primary on `950855bf`), refuses unless stitches match the stored
design (all 11 did), keeps `edge_wobble.analyse_plan(...)["flagged"]`
locations (preflight drops them), merges within 2 mm.

**Result (instrument reading, n = 20 pins / 7 logos):** hit 0.60 vs chance
0.49 (edge-band 0.48), kappa 0.21, CI [-0.04, +0.21]; AUC 0.51. Not shown.
Misses: Tires' even scallop (high-pass removes it), ProSeal's small "SPRAY
FOAM" text (no flags at all), Fremont "all letters". Strongest flags = satin
column ends he never pinned. Recorded in DOCTRINE measured negatives.

**How to apply:** don't treat `edge_wobble_*` as Kent's smoothness eye; a next
smoothness reader needs absolute roughness, small text, and outline-vs-art.
Reuse the harness, with a new pre-registration, for the next reader (closed or
merged letters, 15 pins on 6 logos). Write-up: `docs/edge-fault-reader-2026-11-10.md`.
