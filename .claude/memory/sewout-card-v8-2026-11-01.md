---
name: sewout-card-v8-2026-11-01
description: Sew-out card v8 — cut_every_jump (Python) and cutEveryJump (browser) OFF beside ON, the small-text bold factor and the 0.8 mm halo; on today's engine the Python flag WALKS Fremont's 148 floats (all on the white field) and CUTS ENTHUSIAST's; Drone's lever is the halo, not the bold factor; the 0.01 mm oracle finds one Python walk 0.029 mm off thread
metadata:
  type: project
---

2026-11-01, the K3 handoff's "Sew-out card v8" queue, cut on main 3896a7ae.
Tool `digitizer/tools/sewout_card_v8.py` (+ `tools/sewout_card_v8_lettering.mjs`
for the browser arm, `digitizer/tools/jump_walk_oracle.py` for the walk), card
`docs/sewout/card-v8-2026-11-01/` (one DST, two cones: white first for the
Fremont field, then dark; PNG, block previews, readback, README, scoring sheet).
92.0 x 79.2 mm, 15,891 stitches (4,126 white), 130 trims, ~24 min. Sew it in
the same sitting as v7.

**What the queue asked and what survived a check against the flips since
10-25** (five of nine lines dropped, each named in the README):
- `cut_every_jump` / `cutEveryJump` OFF | ON (Kent 10-21 / 10-26): KEPT, blocks
  F, E, J. **Today's Fremont at 92.5 is a different job from 10-23's**: the
  small lettering is re-set satin or 2 mm bean lines, and all 148 of its
  floats are rope-strand and bean-letter hops lying on the WHITE field
  (`sew_enclosed_white`, 10-26), so ON walks every one and cuts none (trims 29
  -> 29, +6 stitches). ENTHUSIAST's 19 floats are between letters on bare
  cloth: ON cuts 18 (trims 11 -> 29), 13 of them in the tagline alone. The
  browser flag on "Fritsch's Stitches" (medium_font, 44 mm, flat) cuts all 15
  (trims 3 -> 18). The card shows both answers of the flag, walk and cut.
- bold factor (1.45 vs the pro's 1.7-3.0) and the 0.8 mm halo: KEPT, block D
  (Drone 62.6 hat, AND DRONE under THERMAL and over the dome). Both act at
  stage 4, so Drone is built once per arm; the halo is `small_text.CLEAR_MM`
  (no flag), set per arm by the tool and pinned 0.8 elsewhere. **Measured:
  bold alone trades height for width in the same room** (2.0: x1.32, 1.02 mm
  columns from x1.40 / 0.92), **the halo alone buys height** (0.3: x1.74,
  1.04), together x1.65 / 1.35 -- the pro's x1.57 / 1.26. Arms a | c (bold
  2.0) | d (halo 0.3) | e (both).
- DROPPED: the 0.51 bay mouth (flipped ON 10-26 #1112 from renders; the 0.51
  is the pro's own file median) and the 5's bar slot (today's hat sews EST and
  1895 as 2 mm bean lines under `bean_only_lines`: no bay, no slot); the 0.25
  letter gap (#1084 was a census and a harness prototype, the `sewn_rails`
  clamp never built: no flag); the typed-text fabric preset (no question or
  value written anywhere); ENTHUSIAST's grow-away counters (the flag flipped
  10-26 from renders; the tagline sews on E (a), look there).

**The oracle (the handoff's nitpick):** `jump_walk_oracle.py` is the JS test's
raster oracle ported (0.01 mm cells, the OFF file's thread, no code shared
with the walk), run on each job's whole-design OFF and ON DSTs as the service
writes them. Fremont 154 walked segments (170.7 mm) all on thread; Enthusiast
1 on thread; **Drone 28 walked, ONE 0.54 mm walk stitch 0.029 mm past the
thread's edge** (at the badge's top, not on the card) -- more than the 0.015
the browser's 0.1 mm step showed before it went to 0.01. Arm (b) ships marked
with it; the cure is `_BURY_STEP_MM` 0.1 -> 0.01 (a sampling step, not a
physical constant), a build of its own.

**Card mechanics that mattered:** a piece keeps its OWN jump/cut flags (v7's
tools re-derived them from hop distance, which would have undone the ON arm's
sub-3 mm cuts); a hop the crop made is cut, never left as a float; the white
field is CLIPPED to the window (Liang-Barsky, path order kept) with sub-3 mm
edge hops sewn needle-down, or 22 crop-made cuts appeared along the window
edge; every arm pins 14 flags (`PIN`) and the halo explicitly.

**Why:** a session handed the 10-27 queue would have sewn five arms already
ruled or moot, and would have expected the Python flag to cut on Fremont (it
walks). **How to apply:** re-census a flag's effect on TODAY's engine before
carding it (`--cut` prints floats OFF/ON per job); when a card crops a design,
carry each run's own flags across. Related: [[sewout-card-v7-2026-10-24]],
[[text-cut-jumps-2026-10-27]], [[cut-after-bury-2026-10-23]],
[[reset-grow-away-2026-10-26]], [[reset-room-floor-2026-10-25]].
