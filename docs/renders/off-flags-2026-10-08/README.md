# Contact sheet: four default-OFF flags (2026-10-08)

Evidence only; no default is flipped. Each panel pair is one real-art fixture already in the repo, OFF left, ON right, drawn with `digitizer_core.stitchviz.render_design`, cropped to where the two differ, labelled with stitches / trims / colour changes OFF -> ON. **Nothing here has been sewn.**

| file | flag | ON means | fixtures |
|---|---|---|---|
| `two_tone_snap.png` | `PipelineConfig.two_tone_snap` (PR #674) | black-and-white logo thresholded to two inks | mfab_lc, toat_machine, golke_roofing (80 mm left_chest, 6 colours) |
| `satin_tip_corner_gate.png` | `satin_tip_corner_gate` (PR #677) | a satin tip must land on a convex corner | becker_marine_logo, enthusiast_logo |
| `lettering_columns.png` | `lettering_columns` + `lettering_words` | lettering sewn as Columns from the one word tagger | becker_marine_logo, enthusiast_logo |
| `image_lane_cuts_vs_stitches.png` | JS `fillColumns` image lane, PR #697 candidate C (patch only, not a shipped option) | underlay walk cut at open ground instead of walked round; red rings = trims | mfab_lc, becker_marine_logo, summit_badge (full_back) |
| `overview.png` | all four, first fixture of each | | |

Reproduce: `digitizer/tools/off_flags_sheet.py` (flags 1-3: `python -m tools.off_flags_sheet --flag <flag> OUT`; flag 4 via `--json-pair` on designs dumped by `off-flags-dump.mjs`, run on #697's branch, `--src` the base engine vs the engine with `underlay-checked-plain-walk.diff` applied and `plainRingWay` returning null, `--checked`, `--garment full_back`). Flag 4 compares fillColumns ON today against candidate C, not against fillColumns OFF.
Fixtures with no pair here (fremont patch) were dropped for time.
