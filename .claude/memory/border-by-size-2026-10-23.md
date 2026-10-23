---
name: border-by-size-2026-10-23
description: The pro's size rule for borders built as `border_by_size` (OFF) — at 6 mm and up the separator is STROKE vs the satin ceiling, lettering carries the rule's real population, plain fills are a per-design coin flip
metadata:
  type: project
---

Built from `docs/border-census-2026-10-23.md` (PR #1043): `cfg.border_by_size`,
default OFF. Code: `stage7_sequence._border_by_size_width` / `_min_dim_mm`,
`machine.BORDER_BY_SIZE_*`, `tests/test_border_by_size.py`. Renders:
`docs/renders/border-by-size-2026-10-23/`.

**The rule, sharpened on the OFF rows at 4 mm and up (Fremont hat, Becker hat
large, MFab hat, Gaulke hat):** the pro sews a shape as whole satin while its
stroke fits his ceiling — every letter he satins reads 4.2-5.4 mm wide in his
file (Becker's "Marine", 6 of 6) — and as a FILL under a 1.9-2.5 mm satin
border once the stroke is wider (BECKER 5 of 5, MFAB 4 of 4, MFab's 17 x 6.5
bar). Threshold 6.0 mm on the census's own measure (twice the largest
inscribed circle); width 1.5 at 4-6 mm, 2.1 from 6 up (medians of his
bordered rows). Contrast is not it (census). Rows against it: Bridge's big
fills (8-10 mm, 95-120 dE) are bare in his file, Gaulke's 30 x 16 solid too —
plain fills at 6 mm and up are about half, per design, so the rule on
non-lettering is one pro's habit, not a law.

**Two traps the build hit:**
- The inscribed circle OVERSTATES stroke at junctions: Becker's "Marine"
  letters read 6-8.7 mm by circle, 5.3 by the pro's satin chord. A thin ring
  with a knot (Becker's 2.4 mm ring, 10.4 by circle) passes the circle test;
  the REACH gate (`BORDER_BY_SIZE_REACH_FRAC` 0.5: half the area within one
  column of the fill core the ring leaves) is what keeps it satin — rings
  reach 0.13-0.25, the pro's bordered bar 0.90. The core's own area share
  did NOT separate them (bar 0.07 vs ring 0.05; a first build used it and
  refused the bar). A stroke-width measure (median distance transform along
  the skeleton) would be the better test if this ever flips.
- The population the rule really moves is LETTERING (MFAB, BECKER at 7-8 mm
  stroke, sewn today as split satin under `satin_lettering_split`). Excluded
  here by the task's scope and because the lettering 5-10 mm lane owns it;
  the ON counts on Becker/MFab barely move for that reason.

**Why:** Kent asked for the pro's size rule as a flag with OFF | ON | pro
proof; the census's "size, not contrast" verdict is true at the corpus level
and a coin flip at the shape level above 6 mm.
**How to apply:** flipping it is Kent's, judged in the preview (layout, not
pull). Before extending to letters, measure stroke, not the inscribed circle.
Related: [[border-census-2026-10-23]], [[border-seam-ownership-2026-09-09]],
[[layout-judged-in-preview-2026-10-22]].
