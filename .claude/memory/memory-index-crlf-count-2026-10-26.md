---
name: memory-index-crlf-count-2026-10-26
description: "The loader counts MEMORY.md as stored, so a CRLF Windows copy costs one extra character per line; budget now reads the bytes, .gitattributes pins the notes to LF, and the recipe that actually converts an old checkout"
metadata:
  type: project
---

# The memory budget now counts the file the loader reads — 2026-10-26

**What was wrong.** `tools/memory_budget` and its test read the index with
`Path.read_text`, which translates CRLF to LF. Kent's Windows checkouts are CRLF
(`core.autocrlf=true`, and `.gitattributes` said nothing about `.claude/memory`),
and the loader does NOT translate. Every line cost one more character than the
test saw: 146 on an index of 146 lines, a bit over half of the headroom left
(24,705 as LF, 24,851 as CRLF, against 24,986). The wave-3 flips worker reported
the last entry cut on the primary checkout's copy while this test passed; the
mechanism is confirmed from the loader's code below, the cut itself was not
re-observed.

**What the loader counts** (read out of `~/.local/bin/claude.exe`, 2026-10-06
build, by searching the binary for "Only part of it was loaded"):

    uu="MEMORY.md",lL=200,Xee=25000
    function _tt(t){let r=t.trim();return{trimmed:r,lineCount:count(r,"\n")+1,byteCount:r.length}}

`byteCount` is `r.length`: UTF-16 units of the TRIMMED text, CRs included, so an
emoji is 2 and the trailing newline is free. The ceiling is 25,000, not 24,986;
`BUDGET` stays 24,986 (the 24.4 KiB the 09-15 report printed), the 14 are margin.
There is also a LINE ceiling, `lL=200` (the index has 146). Characters bind first
while lines average over 125, so it is not tested, but a run of very short
entries would hit it.

**What changed.** `read_stored` decodes the bytes (no newline translation);
`char_count` is the loader's count; `.gitattributes` has
`.claude/memory/*.md text eol=lf`; `sorted_text` keeps its input's line endings;
`python -m tools.memory_budget` prints a CRLF line when it finds carriage returns.
Pinned by `test_a_crlf_copy_is_counted_at_its_on_disk_length`.

**Headroom bought, same day (foreman's call).** The CRLF-aware count left 100
characters, with four PRs each adding a line. The 11 oldest live lines (dated
before 2026-09-22 by the archive's own rule) moved to `MEMORY-archive.md`, which
now says "before 2026-09-22": 24,886 -> 22,845 characters, 2,141 left.

**Why:** a budget that reads a different file from the one the loader reads is a
preference, not a check ([[memory-index-archive-split-2026-10-23]] is the same
ceiling from the other side).

**How to apply:**
- Reading a file to count what a tool will load: read the bytes, never `read_text`.
- The attribute does NOT convert an existing CRLF checkout, and
  **`git checkout -- .claude/memory` is a no-op** on it: the files are stat-clean,
  so git skips them (measured here, then again in a throwaway `autocrlf=true`
  clone). Two things do work. A pull that CHANGES a note rewrites it as LF with
  the attribute honoured in the same operation, and MEMORY.md changes in nearly
  every PR, so the index fixes itself on the next pull. To convert every tracked
  note now, with `git status --short .claude/memory` empty first (this discards
  uncommitted edits; untracked notes survive):
  `git rm -q --cached -r .claude/memory` then `git checkout HEAD -- .claude/memory`.
- The brief's 25,007 / 24,862 figures did not reproduce: by the time this was
  measured the primary copy was 24,862 as CRLF and 24,718 as LF. The mechanism did.
