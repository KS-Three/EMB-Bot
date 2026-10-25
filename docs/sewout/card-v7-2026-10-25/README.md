# Sew-out card v7 (2026-10-25): the two flags still waiting on fabric

**Sew this one beside the pro's Fremont patch.** Kent ruled 2026-10-22 that
stitch layout is judged in the preview; only what fabric does to thread needs
a sew-out. Two flags on main are that kind. Every number is a candidate until
you sew it (ROADMAP gate 1). Print `card_v7_40wt_worksheet.png` (or `.pdf`) and
take it to the machine.

**What to sew:** `card_v7_40wt.dst`, **one dark cone**, **40 wt**, 75/11, a
**flat 4 x 4 in hoop** (the design is 88.4 x 93.2 mm: too tall for a cap frame's
~57 mm), the structured twill you sewed card v4 on, with your Fremont backing. 12,512 stitches, 59 trims, about 19 minutes
(stitch count at 650 spm, not a measurement). Trims on.

## The arms

Teeth above each piece count its arm. Each arm pins BOTH flags (an unpinned
OFF would follow a later default flip):

| Teeth | Arm | `pull_comp_by_stroke` | `pro_measured_values` |
|---|---|---|---|
| 1 | (a) both off | off | off |
| 2 | (b) pull by stroke | **ON** | off |
| 3 | (c) pro values | off | **ON**: fill stitch 3.49 (3.0), satin 0.37 (0.40), bean 0.95 (0.73) |
| 4 | (d) both on | **ON** | **ON** |

Every arm also carries `BASE`, the flips Kent has ruled whose flags are on
main but whose flip PRs (#1057, #1070) had not merged when this was cut, so
row (a) is what ships: `fill_turn_slant` True, `trim_bury_under_later` True, `small_solids_satin` True, `compact_solids_satin` True, `satin_underlay_short_columns` True, `fill_underlay_cross` True, `small_text_cap_mm` 4.0, `small_text_cap_max_width_scale` 1.05, `small_text_cap_min_stroke_mm` 0.85, `small_text_cap_letter_gap_mm` 0.25, `small_text_cap_bold_scale` 1.45, `lettering_columns_small_bold` True, `border_by_size` True, `enclosed_alpha_hole_parts` True, `lettering_columns_corner_fold` True, `small_text_cap_reach_edges` True. `border_from_outline` is ruled too but was
not a flag on main (#1065). `tie_in_off` (ruled; an OFF flag on main since
#1042, merged after the cut) does not reach the card: the card strips every
piece's locks and lays its own, as every card tool does.

## The three blocks

- **F**: Hotel Fremont at **92.5 mm, the pro's size**, Hat: the HOTEL FREMONT
  band (THE, HOTEL FREMONT, the two bars) and the crest (Wisconsin's fill, EST,
  1895). **F sews (a) and (c) only**: Fremont's strokes are ~0.85 mm, where
  the pull fit returns the hat's own 0.4, so on these pieces (b) is (a) and (d)
  is (c) byte for byte (the cut's md5s: (b) = (a), (d) = (c)). Across the whole Fremont
  design the flag moves two letters of the tagline (not on the card) by at
  most 0.02 mm, and stitch and trim counts are unchanged: (a) 17,509 / 32, (b) 17,509 / 32, (c) 16,651 / 33, (d) 16,651 / 33. Hold each F
  row against the pro's patch.
- **P**: a fill plate through the real pipeline, Hat: a field with 18 mm rows
  (the pro's 3.49 was read on rows over 10 mm), a 7.5 mm disc, and a 5.5 mm
  disc. Under BASE's `border_by_size` the field and the big disc get a satin
  ring; the small disc keeps the bean edge cap, the only one on the card.
  Fremont's crop has neither a long-row fill nor a cap. Sews (a) and (c):
  no column, so (b) and (d) are the same ((b) = (a), (d) = (c)).
- **M**: Becker MARINE at **76.5 mm, the pro's size**, Hat: wide satin strokes,
  where the pull flag acts: the I and the N, all four arms side by side.
  **Here the pull flag changes construction, not just width:** OFF plans the
  columns as SPLIT satin (two ~2.3 mm stitches per cross, a line of needle
  holes down the middle), ON as plain satin, as the pro sews them (his DST,
  same reader, last row of the table).

| Piece | Teeth | Arm | Stitches | Planned satin: cross / stitch / rail step (mm), split | Planned fill stitch (p75) / bean cap stitch (mm) | Whole design, stitches / trims |
|---|---|---|---|---|---|---|
| F | 1 | (a) both off | 3,745 | 1.42 / 1.42 / 0.4, 0.0% | 1.89 / - | 17,509 / 32 |
| F | 3 | (c) pro values | 3,900 | 1.42 / 1.42 / 0.37, 0.0% | 2.32 / - | 16,651 / 33 |
| P | 1 | (a) both off | 1,556 | - | 3.0 / 0.73 | (the plate is whole) |
| P | 3 | (c) pro values | 1,458 | - | 3.49 / 0.93 | (the plate is whole) |
| M | 1 | (a) both off | 568 | 4.4 / 2.29 / 0.4, 89.1% | - / - | 5,874 / 17 |
| M | 2 | (b) pull by stroke | 344 | 3.79 / 3.76 / 0.4, 5.1% | - / - | 5,421 / 17 |
| M | 3 | (c) pro values | 612 | 4.4 / 2.27 / 0.36, 89.6% | - / - | 6,164 / 16 |
| M | 4 | (d) both on | 364 | 3.79 / 3.76 / 0.36, 5.5% | - / - | 5,675 / 16 |
| M | - | the pro's file (`becker_hat_small_beckers_logo_hat_2_a.dst`) | 554 | 4.02 / 3.74 / (DST grid), 7.1% | - | - |

Look for: satin coverage (fabric between stitches), the bars and the wide
columns lying flat or puckering, the plate's fill covering and the small
disc's bean edge, the I's stem width against the art (~4.2 mm drawn, the pro
sews 4.0) and whether it sews split or plain, and the gaps staying open.

![](card_v7_40wt.png)

## Why only these two

Grepped on main (memory, `config.py`, MASTER_SCOPE) for flags held "until a
sew-out" / "unsewn" / "Kent flips after sew-out", then each checked against a
later ruling:

| Candidate | Not on this card because |
|---|---|
| `fill_turn_slant` | Kent held it for "the next card's OFF/ON swatch" (10-22), then flipped it ON from the flip sheet (10-23, #1049 -> #1057). In BASE. |
| `satin_underlay_short_columns` | flipped ON 10-23 (layout: underlay presence). In BASE. Its zigzag pitch has no knob, and the pro's pitch is not measured (0.6-1.3 mm, it swings with the reader's satin gate: `short-column-underlay-2026-10-22`), so there is no candidate value to sew. |
| `fill_underlay_cross` | flipped ON 10-23 (layout). In BASE. Its constants match the pro already: row 1.0 / stitch 4.0 against his 0.98 / 3.99 (`docs/settings-vs-pro-2026-10-21.md` row 15). |
| `trim_bury_under_later`, `small_solids_satin`, `compact_solids_satin` | flipped ON 10-23 (layout). In BASE. |
| `cut_every_jump` | held by Kent until #1048's walk-on-the-work lands: a construction hold, not fabric. |
| `tie_in_off` | ruled ON (10-23); its locks are the card's own on every piece, so no arm could show it. |
| `border_from_outline` | ruled ON (10-24), not a flag on main yet (#1065). |
| older gate-1 candidates (`bean_letter_*`, hairline / small-print flags, `chain_links`, ...) | not re-armed: cards v2-v6 carry them, and this card is the two flags Kent's 10-22 ruling leaves on fabric (queue item I5). The small-text set in BASE sews Fremont's small words as satin, so the bean-letter candidates no longer reach them. |
| `edge_cap_bean_pitch_mm` | its question (a longer bean stitch than 0.73) is asked here: `pro_measured_values` sews the bean edge cap at the pro's 0.95. |

## The file (pystitch reading the DST back)

| | 40 wt |
|---|---|
| file | `card_v7_40wt.dst` (39,512 bytes) |
| blocks on the card | 3 |
| stitches in the file / in the plan | 12,512 / 12,512 |
| colour changes in the file / planned | 0 / 0 |
| colours (stops) | 1 |
| extent (mm), x by y | 88.4 x 93.2 |
| x range / y range (mm) | [-44.2, 44.2] / [-46.6, 46.6] |
| inside 100 x 100 mm | yes |
| longest needle stitch (mm) | 4.83 |
| longest record, per axis (mm; the format's limit is 12.1) | 12.0 |
| trims | 59 |
| 0.8 mm lock-leg stitches | 725 |

Stitches per piece:

| piece | stitches |
|---|---|
| F:a | 3745 |
| F:c | 3900 |
| F:strips | 32 |
| M:a | 568 |
| M:b | 344 |
| M:c | 612 |
| M:d | 364 |
| M:strips | 72 |
| P:a | 1556 |
| P:c | 1458 |
| P:strips | 32 |

Stitches per colour stop:

| stop | thread | stitches (thread m) |
|---|---|---|
| 1 | dark | 12,683 (20.93) |

Where each piece sits (mm, x0 y0 x1 y1, centre of the card at 0, 0):

| piece | box |
|---|---|
| F:a | [-44.2, -44.6, 44.2, -18.3] |
| F:c | [-44.2, -13.3, 44.2, 12.9] |
| M:a | [-44.2, 33.8, -25.1, 46.6] |
| M:b | [-21.1, 33.8, -2.6, 46.6] |
| M:c | [2.0, 33.8, 21.1, 46.6] |
| M:d | [25.1, 33.8, 43.6, 46.6] |
| P:a | [-44.2, 18.5, -9.4, 28.2] |
| P:c | [-5.4, 18.5, 29.4, 28.2] |

