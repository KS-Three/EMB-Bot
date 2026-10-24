---
name: monoline-script-satin-2026-10-24
description: L7 script/italic census (Tires, Bridge vs the pro) — Tires' joined "ires" sewed FILL on dt_p90_cap alone; `monoline_script_satin` (OFF) gives a monoline stroke the lettering split's ceiling; pro's crosses stay square to the stroke on italic slants
metadata:
  type: project
---

L7, 2026-10-24. Census tool `digitizer/tools/script_census.py` (one reader,
both DSTs, stroke direction from the file's OWN coverage via structure tensor
— a fill's rows advance square to themselves, so a column's own spine can't
judge squareness). `FILE.dst@N` reads one colour block (Bridge's word touches
the ring otherwise).

- **Italic question answered:** the pro's crosses rotate WITH the stroke —
  on slanted strokes cross-vs-text 33.7° against slant 32.5° (dev 0.3°)
  on Tires, dev 3.0° on Bridge. Ours already does the same wherever we sew
  satin (T stem dev −3.3° both). Not a gap.
- **The gap:** Tires' "ires" (919 mm², ribbon 4.5 mm) sewed a 45° tatami —
  `classify_ribbon` reason `dt_p90_cap` (p90 5.37 vs 5.0) and nothing else.
  Pro: 9 satin columns, 8.9 % of crosses > 5 mm (max 6.79). Rule: monoline
  (dt_cv ≤ 0.25, elongation ≥ 20) → lettering-split ceiling. Over L9's
  21-job cache (671 regions) it fires on ONE shape (Tires); the four other
  non-text `dt_p90_cap` shapes (Golden Tee, MFab) read dt_cv 0.39–0.43 and
  the pro fills them. n = 1 supporting row — say so.
- **ON costs:** trims 10 → 24 (pro 10), column overlap median 7.6 mm vs his
  0.4; the satin tier's skeleton decomposition at the r/e/s junctions. The
  follow-up is construction (Column-lane-style walk), not the tier.
- **Trap:** rembg times out under a loaded laptop → PHOTO_BACKGROUND_REMOVAL_
  UNAVAILABLE even with main's venv patched in (Tires 8,075 vs 8,001 st).
  Check the warning in every Tires run; render from a pickled generation.
- Bridge: flag byte-identical. Its gaps are stroke width 2.76 vs 1.96 mm
  (pull + 400 px JPEG — gate 1) and stacked overlap 3.9 vs 0 mm.

Related: [[bridge-border-and-script-2026-09-30]], [[lettering-architecture-2026-10-07]].
