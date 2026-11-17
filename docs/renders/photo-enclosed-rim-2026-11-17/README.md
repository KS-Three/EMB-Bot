# MFab's missing white band above AND / LLC: `photo_enclosed_rim` already cures it (2026-11-17)

Prime-grader fault on `mfab_hat` (105 x 40 mm, hat_front): the white band along
the top of the small line's backing is a few loose threads over black above LLC
(93.0, 24.6 mm) and above the A and N of AND (12.0, 24.8 mm), and the white
outlines round WELDING are uneven (69, 30 mm). No code change: an OFF flag that
exists already does it. **Not flipped.** This folder is the evidence for the
flip question.

## Cause, stage by stage (cloud container, no `rembg_isolated`)

Column through the band above LLC, 0.25 mm per pixel (4 px/mm work grid):

| stage | white band there |
|---|---|
| source art | 5 px, 1.25 mm (y 4.09 to 5.34 mm) |
| stage 1 prep `p.rgb` | 5 px of white (252) |
| stage 1 `enclosed_mask` (the white the field is made of) | 3 px: the two edge rows fall out of the mask |
| stage 2 labels | edge rows go to the MAIN population (label 1), the middle 3 rows to the enclosed one (label 2) |
| stage 3 masks | the 1 px edge pieces are under the min-detail floor and are absorbed by the black; white keeps rows 101-103 (0.75 mm) |
| stage 4 polygon | white field 4.65 to 5.0 mm: 0.35 mm |
| stage 7 | a 0.35 mm strip cannot hold a satin loop or a fill row, so it sews as loose threads |

The same loss eats 1 px off each side of every enclosed white edge in the photo
lane, which is why the outlines round WELDING come out narrow and scalloped
as well as the band. A column above the A and N reads the same.
`cfg.photo_enclosed_rim` (built OFF 2026-11-06, `docs/photo-enclosed-rim-2026-11-06.md`)
is the fix for exactly this: the rim pixels of an enclosed ground rejoin its
population before the floor. Kent 2026-11-14: "Keep off, fix the collapse"; its
collapse at 35 to 40 mm and the three worse images are fixed behind the flag
since, and the white-loop width has its own key (`keyline_loop_fit`).

## Pictures (ORIGINAL | BEFORE flag OFF | AFTER flag ON, same frame)

- [`mfab_hat_whole.png`](mfab_hat_whole.png)
- [`mfab_hat_AND_zoom.png`](mfab_hat_AND_zoom.png): band above A and N
- [`mfab_hat_LLC_zoom.png`](mfab_hat_LLC_zoom.png): band above LLC
- [`mfab_hat_WELDING_zoom.png`](mfab_hat_WELDING_zoom.png): outlines round the letters

## What moved

Nine committed pro jobs (`tools.prime_grader.population()`), each run OFF and ON
through the Studio's request at its own width and garment: **1 of 9 moves**
(`mfab_hat`), **1 of 1 is pictured**. The other eight are byte-identical in their
stitch list (md5 of the stitch list OFF = ON): becker_hat_large, gaulke_roofing_hat,
hotel_fremont_hat, precision_drone, tires_hat_3d, goldentee_hat, toat_machine_hat,
toat_beanie.

| design | stitches OFF -> ON | trims OFF -> ON | by eye |
|---|---|---|---|
| `mfab_hat` | 20,846 -> 20,990 | 26 -> 18 | **Better.** The white band above AND and LLC is a solid white strip, as the art has it; the outlines round WELDING are wider and even; the A's white slit is wider. By eye the black small letters sit slightly heavier on the white (the band is back, so the black's share looks larger); nothing got worse that I can see. |

Not fixed by this flag: the LL pair of LLC is still busy, the M's inner mark
still sews as a ragged blob (separate faults on the scorecard).

## Limits

- **No cutout lane here.** This container has no `rembg_isolated`, so MFab ran
  without the background cutout Kent's machine uses. The mechanism above is in
  stage 1/2, before the cutout acts on the image, and the 2026-11-13 live-engine
  measurement read the flag on both lanes (`docs/photo-enclosed-rim-2026-11-06.md`
  addendum), but I did not run MFab through the cutout here. Re-run on Kent's
  machine before relying on the cutout arm.
- **Other widths.** The rim doc records the flag at 30 and 60 to 113.5 mm and its
  white M-FAB faces at 45 to 50 mm (the 0.6 mm keyline rule, waits on Kent). This
  folder is the 105 mm job only. At 105 mm the loop fits
  (`docs/keyline-loop-fit-2026-11-15.md`: fits from 70 mm).
- Stitch counts and trims are context, not a quality claim.
cat: /tmp/claude-0/-home-user-EMB-Bot/3d687838-2dd9-5938-bac4-c030d4c2d355/scratchpad/readme_add.md: No such file or directory

## Added 2026-11-17 for the director: other widths and the 26 fixtures

**This container has no `rembg_isolated`, so Kent's machine renders MFab with a
background cutout that none of these pictures have.**

### MFab at the widths the 2026-11-14 record flagged (flag OFF | ON, hat_front, Studio request)

ORIGINAL | BEFORE | AFTER, one picture per width. The pictures are small, so the
calls are of whole faces and loops, not single stitches.

| width | picture | stitches OFF -> ON | trims | by eye, ON |
|---|---|---|---|---|
| 45 mm | [`mfab_hat_45mm.png`](mfab_hat_45mm.png) | 4,958 -> 6,404 | 9 -> 13 | **Still wrong.** White loops are fat and the M-FAB faces are narrow slivers between them; the small line is a smear. OFF is also rough, but its faces are fuller. I call ON worse here. |
| 50 mm | [`mfab_hat_50mm.png`](mfab_hat_50mm.png) | 5,586 -> 7,174 | 9 -> 14 | **Still wrong.** Same: heavy white loops, thin faces, WELDING mangled. ON worse. |
| 60 mm | [`mfab_hat_60mm.png`](mfab_hat_60mm.png) | 7,861 -> 9,277 | 8 -> 15 | **Better.** The small line reads and its white backing is back; OFF mushes W-E-L. Loops still a little heavy, faces hold. |
| 80 mm | [`mfab_hat_80mm.png`](mfab_hat_80mm.png) | 13,637 -> 14,034 | 22 -> 20 | **Better.** OFF has a grey scribble where W and E should be; ON sews the small line cleanly with its white outline. |
| 105 mm | [`mfab_hat_whole.png`](mfab_hat_whole.png) and zooms | 20,846 -> 20,990 | 26 -> 18 | **Better** (above). |
| `mfab_lc` 96.7 mm, left_chest | none: ON is byte-identical to OFF | 17,906 = 17,906 | 23 = 23 | no change. |

So the 45-50 mm white-loop problem is **not** fixed by `photo_enclosed_rim` alone;
the record puts its fix behind `cfg.extra["keyline_loop_fit"]`, not run here.
Nothing was flipped.

### The 26 corpus fixtures (`tools.corpus_scorecard.FIXTURES`), 80 mm, left_chest

Studio request at 80 mm (`tools.fremont_triage.studio_request(80.0)`) with
`garment_id` left_chest, compared by md5 of `design["stitches"]`: **1 of 26 moves,
1 of 1 pictured, 25 byte-identical**; none worse.

| fixture | stitches OFF -> ON | trims | by eye, ON |
|---|---|---|---|
| `photo/summit_badge.png` ([`summit_badge_80mm.png`](summit_badge_80mm.png)) | 28,384 -> 26,960 | 41 = 41 | No visible change: ring, halves, spokes and both text lines read the same at this size. About 5% fewer stitches from a small difference in the lettering fill that I cannot see in the picture. |

Unmoved: bg_uncertain, logo_alpha, logo_whitebg, ribbon_curve, becker_marine_logo,
logo_script_tires, drone_render, enthusiast_logo, fur_ramp, gradient_ramp_linear,
gradient_ramp_radial, photo_chrome_specular, photo_dof_meadow, photo_grass_macro,
photo_owl_pale, photo_scene_stub, photo_subject_stub, photo_sunset_backlit,
region_blobs, repro_gradient_white_icon, logo_bridge_bar, logo_gaulke_roofing,
logo_golden_tee, logo_hotel_fremont, screenshot_phone_ui_golke.
