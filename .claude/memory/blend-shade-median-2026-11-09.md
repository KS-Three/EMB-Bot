---
name: blend-shade-median-2026-11-09
description: "2026-11-09 — defect 28 cause hunt: Fremont's block was already fixed 11-07 (#1312/#1329), MASTER_SCOPE line stale; summit's 0111 = mean of a 9-sample end bucket with speckle; `blend_shade_median` built OFF clears it, 20 other gradient/flat entries md5-identical"
metadata:
  type: project
---

# Defect 28 cause hunt — 2026-11-09

Kent picked "Defect 28 cause-hunt". Re-ran the three leftovers on main 19bde3e3.

**Fremont: already closed.** `logo_hotel_fremont` is B 76 (left_chest) / B 88
(hat_front) with NO thread finding. Cause was the grader reading the ground an
enlarged letter grew over (#1312 probe, `thread_match_grade_traced_letter` ON
11-07, #1329). MASTER_SCOPE item 28 still says "cause not established": stale.
It is also class `flat` now, not gradient.

**Summit: cause found.** Background region Scd5f9d89, per-region RADIAL ramp,
no design ramp, not carved. Extremes are single pixels (L 19 and L 183): 60.4
dE, so 5 shades. The t = 1 bucket holds 9 of 2,500 samples, 3 bright speckle
pixels; `_shade_lab_colors` takes the MEAN (L* 48.8) and snaps `0111`, but the
band's artwork is (74,69,64), L* 30. Median of the same 9 is L* 29.5 -> `0134`
(loaded). The bimodal-mean failure a third time (cf. gaulke, thread-match-excess).

**Built OFF: `cfg.blend_shade_median`.** One reader (stage6_blend per-region
path; design-ramp path untouched). 22 gradient-class-at-the-time entries x both
arms: only summit moves (both garments: THREAD_MATCH_POOR block 1 -> 0, F 0 ->
F 10, still F on `GROUND_SEWN`); the other 20 plan md5 identical. Flip is
Kent's. Lanes today: only drone, ramp_linear, ramp_radial, summit trace
`gradient`; tires/bridge_bar/gaulke/golden_tee/fremont/screenshot/white_icon
trace `flat`. Flat raw blocks left: bridge_bar 3, screenshot 1 (per garment).
Photo stub `0722` untouched. Doc: `docs/blend-shade-median-2026-11-09.md`.
