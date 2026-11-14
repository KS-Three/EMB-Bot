---
name: second-digitize-timing-2026-11-13
description: "Second digitize 3x slower" (walkthrough 11-12) is laptop contention, not a defect; Cancel freed the worker only after 1.4-5.5 s until seams went into stage 4's lettering loops and the keyline
metadata:
  type: project
---

The 11-12 walkthrough's 12-15 s then 44 s "after a Cancel" is **machine contention**. Measured on Becker at 96 mm with `digitizer/tools/second_digitize_timing.py` (its own service on :8799, seam-logging probe, `typeperf` load). B/A was 0.79-1.10 and C/A 0.55-1.26 in every repetition. The same cold run swung 19.1 s -> 54.8 s in 15 min as other load went from 1.4 to 7.3 cores of 8. Run CPU grew too, about 21 -> 47 s over the afternoon, on origin/main's engine as much as ours (interleaved A/B).

The real defect was small: Cancel left the single worker busy for 1.4-5.5 s, and the next run queued for up to 3.4 s. The cause was three seam-free stretches:

- `textcluster._neck_split`'s piece loop (393 pieces on Becker's ring, 5 s)
- `plan_letterform_priors` (about 0.4 s per letter)
- `stage6_border.keyline_runs` / exact `_satin_loop` / `_bury_walks`

Seams now sit in all three ("text cluster neck splits", "letterform priors", "keyline"; `tests/test_cancel_seams_1113.py`). After the fix the worker is free within 0.0-0.21 s and C queues for 0.01 s. Doc: `docs/second-digitize-timing-2026-11-13.md`.

**Why:** a timing claim made on a busy laptop needs the load measured over the run, not one snapshot. That laptop never had a quiet window that afternoon.

**How to apply:** before calling a slow run a regression, compare its wall time with its CPU time and the other-process load (`second_digitize_report.py` columns). Related: [[service-timeout-cancel-2026-10-30]], [[stage7-scene-speed-2026-10-29]].
