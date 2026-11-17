# `growth_keeps_gaps_between` on the 9 pro jobs (2026-11-17)

**Why the first flag was worse (cause, measured).** `growth_keeps_gaps` has two rules: keep the gap between two shapes, and hold a shape's own holes at art size. On TOAT Machine the white background fill has 15 holes of 0.5-2 mm (the halo around lettered shapes sewn over it). The own-holes rule left 63 mm2 of that bare. The Gaulke cure needs only the first rule.

**The guard.** `cfg.extra["growth_keeps_gaps_between"]` (built OFF, byte-identical when absent): the between-shapes rule only; a shape's own holes are grown over as OFF. `growth_keeps_gaps` itself is unchanged. Test: `tests/test_growth_geometry.py::test_between_mode_keeps_the_gap_but_not_a_shapes_own_hole`.

**Sweep, 9 pro jobs, OFF vs between ON: 7 moved, 7 pictured, 2 byte-identical** (becker_hat_large, tires_hat_3d). Each picture is ORIGINAL | BEFORE | AFTER. All pictures viewed by eye:

| job | stitches OFF -> ON | by eye | old flag (`growth_keeps_gaps`) was |
|---|---|---|---|
| gaulke_roofing_hat | 7392 -> 7363 | **better**: sun/roof gap open on both peaks (`sun_gap_*_crop.png` for the old flag shows the same result) | better |
| toat_machine_hat | 17430 -> 17404 | no visible change | **worse**, 22441 |
| toat_beanie | 17357 -> 17140 | no visible change | 20452 |
| hotel_fremont_hat | 16054 -> 16054 | no visible change | 23481 |
| mfab_hat | 20846 -> 22155 | no visible change | 22155 |
| precision_drone | 14182 -> 15165 | no visible change | 16575 |
| goldentee_hat | 13613 -> 13899 | no visible change | 13899 |

Nothing is worse by eye. Catch: MFab (+6%), Drone (+7%) and Golden Tee (+2%) gain stitches with no visible gain at this size. I have not traced where the extra stitches go (the by-eye pictures show no difference). Whether those gaps open on cloth is a sew-out matter (gate 1); these place growth, they do not size it.
