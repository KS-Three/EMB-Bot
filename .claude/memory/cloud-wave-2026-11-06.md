---
name: cloud-wave-2026-11-06
description: Kent 11-06 "get 10 agents working in the cloud, you choose": foreman dispatched 10 cloud lanes (yardstick scorer, Euler fill census, C2 satin/fill vote, stage-7 speed, rotated nest guard, PR 1284 rescue, e2e apt, offsetRing test, dropped-element v2, shard balance)
metadata:
  type: project
---

**Kent, 2026-11-06:** "Let's get 10 agents working in the cloud, you choose the
subject/content but i want some real improvements for embot." Foreman (k3) ran an
Opus scout over ROADMAP, MASTER_SCOPE, `docs/lagging-areas-2026-11-06/`, open PRs
and 833 `origin/claude/*` branches; picked 10 of its 14 candidates, no two on one
file, every new behaviour behind a default-OFF flag.

**The 10 lanes (all `start_session` target cloud, started from a desktop-app turn):**
1. rescue-1284: PR #1284 (satin/fill C3 oracle) was armed but CONFLICTING + e2e red.
2. euler-fill-census: `digitizer/tools/fill_euler_census.py`, bar >= 20 of 32 cuts one walk.
3. yardstick-perceptual: `tools/yardstick_perceptual.py` FLIP/LPIPS/DreamSim + `--labels`; kappa vs Kent NOT measurable in cloud (labels + pro renders laptop-only).
4. satin-fill-vote: C2, `stage6_satin.py`, flag `satin_fill_vote` OFF.
5. stage7-speed: `_ring_route` vectorise, byte-identical.
6. nest-guard-rotated: `textcluster.py` `_drop_nested`, flag `text_cluster_nest_guard_rotated` OFF.
7. e2e-apt-time: studio-e2e job only.
8. offsetring-spike-test: `test/offset-ring-spike.test.js`, defect 55, pins not hides.
9. dropped-element-v2: flag `dropped_element_v2` OFF, the 2 Good/Great false fires.
10. shard-balance: `tests/.shard_durations.json` refresh if max/mean > 1.15.

**Dropped:** stage-0 re-flip (PR #1282 closed unmerged after Kent ruled ON; a local
session owns its blocker, the Bridge teal JPEG fringe), Qwen-VL + Bradley-Terry
(laptop / low prior), OCR re-time (same file as 6).

**Traps hit:** `start_session` refuses every call from a Remote Control turn
("can't start that session"); the briefs had to wait for a desktop-app turn. Cloud
sessions ignore the `model` parameter, so Opus/Sonnet per lane cannot be chosen.
Cloud sessions never report back; check PRs, not notes.

**How to apply:** a session picking next work checks these 10 PRs first (`gh pr
list --search "2026-11-06"`); the scout also flagged ROADMAP phase 1's zero-tolerance
exit vs labels that repeat 1 of 4, still Kent's to settle. Related:
[[lagging-areas-2026-11-06]], [[external-repo-sourcing-2026-11-06]],
[[agents-cheap-models-2026-11-02]], [[stacked-pr-auto-merge-trap-2026-11-06]].
