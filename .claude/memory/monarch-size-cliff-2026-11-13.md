---
name: monarch-size-cliff-2026-11-13
description: Monarch loses a wing cell only at targets 90.50 / 91.75 mm: one cell's stroke CV jitters under textcluster LETTER_STROKE_CV_MAX 0.55, the wings tag as an 11-letter word, the Column lane sews a V as one arm (cover 0.656); owl same (-4.5% black); lighthouse CRASHES at 25.125 / 25.63
metadata:
  type: project
---

Full record: `docs/monarch-size-cliff-2026-11-13.md`. Kent picked "Size fragility trace" on 2026-11-13. This was
diagnosis only: nothing was built or flipped.

**Not a cliff, not segmentation.** Monarch sweep, 89-92 mm target by 0.25 mm: the orange regions and their area grow
smoothly. Sewn orange dips at exactly two widths, 90.50 (−7.1%) and 91.75 (−5.1%).

**Mechanism.** The wing cell at (+14, +24) mm has a skeleton stroke CV that jitters with size: 0.537 to 0.582. It
passes `textcluster._letter_candidates`' `LETTER_STROKE_CV_MAX` 0.55 only at those two widths. It then links the
orange cells into one 11-member cluster (`detect_text_clusters`). `columns.is_lettering` routes them to the Column
lane, which sews the V-shaped cell `Sfe1be372` as one arm: 292 → 198 stitches, `satin_cover` 0.656 against ≥ 0.964
untagged.

**Gate 1:** does not apply (a tagger bound, not a physical constant).

**Other designs.** The owl has the same flicker: 3 black shapes are tagged at 79.2 / 79.6 / 80.8 / 81.6 mm, costing
about 4.5% of its black. Seven designs are stable.

**Separate bug, not traced:** the lighthouse crashes at 25.125 and 25.63 mm (`stage6_fill.principal_angle_deg` given
a MultiPolygon).

**Why:** a session will otherwise retune `LETTER_STROKE_CV_MAX`. The CV jitters, so a new bound only moves the bad
widths (DOCTRINE 2026-09-16).

**How to apply:** options sent to Kent. My pick is a Column-lane `satin_cover` hand-back, built OFF. When a shape
"loses area at one size", sweep the target and check `text_candidate` before blaming segmentation. Related:
[[starter-weak-spots-2026-11-12]], [[the-80mm-ink-link-2026-10-15]].
