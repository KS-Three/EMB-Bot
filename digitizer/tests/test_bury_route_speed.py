"""`_bury_route`'s cropped geodesic proposes the route the full grid did.

2026-11-07, a speed pass on `stage7_sequence.py` that had to leave every
stitch where it was. `_bury_route` rasters the later thread near a cut hop
onto the link-budget square (up to 1,449 px a side) and asks skimage's
`MCP_Geometric` for a geodesic through it; the thread fills a sliver of the
square, and `MCP_Geometric` pays its set-up per cell of the whole grid. It
now runs on the mask cropped to the bounding box of its finite cells.

skimage ignores infinite cells, so the crop drops nothing a path could
cross -- but "the same path" is a claim about a heap's tie order as much as
about geometry, so this holds the cropped search against the uncropped one
(`_full_grid_route` below is the pre-change body, kept verbatim) on random
later thread: same proposal, corner for corner, or None together. The
real-artwork proof is the PR's md5 table (owl, Becker, the gradient ramp).

Also here: the `coords` memo hands `_bury_route` the array it used to read
from GEOS itself, and `_owned_by_later`'s band cache answers the same
seams with and without it.
"""
from __future__ import annotations

import math
import random

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import machine
from digitizer_core.stage7_sequence import (_BURY_PX_PER_MM, _bury_route, _link_budget_mm,
                                            _owned_by_later)

HALF = machine.COVERAGE_THREAD_W_MM / 2.0


class _Everything:
    """A cover that passes every leg: the test compares PROPOSALS, so the
    exact per-leg test must not hide a different route behind a None."""

    def covers(self, _seg) -> bool:
        return True


def _full_grid_route(a, b, gap, k, cover, lines, idx, tree, half):
    """`_bury_route` as it stood before the crop (2026-11-06), verbatim."""
    import cv2
    from skimage.graph import MCP_Geometric
    budget = _link_budget_mm(gap)
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    r = budget / 2.0 + half
    near = [idx[j] for j in tree.query(Point(mx, my).buffer(r))]
    later = [lines[j] for j in near if j >= k]
    if not later:
        return None
    ppm = _BURY_PX_PER_MM
    x0, y0 = mx - r, my - r
    n = int(math.ceil(2 * r * ppm)) + 1
    mask = np.zeros((n, n), np.uint8)
    lw = max(1, int(round(2 * half * ppm)))
    for g in later:
        pts = np.round((np.asarray(g.coords) - (x0, y0)) * ppm).astype(np.int32)
        cv2.polylines(mask, [pts], False, 1, lw)
    er = int(math.ceil((half + half / 2.0) * ppm)) + 1
    mask = cv2.erode(mask, np.ones((2 * er + 1, 2 * er + 1), np.uint8))
    ia = (int(round((a[1] - y0) * ppm)), int(round((a[0] - x0) * ppm)))
    ib = (int(round((b[1] - y0) * ppm)), int(round((b[0] - x0) * ppm)))
    for (yy, xx) in (ia, ib):
        cv2.circle(mask, (xx, yy), int(machine.COVERAGE_THREAD_W_MM * ppm), 1, -1)
    if not (0 <= ia[0] < n and 0 <= ia[1] < n and 0 <= ib[0] < n and 0 <= ib[1] < n):
        return None
    mcp = MCP_Geometric(np.where(mask > 0, 1.0, np.inf))
    costs, _ = mcp.find_costs([ia], [ib])
    if not np.isfinite(costs[ib]) or costs[ib] / ppm > budget:
        return None
    path = mcp.traceback(ib)
    line = LineString([(x0 + c / ppm, y0 + rr / ppm) for rr, c in path]).simplify(half / 2.0)
    route = [a] + list(line.coords)[1:-1] + [b]
    if sum(math.dist(p, q) for p, q in zip(route, route[1:])) > budget:
        return None
    if not all(cover.covers(LineString([p, q])) for p, q in zip(route, route[1:])):
        return None
    return route


def _zigzag(rng, cx, cy, w, h, rows):
    """A satin-like band of `rows` rails across a w x h box at (cx, cy)."""
    pts = []
    for i in range(rows):
        y = cy - h / 2 + h * i / max(1, rows - 1)
        x = cx - w / 2 if i % 2 == 0 else cx + w / 2
        pts.append((x + rng.uniform(-0.05, 0.05), y))
    return pts


def _case(seed: int):
    """A cut hop of 2-8 mm and a few bands of later thread around it, some
    of them bridging the gap, so a good share of cases find a route."""
    rng = random.Random(seed)
    a = (rng.uniform(-3, 3), rng.uniform(-3, 3))
    ang = rng.uniform(0, 2 * math.pi)
    gap = rng.uniform(2.0, 8.0)
    b = (a[0] + gap * math.cos(ang), a[1] + gap * math.sin(ang))
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    pts_lists = []
    for _ in range(rng.randint(1, 5)):
        # one band straddling the hop's middle, dense enough to survive the
        # erosion in most seeds (rows 0.3 mm apart under a 0.4 mm thread) but
        # sometimes not; the rest scattered nearby, any density
        if not pts_lists or rng.random() < 0.3:
            cx, cy = mx + rng.uniform(-0.3, 0.3), my + rng.uniform(-0.3, 0.3)
            w = abs(b[0] - a[0]) + rng.uniform(1.5, 4.0)
            h = abs(b[1] - a[1]) + rng.uniform(1.5, 4.0)
            rows = int(h / 0.3) + 2 if rng.random() < 0.7 else rng.randint(4, 12)
        else:
            cx, cy = mx + rng.uniform(-6, 6), my + rng.uniform(-6, 6)
            w, h, rows = rng.uniform(1.5, 6.0), rng.uniform(1.5, 6.0), rng.randint(4, 24)
        pts_lists.append(_zigzag(rng, cx, cy, w, h, rows))
    # `k`: the hop index; every line is "later" (index >= k) except the first
    k = 1
    lines = [LineString(p) for p in pts_lists]
    idx = list(range(len(lines)))
    tree = shapely.STRtree(lines)
    return a, b, gap, k, lines, idx, tree


@pytest.mark.parametrize("seed", range(120))
def test_the_cropped_geodesic_is_the_full_grid_geodesic(seed):
    a, b, gap, k, lines, idx, tree = _case(seed)
    cover = _Everything()
    want = _full_grid_route(a, b, gap, k, cover, lines, idx, tree, HALF)
    got = _bury_route(a, b, gap, k, cover, lines, idx, tree, HALF)
    assert got == want


def test_enough_random_cases_find_a_route():
    """The comparison above is only a proof if routes are actually proposed:
    a suite of all-None cases would pass with any crop."""
    found = 0
    for seed in range(120):
        a, b, gap, k, lines, idx, tree = _case(seed)
        if _full_grid_route(a, b, gap, k, _Everything(), lines, idx, tree, HALF) is not None:
            found += 1
    assert found >= 20, found


def test_the_coords_memo_is_the_array_it_replaces():
    a, b, gap, k, lines, idx, tree = _case(7)
    arrays = {}

    def coords(j):
        if j not in arrays:
            arrays[j] = np.asarray(lines[j].coords)
        return arrays[j]

    cover = _Everything()
    assert (_bury_route(a, b, gap, k, cover, lines, idx, tree, HALF, coords)
            == _bury_route(a, b, gap, k, cover, lines, idx, tree, HALF))


def test_owned_by_later_answers_the_same_seams_with_its_band_cache():
    """Three abutting squares; the middle one's seams against both
    neighbours, asked twice with one cache (the second ask is the hit)."""
    sq = {f"s{i}": Polygon([(i, 0), (i + 1, 0), (i + 1, 1), (i, 1)]) for i in range(3)}
    later = {"s0": sq["s0"], "s2": sq["s2"]}
    cache: dict = {}
    plain = _owned_by_later(sq["s1"], later, 0.5, eps_mm=0.05)
    first = _owned_by_later(sq["s1"], later, 0.5, eps_mm=0.05, cache=cache)
    second = _owned_by_later(sq["s1"], later, 0.5, eps_mm=0.05, cache=cache)
    assert plain[1] == first[1] == second[1]
    assert len(plain[1]) == 2
    assert plain[0].equals_exact(first[0], 0.0) and plain[0].equals_exact(second[0], 0.0)
    assert len(cache) == 3, "one band per geometry object, visible and later alike"
