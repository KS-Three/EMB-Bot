# color_cap_fuse_split_tones: every design it moves (2026-11-18)

Original | flag OFF | flag ON, same size and frame. Main plus the flag (built
OFF; these are what ON would do), with the topology guard: **only edge-to-edge
halves fuse; a piece lying in a hole of the other (a dot inside its ring) never
does.** Swept with `python -m tools.cap_fuse_sweep` (the 9 prime-grader pro
jobs at their own sizes) and `--fixtures` (the 26 `corpus_scorecard.FIXTURES`
at 80 mm, left chest, Studio request); the md5 of `design["stitches"]` is
compared.

**Moved: 2 of 35 runs. Pictured: 2 of 2** (whole-design pair each, lettering
close-ups, and for the pro job close-ups of the changed spots). The other 33
are stitch-identical (`sweep.json`, `fixtures-*of3.json`). **Worse by eye: none.**

## History (kept so it is not repeated)

The first version fused any two cap-folded pieces sharing 1 mm of outline. On
the Drone's target icon that fused the inner dot into its ring and clogged the
open centre: worse. The topology guard (`cap_fuse._sits_in_hole`) refuses a
pair where most of one lies inside a hole of the other. THERMAL's two bands
touch along a shared edge and neither encloses the other, so they still fuse.
The same guard also stops the camera-gimbal pair (one orange lens in the first
version): that spot is now identical to OFF, not better, not worse.

## What each mover changed (read from the plan, not the picture)

`precision_drone` (62.6 mm hat): 117 -> 112 regions, 5 unions, stitches
14114 -> 14202, lettering-tagged shapes 25 -> 26.

| union (kept + absorbed) | where | from thread | by eye |
|---|---|---|---|
| `S95978c7e` + `Sb2de8c40` | THERMAL, E (x 22-27 mm) | 0824 + 0700 | **Better**: one letter, tagged `lettering_group`, same ~0 deg angle as T and H (`spot_THERMAL...`, `precision_drone_closeup_lettering.png`) |
| `S885001f8` + `S755bef70` | THERMAL, R (x 28-34 mm) | 0824 + 0700 | **Better**: one letter, tagged; its real counter kept |
| `S023dfb17` + `S0405abeb` | THERMAL, M | 0700 | Better (M tidier; not tagged as lettering) |
| `S4ba0c4f5` + `S6bc433a5` | THERMAL, A | 0824 | Better/no worse (bar pile reduced; not tagged) |
| `Sa9f1767c` + `S463bf58d` | PRECISION, the O (x 49-53 mm) | 3770 | No visible change (`spot_PRECISION_ON...`); two shapes became one |

Target icon (`spot_target_icon...`): not fused any more; ON matches OFF, centre
stays open. Camera gimbal: not fused; identical to OFF.

The E carries a 0.149 mm2 sliver hole (about 1.3 x 0.2 mm) where the two traced
bands did not meet; it is the traced gap, left as it is (closing it needs a width
constant next to ROADMAP gate 1).

`photo/drone_render.png` (80 mm, left chest): 119 -> 117 regions, stitches
18436 -> 18392, lettering-tagged 21 -> 21; two unions: the O of PRECISION
(`S718a4e40` + `Se1ac9b61`, x 62-67 mm, thread 3971) and the target icon's
ring halves (`S3c682663` + `S563951d0-2`, x 38-42 mm, y 78-81 mm, thread
1305). By eye (`drone_render.png`, `drone_render_closeup_lettering.png`): the
target icon sews as a clean open ring where OFF clogs it with a blob (better,
though the art's inner dot is not sewn in either); PRECISION's O no visible
change. Nothing worse seen.

Pictures: `precision_drone.png`, `drone_render.png`, the four `spot_*.png`
close-ups, `*_closeup_lettering.png`. Original art and our renders only: no
render of the professional's file is committed here.
