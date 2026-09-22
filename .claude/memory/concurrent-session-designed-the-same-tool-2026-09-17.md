---
name: concurrent-session-designed-the-same-tool-2026-09-17
description: Two live sessions on one checkout designed the same tool an hour apart; check reflog + worktree list for a sibling's work BEFORE brainstorming, and never switch the shared checkout's branch
metadata:
  type: feedback
---

Kent asked this session for "an interactive artifact of 40 before/after pairs
… feedback for what's working". I ran a full brainstorm (four
AskUserQuestion rounds) and got a design approved — then found that another
session, on the SAME main checkout, had already spec'd and planned the same
thing ninety minutes earlier (`docs/superpowers/specs/2026-09-17-eye-pairs-design.md`,
approved by Kent section by section, with a ruling that contradicted mine:
"the picker is a local page, NOT an Artifact"). By the time I noticed, that
session was executing Task 1 in its own worktree.

Two mistakes, both mine:

1. **I cut a branch on the shared checkout with `git checkout -b`.** The
   checkout was sitting on the other session's branch (`claude/eye-pairs-yardstick`),
   not `main` as the stale session-start snapshot said; my checkout switch
   pulled the rug from under a live session. `git reflog` showed the whole
   sequence. **Never change the shared checkout's branch — `EnterWorktree`
   from the start.**
2. **`EnterWorktree` bases the new lane on the cwd's HEAD when the shell
   has drifted into another worktree**, so my lane silently carried the
   other session's five commits until I `git reset --hard origin/main`.

**Why:** Kent runs several sessions in parallel and does not always tell
each what the others are doing. A duplicate design costs him a round of
answers and would have cost a duplicate 1–3 hour render.

**How to apply:** Before brainstorming anything that sounds like a tool or
a review harness, spend one command on `git reflog -10 --date=iso` and
`git worktree list` and read the newest `docs/superpowers/specs/` names.
If a sibling has the topic, surface the overlap to Kent with the
non-overlapping piece as the recommended option (that is what he chose:
"run the existing plan; artifact AFTER the sitting"). Related:
[[worktree-add-empty-var-wipes-cwd]], [[worktree-venv-and-baselines]],
[[worktree-session-harness-guard-2026-09-17]].
