---
name: yardstick-dreamsim-2026-11-08
description: DreamSim vs Kent's eye, 11-08: passed on the 100 pooled pro pairs (+0.197) but did NOT replicate on a fresh blind sitting (+0.099, CI crosses 0) or the 1102 hold-out (-0.127); no instrument stands in for Kent
metadata:
  type: project
---

Three pre-registered reads, all on 2026-11-08, with the same instrument and the
same claim rule (pairs lower bound above 0 AND beat mse's point kappa):

- 100 pooled pro pairs: DreamSim +0.197 [+0.07, +0.32], mse +0.053. Passed.
  `docs/yardstick-perceptual-result-2026-11-08.md`.
- Fresh sitting `dreamsim-confirm-1108` (22 pro jobs, 6 arms, 53 live, Kent
  decided 17): +0.099 [-0.04, +0.24], mse -0.005. NOT confirmed.
  `docs/yardstick-perceptual-confirm-2026-11-08.md`.
- Hold-out: the 1102 population-A pairs (29, 14 decided): -0.127, no evidence.

**Why:** the first pass did not replicate. Kent chose "Confirm on new pairs" to
test exactly this.

**How to apply:**
- Do not propose DreamSim, or any LPIPS/FLIP/mse, as a stand-in for Kent's eye.
  A new attempt needs a new instrument and a new pre-registration, not a re-read
  of these pairs.
- `sitting.py` now has `rejudge_pro_jobs` (a spec opt-in, since Kent has judged
  every pro artwork).
- `tools/yardstick_perceptual.py from-sitting` turns any sitting into a
  yardstick pair list.
- `sitting analyse` silently drops Gaulke (`pooled.KENT_EXCLUDED`) while
  `from-sitting` keeps it, so name the pair set in the prereg.
- Set `EMB_BRIDGE_PRO` when running from a scratchpad worktree.
- Related: [[yardstick-pro-pair-2026-11-01]], [[vlm-judge-100-2026-11-06]].
