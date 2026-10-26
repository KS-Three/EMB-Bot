---
name: isolated-pieces-2026-10-25
description: W4-02 — #1072's +33 isolated pieces is MFab's white keyline fragments plus block accounting (compare ENTRIES, not greedy); the white flip removes them but moves 16 cuts inside the band; `absorb_fragments` built OFF, after stage 5, takes MFab 77 -> 60 trims
metadata:
  type: project
---

W4-02 read every piece no tour reaches without a cut on the five #1072 hats
with a new reader, `digitizer/tools/isolated_pieces.py` (sequence_pro's piece
and reach rules; per block, reach COMPONENTS; the pro read at the same place
through `register_pair`, by his thread ON TOP). Main 7995d515, both
`sew_enclosed_white` arms. Doc: `docs/isolated-pieces-2026-10-25.md`.

- **Compare files by ENTRIES** (components over the file, each entered by a
  colour change or a cut). Isolated and greedy counts free one piece per
  block, and the pro's Drone is 22 blocks to our 9: Drone reads 52 isolated
  to his 38 for 61 entries to his 60. Five jobs, white OFF: 132 vs 129.
- **The real excess is MFab's 22 white keyline fragments** (rescued sub-floor
  specks 0.3-0.7 mm wide, 0.0-0.2 mm from the unsewn white field). The pro
  sews those places as his band (merges 17, bridges 5).
- **The white flip removes them (22 -> 1) but MFab trims RISE 59 -> 77**: the
  fragments now lie on the sewn band and stage 7 cuts run loop to run loop
  (16 cuts) -- the cut moved inside the piece.
- Built `cfg.extra["absorb_fragments"]` OFF (`digitizer_core/fragment_absorb.py`,
  two lines after `resolve_overlaps` in `_plan_stitches`): a fragment narrower
  than the pro's narrowest satin column (0.70 mm, census p01 of 2,141 swings
  ACROSS the column in 28 files) within one thread of a same-thread body is
  unioned into it. MFab white ON: 77 -> 60 trims, cut arm 57 -> 43, exposed
  travel 25.0 -> 22.8, bare equal. Byte-identical on Fremont/Becker/Gaulke and
  on MFab white OFF; Drone one fragment, +1 isolated, trims equal.
- **Gate 3 refused the first build**: unioned BEFORE stage 5, the field's new
  outline re-planned the black (a letter's holes 6 -> 4), its fill
  re-sectioned, MFab exposed 25.0 -> 41.3 mm on one 17.4 mm leg. After stage 5
  no other colour moves.

**Why:** "isolated pieces" read as a construction gap; mostly it was the
colour-block accounting, and the real part is the white flip's.
**How to apply:** quote entries, not greedy cuts, across files with different
block counts. A region-level change before stage 5 re-plans every colour
round it: if only one colour should move, act on stage 5's planned regions.
Footprint width cannot census anything under ~1.1 mm (lock knots); read
satin swings. Becker under the white flip: stitches 8,056 -> 16,921, exposed
14.0 -> 43.8 mm -- flag for the flip PR. Related:
[[sequence-like-pro-2026-10-25]], [[in-piece-cuts-2026-10-25]],
[[white-faces-fill-2026-10-25]], [[enclosed-white-like-pro-2026-10-23]].
