"""`cfg.satin_hairline_tier` -- the stroke-level hairline tier (defect 24).

The 2026-09-03 mechanism (`_hairline_stretches`, `tests/test_small_lettering.py`)
splits a stroke PER STATION: a stretch of crosses under `SATIN_MIN_CROSS_MM`
sews as a bean, a short dip is hopped. A column whose crosses STRADDLE the
floor -- 0.5-0.6 mm -- therefore sews a satin with a cross missing here and
there, never a bean. The tier reads the stroke whole: median cross under
`_HAIRLINE_COLUMN_MM` (1.2 x the floor, the hairline line
`_split_sharp_corners` already draws), the whole stroke is one bean.

Built OFF; off is byte-identical. Fixture: a 10 mm column whose width wobbles
+-0.06 mm round a nominal width -- the straddle, in miniature.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core import stage6_satin as s6
from digitizer_core.stage6_satin import satin_shape


def _wobble(w0: float, amp: float = 0.12, length: float = 10.0, n: int = 200,
            period: float = 2.5) -> Polygon:
    ys = [length * i / n for i in range(n + 1)]
    hw = [(w0 + amp * math.sin(2 * math.pi * y / period)) / 2 for y in ys]
    return Polygon([(-h, y) for h, y in zip(hw, ys)]
                   + [(h, y) for h, y in reversed(list(zip(hw, ys)))])


def _sew(poly: Polygon, tier: bool):
    return satin_shape(poly, "I", underlay_style="none", trim_at_mm=3.0,
                       hairline_tier=tier)


def _sig(runs):
    return [(r.kind, [tuple(p) for p in r.points]) for r in runs]


def test_the_flag_is_off_by_default():
    assert PipelineConfig().satin_hairline_tier is False


def test_the_line_is_the_existing_hairline_expression():
    """No new floor (gate 1): the tier's width line is the join rule's."""
    assert s6._HAIRLINE_COLUMN_MM == 1.2 * machine.SATIN_MIN_CROSS_MM


def test_a_straddling_column_is_a_stuttering_satin_off_and_one_bean_on():
    poly = _wobble(0.55)
    off, _ = _sew(poly, False)
    on, report = _sew(poly, True)
    assert [r.kind for r in off] == [stitches.SATIN]
    # off: crosses dropped under the floor and hopped -- fewer crosses than
    # the same column sews at 1.5 mm
    wide, _ = _sew(_wobble(1.5), False)
    assert len(off[0].points) < 0.7 * len(wide[0].points)
    assert [r.kind for r in on] == [stitches.RUN]
    assert not report["empty"]
    pts = on[0].points
    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(steps) < 1.5 * machine.BEAN_STITCH_MM
    # three laps of the spine, ending at the far end
    assert len(pts) >= 2 * machine.BEAN_PASSES


def test_a_column_over_the_line_is_untouched_by_the_tier():
    for w0 in (0.7, 0.8, 1.5):
        poly = _wobble(w0)
        assert _sig(_sew(poly, True)[0]) == _sig(_sew(poly, False)[0]), w0


def test_a_plain_bar_is_byte_identical_on():
    poly = box(0.0, 0.0, 12.0, 2.0)
    assert _sig(_sew(poly, True)[0]) == _sig(_sew(poly, False)[0])


def test_a_stub_too_short_for_a_bean_keeps_today_s_split():
    """Under two bean stitches of spine the tier would drop crosses that
    sew; it declines and the per-station split stands."""
    poly = _wobble(0.55, length=1.2, n=40, period=0.6)
    assert _sig(_sew(poly, True)[0]) == _sig(_sew(poly, False)[0])


def test_the_tier_helper_reads_the_median_not_the_minimum():
    spine = [(0.0, float(y)) for y in range(10)]
    rails = lambda w: ([(-w / 2, y) for _, y in spine], [(w / 2, y) for _, y in spine])
    # one thin cross in a 0.8 mm column: not a hairline column
    a, b = rails(0.8)
    a[3], b[3] = (-0.2, 3.0), (0.2, 3.0)
    crosses = list(zip(a, b))
    assert s6._hairline_tier_stretch(crosses, spine, a, b, None, 0.0) is None
    a, b = rails(0.55)
    crosses = list(zip(a, b))
    assert s6._hairline_tier_stretch(crosses, spine, a, b, None, 0.0) == (0, 9)
