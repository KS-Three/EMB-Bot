---
name: vlm-prescreen-2026-11-06
description: The PRESCREEN pre-registration computed once (Kent 11-06 "Compute pre-screen pre-reg"): threshold-4 classes; settled-pair kappa +0.39 [+0.15, +0.59] n 39 of 54 and replication +0.29 [+0.07, +0.50] n 67 of 99, both above chance; licenses a display-only row PROPOSAL; "nothing to choose" swallows 13/29 and 18/40 of Kent's side picks
metadata:
  type: project
---

**What ran (2026-11-06, `claude/vlm-prescreen-compute`).**
`python -m tools.eye_pairs.vlm_prescreen` ran once over committed verdicts and
picks. There was no render and no model call. The results are in
`docs/eye-pairs-2026-11-04/vlm-judge-100/PRESCREEN-RESULTS.md` and
`prescreen.json`. `tests/test_vlm_prescreen.py` pins the threshold (4) to the
pre-registration text.

**The classes.**
- **Nothing to choose:** a tie.
- **Plainly damaged:** a side pick with confidence 4 or more.
- **Kent has to look:** everything else.

**What it read.**
- **Primary** (the 11-04 Fable judge, 54 pairs): the settled pairs' 3-way
  kappa is +0.39, CI pairs [+0.15, +0.59], CI designs [+0.23, +0.52], above
  chance, n 39 settled.
- **Replication** (the 11-06 Opus judge, 99 pairs; contaminated, since that
  judge knew the rule): +0.29, CI pairs [+0.07, +0.50], CI fixtures
  [+0.11, +0.45], above chance, n 67 settled.
- **Tie class alone** (a binary kappa): +0.31 on 54 and +0.28 on 99, both
  above chance.
- **Plainly damaged:** only 7 and 6 pairs. Kent picked the same side on 11 of
  the 13, tied 1 (P042 on 54) and went the other way on 1 (P037 on 99, "open
  columns will not cover", a sew-out question).
- **Identical controls:** 3/3 and 4/4 landed in "nothing to choose".

**The catch.** "Nothing to choose" also holds 13 of Kent's 29 side picks (54
set) and 18 of 40 (99 set). The tie label is the screen's weak point; the
damaged label is strong but rare.

**How to apply:**
- **What it licenses.** Only a PROPOSAL to Kent for a display-only class
  column on the eye-pairs page, with the catch above stated beside it. It
  does not license building it, using it to skip, drop or route pairs, any
  flag or gate use, or pooling it with Kent's labels.
- **Changing the rule.** A different threshold is a new dated
  pre-registration, never a re-run of this one (stopping rule).
- **Quoting it.** Quote both kappas with both intervals and n settled and n
  live.

Related: [[vlm-judge-100-2026-11-06]], [[vlm-judge-2026-11-04]].
