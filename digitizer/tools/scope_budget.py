#!/usr/bin/env python
"""Where MASTER_SCOPE's 27,000 words actually go, and what is left.

`MASTER_SCOPE.md` states its own rule: *"Current state ONLY, under an
800-line budget"*, with per-area detail in `docs/scope/` and dated snapshots
in `docs/scope-history.md`. **Nothing enforced it**, and on 2026-09-07 the
file reached **799** — one line of headroom, with the next entry blocked.

The instinct at that point is to retire a live defect. **Measured, that is
the wrong place to cut**, and the numbers are why this file exists rather
than a note:

    section                                    lines   share
    Capability areas                             255   31.9%
    Cross-cutting issues                         141   17.6%
    Live defects                                 138   17.2%   (30 entries)
    Waiting on Kent                               95   11.9%
    How this document works                       70    8.8%

**Live defects are 17% of the file.** The pressure is in the capability
areas, and area 1 alone takes **107 lines against a `docs/scope/` detail
file of 3,871** -- the offload mechanism the document already documents,
already built, and pointed at from the section header. Areas 2, 4 and 5 take
14, 21 and 43.

Retiring a numbered defect also reclaims nothing: the Closed section keeps
every number *"because ten other docs cite them by number"*, so moving an
entry from Live to Closed swaps a line for a line. **The only real reclaim is
summarising a capability area back down to a summary.**

    .venv/bin/python -m tools.scope_budget       # Windows: .venv/Scripts/
    python tools/scope_budget.py                 # run from digitizer/
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCOPE = REPO / "MASTER_SCOPE.md"
BUDGET = 27_000

# `python tools/scope_budget.py` puts `tools/` on sys.path, NOT `digitizer/`,
# so `tools._console` is unimportable until this line. Both invocations above
# have to keep working; the repo already uses this pattern in ten other tools.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools._console import utf8_console                    # noqa: E402


def word_count(text: str) -> int:
    """The budget's unit since 2026-09-14 (Kent's ruling). Whitespace-split.

    **Not `wc -w`, and not lines.**

    Lines went first: they could not see this file's content in either
    direction. The 2026-09-14 correction pass REMOVED 181 words and 1,208
    characters while ADDING 45 lines, because the text it replaced sat on very
    long lines and the replacement wrapped at the file's median 76 — and the
    file holds a single 23,638-character line, 13.5% of its characters counted
    as 1 of 801. Worse, the cheapest way to obey a line budget is to join
    paragraphs onto long lines: no content saved, every future diff a
    whole-paragraph rewrite, growth hidden from the number meant to catch it.

    `wc -w` was rejected on measurement, not taste: it is LOCALE-DEPENDENT on
    this file — 26,381 under `C`/`POSIX`, 27,289 under `C.UTF-8`, a 908-word
    (3.4%) gap, because the C locale mis-splits the em-dashes, arrows and `×`
    this document is full of. Cloud containers here run with `LANG` unset, so a
    session would have read 908 fewer words than Kent's box. A budget that
    answers differently depending on who asks is not a budget.

    `str.split()` agrees with `awk '{n+=NF}'` — the command the document's own
    rule 4 names — under every locale tested. `wc -m` drifts like `wc -w`.
    """
    return len(text.split())


def line_count(text: str) -> int:
    """`wc -l`, which is what "an 800-line budget" has always meant here.

    `text.split("\n")` on a file with a trailing newline returns one extra
    empty element, so the first cut of this tool reported 800 for a file
    `wc -l` calls 799 — an instrument off by one against the number it
    exists to enforce, which would have fired the budget test a line early.
    """
    return len(text.splitlines())


def sections(text: str) -> list[tuple[str, int]]:
    """`## ` headings and the line count each one owns, in file order."""
    lines = text.splitlines()
    marks = [i for i, l in enumerate(lines) if l.startswith("## ")]
    out = []
    for j, i in enumerate(marks):
        end = marks[j + 1] if j + 1 < len(marks) else len(lines)
        out.append((lines[i][3:].strip(), end - i))
    return out


def areas(text: str) -> list[tuple[str, int, int]]:
    """Each capability area: its lines here, and its detail file's lines.

    The gap between the two is the reclaim. A summary that has grown to a
    third of the budget while its own detail file holds thousands of lines is
    the document's own offload mechanism sitting unused.
    """
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines)
                     if l.startswith("## Capability areas"))
    except StopIteration:                                 # pragma: no cover
        return []
    end = next((i for i, l in enumerate(lines)
                if i > start and l.startswith("## ")), len(lines))
    marks = [i for i in range(start, end) if lines[i].startswith("### ")]
    out = []
    for j, i in enumerate(marks):
        stop = marks[j + 1] if j + 1 < len(marks) else end
        name = lines[i][4:].strip()
        m = re.search(r"\((docs/scope/[^)]+)\)", name)
        detail = 0
        if m and (REPO / m.group(1)).is_file():
            detail = line_count((REPO / m.group(1)).read_text(
                encoding="utf-8"))
        out.append((name.split(" — ")[0], stop - i, detail))
    return out


def live_and_closed(text: str) -> tuple[list[tuple[str, int, str]],
                                        list[tuple[str, int, str]]]:
    """The numbered entries of the Live defects section, split at `### Closed`.

    **The split is the whole trick.** `### Closed` is an H3 INSIDE the Live
    defects H2, and its twelve entries are pointers by design — they carry a
    date inline ("RESOLVED 2026-08-19") rather than the `*(verb date —
    source)*` tail the live entries take. A first cut of this sliced on the H2
    alone and reported **twelve** rule violations, every one of them a closed
    pointer behaving exactly as documented. Read the matches, not the count.

    Each entry is (number, 0-based line, joined body) — bodies continue until
    the next numbered line, because entries here wrap.
    """
    lines = text.splitlines()
    ds = next(i for i, l in enumerate(lines) if l.startswith("## Live defects"))
    de = next(i for i, l in enumerate(lines)
              if i > ds and l.startswith("## "))
    cut = next((i for i in range(ds, de)
                if lines[i].startswith("### Closed")), de)

    def grab(a: int, b: int):
        out, cur = [], None
        for i in range(a, b):
            m = re.match(r"^(\d+)\. ", lines[i])
            if m:
                if cur:
                    out.append(tuple(cur))
                cur = [m.group(1), i, lines[i]]
            elif cur and lines[i].strip():
                cur[2] += " " + lines[i]
        if cur:
            out.append(tuple(cur))
        return out

    return grab(ds, cut), grab(cut, de)


def main(argv: list[str]) -> int:
    utf8_console()
    text = SCOPE.read_text(encoding="utf-8")
    total = line_count(text)
    words = word_count(text)
    print(f"MASTER_SCOPE.md — {words:,} words against a {BUDGET:,}-word budget "
          f"({BUDGET - words:,} left); {total} lines, which is NOT the budget\n")

    print(f"{'section':46} {'lines':>6} {'share':>7}")
    print("-" * 61)
    for name, n in sorted(sections(text), key=lambda r: -r[1]):
        print(f"{name[:46]:46} {n:6} {100 * n / total:6.1f}%")

    rows = areas(text)
    worst = max(rows, key=lambda r: r[1], default=("", 0, 0))
    if rows:
        print(f"\n{'capability area':46} {'here':>6} {'detail':>7}")
        print("-" * 61)
        for name, here, detail in sorted(rows, key=lambda r: -r[1]):
            print(f"{name[:46]:46} {here:6} {detail:7}")
    live, closed = live_and_closed(text)
    print(f"\nnumbered entries: {len(live)} live, {len(closed)} closed pointers")

    if rows:
        print(f"\nThe reclaim is {worst[0]}: {worst[1]} lines here against "
              f"{worst[2]} in its own detail file. Retiring a numbered defect "
              f"reclaims NOTHING — the Closed section keeps every number, so "
              f"the move swaps a line for a line.")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
