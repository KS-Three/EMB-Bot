---
name: embot-sub-unit-stitches-lane
description: "EMB-Bot lane \"two stitch records on one point\" — Kent chose a new flag; `dedupeHoles` built OFF, PR #623 open (2026-10-04); rule deliberately narrow (never looks through a jump); flip is \"Waiting on Kent\" 25"
metadata:
  type: project
---

*Imported 2026-10-04 as a SNAPSHOT from the memory folder of sessions rooted outside this repo (`~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, session `7bdbbefa-2143-4bb4-9273-639fbbfd6546`, last written 2026-10-04T05:31:48.670Z); see [[wrong-root-sessions-and-global-guards-2026-10-04]]. The source may have moved on since. "I" below is the session that wrote it. PR states re-checked at import: #623 open, not armed.*

EMB-Bot, task handed over from PR #617: the browser shape builder rounds to 0.1 mm, so two penetrations nearer than that become two `stitch` records on one point. See [[embot-browser-fill-lane-state]] and [[embot-handover-numbers-and-stacked-branches]].

**Kent's ruling, 2026-10-03 (AskUserQuestion, four priced options):** "New flag, every run": a record-stream rule in `pushRun`, behind a new builder flag built OFF. He did not pick "column-walk passes only", "leave rows out of the columns", or "leave it".

**Built:** `dedupeHoles: true` on `buildQualityDesign` (`src/digitize.js`, `pushRun`, `hole` local to it). A stitch is left out ONLY when the record straight before it is a stitch on the same point. After any jump or cut the stitch is laid. Flag absent: identical to main on 16,525 designs. Flag on: 16,575 to 0 (sweep), 39,948 to 0 (Studio lanes), cuts unchanged in the stream and as a DST reader finds them.

**The mistake not to repeat (mine, 2026-10-03/04):** after Kent chose, I widened the rule to "ask the thread, not the frame" (look through jumps), which was more than was priced for him. The independent audit held every claim and still undid it with one remark: a DST has no cut, `dst.js` writes one as three jump records, a reader takes any three jumps in a row for one, so taking a stitch from between two jumps can make a cut nobody asked for. Reverted to the narrow rule. Leaves 15 (sweep) and 61 (Studio) doubled holes that have a jump between the two.

**State when written (early 2026-10-04):**
- PR https://github.com/KS-Three/EMB-Bot/pull/623, branch `claude/sub-unit-stitches` (head `e26a3a30`), worktree `.claude\worktrees\sub-unit-stitches`. Ready for review. NOT armed until the independent agent (`dedupe-holes-audit`) finishes its SECOND look, at the narrowed rule (`audit\new-src-2` in this session's scratchpad). Check `gh pr view 623`.
- "Waiting on Kent" 25 in MASTER_SCOPE is the flip (`generate.js`'s three shape call sites, re-pin of shape snapshots). Not sewn. Lettering has no such rule.
- Two chips spawned from this lane: the 12-point preset star's 48,645-stitch satin (its session found `skeletonEdges` in `src/satin.js`), and "a DST reader finds far more cuts than the stream has trims" (floats over 24.2 mm are three jump records; `ties` does not lock them).

**How to apply:** `node tools/sub-unit-stitch-census.mjs [srcDir] [--corpus sweep|studio|file.cjs] [--against otherSrc] [--on k=v] [--off k=v]`; `--against` proves "flag absent: the same stream" and compares the cuts a DST reader finds; about 9 minutes for both sets. If Kent asks to flip the flag, that is its own PR.
