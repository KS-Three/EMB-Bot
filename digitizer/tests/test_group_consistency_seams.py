"""`group_consistency`'s pair loops: a Cancel lands inside them, they cost far
less than every pair, and they find the same groups (review 2026-11-14).

`like_lines` (`cfg.group_consistent_tier`) and `like_shapes` /
`shared_angles` (`cfg.group_consistent_fill_angle`), both ON by default
since 2026-11-14, tested every pair of shapes through shapely with no
`deadline.check`: 1,600 same-thread squares took 31.6 s in `like_lines` and
27.8 s in `like_shapes` on the shared laptop, a Cancel unheard throughout.
The old loops are kept below, verbatim, as the reference the new ones must
match group for group.
"""
from __future__ import annotations

import random
import statistics as st
import threading
import time

import pytest
from shapely.geometry import box

from digitizer_core import deadline
from digitizer_core import group_consistency as gc
from digitizer_core.lettering_thread import STRAY_HEIGHT_RATIO, STRAY_MAX_GAP_H, STRAY_MIN_OVERLAP
from digitizer_core.regions import Region
from digitizer_core.textcluster import MIN_CLUSTER_MEMBERS


def _region(sid, poly, thread):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0})


def _grid(n_side, thread=0, pitch=3.0, size=2.0):
    return [_region(f"s{i}_{j}", box(i * pitch, j * pitch, i * pitch + size, j * pitch + size), thread)
            for i in range(n_side) for j in range(n_side)]


# ---- the loops as they were (origin/main 66b11432), the reference -----------

def _old_line_mates(a, b) -> bool:
    x0, y0, x1, y1 = a.polygon.bounds
    u0, v0, u1, v1 = b.polygon.bounds
    h, k = y1 - y0, v1 - v0
    if h <= 0 or k <= 0 or min(h, k) / max(h, k) < STRAY_HEIGHT_RATIO:
        return False
    if min(y1, v1) - max(y0, v0) < STRAY_MIN_OVERLAP * min(h, k):
        return False
    return a.polygon.distance(b.polygon) <= STRAY_MAX_GAP_H * max(h, k)


def _old_adopt_stacked(regs, groups):
    grouped = {i for g in groups for i in g}
    free = [i for i in range(len(regs)) if i not in grouped]
    for x in free:
        for y in free:
            if y <= x or regs[x].thread_index != regs[y].thread_index:
                continue
            a, b = regs[x].polygon.bounds, regs[y].polygon.bounds
            if not gc._stacked(a, b):
                continue
            u = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
            for g in groups:
                if regs[g[0]].thread_index != regs[x].thread_index:
                    continue
                top = st.median(regs[i].polygon.bounds[1] for i in g)
                bot = st.median(regs[i].polygon.bounds[3] for i in g)
                H = bot - top
                if H <= 0 or abs(u[1] - top) > gc.STACK_BAND_TOL * H or abs(u[3] - bot) > gc.STACK_BAND_TOL * H:
                    continue
                gap = max(b[1] - a[3], a[1] - b[3])
                if gap > gc.STACK_GAP_MAX * H:
                    continue
                near = min(regs[i].polygon.distance(regs[k].polygon) for i in g for k in (x, y))
                if near > STRAY_MAX_GAP_H * H:
                    continue
                g.extend([x, y])
                break


def _components(n, pairs):
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in pairs:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    by: dict[int, list] = {}
    for i in range(n):
        by.setdefault(find(i), []).append(i)
    return [g for _k, g in sorted(by.items())]


def _old_like_lines(regions, min_members=MIN_CLUSTER_MEMBERS):
    regs = [r for r in regions if r.polygon is not None and not r.polygon.is_empty]
    pairs = [(i, j) for i in range(len(regs)) for j in range(i + 1, len(regs))
             if regs[i].thread_index == regs[j].thread_index and _old_line_mates(regs[i], regs[j])]
    groups = [g for g in _components(len(regs), pairs) if len(g) >= min_members]
    _old_adopt_stacked(regs, groups)
    return [[regs[i] for i in sorted(g)] for g in groups]


def _old_like_shapes(regions, min_members=2):
    regs = [r for r in regions if r.polygon is not None and not r.polygon.is_empty and r.polygon.area > 0]
    elong = [gc.rect_axis(r.polygon)[1] for r in regs]

    def ratio(a, b):
        lo, hi = min(a, b), max(a, b)
        return hi / lo if lo > 0 else float("inf")
    pairs = [(i, j) for i in range(len(regs)) for j in range(i + 1, len(regs))
             if regs[i].thread_index == regs[j].thread_index
             and ratio(regs[i].polygon.area, regs[j].polygon.area) <= gc.LIKE_AREA_RATIO
             and ratio(elong[i], elong[j]) <= gc.LIKE_ELONG_RATIO]
    return [[regs[i] for i in g] for g in _components(len(regs), pairs) if len(g) >= min_members]


def _ids(groups):
    return [[r.shape_id for r in g] for g in groups]


def _scatter(seed, n=160):
    """Words of letters, stacked glyph pieces, stray bars, in three threads."""
    rnd = random.Random(seed)
    out = []
    for k in range(n):
        t = rnd.randrange(3)
        if rnd.random() < 0.6:                     # a letter on one of a few lines
            line = rnd.randrange(6)
            x, h = rnd.uniform(0, 120), rnd.uniform(4.0, 6.0)
            y = line * 9.0 + rnd.uniform(-0.6, 0.6)
            out.append(_region(f"r{k}", box(x, y, x + rnd.uniform(1.0, 4.0), y + h), t))
        elif rnd.random() < 0.5:                   # a two-piece glyph: bar and dot
            line = rnd.randrange(6)
            x, y = rnd.uniform(0, 120), line * 9.0
            out.append(_region(f"r{k}a", box(x, y, x + 1.0, y + 3.6), t))
            out.append(_region(f"r{k}b", box(x, y + 4.2, x + 1.0, y + 5.2), t))
        else:                                      # anything, anywhere
            x, y = rnd.uniform(0, 120), rnd.uniform(0, 60)
            out.append(_region(f"r{k}", box(x, y, x + rnd.uniform(0.5, 8), y + rnd.uniform(0.5, 8)), t))
    rnd.shuffle(out)
    return out


@pytest.mark.parametrize("seed", range(6))
def test_the_same_groups_as_every_pair(seed):
    regs = _scatter(seed)
    assert _ids(gc.like_lines(regs)) == _ids(_old_like_lines(regs))
    assert _ids(gc.like_shapes(regs)) == _ids(_old_like_shapes(regs))


def test_the_same_groups_on_a_grid_and_a_word():
    regs = _grid(9) + [_region(f"w{i}", box(40 + 3.2 * i, 0, 42 + 3.2 * i, 5), 1) for i in range(8)]
    assert _ids(gc.like_lines(regs)) == _ids(_old_like_lines(regs))
    assert _ids(gc.like_shapes(regs)) == _ids(_old_like_shapes(regs))
    assert gc.like_lines(regs) and gc.like_shapes(regs)            # not vacuous


@pytest.mark.parametrize("call", [
    lambda regs: gc.like_lines(regs),
    lambda regs: gc.like_shapes(regs),
    lambda regs: gc.shared_angles(regs, lambda r: 30.0),
], ids=["like_lines", "like_shapes", "shared_angles"])
def test_a_cancel_lands_inside_the_pair_loops(call):
    regs = _grid(6)
    cancel = threading.Event()
    cancel.set()
    with deadline.scope(None, cancel=cancel):
        with pytest.raises(deadline.Cancelled):
            call(regs)
    assert call(regs) is not None                  # unarmed, it runs to the end


def test_many_like_shapes_cost_far_less_than_every_pair():
    # 1,600 squares, one thread: 59 s for the two before (shared laptop,
    # 2026-11-14), every pair through shapely. The bound is loose for CI.
    regs = _grid(40)
    t = time.perf_counter()
    lines = gc.like_lines(regs)
    shapes = gc.like_shapes(regs)
    secs = time.perf_counter() - t
    assert len(lines) == 40 and len(shapes) == 1
    assert secs < 8.0, f"{secs:.1f} s"
