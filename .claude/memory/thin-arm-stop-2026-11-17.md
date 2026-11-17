---
name: thin-arm-stop-2026-11-17
description: Toat Machine's script M sewed a fan of crossing stitches over each thick stem top where the hairline joins; satin_thin_arm_stop stops a thin arm at a node >= 2x its width; ON 11-17 (Kent "Flip ON"); 16 of 35 runs move, 2 slightly worse
metadata:
  type: project
---

2026-11-17, prime grader scorecard (`toat_machine_hat`, pins 10.5/23.5, 20.5/24.0).
PR #1635, lane `claude/prime-fix-toat-m-stem-tops`.

- **Stage:** the M is the skeleton satin tier (`stage6_satin`), NOT the column
  lane: `lettering_columns_apex_pro*`, `corner_fold*` and `script_strokes` leave
  the M's stitches identical (17,430 in every arm). At the end-trim block a hairline
  arm ran INTO the node by its own half-width (`satin_junction_stack` part B) and
  was tip-capped (`_is_tip_end` -> `_extend_to_cap`): the fan.
- **Fix:** `satin_thin_arm_stop` — an arm whose node is >= 2x its own width
  (`_meets_wider`: median field 1.5-4 mm back from the end) gets neither. ON by
  Kent's flip ("Flip ON (Recommended)"); `THIN_ARM_STOP_2026_11_17_OFF` pins it.
- **Existing flags:** `satin_tip_corner_gate` ON + `satin_junction_stack` OFF cleans
  the same tops but moves every logo (stack is the ON default since 09-19).
- **Movers:** 6 of 9 pro jobs, 10 of 26 fixtures. Better: Toat hat and beanie,
  Golden Tee, white-icon, owl. Slightly worse: scene_stub, phone_ui_golke.
  Pictures: `docs/renders/thin-arm-stop-2026-11-17/`.
- **Not fixed:** the lumpy head of the M's first stem (separate cause).
