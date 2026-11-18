# color_cap_fuse_split_tones: every design it moves (2026-11-18)

Original | flag OFF | flag ON, same size and frame. Main `8051f118` plus the
flag (built OFF; these are what ON would do). Swept with
`python -m tools.cap_fuse_sweep` (the 9 prime-grader pro jobs at their own
sizes) and `--fixtures` (the 26 `corpus_scorecard.FIXTURES` at 80 mm, left
chest, Studio request); the md5 of `design["stitches"]` is compared.

**Moved: 2 of 35 runs. Pictured: 2 of 2** (whole-design pair each, plus
close-ups of the changed spots for the pro job). The other 33 are
stitch-identical (`sweep.json`, `fixtures-*of3.json`).

## Worse, named first

- **`precision_drone`, the target icon at the bottom** (`spot_target_icon_x25-37_y57-66.png`).
  Worse by eye. OFF is a ring with an open hollow centre; ON fuses the ring's
  two halves (`Sc374e8c8` + `S24664d70`, and the centre piece `Sa55452bd`
  into `Sc374e8c8`), and the centre fills with crossing stitches. The art has
  an open ring with a dot. The fuse unions pieces that the art keeps apart
  (the ring and its centre dot are different tones, both folded onto 1305).

## What each mover changed (read from the plan, not the picture)

`precision_drone` (62.6 mm hat): 117 -> 109 regions, 8 unions, stitches
14114 -> 14178, lettering-tagged shapes 25 -> 26.

| union (kept + absorbed) | where | from thread | by eye |
|---|---|---|---|
| `S95978c7e` + `Sb2de8c40` | THERMAL, E | 0824 + 0700 | **Better**: one letter, tagged `lettering_group`, same ~0 deg angle as T and H |
| `S885001f8` + `S755bef70` | THERMAL, R | 0824 + 0700 | **Better**: one letter, tagged; its real counter kept |
| `S023dfb17` + `S0405abeb` | THERMAL, M | 0700 | Better (M tidier; not tagged as lettering) |
| `S4ba0c4f5` + `S6bc433a5` | THERMAL, A | 0824 | Better/no worse (A's bar pile reduced; not tagged) |
| `S7eafb519` + `S6a243ed7` | camera gimbal, x 28-31 mm, y 20-25 | 1321 | **Better**: one orange lens, one direction (`spot_camera_gimbal...`) |
| `Sa9f1767c` + `S463bf58d` | PRECISION, the O, x 49-53 mm | 3770 | No visible change (`spot_PRECISION_ON...`); two shapes became one |
| `Sc374e8c8-2` + `S24664d70`, `Sc374e8c8` + `Sa55452bd` | target icon | 0824 | **Worse** (above) |

The E carries a 0.149 mm2 sliver hole (about 1.3 x 0.2 mm) where the two traced
bands did not meet; it is the traced gap, left as it is (closing it needs a width
constant next to ROADMAP gate 1).

`photo/drone_render.png` (80 mm, left chest): 119 -> 116 regions, stitches
18436 -> 18369, lettering-tagged 21 -> 21. By eye (`drone_render.png`): the
target icon becomes a clean open ring (better), THERMAL a little cleaner,
nothing worse seen.

Pictures: `precision_drone.png`, `drone_render.png`, the four `spot_*.png`
close-ups, `*_closeup_lettering.png`. Original art and our renders only: no
render of the professional's file is committed here.
