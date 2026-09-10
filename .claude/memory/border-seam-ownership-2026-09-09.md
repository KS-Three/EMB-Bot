---
name: border-seam-ownership-2026-09-09
description: Satin borders sat 1.9 mm inside every abutting colour — the 2026-08-06 seam-yield inset the LATER shape; Kent ruled the colour sewn on top owns a shared seam and the shape underneath skips that stretch (open arcs, still on its edge). Seam detection needs 2×simplify_tol, not a hair-width.
metadata:
  type: project
---

**What Kent saw (2026-09-09):** *"the satin border is not following the outline
of each color"* — Instagram icon, `border="auto"`, 80 mm, forced flat. Measured:
14 of 17 bordered shapes had their border a median 1.4–1.9 mm INSIDE their own
edge (7–31% of border points on the edge vs. the correct 50%), and one shape
lost its border outright. Only the three first-sewn shapes were right.

**Root cause:** `stage7_sequence._yield_frontage` (commit `baa7abc`,
2026-08-06, "fix border seam-sharing for real"). Its rule: the first-sewn shape
keeps a shared seam, and every later shape's WHOLE border input is pulled back
column + margin (1.9 mm) off it. On artwork where every colour abuts — every
flat logo — that is a satin stripe through the fill, not a border. Its own test
asserted the inset as the wanted outcome. Invisible for a month because
`cfg.border` was unreachable from the Studio until PR #318 (2026-09-02).

**Kent's ruling (AskUserQuestion, 2026-09-09):** the colour sewn ON TOP owns the
seam — its column covers both fills' edges, which is what a border is for — and
the shape underneath skips that stretch, sewing the rest of its ring as open
arcs on its own edge. Not picked: first-colour-owns-with-omit (owner is whatever
stage 5's layer order says), both-stack (a 1.7 mm doubled ridge on every seam).

**How it is built:** `border_later` = shapes predicted to border
(`routes_to_run`, `_sews_satin`, `_border_wanted` — the same predicates
`stitch_one` routes on) minus every shape already picked to sew;
`_owned_by_later` unions the seam bands with them → `border_runs(omit=…)` →
`_ring_arcs` splits the ring, `_satin_arc` / `_bean_arc` sew what remains.
A bean ring judges each spine sample by its NEAREST EDGE (`nearest_points`),
not by distance to the seam — on a thin shape both sides of the spine are
within a column of it. `omit=None` is byte-identical to the closed circuit.

**The second defect, exposed by the first fix:** `_seam_band`'s 0.02 mm
hair-width assumed two abutting visible edges are "the identical curve". They
are NOT: each side is its own DP contour of the same pixel boundary (the
earlier shape's edge is the later ARTWORK's outline, the later shape's is the
earlier ARTWORK's — stage 5 clips against `geom_by_layer`). Measured on the
icon: p90 0.09–0.43 mm apart, only 13–67% of each seam within 0.04 mm. The
old 1.9 mm retreat swallowed those gaps; a tight omit showed them as 28 stubs of
1.6–2.4 mm border on one ring, EVERY one across a later bordering shape.
Tolerance is now `2 * cfg.simplify_tol_mm` (0.4 mm) at the call site; the
module default stays 0.02 for exact fixtures and diagnostics.

**Icon after:** every bordered shape has ~half its border points on its visible
edge (p10 0.00, the outer rail); 33,292 → 30,420 stitches; trims 34 → 30; the
pink ring's 28 stubs → 1 arc, and that one is across the satin-tier shape that
never borders. A fully enclosed EARLY shape (the small circle) now gets no border
of its own — the ring sewn over it borders that seam — correct by the rule, and
`BORDER_SEAM_SHARED` reports the pairs as a note, not a defect.

**Three test-writing traps, one session:** a free edge sits at the
PULL-COMPENSATED position (x = −0.3, not 0 — hit three times); a 2 mm slot
lightens to a bean on its spine, shortened ~2 mm per end by the corner
relaxation; `_seam_band`'s length (area / 2·eps) is a lower bound once eps
widens — fine for a threshold, wrong as a measurement.

**Prediction blind spots, all bounded, none seen on the icon:** a predicted fill
whose rows all degenerate, a `photo_width_floor` reroute, or widened lettering
the classifier reads differently on its column → that seam goes unbordered on
one stretch; a gradient shape riding the design ramp → both sides border it.

Related: [[first-physical-sewout-2026-09-01]] (borders-last, the same icon),
[[studio-display-layer-2026-08-25]] (render before ruling — this was found by
a render too, not by a number).
