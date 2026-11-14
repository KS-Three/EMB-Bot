"""GIMP-palette (.gpl) parsing — the format every thread chart arrives in.

Kept separate from `threads.py` so there is exactly one parser: `tools/
gen_charts.py` generates every brand in `chart_data/` through this function,
and nothing else reads a .gpl.

A body line is `R G B <name words> <catalog number>`, whitespace separated,
after a three-or-four line header. The catalog number is the last field and
always contains a digit in these charts, which is how it is told apart from a
name-only line — some palettes ship without codes, and then the whole
remainder is the name.

Two Simthread charts add a fifth column after the number: the spool's measured
L,a,b ("Black 900 22.34,-0.6,-0.46"). That triple is not a catalog number, so
it is dropped before the last field is read (taking it as the number shipped
"22.34,-0.6,-0.46" as the Thread # for all 78 rows, found 2026-11-13). The Glow
chart's number column is a literal "n/a", which means "no number", not a name
word: it becomes an empty number with a clean name.

This mirrors `parseGpl` in `tools/build-threads.mjs` deliberately and exactly.
The browser and the service must agree on how many colors a brand has and what
they are called, so `tests/test_charts.py` asserts the two agree rather than
trusting that they do.
"""
from __future__ import annotations

import re

_LINE = re.compile(r"^(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+(.+)$")
_LAB_TRIPLE = re.compile(r"\s+-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$")
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
        rest = _LAB_TRIPLE.sub("", m.group(4).strip())
        parts = rest.rsplit(None, 1)
        if len(parts) == 2 and parts[1].lower() == "n/a":
            name, number = parts[0].strip(), ""
        elif len(parts) == 2 and any(c.isdigit() for c in parts[1]):
            name, number = parts[0].strip(), parts[1].strip()
        else:
            name, number = rest, ""
        # A line that is nothing but a catalog number still names a real spool.
        if not name:
            name, number = number, ""
        name = " ".join(name.split())
        if name:
            entries.append((number, name, (r, g, b)))
    return entries
