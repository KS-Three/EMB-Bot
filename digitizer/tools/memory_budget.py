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
    .venv/bin/python -m tools.memory_budget --sort     # put the entries in order

Entries are alphabetical by link filename (2026-10-24): a PR inserts its line
at its sorted place, not at the bottom, so two open PRs stop colliding on the
last line of the file.

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
#: Index lines for notes dated before 2026-09-15, split out 2026-10-23. NOT
#: auto-loaded, so it has no character ceiling — only the per-line cap.
ARCHIVE = MEMDIR / "MEMORY-archive.md"
INDEXES = ("MEMORY.md", "MEMORY-archive.md")

#: Characters, not bytes and not lines, counted on the file AS STORED. See
#: `char_count`. This is 24.4 KiB, the figure the loader printed on 2026-09-15.
#: The loader's own constant is 25,000 (`Xee=25000` in the 2026-10-06 CLI
#: build), so the 14 characters between them are margin, kept on purpose.
BUDGET = 24_986

#: The per-line target the index states in its own header.
LINE_CAP = 260

# `python tools/memory_budget.py` puts `tools/` on sys.path, NOT `digitizer/`,
# so `tools._console` is unimportable until this line. See that module for
# why a tool that prints doc text has to widen its own stdout.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools._console import utf8_console                    # noqa: E402

ENTRY = re.compile(r"^- \[(?P<title>.+?)\]\((?P<rel>.+?)\)\s*—\s*(?P<hook>.*)$")


#: What JavaScript's `String.prototype.trim` strips (the spec's WhiteSpace and
#: LineTerminator), by code point. Python's `str.strip()` is a different set: it
#: takes U+001C-U+001F and U+0085 and leaves U+FEFF.
_JS_WHITESPACE = "".join(map(chr, (
    0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B),
    0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF)))


def read_stored(path: pathlib.Path) -> str:
    """The file's text exactly as it sits on disk: no newline translation.

    `Path.read_text` translates CRLF to LF, so on Kent's Windows box it showed
    this budget a file ~146 characters shorter than the loader reads. Decoding
    the bytes keeps every `\\r`.
    """
    return pathlib.Path(path).read_bytes().decode("utf-8")


def char_count(text: str) -> int:
    """What the loader's ceiling counts: UTF-16 units of the TRIMMED text, as stored.

    **Read the file with `read_stored`, not `read_text`** (found 2026-10-26).
    The loader does not translate newlines, so a CRLF working copy costs one
    extra character per line, and `read_text` hid exactly that: this budget
    could pass on a Windows copy the loader would cut. The count is
    taken from the loader's own code in the CLI binary
    (`~/.local/bin/claude.exe`, 2026-10-06 build; search it for "Only part of
    it was loaded"):

        uu="MEMORY.md",lL=200,Xee=25000
        function _tt(t){let r=t.trim();
          return{trimmed:r,lineCount:count(r,"\\n")+1,byteCount:r.length}}

    `byteCount` is `r.length`, a JavaScript string length, so UTF-16 code
    units: a non-BMP character (an emoji) is TWO, and a CR is one. It is also
    computed AFTER `trim()`, so the trailing newline is free. `lL=200` is a
    second, line ceiling; the index is far from it and the character ceiling
    binds first while lines average over 125 characters.

    Not bytes, not lines, not words. Calibrated against the loader's own report
    rather than assumed. On
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
    return len(text.strip(_JS_WHITESPACE).encode("utf-16-le")) // 2


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


def unregistered(text: str, archive_text: str = "") -> list[str]:
    """Note files on disk that no registry line (live OR archive) points at.

    The skill's orphan check, and the reason it matters here is narrower than
    tidiness: an unregistered note is one the recall step cannot reach, so it
    is written, committed, and inert.
    """
    listed = {(MEMDIR / rel).resolve()
              for _t, rel, _h, _n in entries(text) + entries(archive_text)}
    return sorted(p.name for p in MEMDIR.glob("*.md")
                  if p.name not in INDEXES and p.resolve() not in listed)


def double_registered(text: str, archive_text: str) -> list[str]:
    """Paths indexed more than once across the two files (or twice in one).

    A note must sit in exactly one index: in both, the archive pass that moves
    a line leaves a stale copy behind and the two files drift apart.
    """
    seen: dict[pathlib.Path, int] = {}
    for _t, rel, _h, _n in entries(text) + entries(archive_text):
        key = (MEMDIR / rel).resolve()
        seen[key] = seen.get(key, 0) + 1
    return sorted(k.name for k, n in seen.items() if n > 1)


def sort_key(rel: str) -> tuple[str, str]:
    """Where an entry sorts: its link target's FILENAME, case-folded (the
    directory part of the one `../../docs/` entry does not count), then the
    whole path so two equal names still order the same way every time."""
    return (pathlib.PurePosixPath(rel).name.lower(), rel)


def order_problems(text: str) -> list[str]:
    """Why the live index is not in its sorted order; empty when it is.

    Entries are kept ALPHABETICAL by link filename, with the archive pointer
    first. Every PR used to append its line at the BOTTOM, so any two open PRs
    conflicted there; an alphabetical insert collides only when two notes
    sort next to each other. Each message says where the line belongs.
    """
    rows = entries(text)
    problems: list[str] = []
    if rows and rows[0][1] != ARCHIVE.name:
        problems.append(f"the archive pointer ({ARCHIVE.name}) must be the FIRST entry, "
                        f"under the header; the first entry is {rows[0][1]!r}")
    body = [(t, rel) for t, rel, _h, _n in rows if rel != ARCHIVE.name]
    keys = [sort_key(rel) for _t, rel in body]
    want = sorted(body, key=lambda r: sort_key(r[1]))
    descent = next((i for i in range(1, len(keys)) if keys[i] < keys[i - 1]), None)
    if descent is not None:
        # the misplaced line is the one whose removal leaves the rest in order:
        # the latecomer appended at the bottom, or the line dropped in too early
        rest = keys[:descent] + keys[descent + 1:]
        odd = descent if rest == sorted(rest) else descent - 1
        rel = body[odd][1]
        j = [r[1] for r in want].index(rel)
        before = want[j - 1][1] if j else "the archive pointer"
        after = want[j + 1][1] if j + 1 < len(want) else "the end of the file"
        problems.append(f"{rel!r} is out of order: it goes after {before!r} and before {after!r} "
                        f"(entries are alphabetical by link filename; `python -m tools.memory_budget "
                        f"--sort` rewrites the file in order)")
    return problems


def sorted_text(text: str) -> str:
    """`text` with its registry lines in the order `order_problems` wants:
    the header and any other prose where they are, the archive pointer first,
    the rest alphabetical by link filename. The line endings of `text` are kept
    (CRLF in, CRLF out), so a copy read as stored round-trips unchanged."""
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    idx = [i for i, ln in enumerate(lines) if ENTRY.match(ln)]
    if not idx:
        return text
    pointer = [lines[i] for i in idx if ENTRY.match(lines[i]).group("rel") == ARCHIVE.name]
    rest = sorted((lines[i] for i in idx if ENTRY.match(lines[i]).group("rel") != ARCHIVE.name),
                  key=lambda ln: sort_key(ENTRY.match(ln).group("rel")))
    for i, ln in zip(idx, pointer + rest):
        lines[i] = ln
    return eol.join(lines) + (eol if text.endswith("\n") else "")


def main(argv: list[str]) -> int:
    utf8_console()
    if "--sort" in argv:
        before = read_stored(INDEX)
        lf = before.replace("\r\n", "\n")          # the rewrite is LF either way
        after = sorted_text(lf)
        INDEX.write_text(after, encoding="utf-8", newline="\n")
        print("MEMORY.md entries sorted" if after != lf
              else "MEMORY.md already in order" if after == before
              else "MEMORY.md already in order; rewritten with LF line endings")
        return 0
    text = read_stored(INDEX)
    n = char_count(text)
    rows = entries(text)
    left = BUDGET - n

    print(f"MEMORY.md — {n:,} chars ({kib(n):.1f} KiB) as stored on disk, against a "
          f"{BUDGET:,} ceiling ({kib(BUDGET):.1f} KiB); {left:,} left, {len(rows)} entries")
    crs = text.count("\r")
    if crs:
        print(f"CRLF: this copy has {crs:,} carriage returns and the loader counts "
              f"every one; with LF endings it is "
              f"{char_count(text.replace(chr(13) + chr(10), chr(10))):,}. "
              f"`.gitattributes` pins .claude/memory/*.md to LF; a pull that changes "
              f"this file rewrites it as LF, or convert every note now with "
              f"`git rm -q --cached -r .claude/memory` then "
              f"`git checkout HEAD -- .claude/memory` (plain `git checkout --` skips "
              f"files git thinks are unchanged).")
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

    archive_text = read_stored(ARCHIVE) if ARCHIVE.is_file() else ""
    arows = entries(archive_text)
    print(f"MEMORY-archive.md — {char_count(archive_text):,} chars, "
          f"{len(arows)} entries, not auto-loaded; longest "
          f"{max((r[3] for r in arows), default=0)}, "
          f"over cap {sum(1 for r in arows if r[3] > LINE_CAP)}")

    bad = unresolved(text) + unresolved(archive_text)
    orphans = unregistered(text, archive_text)
    print(f"broken links: {bad or 'none'}")
    print(f"unregistered notes: {orphans or 'none'}")
    print(f"indexed twice: {double_registered(text, archive_text) or 'none'}")
    print(f"order: {order_problems(text) or 'alphabetical by link filename'}")

    if n > BUDGET:
        print(f"\nOVER BUDGET by {n - BUDGET:,} chars. The loader will drop "
              f"entries from the BOTTOM — the newest memories — silently. "
              f"Shorten the longest HOOKS above and move the detail into the "
              f"note; deleting an entry is not the reclaim.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    import sys as _sys
    if {"-h", "--help"} & set(_sys.argv[1:]):
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
