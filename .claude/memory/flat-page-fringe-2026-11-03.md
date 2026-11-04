---
name: flat-page-fringe-2026-11-03
description: flat_page_fringe_exclude (OFF): the page-edge blend leaves the flat palette fit and stage 3's chain rescue. Pooh pale-thread flecks 59 -> 25 at 80 mm; band scales with upscale; page = median, not bg_edge_rgb; the outline's INNER blend is untouched
metadata:
  type: project
---

Kent 2026-11-03, Pooh at 6 colours, "a hole in the honey jar": the sheen sewed
in Stone 0873 (reads as fabric), shared with the page-edge fringe's 59 flecks.

**What it is** (`stage2_quantize.page_fringe`, `_kmeans(drop=)`, stage 3
`_chained_small_regions(fringe=)`): flat lane only, never an alpha cut-out.
A band pixel within `max(flat_page_fringe_px, ceil(upscale)+1)` of the page is
fringe when it is within 2 flood tolerances of the PAGE colour, or on the
chord page -> the farthest-in-colour valid pixel beyond it (t < 0.85, within
2 x `merge_delta_e`). Fringe pixels do not vote in the Lloyd update (the
k-means++ init still sees them), take their nearest non-fringe pixel's label,
and a stage-3 chain mostly of them is not rescued.

**Measured (Pooh 80 mm, 6 colours):** pale thread Stone 0873 -> Wild Rice 0862
(the pot's own tone), sub-3 mm2 flecks on it 59 -> 25, regions 237 -> 222,
stitches 28,004 -> 25,914. Palette also moves elsewhere (olive on the pot's lit
side), so "nothing else changes" is NOT met; 54.6 mm picks other threads.

**Traps:** (1) dropping fringe pixels BEFORE the init re-seeds the whole
palette (use `drop`); (2) the ramp is `upscale` px wide; (3) `bg_edge_rgb` is
pulled toward the figure, the page is the median of `bg_mask` pixels; (4) a thin
dark outline inside the band: take the farthest-in-colour pixel beyond, not
the nearest interior one; (5) the outline's INNER blend with the fill still
seeds pale flecks: not built, the next option.
Related: [[white-counters-open-2026-10-26]], [[flip-sheet-wave3-2026-10-26]].
