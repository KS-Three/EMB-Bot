## instrument as the test reads it (grid registration, art at stitch width)
| fixture | arm | lost_frac | unsewn | wrong colour | overshoot | uncovered ink | stitches | trims | shift |
|---|---|---|---|---|---|---|---|---|---|
| becker | shipped | 0.0236 | 0.0150 | 0.0000 | 0.0086 | 6.00% | 10,969 | 59 | (+0.0, +0.4) |
| becker | lane | 0.0381 | 0.0234 | 0.0000 | 0.0147 | 6.29% | 8,708 | 27 | (+0.0, +0.4) |
| becker | lane+cap | 0.0364 | 0.0217 | 0.0000 | 0.0147 | 6.00% | 8,731 | 27 | (+0.0, +0.4) |
| bridge | shipped | 0.2213 | 0.0000 | 0.1728 | 0.0484 | 0.17% | 18,837 | 101 | (+0.0, +0.0) |
| bridge | lane | 0.2283 | 0.0000 | 0.1799 | 0.0484 | 0.17% | 18,870 | 98 | (+0.0, +0.0) |
| bridge | lane+cap | 0.2283 | 0.0000 | 0.1799 | 0.0484 | 0.17% | 18,870 | 98 | (+0.0, +0.0) |
| drone | shipped | 0.1003 | 0.0000 | 0.0533 | 0.0470 | 0.33% | 19,644 | 132 | (+0.0, +0.4) |
| drone | lane | 0.1060 | 0.0000 | 0.0534 | 0.0526 | 0.45% | 19,191 | 134 | (+0.0, +0.4) |
| drone | lane+cap | 0.1066 | 0.0000 | 0.0534 | 0.0532 | 0.34% | 19,251 | 134 | (+0.0, +0.4) |
| enthusiast | shipped | 0.2771 | 0.0000 | 0.0000 | 0.2771 | 1.80% | 2,602 | 14 | (+0.4, +0.4) |
| enthusiast | lane | 0.3110 | 0.0000 | 0.0000 | 0.3110 | 0.59% | 2,365 | 7 | (+0.4, +0.0) |
| enthusiast | lane+cap | 0.3627 | 0.0000 | 0.0000 | 0.3627 | 1.08% | 2,403 | 7 | (+0.4, +0.4) |
| fremont | shipped | 0.0302 | 0.0000 | 0.0302 | 0.0000 | 0.00% | 20,819 | 63 | (+0.0, +0.0) |
| fremont | lane | 0.0325 | 0.0000 | 0.0325 | 0.0000 | 0.00% | 20,727 | 59 | (+0.0, +0.0) |
| fremont | lane+cap | 0.0326 | 0.0000 | 0.0326 | 0.0000 | 0.00% | 20,783 | 59 | (+0.0, +0.0) |
| golden_tee | shipped | 0.4501 | 0.0000 | 0.2337 | 0.2164 | 0.18% | 8,950 | 44 | (+0.0, +0.4) |
| golden_tee | lane | 0.4698 | 0.0000 | 0.2363 | 0.2335 | 0.20% | 8,398 | 43 | (+0.0, +0.4) |
| golden_tee | lane+cap | 0.4698 | 0.0000 | 0.2363 | 0.2335 | 0.20% | 8,398 | 43 | (+0.0, +0.4) |

## one-pixel registration (each design its own best)
| fixture | shipped | lane | lane+cap |
|---|---|---|---|
| becker | 0.0219 (u 0.0125 w 0.0000 o 0.0094) | 0.0226 (u 0.0178 w 0.0000 o 0.0048) | 0.0168 (u 0.0119 w 0.0000 o 0.0048) |
| bridge | 0.2010 (u 0.0000 w 0.1517 o 0.0493) | 0.2093 (u 0.0000 w 0.1600 o 0.0493) | 0.2093 (u 0.0000 w 0.1600 o 0.0493) |
| drone | 0.0635 (u 0.0000 w 0.0310 o 0.0324) | 0.0638 (u 0.0000 w 0.0311 o 0.0327) | 0.0639 (u 0.0000 w 0.0311 o 0.0328) |
| enthusiast | 0.1697 (u 0.0000 w 0.0000 o 0.1697) | 0.2841 (u 0.0000 w 0.0000 o 0.2841) | 0.2953 (u 0.0000 w 0.0000 o 0.2953) |
| fremont | 0.1028 (u 0.0000 w 0.1028 o 0.0000) | 0.1042 (u 0.0000 w 0.1042 o 0.0000) | 0.1066 (u 0.0000 w 0.1066 o 0.0000) |
| golden_tee | 0.4000 (u 0.0000 w 0.1925 o 0.2075) | 0.4263 (u 0.0000 w 0.2141 o 0.2122) | 0.4263 (u 0.0000 w 0.2141 o 0.2122) |

## matched: ONE physical alignment (shipped design's best 0.1 mm fit), artwork at its own width, mm2
| fixture | arm | lost_frac | unsewn | wrong colour | overshoot | letters overshoot | letters unsewn | spill >0.5 mm |
|---|---|---|---|---|---|---|---|---|
| becker | shipped | 0.0149 | 29.2 | 0.0 | 12.9 | 1.4 | 17.2 | 4.6 |
| becker | lane | 0.0215 | 44.6 | 0.0 | 16.0 | 4.5 | 32.6 | 5.2 |
| becker | lane+cap | 0.0157 | 28.2 | 0.0 | 16.0 | 4.6 | 16.2 | 5.1 |
| bridge | shipped | 0.1937 | 0.0 | 390.4 | 96.9 | 0 | 0 | 2.9 |
| bridge | lane | 0.2014 | 0.0 | 409.8 | 96.9 | 0 | 0 | 2.9 |
| bridge | lane+cap | 0.2014 | 0.0 | 409.8 | 96.9 | 0 | 0 | 2.9 |
| drone | shipped | 0.0701 | 0.0 | 113.0 | 109.6 | 20.5 | 0 | 30.9 |
| drone | lane | 0.0734 | 0.0 | 113.0 | 120.2 | 31.1 | 0 | 35.6 |
| drone | lane+cap | 0.0738 | 0.0 | 113.0 | 121.4 | 32.3 | 0 | 35.8 |
| enthusiast | shipped | 0.1750 | 0.0 | 0.0 | 68.1 | 37.8 | 0 | 8.3 |
| enthusiast | lane | 0.2667 | 0.0 | 0.0 | 103.8 | 73.7 | 0 | 13.5 |
| enthusiast | lane+cap | 0.2824 | 0.0 | 0.0 | 109.9 | 79.8 | 0 | 14.1 |
| fremont | shipped | 0.1277 | 0.0 | 369.8 | 0.0 | 0 | 0 | 33.0 |
| fremont | lane | 0.1299 | 0.0 | 376.2 | 0.0 | 0 | 0 | 33.0 |
| fremont | lane+cap | 0.1312 | 0.0 | 380.0 | 0.0 | 0 | 0 | 33.0 |
| golden_tee | shipped | 0.4308 | 0.0 | 193.4 | 198.2 | 84.7 | 0 | 28.6 |
| golden_tee | lane | 0.4463 | 0.0 | 204.1 | 201.7 | 88.8 | 0 | 36.1 |
| golden_tee | lane+cap | 0.4463 | 0.0 | 204.1 | 201.7 | 88.8 | 0 | 36.1 |

## becker with coverage_edges, matched, MARINE row (y > 12 mm) and whole design, mm2
| arm | lost_frac | unsewn | overshoot | MARINE unsewn | MARINE overshoot | MARINE bare (unfiltered) |
|---|---|---|---|---|---|---|
| shipped | 0.0149 | 29.2 | 12.9 | 17.2 | 1.4 | 65.7 |
| lane | 0.0215 | 44.6 | 16.0 | 32.6 | 4.5 | 65.6 |
| lane+cap | 0.0157 | 28.2 | 16.0 | 16.2 | 4.6 | 57.6 |
| coverage_edges | 0.0220 | 31.7 | 30.4 | 10.2 | 19.3 | 55.9 |
| coverage_edges + lane | 0.0247 | 44.5 | 25.2 | 23.0 | 14.1 | 60.4 |
| coverage_edges + lane+cap | 0.0208 | 33.6 | 25.2 | 12.0 | 14.0 | 51.3 |

covoff grid 0.028 0.009 0.019 stitches 11421 trims 62
cov grid 0.0342 0.0162 0.018 stitches 8896 trims 21
covcap grid 0.0294 0.0089 0.0205 stitches 8937 trims 21
