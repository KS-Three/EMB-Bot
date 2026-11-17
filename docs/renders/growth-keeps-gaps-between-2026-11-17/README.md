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

## Where the extra stitches on MFab / Drone / Golden Tee go (measured 2026-11-17)

The flag only removes growth (never adds): thread area falls on all three (MFab -50 mm2, Drone -54, Golden Tee -7), yet stitches rise.
- **MFab +1309:** all in block 0, the big black base fill (+1221; jumps 36 -> 50). Its stage-5 polygon goes from 4 holes to 43 and its perimeter from 581 to 896 mm: the flag cuts about 39 small holes into the base where it used to grow over thin gaps between the base and neighbouring shapes. Each hole costs row breaks and edge stitches. The 50 mm2 removed is 89% NOT under later thread, i.e. it is now left open as bare fabric (that is the rule's point), not hidden fill.
- **Drone +983:** same mechanism, 22 shapes changed, mostly small thread-173 shapes of 9-16 mm2 losing 3-5 mm2 each; 97% of the removed area is not under later thread.
- **Golden Tee +286:** 6 shapes, 7.4 mm2 removed, 69% not under later thread.
So it is not fill sewn under other thread for nothing: it is extra row breaks and edge stitching around newly opened gaps. Whether those gaps stay open on cloth is the sew-out's to say.

## 26 fixtures at the Studio request (80 mm, left_chest), OFF vs between ON

Compared by md5 of `design["stitches"]`: **17 of 26 moved, 17 pictured** in `fixtures/` (ORIGINAL | BEFORE | AFTER, stitch counts in the labels); 9 identical (ribbon_curve, fur_ramp, both gradient ramps, grass_macro, subject_stub, repro_gradient_white_icon, becker_marine_logo, logo_bridge_bar). `fixtures/sweep.json` has all counts.

**Worse, named first:**
- `photo/summit_badge` (28384 -> 32292, +13.8%): a thin purple sliver now pokes down from the top purple segment into the dark half at the top centre, plus a seam line across that segment; the dark/orange halves' thin seam now shows, as the art has it. Net worse.
- `logo_alpha` and `logo_whitebg` (6190 -> 6180, 6696 -> 6692): a thin seam line shows across the top of the blue ring. Slightly worse, small.

**Better:** `photo/logo_gaulke_roofing` at 80 mm (5058 -> 5049): the sun/roof gap is open along both peaks.

**No visible change by eye:** bg_uncertain (11245 -> 11220), photo/drone_render (+558), photo/enthusiast_logo (+2), photo_chrome_specular (+368), photo_dof_meadow (+352), photo_owl_pale (+133), photo_scene_stub (+1327), photo_sunset_backlit (-28), photo/region_blobs (+88), logo_script_tires (+2), photo/logo_golden_tee (+295), photo/logo_hotel_fremont (12648 -> 12648, same count), photo/screenshot_phone_ui_golke (-74).

Reading: the flag is not safe to flip for all designs: summit_badge gets a visible artefact. Cause not traced.

## Pointer for whoever picks this up (untested idea, not built)

`growth_keeps_gaps_between` already runs only the between-shapes branch of `_kept_gaps` (a shape's own holes are off in this mode), so MFab's 39 new holes come from that same branch: the lens between the base fill and many small neighbouring shapes. Gaulke's gap is two large shapes (sun fill, roof) facing each other along a long straight-ish edge. A scope that would hold it and leave MFab's alone is a size gate on the pair: keep the lens only when both shapes are large (e.g. each over a few hundred mm2) or the facing edge is long (a few mm). Not measured: it needs the same 9-job and 26-fixture sweep before anyone trusts it, and `summit_badge`'s sliver (cause not traced) may sit outside it.
