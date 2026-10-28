# `dark_ink_refuse_strays` OFF | ON (2026-10-28)

Kent's ruling on #1172, 2026-10-28: **"Keep ON, queue refusal (worker's pick)"**. This sheet is the refusal,
built OFF: **OFF is today's main** (`keep_dark_thin_strokes` ON since #1172, the flag `False`), **ON is the
refusal** (`dark_ink_refuse_strays=True`). Open **`sheet.html`** (one self-contained page, every image
inline); the JPEGs beside it are the same tiles.

**The rule** (`digitizer_core/thin_ink.py`, `stray_clause`, one gated line in `find_dark_thin_ink`): a kept
dark component is refused when (a) its bbox lies within `DARK_INK_EDGE_PX` = guard + ring = 4 px of the
artwork's bounding box at the sent width (`p.art_bbox`): its one-ground test ran on part of a ring; or (b)
fewer than `DARK_INK_STRAY_SHARE` = 0.5 of its own pixels sit `DARK_INK_DEPTH_L` = 8 L* under the ring's
median, the black-hat's pixel test re-asked of the component as a whole.

**How it was made.** `digitizer/tools/dark_ink_flip_sheet.py` (`run --flag dark_ink_refuse_strays`, then
`report --flag dark_ink_refuse_strays --hero photo/owl_kent.jpg art/logo_hotel_fremont_patch.png
photo/summit_badge.png`), the Studio request at 80 mm `left_chest` (`tools.fremont_triage.studio_request(80.0)`),
shipped defaults, both arms setting the one flag explicitly. Counts are the DST's own records (pystitch):
stitches, TRIM records, colour blocks; regions from the plan. The heroes get one window per dark-ink read of
OFF (`*__dark<i>_off.jpg`, `*__dark<i>_on.jpg`, `*__dark<i>_art.jpg`: OFF, ON and the artwork under the same
window), the ON tile labelled `kept` or `REFUSED`: 16 for the owl, 14 for the Fremont patch, none for
summit_badge (it carves nothing). **No pro file exists for any fixture here, so there is no pro column.**

**The artwork window is fixed with this sheet.** The 2026-10-28 flip sheet's `_art_crop` clipped a window
that ran past the artwork's edge and stretched what was left to the whole window, so every edge window's
artwork sat shifted inward against the OFF and ON renders beside it. The 10 reads #1172's table judged
"not ink" are the 10 components within 1 px of the frame; under a padded window (mid grey past the edge)
the owl's left-edge Blackberry columns sit on a dark feather streak and its bottom-edge Dark Rattan bits on
dark blotches, and the patch's two "black blobs in the white gap" are the chevron's lower black band where
the frame cuts it. Measured on the engine's own raster (Lab, the space the tails read), all 30 reads are
11-98 L* darker than their ring's median with 0.75-1.0 of their pixels 8 L* under it, so clause (b) fires on
none of them; clause (a) refuses the 10 and the two "mixed" reads at the frame.

## Every fixture (regions / stitches / trims / colour blocks, DST md5 OFF vs ON)

| fixture | stage 0 | OFF (= main) | ON (refusal) | DST |
|---|---|---|---|---|
| photo/summit_badge.png | gradient | 42 / 29,799 / 33 / 11 | same | identical (the control: nothing carved, nothing to refuse) |
| photo/owl_kent.jpg | gradient | 115 / 36,552 / 139 / 8 | 109 / 36,036 / 132 / 9 | moves (16 dark reads, 10 refused: `edge`) |
| art/logo_hotel_fremont_patch.png | gradient | 76 / 18,838 / 35 / 4 | 74 / 19,082 / 30 / 4 | moves (14 dark reads, 2 refused: `edge`) |
| photo/drone_render.png, logo_drone_thermal_badge.png (same bytes), logo_bridge_bar.jpg, logo_hotel_fremont.webp, logo_gaulke_roofing.png, logo_golden_tee.jpg, region_blobs.png, gradient_ramp_linear.png, gradient_ramp_radial.png, repro_gradient_white_icon.png, screenshot_phone_ui_golke.jpg | gradient | | | identical |
| art/logo_golke_roofing.png, logo_mfab_lc.png, logo_toat_beanie.png, logo_toat_machine.png | gradient | | | identical |
| photo/enthusiast_logo.png (flat), photo/photo_scene_stub.png (photo_scene) | controls | | | identical |

OFF here is main a71fd5cd (#1172 merged): the owl's and the patch's OFF counts are #1172's ON counts to the
stitch. `sheet.json` carries every number above.
