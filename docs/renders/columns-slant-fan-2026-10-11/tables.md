# Slanted-terminal fan: per-letter readings, 2026-10-11

Every lettering shape on the six eye-pair logos (each at its `REAL_ART` size and garment) with at least one straight column end fanned by `outline_cut._fan_ends`, three arms: **off** (shipped, both lane flags OFF), **before** (lane ON as on main 9185781c), **after** (lane ON, this branch). Produced by `run_arms.py` then `fan_table.py`; letters named by eye from renders.

- **unsewn / bare**: #828's matched instrument (`../columns-lost-frac-2026-10-11/matched.py`), one physical alignment (shipped's best 0.1 mm fit), mm2 of artwork ink attributed to the shape. "unsewn" counts only regions the instrument keeps; "bare" is every ink pixel with no thread.
- **trace-bare**: the shape's own traced polygon with no thread within the 0.4 mm the instrument draws; no raster, no registration.
- **pivots moved**: fanned ends where the new rule moved the pivot to the slant's near corner. Only the Becker A's apex qualifies on these six logos. Every other fanned end keeps its pivot and changes only by the slant-face reach.
- Fremont's letters read 0 on the matched instrument because their spill lands on a neighbouring ink (wrong colour, not counted per shape here).
| logo | shape | letter | fanned ends before / after | pivots moved | unsewn off / before / after | bare off / before / after | trace-bare off / before / after | stitches off / before / after |
|---|---|---|---|---|---|---|---|---|
| becker | S501501b6 | A | 6 / 6 | 1 | 1.3 / 6.7 / 1.1 | 10.47 / 15.27 / 10.26 | 0.51 / 1.52 / 0.13 | 795 / 476 / 478 |
| becker | Scc08b907 | M | 4 / 4 | 0 | 4.9 / 5.0 / 5.0 | 13.44 / 13.64 / 13.63 | 1.56 / 0.00 / 0.00 | 1180 / 540 / 546 |
| becker | Sdd5f27fb | N | 3 / 3 | 0 | 4.0 / 2.4 / 2.4 | 11.99 / 9.13 / 8.63 | 5.36 / 0.05 / 0.08 | 1162 / 634 / 648 |
| becker | Sf1c25fcd | E | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 7.46 / 9.85 / 9.57 | 0.61 / 0.01 / 0.21 | 830 / 495 / 495 |
| bridge | S2953082f | script fragment | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 1.40 / 0.07 / 0.20 | 30 / 49 / 49 |
| bridge | S2c4ea3ad | script fragment | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.09 / 0.07 / 0.06 | 115 / 128 / 132 |
| bridge | S3963a893 | script fragment | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.67 / 0.10 / 0.09 | 52 / 65 / 60 |
| bridge | Sc434b18d | script fragment | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.08 / 0.04 / 0.05 | 82 / 53 / 51 |
| drone | S0d4a3c8f | N | 3 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.29 / 0.19 | 0.00 / 0.10 / 0.07 | 58 / 63 / 67 |
| drone | S14057482 | E | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.09 / 0.03 / 0.00 | 0.07 / 0.00 / 0.00 | 148 / 135 / 135 |
| drone | S1e345617 | P | 4 / 4 | 0 | 0.0 / 0.0 / 0.0 | 0.01 / 0.42 / 0.09 | 0.09 / 0.12 / 0.03 | 226 / 166 / 178 |
| drone | S24beef6d | C | 4 / 4 | 0 | 0.0 / 0.0 / 0.0 | 0.01 / 0.04 / 0.06 | 0.10 / 0.08 / 0.10 | 135 / 156 / 156 |
| drone | S3c4af2e7 | O | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.11 / 0.00 / 0.00 | 0.14 / 0.04 / 0.04 | 256 / 191 / 191 |
| drone | S3e7df60e | H | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.19 / 0.04 / 0.00 | 0.15 / 0.06 / 0.00 | 167 / 126 / 126 |
| drone | S5403dda0 | N | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.10 / 0.25 / 0.25 | 0.01 / 0.07 / 0.07 | 52 / 68 / 68 |
| drone | S6cc4a060 | M | 6 / 6 | 0 | 0.0 / 0.0 / 0.0 | 0.29 / 0.19 / 0.18 | 0.20 / 0.01 / 0.02 | 150 / 163 / 161 |
| drone | S6d6db17f | D | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.01 / 0.01 / 0.01 | 66 / 73 / 73 |
| drone | S6dd674f6 | R | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.22 / 0.08 / 0.08 | 0.16 / 0.07 / 0.06 | 276 / 196 / 195 |
| drone | S79734ace | I | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.02 / 0.03 / 0.03 | 41 / 43 / 43 |
| drone | S81b4b426 | L | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.07 / 0.00 / 0.01 | 0.15 / 0.00 / 0.03 | 80 / 88 / 86 |
| drone | S81d913c5 | A | 6 / 6 | 0 | 0.0 / 0.0 / 0.0 | 0.03 / 0.00 / 0.00 | 0.03 / 0.03 / 0.02 | 123 / 122 / 128 |
| drone | S8438f8fc | N | 3 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.25 / 0.06 / 0.06 | 0.25 / 0.03 / 0.02 | 230 / 176 / 177 |
| drone | S84fc22b3 | T | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.12 / 0.00 | 0.00 / 0.01 / 0.06 | 98 / 84 / 84 |
| drone | S89cc9fe3 | S | 5 / 5 | 0 | 0.0 / 0.0 / 0.0 | 0.30 / 0.23 / 0.03 | 0.23 / 0.12 / 0.09 | 304 / 239 / 238 |
| drone | S9833f682 | A | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.31 / 0.24 / 0.24 | 0.06 / 0.04 / 0.03 | 64 / 64 / 62 |
| drone | Sa05913cd | R | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.23 / 0.16 / 0.16 | 0.05 / 0.01 / 0.01 | 84 / 84 / 84 |
| drone | Sa34f3d79 | E | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.12 / 0.45 / 0.05 | 0.02 / 0.00 / 0.07 | 217 / 191 / 191 |
| drone | Sbf8a37c3 | R | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.01 / 0.08 / 0.08 | 0.03 / 0.05 / 0.05 | 185 / 147 / 146 |
| drone | Sc874fb6b | fragment | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.07 / 0.00 / 0.00 | 82 / 84 / 84 |
| enthusiast | S7d55ed5c | N | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.61 / 0.07 / 0.07 | 0.96 / 0.00 / 0.00 | 136 / 127 / 133 |
| enthusiast | S90fd1f2c | H | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.07 / 0.19 / 0.19 | 0.06 / 0.00 / 0.00 | 155 / 115 / 116 |
| enthusiast | Scd87e08f | A | 6 / 6 | 0 | 0.0 / 0.0 / 0.0 | 0.41 / 0.08 / 0.09 | 0.96 / 0.06 / 0.06 | 170 / 130 / 138 |

| logo | lost_frac off / before / after (matched) | unsewn mm2 | letters' unsewn mm2 |
|---|---|---|---|
| becker | 0.0149 / 0.0150 / 0.0131 | 29.2 / 29.2 / 23.7 | 17.2 / 17.2 / 11.6 |
| bridge | 0.1937 / 0.1917 / 0.1920 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| drone | 0.0701 / 0.0661 / 0.0665 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| enthusiast | 0.1750 / 0.1395 / 0.1409 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |

| logo | shape | letter | fanned ends before / after | pivots moved | unsewn off / before / after | bare off / before / after | trace-bare off / before / after | stitches off / before / after |
|---|---|---|---|---|---|---|---|---|
| fremont | S3ddcec6c | ? | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.07 / 0.24 / 0.24 | 82 / 53 / 53 |
| fremont | S402cb6b3 | ? | 4 / 4 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.04 / 0.16 / 0.16 | 125 / 125 / 125 |
| fremont | S42e426b8 | ? | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.03 / 0.23 / 0.23 | 49 / 47 / 47 |
| fremont | S5467a2d3 | ? | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.15 / 0.43 / 0.43 | 194 / 209 / 209 |
| fremont | S666da526 | ? | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.06 / 0.14 / 0.14 | 55 / 57 / 56 |
| fremont | S9c0c9dc7 | ? | 1 / 1 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.14 / 0.07 / 0.07 | 172 / 158 / 158 |
| fremont | Sbad07f9f | ? | 4 / 4 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.03 / 0.12 / 0.11 | 119 / 128 / 128 |
| fremont | Sd4b05ae6 | ? | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.15 / 0.04 / 0.04 | 166 / 182 / 182 |
| fremont | Sf629d513 | ? | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.19 / 0.01 / 0.01 | 184 / 167 / 165 |
| golden_tee | S0bcd1e39 | ? | 3 / 3 | 0 | 0.0 / 0.0 / 0.0 | 0.04 / 0.02 / 0.02 | 0.25 / 0.08 / 0.06 | 816 / 772 / 776 |
| golden_tee | S235ce2af | ? | 2 / 2 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.00 / 0.11 / 0.10 | 477 / 255 / 257 |
| golden_tee | S597c2467 | ? | 7 / 7 | 0 | 0.0 / 0.0 / 0.0 | 0.95 / 0.97 / 0.95 | 0.00 / 0.16 / 0.04 | 573 / 549 / 557 |
| golden_tee | Sd872d036 | ? | 5 / 5 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.00 | 0.01 / 0.23 / 0.20 | 224 / 153 / 156 |
| golden_tee | Se631d99f | ? | 4 / 4 | 0 | 0.0 / 0.0 / 0.0 | 0.00 / 0.00 / 0.05 | 0.01 / 0.00 / 0.22 | 314 / 114 / 112 |

| logo | lost_frac off / before / after (matched) | unsewn mm2 | letters' unsewn mm2 |
|---|---|---|---|
| fremont | 0.1277 / 0.1143 / 0.1145 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |
| golden_tee | 0.4308 / 0.3951 / 0.3976 | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 |

