"""`cfg.edge_cap_walk_covered` — walk the covered stretch between two cap arcs.

MASTER_SCOPE defect 19's trim bill: the gate splits a silhouette ring into
arcs wherever something linear already sews the edge, and the needle lifts
over each covered stretch between them. ON, the cap walks that stretch
instead — one pass at bean stations, every station on the cover — when the
walk costs no more than `machine.TRIM_COST_STITCHES`. OFF (the default) is
the shipped cap byte for byte. Built 2026-10-08.
"""
from __future__ import annotations

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage6_border import _covered_walk, silhouette_cap
from shapely.prepared import prep


def _square(s: float) -> Polygon:
    return Polygon([(0, 0), (s, 0), (s, s), (0, s)])


def _cover(*segments) -> object:
    """Linear cover standing on the given edge segments, one border wide."""
    return unary_union([LineString(seg).buffer(machine.BORDER_WIDTH_MM / 2)
                        for seg in segments])


def _cap(poly, omit, **kw):
    return silhouette_cap(poly, "S", style="bean", entry=None,
                          trim_at_mm=2.0, omit=omit, **kw)


def _points(runs):
    return [p for r in runs for p in r.points]


def test_default_is_off():
    assert PipelineConfig().edge_cap_walk_covered is False


def test_off_is_byte_identical_to_not_asking():
    poly = _square(30)
    omit = _cover([(30, 10), (30, 14)], [(10, 30), (14, 30)])
    a, ra = _cap(poly, omit)
    b, rb = _cap(poly, omit, walk_covered=False)
    assert [(r.points, r.jump, r.trim) for r in a] == \
        [(r.points, r.jump, r.trim) for r in b]
    assert ra == rb and ra["walked"] == 0


def test_short_covered_stretch_is_walked_not_jumped():
    poly = _square(30)
    omit = _cover([(30, 10), (30, 14)], [(10, 30), (14, 30)])
    off, r_off = _cap(poly, omit)
    on, r_on = _cap(poly, omit, walk_covered=True)
    assert r_off["arcs"] == r_on["arcs"] == 2
    assert r_on["walked"] == 1
    assert sum(r.jump for r in on) == sum(r.jump for r in off) - 1
    assert sum(r.trim for r in on) <= sum(r.trim for r in off)
    # Every stitch the walk added stands on the cover the gate judged by.
    cover = omit.buffer(machine.BORDER_HOST_MARGIN_MM)
    added = set(_points(on)) - set(_points(off))
    assert added and all(cover.intersects(Point(p)) for p in added)
    # And the needle never lifts mid-walk: the walked run's steps are bean
    # stations, not a hop.
    walked = next(r for r in on[1:] if not r.jump)
    steps = [LineString([a, b]).length
             for a, b in zip(walked.points, walked.points[1:])]
    assert max(steps) <= machine.MAX_STITCH_MM + 1e-9


def test_walk_longer_than_a_trim_is_not_taken():
    # Left side covered end to end (120 mm) — walking it would cost ~164
    # bean stations, more than a trim's `TRIM_COST_STITCHES`.
    s = 120.0
    poly = _square(s)
    omit = _cover([(0, 0), (0, s)], [(s, 60), (s, 64)])
    on, r_on = _cap(poly, omit, walk_covered=True)
    assert r_on["arcs"] == 2
    assert r_on["walked"] == 1          # the 4 mm gap, not the 120 mm side
    assert s / machine.BEAN_STITCH_MM > machine.TRIM_COST_STITCHES


def test_walk_refuses_bare_fabric():
    ring = list(_square(30).exterior.coords)
    cover = prep(_cover([(30, 0), (30, 10)]).buffer(0.05))
    # From (30, 0) up to (30, 20): the second half is bare.
    assert _covered_walk(ring, (30, 0), (30, 20), cover, 1000) is None
    walk = _covered_walk(ring, (30, 0), (30, 9), cover, 1000)
    assert walk is not None and walk[-1] == (30, 9)


def test_satin_style_never_walks():
    poly = _square(30)
    omit = _cover([(30, 10), (30, 14)], [(10, 30), (14, 30)])
    a, ra = silhouette_cap(poly, "S", style="satin", entry=None,
                           trim_at_mm=2.0, omit=omit)
    b, rb = silhouette_cap(poly, "S", style="satin", entry=None,
                           trim_at_mm=2.0, omit=omit, walk_covered=True)
    assert [r.points for r in a] == [r.points for r in b]
    assert rb["walked"] == 0
