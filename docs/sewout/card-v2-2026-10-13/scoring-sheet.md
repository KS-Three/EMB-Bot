# Scoring sheet, sew-out card v2

One table per sew-out, one row per piece. **Thread breaks** come from the
machine counter. **Y/N** columns: write Y or N; a cell that does not apply is
marked `n/a`. Where a cell asks for several values (`B:_ O:_ ...`), fill in
each. The free note is for anything else, including the photo
(`macro: Y/N, arm's length: Y/N`).

Read each pair OFF then ON (OFF is 1 tooth, ON is 2 teeth; block G arms are
1, 2, 3 teeth). **Score OFF and ON the same way**, and score the pair together
before you move on.

- **Counters open (Y/N), per letter:** the bare cloth inside the letter shows
  as a hole (Y) or is filled in with thread (N).
- **Bare line along a counter (Y/N):** a line of cloth shows between a counter
  and the column that borders it (the column did not cover its own ink).
- **Legible at arm's length (Y/N):** you can read the word without being told.
- **Fabric visible in the seam (Y/N), per gap:** bare cloth shows between the
  bar and the fill at that gap, at arm's length and under a loupe.
- **Seam ridge or pucker (Y/N):** the bar's edge sits on a hard ridge, or the
  cloth puckers along the seam (the tuck-under is too much).
- **Edge reads closer to the drawn outline (OFF / ON / same):** compare the
  two H words against the picture in `card_v2_*wt.png`: which letter edge sits
  closer to the drawn one?
- **Letter looks thinner (Y/N):** the stroke reads lighter than its partner.

Candidate numbers under test; none of them is settled until this sheet is
filled in.

| Candidate | Value | What settles it |
|---|---|---|
| `SMALL_PRINT_COUNTER_MIN_WIDTHS` | 1.0 laid widths: 0.40 mm at 40 wt, ~0.32 mm at 60 wt | block F: counters open ON where OFF shut, at 3 and 4 mm |
| counter hold-off | half a laid width: 0.20 mm at 40 wt, 0.16 mm at 60 wt | block F: no bare line along a counter ON, counter stays its drawn size |
| `forbid_gap_mm` | 0.4 or 0.8 (or none) | block G: which arm shows no fabric in the 0.3 / 0.6 mm seams, with no ridge |
| Column reach | the Column lane's 0.06-0.07 mm shortfall | block H: does ON look thinner, or its edge farther from the drawn one? |

## Sew-out 1: `card_v2_40wt.dst`, 40 wt, needle 75/11, pique + cutaway + topping

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light): ______________________

| Piece | Thread breaks (count) | Counters open (Y/N), per letter | Bare line along a counter (Y/N) | Legible at arm's length (Y/N) | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Edge closer to the drawn outline (OFF / ON / same) | Letter thinner (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|---|
| **F** 4 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 4 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **G** arm 1, OFF | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 2, 0.4 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 3, 0.8 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **H** Column lane OFF | ___ | n/a | n/a | _ | n/a | n/a | _ | _ | |
| **H** Column lane ON | ___ | n/a | n/a | _ | n/a | n/a | (same cell as above) | _ | |

Arm's length read of the whole hoop: ______________________________________

## Sew-out 2: `card_v2_60wt.dst`, 60 wt, needle 65/9 or v1's pick, pique + cutaway + topping

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light): ______________________

| Piece | Thread breaks (count) | Counters open (Y/N), per letter | Bare line along a counter (Y/N) | Legible at arm's length (Y/N) | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Edge closer to the drawn outline (OFF / ON / same) | Letter thinner (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|---|
| **F** 4 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 4 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **G** arm 1, OFF | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 2, 0.4 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 3, 0.8 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **H** Column lane OFF | ___ | n/a | n/a | _ | n/a | n/a | _ | _ | |
| **H** Column lane ON | ___ | n/a | n/a | _ | n/a | n/a | (same cell as above) | _ | |

Arm's length read of the whole hoop: ______________________________________

## Sew-out 3: `card_v2_40wt.dst`, 40 wt, needle 75/11, twill + tearaway

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light): ______________________

| Piece | Thread breaks (count) | Counters open (Y/N), per letter | Bare line along a counter (Y/N) | Legible at arm's length (Y/N) | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Edge closer to the drawn outline (OFF / ON / same) | Letter thinner (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|---|
| **F** 4 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 4 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **G** arm 1, OFF | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 2, 0.4 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 3, 0.8 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **H** Column lane OFF | ___ | n/a | n/a | _ | n/a | n/a | _ | _ | |
| **H** Column lane ON | ___ | n/a | n/a | _ | n/a | n/a | (same cell as above) | _ | |

Arm's length read of the whole hoop: ______________________________________

## Sew-out 4: `card_v2_60wt.dst`, 60 wt, needle 65/9 or v1's pick, twill + tearaway

Date: ________  Machine: ____________  Speed (spm): ______  Thread (dark / light): ______________________

| Piece | Thread breaks (count) | Counters open (Y/N), per letter | Bare line along a counter (Y/N) | Legible at arm's length (Y/N) | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Edge closer to the drawn outline (OFF / ON / same) | Letter thinner (Y/N) | Free note |
|---|---|---|---|---|---|---|---|---|---|
| **F** 4 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 4 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm OFF | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **F** 3 mm ON | ___ | B:_ O:_ A:_ R:_ D:_ | _ | _ | n/a | n/a | n/a | n/a | |
| **G** arm 1, OFF | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 2, 0.4 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **G** arm 3, 0.8 | ___ | n/a | n/a | n/a | 0.3:_ 0.6:_ 1.0:_ | _ | n/a | n/a | |
| **H** Column lane OFF | ___ | n/a | n/a | _ | n/a | n/a | _ | _ | |
| **H** Column lane ON | ___ | n/a | n/a | _ | n/a | n/a | (same cell as above) | _ | |

Arm's length read of the whole hoop: ______________________________________
