---
name: goldentee-swoosh-hairline-2026-11-18
description: "2026-11-18 prime-grader pin (10,8) Golden Tee swoosh outer 'hairline sewn heavy': the pro sews it as a ~1.0 mm black satin band too (ours 1.33); saw teeth = satin end caps (pro scallops too); no code; hairline ON thins every edge (wrong); satin_hairline_tier no-op"
metadata:
  type: project
---
Reproduced on main, not a fault vs the pro. Outer band ours 1.33 / pro 1.0 mm, inner 1.9 / 2.0; edge jitter 0.49 vs 0.34 px at 12 px/mm. Excess 0.3 mm = satin cross floor + pull (gate 1). `satin_hairline_tier` changes nothing here; global `hairline` thins G/T/GOLF edges the pro keeps thick. Doc: `docs/goldentee-swoosh-hairline-2026-11-18.md`. How to apply: before building a "bean the hairline" cure, measure the pro's band; a pro that sews 1 mm satin is the target, not a run.
