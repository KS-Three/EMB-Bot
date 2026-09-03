# Round curves — defect 22, built OFF for Kent's flip; and the fill-dust defect found under it, FIXED (2026-09-03)

Kent's note 4 on the Hotel Fremont screenshot: *"This 'O' is not round."*
Traced 2026-09-02 (`docs/hotel-fremont-fine-details-2026-09-02.md` note 4):
`simplify_tol_mm` is a maximum DEVIATION, and 0.2 mm on the O's 2.4 mm-radius
counter is a **9-gon** whose 47° corners the eye reads even though no vertex
is more than a quarter-thread off the arc. Kent picked this next after the
corner join. The two standing rulings stay as they are — `simplify_tol_mm`
holds at 0.2 (2026-08-17) and size-proportional scaling is closed (08-07);
this is a second knob, not a re-tuning of the first.

## What was built — `PipelineConfig.curve_turn_deg` (default None)

Stage 4 traces every mask with OpenCV and simplifies it with Douglas-Peucker
at `simplify_tol_mm`. With `curve_turn_deg` set, `_refine_curves` re-reads
every simplified edge against the raw contour arc it replaced and splits it
at the arc's **midpoint** until the chord's sagitta is under
min(`simplify_tol_mm`, chord × turn / 8) — the small-angle sagitta of an arc
that turns `turn` degrees at one vertex — floored at **one raster pixel**,
the staircase's own amplitude. An inserted vertex is the mean of the raw
contour points within two pixels of the midpoint, a sub-pixel estimate of
the curve instead of one staircase pixel. Straight edges never split (their
sagitta is the staircase, under the floor), so a rectangle stays a
rectangle; only arcs gain vertices. Sub-detail shapes (the rescued small
lettering, already at a 0.5 px tolerance) are untouched.

Why the midpoint and not the max-deviation point: splitting where the
deviation is largest — Douglas-Peucker's own rule — re-picks staircase
corners once the tolerance is near a pixel, and every prototype that did so
came back with 90° vertex turns on a raster circle. Splitting at the arc's
midpoint and averaging a two-pixel window is what makes the polygon follow
the curve rather than the pixels.

Not a physical constant: no fabric quantity moves; the floor and the window
are raster quantities like `SATIN_HOUSE_CHORD_PX`. Not a re-calibration of
stage 0. Not the smoothing DOCTRINE rules out — nothing is blurred; the
polygon is re-read from the same raster where it curved.

## Measured

**Fremont's O with the flag at 15°** (`scratchpad` probe; 31 px/mm):

| ring | vertices | max turn at a vertex | radial dev. from a fitted circle |
|---|---|---|---|
| counter (own fill region) | 9 → **29** | 48° → **21°** | −0.038/+0.022 → −0.047/+0.039 |
| O outer ring | 16 → 30 | 24° → 17° | |
| O inner ring | 9 → **33** | 47° → **17°** | |
| sewn inner rail | 43 stations | | σ **0.038 → 0.026 mm**, range 0.174 → 0.121 |

The counter's area goes 15.8 → 17.1 mm²: the 9-gon's chords cut inside the
arc, and the true counter is the bigger one.

**Synthetic circles** (the prototype ladder, vertices before → after at
15°, p95 vertex turn after): at 31 px/mm R 2.4 mm 8 → 88 (18°), R 3 16 → 52
(26°), R 13 32 → 32 (12°); at 8–10 px/mm R 2.4 12 → 16–24 (26–31°) — the
pixel floor governs and a 2.4 mm arc cannot be read finer than that from
such a raster. Becker at 4 px/mm is byte-identical with the flag on: the
floor (0.25 mm) is above the tolerance.

**Fixtures, flag on vs off**, with the fill-dust splitter masked (see
below) so the numbers are the flag's alone:

| fixture | stitches | trims | polygon vertices | `curve_fidelity` roughness |
|---|---|---|---|---|
| `logo_whitebg` | 1982 → 1966 | 6 → 6 | 113 → 142 | 1.61 → 1.61 |
| `logo_alpha` | 1968 → 1964 | 6 → 6 | 116 → 140 | 0.48 → 0.48 |
| `ribbon_curve` | 1001 → 989 | 1 → 1 | 37 → 39 | 9.45 → **8.72** |
| `becker_marine` | 4421 → 4421 | 28 → 28 | 1324 → 1324 | 12.60 → 12.60 |
| `logo_hotel_fremont` | 5789 → 5795 | 52 → **45** | 762 → 1631 | 4.09 → 4.14 |
| `drone_render` | 8670 → 8753 | 93 → 95 | 1318 → 2101 | 9.32 → 9.11 |
| `enthusiast_logo` @ 93 | 2959 → 2900 | 25 → **19** | 599 → 652 | 10.59 → 11.42 |

Digitize time unchanged. `curve_fidelity`'s `roughness_deg` reads the SEWN
path's local turn irregularity; it moves little because satin rails and fill
rows already smooth the polygon, and ENTHUSIAST's rise is the ±half-pixel
jitter the inserted vertices carry at 11 px/mm on small letters — the
resolution limit named above, the reason the flag is a call and not a
default. Off is md5-identical on whitebg, alpha, ribbon_curve and Fremont.

## Found under it — fill stitches halved by float dust (defect 25)

The first measurement said Fremont's fill field lost **13%** of its
stitches with the flag on, at the same area and the same row angle. It was
not the flag. `stage6_fill.emit` runs every fill path through
`stitches.split_long_moves(path, stitch_mm)`, which splits any step LONGER
than `stitch_mm`; the row grid is laid at exactly 3.0 mm in the row frame,
and after rotation back to design space a step measures 3.0000000000000004
as often as 2.9999999999999996. The former is split into two 1.5 mm
stitches. Which rows get it depends on the row angle's cosine, so any
change to a shape's polygon re-rolls the dice — the ±10% stitch-count noise
on fill-heavy fixtures, and every one of those half stitches is a needle
penetration the design did not want. Measured with `tools/fill_dust.py`
(committed; `dust` = steps over the threshold by under a micron):

| fixture | fill/travel steps | dust splits | share of the design's stitches |
|---|---|---|---|
| `logo_whitebg` | 1520 | 180 | **8.3%** |
| `logo_alpha` | 1511 | 104 | 5.0% |
| `becker_marine` | 461 | 58 | 1.3% |
| `logo_hotel_fremont` | 2450 | **576** | **9.0%** |
| `drone_render` | 3058 | 59 | 0.7% |
| `photo_sunset_backlit` | 7102 | **1198** | **10.3%** |
| `ribbon_curve`, `enthusiast_logo` | | 0 | 0 |

The fix is one comparison — split only when the step exceeds `stitch_mm`
by more than a micron — and it moves every fill golden, which is why it is
recorded here and not shipped in the same PR as an OFF flag. The flip of
`curve_turn_deg` moves the same goldens, so the two belong in one re-pin
round.

## Review (emb-bot-reviewer), applied before the PR left draft

- **The flip's blocker, Kent's call.** With the flag at 15°, two of Fremont's
  25 shapes change tier: the 2.6 mm letters of the small line
  (`S54b55cf1`, 2.5 × 2.6 mm) go satin → fill, and their neighbour loses a
  stroke. Mechanism: Douglas-Peucker at 0.2 mm was INFLATING those letters
  by 14% (Hausdorff to the raw contour 5.75 px; the refined polygon is at
  1.14 px), and the honest polygon's ribbon width drops 0.468 → 0.381 mm —
  under `SATIN_MIN_CROSS_MM` (0.5) once the rails sit symmetric — so
  `satin_stroke` drops every cross, `satin_shape` reports empty and stage 7
  falls through to fill. The hairline population defect 24 already names;
  the refinement removes the inflation that was masking it. A design-level
  stitch delta cannot see a per-shape tier flip; the flip's evidence must
  include a per-shape `kind` diff on every fixture. Whether to scope the
  refinement out of near-floor lettering (skip shapes whose ribbon width
  is within ~20% of the minimum cross) or to route those letters to a run
  tier is Kent's decision, not a default to pick here.
- **Vertex mapping fixed.** The DP-vertex → raw-index map was a nearest-point
  search taking the FIRST occurrence; a `CHAIN_APPROX_NONE` contour visits a
  one-pixel-wide neck or serif twice with identical coordinates, so return-
  leg vertices were sent to their outbound twins and re-sorted (a two-blob
  fixture with a 1 px neck re-routed its ring; the sagitta bound re-split
  every orphaned arc so the geometry survived by luck). Now a lockstep walk
  of both rings, monotone and unwrapped, refusing the refinement when a
  vertex is not on the raw ring; it also removes the O(V × n) term.
- **The angle term is inert at the O's radius** — every chord under ~30 px
  is bounded by the one-pixel floor, so 5, 10 and 15° read the same polygon
  at r = 75 px; the `chord × turn/8` term first governs around r ≈ 300 px
  (15° → 32 vertices at 12.7°, 30° → 20 at 22.8°). A test at that radius
  now pins it. The config comment's resolution claims were overstated and
  are corrected: a 2.4 mm disc at 6 px/mm does not change at all, at
  8–12 px/mm reads a 12-gon with 35° corners either way, and only at
  31 px/mm reads 36 vertices at 15° — Fremont is the best case, a
  600–1200 px logo at 80 mm sits at 7.5–15 px/mm.
- **Recorded in the flag's favour:** DP's 0.2 mm 8-gon under-covers a
  2.4 mm disc's area by 10% (16.28 vs 18.10 mm²); refined it is within
  1.5%. On Fremont both O counters gain ~8% area and the rings lose it.
- Non-positive values mean off; `_CURVE_WINDOW_STEPS` is a step count, not
  pixels; the dead variable is gone. Cost measured: Fremont 0.05 s over 55
  calls, sunset 0.18 s over 28, against a 56 s pipeline.

## Kent's rulings, and what shipped on them (same day)

1. **Fix the dust now, hold the curve flip.** `stitches.SPLIT_TOLERANCE_MM`
   (1e-6 mm): `split_long_moves` splits a step only when it exceeds the cap by
   more than a micron. A micron is far under any raster or machine quantum
   and above every measured artefact (excess 2e-15 to 4e-15 mm). Measured,
   whole designs:

   | fixture | stitches before → after | trims |
   |---|---|---|
   | `logo_whitebg` | 2162 → **1982** (−8.3%) | 6 → 6 |
   | `logo_alpha` | 2072 → **1968** (−5.0%) | 6 → 6 |
   | `becker_marine` | 4479 → 4421 (−1.3%) | 28 → 28 |
   | `logo_hotel_fremont` | 6365 → **5789** (−9.0%) | 52 → 52 |
   | `drone_render` | 8729 → 8670 (−0.7%) | 93 → 93 |
   | `photo_sunset_backlit` | 11614 → **10416** (−10.3%) | 42 → 42 |
   | `photo_dof_meadow` | 9667 → 9516 (−1.6%) | 35 → 35 |
   | `ribbon_curve`, `enthusiast_logo` @ 93 | unchanged (no dust) | |

   Not one row, angle, trim or region moves — the same rows sew with the
   stitch length they were laid at. Goldens re-pinned under the
   pre-change-tree discipline: `logo_whitebg` and `logo_alpha` flat-lane
   keys via `tools/recapture_flat_lane_key.py --pre-change-tree <main at
   e2aa965> --control ribbon_curve.png` (machine OK, control OK, every
   other key untouched); `test_pushcomp.GOLDEN_FLAG_OFF[whitebg,
   left_chest]` 2162 → 1982 (the pre-change tree reproduced the old tuple
   first); `towel` and `enthusiast` stay the platform reds. A unit test pins
   the dust step, the exact step and the genuinely long step.
2. **Near-floor lettering keeps today's polygon.** `_wide_enough_to_refine`:
   a shape whose ribbon width (2 × area / perimeter on the simplified shell)
   is within 20% of `SATIN_MIN_CROSS_MM` is not refined at either ring, so
   the 2.6 mm letters keep the inflated Douglas-Peucker polygon that has
   been sewing all along and stay satin. Built into the flag; the flag stays
   OFF until the flip round.

## Tests

`tests/test_run_tier.py`: None is byte-identical to Douglas-Peucker; a
2.4 mm-radius disc at 31 px/mm goes from ≤ 16 vertices to ≥ 3× as many with
no vertex turning more than 30° and every vertex within 1.5 px of the true
circle; a rotated rectangle keeps its four vertices; at r = 300 px 15°
reads more vertices and smaller turns than 30°; a two-disc shape with a
one-pixel neck keeps its simplified vertices in ring order and its area
within 5%.

## Not this

The shipped fixtures have no lowercase and no large smooth curve beyond
`ribbon_curve` (R ≈ 13 mm) and the O; a badge with concentric rings at
8–10 px/mm is where the pixel-floor jitter would first show, and none is in
`testdata/`. The rescued small lettering keeps its 0.5 px tolerance and its
staircase.

## Review follow-up (2026-09-03, after #328 merged) — the guard has to be per ring

The emb-bot-reviewer measured the shipped guard on Fremont under
`curve_turn_deg=15`: the two near-floor letters (`S54b55cf1` 0.47 mm,
`S9bac9a3c` 0.39 mm) were correctly skipped — their own polygons byte-identical
OFF vs ON — and they **still fell to fill** (24 → 0 satin penetrations on
the first, on the pre-change tree; 28 at HEAD after the rail fix added two
crosses). The letters are also HOLES of the background region they sit in
(`S78e6cd01`, 22 holes); the shell-only guard refined those holes, and
stage 5's overlap resolution reshapes a letter against its background's
hole. Forcing the guard off everywhere restored satin, so the coupling is
the holes, not the letters' contours.

Fix (this branch): every ring is judged on its own —
`_wide_enough_to_refine` gates each hole as well as the shell, and an
invalid (bowtie) ring is repaired with `make_valid` before it is measured
rather than failing open. Re-measured on Fremont, ON vs OFF: `S54b55cf1`
28 → 28 satin penetrations, `S9bac9a3c` 16 → 16, shapes by tier identical
(19 satin, 5 fill), 5790 st, trims 52 → 45. Pinned by
`tests/test_run_tier.py::test_near_floor_holes_keep_their_polygon_while_the_shell_is_refined`
(a disc background with a 0.45 mm bar hole and a 1.3 mm disc hole: shell and
disc hole refined, bar hole byte-identical).

Still open from the review: a ring letter at the floor (an "O" whose shell
and counter are both wide while the ribbon between them is not) is measured
by its shell alone and would be refined; no fixture has one (Fremont's ring
shapes are 0.69–0.74 mm with their holes). A with-holes width would close it.
Also from the review: the dust test's 35° case measured exactly 3.0 on the
review machine and never entered the fixed branch — replaced with a
`math.nextafter` step (old engine 3 points, new 2) plus the two-cap case.

## The flip (2026-09-03, Kent's call after #329) — ON at 15°, where the tolerance has four pixels

Kent picked the flip once the per-ring guard was verified. The evidence the
#327 review asked for — a per-shape tier diff on every fixture — is
`tools/curve_tiers.py` (shapes paired across the flag by id, then by
centroid, because shape ids are content-derived and move with the polygon).
Run ungated first, at the 1 px floor, on every fixture:

| fixture | px/mm | stitches | trims | vertices | roughness | tier changes |
|---|---|---|---|---|---|---|
| Fremont | 31 | 5795 → 5790 | 52 → **45** | 762 → 1501 | 3.19 → **2.91** | none |
| drone | 19 | 8666 → 8781 | 93 → 96 | 1318 → 2044 | 7.51 → 7.36 | **1**: a 12 × 3 mm ribbon satin → fill |
| gaulke | 16 | 3867 → 3950 | 26 → 20 | 1076 → 1521 | 8.90 → 9.10 | none |
| ENTHUSIAST @ 93 | 15 | 2955 → 2898 | 25 → 19 | 599 → 652 | 9.01 → 9.86 | none |
| whitebg / alpha / ribbon | 10 | −16 / −4 / −10 | same | +26 / +21 / +2 | same / same / 2.54 → 2.48 | none |
| sunset | 10 | 10416 → 10945 | 42 → 40 | 2441 → 4350 | 16.10 → 16.54 | none |
| meadow | 10 | 9514 → 9373 | 35 → 38 | 1479 → 2509 | 15.20 → 16.50 | **2**: a 2.4 mm blob fill → satin; a 0.9 mm² run shape gone |
| Becker | 4 | unchanged | | | | none |

Two things the design-level numbers could not have shown:

- **The tier changes are the DT classifier reading boundary detail.** The
  drone ribbon (12 × 3 mm, width 1.07 mm, aspect 12.7) is `dt_irregular`
  either way (cv 0.60) and lives on the promotion path; its `explained`
  (area / (skeleton length × width)) fell 0.83 → 0.70 because the 1-px
  thinning of the refined polygon grew 17% more skeleton — spurs off the
  new vertices — and 0.80 is the promotion floor. The meadow blob (2.4 mm
  wide, aspect 3.5, at the 3.0 aspect edge) crossed the regularity gate the
  other way (cv 0.53 → 0.48). Neither shape got a different artwork; the
  classifier's skeleton did.
- **Below ~16 px/mm the refinement traces raster texture, not arcs.** The
  sagitta floor is one pixel whatever the resolution; at 10 px/mm the
  tolerance is two pixels, so any bump over half the tolerance — antialiasing,
  JPEG, a scan's edge — earns a vertex, and the ±2-step mean does not smooth
  it away. Vertices +40–80% and roughness UP on every fixture at 10–16 px/mm;
  DOWN on Fremont (31) and drone (19).

**Floors do not fix it — they cost the O.** `_CURVE_FLOOR_PX` swept on
Fremont's O: 1 px → counter 33 vertices / 17° turns; 2 px → 17 / 27°;
3 px → 16 / 27°. Half the O's gain lives under two pixels at 31 px/mm.

**The gate: `_CURVE_MIN_EPS_PX` = 4.** The refinement runs only where the
tolerance is at least four pixels (20 px/mm at 0.2 mm) — the line the
fixtures draw between reading arcs and reading texture. A raster quantity,
not a physical one; below it the default is byte-identical to
Douglas-Peucker, pinned by
`tests/test_run_tier.py::test_curve_refinement_needs_four_pixels_of_tolerance`.
Of the fixtures only Fremont (31 px/mm) is over the line; a phone scan or a
print-resolution logo is, a 600–1200 px web logo at 80 mm is not.

GATED_TABLE

Tests: `test_curve_turn_deg_is_on_by_default` (a fresh config refines the
2.4 mm disc at 31 px/mm), `test_curve_turn_deg_off_is_byte_identical_to_
douglas_peucker` (None, 0 and a negative all give plain DP), the four-pixel
gate above; the simplify-tolerance invariance test now isolates the flag
(with it on, the realized deviation drops UNDER the tolerance — 0.13 mm at
8 px/mm — which is the flag doing its job, not the tolerance moving).

