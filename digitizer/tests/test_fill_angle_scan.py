"""`stage6_fill._scan_rows` counts a fill's columns from edge crossings in
numpy instead of one GEOS overlay per scanline (2026-11-11, speed only).

It feeds `_cols_at_angle` alone, so what must hold is the COUNT: wherever it
answers, `_columns` cuts its rows into as many columns as it cuts
`_row_spans`' -- and wherever a decision sits near a tie, it answers None
and GEOS decides, as before.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import stage6_fill as s6
from digitizer_core.stage6_fill import _columns, _row_spans, _scan_rows

ROW = 0.4


def _blob(rng, n_verts: int, radius: float, holes: int) -> Polygon:
    """A star-shaped ring with noisy radius, minus a few discs and slots."""
    ang = np.sort(rng.uniform(0, 2 * math.pi, n_verts))
    rad = radius * rng.uniform(0.35, 1.0, n_verts)
    poly = Polygon(np.column_stack([rad * np.cos(ang), rad * np.sin(ang)])).buffer(0)
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    for _ in range(holes):
        x, y = rng.uniform(-radius / 2, radius / 2, 2)
        cut = (Point(x, y).buffer(rng.uniform(0.3, radius / 5), 6) if rng.random() < 0.6
               else affinity.rotate(box(x, y, x + rng.uniform(1, radius / 2), y + rng.uniform(0.2, 1.0)),
                                    rng.uniform(0, 180), origin=(x, y)))
        out = poly.difference(cut)
        if out.geom_type == "Polygon" and not out.is_empty:
            poly = out
    return poly


def _shapes():
    rng = np.random.default_rng(1111)
    out = []
    for i in range(70):
        out.append(_blob(rng, int(rng.integers(5, 60)), float(rng.uniform(2, 40)),
                         int(rng.integers(0, 6))))
    # buffer output: the dense arcs a real region's boundary is made of
    for i in range(20):
        out.append(_blob(rng, 12, 15.0, 2).buffer(rng.uniform(0.2, 1.5)))
    # a comb and a staircase: many spans per row, forks and merges
    out.append(unary_union([box(0, 0, 30, 3)] + [box(2 * i, 0, 2 * i + 1.1, 20) for i in range(15)]))
    out.append(unary_union([box(3 * i, 3 * i, 3 * i + 5, 3 * i + 5) for i in range(8)]))
    return [p for p in out if p.geom_type == "Polygon" and not p.is_empty]


SHAPES = _shapes()
ANGLES = [i * (180.0 / 16) for i in range(16)] + [7.3, 33.3, 101.9]


def test_the_count_is_the_geos_count():
    answered = declined = 0
    for n, poly in enumerate(SHAPES):
        for angle in ANGLES:
            rotated = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
            want = len(_columns(_row_spans(rotated, ROW)))
            rows = _scan_rows(rotated, ROW)
            if rows is None:
                declined += 1
                continue
            answered += 1
            assert len(_columns(rows)) == want, (n, angle)
    # it must answer nearly always, or it buys nothing
    assert answered > 20 * max(1, declined), (answered, declined)


def test_the_rows_are_the_geos_rows_to_far_inside_the_tolerance():
    """Same rows listed, same number of spans in each, every end within
    1e-9 mm: what the tie guards are sized against."""
    worst = 0.0
    for poly in SHAPES[::3]:
        for angle in (0.0, 33.75, 90.0, 123.75):
            rotated = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
            rows = _scan_rows(rotated, ROW)
            if rows is None:
                continue
            ref = _row_spans(rotated, ROW)
            assert [(ri, y, len(sp)) for ri, y, sp in rows] == [(ri, y, len(sp)) for ri, y, sp in ref]
            for (_, _, a), (_, _, b) in zip(rows, ref):
                worst = max(worst, max(abs(p - q) for sa, sb in zip(a, b) for p, q in zip(sa, sb)))
    assert worst < 1e-9, worst


@pytest.mark.parametrize("poly", [
    box(0, 0, 10, 0.0 + 0.0 + ROW * (25 + 0.5)),                # the last row IS the top edge
    box(0, 0, 10, 10).difference(box(2, 0.2, 4, 3)),            # a hole's edge on a row
    Polygon([(0, 0), (10, 0), (10, 10), (5, 0.6), (0, 10)]),    # a vertex on a row
    box(0, 0, 10, 0.9).union(                                   # a span a micron wide
        Polygon([(5, 0.9), (5.000001, 0.9), (5.0000005, 2.9)])),
], ids=["top-edge", "hole-edge", "vertex", "sliver-span"])
def test_a_tie_goes_back_to_geos(poly):
    assert poly.geom_type == "Polygon" and poly.is_valid
    assert _scan_rows(poly, ROW) is None
    assert s6._cols_at_angle(poly, 0.0, ROW) == len(_columns(_row_spans(poly, ROW)))


def test_an_end_at_the_overlap_threshold_goes_back_to_geos():
    """Two spans in neighbouring rows whose overlap is `_OVERLAP_EPS_MM`
    itself: `_columns` joins or splits them on the last bits."""
    eps = s6._OVERLAP_EPS_MM
    step = box(0, 0, 5, 0.4).union(box(5 - eps, 0.4, 10, 0.8))
    assert step.geom_type == "Polygon" and step.is_valid
    # rows at 0.2 and 0.6: one span each, overlapping by exactly eps
    assert _scan_rows(step, ROW) is None
    clear = box(0, 0, 5, 0.4).union(box(4, 0.4, 10, 0.8))
    assert len(_columns(_scan_rows(clear, ROW))) == len(_columns(_row_spans(clear, ROW))) == 1


def test_what_is_not_a_valid_polygon_goes_back_to_geos():
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    assert not bowtie.is_valid
    assert _scan_rows(bowtie, ROW) is None
    assert _scan_rows(MultiPolygon([box(0, 0, 5, 5), box(8, 0, 12, 5)]), ROW) is None
    assert _scan_rows(Polygon(), ROW) is None


def test_a_shape_under_one_row_lists_what_geos_lists():
    thin = box(0, 0, 10, 0.3)
    assert _scan_rows(thin, ROW) is not None
    assert len(_columns(_scan_rows(thin, ROW))) == len(_columns(_row_spans(thin, ROW)))


def test_the_angle_search_picks_the_same_angle(monkeypatch):
    """`best_fill_angle_deg` with the scan and with GEOS alone."""
    fast = [s6.best_fill_angle_deg(p, ROW) for p in SHAPES[::2]]
    monkeypatch.setattr(s6, "_scan_rows", lambda poly, row_mm: None)
    assert [s6.best_fill_angle_deg(p, ROW) for p in SHAPES[::2]] == fast
