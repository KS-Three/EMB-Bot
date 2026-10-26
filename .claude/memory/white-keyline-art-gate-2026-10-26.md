---
name: white-keyline-art-gate-2026-10-26
description: Kent 2026-10-26 "Gate to MFab art first" — white_keyline_art_recipe turns the MFab recipe on only for a dark host round a white field outlining letters; read on stage-4 regions with find_art_outlines; fires on MFab hat/LC only of 22 jobs
metadata:
  type: project
---

Kent ruled 2026-10-26: "Gate to MFab art first (Recommended)".

**Why a gate:** made a default for all art, the MFab recipe changed 19 of 20
other paired jobs and damaged four:

- Gaulke: the roof line was buried.
- Tires: the e counters were sewn white.
- ProSeal: the slot and the counters were sewn white.
- Becker: a white edge showed past the band.

So the recipe turns on by itself only on MFab-type art, and the other jobs
wait for their defects to be fixed.

**The flag** is `white_keyline_art_recipe` (`digitizer_core/white_keyline_art.py`).
It reads the stage-4 regions in `finish_generation`, BEFORE
`sew_enclosed_white` (the recipe's first switch) acts, using
`art_outline.find_art_outlines`. It fires when an outline is:

- `enclosed_background` (the white field);
- round at least one text-tagged, non-background body;
- inside a non-background host of `RING_MIN_AREA_MM2`, covering `INSIDE_MIN`
  of the field.

The verdict rides `PipelineResult.white_keyline_art` and is folded into
`plan_stitches` the way the photo verdict is. The recipe is six switches, the
rim (#1096) included.

**Measured:**

- It fires on MFab hat and LC.
- It reads false on the other 20 paired jobs.
- On MFab, the gate's DST equals the explicit recipe's, byte for byte.

**Why it stays narrow:**

- Becker's outline is its black band, and its white letter faces are
  background.
- To a T's and Drone's outlines hold no letter.

**How to apply:**

- To widen the gate to a new art type, fix that art's recipe defect first,
  then widen the test. Don't loosen it.
- The defaults md5s in a bystander report go stale the moment main's defaults
  move (#1057 did): prove "unchanged" with the verdict plus spot checks, not
  with old md5s.

Related: [[mfab-recipe-trims-2026-10-26]], [[mfab-underfill-panels-2026-10-25]].
