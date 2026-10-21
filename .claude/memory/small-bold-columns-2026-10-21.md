---
name: small-bold-columns-2026-10-21
description: Column lane on ~4 mm grown bold letters — `lettering_columns_small_bold` (OFF): pull a share of stroke width, thin pieces floored not dropped, no pivot fans; costs bare 0.7→4.3 mm2; counters of 8/9/S are closed UPSTREAM by the growth
metadata:
  type: project
---

2026-10-21, follow-on to [[card-v4-sewout-letter-size-2026-10-20]]. The grown
Fremont small words (cap 4.0 / width 1.05 / stroke 0.85, 92.5 mm Hat) sewed as
blobs in the Column lane. Built `cfg.lettering_columns_small_bold` (OFF), stage 7
passes it only under `_small` (extent < 5 mm), so HOTEL FREMONT is untouched.

**Measured on the 21 grown letters** (isolated harness: captured stage-7 calls
replayed through `lettering_columns_shape`), OFF → ON: median satin stitch
1.23 → 0.85 mm (pro's DST: 0.86 tagline, 0.81 EST 1895, 0.90 THE — read off the
pro's colour block, not a box); crossed zigzag legs 238 → 9; folds 35 → 1;
unsewn 0 → 0 (a plain 0.1 pull gives 8 unsewn); sewn outside the letter
76.5 → 19.3 mm2. Costs: bare 0.7 → 4.3 mm2 (square ends leave corners), exposed
travel 17.9 → 24.7 mm.

**What did not matter:** `_MERGE_PAD_MM`, `_JUNCTION_TUCK_MM` (the tuck is
already capped at half a stroke). `SIMPLIFY_MM` did (0.12 → 0.06 under the flag).

**Traps:** `sewn_knots`' crossed count flips 3 ↔ 130 on a 0.02 mm pull change —
noise at this scale; read the render, never tune to it. Fans come from TWO
places: `_fan_ends` on straight pieces, and DTW `pair_rails` where one rail of
a serif block collapses to its inner corner. Rings (the 8) still fan, as the
pro's do.

**Not the lane's to fix:** 8, 9, S counters are 0.07–0.24 mm2 in the GROWN
polygons — a 2 mm-wide digit cannot hold two 0.85 mm strokes and a visible
counter. The pro's digits are wider. That is `small_text_cap_max_width_scale`
/ the stroke floor, upstream.

**Why:** a fixed fabric pull is a fraction of a big column and most of a small
one. **How to apply:** before tuning lane constants on small text, measure the
pro's satin stitch lengths per colour block, and check the input polygon
(render it) before blaming construction.
