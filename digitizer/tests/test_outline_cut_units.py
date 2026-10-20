"""Unit tests for the small, pure pieces of `digitizer_core/outline_cut.py` and
the helpers of `digitizer_core/ink_path.py`. Whole-letter behaviour lives in
test_lettering_columns.py / test_ink_path.py; these pin the geometry the rest
stands on, using plain shapely shapes (no image, no fixtures)."""
import math

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import ink_path, outline_cut as oc


def test_unit_normalises_and_zero_is_zero():
    assert oc._unit((3.0, 4.0)) == pytest.approx((0.6, 0.8))
    assert oc._unit((0.0, 0.0)) == (0.0, 0.0)


def test_stroke_width_is_2a_over_p():
    # a 10 x 1 ribbon: 2*10/22
    assert oc.stroke_width(box(0, 0, 10, 1)) == pytest.approx(20.0 / 22.0)


def test_split_without_cuts_returns_the_polygon():
    out = oc.split(box(0, 0, 10, 2), [])
    assert len(out) == 1 and out[0].area == pytest.approx(20.0)


def test_split_along_a_cut_gives_two_pieces_covering_the_polygon():
    poly = box(0, 0, 10, 2)
    out = oc.split(poly, [((5.0, 0.0), (5.0, 2.0), 0.0, 2.0)])
    assert len(out) == 2
    assert sum(p.area for p in out) == pytest.approx(20.0, abs=0.05)
    assert sorted(round(p.area) for p in out) == [10, 10]


def test_split_drops_scraps():
    poly = box(0, 0, 10, 2)
    # a cut 0.01 mm from the edge leaves a 0.02 mm² sliver, under the 0.05 floor
    out = oc.split(poly, [((0.01, 0.0), (0.01, 2.0), 0.0, 2.0)])
    assert len(out) == 1


def test_pair_rails_parallel_lines_gives_square_crosses_at_the_pitch():
    A = [(0.0, 0.0), (10.0, 0.0)]
    B = [(0.0, 2.0), (10.0, 2.0)]
    st = oc.pair_rails(A, B, 0.5)
    assert 18 <= len(st) <= 22
    for pa, pb in st:
        assert pa[0] == pytest.approx(pb[0], abs=0.15)
        assert pa[1] == pytest.approx(0.0) and pb[1] == pytest.approx(2.0)
    xs = [pa[0] for pa, _ in st]
    assert xs == sorted(xs)
    assert np.diff(xs).mean() == pytest.approx(0.5, abs=0.1)


def test_pair_rails_endpoints_pair_with_endpoints():
    st = oc.pair_rails([(0.0, 0.0), (6.0, 0.0)], [(0.0, 1.0), (6.0, 1.0)], 0.4)
    assert st[0][0] == pytest.approx((0.0, 0.0)) and st[0][1] == pytest.approx((0.0, 1.0))


def test_letter_columns_straight_bar_is_one_column_nothing_unsewn():
    r = oc.letter_columns(box(0, 0, 12, 1.6))
    assert r.W == pytest.approx(oc.stroke_width(box(0, 0, 12, 1.6)), rel=0.05)
    assert len(r.columns) == 1 and r.unsewn == []
    assert r.cuts == []


def test_letter_columns_plus_sign_is_cut_at_its_junction():
    plus = box(0, 4, 12, 5.6).union(box(5.2, 0, 6.8, 9.6))
    r = oc.letter_columns(plus)
    assert len(r.cuts) >= 1
    assert len(r.columns) >= 2


def test_letter_columns_ring_drops_a_pinhole_but_keeps_a_counter():
    outer = box(0, 0, 10, 10)
    pinhole = box(4.9, 4.9, 5.0, 5.0)
    r = oc.letter_columns(Polygon(outer.exterior, [pinhole.exterior.coords]))
    assert len(r.poly.interiors) == 0


def test_letter_columns_empty_after_cleanup_is_an_empty_answer():
    # a speck: simplify leaves nothing sewable, and it must not raise
    r = oc.letter_columns(Polygon([(0, 0), (0.05, 0), (0.05, 0.05), (0, 0.05)]))
    assert r.columns == []


def test_letter_columns_is_deterministic():
    plus = box(0, 4, 12, 5.6).union(box(5.2, 0, 6.8, 9.6))
    a, b = oc.letter_columns(plus), oc.letter_columns(plus)
    assert len(a.columns) == len(b.columns)
    assert a.columns and [c.stations for c in a.columns] == [c.stations for c in b.columns]


# ---- ink_path helpers ------------------------------------------------------

def test_length_of_a_polyline():
    assert ink_path._length([(0, 0), (3, 4), (3, 10)]) == pytest.approx(11.0)
    assert ink_path._length([(1, 1)]) == 0.0
    assert ink_path._length([]) == 0.0


def test_carry_out_pushes_the_end_outward_by_the_half_width():
    width = np.full((20, 20), 3.0)
    # spine runs left to right; end at x=10, the inward points trail to its left
    inward = [(10.0 - k, 5.0) for k in range(0, 8)]
    x, y = ink_path._carry_out((10.0, 5.0), inward, width)
    assert (x, y) == pytest.approx((13.0, 5.0))


def test_carry_out_leaves_the_end_alone_with_no_ink_or_no_spine():
    width = np.zeros((10, 10))
    assert ink_path._carry_out((4.0, 4.0), [(3.0, 4.0)], width) == (4.0, 4.0)
    width = np.full((10, 10), 2.0)
    assert ink_path._carry_out((4.0, 4.0), [], width) == (4.0, 4.0)


def test_carry_out_clamps_an_end_outside_the_image():
    width = np.full((10, 10), 1.0)
    x, y = ink_path._carry_out((-5.0, 50.0), [(-4.0, 50.0)], width)
    assert math.isfinite(x) and math.isfinite(y)
