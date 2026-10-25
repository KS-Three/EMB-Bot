---
name: pro-measured-values-2026-10-23
description: `pro_measured_values` flag (built OFF) puts the pro's fill stitch 3.49, satin 0.37/0.35, bean 0.95 on hat/LC/beanie presets; Kent flips after a sew-out
metadata:
  type: project
---

One flag, `cfg.pro_measured_values` (browser: `proMeasuredValues`), default OFF.
ON, on `structured_cap` / `pique_knit` / `jersey_tee` only: fill stitch 3.49 mm
(machine 3.0, JS 4.0), satin spacing 0.37 (0.35 on jersey_tee) against 0.40, bean
pitch 0.95 against 0.73 (bean letters and the bean edge cap; the run tier keeps
0.73). Numbers are rows 1, 2, 11, 19 of `docs/settings-vs-pro-2026-10-21.md`.

**Why:** ROADMAP gate 1 — physical constants, so built OFF, Kent flips after a
sew-out. The table in `fabrics.py` is untouched; values live in
`fabrics.PRO_*` / `pro_values_for`, mirrored in `src/fabrics.js` `PRO_MEASURED`,
paired by `test_fabric_wire.py`.

**How to apply:** an explicit `fill_stitch_mm`, `bean_letter_stitch_mm` or
`edge_cap_bean_pitch_mm` still wins over the flag. The satin value is a factor on
`SATIN_SPACING_MM` in `stage7_sequence`, so it also rides the thread-weight path.
Output-geometry tests: `tests/test_pro_measured_values.py`, `test/digitize.test.js`.
Renders: `docs/renders/pro-preset-values-2026-10-23/` (`tools/pro_values_render.py`).
Not covered: border-edge satin density (row 3, "read again when row 1 is sewn").

See [[cross-underlay-presets-2026-10-21]] for the sibling OFF flag on the same three presets.
