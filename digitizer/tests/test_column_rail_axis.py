"""`cfg.lettering_columns_rail_axis` (2026-10-20): a short italic bar's
straight axis is its RAILS' direction, not its spine's chord.

Proseal's wordmark at the pro's 85.9 mm hat width (bold italic sans, 9.3 mm
caps, ~2.2 mm strokes): the E's middle arm is a 4.5 x 2.2 mm parallelogram
whose ends lean with the italic. Its own outline is not coherent enough for
`outline_cut.straight_axis`'s doubled-angle mean (0.44 of the 0.55 bar: the
slanted end and the two slot-back stubs outweigh it), so the axis fell back
to the medial spine's end-to-end chord -- and the spine of a sheared
parallelogram runs corner to acute corner, 12.4 deg off its rails. The arm's
crosses sewed at 77.6 deg while the top and bottom arms sewed at 90.0: an
angle change inside one letter, the "patchwork" Kent sees. The synthetic
bars below reproduce it with no artwork: every 3.5-4.5 mm bar leaning 8-20
deg reads 10-22 deg off.

ON, a straight piece that took the chord fallback (and passed its
straightness gate, unchanged) takes the direction of its two longest own
sides instead, when those are parallel (the 7 deg the upright snap already
uses) and on opposite sides of the stroke (half a stroke width apart), and
the chord is more than those 7 deg off them.
"""
import math

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import outline_cut as oc


def para(L, H, lean_deg):
    s = H * math.tan(math.radians(lean_deg))
    return Polygon([(s, 0), (L + s, 0), (L, H), (0, H)])


def deg(u):
    a = math.degrees(math.atan2(u[1], u[0])) % 180.0
    return min(a, 180.0 - a)


@pytest.mark.parametrize("L", [3.5, 4.5])
@pytest.mark.parametrize("lean", [8, 12, 15, 20])
def test_off_a_short_italic_bar_tilts_off_its_rails(L, lean):
    # the defect, pinned: the spine chord leans the bar's axis
    p = para(L, 2.2, lean)
    u = oc.straight_axis(p, oc.stroke_width(p))
    assert u is not None and deg(u) > 8.0


@pytest.mark.parametrize("L", [3.5, 4.5, 6.0, 8.0])
@pytest.mark.parametrize("lean", [8, 12, 15, 20])
def test_on_a_short_italic_bar_runs_along_its_rails(L, lean):
    p = para(L, 2.2, lean)
    u = oc.straight_axis(p, oc.stroke_width(p), rail_axis=True)
    assert u is not None and deg(u) < 0.5


def test_on_a_bar_whose_outline_is_coherent_is_untouched():
    # the rail rule is read only where the chord fallback was
    p = para(8.0, 2.2, 12)
    W = oc.stroke_width(p)
    assert oc.straight_axis(p, W, rail_axis=True) == oc.straight_axis(p, W)


def test_on_an_l_still_is_not_straight():
    # the chord's straightness gate still decides whether a piece bends
    L = Polygon([(0, 0), (2, 0), (2, 6), (6, 6), (6, 8), (0, 8)])
    W = oc.stroke_width(L)
    assert oc.straight_axis(L, W) is None
    assert oc.straight_axis(L, W, rail_axis=True) is None


def test_on_the_italic_arm_sews_square_to_its_rails():
    # whole-letter path: letter_columns hands the rule to every build_column
    p = para(4.5, 2.2, 12)
    off = oc.letter_columns(p, rail_axis=False)
    on = oc.letter_columns(p, rail_axis=True)
    assert len(off.columns) == len(on.columns) == 1

    def mid_lean(col):
        st = col.stations[len(col.stations) // 2]
        a = math.degrees(math.atan2(st[1][1] - st[0][1], st[1][0] - st[0][0])) % 180.0
        return abs(a - 90.0)
    assert mid_lean(off.columns[0]) > 8.0
    assert mid_lean(on.columns[0]) < 0.5


def test_flag_default_preflip_and_flagcost():
    from .conftest import PRE_FLIP
    from tools.pro_parity import flagcost as fc
    assert PipelineConfig().lettering_columns_rail_axis is True
    assert PRE_FLIP["lettering_columns_rail_axis"] is False
    assert fc.FLAGS["lettering_columns_rail_axis"] is False


def test_stage7_hands_the_flag_to_the_lane(monkeypatch):
    # the flag reaches `letter_columns`, and OFF the call is today's
    from digitizer_core import columns as C
    seen = []
    real = oc.letter_columns

    def spy(poly, **kw):
        seen.append(kw.get("rail_axis", False))
        return real(poly, **kw)
    monkeypatch.setattr(oc, "letter_columns", spy)
    p = para(4.5, 2.2, 12)
    kw = dict(trim_at_mm=3.0, spacing_mm=0.4)
    C.lettering_columns_shape(p, "S", **kw)
    C.lettering_columns_shape(p, "S", rail_axis=True, **kw)
    assert seen == [False, True]
