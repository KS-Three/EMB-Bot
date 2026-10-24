---
name: border-from-outline-2026-10-24
description: The pro's border follows an OUTLINE IN THE ART (kappa 0.78, n 602), not size or stroke; built as border_from_outline (OFF) — outline loops each body at his width, bodies fill. Read before touching border_by_size, keyline or any border rule.
metadata:
  type: project
---

L4, 2026-10-24. Tool `digitizer/tools/outline_census.py` (measure / digitize /
replan / prove / render), detector `digitizer_core/art_outline.py`, flag
`cfg.border_from_outline` (OFF), tests `tests/test_border_from_outline.py`.

- **The rule, one detector both ways:** an outline is a region whose looped
  hole holds a BODY that touches the hole ring (>= 0.25 of its edge), fills it
  with its hole-mates (>= 0.5), is not a counter, and is at least as wide as
  the outline is thick: stroke (2A/P) / band (holder area within 4 mm per mm of
  body edge) >= 1.0. Pro-bordered bodies read 1.34-3.14; everything else
  non-counter <= 0.87 (MFab's AND WELDING inside the SAME keyline 0.50-0.87,
  satined by the pro — the ratio is what separates big from small letters).
- **Census, against `border_census`'s pro class:** pooled kappa 0.78 (raw
  0.978, n 602), >= 4 mm kappa 0.72, one file per artwork 0.85. Misses: MFab's
  badge and Fremont patch's field (pro borders, no art outline). False
  positives all Bridge: the wheel ring round the yellow disc (his file DOES
  ring it in satin; the census reads FILL) and the bowl/waves line drawing (he
  deleted the drawing). Gaulke counters read "pro BORDER" — letter satin on the
  counter edge — so counters leave the population.
- **Pro width on outlined bodies:** 4-6 mm 1.71 (n 9), 6+ 2.20 (n 15) ->
  `machine.OUTLINE_WIDTH_MM` ((6, 2.2), (0, 1.7)).
- **Construction traps:** spanning a thick keyline to its far edge fanned the
  loop's outer edge into a fringe (Becker's drop shadow) — the pro sews ONE
  width, so the thick rest is filled under; `_CLAMP_STEPS` (1.0/0.85/0.7)
  cost 15% of a thin keyline's width, so outline loops clamp exactly
  (`_exact_cross`). Unsewn bodies (Becker faces, white OFF) never reach
  stage 7: detection runs in `plan_stitches` over ALL regions.
- MFab with `sew_enclosed_white` OFF does not change (its outline is the unsewn
  white keyline). Convex outer corners still fan (pro mitres) — same as #1059.

**Why:** Kent's border choice needed the pro's real separator; size (#1050)
and stroke both measured false for letters.
**How to apply:** flipping is Kent's (layout, judged in the preview).
Precedence: outline rule beats `border_by_size` and `enclosed_white_keyline`
on shapes it reads. Related: [[border-census-2026-10-23]],
[[border-by-size-2026-10-23]], [[keyline-band-2026-10-23]].
