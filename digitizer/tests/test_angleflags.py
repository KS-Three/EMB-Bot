"""`tools/pro_parity/angleflags.py` — do the edge flags turn the fill rows?

The finding rests on two small pieces of logic, and either one being wrong
would move the headline number silently: treating row directions as axial
(90 and -90 are the same rows, so they are NOT a turn), and pairing shapes
across arms without double-claiming one.
"""
from __future__ import annotations

from shapely.geometry import Polygon

from tools.pro_parity import angleflags as af


def _rec(shape_id, cx, cy, area, angle=0.0):
    return {"shape_id": shape_id, "cx": cx, "cy": cy, "area": area, "angle": angle}


def test_row_directions_are_axial():
    """The biggest reported turn is 90 -> -2.82. If 0 and 180 were treated as
    different, every near-horizontal fill would read as a half-turn."""
    assert af.angular_dist(0.0, 180.0) == 0.0
    assert af.angular_dist(90.0, -90.0) == 0.0
    assert abs(af.angular_dist(90.0, -2.82) - 87.18) < 1e-9
    assert abs(af.angular_dist(170.0, 10.0) - 20.0) < 1e-9


def test_match_prefers_the_id_then_falls_back_to_a_close_centroid():
    ship = [_rec("S1", 0.0, 0.0, 100.0), _rec("S2", 50.0, 0.0, 40.0)]
    other = [_rec("S1", 0.2, 0.0, 101.0),
             _rec("Sren", 50.4, 0.3, 42.0)]       # renamed by the flags
    pairs = af.match(ship, other)
    assert pairs[0][1]["shape_id"] == "S1"
    assert pairs[1][1]["shape_id"] == "Sren"


def test_match_refuses_a_far_or_differently_sized_shape_rather_than_guess():
    """An unmatched shape is reported and not counted as turned, which keeps
    the turned count a floor. A loose match would inflate it instead."""
    ship = [_rec("S1", 0.0, 0.0, 100.0), _rec("S2", 10.0, 0.0, 100.0)]
    other = [_rec("Sx", 2.0, 0.0, 100.0),          # 2 mm away
             _rec("Sy", 10.1, 0.0, 150.0)]         # 50% larger
    assert [o for _s, o in af.match(ship, other)] == [None, None]


def test_match_never_claims_one_shape_twice():
    ship = [_rec("S1", 0.0, 0.0, 100.0), _rec("S1", 0.1, 0.0, 100.0)]
    other = [_rec("S1", 0.0, 0.0, 100.0)]
    got = [o for _s, o in af.match(ship, other)]
    assert got.count(None) == 1 and sum(o is not None for o in got) == 1


def test_column_margin_is_zero_for_a_square_and_positive_for_a_long_bar():
    """A square cuts into one column at 0 and at 90 degrees — a tie. A long
    thin bar rowed across its length needs many columns, so its best angle
    wins by a margin."""
    square = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    notched = Polygon([(0, 0), (40, 0), (40, 4), (22, 4), (22, 2), (18, 2),
                       (18, 4), (0, 4)])
    assert af.column_margin(square, 0.4) == 0
    assert af.column_margin(notched, 0.4) >= 1
