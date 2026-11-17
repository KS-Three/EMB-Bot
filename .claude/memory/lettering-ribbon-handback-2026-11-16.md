---
name: lettering-ribbon-handback-2026-11-16
description: `lettering_columns_ribbon_handback` (ON since 2026-11-16, Kent "Flip ON"): a Column-lane member that is a dt_p90 OUTLIER (>= 1.6x its cluster median, cluster >= 3) AND has an ordinary fill verdict sews down the ladder. Fixes Adidas' bar only; plain fill rule rejected (31 real letters)
metadata:
  type: project
---

Lettering ribbon hand-back, 2026-11-16 (built OFF, then flipped ON the same day: Kent, shown the Adidas ORIGINAL ART | BEFORE | AFTER sheet, "Flip ON (Recommended)").

**Fault.** A non-letter tagged into a text cluster (`textcluster.py`) is routed to the Column lane (`columns.is_lettering`), which skips `classify_ribbon`, so a solid sews one fanned satin column. Texaco's red-disc wedges (`dt_p90_cap` 6.2 vs 5.0; `dt_irregular` 0.527/0.518 vs 0.5) and Adidas' smallest bar (`width_cap` 5.601 vs 5.0, 144.9 mm2, split satin with slits).

**Plain rule REJECTED (foreman, sheets viewed).** Census of 43 jobs, 509 lane members: 39 fill verdicts (dt_p90_cap 23, width_cap 8, dt_irregular 5, aspect 2, photo_width_floor 1), of which 31 are real bold letters (Becker, Visa, Canon, USGS); ON they went to the ladder (Visa 4385/5 -> 9550/10, Canon 3344/5 -> 7480/10).

**Rule now.** `stage7_sequence.stamp_ribbon_outliers` (once per design, in the pipeline before borders-last and again at sequence start) stamps a lane member whose dt_p90 is >= `RIBBON_HANDBACK_OUTLIER` (1.6) x the median of its text cluster's lane members (cluster >= 3). `_ribbon_handback` then also needs an ordinary-ceiling fill verdict (not `photo_width_floor`); it sews as untagged (ordinary ceiling, by-size border), tags stay. Ratio table (14 jobs, 178 members): real letters max 1.30, Adidas bar 2.01, Texaco 1.43-1.53 (stay in the lane on purpose), Gaulke/MFab ~1.0-1.42 stay. Candidate resting on one logo.

**Measured** (14 jobs with a fill-verdict member): only Adidas changes, 6829/8 -> 7212/8 (slits gone); the other 13 are byte-identical. Tests `tests/test_lettering_ribbon_handback.py`; `test_polygon_axis` now counts four `polygon_axis` readers. ON since 2026-11-16; conftest `RIBBON_HANDBACK_2026_11_16_OFF` pins the pre-flip engine.
