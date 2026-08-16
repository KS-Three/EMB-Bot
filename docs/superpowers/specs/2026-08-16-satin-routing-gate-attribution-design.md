# Satin/fill routing — gate attribution, then a targeted promotion path

**Status: BOTH SLICES LANDED 2026-08-16. Results and the numbers that changed
this plan mid-flight: [`docs/satin-gate-attribution-2026-08-16.md`](../../satin-gate-attribution-2026-08-16.md).**

Two things in this document were overtaken by its own measurement, kept rather
than rewritten because the corrections are the point:

- §4's width floor is **not built** — measurement disproved it for flat art (61
  of 64 sub-1mm satin shapes are ground the pro also satins). See that doc §7.
- §4's promotion path shipped with a second term this spec did not anticipate.
  `explained` alone promoted the benchmark starburst back to satin; an
  elongation floor was needed, and an existing test caught it.

Closes MASTER_SCOPE live defect 5 (satin-vs-fill routing sits at chance) and
live defect 2 (no width floor under satin) as one piece of work, because both
are the same code point behaving as a one-way tightening ladder.

## 1. The defect, as measured

Against the 23 professional designs, over 15,953 shared 2 mm cells
*(measured 2026-08-14 — confusion matrix, `docs/scope/1-auto-digitizing-quality.md`)*:

| pro \ ours | run | satin | fill | share of ground |
|---|---|---|---|---|
| run | 0 | 15 | 32 | 0.3% |
| satin | 324 | 5,241 | 2,991 | 53.6% |
| fill | 294 | 2,348 | 4,708 | 46.1% |

Marginals nearly agree (pro 53.6% satin / 46.1% fill against our 47.7% / 48.5%)
while per-place agreement is 0.624 raw against a 0.479 chance floor — **0.278
corrected**. The engine sews the right *amount* of satin in the wrong *places*,
so the two errors cancel in every metric that looks at totals. Retuning
`satin_max` cannot fix it: a wider cap buys satin where we already over-satin.

**Structural cause.** `is_satin_candidate` (`stage6_satin.py:185`) is three
consecutive *rejection* gates:

1. `ribbon_width_mm(poly) > max_width_mm` — the 5.0 mm cap,
2. `length_est < 3·w` — aspect, off half the perimeter,
3. `_dt_regular_and_within_cap` — `2σ ≥ μ` at skeletal pixels, or `p90 > cap`;
   its own docstring calls it "a pure TIGHTENING, it can only turn a satin call
   into a fill call, never the reverse".

There is no path that promotes a shape any gate rejected. So every
pro-satin-sewn-as-fill cell is one of those three firing, and the reverse errors
are shapes that passed all three and should not have.

## 2. Why measurement comes before the fix

The obvious hypothesis — script and dimensional lettering carries thick-and-thin
strokes, inflating σ, so the regularity gate rejects it (`tires_hat_3d`: pro sews
98.3% satin, we sew 81.5% fill) — is a story, not a measurement.

This repo has been flattered by a plausible-but-wrong signal four separate times
(`docs/handoff-2026-08-16.md` §3). Slice 1 exists so slice 2 targets the gate
that is actually doing the damage.

## 3. Slice 1 — gate attribution. No behaviour change.

### 3a. Refactor for visibility

`classify_ribbon(poly, cap) -> RibbonVerdict(satin: bool, reason: str, metrics: dict)`
becomes the implementation; `is_satin_candidate` becomes a thin bool wrapper, so
no caller changes and no stitch coordinate moves.

- `reason` ∈ `width_cap` | `aspect` | `dt_irregular` | `dt_p90_cap` |
  `dt_degenerate` | `satin` — the FIRST gate that fired, matching the existing
  short-circuit order exactly.
- `metrics`: `ribbon_w`, `length_est`, `aspect` (`length_est / w`), `dt_mean`,
  `dt_std`, `dt_cv` (`σ/μ`), `dt_p90_mm`, `area_mm2`.

Acceptance: `tests/test_satin.py` passes unchanged (51 tests, green at
`8d4e8e0`), plus new cases asserting each `reason` value is reachable and that
`is_satin_candidate(p, c) == classify_ribbon(p, c).satin` on the four letterform
archetypes.

### 3b. The probe

`digitizer/tools/pro_parity/gateprobe.py`. Per shape, per design: the verdict and
metrics above, joined to the pro's ground truth for that shape's cells using the
scorecard's own `cell_stats` and registration — the same comparison the score
reports, not a new one.

Output: a CSV plus a summary that answers one question — **of the pro-satin
ground we sew as fill, which gate rejected it, and by how much did it miss?**
"By how much" is the margin in the gate's own units (mm over the cap, aspect
below 3.0, `dt_cv` above 0.5), because a fix is only cheap if the misses cluster
just past the line.

### 3c. Population

Both lanes:

- the 23-design reconstructed corpus (`prep_all.py`) — where the confusion matrix
  above came from, so the numbers line up;
- the 15 real-artwork designs (`prep_both.py`) run with `forced_class='flat'`,
  because 10 of them are stage-0 misrouted into the photo lane and never reach
  the satin/fill ladder at all. Kent labelled 14 of the 15 flat
  (`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`
  §3), so forcing flat is honest here and keeps the stage-0 blocker off this
  work's critical path.

### 3d. Where it runs

The pinned worktree, per the standing ruling — three baselines were invalidated
on 2026-08-15 by commits landing mid-run. Verify module resolution hits the
worktree's own `digitizer_core`.

## 4. Slice 2 — the fix

Scoped by slice 1's table, so the detail is deliberately not fixed here. Two
parts are committed to regardless:

**The promotion path.** Whichever gate accounts for the bulk of the pro-satin
ground we fill gets a second opinion that can say *yes* — the ladder stops being
one-way. Shapes rejected by a gate at a margin slice 1 shows to be noise-sized
are promoted back to satin.

**The width floor** (live defect 2). 19 of 162 corpus regions sew sub-millimetre
satin — thread piles and the needle re-punches the same hole. `2·p90 < ~1.0 mm`
reroutes to a run stitch. The exact threshold comes from a sweep, not from this
document.

### Acceptance

- **Primary: corrected kappa for stitch type must rise**, measured by
  `scorecard.py`'s own `parts["sttype"]` over the corpus. This is the direct
  measure of the defect. The total parity score is NOT the primary criterion —
  its own ceiling is 75-84 (`selfconsistency.py`) and it moves for reasons
  unrelated to this work.
- **Secondary: total corpus score must not regress.**
- **Golden churn is presented to Kent, never auto-captured** — and judged in CI,
  not on Windows, per the standing ruling on the three platform-divergent
  goldens.
- No sew-out claim. Everything here is geometry agreement with a professional
  digitization, which is the best proxy available and not the same as thread on
  fabric.

## 5. Explicitly out of scope

- Stage 0's flat/gradient gate — blocked on artwork, tracked in its own spec.
- Retuning `SATIN_MAX_WIDTH_MM` globally (measured: cannot fix a placement
  defect).
- `_DT_TIGHTEN_PERCENTILE`'s never-swept 70/80/95 question, unless slice 1 puts
  it on the critical path.
