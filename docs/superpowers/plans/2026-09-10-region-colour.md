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
| `drone_render` (gradient) | 58 | 26 / 65.2% | 33 / 79.5% | 2 | 23.4 |
| `enthusiast_logo` (flat) | 0 — flat lane | | | | |
| `fur_ramp` (photo_scene) | 8 | 0 / 0.0% | 0 / 0.0% | 0 | 0.1 |
| `gradient_ramp_linear` (gradient) | 1 | 0 / 0.0% | 0 / 0.0% | 0 | 0.3 |
| `gradient_ramp_radial` (gradient) | 1 | 1 / 100.0% | 1 / 100.0% | 0 | 2.6 |
| `photo_chrome_specular` (photo_scene) | 12 | 3 / 34.8% | 3 / 34.8% | 0 | 2.1 |
| `photo_dof_meadow` (photo_scene) | 16 | 4 / 7.6% | 3 / 4.7% | 0 | 4.3 |
| `photo_grass_macro` (photo_subject) | 2 | 0 / 0.0% | 0 / 0.0% | 0 | 0.5 |
| `photo_owl_pale` (photo_scene) | 6 | 0 / 0.0% | 0 / 0.0% | 0 | 5.7 |
| `photo_scene_stub` (photo_scene) | 14 | 1 / 28.6% | 1 / 28.6% | 0 | 1.1 |
| `photo_subject_stub` (photo_subject) | 1 | 1 / 100.0% | 1 / 100.0% | 0 | 9.9 |
| `photo_sunset_backlit` (photo_scene) | 9 | 0 / 0.0% | 1 / 19.7% | 0 | 2.2 |
| `region_blobs` (gradient) | 4 | 0 / 0.0% | 1 / 18.1% | 0 | 2.8 |
| `repro_gradient_white_icon` (gradient) | 8 | 4 / 33.2% | 4 / 33.2% | 2 | 28.6 |
| `summit_badge` (gradient) | 34 | 8 / 8.0% | 8 / 8.0% | 0 | 9.3 |
| `becker_marine_logo` (flat) | 0 — flat lane | | | | |
| `logo_script_tires` (photo_scene) | 4 | 0 / 0.0% | 0 / 0.0% | 0 | 1.8 |
| `logo_bridge_bar` (gradient) | 50 | 11 / 56.9% | 19 / 58.2% | 0 | 6.4 |
| `logo_gaulke_roofing` (gradient) | 18 | 12 / 1.6% | 12 / 1.6% | 0 | 9.3 |
| `logo_golden_tee` (gradient) | 35 | 15 / 33.8% | 15 / 33.8% | 2 | 15.0 |
| `logo_hotel_fremont` (gradient) | 49 | 8 / 2.9% | 8 / 2.9% | 0 | 8.8 |
| `screenshot_phone_ui_golke` (gradient) | 92 | 52 / 65.0% | 53 / 65.9% | 27 | 13.9 |

**20 of 26 fixtures reach the lane; 422 regions; the median moves the
spool of 146, the modal mean of 163; 33 are bimodal (27 of them on the
phone-UI screenshot).** (`mean` here is the engine's own OFF point — the
RGB mean converted once; the first census averaged in Lab and read 155 /
169, corrected with the seam.) The synthetic ramps and the photographs move
nothing or next to nothing (fur ramp 0.1 ΔE00 worst); the real logos
move most of their AREA — Bridge Bar 56.9%, drone 65.2%, the screenshot
65.0%, Golden Tee 33.8% — because their big flat regions are the
ones with things drawn on them; gaulke and Fremont move 13 and 7 small
regions (1.6% and 2.9% of area). A moved spool is the region's own
nearest thread, not the palette's choice: what a design actually sews
is §4.2's flip sheet.

**The statistic: the modal mean.** The two candidates move nearly the
same regions (146 and 163); where they differ the modal mean lands on the
artwork. On Bridge Bar's disc (18,804 px): mean → `6031` Limelight, median →
`0713` Lemon (2.1 ΔE00 from the disc's pixels), modal mean → `0501` Sun
(1.0). A per-channel median is itself a colour no single pixel need
carry; the modal mean averages the pixels that ARE the region's colour.
Three more of Bridge Bar's regions change spool with either: the red
script `1521 → 1720`, a dark region `5866 Herb Green → 1375 Dark
Charcoal`, an olive shard `6156 → 5866` — each a colour the mean had
invented from an edge.

### 4.2 The flip sheet — `off` against `region_colour`, 26 fixtures at 80 mm

`tools/flip_sheet.py`, fresh caches (`build/flip_sheet_rc`, `_mc6`) on this
tree — the item-8 caches' `off` rows are the PRE-flip engine and cannot be
reused. `off` here is the shipped engine: the four colour flags ON, item 9
ON (no garment named, so it declines).

**At the engine's 12:** 11 fixtures move, 15 are byte-identical (every
flat-lane fixture, gaulke, Fremont, the ramps, the owl, the fur). Net
+2,485 stitches, +27 trims, −1 block, 0 cones, −1 stop; one grade up
(Bridge Bar F 0 → F 4), none down.

| fixture | OFF: grade · st · tr · cones · blocks | ON | what moved |
|---|---|---|---|
| Bridge Bar | F · 14,586 · 126 · 12 · 13 | F · 14,386 · 125 · **11 · 11** | the disc `6031 → 0501`; −1 cone, −2 blocks, F 0 → F 4 |
| screenshot | F · 7,550 · 71 · 12 · 12 | F · 7,546 · 63 · **10 · 10** | −2 cones, −2 blocks, −8 trims |
| Golden Tee | F · 6,719 · 58 · 11 · 11 | F · 6,795 · 64 · 12 · 12 | the yellows regroup; +1 cone, +6 trims |
| drone | F · 16,367 · 87 · 12 · 12 | F · 16,337 · 87 · 12 · 12 | grey shards `2564 → 0111`; −30 stitches |
| chrome | C · 34,849 · 89 · 7 · 7 | C · 34,881 · 89 · 8 · 8 | +1 cone |
| meadow | C · 19,892 · 34 · 5 · 5 | C · 19,412 · 41 · 5 · 5 | −480 stitches, +7 trims |
| repro white icon | D · 22,361 · 24 · 5 · 5 | D · 22,078 · 19 · 5 · 5 | −283 stitches, −5 trims |
| summit badge | F · 17,882 · 37 · 12 · 12 | F · 17,874 · 36 · 12 · 12 | −8 stitches, −1 trim |
| photo_scene_stub | B · 16,083 · 44 · 4 · 4 | B · 19,465 · 73 · 5 · 5 | **+3,382 stitches, +29 trims, +1 cone** — see below |
| photo_subject_stub, sunset | = counts | = counts | a spool swap inside the same counts |

Read against the findings: **Bridge Bar** loses `COLOR_STOPS_HEAVY`, a
repeated `0108` cone (13 blocks for 12 cones OFF), Herb Green and one of
its three `THREAD_MATCH_POOR` blocks; its script goes `1521 → 1720`, its
teal `4531 → 4423`, its dark region `5866 → 1375` — every one a colour the
mean had invented from an edge. **The screenshot** loses `COLOR_STOPS_HEAVY`
with its two cones. **Golden Tee** goes the other way on cones — twelve
for eleven, `COLOR_STOPS_HEAVY` gained, +6 trims — while its
`THREAD_MATCH_POOR` blocks fall from four to two: the yellows regroup onto
spools closer to the letters' own pixels. **The photo-scene stub** (a
synthetic scene) takes a fifth spool, `4133`, and the label map falls into
31 regions where it had 21: +3,382 stitches and +29 trims at the same B 76
— the one real price on this sheet, on a fixture no customer uploads.
**meadow, sunset and the subject stub** swap one spool for its neighbour
(`1334 → 1301`, `1334 → 1332`, `2762 → 0722`) at the same grade;
**chrome** gains White and Whale for two greys.

**At the Studio's 6** (`build/flip_sheet_rc_mc6`): the same 11 move and
15 are byte-identical. Net +1,922 stitches, +2 trims, **−2 blocks, −2
stops**, +1 cone (the stub's); no grade letter moves — the real logos sit
on the F floor either way, so the findings are the reading.

| fixture | OFF: st · tr · cones · blocks · blocking | ON | what moved |
|---|---|---|---|
| Bridge Bar | 14,588 · 124 · 6 · 7 · 2 | **13,820 · 96 · 6 · 6** · 3 | the disc `6031 → 0501`; the repeated `0108` gone (7 blocks for 6 cones OFF); −768 stitches, **−28 trims**; one more blocking thread (below) |
| Golden Tee | 6,828 · 62 · 6 · 9 · 4 | 6,795 · 59 · 6 · **7** · **3** | two repeated cones gone (9 blocks for 6 cones OFF); the yellows `1120/1220/0811 → 0703/1102/1902`; one blocking thread fewer |
| screenshot | 7,530 · 66 · 6 · 6 · 5 | 7,563 · 66 · 6 · 6 · **4** | one blocking thread fewer; `0134/3640/0015 → 1776/0108/3630` |
| drone | 16,141 · 92 · 6 · 8 · 4 | 16,190 · 91 · 6 · 8 · 5 | one more blocking thread (below); `2776/0904/0142 → 1776/1102/0145` |
| photo_scene_stub | 16,083 · 44 · 4 · 4 · 0 | 19,465 · 73 · 5 · 5 · 0 | the same fifth spool and +29 trims as at 12 |
| chrome, meadow, sunset, summit, subject stub, repro | spool swaps at the same counts (meadow −480 st / +7 tr; repro −283 / −5) | | |

**The blocking threads at 6, named** (`THREAD_MATCH_POOR`, preflight given the
artwork path as the scorecard gives it — see DOCTRINE 2026-09-10 on what a
hand-fed RGB array does to this number):

- **Bridge Bar** OFF: 2 blocks — Black 18.8 on a 13 mm² olive shard,
  Caribbean 14.7 on 5 mm² teal shards; the script warns at 6.5 under
  Flamingo and the disc at 7.5 under Limelight. ON: 3 blocks — Herb Green
  16.2 on the same olive shard (better than Black's 18.8), Marine Aqua 11.5
  on the same teal shards (better than 14.7), Cobblestone 10.6 on a 15 mm²
  grey shard (new, at the threshold); **the disc and the script leave the
  list entirely** — 1,246 mm² of artwork, under Sun and Not Quite Red, now
  inside the visible threshold. "One more block" is three shards of 5–15
  mm², each nearer its thread than before or within a unit of the line.
- **Golden Tee** OFF: 4 blocks — Black **40.4** on a 16 mm² red shard,
  Sunset 11.3 on the 153 mm² yellow-orange, Sterling 16.1 and Apricot 22.1
  on 2–3 mm² shards. ON: 3 blocks, all on shards of 3–6 mm² (Orange Peel
  13.5, Poinsettia 16.9, Silver 15.3); the red shard and the 153 mm²
  yellow-orange leave the list.
- **the screenshot** OFF: 5 blocks including Black 11.5 on the **470 mm²**
  dark ground; ON: 4, all on shards of 1–10 mm²; the ground leaves the
  list.
- **drone** OFF: 4 blocks on shards of 3–17 mm². ON: 5 — the same Fox Fire
  and Flag Blue shards, Blackberry 15.7 on 3 mm², Silver 33.1 on a 2 mm²
  grey, and **Pumpkin 10.9 on the 211 mm² orange**, the one large shape
  that gets worse: by colour that orange is 3.5 from Fox Fire and 6.0 from
  Pumpkin, and at six cones the palette now spends one orange spool where
  it spent two. The one real loss at the Studio's budget, and a budget
  trade rather than a wrong point.

So at 6 the flag moves the blocks OFF the big shapes and onto shards, on
three of the four real logos, and costs drone's orange one spool step.

### 4.3 Looked at — `docs/renders/region-colour-2026-09-10/` (OFF left, ON right, 80 mm, the engine's 12)

- **Bridge Bar**: the disc is a yellow-green under the mean and a clean
  yellow under the modal mean — `6031` Limelight to `0501` Sun, the one
  visible change on the sheet and the one this build exists for. The
  script, the greys and the wheel are the same cones; three sub-mm grey
  shards go `0108 → 0142`.
- **Golden Tee**: the render tool marks four shapes `0015 → 3971` — the GT
  letter bodies and the arc, 643 mm² of *unstitched* holes. That is not the
  region colour: those regions are quantized as their own population and
  never enter the k-medoids. Under the modal mean the k-medoids selected
  one more spool (13 for 12) and the design went over the engine's 12, so
  the colour cap remapped the thread carried only by holes — "holes buy no
  slot" — into its nearest kept cone. On fabric nothing changes: on the
  Studio's default Natural the holes stay holes, and on navy item 9's rule
  counts them as sewn area so their White keeps its slot. What DOES move is
  the yellows: two of the GOLF letters' regions that the mean sent to
  `1120`/`1220` land together on `0703`, and the darker band goes
  `0700 → 1102` — the modal means of the yellow regions are brighter and
  more saturated than their means, and they group differently. Six cones
  of Golden Tee's twelve are different spools; the letters read the same.
- **drone**: the same logo. Seven of the tagline's grey shards go `2564 →
  0111` Whale, the emblem `0824 → 1310`, one white sliver to Skylight; the
  window's blue reads a shade deeper.

The render is at 12. The Studio ships 6, where the cap does most of the
choosing; §4.2's sheet carries both budgets.

## 5. Decisions — Kent's

1. The statistic (median or modal mean), on §3's numbers.
2. The flip, on the flip sheet's row and the Bridge Bar render — a
   recapture of the photo-lane snapshot on CI if any golden fixture moves.
