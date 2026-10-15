# small_text_true_size ON with the 0.45 mm counter guard: measured 2026-10-15

Studio request path (`tools/fremont_triage.run_arm` through `small_lettering_compare.run_cell`), Hotel Fremont on a Hat at 65 / 72 / 81 / 92.5 mm. Arms: **main (OFF)** = `small_text_true_size=False`, the engine before the flip; **ON + guard** = the shipped default (switch ON, `small_text_keep_stray_lines` filled True, `small_text_true_size_min_counter_mm` 0.45, ink ring OFF); **ON, no guard** = the same with `small_text_true_size_min_counter_mm=None`.

Per line: the restore step's own read of the line's smallest SOURCE counter (`small_text.line_min_counter_mm`, the counter census's measure, PR #964) and whether the switch acted; counters open of the source's (`glyph_legibility`); legibility; OCR glyphs recovered with a Wilson 95% interval (secondary: n is 2-11 glyphs, a census, not a rate); stitches and trims inside the word's box. "whole design" md5 is over the design's stitch records. Nothing here was sewn; 0.45 is a gate-1 CANDIDATE.


#### Fremont Hat 65 mm

| line | arm | smallest source counter mm (guard) | counters open | legibility | OCR (Wilson 95%) | stitches | trims |
|---|---|---|---|---|---|---|---|
| EST | main (OFF) | - (switch OFF) | 0 of 0 | 0.917 | 1/3 [0.06-0.79] | 131 | 1 |
| EST | ON + guard | 0.45 (switch acts) | 0 of 0 | 0.920 | 1/3 [0.06-0.79] | 137 | 1 |
| EST | ON, no guard | not read (no guard) | 0 of 0 | 0.920 | 1/3 [0.06-0.79] | 137 | 1 |
| 1895 | main (OFF) | - (switch OFF) | 2 of 3 | 0.769 | 0/4 [0.00-0.49] | 148 | 2 |
| 1895 | ON + guard | 0.45 (switch acts) | 2 of 3 | 0.769 | 1/4 [0.05-0.70] | 151 | 2 |
| 1895 | ON, no guard | not read (no guard) | 2 of 3 | 0.769 | 1/4 [0.05-0.70] | 151 | 2 |
| THE | main (OFF) | - (switch OFF) | 0 of 0 | 1.000 | 3/3 [0.44-1.00] | 272 | 2 |
| THE | ON + guard | none (switch acts) | 0 of 0 | 0.989 | 3/3 [0.44-1.00] | 221 | 0 |
| THE | ON, no guard | not read (no guard) | 0 of 0 | 0.989 | 3/3 [0.44-1.00] | 221 | 0 |
| tagline | main (OFF) | - (switch OFF) | 3 of 4 | 0.893 | 10/11 [0.62-0.98] | 674 | 6 |
| tagline | ON + guard | 0.439 (below_min_counter) | 3 of 4 | 0.893 | 8/11 [0.43-0.90] | 678 | 7 |
| tagline | ON, no guard | not read (no guard) | 1 of 4 | 0.736 | 5/11 [0.21-0.72] | 543 | 5 |
| whole design | main (OFF) | stitch md5 `c2bbbb00` | | | | 11,463 | 43 |
| whole design | ON + guard | stitch md5 `a037bffe` | | | | 11,423 | 42 |
| whole design | ON, no guard | stitch md5 `a8274d0d` | | | | 11,269 | 39 |

#### Fremont Hat 72 mm

| line | arm | smallest source counter mm (guard) | counters open | legibility | OCR (Wilson 95%) | stitches | trims |
|---|---|---|---|---|---|---|---|
| EST | main (OFF) | - (switch OFF) | 0 of 0 | 0.949 | 1/2 [0.10-0.91] | 149 | 1 |
| EST | ON + guard | none (switch acts) | 0 of 0 | 0.929 | 1/2 [0.10-0.91] | 105 | 0 |
| EST | ON, no guard | not read (no guard) | 0 of 0 | 0.929 | 1/2 [0.10-0.91] | 105 | 0 |
| 1895 | main (OFF) | - (switch OFF) | 1 of 3 | 0.530 | 0/4 [0.00-0.49] | 177 | 2 |
| 1895 | ON + guard | 0.5 (switch acts) | 2 of 3 | 0.786 | 2/4 [0.15-0.85] | 175 | 2 |
| 1895 | ON, no guard | not read (no guard) | 2 of 3 | 0.786 | 2/4 [0.15-0.85] | 175 | 2 |
| THE | main (OFF) | - (switch OFF) | 0 of 0 | 0.634 | 1/3 [0.06-0.79] | 285 | 2 |
| THE | ON + guard | not in a text line | 0 of 0 | 0.634 | 1/3 [0.06-0.79] | 291 | 3 |
| THE | ON, no guard | not in a text line | 0 of 0 | 0.634 | 1/3 [0.06-0.79] | 291 | 3 |
| tagline | main (OFF) | - (switch OFF) | 0 of 4 | 0.676 | 9/11 [0.52-0.95] | 780 | 5 |
| tagline | ON + guard | 0.47 (switch acts) | 1 of 4 | 0.677 | 10/11 [0.62-0.98] | 654 | 7 |
| tagline | ON, no guard | not read (no guard) | 1 of 4 | 0.677 | 10/11 [0.62-0.98] | 654 | 7 |
| whole design | main (OFF) | stitch md5 `6f45f4e1` | | | | 13,363 | 44 |
| whole design | ON + guard | stitch md5 `e3437a9c` | | | | 13,195 | 46 |
| whole design | ON, no guard | stitch md5 `e3437a9c` | | | | 13,195 | 46 |

#### Fremont Hat 81 mm

| line | arm | smallest source counter mm (guard) | counters open | legibility | OCR (Wilson 95%) | stitches | trims |
|---|---|---|---|---|---|---|---|
| EST | main (OFF) | - (switch OFF) | 0 of 0 | 0.967 | 1/2 [0.10-0.91] | 166 | 1 |
| EST | ON + guard | none (switch acts) | 0 of 0 | 0.947 | 2/2 [0.34-1.00] | 124 | 0 |
| EST | ON, no guard | not read (no guard) | 0 of 0 | 0.947 | 2/2 [0.34-1.00] | 124 | 0 |
| 1895 | main (OFF) | - (switch OFF) | 1 of 3 | 0.551 | 1/4 [0.05-0.70] | 212 | 1 |
| 1895 | ON + guard | 0.55 (switch acts) | 3 of 3 | 0.916 | 2/4 [0.15-0.85] | 199 | 2 |
| 1895 | ON, no guard | not read (no guard) | 3 of 3 | 0.916 | 2/4 [0.15-0.85] | 199 | 2 |
| THE | main (OFF) | - (switch OFF) | 0 of 0 | 0.974 | 1/3 [0.06-0.79] | 364 | 3 |
| THE | ON + guard | none (switch acts) | 0 of 0 | 0.998 | 3/3 [0.44-1.00] | 329 | 2 |
| THE | ON, no guard | not read (no guard) | 0 of 0 | 0.998 | 3/3 [0.44-1.00] | 329 | 2 |
| tagline | main (OFF) | - (switch OFF) | 1 of 4 | 0.614 | 11/11 [0.74-1.00] | 970 | 7 |
| tagline | ON + guard | 0.549 (switch acts) | 4 of 4 | 0.996 | 11/11 [0.74-1.00] | 849 | 6 |
| tagline | ON, no guard | not read (no guard) | 4 of 4 | 0.996 | 11/11 [0.74-1.00] | 849 | 6 |
| whole design | main (OFF) | stitch md5 `27cab04f` | | | | 15,625 | 47 |
| whole design | ON + guard | stitch md5 `b4aebef6` | | | | 15,330 | 41 |
| whole design | ON, no guard | stitch md5 `b4aebef6` | | | | 15,330 | 41 |

#### Fremont Hat 92.5 mm

| line | arm | smallest source counter mm (guard) | counters open | legibility | OCR (Wilson 95%) | stitches | trims |
|---|---|---|---|---|---|---|---|
| EST | main (OFF) | - (switch OFF) | 0 of 0 | 0.987 | 1/3 [0.06-0.79] | 203 | 1 |
| EST | ON + guard | none (switch acts) | 0 of 0 | 0.984 | 3/3 [0.44-1.00] | 167 | 1 |
| EST | ON, no guard | not read (no guard) | 0 of 0 | 0.984 | 3/3 [0.44-1.00] | 167 | 1 |
| 1895 | main (OFF) | - (switch OFF) | 0 of 3 | 0.214 | 0/4 [0.00-0.49] | 260 | 1 |
| 1895 | ON + guard | 0.65 (switch acts) | 3 of 3 | 0.960 | 2/4 [0.15-0.85] | 225 | 1 |
| 1895 | ON, no guard | not read (no guard) | 3 of 3 | 0.960 | 2/4 [0.15-0.85] | 225 | 1 |
| THE | main (OFF) | - (switch OFF) | 0 of 0 | 0.649 | 1/3 [0.06-0.79] | 423 | 3 |
| THE | ON + guard | none (tall_enough) | 0 of 0 | 0.667 | 3/3 [0.44-1.00] | 436 | 3 |
| THE | ON, no guard | (tall_enough) | 0 of 0 | 0.667 | 3/3 [0.44-1.00] | 436 | 3 |
| tagline | main (OFF) | - (switch OFF) | 1 of 4 | 0.692 | 11/11 [0.74-1.00] | 1344 | 14 |
| tagline | ON + guard | 0.6 (switch acts) | 4 of 4 | 0.999 | 10/11 [0.62-0.98] | 1217 | 16 |
| tagline | ON, no guard | not read (no guard) | 4 of 4 | 0.999 | 10/11 [0.62-0.98] | 1217 | 16 |
| whole design | main (OFF) | stitch md5 `b0dc5f1d` | | | | 18,882 | 53 |
| whole design | ON + guard | stitch md5 `a5b96dd1` | | | | 18,675 | 54 |
| whole design | ON, no guard | stitch md5 `a5b96dd1` | | | | 18,675 | 54 |

## The 17-design corpus (`small_lettering_compare --corpus <design> main|switch`)

Every switch cell's md5 equals the UNGUARDED switch's of 2026-10-14 (17 of 17): the guard changes nothing on the corpus.

| design | main st / tr | small_text_true_size ON (the default) st / tr | same? | shapes changed | dAU mm2 | dBare mm2 |
|---|---|---|---|---|---|---|
| becker | 8,758 / 29 | 8,758 / 29 | yes | 0 | +0.00 | +0.00 |
| tires | 2,732 / 8 | 2,732 / 8 | yes | 0 | +0.00 | +0.00 |
| enthusiast | 2,447 / 9 | 2,408 / 8 | NO | 22 | +0.00 | +0.12 |
| fremont | 20,952 / 61 | 20,832 / 48 | NO | 74 | +0.00 | +0.00 |
| bridge | 18,923 / 99 | 18,923 / 99 | yes | 0 | +0.00 | +0.00 |
| golden_tee | 8,412 / 45 | 8,412 / 45 | yes | 0 | +0.00 | +0.00 |
| gaulke | 4,893 / 23 | 4,893 / 23 | yes | 0 | +0.00 | +0.00 |
| drone | 19,326 / 131 | 19,281 / 130 | NO | 8 | +0.00 | +0.44 |
| screenshot | 8,467 / 58 | 8,511 / 63 | NO | 37 | +0.00 | +2.69 |
| fremont_hat81 | 15,625 / 47 | 15,330 / 41 | NO | 123 | +0.00 | +0.00 |
| fremont_hat925 | 18,882 / 53 | 18,675 / 54 | NO | 71 | +0.00 | +0.00 |
| sp_synthetic_2.5 | 463 / 8 | 321 / 1 | NO | 8 | +0.00 | +1.25 |
| sp_synthetic_3 | 474 / 4 | 378 / 2 | NO | 8 | +0.00 | +0.93 |
| sp_synthetic_4 | 547 / 4 | 547 / 4 | yes | 0 | +0.00 | +0.00 |
| sp_fremont_tagline_2.5 | 624 / 5 | 569 / 5 | NO | 13 | +0.00 | +1.44 |
| sp_fremont_tagline_3 | 618 / 7 | 719 / 5 | NO | 13 | +0.00 | -2.06 |
| sp_fremont_tagline_4 | 944 / 6 | 991 / 10 | NO | 13 | +0.00 | +1.56 |

| design | arm | words | mean legibility | worst word | OCR glyphs recovered (Wilson 95%) |
|---|---|---|---|---|---|
| becker | main | 2 | 0.913 | BECKER 0.827 | n/a |
| becker | switch | 2 | 0.913 | BECKER 0.827 | n/a |
| fremont | main | 6 | 0.816 | 1895 0.214 | 27/33 [0.66-0.91] |
| fremont | switch | 6 | 0.932 | the 0.667 | 29/33 [0.73-0.95] |
| bridge | main | 2 | 0.480 | BAR & RESTAURANT 0.227 | 0/1 [0.00-0.79] |
| bridge | switch | 2 | 0.480 | BAR & RESTAURANT 0.227 | 0/1 [0.00-0.79] |
| fremont_hat81 | main | 6 | 0.816 | 1895 0.551 | 26/32 [0.65-0.91] |
| fremont_hat81 | switch | 6 | 0.941 | fremont 0.835 | 30/32 [0.80-0.98] |
| fremont_hat925 | main | 6 | 0.747 | 1895 0.214 | 25/33 [0.59-0.87] |
| fremont_hat925 | switch | 6 | 0.925 | the 0.667 | 30/33 [0.76-0.97] |

