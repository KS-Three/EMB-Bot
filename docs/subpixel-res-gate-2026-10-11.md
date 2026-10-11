# A resolution floor under the native edge read — 2026-10-11

**Question.** PR #818 found that `cfg.subpixel_edges_upscaled` (Kent's
2026-09-18 flip, ON) causes the Becker outline reversals — vertices turning
back more than 120 degrees, 7.1 per 100 mm ON against 0.0 OFF at 1.8 px/mm —
and buys no edge accuracy at 1.8 px/mm in three cases of four, while it earns
its keep at 3. Should the read be skipped below some source resolution?

**What was built.** `cfg.subpixel_edges_min_px_per_mm`, default `None`
(today, byte for byte). Set, a source stage 1 upscaled that delivers less
than the floor skips the native read, and the curve refinement that rides on
it, and keeps the pre-flip polygon. `tests/test_subpixel_res_gate.py`.

## Recommendation

**Leave it unset.** At 1.8 px/mm the floor does remove the reversals (Becker
7.1 → 0.0 per 100 mm; the four truth cases 4.1 → 1.5 on average), and on real
logos it costs no edge accuracy (mean median error 0.115 → 0.108 mm, a
difference under the harness's ~0.01 mm noise; `golden-1.8-before-after.png`
shows the zigzags it removes). But the Becker render shows what the
reversal count cannot: on Becker the floor brings back the 0.68 mm source-pixel
staircase that the 09-18 flip was made to remove — right-angle turns 26.5 →
81.3 per 100 mm, every BECKER outline a stair (`becker-1.8-before-after.png`).
On top of that, the letterform pass then fits arcs to MARINE's stairs and bites
a notch into the M and the R. A reversal is a few spikes on a smooth line; a
staircase is the whole line. On clean geometric art the read is also plainly
better at 1.8 px/mm (`edge_truth_ladder.py`: rectangles 0.27 → 0.02 mm RMS
from the true edge, the ribbon 0.13 → 0.07). The reversals are better
fixed where they start, in the read's corner placement, or by
`coverage_edges` (#818) on Becker's class, than by switching the read off.
**If Kent wants the floor anyway, use 2.5, not 3.0.** Every case measured here
gives the same result with 2.5 or 3.0, because nothing was measured between 1.8
and 3. But real 3 px/mm sources read 3.00–3.01 in stage 1, so a floor of
exactly 3.0 would turn the read off for a source at 2.99.

## The options in Kent's terms

| option | outline reversals (per 100 mm) | edge error (median, mm) | staircase |
|---|---|---|---|
| **A. floor unset (today)** | Becker 7.1 at 1.8, 5.6 at 3; truth cases 4.1 / 5.7 / 6.2 at 1.8 / 3 / 5 | 0.115 / 0.059 / 0.036 | gone at every resolution |
| **B. floor 2.5 or 3.0** | Becker **0.0** at 1.8; truth cases **1.5** at 1.8; unchanged at 3 and 5 | 0.108 / 0.059 / 0.036 (real logos); synthetic rectangles 0.27 instead of 0.02 at 1.8 | **back at 1.8 px/mm**: Becker 81 right-angle turns per 100 mm vs 27 |
| C. read off entirely | 0.0 / 1.3 / 1.8 on Becker; 1.5 / 4.7 / 5.8 | 0.108 / 0.068 / 0.051 | back at every resolution below the work grid |

Truth-case numbers are the mean over four cases. Full tables:
`docs/renders/subpixel-res-gate-2026-10-11/tables.md`.

## Method

- **Harness**: the 2026-10-10 head-to-head's own scripts (truth runs,
  registration, scores) driven by
  `docs/renders/subpixel-res-gate-2026-10-11/scripts/gate_table.py`. Truth =
  golden_tee and hotel_fremont at their native 21.8 and 31.3 px/mm, stages 0–3.
  Rungs = the same file brought down with `INTER_AREA` to 1.8, 3 and 5 px/mm,
  calibrated on stage 1 so it never reads under the nominal value. Stages 0–3
  run once per rung; bare stage 4 runs on the same masks under each setting.
  Registration (scale + shift) is fitted on the mask's own outline, so no
  setting is favoured.
- **Cases**: both logos in the gradient lane, where stage 0 routes them, and
  each logo's busiest colour layer as a one-ink alpha cutout (Becker's
  class). Becker itself has no truth. It was read at 80 mm (its own 1.81 px/mm)
  and sewn smaller for 3 and 5 (48.3 and 29.0 mm).
- **Reproduces #818**: golden logo at 1.8 reads 0.114 / 0.108 mm and 3.8 / 6.8
  reversals, as the head-to-head's `tables-stage4-flags.txt` did. Becker reads
  0.0 / 7.1 with 1,548 / 1,897 nodes, the same. The derived one-ink cutouts
  differ slightly from 10-10's (golden 0.095 / 0.114 here against 0.085 /
  0.094), because the layer was cut from a fresh truth run.
- **Right-angle turns** (60–120°, `scripts/add_stairs.py`) were added after
  the render. The reversal count can't see a staircase, because a stair step
  turns 90° and never passes 120°. A square corner counts too, so read the
  difference between columns, not the level.
- **Ladder**: `tools/edge_truth_ladder.py`, analytic truth, its 200 / 400 /
  600 px rungs read at the widths that give 1.8 / 3 / 5 px/mm
  (`scripts/ladder_gate.py`).
- **The floor works as specified**: in every row, the floor-3.0 column equals
  OFF at 1.8 and ON at 3 and 5, number for number.

## What this does not show

No stitches and no sew-out. Two logos, two derived cases, one real file, one
run each. `INTER_AREA` models a clean low-res export, not JPEG. The letterform
bites are attributed by their position and by the six MARINE regions carrying
`letterform_prior` in both runs. Nobody rendered `letterform_priors_k=None` to
confirm it.
