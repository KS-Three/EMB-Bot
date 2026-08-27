# The instrument that had to be rebuilt from its own artifact — 2026-08-27

## What was lost, and what saved it

A previous cloud session built `digitizer/tools/artfidelity_self.py` — the
first instrument in this repo that asks "does our stitch-out look like the
artwork" with **no professional reference** — validated it into an artifact for
Kent, wrote a report-only CI job, and ran a four-parameter search. **None of it
was ever pushed.** The container was reclaimed and all four items went with it.

The next session opened on a fresh clone: `main` at `b9620ac`, working tree
clean, the designated branch sitting exactly on main with zero commits, no open
PRs, no stash, no dangling objects, no worktrees. The code was simply gone.

**The artifact survived, and it was enough.** `claude.ai/code/artifact/
b313a4a6-5089-45ad-a2b2-815c142b1c85` — "Does the metric match your eye?" —
carried the full 14-row table (9 ranked, 5 refused), the three component
definitions in its footer prose, the refusal taxonomy, and every component
value to 3 decimals with the composite to 1.

**The composite weights were recovered exactly, by least squares over those 14
rows.** Solving returns 0.3986 / 0.2498 / 0.3517, sum 1.0001, max residual 0.08
on a 0-100 scale — entirely the artifact's own rounding. So
`ARTFID = 100 * (0.40*coverage + 0.25*colour + 0.35*structure)` is a recovery,
not a guess, and `tests/test_artfidelity_self.py` embeds the table so it stays
one.

**The lesson is the boring one, and it cost a session:** in a cloud container,
unpushed is deleted. Push the branch early even when the work is half-finished.
A published artifact turned out to be a better backup than the filesystem.

## The colour component was got wrong TWICE, and a green suite never noticed

All three readings below are faithful to the artifact's phrase *"median
CIEDE2000 excess over the best available spool"*. Two are **structurally dead**
— and dead the same way, which is the transferable part: **the floor was
something the pipeline had already optimised, so the excess was zero by
construction.**

1. **Floor = best spool the design ALREADY sews** (preflight's
   `_best_loaded_spool_error`). Identically zero — stage 4 has by then snapped
   every region to its nearest loaded spool, so the assigned thread *is* the
   floor. That function is a *rescoring escape*, built to suppress a false
   `THREAD_MATCH_POOR` when a free swap was available and not taken; read as a
   fidelity measure it calls every design perfect. **Measured: colour 1.000 on
   all fourteen fixtures.**

2. **Floor = best SINGLE spool for the whole region**
   (`median(d_assigned) - min_spool median(d_spool)`). Also ~zero, one step
   removed: choosing the chart spool that best serves a region is *exactly what
   stage 4 does*. **Measured: 1.000 on the tonal designs too**, including
   `region_blobs`, which the artifact scored 0.625.

3. **Floor = each PIXEL's own best spool** — the live one. A region is charged
   for the pixels its single assigned thread cannot serve *when a better thread
   for those pixels existed on the chart*. Nothing in the pipeline has already
   minimised that: one thread per region cannot be every pixel's best. This is
   tonal-compression error, which is what the component is named for.

The ordering is the whole component: **subtract per pixel, then take the
median** — not the difference of two medians. `tests/test_artfidelity_self.py::
test_the_subtraction_must_happen_before_the_median_not_after` pins it on a
bimodal region that separates the two readings (dead ~0, live >20).

**What caught it was the corpus run, not the tests.** 30-odd unit tests passed
against reading (1) because a component that returns 1.000 is perfectly
well-behaved. What exposed it was that the artifact's colour column *varies*
and the rebuild's did not. **A component that returns the same value for every
input measures nothing — and this one carried 25% of the composite's weight
while doing so.** Diff a new instrument's whole column against a known one
before believing any single row.

A second trap on the way: preflight's "pooling was this instrument's original
sin" ruling was **over-applied** here at first, and it pushed the rebuild toward
reading (2). That ruling is about collapsing a region's pixels to one summary
*colour* before measuring. Aggregating per-pixel *errors* is a different act —
preflight does it itself inside every region. Read what a ruling forbids, not
what it sounds like it forbids.

## What is recovered, and what is only stated

Recovered: the component definitions, the composite weights, the refusal
taxonomy and which fixtures fall in it. **Not recoverable, therefore stated
choices flagged at each constant:** ink-mask threshold, registration window and
step, SSIM scale count and window, the colour scale constant
(`DELTA_E_CLEARLY_DIFFERENT`, 10.0), the subject-mismatch cut (3.0), and the
per-region floor subsample.

So **the artifact's table is a historical record, not a reproduction target.**
The rebuild's first run is a NEW baseline; comparisons start there. Do not
report a delta against that table as an engine change.

## Related

- The instrument: `digitizer/tools/artfidelity_self.py` (its module docstring
  carries the provenance in full).
- Siblings it deliberately matches at `RES = 10.0`:
  `digitizer/tools/pro_parity/{artfidelity,bare,holecrop,forkprobe}.py`.
- The CI job: `art-fidelity-baseline` in
  `.github/workflows/python-package-conda.yml` — report-only, main-only,
  `continue-on-error`, existing to capture the **Linux** baseline because these
  numbers are platform-sensitive the same way the three deselected goldens are.
- ROADMAP phase 1's exit condition is the question this instrument asks, and
  hard gate 4 is why `--components` exists.
