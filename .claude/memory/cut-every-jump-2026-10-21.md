---
name: cut-every-jump-2026-10-21
description: `cut_every_jump` built OFF — every uncut needle-up move buried under later thread, else cut + locked; 9 jobs 285 uncut -> 0 but trims 434 -> 674 (pro 246), Fremont 80 -> 186 (pro 21); gate 1 sew-out
metadata:
  type: project
---

Settings-vs-pro row 25: the pro's 28 DSTs leave NO needle-up move uncut; we
left 285 short jumps (0.5-3.0 mm) over nine paired jobs. `cfg.cut_every_jump`
(built OFF 2026-10-21, `stage7_sequence._cut_or_bury_jumps`) sews each one
needle-down where thread sewn LATER hides it (`trim_bury_under_later`'s cover,
now shared as `_later_thread_burier`), and otherwise cuts it with
`apply_ties`' locks (`stitches.tie_in` / `tie_off`).

- **Order from the pro's files:** of his 59 non-colour cuts of 3 mm or less,
  1 lies under later thread (`tools/trim_classes.py`, 27 DSTs) — so bury first.
- **Measured, nine jobs, read from the DST:** uncut 285 -> 0; 45 sewn down,
  240 cut; trims 434 -> 674 against the pro's 246; stitches +2.0%; new thread
  on bare fabric 0.0 mm on every job; OFF md5 = base on all nine.
- **The catch:** Fremont hat trims 80 -> 186 against the pro's 21. He has no
  short hops to cut because he builds fewer pieces; cutting ours copies his
  rule, not his result.
- Composes with `trim_bury_under_later`: that pass turns CUT hops in art
  blocks into travel and runs first; this one handles UNCUT jumps in every
  block and runs last. Disjoint hops, same cover rule.

**Kent 2026-10-21: sew-out arm first** — Fremont hat OFF beside ON on the
next card; stays OFF until then.

**Why:** a session told "the pro cuts every jump" would flip this and
2x Fremont's trims. **How to apply:** the flip is Kent's after a sew-out
(gate 1: trimmer wear and tie knots against floats). Related:
[[trim-economy-2026-10-21]], [[pro-trim-threshold]].
