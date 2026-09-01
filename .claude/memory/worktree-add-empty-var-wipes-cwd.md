---
name: worktree-add-empty-var-wipes-cwd
description: "git worktree add with an empty/undefined path variable, run from inside a worktree, empties that worktree's cwd on rollback — recreate with worktree add <path> <branch>, commits survive"
metadata: 
  node_type: memory
  type: project
  originSessionId: 42f99b0c-fecf-44b5-9dfd-047117f2410c
  modified: 2026-09-01T04:17:33.915Z
---

2026-08-31, during the borders-last review (PR #300): the emb-bot-reviewer
subagent ran `git worktree add "$TMP_MAIN" origin/main --detach` with
`$TMP_MAIN` undefined, from inside lane `wonderful-shaw-69a326`. Git's
failure rollback emptied the cwd (every checked-out file gone), and a
follow-up `git worktree prune` deleted the lane's admin metadata.

**Why:** an empty first argument + rollback semantics; the damage is to the
CHECKOUT only. Branch and commits were fully intact.

**How to apply:**
- Quote-and-verify any path variable before `git worktree add`; never run it
  from inside the lane it might affect.
- Repair is one command from the primary repo (empty target dir is reused):
  `git -C <repo> worktree add <lane-path> <branch>` — restores the checkout
  with the branch attached. Check `git worktree list` + `git log <branch>`
  first; expect zero loss if the tree was clean.
- Uncommitted work in the lane at wipe time WOULD be lost — commit
  checkpoints before spawning agents that touch git plumbing. Related:
  [[first-real-photos-2026-08-23]] ("give every agent its own worktree").
