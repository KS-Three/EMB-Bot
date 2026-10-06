"""`cross_tatami` (2026-10-05): one sparse tatami pass under a fill, crossing
the top fill at 90 degrees, rows 1.0 mm, stitches 4.0 mm, no edge run — the
recipe read off Kent's commissioned files (`docs/underlay-audit-2026-10-05.md`:
34 large fills, row pitch p50 0.98 mm, stitch p50 3.99 mm, angle p50 89
degrees, 16% of the top fill's thread).

A CHOICE, not a default: no fabric preset names it, so nothing sews it unless
a design or a shape asks. Not sewn by us; the two numbers are the
professional's.
"""
from __future__ import annotations

import json
import math

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import fabrics, machine, stitches
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage6_fill import _underlay_paths, stitch_shape
from digitizer_core.threads import CHART

RECT = Polygon([(0, 0), (40, 0), (40, 30), (0, 30)])
HOLED = Polygon([(0, 0), (40, 0), (40, 30), (0, 30)],
                [[(15, 10), (25, 10), (25, 20), (15, 20)]])


def _segments(paths):
    for path in paths:
        for a, b in zip(path, path[1:]):
            yield a, b


def _rows(paths, fill_angle_deg: float):
    """The pass's rows: every segment longer than the row step, as
    (direction relative to the fill angle in degrees mod 180, position across
    the rows in mm)."""
    out = []
    a = math.radians(fill_angle_deg + 90.0)
    ux, uy = math.cos(a), math.sin(a)          # along a crossing row
    for (x0, y0), (x1, y1) in _segments(paths):
        length = math.hypot(x1 - x0, y1 - y0)
        if length <= 1.5 * machine.UNDERLAY_CROSS_ROW_MM:
            continue
        direction = (math.degrees(math.atan2(y1 - y0, x1 - x0)) - fill_angle_deg) % 180.0
        across = -x0 * uy + y0 * ux
        out.append((direction, across))
    return out


def test_the_constants_are_the_professionals():
    assert machine.UNDERLAY_CROSS_ROW_MM == 1.0
    assert machine.UNDERLAY_CROSS_STITCH_MM == 4.0


def test_no_fabric_preset_sews_it():
    assert all(f.fill_underlay != "cross_tatami" for f in fabrics.FABRICS)
    assert all(f.satin_underlay != "cross_tatami" for f in fabrics.FABRICS)


@pytest.mark.parametrize("fill_angle", [0.0, 30.0, 90.0])
def test_the_pass_crosses_the_fill_at_ninety_degrees_at_one_millimetre(fill_angle):
    paths = _underlay_paths(RECT, "cross_tatami", fill_angle)
    long_segments = _rows(paths, fill_angle)
    # The rest of the long segments are the hops along the edge from one row
    # to the next, where the edge meets the rows at a shallow angle.
    rows = [(d, a) for d, a in long_segments if abs(d - 90.0) < 0.5]
    assert len(rows) > 20
    assert len(rows) >= 0.9 * len(long_segments), (len(rows), len(long_segments))
    positions = sorted({round(across, 3) for _d, across in rows})
    gaps = [b - a for a, b in zip(positions, positions[1:])]
    assert gaps and all(abs(g - machine.UNDERLAY_CROSS_ROW_MM) < 0.01 for g in gaps), gaps


def test_no_stitch_is_longer_than_four_millimetres():
    paths = _underlay_paths(RECT, "cross_tatami", 0.0)
    longest = max(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in _segments(paths))
    assert longest <= machine.UNDERLAY_CROSS_STITCH_MM + 1e-6
    # and it is a 4 mm pass, not the 2.5 mm lattice stitch
    assert longest > machine.UNDERLAY_STITCH_MM + 0.5


def test_the_pass_stays_inside_the_inset_and_out_of_holes():
    keep = HOLED.buffer(-machine.UNDERLAY_INSET_MM + 0.01)
    for path in _underlay_paths(HOLED, "cross_tatami", 0.0):
        for x, y in path:
            assert keep.covers(Point(x, y)), (x, y)


def test_there_is_no_edge_run():
    """`edge_lattice` minus its edge walk: the same call shape, so the pass
    alone is exactly what `zigzag` sews at this row and stitch."""
    cross = _underlay_paths(RECT, "cross_tatami", 0.0)
    edge_first = _underlay_paths(RECT, "edge_lattice", 0.0)
    ring = RECT.buffer(-machine.UNDERLAY_INSET_MM).exterior
    on_ring = lambda path: all(ring.distance(Point(p)) < 1e-6 for p in path)
    assert on_ring(edge_first[0]), "fixture: edge_lattice opens with its edge walk"
    assert not any(on_ring(path) for path in cross)


def test_it_goes_down_before_the_fill_at_about_a_sixth_of_its_thread():
    runs, _report = stitch_shape(
        RECT, "S1", angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="cross_tatami",
        trim_at_mm=machine.TRIM_AT_MM)
    kinds = [r.kind for r in runs]
    assert stitches.UNDERLAY in kinds
    assert kinds.index(stitches.UNDERLAY) < kinds.index(stitches.FILL)
    last_underlay = max(i for i, k in enumerate(kinds) if k == stitches.UNDERLAY)
    assert last_underlay < kinds.index(stitches.FILL)
    under = sum(r.length_mm for r in runs if r.kind == stitches.UNDERLAY)
    top = sum(r.length_mm for r in runs if r.kind == stitches.FILL)
    # The professional's share: p10-p90 11-20% of the top fill's thread.
    assert 0.11 <= under / top <= 0.20, under / top


def test_the_sewn_pass_keeps_its_four_millimetre_stitch():
    """`stitch_shape` re-splits every underlay path at a maximum step. At the
    lattice's 2.5 mm that halved each 4 mm stitch to 2 mm — found by reading
    our own DST back with the instrument that read the professional's
    (2026-10-05): pitch 1.0, stitch 2.0."""
    runs, _report = stitch_shape(
        RECT, "S1", angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="cross_tatami",
        trim_at_mm=machine.TRIM_AT_MM)
    lengths = [round(math.hypot(b[0] - a[0], b[1] - a[1]), 1)
               for r in runs if r.kind == stitches.UNDERLAY
               for a, b in zip(r.points, r.points[1:])]
    most_common = max(set(lengths), key=lengths.count)
    assert most_common == machine.UNDERLAY_CROSS_STITCH_MM, most_common
    assert max(lengths) <= machine.UNDERLAY_CROSS_STITCH_MM


def test_a_shape_override_may_ask_for_it():
    region = Region(shape_id="S1", polygon=RECT, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=RECT.area,
                    meta={"layer": 0})
    regions, _threads, _notes = apply_shape_edits(
        [region], [0], [], {"S1": {"underlay_style": "Cross_Tatami"}}, CHART)
    assert regions[0].meta["underlay_style"] == "cross_tatami"


def test_the_service_accepts_it_on_the_wire():
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"underlay_style": "cross_tatami"}}})) == \
        {"shape_overrides": {"S1": {"underlay_style": "cross_tatami"}}}
