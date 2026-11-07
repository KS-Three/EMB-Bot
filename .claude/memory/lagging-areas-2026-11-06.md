---
name: lagging-areas-2026-11-06
description: Kent 11-06 asked which areas lag; top 3 = yardstick (phase 1 exit unmet), satin-vs-fill kappa 0.387, trims/fragmentation; three Sonnet researchers found no external repo fixes any of them, only in-house instruments and oracles
metadata:
  type: project
---

**Kent, 2026-11-06:** "What areas of embot are lagging that need improvement?
Identify the top 3, and release lower level agents to research how they can be
addressed / resolved. Try looking for existing repos."

**Top 3, picked from MASTER_SCOPE (area 1 the only Low) and ROADMAP (phase 1
and both phase 3 exits unmet):** (1) the yardstick: no fidelity instrument
clears chance against Kent's 115 labelled pairs, VLM judge +0.36 on ties/damage
only; (2) satin-vs-fill routing, kappa 0.387 vs ceiling 0.650, per-region oracle
0.365; (3) trims/fragmentation, cuts 391 vs pro 409 but breaks 879 vs 425, fill
sections 32 vs 0. Runner-up photo lane, not researched (active fix session,
Kent 11-05 "do not stack").

**What the three Sonnet notes found** (`docs/lagging-areas-2026-11-06/`):
no open repo ships the discriminator any of the three needs; every 2026
digitizer uses the same width table (kappa ~0.13). Recommendations are
instruments first: (1) score FLIP / LPIPS / DreamSim against Kent's labels on
the 54 live 1102 pairs, a local Qwen-VL second judge in `vlm_judge.py`, InkSim
(GPL, output only) as a cloth-like render; labels are the real gap (49 sides of
115, repeat 1 of 4, renders deleted; keep renders on Drive). (2) `polygon_axis.py`
already IS the polygon-native axis (OFF since the 09-16 "M over-stitched" ruling,
DOCTRINE ~6077), so centerline/pygeoops/straight-skeleton libs are duplicates;
stability fixes buy +0.00 to +0.02; the decider is an oracle ground-splitter in
`satin_fill_census` (>= 0.55 build layering inference, <= 0.45 close it). (3)
Euler-tour fill on networkx (pinned 3.6.1; use `min_weight_matching`, not
`eulerize`), census over the 32 fill-section cuts first; the 488 uncut floats
are gate 1 (`cut_every_jump` + float-ladder sew-out).

**Flagged for Kent:** ROADMAP phase 1's "nothing he judges better ever scores
worse" is zero-tolerance against labels that repeat 1 of 4; needs a tolerance.

**How to apply:** a session picking next work in these areas starts from these
notes, not a fresh repo sweep; the 09-12 / 11-04 / 11-06 sweeps plus these three
cover the field. Related: [[vlm-judge-2026-11-04]],
[[satin-fill-remeasure-2026-10-29]], [[trim-defects-4-6-2026-10-29]],
[[external-repo-sourcing-2026-11-06]], [[free-digitizer-followups-2026-11-05]].

**C3 result (PR #1284, 2026-11-06, Sonnet session):** oracle-split mean kappa
0.381 -> **0.482** over 21 jobs at the 10-cell blob floor (5 cells 0.561, 20
cells 0.427; ceiling 0.649). **Kent's ruling 2026-11-06: keep 10 cells, "no
verdict"** — the layering direction stays open but unproven; no design session
starts on it. A high oracle number is a maximum (reads the pro's blobs), never
what inference from flat art could reach.
