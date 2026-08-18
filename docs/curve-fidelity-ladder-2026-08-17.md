# Curve-fidelity tol ladder — 2026-08-17

Task 2 of `docs/superpowers/plans/2026-08-17-shape-fidelity.md`. Answers: does
lowering `simplify_tol_mm` (default 0.2, `config.py:343`) improve how faithfully
the engine's coverage follows the customer's artwork on the real corpus?

**Verdict: no. The constant-tol lever is dead on corpus evidence.** Outline
fidelity is flat to slightly worse at tighter tolerances, one design hard-fails
at 0.05, stitch counts and prep time rise. Recommendation at the end.

## Method

Three arms through `prep_both.py` (engine at `73f37da` + this lane's
instrument commits; shipped routing, no forced class; garment from filename),
one pinned worktree, one `PRO_PARITY_OUT` per arm, sequential:
`PRO_PARITY_SIMPLIFY_TOL` ∈ {0.2, 0.1, 0.05} (`c3db6ab`'s harness hook).
Measured with `enginefidelity.py` (`56b4bdf`): engine-vs-art IoU at best
shift, plus symmetric Hausdorff and mean boundary distance in mm at that
alignment. Full logs: `parity_out_ladder/ladder.log`; raw tables:
`ef-tol{020,010,005}.txt` per arm.

**Denominator note:** `gaulke_roofing_hat` FAILS outright at 0.05
(`GEOSException: TopologyException: side location conflict` during prep), so
all paired numbers below are over the **same 14 designs** in every arm —
the 15-design per-arm means the CLI prints are not comparable across arms
and are not quoted here.

## Paired results (n = 14, identical set per arm)

| metric | 0.20 (shipped) | 0.10 | 0.05 |
|---|---|---|---|
| mean boundary distance (mm) | **1.194** | 1.209 | 1.362 |
| mean Hausdorff (mm) | 11.39 | 11.03 | 11.05 |
| mean art_iou | **0.802** | 0.796 | 0.795 |
| total real-lane stitches | 127,777 (15) | 131,161 (15) | 120,802 (14) |
| prep wall time (s) | 367 | 403 | 433 |

Per-design highlights:
- `becker_*` (five designs, the 0.26–0.37 mm regime): differences are noise;
  0.10 and 0.05 are byte-identical to each other on four of five.
- `tires_hat_3d`: **degrades 3×** at 0.05 (meanb 0.213 → 0.688; iou 0.905 →
  0.877). Tighter tol preserves quantize/AA jitter vertices as real geometry.
- `hotel_fremont_*`: moves both directions (2.61 → 2.23 → 3.05) — unstable,
  not improved.
- `gaulke_roofing_hat`: killed at 0.05 by invalid topology out of RDP —
  near-degenerate vertices survive simplification and a downstream shapely op
  refuses the polygon. A config-space latent bug worth knowing about, but the
  arm result alone is disqualifying for 0.05 as a default.

## Why the synthetic demo misled

The same-day synthetic glyph (flat Instagram-style mark, forced flat,
tol 0.05) showed visibly smoother curves. On the corpus the effect vanishes
because at 10 px/mm with 0.40 mm thread, RDP sagitta on real-size curves
(~0.1–0.15 mm) sits **inside the thread width** — the coverage raster cannot
see it — while the costs (noise vertices kept, degenerate topology, +2.6%
stitches at 0.10) are fully visible. Faceting is real geometry, but it is not
a corpus-measurable art-fidelity defect at these sizes.

The numbers that ARE large — Hausdorff 17–24 mm on `bridge_*`,
`hotel_fremont_*`, `gaulke_*`, `precision_drone` with high IoU — are
structural: far-off worst points from unsewn/displaced elements (the
`SHAPES_LEFT_UNSEWN` / enclosed-background family, and re-composed layouts),
not RDP chords. That is where the real art-fidelity error lives. Follow-up
candidate, not scope-crept here.

## Recommendation (decision is Kent's — plan Task 2 gate)

1. **Leave `simplify_tol_mm = 0.2`.** No default change, no golden churn.
2. **Do not ship a Studio-sent tighter tol** — same evidence kills it.
3. **Do not build arc-aware refinement on this evidence.** If big-curve
   visual smoothness matters as a *product* judgment (screen render, not
   sewn cloth — thread width hides it on fabric), that is a Kent call and a
   new measurement (render-side, not stitch-side), not this lever.
4. The measurable art-fidelity levers exposed instead: the 17–24 mm Hausdorff
   outliers (unsewn enclosed background, displaced elements) and the
   0.05-arm GEOS invalidity (harmless today, latent under any future tol
   change; noted, not fixed here).

Negative result, recorded per house convention: a lever measured dead is a
result, and nobody has to re-run this ladder to relearn it.
