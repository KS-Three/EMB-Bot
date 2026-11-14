---
name: regular-structure-2026-11-13
description: "`regular_structure` built OFF 2026-11-13 (Bridge's wheel: handles 0.18 -> 0.006 mm apart); census of 11 designs: ONLY Bridge is stage-4 geometry, the rest of the 'make them alike' family is later stages (angle, tag, pull, text tagger)"
metadata:
  type: project
---

# Regular structure (`regular_structure`) — 2026-11-13

Kent on Bridge hat: "All of the wheel handles look different from eachother,
this would be better if they all looked the same." Worker under the
2026-11-13 Director, from his family of pins (flag stripes, Jakarta's dot grid,
pixel-art openings, emoji legs, mascot feet).

**The eye finding that shaped the build.** Bridge's rim and eight handles are
ONE black stage-4 region (`Sc050577e`, 467 mm2, source px 0.227 mm), so no
grouping of separate regions could see the handles. The module does both:
congruent groups of separate regions (rotation / row-grid lattice / mirrored
pair) AND self-symmetry of one region (8-fold + mirror here). Mean shape =
aligned signed-distance average (cv2 fill + distanceTransform; skimage's
fill took 13 s per copy, cv2 0.15 s).

**Census (stage 4, kit widths), numbers in the PR and in
`eye_pairs_out/regular-structure-1113/census/`:**
- Bridge: handles 0.31-1.15 src px off their mean, dilation only -0.17..+0.07
  px = trace noise -> GEOMETRY, fixed: pairwise 0.176 mm mean -> 0.006 mm.
- Flag: stripes agree to 0.015 mm, stars to 0.02 mm. Kent's widths come from
  pull ([[flag-stripes-seam-cap-2026-10-30]]). Stars sew at 8 different satin
  angles (36-160 deg): an ANGLE problem.
- toat_machine: 4 "=" dashes congruent, satin at 64/69/70/85 deg.
- Mascot feet: SAME thread 1120, not congruent (448 vs 412 mm2); "different
  colours" = fill direction lit. Emoji legs the same (147 vs 117 mm2).
- Pixel art: no repeats; "some openings bean, some not" = 5 openings tagged
  `enclosed_background`, 15 plain holes.
- Jakarta dot grid: equal at stage 4 but text-tagged (`small_text_*`); the
  lettering path merges it. Out of scope here.
- QR: three finder rings + cores at stage 4, congruent to 0.03 mm, but the
  rings are MISSING from the stitches (sewn under the white layer): Kent's
  "Entire black square and black border is missing" is a layering defect
  downstream, not geometry. Moving one ring 0.11 mm onto the lattice let a
  sliver peek out -- hence the floor below.
- Drone, Golden Tee: nothing worth moving.

**Gates (source px):** mean distance 1.5 (1.0 refused Bridge's worst handle,
1.15), dilation 0.5 (a size step is coherent, noise nets out: this is what
separates the two), worst point 4, move cap 3. Plus: nothing redrawn unless
some member moves more than max(0.1 mm Design unit, 1.5 src px) --
redrawing the flag's 0.005 mm stripes re-planned the long red satin 500 ->
1,399 stitches at a 5 deg tilt; a stacked layer is
not a seam (QR cores lie ON white squares); a self-repeat needs solidity <=
0.9 (the drone's 2 mm2 grey blob passed as a 3-fold triangle).

**OFF:** module never loads; md5 = main on emoji, mascot, pixel art.
**ON:** md5 = OFF on emoji, mascot, pixel, drone, Golden Tee (no repeats).

**For the next session:** `meta["congruent_group"]` (`id`, `kind`, `angle_deg`,
`mirror`, `moved`) is on every member of a confirmed group even when nothing
moved -- the table the group-consistency stage reads to pick one satin/fill
angle per group (angle relative to `angle_deg`). Not built: carrying a
member's new outline into the hole of the region it sits in (stars on a
canton keep a held seam).
