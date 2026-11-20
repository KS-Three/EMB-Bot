---
name: foreman-handover-2026-11-20
description: Foreman state when Kent ended PC sessions 2026-11-20 10:58 CST - open PRs, unfinished fold lanes, pending Kent decisions
metadata:
  type: project
---

Foreman session "foreman-code-sessions" ran 2026-11-20 and stopped at 10:58 CST (Kent switched PC users).

Open PRs, all armed (they merge on their own): #1736 queue.json Leave-OFF record, #1737 satin_seam_hold off photos, #1738 satin_junction_block built OFF (ON fixes 0/5 MFab top-line faults; pictures only in a gitignored scratch pack), #1739 SAM2 ONNX probe docs. If one is CLEAN but unmerged, squash-merge it; if red, the owning session is gone, so start a fixer on the same branch.

Unfinished, no PR: fold tier A remainder (branch `claude/sad-benz-2607bb`, 11 ON flags folded, fold_check byte-identical proof was ~half done) and fold tier B2 (`claude/peaceful-noether-cf7caa` / `claude/fold-b2-imageprep`, 6/12 folded, 6 skipped because their OFF arms are pinned baselines; md5 proof pending). Both were told to WIP-commit and push at 10:54; check origin before assuming the work exists (footgun 8). Both edit digitizer config.py/conftest.py. B3 colour/merge, B4 borders/small text, B5 fill, B6 lettering_columns follow B2.

Kent ruled "Re-spawn under me": new work starts as child sessions of the foreman; old sessions get archived once their PRs are open.

Pending Kent decisions, not yet asked (flips/deletes need before/after pictures): tier E (7 flags), tier H (73 OFF layout switches), OFF-census dead flags (28 inert + 10 parent-only), 3D puff branch `claude/3d-puff-ui-toggle-bdeef1` unverified, sew-out cards v7/v8 unsewn.

**Why:** the session ended mid-wave; the cloud sessions and the PC's local sessions don't carry this state.
**How to apply:** a new foreman reads this first, checks `gh pr list` and the two fold branches on origin, and resumes. Related: [[agents-cheap-models-2026-11-02]], [[foreman-wakeup-while-wave-out-2026-11-12]].
