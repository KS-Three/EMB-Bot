"""Compact solids sew as one satin column, not a fill with a ring round it
(`compact_solids_satin`, 2026-10-22, folded into the code 2026-11-19).

The defect (Proseal at the pro's 85.9 mm, Hat): the sixteen teal spray
hexagons at or over the detail floor (2.0-3.7 mm across) fail the ribbon
classifier's aspect test (`classify_ribbon`: a regular hexagon's length
estimate is ~1.3 widths against the 3 a ribbon needs), so stage 7 sews them
as tatami rows; every row end stands in open air, so the bean edge cap
(`edge_cap="bean"`) then draws a ring round each one. That ring is the
"satin border" Kent saw. The pro's DST sews every hexagon, 1.6 to 4.8 mm
across, as ONE satin blob with nothing round it.

A non-lettering solid with no hole that the classifier refused for
aspect only sews `stage6_satin.small_solid_satin` -- one column across its
short side at the block's satin pitch -- the same emitter the rescue's
`small_solids_satin` uses below the floor. Satin is linear cover, so the
edge cap leaves that edge alone on its own.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence


def _hexagon(across: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    r = across / 2.0
    return Polygon([(cx + r * math.cos(math.radians(60 * k)),
                     cy + r * math.sin(math.radians(60 * k))) for k in range(6)])


def _plan(poly: Polygon, **cfg_kw):
    reg = Region(shape_id="Sblob", polygon=poly, thread_index=0,
                 thread_number="4101", area_mm2=poly.area, source="test",
                 meta={"layer": 0})
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, warnings = sequence(planned, fabric_for_garment("hat_front"),
                                PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs], warnings


def _kinds(runs, shape_id="Sblob"):
    return [r.kind for r in runs if r.shape_id == shape_id]


def test_a_3mm_hexagon_sews_one_satin_and_no_cap():
    hexa = _hexagon(3.4)
    runs, _w = _plan(hexa)
    assert _kinds(runs) == [stitches.SATIN], _kinds(runs)
    assert not [r for r in runs if r.shape_id == "__edge_cap__"]
    pts = [r for r in runs if r.shape_id == "Sblob"][0].points
    # crosses at the satin pitch across a 3.4 mm hexagon: a column, not a dot
    assert len(pts) >= 12
    for x, y in pts:
        assert hexa.buffer(0.05).covers(Point(x, y)), (x, y)
    segs = [LineString([a, b]) for a, b in zip(pts, pts[1:]) if a != b]
    assert min(s.distance(hexa.centroid) for s in segs) < 0.3
    # every cross spans the shape: the longest stitch is the hexagon's own
    # chord, over two thirds of its width
    assert max(s.length for s in segs) > 0.66 * 3.4


def test_a_hexagon_over_the_satin_ceiling_still_fills():
    """Width over `machine.SATIN_MAX_WIDTH_MM` is the classifier's own
    width-cap refusal, not an aspect one: the fill tier keeps it."""
    across = machine.SATIN_MAX_WIDTH_MM * 1.6
    runs, _w = _plan(_hexagon(across))
    assert stitches.FILL in _kinds(runs)
    assert stitches.SATIN not in _kinds(runs)


def test_a_ribbon_still_sews_the_satin_tier_not_the_blob_column():
    """A 2 x 12 mm bar passes the aspect test and takes the ordinary satin
    tier; the rule must not touch it (its column has pull comp and caps)."""
    bar = Polygon([(0, 0), (12, 0), (12, 2), (0, 2)])
    runs, _ = _plan(bar)
    assert _kinds(runs) == [stitches.SATIN]


def test_a_hexagon_with_a_hole_is_left_to_the_tier_it_had():
    """A holed shape is not a solid (`is_small_solid`): the rule never
    reads it, whichever tier the classifier gives it."""
    outer = _hexagon(3.4)
    ring = Polygon(outer.exterior.coords, [list(_hexagon(1.0).exterior.coords)])
    runs, _w = _plan(ring)
    # the satin tier's two rails round the hole, not the blob rule's one column
    assert _kinds(runs) == [stitches.SATIN, stitches.SATIN], _kinds(runs)


def test_lettering_is_left_alone():
    """A text-cluster member is the Column lane's or the fill's, never this
    rule's: an O-less blob tagged as text keeps the fill's path."""
    hexa = _hexagon(3.4)
    reg = Region(shape_id="Sblob", polygon=hexa, thread_index=0,
                 thread_number="4101", area_mm2=hexa.area, source="test",
                 meta={"layer": 0, "text_cluster_id": 1, "text_candidate": True})
    planned = [PlannedRegion(region=reg, polygon=hexa, sew_index=0)]
    # `lettering_columns_skip_blobs` (ON) already untags a solid blob as
    # lettering; off, the tag stands and this rule must still step aside
    cfg = PipelineConfig(underlay=False, lettering_columns=False,
                         lettering_columns_skip_blobs=False)
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg)
    kinds = [r.kind for blk in blocks for r in blk.runs if r.shape_id == "Sblob"]
    assert stitches.FILL in kinds
    assert stitches.SATIN not in kinds
