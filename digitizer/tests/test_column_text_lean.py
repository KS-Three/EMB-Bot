"""Crosses square to the line of text in the Column lane
(`cfg.lettering_columns_text_lean`, built OFF 2026-10-23;
`digitizer_core/column_lean.py`, `docs/lettering-10mm-up-2026-10-23.md`).

The pro sews every stroke of Becker's MARINE (12.8-17.1 mm caps) with the
stems' cross, square to the line of text, diagonals included; the Column
lane stations each straight piece square to its own axis. ON, a straight
column whose axis the word's house cross can span within the 30 degree
lean cap (`stage6_satin._clamp_to_span`, Kent's 2026-09-03 convention) is
re-stationed with its crosses along the house, one every spacing /
cos(lean) along the axis; an upright stem under upright text, a curved
column and a letter with no house angle keep their stations. OFF is the
lane as it was, station for station.
"""
from __future__ import annotations

import math

from shapely.affinity import rotate
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core.column_lean import (MIN_LEAN_DEG, cross_direction, lean_column,
                                        lean_columns, lean_stations)
from digitizer_core.columns import Column, column_runs, lettering_columns_shape
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.outline_cut import letter_columns
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence
from digitizer_core.stage6_satin import SATIN_HOUSE_MIN_SPAN_DEG

PITCH = machine.SATIN_SPACING_MM
CAP_DEG = 90.0 - SATIN_HOUSE_MIN_SPAN_DEG           # 30: the convention's lean cap


def _bar(width=4.0, length=14.0, rot_deg=0.0) -> Polygon:
    bar = Polygon([(0, 0), (width, 0), (width, length), (0, length)])
    return rotate(bar, rot_deg, origin=(width / 2, length / 2)) if rot_deg else bar


def _columns(poly):
    return letter_columns(poly, pitch_mm=PITCH, rail_axis=True).columns


def _cross_deg(station) -> float:
    (ax, ay), (bx, by) = station
    return math.degrees(math.atan2(by - ay, bx - ax)) % 180.0


def _leans(cols) -> list[float]:
    return [cross_direction(c.axis, 0.0)[2] for c in cols if c.axis is not None]


def test_flag_default_is_on():
    # Kent 2026-10-24, "Flip it ON" (docs/big-letter-construction-2026-10-24.md)
    assert PipelineConfig().lettering_columns_text_lean is True


def test_cross_direction_is_the_satin_tiers_clamp():
    # an upright stem under upright text (house 0 = a horizontal cross):
    # the cross IS the house, no lean
    cx, cy, lean = cross_direction((0.0, 1.0), 0.0)
    assert abs(cx) > 0.999 and lean < 1e-9
    # a 30 degree diagonal: the house exactly, at the cap
    u = (math.sin(math.radians(30)), math.cos(math.radians(30)))
    cx, cy, lean = cross_direction(u, 0.0)
    assert abs(cy) < 1e-9 and abs(lean - 30.0) < 1e-6
    # a 45 degree diagonal: past the cap the lean fades (22.5 here)
    u = (math.sqrt(0.5), math.sqrt(0.5))
    _cx, _cy, lean = cross_direction(u, 0.0)
    assert abs(lean - 22.5) < 1e-6
    # a horizontal bar: its own perpendicular, no lean
    _cx, _cy, lean = cross_direction((1.0, 0.0), 0.0)
    assert lean < 1e-9


def test_an_upright_stem_keeps_its_stations_object_for_object():
    cols = _columns(_bar())
    assert len(cols) == 1 and cols[0].kind == "straight"
    out = lean_columns(cols, 0.0, PITCH)
    assert out[0] is cols[0]
    assert lean_columns(cols, None, PITCH) is cols


def test_a_diagonal_takes_the_house_cross_at_the_conventions_spacing():
    for rot in (15.0, 30.0):
        cols = _columns(_bar(rot_deg=rot))
        assert len(cols) == 1 and cols[0].kind == "straight"
        before = cols[0]
        after = lean_column(before, 0.0, PITCH)
        assert after is not before
        # every cross horizontal: the house, not the piece's own normal
        mid = after.stations[len(after.stations) // 2]
        assert min(_cross_deg(mid), 180.0 - _cross_deg(mid)) < 0.5
        # the cross spans the stroke at W / cos(lean)
        w = math.dist(*mid)
        assert abs(w - 4.0 / math.cos(math.radians(rot))) < 0.05
        # stations one pitch / cos(lean) apart along the axis: fewer of them
        # (the leaned lines that only clip a corner at each end are short)
        expect = 14.0 * math.cos(math.radians(rot)) / PITCH
        assert abs(len(after.stations) - expect) <= 8, (len(after.stations), expect)
        # the crosses sit the satin spacing apart, measured square to themselves
        a0, a1 = after.stations[10][0], after.stations[11][0]
        axis = after.axis
        along = abs((a1[0] - a0[0]) * axis[0] + (a1[1] - a0[1]) * axis[1])
        assert abs(along * math.cos(math.radians(rot)) - PITCH) < 0.02
        # rails keep their sides: rail A's end is on the same side as before
        assert after.rail_a == before.rail_a and after.rail_b == before.rail_b
        assert after.piece is before.piece and after.axis == before.axis


def test_past_the_cap_the_lean_fades_toward_the_pieces_own_normal():
    cols = _columns(_bar(rot_deg=45.0))
    after = lean_column(cols[0], 0.0, PITCH)
    mid = after.stations[len(after.stations) // 2]
    d = min(_cross_deg(mid), 180.0 - _cross_deg(mid))
    assert abs(d - 22.5) < 1.0          # half the cap, the fade's value at 45


def test_a_lean_under_the_floor_or_a_curved_column_is_left_alone():
    cols = _columns(_bar(rot_deg=MIN_LEAN_DEG / 2))
    assert lean_column(cols[0], 0.0, PITCH) is cols[0]
    curved = Column(stations=[((0, 0), (1, 0)), ((0, 1), (1, 1)), ((0, 2), (1, 2))],
                    piece=_bar(), kind="curved", axis=None, width_mm=1.0)
    assert lean_column(curved, 0.0, PITCH) is curved


def test_lean_stations_needs_three_crosses():
    tiny = Polygon([(0, 0), (0.3, 0), (0.3, 0.5), (0, 0.5)])
    assert lean_stations(tiny, (0.0, 1.0), (math.cos(0.3), math.sin(0.3)), PITCH) is None


def test_the_leaned_columns_sew():
    piece = _bar(rot_deg=30.0)
    cols = lean_columns(_columns(piece), 0.0, PITCH)
    runs, report = column_runs(cols, piece, "S1", trim_at_mm=3.0, pull_mm=0.3, pull_floor_mm=0.5)
    assert runs and not report["empty"]
    assert report["stations"] == len(cols[0].stations)


def _n_letter() -> Polygon:
    """An N: two upright stems and a diagonal, 4 mm strokes, 16 mm cap."""
    stem_l = Polygon([(0, 0), (4, 0), (4, 16), (0, 16)])
    stem_r = Polygon([(12, 0), (16, 0), (16, 16), (12, 16)])
    diag = Polygon([(0, 16), (4.5, 16), (16, 0), (11.5, 0)])
    return stem_l.union(stem_r).union(diag)


def _plan(poly: Polygon, meta: dict | None = None, **cfg_kw):
    m = {"layer": 0, "text_candidate": True, "lettering_group": True, "text_cluster_id": "TC1"}
    m.update(meta or {})
    reg = Region(shape_id="Sn", polygon=poly, thread_index=0,
                 thread_number="4101", area_mm2=poly.area, source="test", meta=m)
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, lettering_columns_skip_blobs=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _satin_cross_angles(runs) -> list[float]:
    """Angle from horizontal of every satin stitch over 2 mm (the crosses)."""
    out = []
    for r in runs:
        if r.kind != "satin":
            continue
        for a, b in zip(r.points, r.points[1:]):
            if math.dist(a, b) >= 2.0:
                d = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
                out.append(min(d, 180.0 - d))
    return out


def test_off_is_the_lane_as_it_was_with_a_house_angle_present():
    n = _n_letter()
    a = _plan(n, {"satin_angle_deg": 0.0})
    b = _plan(n, {"satin_angle_deg": 0.0}, lettering_columns_text_lean=False)
    assert [r.points for r in a] == [r.points for r in b]


def test_on_with_no_house_angle_is_the_lane_as_it_was():
    n = _n_letter()
    a = _plan(n)
    b = _plan(n, lettering_columns_text_lean=True)
    assert [r.points for r in a] == [r.points for r in b]


def test_on_the_n_diagonal_sews_with_the_stems_cross():
    n = _n_letter()
    off = _plan(n, {"satin_angle_deg": 0.0})
    on = _plan(n, {"satin_angle_deg": 0.0}, lettering_columns_text_lean=True)
    assert [r.points for r in on] != [r.points for r in off]
    off_angles, on_angles = _satin_cross_angles(off), _satin_cross_angles(on)
    # off, the diagonal's crosses sit square to the diagonal (this N's runs
    # 35.7 deg off upright, so its crosses are 30-60 deg off the stems');
    # on, past the cap the lean fades and every cross lies within 20 deg
    # of the stems' horizontal
    assert sum(1 for a in off_angles if a > 20.0) >= 20
    assert max(on_angles) < 20.0, max(on_angles)
    assert sum(1 for a in on_angles if a > 5.0) >= 10        # the diagonal still leans


def test_the_wiring_reads_the_designs_house_when_the_word_has_none():
    n = _n_letter()
    off = _plan(n, satin_angle_deg=0.0)
    on = _plan(n, satin_angle_deg=0.0, lettering_columns_text_lean=True)
    assert [r.points for r in on] != [r.points for r in off]


def test_lettering_columns_shape_takes_the_lean_directly():
    n = _n_letter()
    plain, _ = lettering_columns_shape(n, "Sn", trim_at_mm=3.0, rail_axis=True)
    leaned, _ = lettering_columns_shape(n, "Sn", trim_at_mm=3.0, rail_axis=True, text_lean_deg=0.0)
    assert [r.points for r in plain] != [r.points for r in leaned]
    same, _ = lettering_columns_shape(n, "Sn", trim_at_mm=3.0, rail_axis=True, text_lean_deg=None)
    assert [r.points for r in plain] == [r.points for r in same]
