# Gaulke Roofing LC against the pro: deltas, causes, one fix (2026-11-19)

Kent, 2026-11-19: "see how you digitize this logo today, see how the pro
digitizes it, figure out the deltas, determine why you have deltas, then begin
fixes/changes to your code that moves you closer to the Pros output (almost
like a trial and error methodology)."

Job `gaulke_roofing_lc`: `testdata/photo/logo_gaulke_roofing.png` at the pro's
95.2 mm, left chest, the Studio's request (`tools.pro_pair`), against
`Embroidery Files/Gaulke Roofing/c golke logo LC.DST`. Numbers only here; the
pro's file is drawn nowhere in the repo (`tests/test_no_new_pro_renders`).

## 1. Today against the pro (main 283a54df)

`tools.pro_baseline` (one reader both sides):

| | ours | pro |
|---|---|---|
| stitches | 5,379 | 5,151 |
| trims | 23 | 42 |
| needle-up mm | 220 | 373 |
| stitch-type kappa (chance floor) | 0.24 (0.86) | |
| direction kappa | 0.50 | |
| solid IoU | 0.74 | |

The registered overlay (`tools/pro_parity/overlay.py`) puts the lettering on
the pro's within a fringe. The large miss is the roof and sun: his sit about
1 mm higher against the text, uniformly, which reads as his layout departing
from the art (DOCTRINE: "where the pro departs from the art"), not as a
tracing error. Not chased.

## 2. The lettering: where the construction differs

Per letter of STEEL ROOFING (`tools.letter_pieces` via
`tools.marine_construct.read_file`, rows 0.83-1.0), and by eye at 100 px/mm:

| letter | pro | ours today |
|---|---|---|
| T | stem, then ONE bar across its top (2 pieces, bar 4.1 mm) | bar right half, stem, bar left half (3 pieces; the stem's top crosses lie on the bar) |
| E | middle arm, then ONE column top arm -> stem -> bottom arm (11.2 mm), over the arm's root | stem cut across at the middle arm into two folded halves; arm before (1st E) or after (2nd E) |
| L | one column folded round the corner | one column folded round the corner; its first cross 0.77 mm against 1.36 (a small cap above the stem); last cross doubled |

## 3. Why

The cut is already the pro's. `outline_cut.find_cuts` gives the T a
"through" cut along the bar's underside (stem + whole bar) and the E one
along the stem's edge (middle arm + one folded column): two columns each,
captured from stage 7's own call.

The walk splits it. `columns._span_graph` cuts a through column into two spans
where another column's end lands on it, and the postman's walk
(`_euler_trail`, then `_edge_walk`) sews the halves either side of the
butting stroke. Starting at the butting stroke's free tip (`prefer`) was
already capped at the trim distance because on Gaulke's 4 mm caps it cost
entry trims (23 -> 30, `prefer_within_mm`).

## 4. The fix tried: `cfg.extra["lettering_columns_through_last"]` (built OFF)

For a letter whose junctions all land on ONE through column from free-tipped
branches, the walk becomes: each branch run out under itself and sewn back to
its join, then the through column run under to its far end and sewn whole,
keeping the walk's own entry and exit end (`columns._through_last_walk`). The
emit rule already sews a span's satin on its LAST visit, so every run-out lies
under satin to come. Kept per letter only when the sewn stitches cost no more
trims and no more hop on finished satin (`_walk_cost`) than today's walk.

Gaulke LC, 95.2 mm:

| arm | trims | stitches | direction kappa |
|---|---|---|---|
| today | 23 | 5,379 | 0.495 |
| through_last | 22 | 5,368 | 0.491 |
| reading_order | 21 | 5,372 | 0.488 |
| through_last + reading_order | 21 | 5,362 | 0.478 |
| pro | 42 | 5,151 | |

- **T:** bar whole after the stem on its own; the reader now counts 2 pieces
  (4.4 + 4.0 mm) against his 2 (5.5 + 4.1).
- **E:** whole only together with `lettering_columns_reading_order`. Sewn
  right to left (today's order on this line) the E is left toward the T, and
  its one column ends at an arm tip on its RIGHT, so the cost check refuses it
  (a counted trim out). Sewn left to right, it is the pro's: middle arm, then
  one 64-point satin top arm -> stem -> bottom arm.
- **The yardstick does not see it.** Direction and stitch-type kappa move by
  0.02 or less (noise; ROADMAP gate 4), because they read each cell's
  direction, not which stroke lies on top. The evidence is the construction
  count above and the pictures.

Tests: `tests/test_through_last.py` (the four STEEL letters as stage 7 hands
them, `testdata/gaulke95_lane_letters.json`). Our renders only:
`docs/renders/gaulke-through-last-2026-11-19/`.

**Flag sweep** (`tools.flag_sweep`, 18 tripwire placements + 26 corpus
fixtures, 0 errors):

| sweep | moved | trims that changed |
|---|---|---|
| `through_last` alone | 11 of 44 | gaulke hat 30 -> 28, LC 23 -> 22, beanie 22 -> 21, `drone_render` 102 -> 103; the rest unchanged |
| `through_last`, `reading_order` ON both arms | 11 of 44 | `enthusiast_logo` 8 -> 7; the rest unchanged |

Movers alone: the three Gaulke placements, `mfab_hat`, `precision_drone`,
`toat_machine_beanie`, and corpus `drone_render`, `enthusiast_logo`,
`logo_bridge_bar`, `logo_gaulke_roofing`, `screenshot_phone_ui_golke`.
Stitches within +-14 everywhere; needle-up within +-5 mm except
`enthusiast_logo` +11 mm. By eye at the 8 mm window of most change: the
Enthusiast T's bar is one piece, the Drone R's leg runs whole over the
bowl's join, MFab and Toat move a junction slightly; nothing read worse.
Not a flip request yet: the before/after pages come first (CLAUDE.md).

## 5. Next deltas, in order

1. The L's first cross (0.77 mm against 1.36): the pro's top is flat and full
   width, split in two.
2. The E's corner fans: his read as one curve, ours turn
   (`lettering_columns_inside_stagger` walks the inside ends; with it off our
   fans look like his). A flag Kent flipped ON from measurements: his call.
3. Trims: he trims nearly twice as often (42 against 21-23). Not a target
   (Kent 11-02 on trims: "My eye stands").

## 6. The reading_order defects this session was started on

- **STEEI (the L's foot lost under `reading_order`)** reproduces only on the
  pack's ref ef11041f (20 -> 22 trims). There the L's satin covered its stem
  only, in BOTH arms; OFF's foot was drawn by a travel run that happened to
  lie along it (entered from the R, right to left), ON entered from the E and
  laid none. On main 283a54df the L is one folded column both ways (19 -> 20
  trims at 80 mm). Fixed upstream, not by the flag.
- **Reach into photos:** on main without the rembg pointer,
  `photo_chrome_specular` has no lettering regions and the flag moves nothing
  (84 trims both). The pack's 39 -> 42 used the primary checkout's rembg; not
  re-measured with it.
