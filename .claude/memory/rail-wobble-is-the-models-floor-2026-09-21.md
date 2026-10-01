---
name: rail-wobble-is-the-models-floor-2026-09-21
description: satin rail wobble 0.089 mm is the rail MODEL's floor with every defence working — six ablations all net-positive, no mechanism to switch off; and satin's mean deviation is OUTWARD, not inward
metadata:
  type: project
---

Kent asked 2026-09-21 what needed work with no sew-out available, then picked
the rails — the *"WHY rails wobble"* [[edge-wobble-is-satin-rails-2026-09-19]]
left open. Measured on `origin/main` at `b14c0a95`; full trail
`docs/rail-wobble-cause-2026-09-21.md`, PR #544.

**The sign is OUTWARD, and the other two tiers are the control.** `edge_wobble`
`offset` on three real logos: satin **+0.25 / +0.25 / +0.24 mm**, `fill`
**+0.30 exactly** (std 0.010–0.019), `line` **+0.00** (std 0.000). Same designs,
same `pique_knit` pull comp. Only satin misses its own pedestal and only satin
has variance (std 0.089 / 0.092 / 0.070). The worst points ARE inward (−0.78 to
−0.95) — a millimetre below the pedestal — so "mean outward, tail inward" is one
row, and quoting either alone misreads it.

**Three hypotheses, all refuted, all with tables.** (1) The width filters:
relaxing median-5 + 4 smoothing passes makes it WORSE — std 0.089 → 0.103,
corner share 19.2% → **26.0%** without the median. They are reducing it.
(2) Rays escaping through a junction: real in the sampler (`|side_a − side_b|`
p50 0.141 mm on a 1.10 mm half-width, p90 1.485) but it **never reaches the
rails** — a synthetic perpendicular junction reporting 15 mm against a true
1.5 mm places its rail at **1.50 exactly**, at every stroke length from 51
stations down to 11. (3) Any single mechanism: no short-stitch guard 0.085,
corridor cap off 0.101, no taper zone 0.091, `follow_edge` ON 0.102, against
shipped 0.089.

**Why:** all six defences are net-positive or neutral, so 0.089 mm is the FLOOR
of the model with everything already working, not a defect sitting on one. A
smoothed parallel offset of a medial axis cannot represent a letter's edge
closer than this; `line` and `fill` read 0.000 and 0.010 because they put
thread on boundary geometry instead of reconstructing it.

**How to apply:** do not go tuning `_WIDTH_MEDIAN_WINDOW`,
`_WIDTH_SMOOTH_PASSES`, the corridor cap or the short-stitch guard to fix
edges — each one is already paying for itself. Closing the wobble means
changing the rail model, and that should not start until somebody ties 0.089 mm
to what Kent sees on cloth ([[kent-eye-vs-instruments-2026-08-27]]): #536 has
`enthusiast` at 0% unsewn / 100% overshoot so it does not move `lost_frac`, and
[[six-flags-invisible-at-viewing-size-2026-09-18]] found changes at this scale
read as "no difference". Also do NOT read the 2026-09-20 bisect's inward-rail
item and this wobble as one defect — they are separate, and that is the natural
mistake. One live trade if it is ever wanted: `follow_edge` ON takes bare
outline 2.2 → **0.0 mm** for std 0.089 → 0.102 and mid-column 2.1% → 4.8%.
