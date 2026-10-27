---
name: satin-split-cuts-2026-10-27
description: satin_split (cuts inside one satin piece) is three causes; only the Column-lane letters' is ours -- `lettering_columns_slot_guard` (OFF) walks a letter twice, keeps the cheaper walk; 3 of 8 letter cuts, trims 261 -> 258, exposure -7.1 mm
metadata:
  type: project
---

`tools/inpiece_cuts`' satin_split class is 26 cuts on seven paired jobs (main
8341d1f7, the pro's widths). It is three different things:

- **16: loop-to-loop lifts in keyline/outline bands.** MFab is at or under
  the pro under #1134's `keyline_loop_chain` gate. Becker's bands are Kent's
  (chain held to MFab), and burying lifts with the loops unmoved takes 0 of
  them.
- **2: Drone satin-tier shapes.** The pro lifts more there.
- **8: inside Column-lane letters.** Ours lifts 11 times, the pro once.
  - Under 10 mm the pro lifts on 1 of 84 links between a letter's pieces.
  - Contradicting row: Becker's M, where he lifts 4.7 mm too.

**Cause of the letter cuts.** `columns._span_graph` merges ends within
1.3 W + 0.3 + pull (5 mm on Becker's bold strokes), across an E's slot or an
M's notch. The hop between the "same" node then leaves the letter, and step 4
trims it. The corner fold's `within` guard ran only on folded letters.

**The guard alone is a trap.** It took all 8 letter cuts, but exposure rose
by 10 mm. Step 4 sews hops with up to max(3, 2W) left on finished satin, so
the new walk crosses satin just sewn. Fremont's trims also rose by 2.

**`cfg.lettering_columns_slot_guard` (OFF):**

- `letter_walk.pick` walks each letter's final cut both ways.
- It keeps the guarded walk only where it cuts no more and lays no more travel
  off later satin.
- The fold-cut judge stays on today's walk: routing the judge through the pick
  changed which cut a Drone letter got.
- Measured: Becker S M, Becker L E and Gaulke E lose their cut. Exposure
  221.1 -> 214.0 mm, bare 10.65 -> 10.55. OFF is byte for byte on 7 jobs.
  MFab hat and the Drone are byte for byte ON too.

**How to apply:**

- To cut the 5 letter cuts left, change the construction, not the merge: end
  each satin where the next one starts, under satin still to come (the pro's
  way). Ours ends on a rail and crosses the column it just sewed.
- MFab's N and I cut between two walk components. That is a different fix.

Doc: `docs/satin-split-cuts-2026-10-27.md`. Related: [[apex-cut-2026-10-25]],
[[column-corner-folds-2026-10-23]], [[keyline-loop-chain-2026-10-26]],
[[in-piece-cuts-2026-10-25]].
