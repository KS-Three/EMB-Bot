"""No size ring on a shape with a sharp convex corner (`cfg.border_by_size_smooth_only`, built OFF 2026-11-17).

The size ring (`border_by_size`) is built on the shape with its corners
relaxed inward by 2.1 mm, so on a sharp-cornered shape it redraws the outline
(a flat 10 mm square sews as a cushion; area loss 0.062 is under
`border_by_size_corner_loss`'s 0.083). ON, a shape whose exterior outline has a
convex corner of interior angle <= 110 degrees with a straight run of one
ring width each side is no ring's and sews as a plain fill. Off, byte-identical.

Synthetic shapes only: the logos are not in the repo.
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import Point, Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import (BORDER_GROUP_KEY, _border_by_size_width, _sharp_corners,
                                            sequence, tag_border_by_size_groups)

ON = dict(border_by_size_smooth_only=True)
OFF = dict(border_by_size_smooth_only=False)


def _region(poly, sid="Sbig", **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="4101",
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _plan(poly, **cfg_kw):
    reg = _region(poly)
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _kinds(runs):
    return [r.kind for r in runs]


def _md5(runs):
    h = hashlib.md5()
    for r in runs:
        h.update(r.kind.encode())
        for x, y in r.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _rounded(w, h, r=2.1):
    return box(0, 0, w, h).buffer(-r).buffer(r, 32)


def _star(points=5, outer=10.0, inner=4.0):
    pts = []
    for i in range(points * 2):
        rad = outer if i % 2 == 0 else inner
        a = math.pi / 2 + i * math.pi / points
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    return Polygon(pts)


def _crescent():
    return Point(0, 0).buffer(12.0, 64).difference(Point(4.0, 0).buffer(10.5, 64))


# ------------------------------------------------------------- the detector
def test_a_square_has_four_corners():
    assert _sharp_corners(box(0, 0, 10, 10)) == 4


def test_a_triangle_has_three():
    assert _sharp_corners(Polygon([(0, 0), (12, 0), (6, 10.4)])) == 3


def test_a_circle_has_none():
    assert _sharp_corners(Point(0, 0).buffer(6.0, 64)) == 0


def test_a_rounded_rectangle_at_the_ring_radius_has_none():
    assert _sharp_corners(_rounded(14, 10)) == 0


def test_a_parallelogram_has_only_the_acute_pair():
    # 60 and 120 degrees: the 120 degree pair is over the 110 degree limit
    assert _sharp_corners(Polygon([(0, 0), (12, 0), (18, 10.39), (6, 10.39)])) == 2


def test_a_five_point_star_has_five():
    assert _sharp_corners(_star()) == 5


def test_a_crescent_has_its_two_tips():
    assert _sharp_corners(_crescent()) == 2


def test_a_corner_with_a_short_leg_is_no_corner():
    # a 1 mm notch step: both sides of the corner are shorter than the ring width
    stepped = Polygon([(0, 0), (10, 0), (10, 10), (1, 10), (1, 9), (0, 9)])
    assert _sharp_corners(stepped) == 3          # the 1 mm step's two corners do not count


def test_a_raster_rounded_corner_counts_once():
    r03 = box(0, 0, 10, 10).buffer(-0.3).buffer(0.3, 4)       # 0.3 mm tips, as a trace leaves them
    assert _sharp_corners(r03) == 4


def test_holes_are_ignored():
    holed = box(0, 0, 20, 20).difference(box(5, 5, 12, 12))
    assert _sharp_corners(holed) == 4            # the hole's four convex-to-the-hole corners are not counted
    ring = Point(0, 0).buffer(10, 64).difference(box(-3, -3, 3, 3))
    assert _sharp_corners(ring) == 0


def test_a_multipolygon_sums_its_parts():
    two = box(0, 0, 8, 8).union(box(20, 0, 28, 8))
    assert _sharp_corners(two) == 8


# ------------------------------------------------------------- the rule
def test_flag_default_is_off():
    assert PipelineConfig().border_by_size_smooth_only is False


def test_the_pin_file_carries_it_false():
    from .conftest import ENGINE_2026_10_27
    assert ENGINE_2026_10_27["border_by_size_smooth_only"] is False


def test_on_a_10mm_sharp_square_is_a_plain_fill():
    # loss 0.062 is under the corner-loss rule's 0.083, so only this rule refuses it
    assert stitches.BORDER in _kinds(_plan(box(0, 0, 10, 10), **OFF))
    kinds = _kinds(_plan(box(0, 0, 10, 10), **ON))
    assert stitches.FILL in kinds and stitches.BORDER not in kinds


def test_on_a_12mm_disc_keeps_its_ring_byte_identical():
    disc = Point(0, 0).buffer(6.0, 64)
    off, on = _plan(disc, **OFF), _plan(disc, **ON)
    assert stitches.BORDER in _kinds(on)
    assert _md5(off) == _md5(on)


def test_on_a_rounded_square_keeps_its_ring_byte_identical():
    sq = _rounded(12, 12)
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER in _kinds(on)
    assert _md5(off) == _md5(on)


def test_off_is_the_default_byte_for_byte():
    sq = box(0, 0, 10, 10)
    assert _md5(_plan(sq)) == _md5(_plan(sq, **OFF))
    assert stitches.BORDER in _kinds(_plan(sq))


def test_the_prediction_and_the_emitter_agree_both_ways():
    sq = box(0, 0, 10, 10)
    for flags, ringed in ((OFF, True), (ON, False)):
        cfg = PipelineConfig(underlay=False, **flags)
        assert (_border_by_size_width(_region(sq), cfg) is not None) is ringed
        assert (stitches.BORDER in _kinds(_plan(sq, **flags))) is ringed


def test_the_rule_wins_over_a_group_stamp():
    sq = _region(box(0, 0, 10, 10))
    sq.meta[BORDER_GROUP_KEY] = True
    assert _border_by_size_width(sq, PipelineConfig(**ON)) is None
    assert _border_by_size_width(sq, PipelineConfig(**OFF)) is not None


def test_the_group_stamp_does_not_re_ring_a_refused_shape():
    # three like bars (one line) plus a sharp square among them: tagging reads
    # the bars alone and never stamps the square
    bars = [_region(box(x, 0, x + 6.3, 20), sid=f"B{i}") for i, x in enumerate((20, 30, 40))]
    sq = _region(box(0, 5, 10, 15), sid="Sq")
    on = PipelineConfig(**ON)
    tag_border_by_size_groups(bars + [sq], on)
    with_sq = [b.meta.get(BORDER_GROUP_KEY) for b in bars]
    assert BORDER_GROUP_KEY not in sq.meta
    tag_border_by_size_groups(bars, on)
    assert with_sq == [b.meta.get(BORDER_GROUP_KEY) for b in bars]
    assert _border_by_size_width(sq, on) is None


def test_a_shape_under_the_floor_is_untouched():
    sq = box(0, 0, 5.0, 5.0)
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER not in _kinds(off)
    assert _md5(off) == _md5(on)


def test_the_constants_are_geometry():
    assert machine.BORDER_SMOOTH_SIMPLIFY_MM == 0.15
    assert machine.BORDER_SMOOTH_SHARP_MAX_DEG == 110.0


def test_a_stair_stepped_wedge_keeps_all_its_corners():
    # a 15 x 4 mm right triangle as a raster trace leaves it: every edge a 0.1 mm staircase
    cols = [box(i * 0.1, 0.0, (i + 1) * 0.1, math.floor(i * 0.1 * 4 / 15 / 0.1) * 0.1) for i in range(150)]
    from shapely.ops import unary_union
    wedge = unary_union([c for c in cols if c.area > 0] + [box(14.9, 0, 15.0, 4.0)])
    assert wedge.geom_type == "Polygon"
    assert _sharp_corners(wedge) == 3
