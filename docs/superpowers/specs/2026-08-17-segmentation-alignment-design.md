# Segmentation-alignment fix for the satin/fill straddle headroom

**Status: DRAFT — awaiting Kent. Phase 3 territory; nothing here is scheduled.**

## Recommendation: do not build this

The measurement this spec was supposed to be gated on
(`docs/segmentation-alignment-2026-08-17.md`) came back negative. Item 7 of
the measurement-debt plan asked what KIND of satin/fill straddling caps the
oracle at 76.6% (`docs/satin-gate-attribution-2026-08-16.md` §4), because the
answer decides the mechanism: `ring` → border-satin generation, `split` →
region-splitting at an artwork boundary. Measured over the 15-design real
corpus, neither dominates:

| pattern | shapes | cells | share of straddled cells |
|---|---|---|---|
| `speckle` | 50 | 4,073 | 95.8% |
| `split` | 42 | 161 | 3.8% |
| `ring` | 2 | 19 | 0.4% |

`speckle` — cell-scale mixing with no dominant border/interior split and more
connected components than a clean partition — dominates by a wide margin.
That reads as registration/cell-grid noise, not a systematic segmentation-
boundary error a region-level mechanism could target. **No mechanism is
proposed below for `ring` or `split`, because even a perfect implementation
of both recovers at most 180 of 8,539 graded cells (2.1%) on this corpus** —
nowhere near the 20+ points of headroom the oracle ceiling implies. Building
either would be shipping engine complexity against a headroom the data says
is mostly somewhere else.

This document exists to record that the gate was checked, honestly, and
failed — not to propose the mechanism the plan anticipated. The rest of this
spec states what WOULD have been proposed had one pattern dominated, purely
so the reasoning and the acceptance bar are on record if a future
measurement (different corpus, better registration, finer cell grid) changes
this verdict.

## What was measured

See `docs/segmentation-alignment-2026-08-17.md` in full. Summary: 446 of 619
region-shapes across 15 designs land on ground the pro also sewed (8,539
graded cells); 49.8% of those cells sit in a straddled shape (matching the
attribution doc's 48.1% "under 75% one type" figure); within that straddled
population, `speckle` is 95.8% of the cells, `split` 3.8%, `ring` 0.4%.
`ring` — the classic "pro satins the outline, fills the body" — occurs in
only 2 of 15 designs and 19 total cells; it is not a real pattern in this
corpus, not a measurement artifact of a small sample.

## If a future measurement found `ring` or `split` dominant

Recorded for reuse, not proposed now:

- **`ring` dominant** → border-satin generation sized off the pro's measured
  band width distribution from `splitprobe.py`'s per-shape CSV (`cells`,
  `purity` columns; band width would need a new column — the current CSV
  does not carry it, since `ring` never needed sizing on this corpus).
  Mechanism: for a region `classify_straddle` reads as `ring`, generate a
  satin border stroke at the measured band width around the existing fill
  region, rather than re-segmenting.
- **`split` dominant** → boundary detection restricted to artwork-visible
  edges (colour/luminance boundaries in the source art), citing where the
  straddled shapes' partition lines sit relative to those edges — not a
  generic re-segmentation, which risks manufacturing boundaries the artwork
  does not have.

## Acceptance criteria (if built)

- **Primary: corrected kappa for stitch type must rise**, measured by
  `scorecard.py`'s `parts["sttype"]` over the corpus, per
  `digitizer/tools/pro_parity/kappacheck.py` — the same instrument Task 1
  used to verify the satin-routing promotion. This is ROADMAP hard gate 4:
  the acceptance bar is corrected kappa, not raw agreement or composite
  score.
- **Secondary: total corpus score must not regress.**
- **`ring`/`split` cell counts must not have been cherry-picked** — measured
  on the full 15-design corpus, not a subset chosen post hoc.
- Golden churn presented to Kent, never auto-captured, judged in CI not on
  Windows, per the standing ruling.

## Non-goals

- **No engine change until Kent schedules it.** This is Phase 3 territory;
  the ROADMAP ordering that puts it there is advisory-only, but nothing here
  authorizes writing engine code.
- **No default flips.** Even if built, this would not change default
  segmentation behavior without a separate, explicit rollout decision.
- **No synthetic fixtures**, per ROADMAP hard gate 2's spirit — any future
  measurement of this question stays on real customer artwork against real
  professional digitizations, the same corpus this spec's own measurement
  used.
- **No claim that speckle is unfixable in principle** — only that it is not
  a region-level segmentation fix, and diagnosing it (registration
  precision? cell-grid resolution? something else?) is unscoped, separate
  work this document does not propose.
