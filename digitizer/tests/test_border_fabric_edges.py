"""`border_by_size` rings fabric edges only (`cfg.border_by_size_fabric_edges`,
built OFF 2026-10-28; `docs/bean-border-logic-2026-10-28.md`).

On Kent's Instagram icon `border_by_size` ringed every gradient band of 6 mm
and up round its whole perimeter, seams with the next band included, and the
logo's own outline only where a band happened to reach it. ON, a size ring
skips every stretch it shares with another sewn region, so two butting
colours meet on a plain seam and the ring follows the bare-fabric edge.
Off, byte-identical.
"""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence


def _rect(x0, y0, x1, y1) -> Polygon:
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


# Two 10 x 10 mm squares of different threads sharing the x = 0 edge.
LEFT = _rect(-10.0, -5.0, 0.0, 5.0)
RIGHT = _rect(0.0, -5.0, 10.0, 5.0)


def _plan(**cfg_kw):
    planned = []
    for i, (sid, poly, thread) in enumerate((("Sleft", LEFT, "4101"), ("Sright", RIGHT, "4102"))):
        reg = Region(shape_id=sid, polygon=poly, thread_index=i, thread_number=thread,
                     area_mm2=poly.area, source="test", meta={"layer": 0})
        planned.append(PlannedRegion(region=reg, polygon=poly, sew_index=i))
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _border_pts(runs):
    return [p for r in runs if r.kind == stitches.BORDER for p in r.points]


def _near_seam(pts, reach=1.0):
    """Border penetrations within `reach` of the shared edge, away from the
    two outer corners where the fabric edge itself turns."""
    return [p for p in pts if abs(p[0]) <= reach and abs(p[1]) < 3.0]


def test_default_is_off():
    assert PipelineConfig().border_by_size_fabric_edges is False


def test_off_the_seam_carries_a_ring():
    # today's engine: seam ownership hands the seam to the later square, which rings it
    assert _near_seam(_border_pts(_plan()))


def test_on_the_seam_is_bare_and_the_fabric_edges_keep_their_ring():
    runs = _plan(border_by_size_fabric_edges=True)
    pts = _border_pts(runs)
    assert pts, "the fabric edges lost their ring too"
    assert not _near_seam(pts)
    # both squares keep ring on their outer side (x = -10 and x = +10)
    assert any(p[0] < -8.0 for p in pts) and any(p[0] > 8.0 for p in pts)


def test_on_both_squares_still_fill():
    runs = _plan(border_by_size_fabric_edges=True)
    for sid in ("Sleft", "Sright"):
        assert any(r.kind == stitches.FILL and r.shape_id == sid for r in runs)


def test_on_a_lone_square_is_unchanged():
    # nothing to share a seam with: the ring is the whole edge, as OFF
    poly = _rect(-5.0, -5.0, 5.0, 5.0)

    def one(**kw):
        reg = Region(shape_id="Sone", polygon=poly, thread_index=0, thread_number="4101",
                     area_mm2=poly.area, source="test", meta={"layer": 0})
        blocks, _w = sequence([PlannedRegion(region=reg, polygon=poly, sew_index=0)],
                              fabric_for_garment("hat_front"), PipelineConfig(underlay=False, **kw))
        return [(r.kind, tuple(map(tuple, r.points))) for b in blocks for r in b.runs]

    assert one(border_by_size_fabric_edges=True) == one()


def test_border_by_size_off_makes_the_flag_inert():
    a = _plan(border_by_size=False)
    b = _plan(border_by_size=False, border_by_size_fabric_edges=True)
    assert [(r.kind, r.points) for r in a] == [(r.kind, r.points) for r in b]
