# The satin raster ate every counter's edge — 2026-09-04

**Found by** `tools/sewn_compensation.py` on the pull-comp PR (#344): the
repro's white satin frame and ring read 57% / 47% of their compensation
strips covered, the blend regions 100%.

**Mechanism.** `stage6_satin._rasterize` (and its byte-equal twin
`shapefield.rasterize_polygon`) painted holes with `cv2.fillPoly(…, 0)`.
`fillPoly` paints boundary pixels: the exterior gains half a pixel, a hole
LOSES half a pixel, the medial axis shifts outward, and `_rail_points` sets
both rails to the NEARER boundary hit (the exterior), so the hole-side rail
stopped two half-pixels short — 0.18 mm at 6 px/mm, measured on the repro's
frame and ring; the exterior rail sat within 0.006 mm.

**Fix.** Paint each hole half a pixel SMALLER (`shapefield.hole_px`, shared
by both twins; a hole too small to survive the shrink is painted as it was).
Hole-free masks byte-identical. Frame 57 → 66%, ring 47 → 59%. The
instrument's ceiling for a perfect satin strip is ~80% (0.4 mm legs under a
0.15 mm buffer); the rest is corner smoothing, recovered by
`rails_follow_edge` (sew-out gated — Kent's call, do not flip it).

**Rejected, measured:** redrawing the hole's boundary as material after the
fill (`cv2.polylines`) — closes a three-pixel counter to a speck the medial
axis trips over (the drone's satin "A" at hat front: 97 → 54% of its artwork
sewn) and spurs larger holes (scene_stub's uncovered area doubled). A
pixel-centre-exact raster (`shapely.contains_xy`) fixes more but re-touches
bars and tips (pushcomp cap gaps shift 0.2 mm, ribbon_curve's start cap
fans) — 8 test failures vs 1. `rint`, `shift=8`, `LINE_AA` do not fix the
bias at all.

**Trap.** `pkill -f <pattern>` / `pgrep -f` match the shell running them —
filter to python processes first (bitten twice this session).
