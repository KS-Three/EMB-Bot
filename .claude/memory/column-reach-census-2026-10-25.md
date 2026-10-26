---
name: column-reach-census-2026-10-25
description: W3-06 — on merged main 257 of 296 hand-labelled letters reach the Column lane at the pro's widths; the 39 misses are BECKER's white faces and split/script letters, not a tagger ratio; no textcluster rescue raises held-out kappa
metadata:
  type: project
---

2026-10-25/26, lane `nervous-chebyshev-a8989d` (W3-06). Tool
`digitizer/tools/column_reach_census.py`, doc `docs/column-reach-census-2026-10-25.md`.
Labels in `testdata/lettering_truth.json` under NEW keys `relabels` (Gaulke's F
moved id since b7d63ae) and `pairs` (ProSeal hat/beanie, MFab hat/LC,
agent-labelled at the pro's widths on the Studio request, MFab on the rembg path).

**Merged main (46949f78, after #1057 made the small-text re-set default).** 13
labelled pairs (Golden Tee unlabelled: its bevel). 257 of 296 letters reach the
lane, reach kappa 0.878; detection kappa 0.660. Misses 39: white faces 20 (BECKER,
`enclosed_background`, `sew_enclosed_white` OFF), aspect 10 (Drone THERMAL at 62.6
mm: E, R, A, L each split into two same-thread pieces by segmentation; Drone's M
1.415; MFab's F top bar cut off by the keyline; Tires' script word), height ratio
3 (ProSeal's half-height "+", MFab LC's N at 0.798), and a handful more.

**4fcdb4e6 (before #1057):** 178 of 296; 80 of the 118 misses were the stage-7
bean rung taking small text under `small_text_true_size`
(`stage7_sequence.py:2960`, ahead of the lane at `:3184`). The re-set flags fixed
exactly those: 54 -> 133 of 144 on the five small-text pairs, as #1057's default.

**The tagger is not where reach is lost.** Every textcluster constant moved
census-side (`grid`, `@NAME`: height ratio 0.78/0.75/0.70, aspect 1.5/1.8,
two-member lines, ΔE 30) wins only its own job in-sample (h 0.78: MFab LC's N;
ΔE 30: Drone's T and H, by merging orange THERMAL into grey PRECISION), and
leave-one-JOB-out stays at today's kappa. Reported, not built.

**Drone's A of AND** (known miss): tagged, then stripped by true-size restore as
a stray because `small_text._core` reads a line as ONE thread by identity (2564 vs
1972, ΔE 18.2, inside the tagger's 20). Moot on merged main (the re-set takes it).

**Why:** the Column lane's construction gains reach only letters stage 7 hands it;
the census says the gates were policy (small-text route, now flipped; white faces,
held) and segmentation, not the tagger's ratios.
**How to apply:** before a tagger change "for reach", run `column_reach_census
read` and `grid` and quote leave-one-JOB-out kappa, never in-sample. Split letters
(THERMAL) are segmentation's: no door ratio admits a half letter.

Related: [[small-text-floor-2026-10-24]], [[wide-letters-mfab-w-2026-10-23]],
[[word-tagger-l1-2026-10-08]], [[white-rerule-packet-2026-10-25]],
[[lettering-board-2026-10-25]].
