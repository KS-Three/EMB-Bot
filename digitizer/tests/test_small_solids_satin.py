"""Small SOLID shapes sew as one satin dot, not as a hollow ring
(`cfg.small_solids_satin`, 2026-10-20).

The defect (Proseal at the pro's 85.9 mm, Hat): the "+" between FOAM and
COATINGS (1.52 x 1.52 mm, 1.11 mm^2) and the six teal spray hexagons
(1.1-1.3 mm across, 1.11-1.61 mm^2) are under the sewable-detail area floor
(`min_detail_mm` ** 2 = 2.25 mm^2), so stage 7 routes them to the run tier,
which sews a bean circuit on the OUTLINE. The run tier's own docstring says
why that is right for a stroke ("the two sides of a stroke sit closer
together than the thread is wide, so the traced outline reads as a solid
monoline glyph"), and that premise is false for a solid: inset by half the
laid width, the hexagon still has 0.4-0.6 mm^2 of bare inside, so it sews as
a ring with nothing in it. The pro sews each as one satin blob.

ON, a rescued non-lettering shape with no hole whose inside the ring would
leave bare -- `poly.buffer(-laid / 2)` at or over `machine.RUN_MIN_AREA_MM2`,
the thread's own one-penetration area -- sews as ONE satin column along its
long axis, each cross the shape's own width (`stage6_satin.small_solid_satin`,
the junction cover's `_principal_spine` + `satin_stroke`). No new constant.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence


def _hexagon(across: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    r = across / 2.0
    return Polygon([(cx + r * math.cos(math.radians(60 * k)),
                     cy + r * math.sin(math.radians(60 * k))) for k in range(6)])


def _plan(poly: Polygon, **cfg_kw):
    reg = Region(shape_id="Sdot", polygon=poly, thread_index=0,
                 thread_number="4101", area_mm2=poly.area, source="test",
                 meta={"layer": 0, "rescued_small_shape": True})
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, warnings = sequence(planned, fabric_for_garment("hat_front"),
                                PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs if r.shape_id == "Sdot"], warnings


def test_flag_default_is_off():
    assert PipelineConfig().small_solids_satin is False


def test_off_a_small_hexagon_sews_its_outline_ring():
    """The defect as it ships: a 1.3 mm hexagon is a bean ring."""
    runs, _w = _plan(_hexagon(1.3))
    assert runs and {r.kind for r in runs} == {"run"}


def test_on_a_small_hexagon_sews_one_satin_that_covers_its_middle():
    hexa = _hexagon(1.3)
    runs, _w = _plan(hexa, small_solids_satin=True)
    assert [r.kind for r in runs] == ["satin"], [r.kind for r in runs]
    pts = runs[0].points
    assert len(pts) >= 6
    # every needle point on (or a hair off) the drawn shape: the dot's width
    # is the shape's own, nothing grown
    for x, y in pts:
        assert hexa.buffer(0.05).covers(Point(x, y)), (x, y)
    # the middle is under thread: some cross passes within a thread width of
    # the centre, which the ring never does (its nearest pass is ~0.56 mm off)
    segs = [LineString([a, b]) for a, b in zip(pts, pts[1:]) if a != b]
    near = min(s.distance(hexa.centroid) for s in segs)
    assert near < 0.2, near


def test_on_a_thin_stroke_still_sews_a_run():
    """A stroke whose ring already reads solid keeps the run tier: a 0.3 mm
    line, inset by half a laid width, has nothing left inside."""
    line = Polygon([(0, 0), (3.0, 0), (3.0, 0.3), (0, 0.3)])
    runs, _w = _plan(line, small_solids_satin=True)
    assert runs and {r.kind for r in runs} == {"run"}


def test_on_a_shape_with_a_hole_still_sews_a_run():
    """A ring is what the run tier is for: a holed shape is not a solid."""
    outer = _hexagon(1.45)
    ring = Polygon(outer.exterior.coords, [list(_hexagon(0.5).exterior.coords)])
    runs, _w = _plan(ring, small_solids_satin=True)
    assert runs and {r.kind for r in runs} == {"run"}


def test_on_a_small_plus_sews_one_blob_with_every_needle_point_on_the_art():
    """Proseal's "+" (1.52 mm across): the ring sewed it as a hollow
    quadrilateral, the bean's 0.73 mm stations cutting its corners. ON it is
    one satin blob, the pro's construction; a cross may bridge a notch, but
    each needle point is on the artwork. Arms 0.6 mm: inset by half a laid
    width there is bare cloth left (the traced Proseal "+" leaves 0.186 mm^2).
    A plus of 0.43 mm arms leaves ~0.07 mm^2 -- its ring covers it, and it
    stays a run (the next test)."""
    h, w = 1.52 / 2, 0.6 / 2
    plus = Polygon([(-w, -h), (w, -h), (w, -w), (h, -w), (h, w), (w, w), (w, h),
                    (-w, h), (-w, w), (-h, w), (-h, -w), (-w, -w)])
    runs, _w = _plan(plus, small_solids_satin=True)
    assert [r.kind for r in runs] == ["satin"], [r.kind for r in runs]
    pts = runs[0].points
    assert len(pts) >= 4
    for x, y in pts:
        assert plus.buffer(1e-6).covers(Point(x, y)), (x, y)
    segs = [LineString([a, b]) for a, b in zip(pts, pts[1:]) if a != b]
    assert min(s.distance(plus.centroid) for s in segs) < 0.2


def test_on_a_thin_armed_plus_stays_a_run():
    h, w = 1.52 / 2, 0.43 / 2
    plus = Polygon([(-w, -h), (w, -h), (w, -w), (h, -w), (h, w), (w, w), (w, h),
                    (-w, h), (-w, w), (-h, w), (-h, -w), (-w, -w)])
    runs, _w = _plan(plus, small_solids_satin=True)
    assert runs and {r.kind for r in runs} == {"run"}


def test_the_flag_is_built_off_so_it_is_not_in_the_pre_flip_or_flagcost_tables():
    """Built OFF: the pre-flip engine IS the default, so neither table that
    lists ON flags carries it. A flip adds it to both."""
    from tests.conftest import PRE_FLIP
    from tools.pro_parity.flagcost import FLAGS
    assert "small_solids_satin" not in PRE_FLIP
    assert "small_solids_satin" not in FLAGS
