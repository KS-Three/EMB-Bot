"""`tools/row_pitch_union.py` — the union-of-passes row pitch, pinned on synthetic fields.

The one case that matters: two interleaved passes read as their union, which
the per-pass instrument cannot see. And two different spacings must both come
back, because a reader that returns 0.40 for everything is a stopped clock.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from row_pitch_union import union_pitch  # noqa: E402


def _field(row_mm: float, offset: float = 0.0, width: float = 12.0, height: float = 12.0,
           stitch_mm: float = 3.0, angle_deg: float = 0.0, split_cycle: int = 0):
    """One needle-down pass: parallel rows `row_mm` apart, boustrophedon, 3 mm stitches.
    `split_cycle` > 0 offsets the penetrations by stitch_mm/split_cycle per row —
    a professional tatami's split pattern, the thing that fools an autocorrelation."""
    segs = []
    n_rows = int(height / row_mm)
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    for i in range(n_rows):
        y = offset + i * row_mm
        phase = (i % split_cycle) * stitch_mm / split_cycle if split_cycle else 0.0
        xs = np.arange(-phase, width + stitch_mm, stitch_mm)
        xs = np.clip(xs, 0.0, width)
        pts = [(x, y) for x in xs]
        if i % 2:
            pts = pts[::-1]
        pts = [(x * c - y_ * s, x * s + y_ * c) for x, y_ in pts]
        for j in range(len(pts) - 1):
            if pts[j] != pts[j + 1]:
                segs.append((pts[j], pts[j + 1]))
    return segs


@pytest.mark.parametrize("row_mm", [0.40, 0.20, 0.15])
def test_recovers_a_single_pass_at_three_spacings(row_mm):
    r = union_pitch(_field(row_mm))
    assert r is not None
    assert r["pitch_mm"] == pytest.approx(row_mm, abs=0.01)


def test_two_interleaved_passes_read_as_their_union():
    """0.40 + 0.40 offset 0.20 covers cloth at 0.20 — the case per-pass reading misses."""
    segs = _field(0.40) + _field(0.40, offset=0.20)
    r = union_pitch(segs)
    assert r is not None
    assert r["pitch_mm"] == pytest.approx(0.20, abs=0.01)
    assert r["rows"] >= 30


def test_a_professional_split_tatami_reads_its_row_pitch_not_its_penetration_cycle():
    """Penetrations offset by a third of a stitch each row repeat every 3 rows;
    3 x 0.14 is 0.42. The rows are still 0.14 apart and that is the answer."""
    r = union_pitch(_field(0.14, split_cycle=3, angle_deg=12.0))
    assert r is not None
    assert r["pitch_mm"] == pytest.approx(0.14, abs=0.01)
    assert abs(r["angle_deg"] - 12.0) < 1.5


def test_underlay_at_another_angle_does_not_count_as_rows():
    segs = _field(0.40) + _field(2.0, angle_deg=90.0)
    r = union_pitch(segs)
    assert r is not None
    assert r["pitch_mm"] == pytest.approx(0.40, abs=0.01)


def test_too_few_segments_returns_none():
    assert union_pitch(_field(0.40, width=2.0, height=1.0)) is None
