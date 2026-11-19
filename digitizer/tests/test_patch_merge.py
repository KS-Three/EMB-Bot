"""`script_strokes_patch_merge` (built OFF 2026-11-19): a patch column that continues a
stroke's end joins that column; a far, turned or off-art patch stays a patch."""
from __future__ import annotations

import math

from shapely.geometry import box

from digitizer_core import patch_merge as pm
from digitizer_core.columns import Column
from digitizer_core.script_strokes import _ribbon


def _col(x0, n, step=0.4, half=1.0, ang=90.0, y=0.0):
    a = math.radians(ang)
    dx, dy = half * math.cos(a), half * math.sin(a)
    sts = [((x0 + step * i - dx, y - dy), (x0 + step * i + dx, y + dy)) for i in range(n)]
    return Column(stations=sts, piece=_ribbon(sts), kind="curved", axis=None, width_mm=2 * half)


POLY = box(-1, -3, 30, 3)


def test_off_by_default():
    assert pm.armed() is False
    with pm.patch_merge_scope(True):
        assert pm.armed() is True
    assert pm.armed() is False


def test_patch_beyond_the_end_joins_the_column():
    c = _col(0.0, 10)                       # ends at x = 3.6
    p = _col(4.8, 4)                        # starts 1.2 mm on
    cols, left, n = pm.merge_patches([c], [p], POLY, 0.4)
    assert n == 1 and left == []
    assert len(cols[0].stations) > len(c.stations) + len(p.stations) - 1
    xs = [(a[0] + b[0]) / 2 for a, b in cols[0].stations]
    assert xs == sorted(xs)                 # one monotone run, gap filled at the pitch
    assert max(b[1] for a, b in cols[0].stations) <= 1.0001


def test_patch_before_the_start_is_prepended():
    c = _col(10.0, 10)
    p = _col(7.2, 4)                        # ends at 8.4, 1.6 mm before the column
    cols, left, n = pm.merge_patches([c], [p], POLY, 0.4)
    assert n == 1
    xs = [(a[0] + b[0]) / 2 for a, b in cols[0].stations]
    assert xs == sorted(xs) and abs(xs[0] - 7.2) < 1e-9


def test_far_patch_stays():
    c = _col(0.0, 10)
    p = _col(10.0, 4)
    cols, left, n = pm.merge_patches([c], [p], POLY, 0.4)
    assert n == 0 and left == [p] and cols == [c]


def test_turned_patch_stays():
    c = _col(0.0, 10)
    p = _col(4.8, 4, ang=0.0)               # crosses 90 degrees off
    cols, left, n = pm.merge_patches([c], [p], POLY, 0.4)
    assert n == 0 and left == [p]


def test_gap_off_the_art_keeps_the_patch():
    c = _col(0.0, 10)
    p = _col(4.8, 4)
    hole = box(3.8, -3, 4.6, 3)             # the gap between them is not ink
    from shapely.geometry import box as b
    poly = b(-1, -3, 30, 3).difference(hole)
    cols, left, n = pm.merge_patches([c], [p], poly, 0.4)
    assert n == 0 and left == [p]


def test_no_patches_passes_through():
    c = _col(0.0, 10)
    assert pm.merge_patches([c], [], POLY, 0.4) == ([c], [], 0)
