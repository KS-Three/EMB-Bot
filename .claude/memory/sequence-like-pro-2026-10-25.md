---
name: sequence-like-pro-2026-10-25
description: L10 "sew in the pro's order" measured FALSE, nothing built — the pro sews the cap rule (bottom-centre start, rows bottom-up, centre-out) and it costs him 1.7-5x a sweep; our order mistakes are 18 of 145 extra cuts; the gap is cuts inside one piece and isolated pieces
metadata:
  type: project
---

Queue item L10 asked for a `sequence_like_pro` flag on the reading that,
after #1048, "what remains is ORDER". Measured first with a new reader,
`digitizer/tools/sequence_pro.py` (one reader both DSTs, pieces per colour
block, every cut classed); full table `docs/sequence-like-pro-2026-10-25.md`.
Five hat jobs (Fremont, Becker large, MFab, Drone, Gaulke), `main` a7a7259f
+ #1048, arm with `trim_bury_under_later` + `cut_every_jump` ON.

- **The pro's order is the cap rule on 5 of 5 files**: first stitch at
  bottom-centre, each colour starts near the centreline, rows bottom-up,
  centre piece then one side outward then the other. The rule reproduces his
  piece order (Becker 52.5 = 52.5 mm, MFab 68.3 vs 67.9).
- **It costs him**: piece gap 1.7-5x stage 7's sweep over his own pieces.
  On OUR pieces it raises the gap on all five (Becker 49 -> 127 mm).
- **Ours 291 cuts, his 146.** A reachable piece passed over (the only
  order-fixable class): 18 ours, 2 his. Dead ends 140 vs 129 that any
  greedy tour of our pieces is forced into. Order buys at most ~29.
- We sew FEWER colours than he does on 4 of 5, so colour order buys nothing.
- **The gap is construction, ranked (cut arm, five jobs):**
  1. Cuts INSIDE one piece, 84 vs 25 (+59): Fremont's field 16 (11 its own
     fill sections), Becker's ring 12 (6 satin-to-satin splits), Drone's
     field 9 fill sections, the edge cap 19 (1/3/6/5/4 by job).
  2. Isolated pieces, +33 (any greedy order is forced into 129 cuts on ours,
     96 on his): MFab's slivers (29 pieces, 31 cuts in 1,438 stitches) and
     white left as fabric.
  3. Buried walk between pieces: Drone's pro walks 1,021 mm needle-down, we
     walk 135 mm (his 38 between-piece cuts for 84 pieces, our 82 for 90).

**Why:** "sew like the pro" reads as "copy his order", and his order is a cap
rule that spends travel (`cap_center_out`, parked OFF for exactly that,
DOCTRINE 2026-09-19). His low count comes from fewer, joined pieces.
**How to apply:** before an ordering build, run `tools/sequence_pro.py` and
read `cut_skipped_reach` — only that class moves with order. A DST revisit
count overcounts on files that walk across pieces; check run-level re-entries.
Related: [[cut-after-bury-2026-10-23]], [[trim-economy-2026-10-21]],
[[cap-order-and-the-pair-experiment-2026-09-19]],
[[silhouette-underfill-2026-10-24]].
