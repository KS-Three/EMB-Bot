# `growth_keeps_gaps` on the 9 pro jobs (2026-11-17)

Finding for the prime grader's Gaulke fault "the white gap between the sun and the peaks closes" (x 46.5 y 13.5 and x 67.5 y 12.5 mm).

**Cause: stage 5 growth.** Region polygons keep the art's 1.09 mm sun-to-roof gap through stage 4; stage 5 pull/overlap growth takes it to 0.69 mm, and the satin edge then closes it where the stitches touch. `cfg.extra["growth_keeps_gaps"]` (built OFF, #1485) already holds it at 1.09 mm at stage 5. No new code: this is not a satin-push or compact-satin problem (`satin_push_keeps_gaps` 0.5 and `compact_satin_keeps_gaps` are already ON by default). No pull amount changes (gate 1).

Crops: `sun_gap_BEFORE_crop.png` / `sun_gap_AFTER_crop.png` (Gaulke, x 36-76, y 6-22 mm): ON gives one continuous white line, right end open.

**Sweep:** 9 jobs, flag OFF vs ON. **7 moved, 7 pictured, 2 byte-identical** (becker_hat_large, tires_hat_3d). Each picture is ORIGINAL | BEFORE | AFTER. By eye:

| job | stitches OFF -> ON | by eye |
|---|---|---|
| gaulke_roofing_hat | 7392 -> 7363 | **better**: sun/roof gap open on both peaks |
| toat_machine_hat | 17430 -> 22441 | **worse**: the white background fill turns grey and streaky |
| toat_beanie | 17357 -> 20452 | no clear change at this size; +18% stitches unexplained |
| hotel_fremont_hat | 16054 -> 23481 | no visible change, but +46% stitches |
| mfab_hat | 20846 -> 22155 | no visible change |
| precision_drone | 14182 -> 16575 | no visible change |
| goldentee_hat | 13613 -> 13899 | no clear change; shadow-ring edges differ slightly |

Catch: the flag adds many stitches on four designs with no visible gain, and TOAT Machine's fill degrades. Not safe to flip as is; the fill/stitch growth on those needs a cause first.
