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

Mechanical notes: a satin run is an alternating zigzag, so its raw point
sequence turns ~180 deg per vertex and reads as noise — `points[0::2]` /
`[1::2]` are the two rails, each tracing an artwork edge (verified on
`logo_whitebg`: raw chords 2.66-2.69 mm, rails a clean 0.406 mm). Only the
VISIBLE tiers are measured (satin, border, bean, run): underlay is hidden under
its satin, fill is tatami row reversal rather than artwork shape.

See also [[letterform-fidelity-2026-08-26]] (the same "instrument was blind to
it" failure), [[artfidelity-self-rebuild-2026-08-27]] (and its warning about
losing a cloud session's work unpushed).
