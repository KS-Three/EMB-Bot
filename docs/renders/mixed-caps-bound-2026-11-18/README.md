# `text_cluster_mixed_caps` with the bound, 2026-11-18

The director's bound (after the gradient icon's bands were tagged as lettering and the flip was withdrawn,
`docs/renders/text-cluster-mixed-caps-2026-11-17/`): a group the mixed-height re-cluster forms must hold **a pair
the normal 0.8-ratio pass would link** (`textcluster._has_letter_pair`: `_linked` at `LETTER_HEIGHT_RATIO`, one
ink, stroke, reach). TOAT's T and T (or its o and A) are such a pair. Built OFF, as before; OFF is byte-identical.
Pictures here are ORIGINAL | BEFORE (flag OFF) | AFTER (flag ON), same 44 designs as the first census.

## Every test file that mentions text, tag, letter, border, cluster or repro_gradient, flag ON

156 files (file names matching those words, plus every file that mentions `text_cluster`, `textcluster`,
`repro_gradient`, `letter_candidates`, `is_lettering` or `text_candidate`) run with the default temporarily True:
**2,683 passed, 18 skipped, 2 xfailed, 2 failed.** The two failures:
1. `test_text_cluster_mixed_caps.py::test_the_config_field_defaults_off...` asserts the default is OFF: expected
   under the temporary True.
2. `test_stage2_photo_segment.py::...match_golden...[photo/enthusiast_logo.png]`: the known platform-numerics
   golden (CI deselects it); **it fails the same way with the flag OFF** (rerun, 1 failed 3 passed).
`test_borders_last.py::test_repro_fixture_border_satin_sews_after_its_cone_s_fills` (the guard the first flip broke)
**passes with the flag ON** now. No guard breaches.

## Census: 7 of 44 move (same 7), 0 worse by eye, ONE wrong tag still

| Design | By eye | Tag |
|---|---|---|
| `toat_machine_hat`, `toat_machine_beanie` (row), `toat_beanie` | **better**: the A has two legs, a flat top and an open counter, the T bars lose the fanned patch (the cure is kept) | 4 letters, one row, aligned (centre spread 0.19 of the tallest on the hat) |
| `toat_beanie` i-dot of "Machine" | neutral to better (the dot now leans like the art's) | **a fifth member that is not in the row** (centre spread of the cluster 1.26 of the tallest): the i-dot joins the "To A T" cluster at the 0.6 height band |
| `repro_gradient_white_icon` (80 mm left chest, the census setting) | no visible change by eye (border bands turn their stitches slightly differently) | **STILL TAGGED AS LETTERING: 4 shapes** (two 19.1 / 19.0 mm twin frame bars 3.4 mm wide, which pair at 0.8, plus a rotated bar and a 25 mm triangle that join at 0.6); centre spread 1.83 of the tallest. The 90 mm test no longer tags it, the 80 mm census does. |
| `drone_render`, `mfab_lc`, golke screenshot | no visible change (the golke "Photo" stays at its drawn size) | the golke row and the others tag as before (the first run's fix still holds) |

**The bound is not enough on its own.** Two twin frame bars pair "like two letters", so the icon at 80 mm still
starts a row. What separates the cases by number is that the TOAT row is ON ONE LINE (the letters' vertical centres
spread 0.19 of the tallest glyph on the hat) and the icon's tagged group is not (1.83); the beanie's i-dot
(1.26) is not on the line either. That is a "same line" rule, a new term, not something the letter door knows
today; it is NOT built here.
