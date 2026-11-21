# flag sweep: `outline_redraw_native` OFF=false vs ON=true

44 runs (18 tripwire placements, 26 corpus fixtures): **28 moved**, 16 unchanged, 0 errored.

| run | moved | md5 off | md5 on | stitches | trims | jumps | needle-up mm | colours |
|---|---|---|---|---|---|---|---|---|
| becker_hat_large | no | `9a938b2a58` | `9a938b2a58` | 15958 | 17 | 49 | 442.9 | 2 |
| becker_lc_large | no | `f07fbadf67` | `f07fbadf67` | 14423 | 11 | 27 | 196.9 | 2 |
| becker_hat_small | no | `562db43334` | `562db43334` | 9847 | 12 | 34 | 263.9 | 2 |
| becker_chest_small | no | `fbb4a85131` | `fbb4a85131` | 9713 | 10 | 32 | 249.5 | 2 |
| becker_beanie | no | `ac3ab8557d` | `ac3ab8557d` | 13347 | 14 | 38 | 301.6 | 3 |
| gaulke_roofing_hat | yes | `97111fc67e` | `452a773691` | 6598 -> 6629 (+31) | 30 -> 29 (-1) | 59 -> 48 (-11) | 340.8 -> 223.3 (-117.5) | 1 |
| gaulke_roofing_lc | yes | `52aef87fb3` | `bb93494bc1` | 5379 -> 5326 (-53) | 23 -> 22 (-1) | 50 -> 49 (-1) | 219.3 -> 190.7 (-28.6) | 1 |
| gaulke_roofing_beanie | yes | `a7d75b075e` | `5914272e7e` | 7093 -> 7195 (+102) | 22 | 59 -> 56 (-3) | 276.9 -> 247.0 (-29.9) | 2 |
| hotel_fremont_hat | yes | `bb51365656` | `46f8908104` | 15169 -> 15177 (+8) | 26 -> 20 (-6) | 79 | 377.6 -> 356.5 (-21.1) | 4 |
| hotel_fremont_patch | yes | `49a7f46de6` | `16c4b64b59` | 14238 -> 14233 (-5) | 21 -> 22 (+1) | 82 -> 80 (-2) | 390.5 -> 368.8 (-21.7) | 4 |
| mfab_hat | no | `70f67f83b3` | `70f67f83b3` | 20516 | 23 | 68 | 580.1 | 3 |
| mfab_lc | no | `e177f551bc` | `e177f551bc` | 17564 | 17 | 60 | 505.4 | 3 |
| precision_drone | yes | `3c66b0fb23` | `2e0f4f7aab` | 13962 -> 14015 (+53) | 93 -> 94 (+1) | 192 -> 187 (-5) | 1460.2 -> 1405.9 (-54.3) | 8 |
| tires_hat_3d | yes | `3eb7b4d41b` | `38abc3597c` | 4638 -> 4611 (-27) | 7 -> 6 (-1) | 9 -> 10 (+1) | 68.6 -> 87.2 (+18.6) | 1 |
| goldentee_hat | yes | `08174a7530` | `ec995defd0` | 9932 -> 10040 (+108) | 48 -> 49 (+1) | 93 -> 97 (+4) | 642.8 -> 664.7 (+21.9) | 6 |
| toat_machine_hat | no | `b2e856d3bb` | `b2e856d3bb` | 17086 | 17 | 45 | 263.7 | 2 |
| toat_machine_beanie | no | `69ae08317a` | `69ae08317a` | 16824 | 18 | 48 | 366.2 | 3 |
| toat_beanie | no | `64aa51d5c3` | `64aa51d5c3` | 17147 | 25 | 41 | 224.1 | 3 |
| corpus:bg_uncertain.png | no | `f81b90d5e4` | `f81b90d5e4` | 11803 | 3 | 15 | 121.3 | 2 |
| corpus:logo_alpha.png | yes | `3ec2cdc9dd` | `758bb00296` | 6302 -> 6340 (+38) | 3 -> 4 (+1) | 19 | 174.0 -> 170.6 (-3.4) | 5 |
| corpus:logo_whitebg.png | yes | `638cacb3ec` | `62564833b9` | 6828 -> 6843 (+15) | 3 | 22 -> 21 (-1) | 206.5 -> 186.4 (-20.1) | 6 |
| corpus:ribbon_curve.png | yes | `0942ad4f2f` | `31b6c85ad8` | 1020 -> 1025 (+5) | 0 | 3 | 0.0 | 1 |
| corpus:photo/drone_render.png | yes | `ed8d87f56a` | `5869d8b3a1` | 18362 -> 18361 (-1) | 103 -> 104 (+1) | 223 -> 238 (+15) | 1831.0 -> 1997.7 (+166.7) | 9 |
| corpus:photo/enthusiast_logo.png | yes | `b5a9d90997` | `df364758a0` | 2388 -> 2367 (-21) | 7 -> 8 (+1) | 35 -> 37 (+2) | 114.7 -> 122.8 (+8.1) | 2 |
| corpus:photo/fur_ramp.png | yes | `d07936d48e` | `4d6fa4318f` | 7217 -> 7225 (+8) | 2 | 21 -> 22 (+1) | 224.6 -> 226.3 (+1.7) | 6 |
| corpus:photo/gradient_ramp_linear.png | no | `125c30256d` | `125c30256d` | 11054 | 1 | 14 | 128.5 | 5 |
| corpus:photo/gradient_ramp_radial.png | no | `ae0df322ce` | `ae0df322ce` | 18642 | 1 | 19 | 161.0 | 5 |
| corpus:photo/photo_chrome_specular.png | yes | `51756aa3e8` | `49fd0ffe54` | 36844 -> 37212 (+368) | 84 -> 85 (+1) | 214 -> 212 (-2) | 1864.4 -> 1784.7 (-79.7) | 6 |
| corpus:photo/photo_dof_meadow.png | yes | `dcff66292b` | `f7af94ffac` | 21719 -> 21850 (+131) | 51 -> 48 (-3) | 178 -> 174 (-4) | 933.9 -> 914.8 (-19.1) | 5 |
| corpus:photo/photo_grass_macro.png | yes | `3764649d60` | `240a3eac75` | 4013 -> 4027 (+14) | 9 -> 11 (+2) | 24 -> 28 (+4) | 196.8 -> 248.7 (+51.9) | 2 |
| corpus:photo/photo_owl_pale.png | yes | `9dc92d3205` | `3d28312ca5` | 25283 -> 25259 (-24) | 4 -> 5 (+1) | 11 -> 19 (+8) | 88.1 -> 173.6 (+85.5) | 3 |
| corpus:photo/photo_scene_stub.png | yes | `158e0b7360` | `30f61c0b25` | 23655 -> 23298 (-357) | 70 -> 75 (+5) | 179 -> 196 (+17) | 1595.0 -> 1720.9 (+125.9) | 5 |
| corpus:photo/photo_subject_stub.png | no | `c9f3d27c51` | `c9f3d27c51` | 3187 | 0 | 4 | 2.8 | 1 |
| corpus:photo/photo_sunset_backlit.png | yes | `9bf4099e54` | `5fabdbf6b9` | 26798 -> 26878 (+80) | 90 -> 98 (+8) | 362 -> 395 (+33) | 1580.7 -> 1696.2 (+115.5) | 5 |
| corpus:photo/region_blobs.png | yes | `e7d650da66` | `2fb39228d4` | 19318 -> 19210 (-108) | 20 -> 19 (-1) | 51 -> 52 (+1) | 501.0 -> 512.7 (+11.7) | 6 |
| corpus:photo/repro_gradient_white_icon.png | yes | `5fa820046e` | `b8b02d8d1a` | 22930 -> 22103 (-827) | 10 -> 11 (+1) | 41 -> 48 (+7) | 409.7 -> 517.6 (+107.9) | 5 |
| corpus:photo/summit_badge.png | yes | `96e9f9814f` | `31d33aa64a` | 28990 -> 27550 (-1440) | 33 -> 27 (-6) | 117 -> 108 (-9) | 902.7 -> 856.2 (-46.5) | 8 -> 6 (-2) |
| corpus:becker_marine_logo.png | no | `df01b96dd9` | `df01b96dd9` | 10897 | 13 | 32 | 246.9 | 2 |
| corpus:logo_script_tires.png | yes | `bbbf7d3982` | `fb05dc562b` | 2820 -> 2709 (-111) | 4 -> 5 (+1) | 9 -> 5 (-4) | 76.8 -> 32.9 (-43.9) | 1 |
| corpus:photo/logo_bridge_bar.jpg | no | `22f2b147ed` | `22f2b147ed` | 10465 | 16 | 30 | 198.9 | 4 |
| corpus:photo/logo_gaulke_roofing.png | yes | `ad50c07997` | `6f3bbed996` | 4832 -> 4810 (-22) | 20 -> 18 (-2) | 46 -> 48 (+2) | 178.5 -> 191.4 (+12.9) | 1 |
| corpus:photo/logo_golden_tee.jpg | yes | `a1f421da1d` | `d50b24281a` | 10875 -> 10897 (+22) | 56 -> 49 (-7) | 97 -> 90 (-7) | 674.0 -> 606.0 (-68) | 6 |
| corpus:photo/logo_hotel_fremont.webp | yes | `56d71b86b1` | `dd8d2ece03` | 12175 -> 12169 (-6) | 28 | 111 | 363.4 -> 363.8 (+0.4) | 4 |
| corpus:photo/screenshot_phone_ui_golke.jpg | yes | `8c5832a443` | `2c1240d054` | 10723 -> 10697 (-26) | 107 -> 116 (+9) | 387 -> 386 (-1) | 2547.9 -> 2612.9 (+65) | 6 |
