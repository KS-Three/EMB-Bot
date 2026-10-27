---
name: keyline-loop-chain-2026-10-26
description: keyline_loop_chain (OFF) — white keyline loops chained the pro's way: each loop starts nearest the next, the hop walked under loops still to sew (bury_hops' rule, footprint shrunk half a thread); MFab white-loop cuts 11 -> 5 (pro 5/6)
metadata:
  type: project
---

**What the pro does.** The pro sews MFab's white keyline as a few long satin
chains (6 cuts over 3 pieces). He walks loop to loop, 3-12 mm mostly. 96-100%
of each walk lies under white he sews AFTER it.

**What ours did.** Ours lifted between loops. Each loop ended where it began,
on the far side from the next letter.

**`cfg.keyline_loop_chain` (built OFF 2026-10-26, `stage6_border.keyline_runs`)**
does three things:

- **Chained start:** each loop starts, and so ends, where it comes nearest
  the loop sewn after it.
- **Buried hop:** each hop is walked under the loops still to sew
  (`_bury_walks`). It uses `monoline.bury_hops`' rule, with the satin
  footprint shrunk half a thread first.
- **Otherwise as before:** where no buried walk exists the needle lifts; it
  never bridges across finished thread. The band's first loop is entered
  where it was, then walked round under its own satin.

**Measured on main + #1122:** MFab white-loop cuts go 11 -> 5 on both jobs.
DST trims go hat 30 -> 22 and LC 25 -> 19 (pro 18 / 19). The exposed walk,
read the same way on both files, falls.

**On Becker's outline loops (flag ON):**

- 4 fewer trims;
- one walk on the band's edge, 0.1 mm of bare thread;
- one loop seam moved, opening a 0.3 mm2 gap.

**How to apply:**

- **Chain every loop, not only the ones you can bury.** The first build
  chained a start only when the walk into it was buried, and it barely moved
  (hat 7 -> 6 cuts).
- **Read exposure with both instruments.** `tools/travel_cover` reads a walk a
  few tenths inside a satin rail as exposed (its 1 mm cell is mostly off the
  satin). Pair it with a DST walk read before calling a walk exposed.

Related: [[keyline-band-2026-10-23]], [[white-keyline-art-gate-2026-10-26]], [[mfab-recipe-trims-2026-10-26]].
