---
name: foreman-merge-push-findings-2026-11-08
description: Foreman run 11-07/08 (62 PRs merged, #1301-#1362): squash branches refuse `branch -d`, test.fail() is expected, empty log != green, fix-lane branch names need a finding index, app prState lags GitHub
metadata:
  type: project
---

The 11-07/08 foreman run merged 62 PRs (#1301 to #1362) and left `main` green. On 11-08 the cleanup removed 30 worktrees and deleted 85 sessions whose work had landed. Every leftover diff was copied to `G:\My Drive\EMB-Bot\worktree-leftovers-2026-11-08\` first. The full write-up, including what was kept and why, is in `docs/foreman-run-2026-11-07.md`.

**Why:** each item below cost the run time and will cost it again.

**How to apply:**
- **Squash-merged branches refuse `git branch -d`.** 21 local branches stay behind after cleanup. Never use `-D`, and never re-push a branch to get past `-d`. Kent decides what happens to them.
- **A `test.fail()` result is expected, not red.** Parse Playwright results against `expectedStatus`.
- **An empty job log is not green.** Get the results with `gh run download <run> -n studio-e2e-shard-N`.
- **Name a fix-lane branch by PR + file + finding index.** Two findings on the same file of #1344 collided on one branch.
- **Check the PR state with `gh pr view`.** The app's `prState` for archived sessions can be weeks stale (it still showed #643 as OPEN).
- **A lane whose dev server is still running cannot be deleted** ("Invalid argument"). Stop its `node` process first.
- **The Recycle Bin API refuses long or locked paths.** Delete a lane's `node_modules` first, since `npm ci` regenerates it.

Related: [[local-lanes-fill-disk-2026-11-08]], [[foreman-merges-and-bypass-2026-11-06]], [[stacked-pr-auto-merge-trap-2026-11-06]].
