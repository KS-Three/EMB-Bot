# Today's main against the pro, every paired job (2026-10-27)

**Measured on main `2c6b656c`.** These are its digitize outputs: 20 jobs from the white-recipe v2 run's TODAY arm, plus MFab hat and LC digitized once on the same head. Each job was digitized with the Studio's request at the pro's width and garment, then read beside the pro's file. **Numbers only: no pro file or render is committed.**

**Main has moved since.** Three defaults flipped after `2c6b656c`, and they will move some rows:

- `small_text_reset_grow_away` ON (#1127): ProSeal's tagline.
- `keyline_loop_chain` rides the MFab gate (#1134): MFab hat and LC trims.
- `script_strokes` ON (#1136): script words on Bridge, Tires and To a T.

Re-run the commands below on the current head before quoting a row from those jobs as live.

## How to read it

| figure | meaning |
|---|---|
| stitches / trims / colour changes | Read from each machine file by one reader (`tools.pro_pair.pro_counts`, pystitch), ours and the pro's alike. |
| needle-up mm | The straight gap the needle flies with the thread up, from the last stitch before a JUMP / TRIM / COLOR_CHANGE / STOP to the first stitch after it, summed. `hops` counts those gaps. |
| sttype kappa | `pro_parity.scorecard`'s stitch-type agreement (satin / fill / run) over the shared solid area. It is **chance-corrected** (ROADMAP gate 4), and the chance floor is printed beside it. No raw agreement is quoted. |
| direction kappa | Same area, stitch direction, chance-corrected. 0.00 means no better than chance. |
| word cc | `tools.word_legibility`'s chance-corrected per-word reading at native size, over the words located in both files. It exists only for the four jobs with pinned words. A word that cannot be located is n/loc, never 0. |

On MFab, the reader cannot read MFAB or LLC off the art itself (art cc 0.00), so that job's cc is a weak signal.

## Rebuild

From `digitizer/`, on the head you want measured:

```
python -m tools.pro_baseline digitize --runs DIR      # one digitize per job (22), the Studio's request
python -m tools.pro_baseline measure --runs DIR       # counts, needle-up, kappas, word cc -> DIR/baseline.json
python -m tools.pro_baseline table --runs DIR         # these tables
```

The pro files are gitignored third-party files: set `EMB_SCRATCH_KENT` and `EMB_BRIDGE_PRO` (`tools/pro_baseline.py`'s docstring).

One digitize at a time; each needs a cpu slot on Kent's laptop. For this doc the digitize step ran through the v2 harness: the same request, with a rembg timeout of 900 s against main's 120 s, which only decides whether a slow cutout finishes. `measure` and `table` are exactly the commands above.

## All jobs

| job | stitches ours / pro (gap) | trims ours / pro (gap) | colour changes ours / pro | needle-up mm ours / pro (gap) | sttype kappa (chance) | direction kappa | word cc ours / pro |
|---|---|---|---|---|---|---|---|
| bridge_hat | 9,608 / 6,650 (+44%) | 24 / 20 (+4) | 5 / 4 | 454 / 199 (+128%) | 0.23 (0.51) | 0.03 | - |
| bridge_lc | 15,278 / 8,535 (+79%) | 32 / 20 (+12) | 5 / 4 | 730 / 214 (+241%) | 0.04 (0.50) | 0.00 | - |
| becker_hat_large | 16,915 / 12,356 (+37%) | 24 / 10 (+14) | 1 / 4 | 624 / 416 (+50%) | 0.20 (0.50) | 0.34 | 1.00 / 1.00 (n 2) |
| becker_lc_large | 15,496 / 11,274 (+37%) | 26 / 12 (+14) | 1 / 3 | 698 / 376 (+86%) | 0.25 (0.49) | 0.34 | - |
| becker_hat_small | 11,144 / 8,694 (+28%) | 17 / 11 (+6) | 1 / 4 | 397 / 322 (+23%) | 0.50 (0.50) | 0.42 | - |
| becker_chest_small | 10,948 / 8,694 (+26%) | 21 / 12 (+9) | 1 / 3 | 445 / 292 (+52%) | 0.50 (0.50) | 0.45 | - |
| becker_beanie | 14,495 / 11,411 (+27%) | 18 / 11 (+7) | 2 / 5 | 338 / 376 (-10%) | 0.23 (0.54) | 0.40 | - |
| gaulke_roofing_hat | 7,474 / 6,138 (+22%) | 31 / 42 (-11) | 2 / 0 | 420 / 502 (-16%) | 0.14 (0.84) | 0.51 | - |
| gaulke_roofing_lc | 5,778 / 5,151 (+12%) | 23 / 42 (-19) | 1 / 0 | 317 / 373 (-15%) | 0.29 (0.87) | 0.51 | - |
| gaulke_roofing_beanie | 7,694 / 7,051 (+9%) | 25 / 42 (-17) | 3 / 1 | 365 / 409 (-11%) | 0.31 (0.51) | 0.01 | - |
| hotel_fremont_hat | 17,385 / 17,067 (+2%) | 38 / 21 (+17) | 3 / 10 | 636 / 507 (+25%) | 0.39 (0.43) | 0.00 | 0.61 / 1.00 (n 8) |
| hotel_fremont_patch | 19,292 / 15,458 (+25%) | 40 / 21 (+19) | 3 / 8 | 726 / 533 (+36%) | 0.48 (0.44) | 0.00 | - |
| mfab_hat | 20,561 / 17,568 (+17%) | 30 / 19 (+11) | 2 / 4 | 662 / 392 (+69%) | 0.56 (0.49) | 0.00 | 0.04 / 0.60 (n 4) |
| mfab_lc | 17,777 / 15,786 (+13%) | 25 / 20 (+5) | 2 / 4 | 341 / 368 (-7%) | 0.56 (0.48) | 0.00 | - |
| precision_drone | 14,547 / 14,552 (+0%) | 92 / 59 (+33) | 11 / 22 | 1,858 / 901 (+106%) | 0.20 (0.57) | 0.24 | - |
| proseal_hat | 6,761 / 5,894 (+15%) | 33 / 54 (-21) | 6 / 4 | 479 / 431 (+11%) | 0.21 (0.69) | 0.39 | 0.93 / 1.00 (n 3) |
| proseal_beanie | 7,731 / 7,117 (+9%) | 27 / 48 (-21) | 7 / 5 | 483 / 404 (+20%) | 0.21 (0.43) | 0.00 | - |
| tires_hat_3d | 8,205 / 5,555 (+48%) | 7 / 10 (-3) | 0 / 1 | 191 / 273 (-30%) | 0.00 (0.50) | 0.25 | - |
| goldentee_hat | 11,629 / 5,973 (+95%) | 26 / 10 (+16) | 8 / 6 | 550 / 289 (+90%) | 0.58 (0.66) | 0.27 | - |
| toat_machine_hat | 23,427 / 13,886 (+69%) | 58 / 31 (+27) | 1 / 1 | 872 / 528 (+65%) | 0.40 (0.50) | 0.10 | - |
| toat_machine_beanie | 21,292 / 14,817 (+44%) | 46 / 31 (+15) | 2 / 2 | 710 / 531 (+34%) | 0.35 (0.51) | 0.22 | - |
| toat_beanie | 20,964 / 15,111 (+39%) | 40 / 31 (+9) | 2 / 2 | 756 / 533 (+42%) | 0.40 (0.50) | 0.27 | - |

## Five worst gaps

Each artwork counts once, by its worst job. The gap is ours minus the pro's, as a share of the pro's.

**By trims**

| artwork | job | ours | pro | gap |
|---|---|---|---|---|
| Golden Tee | goldentee_hat | 26 | 10 | +16 (+160%) |
| Becker | becker_hat_large | 24 | 10 | +14 (+140%) |
| Hotel Fremont | hotel_fremont_patch | 40 | 21 | +19 (+90%) |
| To a T | toat_machine_hat | 58 | 31 | +27 (+87%) |
| Bridge | bridge_lc | 32 | 20 | +12 (+60%) |

Next by share: MFab hat, 30 against 19 (+58%), and Precision Drone, 92 against 59 (+56%). Drone's +33 is the largest trim gap in absolute terms. Our trims sit BELOW the pro's on Gaulke (all three jobs, -11 to -19), ProSeal (-21 on both) and Tires (-3).

**By stitches**

| artwork | job | ours | pro | gap |
|---|---|---|---|---|
| Golden Tee | goldentee_hat | 11,629 | 5,973 | +5,656 (+95%) |
| Bridge | bridge_lc | 15,278 | 8,535 | +6,743 (+79%) |
| To a T | toat_machine_hat | 23,427 | 13,886 | +9,541 (+69%) |
| Tires | tires_hat_3d | 8,205 | 5,555 | +2,650 (+48%) |
| Becker | becker_lc_large | 15,496 | 11,274 | +4,222 (+37%) |

Every job sews more stitches than the pro except Precision Drone, which matches him (14,547 against 14,552).

## Per job

#### bridge_hat (hat_front, 63.3 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 9,608 | 6,650 | +2,958 (+44%) |
| trims | 24 | 20 | +4 (+20%) |
| colour changes | 5 | 4 | +1 (+25%) |
| needle-up mm | 454 | 199 | +255 (+128%) |
| needle-up hops | 43 | 23 | +20 (+87%) |
| sttype kappa (chance floor) | 0.23 (0.51) | | |
| direction kappa | 0.03 | | |

#### bridge_lc (left_chest, 76.6 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 15,278 | 8,535 | +6,743 (+79%) |
| trims | 32 | 20 | +12 (+60%) |
| colour changes | 5 | 4 | +1 (+25%) |
| needle-up mm | 730 | 214 | +516 (+241%) |
| needle-up hops | 51 | 23 | +28 (+122%) |
| sttype kappa (chance floor) | 0.04 (0.50) | | |
| direction kappa | 0.00 | | |

#### becker_hat_large (hat_front, 101.9 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 16,915 | 12,356 | +4,559 (+37%) |
| trims | 24 | 10 | +14 (+140%) |
| colour changes | 1 | 4 | -3 (-75%) |
| needle-up mm | 624 | 416 | +208 (+50%) |
| needle-up hops | 31 | 13 | +18 (+138%) |
| sttype kappa (chance floor) | 0.20 (0.50) | | |
| direction kappa | 0.34 | | |
| word cc, native (2 words) | 1.00 | 1.00 | +0.00 |

#### becker_lc_large (left_chest, 95.7 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 15,496 | 11,274 | +4,222 (+37%) |
| trims | 26 | 12 | +14 (+117%) |
| colour changes | 1 | 3 | -2 (-67%) |
| needle-up mm | 698 | 376 | +322 (+86%) |
| needle-up hops | 34 | 14 | +20 (+143%) |
| sttype kappa (chance floor) | 0.25 (0.49) | | |
| direction kappa | 0.34 | | |

#### becker_hat_small (hat_front, 76.5 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 11,144 | 8,694 | +2,450 (+28%) |
| trims | 17 | 11 | +6 (+55%) |
| colour changes | 1 | 4 | -3 (-75%) |
| needle-up mm | 397 | 322 | +75 (+23%) |
| needle-up hops | 22 | 14 | +8 (+57%) |
| sttype kappa (chance floor) | 0.50 (0.50) | | |
| direction kappa | 0.42 | | |

#### becker_chest_small (left_chest, 76.5 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 10,948 | 8,694 | +2,254 (+26%) |
| trims | 21 | 12 | +9 (+75%) |
| colour changes | 1 | 3 | -2 (-67%) |
| needle-up mm | 445 | 292 | +153 (+52%) |
| needle-up hops | 28 | 14 | +14 (+100%) |
| sttype kappa (chance floor) | 0.50 (0.50) | | |
| direction kappa | 0.45 | | |

#### becker_beanie (beanie, 79.8 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 14,495 | 11,411 | +3,084 (+27%) |
| trims | 18 | 11 | +7 (+64%) |
| colour changes | 2 | 5 | -3 (-60%) |
| needle-up mm | 338 | 376 | -37 (-10%) |
| needle-up hops | 24 | 15 | +9 (+60%) |
| sttype kappa (chance floor) | 0.23 (0.54) | | |
| direction kappa | 0.40 | | |

#### gaulke_roofing_hat (hat_front, 114.2 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 7,474 | 6,138 | +1,336 (+22%) |
| trims | 31 | 42 | -11 (-26%) |
| colour changes | 2 | 0 | +2 |
| needle-up mm | 420 | 502 | -82 (-16%) |
| needle-up hops | 47 | 41 | +6 (+15%) |
| sttype kappa (chance floor) | 0.14 (0.84) | | |
| direction kappa | 0.51 | | |

#### gaulke_roofing_lc (left_chest, 95.2 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 5,778 | 5,151 | +627 (+12%) |
| trims | 23 | 42 | -19 (-45%) |
| colour changes | 1 | 0 | +1 |
| needle-up mm | 317 | 373 | -56 (-15%) |
| needle-up hops | 47 | 41 | +6 (+15%) |
| sttype kappa (chance floor) | 0.29 (0.87) | | |
| direction kappa | 0.51 | | |

#### gaulke_roofing_beanie (beanie, 93.8 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 7,694 | 7,051 | +643 (+9%) |
| trims | 25 | 42 | -17 (-40%) |
| colour changes | 3 | 1 | +2 (+200%) |
| needle-up mm | 365 | 409 | -44 (-11%) |
| needle-up hops | 50 | 42 | +8 (+19%) |
| sttype kappa (chance floor) | 0.31 (0.51) | | |
| direction kappa | 0.01 | | |

#### hotel_fremont_hat (hat_front, 92.6 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 17,385 | 17,067 | +318 (+2%) |
| trims | 38 | 21 | +17 (+81%) |
| colour changes | 3 | 10 | -7 (-70%) |
| needle-up mm | 636 | 507 | +129 (+25%) |
| needle-up hops | 180 | 30 | +150 (+500%) |
| sttype kappa (chance floor) | 0.39 (0.43) | | |
| direction kappa | 0.00 | | |
| word cc, native (8 words) | 0.61 | 1.00 | -0.39 |

#### hotel_fremont_patch (patch, 92.5 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 19,292 | 15,458 | +3,834 (+25%) |
| trims | 40 | 21 | +19 (+90%) |
| colour changes | 3 | 8 | -5 (-62%) |
| needle-up mm | 726 | 533 | +194 (+36%) |
| needle-up hops | 180 | 28 | +152 (+543%) |
| sttype kappa (chance floor) | 0.48 (0.44) | | |
| direction kappa | 0.00 | | |

#### mfab_hat (hat_front, 104.9 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 20,561 | 17,568 | +2,993 (+17%) |
| trims | 30 | 19 | +11 (+58%) |
| colour changes | 2 | 4 | -2 (-50%) |
| needle-up mm | 662 | 392 | +270 (+69%) |
| needle-up hops | 44 | 22 | +22 (+100%) |
| sttype kappa (chance floor) | 0.56 (0.49) | | |
| direction kappa | 0.00 | | |
| word cc, native (4 words) | 0.04 | 0.60 | -0.56 |

#### mfab_lc (left_chest, 96.7 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 17,777 | 15,786 | +1,991 (+13%) |
| trims | 25 | 20 | +5 (+25%) |
| colour changes | 2 | 4 | -2 (-50%) |
| needle-up mm | 341 | 368 | -26 (-7%) |
| needle-up hops | 39 | 23 | +16 (+70%) |
| sttype kappa (chance floor) | 0.56 (0.48) | | |
| direction kappa | 0.00 | | |

#### precision_drone (hat_front, 62.6 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 14,547 | 14,552 | -5 (+0%) |
| trims | 92 | 59 | +33 (+56%) |
| colour changes | 11 | 22 | -11 (-50%) |
| needle-up mm | 1,858 | 901 | +957 (+106%) |
| needle-up hops | 150 | 80 | +70 (+88%) |
| sttype kappa (chance floor) | 0.20 (0.57) | | |
| direction kappa | 0.24 | | |

#### proseal_hat (hat_front, 85.9 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 6,761 | 5,894 | +867 (+15%) |
| trims | 33 | 54 | -21 (-39%) |
| colour changes | 6 | 4 | +2 (+50%) |
| needle-up mm | 479 | 431 | +48 (+11%) |
| needle-up hops | 63 | 57 | +6 (+11%) |
| sttype kappa (chance floor) | 0.21 (0.69) | | |
| direction kappa | 0.39 | | |
| word cc, native (3 words) | 0.93 | 1.00 | -0.07 |

#### proseal_beanie (beanie, 75.0 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 7,731 | 7,117 | +614 (+9%) |
| trims | 27 | 48 | -21 (-44%) |
| colour changes | 7 | 5 | +2 (+40%) |
| needle-up mm | 483 | 404 | +79 (+20%) |
| needle-up hops | 61 | 52 | +9 (+17%) |
| sttype kappa (chance floor) | 0.21 (0.43) | | |
| direction kappa | 0.00 | | |

#### tires_hat_3d (hat_front, 114.3 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 8,205 | 5,555 | +2,650 (+48%) |
| trims | 7 | 10 | -3 (-30%) |
| colour changes | 0 | 1 | -1 (-100%) |
| needle-up mm | 191 | 273 | -82 (-30%) |
| needle-up hops | 7 | 10 | -3 (-30%) |
| sttype kappa (chance floor) | 0.00 (0.50) | | |
| direction kappa | 0.25 | | |

#### goldentee_hat (hat_front, 74.9 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 11,629 | 5,973 | +5,656 (+95%) |
| trims | 26 | 10 | +16 (+160%) |
| colour changes | 8 | 6 | +2 (+33%) |
| needle-up mm | 550 | 289 | +261 (+90%) |
| needle-up hops | 43 | 15 | +28 (+187%) |
| sttype kappa (chance floor) | 0.58 (0.66) | | |
| direction kappa | 0.27 | | |

#### toat_machine_hat (hat_front, 89.5 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 23,427 | 13,886 | +9,541 (+69%) |
| trims | 58 | 31 | +27 (+87%) |
| colour changes | 1 | 1 | +0 (+0%) |
| needle-up mm | 872 | 528 | +344 (+65%) |
| needle-up hops | 119 | 31 | +88 (+284%) |
| sttype kappa (chance floor) | 0.40 (0.50) | | |
| direction kappa | 0.10 | | |

#### toat_machine_beanie (beanie, 81.0 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 21,292 | 14,817 | +6,475 (+44%) |
| trims | 46 | 31 | +15 (+48%) |
| colour changes | 2 | 2 | +0 (+0%) |
| needle-up mm | 710 | 531 | +179 (+34%) |
| needle-up hops | 70 | 32 | +38 (+119%) |
| sttype kappa (chance floor) | 0.35 (0.51) | | |
| direction kappa | 0.22 | | |

#### toat_beanie (beanie, 82.3 mm)

| | ours | pro | gap |
|---|---|---|---|
| stitches | 20,964 | 15,111 | +5,853 (+39%) |
| trims | 40 | 31 | +9 (+29%) |
| colour changes | 2 | 2 | +0 (+0%) |
| needle-up mm | 756 | 533 | +222 (+42%) |
| needle-up hops | 88 | 32 | +56 (+175%) |
| sttype kappa (chance floor) | 0.40 (0.50) | | |
| direction kappa | 0.27 | | |
