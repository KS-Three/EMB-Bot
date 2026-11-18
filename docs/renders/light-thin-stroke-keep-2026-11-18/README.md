# light_thin_stroke_keep: every run it moves (2026-11-18)

Original | flag OFF | flag ON, same size and frame (`*_original_before_after.png`), and
close-ups of the changed spots (`*_closeupN.png`, BEFORE | AFTER).

**Moved: 3 of 35 runs, all 3 pictured.** The 9 prime-grader pro jobs at their own sizes (2 moved:
`precision_drone`, `mfab_hat`) and the 26 `corpus_scorecard.FIXTURES` at 80 mm, left chest, Studio
request (1 moved: `drone_render`); the other 32 are stitch-identical by md5 of `design["stitches"]`.
First cut, before the 0.5 mm2 floor, also moved `summit_badge` (one 0.19 mm2 speck, no visible change).

The rule (`stage3_segment.resolve_small_regions`, photo lane): a sub-floor region that clears the
run floors, is >= 4x longer than wide, is >= 30 CIELAB L lighter than the region it would join, and
is >= 0.5 mm2 is kept for the run tier instead of absorbed.

| design | stitches OFF -> ON | what changed (read off the plan) | by eye |
|---|---|---|---|
| `precision_drone` (62.6 mm hat) | 14,114 -> 14,305 | 2 regions kept instead of absorbed, both silver (3971): the blade tip's highlight (0.77 mm2, x -30..-24.5, y -17.9) and the crosshair's top (1.03 mm2). | **Better, small.** The lower-left blade gets a white highlight bar, the vertical crosshair line is continuous as in the art. **The blade is still a thick black slab:** the slab is the dark edges plus pull-compensation growth, which this flag does not touch. |
| `drone_render` (80 mm) | 18,436 -> 18,521 | 2 regions kept (silver 3971): 1.69 mm2 and a 0.84 mm2 vertical line on the crosshair. | **Slightly better.** The crosshair's vertical line runs through as in the art. |
| `mfab_hat` (pro job) | 20,549 -> 20,343 | 2 regions kept (0.19 mm2 each, white 0015) and the big black and white hosts re-shaped (white host 772.75 -> 793.52 mm2; black 307.11 -> 306.56 mm2). | **Worse.** The first W of WELDING loses its white outline stroke and shows a black zig. Raster is 4 px/mm, where the rule fires on many regions. |

Net: the flag does what it was built for on the Drone, but not the grader's complaint (the black
slab is still there), and it breaks one letter on Mfab. **Not a flip candidate as built.**
