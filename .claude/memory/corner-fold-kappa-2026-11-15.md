---
name: corner-fold-kappa-2026-11-15
description: the Becker hat kappa drop under corner_fold_apex_side (0.337 -> 0.289) is REGISTRATION, not the fold; one frame: hat_large +0.006, hat_small -0.008; a 0.1 mm thread change re-cuts the 2 mm grid, +-0.05 on any scorecard kappa
metadata:
  type: project
---

Kent ruled 2026-11-15 "Accept + investigate (Recommended)" on the tripwire
re-capture (#1568), accepting becker_hat_large stitch-type kappa 0.337 -> 0.289
and becker_hat_small 0.557 -> 0.518 as the cost of
`lettering_columns_corner_fold_apex_side`. The investigation
(`docs/corner-fold-kappa-2026-11-15.md`) found the fold is not the cause.

- **Held in one frame** (the fold-OFF arm's registration and bounds for both arms),
  the fold moves stitch-type kappa by +0.006 (hat_large), -0.008 (hat_small),
  +0.002 (lc_large), +0.001 (chest), +0.007 (beanie). Direction kappa is the same story.
- **The tripwire's swing is `scorecard.register`.** The fold adds 0.1 mm at the E,
  and the IoU hill-climb lands 0.2-0.55 mm away on a flat plateau (IoU differs by
  about 0.001). That re-cuts the 2 mm cell grid. Even the PRO's cell mix changed
  (345 -> 327 satin cells), from a committed file.
- **lc_large's +0.031 is the same artifact the other way.**
- **The grid alone** (64 anchor offsets, registration held) moves a Becker kappa
  with SD 0.02-0.04, range about 0.1.
- **Where the fold does change agreement:** 9 of 911 cells on hat_large, all on
  MARINE's E, net +3. The hypothesis (the E's top-left, where we fan and the pro
  caps) was tested and is not where the 0.048 went.

**Why:** every kappa row in the tripwire carries tolerance 0.00, because five
runners write the same DST and agree on the registration. So any engine change
that moves an outline by a sliver can turn a kappa row red or green with no
stitch-type change.

**How to apply:** before attributing a kappa move to an engine change, check
whether `registration_mm` moved (`scorecard.register` on both arms). If it did,
re-score both arms in one frame (OFF's registration and bounds) and quote that
figure. See [[nightly-tripwire-2026-11-02]] and [[corner-turn-2026-11-14]].

**Kent's ruling, 2026-11-15: "Pin tripwire frame (Recommended)"** (option B of
four). It is built OFF as `tools/tripwire.py --pin-frame` plus the workflow
dispatch input `pin_frame`:
- the ledger's `frames` hold a shift and grid origin per job;
- `scorecard.score_design(frame=...)` reads at the pin and re-registers only past
  `PIN_MARGIN` 0.01 IoU (plateau <= 0.006, a real 0.5 mm move 0.014-0.044).

Flipping it is Kent's: a capture with pins, then the schedule passes the flag
(docs/tripwire-frame-pin-2026-11-15.md). His accepted catch: the corpus
scorecard and flip-PR kappas still re-register per arm, so quote their deltas
from one frame.
