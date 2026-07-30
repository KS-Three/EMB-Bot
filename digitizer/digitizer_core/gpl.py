"""GIMP-palette (.gpl) parsing — the format every thread chart arrives in.

Kept separate from `threads.py` so there is exactly one parser: `tools/
gen_charts.py` generates every brand in `chart_data/` through this function,
and nothing else reads a .gpl.

A body line is `R G B <name words> <catalog number>`, whitespace separated,
after a three-or-four line header. The catalog number is the last field and
always contains a digit in these charts, which is how it is told apart from a
name-only line — some palettes ship without codes, and then the whole
remainder is the name.

This mirrors `parseGpl` in `tools/build-threads.mjs` deliberately and exactly.
The browser and the service must agree on how many colors a brand has and what
they are called, so `tests/test_charts.py` asserts the two agree rather than
trusting that they do.
"""
from __future__ import annotations

import re

_LINE = re.compile(r"^(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+(.+)$")
_HEADER = re.compile(r"^(gimp palette|name:|columns:)", re.IGNORECASE)


def parse_gpl(text: str) -> list[tuple[str, str, tuple[int, int, int]]]:
    """-> [(catalog_number, name, (r, g, b))] in file order."""
    entries: list[tuple[str, str, tuple[int, int, int]]] = []
    for raw in re.split(r"\r\n|\r|\n", text):
        line = raw.strip()
        if not line or line.startswith("#") or _HEADER.match(line):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if max(r, g, b) > 255:
            continue
        rest = m.group(4).strip()
        parts = rest.rsplit(None, 1)
        if len(parts) == 2 and any(c.isdigit() for c in parts[1]):
            name, number = parts[0].strip(), parts[1].strip()
        else:
            name, number = rest, ""
        # A line that is nothing but a catalog number still names a real spool.
        if not name:
            name, number = number, ""
        if name:
            entries.append((number, name, (r, g, b)))
    return entries
