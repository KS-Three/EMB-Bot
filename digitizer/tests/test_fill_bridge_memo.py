"""The covered-bridge memo (`stage6_fill._BridgeMemo`, 2026-11-11) must show
up in the clock and nowhere else.

One fill shape's order is walked with the covered routing by both reorders,
by seam pricing and then by `emit`; the memo hands a walk the bridge an
earlier walk computed from the same state. Its safety is that `travel_path`
is a pure function of that state, so the tests compare against the same
code with the memo switched off -- every stitch, not a stored hash.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import machine
from digitizer_core import stage6_fill as F
from digitizer_core.stage6_fill import (cut_exposed_scope, seam_order_scope, seam_priced_scope,
                                        stitch_shape)

ROW = machine.FILL_ROW_MM_BEFORE_2026_09_03       # 0.4: enough columns, quick


def _plates():
    rng = np.random.default_rng(1111)
    out = []
    for _ in range(6):
        w, h = rng.uniform(25, 45), rng.uniform(18, 30)
        holes = [Point(rng.uniform(4, w - 4), rng.uniform(4, h - 4)).buffer(rng.uniform(1.0, 3.5), 5)
                 for _ in range(int(rng.integers(2, 7)))]
        slots = [affinity.rotate(box(x, 3, x + 1.2, h - 6), rng.uniform(-20, 20))
                 for x in rng.uniform(5, w - 5, int(rng.integers(0, 3)))]
        poly = box(0, 0, w, h).difference(unary_union(holes + slots))
        if poly.geom_type == "Polygon":
            out.append(poly)
    # a comb: every tooth is a column the walk leaves and comes back past
    out.append(unary_union([box(0, 0, 40, 4)] + [box(4 * i, 0, 4 * i + 2.4, 22) for i in range(10)]))
    return out


PLATES = _plates()


@pytest.fixture(autouse=True)
def _clean():
    F.clear_fill_reorder_memo()
    yield
    F.clear_fill_reorder_memo()


def _sew(poly, angle):
    F.clear_fill_reorder_memo()             # the reorder memo would skip the pricing walks
    with seam_order_scope(True), seam_priced_scope(True), cut_exposed_scope(True):
        runs, _report = stitch_shape(poly, "S", angle_deg=angle, row_mm=ROW, stitch_mm=3.0,
                                     underlay_style="none", trim_at_mm=3.0,
                                     start_near=(0.0, 0.0), under_cover=True, cut_bridges=True)
    return [(r.kind, r.jump, r.trim, tuple(r.points)) for r in runs]


@pytest.mark.parametrize("angle", [0.0, 37.0, None])
def test_every_stitch_is_the_same_with_and_without_the_memo(monkeypatch, angle):
    before = dict(F._bridge_memo_stats)
    with_memo = [_sew(p, angle) for p in PLATES]
    hits = F._bridge_memo_stats["hit"] - before["hit"]
    monkeypatch.setattr(F, "_BRIDGE_MEMO_MAX", 0)          # learns nothing: every ask computes
    before = dict(F._bridge_memo_stats)
    without = [_sew(p, angle) for p in PLATES]
    assert F._bridge_memo_stats["hit"] == before["hit"]
    assert with_memo == without
    assert hits > 0, "the fixtures must exercise a hit, or this compares nothing"


def test_a_repeated_walk_is_all_hits_and_the_same_cost():
    poly = PLATES[0]
    ring = F._inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    paths = F._fill_paths(poly, 0.0, ROW, 3.0, machine.FILL_STAGGERS, (0.0, 0.0))
    assert len(paths) >= 4
    plain = F._order_cost(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
    memo = F._BridgeMemo()
    token = F._BRIDGE_MEMO.set(memo)
    try:
        first = F._order_cost(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
        asked = memo.misses
        assert memo.hits == 0 and asked > 0
        second = F._order_cost(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
        assert memo.misses == asked and memo.hits == asked
        # an order that differs from its second path on shares the first bridge only
        other = [paths[0]] + paths[:0:-1]
        F._order_cost(other, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
        assert memo.hits == asked + 1
    finally:
        F._BRIDGE_MEMO.reset(token)
    assert first == second == plain


def test_a_hit_puts_back_the_rings_the_call_left(monkeypatch):
    """`travel_path` leaves its rebuilt unsewn rings in the walk's `cache`
    for the next bridge to try first; a hit must leave the same list."""
    poly = PLATES[0]
    ring = F._inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    paths = F._fill_paths(poly, 0.0, ROW, 3.0, machine.FILL_STAGGERS, (0.0, 0.0))
    seen: list[list] = []
    real = F.travel_path

    def spy(poly, ring, a, b, slack=None, sewn=None, cache=None):
        out = real(poly, ring, a, b, slack, sewn, cache)
        seen.append((a, b, cache.get("unsewn_rings") if cache is not None else None))
        return out

    monkeypatch.setattr(F, "travel_path", spy)
    memo = F._BridgeMemo()
    token = F._BRIDGE_MEMO.set(memo)
    try:
        list(F._order_cost_walk(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW))
        computed = list(seen)
        assert any(rings is not None for _a, _b, rings in computed), "fixture never rebuilt rings"
        # replay by hand: every ask a hit, and the cache after each is the list the miss left
        chain, sewn, cache, cur = memo.start(poly, ring, slack), None, {}, (0.0, 0.0)
        k = 0
        for path in paths:
            _bridge, chain = memo.bridge(chain, poly, ring, cur, path[0], slack, sewn, cache)
            assert cache.get("unsewn_rings") is computed[k][2]
            k += 1
            if len(path) > 1:
                fp = F._footprint(path, ROW)
                sewn = F._sewn_add(sewn, fp)
                chain = memo.laid(chain, fp)
            cur = path[-1]
        assert len(seen) == len(computed)                  # nothing was recomputed
    finally:
        F._BRIDGE_MEMO.reset(token)


def test_outside_stitch_shape_there_is_no_memo():
    assert F._BRIDGE_MEMO.get() is None
    _sew(PLATES[0], 0.0)
    assert F._BRIDGE_MEMO.get() is None


def test_the_memo_stops_learning_at_its_cap(monkeypatch):
    monkeypatch.setattr(F, "_BRIDGE_MEMO_MAX", 3)
    poly = PLATES[0]
    ring = F._inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    paths = F._fill_paths(poly, 0.0, ROW, 3.0, machine.FILL_STAGGERS, (0.0, 0.0))
    memo = F._BridgeMemo()
    token = F._BRIDGE_MEMO.set(memo)
    try:
        a = F._order_cost(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
        b = F._order_cost(paths, poly, ring, slack, (0.0, 0.0), 3.0, ROW)
    finally:
        F._BRIDGE_MEMO.reset(token)
    assert len(memo.bridges) == 3 and a == b
