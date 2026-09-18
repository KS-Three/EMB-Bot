---
name: native-ramp-edge-read-2026-09-18
description: Low-res uploads sew staircases because stage 1 thresholds alpha and NEAREST-upscales the mask; the ramp is still in the file. `subpixel_edges_upscaled` reads it at the source's resolution (built OFF). Byte-identity is an expression, not a value.
metadata:
  type: project
---

# The staircase on low-resolution uploads, and the read that removes it (2026-09-18)

Kent asked for better outlining of "non-standard shapes" and crisp lettering.
Rendered beside its artwork, the real logo whose outline disagrees at arm's
length is the low-resolution one: `becker_marine_logo.png` is 146 px wide,
its shape entirely in ALPHA (RGB black everywhere), 1.46 px/mm at 100 mm, and
every outline and MARINE letter sews a staircase of 0.68 mm steps.

**Mechanism (`stage1_prep`):** `alpha < 128` makes the background mask, a
NEAREST resize carries it to the 4.0 px/mm floor as whole source pixels, and
`stage4_vectorize` declines `subpixel_edges` on any upscaled source because
the Lanczos ramp in `rgb` is manufactured. The alpha carries 256 levels, 17%
of pixels mid-ramp: the edge was locatable to a fraction of a source pixel
all along, and stage 1 threw it away.

**Built (PR #515): `cfg.subpixel_edges_upscaled`, DEFAULT OFF.** `Prep`
keeps `native_rgb` / `native_alpha` / `upscale`; stage 4 maps each vertex
down by cv2's half-pixel-centre rule, reads the source's pixels (Lab over
white by alpha + alpha as a fourth channel), chords scaled by the upscale,
maps back. `subpixel._fit_corners` places every flagged corner where the
lines fitted through its two sides' accepted vertices meet. Synthetic disc
radial RMS 0.25 → 0.013 mm; ladder 200 rung rectangles' Hausdorff 0.26/0.34
→ 0.03/0.04 at four vertices; 400 rung byte-identical. Scope-history entry
of the day has the tables; renders in `docs/renders/native-ramp-2026-09-18/`.

**The trade-off, which is why it shipped OFF:** the polygon is right by every
instrument, and Becker at 100 mm then flips its 1021 mm² outline band FILL →
SATIN (DT p90 drops under the 5.0 cap once the staircase goes) into the satin
decomposition defect: uncovered 0 → 35 mm², visibly worse at arm's length.
`satin_polygon_axis` on top does not rescue it. This is the classifier cliff
(`classifier-cliff-is-input-resolution-2026-09-16.md`) seen from the other
side. The flip is Kent's.

## Traps — each cost real time

- **"Byte-identical" is an EXPRESSION, not a value.** Replacing
  `hypot(hypot(a, b), c)` with `np.linalg.norm` changed the last float32 ulp
  on a quarter of vectors and moved one drone vertex by 3.2e-6 mm with the
  flag OFF. Rounded goldens (4 dp) cannot see it; the reviewer's exact A/B
  (`git archive` of base, WKB + hex floats) can. When touching a shared
  expression on the default path, run that A/B, not the goldens.
- **The corner profile read is biased on anti-aliased art**, and it does not
  say so: the profile through a corner pixel samples the OTHER edge's ramp,
  so it either refuses the corner (bevel) or ACCEPTS it 0.35–0.77 px short.
  The ladder's rectangles never showed it because their edges sit on pixel
  boundaries. Fit the sides, intersect the lines. The reach cap is 1.5·√2 px
  (1.5 refused every corner: a quantiser-eroded corner pixel puts the trace
  a whole pixel in on both axes past the half it already sits in).
- **`abs(da @ db)` is symmetric about a right angle.** A turn test on it
  refuses every apex past 120° — A, V, M, N, star points — which is the
  lettering the flag was built for. Orient along travel, drop the abs.
- **cv2 has two resize conventions**: half-pixel centres for Lanczos/area,
  floor for NEAREST — the masks sit +0.5 upscaled px off the centre rule —
  and the per-axis factor is `new_size / (w, h)`, not `want`.
- **Alpha cutouts hide the ramp in alpha.** `mid-tone fraction` of the RGB
  read 0.000 on Becker; the alpha read 0.169. Check both before saying a
  source has no anti-aliasing.
