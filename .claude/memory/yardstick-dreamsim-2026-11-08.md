---
name: yardstick-dreamsim-2026-11-08
description: Pre-registered perceptual yardstick run on the 100 pro pairs: DreamSim agrees with Kent above chance (kappa +0.197), claim rule met; nothing flipped
metadata:
  type: project
---

The one pre-registered run (Kent 11-08: "Pre-register, run once", then "Re-render
100, then run") read DreamSim at 3-way kappa +0.197, pairs CI [+0.07, +0.32],
designs CI [+0.10, +0.29], n 100 (Kent decided 41), against mse +0.053. Claim rule
met. lpips_vgg also cleared (+0.211) but is a lead only, and fails the blank oracle.
Full record: `docs/yardstick-perceptual-result-2026-11-08.md`; prereg beside it.

**Why:** first instrument to clear chance against Kent's eye on these pairs without a
Claude judge (the eye sessions read +0.34/+0.36, [[vlm-judge-100-2026-11-06]]).

**How to apply:** it licenses a proposal to Kent, not a flip or a gate move. Use
the design-clustered CI (pairs share a "before" render). From a scratchpad worktree
set `EMB_BRIDGE_PRO` or `from-pro-pooled` silently skips the 19 Bridge pairs.
Follow-ups: [[yardstick-pro-pair-2026-11-01]].
