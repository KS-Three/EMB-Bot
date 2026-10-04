---
name: build-what-was-priced
description: "After Kent picks an option I measured and priced, build that option exactly; an \"improvement\" beyond it is a new, unpriced change"
metadata:
  type: feedback
---

*Imported 2026-10-04 as a SNAPSHOT from the memory folder of sessions rooted outside this repo (`~/.claude/projects/C--Users-EE-LT-11030--claude-work/memory/`, session `7bdbbefa-2143-4bb4-9273-639fbbfd6546`, last written 2026-10-04T05:32:29.532Z); see [[wrong-root-sessions-and-global-guards-2026-10-04]]. The source may have moved on since. "I" below is the session that wrote it. PR states re-checked at import: #623 open, not armed.*

When I put priced options to Kent and he picks one, the thing to build is the thing that was measured, no wider. This is my own lesson from 2026-10-03/04 (EMB-Bot PR #623, [[embot-sub-unit-stitches-lane]]), not something Kent said.

**What happened:** the option he chose ("no run lays a second stitch in a hole") had been prototyped and priced as "drop a stitch whose previous record is a stitch on the same point". While building it I widened it to look through jump records, because it removed 15 to 61 more doubled holes and read as cleaner. My own tests, mutants and 16,525-design proof all passed. An independent audit then pointed out that a DST cut is written as three jump records, so removing a stitch from between two jumps can create a cut nobody asked for. I reverted to the priced rule and paid for a second audit, a second CI run and a rewritten record.

**Why:** the numbers Kent decided on describe one rule. A wider rule has costs nobody priced, and my own checks were built around my own idea of what could go wrong.

**How to apply:** build the priced rule first and prove it equals the prototype's numbers. If a wider rule looks better, say so as a separate, measured proposal (or a follow-up chip), with its own costs, instead of folding it into the build. And when a change touches what is written to a stitch file, check it at the file level (write it and read it back), not only at the stream level.
