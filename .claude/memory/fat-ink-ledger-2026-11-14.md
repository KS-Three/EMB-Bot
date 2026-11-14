---
name: fat-ink-ledger-2026-11-14
description: "2026-11-14 — width ledger (`tools/width_ledger.py`) on 7 designs: ours ~= the pro's ink area on Becker/Bridge; width enters at stage-5 fill/column pull (round joins) and stage-6 satin rails + thread; `pull_comp_along_stitch_only` + `growth_keeps_gaps` built OFF in stage 5"
metadata:
  type: project
---

# Fat ink: where the width enters — 2026-11-13/14

The Director's brief after Kent's 11-12 sitting (merged letters, closed
counters, lost spacing: the biggest stitch-side pin cluster). Tool:
`digitizer/tools/width_ledger.py`; captures, ledgers, sheets:
`digitizer/eye_pairs_out/fat-ink-1113/` (primary checkout, gitignored).

**Method.** One digitize per design keeps every stage (art raster, stage 4,
after the re-set, stage 5 planned, needle, thread, the pro's file registered
by `pro_parity.pairframe.register_pair`). Each footprint is a map of the
VISIBLE colour, painted in sew order (a white keyline over a black band is the
gap it is). Six strokes and four gaps/counters per design are read at the
ART's own medial points.

**Findings (OFF, studio request at kit / pro size).**
- Ink area, thread over art: Becker 1.18 vs the pro's 1.19, Bridge 1.09 vs
  1.09, MFab 1.12 vs 0.95. The earlier "ours 18-30% heavier, pro within 1%"
  (`agent-eye-1113/width_check*.json`) was a dark-pixel read of shaded
  renders; drawn the same way, the pro's thread is as heavy as ours on two of
  three. Area is not where we differ; local gaps and corners are.
- Where it enters: fills and Column-lane lettering grow at STAGE 5 by an
  isotropic `buffer(pull)` with round joins (Becker's lettering satins +0.96 mm,
  Jakarta's fill triangle +0.58 and rounded, MFab's keyline gap 1.55 -> 0.92 at
  stage 5 alone). Plain satin takes the pull on its RAILS in stage 6 (+0.2-0.3)
  and the thread adds 0.3-0.4: Jakarta's a counter 1.8 -> 1.0, k_line's two
  0.5 mm counters shut.
- Not width: Bridge's thin satin letters (0.86-1.02 mm art) are traced
  1.33-1.70 mm at stage 4 (a floor in stages 2-4).

**Built OFF (stage5_overlap.py, `cfg.extra`).** `pull_comp_along_stitch_only`:
a fill grows only along the axis it sews (square corners). A fill with no angle
of its own: stage 5 runs once with neither flag (`_off_angles`) and hands stage 7
the angle stage 6 picks on THAT shape, under either flag. Three builds that
guessed the old shape turned Bridge's round field 90 -> 102, 78, 34 degrees: on
a round field the pick is a near tie any change tips. Check row angles (design
runs, `fat-ink-1113/scripts`) on any change to a fill's planned shape. `growth_keeps_gaps`:
growth stays out of bare fabric the art keeps between shapes (>= 0.5 mm any
colour, any gap on one thread) up to 2 mm, and counters of that width keep
their art size. Magnitude (`Fabric.pull_comp_mm`) untouched: gate 1.

**Named, not built:** the satin rail emitter's growth into counters and gaps
(stage 6, another lane; #1479 open); the Column lane's isotropic growth at the
column ends; the stage-4 floor on Bridge's thin letters.

Related: [[eye-first-diagnosis-2026-11-13]], [[reset-one-baseline-2026-11-13]].
