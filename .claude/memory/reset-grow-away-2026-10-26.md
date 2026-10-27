---
name: reset-grow-away-2026-10-26
description: W4-04 -- `small_text_reset_grow_away` (cfg.extra, OFF) lands W3-11's pair: re-set letters widened by their RETRACED stroke, and a line with a neighbour the art leaves under 2 mm holds that edge (+-0.5 mm) while the far side, design edge included, takes the growth; beanie x1.15 -> x1.56, no no_room
metadata:
  type: project
---

2026-10-26, W4-04, builds what [[reset-room-floor-2026-10-25]] measured
(W3-11, PR #1099). Doc: `docs/reset-grow-away-2026-10-26.md`. Tests:
`digitizer/tests/test_small_text_grow_away.py`. Flag:
`cfg.extra["small_text_reset_grow_away"]`, read at the pipeline's one
`enlarge_small_text` call (`grow_away=True`); OFF byte-identical (md5 pinned
on main 46949f78). Layout: Kent flips it from renders, no sew-out.

**What it does (small_text.py):**
- `_traced_stroke`: 2 x the mean skeleton half-width of the RETRACED letters,
  median over the line, replaces the tagger's tag in the widening (and in the
  `text_cluster_stroke_mm` the re-set writes back).
- `_near_side`: per 0.1 mm column, the gap to the next shape above and below,
  read on the ART polygons (snapshot at the call), not on lines already grown.
  Near = the smaller gap if under `GROW_AWAY_NEAR_MM` 2.0.
- `_grow_away`: candidates are the held near edge, then moves of up to
  `GROW_AWAY_NEAR_GIVE_MM` 0.5 either way, on two grids (0.25 steps from the
  held edge AND today's art-anchored grid). The far design edge gives way by
  the whole growth. Nothing holds at any scale: today's placement.

**Traps hit building it:**
- One grid only from the held edge cost Drone x1.317 -> x1.234: its line fits
  between the dome icon and THERMAL only 0.50 up, between grid points. Hence
  the second grid.
- An unlimited "away" move let Fremont's date slide 2.3 mm onto THE again (the
  rope arcs down either side of it). Capping the near edge at +-0.5 is the
  pro's 0.07-0.46.
- Reading neighbours on the CURRENT regions made THE see its grown date
  1.5 mm above it and grow down. Read the art.
- `_place_line_reset` with `near`: costs are |near-edge move|, not |dy|.

**Measured ON vs OFF vs pro (full digitizes, 5 jobs):** ProSeal hat's
tagline cap / base +0.02 / +1.00 at x1.31 (pro -0.03 / +0.92, x1.30; OFF
-0.63 / 0.00); beanie x1.15 -> x1.56 (pro x1.49); ProSeal sews 0.81-0.82
(OFF 0.71-0.78, pro 1.10-1.26); Fremont's date holds under the rope
instead of straddling THE; 0 no_room either arm. Residual: the width rule
(beanie line x1.20 past its bar's ends, pro x1.14; Fremont date f 1.10).

**Kent's numbers (gate 1, not acted on):** Drone stops at x1.40 (pro x1.57)
against the 0.8 mm halo plus widening -- THERMAL above, the dome below, the
dashes beside; the pro keeps 0.15 / 0.30 mm thread to thread. The beanie is
NOT blocked by clearance under this flag (x1.56 vs pro x1.49).

**Contradicting rows, reported not fitted:** Fremont hat EST 1895 (the pro
dropped the rope and moved the date 2.07 down; ours holds by the rope), and
THE (no near side; placed as before).
