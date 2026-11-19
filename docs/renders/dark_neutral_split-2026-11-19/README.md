# dark_neutral_split: a tonal cut of the Drone's black region (2026-11-19) — built OFF, not recommended to flip

Flag `dark_neutral_split` (PipelineConfig, default False, `stage2_photo_segment.split_dark_neutral_regions`).
Pictures are our renders and the Drone's own art only (ORIGINAL | BEFORE flag OFF | AFTER flag ON):
`precision_drone_whole.png`, `drone_render_whole.png`, and `*_drone_closeup.png` (top two thirds of each).

## Census (before building): `python -m tools.dark_split_census --out DIR`
Over the 44 sweep designs, 9 regions are dark (area >= 100 mm2, mean L* <= 35) and >= 50% neutral:
mfab_hat x5 (L* 2-6, no mid tone, gap -0.8), precision_drone, drone_render, summit_badge (gap 6.3), photo_chrome_specular
(91% mid tone, existing tonal split already in force). The Drone's 815 mm2 black region is NOT bimodal: 322 mm2 below
L* 3, then a continuum L* 3-30; an Otsu/k-means cut lands on the forest or the highlight tail, so the cut is a fixed
neutral L* >= 8 with pieces >= 10 mm2. Chosen bounds (constants `DARK_SPLIT_*`): both tones >= 60 mm2, gap >= 12 L*,
<= 14 pieces, solidity >= 0.6, only where the ordinary tonal split is not in force. They fire on exactly the 2 Drone
runs and none of the other 42, so the other 42 cannot move; the full 90-minute 44-run sweep was not run (nothing to find).
Not stage 0, no gate-1 constant touched, no colour-cap change.

## What moved (flag_sweep rows, OFF -> ON)
| run | stitches | trims | jumps | needle-up mm | colours |
|---|---|---|---|---|---|
| precision_drone (hat, 62.6 mm) | 13976 -> 14291 (+315) | 92 -> 92 | 190 -> 193 | 1459 -> 1493 | 8 -> 8 |
| drone_render (80 mm) | 18409 -> 17790 (-619) | 103 -> 100 | 226 -> 220 | 1839 -> 1828 | 9 -> 9 |

## Verdict by eye: not clearly better, leave OFF
- precision_drone: the arms get their own dark-grey panels (both upper arms and the lower-left arm). Modest gain. The
  body, the camera housing and the lens are still fragments, and the sky is still black: the cut does not give the body a shape.
- drone_render at 80 mm: worse. The navy base goes charcoal (the new mid tone changes which spools the palette keeps), and
  the camera housing outline and the body's top lines that BEFORE sewed are gone. Colour count did not rise.
Cause: the body panels are thin gloss edges of L* 8-30 on a near-black body (~140-175 mm2 in ~10 pieces); as threads at
62 mm they are 1-2 mm wide, a thread-width limit more than a region-shape one. Thread stacking was not measured (see below).

## Not done
Stacked-thread area / coverage and preflight figures not measured on the movers; the flag-ON related tests were not run
beyond a 350-test subset (stage-2, cap fuse, byte-identical photo lane, service) which all pass with OFF default.
