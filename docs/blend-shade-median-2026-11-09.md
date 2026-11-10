# Defect 28 cause hunt: summit's `0111` and `blend_shade_median` (2026-11-09)

Main 19bde3e3, 80 mm, Windows, `corpus_scorecard` fixtures, `digitize` then `run_preflight`.

## Fremont: closed before this started
`logo_hotel_fremont`: B 76 left_chest, B 88 hat_front, no `THREAD_MATCH_POOR`.
Fixed by #1312 (traced) and #1329 (`thread_match_grade_traced_letter` ON, 11-07).
It now traces `flat`. MASTER_SCOPE item 28's "cause not established" is stale.

## Summit: cause
Region `Scd5f9d89` (the background, 2,776 mm2) takes the per-region path in
`stage6_blend.blend_fill`: radial fit r2 0.689, no design ramp, not carved.
Extremes are single pixels (rgb 19,19,19 and 183,183,183), 60.4 dE00, so n = 5.

| shade | centre | samples | bucket mean L* | thread (mean) | median artwork rgb |
|---|---|---|---|---|---|
| 0 | 0.00 | 104 | 44.2 | 0674 | 109,105,99 |
| 1 | 0.25 | 490 | 40.7 | 0128 | 100,95,90 |
| 2 | 0.50 | 966 | 35.8 | 4174 | 88,84,79 |
| 3 | 0.75 | 931 | 31.2 | 4174 | 77,73,68 |
| 4 | 1.00 | **9** | **48.8** | **0111** | **74,69,64** |

Bucket 4 holds 0.4% of the samples; three are bright speckle. Mean L* 48.8
snaps to `0111` (127 grey); the band's pixels are L* 30 (L* pct10/50/90 =
29/30/30), 21.5 dE00 off, 16.9 excess over loaded `0134` (4.6 off). The median
of the same 9 is L* 29.5 and snaps to `0134`.

## Fix, built OFF: `cfg.blend_shade_median`
`_shade_lab_colors(..., median=True)` on the per-region path only.

Gradient-class-at-the-time fixtures (11) x 2 garments x {OFF, ON}, plan md5 from
`iter_runs`:

| | OFF | ON |
|---|---|---|
| entries whose plan md5 moves | | 2 (summit, both garments) |
| entries identical | | 20 |
| THREAD_MATCH_POOR blocks, these 22 entries | 10 | 8 |
| of those, summit | 2 | 0 |
| all `block` findings, these 22 entries | 12 | 10 |
| summit grade | F 0 | F 10 (left_chest, hat_front) |

Summit stays F on `GROUND_SEWN`. Stitches: left_chest 28,325 -> 28,436,
hat_front 28,523 -> 28,504.

Lane today: only drone, gradient_ramp_linear/radial and summit trace
`gradient`. The other seven trace `flat`. The remaining blocks are flat-lane
raw distance: bridge_bar 3 and screenshot_phone_ui 1 per garment. Photo stub
`0722` (2 blocks, photo route) is untouched.
