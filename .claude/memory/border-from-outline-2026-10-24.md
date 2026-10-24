---
name: border-from-outline-2026-10-24
description: The pro's border follows an OUTLINE IN THE ART (kappa 0.76, n 588), not size or stroke; built as border_from_outline (OFF) — outline loops each body at his width (the art outline's thickness, 1.5-2.5), bodies fill. Read before touching border_by_size, keyline or any border rule.
metadata:
  type: project
---

L4, 2026-10-24. Tool `digitizer/tools/outline_census.py` (measure / digitize /
replan / prove / render), detector `digitizer_core/art_outline.py`, flag
`cfg.border_from_outline` (OFF), tests `tests/test_border_from_outline.py`.

- **The rule, one detector both ways:** an outline is a BAND region (>= 0.9 of
  it within 4 mm of its looped holes; Bridge's spoked wheel 0.67-0.71 is not)
  whose hole holds a BODY that touches the hole ring (>= 0.25 of its edge),
  fills it with its hole-mates (>= 0.5), is not held by a LETTER (a counter,
  sewn or not: Fremont's O's hold white the field sews — looping them sewed a
  spiked sun), and is at least as wide as the outline is thick: stroke (2A/P)
  / band (holder area within 4 mm per mm of body edge) >= 1.0. Pro-bordered
  bodies read 1.34-3.14; everything else <= 0.87 (MFab's AND WELDING inside
  the SAME keyline 0.50-0.87, satined by the pro).
- **Census, against `border_census`'s pro class:** pooled kappa 0.76 (raw
  0.980, n 588), >= 4 mm 0.73, one file per artwork 0.83. Misses: MFab's
  badge, Fremont patch's field, Bridge's wheel (pro borders, no art outline
  by the rule). False positives: Bridge's bowl/waves line drawing (he deleted
  the drawing). Counters (49, 13 read "pro BORDER" — letter satin on the
  counter edge) leave the population.
- **His width is ONE per outline and follows the art outline's thickness,
  not the body's size** (Becker large: all five faces ~2.4, faces 5.7-8.1 mm).
  Width = median band clamped 1.5-2.5 (`machine.OUTLINE_WIDTH_MM`): median
  miss 0.05 mm against 0.20 for size bands (a first build by size sewed
  Becker large at 1.7 against his 2.4). MFab is the widest miss (2.0 vs 2.4).
- **Construction traps:** spanning a thick keyline to its far edge fanned the
  loop's outer edge into a fringe (Becker's drop shadow) — the pro sews ONE
  width, so the thick rest is filled under; `_CLAMP_STEPS` (1.0/0.85/0.7)
  cost 15% of a thin keyline's width, so outline loops clamp exactly
  (`_exact_cross`). Unsewn bodies (Becker faces, white OFF) never reach
  stage 7: detection runs in `plan_stitches` over ALL regions.
- MFab with `sew_enclosed_white` OFF does not change (its outline is the unsewn
  white keyline). Convex outer corners still fan (pro mitres) — same as #1059;
  on Bridge's line drawing ON adds spikes and one garment pinhole (an outline
  strip under 1.2 mm the rest-fill drops). Fremont (control) ON = OFF bytes.
- G: (Drive) unmounted when C: filled on 10-24: `outline_census --width` and
  `_refind_pro` work round a missing root; Bridge's pro file is G:-only.

**Why:** Kent's border choice needed the pro's real separator; size (#1050)
and stroke both measured false for letters.
**How to apply:** flipping is Kent's (layout, judged in the preview).
Precedence: outline rule beats `border_by_size` and `enclosed_white_keyline`
on shapes it reads. Related: [[border-census-2026-10-23]],
[[border-by-size-2026-10-23]], [[keyline-band-2026-10-23]].
