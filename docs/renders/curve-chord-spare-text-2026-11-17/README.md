# curve_chord_stage4_spare_text: ORIGINAL | BEFORE | AFTER (2026-11-17)

Flag state: BEFORE = all three flags OFF (main). AFTER = `curve_chord_mm=0.4`,
`curve_chord_stage4=True`, `curve_chord_stage4_spare_text=True`. The nine
committed pro jobs (`tools.prime_grader.population()`), each at its own garment
and width. **All 9 moved (stitch stream differs); 9 of 9 are pictured.** Whole-design
pictures at 12 px/mm; read at that size, which hides small changes.
`rows.json` has stitch counts, trims and the changed-pixel share.

| design | stitches OFF -> ON | by eye |
|---|---|---|
| tires_hat_3d | 4544 -> 4500 | **better, partly.** The r's bottom turn is a round curve in the tile (was a 9 mm chord with a corner). The e's upper exit edge and the r/e lump at (74, 31.5) are unchanged. |
| precision_drone | 14182 -> 13970 | **worse.** "AND DRONE" letters thinned and broken (the D, R, O especially); 13.6 % of pixels changed. |
| mfab_hat | 20846 -> 20738 | **worse.** The W of "WELDING" lost a stroke and reads as a Z. |
| goldentee_hat | 13613 -> 14951 | **worse, probably.** The swoosh's white fill changes direction and goes patchy; +1,338 stitches. |
| hotel_fremont_hat | 16054 -> 15976 | no visible change at this size (6.6 % of pixels differ, trims 31 -> 26; the rope border differs slightly). Not judged better or worse. |
| becker_hat_large | 16249 -> 16305 | no visible change (0.08 % of pixels). |
| gaulke_roofing_hat | 7392 -> 7448 | no visible change at this size. |
| toat_machine_hat | 17430 -> 17427 | no visible change (0.02 % of pixels); picture not studied beyond the pixel share. |
| toat_beanie | 17357 -> 17357 | no visible change (0.01 % of pixels); same note. |

Why the lettering still moves: "AND DRONE" and "WELDING" are not text-tagged
when stage 4 runs the densify, so the spare never hands them back. The flag does
what it says (a text-tagged shape keeps its old polygon) and that is not enough.
Instrument readings and by-eye calls on one run each, not quality claims.
