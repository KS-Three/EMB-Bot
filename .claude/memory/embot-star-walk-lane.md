---
name: embot-star-walk-lane
description: "EMB-Bot star/satin-walk lane — PR #624 (skeletonEdges walk that never ended) armed 2026-10-03; defect 57 (browser medial satin) open, cure order put to Kent, do not build without his pick"
metadata:
  type: project
---

*Imported 2026-10-04 as a SNAPSHOT from the memory folder of sessions rooted outside this repo (`~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, session `a3870e6b-5bc4-4f5b-8f00-ff8f6c5432dc`, last written 2026-10-04T04:44:29.994Z); see [[wrong-root-sessions-and-global-guards-2026-10-04]]. The source may have moved on since. "I" below is the session that wrote it. PR states re-checked at import: #624 open with auto-merge armed.*

Lane: branch `claude/star-satin-runaway`, worktree `.claude/worktrees/star-satin-runaway`, [KS-Three/EMB-Bot#624](https://github.com/KS-Three/EMB-Bot/pull/624). Opened and armed (merge method "merge") 2026-10-03 after an independent re-measure; merging is Kent's / auto-merge.

What it fixed: `skeletonEdges` in `src/satin.js` walked for ever round three touching pixels; only the `w*h` guard stopped it and the satin emitter sewed the result (20 mm 12-point star: 48,645 stitches, now 729). Moves only designs where a walk reached the guard: 4,038 of 145,600 swept stars, thin round-ended bars, 273 of 612 image-lane designs. MASTER_SCOPE closed entry 56.

What it left, and must NOT be built without Kent's pick ("Waiting on Kent" 26, MASTER_SCOPE live defect 57): the browser's medial satin lays a stitch as long as the star or the bar, sews strokes twice, finds "rings" in shapes with no hole, and a 2 mm round shape now sews four stitches. Three candidate cures were put to him by AskUserQuestion on 2026-10-03: the bar's end, the star's tier (branch guard on the whole rung), one pixel one edge (port the Python tracer's consumed set). A cap on a cross's length is a number and gate 1's: not offered.

**Why:** the cures move most satin designs and one trades long stitches for sub-millimetre fill rows nothing has sewn, so the order is Kent's call.

**How to apply:** if asked to continue this lane, check whether #624 merged and what Kent picked before touching `src/satin.js` or the branch guard in `src/digitize.js`. `node tools/satin-walk-census.mjs` (in the repo once #624 merges) reproduces every number; `--against <tree>` says which designs a change moves. Numbers 54/55 belong to PR #621, 25 to #623. Related: [[embot-sub-unit-stitches-lane]], [[embot-closed-ring-lane]], [[long-runs-on-this-laptop]].

Leftovers on disk from that session (C: had 1.6 GB free): `%TEMP%\star-remeasure-k7q3x` (613 MB, the independent agent's files), the session scratchpad (317 MB), and `app\node_modules` + `app\public` in the worktree (192 MB). Kent was told; not deleted by the session.
