---
name: pot-slot-swing-2026-11-03
description: Pooh's pot body swings between a pale and a dark palette slot because k-means centres drift (fringe-blend votes + size-dependent init), the chart has no olive; measured, nothing built
metadata:
  type: project
---

Kent's ruling 11-03: #1230 (`flat_page_fringe_exclude`) stays OFF; measure the swing, do not build.
Probe: stage 2 wrapped on Pooh (266 px, 2.99 px/mm at 80 mm; 4.38 at 54.6), forced flat,
`max_colors` 6, seed default. The four harness cells reproduce their md5s exactly
(e3fca649, 7ef7f84b, 473345df, 11bb904a). Numbers only; no render kept in the repo.

**The pot is ONE shaded body, not two tones.** 27,306 px at 80 mm (12,726 at 54.6), 9.5% of the
fit sample at both sizes. Lab L 5/25/50/75/95 = 48.8 / 55.4 / 59.6 / 64.6 / 70.0, unimodal. The
chart has no olive: nearest thread to the art highlight (64.4,-3.8,19.7) is 6071 at dE00 7.0; to the
pot mean (59.8,-4.0,19.2) it is 0152 at 9.8 (0862 9.8, 0853 10.3). The pixels alone want 0555
and 6071 (9,760 / 7,880 of 27,306 nearest-thread). So ANY palette cuts it somewhere.

**Deciding stage = Lloyd (the fit), then the chart snap as amplifier.** Init is identical OFF vs ON
(same seeds: the flag keeps the draw) but differs by SIZE: 80 mm seeds on the pot at L59 and L66;
54.6 mm at L71 and L61 (the 40,000-row sample is a different stride). OFF vs ON at 80 mm first
diverges at Lloyd (final centres hash b25ae236 vs 81e4f879; 1,209 then 3,331 fringe rows leave the
vote of 40,000). Centre of the two pot slots, fit votes, pot pixels each side (full grid):
- OFF 80: L51 (4,863 votes) / L75 (1,964); pot 19,859 / 7,413 = 73/27 -> 0763 / 0873 (the hole).
- ON 80: L41 (2,404) / L62 (3,996); pot 3,048 / 24,221 = 11/89 -> 0454 / 6071.
- OFF 54.6: L46 / L66 centres; pot 2,108 / 10,618 = 17/83 -> 0945 / 6071.
- ON 54.6: L59 centre (one slot); pot 12,706 / 20 -> 0152.
So not "a few hundred votes": the centres move 10-24 L on ~3% of votes (grey fringe blends sit
between the slots and drag both), and 2.3-3.8k pot px (8-14%) lie within 3 dE76 of the cut.
Stages ruled out: majority filter moves <100 pot px per cell; phantom dissolve removes NOTHING in
any cell (max edge fraction .44 against 0.9); the colour cap never fires (no COLOR_CAP_APPLIED) and
final region threads equal the stage-2 snap in all four cells. Chart snap is a near-tie: ON 80
centre (62,-4,19) -> 6071 9.1 / 0862 9.2 / 0453 9.2; ON 54.6 (59,-4,20) -> 0152 9.6 / 0862 9.7 / 0853 9.7.

**7 colours:** the pale seed (L66) ends at (90,2,7) with 689 votes = grey-white fringe blends
(5,586 px, edge fraction .43) -> own slot 0015, 79 mm2 of flecks, plus 1526 113 mm2. OFF 7 does
close the hole (pot one slot 0555, 490 mm2, 8 colours). ON 7: no fleck slot, pot unchanged vs ON 6
(6071 / 0454), extra slot is 1312, 110 mm2. 7 spends the slot on the fringe, it does not hold the pot.

**Becker shares the disease.** Same flag, stage 2 only, 6 colours, jpgs in `testdata/reference`:
the mid-tone slot (L48-54, between pale 4073 and dark 2776) changes thread in 3 of 4 (LC 0111 ->
0674; small hat 3274 -> 0111 + 4074 split; chest 0674 -> 0128 at dE00 9.5); hat large keeps its
threads. Two-tone art is inert: MFab hat/LC, Golke, Fremont patch, TOAT beanie/machine, marine.

**Options (nothing built):** area-weighted init 2-3 d, removes only the size-dependent seed, moves every
flat palette; per-region re-snap after the cap 2 d, fixes ties not the partition (cluster centre ~
region mean, so ON 80's 9.1/9.2/9.2 stays); large-region own slot 3-4 d, still lands 9.8 off (no olive in
the chart) and the cap re-merges it; dissolve threshold 0 effect (not the decider); 7th colour = a Kent
thread spend. Only measured stabiliser: the flag (one-slot pot at both sizes); residual = chart gap.

**Why:** a shaded body with no matching chart thread and two competing k-means slots has no stable
cut; the fringe's few percent of votes and the sample stride choose it. **How to apply:** do not tune
the dissolve or cap for a pot-type swing; read a mid-tone slot's thread as fragile on any flat art with a
mid-tone body between pale and dark (Becker x3); quote `kmeans` centres + chart tie gaps, not region
counts; a flip of #1230 needs the Becker mid-tone threads on Kent's flip sheet first. See
[[colour-cap-sewn-2026-10-29]], [[dark-ink-bean-2026-10-28]], [[stage0-flake-output-alignment-2026-10-25]].
