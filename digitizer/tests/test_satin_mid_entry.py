"""`cfg.satin_mid_entry` (built OFF 2026-10-08): reach a satin column's start
along its own centreline instead of cutting to it."""
from __future__ import annotations

import math

from digitizer_core import stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.stage7_sequence import _MID_ENTRY_MAX_STITCHES, _satin_mid_entry
from digitizer_core.stitches import StitchRun


def _column(length_mm: float, width_mm: float = 2.0, pitch: float = 0.4):
    """A straight horizontal satin column, zigzagging between y=0 and y=width."""
    n = int(length_mm / pitch)
    return [(i * pitch, 0.0 if i % 2 == 0 else width_mm) for i in range(n + 1)]


def test_default_is_off():
    assert PipelineConfig().satin_mid_entry is False


def test_mid_column_cursor_walks_the_centreline_to_the_start():
    sat = StitchRun(_column(20.0), kind=stitches.SATIN, shape_id="S1")
    cursor = (10.0, 3.5)                       # 2.5 mm above the centreline at x=10
    out = _satin_mid_entry([sat], cursor, trim_at=3.0)
    assert len(out) == 2 and out[1] is sat
    travel = out[0]
    assert travel.kind == stitches.TRAVEL and travel.shape_id == "S1"
    assert math.dist(cursor, travel.points[0]) <= 3.0          # no cut to get on
    # lands on the first station, between the first two satin points
    assert travel.points[-1] == (0.2, 1.0)
    # every travel stitch is on the centreline, inside the column the satin covers
    assert all(abs(y - 1.0) < 1e-9 and -1e-9 <= x <= 20.0 for x, y in travel.points)
    steps = [math.dist(a, b) for a, b in zip(travel.points, travel.points[1:])]
    assert max(steps) <= 2.5 + 1e-9


def test_unchanged_when_start_is_in_reach_or_nothing_is():
    sat = StitchRun(_column(20.0), kind=stitches.SATIN)
    assert _satin_mid_entry([sat], (0.0, -2.0), 3.0) == [sat]   # start in reach
    assert _satin_mid_entry([sat], (10.0, 9.0), 3.0) == [sat]   # column out of reach


def test_unchanged_behind_an_underlay_or_over_budget():
    under = StitchRun([(0, 1), (20, 1)], kind=stitches.UNDERLAY)
    sat = StitchRun(_column(20.0), kind=stitches.SATIN)
    assert _satin_mid_entry([under, sat], (10.0, 3.5), 3.0) == [under, sat]
    long = StitchRun(_column(200.0), kind=stitches.SATIN)
    far = (2.5 * (_MID_ENTRY_MAX_STITCHES + 5), 3.5)
    assert _satin_mid_entry([long], far, 3.0) == [long]
