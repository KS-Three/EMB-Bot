---
name: lane-triage-2026-10-11
description: 10-11 lane cleanup — how to tell a landed lane under squash merges, which lanes are removable, which hold stranded work, and what the satin spine port taught
metadata:
  type: project
---

Cleanup session 2026-10-11 (Kent: "clean up anything left open"). Follows
[[orphan-lane-sweep-2026-09-30]]. This is a SNAPSHOT: run `git worktree list`
and re-check before acting on any lane named here.

## Telling a landed lane (the repo squash-merges)

`git branch --merged` / `merge-base --is-ancestor` called 26 lanes unmerged;
4 held stranded work. In order of cost:

1. `gh pr list --head <branch> --state merged --json number,headRefOid` — lane
   HEAD equal to a merged PR's head, or an ancestor of it, means it landed.
2. `git cherry origin/main <lane>` with no `+` lines — every patch is in main.
3. `git merge-tree --write-tree origin/main <lane>` — result tree equal to
   main's tree means merging adds nothing. A CONFLICT here proves nothing:
   squash plus later edits conflicts on a lane that fully landed.
4. For a lane with no PR: per touched file, is it missing from main, identical,
   or different. "Missing" is the real signal.

## State when the session ended

Done: 16 dead worktree entries pruned, 51 merged local branches deleted
(none held by a live lane), six laptop-only branches pushed, #816 and #817
merged.

**Removable, Kent's to run** (the hook denies `git worktree remove`): 20
landed lanes, the duplicates `upload-crop` and `star-satin-runaway`, and after
#817 `satin-bar-end` and `satin-spine-port`. Five landed lanes had dirty files
nobody inspected: `serif-junction-fans`, `columns-sitting`,
`gaulke-ground-sewn`, `edge-wobble-instrument`, `youthful-poincare-37ed66`.

**Stranded, all commits on origin:**
- `manual-columns` — plan 2 of 3 of the manual-digitizing-gaps spec. Tasks
  1-4 committed, task 5 pushed as a `wip:` commit (unverified), 6-7 not
  started, so no user can draw a column yet. Lane specs pass on its 10-01
  base; 47 commits on `src/digitize.js` since. Its popover warns past 6.5 mm:
  NOT checked against gate 1.
- `pro-overlay-loop` (branch `claude/pro-overlay-diff`) — parked by Kent
  09-30. PR 3 of the overlay; 39 files not in main.

## Traps met

- **A lane cut with `git worktree add -b X origin/main` tracks `origin/main`.**
  A bare `git push` there aims at main, and Kent's admin bypass means
  protection does not stop it. Six branches were like this, and the lane this
  session made was a seventh. Push by explicit refspec; check with
  `git for-each-ref --format='%(refname:short) %(upstream:short)' refs/heads`.
- **The same satin bug was fixed three times** (lane 10-04 never PR'd,
  `7bb83e9b` on main 10-08, #764 closed as superseded). The lane's
  MASTER_SCOPE text said "PR open"; none existed. A doc's claim that a PR is
  open is not a PR: `gh pr list --head`.
- **A lane's own records can hold a condition on merging it.** `satin-bar-end`
  said Kent's eye on its sheets was the condition for arming. Read the lane's
  MASTER_SCOPE diff before arming a ported lane. Its sheets compared against a
  main that no longer existed; fresh ones against today's main reversed one
  recorded cost (the bar's needle-up move is on main too).
- **Porting a geometry change breaks fixture-hunting tests, not just pinned
  numbers.** `dedupeHoles` / `cutFloats` tests need a satin shape that still
  produces a degenerate stream; seven had to be re-found by sweep
  (#817's commit message lists them).
