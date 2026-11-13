---
name: eye-first-diagnosis-2026-11-13
description: "Kent 2026-11-13: sessions measure with yardsticks instead of looking; diagnose a bad render by eye against the ORIGINAL first, and do not ask him to grade what a session can see"
metadata:
  type: feedback
---

Diagnose a bad digitize by looking at the render beside the original art,
stage by stage, before reaching for a yardstick or asking Kent to grade.

**Why:** Kent, 2026-11-13, after a session listed a render's faults from one
picture and then offered him a grading choice: "you know what the issues are
perfectly fine, so why do you need me to grade them for you? Are you not
using your brain to diognose the issues and instead using your yardstick to
measure the digitizes photos?" The same session then found the cause (a
1.5 mm satin floor on a 0.4 mm keyline) in under an hour with `debug_dir`
stage dumps and its own eye. None of the three fault readers had ever tried a
session's eye against his pins.

**How to apply:**
- Two jobs, do not mix them. Finding gross faults against the original: the
  session's job, by eye, no sitting needed. Picking the better of two close
  variants (a flag flip): still Kent's, the session eye read only kappa +0.34
  against him there ([[vlm-judge-100-2026-11-06]]).
- The eye needs the ORIGINAL beside the render. Without it this session called
  a hairline keyline "a border that is too heavy": symptom right, cause wrong.
- Trace with `PipelineConfig(debug_dir=...)` and look at each stage's picture;
  name the stage, then confirm with a number.
- A scratch renderer can lie: one here skipped every run that starts with a
  jump and drew fills as missing. Cross-check against the pipeline's own
  `stage6_stitches.png`.
- My reading (not his words): yardsticks stay for CI gates and flips; they are
  not the diagnosis tool.

Related: [[hairline-keyline-bean-2026-11-13]], [[kent-judging-rubric-2026-11-07]].
