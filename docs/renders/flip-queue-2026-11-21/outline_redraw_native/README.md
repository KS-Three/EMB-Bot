Moved: 28 of 44 runs; pictured: 8.

# `outline_redraw_native`: flip-readiness evidence, 2026-11-21

**What it does** (`PipelineConfig.outline_redraw_native`, built OFF 2026-11-14,
`digitizer_core/config.py`, memory `jag-source-2026-11-13`, `curve-facets-2026-11-14`).
`outline_redraw_k` is already ON at 0.75 (Kent's flip, 2026-11-14), but it only
redraws uploads that stage 1 upscaled. This flag also applies it to a source at
its own resolution, in arcs-only mode: runs that one circle explains (bowls,
circles) are rewritten as true arcs, while straight runs and corners keep
stage 4's vertices. It targets stage 4's 12-20 degree chord facets (18 of
Kent's 49 "smooth" pins). **The builder's own note: "Default OFF because ...
the Column lane's satin answered unpredictably"** (and_pizza, 2026-11-13:
smoother on some bowls, a straight cut across the p's arc on others).

**The sweep.** `python -m tools.flag_sweep --flag outline_redraw_native --pictures`
on `main` at `2d4e132e`. All 44 runs finished, with 0 errors. 28 moved: 8 of
the 18 tripwire placements and 20 of the 26 corpus fixtures. The five Becker
placements and both MFab placements are byte-identical, because those uploads
are upscaled and `outline_redraw_k` already redraws them.

- `gaulke_roofing_hat`: stitches 6598 -> 6629 (+31) ; trims 30 -> 29 (-1) ; jumps 59 -> 48 (-11) ; needle-up mm 340.8 -> 223.3 (-117.5) 
- `gaulke_roofing_lc`: stitches 5379 -> 5326 (-53) ; trims 23 -> 22 (-1) ; jumps 50 -> 49 (-1) ; needle-up mm 219.3 -> 190.7 (-28.6) 
- `gaulke_roofing_beanie`: stitches 7093 -> 7195 (+102) ; trims 22 ; jumps 59 -> 56 (-3) ; needle-up mm 276.9 -> 247.0 (-29.9) 
- `hotel_fremont_hat`: stitches 15169 -> 15177 (+8) ; trims 26 -> 20 (-6) ; jumps 79 ; needle-up mm 377.6 -> 356.5 (-21.1) 
- `hotel_fremont_patch`: stitches 14238 -> 14233 (-5) ; trims 21 -> 22 (+1) ; jumps 82 -> 80 (-2) ; needle-up mm 390.5 -> 368.8 (-21.7) 
- `precision_drone`: stitches 13962 -> 14015 (+53) ; trims 93 -> 94 (+1) ; jumps 192 -> 187 (-5) ; needle-up mm 1460.2 -> 1405.9 (-54.3) 
- `tires_hat_3d`: stitches 4638 -> 4611 (-27) ; trims 7 -> 6 (-1) ; jumps 9 -> 10 (+1) ; needle-up mm 68.6 -> 87.2 (+18.6) 
- `goldentee_hat`: stitches 9932 -> 10040 (+108) ; trims 48 -> 49 (+1) ; jumps 93 -> 97 (+4) ; needle-up mm 642.8 -> 664.7 (+21.9) 
- `corpus:logo_alpha.png`: stitches 6302 -> 6340 (+38) ; trims 3 -> 4 (+1) ; jumps 19 ; needle-up mm 174.0 -> 170.6 (-3.4) 
- `corpus:logo_whitebg.png`: stitches 6828 -> 6843 (+15) ; trims 3 ; jumps 22 -> 21 (-1) ; needle-up mm 206.5 -> 186.4 (-20.1) 
- `corpus:ribbon_curve.png`: stitches 1020 -> 1025 (+5) ; trims 0 ; jumps 3 ; needle-up mm 0.0 
- `corpus:photo/drone_render.png`: stitches 18362 -> 18361 (-1) ; trims 103 -> 104 (+1) ; jumps 223 -> 238 (+15) ; needle-up mm 1831.0 -> 1997.7 (+166.7) 
- `corpus:photo/enthusiast_logo.png`: stitches 2388 -> 2367 (-21) ; trims 7 -> 8 (+1) ; jumps 35 -> 37 (+2) ; needle-up mm 114.7 -> 122.8 (+8.1) 
- `corpus:photo/fur_ramp.png`: stitches 7217 -> 7225 (+8) ; trims 2 ; jumps 21 -> 22 (+1) ; needle-up mm 224.6 -> 226.3 (+1.7) 
- `corpus:photo/photo_chrome_specular.png`: stitches 36844 -> 37212 (+368) ; trims 84 -> 85 (+1) ; jumps 214 -> 212 (-2) ; needle-up mm 1864.4 -> 1784.7 (-79.7) 
- `corpus:photo/photo_dof_meadow.png`: stitches 21719 -> 21850 (+131) ; trims 51 -> 48 (-3) ; jumps 178 -> 174 (-4) ; needle-up mm 933.9 -> 914.8 (-19.1) 
- `corpus:photo/photo_grass_macro.png`: stitches 4013 -> 4027 (+14) ; trims 9 -> 11 (+2) ; jumps 24 -> 28 (+4) ; needle-up mm 196.8 -> 248.7 (+51.9) 
- `corpus:photo/photo_owl_pale.png`: stitches 25283 -> 25259 (-24) ; trims 4 -> 5 (+1) ; jumps 11 -> 19 (+8) ; needle-up mm 88.1 -> 173.6 (+85.5) 
- `corpus:photo/photo_scene_stub.png`: stitches 23655 -> 23298 (-357) ; trims 70 -> 75 (+5) ; jumps 179 -> 196 (+17) ; needle-up mm 1595.0 -> 1720.9 (+125.9) 
- `corpus:photo/photo_sunset_backlit.png`: stitches 26798 -> 26878 (+80) ; trims 90 -> 98 (+8) ; jumps 362 -> 395 (+33) ; needle-up mm 1580.7 -> 1696.2 (+115.5) 
- `corpus:photo/region_blobs.png`: stitches 19318 -> 19210 (-108) ; trims 20 -> 19 (-1) ; jumps 51 -> 52 (+1) ; needle-up mm 501.0 -> 512.7 (+11.7) 
- `corpus:photo/repro_gradient_white_icon.png`: stitches 22930 -> 22103 (-827) ; trims 10 -> 11 (+1) ; jumps 41 -> 48 (+7) ; needle-up mm 409.7 -> 517.6 (+107.9) 
- `corpus:photo/summit_badge.png`: stitches 28990 -> 27550 (-1440) ; trims 33 -> 27 (-6) ; jumps 117 -> 108 (-9) ; needle-up mm 902.7 -> 856.2 (-46.5) 
- `corpus:logo_script_tires.png`: stitches 2820 -> 2709 (-111) ; trims 4 -> 5 (+1) ; jumps 9 -> 5 (-4) ; needle-up mm 76.8 -> 32.9 (-43.9) 
- `corpus:photo/logo_gaulke_roofing.png`: stitches 4832 -> 4810 (-22) ; trims 20 -> 18 (-2) ; jumps 46 -> 48 (+2) ; needle-up mm 178.5 -> 191.4 (+12.9) 
- `corpus:photo/logo_golden_tee.jpg`: stitches 10875 -> 10897 (+22) ; trims 56 -> 49 (-7) ; jumps 97 -> 90 (-7) ; needle-up mm 674.0 -> 606.0 (-68) 
- `corpus:photo/logo_hotel_fremont.webp`: stitches 12175 -> 12169 (-6) ; trims 28 ; jumps 111 ; needle-up mm 363.4 -> 363.8 (+0.4) 
- `corpus:photo/screenshot_phone_ui_golke.jpg`: stitches 10723 -> 10697 (-26) ; trims 107 -> 116 (+9) ; jumps 387 -> 386 (-1) ; needle-up mm 2547.9 -> 2612.9 (+65) 

Totals across the 28: trims +6 net (largest rises: `photo_sunset_backlit` +8,
`screenshot_phone_ui_golke` +9, `photo_scene_stub` +5; largest falls:
`goldentee` corpus -7, `hotel_fremont_hat` -6, `summit_badge` -6). Needle-up
falls by over 100 mm on `gaulke_roofing_hat` and rises by over 100 mm on
`drone_render`, `photo_scene_stub`, `photo_sunset_backlit` and
`repro_gradient_white_icon`. `summit_badge` sews 2 fewer colours (8 -> 6).

**By-eye read against the original art.** Each picture is ORIGINAL | BEFORE |
AFTER. The `zoom_*` files are BEFORE left, AFTER right, at the spots the
0.6 mm change locator found.

- **`gaulke_roofing_beanie`: better.** The "&" in STEEL ROOFING & SUPPLY. BEFORE
  sews only its lower half, and the top loop the art has is missing. AFTER
  sews the whole ampersand (`zoom_gaulke_roofing_beanie_z0.png`).
- **`gaulke_roofing_hat`: better.** Its "&" is fuller and rounder, closer to the
  art, and the G's bar is cleaner (`zoom_gaulke_roofing_hat_amp.png`).
  Needle-up is down 117 mm. The roof and sun are the same.
- **`region_blobs` (corpus): worse.** AFTER opens a white seam between the
  pink and blue blobs, and one long travel stitch lies across the blue ring
  (`zoom_region_blobs_z1.png`). The pink blob's outer edge goes from ragged to
  round, which is neither closer nor further from the art's soft gradient.
  Colours also shift: the green is lighter, the blue darker.
- **`hotel_fremont_hat`: worse, slightly.** Where a tan stroke meets the
  black, AFTER leaves a small lump of short tan stitches the art does not have
  (`zoom_hotel_fremont_hat_z0.png`). Trims fall 26 -> 20.
- `summit_badge` (corpus): same. The "U" bowl turns as one fan in AFTER where
  BEFORE turned in steps (`zoom_summit_badge_z0.png`). It reads slightly
  rounder, and is no closer to the art at print size. 2 fewer colours.
- `goldentee_hat`: same. The L's black shadow edge thickens a little.
- `tires_hat_3d`: same. The script's outline is smoother in a few places;
  nothing changes at print size.
- `precision_drone`: same at print size.
- The 20 unpictured movers: I read each diff's boxes. Except `photo_scene_stub`
  (a re-split of the water tones, same at print size, +5 trims) and
  `photo_grass_macro` (same, +52 mm needle-up), the changes are under 2 mm
  and local.

**Verdict: mixed.** Two clear improvements (Gaulke's "&" on hat and beanie).
Two worse: `region_blobs` (white seam and a travel stitch across the blue)
and `hotel_fremont_hat` (a small lump at a junction). The rest look the same
at print size. Trims and needle-up rise on four photo fixtures. Those
fixtures are not this flag's target, but they still move.

Files: eight ORIGINAL | BEFORE | AFTER strips, five `zoom_*` crops, `sweep.md`.
The originals are art already in the repo (`Embroidery Files.zip` and the
corpus fixtures). No pro stitch file is rendered.
