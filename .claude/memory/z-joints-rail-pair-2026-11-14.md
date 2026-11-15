---
name: z-joints-rail-pair-2026-11-14
description: and_pizza's Z under apex_cut fanned at one joint only because its top bar's piece read CURVED (coherence 0.46, spine bent) while the 180-deg bottom bar scraped straight; `rail_pair_bars` (cfg.extra, OFF) reads two long parallel sides as a straight bar; the guard still refuses the Z tips
metadata:
  type: project
---

Director's queue item 2, 2026-11-14. The apex guard (#1514) returned
and_pizza to OFF, saying only one of each Z's two joints fans and blaming
the walk's sewing order.

**Traced:**
- Under apex cut the Z's top bar is a short slab with one slanted end.
  `straight_axis` reads its outline coherence as 0.46 (< 0.55) and its
  spine as bent, so it is built as a curved column whose crosses swing into
  the cut. That swing is the fan.
- The bottom bar, the same shape turned 180 deg, scraped through the spine
  test and sewed straight.
- Walk order (bottom bar -> diagonal -> top bar) puts the swung bar on top.
  No single walk covers both bars' ends.

**`cfg.extra["lettering_columns_rail_pair_bars"]` (built OFF):** a piece that
fails both tests is straight when two long own sides run parallel ACROSS the
stroke (the longer >= 1 W, the other >= half of it). A half ring stays
curved. With it, both Zs build both bars straight and the joints read alike.

**The guard** refuses the Z tips on its own slide rule (0.96-1.00), not on
the fan. Whether to let them through is its owner's call.

**Why:** an asymmetry between mirror-image joints is a construction fork,
not an order.
**How to apply:** when two mirror joints differ, check each piece's column
`kind` first.

Write-up: `docs/z-joints-rail-pair-2026-11-14.md`. See
[[flip-candidates-2026-11-14]].
