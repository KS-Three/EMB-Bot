# Pro overlay loop — first run (2026-09-11)

Engine: `claude/pro-overlay-diff` at `ce2c114` (origin/main `6919485` + this lane). Prep: real lane, `prep_both.py <slugs>`, corpus root `scratch_kent/Embroidery Files`, art via `ART_FALLBACK` (the Drive was not mounted this run — all three designs resolved through the committed fixtures in `digitizer/testdata/`). Commands at the bottom. No ranking, no score: every number below is a measurement, not a grade.

## Becker LC large — 95.7 mm, left_chest

registration iou 0.643, scale 0.996, flip_y False, shift (0.3, 0.2) mm. Sheet: `docs/renders/pro-overlay-2026-09-11/becker_lc_large_overlay.png`.

### Flagged craft rows

`density` is reported here and never flagged: row/fill pitch is a ruled constant (`machine.FILL_ROW_MM` = 0.15 mm), not a target either side is graded against. `trims` counts distinct SOURCE PASSES that contributed thread to a region (a lift count), not the region's own chunk count — chunking a long pro pass at a region boundary can hand one region several chunks from a single lift.

| region | mm² | flags | tier ours / pro | width p50 | direction | pitch | layers | density (reported, not flagged) | trims (distinct passes, not lifts) | recipe |
|---|---:|---|---|---|---|---|---|---|---|---|
| See5c8a7d | 20.50 | tier,width,direction,pitch,layers | fill / satin (planned fill) | 0.19 / 3.10 | 77.50 / 3.30 | 0.12 / 0.16 | 5.75 / 3.94 | 19.41 / 15.56 | 1 / 2 | `S.R \| R \| O \| R \| O \| R \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S79ea681a | 162.70 | tier,width,pitch,layers | fill / satin (planned fill) | 0.21 / 4.90 | 92.90 / 155.40 | 0.15 / 0.20 | 5.67 / 1.70 | 16.34 / 9.92 | 1 / 1 | `S.R \| R \| R \| R \| R \| R \| …` / `Z \| R.S.Z.R \| O \| R.S.Z.R \| O \| S` |
| Sd173a6a3 | 917.20 | tier,width,layers | fill / satin (planned fill) | 0.26 / 2.26 | 166.60 / 22.20 | 0.15 / 0.12 | 5.50 / 3.34 | 18.64 / 15.58 | 20 / 4 | `S.O.R \| O \| O \| O \| O \| R \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S64bc1dbe | 189.70 | tier,width,layers | fill / satin (planned fill) | 0.28 / 4.90 | 83.40 / 176.60 | 0.14 / 0.15 | 5.67 / 1.68 | 16.23 / 9.16 | 1 / 1 | `R \| R \| R \| R \| R \| R \| …` / `R.Z.R.S.R.Z \| R \| R \| S.Z.R.S.Z \| R \| R.` |
| S32b446a3 | 187.80 | tier,width,layers | fill / satin (planned fill) | 0.28 / 4.90 | 90.70 / 175.00 | 0.14 / 0.15 | 5.67 / 3.41 | 16.36 / 10.06 | 1 / 1 | `S.R \| O \| O \| O \| O \| O \| …` / `R.Z.R \| R \| S.Z \| R \| R \| S.Z.O.R.S.Z.R.` |
| Sa1103fec | 166.00 | tier,width,layers | fill / satin (planned fill) | 0.19 / 4.67 | 79.00 / 8.60 | 0.15 / 0.15 | 5.65 / 1.70 | 16.35 / 9.96 | 1 / 1 | `S.R \| R \| R \| O \| O \| R \| …` / `Z.R.S.O.Z \| R \| R \| R \| S.O.Z.R.S` |
| S9e70ec80 | 149.50 | tier,width,layers | fill / satin (planned fill) | 0.41 / 4.80 | 173.20 / 145.10 | 0.14 / 0.15 | 5.72 / 1.57 | 16.66 / 8.74 | 1 / 1 | `S.R \| R \| R \| R \| R \| R \| …` / `Z.R.S.O.Z.Z.R.S \| Z \| R \| S \| O` |
| S1a1d6bde | 71.20 | tier,width,pitch | fill / satin (planned satin) | 4.31 / 4.90 | 4.40 / 164.30 | 0.13 / 0.20 | 1.05 / 1.64 | 5.86 / 9.47 | 2 / 1 | `S \| S.Z.S` / `S.Z.R \| O \| S` |
| Sa0fdcf51 | 19.90 | tier,width,layers | fill / satin (planned fill) | 0.23 / 3.30 | 83.50 / 10.80 | 0.18 / 0.18 | 5.73 / 4.09 | 19.31 / 16.66 | 1 / 2 | `S.O.R \| R \| R \| R \| R \| R \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sd7b29a99 | 322.00 | tier,layers | run / fill | — / 2.44 | 86.70 / 20.10 | — / 0.16 | 0.37 / 2.82 | 0.16 / 6.66 | 6 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| R \| O \| O \| …` |
| S9abe3aa7 | 192.90 | tier,layers | run / fill | — / 1.90 | 85.70 / 22.30 | — / 0.17 | 0.44 / 2.95 | 0.21 / 7.21 | 6 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S5be3de64 | 175.90 | tier,layers | run / fill | — / — | 21.40 / 21.60 | — / 0.16 | 0.42 / 2.80 | 0.13 / 6.09 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `R \| O \| O \| O \| O \| O \| …` |
| Sd761ec00 | 30.90 | tier,layers | fill / satin (planned fill) | — / 4.20 | 140.50 / 12.20 | 0.18 / 0.18 | 5.69 / 3.96 | 18.15 / 16.26 | 1 / 2 | `S.R \| R \| O \| R \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S7d68682c | 322.20 | layers | none / fill | — / — | 93.80 / 22.70 | — / 0.18 | 0.37 / 2.74 | 0.13 / 6.41 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `R \| O \| O \| R \| O \| O \| …` |
| Sef4e6850 | 300.50 | layers | none / fill | — / 1.80 | 117.80 / 23.70 | — / 0.17 | 0.43 / 2.87 | 0.18 / 6.85 | 7 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |

15 flagged rows: 9 belong to "BECKER" (the arched outline word plus its drop-shadow layer — `Sd173a6a3`, `Sef4e6850`, `S9abe3aa7`, `S5be3de64`, `Sd7b29a99`, `S7d68682c`, `See5c8a7d`, `Sa0fdcf51`, `Sd761ec00`), 6 to "MARINE" (`S64bc1dbe`, `S32b446a3`, `Sa1103fec`, `S79ea681a`, `S9e70ec80`, `S1a1d6bde`). Crops: `becker_lc_large_crop_becker_outline.png` (union of the 9 BECKER rows' bounds), `becker_lc_large_crop_marine.png` (union of the 6 MARINE rows' bounds).

### Shape rows — Kent's call (the pro departed from the artwork)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| redesign | pro | 239.7 | [-35.7, -8.9] | S7d68682c | `--crop -44.5 -23.3 -26.9 7.7` |
| redesign | pro | 238.6 | [36.0, -9.5] | Sd7b29a99 | `--crop 27.3 -25.3 45.9 7.7` |
| redesign | pro | 129.0 | [6.0, -17.3] | S9abe3aa7 | `--crop -0.5 -28.4 15.0 -6.1` |
| redesign | pro | 113.3 | [21.0, -14.4] | S5be3de64 | `--crop 14.6 -26.5 28.2 -1.5` |
| redesign | pro | 100.0 | [-21.2, -14.3] | Sef4e6850 | `--crop -26.7 -26.2 -14.5 -2.2` |
| redesign | pro | 84.9 | [-8.9, -16.3] | Sd173a6a3 | `--crop -14.9 -28.4 -0.7 -7.4` |
| redesign | ours | 42.7 | [15.2, -27.6] | Sd173a6a3 | `--crop -12.5 -31.0 45.2 -19.5` |
| redesign | pro | 15.1 | [-0.1, -5.0] | Sd173a6a3 | `--crop -12.1 -8.2 10.4 -2.9` |
| redesign | pro | 11.7 | [17.6, -1.7] | Sd173a6a3 | `--crop 8.3 -6.1 26.2 2.3` |
| redesign | ours | 11.2 | [-20.0, -26.6] | Sd173a6a3 | `--crop -28.6 -29.5 -12.5 -22.9` |
| redesign | ours | 7.6 | [-40.4, 25.1] | S32b446a3 | `--crop -46.2 19.1 -38.7 30.6` |
| redesign | pro | 4.9 | [-45.9, 24.4] | S32b446a3 | `--crop -47.1 18.1 -44.6 30.6` |
| redesign | ours | 4.8 | [-34.2, -24.9] | Sd173a6a3 | `--crop -39.7 -26.4 -28.9 -22.9` |
| redesign | ours | 3.9 | [42.4, 20.0] | S9e70ec80 | `--crop 37.5 17.0 45.2 24.0` |
| redesign | pro | 3.7 | [-16.1, -1.7] | Sd173a6a3 | `--crop -21.2 -4.5 -11.6 1.1` |
| redesign (dust) | mixed | 56.8 | 245 pieces | | |
*redesign: and 6 more, 15.6 mm² total*

Every non-dust redesign row's nearest region is a BECKER or MARINE shape (`S7d68682c`, `Sd7b29a99`, `S9abe3aa7`, `S5be3de64`, `Sef4e6850`, `Sd173a6a3` ×6, `S32b446a3` ×2, `S9e70ec80`) — the pro's letter bodies (arch banner curvature, serif terminals, the drop-shadow offset) depart from what the flat artwork's ink shows, on both BECKER and MARINE.

### Shape rows — ours (dropped elements, sewn background)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| background | ours | 17.9 | [-35.1, 8.7] | Sd173a6a3 | `--crop -48.1 1.2 -24.7 12.2` |
| background | ours | 13.7 | [-38.9, 25.8] | S32b446a3 | `--crop -46.2 20.1 -33.5 31.3` |
| background | ours | 12.8 | [-29.4, 24.0] | S32b446a3 | `--crop -35.1 12.6 -27.4 31.3` |
| background | ours | 10.8 | [30.2, 24.7] | S64bc1dbe | `--crop 24.2 12.6 32.5 31.3` |
| background | ours | 9.3 | [43.3, 22.5] | S9e70ec80 | `--crop 37.9 18.1 46.3 25.4` |
| background | ours | 9.2 | [42.8, 17.6] | S9e70ec80 | `--crop 37.9 12.6 46.3 20.1` |
| background | ours | 8.7 | [-22.0, 29.0] | S79ea681a | `--crop -28.6 26.6 -15.8 31.3` |
| background | ours | 8.3 | [20.7, 28.1] | S64bc1dbe | `--crop 15.1 22.1 23.6 31.3` |
| background | ours | 8.0 | [36.6, 27.5] | S9e70ec80 | `--crop 31.4 16.9 45.0 31.3` |
| background | ours | 7.4 | [45.6, -2.0] | Sd173a6a3 | `--crop 41.9 -8.0 49.4 4.6` |
| background | ours | 5.0 | [4.6, 22.4] | Sa1103fec | `--crop 1.6 17.1 6.9 26.6` |
| background | ours | 4.4 | [1.6, 29.9] | Sa1103fec | `--crop -2.8 28.6 6.1 31.3` |
| background | ours | 4.1 | [-13.7, 29.9] | S79ea681a | `--crop -17.8 28.6 -9.5 31.3` |
| background | ours | 3.4 | [-5.6, 29.9] | Sa1103fec | `--crop -9.3 28.6 -1.8 31.3` |
| background | ours | 2.8 | [44.4, -20.9] | Sd173a6a3 | `--crop 41.9 -24.2 46.3 -17.4` |
| background (dust) | ours | 12.9 | 70 pieces | | |
| dropped | pro | 10.0 | [38.9, 13.0] | S9e70ec80 | `--crop 32.1 11.6 45.9 14.7` |
| dropped | pro | 9.4 | [-4.2, 13.1] | Sa1103fec | `--crop -9.9 11.6 3.3 15.9` |
| dropped | pro | 8.4 | [-20.1, 13.0] | S79ea681a | `--crop -25.6 11.6 -14.5 14.7` |
| dropped | pro | 8.3 | [10.2, 14.0] | S1a1d6bde | `--crop 6.3 11.6 14.3 19.0` |
| dropped | pro | 7.9 | [-35.5, 4.7] | S7d68682c | `--crop -45.1 0.5 -28.5 8.5` |
| dropped | pro | 5.8 | [18.3, 13.3] | S64bc1dbe | `--crop 14.5 11.6 22.9 17.1` |
| dropped | pro | 5.7 | [-42.6, 13.0] | S32b446a3 | `--crop -46.6 11.6 -38.1 14.6` |
| dropped | pro | 5.4 | [-16.4, -7.1] | Sef4e6850 | `--crop -21.1 -11.8 -13.8 -3.4` |
| dropped | pro | 4.8 | [20.5, -11.2] | S5be3de64 | `--crop 18.9 -14.6 23.6 -6.8` |
| dropped | pro | 4.6 | [-6.4, -8.3] | Sef4e6850 | `--crop -11.6 -10.7 -1.4 -6.6` |
| dropped | pro | 4.6 | [-36.7, -3.9] | S7d68682c | `--crop -38.1 -8.8 -32.1 2.5` |
| dropped | pro | 4.4 | [24.8, -13.1] | S5be3de64 | `--crop 22.5 -17.3 26.2 -9.0` |
| dropped | pro | 3.8 | [21.0, -20.3] | S5be3de64 | `--crop 18.9 -23.2 24.8 -16.6` |
| dropped | pro | 3.8 | [4.6, -15.4] | S9abe3aa7 | `--crop 3.2 -18.6 6.5 -11.4` |
| dropped | pro | 3.8 | [-45.5, 24.9] | S32b446a3 | `--crop -46.6 18.7 -44.1 30.5` |
| dropped (dust) | pro | 46.8 | 128 pieces | | |
*background: and 4 more, 9.6 mm² total*
*dropped: and 13 more, 39.3 mm² total*

## Becker hat large — 101.9 mm, hat_front

registration iou 0.650, scale 0.993, flip_y False, shift (0.0, 0.1) mm. Sheet: `docs/renders/pro-overlay-2026-09-11/becker_hat_large_overlay.png`.

### Flagged craft rows

`density` is reported here and never flagged: row/fill pitch is a ruled constant (`machine.FILL_ROW_MM` = 0.15 mm), not a target either side is graded against. `trims` counts distinct SOURCE PASSES that contributed thread to a region (a lift count), not the region's own chunk count — chunking a long pro pass at a region boundary can hand one region several chunks from a single lift.

| region | mm² | flags | tier ours / pro | width p50 | direction | pitch | layers | density (reported, not flagged) | trims (distinct passes, not lifts) | recipe |
|---|---:|---|---|---|---|---|---|---|---|---|
| S6040686f | 21.60 | tier,width,direction,pitch,layers | fill / satin (planned fill) | 0.24 / 3.38 | 92.80 / 11.10 | 0.12 / 0.17 | 5.93 / 3.93 | 19.93 / 15.44 | 1 / 2 | `S.R \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S92a90056 | 1052.50 | tier,width,pitch,layers | fill / satin (planned fill) | 0.25 / 2.38 | 95.10 / 21.30 | 0.16 / 0.12 | 5.57 / 3.35 | 18.91 / 15.33 | 24 / 4 | `S.R.R \| R \| R \| R \| R \| R \| …` / `O \| R \| R \| O \| R \| O \| …` |
| Sff923e8d | 185.90 | tier,width,pitch,layers | fill / satin (planned fill) | 0.23 / 5.14 | 86.00 / 157.70 | 0.12 / 0.20 | 5.98 / 1.71 | 17.42 / 9.90 | 1 / 1 | `S.R \| R \| R \| R \| R \| R \| …` / `Z \| R.S.R.Z.Z.R \| R.S.S.S.Z.R.S` |
| Sa42b7e5b | 167.80 | tier,width,pitch,layers | fill / satin (planned fill) | 0.33 / 5.10 | 25.40 / 115.90 | 0.11 / 0.15 | 6.05 / 1.54 | 17.75 / 8.60 | 1 / 1 | `S.R \| O \| O \| O \| O \| O \| …` / `Z.R.S.O.Z.Z \| R \| R \| S \| Z \| R \| …` |
| S1365beb6 | 216.80 | tier,width,layers | fill / satin (planned fill) | 0.24 / 5.20 | 76.50 / 173.00 | 0.12 / 0.15 | 5.85 / 1.64 | 16.95 / 9.08 | 1 / 1 | `S.R \| R \| O \| O \| O \| O \| …` / `R.Z.R.S.R.Z.R \| R \| S.Z.R.S.Z \| R \| R.S` |
| S88e95ddc | 211.80 | tier,width,layers | fill / satin (planned fill) | 0.21 / 5.20 | 78.50 / 172.40 | 0.13 / 0.15 | 5.93 / 3.44 | 17.31 / 9.83 | 2 / 1 | `S.R.R \| O \| O \| O \| O \| O \| …` / `R.Z.R \| S.Z \| R \| R \| S.Z.O.R.S.Z.R.S \| ` |
| S82f28c31 | 192.20 | tier,width,layers | fill / satin (planned fill) | 0.27 / 4.89 | 56.80 / 7.60 | 0.12 / 0.15 | 6.02 / 1.66 | 17.40 / 9.57 | 1 / 1 | `S.R \| R \| R \| O \| O \| O \| …` / `Z.R \| R.S.Z.Z.R \| O \| O \| R \| S.O.Z.R.S` |
| S9059f9a2 | 76.40 | tier,width,pitch | fill / satin (planned satin) | 1.39 / 5.20 | 159.10 / 161.00 | 0.14 / 0.20 | 2.14 / 1.56 | 5.90 / 9.94 | 1 / 1 | `S.O.S.O.Z.S` / `S.Z.R \| O \| S.S \| O` |
| Sb7019eaf | 365.80 | tier,layers | run / fill | — / — | 66.50 / 21.50 | — / 0.17 | 0.59 / 2.82 | 0.55 / 6.56 | 6 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| R \| O \| O \| O \| …` |
| Sd6d16b15 | 364.90 | tier,layers | run / fill | — / — | 102.60 / 21.70 | — / 0.17 | 0.55 / 2.78 | 0.44 / 6.60 | 6 / 2 | `O \| O \| O \| O \| O \| O \| …` / `R \| O \| O \| O \| O \| O \| …` |
| Sf6a92112 | 339.50 | tier,layers | run / fill | — / 1.90 | 170.40 / 23.90 | — / 0.16 | 0.70 / 2.90 | 0.67 / 7.01 | 11 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S030953b8 | 216.20 | tier,layers | run / fill | — / 2.00 | 82.70 / 23.40 | — / 0.16 | 0.65 / 2.98 | 0.57 / 7.21 | 7 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S780cc713 | 197.10 | tier,layers | run / fill | — / — | 1.80 / 22.40 | — / 0.16 | 0.76 / 2.76 | 0.67 / 6.22 | 5 / 2 | `O \| O \| O \| O \| O \| O \| …` / `R \| O \| O \| O \| O \| O \| …` |
| S3c0fe5df | 35.10 | pitch,layers | fill / fill (planned fill) | — / 4.40 | 138.80 / 13.10 | 0.12 / 0.18 | 5.85 / 3.91 | 18.99 / 16.17 | 1 / 2 | `S.R \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S77c113dd | 21.50 | layers | fill / fill (planned fill) | — / 3.50 | 6.00 / 12.30 | 0.15 / 0.18 | 5.87 / 4.40 | 19.70 / 17.16 | 1 / 2 | `S.R \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S5a7aaa27 | 9.00 | layers | run / none | — / — | — / — | — / — | 1.71 / 0.48 | 1.59 / 0.00 | 1 / 0 | `O \| O \| O \| O \| O \| O \| …` / `` |
| Sff923e8d-2 | 6.30 | layers | run / run | — / — | — / — | — / — | 2.67 / 0.67 | 2.44 / 0.45 | 1 / 1 | `O \| O \| O \| O \| O \| O \| …` / `O` |

17 flagged rows: 8 belong to "BECKER" (`S92a90056`, `Sf6a92112`, `S030953b8`, `S780cc713`, `Sb7019eaf`, `Sd6d16b15`, `S6040686f`, `S77c113dd`), 8 to "MARINE" (`S1365beb6`, `S88e95ddc`, `S82f28c31`, `Sff923e8d`, `Sa42b7e5b`, `S9059f9a2`, `S5a7aaa27`, `Sff923e8d-2`), and one (`S3c0fe5df`) sits inside the BECKER bounding box (a small fill-tier accent near the banner). Crops: `becker_hat_large_crop_becker_outline.png`, `becker_hat_large_crop_marine.png`.

### Shape rows — Kent's call (the pro departed from the artwork)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| redesign | pro | 263.8 | [-38.2, -9.6] | Sd6d16b15 | `--crop -47.3 -24.4 -29.0 8.1` |
| redesign | pro | 263.7 | [37.9, -10.1] | Sb7019eaf | `--crop 28.5 -26.8 48.3 8.1` |
| redesign | pro | 140.5 | [6.0, -18.4] | S030953b8 | `--crop -0.8 -30.4 15.6 -6.5` |
| redesign | pro | 121.1 | [22.0, -15.3] | S780cc713 | `--crop 15.5 -28.0 29.4 -1.6` |
| redesign | pro | 110.7 | [-22.9, -15.2] | Sf6a92112 | `--crop -28.5 -27.5 -15.8 -2.4` |
| redesign | pro | 92.6 | [-9.8, -17.3] | S92a90056 | `--crop -16.1 -30.4 -1.3 -7.9` |
| redesign | ours | 45.9 | [13.8, -29.7] | S92a90056 | `--crop -14.7 -32.9 46.2 -22.7` |
| redesign | pro | 17.1 | [14.4, 23.0] | S9059f9a2 | `--crop 12.2 12.4 17.4 32.4` |
| redesign | ours | 14.1 | [-21.6, -28.3] | S92a90056 | `--crop -30.5 -31.5 -13.7 -24.3` |
| redesign | pro | 13.0 | [0.3, -5.3] | S92a90056 | `--crop -11.9 -8.3 9.8 -3.2` |
| redesign | ours | 11.0 | [16.9, 23.1] | S1365beb6 | `--crop 15.0 13.1 18.5 31.5` |
| redesign | pro | 10.1 | [18.8, -1.8] | S92a90056 | `--crop 9.3 -5.8 27.4 2.2` |
| redesign | ours | 7.9 | [35.1, 25.5] | Sa42b7e5b | `--crop 33.8 18.0 36.7 32.5` |
| redesign | ours | 7.8 | [-9.0, 25.4] | S82f28c31 | `--crop -10.8 18.1 -2.5 32.5` |
| redesign | pro | 7.1 | [-0.2, 14.7] | S82f28c31 | `--crop -10.9 12.2 6.8 20.4` |
| redesign (dust) | mixed | 29.0 | 122 pieces | | |
*redesign: and 21 more, 81.4 mm² total*

Same pattern as LC large: every non-dust redesign row's nearest region is a BECKER or MARINE shape.

### Shape rows — ours (dropped elements, sewn background)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| background | ours | 18.0 | [45.2, 21.7] | Sa42b7e5b | `--crop 40.1 14.1 48.8 27.0` |
| background | ours | 16.8 | [-37.3, 9.2] | S92a90056 | `--crop -51.0 1.3 -26.5 12.9` |
| background | ours | 15.7 | [-20.7, 31.3] | Sff923e8d | `--crop -30.5 28.4 -10.6 33.3` |
| background | ours | 14.7 | [-41.7, 27.4] | S88e95ddc | `--crop -49.3 21.5 -36.0 33.3` |
| background | ours | 10.4 | [-31.9, 27.0] | S88e95ddc | `--crop -37.3 13.3 -29.4 33.3` |
| background | ours | 7.6 | [48.3, -2.0] | S92a90056 | `--crop 44.7 -8.4 52.3 4.7` |
| background | ours | 7.4 | [20.7, 31.0] | S1365beb6 | `--crop 15.3 24.2 24.7 33.3` |
| background | ours | 7.0 | [40.4, 31.9] | Sa42b7e5b | `--crop 33.8 30.5 47.5 33.3` |
| background | ours | 6.8 | [1.1, 31.7] | S82f28c31 | `--crop -3.8 29.1 6.3 33.3` |
| background | ours | 5.8 | [29.5, 31.7] | S1365beb6 | `--crop 24.7 28.6 34.1 33.3` |
| background | ours | 5.0 | [-6.3, 31.8] | S82f28c31 | `--crop -10.4 30.2 -2.1 33.3` |
| background | ours | 3.9 | [34.9, 8.8] | S92a90056 | `--crop 29.6 6.2 40.1 10.9` |
| background | ours | 3.7 | [4.6, 24.2] | S82f28c31 | `--crop 1.8 18.4 7.1 28.1` |
| background | ours | 3.7 | [16.4, 24.8] | S1365beb6 | `--crop 15.0 18.6 17.7 31.5` |
| background | ours | 2.8 | [46.5, -23.0] | S92a90056 | `--crop 44.2 -25.8 48.8 -19.6` |
| background (dust) | ours | 17.4 | 88 pieces | | |
| dropped | pro | 11.7 | [9.5, 15.1] | S9059f9a2 | `--crop 6.8 12.4 14.9 20.1` |
| dropped | pro | 8.6 | [41.0, 13.7] | Sa42b7e5b | `--crop 34.0 12.4 48.3 15.4` |
| dropped | pro | 7.9 | [-5.0, 13.8] | S82f28c31 | `--crop -10.8 12.4 3.1 17.0` |
| dropped | pro | 7.0 | [-21.4, 13.7] | Sff923e8d | `--crop -27.1 12.4 -15.8 15.2` |
| dropped | pro | 5.1 | [-48.6, 26.2] | S88e95ddc | `--crop -49.8 20.0 -47.2 32.4` |
| dropped | pro | 4.9 | [-45.7, 13.7] | S88e95ddc | `--crop -49.8 12.4 -40.8 15.4` |
| dropped | pro | 4.6 | [21.5, -12.1] | S780cc713 | `--crop 19.8 -15.5 24.7 -7.2` |
| dropped | pro | 4.2 | [4.6, -16.4] | S030953b8 | `--crop 3.2 -19.7 6.6 -12.1` |
| dropped | pro | 4.0 | [26.0, -14.1] | S780cc713 | `--crop 23.9 -18.4 27.4 -9.9` |
| dropped | pro | 4.0 | [-39.3, -4.1] | Sd6d16b15 | `--crop -40.8 -9.2 -34.6 2.6` |
| dropped | pro | 3.8 | [19.8, 13.7] | S1365beb6 | `--crop 16.2 12.4 24.0 15.2` |
| dropped | pro | 3.7 | [45.6, -16.7] | Sb7019eaf | `--crop 44.2 -20.4 47.1 -12.8` |
| dropped | pro | 3.6 | [-17.3, -7.7] | Sf6a92112 | `--crop -20.6 -12.2 -15.3 -4.5` |
| dropped | pro | 3.6 | [-35.8, 4.4] | Sd6d16b15 | `--crop -39.3 2.0 -32.1 6.7` |
| dropped | pro | 3.4 | [-34.3, 13.8] | S88e95ddc | `--crop -38.7 12.6 -30.4 15.3` |
| dropped (dust) | pro | 54.3 | 136 pieces | | |
*background: and 3 more, 7.4 mm² total*
*dropped: and 6 more, 16.7 mm² total*

## Hotel Fremont patch — 92.5 mm, patch

registration iou 0.983, scale 0.998, flip_y True, shift (-0.0, 0.4) mm. Sheet: `docs/renders/pro-overlay-2026-09-11/hotel_fremont_patch_overlay.png`.

### Flagged craft rows

`density` is reported here and never flagged: row/fill pitch is a ruled constant (`machine.FILL_ROW_MM` = 0.15 mm), not a target either side is graded against. `trims` counts distinct SOURCE PASSES that contributed thread to a region (a lift count), not the region's own chunk count — chunking a long pro pass at a region boundary can hand one region several chunks from a single lift.

| region | mm² | flags | tier ours / pro | width p50 | direction | pitch | layers | density (reported, not flagged) | trims (distinct passes, not lifts) | recipe |
|---|---:|---|---|---|---|---|---|---|---|---|
| Scf52eca9 | 25.10 | tier,width,direction | satin / run (planned satin) | 0.98 / 3.35 | 97.20 / 112.70 | — / — | 4.01 / 3.04 | 7.21 / 6.11 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Se0a7d935 | 14.70 | tier,width,direction | run / satin (planned satin) | 1.10 / 1.70 | 87.50 / 29.20 | — / — | 4.06 / 4.30 | 3.20 / 2.95 | 8 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S06ca1ceb | 12.20 | width,direction,layers | satin / satin (planned satin) | 0.98 / 3.19 | 91.10 / 52.60 | — / 0.18 | 3.89 / 2.81 | 7.15 / 20.93 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| Z \| O \| S` |
| S89bdb7e6 | 8.90 | width,direction,layers | satin / satin (planned satin) | 0.89 / 3.21 | 90.10 / 57.90 | — / 0.18 | 4.97 / 2.88 | 5.49 / 17.99 | 6 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| Z \| O \| O \| …` |
| Sa63d2957 | 8.10 | tier,width,direction | satin / run (planned satin) | 0.80 / 1.40 | 85.60 / 1.30 | — / — | 4.06 / 4.41 | 7.67 / 6.19 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S9c3989d0 | 7.50 | width,direction,layers | satin / satin (planned satin) | 1.26 / 1.70 | 83.70 / 39.40 | — / — | 3.32 / 4.76 | 3.94 / 6.45 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S42e426b8 | 3.10 | tier,direction,layers | satin / run (planned satin) | 0.80 / — | 90.10 / 11.50 | — / — | 1.85 / 4.56 | 1.07 / 1.66 | 1 / 1 | `O` / `O \| O` |
| S78e6cd01 | 2101.40 | width,direction | fill / fill (planned fill) | 0.58 / 1.40 | 90.70 / 15.30 | 0.13 / 0.14 | 2.81 / 3.55 | 9.41 / 12.84 | 180 / 15 | `O \| O \| O \| O \| O \| O \| …` / `O \| R \| R \| R \| O \| R \| …` |
| S234804ac | 36.60 | width,layers | satin / satin (planned satin) | 1.00 / 2.30 | 93.30 / 91.60 | — / 0.20 | 3.79 / 5.00 | 7.15 / 18.58 | 10 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S1800e700 | 36.40 | width,layers | satin / satin (planned satin) | 0.99 / 3.20 | 96.80 / 106.00 | — / 0.17 | 3.92 / 2.10 | 7.08 / 21.86 | 6 / 1 | `O \| O \| O \| O \| O \| O \| …` / `Z \| O \| O \| R \| S \| O \| …` |
| Sf93498a6 | 30.30 | tier,width | fill / run (planned fill) | 0.12 / 0.80 | 19.60 / 9.50 | 0.14 / 0.15 | 3.75 / 3.67 | 6.96 / 7.56 | 5 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S5e7178ba | 28.90 | width,direction | satin / satin (planned satin) | 1.06 / 3.10 | 88.80 / 64.40 | — / 0.18 | 3.72 / 2.84 | 6.77 / 20.19 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S3c536514 | 24.10 | width,direction | satin / satin (planned satin) | 0.70 / 1.40 | 86.50 / 11.40 | 0.60 / — | 4.16 / 3.92 | 8.43 / 4.35 | 5 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sf979bc42 | 23.00 | tier,direction | fill / satin (planned fill) | — / 1.50 | 101.10 / 17.80 | 0.15 / 0.14 | 2.71 / 3.13 | 9.81 / 11.86 | 2 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S10d3c3b0 | 22.90 | tier,direction | fill / satin (planned fill) | — / 1.49 | 92.60 / 13.60 | 0.11 / 0.15 | 2.72 / 3.34 | 9.95 / 12.44 | 2 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Scd77d305 | 19.70 | tier,direction | satin / run (planned satin) | 1.00 / — | 88.30 / 160.60 | — / — | 3.94 / 3.52 | 5.10 / 1.86 | 9 / 1 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sec0656d0 | 18.30 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 94.30 / 10.70 | 0.39 / — | 4.15 / 4.67 | 9.76 / 5.54 | 10 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S9c0c9dc7 | 17.40 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 98.00 / 177.10 | — / — | 3.94 / 4.60 | 8.44 / 7.34 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sf629d513 | 17.00 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 105.80 / 7.60 | — / — | 4.48 / 4.30 | 8.93 / 7.44 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sfacb88b7 | 16.50 | width,pitch | satin / satin (planned satin) | 0.80 / 1.40 | — / — | 0.60 / 0.35 | 4.00 / 4.81 | 9.62 / 9.62 | 5 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sbb420d8d | 16.00 | width,direction | satin / satin (planned satin) | 0.77 / 1.50 | 90.50 / 7.20 | — / — | 4.68 / 4.04 | 6.62 / 5.27 | 3 / 2 | `S \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Se137a45a | 15.90 | width,direction | satin / satin (planned satin) | 0.78 / 1.43 | 91.20 / 170.20 | — / — | 4.63 / 4.42 | 7.41 / 7.35 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Saef2bbe4 | 14.00 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 89.00 / 7.00 | — / — | 3.77 / 4.27 | 8.95 / 4.44 | 8 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sfdca3492 | 13.60 | width,direction | satin / satin (planned satin) | 1.00 / 3.19 | 84.40 / 44.70 | — / 0.18 | 3.51 / 2.75 | 6.84 / 21.25 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| Z \| R \| S \| O \| …` |
| Sf0dec763 | 12.50 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 95.90 / 8.20 | — / — | 4.00 / 3.99 | 10.19 / 5.70 | 5 / 2 | `R \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S7aadeb41 | 12.10 | tier,direction | satin / run (planned satin) | 0.82 / — | 103.10 / 139.50 | — / — | 3.83 / 4.23 | 2.41 / 1.69 | 6 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O` |
| S92cbbbfb | 11.30 | width,direction | satin / satin (planned satin) | 0.80 / 1.40 | 85.40 / 11.30 | — / — | 4.03 / 4.14 | 6.75 / 7.50 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sda4bc9a5 | 9.80 | direction,layers | satin / satin (planned satin) | 1.50 / 1.39 | 91.10 / 56.30 | — / — | 1.18 / 2.57 | 9.12 / 9.62 | 6 / 1 | `O \| O \| O \| L \| S.O \| S \| …` / `R \| R \| R \| S` |
| S9a48e915 | 9.40 | width,direction | satin / satin (planned satin) | 0.77 / 1.40 | 87.80 / 0.10 | — / — | 3.63 / 4.41 | 9.16 / 9.23 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| Sdf7cf574 | 8.90 | width,direction | satin / satin (planned satin) | 1.03 / 1.71 | 96.60 / 145.20 | — / — | 3.93 / 4.14 | 1.94 / 3.32 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| S \| O` |
| S67285fc4 | 8.80 | width,direction | satin / satin (planned satin) | 1.00 / 3.16 | 80.40 / 41.00 | — / — | 3.74 / 3.03 | 6.60 / 19.87 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| Z \| O \| …` |
| Sbe6c9978 | 8.50 | tier,direction | satin / run (planned satin) | 0.50 / — | 91.00 / 14.00 | — / — | 4.46 / 4.12 | 2.63 / 2.04 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| S \| O \| O \| …` |
| S3d684c8d | 6.30 | tier,layers | run / satin (planned fill) | — / 1.30 | 5.10 / 2.90 | — / — | 2.75 / 4.10 | 11.98 / 19.66 | 3 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S921a74a1 | 5.90 | direction,layers | run / none (planned satin) | — / — | 102.10 / 36.80 | — / — | 3.10 / 4.66 | 0.95 / 0.89 | 2 / 2 | `O \| O \| O \| O \| O` / `O \| O` |
| Sca9d5ea0 | 5.10 | direction,layers | run / none (planned satin) | 0.61 / — | 109.90 / 156.50 | — / — | 2.15 / 3.54 | 2.73 / 0.00 | 2 / 0 | `O \| S \| O \| O \| O \| O` / `` |
| S11c70290 | 4.80 | direction,layers | run / none (planned satin) | — / — | 105.30 / 25.10 | — / — | 2.72 / 4.46 | 1.81 / 0.73 | 2 / 1 | `O \| O \| O \| O \| O` / `O \| O` |
| Sc66cffd5 | 4.50 | tier,direction | satin / run (planned satin) | 0.56 / — | 91.70 / 26.80 | — / — | 4.20 / 4.28 | 0.77 / 2.31 | 2 / 2 | `O \| O` / `O \| O \| O` |
| Sac264dc6 | 3.50 | direction,layers | none / none (planned satin) | — / — | 90.00 / 47.80 | — / — | 1.98 / 4.27 | 0.00 / 0.00 | 0 / 0 | `` / `` |
| S3205355f | 2.80 | direction,layers | none / none (planned satin) | — / — | 95.60 / 16.50 | — / — | 1.36 / 4.13 | 0.00 / 0.00 | 0 / 0 | `` / `` |
| S30b4f308 | 2.40 | direction,layers | satin / none (planned satin) | 0.64 / — | 96.90 / 12.50 | — / — | 1.42 / 3.98 | 3.69 / 2.22 | 1 / 2 | `S \| S` / `O \| O` |
| Sf4300e5b | 86.60 | width | satin / satin (planned satin) | 0.90 / 2.10 | — / — | — / 0.23 | 3.94 / 4.43 | 7.16 / 9.69 | 24 / 3 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S942bc7ba | 36.90 | width | satin / satin (planned satin) | 1.00 / 2.30 | 94.10 / 94.30 | — / 0.15 | 4.28 / 5.09 | 7.91 / 18.31 | 9 / 4 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S1e81b932 | 11.30 | width | satin / satin (planned satin) | 0.76 / 1.30 | — / — | — / — | 4.08 / 4.07 | 10.22 / 9.40 | 5 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S37cb1978 | 11.00 | width | satin / satin (planned satin) | 1.01 / 1.71 | 95.40 / 170.10 | — / — | 4.26 / 4.09 | 3.23 / 3.25 | 7 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O \| O \| O \| …` |
| S863edab0 | 10.80 | direction | satin / none (planned satin) | 0.80 / — | 92.20 / 31.90 | — / — | 4.33 / 4.73 | 2.18 / 1.15 | 9 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O \| O` |
| Sa08e5e56 | 6.60 | direction | run / none (planned satin) | — / — | 124.10 / 146.00 | — / — | 3.12 / 3.92 | 1.41 / 0.96 | 4 / 2 | `O \| O \| O \| O \| O \| O \| …` / `O \| O \| O` |
| S666da526 | 4.60 | layers | run / none (planned satin) | — / — | — / — | — / — | 1.16 / 4.43 | 0.53 / 0.00 | 2 / 0 | `O \| O \| O` / `` |
| S3ddcec6c | 3.70 | layers | none / none (planned satin) | — / — | — / — | — / — | 2.38 / 4.32 | 0.00 / 0.00 | 0 / 0 | `` / `` |
| S9eb13c93 | 2.80 | layers | run / none (planned satin) | — / — | — / — | — / — | 2.73 / 4.34 | 0.48 / 0.00 | 1 / 0 | `O` / `` |
| Scc086035 | 2.70 | direction | satin / none (planned satin) | 0.82 / — | 81.60 / 11.50 | — / — | 2.56 / 2.73 | 3.56 / 2.73 | 2 / 1 | `O \| O \| O \| S` / `O \| O` |
| S161bdd7e | 2.10 | direction | none / run (planned run) | — / — | 82.00 / 11.50 | — / — | 3.87 / 3.97 | 0.00 / 3.27 | 0 / 2 | `` / `O \| O \| O` |
| S2666889d | 0.90 | layers | none / none (planned run) | — / — | — / — | — / — | 5.53 / 4.26 | 0.00 / 0.00 | 0 / 0 | `` / `` |
| Secf8fc7f | 0.90 | layers | none / none (planned run) | — / — | — / — | — / — | 7.17 / 3.18 | 0.00 / 0.00 | 0 / 0 | `` / `` |
| Sec4925f2 | 0.90 | layers | none / none (planned run) | — / — | — / — | — / — | 5.79 / 4.02 | 0.00 / 1.98 | 0 / 1 | `` / `O` |

54 flagged rows (corrected count — an earlier draft of this doc miscounted this table at 52). `S78e6cd01` is the patch's own background tatami (fill/fill, no tier mismatch — flagged only on width/direction). Four named elements identified from the artwork and the region bounds (`ours_regions.json`'s `bounds` field, in the same registered mm frame `--crop` takes):

- **THE** — `S666da526`, `S3ddcec6c`, `S42e426b8` (the three letters). Crop: `hotel_fremont_patch_crop_the.png`.
- **EST 1895** — `Sf93498a6` (the Wisconsin state silhouette), `Sdf7cf574` ("ES" of EST), `Scc086035` (a state-outline notch), `Sec4925f2`, `S161bdd7e` (digit fragments of "1895"). Crop: `hotel_fremont_patch_crop_est_1895.png`.
- **the rope** — representative top diagonal chain: `S7aadeb41`, `S37cb1978`, `S3205355f`, `S863edab0`, `S9eb13c93`, `S11c70290`, `Secf8fc7f`, `S921a74a1` (the twisted-cord border also recurs, same defect, at the other three diagonal edges of the patch — `S9c3989d0`, `Sa08e5e56`, `Sbe6c9978`, `S30b4f308`, `Sc66cffd5`, `Sca9d5ea0`, `Scf52eca9`, `S67285fc4` are the bottom-edge instances, not separately cropped). Crop: `hotel_fremont_patch_crop_rope.png`.
- **the tagline** ("EAT | STAY | PLAY") — `S5e7178ba` (EAT), `Se0a7d935` (STAY), `Scd77d305` (PLAY), `Sac264dc6`, `S2666889d` (the pipe dividers). Crop: `hotel_fremont_patch_crop_tagline.png`.

That accounts for 29 rows (plus `S78e6cd01`, already covered above) and four more (`S234804ac`, `S1800e700`, `S942bc7ba`, `Sf4300e5b`) are the plain black rule lines flanking "THE" and under "HOTEL FREMONT" — not one of Kent's previously-reviewed named elements, no separate crop made. **The remaining 20 rows are NOT covered by any crop above** — an earlier draft of this doc wrongly implied the four rule lines were the only leftover. Sixteen of the 20 are "HOTEL FREMONT"'s own title-letter satin columns (`Sbb420d8d`, `Se137a45a`, `Sec0656d0`, `S9c0c9dc7`, `Sf629d513`, `Sfacb88b7`, `Saef2bbe4`, `Sf0dec763`, `S1e81b932`, `S92cbbbfb`, `S9a48e915`, `Sa63d2957`, `S3c536514`, `Sf979bc42`, `S10d3c3b0`, `S3d684c8d`) — see the "HOTEL FREMONT title letters" observation under expectation 4 below. The other four (`S06ca1ceb`, `S89bdb7e6`, `Sfdca3492`, `Sda4bc9a5`) are additional small satin pieces near the EST 1895/rope bands (width ours 0.89-1.5 mm / pro 1.39-3.21 mm) that were not folded into either crop and were not separately classified.

### Shape rows — Kent's call (the pro departed from the artwork)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| redesign | pro | 24.0 | [5.3, 19.0] | S863edab0 | `--crop -33.3 8.6 33.2 27.2` |
| redesign | pro | 21.1 | [-1.8, -18.3] | S78e6cd01 | `--crop -38.5 -26.2 33.2 -7.6` |
| redesign (dust) | mixed | 67.6 | 1799 pieces | | |

Two non-dust redesign rows only, both large (near-full-width) — the top one spans the EST/1895/rope band, the bottom one the tagline band. The 1,799-piece dust row is the biggest of any design in this run: the patch's twisted-rope texture and small serif digits fragment heavily under this comparison, most of it registration noise rather than a craft defect (see "registration caveats" in the memory file).

### Shape rows — ours (dropped elements, sewn background)

| tag | sewn_by | mm² | centre | nearest region | crop |
|---|---|---:|---|---|---|
| dropped | pro | 4.2 | [-4.3, -12.9] | S78e6cd01 | `--crop -5.5 -19.2 -3.0 -6.4` |
| dropped | pro | 3.1 | [37.1, -2.1] | S78e6cd01 | `--crop 36.0 -7.0 38.4 2.9` |
| dropped | pro | 2.5 | [-15.0, -10.7] | S78e6cd01 | `--crop -16.1 -15.2 -13.7 -6.4` |
| dropped (dust) | pro | 528.0 | 3291 pieces | | |
| background (dust) | ours | 14.3 | 442 pieces | | |

No non-dust background row at all — unlike both Becker designs, our engine sews essentially nothing outside the artwork's ink on this patch. The 3,291-piece `dropped` dust row (528.0 mm²) is registration noise from the fine rope/lettering texture, the same effect as the redesign dust row above.

## Against the record

Six expectations from the spec, checked against this run's own catalogues:

1. **MARINE tier (our tatami against the pro's 5-7 mm columns) — CONFIRMED.** Both designs' MARINE flagged rows show `tier ours / pro` = `fill / satin` with `width p50` ours 0.19-0.41 mm against pro 4.67-5.20 mm — e.g. `becker_lc_large` row `S64bc1dbe` (0.28 / 4.90) and `becker_hat_large` row `S1365beb6` (0.24 / 5.20). The pro's measured column width (4.67-5.20 mm p50) runs slightly under the spec's stated 5-7 mm, but the core claim — ours is fine tatami, the pro is a wide satin column — holds on every MARINE row in both designs.
2. **Satin share of penetrations (measured 2.2% against 44.3% in MASTER_SCOPE) — CONFIRMED (qualitatively; this run does not recompute the percentage).** `diff.py` reports per-region tier, not a corpus-wide penetration share, so the 2.2%/44.3% figures themselves are not reproduced here. But the same underlying gap shows up on every large BECKER/MARINE region in both designs as a `tier` flag: `fill / satin` (ours never reaches satin on the arch or the letter bodies) or `run / fill` (the drop-shadow layer, which the pro sews as a filled shape, comes out of our engine as bare running stitches). Fifteen of fifteen flagged rows on `becker_lc_large` and fifteen of seventeen on `becker_hat_large` carry a `tier` mismatch in this direction.
3. **One fill angle (the pro holds about 20 degrees at every size) — CONFIRMED.** Pro `direction` on the drop-shadow/fill-tier rows clusters tightly: `becker_lc_large` — `Sd173a6a3` 22.2°, `S9abe3aa7` 22.3°, `Sd7b29a99` 20.1°, `S5be3de64` 21.6°, `S7d68682c` 22.7°, `Sef4e6850` 23.7°; `becker_hat_large` — `S030953b8` 23.4°, `Sb7019eaf` 21.5°, `Sd6d16b15` 21.7°, `Sf6a92112` 23.9°, `S780cc713` 22.4°. Eleven of eleven measurable fill-tier pro rows land within 20-24° across both designs and both sizes.
4. **Fremont lettering column width (the pro 0.82-0.90 mm where we sew bean runs) — NOT SETTLED.**

   **Where the 0.82-0.90 mm figure comes from, and what kind of number it is.** `docs/kent-review-2026-09-03.md:143` reads *"The gold lettering block (1,090 st) has a median stitch of 0.82 mm inside the tagline band and THE's black block 0.90 mm — satin columns of roughly 0.8-0.9 mm."* This run's own `pro_blocks.json` for `hotel_fremont_patch` reproduces the primary figure exactly: block 8, rgb `[178, 118, 36]` (gold), **1,090 stitches, `len_p50` 0.82 mm, `row_spacing_mm` 0.4**. That confirms the citation, but `len_p50` is a **median point-to-point stitch length**, not a `satin_columns.measure` column width (the apex-to-chord offset this catalogue's `width p50` reports). The two are related, not interchangeable: on a satin column, consecutive needle points alternate rails, so a stitch length is approximately `sqrt(width² + pitch²)` — the record's figure is a width PROXY that over-reads by the pitch term. Backing the pitch out of block 8's own 0.4 mm row spacing: `sqrt(0.82² - 0.4²) ≈ 0.72 mm`, and the same correction on THE's quoted 0.90 mm gives `sqrt(0.90² - 0.4²) ≈ 0.81 mm`. So the record's "roughly 0.8-0.9 mm columns" reads as a true column width of roughly **0.72-0.81 mm** once the pitch term is removed — a reasonable proxy, not a category error, but not the same quantity this catalogue's `width p50` measures either, and the two must not be quoted interchangeably (see the new DOCTRINE entry).

   **What the loop measures on the actual tagline and THE regions** — the elements the record's sentence describes — is mostly nothing: of the 8 flagged/candidate regions in those two crops, `width p50` is unmeasurable (`None`) on 5 of them.

   | region | element | ours tier / width p50 | pro tier / width p50 |
   |---|---|---|---|
   | S5e7178ba | EAT | satin / 1.06 | satin / 3.10 |
   | Se0a7d935 | STAY | run / 1.10 | satin / 1.70 |
   | Scd77d305 | PLAY | satin / 1.00 | run / — |
   | Sac264dc6 | pipe (EAT\|STAY) | none / — | none / — |
   | S2666889d | pipe/dot | none / — | none / — |
   | S666da526 | THE (T) | run / — | none / — |
   | S3ddcec6c | THE (H/E) | none / — | none / — |
   | S42e426b8 | THE (T) | satin / 0.80 | run / — |

   Pro-side width is measurable on only 2 of 8 (3.10 mm on EAT, 1.70 mm on STAY) — neither in the 0.72-0.81 mm corrected-proxy range, but the sample is too sparse and too scattered (a 1.4x spread between the two measurable rows alone) to say the record's figure is wrong for this element; the instrument simply cannot see most of what the record describes.

   **The "HOTEL FREMONT" title letters are a different element, reported here as its own observation, not as a check on the record.** Sixteen flagged regions belong to "HOTEL FREMONT"'s own lettering band (`Sbb420d8d`, `Se137a45a`, `Sec0656d0`, `S9c0c9dc7`, `Sf629d513`, `Sfacb88b7`, `Saef2bbe4`, `Sf0dec763`, `S1e81b932`, `S92cbbbfb`, `S9a48e915`, `Sa63d2957`, `S3c536514`, `Sf979bc42`, `S10d3c3b0`, `S3d684c8d`) — none of them the tagline or THE. `width p50` there runs pro 1.30-1.50 mm / ours 0.70-0.80 mm (e.g. `Sec0656d0` 0.80/1.40, `S9c0c9dc7` 0.80/1.40, `Sbb420d8d` 0.77/1.50), both sides tiered `satin` on 12 of the 16 (the other four: `Sa63d2957` pro is `run`; `Sf979bc42` and `S10d3c3b0` ours is `fill`; `S3d684c8d` ours is `run`). This is a real, measurable gap, but it is not the one the record's sentence makes a claim about.

   **Verdict: not settled.** The record's figure describes the tagline and THE, this loop reads those specific regions as mostly unmeasurable, and the one element this loop DID measure well (HOTEL FREMONT's title letters) is not the element the record describes. Neither confirms nor refutes it — checking this expectation properly needs either a `satin_columns` reading of THE and the tagline directly (not `len_p50`), or a design where those elements sew wide enough to measure.
5. **Trims (Becker 29 against the pro's 12) — CONFIRMED (magnitude; exact counts differ).** `becker_lc_large`'s Design table reads 30 ours / 10 pro; `becker_hat_large` reads 34 ours / 10 pro. Both land close to the spec's stated 29/12 (within one trim on the pro side, one to four on ours) and preserve the roughly 3x ratio the spec describes — but neither design reproduces the exact 29/12 pair, so the specific numbers should be read as approximate, not as a fixed target.
6. **Becker letter bodies as a redesign row — CONFIRMED.** Every non-dust `redesign` row in both Becker designs' "Shape rows — Kent's call" table has a BECKER or MARINE shape as its `nearest_region` (`Sd173a6a3`, `Sd7b29a99`, `S9abe3aa7`, `S5be3de64`, `Sef4e6850`, `S7d68682c`, `S32b446a3`, `S9e70ec80` on `becker_lc_large`; the equivalent shadow/letter shapes on `becker_hat_large`) — the pro's arch-banner curvature and letter terminals depart from the flat artwork's ink on both designs, landing squarely in the tag the loop reserves for Kent's own call rather than a defect.

## Commands

```bash
cd digitizer
PRO_PARITY_ROOT="C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/scratch_kent/Embroidery Files" \
PRO_PARITY_OUT="<out>" \
.venv/Scripts/python tools/pro_parity/prep_both.py becker_lc_large becker_hat_large hotel_fremont_patch

.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_lc_large" --by-thread
.venv/Scripts/python tools/pro_parity/diff.py --dir "<out>/real/becker_lc_large"
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_hat_large" --by-thread
.venv/Scripts/python tools/pro_parity/diff.py --dir "<out>/real/becker_hat_large"
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/hotel_fremont_patch" --by-thread
.venv/Scripts/python tools/pro_parity/diff.py --dir "<out>/real/hotel_fremont_patch"

# named-element crops (bounds from each design's ours_regions.json "bounds" field, +1mm pad)
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_lc_large" --crop -48.9 -30.8 48.6 11.2 --crop-name becker_outline
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_lc_large" --crop -47.4 13.0 45.4 30.5 --crop-name marine
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_hat_large" --crop -52.0 -32.6 51.8 12.1 --crop-name becker_outline
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/becker_hat_large" --crop -50.5 13.9 48.2 32.6 --crop-name marine
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/hotel_fremont_patch" --crop -5.9 -9.7 6.0 -4.6 --crop-name the
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/hotel_fremont_patch" --crop -20.0 -19.0 8.3 -10.0 --crop-name est_1895
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/hotel_fremont_patch" --crop -29.5 -23.0 29.6 -7.8 --crop-name rope
.venv/Scripts/python tools/pro_parity/overlay.py --dir "<out>/real/hotel_fremont_patch" --crop -25.8 12.3 18.9 24.8 --crop-name tagline
```

`PYTHONUTF8=1` avoided a `UnicodeEncodeError` from `diff.py`'s stdout arrow character on this Windows console (cp1252); both catalogue files write correctly either way since the crash happens after `catalogue.md`/`diff.json` are already written.

**Render budget:** `docs/renders/pro-overlay-2026-09-11/` is 6.5 MB. The flicker pairs (`flicker_pro*`/`flicker_ours*`, 5 files per crop plus 2 per design) were dropped entirely to stay under the ~10 MB target — only `overlay`, `pro_only`, `ours_only`, `by_thread/*`, and the overlay variant of each named-element crop are kept. The eight named-element crops were additionally downsized (max width 1400 px, from their native `CROP_PPM=36` render) to keep the total well under budget; none needed downsizing below native size where the native crop was already under 1400 px wide (Fremont's `the` crop, 428x205, kept at full resolution).
