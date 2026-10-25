---
name: white-faces-fill-2026-10-25
description: Flipping sew_enclosed_white ON made Becker 8.4x slower because its white BECKER faces carry the word's text tag and sewed as Column-lane letters; `sew_enclosed_white_fields_fill` (OFF) sends a sewn white field to the fill tier at the pro's 22 deg. The house angle hides in fill_angle_deg.
metadata:
  type: project
---

2026-10-25, Kent: "Ship 3, fix white next". The five-flag flip (#1071) shipped
three lettering flags; `sew_enclosed_white` + `enclosed_white_keyline` were
held OFF because of this. Follow-up branch `claude/white-faces-fill`.

**The defect:** with `sew_enclosed_white` ON, Becker at 100 mm left chest took
2,848 s against 340 s (cProfile; 859 s against 104 s unprofiled), with
2,590 s in `outline_cut._refine` / `_fold_refine` / `pair_rails`. The five
white faces (200-370 mm2) sit in the BECKER word's text cluster and house
group, so `columns.is_lettering` sent each to the Column lane. That also
crashed GEOS on a one-station leg (`columns.column_runs`, guarded in #1071).

**Built OFF:** `cfg.sew_enclosed_white_fields_fill`. A sewn white field is not
lettering, sews on the fill tier (a forced rung, so a too-narrow field falls
back to the ladder) at `machine.WHITE_FIELD_FILL_ANGLE_DEG` 22 (the pro's rows:
3,364 of 3,912 long stitches at 20-25 deg). Becker 95.7 mm: 70.6 s against
55.3 s white OFF; the face block's rows read 20 deg on 97% like his.

**Trap:** the word's HOUSE angle is written into `meta["fill_angle_deg"]` by
`textcluster` (setdefault), the same slot a review override uses, so the
face filled flat at 0 deg until the white angle went ahead of it. Tell a
review override apart by `cfg.shape_overrides`, not by the meta key.

**Open:** faces 7,730 stitches against the pro's 4,949 (one continuous 20 deg
fill per half of the word; ours five clipped faces, median stitch 1.93 against
3.45 mm -- the length is `pro_measured_values`, gate 1). Flipping is Kent's.

Related: [[sew-white-areas-2026-10-21]], [[keyline-band-2026-10-23]],
[[big-letter-construction-2026-10-24]].
