---
name: border-by-size-corner-loss-2026-11-17
description: border_by_size ring redraws a small square as a cushion (Intel's blue square, loss 12.1% vs next 5.8%); border_by_size_corner_loss refuses a ring over 0.083 rounding loss; ON 11-17 (Kent "Flip ON"); only Intel moves of 44 jobs
metadata:
  type: project
---

2026-11-17. Fault: `border_by_size` rings a fill of min dim >= 6 mm with a 2.1 mm
satin loop built on `round_inward(part, BORDER_CORNER_RADIUS_MM = 2.1)`
(`stage6_border.py` ~l.1065). On Intel's blue square (Commons PNG, 100 mm left
chest, 7.3 x 7.2 mm, region Sa06ad4a2) four 2.1 mm arcs leave 3 mm of straight
edge: the flat square sews as a cushion of four trapezoids (141-point ring over
250 fill points).

- **Not a mitre.** The existing `_satin_loop(mitre=)` is `outline_loop_mitre`'s
  pivot (`_pivot_ring`, "NOT a mitre", keyline far rail outside). On a by-size
  ring the far rail is inward and the pivot never fires: probe md5 identical
  ON/OFF. No second mitre was written.
- **Rule.** `loss = 1 - area(round_inward(poly)) / area(poly)` on the region
  polygon (`stage7_sequence._corner_loss`). Census of 44 jobs (22 JOBS, 10 logo
  batch, 10 batch2, texaco, intel), 19 by-size rings: Intel 0.1205 (2.10x the
  next), Texaco T's 0.0575 / 0.0508, NPS 0.0356 ... Python 0.0016.
  `machine.BORDER_BY_SIZE_CORNER_LOSS_MAX` = 0.083 (geometric middle).
- **Flipped ON 2026-11-17** (Kent, shown the Intel ORIGINAL ART | BEFORE | AFTER
  sheet: "Flip ON (Recommended)"). `CORNER_LOSS_2026_11_17_OFF` in conftest
  `PRE_FLIP`; the pin file stays false.
- **`border_by_size_corner_loss` (was OFF at build).** `_border_by_size_width` reads None over
  the constant, so prediction, seam ownership and emitter agree; wins over a
  group stamp, and `tag_border_by_size_groups` skips a refused shape (no
  evidence for its line).
- **Measured, OFF vs ON, 44 jobs:** only Intel changes (5077 -> 4932 stitches,
  trims 8 -> 7, ring gone, plain fill square); 43 byte-identical (32 with no
  ring, 11 with rings). Pictures local only (public repo).
- Tests `tests/test_border_by_size_corner_loss.py`. Built OFF 11-17 (#1622), flipped ON the same day.
