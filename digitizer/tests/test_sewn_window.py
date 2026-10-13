"""`_Sewn` and `travel_path`'s window: faster, and asking the same question.

Covered routing used to keep the fill sewn so far as ONE geometry and ask
every bridge's questions of all of it. On owl_kent that was most of a cold
digitize (`_reorder_for_cover` 48 s of 145 measured 2026-10-13). `_Sewn` keeps
the footprints apart: a line is measured against the footprints whose boxes
meet it, and the unsewn ground is built only in the window a route within
`travel_path`'s length budget can reach. These tests hold both to the
single-geometry answer -- on lengths, on area, and on the routes themselves.
"""
import random

import pytest
import shapely
from shapely.geometry import LineString, Polygon

from digitizer_core import stage6_fill as F

ROW = 0.4
_HOLED = Polygon([(0, 0), (40, 0), (40, 24), (0, 24)]).difference(
    Polygon([(14, 6), (26, 6), (26, 18), (14, 18)]))


@pytest.fixture(autouse=True)
def _clean_memo():
    F.clear_fill_reorder_memo()
    yield
    F.clear_fill_reorder_memo()


def _paths():
    return [p for p in F._fill_paths(_HOLED, 90.0, ROW, 3.0, 3) if len(p) > 1]


def _both(paths):
    """The fill sewn after each path, as a `_Sewn` and as one union."""
    sewn = whole = None
    for p in paths:
        fp = F._footprint(p, ROW)
        sewn = F._sewn_add(sewn, fp)
        whole = fp if whole is None else whole.union(fp)
        yield sewn, whole


def test_on_line_is_the_length_on_the_union():
    """Including lines whose box meets a footprint the line itself misses --
    the intersection is then EMPTY, which must count as nothing (it once read
    as NaN and passed an exposed haul as hidden)."""
    paths = _paths()
    sewn, whole = list(_both(paths[: len(paths) // 2]))[-1]
    rng = random.Random(7)
    for _ in range(200):
        a, b = rng.choice(paths)[0], rng.choice(paths)[-1]
        line = LineString([a, b, (rng.uniform(0, 40), rng.uniform(0, 24))])
        assert sewn.on_line(line) == pytest.approx(line.intersection(whole).length,
                                                   abs=1e-9)


def test_clipped_is_the_union_inside_the_box():
    paths = _paths()
    sewn, whole = list(_both(paths[: len(paths) // 2]))[-1]   # one object, grown
    for x0, y0 in [(0.0, 0.0), (10.0, 4.0), (30.0, 15.0)]:
        win = shapely.box(x0, y0, x0 + 12.0, y0 + 9.0)
        got = sewn.clipped(x0, y0, x0 + 12.0, y0 + 9.0)
        assert got.symmetric_difference(whole.intersection(win)).area < 1e-9


def test_windowed_routes_are_the_whole_shape_routes():
    """Every bridge of a walk over the holed plate, routed with `_Sewn` and
    with the single union, in every order the comb walk has: same route."""
    paths = _paths()
    ring = F._inset_ring(_HOLED, F.machine.TRAVEL_INSET_MM)
    slack = _HOLED.buffer(0.01)
    rng = random.Random(3)
    exposed = 0
    for (sewn, whole), nxt in zip(_both(paths), paths[1:]):
        for b in (nxt[0], rng.choice(paths)[0]):
            a = paths[paths.index(nxt) - 1][-1]
            want = F.travel_path(_HOLED, ring, a, b, slack, whole, {})
            got = F.travel_path(_HOLED, ring, a, b, slack, sewn, {})
            assert got == want
            exposed += F._exposed_mm([a, b], whole) > F._EXPOSED_TOLERANCE_MM
    assert exposed, "fixture must exercise the covered branch"
