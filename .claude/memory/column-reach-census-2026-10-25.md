---
name: column-reach-census-2026-10-25
description: W3-06 — 178 of 296 hand-labelled letters reach the Column lane at the pro's widths; 85% of misses are two by-design routes (small-text bean rung 76, BECKER white faces 20), not the tagger; no tagger ratio rescue raises held-out kappa
metadata:
  type: project
---

2026-10-25, lane `nervous-chebyshev-a8989d` (W3-06), engine 4fcdb4e6.
Tool `digitizer/tools/column_reach_census.py`; labels in
`testdata/lettering_truth.json` under NEW keys `relabels` (Gaulke's F moved
id since b7d63ae) and `pairs` (ProSeal hat/beanie, MFab hat/LC, agent-labelled
at the pro's widths on the Studio request, MFab on the rembg path).

**The census.** 13 labelled pairs at the pro's width (Golden Tee digitized,
unlabelled: its bevel has no honest letter call). 296 letters, 275 detected
(pooled detection kappa 0.653), 178 built by the lane (reach kappa 0.650).
Misses 118: **stage-7 route 80** (76 = `rung:bean_letter`, small text under
`small_text_true_size`; 3 Drone THERMAL `guard:ink_stray`; 1 `run_outline`),
**unsewn white 20** (BECKER's arched letters are `enclosed_background`,
`sew_enclosed_white` OFF), aspect 10, height ratio 5, other thread 1,
distance 1, stroke cv 1. Premise TRUE: two reasons hold 85%, and neither is
the tagger.

**The tagger is not where reach is lost.** Every text-tagger constant moved
census-side (`grid`, `@NAME`): height ratio 0.78/0.75/0.70, aspect 1.5/1.8,
two-member lines, ΔE 30. Each wins only its own job in-sample (0.648 → 0.651
MFab LC's N at 0.798; ΔE 30 → 0.653 by merging Drone's orange THERMAL into
grey PRECISION, the split the tagger's comment keeps on purpose), and
leave-one-JOB-out stays 0.648 for all. Reported, not built.

**The known misses, traced.** (1) Drone's A of AND IS tagged (wide-letter
adoption); true-size restore strips it as a stray because `small_text._core`
reads a line as ONE thread by identity (2564 vs the line's 1972, ΔE 18.2,
inside the tagger's 20). ProSeal's A is not stripped at main (cap 3.15 mm,
over restore's 3.0) and sews in the bean line; under the re-set flags
(`small_text_cap_mm` 4 + `small_text_cap_reach_edges`, both OFF) it reaches
the lane. (2) MFab LC's N: height ratio 0.798, in-sample only. (3) Drone
THERMAL at 62.6 mm: E, R, A, L each split into two same-thread pieces by
segmentation, so their "aspect" refusals are pieces, flagged `split`.

**Why:** the lettering week's Column-lane gains reach only letters stage 7
hands the lane; the census says the gate is policy (small-text route, white
faces), already built as OFF flags, not the tagger.
**How to apply:** before a tagger change "for reach", run
`column_reach_census read` and `grid`; quote held-out kappa, never the
in-sample one. The re-set arm is the measurement of what Kent's small-text
flip buys in reach.

Related: [[small-text-floor-2026-10-24]], [[wide-letters-mfab-w-2026-10-23]],
[[word-tagger-l1-2026-10-08]], [[white-rerule-packet-2026-10-25]],
[[lettering-board-2026-10-25]].
