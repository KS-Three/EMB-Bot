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

## 4. Measured

### 4.1 The census (`tools/region_colour.py`, 26 fixtures at 80 mm, 2026-09-10)

Per SLIC-lane fixture: regions, how many regions (and what share of the
fixture's pixel area) change their nearest chart spool under each
candidate, the bimodal count (mean-to-median over 10 ΔE00) and the worst
mean-to-median distance.

| fixture (class) | regions | median: moved / area | modal: moved / area | bimodal | worst mean→median ΔE00 |
|---|---:|---|---|---:|---:|
| `bg_uncertain` (flat) | 0 — flat lane | | | | |
| `logo_alpha` (flat) | 0 — flat lane | | | | |
| `logo_whitebg` (flat) | 0 — flat lane | | | | |
| `ribbon_curve` (flat) | 0 — flat lane | | | | |
| `drone_render` (gradient) | 58 | 26 / 66.8% | 32 / 80.5% | 2 | 14.0 |
| `enthusiast_logo` (flat) | 0 — flat lane | | | | |
| `fur_ramp` (photo_scene) | 8 | 0 / 0.0% | 0 / 0.0% | 0 | 0.1 |
| `gradient_ramp_linear` (gradient) | 1 | 0 / 0.0% | 0 / 0.0% | 0 | 0.6 |
| `gradient_ramp_radial` (gradient) | 1 | 0 / 0.0% | 0 / 0.0% | 0 | 2.3 |
| `photo_chrome_specular` (photo_scene) | 12 | 4 / 36.4% | 4 / 36.4% | 0 | 2.1 |
| `photo_dof_meadow` (photo_scene) | 16 | 4 / 7.6% | 3 / 4.7% | 0 | 4.2 |
| `photo_grass_macro` (photo_subject) | 2 | 0 / 0.0% | 0 / 0.0% | 0 | 0.6 |
| `photo_owl_pale` (photo_scene) | 6 | 0 / 0.0% | 0 / 0.0% | 0 | 5.1 |
| `photo_scene_stub` (photo_scene) | 14 | 1 / 28.6% | 1 / 28.6% | 0 | 1.0 |
| `photo_subject_stub` (photo_subject) | 1 | 1 / 100.0% | 1 / 100.0% | 0 | 1.7 |
| `photo_sunset_backlit` (photo_scene) | 9 | 1 / 26.9% | 2 / 46.7% | 0 | 2.0 |
| `region_blobs` (gradient) | 4 | 0 / 0.0% | 1 / 18.1% | 0 | 2.6 |
| `repro_gradient_white_icon` (gradient) | 8 | 3 / 17.2% | 3 / 17.2% | 2 | 26.9 |
| `summit_badge` (gradient) | 34 | 8 / 8.0% | 8 / 8.0% | 0 | 9.8 |
| `becker_marine_logo` (flat) | 0 — flat lane | | | | |
| `logo_script_tires` (photo_scene) | 4 | 0 / 0.0% | 0 / 0.0% | 0 | 2.6 |
| `logo_bridge_bar` (gradient) | 50 | 13 / 66.5% | 19 / 67.7% | 0 | 6.2 |
| `logo_gaulke_roofing` (gradient) | 18 | 13 / 1.8% | 13 / 1.8% | 1 | 10.2 |
| `logo_golden_tee` (gradient) | 35 | 17 / 54.4% | 17 / 54.4% | 2 | 13.5 |
| `logo_hotel_fremont` (gradient) | 49 | 7 / 2.6% | 7 / 2.6% | 0 | 8.5 |
| `screenshot_phone_ui_golke` (gradient) | 92 | 57 / 69.7% | 58 / 70.2% | 26 | 13.3 |

**20 of 26 fixtures reach the lane; 422 regions; the median moves the
spool of 155, the modal mean of 169; 33 are bimodal (26 of them on the
phone-UI screenshot).** The synthetic ramps and the photographs move
nothing or next to nothing (fur ramp 0.1 ΔE00 worst); the real logos
move most of their AREA — Bridge Bar 66.5%, Golden Tee 54.4%, drone
66.8%, the screenshot 69.7% — because their big flat regions are the
ones with things drawn on them; gaulke and Fremont move 13 and 7 small
regions (1.8% and 2.6% of area). A moved spool is the region's own
nearest thread, not the palette's choice: what a design actually sews
is §4.2's flip sheet.

**The statistic: the modal mean.** The two candidates move nearly the
same regions; where they differ the modal mean lands on the artwork.
On Bridge Bar's disc (18,804 px): mean → `6031` Limelight, median →
`0713` Lemon (2.1 ΔE00 from the disc's pixels), modal mean → `0501` Sun
(1.0). A per-channel median is itself a colour no single pixel need
carry; the modal mean averages the pixels that ARE the region's colour.
Three more of Bridge Bar's regions change spool with either: the red
script `1521 → 1720`, a dark region `5866 Herb Green → 1375 Dark
Charcoal`, an olive shard `6156 → 5866` — each a colour the mean had
invented from an edge.

### 4.2 The flip sheet — `off` against `region_colour`, 26 fixtures

*(pending)*

## 5. Decisions — Kent's

1. The statistic (median or modal mean), on §3's numbers.
2. The flip, on the flip sheet's row and the Bridge Bar render — a
   recapture of the photo-lane snapshot on CI if any golden fixture moves.
