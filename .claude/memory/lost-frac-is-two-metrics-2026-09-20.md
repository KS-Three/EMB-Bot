---
name: lost-frac-is-two-metrics-2026-09-20
description: enthusiast's lost_frac is 100% OVERSHOOT and 0% unsewn ink; the rail's spill and its jitter win are one knob, and three cures each traded one instrument for another
metadata:
  type: project
---

**`dropped_elements`' `lost_frac` sums two opposite defects, and a fixture is
usually entirely one of them.** Measured 2026-09-20, all four at 80 mm
left_chest:

    enthusiast  lost_frac 0.3002   unsewn   0%   overshoot 100%
    tires       lost_frac 0.1270   unsewn   0%   overshoot 100%
    becker      lost_frac 0.0509   unsewn  44%   overshoot  56%
    bridge      lost_frac 0.1070   unsewn 100%   overshoot   0%

`enthusiast`'s 0.3006 is **0.0 mm² of unsewn ink and 118.7 mm² of thread on
bare cloth** — all 32 regions `ink=False`, `cover` ≈ 0.99 — while
`rail_edge --bare` reads **3.94% before and after** the commit blamed for the
move. **The letters sew fatter than they are drawn; nothing went uncovered.**
A brief asked me to "recover the lost coverage" on this fixture; there was
none to recover. Both halves ship separately now (`unsewn_frac`,
`overshoot_frac`, `FEATURES_SCHEMA` 2).

**Why both wordmarks regressed against the 08-27 engine while both
non-wordmarks improved.** `768de79e` (defect 23) puts an overshooting rail on
the nearest boundary crossing instead of stepping in 15% — 242 firings on
this fixture of 1436 satin penetrations, at a median **0.980** of the
requested width, so the rail lands ON the shape edge. Rails further out cover
more artwork **and** spill more thread: one knob, two populations. Confirmed
in today's tree, not just at that commit — neutralising the branch on current
`main` moves lost_frac 0.3006 → 0.2584.

**Three cures measured, every one bought an instrument with another:**

    candidate                lost_frac  jitter enth/becker  bare(93mm)
    shipped                     0.3006     0.0227 / 0.0246     3.94%
    revert the branch           0.2584     0.0413 / 0.0447     3.94%
    inset the branch 0.20 mm    0.2430     0.0401 / 0.0539     3.99%
    global corridor cap         0.2420     0.0280 / 0.0287     5.58%

The inset is **worse than a full revert on becker**, and that generalises:
**jitter is deviation from the neighbours' chord, so offsetting a SUBSET is a
step at every boundary of that subset** — the crossing placement is smooth
precisely *because* it agrees with neighbours sitting on the edge. The
corridor cap is global and so holds jitter, but pays in real coverage and
drops `max_out` 0.541 → 0.300 mm, which is pull comp, gate 1.

**Kent's ruling 2026-09-20: keep 768de79e's placement, pin what actually
regressed.** Spill and the jitter win are one degree of freedom, not two
effects to separate.

**`unsewn_frac` alone cannot police the trade — measured, not assumed.** The
guard first pinned it at 0.02 and claimed it caught the corridor cap; the cap
read **0.0028** and passed, because `dropped_elements` only counts regions
≥ 1 mm² after a 0.5 mm opening, so a thin rind along every column never forms
a region it can see. `rail_edge.bare_area` does (5.50% → 7.22%). Two shapes
of loss, two instruments; a guard pinning one is gameable by the other.

`tests/test_lettering_coverage_regression.py` (name stale — the worktree hook
refuses a rename) pins three, each verified to fire. Full trail: DOCTRINE
2026-09-20, COOKBOOK's instrument traps. Related: [[rail-dents-2026-09-03]],
[[instruments-that-underreport-2026-09-06]],
[[thresholds-on-the-wrong-population-2026-08-28]],
[[edge-wobble-is-satin-rails-2026-09-19]].
