"""`cfg.satin_tip_floor_cross` (built OFF 2026-11-18): a satin column whose
spine stops short of a thin art tip is carried on to the tip at the floor
cross (`machine.SATIN_MIN_CROSS_MM`, unchanged: ROADMAP gate 1). Off is
byte-identical. Fixture: a 20 mm bar 3 mm wide ending in a long thin wedge,
the Gaulke roof wing in miniature."""
from __future__ import annotations

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig
from digitizer_core.stage6_satin import satin_shape


def _wedge_bar() -> Polygon:
    # a bent wedge: the skeleton's spine stops about 0.7 mm short of the point
    return Polygon([(0, 0), (10, -1.2), (20, -3), (20, 0.2), (10, 1.2)])


def _sew(poly, flag):
    return satin_shape(poly, "W", underlay_style="none", trim_at_mm=3.0, tip_floor_cross=flag)[0]


def _sig(runs):
    return [(r.kind, [tuple(p) for p in r.points]) for r in runs]


def _min_x(runs):
    return min(p[0] for r in runs for p in r.points)


def test_the_flag_is_off_by_default():
    assert PipelineConfig().satin_tip_floor_cross is False


def test_off_is_byte_identical():
    poly = _wedge_bar()
    assert _sig(_sew(poly, False)) == _sig(satin_shape(poly, "W", underlay_style="none", trim_at_mm=3.0)[0])


def test_on_carries_a_pointed_end_to_the_tip_without_leaving_the_art():
    poly = _wedge_bar()
    off, on = _sew(poly, False), _sew(poly, True)
    assert _min_x(off) > 0.5 and _min_x(on) < 0.05, (_min_x(on), _min_x(off))
    # nothing sewn outside the art (+ the floor's own half cross at the tip)
    for r in on:
        for p in r.points:
            assert poly.buffer(0.35).covers(Point(p)), p


def test_a_flat_end_is_untouched():
    flat = Polygon([(0, -1.5), (20, -1.5), (20, 1.5), (0, 1.5)])
    assert _sig(_sew(flat, True)) == _sig(_sew(flat, False))
