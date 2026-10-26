"""`cfg.silhouette_underfill_rim` (2026-10-25, built OFF): the under-fill
host's outer edge sewn as one closed satin loop after its fill, in its colour
(`stage6_border.underfill_rim_runs`).

Read from each file's own stitches: where a ring hosts its own under-fill
(MFab's black band, Fremont's white ground) the pro rims the fill's whole outer
edge with satin in the fill's colour, crosses square to the edge, width CV
0.03 -- MFab one closed column at 1.86-1.94 mm, Fremont the same edge in two
passes at 1.39-1.73. Where a letter hosts (Becker), the ring is the satin on
top already; no rim.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon, box

from digitizer_core import PipelineConfig, stitches
from digitizer_core import stage6_border as sb

W = sb.UNDERFILL_RIM_WIDTH_MM
#: an L-shaped silhouette: five convex corners, one concave at (20, 10)
ELL = Polygon([(0, 0), (40, 0), (40, 10), (20, 10), (20, 30), (0, 30)])


def _satin(runs):
    sat = [r for r in runs if r.kind == stitches.SATIN]
    return [p for r in sat for p in r.points], sat


def test_flag_is_off_by_default():
    assert PipelineConfig().silhouette_underfill_rim is False


def test_the_width_is_the_pros_measured_rim():
    # median of MFab hat 1.94, LC 1.86, Fremont hat 1.61, patch 1.65
    assert 1.6 <= W <= 1.95


def test_one_closed_loop_round_the_whole_edge_inside_the_outline():
    o = box(0, 0, 40, 20)
    runs, rep = sb.underfill_rim_runs(o, "Shost", entry=(1.0, 1.0), trim_at_mm=3.0)
    pts, sat = _satin(runs)
    assert rep["loops"] == 1 and len(sat) == 1
    assert all(r.shape_id == "Shost" for r in runs)
    ring = o.exterior
    near = [p for p in pts if ring.distance(Point(p)) < 0.05]
    # the rail walks the whole edge: no stretch of it longer than 0.5 mm unsewn
    s = sorted(ring.project(Point(p)) for p in near)
    gaps = [b - a for a, b in zip(s, s[1:])] + [s[0] + ring.length - s[-1]]
    assert max(gaps) <= 0.5
    # every cross inside the outline, reaching the rim's width and no further
    assert all(o.buffer(0.03).contains(Point(p)) for p in pts)
    assert max(ring.distance(Point(p)) for p in pts) <= W + 1e-6


def test_crosses_stand_square_to_a_straight_edge():
    o = box(0, 0, 40, 20)
    runs, _ = sb.underfill_rim_runs(o, "S", entry=(1.0, 1.0), trim_at_mm=3.0)
    pts, _ = _satin(runs)
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        # along the bottom edge, away from the corners and the loop's join
        if 8 < mid[0] < 32 and mid[1] < W:
            d = (b[0] - a[0], b[1] - a[1])
            off = math.degrees(math.atan2(abs(d[0]), abs(d[1])))
            # a zigzag's own slant: half a pitch over the width
            assert off <= math.degrees(math.atan2(0.2, W)) + 0.5


def test_the_concave_corner_pivots_its_inner_rail_dense():
    runs, _ = sb.underfill_rim_runs(ELL, "S", entry=(1.0, 1.0), trim_at_mm=3.0)
    pts, _ = _satin(runs)
    ring = ELL.exterior
    corner = (20.0, 10.0)
    inner = [p for p in pts if ring.distance(Point(p)) > 0.5 * W and math.dist(p, corner) < 2.0 * W]
    steps = [math.dist(a, b) for a, b in zip(inner, inner[1:])]
    assert max(steps) <= 1.25 * 0.4


def test_each_part_gets_its_own_loop_and_a_speck_none():
    two = box(0, 0, 20, 10).union(box(30, 0, 50, 10)).union(box(60, 0, 61, 1))
    runs, rep = sb.underfill_rim_runs(two, "S", entry=(0.0, 0.0), trim_at_mm=3.0)
    assert rep["loops"] == 2


def test_an_empty_outline_sews_nothing():
    runs, rep = sb.underfill_rim_runs(Polygon(), "S", entry=None, trim_at_mm=3.0)
    assert runs == [] and rep["empty"]


def test_the_rim_leaves_the_loop_flag_as_it_found_it():
    assert sb._LOOP_MITRE.get() is False
    sb.underfill_rim_runs(box(0, 0, 10, 10), "S", entry=None, trim_at_mm=3.0)
    assert sb._LOOP_MITRE.get() is False


def test_the_rail_is_on_the_edge_not_the_crosses_far_end():
    o = box(0, 0, 40, 20)
    runs, _ = sb.underfill_rim_runs(o, "S", entry=(1.0, 1.0), trim_at_mm=3.0)
    pts, _ = _satin(runs)
    on_edge = sum(LineString(o.exterior.coords).distance(Point(p)) < 0.05 for p in pts)
    # alternate penetrations: half on the edge
    assert abs(on_edge / len(pts) - 0.5) < 0.05


# --- the plan: `stage7_sequence` appends the rim to a ring host's runs ----------
# The fixtures are `test_silhouette_underfill`'s: MFab's band hosting its own
# under-fill, Becker's ring whose under-fill a letter hosts.
from tests.test_silhouette_underfill import _md5, _sew, becker, mfab  # noqa: E402

#: captured on origin/main 37c676c2 (before this flag), the under-fill ON
OFF_MD5 = {"mfab": "a429f57a0a79155e7d63ffea56fdabc6", "becker": "cd652df0ebca32d933202309b29e2bc4"}


def test_off_is_the_plan_as_it_was():
    assert _md5(_sew(mfab(), silhouette_underfill=True)[1]) == OFF_MD5["mfab"]
    assert _md5(_sew(becker(), silhouette_underfill=True)[1]) == OFF_MD5["becker"]


def test_off_never_reaches_the_rim(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("silhouette_underfill_rim code reached with the flag off")
    from digitizer_core import stage7_sequence as s7
    monkeypatch.setattr(s7, "underfill_rim_after", boom)
    _sew(mfab(), silhouette_underfill=True)


def test_on_the_ring_host_sews_its_rim_right_after_its_fill():
    planned, blocks = _sew(mfab(), silhouette_underfill=True, silhouette_underfill_rim=True)
    # on the edge the fill sews: stage 5's polygon, grown by the hat's pull
    ring = Polygon(next(p for p in planned if p.shape_id == "Sring").polygon.exterior)
    assert ring.bounds[0] < 0 and ring.bounds[3] > 24
    for b in blocks:
        mine = [r for r in b.runs if r.shape_id == "Sring"]
        if not mine:
            continue
        kinds = [r.kind for r in mine]
        assert stitches.FILL in kinds and kinds[-1] == stitches.SATIN
        # the satin after the last fill run is the rim: rail on the outer edge
        last_fill = max(i for i, k in enumerate(kinds) if k == stitches.FILL)
        rim = [p for r in mine[last_fill + 1:] if r.kind == stitches.SATIN for p in r.points]
        on_edge = [p for p in rim if ring.exterior.distance(Point(p)) < 0.05]
        assert len(on_edge) > 0.45 * len(rim)
        assert all(ring.buffer(0.03).contains(Point(p)) for p in rim)
        return
    raise AssertionError("no block sews the ring host")


def test_on_a_letter_host_has_no_rim_its_ring_is_the_satin():
    off = _md5(_sew(becker(), silhouette_underfill=True)[1])
    on = _md5(_sew(becker(), silhouette_underfill=True, silhouette_underfill_rim=True)[1])
    assert on == off


def test_without_the_underfill_the_rim_has_nothing_to_rim():
    assert (_md5(_sew(mfab(), silhouette_underfill_rim=True)[1])
            == _md5(_sew(mfab())[1]))
