# Curve fidelity, read from the stitch path — 2026-08-27

The second of Kent's two smoothness complaints, and the one no instrument here
could answer. `tools/curve_fidelity.py` is the answer; this note is why it
exists, what it can and cannot say, and what it measured on its first run.

## The question

Reviewing fourteen stitch-outs on 2026-08-27 Kent raised smoothness on eight of
them. His notes hold two distinct faults, and he confirmed they matter about
equally:

* **Edge noise** — *"the edges around BECKER... they are jaged"*, *"it's
  sawtoothed and jaged"*. `tools/edge_smoothness.py` owns this.
* **Curve fidelity** — *"Lines/circles are not smooth like the photo"*. A curve
  sewn as a polygon. Nothing owned this.

`enginefidelity.py`'s docstring had already named the case in the abstract —
"a 20 mm circle RDP'd into a 20-gon and a faithful circle can score
identically" — without anything able to measure it.

## Why it needed a different input, not a different threshold

A turning-concentration measure was the obvious approach and was built first,
against a rasterised mask. It was **rejected on 2026-08-27** because it is not
even monotonic: a rasterised circle reads *more* angular than a 40-gon at every
resample step, since a raster boundary is itself a staircase of 45 and 90 degree
steps. The raster IS a polygon, and no resampling of it recovers the curve
underneath. That table is preserved in `edge_smoothness.py`'s docstring.

So the same measure was pointed at `plan.iter_runs()` — the vertices the machine
actually sews, floats in millimetres, no raster, no registration, no alignment
quantum. The idea was sound; the raster was the problem:

| step mm | circle | 60-gon | 40-gon | 20-gon | 12-gon | monotonic? |
|---|---|---|---|---|---|---|
| 0.5 | 0.0002 | 0.3612 | 0.5791 | 0.7933 | 0.8786 | **yes** |
| 1.0 | 0.0001 | 0.0015 | 0.1658 | 0.5793 | 0.7566 | **yes** |
| 2.0 | 0.0000 | 0.0015 | 0.0284 | 0.1639 | 0.4936 | **yes** |
| 3.0 | 0.0000 | 0.0015 | 0.0012 | 0.0002 | 0.2353 | no |

The 3.0 mm row is the instrument's physical floor, not a bug, and it is printed
rather than trimmed: a 20 mm 20-gon has 3.13 mm edges, so sampling every 3.0 mm
lands about one vertex per edge and every vertex turns alike — the polygon goes
invisible because the needle is as coarse as it is. **Arms must be compared at
one stitch length.** This ladder is an executable test
(`tests/test_curve_fidelity.py`), not a remembered number.

## Two numbers, because one is not enough

`turn_gini` alone would be a bad instrument. It asks whether turning is spread
evenly around the outline, which conflates polygonisation with a shape that
legitimately mixes straight sides and true arcs. A rounded rectangle — flat
sides, exact quarter-circle corners, nothing wrong with it — reads 0.656, about
what a 20-gon reads. Real logos are almost all mixed geometry, so on its own
this number would flag everything.

So the turning sequence is also read locally, as `roughness_deg`: a true curve
holds a near-constant turn per stitch whatever its radius, while a polygonised
one alternates flat-flat-flat-CORNER.

| shape | turn_gini | roughness_deg |
|---|---|---|
| circle | 0.0002 | 0.001 |
| rounded rect (genuinely smooth) | 0.6556 | 0.348 ← gini fooled |
| 20-gon | 0.7933 | 4.147 |
| 12-gon | 0.8786 | 4.008 |
| square (4 real corners) | refused | refused |

`turn_gini` ranks severity but is fooled by mixed geometry; `roughness_deg`
detects polygonisation regardless of mixed geometry but **saturates and then
reverses** (40-gon 4.28, 20-gon 4.15, 12-gon 4.01), so it cannot rank. They are
deliberately two views of one thing that fail differently — the same
construction as `edge_smoothness`'s `ragged_mm` / `perimeter_ratio` pair. A
design where they disagree is worth looking at rather than averaging.

Turns at or above `CORNER_DEG` (60) are intentional corners and are excluded.
That is what stops a square topping the ranking — and with its corners gone a
square has no curved vertex left, so it refuses rather than scoring. The
standing false positive is a many-pointed star, whose vertices sit below the
threshold and read as polygonisation.

## What it cannot do

**It cannot read intent.** A logo that IS a 20-gon and a circle polygonised to
one are the same path. Nothing here separates them, so the absolute number is
not a grade — it is a **paired** measure, read as a delta across arms over one
design, exactly as the 2026-08-17 tol ladder was.

**Sagitta was tried and cut.** The obvious physical alternative — millimetres of
bow between the sewn chord and the curve it samples, `s = (L/2)·tan(θ/4)`, exact
for a regular sampling — is not monotonic, because dense resampling makes a
polygon's straight edges look like a finely-sampled curve. It measures how
finely the path was sampled, not how faithfully it follows a curve. The table is
in `curve_fidelity.py`'s docstring so it is not rebuilt as the "obvious" fix.

## First real reading, and the trap in it

Re-running the 2026-08-17 `simplify_tol_mm` ladder — the lever that doc could
not measure at all, because every delta it saw sat an order of magnitude inside
the raster instrument's 0.35 mm floor:

| fixture | 0.2 gini / rough | 0.1 gini / rough | 0.05 gini / rough |
|---|---|---|---|
| `logo_whitebg` | 0.9559 / 1.613 | 0.9559 / 1.613 | 0.9559 / 1.613 |
| `ribbon_curve` | 0.5732 / 9.446 | 0.5881 / 8.832 | 0.5244 / 11.535 |
| `becker_marine_logo` | 0.5026 / 13.153 | 0.5865 / 11.034 | 0.5865 / 11.034 |

`logo_whitebg` does not move, and should not: stage 4 floors realized epsilon at
0.5 px, so its plan is byte-identical across all three arms — the same effect
that made 9 of 14 designs identical in the 2026-08-17 ladder. An instrument that
invented a delta there would be broken. This one reports zero.

**And `becker_marine_logo`'s apparent improvement is not clean.** Its trace
count goes 50 → 77 and its curve vertices 1991 → 2556 between 0.2 and 0.1: the
shape population itself changed, so part of that move is the denominator, not
the geometry. `ribbon_curve` does the same more quietly — its corner count
triples, 6 → 26, as finer RDP preserves sharper vertices that then fall out of
the measured set.

That is ROADMAP hard gate 4's failure mode wearing a different hat: the mix
moved, so a "gain" can be the floor shifting. `traces`, `curve_vertices` and
`corner_vertices` are reported on every row for exactly this reason — **read
them alongside every delta, and distrust any comparison where they moved.**

**No engine default changes on this table.** It demonstrates that the instrument
resolves a lever the raster could not, and nothing more. `simplify_tol_mm` stays
0.2 (Kent, 2026-08-17); re-opening it needs arms that hold the trace population
constant, and that is its own piece of work.

## The full fixture sweep, and what not to read into it

All fourteen `artfidelity_self` fixtures, sorted by `roughness_deg`:

| fixture | route | gini | rough | curve v | corner v | traces |
|---|---|---|---|---|---|---|
| `becker_marine_logo` | flat | 0.5026 | 13.153 | 1991 | 1029 | 50 |
| `logo_script_tires` | photo_scene | 0.5984 | 12.835 | 957 | 617 | 15 |
| `enthusiast_logo` | flat | 0.5264 | 11.479 | 898 | 653 | 49 |
| `logo_bridge_bar` | gradient | 0.5295 | 11.112 | 4137 | 1381 | 137 |
| `drone_render` | gradient | 0.5730 | 9.557 | 2336 | 901 | 107 |
| `ribbon_curve` | flat | 0.5732 | 9.446 | 462 | 6 | 2 |
| `logo_gaulke_roofing` | gradient | 0.7231 | 9.315 | 411 | 121 | 5 |
| `summit_badge` | gradient | 0.5604 | 8.977 | 1166 | 315 | 41 |
| `logo_golden_tee` | gradient | 0.5454 | 7.236 | 4032 | 788 | 98 |
| `logo_hotel_fremont` | gradient | 0.5751 | 5.460 | 2131 | 190 | 88 |
| `logo_whitebg` | flat | 0.9559 | 1.613 | 113 | 22 | 2 |
| `logo_alpha` | flat | 0.9455 | 0.485 | 110 | 25 | 2 |
| `bg_uncertain` | flat | — | — | 0 | 0 | 0 |
| `region_blobs` | gradient | — | — | 0 | 0 | 0 |

The two refusals are correct: neither design produces a single visible outline
run, so there is no curve to read and the instrument says so instead of
returning a number.

**One observation, deliberately stated as less than it looks.** The four
designs Kent described in edge-noise language — `becker` (*"jaged"*),
`logo_script_tires` (*"sawtoothed and jaged"*), `enthusiast_logo` (*"wavey and
not crisp"*), `logo_bridge_bar` (*"should be cleaner and more crisp"*) — are the
top four on `roughness_deg`. That is 4 of 4, and it is worth knowing.

It is **not** a validation, for three reasons, and none of them should be
skipped when quoting the table:

1. It is a post-hoc read of twelve designs, not a pre-registered test.
2. `roughness_deg` was built to detect POLYGONISATION, and might have been
   re-reading stitch-level edge noise instead — `edge_smoothness.ragged_mm`'s
   question, not this instrument's. **This has now been checked; see the next
   section. It is not edge noise.**
3. **The `turn_gini` column must not be ranked at all here.** `logo_whitebg` and
   `logo_alpha` top it at 0.95, on **2 traces and ~110 vertices each** — one
   satin column's two rails. A concentration statistic on a denominator that
   small is not comparable to a 137-trace design's. This is the "not a grade,
   a paired measure" limit showing up in practice on the very first corpus run.

## What the two numbers actually measure (checked, 2026-08-27)

Both instruments computed from ONE `digitize()` per design, over the same 12
measurable fixtures, so the comparison is exact rather than two separate runs.

### `roughness_deg` is not edge noise

| pair | Pearson | Spearman | 95% CI (Spearman) |
|---|---|---|---|
| `roughness_deg` vs `ragged_mm` | 0.153 | **0.028** | [−0.55, 0.59] |
| `turn_gini` vs `ragged_mm` | −0.021 | 0.028 | [−0.55, 0.59] |

The rankings are near-inverted at the ends: `becker_marine_logo` tops roughness
and sits 8th of 12 on raggedness; `summit_badge` tops raggedness and sits 8th on
roughness. So the two instruments are **not redundant** — the curve-fidelity and
edge-noise halves of Kent's complaint really are separate measurements.

On n = 12 that confidence interval is wide. This rules out the two being
redundant; it does **not** prove them independent, and nobody should quote it as
though it did.

### But `turn_gini` is substantially a complexity statistic

| pair | Pearson | Spearman |
|---|---|---|
| `turn_gini` vs log(trace count) | **−0.763** | −0.676 |
| `roughness_deg` vs log(trace count) | 0.496 | 0.359 |

| fixture | traces | gini | rough |
|---|---|---|---|
| `logo_alpha` | 2 | 0.946 | 0.48 |
| `logo_whitebg` | 2 | 0.956 | 1.61 |
| `ribbon_curve` | 2 | 0.573 | 9.45 |
| `logo_gaulke_roofing` | 5 | 0.723 | 9.32 |
| `becker_marine_logo` | 50 | 0.503 | 13.15 |
| `logo_bridge_bar` | 137 | 0.529 | 11.11 |

The two 2-trace designs pin the top of the gini ranking at 0.95, and everything
with 5+ traces collapses into a 0.50–0.72 band. That is also why the two columns
read Pearson −0.832 against **each other** on real artwork while they move
together on the synthetic ladder: gini is pulled down by complexity as roughness
drifts up with it.

**Consequence, and it is a real demotion.** `roughness_deg` is the number to read
per design. `turn_gini` earns its keep on the synthetic ladder and inside a
paired arm where the design is held fixed — not down a column of mixed designs.
The CLI now marks any design under `TRACE_FLOOR_FOR_RANKING` (5) as `thin`, so
the misreading is harder to make by accident. This also sharpens the paired-arm
caution above: `becker`'s trace count moving 50 → 77 between tol arms is not a
minor confound on the gini column, it is the dominant term.

## Status

Instrument only — no engine behaviour changed. Runs on the flat lane against
real stitch paths; `--all` covers the fourteen `artfidelity_self` fixtures.

## First run on REAL client artwork (2026-08-28)

Everything above is the fourteen built-in fixtures. `digitizer/testdata/reference/`
carries four of Kent's actual Becker logos — the same mark at different
placements and physical sizes, which is the one case where `turn_gini` is
legitimately readable, because the design is held fixed and only scale changes.

| placement | route | gini | rough | curve v | corner v | corners as % |
|---|---|---|---|---|---|---|
| chest **small** | gradient | 0.536 | **12.31** | 116 | 120 | 50.8% |
| hat **small** | gradient | 0.491 | **12.25** | 151 | 111 | 42.4% |
| hat polo **large** (logolc) | gradient | 0.533 | 9.75 | 1081 | 397 | 26.9% |
| hat polo **large** (logo_hat) | gradient | 0.521 | 10.46 | 1338 | 632 | 32.1% |

All four route `gradient`, corroborating the standing corpus finding that real
logo art carries JPEG ringing and anti-aliased edges the synthetics lack.

**The small placements measure rougher — 12.3 against 9.8–10.5.** That is
physically sensible: fewer stitches span the same curve, so the polygonisation
shows. It is also consistent with Kent calling the Becker edges jagged.

### An inference that looked obvious, and was refuted the same hour

The small placements also exclude far more vertices as corners (44% and 38% of
all turns, against 31% at hat-polo size). The tempting reading is that at small
scale the polygonisation turns grow past `CORNER_DEG` and get thrown out — so the
instrument would be blindest exactly where the fault is worst, and small-placement
numbers would be floors.

**Tested by looking at where the excluded turns actually sit, and it does not
hold:**

| placement | excluded | 60–75° | 75–90° | 90–120° | >120° | median |
|---|---|---|---|---|---|---|
| chest small | 44.0% | 7.5% | 5.0% | 7.5% | **80.0%** | 143.9° |
| hat small | 37.6% | 10.8% | 6.3% | 9.0% | **73.9%** | 143.3° |
| hat large | 31.0% | 6.3% | 7.1% | 13.4% | **73.1%** | 137.5° |

If polygonisation were crossing the threshold, the excluded turns would pile up
just above 60°. They do not — 73–80% of them exceed 120°, with a median near 140°,
at **both** sizes. Those are genuine reversals, and the distribution barely moves
with scale. The corner threshold is behaving as designed; the small placements
simply carry a higher share of sharp features relative to smooth curve.

**So: small placements really are rougher, and the corner threshold is not why.**
Recorded because the refuted version is the more natural thing to believe, and it
would have hardened into a stated defect on the next copy-forward — the failure
mode `MASTER_SCOPE`'s own Corrections section exists to keep visible.

---

## Correction (2026-08-28): the section above is wrong about size

**Everything in "First run on REAL client artwork" that reads as a SIZE effect
is a misread of what was run, and it is left standing above rather than edited
away, per this repo's convention for a claim that has to be withdrawn.**

All four runs used the default `target_width_mm = 80.0`. The words "small" and
"large" in those filenames are the PROFESSIONAL's garment placement — chest,
hat, hat-polo — not the size anything was digitized at. Nothing in that table
varied physical size, so it cannot say anything about it. The framing that the
four were "the same mark at different physical sizes, the one case where
`turn_gini` is legitimately readable" is wrong twice over: the design was not
held fixed (they are four different source files) and the scale never changed.

What the table actually shows, measured:

| file | traces | curve v | gini | rough |
|---|---|---|---|---|
| chest_small…lc_2_a | 10 | 116 | 0.536 | 12.31 |
| hat_small…hat_2_a | 11 | 151 | 0.491 | 12.25 |
| hat_polo_large…logo_hat | 52 | 1338 | 0.521 | 10.46 |
| hat_polo_large…logolc | 46 | 1081 | 0.533 | 9.75 |

The two rough ones carry **10-11 traces against 46-52** — a five-fold gap in
design complexity at identical target size. That is the axis already documented
above, arriving again. The corner-threshold sub-claim, itself already refuted on
its own terms, was answering a question the data could not pose.

### And the 0.5 px epsilon floor is not involved either

It was the obvious suspect and it is **provably inactive here.** All four sources
are 807-826 px wide at an 80 mm target, so `px_per_mm` is 10.09-10.32, and
`eps_px = max(0.5, 0.2 x 10.2) = 2.04` — four times clear of the floor. The floor
binds only below `0.5 / simplify_tol_mm` = **2.5 px/mm**, and stage 1's
`min_px_per_mm = 4.0` upscale means shipped configurations do not reach it. The
2026-08-17 ladder saw the floor bite because its 0.10 and 0.05 ARMS put `eps_px`
at 0.4 and 0.2; at the shipped 0.2 it never engages.

**So: do not chase the epsilon floor as a cause of rough curves at shipped
settings.** It is dead by arithmetic, not by argument.

### Size tested properly, and there is no clean size effect either

The experiment the section above should have been: ONE artwork, only
`target_width_mm` varying, so the design really is held fixed.

`becker_hat_polo_large_logo_hat` (the rich one, 46-52 traces at 80 mm):

| width mm | px/mm | eps_px | gini | rough | traces | curve v |
|---|---|---|---|---|---|---|
| 40 | 20.55 | 4.11 | 0.506 | 10.39 | 23 | 427 |
| 60 | 13.70 | 2.74 | 0.504 | 11.01 | 29 | 790 |
| 80 | 10.28 | 2.06 | 0.521 | 10.46 | 52 | 1338 |
| 120 | 6.85 | 1.37 | 0.556 | 11.17 | 78 | 2268 |

`becker_chest_small_logo_lc_2_a` (the sparse one):

| width mm | px/mm | eps_px | gini | rough | traces | curve v |
|---|---|---|---|---|---|---|
| 40 | 20.65 | 4.13 | 0.507 | **18.33** | **3** | 79 |
| 60 | 13.77 | 2.75 | 0.512 | 12.53 | 7 | 72 |
| 80 | 10.32 | 2.06 | 0.536 | 12.31 | 10 | 116 |

**Roughness is flat across a 3x size range on the rich artwork** — 10.39, 11.01,
10.46, 11.17, with no trend. The sparse one does climb as it shrinks (12.31 ->
18.33), but at 40 mm it is down to **3 traces and 79 vertices**, which the CLI
itself flags `thin`; size and surviving complexity move together there and
cannot be separated by this design.

`eps_px` spans 1.37 to 4.13 over the whole sweep — the 0.5 px floor is not
approached anywhere, at any size, confirming the arithmetic above empirically.

**Negative result, recorded per house convention:** neither physical size nor the
epsilon floor explains rough curves at shipped settings. What keeps surviving
every cut of this data is design complexity — trace count — which is the one
axis the instrument's own docstring already warns is confounded with everything
else. Anyone wanting a size answer needs artwork whose surviving shape count
does NOT move with scale, and nothing in the corpus does that today.

