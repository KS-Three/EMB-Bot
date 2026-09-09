# Sub-pixel, anti-alias-aware edges in stage 4 — plan

**Date:** 2026-09-08
**Status:** decision document; **PR 1 (the instrument) built 2026-09-08**,
engine untouched. Item 3 of `docs/quality-review-2026-09-08.md`, Kent's
pick.
**Instrument this plan proposes:** `tools/edge_truth_ladder.py` — built; its
baseline corrected the acceptance criterion in §5.

## 0. What already governs this — read before changing the plan

- **Smoothing region polygons is a measured negative** (DOCTRINE):
  Douglas-Peucker already meets its 0.2 mm tolerance to 0.002 mm, the
  raggedness number on the owl was macro sprawl, and a smoothing radius
  would be a new gate-1 constant. This plan does not smooth a polygon; it
  changes where the polygon's vertices come from.
- **A sub-pixel refinement below a few pixels of tolerance reads raster
  texture as geometry, and the damage shows in the CLASSIFIER** (DOCTRINE
  gotcha, 2026-09-03): `curve_turn_deg`'s one-pixel floor at 10–16 px/mm
  read anti-aliasing and JPEG as arcs, every such fixture got rougher, and
  two borderline ribbons changed tier through the DT skeleton. The cure was
  `_CURVE_MIN_PX_PER_MM` = 20. **Rule from the same entry: any stage-4
  geometry change flips with a per-shape tier diff on every fixture,
  paired by centroid** (`tools/curve_tiers.py`).
- **`simplify_tol_mm` stays at 0.2** (ruling 2026-08-17) and
  size-proportional scaling is closed (2026-08-07). This plan moves neither.
- **Near-floor lettering is exempt per ring** from refinement (Kent,
  2026-09-03: the Douglas-Peucker inflation is what keeps 0.38–0.47 mm
  strokes above the cross floor). The exemption stays.
- **The satin/fill classifier's boundary-detail sensitivity is intrinsic to
  its thresholds** (eight cures measured, none adopted). This plan may
  REDUCE the raster grain that feeds it; it must not be sold as a cure for
  the thresholds.

## 1. The gap

`stage4_vectorize.vectorize` traces each label mask with OpenCV, simplifies
at 0.2 mm, and, since 2026-09-03, re-reads each simplified edge against the
raw contour arc — but only at 20 px/mm or above. Measured 2026-09-08
(`docs/quality-review-2026-09-08.md` §2a): **2 of 29 fixtures** reach that
gate at 80 mm. Every design Kent called jagged, sawtoothed or not smooth on
2026-08-27 — `logo_whitebg`, `ribbon_curve`, `becker_marine`,
`logo_script_tires`, `enthusiast_logo` — sits at 1.8–19.8 px/mm, so the
round-curves fix is byte-identical on the designs it was asked for.
`tools/edge_smoothness.py` reads 0.13–0.22 mm of raggedness on the corpus,
measured against the raster, which is itself the staircase.

## 2. Why the current refinement cannot go lower

`_refine_curves` estimates a sub-pixel point as the MEAN of the raw contour
pixels within two steps of an arc's midpoint. That averages staircase
corners, which is why its floor is one pixel: below it the staircase is
read as arcs. At 10 px/mm one pixel is 0.1 mm — half the tolerance — so
the gate refuses, correctly, and the polygon stays a polygon.

The information that locates an edge below a pixel is in the grey levels.
Every fixture in `testdata/` is drawn at 4× and downscaled with
`INTER_AREA` precisely so that "every edge carries a realistic 1–2 px
anti-alias halo" (`tools/make_test_logo.py`); real exports and photographs
carry the same ramp. Stage 4 never reads it — it reads the label mask,
which is the ramp thresholded at whatever the majority filter left. The
edge's true position inside that ramp is where the pixel colour is halfway
between the two sides, and that is readable to a small fraction of a pixel.

## 3. The design

`cfg.subpixel_edges`, default OFF, byte-identical off. One new step in
`vectorize`, between `findContours` (`CHAIN_APPROX_NONE`) and
Douglas-Peucker:

1. **For each raw contour vertex** `v` (a pixel centre) take the local
   normal `n` from its neighbours two steps either side.
2. **Sample the prepped image along `n`** at seven offsets from −1.5 to
   +1.5 px (bilinear), in Lab (`p.rgb`), or in alpha when `p.bg_from_alpha`
   and the outside is background.
3. **Project each sample onto the axis between the two side colours**: the
   inside colour is this label's cluster colour (`Quant.cluster_rgb`, or the
   local mean two pixels inside), the outside colour the neighbouring
   label's, or `Prep.bg_edge_rgb` against background. That gives `t(s)` in
   [0, 1] along the profile.
4. **Accept** when `t` is monotonic over the window and crosses 0.5 exactly
   once within ±0.75 px; the edge point is `v + s* · n`. **Reject** (keep the
   pixel centre) otherwise — JPEG ringing fails monotonicity, texture fails
   it, a third label meeting at the vertex fails the two-colour axis.
5. **Carry an `accepted` mask** with the sub-pixel contour. Douglas-Peucker
   runs on the sub-pixel coordinates at the same 0.2 mm; `_refine_curves`
   runs with its floor lowered from `_CURVE_FLOOR_PX` 1.0 to a sub-pixel
   floor (0.25 px) only on chords whose raw points were at least 80%
   accepted; and the `_CURVE_MIN_PX_PER_MM` gate is replaced by that
   acceptance test. Refinement then happens where the edge is actually
   known to sub-pixel precision, at any resolution, and stays off where it
   is not.

Holes get the same treatment. Sub-detail shapes keep their 0.5 px epsilon.
The near-floor lettering exemption stays per ring. The enclosed population
and the majority filter can move a LABEL by a pixel; the position now
comes from the image, so that wobble stops mattering.

**A stated limit:** a stroke under about three pixels wide has no plateau
between its two ramps, so the crossing is undefined and the vertex is kept
at the pixel centre. Those strokes are item 2's plan, not this one. Sources
under the resolution floor (Becker at 1.46 px/mm, Lanczos-upscaled to 4)
have a smooth ramp by construction; whether it locates the edge or the
upscale's own ringing is measured, not assumed (§5).

**Why not a tracer.** vtracer (MIT, evaluated 2026-08-17) fits splines to a
BINARY mask; it does not read the ramp either, and its Python wheel has an
untested keyword-argument crash on 3.14. It stays the fallback for sources
with no ramp to read.

**BUILT 2026-09-09 (PR 2) — `cfg.subpixel_edges`, `digitizer_core/subpixel.py`,
default OFF and byte-identical off; three things the construction above did
not say, each measured before it was written in:**

1. **The position is area conservation, not the 0.5 crossing.** The ramp an
   INTER_AREA downscale (or any renderer's coverage) leaves is piecewise
   linear with its knots half a pixel off the pixel centres, so the 0.5
   crossing of the linearly interpolated profile is biased by up to
   ±0.09 px, antisymmetric in the edge's sub-pixel phase. Integrating the
   inside fraction across the window instead is exact for a straight edge
   whatever the ramp's width or angle, and for any ramp symmetric about the
   edge: on a straight edge at four phases the integral errs −0.05 to
   +0.01 px against −0.10 to +0.09; on a disc rendered at 16x, 0.037 px of
   scatter and 0.014 of bias against 0.058 and 0.009. Acceptance still asks
   for a monotonic profile with one crossing, plus both plateaus inside the
   window (the integral's precondition). The 4x fixtures themselves are
   only good to an eighth of a pixel, which is why the unit test renders
   its disc at 16x.
2. **Two windows, and dropped rejects.** A label can sit a whole pixel off
   its edge (stage 2 hands a halo pixel to the darker cluster: the white
   disc enclosed by the whitebg ring traces 0.8–1.0 px inside its
   anti-alias edge and a ±1.5 px window refused 53% of its vertices), so a
   ±2.5 px pass runs where the ±1.5 one refuses; it needs five pixels of
   plateau either side and so admits nothing new on a stroke. And an
   8-connected trace's inner corner pixels sit a full pixel inside the
   edge, past any window: refused, each was an inward spike the simplifier
   kept (the 400 px circle's Hausdorff 0.18 → 0.24 mm), so a run of at most
   two rejected vertices between accepted ones is dropped before
   Douglas-Peucker — their position is unknown and their neighbours' is
   not.
3. **Corners are read along each side.** The one-dimensional ramp model
   fails where two sides meet inside the window: a right-angle corner pixel
   moved along its blended diagonal reaches 0.5 px of the 0.71 it needs,
   and every rectangle came out bevelled (the 800 px bar's Hausdorff 0.09 →
   0.18 mm, spread tripled, while the curves improved). A vertex whose side
   chords (±3 steps) turn ≥ 60° is read along each side's own normal and
   placed where the two offset side lines meet, capped at the narrow window
   along both sides (1.06 px — a one-pixel protrusion of the label turns
   like a corner and met its side lines 2.4 px outside the circle before
   the cap). Rectangles then land on their true corners: bar 0.119 →
   0.021 mm Hausdorff at 400 px, 0.089 → 0.004 at 800; purple's four
   vertices to 0.000 mm.

**What the 400 and 800 rungs show, whitebg, flat lane.** The ladder gained
vertex-only columns for this (`vertex_offset_mm`, `vertex_spread_mm`,
`vertex_max_mm`): the polygon's VERTICES land on the edge — circle vertex
spread 0.049 → 0.013 mm at 400 px (0.023 → 0.007 at 800), ring 0.061 →
0.014 (0.032 → 0.007), rectangles 0.00–0.01 — while the polygon's boundary
offset on the circle gets MORE negative (−0.045 → −0.067 mm at 400):
with its vertices on the edge the polygon is inscribed, and every chord
sags inward by the simplifier's tolerance, which the staircase's outer
corners used to mask. That is the floor §5 named and PR 3 is for; the
boundary spread still falls on the circle (0.057 → 0.048; 0.047 → 0.033)
and the ring's rises slightly for the same inscribed reason (0.085 → 0.097).
Reading the boundary offset alone here would call PR 2 a regression; the
vertex columns are the ones it is judged on.

**PR 3 BUILT the same day, same flag** — `_refine_curves(accepted=...)`: a
chord whose spanned raw points are at least 80% accepted is floored at
0.25 px instead of 1.0, its inserted vertex is the midpoint's own sub-pixel
point (the windowed mean is a staircase remedy and pulls a known point
inward on a curve), and the `_CURVE_MIN_PX_PER_MM` gate lifts when the flag
is on — chord by chord, the acceptance test replaces it. Where it bites is
where the plan did not quite say: the 15° turn rule, not the floor, decides
where splitting stops on a large radius (on the ladder's 14 mm circle the
one-pixel floor and the quarter-pixel floor end at the same chords), and
the floor governs on SMALL radii, where the 15° chord is under ~30 px and
its sagitta under a pixel — the ring's 7 mm hole went 40 → 70 vertices at
400 px, Hausdorff 0.285 → 0.140 mm, and at 800 the circle's boundary spread
fell 0.047 → 0.025 (PR 2 alone: 0.033) with its Hausdorff halved, the
ring's 0.070 → 0.044 with Hausdorff 0.218 → 0.094. The ribbon's spread
holds at the OFF 3200 rung's level (0.065–0.066 against 0.067) and its
roughness falls (7.97 → 5.86 at 400 px; 6.55 → 4.20 at 1600). Whether
every rung now clears §5's criterion is in scope-history's entry for the
day, with the full ladder and the tier diff.

## 4. What it should move — predictions, to be tested

- `tools/edge_smoothness.py` `ragged_mm` down on every fixture between 5
  and 20 px/mm, unchanged above.
- `tools/curve_fidelity.py` `roughness_deg` down on `logo_whitebg`,
  `ribbon_curve`, `logo_alpha`, `enthusiast`.
- `tools/ribbon_stability.py` flips 5 of 219 → fewer, because the raster
  grain that grows spurs on the classifier's skeleton is what leaves the
  polygon. Not a promise: DOCTRINE says the thresholds are the mechanism.
- `tools/curve_tiers.py`: a small number of tier changes on borderline
  ribbons, listed by centroid, each looked at.
- Stitch counts and trims move a little everywhere; nothing should move by
  a tenth.

## 5. Instrument first (PR 1) — `tools/edge_truth_ladder.py`

The synthetic fixtures carry their own vector truth: `make_test_logo.py`
draws a circle at (200, 250) with radius 120, a ring at (450, 250) radii
110/60, rectangles at known corners, a stroked polyline for the ribbon. The
ladder regenerates `logo_whitebg` and `ribbon_curve` at 200, 400, 800,
1600 and 3200 px, runs stages 1–4 at 80 mm, and measures each shape's
polygon against the analytic edge in the same frame — RMS and Hausdorff
deviation in mm, plus the vertex-turn statistics `curve_fidelity` reads —
with no registration search and no rasterised truth. Flag OFF today, the
deviation is bounded below by the staircase and falls with resolution;
flag ON, it should be close to flat across the ladder. That is the
acceptance criterion, and it is stated before any engine code exists.

The same tool runs `curve_tiers.py`'s cases on the real fixtures so the
per-shape tier diff the doctrine requires comes out of one command.

**BUILT 2026-09-08** — `digitizer/tools/edge_truth_ladder.py`, 10 tests,
baseline in scope-history's third 09-08 entry. The baseline corrects the
paragraph above in one place: **the deviation flag OFF is bounded below by
the pixel only up to about 15 px/mm; above that the floor is the 0.2 mm
Douglas-Peucker tolerance's chord sag, and it does not fall with
resolution.** The ribbon's polygon has the same 37 vertices and the same
0.06 mm spread at 400, 800 and 1600 px; the circle's inward offset plateaus
at the mean sag of a 34-chord polygon. So "close to flat across the ladder"
is already true OFF from 400 px up, and the criterion is restated:

- **Flag ON, every rung's spread at or under the OFF ladder's 3200 rung**
  (circle 0.023 mm, ring 0.031, ribbon 0.067), the 200 and 400 rungs
  falling toward it.
- **PR 2 alone (the profile crossing, same simplifier) is predicted to move
  only the 200 and 400 rungs.** The ribbon cannot move until PR 3 keys the
  refinement floor to acceptance, because the simplifier is its floor. If
  PR 2 moves the 1600 rung, something other than the construction did.
- The existing refinement, at the one rung its 20 px/mm gate admits (3200),
  halves the ring's spread (0.064 → 0.031) and takes the ribbon's from
  0.076 to 0.067; it leaves the circle untouched (its chords turn 10°,
  under the 15° asked). That is the reference the flip is measured against
  where both run: `--flag curve_turn_deg=0` is the OFF arm.
- The 200 px rung (Lanczos-upscaled ×1.9 to the floor) is a different
  regime — 19 regions instead of 7, rectangles 0.2–0.3 mm inside their
  edges, the dot not produced — and is §8's third decision's baseline.

## 6. What must not regress, with its fixture

| invariant | pinned by |
|---|---|
| flag OFF byte-identical | `test_flat_lane_byte_identical.py`, `test_photo_lane_byte_identical.py` |
| per-shape tier diff on every fixture, paired by centroid | `tools/curve_tiers.py` output in the PR body, every tier change named |
| near-floor lettering untouched | Fremont `S54b55cf1`'s 24 satin penetrations (the PR #328 review case) |
| sub-detail epsilon | `test_stages.py` rescued-lettering cases |
| the archetypes and the serrated disc | `tests/test_satin.py` |
| trim ceiling 4.1/1k | `tests/test_chaining.py` |
| JPEG art does not gain vertices from ringing | `logo_bridge_bar`, `logo_golden_tee`: vertex count and `ragged_mm` flag ON vs OFF |
| goldens | every fixture's polygons move ON; re-capture is Kent's approval, in CI, never on Windows |

## 7. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| 1 | **BUILT 2026-09-08** — the ladder, baseline numbers OFF, the criterion corrected (§5) | ~500 lines + 10 tests | none |
| 2 | **BUILT 2026-09-09** — `cfg.subpixel_edges`, OFF, byte-identical off: the area-integral edge position, two windows, dropped isolated rejects, corners read along each side (§3's BUILT note); the ladder's vertex-only columns; 13 tests. Vertices on the edge at every rung measured; the boundary offset is now the simplifier's sag, PR 3's | ~330 + 13 tests | none |
| 3 | **BUILT 2026-09-09** — `_refine_curves(accepted=...)`: 0.25 px floor on ≥80%-accepted chords, the midpoint's own point inserted, the 20 px/mm gate lifted ON; bites on small radii where the 15° rule wanted chords the pixel floor refused (§3's BUILT note) | ~40 + 3 tests | none |
| 4 | **FLIPPED 2026-09-09, Kent's approval** — `subpixel_edges` default True; the flat-lane goldens re-captured on ubuntu-latest by a temporary workflow that proves the runner on the pre-change engine first (`tools/recapture_flat_lane_key.py`), the pushcomp pins re-pinned the same way (`tools/pushcomp_pins.py`); ladder, tier diff and renders in scope-history's flip entry. `curve_turn_deg` stays 15°; upscaled sources stay declined — both carried forward as Kent's | docs + goldens | given |

## 8. Decisions for Kent

1. Approve the construction (read the ramp; never smooth the polygon).
2. Accept that the flip moves every golden, judged in CI.
3. Whether Becker-class sources (under the resolution floor, upscaled) are
   in scope for the flip or excluded until measured.
