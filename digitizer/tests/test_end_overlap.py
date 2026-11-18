"""`lettering_columns_end_overlap_cut` (built OFF 2026-11-18): an end station
lying over a LONGER script column at a turned cross goes; parallel overlap,
the longer column and a short column are never touched."""
from __future__ import annotations

import math

from digitizer_core import end_overlap
from digitizer_core.columns import Column
from digitizer_core.script_strokes import _ribbon


def _col(points, half=1.0, turn_deg=0.0):
    """A vertical-ish column: crosses `half` each side, tilted `turn_deg` off horizontal."""
    t = math.radians(turn_deg)
    dx, dy = half * math.cos(t), half * math.sin(t)
    sts = [((x - dx, y - dy), (x + dx, y + dy)) for x, y in points]
    return Column(stations=sts, piece=_ribbon(sts), kind="curved", axis=None, width_mm=2 * half)


def _long():
    return _col([(0.0, 0.4 * i) for i in range(40)])             # horizontal crosses, x -1..1


def test_off_scope_is_default():
    assert end_overlap.armed() is False


def test_turned_end_over_a_longer_column_is_cut():
    stem = _long()
    # a hairline arriving across the stem, crosses 90 degrees off, its last stations on the stem
    tail = _col([(6.0 - 0.4 * i, 7.0) for i in range(16)], half=0.6, turn_deg=90.0)
    out, n = end_overlap.cut_columns([stem, tail])
    assert n > 0 and len(out[1].stations) < len(tail.stations)
    assert out[0] is stem                                        # the longer column is never cut
    assert len(out[1].stations) >= end_overlap.KEEP


def test_parallel_overlap_is_left_alone():
    stem = _long()
    run = _col([(0.2, 8.0 + 0.4 * i) for i in range(16)])        # same cross angle, on the stem
    out, n = end_overlap.cut_columns([stem, run])
    assert n == 0 and out[1] is run


def test_short_column_keeps_its_stations():
    stem = _long()
    short = _col([(0.0, 8.0 + 0.4 * i) for i in range(end_overlap.KEEP)], turn_deg=90.0)
    out, n = end_overlap.cut_columns([stem, short])
    assert n == 0


def test_one_column_passes_through():
    c = _long()
    out, n = end_overlap.cut_columns([c])
    assert n == 0 and out == [c]
