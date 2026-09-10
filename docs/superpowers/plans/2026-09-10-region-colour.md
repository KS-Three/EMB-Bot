# A robust region colour for the palette (2026-09-10)

**Status: PLANNED — Kent's pick 2026-09-10 12:57Z after item 9 (#443, #444).**
The loss the colour-bundle flip's own test run found (#442, decision sheet
§2's bind entry): Bridge Bar's disc sews `6031` Limelight, 7.0 ΔE00 from
the artwork's yellow, because stage 2 hands the palette a colour no pixel
carries. Repair it at its source, behind a flag, measured on the flip sheet.

## 0. What already governs this — read before changing the plan

- **The palette is a chart-restricted weighted k-medoids over REGION
  colours** (`palette.select_palette`, plan
  `docs/superpowers/plans/2026-08-1x-photo-palette.md` lineage): one Lab
  point and one weight per region, `max_k = cfg.max_colors` as a soft cap.
  It chooses spools for the points it is given. On Bridge Bar it chose
  correctly for the point it was given — that is the finding, not a
  palette bug.
- **The point is the region's plain mean** (`stage2_photo_segment.py`, the
  `region_labs` list before `select_palette`): `rgb_to_lab(pixels.mean())`.
  Every SLIC+RAG region — the lane six of seven real logos route to.
- **Measured 2026-09-10 (#442 test run):** Bridge Bar's disc pixels sit at
  (251, 235, 65), 1.0 ΔE00 from `0501` Sun; the disc REGION's mean is
  (223, 220, 77), 12 ΔE00 darker and greener — the black lettering, the
  bird and the rope inside it pull the mean through their anti-aliased
  edges and grey halos — and Limelight is that mean's nearest spool (2.5).
  Before the bundle flip the unbound re-snap read the source pixels and
  corrected the disc to Sun (double-loading Lemon beside it); the bind now
  holds the palette's answer. The bind is right to; the point was wrong.
- **DOCTRINE 2026-09-10:** *stage 2 hands the palette a region's MEAN, and a
  big region full of inclusions turns it into a colour no pixel carries* —
  and *a flag that closes an escape is asked what the escape was
  correcting*. This build is the answer to both.
- **The photo-lane snapshot golden** (`tests/test_stage2_photo_segment.py::
  test_flat_and_gradient_lanes_still_match_golden_after_photo_dispatch`)
  pins the SLIC lane's output on the golden fixtures; a flip that moves any
  of them is a recapture on ubuntu CI, never here (DOCTRINE). Flag first.
- **Gates:** none. A colour statistic is not a physical constant (gate 1);
  stage 0 is untouched (gate 2); no default-OFF tier flips (gate 3); the
  measurement is per fixture in cones, spools, stitches, trims and the
  render, never a raw agreement number (gate 4).

## 1. The gap

A region's representative colour should be the colour its pixels ARE. The
mean is that only when the region is uniform. A real logo's big flat region
is never uniform: everything drawn on it — lettering, icons, halos — leaves
anti-aliased edge pixels inside the region's mask, and JPEG ringing adds
grey. A mean over 18,800 weight-units of yellow plus a few hundred of black
and grey edge is a yellow-green; the median is yellow. The palette then
spends a spool on the wrong colour, and every downstream correction is an
escape (the re-snap) or a rule (the bind) arguing with it.

## 2. The design

- **`cfg.robust_region_colour: bool = False`** — DEFAULT OFF and
  byte-identical off. ON, the point handed to the palette for each SLIC+RAG
  region is a robust centre of its Lab pixels instead of the mean. The
  statistic is chosen by §3's instrument from two candidates, the same for
  every region:
  1. **the per-channel median** in Lab — cheap, and exact for a pure colour
     with a minority of edge pixels;
  2. **the modal mean** — the mean over the pixels within `DELTA_E_VISIBLE`
     (5) of that median: the median's robustness with the mean's
     smoothness on a gradient region.
  A region whose pixels are half one colour and half another has no right
  answer under any statistic; the instrument reports how many such regions
  exist (mean-to-median ΔE00 over 10 AND neither half a minority).
- **One seam.** The mean lives in ONE place; the change factors it into
  `_region_lab(pixels_lab, cfg)` so the flag, the instrument and the test
  all read the same function. Nothing else moves: the shade-demand buckets
  (`_shade_demand_points`) keep their per-bucket means (a bucket is a
  narrow tonal band, and the demand rows steer spool selection, not region
  labels); the tonal split's lo/hi contrast keeps its means (a statistic
  of two extremes, not a colour).
- **What can move.** Every k-medoids input on every SLIC-lane fixture, so
  every gradient/photo palette can change spools, and with it cones,
  blocks, the cap's merges and the re-snap. The flip sheet prices it as one
  arm; the render shows Bridge Bar's disc.

## 3. Instrument first — `tools/region_colour.py`

For every scorecard fixture that reaches the SLIC+RAG lane, every region:
area (weight), the mean, the median, the modal mean, the ΔE00 from the
mean to each, the nearest chart spool under each and whether it differs
from the mean's. Per fixture: how many regions and how much weighted area
change spool under each candidate; the bimodal count. Corpus totals. This
is the number that picks the statistic, and it is measured before the
flag's ON path is written.

## 4. Measured — filled after the instrument and the flip sheet run

*(pending)*

## 5. Decisions — Kent's

1. The statistic (median or modal mean), on §3's numbers.
2. The flip, on the flip sheet's row and the Bridge Bar render — a
   recapture of the photo-lane snapshot on CI if any golden fixture moves.
