# Why the flat lane split Bridge's blue, and the cure — 2026-11-06

`stage0_scale_relative_grad` (PR #1278, OFF) routes `logo_bridge_bar.jpg` to the
FLAT lane. PR #1282 tried the flip and was held on the render
(`docs/stage0-scale-relative-bucket-c-2026-11-06.md` on branch
`claude/stage0-scale-relative-flip`): the blue lettering sewed pale Vintage Blue
4752, every spoke and the ring gained a pale-blue ring, the waves and anchor
sewed olive, and trims went 45 -> 157 (hat). This page finds where, proves it
with a number that moves when you intervene, and cures it behind two new
default-OFF flags that act only on an enlarged raster. Committed test art
only; no pro file is read or drawn.

Instrument: `digitizer/tools/flat_fringe_soft_ramp.py` (`sheets`, `md5`, `pairs`).
Tests: `digitizer/tests/test_flat_fringe_soft_ramp.py`.
Sheets: `docs/renders/flat-fringe-soft-ramp-2026-11-06/`.

## What the art is

A 400 x 400 JPEG: a yellow disc, a black ring and eight black spokes, red
"Bridge", blue "BAR & RESTAURANT" (source median Lab (53, -11, -35), Reef Blue
3815), and **thin black** waves and anchor. The "teal waves" the gradient lane
sews are not in the art either: there they are black, one source pixel wide.

At 113.5 mm hat the raster is enlarged x3.25 to the 8 px/mm working grid, and
the JPEG's edges are soft: the page-to-black gap measures p50 4.0 source px
(three intermediate pixels; golden_tee and the screenshot read 2.4 and 3.4).
Every edge is a ramp about **10 working px** deep. Both mechanisms below are
that ramp.

## Where the blue stops being one colour: stage 2, the k-means fit

Captured `quantize`'s input in the pipeline (flag-True routing, flat lane,
`max_colors` 6) and replayed `_quantize_population` step by step. The palette is
already wrong out of the Lloyd fit, before the majority filter, dissolve, cap or
snap:

| k-means centre (Lab) | pixels | edge frac | snaps to | what it is |
|---|---|---|---|---|
| (92.3, -14.0, 77.8) | 108,312 | 0.06 | 0713 Lemon | the disc |
| (4.4, 0.0, 1.4) | 91,366 | 0.09 | 0020 Black | ring, spokes |
| (51.0, 62.2, 45.0) | 32,470 | 0.06 | 1521 Flamingo | "Bridge" |
| (64.6, -8.9, -1.9) | 41,251 | 0.14 | **4752 Vintage Blue** | blue lettering + page fringe |
| (77.6, -13.5, 50.4) | 33,456 | 0.44 | 0442 Tarnished Gold | yellow-to-blue/black ramps |
| (38.1, -7.6, 32.1) | 17,043 | 0.50 | 6156 Olive | yellow-to-black ramps: the waves |

Not the colour cap (6 clusters, 6 spools, no fold), not the chart snap (the
centre itself is grey-blue), not the tracer.

### Mechanism 1: the spokes' page fringe votes with the blue

Of the "blue" cluster's 41,251 pixels, **63% (25,920) are neutral grey** (chroma
< 8, mean L* 68.6) at p50 3.0 / p90 5.2 working px from the page: the black
spokes' anti-alias ramp against white. Only 14% are blue. Neutral grey sits
nearer the blue centre than black or the page, so the ramp takes the blue's
slot and drags it to 4752.

The existing `flat_page_fringe_exclude` (built OFF 2026-11-03 for Pooh) is
meant to take that ramp out of the fit, but its band is `upscale + 1` = **5 px**:
it assumes a ONE-source-pixel edge. The ramp is ~9. With it ON, the blue comes
back to Caribbean 4531, but the greys at 5-8 px still assign blue by colour,
and every band pixel then copies its nearest non-band pixel's label: teal
speckles round every spoke (trims 157 -> 172).

**The number:** blue-labelled pixels within 12 px of the page, by band width
(fringe flag ON):

| band (working px) | 5 (`upscale+1`, the existing rule) | 6 | 7 | 8 | 9 | 11 (this cure) |
|---|---|---|---|---|---|---|
| blue px at the page | 16,696 | 6,049 | 1,804 | 449 | 0 | 0 |

The blue centre moves 13.8 -> 3.7 dE00 from 4531, and all 16,340 of its pixels
are lettering (all > 20 px from the page, chroma p50 29.6).

### Mechanism 2: interior ramps form clusters the dissolve keeps

The yellow-to-black ramps (the ring's inner edge, the one-pixel waves and
anchor, which never reach black at x3.25) form the olive cluster, and the
yellow-to-blue/black ramps the Tarnished Gold one (97 regions, 78 under 3 mm²:
the trim driver). Both lie on a chord between two kept inks (olive: t 0.39
from black toward the yellow, 2.4 off the chord; gold: on the blue-to-yellow
chord, 5.1 off it; both under `merge_delta_e` 6). The phantom dissolve exists for exactly this, but
counts only the ONE pixel at a label change as edge:

| cluster | edge frac, 1 px | edge frac, within the ramp (5 px) |
|---|---|---|
| 6156 Olive | 0.49 | **1.00** |
| 0442 Tarnished Gold | 0.43 | **1.00** |
| 0020 Black | 0.09 | 0.50 |
| 0713 Lemon | 0.06 | 0.38 |
| 1521 Flamingo | 0.06 | 0.41 |

against the 0.9 gate. And when dissolved, the shipped rule sends a phantom to
the nearest kept centre in Lab: olive is 43.1 from the blue centre and 46.2
from black, so a widened gate alone would have sewn the waves BLUE.

## The cure: two new flags, both OFF, both read an ENLARGED raster only

- **`flat_page_fringe_soft_ramp`**: on an enlarged raster, the page-fringe
  exclusion (`stage2_quantize.page_fringe`: no vote in the fit, the nearest
  non-fringe pixel's label, no stage-3 chain rescue) runs with a band
  `flat_page_fringe_ramp_src_px` (3.0) source px x upscale + 1 deep: 11 px on
  Bridge hat. It runs WITHOUT `flat_page_fringe_exclude` (that flag's
  outline-inner pass and its full-resolution band stay off); with that flag
  also ON it only sizes its band. A source at or above the grid is untouched.
- **`flat_ramp_blend_dissolve`**: on an enlarged raster, a cluster the
  one-pixel dissolve keeps but which is edge within half the soft ramp
  (`ceil(3.0 x upscale / 2)`, 5 px on Bridge hat) is dissolved when it lies on
  the Lab chord between two colours the first round KEPT (or one and the
  page), and joins the NEARER END of that chord. The first round is unchanged.

Each alone leaves the other's defect (tested: the dissolve alone keeps 4752;
the soft band alone keeps 6156 + 0442). Together the stage-2 palette is the
art's four inks, **0713 / 0020 / 1521 / 4531**.

### Two things the measurement changed on the way

1. **The cure first used `flat_page_fringe_exclude` too, and it broke the
   screenshot.** That flag acts at FULL resolution as well
   (`screenshot_phone_ui_golke.jpg` is 12.75 px/mm at 80 mm, reduced to the
   grid, never enlarged): under flip routing it garbled "Done" again and
   closed "SNOW PLOWING" into "SNOWPLOWING", the very lettering the flip
   improved. So the soft band runs on its own, on enlarged rasters only, and
   the screenshot and golden_tee are byte-identical with the cure ON.
2. **The first dissolve ate fremont_patch's tan rope.**
   `art/logo_hotel_fremont_patch.png` (371 px, x1.73 at 80 mm): the tan rope
   border, "EST 1896" and "EAT | STAY | PLAY" are 1-2 source px, so their core
   reads grey-tan (Dolphin 0152, Lab (57.7, 0.4, 6.3)), edge 0.86 at one pixel
   and 1.00 at the ramp's depth. It is a Lab blend of two OTHER blend clusters
   (its own charcoal and sterling ramps), not of two kept inks, and sits 6.3
   off the black-white chord (gate 6.0). The guard (a blend of KEPT colours
   only) keeps it; fremont_patch is byte-identical with the cure ON
   (`test_a_thin_real_ink_between_its_own_ramps_is_kept`). The margin is thin,
   6.3 against 6.0, and that is the catch: a thin real ink lying ON the chord
   between two kept inks reads as a blend, exactly as it always has at one
   pixel.

## Results: OFF vs ON

### Bridge, at the pro's two sizes (Studio request, `max_colors` 6)

`main` = the shipped engine (gradient routing); `flip` =
`stage0_scale_relative_grad` True (flat lane); `flip+cure` = flip plus the two
flags.

| job | arm | lane | stitches | trims | regions | threads (sewn mm²) |
|---|---|---|---|---|---|---|
| Bridge hat 113.5 | main | gradient | 33,996 | 45 | 56 | 0501 1905, 0020 1583, 1720 502, 0713 307, 5010 269, 4531 116 |
| | flip | flat | 41,853 | 157 | 204 | 0713 1972, 0020 1577, 1521 499, **4752 302**, **0442 272**, **6156 141** |
| | **flip+cure** | flat | **20,182** | **23** | **30** | 0713 2218, 0020 1796, 1521 498, **4531 254** |
| Bridge LC 96 | main | gradient | 17,648 | 36 | 55 | 0501 1538, 0020 1121, 1720 364, 4531 134, 0465 71, 5422 69 |
| | flip | flat | 28,048 | 131 | 162 | 0713 1393, 0020 1122, 1521 357, 0442 220, 4752 215, 6156 106 |
| | **flip+cure** | flat | **14,943** | **17** | **29** | 0713 1581, 0020 1283, 1521 357, **4531 182** |

Teal cones: main sews two for the one blue ink (4531 + 5010 on the hat, 4531 +
5422 on the LC); flip sews none (pale 4752); flip+cure sews **one, 4531**.
Regions under 3 mm²: hat 16 / 149 / **3**, LC 16 / 108 / **3** (main / flip /
flip+cure).

Renders, left main, middle flip, right flip+cure:
[hat](renders/flat-fringe-soft-ramp-2026-11-06/bridge_hat.jpg),
[hat lettering](renders/flat-fringe-soft-ramp-2026-11-06/bridge_hat_lettering.jpg),
[LC](renders/flat-fringe-soft-ramp-2026-11-06/bridge_lc.jpg),
[LC lettering](renders/flat-fringe-soft-ramp-2026-11-06/bridge_lc_lettering.jpg).
My read: flip+cure sews what the art draws. The waves, anchor and "&" sew black
(main sews the waves olive and teal, flip olive). "BAR & RESTAURANT" sews in
one teal. The spokes are clean (flip draws a pale-blue ring on each; main
leaves teal flecks on a few). No olive or gold flecks sit on the ring's inner
edge. The small lettering is as blobby as main's: 4 mm letters from a 400 px
JPEG are a separate reach gap. Residual: the disc sews 0713 Lemon, not main's
0501 Sun (row 9 below). The flat lane's k-means yellow centre carries the
yellow side of the ramps.

### golden_tee and the screenshot (80 mm left chest)

| job | main | flip | flip+cure |
|---|---|---|---|
| golden_tee | 11,858 / 41 / 46 | 14,237 / 57 / 94 | **byte-identical to flip** |
| screenshot | 7,761 / 55 / 149 | 11,607 / 131 / 287 | **byte-identical to flip** |

(stitches / trims / regions.) Neither source is enlarged at 80 mm, so the
cure cannot touch them: the screenshot's improvement under the flip survives
unchanged, and golden_tee is exactly what the flip makes it.

### The 15 real flat logos (`tools.stage0_scale_relative`), 80 mm left chest

`python -m tools.flat_fringe_soft_ramp md5`. A job whose lane is not flat
never reaches the flags (only `quantize` reads them) and is not digitized.

- **Flags OFF are byte-identical to main**: 16 of 16 flat-lane arms (2 at
  main routing, 14 at flip routing) are md5-equal to the same run on
  `origin/main` 6a7bb7f2 (`--off-only`, throwaway checkout).
- **Cure ON at main routing: nothing moves.** The two flat-routed logos,
  becker and enthusiast, are alpha cut-outs.
- **Cure ON at flip routing: 4 of 14 move**, all enlarged sources:

| logo | flip (st / trims / regions / colours) | flip+cure | read |
|---|---|---|---|
| bridge | 20,885 / 107 / 202 / 6 | 11,401 / 16 / 28 / 4 | the cure (above) |
| golke_art | 5,375 / 25 / 60 / 2 | 5,825 / 20 / 53 / 2 | [render](renders/flat-fringe-soft-ramp-2026-11-06/golke_art.jpg): the "+" window sews a clean white cross where flip sewed black blobs over it; the rest is equal |
| toat_beanie | 15,437 / 26 / 87 / 2 | 15,153 / 22 / 77 / 2 | [render](renders/flat-fringe-soft-ramp-2026-11-06/toat_beanie.jpg): visually the same; 10 fewer sub-3 mm² white pieces |
| toat_machine | 17,074 / 24 / 90 / 2 | 17,160 / 24 / 81 / 2 | [render](renders/flat-fringe-soft-ramp-2026-11-06/toat_machine.jpg): visually the same; 9 fewer sub-3 mm² white pieces |

Unmoved at flip routing: becker, tires, enthusiast, fremont, gaulke,
golden_tee, screenshot, mfab_lc, fremont_patch and proseal. mfab_hat routes
photo_scene both ways.

### Flat-lane goldens

The three `FLAT_GOLDEN_MD5` fixtures are byte-identical with the cure ON
(`test_the_cure_moves_no_flat_golden`): none is enlarged at 80 mm or has a
page fringe. `tests/test_flat_page_fringe.py` passes unchanged.

### The nine tests (bucket c), re-read with the cure ON under flip routing

Rows 1, 2, 3, 7, 8 and 9 of `docs/stage0-scale-relative-bucket-c-2026-11-06.md`
(branch `claude/stage0-scale-relative-flip`). Run in a throwaway checkout with
`stage0_scale_relative_grad`, `flat_page_fringe_soft_ramp` and
`flat_ramp_blend_dissolve` as defaults, through each test's own config (80 mm
left chest).

| # | test | main (OFF) | flip | **flip+cure** | read |
|---|---|---|---|---|---|
| 1 | `test_on_bridge_keeps_its_eight_bean_letters` | 8 | 15 | **9** | near main; fails its literal 8 |
| 2 | `test_bridges_words_are_tagged_and_sew_as_runs_along_their_ink` | pass | 7 of 15 tagged | **pass** | repaired |
| 3 | `test_bridge_50mm_bar_and_restaurant_is_freed_from_the_badge` | 12 letters | 4 | **7** | better than flip, short of main |
| 7 | `test_bridges_teal_words_survive_tracing_on_the_working_grid` | 78.9 / 186.9 mm² | 119.8 / 142.4 | **119.8 / 127.2**, one cone (4531) | the test's docstring puts the art's teal at ~96 mm²; main's 187 counts the waves it sews teal. The 4 px/mm defect arm no longer reproduces on this lane, so the test's premise is gone |
| 8 | `test_bridge_halo_lever_takes_most_of_the_flips_halo` | 25.6 -> 4.1 mm² | 8.9 -> 8.9 | **5.8 -> 5.8** | smaller halo than flip's, with nothing left for the lever; fails its premise (>= 10) |
| 9 | `test_the_pre_flip_engine_sews_the_disc_limelight_and_the_shipped_one_sews_the_artworks_yellow` | 6031 / 0501 Sun | 0713 / 0713 | **0713 / 0713** | not moved by the cure: the disc sews Lemon (2.1 dE00), not Sun (1.0) |

## What this settles, and what it does not

- The mechanism is in the palette: the k-means fit, before any later stage.
  The numbers that move on intervention: blue-labelled pixels at the page go
  16,696 -> 0 (band 5 -> 11); the blue centre goes 13.8 -> 3.7 dE00 from 4531;
  the olive/gold edge fraction goes 0.49/0.43 -> 1.00 at the ramp's depth.
- The cure touches only enlarged sources (a low-resolution upload drawn larger
  than its pixels). It is byte-identical OFF. ON, 4 of 14 flat-routed real
  logos move, and I read each render as same-or-better.
- Not settled: rows 1, 3 and 9 still differ from main. Row 9's disc yellow
  (Lemon vs Sun) is a separate flat-lane centre bias.
- The stage-0 flip, and flipping these flags, are Kent's (ROADMAP gate 3).
