---
name: connector-edge-walk-2026-11-14
description: Kent 11-14 "Build edge-walk" on #1490; `lettering_columns_connectors_edge_walk` (OFF) reorders the Column-lane walk so a join is covered by the stroke sewn next; 28 designs 268/44/32 mm at 589/639/596 trims; the pro's corner (one column turning it) NOT made — the fold is refused on Becker's E
metadata:
  type: project
---

Kent's ruling on #1490's pin #14 sheet, 2026-11-14: "Build edge-walk, notice
how the pro makes a nice corner with the thread andc continues the stitch to
the right". `connectors_buried` stays OFF until this lands and he sees it.

**The pro, read by eye on Becker's MARINE E, N and A (eight joins):**
- The stroke sewn first ENDS at the join, and the next stroke's satin STARTS
  there and covers it.
- He gets there inside the next stroke, as its underlay.
- A stroke with a free tip runs out under itself and is sewn back to its
  join.
- The E's bottom-left is ONE column turning the corner (that is Kent's
  "corner").
- No travel crosses a finished stroke.

**Ours:** the postman Euler walk is blind to which end a stroke ends at, so
a stroke ended at its far tip and the hop ran back across it.

**`lettering_columns_connectors_edge_walk` (built OFF; implies
connectors_buried):**
- When the buried walk leaves a trim inside the letter or a hop over 1 mm on
  finished satin, it prices every Euler trail per component, plus one more
  doubled span.
- It sews the 8 best and keeps a strictly better one by its stitches
  (`columns._edge_walk`, `_walk_cost`).
- The fold-cut judge reads the buried walk, so the cut stays the same.

**The 28 designs (#1490's set), OFF / buried / edge:**
- letters' travel on finished thread 268 / 44 / 32 mm;
- trims 589 / 639 / 596;
- digitize time the same as buried.

**Not done:** the corner. `lettering_columns_corner_fold` refuses both of
the E's inside corners. A third piece (the middle arm, about 1 mm away
across the narrow slot) touches each one, over the tenth-of-second rule in
`outline_cut._fold_corners`. The Director's next PR is the corner turn.

**Why:** Kent's flip of connectors_buried waits on this.
**How to apply:**
- A join's cleanliness is decided by the walk order, not the hop's route.
  Price walk orders on the emitted stitches.
- A station price disagreed with the stitches here and moved two clean
  letters the wrong way.

Write-up: `docs/connector-edge-walk-2026-11-14.md`. See
[[connectors-on-top-2026-11-14]].
