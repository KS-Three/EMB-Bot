---
name: embot-star-walk-lane
description: "EMB-Bot star/satin-walk lane — PR #624 (skeletonEdges walk that never ended) armed 2026-10-03; defect 57 (browser medial satin) open, cure order put to Kent, do not build without his pick"
metadata:
  node_type: memory
  type: project
  originSessionId: a3870e6b-5bc4-4f5b-8f00-ff8f6c5432dc
  modified: 2026-10-04T04:44:29.994Z
---

> **Snapshot, copied 2026-10-04 (morning) from outside the repo.** Sessions rooted in
> `C:\Users\EE-LT-11030\.claude-work` keep their memory in
> `~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, which is not this
> folder: nothing written there rides a PR or reaches a session rooted in EMB-Bot.
> The original may still be edited by the session that wrote it, so check a fact here
> before acting on it. PRs it names, at this copy: #624 open, armed.
> See [[memory-outside-the-repo]].

Lane: branch `claude/star-satin-runaway`, worktree `.claude/worktrees/star-satin-runaway`, [KS-Three/EMB-Bot#624](https://github.com/KS-Three/EMB-Bot/pull/624). Opened and armed (merge method "merge") 2026-10-03 after an independent re-measure; merging is Kent's / auto-merge.

What it fixed: `skeletonEdges` in `src/satin.js` walked for ever round three touching pixels; only the `w*h` guard stopped it and the satin emitter sewed the result (20 mm 12-point star: 48,645 stitches, now 729). Moves only designs where a walk reached the guard: 4,038 of 145,600 swept stars, thin round-ended bars, 273 of 612 image-lane designs. MASTER_SCOPE closed entry 56.

What it left, and must NOT be built without Kent's pick ("Waiting on Kent" 26, MASTER_SCOPE live defect 57): the browser's medial satin lays a stitch as long as the star or the bar, sews strokes twice, finds "rings" in shapes with no hole, and a 2 mm round shape now sews four stitches. Three candidate cures were put to him by AskUserQuestion on 2026-10-03: the bar's end, the star's tier (branch guard on the whole rung), one pixel one edge (port the Python tracer's consumed set). A cap on a cross's length is a number and gate 1's: not offered.

**Why:** the cures move most satin designs and one trades long stitches for sub-millimetre fill rows nothing has sewn, so the order is Kent's call.

**How to apply:** if asked to continue this lane, check whether #624 merged and what Kent picked before touching `src/satin.js` or the branch guard in `src/digitize.js`. `node tools/satin-walk-census.mjs` (in the repo once #624 merges) reproduces every number; `--against <tree>` says which designs a change moves. Numbers 54/55 belong to PR #621, 25 to #623. Related: [[embot-sub-unit-stitches-lane]], [[embot-closed-ring-lane]], [[long-runs-on-this-laptop]].

Leftovers on disk from that session (C: had 1.6 GB free): `%TEMP%\star-remeasure-k7q3x` (613 MB, the independent agent's files), the session scratchpad (317 MB), and `app\node_modules` + `app\public` in the worktree (192 MB). Kent was told; not deleted by the session.
