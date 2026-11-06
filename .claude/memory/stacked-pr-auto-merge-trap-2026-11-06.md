---
name: stacked-pr-auto-merge-trap-2026-11-06
description: A PR stacked on another PR's branch with auto-merge armed merges INTO that branch, not main, when the base PR merges first and its branch survives (deleteBranchOnMerge is off here)
metadata:
  type: feedback
---

**What happened (2026-11-06).** The frame-hold follow-up to Move shape was opened as PR #1259 with base `claude/move-shape-378f90` (PR #1255's head) and auto-merge armed. #1255 squash-merged to `main` at 04:24Z; its branch stayed, because the repo has `deleteBranchOnMerge: false`. GitHub retargets a stacked PR to `main` only when the base branch is DELETED, so #1259 kept its base and auto-merge landed it into the dead branch at 05:08Z. `main` never saw it. The worker noticed and re-opened the same commit as #1260 against `main`.

**Why:** a stacked PR plus auto-merge is a race nobody watches. The merge "succeeds", the PR reads MERGED, the session's note says done, and nothing reached `main`: every check a director runs (`gh pr view --json state`) reports the one state that means finished.

**How to apply:** a worker bases a follow-up on `main`, never on a sibling's unmerged branch. If a stack is unavoidable, do not arm auto-merge until the base PR has merged AND `gh pr view <n> --json baseRefName` reads `main`. After any stacked PR merges, read `mergeCommit` and `baseRefName`, and confirm the commit with `git branch -r --contains` naming `origin/main`. Flipping `deleteBranchOnMerge` on the repo (Kent's call) removes the trap at the source. Related: [[move-shape-2026-11-05]].
