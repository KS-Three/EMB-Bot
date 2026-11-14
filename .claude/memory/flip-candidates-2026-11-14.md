---
name: flip-candidates-2026-11-14
description: Two flip candidates measured 11-14 for Kent - `inshape_piece_lift` (ON since 11-14, Kent "Flip ON"; plain bug, Becker/MFab 13.7-60.6 mm needle-down stitches across white letters, Kent's "random cross over stitch") and `lettering_columns_apex_cut` (corpus OFF|ON verdicts)
metadata:
  type: project
---

Director's follow-ups on 2026-11-14 after the jag-source trace
([[jag-source-2026-11-13]]).

**`inshape_piece_lift` (PR #1483, built OFF; ON since Kent 2026-11-14, "Flip ON").** Kent's "Random Cross over
stitch shouldn't be here", on Becker hat large:
- Pins #0 and #1 are single needle-down stitches of 15.0 and 37.5 mm across
  the white letters.
- Cause: stage 7 concatenates `border_from_outline` / `enclosed_white_keyline`
  pieces (`keyline_rest`) with the step unset, so the adapter writes it as one
  stitch.
- Stitches over the 12.1 mm machine limit occur ONLY on Becker (5 sizes) and
  MFab (2). ON: none, at +1-2 trims each. The flat golden does not move.
- The 11-06 census's `extra["split_long_inshape_stitches"]` only tacked the
  same visible line down.
- Pins #14/#15 are a different cause: the Column lane's connector sewn on
  top of its own satin. Not fixed.
- Ruled: ON, accepting the +1-2 trims per design on Becker and MFab.
  CI tripwire alone (11-14): trims +1-2 on Becker x5, MFab x2; Becker hat
  large word cc 1.00 -> 0.84 alone, 1.00 with the redraw beside it.
  PRE_FLIP and `engine_2026_10_27.json` pin it False.

**`lettering_columns_apex_cut` corpus**
(`docs/apex-cut-corpus-2026-11-14.md`):
- 43 designs, 25 moved; by eye 10 better, 10 the same, 1 mixed, 4 worse.
- Better: all five Becker M's, ProSeal's A, Bridge's ring letters, the
  duotone N.
- Worse:
  - outline_lineart_logo, badly: line art tagged as text turns into long
    single bars;
  - k_line's K junction;
  - two stitches across the drone N's stem;
  - mfab_lc, slightly.
- Not a clean flip as built: it wants a guard (a cap on cross length
  against the stroke) first.

**How to apply:** both are Kent's flips. The table in
`docs/apex-cut-corpus-2026-11-14.md` is what he decides from. A stitch over
12.1 mm is never a judgement call: look for unset steps wherever stage 7
concatenates `stitch_shape` calls.
