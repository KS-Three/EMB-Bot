---
name: lettering-10mm-up-band-2026-10-23
description: The 10 mm and up lettering band against the pro — only MARINE is sewn in full on both sides; the pro crosses every stroke square to the LINE OF TEXT (diagonals included) and the Column lane did not; `lettering_columns_text_lean` built OFF. BECKER faces and MFab's keyline are white and unsewn (sew_enclosed_white's); the "fill + border above the ceiling" reading is a KEYLINE rule
metadata:
  type: project
---

Doc `docs/lettering-10mm-up-2026-10-23.md`, renders
`docs/renders/lettering-10mm-up-2026-10-23/`, flag `cfg.lettering_columns_text_lean`
(`digitizer_core/column_lean.py`, `tests/test_column_text_lean.py`).

**Band jobs at the pro's widths:** Becker MARINE 12.8-17.1 mm on four
garments (whole satin 4.0-5.2 in his files), BECKER 18-34 mm (fill under
the art's 2.4 mm outline), MFAB 17-18 mm (black fill under a 2.0 mm WHITE
satin keyline), Tires' 3D script (4.3-4.6 mm satin at 0.14 pitch), Bridge's
11 mm script (fill under a 1.5 mm border). Gaulke, Fremont, Drone, Proseal
have nothing over 10 mm.

**Only MARINE compares construction on today's engine.** BECKER's faces
are WHITE in the art and MFab's letters are black-on-black drawn by a
0.7 mm white keyline: both sew nothing today (`sew_enclosed_white`, #1031,
the `white-like-pro` lane), so our MFAB satin columns are thread the pro
never sews. **The border memo's "stroke over the ceiling -> fill + border"
is wrong on the skeleton measure**: MFAB strokes 4.3-5.2, MARINE large
4.2-5.3, the same, and he satins MARINE whole. His bordered letters all
carry an outline/keyline in the ART and the border IS it, widened to
2.0-2.5 mm. Bridge's bare script is the one stroke-only case.

**MARINE, 24 letters:** the pro cuts MORE pieces (163 columns to our 77,
324 butts to 108) and fans more ends -- the 5-10 mm band's instruments
call ours cleaner. What the eye sees: he sews every stroke with the
stems' cross, square to the line of text, diagonals included (N, A's
legs, M's V); the Column lane stations each piece square to its own
axis, so our diagonals are a second sheen and the M's V a tangle. That is
Kent's 2026-09-03 convention (`_clamp_to_span`, 30 deg cap, spacing/cos)
which the lane never carried. Built OFF, ON-eligible (layout): Becker hat
small N lean 7.2 -> 5.2 (pro 5.6), A 14.8 -> 4.6, M fans 6/10 -> 2/8,
design 5,928 -> 5,866 st; OFF byte-identical on real art (md5). The M's V
still tangles (corner-folds lane); the A's left leg sews 9% less.

**Also measured, not built:** 2 penetrations on 91% of our 4.3-5.9 mm
crosses where he sews whole to 5.3 (`SPLIT_SATIN_ABOVE_MM` + the comb's
carry; gate 1); M-stem rail wobble 0.19-0.25 vs 0.03-0.05 (traced outline
of 0.52 mm/px art); trims 34 vs 16 (he jumps uncut); Tires' "ires" fills
(`wide_columns` OFF, gate 1).

**Traps:** `pro_fill_underlay` reads satin crosses as dense rows and
split-satin legs as 2.3 mm "fill stitches" -- fuse collinear legs before
any construction read; a leaned scan line must pass through the axis line
THROUGH THE PIECE (centroid offset), or a third of the stations fall off
one end (the first run lost half the A); `lettering_group` is a bool, so
group words by `text_cluster_id`; the pro's PES colours are the customer's
spec, not the art's.

**Why:** Kent's standing fine-lettering priority, one band at a time
against his pro's files. **How to apply:** judge the flip on the renders;
measure the next band's "white vs sewn" before construction.
Related: [[lettering-5-10mm-band-2026-10-23]], [[border-by-size-2026-10-23]],
[[stitch-angle-convention-2026-09-03]], [[lettering-architecture-2026-10-07]].
