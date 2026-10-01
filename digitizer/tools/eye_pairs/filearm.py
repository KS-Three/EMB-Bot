"""A design read from a stitch file: the pro's own digitize beside ours.

The third kind of arm (2026-10-01, Kent's pick after the texture sitting):
not a flag on today's engine and not an older engine, but a professional's
machine file for the same logo, read through `adapter.pattern_to_design` so
the page draws both sides by one rule. A `__file__` arm names one file per
fixture; a fixture without one gets no row. Everything about the design is
what the file holds -- the colours come from its thread list (a PES has one,
a DST does not), and there is no `runs` index because a machine file has no
run structure left in it.
"""
from __future__ import annotations

from pathlib import Path

import pystitch

from digitizer_core.adapter import pattern_to_design


def design_from_file(path: str | Path, name: str | None = None) -> dict:
    """-> the file's stitches as an EMB-Bot Design dict (0.1 mm, y up)."""
    path = Path(path)
    pattern = pystitch.read(str(path))
    if pattern is None:
        raise ValueError(f"unreadable stitch file: {path}")
    return pattern_to_design(pattern, name=name or path.stem)
