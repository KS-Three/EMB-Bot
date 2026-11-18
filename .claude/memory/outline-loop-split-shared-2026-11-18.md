---
name: outline-loop-split-shared-2026-11-18
description: Becker large's B/E outline "knot" = two face loops both covering the 2.7-3.0 mm stem; `outline_loop_split_shared` (OFF) cuts each loop's crosses at the shared line; 3 of 35 runs move, none worse; the top V is still a fan (pro uses one border loop)
metadata:
  type: project
---

Prime-grader fault `L_becker_hat_large` pin x21 y8.5 (and E/R join x78-81 y4-5). The outline is one region (5 face
holes) sewn as one satin loop per hole by `border_from_outline` (`stage6_border.keyline_runs`); where two faces stand
under two loop widths apart both loops cover the stem. Stem WIDTH is faithful to the art (region polygon 2.7-3.0 mm).
Flag `outline_loop_split_shared` (OFF, `stage6_border._split_cross`, `SPLIT_LAP_MM` 0.2): crosses stop at the shared
line, a cut under the 0.5 mm satin floor is not made. Becker large: 1,874 of 8,484 crosses cut (mean 0.75 mm).
35 runs: 3 move (becker_hat_large, mfab_hat, fx_becker_marine_logo), none worse by eye
(`docs/renders/outline-loop-split-shared-2026-11-18/`). Stitch count unchanged: crosses stop overlapping, thread
does not fall. NOT the pro's construction: the V at the top of each dip is still a fan; that needs one border loop
round the word plus the stem as its own column. With the flag ON `tests/test_silhouette_underfill_panels.py`'s two md5
pins (`becker_underfill`, `mfab_underfill`) move (byte pins, not quality). Related: [[border-from-outline-2026-10-24]].
