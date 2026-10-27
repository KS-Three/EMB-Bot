---
name: outline-loop-pivot-2026-10-25
description: The keyline/outline loop's corner "spikes" are SPARSE far ends (1.1 mm apart vs the pro's 0.4), not a missing mitre -- the pro's corner on MFab's keyline is the same round arc ours is (far ends 1.00 W from the corner; a mitre would be 1.43). Built OFF, ON since Kent's flip 2026-10-26, as `outline_loop_mitre` (name from the brief): dense pivot, no corner detector. Becker's K/E corners the pro BUTTS square instead -- unbuilt.
metadata:
  type: project
---

2026-10-25, task 10 of the lettering wave, lane `diagonal-junction-letters-62899f`,
branch `claude/outline-corner-mitre`. Flag `cfg.outline_loop_mitre` (OFF),
`stage6_border._pivot_ring` + `loop_mitre_scope` (wired in
`pipeline.plan_stitches` beside `apex_cut_scope`), reader `tools/loop_corners.py`,
tests `tests/test_outline_loop_mitre.py`. Numbers and crops: the PR body and
`docs/renders/outline-loop-mitre-2026-10-25/`.

**Premise half false.** The brief said the pro MITRES where our far rail fans
into spikes. Measured on clean convex corners (turn >= 70, a straight edge of
one loop width each side; letter faces snapped onto the pro's near rail):
his far ends stand 1.00 W from the corner on MFab LC's white keyline (n=12)
and 1.12 W on Becker large's outline satin (n=5) -- a round pivot, where a
mitre point is 1.43 / 1.55 W. Ours OFF is the same arc (0.95 / 1.16). What
differs is DENSITY: far-rail pitch through the corner 0.43 / 0.40 mm for him,
1.10 / 1.16 for us; corners with a step over 0.8 mm 13 of 15 / 6 of 6.

**Why the first build failed.** A mitre with a corner detector (turn >= 50
over half a width) fired on traced notches (Becker K's corner step) and put
crosses 2 W long through MFab's inner V -- worse than OFF. Don't rebuild it:
`_pivot_ring` needs no detector -- wherever two neighbouring crosses' far ends
part by more than 2 steps on a convex turn (far step along the near step), it
inserts crosses between them, near end interpolated on the outline, direction
interpolated, about one per step of the far rail; `_short_stitch_guard` then
pulls the near rail's pile too (every other cross short). Concave corners and
curves of radius above ~5 mm at 2.4 W are untouched.

**Result.** Pitch 0.38 / 0.41; fans 6/15, 3/6 (pro 5/12, 3/5). Keyline
stitches 4,257 -> 5,311 (pro 5,360); Becker large outline 4,169 -> 4,814 (pro
4,095), small 2,898 -> 3,398. OFF byte-identical to main on all three
(border_from_outline ON). Kent's flip; layout, judged in the preview.

**ON since 2026-10-26** (Kent, wave-3 flip sheet: "Outline corners pivot";
`PRE_FLIP` names the OFF arm). Sheet: Becker hat large 7,859/19 -> 8,556/18,
small 5,162/17 -> 5,659/17; Bridge byte-identical.

**Open.** Becker's K top-left and E corners: the pro runs one column straight
past the corner and stops the other square under it (a butt) -- neither a
pivot nor a mitre point; n too small for a rule. The touching letters' shared
column (MFab's M foot, the chaos both arms keep there) is the next gap, not
this one.
