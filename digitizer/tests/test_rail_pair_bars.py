"""`cfg.extra["lettering_columns_rail_pair_bars"]` (built OFF 2026-11-14): a
slab with two long parallel sides of its own is a straight bar.

Under `lettering_columns_apex_cut` and_pizza's two Z joints are one shape
turned 180 degrees, yet only the top-right one fanned (#1514): its top bar's
piece -- the one below, as the cut hands it over -- read neither a coherent
outline (0.46 against `straight_axis`' 0.55) nor a straight spine, so it sewed
as a curved column whose crosses swung round into the tip's cut, while the
bottom bar's spine scraped through and sewed straight.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon

from digitizer_core import outline_cut

W = 3.528
TOP_BAR = Polygon([(0.411, -4.247), (0.411, -0.457), (5.525, -0.411), (6.959, -1.091),
                   (5.463, -4.247), (0.411, -4.247)])
CUTS = [LineString(c) for c in ([(2.992, 2.53), (6.117, 8.721)], [(5.936, 4.84), (4.519, 5.555)],
                                [(8.434, 2.017), (5.463, -4.247)], [(5.525, -0.411), (6.959, -1.091)])]


def test_off_the_z_bar_is_not_straight():
    assert outline_cut.straight_axis(TOP_BAR, W, CUTS, rail_axis=True) is None


def test_on_the_z_bar_reads_its_rails():
    with outline_cut.rail_pair_bars_scope(True):
        assert outline_cut.straight_axis(TOP_BAR, W, CUTS, rail_axis=True) == (1.0, 0.0)


def test_scope_off_sets_nothing():
    with outline_cut.rail_pair_bars_scope(False):
        assert outline_cut.straight_axis(TOP_BAR, W, CUTS, rail_axis=True) is None
    assert outline_cut._RAIL_PAIR_BARS.get() is False


def test_a_bend_without_two_long_rails_stays_bent():
    # a half ring: bent OFF, and no two long sides of its own run parallel across it
    ts = [i * math.pi / 40 for i in range(41)]
    arc = Polygon([(5 * math.cos(t), 5 * math.sin(t)) for t in ts]
                  + [(2 * math.cos(t), 2 * math.sin(t)) for t in ts[::-1]])
    assert outline_cut.straight_axis(arc, 3.0, [], rail_axis=True) is None
    with outline_cut.rail_pair_bars_scope(True):
        assert outline_cut.straight_axis(arc, 3.0, [], rail_axis=True) is None
