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
**FLIPPED ON the same day** (Kent: "Flip ON (Recommended)") after a 21-logo corpus check.
9 logos change, all with fewer stitches. That includes both logos he graded Great: Tux and
the flat bull lose their inner same-colour rings inside the art's own outline. Trims rise
+1 to +9 on 5 of them. `PRE_FLIP` pins it False.
**How to apply:** ring colour is still undecided. The "bare outer stretches" turned out to
be covered on a closer render. The satin cap's stray stretch was its arc-to-arc bridge
sewn across finished fill; it now lifts instead (#1185).
**Kent's 13 circles on Instagram (10-29):** 9 are fill travel, the rest are sliver satin,
stage-2 jaggies and specks.
- `travel_legs`' exact read: 53 mm on the band's own finished rows.
  `fill_bridge_cut_exposed` (built OFF) cuts every such bridge past trim_at: 53 -> 0.4 mm,
  trims 23 -> 31. Adding `fill_section_travel` (Kent HELD it 10-27) gives 2.8 mm, trims 27.
- Still showing: underlay hops BURIED under rows nearly parallel to them (the top pink
  line). They show in the render and the exposure tools read them as covered. Read the
  ZOOM, not the number.
Related:
[[border-by-size-2026-10-23]], [[border-from-outline-2026-10-24]],
[[bean-census-2026-10-27]], [[instagram-gradient-lane-edges-2026-09-30]].
