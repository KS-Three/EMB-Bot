#!/usr/bin/env python
"""What `.claude/memory/MEMORY.md` costs, and how close it is to vanishing.

`MEMORY.md` is the index the memory system loads WHOLE into every session. It
has a hard ceiling, and past it the loader **truncates from the bottom and says
so only in a `<system-reminder>` nobody is required to read**. The entries do
not degrade; they stop existing.

**That already happened.** On 2026-09-15 the file stood at 48,421 characters
against a 24,986 ceiling and the loader reported: *"Only part of it was loaded:
16 of 57 lines were cut off, starting at line 42."* Sixteen memories — every
one written after 2026-09-03, so the NEWEST work — were invisible to the
session that was supposed to be using them, including the DST axis fix, the
fill-row ruling and the wide-column census.

    .venv/bin/python -m tools.memory_budget

The reclaim is the HOOK text, never an entry. Every note keeps its line; the
line just stops carrying the note's contents. A hook exists to help a session
decide whether to open the file.
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
MEMDIR = REPO / ".claude" / "memory"
INDEX = MEMDIR / "MEMORY.md"

#: Characters, not bytes and not lines. See `char_count`.
BUDGET = 24_986

#: The per-line target the index states in its own header.
LINE_CAP = 260

# `python tools/memory_budget.py` puts `tools/` on sys.path, NOT `digitizer/`,
# so `tools._console` is unimportable until this line. See that module for
# why a tool that prints doc text has to widen its own stdout.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools._console import utf8_console                    # noqa: E402

ENTRY = re.compile(r"^- \[(?P<title>.+?)\]\((?P<rel>.+?)\)\s*—\s*(?P<hook>.*)$")


def char_count(text: str) -> int:
    """`len(text)` — Unicode CHARACTERS. Not bytes, not lines, not words.

    Calibrated against the loader's own report rather than assumed. On
    2026-09-15 it called this file **47.3KB** with a **24.4KB** limit:

        bytes  48,929  ->  47.8 KiB   (wrong, and 0.5 KiB optimistic)
        chars  48,421  ->  47.3 KiB   <- what the loader said
        lines      57
        words   7,409

    The gap is real: this file is full of em-dashes, arrows and curly quotes at
    2-3 bytes each, so a byte budget reads ~0.5 KiB high and would let the index
    cross the real ceiling while still reporting headroom.

    **Lines cannot see this file at all**, which is the trap `scope_budget.py`
    hit from the other direction and DOCTRINE records as *"A budget that cannot
    see its own file"*. MEMORY.md was 57 lines when it overflowed — one line per
    memory, a number that barely moves — while single hooks ran past 3,400
    characters. A line budget would have read 57 and seen nothing wrong.
    """
    return len(text)


def kib(n: int) -> float:
    """The loader reports KiB, so the tool does too, or the numbers won't match."""
    return n / 1024


def entries(text: str) -> list[tuple[str, str, str, int]]:
    """Every registry line as (title, relative path, hook, full line length)."""
    out = []
    for line in text.splitlines():
        m = ENTRY.match(line)
        if m:
            out.append((m.group("title"), m.group("rel"), m.group("hook"),
                        len(line)))
    return out


def unresolved(text: str) -> list[str]:
    """Registry paths with no file behind them.

    Relative to the index, so the one `../../docs/` entry resolves too.
    """
    return [rel for _t, rel, _h, _n in entries(text)
            if not (MEMDIR / rel).resolve().is_file()]


def unregistered(text: str) -> list[str]:
    """Note files on disk that no registry line points at.

    The skill's orphan check, and the reason it matters here is narrower than
    tidiness: an unregistered note is one the recall step cannot reach, so it
    is written, committed, and inert.
    """
    listed = {(MEMDIR / rel).resolve() for _t, rel, _h, _n in entries(text)}
    return sorted(p.name for p in MEMDIR.glob("*.md")
                  if p.name != "MEMORY.md" and p.resolve() not in listed)


def main(argv: list[str]) -> int:
    utf8_console()
    text = INDEX.read_text(encoding="utf-8")
    n = char_count(text)
    rows = entries(text)
    left = BUDGET - n

    print(f"MEMORY.md — {n:,} chars ({kib(n):.1f} KiB) against a {BUDGET:,} "
          f"ceiling ({kib(BUDGET):.1f} KiB); {left:,} left, {len(rows)} entries")
    if left > 0 and rows:
        print(f"room for roughly {left // max(1, n // len(rows))} more entries "
              f"at the current average of {n // len(rows)} chars\n")
    else:
        print()

    over = [r for r in rows if r[3] > LINE_CAP]
    print(f"{'entry':52} {'chars':>6}")
    print("-" * 60)
    for title, _rel, _hook, ln in sorted(rows, key=lambda r: -r[3])[:10]:
        print(f"{title[:52]:52} {ln:6}")

    print(f"\nlongest {max((r[3] for r in rows), default=0)}, "
          f"cap {LINE_CAP}, over cap {len(over)}")

    bad, orphans = unresolved(text), unregistered(text)
    print(f"broken links: {bad or 'none'}")
    print(f"unregistered notes: {orphans or 'none'}")

    if n > BUDGET:
        print(f"\nOVER BUDGET by {n - BUDGET:,} chars. The loader will drop "
              f"entries from the BOTTOM — the newest memories — silently. "
              f"Shorten the longest HOOKS above and move the detail into the "
              f"note; deleting an entry is not the reclaim.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
