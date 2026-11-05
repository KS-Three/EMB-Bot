---
name: mfab-photo-route-2026-11-04
description: MFab hat classes photo_scene at every width (grain gate 0.298 vs 0.28, veto 0.856 vs 0.90); the 60 and 101 mm defect is the photo lane skipping the 8 px/mm working grid (W+E stay joined), NOT its segmenter; fix = photo_work_grid, OFF
metadata:
  type: project
---

# MFab hat at 100.8 mm, default route: "WE"+"L" white blob (diagnosis 2026-11-04; cause corrected 2026-11-05)

**Correction 2026-11-05 (the photo-lane session):** the first diagnosis below read the cause as the photo lane's SEGMENTER merging thin gaps (superpixel merge, bilateral kill). That was wrong. Measured on main 77c81ab2: at 100.8 mm the stage-2 labels keep 92% of the art's white in the small-line band and no black is lost, and the stage-4 regions are clean (37 regions, fewer fragments than 113.5's 93). The real cause: `work_grid_px_per_mm` deliberately keeps the photo classes on the source line (the working grid is for line art), so this art, classed photo_scene, reaches the lane at 4.0 px/mm (6.7 at 60 mm). In the raw art W and E touch by a one-pixel black bridge (one 355 px component, 4- and 8-connected). On the source line the region cut keeps them ONE region, S0d081325, 54 mm2; it has no text tags, so it is no rider (`silhouette_underfill.find_riders`), is merged into the black host (`merged_into`), and the white panel sews a 503-point fill over it. The flat route's Lanczos enlargement to 8 px/mm opens the bridge; at 113.5 mm the resample opens it too (two tagged regions, 30 and 32 mm2). Fix: `cfg.photo_work_grid` (OFF) makes the photo classes take the working grid; ON, 60 and 100.8 mm sew black, white, black. The stage-0 numbers below still hold; the sections that blame the segmenter do not.

Cause (first diagnosis, WRONG on the mechanism): NOT the white-keyline recipe ([[white-keyline-art-gate-2026-10-26]]). The default route sends this art down the PHOTO lane (`CLASSIFIED_PHOTO_SCENE`), at every width. The photo lane smears the small line at 100.8 mm. Same family as the 36.7 mm head-to-head in [[dade-app-teardown-2026-11-04]] (that one is the other defect, PR #1235).

## Measured (offline, from the 100.8 / 113.5 / 36.7 job JSONs of the briefing session, main 053ed41c)
- Stage 0 on `logo_mfab_hat.png` + Studio hat_front config: `photo_scene` at 36.7, 80, 100.8, 113.5 (identical; `classify()` never reads target width). Signals: unique_color_mass 0.298 (gate 0.28, route 'grain'), texture_frac 0.063, two_tone_mass 0.856 (veto needs 0.90), confidence 0.611. Gate background: [[stage0-texture-gate-2026-10-28]].
- Default 100.8: px/mm 4.01, 39 shapes (13 white), 19,096 st, grade C, LETTERING_ILLEGIBLE, PHOTO_RESOLUTION_LOW. Photo segmentation: 739 superpixels -> 49 regions, bilateral texture kill 6 px.
- Default 113.5: px/mm 4.0, 90 shapes (67 white), grade B. Segmentation: 994 superpixels -> 64 regions. So "fine at 113.5" is the same lane landing luckier; the superpixel merge is size-sensitive.
- Flat 100.8 (forced_class flat): px/mm 8.0, 88 shapes (62 white), grade B. Flat 113.5: 79 white, B.
- Warnings and shape counts say the small line's white gap shapes merged inside the photo segmenter, before the keyline fold / sew_enclosed_white / pull-comp stages ever see them.

## Why no fix in the diagnosis session
Fixing the cause by routing this art flat (move the grain gate or the two-tone veto) is stage-0 recalibration. ROADMAP hard gate 2 refuses it, and Kent ruled reporting-only 2026-09-14 on the seed spread of this same gate. The photo-lane fix (stop the SLIC/bilateral merge from joining letters) is a larger change with no pro reference at this size. Nothing was changed and no PR opened. Photo-lane background: [[photo-lane-generalise-2026-10-27]].

## Options put to Kent (diagnosis pick: 1)
1. Do nothing in code; accept preflight (already grade C + LETTERING_ILLEGIBLE + PHOTO_RESOLUTION_LOW). Cost 0. Catch: Studio default on this art stays unstable by size.
2. Two-tone veto 0.90 -> ~0.85 so MFab goes flat. Catch: gate 2 (needs a corpus run of `python -m tools.stage0_photo_gate`, all 39 rows, before any claim) and MFab's 0.856 is only 0.006 inside.
3. Photo-lane fix: keep thin white gaps from merging in SLIC consolidation at <5 px/mm. Larger, needs its own session.

**Decision (Kent, 2026-11-05): option 3.** A session is working on it; read its PR before starting anything here. Options 1 and 2 are not taken: the gates stay where they are.

**Why:** the defect is the lane's merge, so moving a gate would only hide it on this one logo.
**How to apply:** do not tune the grain gate or two-tone veto for MFab; do not blame the keyline recipe for the 60/101 mm blobs.
