---
name: color-cap-fuse-split-tones-2026-11-18
description: Precision Drone THERMAL's E and R were two overlapping shapes each (light + deep gradient band the colour cap folded onto one thread); `color_cap_fuse_split_tones` fuses edge-to-edge halves, ON 11-18 (Kent "Flip ON"); a dot in a ring's hole is never fused
metadata:
  type: project
---

2026-11-18, prime grader scorecard (Precision Drone hat: "THERMAL is mushed in the
middle, the E-R pair piles up", x 22-34 mm, y 50-55 mm). **Not a thread limit:** the
pro's E and R are separate plain column satin with the art's ~0.5 mm gap (gate 1 does
not apply). **Cause:** the orange gradient was cut across the middle into a light band
(thread 0700) and a deep band (0824); the colour cap folded both onto 1305 and left TWO
overlapping shapes per letter (E, R, M, A, L) on two layers, each with its own angle and
neither tagged as lettering (T and H, already one thread, were). None of the 11-15..17
lettering flags is the cause; `bevel_ring_fold` does not cure it.

**Flag** `color_cap_fuse_split_tones` (`cap_fuse.py`, PR #1654, right after the first
cap, before text detection): two cap-moved regions from DIFFERENT original threads, now
one thread, sharing >= 1 mm of outline become one polygon. **Topology guard (director,
11-18):** only edge-to-edge halves fuse; a piece lying in a hole of the other never does.
The first, unguarded version fused the target icon's centre dot into its ring and
clogged the open centre; it was never shown to Kent. 2 of 35 runs move (Drone hat,
`drone_render` at 80 mm), none worse by eye; flag-ON run of 55 related test files: only
the known `enthusiast_logo` golden (red with the flag OFF too). The sweep tool's first run
moved nothing because a TYPED flag went in via `cfg.extra`; pass it as a request key.

**Kent, 11-18:** "Flip ON (Recommended)", told: the gain is modest, the M keeps a slanted
patch, the target's inner dot is still not sewn, one artwork, the E has a 0.149 mm2
sliver hole (the traced gap; closing it needs a width constant beside gate 1). Pictures:
`docs/renders/color_cap_fuse_split_tones-2026-11-18/`. Related: [[prime-grader-2026-11-17]].
