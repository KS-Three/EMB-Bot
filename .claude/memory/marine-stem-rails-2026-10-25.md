---
name: marine-stem-rails-2026-10-25
description: "MARINE M-stem rail wobble 0.19-0.25 vs the pro's 0.03" (#1052) measured FALSE -- the refit stems are straight lines and the rails sit on them; every rail_jitter station over 0.15 mm is a rail turning a corner or a stray split penetration, none a straight stem. The pro's 0.03 is his cuts at notches (L6). `tools/rail_jitter_cause.py` classifies; nothing built
metadata:
  type: project
---

2026-10-25, task 1 of the director's wave, lane `marine-stem-rails-92fdea`.
Brief: build `letterform_priors_long_stems` because `letterform_priors` left
MARINE's stems wobbling. **Premise measured false; record-only PR, no engine
change** (director's call).

**The number reproduces.** `letter_band.rail_jitter` p90 on the M, four Becker
files at the pro's widths (hat / chest small 76.5, LC large 95.7, hat large
101.9): ours 0.21-0.26, the pro's 0.025-0.033.

**It is not wobble.** (1) `letterform_priors` refits all 6 letters on all 4
files (tol 0.40 / 0.52, unexplained <= 0.008): not grid-gated, not refused.
(2) The refit stem edges are ONE straight line each; the Column lane's rails
sit on them at the 0.28 pull, std 0.004-0.015 mm -- neither the outline nor
[[rail-wobble-is-the-models-floor-2026-09-21]] (that floor is the skeleton
tier's; Column rails are the outline). (3) Stem window (35-92% of the cap,
below the slab; upright pieces; one reader on both DSTs): ours 0.013-0.042
on 19 of 24 letters (the DST's 0.1 mm rounding), the pro's 0.000 -- his
stems land on one grid column. The rest (our LC-large M 0.137, hat-small R
0.104, A 0.06-0.10; HIS E 0.22 on both large files) are pieces folding
through a corner inside the window; their stations classify corner. (4) Every station over 0.15 mm classified (`tools/rail_jitter_cause.py`,
fused rails): 318 CORNER (the slab's reflex notch, the M's V crotch, the A's
counter / feet), 49 STRAY (a split leg or short stitch read as a rail), 6 on
R's curved bowl, **0 on a straight stem in any file**.

**Why the pro reads 0.03:** he cuts a piece at every notch (10-11 per M,
[[big-letter-construction-2026-10-24]]), so each piece's rails are straight.
Construction, not a smoother edge.

**What the eye would see instead:** LC large's M top half (slab + V) sews as
big FANS through the V crotch -- construction in `columns.py` /
`outline_cut.py`, sent to the apex-cuts worker (task 2).

**Why:** the 10 mm+ band ([[lettering-10mm-up-band-2026-10-23]]) listed it as
outline wobble from the 146-px art; a brief to build a stem refit followed.
**How to apply:** retire "MARINE stem wobble"; quote `rail_jitter` only per
straight piece (`rail_jitter_cause.stem_window`), never per letter on a
cut-vs-folded comparison; before blaming an outline, check the rails against
the REFIT polygon, not the trace -- `letterform_priors` runs before both.
