# `cap_merged_layer_home` and `shadow_to_page`, flag OFF vs ON (2026-11-18, built OFF, not flipped)

Prime-grader fault `L_goldentee_hat` (Bad, `ruins`): black piles over the gold so the O counter, L and F are hard to read;
a grey fringe is sewn under GOLF for a soft blur; the TM is missing. Cause and numbers:
`docs/goldentee-golf-black-and-fringe-2026-11-18.md`. Two flags, `cfg.extra` keys, one per cause:

- `cap_merged_layer_home`: a DARK (L* <= 35) band (<= 0.8 mm) the colour cap folded onto another spool sews at that spool's layer.
- `shadow_to_page`: `bevel_fold` pass 1 alone (a drop shadow on the art's own page goes to the page).

**Moved, of 44 runs** (18 committed pro jobs at their own size, every placement, plus the 26 `corpus_scorecard.FIXTURES` at the
Studio request, 80 mm `left_chest`; md5 of `design["stitches"]`, four arms OFF / A / B / A+B): **5 move, 39 are byte-identical**
for every arm. MFab hat at 30 mm and Becker hat at 114 mm (sizes the tripwire does not cover): byte-identical. Pictured: 5 of 5
(Summit badge and Chrome moved in an earlier, wider version of A and not in this one).
Every picture is ORIGINAL | BEFORE (flag OFF) | AFTER, same size and frame. Files: `*_overview.png`, `*_close_GOLF.png`.
No professional's file is rendered.

| design | arm | stitches | trims | jumps | needle-up mm | threads | bare thread 0.20 | preflight |
|---|---|---|---|---|---|---|---|---|
| `goldentee_hat` 74.9 mm | OFF | 10,583 | 52 | 20 | 645 | 7 | 0.0 | B 76 |
| | A | 10,622 | 55 | 22 | 622 | 6 | 0.0 | B 76 |
| | B | 9,926 | 51 | 20 | 644 | 7 | 0.0 | B 76 |
| | A+B | 9,943 | 54 | 21 | 643 | 6 | 0.0 | B 76 |
| `fx:photo/logo_golden_tee.jpg` 80 mm | OFF | 11,395 | 62 | 22 | 705 | 7 | 0.51 | C 64 |
| | A+B | 10,602 | 59 | 21 | 692 | 6 | 0.31 (A alone 0.71, WORSE) | C 64 |
| `precision_drone` 62.6 mm | OFF / A | 13,966 / 13,976 | 102 / 100 | 33 / 35 | 1,557 / 1,459 | 9 / 8 | 3.45 / 3.45 | D 52 both |
| `fx:photo/drone_render.png` | OFF / A | 18,123 / 18,132 | 112 / 114 | 36 / 39 | 2,094 / 2,121 | 10 / 9 | 8.59 / 8.59 | D 52 both |
| `fx:photo/screenshot_phone_ui_golke.jpg` | OFF / B | 10,697 / 10,416 | 127 / 120 | 131 / 123 | 2,400 / 2,214 | 8 / 8 | 17.26 / 14.92 | C 64 both |

## By eye

| design | verdict | plan change |
|---|---|---|
| `goldentee_hat` | **Clearly better**, judged at print size first. The black pile is gone, the O counter is open, the L and F bars read, the grey fringe is gone (a few small grey beads remain under the G). Not as flat as the pro, and the red keylines still sew heavy. | A: 8 black bands (0.26 to 15.0 mm2) from layer 6 to layer 1, the second black block is gone (7 -> 6 threads). B: 4 Fieldstone regions dropped (87.1, 11.1, 2.3, 0.2 mm2). |
| `fx:photo/logo_golden_tee.jpg` | Same gain as the hat (same art, 80 mm chest) | A: 8 bands moved; B: 5 Fieldstone regions dropped (99.4, 12.1, 2.6, 2.1, 0.2) |
| `precision_drone` | no visible change | A: 72 dark/narrow cap-merged bands re-layered (e.g. 2776 layer 10 -> 3); the order moved, the picture did not. Jumps +2, needle-up -98 mm |
| `fx:photo/drone_render.png` | no visible change | A: 79 bands re-layered; needle-up +27 mm, jumps +3 |
| `fx:photo/screenshot_phone_ui_golke.jpg` | no visible change except the status-bar battery icon, which takes a green fill | B: 12 regions dropped (1.18 mm2 white, five 0.6-0.9 mm2 greys) |

## What got worse (all small, none by eye)

- `logo_golden_tee.jpg` bare thread 0.51 -> 0.71 mm with A alone (0.31 with both flags); `goldentee_hat` trims +3, jumps +2 with A.
- `drone_render`: +3 jumps, +2 trims, +27 mm needle-up. `precision_drone`: +2 jumps.
- Preflight grade and score move for nobody.

## Rule history

The first A moved every cap-merged region: Precision Drone re-layered 109 shapes (jumps 33 -> 62), Summit badge 34 (bare thread
1.38 -> 3.22 mm, needle-up +109 mm), and the grey fields were re-ordered with nothing to see. Limiting it to bands <= 0.8 mm
still moved Summit and the Drone's mid-tones; adding "thread L* <= 35" took Summit and Chrome out and left the Drone's navy.
Tests: `tests/test_layer_shadow.py` (4); the 15 related files pass with the flags OFF (285) and, forced ON by a plugin,
280 of 281 (the one, `test_white_keyline_art`'s dict-equality check, fails because the plugin adds keys to `cfg.extra`).
