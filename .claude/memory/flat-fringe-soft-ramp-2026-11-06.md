---
name: flat-fringe-soft-ramp-2026-11-06
description: Bridge's blue split on the flat lane (stage0_scale_relative_grad routing) = the 400 px JPEG's 3-source-px soft edge at x3.25; `flat_page_fringe_soft_ramp` + `flat_ramp_blend_dissolve` (both OFF, enlarged rasters only) sew the art's 4 inks
metadata:
  type: project
---

Under `stage0_scale_relative_grad` (OFF) `logo_bridge_bar.jpg` routes FLAT and the
stage-2 k-means fit (not cap, snap, or tracer) loses the blue:

1. **Page fringe**: the spokes' black-to-page ramp is ~9 working px; the
   one-source-px band (`upscale+1` = 5) misses half, the greys vote with the
   blue lettering (63% of its slot) -> Vintage Blue 4752 + pale ring on every
   spoke. Band 5 -> 11: blue px at the page 16,696 -> 0; centre 13.8 -> 3.7
   dE00 from 4531.
2. **Interior ramps**: yellow-to-black (olive 6156 = the waves/anchor, BLACK in
   the art) and yellow-to-blue (gold 0442, 78 sub-3 mm2 pieces) clusters; the
   phantom dissolve counts one pixel as edge (0.49/0.43; 1.00 at ramp depth).

Cure (Bridge hat flip 41,853 st / 157 trims -> 20,182 / 23; main gradient
33,996 / 45): palette 0713/0020/1521/4531.

**Traps hit:** (a) `flat_page_fringe_exclude` acts at full resolution too and
broke the screenshot's "Done"/"SNOW PLOWING", so the soft band runs alone, on
enlarged rasters only. (b) A widened dissolve ate fremont_patch's tan rope
(grey-tan core between its OWN ramp clusters, 6.3 off the black-white chord vs
gate 6.0): second-round candidates must be a Lab blend of two KEPT colours.
Margin thin. (c) The gradient lane's "teal waves" are wrong too: art = black.

Flip is Kent's. Doc: `docs/flat-fringe-soft-ramp-2026-11-06.md`. Related:
[[flat-page-fringe-2026-11-03]], [[pot-slot-swing-2026-11-03]].
