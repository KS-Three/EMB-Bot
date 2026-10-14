# Readout sheet, sew-out card v3

One table per block, one row per arm, for the one sew-out
(`card_v3_40wt.dst`, 40 wt, needle 75/11). **Thread breaks** come from the
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
