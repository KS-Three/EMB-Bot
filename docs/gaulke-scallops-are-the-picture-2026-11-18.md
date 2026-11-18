# Gaulke hat: the "scalloped" round letters are the picture, not the stitches (2026-11-18)

Prime grader pins (scorecard 2026-11-17, `L_gaulke_roofing_hat`): the C of GOLKE has a scalloped outline all
round its bowl, repeating on G, O, S, U (near x 10.0, y 36.0 mm); the first O of ROOFING has a bumpy outer
ring (39.0, 44.5); the outer left roof wing has a scalloped edge and a blunt tip (34.0, 23.0).

**Verdict: the scallops are in the rendering, not in the needle points. No digitizing change. Nothing built.**

## What I looked at
Current main (8051f118), `tools.prime_grader capture --only gaulke_roofing_hat`, then `kit`. At 30 px/mm
our render does show beaded edges on C, G, O, S and on the straight wing edge
(`docs/renders/gaulke-scallops-2026-11-18/ours_tile_B1.png`, `ours_tile_B2.png`: our render only).
The renderer draws each thread as a round-ended filament. A satin edge with an end every 0.4 mm therefore
always looks like a row of beads.

## The measurement
Needle points (plan stitches, design mm) against a fitted circle or line, our file vs the professional's
`.DST` for the same job, aligned by phase correlation of the two coverage rasters. Scripts are alongside
(`*.py.txt`), using `tools.curve_facets.edge_points` to take the needle points that sit on a coverage edge.

| measure | ours | professional's |
|---|---|---|
| C outer bowl, left arc (6.6, 36.5): off-circle RMS | 0.031 mm | 0.030 mm |
| C outer bowl, top arc (11.5, 31.4): off-circle RMS | 0.024 mm | 0.020 mm |
| 27 vs 22 clean arcs (R 2-10 mm) over the lettering band: off-circle median / p90 | 0.024 / 0.046 mm | 0.022 / 0.034 mm |
| same arcs, turn std per needle point | 7.0 deg median | 6.9 deg median |
| end spacing on arcs | 0.42 mm | 0.40 mm |
| straight edge, roof wing underside (36, 27.2): line RMS | 0.048 mm | 0.069 mm |
| straight edge (41, 25.9): line RMS | 0.009 mm | no 5+ point edge |
| straight stem (70, 37): line RMS | 0.10 mm | 0.42 mm |

Our needle points sit on a smooth curve to about 0.02-0.05 mm, which is the 0.1 mm file quantisation floor,
at the same 0.4 mm end spacing as the professional's file; straight edges are straight to 0.01-0.1 mm. This
matches `curve-facets-2026-11-14` (the pro: one satin end every 0.36-0.41 mm). There is no faceted outline and
no rail wobble big enough to see: a 0.03 mm RMS scatter is a tenth of a thread width. The grader's reading
comes from the round-ended thread drawing, which the professional's render shares (the same beading is
visible on its edges in the kit overview).

## Not settled here
- The wing's tip is drawn about 1 mm blunt where the art tapers to a point. I saw it in tile B2 but did not
  measure it, and it is a different mechanism from scalloping (satin end width at a taper), so it is not
  covered by this verdict.
- Readings are instrument readings (ROADMAP gate 4); the probes are 1.0-1.5 mm windows at hand-chosen
  places plus a 1.5 mm grid, and the pro file was aligned by correlation, not by a fit to the art.
- A sew-out would show whether 0.4 mm ends read as a smooth edge in thread; geometry cannot say.
