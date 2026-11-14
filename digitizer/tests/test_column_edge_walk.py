"""`cfg.lettering_columns_connectors_edge_walk` (built OFF 2026-11-14): the
Column lane's walk ordered so the connector between a letter's strokes runs
inside the stroke sewn next, under its satin to come.

Kent on #1490's Becker pin #14 sheet: "Build edge-walk, notice how the pro
makes a nice corner with the thread andc continues the stitch to the right".
At every join of the pro's MARINE E, N and A the stroke he sews first ends
at the join and the next stroke's satin starts there and covers it. Read on
Becker MARINE's six letters as stage 7 hands them to the lane at 80 mm
(`testdata/becker80_lane_letters.json`), with the thread's own footprint
(0.4 mm) as the ground a satin covers.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, columns, stitches

BECKER = Path(__file__).resolve().parent.parent / "testdata" / "becker80_lane_letters.json"


def _letters():
    out = {}
    for key, v in json.loads(BECKER.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[key] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def _on_top(runs) -> list[float]:
    """Per needle-down hop or travel run: mm on the footprint of satin sewn
    before it and under no satin sewn after it (independent of the lane's
    own measure, which reads its stations)."""
    sat = [(k, LineString(r.points).buffer(0.2)) for k, r in enumerate(runs)
           if r.kind == stitches.SATIN and len(r.points) >= 2]
    out = []
    for k, r in enumerate(runs):
        if k == 0 or r.jump or not r.points:
            continue
        a = runs[k - 1].points[-1]
        path = [a, *r.points] if r.kind == stitches.TRAVEL else [a, r.points[0]]
        if math.dist(path[0], path[-1]) < 1e-9:
            continue
        done = unary_union([g for j, g in sat if j < k])
        later = unary_union([g for j, g in sat if j >= k])
        if done.is_empty:
            continue
        x = LineString(path).intersection(done)
        if not later.is_empty:
            x = x.difference(later)
        out.append(x.length)
    return out


def _key(runs):
    return [(r.points, r.kind, r.jump, r.trim) for r in runs]


@pytest.fixture(scope="module")
def sewn():
    rows = {}
    for key, (poly, kw) in _letters().items():
        rows[key] = {arm: columns.lettering_columns_shape(poly, "pin", **kw, **extra)
                     for arm, extra in (("off", {}), ("false", {"edge_walk": False}),
                                        ("buried", {"connectors_buried": True}),
                                        ("edge", {"edge_walk": True}))}
    return rows


# The lane's flags stage 7 passes by default (each ON since 10-13..10-24):
# the fixture's recorded call predates them.
PRODUCTION = dict(fold_cuts=True, square_ends=True, rail_axis=True, corner_fold=True,
                  inside_stagger=True, inside_connectors=True)


@pytest.fixture(scope="module")
def sewn_prod():
    rows = {}
    for key, (poly, kw) in _letters().items():
        rows[key] = {arm: columns.lettering_columns_shape(poly, "pin", **kw, **PRODUCTION, **extra)
                     for arm, extra in (("off", {}), ("buried", {"connectors_buried": True}),
                                        ("edge", {"edge_walk": True}))}
    return rows


def test_default_off():
    assert PipelineConfig().lettering_columns_connectors_edge_walk is False


def test_production_lane_buried_clean_at_offs_trims(sewn_prod):
    # with the arguments stage 7 passes: nothing over the limit on finished
    # satin, as connectors_buried, at no more trims than OFF -- counting the
    # hop into and out of each letter past the trim distance, as the lane's
    # own price does -- where buried pays three more
    _letters_kw = _letters()

    def trims(arm, inside_only=False):
        n = 0
        for key, a in sewn_prod.items():
            runs = a[arm][0]
            kw = _letters_kw[key][1]
            n += (sum(bool(r.trim) for r in runs) if inside_only
                  else columns._walk_cost(runs, kw["start_near"], kw["end_near"], kw["trim_at_mm"])[0])
        return n
    for key, arms in sewn_prod.items():
        tops = _on_top(arms["edge"][0])
        assert max(tops, default=0.0) <= columns._ON_TOP_MAX_MM + 0.05, (key, tops)
    assert trims("edge") <= trims("off") < trims("buried")
    assert trims("edge", inside_only=True) <= trims("buried", inside_only=True)


def test_off_is_the_walk_as_it_was(sewn):
    for arms in sewn.values():
        assert _key(arms["off"][0]) == _key(arms["false"][0])


def test_a_letter_buried_clean_keeps_its_walk(sewn):
    # no cut, no trim inside the letter, nothing over the limit: the walk
    # connectors_buried sews, byte for byte (the M, the I, the E)
    kept = 0
    for arms in sewn.values():
        runs, rep = arms["buried"]
        if rep.get("connectors_cut") or any(r.trim for r in runs) or \
                any(t > columns._ON_TOP_MAX_MM for t in _on_top(runs)):
            continue
        assert _key(arms["edge"][0]) == _key(runs)
        assert not arms["edge"][1].get("edge_walk_reordered")
        kept += 1
    assert kept >= 3


def test_no_hop_left_on_finished_satin(sewn):
    for key, arms in sewn.items():
        tops = _on_top(arms["edge"][0])
        assert max(tops, default=0.0) <= columns._ON_TOP_MAX_MM + 0.05, (key, tops)


def test_the_n_and_the_a_need_no_cut(sewn):
    # connectors_buried cut the N's two hops (its diagonal sewn down to the
    # foot, then back across it) and the A's one; the walk the other way
    # round buries all three
    for key in ("1", "4"):
        assert sewn[key]["buried"][1].get("connectors_cut", 0) >= 1, key
        runs, rep = sewn[key]["edge"]
        assert rep.get("connectors_cut", 0) == 0, key
        assert rep.get("edge_walk_reordered") == 1, key
        assert sum(r.trim for r in runs) < sum(r.trim for r in sewn[key]["buried"][0]), key


def test_never_more_trims_than_off_or_buried(sewn):
    def trims(runs):
        return sum(bool(r.trim) for r in runs)
    edge = sum(trims(a["edge"][0]) for a in sewn.values())
    assert edge <= sum(trims(a["off"][0]) for a in sewn.values())
    assert edge < sum(trims(a["buried"][0]) for a in sewn.values())
    for arms in sewn.values():
        assert trims(arms["edge"][0]) <= trims(arms["buried"][0])


def test_the_a_sews_its_crossbar_before_its_legs(sewn):
    # the pro's A: crossbar first, then the legs over its ends
    runs = sewn["1"]["edge"][0]
    sat = [r for r in runs if r.kind == stitches.SATIN]
    bar_y = [p[1] for p in sat[0].points]
    legs_y = [p[1] for r in sat[1:] for p in r.points]
    # the first satin is the short bar low in the letter: all its stitches
    # below the letter's mid-height, the legs reach the top
    poly, _kw = _letters()["1"]
    mid = (poly.bounds[1] + poly.bounds[3]) / 2
    assert min(bar_y) > mid
    assert min(legs_y) < mid


def test_all_euler_trails():
    # a path a-b-c: two trails (from each end), each span once
    visits = [(0, 0, 1), (1, 1, 2)]
    assert columns._all_euler_trails(visits, 0, 10) == [[(0, 0, 1), (1, 1, 2)]]
    # the same span doubled: out and back is one trail, not two
    visits = [(0, 0, 1), (0, 0, 1)]
    assert columns._all_euler_trails(visits, 0, 10) == [[(0, 0, 1), (0, 1, 0)]]
    # a triangle from node 0: both directions round
    visits = [(0, 0, 1), (1, 1, 2), (2, 2, 0)]
    assert len(columns._all_euler_trails(visits, 0, 10)) == 2
    assert len(columns._all_euler_trails(visits, 0, 1)) == 1
