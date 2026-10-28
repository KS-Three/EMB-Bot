# `keep_dark_thin_strokes` OFF | ON at the flip (2026-10-28)

Kent's ruling on #1170, 2026-10-28: **"Flip ON now (worker's pick)"**. This sheet is the flip itself: **ON is
the shipped default since #1172**, OFF is the engine before it (the flag set `False`, which `tests/conftest.py`
`PRE_FLIP` / `FLIP_2026_10_23` and `tests/engine_2026_10_27.json` pin). Open **`sheet.html`** (one
self-contained page, every image inline); the JPEGs beside it are the same tiles.

**How it was made.** `digitizer/tools/dark_ink_flip_sheet.py` (`run`, then `report --hero photo/owl_kent.jpg
art/logo_hotel_fremont_patch.png`), the Studio request at 80 mm `left_chest`
(`tools.fremont_triage.studio_request(80.0)`), shipped defaults, both arms setting the one flag explicitly.
Counts are the DST's own records (pystitch): stitches, TRIM records, colour blocks; regions from the plan. The
window rule is `tools.flip_sheet_renders`': needle points OFF and ON on a 0.05 mm grid as a multiset, the
18 x 11 mm window holding the most changed points, 40 px/mm. The two heroes get one window per dark-ink region
(`*__dark<i>_off.jpg`, `*__dark<i>_on.jpg`, `*__dark<i>_art.jpg`: OFF, ON and the artwork under the same
window), 16 for the owl and 14 for the Fremont patch; the read-by-read table with an on-ink verdict for each
is in #1172's body. **No pro file exists for any fixture here, so there is no pro column.**

## Every fixture (regions / stitches / trims / colour blocks, DST md5 OFF vs ON)

| fixture | stage 0 | OFF | ON | DST |
|---|---|---|---|---|
| photo/summit_badge.png | gradient | 42 / 29,799 / 33 / 11 | same | identical (the S's counter is refused, #1170) |
| photo/drone_render.png | gradient | 119 / 18,677 / 83 / 11 | 122 / 18,613 / 85 / 11 | moves |
| photo/logo_drone_thermal_badge.png | gradient | same bytes as drone_render.png (`cmp` equal) | same | moves |
| photo/logo_bridge_bar.jpg | gradient | 54 / 15,192 / 38 / 7 | 54 / 15,238 / 38 / 7 | moves |
| photo/logo_hotel_fremont.webp | gradient | 162 / 13,188 / 23 / 4 | 162 / 13,105 / 19 / 4 | moves |
| photo/owl_kent.jpg | gradient | 105 / 35,528 / 127 / 7 | 115 / 36,552 / 139 / 8 | moves (16 dark reads) |
| art/logo_hotel_fremont_patch.png | gradient | 86 / 19,001 / 33 / 3 | 76 / 18,838 / 35 / 4 | moves (14 dark reads; a 4th colour, Stone) |
| photo/logo_gaulke_roofing.png, logo_golden_tee.jpg, region_blobs.png, gradient_ramp_linear.png, gradient_ramp_radial.png, repro_gradient_white_icon.png, screenshot_phone_ui_golke.jpg | gradient | | | identical |
| art/logo_golke_roofing.png, logo_mfab_lc.png, logo_toat_beanie.png, logo_toat_machine.png | gradient | | | identical |
| photo/enthusiast_logo.png (flat), photo/photo_scene_stub.png (photo_scene) | controls | | | identical |

OFF here is main's engine after #1165 and #1171 (the owl's OFF counts differ from the 10-28 fixes sheet for
that reason, not for this flag). `sheet.json` carries every number above, the dark-ink regions per fixture with
the OFF regions they were cut from, and the colour blocks that changed.
