# `keep_dark_thin_strokes` OFF | ON on our own fixtures (2026-10-28)

PR #1160 built `cfg.keep_dark_thin_strokes` OFF and named `testdata/photo/summit_badge.png`
as the fixture to look at before any flip (ON took it from 13 to 11 colour blocks). This is
that look, plus every other fixture in the repo whose DST moves ON, so the flip is judged on
its whole blast radius. Open **`sheet.html`** (one self-contained page, every image inline);
the JPEGs beside it are the same tiles.

**How it was made.** `digitizer/tools/dark_ink_flip_sheet.py` (`run`, then `report`), engine
`1ce2af22` (main at the time), the Studio request at 80 mm `left_chest`
(`tools.fremont_triage.studio_request(80.0)`), shipped defaults. OFF is the default; ON sets
the one flag. Counts are the DST's own records (pystitch): stitches, TRIM records, colour
blocks; regions from the plan. The crop rule is `tools.flip_sheet_renders`': needle points
OFF and ON on a 0.05 mm grid as a multiset, the 18 x 11 mm window holding the most changed
points, 40 px/mm. **No pro file exists for any of these fixtures, so there is no pro column.**

## summit_badge (gradient; a synthetic badge)

| | OFF | ON |
|---|---|---|
| regions | 42 | 43 (1 `dark_ink`) |
| stitches | 31,057 | 29,802 |
| trims (DST) | 36 | 40 |
| colour blocks | 12 | 10 |
| distinct threads | 6 | 6 |
| DST md5 | `01da6626…` | `28840c9b…` |

ON reads ONE dark-ink stroke: `Sccd9bce6`, 2.58 mm² at x -14.2..-11.8 / y 29.7..31.5 mm, the
dark ground inside the lower bowl of the S of SUMMIT (tile `dark0_art` is the artwork at that
window). OFF that patch was already sewn in `4174 Charcoal` as part of the background region
(2.56 of its 2.58 mm²); ON sews it as a 152-point Charcoal bean run. Same thread, so nothing
new shows there.

What does show: the badge's background (`Scd5f9d89`, 2,776 mm², a radial vignette) loses two
of its blend bands. The per-region blend path reads a region's shade count off its two extreme
pixels, and the carve takes the darkest pixel out of the region: the extremes' distance falls
from 60.4 to 28.3 dE00 (probe, `stage6_blend._choose_shade_count`), bands 5 -> 4, and the band
threads go from Armour / Navajo / Charcoal / Charcoal / Whale to Armour / Charcoal / Charcoal /
Charcoal. `0128 Navajo` (3,133 st) and `0111 Whale` (2,902 st) are the two colour blocks that
vanish; their stitches land in Charcoal (7,786 -> 12,101) and Armour (4,044 -> 4,504). The
`whole_off` / `whole_on` tiles show it at viewing size: four concentric greys OFF, a flat
Charcoal ground with one Armour ring ON.

## Every fixture (DST md5 OFF vs ON)

The flag acts on the gradient class only (`pipeline.run_stages`); every image fixture under
`testdata/photo` and `testdata/art` was classified and digitized both ways, with one flat and
one photo_scene fixture as controls. `logo_mfab_hat.png` (photo_scene, needs the rembg venv)
was not run. `logo_drone_thermal_badge.png` is `drone_render.png` byte for byte, so it counts
once.

| fixture | stage 0 | OFF regions / st / tr / blocks / threads | ON | DST |
|---|---|---|---|---|
| photo/summit_badge.png | gradient | 42 / 31,057 / 36 / 12 / 6 | 43 / 29,802 / 40 / 10 / 6 | **moves** |
| photo/drone_render.png (= logo_drone_thermal_badge.png) | gradient | 119 / 18,671 / 83 / 11 / 7 | 122 / 18,607 / 85 / 11 / 7 | **moves**: 3 dark-ink regions of 1.3-1.5 mm² (Darkest Blue, out of Silver) |
| photo/logo_bridge_bar.jpg | gradient | 54 / 15,192 / 38 / 7 / 6 | 54 / 15,238 / 38 / 7 / 6 | **moves**: 1 region, 10.2 mm² Scotty Green (8.4 from green, 1.7 from Sun) |
| photo/logo_hotel_fremont.webp | gradient | 162 / 13,509 / 22 / 4 / 3 | 162 / 13,515 / 20 / 4 / 3 | **moves**: 156 regions re-owned as dark ink, same threads |
| photo/owl_kent.jpg | gradient | 105 / 35,665 / 129 / 12 / 6 | 115 / 36,587 / 139 / 11 / 6 | **moves**: 16 dark-ink regions, +922 st, +10 trims |
| photo/screenshot_phone_ui_golke.jpg | gradient | 149 / 8,429 / 49 / 8 / 6 | 149 / 8,437 / 49 / 8 / 6 | **moves**: 1 region, 0.86 mm² Whale |
| art/logo_hotel_fremont_patch.png | gradient | 86 / 18,979 / 35 / 3 / 3 | 76 / 18,788 / 34 / 4 / 4 | **moves**: 14 dark-ink regions; a NEW thread `0873 Stone` (532 st, one more stop) |
| photo/logo_gaulke_roofing.png | gradient | 53 / 5,097 / 13 / 3 / 3 | same | byte-identical |
| photo/logo_golden_tee.jpg | gradient | 46 / 12,850 / 28 / 9 / 6 | same | byte-identical |
| photo/region_blobs.png | gradient | 3 / 19,938 / 4 / 11 / 11 | same | byte-identical |
| photo/gradient_ramp_linear.png | gradient | 1 / 10,952 / 1 / 6 / 6 | same | byte-identical |
| photo/gradient_ramp_radial.png | gradient | 1 / 17,761 / 5 / 5 / 5 | same | byte-identical |
| photo/repro_gradient_white_icon.png | gradient | 6 / 22,017 / 6 / 6 / 6 | same | byte-identical |
| art/logo_golke_roofing.png | gradient | 60 / 5,488 / 23 / 2 / 2 | same | byte-identical |
| art/logo_mfab_lc.png | gradient | 59 / 13,704 / 15 / 3 / 3 | same | byte-identical |
| art/logo_toat_beanie.png | gradient | 45 / 15,342 / 15 / 2 / 2 | same | byte-identical |
| art/logo_toat_machine.png | gradient | 40 / 15,824 / 18 / 2 / 2 | same | byte-identical |
| photo/enthusiast_logo.png (control) | flat | 31 / 2,422 / 7 / 2 / 2 | same | byte-identical |
| photo/photo_scene_stub.png (control) | photo_scene | 54 / 29,497 / 52 / 6 / 6 | same | byte-identical |

Seven fixtures move (eight files), ten gradient fixtures and both controls are byte-identical.
`sheet.json` carries every number above, the dark-ink regions per fixture with the OFF regions
they were cut from, and the colour blocks that changed.

Nothing here changes an engine default; the flip is Kent's.
