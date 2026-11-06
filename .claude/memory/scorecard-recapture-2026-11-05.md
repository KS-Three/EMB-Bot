---
name: scorecard-recapture-2026-11-05
description: Corpus scorecard recaptured 2026-11-05 on GitHub Actions (new `Corpus scorecard` workflow_dispatch: diff / capture); A/B/C/D/F 9/18/7/6/12 -> 10/20/8/10/4, mean 61.8 -> 71.9; the rise is THREAD_MATCH_POOR quiet on gradient (#1200); Fremont F 28/16 both garments; the WSL pool diff is the fast local read.
metadata:
  type: project
---

2026-11-05, Kent's audit session, branch `claude/scorecard-capture-1105`.
Doc: `docs/scorecard-baseline-attribution-2026-11-05.md`. Ruler moved
`d000e370` (10-05) -> `292418a8` (pipeline tree `fb682ef9`).

**What happened.** 546 pipeline commits had landed under the 10-05 ruler.
The WSL box scored `origin/main` in 18.9 min (`/root/scorecard_pool.py 6`,
cwd a fresh `/root/wt-*` worktree's `digitizer/`); the committed capture ran
on `ubuntu-latest` through `.github/workflows/scorecard-capture.yml`, which
is now the capture button (COOKBOOK rule 3). Remote Control cannot start a
cloud session from a session, which is why the workflow exists.

**Numbers.** 30 of 52 rows moved: 19 up a band, 10 down. Eight of twelve Fs
gone, all `THREAD_MATCH_POOR` blocks resolved by #1200
(`thread_match_excess_gradient` ON, 10-30); its 10-29 doc's own per-row
OFF/ON table predicted 10/20/6/12/4 and is the mid-interval anchor that
splits attribution into 10-05 -> 10-29 drift and post-10-29 flips. Falls:
Fremont B -> F 28 / F 16 (two `0020 Black` dE-100 blocks, recorded 10-29,
excess cannot clear a real reassignment; Linux and WSL agreed on 51 of 52
rows, the one gap an OCR verdict on this row); `LETTERING_TOO_SMALL` on `logo_alpha`,
`logo_whitebg`, sunset (Column lane reads synthetic text as lettering,
#863 / #955); `DENSITY_STACKED` on chrome hat, dof_meadow, sunset (photo
lane, 2-24% more stitches, kept frame #1179 suspected, not rendered).

**Why:** the grade is preflight conformance, phase 1 is open, so a ten-point
rise is a check going quiet, not a better sew-out (gate 4).

**How to apply:** for a fast local read of today's grades, run the WSL pool
script on a fresh worktree (18 min); for anything committed, dispatch the
workflow (`-f mode=capture`), download `scorecard-capture-<run id>`, and
attribute every mover against the previous ruler before committing. Bare
`node --test` at the repo root now swallows `scratch_bench/` (heatstitch
clone, 201 TypeScript fails, exit 1): run `node --test "test/**/*.test.js"`.
See [[thread-match-excess-gradient-2026-10-29]], [[stage0-texture-gate-2026-10-28]].
