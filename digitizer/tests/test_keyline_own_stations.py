"""`keyline_bean._own_stations`: the same answer as buffering the union.

`keyline_bean_runs` asked, for each loop, which of its stations lie further
than half the keyline's width from every line already sewn, by buffering the
UNION of the sewn lines again for every loop: quadratic. The FTC seal at 90
mm spent 429 of 534 planning seconds there (2026-11-17). `_own_stations`
buffers each line once. The reach of a union is the union of the reaches, so
the answers must agree; this pins that.
"""
import random

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from digitizer_core.keyline_bean import _own_stations

HALF = 0.2


def _old(pts, sewn, half):
    near = unary_union(sewn).buffer(half)
    return [not near.contains(Point(p)) for p in pts]


def _random_loops(n, seed):
    rnd = random.Random(seed)
    loops = []
    for _ in range(n):
        cx, cy, r = rnd.uniform(0, 30), rnd.uniform(0, 30), rnd.uniform(0.5, 4.0)
        loops.append(LineString([(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r),
                                 (cx - r, cy + r), (cx - r, cy - r)]))
    return loops


def test_agrees_with_the_union_buffer_on_random_loops():
    loops = _random_loops(60, 7)
    rnd = random.Random(11)
    pts = [(rnd.uniform(-2, 32), rnd.uniform(-2, 32)) for _ in range(400)]
    # stations ON the sewn lines and just off them, where the answer turns
    for ln in loops[:20]:
        x, y = ln.coords[0]
        pts += [(x, y), (x + 0.19, y), (x + 0.21, y), (x - 0.5, y - 0.5)]
    cache: list = []
    for k in range(1, len(loops) + 1, 7):
        assert _own_stations(pts, loops[:k], cache, HALF) == _old(pts, loops[:k], HALF)


def test_the_cache_grows_one_entry_per_sewn_line_and_no_more():
    loops = _random_loops(5, 3)
    cache: list = []
    _own_stations([(0.0, 0.0)], loops[:2], cache, HALF)
    assert len(cache) == 2
    _own_stations([(0.0, 0.0)], loops, cache, HALF)
    assert len(cache) == 5
    _own_stations([(0.0, 0.0)], loops, cache, HALF)
    assert len(cache) == 5


def test_nothing_sewn_every_station_is_its_own():
    assert _own_stations([(0.0, 0.0), (1.0, 1.0)], [], [], HALF) == [True, True]


def test_no_stations():
    assert _own_stations([], _random_loops(2, 1), [], HALF) == []
