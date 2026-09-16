# The index that silently stopped loading its own newest entries

**2026-09-15.** `.claude/memory/MEMORY.md` stood at **48,421 characters against
a 24,986 ceiling**, and the memory loader had been quietly truncating it: *"16
of 57 lines were cut off, starting at line 42."*

**The 16 that vanished were the NEWEST** — everything after 2026-09-03,
including the DST axis fix, the fill-row ruling at 0.15, the seam-ownership
call and the wide-column census. The index is loaded whole into every session,
so for an unknown number of sessions the most recent work was the least
visible, and nothing said so except a reminder those same sessions had to
notice.

## The unit is CHARACTERS, and that is not a detail

Calibrated against the loader's own report rather than assumed. It called the
file **47.3KB** with a **24.4KB** limit:

    bytes  48,929  ->  47.8 KiB   (0.5 KiB optimistic)
    chars  48,421  ->  47.3 KiB   <- what the loader said
    lines      57
    words   7,409

A byte budget reads half a KiB high on a file this full of em-dashes and curly
quotes. **A LINE budget cannot see the file at all** — it was 57 lines while a
single hook ran to **3,409 characters**, longer than most of the notes it was
summarising. This is DOCTRINE's *"A budget that cannot see its own file"*
arriving a second time, from the opposite direction to `scope_budget.py`, which
moved 800 lines -> 27,000 words on 2026-09-14 for the mirror-image reason.

## Trimming an index is a MOVE, not a trim

A checker pulled every backticked identifier, number, ALLCAPS term and quoted
phrase out of each hook and grepped its note. **31 of 54 entries were clean; 23
flagged.** Reading the flags (not counting them) split real orphans from
formatting noise — `12.1 mm` vs `121 units`, `1.46` vs `1.5`, "Eleven" vs "11".

The worst was `palette-mismatch-bounded-2026-09-07`: a **2,649-char hook against
a 3,605-byte note**, carrying an entire second topic the note only gestured at —
the MASTER_SCOPE budget arithmetic and the missing `severity` field on `warn()`.
Six notes were amended before a single index line was shortened.

## Three index lines DISAGREED with their own notes

Not stale-and-vaguer: contradictory. The index is written at the same moment as
the note and then never re-read, so it drifts silently in a file nobody diffs.

| entry | index said | note says |
|---|---|---|
| `fill-travel-under-cover` | Fremont 286->92, gaulke 209->8, sunset trims 53->30 | 286->90, 204->8, 53->42 |
| `first-physical-sewout` | density story **RETRACTED** | **UNSETTLED** — two readings disagree 2x, a calibrated estimator put it back at 0.400 |
| `stitch-angle-convention` | the **48 deg** N was 1.41x dense | **45 deg** throughout |

**Hooks now follow the notes.** When an index and its note disagree, the note
wins: it is the thing that gets re-read and corrected.

## Two stale claims inside one sentence of a note

`emb-bot-digitizer.md` still said *"No physical sew-out has ever been done on
this project"* and that *"the DST axis question"* waited on one. Kent sewed the
Instagram icon on **2026-09-01**, and the axis was settled **2026-09-08** with no
machine involved. Corrected in place with both pointers, and with gate 1's own
test restated: *fabric settles these* — if every source you would consult owns no
machine, the gate does not apply.

## The guard

`digitizer/tools/memory_budget.py` + `digitizer/tests/test_memory_budget.py`
(6 tests), mirroring `scope_budget.py`. Enforces the character ceiling, the
260-char line cap the index states in its own header, link resolution, and the
orphan check in both directions.

**Mutation-tested, because a guard nobody has watched fail is decoration:**
baseline green, then five separate breaks — over budget, broken link, line over
cap, duplicate registration, unregistered note on disk — **all five RED**, tree
restored byte-for-byte.

**The reclaim is the HOOK, never an entry.** Every note needs its line; the line
does not need the note's contents. Deleting a memory to save room is the one
move that is always wrong.

Rebuilt: 48,421 -> 12,201 chars, 54 entries, 0 dropped, 0 broken links, 0
orphans, no BOM or mojibake. Headroom for ~56 more entries.

See also [[dst-codec-axis-discrepancy]], [[first-physical-sewout-2026-09-01]],
[[palette-mismatch-bounded-2026-09-07]].
