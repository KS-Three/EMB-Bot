---
name: scorecard-recapture-2026-11-12
description: Corpus scorecard recaptured 2026-11-12 at ffefc3b1 (run 43253187536); 10/20/8/10/4 -> 8/20/6/10/8, mean 71.9 -> 68.7 FELL: #1301 flat-lane THREAD_MATCH_POOR, #1263 photo under-fill, #1329 clears Fremont; flag-off CI arms attribute all but one row part
metadata:
  type: project
---

2026-11-12, worker session `claude/scorecard-recapture-1112-309ccc`. Doc:
`docs/scorecard-baseline-attribution-2026-11-12.md`. Ruler `292418a8` ->
`ffefc3b1`. Kent: "Yes, recapture" (11-12). [[scorecard-recapture-2026-11-05]]
is the method; the `Corpus scorecard` workflow ran capture + diff on `main`.

**Numbers.** 28 of 52 rows moved: 5 up, 14 down, 9 inside a band; 10/20/8/10/4
-> 8/20/6/10/8, mean 71.9 -> 68.7. The mean FELL (first recapture that did).

**How attributed, new this time.** Throwaway branches off main with a group of
flipped defaults set back, each dispatched with `gh workflow run
scorecard-capture.yml --ref <branch> -f mode=capture` (25 min, run in
parallel, config-only branches, deleted after). The all-flags-off arm
reproduced the old baseline on 51 of 52 rows, so every mover is a flip:
#1301 (stage 0 flat route: `THREAD_MATCH_POOR` on bg_uncertain, bridge,
golden_tee, screenshot, white_icon; trims on gaulke), #1263 (photo under-fill
gate: `DENSITY_STACKED` cleared, `STITCHES_TOO_SHORT` on chrome LC / sunset LC),
#1329 (Fremont F 28/16 -> B 88/76), #1378 (summit +10). #1396
(`enclosed_white_skip_transparent`) moved logo_alpha / drone metrics, no grade.
One row part unattributed: golden_tee hat B 76 -> C 64 (`LETTERING_ILLEGIBLE`,
OCR candidate #1277).

**Kent's ruling 2026-11-12** (relayed by the director): "Land as is
(Recommended)" after seeing the mover table (mean fell, F rows 4 -> 8). Landed
as captured; golden_tee hat B 76 -> C 64 stays unattributed, no bisect arm.

**Why:** grade is preflight conformance (gate 4); a fall here is checks firing
on the flat lane, not a rendered or sewn regression.

**How to apply:** next recapture, reuse the arm method instead of bisecting.
Trap hit: `git commit -am` in the lane carries an installed working-tree
baseline into the arm branch; commit `config.py` by path. The Bash hook blocks
`python -` heredocs: write a script file and run it by path.
