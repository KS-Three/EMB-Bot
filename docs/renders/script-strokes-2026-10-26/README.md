# Script strokes (`script_strokes`, built OFF) — 2026-10-26

Kent's ruling, 2026-10-26: "Measure, then build OFF (Recommended)". A script
word sewn one satin column per pen stroke, crosses square to the stroke, the
pen path read on the artwork's own ink. Engine `ee2675d6` (this branch merged
with main), each job built once and planned OFF and ON from the same
generation; the pro's file beside it, each drawn in its own frame (crop by mm
from each design's own top-left; the pro's DST has no colours).

| file | job | crop |
|---|---|---|
| `bridge_hat_off_on_pro.jpg` | Bridge hat, 63.3 mm | 25 px/mm |
| `bridge_lc_off_on_pro.jpg` | Bridge LC, 76.6 mm | 22 px/mm |
| `tires_off_on_pro.jpg` | Tires hat, 114.3 mm ("ires" and the T's stem) | 12 px/mm, ours drawn grey |
| `machine_hat_off_on_pro.jpg` | To a T Machine hat, 89.5 mm | 20 px/mm, ours drawn grey |

## The word, one reader for all three files (`tools/script_census.py`, the word's colour block)

| job | arm | stitches | runs | cuts | columns (+patches) | square to stroke | slanted dev | stacked overlap mm | coverage width mm |
|---|---|---|---|---|---|---|---|---|---|
| Bridge hat | OFF | 852 | 3 | 2 | 14 (+1) | 0.74 | -9.3 | 3.89 | 2.76 |
| | ON | 754 | 3 | 2 | 13 (+7) | 0.84 | 0.5 | 0.66 | 2.60 |
| | pro | 905 | 6 | 7 | 18 (+2) | 0.77 | 3.0 | 0.00 | 1.96 |
| Bridge LC | OFF | 1,251 | 2 | 1 | 23 | 0.77 | -9.9 | 5.32 | 3.00 |
| | ON | 867 | 3 | 2 | 15 (+5) | 0.89 | -2.1 | 0.72 | 2.78 |
| | pro | 1,111 | 6 | 7 | 14 | 0.87 | -0.9 | 0.67 | 2.24 |
| Tires "ires" | OFF | 6,428 | 5 | 4 | 21 (+4) (fill under a satin border) | 0.68 | -1.8 | 0.00 | 5.48 |
| | ON | 2,853 | 4 | 2 | 11 (+5) | 0.95 | 0.3 | 0.00 | 5.20 |
| | pro | 3,337 | 3 | 3 | 9 (+2) | 0.85 | 0.3 | 0.39 | 4.64 |
| Machine "achine" | OFF | 2,596 | 8 | 0 | 28 (+2) | 0.77 | -1.9 | 6.10 | 3.48 |
| | ON | 1,705 | 4 | 0 | 26 (+6) | 0.84 | 0.5 | 1.02 | 3.36 |
| | pro | 1,956 | 7 | 0 | 20 (+3) | 0.90 | -7.3 | 0.00 | 3.28 |

Coverage width: twice the distance transform's median on the ridge of the
word's thread coverage (0.4 mm thread). The pro sews Bridge thinner than the
art draws it (his crosses 1.56 / 1.78 mm against a drawn 1.76 / 2.12): a
smaller script pull is ROADMAP gate 1 and is not built.

## Against the art (plan mm, the pipeline's own ink read at half-max)

| job | arm | red on the art's ground mm2 | art counters sewn shut mm2 (of) | bare inside the word mm2 |
|---|---|---|---|---|
| Bridge hat | OFF | 36.5 | 4.84 (10.28) | 0.00 |
| | ON | 39.7 | 3.92 | 0.00 |
| Bridge LC | OFF | 43.3 | 6.41 (15.41) | 0.47 |
| | ON | 39.6 | 4.59 | 0.02 |

## Whole design, bystanders

Bridge hat 9,608 st / 30 trims -> 9,510 / 30; Bridge LC 15,278 / 38 ->
14,894 / 39; Tires 8,205 / 8 -> 4,629 / 7 (pro 5,555 / 10); Machine hat
8,450 / 47 -> 7,704 / 44. Byte-identical with the flag ON: Becker hat small,
MFab hat, Hotel Fremont hat, Golden Tee hat (the door takes nothing there).

## What it does not do

Bridge's "ge" stays a dense knot: at 63-77 mm the 400 px JPEG's trace fuses
the letters and closes the g's and e's counters, and the yellow is knocked
out under the word, so opening them would show bare cap. The pro also re-set
Bridge in a taller font of his own — a design call no trace reproduces.
