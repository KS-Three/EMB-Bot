"""`tools.ring_route_share.ring_route_np` against `stage6_fill._ring_route`.

The numpy candidate did not land: on owl_kent it saves well under 1.5 s of
`_order_cost_walk` (PR body, `tools/ring_route_share.py`). This file pins
that it is EXACT, bit for bit, so whoever revisits it starts from a
rewrite known to sew the same stitches:

- real rings: 49 calls on 18 rings captured from owl_kent's stage 7
  (`testdata/owl_ring_routes.json.gz`), each also routed from and to its own
  vertices, from the ring's start, and with a == b, every way round;
- randomised rings: inset rings of random holed polygons, random ends;
- the traps: the `% total` wrap (the closing vertex's arc length is not
  `ring.length`), an offset tie between two DIFFERENT vertices (broken by x,
  then y, as `between.sort()` breaks it), repeated vertices, and gaps at
  exactly TINY_STITCH_MM.

"Exact" means the same number of points, each a tuple of Python floats with
the same bits (`float.hex`, so -0.0 is not 0.0).
"""
from __future__ import annotations

import gzip
import json
import math
import random
from pathlib import Path

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import machine
from digitizer_core import stage6_fill as F
from tools.ring_route_share import ring_route_np

FIXTURE = Path(__file__).resolve().parent.parent / "testdata" / "owl_ring_routes.json.gz"
WAYS = (None, "ahead", "back")


def _bits(route):
    for p in route:
        assert type(p) is tuple and len(p) == 2
        assert all(type(v) is float for v in p)
    return [(x.hex(), y.hex()) for x, y in route]


def _same(ring, a, b, way):
    want = F._ring_route(ring, a, b, way)
    got = ring_route_np(ring, a, b, way)
    assert _bits(got) == _bits(want), (a, b, way)
    return want


def _cum(ring):
    return F._ring_arc(ring)[1]


def _real():
    data = json.loads(gzip.open(FIXTURE, "rt").read())
    rings = [shapely.from_wkb(bytes.fromhex(h)) for h in data["rings"]]
    calls = [(rings[i], (float.fromhex(ax), float.fromhex(ay)),
              (float.fromhex(bx), float.fromhex(by)), way)
             for i, ax, ay, bx, by, way in data["calls"]]
    return rings, calls


# ------------------------------------------------------------------ real rings

def test_real_owl_calls():
    rings, calls = _real()
    assert len(rings) == 18 and len(calls) == 49
    for ring, a, b, way in calls:
        _same(ring, a, b, way)
        for other in WAYS:          # the owl's covered routing asks both ways only
            _same(ring, a, b, other)
    # the fixture holds the cases the rewrite has to get right
    assert any(_cum(r)[-1] != r.length for r in rings)          # the wrap
    # both ends projecting to one arc length: one way round is empty, the
    # other is the whole ring
    assert any(r.project(Point(a)) == r.project(Point(b)) for r, a, b, _ in calls)
    assert {w for *_, w in calls} == {"ahead", "back"}


def test_real_rings_from_their_own_vertices():
    """Ends exactly ON vertices: an offset of 0 (a's vertex) or of exactly
    `span` (b's) is excluded by `0 < offset < span`, so both versions must
    agree on the boundary; plus the ring's start, its closing vertex, and
    a == b, which makes one way empty and the other the whole ring."""
    rings, _ = _real()
    rng = random.Random(1107)
    for ring in rings:
        coords = list(ring.coords)
        n = len(coords)
        picks = {0, n - 1, n // 2} | {rng.randrange(n) for _ in range(4)}
        for i in sorted(picks):
            for j in sorted(picks):
                for way in WAYS:
                    _same(ring, coords[i], coords[j], way)


# ------------------------------------------------------------- randomised rings

def _random_poly(rng: random.Random) -> Polygon:
    cx, cy = rng.uniform(-40, 40), rng.uniform(-40, 40)
    k = rng.randrange(5, 40)
    shell = []
    for t in sorted(rng.uniform(0, 2 * math.pi) for _ in range(k)):
        r = rng.uniform(3, 15)
        shell.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    poly = Polygon(shell).buffer(0)
    if rng.random() < 0.5:
        hole = Point(cx + rng.uniform(-1, 1), cy + rng.uniform(-1, 1)).buffer(rng.uniform(0.5, 2.5))
        poly = poly.difference(hole)
    return poly


def test_randomised_rings():
    rng = random.Random(20261107)
    cases = 0
    for _ in range(60):
        poly = _random_poly(rng)
        if poly.is_empty:
            continue
        for ring in F._inset_ring(poly, machine.TRAVEL_INSET_MM):
            if ring.length == 0:
                continue
            x0, y0, x1, y1 = ring.bounds
            coords = list(ring.coords)
            for _ in range(6):
                a = (rng.uniform(x0, x1), rng.uniform(y0, y1))
                b = (rng.uniform(x0, x1), rng.uniform(y0, y1))
                if rng.random() < 0.3:
                    a = coords[rng.randrange(len(coords))]
                for way in WAYS:
                    _same(ring, a, b, way)
                    cases += 1
    assert cases > 500


# ------------------------------------------------------------------- the traps

def test_offset_tie_between_different_vertices_breaks_on_x_then_y():
    """Two vertices 1e-15 mm apart at an arc length near 100 mm add less than
    half an ulp, so they share one cumulative length and therefore one offset.
    `between.sort()` then orders them by their coordinates, and here that is
    NOT ring order: (100, -1e-15) sorts before (100, 0). The TINY floor keeps
    only the first, so the order decides which point is sewn."""
    ring = LineString([(0, 0), (100, 0), (100, -1e-15), (100, 50), (0, 50), (0, 0)])
    cum = _cum(ring)
    assert cum[1] == cum[2]                                      # the tie is real
    a, b = (-1.0, 10.0), (60.0, 51.0)
    route = _same(ring, a, b, "ahead")
    assert (100.0, -1e-15) in route and (100.0, 0.0) not in route
    # an order by offset alone (a stable argsort) would have kept the other one
    coords, _ = F._ring_arc(ring)
    ta = ring.project(Point(a))
    off = np.remainder(np.asarray(cum[1:]) - ta, ring.length)
    by_offset = [coords[i + 1] for i in np.argsort(off, kind="stable")]
    assert by_offset.index((100.0, 0.0)) < by_offset.index((100.0, -1e-15))
    # and walked the other way round, the tie still sorts by coordinates
    _same(ring, b, a, "back")
    for way in WAYS:
        _same(ring, a, b, way)
        _same(ring, b, a, way)


def test_repeated_vertices():
    ring = LineString([(0, 0), (5, 0), (5, 0), (5, 0), (5, 5), (5, 5), (0, 5), (0, 0)])
    for a in [(0, 0), (5, 0), (2.5, -1), (6, 2.5), (5, 5)]:
        for b in [(0, 5), (5, 0), (-1, 2.5), (5, 5)]:
            for way in WAYS:
                _same(ring, a, b, way)


@pytest.mark.parametrize("gap", [machine.TINY_STITCH_MM,
                                 math.nextafter(machine.TINY_STITCH_MM, 0.0),
                                 math.nextafter(machine.TINY_STITCH_MM, 1.0)])
def test_vertices_at_the_tiny_floor(gap):
    """Vertices spaced at exactly the floor and one ulp either side: the floor
    loop's `>=` sees the same distances in both versions."""
    xs = [i * gap for i in range(21)]
    ring = LineString([(x, 0.0) for x in xs] + [(xs[-1], 3.0), (0.0, 3.0), (0.0, 0.0)])
    for a, b in [((0.0, 0.0), (xs[-1], 0.0)), ((0.3, -0.2), (xs[-1], 2.0)),
                 ((xs[7], 0.0), (xs[13], 0.0)), ((xs[3], 0.1), (1.0, 3.2))]:
        for way in WAYS:
            _same(ring, a, b, way)
            _same(ring, b, a, way)


def test_wrap_past_the_rings_length():
    """A ring whose closing vertex's summed arc length differs from
    `ring.length` (GEOS sums it its own way): routes that start just behind
    the start vertex wrap through `% total` onto the closing vertex."""
    # Whether the two sums differ is platform arithmetic: on Windows seed 7
    # already does, on CI's Linux GEOS it sums seed 7 to the same float. Take
    # the first seed whose sums differ so the wrap edge is exercised where it
    # can occur; where no seed differs the edge cannot arise on that platform,
    # and the exactness checks below still run on the seed-7 ring.
    def _ellipse(seed):
        rng = random.Random(seed)
        pts = [(math.cos(t) * 13.37, math.sin(t) * 7.11)
               for t in sorted(rng.uniform(0, 2 * math.pi) for _ in range(200))]
        return LineString(pts + [pts[0]])
    ring = next((r for r in map(_ellipse, range(7, 207)) if _cum(r)[-1] != r.length),
                _ellipse(7))
    start = ring.coords[0]
    near = [ring.interpolate(d).coords[0] for d in (1e-9, ring.length - 1e-9, 0.25, ring.length - 0.25)]
    for a in [start] + near:
        for b in [start] + near + [(0.0, 0.0), (20.0, 0.0)]:
            for way in WAYS:
                _same(ring, a, b, way)
