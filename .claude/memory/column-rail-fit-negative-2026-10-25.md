---
name: column-rail-fit-negative-2026-10-25
description: W3-03 "fit the Column lane's rails to lines and arcs" measured FALSE on seven pairs -- straight rails read 0.000-0.04 mm on RUN windows (no corner, on the outline), the per-letter wobble is real corners and cuts; a corner-keeping fit's ceiling is today's figure. Don't plan a rail fit. `letter_band.rail_classes` + board column `rail_run`
metadata:
  type: project
---

2026-10-25, wave 3 task W3-03, lane `nervous-chebyshev-a8989d`. Brief: build
`column_rail_fit` (OFF) in `outline_cut.py`, moving rail points by at most
`letterform_priors_k` x the source pixel. **Premise measured false, nothing
built**; foreman's replacement shipped instead: run-window rail wobble beside
today's per-letter figure (`tools/letter_band.py` `rail_classes`, board column
`rail_run`). Widens [[marine-stem-rails-2026-10-25]] (#1077, the four MARINE
files) to all seven pairs and to the fit itself, and uses its classifier.

**The read.** Each of `rail_jitter`'s 9-penetration windows, classed by
`rail_jitter_cause.cause`: `corner` (an outline vertex turning > 20 deg within
0.6 mm), `stray` (a point > 0.6 mm off the outline: a split / short
penetration, or a rail along an internal cut), else `run`. Ours from the
shipped plan; the pro's classed by our outline through the board's
registration. Main 82b0bf28 (text_lean, inside_stagger, wide_letters ON).

| pair (src px) | letter | ours today p90 | ours run p90 (n) | pro run p90 (n) |
|---|---|---|---|---|
| Becker hat 76.5 (0.53) | M / A / N | 0.201 / 0.330 / 0.013 | 0.000 (28) / 0.000 (31) / 0.000 (27) | 0.000 (49) / 0.012 (13) / 0.000 (38) |
| Becker hat 101.9 (0.70) | M / A / N | 0.234 / - / - | 0.000 (71) / 0.000 (50) / 0.000 (54) | 0.000 (76) / 0.040 (22) / 0.000 (66) |
| Becker LC 95.7 (0.66) | M / N | - / 0.013 | 0.001 (55) / 0.000 (47) | 0.000 (73) / 0.000 (61) |
| MFab hat 104.9 (0.26, priors grid-gated) | W / N / N / A | 0.076 / 0.174 / 0.230 / 0.164 | 0.001 / 0.000 / 0.005 / 0.012 | 0.028 / 0.000 / 0.033 / 0.000 |
| Fremont hat 92.6 (0.037) | N / M / E / T | 0.012 / 0.069 / 0.007 / 0.000 | 0.000-0.002 | 0.000-0.019 |
| Drone hat 62.6 (0.081) | R / C | 0.217 / 0.110 | 0.001 / 0.001 | 0.004 / 0.044 |

(`-`: today's raw reader found no window; split legs break its columns.)

1. **No trace wobble to remove.** Read along the same cross lines at every
   stage, straight runs are flat before the priors (Becker M 0.000; N 0.059,
   A 0.125 -> 0.013, 0.093 at the stations) and the rails copy them flat.
2. **The per-letter figure is turns**: junction notches (reflex 34-145 deg),
   the art's own corners (the M's bevelled top-left is one source pixel proud
   in the art), end faces, cut-to-outline steps. The pro's windows near the
   same corners read 0.000 (his columns stop at them,
   [[big-letter-construction-2026-10-24]]).
3. **A corner-keeping fit cannot move it**: zero every run window and M stays
   0.202 -> 0.202, hat-large M 0.145 -> 0.145. Laying the leaning side cuts
   (3-10 deg off the stem, 0.4-1.8 mm off at the far end, past the 0.20-0.53 mm
   cap) along the stem's line: M 0.202 -> 0.202, A 0.255 -> 0.194.
4. **The brief's figures were stale**: MFab W 0.382 -> 0.076 (pro 0.036;
   `text_cluster_wide_letters` ON put it through the lane), Fremont O 0.418 ->
   0.164 (pro 0.145, the curvature floor), MFab A 0.397 -> 0.164 (pro 0.196).

**Run windows that are not wobble**: a fan's inside reads our inside stagger
(pivot ends ~0.4 mm apart by design; MFab's 18 mm MFAB 0.273 against 0.062), a
bowl its curvature (Fremont O 0.164, all run: no corners).

**Owners of what the eye does see (b):** the M's V and the A's apex turns,
corner-fold ([[column-corner-folds-2026-10-23]], #1057); the hat-small M's
second penetrations on its 4.3-4.6 mm crosses, which the raw reader takes for
rail points, the split-ceiling card (gate 1).

**Why:** #1052's 10 mm band and the 5-10 mm band read rail wobble per letter;
two briefs (#1077's stem refit, this rail fit) followed and both measured false.
**How to apply:** quote `rail_run` (board) / `rail_classes` run p90, never the
per-letter `rail_jitter` p90, for "are our rails wobbly"; a run figure over
~0.05 on a straight stroke is the one worth chasing, after ruling out a stagger
or a bowl. Scripts: the shared notes folder's `w303-column-rail-fit/`.
Related: [[lettering-board-2026-10-25]], [[rail-wobble-is-the-models-floor-2026-09-21]].
