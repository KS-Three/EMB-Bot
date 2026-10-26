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

**The flag** is `white_keyline_art_recipe` (`digitizer_core/white_keyline_art.py`), ON by default since 2026-10-26 (the flip PR after #1108).
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

**The MFab extras (Kent 2026-10-26, "MFab extras into the gate", then "Hold
all four", then on the fixed numbers "All four (Recommended)").** `keyline_fold_slivers`, `skip_covered_shapes` and
`cfg.extra["absorb_fragments"]` (`RECIPE_EXTRA`) joined the recipe. MFab DST
trims: hat 40 -> 30, LC 52 -> 25 (pro 18 / 19).

**Absorb first bared the counters under the riders** (LC 12 mm2 new bare).

- **The cause:** a fragment inside a `RIDER_HOLES_KEY` hole split the panel,
  and the union rebuilt every other ring. Stage 7 matches rider holes by
  WKB, so the panel was looped, not filled.
- **The fix:** the join keeps the body's own rings, and the rider holes are
  re-read on the joined polygon.
- **What absorb costs, fixed:** 3 trims on the hat over fold + skip. It saves
  2 on the LC.

**How to apply:**

- Before adding a switch to the recipe, measure new bare garment against the
  recipe without it, not only trims. `hairline_travel`'s bare THREAD read 0.0
  through all of this.
- Any pass that rebuilds a polygon after stage 5 must keep the hole rings
  later passes match by WKB: rider holes, `outline_holes` widths.

Related: [[mfab-recipe-trims-2026-10-26]], [[mfab-underfill-panels-2026-10-25]].
