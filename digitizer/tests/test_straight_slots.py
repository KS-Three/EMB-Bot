"""`cfg.extra["satin_straight_slots"]` (built OFF 2026-11-17).

NOAA's wordmark at 90 mm: the O's counter is a 2.4 x 5.9 mm rounded slot of
the ground's thread. The skeleton satin tier's rails wrap each round end, so
its crosses fanned to 45 deg at both ends. ON, a short straight slot sews as
one column with level crosses by the Column lane's emitter.
`stage6_satin.is_straight_slot` is the test.
"""
import math

from shapely.geometry import Point, Polygon, box

from digitizer_core.columns import lettering_columns_shape
from digitizer_core.stage6_satin import is_straight_slot

CEILING = 5.0


def _rounded_slot(w=2.4, h=5.9, r=0.5):
    """An upright bar with rounded corners, like the counter of a squared O."""
    return box(0, 0, w, h).buffer(-r).buffer(r)


def test_the_noaa_counter_is_a_slot():
    assert is_straight_slot(_rounded_slot(), CEILING)


def test_a_stadium_is_a_slot():
    stadium = Point(0, 0).buffer(1.2).union(Point(0, 3.5).buffer(1.2)).convex_hull
    assert is_straight_slot(stadium, CEILING)


def test_a_square_dot_is_not_a_slot():
    """Elongation under 1.5: `small_solid_satin`'s shape (the A counters, 2.3 mm square)."""
    assert not is_straight_slot(box(0, 0, 2.3, 2.3), CEILING)


def test_a_long_bar_is_not_a_slot():
    """Past elongation 4 the ends are under a quarter of the column."""
    assert not is_straight_slot(box(0, 0, 1.2, 12.0), CEILING)


def test_a_slot_wider_than_the_satin_ceiling_is_not_a_slot():
    assert not is_straight_slot(box(0, 0, 6.0, 14.0), CEILING)


def test_a_ring_is_not_a_slot():
    ring = Polygon(box(0, 0, 2.4, 5.9).exterior.coords, [box(0.8, 1.0, 1.6, 4.9).exterior.coords])
    assert not is_straight_slot(ring, CEILING)


def test_a_bent_bar_is_not_a_slot():
    ell = box(0, 0, 1.2, 5.0).union(box(0, 0, 3.0, 1.2))
    assert not is_straight_slot(ell, CEILING)


def test_a_wedge_is_not_a_slot():
    assert not is_straight_slot(Polygon([(0, 0), (2.4, 0), (1.2, 5.9)]), CEILING)


def test_the_lanes_column_on_a_slot_is_level_from_end_to_end():
    """What the rung sews: one column, no cut, every cross within a few
    degrees of square to the slot's long axis."""
    slot = _rounded_slot()
    runs, report = lettering_columns_shape(slot, "slot", trim_at_mm=3.0, spacing_mm=0.4,
                                           pull_mm=0.3, pull_floor_mm=1.5,
                                           underlay_style="center_run", rail_axis=True)
    assert not report["empty"] and report["columns"] == 1 and not report.get("cuts")
    satin = [r for r in runs if r.kind == "satin"]
    assert len(satin) == 1
    pts = satin[0].points
    # every second stitch is a cross laid square to the (vertical) axis
    worst = max(abs(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])))
                for a, b in zip(pts[0::2], pts[1::2]))
    worst = min(worst, 180.0 - worst)
    assert worst < 6.0, worst
    ys = [p[1] for p in pts]
    assert min(ys) < 0.6 and max(ys) > 5.3          # the column reaches both ends


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("satin_straight_slots")
