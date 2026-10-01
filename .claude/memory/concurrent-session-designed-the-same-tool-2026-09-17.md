---
name: concurrent-session-designed-the-same-tool-2026-09-17
description: Three collisions between parallel sessions (same design, same build, same worktree); check reflog, worktree list, branches and live sessions BEFORE designing; stop a background session with `claude stop` under its own profile, never a bare kill
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

**It happened again 2026-09-28, and worse — a whole BUILD, not a design.**
Kent picked "build upload crop" from a scorecard review; the plan on `main`
(#547) looked unstarted, so the session ran all seven tasks with reviews
(~4 hours). Only afterwards did `git branch --no-merged` show
`claude/upload-crop-build`: the SAME plan, built end to end on 09-22 through
its own final-review fix wave — LOCAL ONLY, never pushed, never a PR. A plan
on `main` with unchecked boxes says nothing about whether it was executed.
**Before executing any plan, grep branch names and recent commit subjects for
its topic:** `git branch -a --format="%(refname:short) %(committerdate:short) %(subject)" | grep -i <topic>`.
And a finished lane that is only on local disk is invisible to every other
session — push it (`git push origin <b>:refs/heads/<b>`) even without a PR.
Resolution that day: Kent chose to compare the two builds and PR the better
one with the other's strengths ported in.

**A third time, 2026-10-01 — two LIVE sessions in one worktree.** Two resumed
background sessions were both designing holes for the manual lane, with
opposite designs (a ring stored inside its parent vs. a shape marked Cut
out). One entered the other's freshly created worktree within three minutes
and committed its own spec and plan there. What caught it: an untracked file
nobody in this session had written, in a worktree just created; then the
worktree's `locked` file under `.git/worktrees/<name>/` naming the OTHER
session's process. Kent was shown both designs and ruled (Cut out — spec
ruling 11), and said to stop the other session.
**Stopping a background session:** a bare process kill does NOT stick — its
supervisor respawned it 11 seconds later and it went on writing its own Task 1
into the worktree, uncommitted. The stop that sticks is `claude stop <id>`, run
under THAT session's own profile (`CLAUDE_CONFIG_DIR` set to the profile it
was launched with); its conversation is kept and resumable. **Never `claude rm
<id>`** while its job still names a live worktree — it removes the worktree
the job points at. The stray edits were committed as found and reverted, not
discarded (the repo's hook refuses discarding under `.claude/worktrees/`).
**How to apply, on top of the above:** before creating a worktree or writing
a spec, check `claude agents --json` and the process list for a session on
the same topic; after creating a worktree, re-check `git status` before the
first write — a file you did not write means someone else is in there.
