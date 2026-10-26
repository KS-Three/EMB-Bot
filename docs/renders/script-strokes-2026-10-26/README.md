# Script strokes (`script_strokes`, built OFF) — 2026-10-26

Kent's ruling, 2026-10-26: "Measure, then build OFF (Recommended)". A script
word sewn one satin column per pen stroke, crosses square to the stroke, the
pen path read on the artwork's own ink. Engine `bde0f145` (this branch merged
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
| | ON | 815 | 1 | 0 | 15 (+5) | 0.84 | -4.6 | 0.66 | 2.68 |
| | pro | 905 | 6 | 7 | 18 (+2) | 0.77 | 3.0 | 0.00 | 1.96 |
| Bridge LC | OFF | 1,251 | 2 | 1 | 23 | 0.77 | -9.9 | 5.32 | 3.00 |
| | ON | 981 | 3 | 2 | 16 (+2) | 0.87 | -2.6 | 1.84 | 2.80 |
| | pro | 1,111 | 6 | 7 | 14 | 0.87 | -0.9 | 0.67 | 2.24 |
| Tires "ires" | OFF | 6,428 | 5 | 4 | 21 (+4) (fill under a satin border) | 0.68 | -1.8 | 0.00 | 5.48 |
| | ON | 3,033 | 2 | 1 | 10 (+3) | 0.95 | 0.2 | 0.34 | 5.12 |
| | pro | 3,337 | 3 | 3 | 9 (+2) | 0.85 | 0.3 | 0.39 | 4.64 |
| Machine "achine" | OFF | 2,596 | 8 | 0 | 28 (+2) | 0.77 | -1.9 | 6.10 | 3.48 |
| | ON | 1,763 | 7 | 0 | 26 (+3) | 0.85 | -0.2 | 0.91 | 3.32 |
| | pro | 1,956 | 7 | 0 | 20 (+3) | 0.90 | -7.3 | 0.00 | 3.28 |

Coverage width: twice the distance transform's median on the ridge of the
word's thread coverage (0.4 mm thread). The pro sews Bridge thinner than the
art draws it (his crosses 1.56 / 1.78 mm against a drawn 1.76 / 2.12): a
smaller script pull is ROADMAP gate 1 and is not built.

## Against the art (plan mm, the pipeline's own ink read at half-max)

| job | arm | red on the art's ground mm2 | art counters sewn shut mm2 (of) | bare inside the word mm2 |
|---|---|---|---|---|
| Bridge hat | OFF | 36.5 | 4.84 (10.28) | 0.00 |
| | ON | 39.4 | 4.20 | 0.00 |
| Bridge LC | OFF | 43.3 | 6.41 (15.41) | 0.47 |
| | ON | 39.8 | 4.74 | 0.01 |

## Whole design, bystanders

Bridge hat 9,608 st / 30 trims -> 9,555 / 30; Bridge LC 15,278 / 38 ->
15,011 / 39; Tires 8,205 / 8 -> 4,807 / 5 (pro 5,555 / 10); Machine hat
8,450 / 47 -> 7,765 / 44. Stage 7's edge cap (a ring where satin leaves
outline bare) rings nothing ON (Machine OFF had one). Bare inside the word:
Tires 0.00 -> 0.20 mm2, Machine 0.53 -> 0.48.

Byte-identical with the flag ON (measured on `ee2675d6`; the commit after
it changes only code past the door): Becker hat small, MFab hat, Hotel
Fremont hat, Golden Tee hat (the door takes nothing there).

## What it does not do

Bridge's "ge" stays a dense knot: at 63-77 mm the 400 px JPEG's trace fuses
the letters and closes the g's and e's counters, and the yellow is knocked
out under the word, so opening them would show bare cap. The pro also re-set
Bridge in a taller font of his own — a design call no trace reproduces.

## Word legibility (`tools/word_legibility.py`, chance-corrected cc at native size, n = 1 word per job)

| job | OFF | ON | pro | note |
|---|---|---|---|---|
| Bridge hat | 0.83 | 0.35 | 1.00 | reach 0.70 -> 0.47 octaves (pro 1.78) |
| Bridge LC | 0.28 | 0.52 | 1.00 | reach 0.20 -> 1.54 (pro 4.16) |
| Tires | -0.27 | 0.14 | 0.00 | blind: the reader cannot read the art itself |
| Machine hat | 0.24 | 0.47 | 0.00 | blind: the reader reads neither the art nor the pro |

Mixed, one word a job, two of four blind: no legibility claim either way
(ROADMAP gate 4).
