"""The cuts a service file carries are the design's cuts — no fewer, no more.

`tools/export-audit.mjs` (2026-10-08) read every service format back with
pystitch and counted cuts against the design. Two writers disagreed with it,
and Kent ruled on both the same day:

  - **JEF wrote no trim command at all.** `pystitch.JefWriter` defaults
    `trims=False`, so a cut lived in the file only if a machine (or reader)
    inferred one from a long move: 22 read back against Golke's 32. Ruling:
    turn trims on — each cut written as three zero-length moves, the
    convention pystitch's own reader cites for a Janome MC400E.

These are file facts, not machine facts: what a given machine does with the
records is gate 1 and unmeasured here.
"""
from __future__ import annotations

import pystitch
import pytest

from digitizer_core.adapter import design_to_pattern
from digitizer_service import formats


def _design(*records):
    st = [{"x": x, "y": y, "type": t} for x, y, t in records]
    st.append({"x": 0, "y": 0, "type": "end"})
    return {"stitches": st, "colors": [{"r": 200, "g": 30, "b": 30}]}


# Two runs 2 mm apart: close enough that no reader infers a cut from the
# distance (pystitch's JEF reader infers one over 3 mm). The first pair is
# joined by a CUT, the second by a float (a jump the design keeps).
CUT_THEN_FLOAT = _design(
    (0, 0, "stitch"), (30, 0, "stitch"), (60, 0, "stitch"),
    (60, 0, "trim"),
    (80, 0, "jump"), (80, 0, "stitch"), (110, 0, "stitch"),
    (130, 0, "jump"), (130, 0, "stitch"), (160, 0, "stitch"),
)


def _cuts(fmt, design, tmp_path):
    """Cuts between sewn runs: consecutive TRIM records count as ONE cut (a
    JEF cut is written as three zero moves and read back as three)."""
    path = tmp_path / f"out.{fmt}"
    path.write_bytes(formats.write(design_to_pattern(design), fmt))
    cuts, prev_trim, sewn = 0, False, False
    for _, _, cmd in pystitch.read(str(path)).stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.TRIM:
            if not prev_trim and sewn:
                cuts += 1
            prev_trim = True
            continue
        if c == pystitch.STITCH:
            sewn = True
        if c != pystitch.JUMP:
            prev_trim = False
    return cuts


def test_jef_carries_the_designs_cut(tmp_path):
    assert _cuts("jef", CUT_THEN_FLOAT, tmp_path) == 1
