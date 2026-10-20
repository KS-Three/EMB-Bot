---
name: lane-cleanup-2026-10-20
description: 10-20 lane cleanup — a dirty lane's uncommitted work was a flip Kent had REVERSED; check the parent session's last word before carrying stranded work; the 84-lane census and what is Kent's to run
metadata:
  type: project
---

Cleanup session 2026-10-20 (Kent: "clear finished work, merge any work into 1
existing code session"). Follows [[lane-triage-2026-10-11]]. SNAPSHOT: re-run
`git worktree list` before acting on any lane named here.

## The trap: stranded work can be reversed work

`quirky-dirac-0e9b52` (branch `claude/open-cored-counters-on`, the app kept it
after archiving "golden_tee O counter: trace the counter as a hole") held an
uncommitted four-file diff flipping `open_cored_counters` to True, its comment
quoting Kent verbatim: "Flip open_cored_counters ON as built in #988." Four
transcripts carry that sentence. It was real — and **Kent reversed it the
same night**: "Leave OFF for now"; "Tell the other session not to flip it
on" (relayed by the fork of "Fine lettering quality issues"; the foreman's
wrap-up reads "its reversal holds: `open_cored_counters` stays OFF, no flip
PR ever pushed"). #995 then built the guard and the hold-off behind the OFF
flag and left the flip question in its body; the night's "four flips" card
(items 41, 46, 52, fold cuts) did not include it. MASTER_SCOPE 47 records the
reversal. This session had the flip re-applied on fresh main, 41 targeted
tests green and the full suite running before the transcript showed it.
Discarded, nothing pushed.

**Why:** a dirty lane is the state of a session at the moment it was archived,
not the state of the decision. A ruling quoted in a diff is evidence the ruling
existed, not that it stands. The reversal lived only in the parent session's
transcript and in MASTER_SCOPE's "(Kent 2026-10-19: 'Leave OFF for now')".

**How to apply:** before carrying any uncommitted lane work forward, read the
LAST turns of the session that owned it and of its parent
(`list_events`), and grep MASTER_SCOPE for the flag. A matching transcript
snippet is not enough; `search_session_transcripts` returns the FIRST hit per
session, which is the ruling, never the reversal.

## The census (one live checkout, 84 lanes, 240 local branches)

Method per [[lane-triage-2026-10-11]]: a branch is LANDED when its tip is an
ancestor of a merged PR's `headRefOid`, or `git cherry origin/main` shows no
`+` line. Dirty lanes were split by `git status --porcelain --untracked-files=no`
(modified tracked files) against untracked-only scratch (logs, `_probe*.py`,
a stray venv). Lists in the session scratchpad: `lanes_remove.txt` (55),
`lanes_inspect.txt` (14 landed lanes with modified source nobody verified),
`lanes_stranded.txt` (8), `branches_delete.txt` (363 landed or empty
`worktree-agent-*` branches, none held by a lane).

Done here: `git fetch --all --prune`, main fast-forwarded 85 commits
(#989-#1010), two dead Temp worktree entries pruned, the flip lane discarded.
**Not done, Kent's:** lane removal (the hook denies `git worktree remove`),
the 363 branch deletes and the lane-removal script (the auto-mode classifier
denied both as local destruction; a backup `refs/backup/<date>/<branch>` per
tip before `branch -D` is the reversible shape). The eight stranded lanes:
`pro-overlay-loop` (parked by Kent 09-30), `satin-bar-end` (ported by #817,
removable per 10-11), `edge-run-start` (7 patches), `fill-columns-ends` (7),
`outline-cut-columns` (2), `upload-crop` (duplicate, 21), `sitting-prep-wok42`
(1 + a modified test), `serif-junction-fans` (#653 merged, tip 3 newer).

## Status after the wrap-up session, 2026-10-20 evening

Done since the census: the 363 branch deletes ran (0 of 363 exist; 103 local
branches left). `quirky-dirac-0e9b52` and its reversed-flip diff were discarded
through the app's `discard_kept_worktree` card (Kent's pick; its branch
`claude/open-cored-counters-on` is kept and landed). The stale
`.claude/pr_body.md` (#988's body) went to the Recycle Bin. **Kent chose to
LEAVE the lanes:** 57 landed clean, 13 landed with unverified modified source,
8 stranded, 3 app reuse-pool (detached `affectionate-yonath`,
`dazzling-bouman`, `sharp-blackburn` — the app reaps those itself; never
`git worktree remove` them). The 13 squash-landed lanes whose `git cherry`
shows `+` lines (cap-follow, columns-density, field-node-edit,
fill-columns-exit, gaulke-ground-sewn, join-square-enthusiast,
join-square-merge, letterform-priors, n-fan, pr572-fix, satin-spine-port,
small-text-true-size, star-satin-runaway) each have a tip inside a merged PR
head — landed, not stranded; `cherry` alone over-counts after a squash merge.
Two things a session cannot do here even with Kent's yes in chat:
`git worktree remove` (the hook) and WRITING a script that names it (the
auto-mode classifier denied the Write). Hand Kent the commands as text.
