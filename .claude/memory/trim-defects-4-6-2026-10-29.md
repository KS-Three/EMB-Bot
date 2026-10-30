---
name: trim-defects-4-6-2026-10-29
description: Defects 4/6 re-measured on main 44ecf1cb, 17 paired jobs — cuts 391 vs pro 409 (0.96x, the 3.1x is gone) but needle-up breaks 2.07x (488 uncut floats); in-piece 27% not 69%; fill sections 32 vs 0; `fill_section_cuts_first` OFF takes 391 -> 377, exposed 723 -> 651
metadata:
  type: project
---

Re-measure for Kent's 2026-10-29 "fix defects 4 and 6". Full record:
`docs/trim-defects-4-6-2026-10-29.md`. 17 jobs (`border_census.PAIRS` +
ProSeal beanie), the pro's width, one reader (`tools/sequence_pro`,
`tools/trim_classes`) on both DSTs.

- **Cuts are at parity:** ours 391, the pro 409 (median per job 1.18x). The
  3.1x is gone; under-later cuts 14 vs 18 (was 43 vs 9).
- **Breaks are not:** we leave 488 needle-up moves uncut, he leaves 16, so
  needle-up moves are 879 vs 425 (2.07x). `cut_every_jump` is the lever: 25
  uncut, +80 cuts, bare thread 158 -> 133 mm.
- **Defect 6's "bulk inside one shape" is stale:** 104 of 391 cuts inside a
  piece (27%), the pro 73 of 409; `trim_locality` reads 14% in-shape.
- **The class the pro never has is fill sections:** ours 32, his 0. The
  section planner already FOUND fewer-cut orders (Becker small 4 -> 3 cuts at
  half the exposure, MFab 8 -> 6), and `_score` refused them for the hidden
  travel under rows still to come.
- **Built `cfg.extra["fill_section_cuts_first"]` OFF.** It implies
  `fill_section_travel` and prices the planner with hidden travel free
  (`stage6_fill._score_hidden_free`); the gate is unchanged. Results: cuts 391
  -> 377, fill sections 32 -> 18, exposed 723 -> 651 mm, bare unchanged. With
  `fill_bridge_cut_exposed`: 390 cuts, 609 mm exposed.

**Superseded on 2026-10-30, main 9a8589f3 (#1198: `fill_seam_order` +
`fill_bridge_cut_exposed` ON):** `_order_for_seams` runs AFTER `_plan_sections`
and re-sequences every section, so the priced order is not the one that sews.
17 jobs: cuts 399 -> 397 (pro 409), exposed 509 -> 506 mm, whole-job CPU +14%,
three Becker jobs +1 cut. Ten moved jobs replayed: seam ON 240 -> 238, seam OFF
247 -> 233, plan CPU +31%. A gain needs the planner choosing INSIDE seam order's
constraint. Seam order also took Becker beanie's exposed 38.6 -> 105.8 mm, bare
3.7 -> 14.8. Sheet: `docs/flip-sheet-2026-10-30.md`. **How to apply:** after any
flip touching fill order, re-read a held fill flag; a flag's price is base-bound.

**Why:** a session handed "3.1x trims" would build a cut-reducer for a gap that
no longer exists in cuts; the live gap is uncut floats (breaks) and one
construction class. **How to apply:** quote breaks (cut + uncut needle-up) as
well as cuts. Before pricing an order, check whether `_score`, not the
planner, is refusing it. ProSeal beanie's 298 mm exposed / 118 mm bare is the
next travel lead. Related: [[in-piece-cuts-2026-10-25]],
[[cut-every-jump-2026-10-21]], [[trim-economy-2026-10-21]],
[[buried-walk-2026-10-26]].
