"""The pro's size rule for borders (`cfg.border_by_size`, built OFF 2026-10-23).

`docs/border-census-2026-10-23.md` measured every closed shape of 16 paired
designs against the pro's files: he rings about 1% of shapes under 2 mm, 7%
at 2-4, 29% at 4-6 and 49% from 6 mm up, and contrast is not the variable.
Re-read at 4 mm and up on Fremont, Becker, MFab and Gaulke (the OFF rows
`tools/border_census.py` regenerates), what separates his bordered from his
unbordered big shapes is the STROKE against the satin ceiling: every letter
he sews as satin reads 4.2-5.4 mm wide in his file, every letter wider than
that is a fill with a 1.9-2.5 mm satin border (BECKER 5/5, MFAB 4/4), and a
plain solid over 6 mm is bordered at 2.4 (MFab's bar) where we fill it bare.

ON, a non-lettering shape on the auto tier with no per-shape border intent
whose smallest dimension (twice the largest inscribed circle, the census's
own measure) is at or over `machine.BORDER_BY_SIZE_MIN_DIM_MM` sews as a
fill with a satin border at the pro's width for its band
(`machine.border_by_size_width_mm`), on the seam it owns under the
2026-09-09 rule; a satin-classified shape of that size is diverted to the
fill tier first. A shape too thin to keep a fill inside the border (the
border would be a re-fill) is left to the tier it had. Lettering is the
Column lane's and is not read here. Off, byte-identical.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence


def _square(side: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    h = side / 2.0
    return Polygon([(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)])


def _plan(poly: Polygon, meta: dict | None = None, **cfg_kw):
    m = {"layer": 0}
    m.update(meta or {})
    reg = Region(shape_id="Sbig", polygon=poly, thread_index=0,
                 thread_number="4101", area_mm2=poly.area, source="test", meta=m)
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, warnings = sequence(planned, fabric_for_garment("hat_front"),
                                PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs], warnings


def _kinds(runs, shape_id="Sbig"):
    return [r.kind for r in runs if r.shape_id == shape_id]


def _border_width(runs, shape_id="Sbig") -> float:
    """Median zigzag chord of the shape's border runs: the sewn column width."""
    chords = []
    for r in runs:
        if r.shape_id != shape_id or r.kind != stitches.BORDER:
            continue
        pts = r.points
        chords.extend(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    chords.sort()
    assert chords, "no border chords"
    return chords[len(chords) // 2]


def test_flag_default_is_on():
    # Kent 2026-10-23, by the pro-count numbers (docs/renders/flip-two-2026-10-23/)
    assert PipelineConfig().border_by_size is True


def test_threshold_and_band_widths_are_the_census_numbers():
    assert machine.BORDER_BY_SIZE_MIN_DIM_MM == 6.0
    assert machine.border_by_size_width_mm(4.5) == 1.5
    assert machine.border_by_size_width_mm(6.0) == 2.1
    assert machine.border_by_size_width_mm(10.3) == 2.1


def test_off_an_8mm_square_fills_with_no_border():
    runs, _w = _plan(_square(8.0), border_by_size=False)
    assert stitches.FILL in _kinds(runs)
    assert stitches.BORDER not in _kinds(runs)


def test_on_an_8mm_square_fills_and_gets_a_satin_border_at_the_pro_width():
    sq = _square(8.0)
    runs, _w = _plan(sq, border_by_size=True)
    kinds = _kinds(runs)
    assert stitches.FILL in kinds and stitches.BORDER in kinds, kinds
    # the border goes on after the fill it covers
    assert kinds.index(stitches.FILL) < kinds.index(stitches.BORDER)
    assert abs(_border_width(runs) - machine.border_by_size_width_mm(8.0)) <= 0.1
    # a ring on the shape's own edge: every border point inside the square
    for r in runs:
        if r.shape_id == "Sbig" and r.kind == stitches.BORDER:
            for x, y in r.points:
                assert sq.buffer(0.05).covers(Point(x, y)), (x, y)
    # the pro's border is on top of a fill, not a re-fill: a fill core remains
    assert sq.buffer(-(machine.border_by_size_width_mm(8.0) + machine.BORDER_HOST_MARGIN_MM)).area > 0
    # satin border is linear cover: the edge cap leaves the edge alone
    assert not [r for r in runs if r.shape_id == "__edge_cap__"]


def test_on_a_1_5mm_square_gets_no_ring():
    runs, _w = _plan(_square(1.5), border_by_size=True)
    assert stitches.BORDER not in _kinds(runs)
    off, _w = _plan(_square(1.5))
    assert [r.points for r in runs] == [r.points for r in off]


def test_on_a_satin_ribbon_under_the_threshold_is_untouched():
    """A 4.5 x 40 mm bar is satin today and under the threshold: the flag
    leaves it alone. (A bar the classifier admits AND the rule reads needs a
    stroke over 6 mm under a ceiling of 5, so the divert is exercised on
    real art -- MFab's bar, Becker's ring -- in the PR's census, not here.)"""
    bar = Polygon([(0, 0), (40, 0), (40, 4.5), (0, 4.5)])
    on, _ = _plan(bar, border_by_size=True)
    off, _ = _plan(bar)
    assert _kinds(off) == [stitches.SATIN]
    assert [r.points for r in on] == [r.points for r in off]


def test_on_a_thin_ring_whose_border_would_be_a_refill_keeps_its_satin():
    """Becker's 2.4 mm ring with a fat junction: its inscribed circle passes
    the threshold at the junction (6.7 mm here) but only the knot is within
    a border width of a fill core (reach 0.16 of the area), so a 2.1 mm
    border would re-fill the ring and the tier it had stands."""
    outer = Point(0, 0).buffer(15.0, 64)
    ring = Polygon(outer.exterior.coords, [list(Point(0, 0).buffer(12.6, 64).exterior.coords)])
    knot = Point(0, 13.8).buffer(3.4, 32)
    shape = ring.union(knot)
    assert shape.geom_type == "Polygon"
    on, _ = _plan(shape, border_by_size=True)
    off, _ = _plan(shape)
    assert [r.points for r in on] == [r.points for r in off]


def test_on_lettering_is_left_alone():
    sq = _square(8.0)
    on, _ = _plan(sq, {"text_cluster_id": "TC1", "text_candidate": True, "lettering_group": True},
                  border_by_size=True, lettering_columns=False, lettering_columns_skip_blobs=False)
    off, _ = _plan(sq, {"text_cluster_id": "TC1", "text_candidate": True, "lettering_group": True},
                   lettering_columns=False, lettering_columns_skip_blobs=False)
    assert [r.points for r in on] == [r.points for r in off]


def test_on_a_per_shape_border_off_still_wins():
    sq = _square(8.0)
    runs, _ = _plan(sq, {"border": "off"}, border_by_size=True)
    assert stitches.BORDER not in _kinds(runs)


def test_the_default_is_the_flag_explicitly_true():
    for poly in (_square(8.0), _square(1.5), Polygon([(0, 0), (40, 0), (40, 4.5), (0, 4.5)])):
        a, _ = _plan(poly)
        b, _ = _plan(poly, border_by_size=True)
        assert [r.points for r in a] == [r.points for r in b]
