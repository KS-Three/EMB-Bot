# flag sweep: `extra.lettering_columns_a_bar` OFF=false vs ON=true

Context `--set`: `{"extra.lettering_columns_block_butt": true}` (both arms)

44 runs (18 tripwire placements, 26 corpus fixtures): **6 moved**, 38 unchanged, 0 errored.

| run | moved | md5 off | md5 on | stitches | trims | jumps | needle-up mm | colours |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | yes | `b7d9faaea4` | `c30ba7b9a9` | 15820 -> 15800 (-20) | 18 | 53 | 508.6 | 2 |
| becker_lc_large | yes | `71b6c32947` | `8c9e137caf` | 14291 -> 14296 (+5) | 13 -> 14 (+1) | 30 -> 32 (+2) | 236.8 -> 244.6 (+7.8) | 2 |
| becker_hat_small | yes | `59d453bd12` | `7d3dbfe75d` | 10165 -> 10144 (-21) | 9 | 35 | 304.4 | 2 |
| becker_chest_small | yes | `d3a1d181de` | `69e1f55d8a` | 10039 -> 10018 (-21) | 7 | 33 | 300.6 | 2 |
| becker_beanie | yes | `d0c32a6ea5` | `ce967c3f31` | 13619 -> 13589 (-30) | 12 | 41 -> 42 (+1) | 376.8 -> 369.4 (-7.4) | 3 |
| gaulke_roofing_hat | no | `e8938c6e21` | `e8938c6e21` | 6618 | 30 | 59 | 341.0 | 1 |
| gaulke_roofing_lc | no | `1e1208439d` | `1e1208439d` | 5379 | 23 | 50 | 219.6 | 1 |
| gaulke_roofing_beanie | no | `eb7beca0da` | `eb7beca0da` | 7124 | 22 | 59 | 277.1 | 2 |
| hotel_fremont_hat | no | `8692d2d22e` | `8692d2d22e` | 15167 | 26 | 79 | 377.2 | 4 |
| hotel_fremont_patch | no | `c5037db3a9` | `c5037db3a9` | 14165 | 19 | 82 | 398.6 | 4 |
| mfab_hat | no | `5093d04371` | `5093d04371` | 20564 | 22 | 80 | 741.9 | 3 |
| mfab_lc | no | `54ed7b8166` | `54ed7b8166` | 17570 | 17 | 60 | 504.9 | 3 |
| precision_drone | no | `839ad27013` | `839ad27013` | 13966 | 93 | 196 | 1557.2 | 9 |
| tires_hat_3d | no | `f8ac955e9b` | `f8ac955e9b` | 4644 | 7 | 11 | 71.3 | 1 |
| goldentee_hat | no | `7b6c3f8060` | `7b6c3f8060` | 10583 | 45 | 91 | 644.9 | 7 |
| toat_machine_hat | no | `da817e2430` | `da817e2430` | 17100 | 18 | 45 | 267.9 | 2 |
| toat_machine_beanie | no | `de337834a6` | `de337834a6` | 16862 | 16 | 45 | 323.6 | 3 |
| toat_beanie | no | `55a54f4e50` | `55a54f4e50` | 17193 | 25 | 42 | 233.6 | 3 |
| corpus:bg_uncertain.png | no | `0c8bafd552` | `0c8bafd552` | 11790 | 3 | 15 | 122.4 | 2 |
| corpus:logo_alpha.png | no | `3647423156` | `3647423156` | 6391 | 3 | 19 | 174.7 | 5 |
| corpus:logo_whitebg.png | no | `2663dc018b` | `2663dc018b` | 6917 | 3 | 22 | 207.1 | 6 |
| corpus:ribbon_curve.png | no | `0942ad4f2f` | `0942ad4f2f` | 1020 | 0 | 3 | 0.0 | 1 |
| corpus:photo/drone_render.png | no | `1c28933040` | `1c28933040` | 18417 | 97 | 239 | 2036.2 | 10 |
| corpus:photo/enthusiast_logo.png | no | `c1a09b9357` | `c1a09b9357` | 2469 | 8 | 35 | 117.8 | 2 |
| corpus:photo/fur_ramp.png | no | `056940c0b9` | `056940c0b9` | 7240 | 3 | 17 | 153.9 | 5 |
| corpus:photo/gradient_ramp_linear.png | no | `125c30256d` | `125c30256d` | 11054 | 1 | 14 | 128.5 | 5 |
| corpus:photo/gradient_ramp_radial.png | no | `611e3b79b7` | `611e3b79b7` | 18721 | 1 | 15 | 112.7 | 5 |
| corpus:photo/photo_chrome_specular.png | no | `f74a8aad81` | `f74a8aad81` | 36783 | 83 | 215 | 1852.2 | 6 |
| corpus:photo/photo_dof_meadow.png | no | `bdfb3b8510` | `bdfb3b8510` | 22253 | 47 | 186 | 937.5 | 5 |
| corpus:photo/photo_grass_macro.png | no | `f3d3be5c01` | `f3d3be5c01` | 4018 | 9 | 24 | 196.8 | 2 |
| corpus:photo/photo_owl_pale.png | no | `b4bb7c04cb` | `b4bb7c04cb` | 24982 | 4 | 11 | 86.0 | 3 |
| corpus:photo/photo_scene_stub.png | no | `abbce67b0f` | `abbce67b0f` | 22287 | 81 | 179 | 1515.5 | 5 |
| corpus:photo/photo_subject_stub.png | no | `c9f3d27c51` | `c9f3d27c51` | 3187 | 0 | 4 | 2.8 | 1 |
| corpus:photo/photo_sunset_backlit.png | no | `443ccf3131` | `443ccf3131` | 27336 | 106 | 409 | 1705.2 | 5 |
| corpus:photo/region_blobs.png | no | `fe55177a93` | `fe55177a93` | 19356 | 20 | 52 | 500.1 | 6 |
| corpus:photo/repro_gradient_white_icon.png | no | `5fa820046e` | `5fa820046e` | 22930 | 10 | 41 | 409.7 | 5 |
| corpus:photo/summit_badge.png | no | `5adcd66ba8` | `5adcd66ba8` | 28995 | 33 | 117 | 905.0 | 8 |
| corpus:becker_marine_logo.png | yes | `d70dedab28` | `2432b1c697` | 11145 -> 11132 (-13) | 14 -> 13 (-1) | 41 -> 40 (-1) | 361.0 -> 355.0 (-6) | 2 |
| corpus:logo_script_tires.png | no | `8a54520c03` | `8a54520c03` | 2807 | 5 | 6 | 54.9 | 1 |
| corpus:photo/logo_bridge_bar.jpg | no | `16fb49b80b` | `16fb49b80b` | 10599 | 15 | 30 | 217.6 | 4 |
| corpus:photo/logo_gaulke_roofing.png | no | `f16139ca34` | `f16139ca34` | 4859 | 20 | 46 | 178.9 | 1 |
| corpus:photo/logo_golden_tee.jpg | no | `9667030b93` | `9667030b93` | 11868 | 51 | 102 | 692.6 | 7 |
| corpus:photo/logo_hotel_fremont.webp | no | `56d71b86b1` | `56d71b86b1` | 12175 | 28 | 111 | 363.4 | 4 |
| corpus:photo/screenshot_phone_ui_golke.jpg | no | `45a8420d65` | `45a8420d65` | 10856 | 108 | 383 | 2446.4 | 6 |
