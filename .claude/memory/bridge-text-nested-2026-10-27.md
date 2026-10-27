---
name: bridge-text-nested-2026-10-27
description: Why Bridge hat's text never reaches the Column lane: textcluster._drop_nested drops 8 of 15 letters inside the 55 mm WHEEL candidate (under the 60 mm LETTER_MAX_HEIGHT_MM); the LC wheel is 65.5 mm, refused, so its text tags. Not quantization (dE 12.9 < 20), not script_strokes
metadata:
  type: project
---

Measure only (worker session of the 2026-10-27 director, main `8341d1f7`); full tables and drivers in the director's notes
folder, `bridge-text-column-lane-2026-10-27.md`. One recorded digitize each of Bridge hat and LC, one counterfactual arm.

**Where:** `digitizer_core/textcluster.py` `_drop_nested` (:596; applied at :994 on the default path, also :973, :1001,
:1697). A candidate whose bbox sits inside a larger candidate's bbox is dropped. The hat's black wheel region (62.6 x 55.1
mm) passes the letter door (`LETTER_MAX_HEIGHT_MM` 60, :461), its bbox holds the whole design, and 8 of the 15 text pieces
are nested away; the other 7 are refused (4 by aspect 1.47-1.52 on letters rotated on the ring, 3 by stroke CV 0.59-0.68).
The LC wheel is 65.5 mm tall, refused at `height_bounds`: 6 of 9 text pieces tag and the lane builds them (20 folds, not 2).

**Not the cause:** colour splitting (the hat's text is teal and green, dE 12.9 against the 20.0 link limit; the LC's is one
thread and still reads 6 of 9) and the script door (the script word is refused at aspect 2.61 and taken by `script_strokes`).

**Counterfactual (census-side, never shipped):** `_drop_nested` ignoring a nester over 6x the median candidate height (the
wheel is 13.7x, the next candidate 1.9x): 0 -> 8 of 15 pieces reach the lane, text folds 2 -> 5 and zones 0 -> 5, against his
35 and 37. Necessary, not sufficient. Narrowest fix, unbuilt: a `text_cluster_nest_guard` flag (OFF) guarding `_drop_nested`,
proof on the 13 pairs of `column_reach_census`.

**How to apply:** before a "Bridge text" or tagger-reach change, quote this; a big region admitted as a letter candidate
nests every glyph away, so a design whose frame region is under 60 mm tall loses its lane. Related:
[[column-reach-census-2026-10-25]], [[bridge-census-2026-10-27]].
