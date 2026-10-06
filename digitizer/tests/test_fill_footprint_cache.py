"""`stage6_fill._footprint` is a cache around one shapely expression; it must
return exactly what the expression returns, and reuse it."""
from shapely.geometry import LineString

from digitizer_core import stage6_fill as F


def test_footprint_equals_the_uncached_expression_and_is_reused():
    F._FOOTPRINT_CACHE.clear()
    path = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (0.0, 4.0)]
    want = LineString(path).simplify(0.075).buffer(0.15)
    got = F._footprint(path, 0.15)
    assert got.equals_exact(want, 0)
    assert F._footprint(list(path), 0.15) is got


def test_a_reversed_path_is_its_own_entry():
    F._FOOTPRINT_CACHE.clear()
    path = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0)]
    a = F._footprint(path, 0.15)
    b = F._footprint(path[::-1], 0.15)
    assert a is not b
    assert len(F._FOOTPRINT_CACHE) == 2


def test_the_cache_is_bounded():
    F._FOOTPRINT_CACHE.clear()
    for i in range(F._FOOTPRINT_MAX + 10):
        F._footprint([(0.0, 0.0), (1.0 + i, 0.0)], 0.15)
    assert len(F._FOOTPRINT_CACHE) == F._FOOTPRINT_MAX
