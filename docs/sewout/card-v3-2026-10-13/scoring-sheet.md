# Readout sheet, sew-out card v3.1

One table per block, one row per arm, for the one sew-out
(`card_v3_1_40wt.dst`, 40 wt, needle 75/11). **Thread breaks** come from the
machine counter. **Y/N** cells: write Y or N. Read the arms of a block together
(1 tooth first), at arm's length first and then under a loupe, and score every
arm the same way.

Date: ________  Machine: ____________  Speed (spm): ______  Fabric / backing: ______________________
Thread (dark / light): ______________________  Needle: 75/11  Fresh needle: Y/N

## F3: 2.2 mm cap APA (does the counter stay open?)

| Arm | Thread breaks | Counter open (Y/N): A1 / P / A2 | Bare line along a counter (Y/N) | Reads APA at arm's length (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today | ___ | A1:_ P:_ A2:_ | _ | _ | |
| 2 teeth: `small_print_floor` ON | ___ | A1:_ P:_ A2:_ | _ | _ | |
| 3 teeth: `small_glyph_keep` ON | ___ | A1:_ P:_ A2:_ | _ | _ | |

## T: Fremont THE at 81 mm (is it a blob?)

| Arm | Thread breaks | Reads THE at arm's length (Y/N) | Letters distinct, T H E (Y/N each) | Blob: strokes fused or fat (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today | ___ | _ | T:_ H:_ E:_ | _ | |
| 2 teeth: `lettering_words` + `lettering_word_tiers` | ___ | _ | T:_ H:_ E:_ | _ | |

(No skeleton arm: the skeleton tier leaves THE as it is.)

## N: Fremont 1895 at 81 mm (does it read 1895?)

| Arm | Thread breaks | Reads 1895 at arm's length (Y/N) | Each digit reads (Y/N): 1 / 8 / 9 / 5 | 8 and 9 counters open (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: `small_glyph_keep` OFF | ___ | _ | 1:_ 8:_ 9:_ 5:_ | 8:_ 9:_ | |
| 2 teeth: `small_glyph_keep` ON | ___ | _ | 1:_ 8:_ 9:_ 5:_ | 8:_ 9:_ | |

## G: forbid gap (card v2's block G)

| Arm | Thread breaks | Fabric visible in the seam (Y/N), per gap | Seam ridge or pucker (Y/N) | Free note |
|---|---|---|---|---|
| 1 tooth: OFF | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |
| 2 teeth: `forbid_gap_mm` 0.4 | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |
| 3 teeth: `forbid_gap_mm` 0.8 | ___ | 0.3:_ 0.6:_ 1.0:_ | _ | |

## X: Fremont E, M->O, N at 81 mm (verification: do the ends come out clean?)

Letters, left to right in the arm: **E** (HOTEL's), then **M, O, N** (FREMONT's).

| Arm | Thread breaks | E: upper arm ends square, no slanted stub (Y/N) | M: vertex stands on its foot, no wedge (Y/N) | M to O: a loop or bar across the notch (Y/N) | N: diagonal ends on the baseline, no ear (Y/N) | Free note |
|---|---|---|---|---|---|---|
| 1 tooth: both flags OFF | ___ | _ | _ | _ | _ | |
| 2 teeth: `lettering_columns_square_ends` + `lettering_columns_inside_connectors` ON | ___ | _ | _ | _ | _ | |

## S: Fremont tagline EAT | STAY | PLAY at 81 mm (does one run down the middle read?)

| Arm | Thread breaks | Thread shred / loop / needle heat (Y/N) | Reads EAT STAY PLAY at arm's length (Y/N) | Weight: letters look one thread, not fat (Y/N) | A counters read as holes (Y/N): EAT / STAY / PLAY | A crossbar reads (Y/N) | Free note |
|---|---|---|---|---|---|---|---|
| 1 tooth: today (skeleton OFF) | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |
| 2 teeth: skeleton, floor 1.0 mm | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |
| 3 teeth: skeleton, floor 0.73 mm | ___ | _ | _ | _ | E:_ S:_ P:_ | _ | |

## B: Becker MARINE at 80 mm (verification: the N's notch)

| Arm | Thread breaks | A thread or stitch across the notch at the top of the N (Y/N) | N reads cleaner than the other arm (Y/N) | Reads MARINE at arm's length (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: both flags OFF | ___ | _ | _ | _ | |
| 2 teeth: both flags ON | ___ | _ | _ | _ | |

## E2: enthusiast ENTERPRISES INC at 80 mm (does the R of PRISES read as an A?)

| Arm | Thread breaks | Reads ENTERPRISES INC at arm's length (Y/N) | R of PRISES reads R / A / unclear | Thread shred / loop / needle heat (Y/N) | Free note |
|---|---|---|---|---|---|
| 1 tooth: today (skeleton OFF) | ___ | _ | _ | _ | |
| 2 teeth: skeleton, floor 0.73 mm | ___ | _ | _ | _ | |

Arm's length read of the whole card: ______________________________________

Candidate numbers under test; none of them is settled until this sheet is
filled in.

| Candidate | Value | What settles it |
|---|---|---|
| `small_print_floor` at 2.2 mm cap | ON keeps an A's triangle open | block F3: counter open in arm 2 and not in arm 1 |
| counter minimum / hold-off | 1.0 laid width (0.40 mm at 40 wt), half-width hold-off (0.20 mm) | block F3: arm 2's A counters (about 0.5 mm) open with no bare line |
| `small_glyph_keep` flip | ON | blocks F3 (arm 3) and N: counters open and digits read |
| `lettering_words` + `lettering_word_tiers` flip | ON | block T: THE reads in arm 2 and not in arm 1 |
| `forbid_gap_mm` | 0.4 or 0.8 (or none) | block G: which arm shows no fabric in the 0.3 / 0.6 mm seams, with no ridge |
| `small_lettering_skeleton` flip | ON | blocks S and E2: arm 2 or 3 reads better than arm 1 with no breaks, and the A crossbars and the enthusiast R survive |
| `small_lettering_skeleton_floor_mm` | None (1.0 mm) or 0.73 mm | block S: arm 3 reads better than arm 2, and its 0.73 mm stitches hold (no shred or loop); this is the question behind `MIN_STITCH_MM` = 1.0 |
| `lettering_columns_square_ends` + `lettering_columns_inside_connectors` flips | ON | blocks X and B: ON ends clean, no loop at the M, no travel across the N's notch; none is a gate |
