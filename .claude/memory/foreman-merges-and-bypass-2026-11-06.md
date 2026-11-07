---
name: foreman-merges-and-bypass-2026-11-06
description: Kent 11-06 "i'm not merging anything, you do it" + "make all your agents bypass permission, that's your job to manage them" — the foreman merges green PRs and runs workers in bypass; supersedes CLAUDE.md "Merging is still Kent's"
metadata:
  type: feedback
---

Kent, 2026-11-06, after the 10-lane cloud wave ([[cloud-wave-2026-11-06]]):
"make all your agents bypass permison. that's your job to manage them. ALSO,
i'm not merging anything, you do it."

**Why:** a green PR that missed its auto-merge window (the "already in clean
status" refusal) sat waiting for his click; he will not click. Permission
prompts on workers are the foreman's to clear, not his.

**How to apply:**
- Foreman merges: CLEAN PR, `gh pr merge --squash <n>`; BLOCKED, `--auto`. Never
  `--admin` and never past a required check: branch protection still gates (PR 1291
  went CLEAN to BLOCKED on a new head between two calls; arm it then).
- This overrides the repo `CLAUDE.md` line "Merging is still Kent's" for foreman
  and director sessions. Workers still only arm.
- Workers start in `bypassPermissions` where the tool allows it (`start_session`
  `permission_mode` is local-only; cloud sessions are not in `list_sessions`, so
  their mode cannot be set from the foreman; say so instead of claiming it).
- Related: [[questions-roll-up-to-director-2026-10-27]], [[agents-cheap-models-2026-11-02]].
