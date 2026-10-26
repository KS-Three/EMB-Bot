"""`cfg.extra["fill_section_travel"]` (built OFF 2026-10-25): a fill's sections
are sewn without cutting between them where the travel can go under rows
still to come, and its underlay hops between hole rings inside the shape.

Measured first on five paired hat jobs (`docs/in-piece-cuts-2026-10-25.md`):
the travel between two sections of ONE fill is the largest class of cut
inside a piece that the professional never makes -- 35 on main, 0 on his
side. Chaining territory, ROADMAP gate 3: the flag stays OFF, and every
stitch it adds must lie where the shape's own fill sews over it afterwards.

The fixtures are shapely polygons on purpose (a traced raster's outline
differs by platform): a field with two rows of square holes, rows
horizontal -- the knock-out construction of Hotel Fremont's field, small.
"""
from __future__ import annotations

import functools
import hashlib
import json
import sys

import pytest
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, fill_section_travel, machine, stitches
from digitizer_core import stage6_fill
from digitizer_core.stage6_fill import _EXPOSED_TOLERANCE_MM, stitch_shape

TRIM_AT = 3.0
ROW = 0.4
HOLES = [box(x, y, x + 8.0, y + 8.0) for x in (6, 20, 34, 48) for y in (8, 24)]
GRID = box(0.0, 0.0, 60.0, 40.0).difference(unary_union(HOLES))


def _sew_now(on: bool, underlay: str = "edge_lattice", shape=GRID, **kw):
    args = dict(angle_deg=0.0, row_mm=ROW, stitch_mm=3.0, underlay_style=underlay,
                trim_at_mm=TRIM_AT, under_cover=True, cut_bridges=True,
                start_near=(0.0, 0.0))
    args.update(kw)
    tok = fill_section_travel._ON.set(on)
    try:
        runs, _report = stitch_shape(shape, "S1", **args)
    finally:
        fill_section_travel._ON.reset(tok)
    return runs


@functools.lru_cache(maxsize=None)
def _sew(on: bool, underlay: str = "edge_lattice"):
    """The fixture, sewn once per arm for the whole file (ON plans; it is
    the slow arm). Callers must not mutate the runs."""
    return tuple(_sew_now(on, underlay))


def _md5(runs) -> str:
    rows = [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
            for r in runs for x, y in r.points]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _cuts(runs, kind=None) -> int:
    return sum(1 for r in runs if r.trim and (kind is None or r.kind == kind))


def _new_travel(off, on):
    """Indices (into `on`) of the TRAVEL runs ON sews that OFF did not."""
    old = {tuple(map(tuple, r.points)) for r in off if r.kind == stitches.TRAVEL}
    return [k for k, r in enumerate(on) if r.kind == stitches.TRAVEL
            and tuple(map(tuple, r.points)) not in old]


def _thread(runs, k):
    """Every needle-down segment of travel run k: from the stitch before it,
    through it, to the stitch after it."""
    return [runs[k - 1].points[-1], *runs[k].points, runs[k + 1].points[0]]


# --------------------------------------------------------------------- OFF --

def test_the_flag_is_off_by_default():
    assert not PipelineConfig().extra.get(fill_section_travel.KEY)
    assert not fill_section_travel.active()


def test_enabled_reads_the_config_and_restores():
    on = PipelineConfig(extra={fill_section_travel.KEY: True})
    with fill_section_travel.enabled(on):
        assert fill_section_travel.active()
        with fill_section_travel.enabled(PipelineConfig()):
            assert not fill_section_travel.active()
        assert fill_section_travel.active()
    assert not fill_section_travel.active()


def test_plan_stitches_reads_the_flag_from_cfg_extra(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches",
                        lambda result, cfg: seen.append(fill_section_travel.active()))
    pipeline.plan_stitches(None, PipelineConfig())
    pipeline.plan_stitches(None, PipelineConfig(extra={fill_section_travel.KEY: True}))
    assert seen == [False, True]
    assert not fill_section_travel.active()


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("fill_section_travel reached with the flag off")
    for name in ("bridge", "plan", "reset"):
        monkeypatch.setattr(fill_section_travel, name, boom)
    _sew_now(False)
    _sew_now(False, underlay="none")


# Captured on the base commit (c531c7b8), before the flag existed.
OFF_MD5 = {"none": "8f8c1bfe4a5352c4a7c3eb6f6a0cc246",
           "edge_lattice": "81e028bb3cf44f121ca52d8e4ede042a"}


@pytest.mark.parametrize("underlay", ["none", "edge_lattice"])
def test_off_is_byte_identical_to_base(underlay):
    """Pinned where it was captured; the in-process test below holds on
    every platform (a planned fill's float order can differ by platform,
    `tests/test_cut_every_jump.py`'s "earlier" case)."""
    got = _md5(_sew(False, underlay))
    if sys.platform == "win32":
        assert got == OFF_MD5[underlay]


@pytest.mark.parametrize("underlay", ["none", "edge_lattice"])
def test_on_with_nothing_found_is_off(monkeypatch, underlay):
    """In-process, every platform: with the router finding nothing and the
    planner proposing nothing, ON is OFF byte for byte -- the flag's only
    effects are those two calls."""
    monkeypatch.setattr(fill_section_travel, "bridge", lambda *_a, **_k: None)
    monkeypatch.setattr(fill_section_travel, "plan", lambda paths, *_a, **_k: paths)
    assert _md5(_sew_now(True, underlay)) == _md5(_sew(False, underlay))


# ---------------------------------------------------------------------- ON --

def test_the_fixture_cuts_in_its_fill_and_its_underlay_with_the_flag_off():
    off = _sew(False)
    assert _cuts(off, stitches.FILL) >= 1
    assert _cuts(off, stitches.UNDERLAY) >= 1


def test_on_cuts_neither():
    on = _sew(True)
    assert _cuts(on, stitches.FILL) == 0
    assert _cuts(on, stitches.UNDERLAY) == 0


def test_on_sews_the_same_penetrations():
    """Order and direction change and travel is added; where the fill and
    the underlay put the needle down does not."""
    def pts(runs, kind):
        return sorted(p for r in runs if r.kind == kind for p in r.points)
    for kind in (stitches.FILL, stitches.UNDERLAY):
        assert pts(_sew(True), kind) == pts(_sew(False), kind), kind


def test_the_shape_exits_where_it_did():
    assert _sew(True)[-1].points[-1] == _sew(False)[-1].points[-1]


def test_every_new_travel_is_sewn_over_by_the_fill():
    """The pro's rule and gate 3's letter: no stitch ON adds is left on top
    of the work or on bare fabric. Read from the runs, not from the router:
    each sample of the new travel's thread lies inside the shape and within
    a row of a FILL run sewn after it, bar one travel stitch at an end
    (`travel_path`'s own allowance, `_EXPOSED_TOLERANCE_MM`)."""
    off, on = _sew(False), _sew(True)
    new = _new_travel(off, on)
    assert new, "the flag sewed no new travel on its own fixture"
    for k in new:
        later = unary_union([LineString(r.points).buffer(ROW) for r in on[k + 1:]
                             if r.kind == stitches.FILL and len(r.points) > 1])
        line = LineString(_thread(on, k))
        assert GRID.buffer(1e-6).covers(line), k
        n = max(2, int(line.length / 0.1))
        bare = sum(1 for i in range(n + 1)
                   if not later.covers(line.interpolate(i / n, normalized=True)))
        assert bare * line.length / n <= _EXPOSED_TOLERANCE_MM + 0.1, (k, bare)


def test_an_underlay_route_keeps_off_the_holes():
    a, b = (4.5, 20.0), (19.0, 20.0)       # either side of a column of holes
    slack = GRID.buffer(0.01)
    got = fill_section_travel.bridge(GRID, slack, a, b, stitches.UNDERLAY)
    assert got is not None
    line = LineString([a, *got])
    inner = GRID.buffer(-machine.TRAVEL_INSET_MM)
    ends = Point(a).buffer(_EXPOSED_TOLERANCE_MM).union(Point(b).buffer(_EXPOSED_TOLERANCE_MM))
    assert inner.union(ends.intersection(slack)).covers(line)
    assert all(not line.intersects(h.buffer(-1e-6)) for h in HOLES)
    assert max(Point(p).distance(Point(q)) for p, q in zip([a, *got], got))         <= machine.TRAVEL_STITCH_MM + 1e-9


def test_a_fill_hop_with_no_rows_to_come_is_not_routed():
    """Nothing still to sew between the ends: no hidden route, so the cut
    stays -- the flag never buys a bridge on finished work."""
    a, b = (4.5, 20.0), (19.0, 20.0)
    slack = GRID.buffer(0.01)
    assert fill_section_travel.bridge(GRID, slack, a, b, stitches.FILL, todo=[],
                                      row_mm=ROW) is None


def test_a_two_pass_fill_is_not_planned(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("planned a two-pass fill")
    monkeypatch.setattr(fill_section_travel, "plan", boom)
    _sew_now(True, underlay="none", technique="crosshatch")


def test_a_dearer_plan_is_not_taken(monkeypatch):
    """`_reorder_for_fewer_cuts`'s contract: price, keep the cheaper, ties
    to the incoming order. A plan the scorer prices dearer changes nothing
    but `emit`'s routes."""
    class Dear(list):
        pass

    real = stage6_fill._order_cost
    priced = []

    def scorer(order, *a, **k):
        priced.append(isinstance(order, Dear))
        return (999, 0.0, 0.0) if isinstance(order, Dear) else real(order, *a, **k)
    monkeypatch.setattr(fill_section_travel, "plan", lambda paths, *_a, **_k: Dear(paths))
    monkeypatch.setattr(stage6_fill, "_order_cost", scorer)
    planned = _sew_now(True, underlay="none")
    assert any(priced), "the planner's order was never priced"
    monkeypatch.setattr(fill_section_travel, "plan", lambda paths, *_a, **_k: paths)
    assert _md5(planned) == _md5(_sew_now(True, underlay="none"))


def test_articulation_points():
    path = {0: {1}, 1: {0, 2}, 2: {1}}
    ring = {0: {1, 2}, 1: {0, 2}, 2: {0, 1}}
    assert fill_section_travel._articulation({0, 1, 2}, path) == {1}
    assert fill_section_travel._articulation({0, 1, 2}, ring) == set()
    assert fill_section_travel._articulation({0, 2}, path) == set()
