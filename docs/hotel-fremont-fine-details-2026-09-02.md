# Hotel Fremont — Kent's five notes, each traced to a mechanism (2026-09-02)

Kent annotated a Studio screenshot of `testdata/photo/logo_hotel_fremont.webp`
digitized at 80 mm (flat-art override, 3 colours, satin on, fill angle auto,
border none) with five notes, and asked for *"the fine details of embroidery
digitizing, things that only a professional digitizer would be able to do."*
This file is the record of where each note comes from in the code, with the
numbers, and what was and was not changed. Everything below was measured on
`digitize()` + `plan.iter_runs()` directly, never on the Studio render, in a
fresh `python3.12` venv on the cloud container.

Kent's notes, verbatim from the screenshot:

1. *"The in-fill stitching doesn't look clean, not sure if it's the stitch out
   or the stitch rendering"*
2. *"This doesn't look like Wisconsin"*
3. *"The 'T' is not uniform, left side drops down"*
4. *"This 'O' is not round"*
5. *"The 'E' & 'L' are different weights or thicknesses through each letter
   (the E is heavy on top and bottom, L is heavy on bottom)"*

## The headline: notes 3 and 5 are ONE mechanism, and it was already half-built

**Every horizontal stroke that ends in a hanging slab serif is walked as a
single L-shaped stroke, and the cross-angle smoothing then leans the crosses
across most of the arm and fans them at the corner.** The stems are clean
because their serifs are symmetric T-junctions and become separate strokes.
Read the stroke decomposition (`extract_strokes`, 80 mm, half-width 0.37 mm):

| letter | stroke | length | free ends | what it is |
|---|---|---|---|---|
| E | 1 | 5.33 mm | both | left serif tip → bottom arm → **up the terminal slab** to y = 1.44 |
| E | 2 | 4.90 mm | both | left serif tip → top arm → **down the terminal slab** |
| L | 1 | 5.14 mm | both | left serif → foot → **up the terminal slab** |
| T | 0 | 6.36 mm | both | **down the left slab** → bar → **down the right slab** (a ⊓) |
| H | 2 | 3.58 mm | neither | crossbar, junction to junction — clean |
| H | 3–6 | 1.5 mm | both | the four serifs, each its own stroke — clean stems |

`_split_sharp_corners` does not cut these: the turn is read on a 3-pass
smoothed spine over a one-half-width baseline and comes in under
`_SPLIT_TURN_DEG` (90). The rail angles are then unwrapped and box-smoothed
six times (`_rail_points`), which spreads a 90° turn over roughly ±1.5 mm of
a 4–5 mm arm. That is the E's "heavy top and bottom", the L's "heavy bottom",
and the T's "left side drops down" — the long diagonal crosses at the corner
pull the visible weight toward the slab. **Withdrawn fixes still stand**
(`.claude/memory/letterform-fidelity-2026-08-26.md`): `_SPLIT_TURN_DEG` 90→70
reds a golden whose own rule says the change is wrong.

**What DOES fix it is the lever built on 2026-08-27 — and it was not firing.**
`set_lettering_house_angle` gives one cross angle to a line of lettering. On
this wordmark it found nothing: the twelve capitals read **R = 0.055 over
n_eff = 1554, nR² = 4.7 against the 6.9 bar** and were rejected. A slab-serif
face has 112 mm of vertical skeleton against 44 mm of horizontal, and in
doubled-angle space a vertical votes at 180° and a horizontal at 0° — they
cancel. This is the same mistake the memory records three times already: a
gate correct on the population it was tuned on (stems-dominated block caps —
Becker's MARINE at R = 0.197) applied to one it had never seen.

### The fix, and the trap beside it

Four-fold angle space sees exactly what doubled space cancels. Quadrupled, a
vertical and a horizontal both vote at 0°, so two orthogonal families
**reinforce**: Hotel Fremont reads **R4 = 0.444, nR4² = 90** on the same
votes. Shipped in `textcluster._cluster_house_angle_deg` as a SECOND reading,
tried only when the doubled reading found nothing — so every cluster admitted
before is admitted at the identical angle (Becker and enthusiast_logo:
byte-identical plans, md5-checked).

Three things had to be right, each measured:

- **The four-fold votes cannot come from raw skeleton pixel steps.** An
  8-connected walk steps only in the eight compass directions, and that
  staircase is four-fold symmetric — invisible in doubled space (24 annuli
  read R = 0.008) and dominant in quadrupled space (the same annuli read
  **R4 = 0.160 at exactly 45°**; four bars 45° apart, which cancel by
  construction, read **0.527**). Resampling each chain at a 4 px chord
  collapses the grain (annuli **0.051**, the four bars **0.127**) while real
  two-family lettering keeps its signal (Fremont **0.444**, its 2.6 mm "THE"
  **0.657**, six synthetic I-beams **0.903**). The doubled reading stays on
  raw steps, so nothing it derives moves.
- **Significance alone cannot reject the residual.** What resampling leaves on
  a true circle (~0.04–0.06) is small but systematic, so enough annuli make it
  "significant" — 24 of them: nR4² = 8.0 against 6.9. Under a biased null a
  significance test answers the wrong question, so the four-fold reading also
  demands an effect: **R4 ≥ 0.25**, five times the residual and under
  six-tenths of the weaker of the **two real wordmarks measured** (0.444 and
  0.657; the third case is synthetic). `test_the_four_fold_grain_stays_well_
  under_the_floor` pins the margin at a third of the floor. Read that
  honestly: it is a raw floor calibrated on two cases, in the module whose
  own history says raw floors fail on the next population — and the next
  population is nameable now: lettering rich in diagonals (A, V, W, X, K, M,
  N, Y, Z) votes at 180° in four-fold space and cancels the orthogonals, so
  a word like AVIATION can fail both readings and sew per-stroke. Nothing
  here has measured one. The principled replacement is a test against the
  measured biased null — `n_eff · max(0, R4 − grain)² ≥ critical`, grain
  pinned by the annuli test — which changes the gate's shape and is Kent's
  call (question 5 below).
- **Which angle: the bisector, NOT the perpendicular to the stems.** Rendered
  both. At house = 0° (horizontal crosses, the Becker answer) the stems are
  clean and **every horizontal element is scrambled**: a bar is 90° off the
  house, past `SATIN_HOUSE_MIN_SPAN_DEG` (45), so `_clamp_to_span` rotates it
  to ±45° with the SIGN decided by sub-degree tangent noise, and the
  smoothing pass then sweeps each bar's crosses through 90° between flips.
  Worse than no house angle at all. At exactly **45°** the cross sits at the
  span limit for both families and nothing is clamped or flipped. A derived
  bisector a degree or two off (Fremont's 42.8–44.4°) nudges the family it
  is further from back to the 45° limit — same sign, no flip — so the two
  families sew within ~2° of each other, with no corner fan. In the
  `stitchviz` render (n = 1, no cloth yet) the E's arms weigh the same as
  its stem and the T's left slab no longer drops.
  **And the bisector needs a convention, because there are two.** The family
  axis comes back mod 90, so "axis + 45" handed drone's THERMAL (axis 0.1°)
  45° and Hotel Fremont (axis 89.4°) 134° — mirror-image slants on the same
  upright lettering, decided by which side of the wrap the noise fell.
  `_bisector_deg` takes the one nearer `SATIN_HOUSE_BISECTOR_DEG` (45), so
  upright text always gets the same slant. 45 vs 135 is Kent's convention
  call; the constant is where to change it.

### Where it fires — the four fixtures measured first (six more below)

| fixture | before | after |
|---|---|---|
| `becker_marine_logo` | 11 angled, 4557 st, 28 trims | **byte-identical** |
| `enthusiast_logo` | 14 angled, 2382 st, 21 trims | **byte-identical** |
| `drone_render` | 17 angled, 9317 st, 86 trims | **21 angled** at 45.1°, 9355 st (+0.4%), 86 trims |
| `logo_hotel_fremont` | 0 angled, 6473 st, 47 trims | **15 angled** (12 capitals + "THE"), at 42.8–44.4° (two groups), 6493 st (+0.3%), 47 trims |

The four drone regions that gained an angle are **T, H, E, R of THERMAL** —
the letters Kent called *"not clean"* on 2026-08-26. Before, the E's stem sewed
a scramble of diagonals and the H's right stem tilted at both ends (the
"deformed H" the letterform memory could not measure); after, all four sew at
one 45° cross. Render pair in the PR body.

**What this does NOT do.** The pro's MARINE (decoded from
`testdata/reference/becker_hat_polo_large_beckers_logolc.dst`, rendered
through `stitchviz`) sews every stroke at one near-horizontal cross —
*including the E's arms and the A's crossbar*, which become short wide
columns of 3–4 mm stitches. Our rail model cannot do that: a cross is a
perpendicular offset of the medial axis at the stroke's half-width, so a
cross laid ALONG a bar is a 0.8 mm stitch on the centreline and the bar's
edges go bare. Sewing a horizontal as a wide short column is a different
construction (sweep the bar's full extent along its perpendicular), and it is
what a house angle of 0° actually needs to be correct. That is real
engineering and Kent's call on convention; the 45° bisector is what the
current model can deliver uniformly today.

## Note 4 — the O is not round: stage 4's 0.2 mm tolerance makes a 9-gon

Measured on the O of HOTEL (`Sa9ce03f2`, outer radius 3.06 mm):

| ring | vertices | radial deviation from a fitted circle |
|---|---|---|
| outer | 16 | −0.023 / +0.018 mm |
| **inner (the counter)** | **9** | **−0.238 / +0.267 mm** |
| outer rail as sewn | 43 stations | σ 0.029 mm |
| inner rail as sewn | 43 stations | σ 0.044, range 0.18 mm |

`simplify_tol_mm = 0.2` is a maximum deviation, and on a 2.4 mm radius it
buys a 9-gon whose CORNERS the eye reads even where the deviation is under a
thread width. The counter is also its own cream fill region (`Sdea02c23`),
sewn on that same 9-gon, which is the polygon visible in Kent's screenshot.
The rails smooth some of it (parallel offsets of a smoothed medial axis) and
lay thread outside the artwork doing so.

**Not changed.** `simplify_tol_mm` stays 0.2 by Kent's 2026-08-17 ruling, and
the "size-proportional" variant is a measured negative. But both were judged
when curve fidelity was unmeasurable — the raster instrument could not see it
(`docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`). This is a direct
geometric measurement on one shape, not a corpus claim. Two candidate
directions, both gate-clean (no fabric constant): a curve-aware tolerance
(tighter on arcs than on straights), or building satin rails against the
pre-simplification contour. Kent's decision — see the questions at the end.

## Note 2 — Wisconsin: a 15-vertex polygon, then 14 fill rows

`Sbf647133`, 5.9 × 6.2 mm, fill tier, 24.5 mm². Stage 4 emits 15 vertices:
the Door County peninsula survives as a 0.7 mm notch, the Lake Superior coast's
bumps and the white star are already gone (the star is under `min_detail_mm`).
Then the fill lays **~14 rows at 45°** across a 6 mm shape with a pentagonal
underlay, and the rows stop 0.7 mm short of the peninsula (under
`MIN_FILL_WIDTH_MM`). What sews is a blob with one tooth. At this size a
professional would carry the silhouette with a running or thin satin
**outline** and let the fill be filler; Kent set Border: None, and the
abruptness gate would refuse `significant` on a coastline anyway. Nothing
changed; it is a scale question and a border question, not a bug.

## Note 1 — the in-fill: it is the stitches, not the render

Control: the professional Becker file's tatami, rendered through the SAME
`stitchviz` at the same px/mm, reads smooth and even. Ours does not, and the
plan says why. The white field `S78e6cd01` (1693 mm², 22 holes) sews as:

| | runs | length |
|---|---|---|
| fill columns | 57 | 5406 mm |
| **travel (needle-down running stitch inside the field)** | **39** | **570 mm** |
| underlay | 11 | 435 mm |

The kind sequence is `…tFtFFtFtFtF…` — a travel run between almost every
pair of columns, and every one of them is laid **over columns already sewn**
(`_fill_paths` orders columns nearest-first, travel is emitted after). 570 mm
of cream running stitch on top of cream tatami is the diagonal lines across
Kent's screenshot, and on cloth a travel over finished fill sits proud of it.
A professional routes travel UNDER fill that has not been sewn yet, or along
an edge a border will cover. Separately, the 22 holes cut the rows into 57
columns whose ends align at each hole's x-extent — the vertical seams.

**Not changed** — sequencing work, gate-clean, and the same class as the two
task cards Kent approved on 2026-09-01 (borders-last, patch-quilt cleanup).
Sized here so it can be picked up: `_reorder_for_fewer_cuts` already knows
the column order; hiding travel means choosing the NEXT column so the bridge
crosses unsewn ground, or deferring it to a covered route.

## What a session should carry

- The `_lettering_groups` → Rayleigh gate is now two readings. When adding a
  third population (script? rotated? mixed case?), measure R2 and R4 on it
  BEFORE assuming either gate sees it — the tell is unchanged: a gate that
  should find lettering finding nothing on a logo that obviously has it.
- Four-fold votes MUST be resampled above the raster grain. `grain.py`-style
  tables for raw vs 3/4/6 px are in the tests' docstrings.
- The bisector is a convention with a wrap; never add 45 to an axis that is
  only defined mod 90.

## Open questions for Kent

1. **45 or 135?** Which slant a house-angle word should carry on upright block
   lettering. One constant.
2. **One-angle lettering the pro's way** — horizontals as wide short columns
   at the stems' perpendicular — is a new construction, not a tuning. Worth a
   design session, or is the 45° bisector the shipping answer?
3. **Re-open `simplify_tol_mm` for curves**, now that `tools/curve_fidelity.py`
   can measure it from the stitch path and the O gives a direct number.
4. **Fill travel under cover** — schedule it with the two sequencing cards.
5. **The four-fold effect floor's shape.** Keep `R4 ≥ 0.25` (a raw floor on
   two real cases) or replace it with the chance-corrected test against the
   measured grain. Either way, measure a diagonal-heavy word first.
