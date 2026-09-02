---
name: hotel-fremont-fine-details-2026-09-02
description: Kent's five Hotel Fremont notes traced — the E/L/T "weight" complaints are the hanging-serif corner fan AND the house angle silently not firing on slab-serif lettering (doubled-angle Rayleigh cancels orthogonal families); fixed with a resampled four-fold reading and the 45° bisector; O = DP 0.2 mm 9-gon; in-fill = 570 mm of travel over finished rows, not the render
metadata:
  type: reference
---

Full record with every number: `docs/hotel-fremont-fine-details-2026-09-02.md`.
This entry is the decisions and the traps.

## What the five notes were

- **E heavy top/bottom, L heavy bottom, T left side drops** → one mechanism.
  A horizontal arm ending in a HANGING slab serif is walked as one L-shaped
  stroke (the serif at a stem's foot is a symmetric T-junction and becomes
  its own stroke, which is why stems were clean). `_split_sharp_corners`
  reads the smoothed turn under 90°, the six-pass angle smoothing in
  `_rail_points` then leans the crosses across most of a 4–5 mm arm and fans
  them at the corner. The withdrawn fixes stay withdrawn.
- **What cured it was the house angle** — the lever built 2026-08-27 — and it
  was NOT FIRING on this logo: nR² = 4.7 against 6.9. **A slab-serif word
  cancels itself in doubled-angle space** (112 mm vertical vs 44 mm
  horizontal skeleton; vertical votes at 180°, horizontal at 0°). The FOURTH
  instance of the threshold-on-the-wrong-population pattern in this one
  feature.
- **O not round** → `simplify_tol_mm` 0.2 turns the 2.4 mm-radius counter
  into a **9-gon, ±0.25 mm** (outer ring 16 verts, ±0.02). The counter is
  also its own cream fill region on that 9-gon. Kent's 2026-08-17 ruling
  predates a curve instrument; his call to re-open.
- **In-fill not clean** → NOT the render: the pro's tatami through the same
  `stitchviz` is smooth. Ours lays **39 travel runs, 570 mm**, each over
  columns already sewn (`tFtFtF…` sequence). Gate-clean sequencing work.
- **Wisconsin** → 15-vertex polygon, 14 fill rows at 45°, peninsula under
  `MIN_FILL_WIDTH_MM`. A scale + border question; Border was None.

## The fix that shipped, and the three traps inside it

Second reading in `_cluster_house_angle_deg`: when doubled space finds
nothing, quadrupled space, same Rayleigh test — two orthogonal families
reinforce there (Fremont R4 = 0.444, nR4² = 90). Before-admitted clusters
are byte-identical by construction (Becker, enthusiast md5-checked).

1. **Raw skeleton steps carry a four-fold GRAIN.** An 8-connected walk only
   steps in eight directions; that staircase cancels in doubled space (annuli
   R = 0.008) and dominates quadrupled space (annuli **0.160 at exactly
   45°**; four bars 45° apart, which cancel by construction, **0.527**).
   Resample at a 4 px chord: annuli 0.051, bars 0.127, real lettering
   0.44–0.90. Doubled votes stay raw so nothing already derived moves.
2. **Significance cannot reject a biased null.** The ~0.05 residual on a true
   circle becomes "significant" at 24 annuli (nR4² = 8.0). So the four-fold
   reading also demands an effect: `SATIN_HOUSE_FOURFOLD_MIN_R` = 0.25 —
   5× the residual, <0.6× the weakest real case. Test pins the margin.
3. **The bisector, not the stems' perpendicular — and there are TWO
   bisectors.** House = 0° (the Becker answer) SCRAMBLES every horizontal:
   90° off the house is past `SATIN_HOUSE_MIN_SPAN_DEG`, `_clamp_to_span`
   flips ±45 on tangent noise, smoothing sweeps the bar through 90° between
   flips — worse than no house angle. 45° sits at the span limit for both
   families: nothing clamps, nothing flips, no corner fan. Then the axis is
   only defined mod 90, so "axis + 45" gave drone 45.1 and Fremont 134.4 —
   mirror slants on the same upright text. `_bisector_deg` takes the one
   nearer the convention.

**Measured on drone_render:** the four regions that gained an angle are
**T, H, E, R of THERMAL** — the letters Kent called "not clean" on
2026-08-26, whose deformed H no instrument could see. Rendered: coherent 45°
on all four. +0.4% stitches, trims flat.

## Fixtures that lie

Buffered square and hexagonal RINGS are degenerate under `_skeleton_chains_mm`:
a 10 mm ring survives spur pruning as **2.5–3.5 mm of corner-arc remnant** per
ring, so any direction read on them is a handful of votes at 45°. The
doctrine's "3 square rings R = 0.167" was measured on that remnant. Circular
annuli are fine (closed 38 mm chain). Do not build a direction claim on ring
fixtures; the test file now says so.

## What the pro actually does, and what our model cannot

The pro's MARINE sews EVERYTHING at one near-horizontal cross — the E's arms
and the A's bar become short wide columns of 3–4 mm stitches. Our rails are
perpendicular offsets of the medial axis at the half-width, so a cross along
a bar collapses to a 0.8 mm stitch on the centreline. "One angle, the pro's
way" is a new construction (sweep the bar's full extent along its
perpendicular), not a tuning — Kent's design call, listed in the doc.

See also [[letterform-fidelity-2026-08-26]], [[thresholds-on-the-wrong-population-2026-08-28]],
[[curve-fidelity-from-stitch-path-2026-08-27]], [[hotel-fremont-pro-parity-findings]].
