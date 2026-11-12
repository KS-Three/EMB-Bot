"""`stage7_sequence._parts_within_margin` answers `a.distance(b) <= margin`
for two big thread unions through a spatial index over their parts
(2026-11-11, speed only), and `_within_margin` hands it only the pairs big
enough for the plain `distance` to be slow.

The low-poly dolphin at 300 mm spent 108.6 s on ONE such `distance` (two
blocks of 12,985 and 86,540 parts); the index answers it in 0.04 s. What must
not move is the answer: `_hoist_same_thread` reorders thread on it.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from digitizer_core import stage7_sequence as s7
from digitizer_core.stage7_sequence import _parts_within_margin, _within_margin


def _thread(rng, n: int, x0: float, y0: float, span: float):
    """A block's sewn geometry as `_block_thread_geom` builds it: a union of
    short runs, with the odd one-point run left as a Point."""
    parts = []
    for _ in range(n):
        x, y = x0 + rng.uniform(0, span), y0 + rng.uniform(0, span)
        if rng.random() < 0.1:
            parts.append(Point(x, y))
            continue
        pts = [(x, y)]
        for _ in range(int(rng.integers(1, 5))):
            x, y = x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5)
            pts.append((x, y))
        parts.append(LineString(pts))
    return unary_union(parts)


@pytest.mark.parametrize("margin", [0.0, 0.5, 2.0])
def test_parts_answer_is_distance_answer(margin):
    """Pairs laid out at every separation from overlapping to well apart, so
    both answers occur at every margin."""
    rng = np.random.default_rng(1111)
    seen = {True: 0, False: 0}
    for k in range(120):
        a = _thread(rng, int(rng.integers(1, 60)), 0.0, 0.0, 10.0)
        gap = rng.uniform(-6.0, 6.0)
        b = _thread(rng, int(rng.integers(1, 60)), 10.0 + gap, rng.uniform(-4, 4), 10.0)
        want = a.distance(b) <= margin
        assert _parts_within_margin(a, b, margin) is want, (k, a.distance(b))
        assert _parts_within_margin(b, a, margin) is want, (k, a.distance(b))
        seen[want] += 1
    assert seen[True] >= 15 and seen[False] >= 15


def test_parts_answer_at_the_margin_itself():
    """Two runs exactly the margin apart are within it (`<=`), and a hair
    further are not: the index's `dwithin` draws the line where `distance`
    does."""
    a = unary_union([LineString([(0, 0), (10, 0)]), LineString([(0, 5), (10, 5)])])
    for gap, want in ((0.5, True), (0.5000001, False), (0.4999999, True)):
        b = unary_union([LineString([(0, -gap), (10, -gap)]), Point(50, 50)])
        assert (a.distance(b) <= 0.5) is want
        assert _parts_within_margin(a, b, 0.5) is want
        assert _parts_within_margin(b, a, 0.5) is want


def test_parts_answer_on_single_geometries():
    """A bare LineString or Point is one part."""
    line, far, near = LineString([(0, 0), (4, 0)]), Point(2, 3), Point(2, 0.25)
    assert _parts_within_margin(line, near, 0.5) is True
    assert _parts_within_margin(line, far, 0.5) is False
    assert _parts_within_margin(near, far, 3.0) is True


def test_batches_reach_a_hit_in_the_last_one(monkeypatch):
    """The scan is by batches of parts and must not stop early on a miss."""
    monkeypatch.setattr(s7, "_WITHIN_INDEXED_BATCH", 4)
    a = unary_union([LineString([(i * 3.0, 0), (i * 3.0 + 1, 0)]) for i in range(30)])
    b = unary_union([LineString([(i * 3.0, 9), (i * 3.0 + 1, 9)]) for i in range(40)]
                    + [Point(88.0, 0.3)])
    assert a.distance(b) <= 0.5
    assert _parts_within_margin(a, b, 0.5) is True
    assert _parts_within_margin(a, b, 0.2) is False


def test_within_margin_routes_by_size(monkeypatch):
    """Small pairs keep the plain `distance` call untouched; a pair past the
    threshold goes to the index. Boxes further apart than the margin never
    reach either."""
    calls = []
    real = s7._parts_within_margin
    monkeypatch.setattr(s7, "_parts_within_margin",
                        lambda a, b, m: calls.append(1) or real(a, b, m))
    rng = np.random.default_rng(5)
    a, b = _thread(rng, 40, 0, 0, 10), _thread(rng, 40, 3, 3, 10)
    want = a.distance(b) <= 0.5
    assert _within_margin(a, b, 0.5) is want and calls == []
    monkeypatch.setattr(s7, "_WITHIN_INDEXED_MIN_COORD_PAIRS", 1)
    assert _within_margin(a, b, 0.5) is want and calls == [1]
    far = _thread(rng, 40, 500, 500, 10)
    assert _within_margin(a, far, 0.5) is False and calls == [1]


def test_size_test_does_not_overflow(monkeypatch):
    """The coordinate counts are numpy int32; 50,000 x 50,000 is past its
    range, and a wrapped product would send the biggest pairs (the ones this
    exists for) back to the slow call. Met on the dolphin's own blocks."""
    import warnings

    calls = []
    real = s7._parts_within_margin
    monkeypatch.setattr(s7, "_parts_within_margin",
                        lambda a, b, m: calls.append(1) or real(a, b, m))
    xs = np.linspace(0.0, 100.0, 50_000)
    a = LineString(np.column_stack([xs, np.zeros_like(xs)]))
    b = LineString(np.column_stack([xs, np.full_like(xs, 0.3)]))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert _within_margin(a, b, 0.5) is True
    assert calls == [1]


def test_hoist_decides_the_same_through_the_index(monkeypatch):
    """`_hoist_same_thread` over blocks that do and do not clear the margin
    returns one order whichever way `_within_margin` answers."""
    from digitizer_core.stitches import StitchBlock, StitchRun

    def block(thread, x0, y0, n, seed):
        r = np.random.default_rng(seed)
        runs = []
        for _ in range(n):
            x, y = x0 + r.uniform(0, 8), y0 + r.uniform(0, 8)
            runs.append(StitchRun(points=[(x, y), (x + r.uniform(-1, 1), y + r.uniform(-1, 1))],
                                  shape_id="s"))
        return StitchBlock(thread_index=thread, thread_number=str(thread),
                           rgb=(1, 2, 3), runs=runs)

    def build():
        return [block(7, 0, 0, 30, 1), block(9, 40, 40, 30, 2), block(7, 2, 2, 30, 3),
                block(4, 1, 1, 30, 4), block(9, 60, 0, 30, 5), block(7, 80, 80, 30, 6)]

    plain = [(b.thread_index, len(b.runs), b.runs[0].points[0])
             for b in s7._hoist_same_thread(build(), trim_at=3.0, margin_mm=0.5)]
    monkeypatch.setattr(s7, "_WITHIN_INDEXED_MIN_COORD_PAIRS", 1)
    indexed = [(b.thread_index, len(b.runs), b.runs[0].points[0])
               for b in s7._hoist_same_thread(build(), trim_at=3.0, margin_mm=0.5)]
    assert indexed == plain
    assert [t for t, _, _ in plain] != [7, 9, 7, 4, 9, 7]      # something did move
