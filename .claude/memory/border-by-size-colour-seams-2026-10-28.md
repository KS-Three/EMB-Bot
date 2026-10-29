---
name: border-by-size-colour-seams-2026-10-28
description: Instagram's "rings round colours, not the logo" = border_by_size satin-ringing each gradient band >= 6 mm (+16.5% stitches), not bean; design-ramp fit refuses there; proposed rule (unbuilt): ring only edges facing fabric
metadata:
  type: project
---

2026-10-28. Kent: auto bean "goes around colours, not primary shapes", with no satin
border round the whole Instagram logo. Doc: `docs/bean-border-logic-2026-10-28.md`
(7-row when/when-not table); web research in
`docs/bean-outline-practice-research-2026-10-28.md`.

- **The rings are SATIN from `border_by_size`, not bean.** It reads each region alone, so
  every gradient band >= 6 mm gets fill + 2.1 mm ring on its whole perimeter, seams
  included. Main 32,023 st vs 27,488 OFF (+16.5%). `bean_only_lines` OFF changes nothing
  (`EDGE_CAP_EMPTY`: the band rings already covered the edge).
- OFF + `edge_cap="satin"` = Kent's picture (one ring round the whole logo): 29,014 st,
  trims 24 -> 30, but one stray cap stretch crosses the yellow band.
- `region_rides_design_ramp` catches nothing here (ramp fit refused). A gradient-lane-wide
  skip is wrong: 8 of 14 pro jobs route gradient.

**Why:** web sources say butting fills get overlap, gradients are blended, and none
outlines the steps; the pro beans 0 of 231 bare body edges.
**BUILT OFF the same day** (Kent: "Build rule OFF + measure"): with
`border_by_size_fabric_edges`, a size ring skips every seam it shares with another sewn
region (`_owned_by_later` over all regions). Instagram 32,023 -> 28,972 st, band rings gone.
**All 16 border_census pairs are byte-identical ON**: `border_by_size` rings only 3 paired
shapes (Gaulke x2, Tires) and none has a seam, so kappa stays 0.730. Shape-level kappa is
blind to it anyway.
**How to apply:** the flip is Kent's (preview). Still open: short outer stretches owned by
bands under 6 mm stay bare, the satin cap has a stray stretch, and ring colour is undecided.
Related:
[[border-by-size-2026-10-23]], [[border-from-outline-2026-10-24]],
[[bean-census-2026-10-27]], [[instagram-gradient-lane-edges-2026-09-30]].
