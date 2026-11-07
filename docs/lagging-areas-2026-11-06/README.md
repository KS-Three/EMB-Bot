# Lagging areas, 2026-11-06: the top three and what exists to fix them

Kent asked (11-06): *"What areas of embot are lagging that need improvement?
Identify the top 3, and release lower level agents to research how they can
be addressed / resolved. Try looking for existing repos that can be utilized."*

Picked from `MASTER_SCOPE.md` (at-a-glance: area 1 is the only Low) and
`ROADMAP.md` (phase 1 exit NOT met; phase 3's two exit clauses NOT met). One
Sonnet researcher per area, read-only, each note under 2,500 words with every
repo claim marked [V]/[U]. Prior sweeps (09-12, 11-04, 11-06) were read first and
not repeated.

| # | Area | Where it stands | Note | Verdict in one line |
|---|---|---|---|---|
| 1 | Yardstick (ROADMAP phase 1) | no fidelity instrument clears chance against Kent's picks over 115 pairs; VLM judge +0.36 on ties/damage only | [1-yardstick.md](1-yardstick.md) | No library fixes it. Labels are the gap (49 sides of 115, repeat 1 of 4, renders deleted). Prototypes: FLIP / LPIPS / DreamSim scored against his labels; a local Qwen-VL second judge; InkSim cloth render (GPL, output only) |
| 2 | Satin-vs-fill routing (defects 5, 26; phase 3) | kappa 0.387, ceiling 0.650, per-region oracle 0.365 | [2-satin-fill.md](2-satin-fill.md) | No external fix. In-house `polygon_axis.py` already is the polygon-native axis (OFF since 09-16). Stability fixes buy +0.00 to +0.02. The decider is C3: an oracle ground-splitter that says whether layering inference is worth building |
| 3 | Trims / fragmentation (defects 4, 6; phase 3) | cuts 391 vs 409, breaks 879 vs 425, fill sections 32 vs 0 | [3-trims-fragmentation.md](3-trims-fragmentation.md) | Almost nothing to adopt. One in-house PROTOTYPE: Euler-tour fill on networkx (already pinned), census first. The 488 uncut floats are gate 1: `cut_every_jump` + a float-ladder sew-out |

**The shared shape of all three:** the gaps are discrimination and labelling
problems; no open repo ships the discriminator, and every 2026 digitizer uses
the same width table (kappa ~0.13). What the notes recommend is instruments
and oracles first, each with a chance-corrected pass/fail, before any engine
change.

**Runner-up, not researched:** the photo lane (area 1 Low, faces TABLED,
defect 20's density). It has an active fix session and Kent's 11-05 ruling
not to stack on it.

**Flagged for Kent (from note 1):** ROADMAP phase 1's exit clause *"nothing he
judges better ever scores worse"* is zero-tolerance against labels that repeat
1 of 4; it needs a tolerance he sets, or it can never be met.

Nothing here is built, flipped or committed to a ruling. Costs: 1-2 sessions
per prototype; cheapest first experiments are note 2's C3 oracle (measurement
only) and note 3's fill-section census (no engine change).
