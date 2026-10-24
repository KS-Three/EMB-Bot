---
name: memory-index-archive-split-2026-10-23
description: MEMORY.md split 2026-10-23 (Kent: "Yes, split") — pre-09-15 lines moved to MEMORY-archive.md (not auto-loaded); new entries go at the BOTTOM of the live index, one line per PR
metadata:
  type: project
---

`.claude/memory/MEMORY.md` sat at its 24,986-character ceiling, so every PR that
added a note conflicted with every other (all three DIRTY PRs on 10-23 were
MEMORY.md only). Kent approved the split in chat 2026-10-23.

**What changed:** the 57 index lines whose note is dated before 2026-09-15
(filename date, else the date `git log --diff-filter=A` first sees the file) moved
whole, same order, to `.claude/memory/MEMORY-archive.md`. The live index keeps ONE
pointer line to it, first in the list, naming the standing rulings (fill rows
0.15, DST axis fixed, Ink/Stitch clean-room, Ember teardowns). Live index went
25,011 -> ~15,600 chars. The notes themselves did not move.

**The archive is NOT auto-loaded.** A session that needs pre-09-15 history or a
standing ruling opens it by hand; the pointer line is the only thing that tells it
to. `DOCTRINE.md`'s index line stayed live (its entry is dated 09-20).

**How to apply:**
- New note = ONE line at the BOTTOM of `MEMORY.md`, one line per PR.
- Near the ceiling, move the OLDEST live lines whole to the archive (same order,
  appended at its bottom). Never delete a line to make room.
- `digitizer/tests/test_memory_budget.py` enforces the live ceiling, the 260-char
  line cap on BOTH files, and that every note file is indexed in exactly one of
  them. `python -m tools.memory_budget` (from `digitizer/`) prints both.
- A merge conflict on MEMORY.md is still possible when two PRs append at the
  bottom; take main's lines and re-add only your own.

Related: [[memory-index-overflow-2026-09-15]], [[memory-outside-the-repo]].
