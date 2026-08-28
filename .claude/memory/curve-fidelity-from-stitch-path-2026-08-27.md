---
name: curve-fidelity-from-stitch-path-2026-08-27
description: curve fidelity is measurable from plan.iter_runs() and NOT from a raster — the rejected turning-concentration measure was right and the raster was wrong; turn_gini ranks but is fooled by mixed geometry, roughness_deg detects but saturates; the instrument's own denominator caught a trace-population confound in the tol ladder
metadata:
  type: reference
---

Kent's smoothness complaint splits in two, and he confirmed both matter about
equally: **edge noise** (*"sawtoothed and jaged"*, `tools/edge_smoothness.py`)
and **curve fidelity** (*"Lines/circles are not smooth like the photo"* — a
curve sewn as a polygon). Nothing owned the second. `tools/curve_fidelity.py`
does now. Full write-up:
`docs/curve-fidelity-from-the-stitch-path-2026-08-27.md`.

**The one load-bearing fact: it is the INPUT that was wrong, not a threshold.**
A turning-concentration measure was built against a rasterised mask and cut on
2026-08-27 because it is not even monotonic — a rasterised circle reads *more*
angular than a 40-gon at every resample step, since a raster boundary is itself
a staircase of 45/90 degree steps. The raster IS a polygon. Pointed at
`plan.iter_runs()` — the vertices the machine actually sews, mm floats, no
raster, no registration, no alignment quantum — **the same measure is monotonic
across the n-gon ladder at 0.5/1.0/2.0 mm sampling.** Both tables are preserved
in the two files' docstrings, and the ladder is an executable test.

- **Its floor is stitch length, and it is physical.** At 3.0 mm sampling a 20-gon
  (3.13 mm edges) reads BELOW a 60-gon: one vertex lands per edge, every vertex
  turns alike, the polygon is invisible because the needle is as coarse as it
  is. Never compare arms at different stitch lengths.
- **Two numbers, failing differently, on purpose.** `turn_gini` ranks severity
  but is fooled by legitimate mixed geometry — a rounded rectangle (flat sides,
  true quarter-circle corners) reads 0.656, about what a 20-gon reads, and real
  logos are almost all mixed geometry. `roughness_deg` reads the turn sequence
  LOCALLY, separates that rounded rect (0.348) from the n-gons (4.1) by an order
  of magnitude — but saturates and then reverses (40-gon 4.28, 20-gon 4.15,
  12-gon 4.01), so it detects and cannot rank. Same construction as
  `ragged_mm`/`perimeter_ratio`; a design where they disagree is worth a look.
- **Corners are excluded above 60 deg**, which is what stops a square topping
  the ranking — and with its corners gone a square has no curved vertex left, so
  it REFUSES rather than scoring. Standing false positive: a many-pointed star.
- **It cannot read intent.** A logo that IS a 20-gon and a circle polygonised to
  one are the same path. The absolute number is not a grade; it is a PAIRED
  measure, read as a delta across arms over one design.
- **Sagitta was tried and cut** — millimetres of bow, `s = (L/2)tan(t/4)`, exact
  for a regular sampling, and NOT monotonic: dense resampling makes a polygon's
  straight edges look like a finely-sampled curve, so it measures sampling
  fineness rather than curve fidelity. Table kept so it is not rebuilt as the
  obvious fix.

**The trap it walked into on its own first reading, and the reason to trust the
denominator columns.** Re-running the 2026-08-17 `simplify_tol_mm` ladder — the
lever that doc could not measure at all, every delta being an order of magnitude
inside the raster's 0.35 mm floor — the instrument resolves it. `logo_whitebg`
correctly reports ZERO movement across all three arms, because stage 4 floors
realized epsilon at 0.5 px and its plan is byte-identical (the same effect that
made 9 of 14 designs identical in 2026-08-17). But `becker_marine_logo`'s
apparent 0.5026 → 0.5865 improvement is **not clean**: its trace count goes
50 → 77 and curve vertices 1991 → 2556 between arms, so part of the move is the
denominator, not the geometry. `ribbon_curve` does it quietly — corner count
triples 6 → 26 as finer RDP preserves sharper vertices that then fall out of the
measured set. That is ROADMAP hard gate 4's failure mode in a different hat: the
mix moved, so the "gain" can be the floor shifting. `traces`,
`curve_vertices` and `corner_vertices` are reported on every row for exactly
this reason — **read them alongside every delta**. No engine default was changed
on that table, and `simplify_tol_mm` stays 0.2 (Kent, 2026-08-17); re-opening it
needs arms that hold the trace population constant.

**What the two numbers turn out to measure (checked 2026-08-27, both
instruments off ONE `digitize()` per design, 12 fixtures).** Two results:

- **`roughness_deg` is NOT edge noise.** Against `edge_smoothness.ragged_mm`:
  Spearman **0.028**, Pearson 0.153, 95% CI [-0.55, 0.59]. Rankings near-inverted
  at the ends (`becker` tops roughness, 8th of 12 on raggedness; `summit_badge`
  the reverse). The curve-fidelity and edge-noise halves of Kent's complaint are
  genuinely separate measurements. n = 12 and the CI is wide — this rules out
  REDUNDANCY, it does not prove independence.
- **`turn_gini` is substantially a COMPLEXITY statistic and must not be ranked
  down a column.** Against log(trace count): Pearson **-0.763**, Spearman -0.676.
  The two 2-trace designs (`logo_whitebg`, `logo_alpha`) pin the top at 0.95
  while every design with 5+ traces collapses into a 0.50-0.72 band. That is also
  why the two columns read Pearson **-0.832 against each other** on real artwork
  while moving together on the synthetic ladder — gini is pulled down by
  complexity as roughness drifts up with it. **`roughness_deg` is the number to
  read per design;** gini earns its keep on the ladder and inside a paired arm
  where the design is held fixed. The CLI marks designs under
  `TRACE_FLOOR_FOR_RANKING` (5) as `thin`. This also sharpens the tol-ladder
  caution: `becker`'s 50 -> 77 trace move is not a minor confound on gini, it is
  the dominant term.

**First REAL-artwork run, 2026-08-28, and the wrong conclusion drawn from it.**
Ran the four Becker artworks in `testdata/reference/`. Reported that SMALL
placements sew rougher (12.3 vs 9.8-10.5) and built a size story on it.
**That is withdrawn — it is not a size effect.** All four ran at the default
`target_width_mm = 80`; "small"/"large" in those filenames is the PRO's garment
placement, not the digitized size, and the four are different source files, so
neither was the design held fixed nor did scale vary. What actually separates
them is trace count: the two rough ones carry **10-11 traces against 46-52** at
identical target size — the complexity axis, arriving again. A corner-threshold
sub-claim built on top of it was refuted on its own terms the same hour, and was
answering a question the data could not pose anyway.

**The 0.5 px epsilon floor is DEAD as an explanation of rough curves at shipped
settings — by arithmetic, not argument.** `eps_px = max(0.5, simplify_tol_mm *
px_per_mm)`, so the floor binds only below `0.5/tol` = **2.5 px/mm**, and stage
1's `min_px_per_mm = 4.0` upscale keeps shipped configs clear of it. On the
Becker set (807-826 px at 80 mm) `px_per_mm` is 10.09-10.32 and `eps_px` = 2.04,
four times clear. The 2026-08-17 ladder saw the floor bite only because its 0.10
and 0.05 ARMS drove `eps_px` to 0.4 and 0.2. Do not re-chase it.

**And physical size, tested properly (one artwork, only `target_width_mm`
varying), does not move roughness monotonically** — 10.39 at 40 mm, 11.01 at 60,
10.46 at 80. Size and complexity are themselves confounded, because more shapes
survive at larger sizes (23 -> 29 -> 52 traces over that sweep).

Mechanical notes: a satin run is an alternating zigzagMechanical notes: a satin run is an alternating zigzag, so its raw point
sequence turns ~180 deg per vertex and reads as noise — `points[0::2]` /
`[1::2]` are the two rails, each tracing an artwork edge (verified on
`logo_whitebg`: raw chords 2.66-2.69 mm, rails a clean 0.406 mm). Only the
VISIBLE tiers are measured (satin, border, bean, run): underlay is hidden under
its satin, fill is tatami row reversal rather than artwork shape.

See also [[letterform-fidelity-2026-08-26]] (the same "instrument was blind to
it" failure), [[artfidelity-self-rebuild-2026-08-27]] (and its warning about
losing a cloud session's work unpushed).
