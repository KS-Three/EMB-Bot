---
name: nightly-tripwire-2026-11-02
description: Nightly regression tripwire over the 18 committed pro pairs (tools/tripwire.py, testdata/tripwire_ledger.json, nightly-tripwire.yml); the population and why, how tolerances are seeded from three runner passes, what a red means, and the traps paid for
metadata:
  type: project
---

**Built 2026-11-02** (architecture review item 4; `digitizer/tools/tripwire.py`,
`digitizer/tests/test_tripwire.py`, `.github/workflows/nightly-tripwire.yml`,
ledger `digitizer/testdata/tripwire_ledger.json`). `measure` digitizes every
committed pair once at the pro's size through `tools.pro_baseline` (Studio
request, one pystitch reader for ours and the pro's DST) and writes a pass;
`capture --from PASS...` turns passes of the SAME tree into the ledger
(baseline = lower median, tolerance = max - min rounded UP to the figure's
resolution: 1 count, 0.1 mm, 0.01 kappa); `check` compares a run against the
ledger with each figure's worse-direction and exits 1 on a wrong-way change
past tolerance, on a figure the run lost, or on a pro-side figure that changed
(the READER changed, so the compare is void). Figures: stitches, trims (cuts),
hops, needle-up mm (up is worse); stitch-type kappa with its chance floor,
direction kappa, word cc at native size (down is worse). No raw agreement in a
pass, the ledger or a table (`validate_ledger` refuses the key, gate 4).

- **Population = 18, not 5.** `pro_baseline.JOBS` filtered to art under
  `testdata/` AND a pro DST in the repo. Only Becker's five are loose in
  `testdata/reference/`; the rest sit inside the committed `Embroidery
  Files.zip` at the repo root (Gaulke x3, Fremont x2, MFab x2, Drone, Tires,
  Golden Tee, To a T x3), a known exposure per the root CLAUDE.md. Bridge
  (files outside the repo) and ProSeal (art not committed) are out. On a
  machine without `scratch_kent/` the tool extracts the 32 needed members
  into `RUNS/_kent` and points `EMB_SCRATCH_KENT` at it; the zip's `To a
  T:Becker Beanies` folder (a macOS colon) is renamed to the `To a T-Becker
  Beanies` the code tables use (`ZIP_RENAMES`).
- **Nightly, never per PR, never required.** Its own workflow: `schedule`
  (06:23 UTC, fires only on `main`) + `workflow_dispatch` (mode `check` or
  `capture`). Capture runs the tree on THREE runners (matrix) and a fourth job
  builds the ledger from their spread; the ledger is re-seeded by dispatching
  capture after a deliberate change and committing the `tripwire-ledger-<run>`
  artifact. Linux numbers only (the deselected goldens and
  art-fidelity-baseline's comment both say Windows is not comparable).
- **MFab and Tires run WITHOUT rembg on the runner** (no `rembg_isolated`
  venv in CI), so their ledger rows describe the classical route; the pass
  records `env.rembg_venv` so a reader can tell. Same as every CI test run.

**Why:** a PR could move any pair's cuts, hops, needle-up or kappa the wrong
way and go green: byte goldens pin frozen engines, the scorecard baseline was
weeks stale, and the two push-to-main report jobs are `continue-on-error` with
no tolerance. A tolerance from a desk is a preference; one from the runner's
own run-to-run spread is a measurement.

**How to apply:** a red nightly names the job and figure; attribute it to the
day's merges with the artifact's `ours.dst` and figures.json before touching
the ledger. A deliberate change re-seeds via capture, never by hand-editing a
tolerance. Traps paid for: the KS-Three `gh` token had no `workflow` scope,
so a new workflow file cannot be pushed from Kent's box until
`gh auth refresh -h github.com -s workflow` (Kent's call 11-02: refresh, do not
switch logins); a Git-Bash `/c/Users/...` path handed to Windows Python lands
under `C:\c\Users\...` (other sessions had done it too: `C:\c` holds their
strays); the worktree guard fails closed on a heredoc whose text says "move"
beside a worktree path, so edit docs with the Edit tool. Related:
[[yardstick-pro-pair-2026-11-01]] (the trim family is what clears chance),
[[lettering-board-2026-10-25]], [[flip-proof-pins-2026-10-27]],
[[stage0-flake-output-alignment-2026-10-25]] (why passes agree bit-for-bit).

**Measured (first Linux capture, run 41513783169, engine 0ec42770):** three
runner passes agreed EXACTLY on all 111 rows (18 jobs; words for 3), so every
tolerance is 0 and "spread seen" is 0. That is a measurement, not a default:
the engine is bit-stable across runners under `OPENCV_IPP=avx2`. Consequence:
ANY merge that moves a pair's figure the wrong way reddens the nightly, and a
deliberate change re-seeds by capture. Passes took 7-8 min each (laptop
dry run budgeted far more); the capture job 38 s.
