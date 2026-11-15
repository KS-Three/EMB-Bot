"""`tools/width_ledger.py`'s two readings, on synthetic masks: a stroke's
width and a gap's width at the ART's own medial points, so a stroke grown
fatter reads fatter, one moved a little is still found, and a gap closed
reads 0. The ledger behind the fat-ink flags (2026-11-13) rests on these."""
from __future__ import annotations

import numpy as np
from shapely.geometry import box

from tools import width_ledger as wl


def _frame():
    return wl.Frame(0.0, 0.0, 20.0, 10.0, pad=0.0)


def _bar(frame, x0, x1, y0=2.0, y1=8.0):
    return wl._fill_polys(frame, [box(x0, y0, x1, y1)])


def test_a_stroke_reads_its_width_and_its_growth():
    f = _frame()
    art = _bar(f, 5.0, 7.0)                                 # 2.0 mm wide
    s = wl.pick_strokes(art.astype(np.uint8), f, lambda x, y: None)
    assert s, "the bar is a stroke"
    pts = s[0]["pts"]
    assert abs(wl.width_at(art, pts, 0.0, 3.0) - 2.0) < 0.15
    fat = _bar(f, 4.6, 7.4)                                 # +0.4 each side
    assert abs(wl.width_at(fat, pts, 0.7, 4.0) - 2.8) < 0.15
    moved = _bar(f, 5.3, 7.3)                               # 0.3 mm aside, same width
    assert abs(wl.width_at(moved, pts, 0.7, 4.0) - 2.0) < 0.15


def test_a_gap_reads_its_width_and_zero_when_closed():
    f = _frame()
    art = (_bar(f, 3.0, 9.0) | _bar(f, 10.0, 16.0)).astype(np.uint8)   # a 1.0 mm gap
    g = wl.pick_gaps(art, f, lambda x, y: None)
    assert g, "the gap is found"
    pts = g[0]["pts"]
    assert abs(wl.width_at(art == 0, pts, 0.0, 2.0) - 1.0) < 0.15
    shut = _bar(f, 3.0, 9.6) | _bar(f, 9.4, 16.0)
    assert wl.width_at(~shut, pts, 0.35, 3.0) == 0.0


def test_runs_paint_in_order_and_close_only_their_own_rows():
    f = _frame()
    # two runs of rows 0.4 mm apart, 0.6 mm from each other: each run closes
    # on itself, never across the gap between them
    rows_a = []
    for i, y in enumerate(np.arange(2.0, 8.0, 0.4)):
        rows_a += [(2.0, y), (9.0, y)] if i % 2 == 0 else [(9.0, y), (2.0, y)]
    rows_b = [(x + 7.6, y) for x, y in rows_a]
    lab = wl._paint_runs(f, [(1, rows_a), (2, rows_b)], 0.0, wl.NEEDLE_CLOSE_MM)
    mid = int(5.0 * wl.R)
    assert (lab[mid, int(5.0 * wl.R)] == 1) and (lab[mid, int(12.0 * wl.R)] == 2)
    assert lab[mid, int(9.3 * wl.R)] == 0, "the 0.6 mm between the runs stays open"
