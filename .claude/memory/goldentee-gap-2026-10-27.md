---
name: goldentee-gap-2026-10-27
description: Golden Tee hat's +95% stitches is mostly the pro SIMPLIFYING the art -- 39% is two layers he never sews (GOLF's silver extrusion, the GT's red inner stroke); the white faces are 22%, their extra a border_by_size ring on the G; Kent ruled no build
metadata:
  type: project
---

**KENT'S RULING, 2026-10-27 (relayed by the director), verbatim: "Record it, no build (Recommended)".**
The numbers are `docs/goldentee-gap-2026-10-27.md`, measured on main `8341d1f7`. The DST is the
pro baseline's (#1141, md5 `a45b0763`): 11,629 stitches and 26 trims, against the pro's 5,973 and 10.

**Where the +5,656 stitches are:**
- Silver +1,503 and Cardinal +676 = 39%. The pro sews neither layer: GOLF is one orange satin per letter.
- White +1,512, of which the faces are +1,243.
- Orange family +985, black +980.
- By area, GOLF is +2,887 (51%) and the GT +2,320.

**Trims, +16:**
- 6 cuts inside a piece where he has none: 3 fill sections in the faces, 3 satin splits.
- About 10 more between pieces: we sew 33 shapes in 6 threads, he sews 16 runs in 3.

**The faces:**
- His rule: ONE 22 deg tatami run per face, on a CROSS underlay, with no ring of its own.
- That holds on Becker too. "No edge run" does not: 4 pro fills walk one.
- Our G face takes a 640-stitch `border_by_size` ring. `border_from_outline` exempts a body only when
  ONE art shape loops it, and Golden Tee's ring is four shapes in four threads.
- That ring is the only one on a sewn white field across the 22 jobs (MFab hat's 128-stitch white ring
  is unchecked). Removing it is priced at -629 stitches, 0 trims.

**Measured negative:** `sew_enclosed_white_fields_fill` ON makes Golden Tee WORSE, 12,430 stitches and
30 trims.
- The faces keep their 92 and 12 deg rows (the 22 deg does not reach them; why was not traced).
- The ball crescent turns from satin into a 1,251-stitch fill.

**Sew-out card candidates (gate 1):**
- face fill stitch length: ours 1.97 mm against his 3.45 mm (`pro_measured_values`);
- the ball crescent's underlay: 355 underlay stitches under 344 satin; his whole band is 430.

**How to apply:**
- Do not re-open Golden Tee's gap as a white-face problem.
- Its lever is R15: drop layers the pro never sews. n = 2 artworks (Golden Tee, Drone), and Becker
  contradicts it (its black drop shadow is sewn). Kent has not asked for it.
- Before flipping `fields_fill` for everyone, price Golden Tee.

Related: [[white-faces-fill-2026-10-25]], [[tm-mark-golden-tee-2026-10-26]], [[border-census-2026-10-23]],
[[border-from-outline-2026-10-24]].
