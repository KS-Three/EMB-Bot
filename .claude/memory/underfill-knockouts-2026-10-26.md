---
name: underfill-knockouts-2026-10-26
description: Two silhouette_underfill defects from the MFab-recipe bystander run, fixed on the ON path - Fremont's white star (a host-colour mark another colour covers) was merged and sewn over; Becker's letter host filled the ring's whole outline, so white ran past the black loops and the edge cap took white. Gaulke's buried white is sew_enclosed_white, NOT the under-fill.
metadata:
  type: project
---

2026-10-26, Kent's ruling "Gate to MFab art first (Recommended)": the recipe goes
default only on MFab-type art; workers fix the defects so the rest can follow.
Lane `diagonal-junction-letters-62899f`, branch `claude/underfill-knockouts`.
`silhouette_underfill.plan` (`COVERED_KEEP_MIN`, `LETTER_HOST_INSET_W`),
`apply_cfg` hands the outlines on with no riders too; tests
`tests/test_underfill_knockouts.py`. Numbers and crops: the PR body.

**Gaulke LC + beanie (the director's D2): not the under-fill.** It never
fires there (45 regions in, 45 out, no ring). `sew_enclosed_white` ALONE
reproduces the recipe's Gaulke LC DST byte for byte (a66ac9be): it moves the
white layer ahead of black, so black sews over the roof line and window
cross. That lives in `enclosed_white.py` -- someone else's lane. The pro
leaves those as open garment gaps.

**Fremont hat star.** A 0.22 mm2 white shape inside the black state, the
ground's colour, so it merged into the white under-fill -- under the state's
black fill. With the under-fill off it sews as a white run on top. Fix: a
host-colour shape that other-colour inner shapes cover >= half of is not
merged. MFab's letters sit in the white field's HOLES (covered 0.0): unchanged.

**Becker x5 white edge.** The host is a white LETTER; it filled the black
ring's outline to its edge. The lower band's art runs 2-4 mm past the loops
`border_from_outline` sews, so white rows showed there, and the EDGE CAP took
the white thread (a second white block, 187 st): that was the "thin white
run". Fix: with the ring's art-outline bodies, the letter host fills no
further than union(hole.buffer(w)) pulled in by 0.5 w at the OUTER edge.
**Trap:** cutting at hole.buffer(0.5 w) instead split the fill at every bar
between letters (trims 6 -> 19); erode the loops' union, don't buffer holes.

**Proof:** Becker hat large (recipe) 17,032 -> 16,879 st, 25 trims, white > 2
mm from the letters 565 -> 3 mm, cap back in the band's thread; Fremont hat
+19 st, +1 trim, star back on top; MFab hat/LC and Gaulke LC plans identical.
