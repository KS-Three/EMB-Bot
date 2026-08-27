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
2. `roughness_deg` was built to detect POLYGONISATION. On real artwork it may
   be responding to stitch-level edge noise instead — which is
   `edge_smoothness.ragged_mm`'s question, not this instrument's. Cross-checking
   the two columns on these same fixtures is the obvious next step and has not
   been done (`edge_smoothness.py` is unmerged on another lane).
3. **The `turn_gini` column must not be ranked at all here.** `logo_whitebg` and
   `logo_alpha` top it at 0.95, on **2 traces and ~110 vertices each** — one
   satin column's two rails. A concentration statistic on a denominator that
   small is not comparable to a 137-trace design's. This is the "not a grade,
   a paired measure" limit showing up in practice on the very first corpus run.

## Status

Instrument only — no engine behaviour changed. Runs on the flat lane against
real stitch paths; `--all` covers the fourteen `artfidelity_self` fixtures.
