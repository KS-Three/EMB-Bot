"""`cfg.extra["lettering_columns_stem_wedge_cap"]` (built OFF 2026-11-18).

Toat Machine's "h" (prime grader): the stem is one `curved` column whose cross
runs 2.3 mm up the stem, 3.2-3.4 mm for ten stations where the c's tail and
the arch's hairline join (the ink's own merge), then 2.3 again. The cap hands
that wedge to the meeting column, but only where a sibling's piece already
covers it.
"""
import math

from shapely.geometry import box

from digitizer_core import wedge_cap as W
from digitizer_core.columns import Column

PITCH = 0.4


def _stem(wedge_from=14, wedge_to=24, n=40, half=1.15, extra=0.9):
    """A vertical stem column (stations every 0.4 mm), its LEFT rail pushed out
    by `extra` mm for stations wedge_from..wedge_to."""
    st = []
    for i in range(n):
        y = i * PITCH
        ax = -half - (extra if wedge_from <= i <= wedge_to else 0.0)
        st.append(((ax, y), (half, y)))
    piece = box(-half - extra, 0, half, n * PITCH)
    return Column(stations=st, piece=piece, kind="curved", axis=None, width_mm=2 * half)


def _width(col, i):
    a, b = col.stations[i]
    return math.dist(a, b)


def test_scope_is_off_by_default():
    assert W.armed() is False
    with W.wedge_cap_scope(True):
        assert W.armed() is True
    assert W.armed() is False


def test_a_sibling_covered_wedge_is_capped_to_the_stem_width():
    stem = _stem()
    sibling = box(-3.0, 4.5, 0.0, 11.0)               # covers the wedge ground on the left
    new, n = W.cap_column(stem, sibling)
    assert n > 0
    for i in range(14, 25):
        assert _width(new, i) < _width(stem, i) - 0.5
        assert abs(_width(new, i) - 2.3) < 0.25       # back to the stem's own width
    assert _width(new, 5) == _width(stem, 5)          # outside the wedge: untouched
    assert _width(new, 35) == _width(stem, 35)


def test_a_wedge_no_sibling_covers_is_left_alone():
    """The cap never leaves ink bare: nothing covers it, nothing is cut."""
    stem = _stem()
    far = box(10.0, 0, 12.0, 3.0)
    new, n = W.cap_column(stem, far)
    assert n == 0 and new is stem
    assert W.cap_column(stem, None)[1] == 0


def test_a_long_swelling_is_not_a_wedge():
    """A swell longer than the window is the stroke's own belly."""
    stem = _stem(wedge_from=6, wedge_to=34)           # 29 stations, ~11.6 mm
    sibling = box(-3.0, 0, 0.0, 16.0)
    new, n = W.cap_column(stem, sibling)
    assert n == 0


def test_a_taper_is_untouched():
    st = []
    for i in range(40):
        w = 0.3 + 3.0 * min(i, 39 - i) / 19.0
        st.append(((-w / 2, i * PITCH), (w / 2, i * PITCH)))
    col = Column(stations=st, piece=box(-2, 0, 2, 16), kind="curved", axis=None, width_mm=3.0)
    new, n = W.cap_column(col, box(-5, -1, 5, 17))
    assert n == 0


def test_ends_of_a_column_are_never_capped():
    stem = _stem(wedge_from=0, wedge_to=8)
    new, n = W.cap_column(stem, box(-3, -1, 0, 5))
    assert n == 0


def test_only_curved_columns_and_the_same_list_when_nothing_changes():
    stem = _stem()
    straight = Column(stations=stem.stations, piece=stem.piece, kind="straight", axis=(0.0, 1.0), width_mm=2.3)
    cols = [straight, Column(stations=_stem(wedge_from=0, wedge_to=-1).stations,
                             piece=box(-9, 0, -8, 1), kind="curved", axis=None, width_mm=2.3)]
    assert W.cap_columns(cols) is cols
    assert W.cap_columns([stem]) == [stem]


def test_cap_columns_caps_the_stem_beside_a_covering_sibling():
    stem = _stem()
    tail = Column(stations=[((-1.6, 4.6 + 0.4 * i), (-0.2, 4.6 + 0.4 * i)) for i in range(15)],
                  piece=box(-3.0, 4.5, 0.0, 10.7), kind="curved", axis=None, width_mm=1.4)
    out = W.cap_columns([stem, tail])
    assert out[1] is tail
    assert _width(out[0], 19) < _width(stem, 19) - 0.5


def test_a_thicker_sibling_never_takes_the_wedge_and_the_hairline_is_not_capped():
    """The hairline that crosses the stem keeps the ground it crosses; only the
    thicker column gives a wedge up, and only to a thinner one."""
    stem = _stem()
    tail = Column(stations=[((-1.6, 4.6 + 0.4 * i), (-0.2, 4.6 + 0.4 * i)) for i in range(15)],
                  piece=box(-3.0, 4.5, 0.0, 10.7), kind="curved", axis=None, width_mm=1.4)
    out = W.cap_columns([tail, stem])               # the order the lane happens to hand them in
    assert out[0] is tail
    assert _width(out[1], 19) < _width(stem, 19) - 0.5
    fat = Column(stations=[((-3.0, 4.6 + 0.4 * i), (-0.2, 4.6 + 0.4 * i)) for i in range(15)],
                 piece=box(-3.0, 4.5, 0.0, 10.7), kind="curved", axis=None, width_mm=2.8)
    assert W.cap_columns([stem, fat])[0] is stem     # a thicker sibling covers nothing of the stem's
