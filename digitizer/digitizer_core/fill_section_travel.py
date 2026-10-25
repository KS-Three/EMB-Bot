"""Sew a fill's sections without cutting between them, travelling under the
rows still to come (`cfg.extra["fill_section_travel"]`, built OFF 2026-10-25).

**Why.** Over five paired hat jobs (Fremont, Becker large, MFab, Precision
Drone, Gaulke) we cut 108 times INSIDE one sewn piece where the professional
cuts 25, and the largest class he never has is the travel between two
sections of ONE fill: 35 cuts on main (Fremont's field 23, Drone's fields
12), 0 on his side (`docs/in-piece-cuts-2026-10-25.md`, read with
`tools/sequence_pro.py`). Two different things make them:

- **Underlay** (Fremont 10): `edge_lattice` walks every hole's ring as its
  own path, and the hop between two rings across a letter has no route
  `travel_path` can find (straight crosses the hole; one inset ring does not
  join both ends). Any route inside the shape is under the fill that follows.
- **Fill** (Fremont 13, Drone 12): the needle finishes a section walled in by
  fill already sewn and by holes, so no route to the next section is hidden.
  On Fremont's horizontal rows the letter band splits into ~20 sections
  between letters; nearest-first sews the bands above and below FIRST, and
  each letter gap is then an island. That is the ORDER, not the router: of
  54 lifted fill bridges, a geodesic over unsewn ground exists for 4.

**What this does, only where stage 6 would otherwise lift the needle:**

1. `bridge`: a bent route between two runs of one shape where `travel_path`
   found none (or `fill_bridge_cut` lifted the one it found). A FILL route
   must lie under the footprint of the paths still to sew -- the next
   section's rows -- and off the fill already laid, as `travel_path`'s own
   covered routing requires; an UNDERLAY route anywhere inside the shape
   inset by `TRAVEL_INSET_MM`, which the fill sews over. Proposed on a raster
   (`MCP_Geometric`, as `stage7_sequence._bury_route` does) and decided
   exactly: every leg is tested against the shape and the allowed ground, so
   the raster can lose a route and never pass a bad one. `travel_path`'s own
   length budget, no new constant.
2. `plan`: the section ORDER the pro would sew: sections that touch few
   unsewn sections first (the gaps between letters), the ones that touch
   many last (the bands above and below, which are the corridors the travel
   runs under meanwhile), each entered at whichever end the needle reaches
   under unsewn ground and left at an end that still touches unsewn ground.
   The planner reasons on a raster; the result is priced with `_score` (the
   same scorer, with the routes `bridge` adds) against the incoming order
   and kept only if cheaper, and the last path is pinned, so the shape exits
   where it did and no other shape moves -- `_reorder_for_fewer_cuts`'s
   contract.

Chaining territory: ROADMAP gate 3 applies, the flag stays OFF. It adds no
thread anywhere the fill does not sew over afterwards, by construction; the
measured exposure is in the doc. Read only inside `plan_stitches`
(`enabled`), so a direct `stitch_shape` call outside it is the engine as it
was.
"""
from __future__ import annotations

import contextlib
import contextvars
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, box

from . import machine

KEY = "fill_section_travel"

_ON: contextvars.ContextVar[bool] = contextvars.ContextVar(KEY, default=False)

# The raster a route is PROPOSED on. Every leg is re-tested exactly, so a
# coarser grid can lose a route but never pass a bad one (the same contract
# as `stage7_sequence._BURY_PX_PER_MM`); 10 px/mm resolves a gap between two
# letters a millimetre wide.
_ROUTE_PX_PER_MM = 10.0
# How far (pixels) and how many pixels deep `hidden_route` looks for the
# first pixel a bridge end can step onto: half a millimetre, nearest first.
# Search bounds only; the leg itself is tested exactly.
_DOCK_PX = 5
_DOCK_TRIES = 24
# The raster the section ORDER is planned on. It only chooses an order, which
# `_score` then prices exactly against the incoming one; 5 px/mm keeps a
# 100 x 60 mm field at 0.15 Mpx for one geodesic map per section.
_PLAN_PX_PER_MM = 5.0
# A work cap, not a quality knob: past this many sections the planner leaves
# the incoming order alone (one geodesic map per section).
_PLAN_MAX_PATHS = 400
# How many of a step's best candidates get the one-step lookahead (one more
# geodesic map each). A work cap.
_LOOKAHEAD = 6


# One shape's bridges and inset, memoized while `stitch_shape` sews it: the
# planner prices an order, then `emit` sews the winner and asks the same
# questions again. Keyed on geometry (each path still to sew by its two ends
# and length), never on object identity, and only ever holding ONE shape:
# `stitch_shape` calls `reset` as it starts and as it returns.
_MEMO: dict = {}


def reset() -> None:
    _MEMO.clear()


@contextlib.contextmanager
def enabled(cfg):
    """Turn the flag on for the stitching inside the block when `cfg` asks."""
    token = _ON.set(bool((getattr(cfg, "extra", None) or {}).get(KEY)))
    try:
        yield
    finally:
        _ON.reset(token)


def active() -> bool:
    return _ON.get()


# ----------------------------------------------------------------- raster ----

def _fill_mask(geom, x0: float, y0: float, ppm: float, shape: tuple[int, int]) -> np.ndarray:
    import cv2
    m = np.zeros(shape, np.uint8)
    for pg in getattr(geom, "geoms", [geom]):
        if pg.is_empty or pg.geom_type != "Polygon":
            continue
        cv2.fillPoly(m, [np.round((np.asarray(pg.exterior.coords)[:, :2] - (x0, y0)) * ppm)
                         .astype(np.int32)], 1)
        for h in pg.interiors:
            cv2.fillPoly(m, [np.round((np.asarray(h.coords)[:, :2] - (x0, y0)) * ppm)
                             .astype(np.int32)], 0)
    return m


def _px(p, x0: float, y0: float, ppm: float) -> tuple[int, int]:
    """(row, col) of a point."""
    return int(round((p[1] - y0) * ppm)), int(round((p[0] - x0) * ppm))


# ------------------------------------------------------------------ route ----

def _budget(a, b) -> float:
    from . import stage6_fill as s6
    return max(s6._TRAVEL_DETOUR_FLOOR_MM, math.dist(a, b) * s6._TRAVEL_DETOUR_FACTOR)


def hidden_route(ground, cover, a, b, budget: float, sewn=None, on_sewn_mm: float = 0.0):
    """Polyline a -> b inside `ground` (and `cover`), at most `budget` long and
    with no more than `on_sewn_mm` of it over `sewn`, or None."""
    import cv2
    from skimage.graph import MCP_Geometric
    from . import stage6_fill as s6
    ppm = _ROUTE_PX_PER_MM
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    r = budget / 2.0 + 1.0
    win = ground.intersection(box(mx - r, my - r, mx + r, my + r))
    if win.is_empty:
        return None
    # The raster spans the window's ground, not the whole budget square.
    bx0, by0, bx1, by1 = win.bounds
    x0, y0 = bx0 - 1.0, by0 - 1.0
    shape = (int(math.ceil((by1 - y0 + 1.0) * ppm)) + 1, int(math.ceil((bx1 - x0 + 1.0) * ppm)) + 1)
    m = _fill_mask(win, x0, y0, ppm, shape)
    # One pixel in from the edge, so a leg between two pixel centres stays
    # inside what the exact test below accepts.
    m = cv2.erode(m, np.ones((3, 3), np.uint8))

    def dock(p):
        """The nearest pixel inside the eroded ground that `p` reaches by a
        straight leg the exact test accepts. The ends of a bridge sit ON the
        shape's edge (a column ends there), so their own pixel is often out."""
        r0, c0 = _px(p, x0, y0, ppm)
        k = _DOCK_PX
        ys, xs = np.nonzero(m[max(0, r0 - k):r0 + k + 1, max(0, c0 - k):c0 + k + 1])
        ys, xs = ys + max(0, r0 - k), xs + max(0, c0 - k)
        for i in np.argsort((ys - r0) ** 2 + (xs - c0) ** 2)[:_DOCK_TRIES]:
            q = (x0 + xs[i] / ppm, y0 + ys[i] / ppm)
            leg = LineString([p, q])
            if ground.covers(leg) and cover.covers(leg):
                return int(ys[i]), int(xs[i])
        return None

    if not all(0 <= v < hi for p in (a, b) for v, hi in zip(_px(p, x0, y0, ppm), shape)):
        return None
    ia, ib = dock(a), dock(b)
    if ia is None or ib is None:
        return None
    mcp = MCP_Geometric(np.where(m > 0, 1.0, np.inf))
    costs, _ = mcp.find_costs([ia], [ib])
    if not np.isfinite(costs[ib]) or costs[ib] / ppm > budget:
        return None
    line = [(x0 + c / ppm, y0 + rr / ppm) for rr, c in mcp.traceback(ib)]
    for tol in (2.0 / ppm, 1.0 / ppm, 0.5 / ppm, 0.0):
        mid = list(LineString(line).simplify(tol).coords) if tol and len(line) > 1 else line
        route = [tuple(a)] + [tuple(p) for p in mid] + [tuple(b)]
        route = [p for i, p in enumerate(route) if i == 0 or p != route[i - 1]]
        ln = LineString(route)
        if ln.length > budget or not ground.covers(ln) or not cover.covers(ln):
            continue
        if sewn is not None and s6._exposed_mm(route, sewn) > on_sewn_mm:
            continue
        return route
    return None


def _ends(cover, a, b):
    from . import stage6_fill as s6
    t = s6._EXPOSED_TOLERANCE_MM
    return cover.intersection(Point(a).buffer(t).union(Point(b).buffer(t)))


def bridge(poly, slack, a, b, kind: str, *, todo=None, row_mm: float | None = None,
           sewn=None):
    """`travel_path`'s return shape (a excluded, b included, at travel pitch)
    for a hop it could not route, or None.

    FILL: under `todo`, the paths not sewn yet (the one `b` starts included),
    each as the footprint `_footprint` gives it. UNDERLAY: inside the shape
    inset by `TRAVEL_INSET_MM`. Anything else: None."""
    from . import stitches
    if math.dist(a, b) < machine.TINY_STITCH_MM:
        return None
    key = ("bridge", kind, tuple(a), tuple(b),
           tuple((tuple(p[0]), tuple(p[-1]), len(p)) for p in todo) if todo else ())
    if key not in _MEMO:
        _MEMO[key] = _bridge(poly, slack, a, b, kind, todo, row_mm, sewn)
    hit = _MEMO[key]
    return None if hit is None else list(hit)


def _bridge(poly, slack, a, b, kind, todo, row_mm, sewn):
    from . import stage6_fill as s6
    from . import stitches
    budget = _budget(a, b)
    if kind == stitches.FILL:
        if not todo or row_mm is None:
            return None
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        half = budget / 2.0 + 1.0
        win = box(mx - half, my - half, mx + half, my + half)
        feet = [s6._footprint(p, row_mm) for p in todo if len(p) > 1
                and LineString(p).intersects(win)]
        if not feet:
            return None
        ground = slack.intersection(shapely.union_all(feet)).union(_ends(slack, a, b))
    elif kind == stitches.UNDERLAY:
        ik = ("inner", poly.wkb)
        if ik not in _MEMO:
            _MEMO[ik] = poly.buffer(-machine.TRAVEL_INSET_MM)
        inner = _MEMO[ik]
        ground = (slack.intersection(inner) if not inner.is_empty else slack).union(
            _ends(slack, a, b))
    else:
        return None
    # A bridge here replaces a lift (no thread at all) or a route that
    # shows, so it may lie on finished fill only where it must: stepping off
    # the column it leaves, inside that column's own footprint, which
    # `_footprint` draws a row wide each side of the row the needle is on.
    route = hidden_route(ground, slack, a, b, budget,
                         sewn if kind == stitches.FILL else None,
                         on_sewn_mm=2.0 * row_mm if row_mm else 0.0)
    if route is None:
        return None
    out: list[tuple[float, float]] = []
    cur = route[0]
    for p in route[1:]:
        out.extend(s6._densify(cur, p, machine.TRAVEL_STITCH_MM))
        cur = p
    return out


# ------------------------------------------------------------------- plan ----

def _articulation(nodes: set, touch: dict) -> set:
    """The sections among `nodes` whose removal disconnects the others (the
    graph's articulation points, Tarjan's low-link, iterative)."""
    disc: dict = {}
    low: dict = {}
    out: set = set()
    t = 0
    for root in sorted(nodes):
        if root in disc:
            continue
        disc[root] = low[root] = t
        t += 1
        kids = 0
        stack = [(root, None, iter(sorted(touch[root] & nodes)))]
        while stack:
            u, parent, it = stack[-1]
            v = next(it, None)
            if v is None:
                stack.pop()
                if parent is not None:
                    low[parent] = min(low[parent], low[u])
                    if parent != root and low[u] >= disc[parent]:
                        out.add(parent)
                continue
            if v == parent:
                continue
            if v in disc:
                low[u] = min(low[u], disc[v])
                continue
            disc[v] = low[v] = t
            t += 1
            if u == root:
                kids += 1
            stack.append((v, u, iter(sorted(touch[v] & nodes))))
        if kids > 1:
            out.add(root)
    return out


def plan(paths, poly, entry, row_mm: float, prefer: str = "whole"):
    """A section order that travels under unsewn ground (see the module
    docstring), the last path pinned; or `paths` itself when there is
    nothing to plan. Raster reasoning only -- the caller prices it.

    Each step takes a section the needle reaches hidden, leaving by an end
    from which another is still reachable (one step of lookahead), and
    among those `prefer` decides: "whole" -- one whose sewing leaves the
    rest connected (not an articulation point of the sections still to
    sew) before the nearest; "near" -- the nearest. Neither wins
    everywhere (Fremont's field and Drone's fields disagree), so
    `stage6_fill._plan_sections` prices both."""
    import cv2
    from skimage.graph import MCP_Geometric
    from . import stage6_fill as s6
    if len(paths) < 3 or len(paths) > _PLAN_MAX_PATHS or entry is None:
        return paths
    if any(len(p) < 2 for p in paths):
        return paths
    ppm = _PLAN_PX_PER_MM
    x0, y0, x1, y1 = poly.bounds
    x0, y0 = x0 - 2.0, y0 - 2.0
    shape = (int(math.ceil((y1 - y0 + 2.0) * ppm)) + 1, int(math.ceil((x1 - x0 + 2.0) * ppm)) + 1)
    inside = _fill_mask(poly, x0, y0, ppm, shape)
    lw = max(1, int(round(2 * row_mm * ppm)))
    feet = []
    for p in paths:
        m = np.zeros(shape, np.uint8)
        pts = np.round((np.asarray(p) - (x0, y0)) * ppm).astype(np.int32)
        cv2.polylines(m, [pts], False, 1, lw)
        feet.append(m.astype(bool))
    # Which sections touch which: footprints one pixel apart (boxes first).
    k3 = np.ones((3, 3), np.uint8)
    grown = [cv2.dilate(f.astype(np.uint8), k3).astype(bool) for f in feet]
    boxes = []
    for p in paths:
        q = np.asarray(p)
        boxes.append((*q.min(axis=0), *q.max(axis=0)))
    pinned = len(paths) - 1
    free = list(range(pinned))
    near = 2.0 * row_mm + 2.0 / ppm
    touch: dict = {i: set() for i in range(len(paths))}
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            bi, bj = boxes[i], boxes[j]
            if (bi[0] > bj[2] + near or bj[0] > bi[2] + near
                    or bi[1] > bj[3] + near or bj[1] > bi[3] + near):
                continue
            if (grown[i] & feet[j]).any():
                touch[i].add(j)
                touch[j].add(i)
    # How many footprints still to sew cover each pixel (the pinned last path
    # among them): a pixel is ground while its count is above zero.
    cnt = np.zeros(shape, np.int16)
    for f in feet:
        cnt += f
    tol = int(math.ceil(s6._EXPOSED_TOLERANCE_MM * ppm))

    def at(p):
        r, c = _px(p, x0, y0, ppm)
        return min(max(r, 0), shape[0] - 1), min(max(c, 0), shape[1] - 1)

    # Past this a hidden route costs more travel stitches than the cut it
    # saves, at `_score`'s own rate -- so the planner never looks further.
    worth = s6._TRIM_STITCH_EQUIVALENT * machine.TRAVEL_STITCH_MM

    def reach_from(here, without=None):
        """Geodesic distance (px) from `here` over `bridge`'s own ground:
        the rows still to sew (the pinned last path among them), and a
        travel stitch round the needle -- inf past `worth`, which bounds the
        map to a window round the needle. Not clipped to `inside` as a
        whole: a section's ends sit ON the shape's edge, where its own pixel
        can fall outside the raster."""
        hr, hc = at(here)
        w = int(math.ceil(worth * ppm))
        r0, r1 = max(0, hr - w), min(shape[0], hr + w + 1)
        c0, c1 = max(0, hc - w), min(shape[1], hc + w + 1)
        ground = cnt[r0:r1, c0:c1] > (0 if without is None else feet[without][r0:r1, c0:c1])
        disc = np.zeros(ground.shape, np.uint8)
        cv2.circle(disc, (hc - c0, hr - r0), tol, 1, -1)
        allowed = ground | ((disc > 0) & (inside[r0:r1, c0:c1] > 0))
        dist = np.full(shape, np.inf)
        dist[r0:r1, c0:c1] = MCP_Geometric(np.where(allowed, 1.0, np.inf)).find_costs(
            [(hr - r0, hc - c0)])[0]
        return dist

    def ends(j, flip):
        return (paths[j][-1], paths[j][0]) if flip else (paths[j][0], paths[j][-1])

    def reached(dist, here, head) -> tuple[bool, float]:
        g = dist[at(head)] / ppm
        return math.isfinite(g) and g <= min(_budget(here, head), worth), g

    remaining = set(free)
    order: list[tuple[int, bool]] = []
    cur = entry
    while remaining:
        dist = reach_from(cur)
        # A section whose sewing would split what is left into parts the
        # needle cannot travel between hidden: sewn last that it can be.
        splits = _articulation(remaining | {pinned}, touch)
        cands = []
        for j in remaining:
            for flip in (False, True):
                head, _tail = ends(j, flip)
                ok, g = reached(dist, cur, head)
                g = g if ok else math.dist(cur, head)
                cands.append((not ok, *((j in splits, g) if prefer == "whole" else (g, j in splits)),
                              j, flip))
        cands.sort()
        # One step ahead, for the few best: leaving by this section's tail,
        # is any section still to sew reachable hidden? Else the next move
        # is a cut whatever it is.
        scored = []
        for miss, k1, k2, j, flip in cands[:_LOOKAHEAD]:
            tail = ends(j, flip)[1]
            left = remaining - {j}
            d2 = reach_from(tail, without=j)
            if left:
                nxt = any(reached(d2, tail, ends(k, f)[0])[0] for k in left for f in (False, True))
            else:
                nxt = reached(d2, tail, paths[pinned][0])[0]
            scored.append((miss, not nxt, k1, k2, j, flip))
        j, flip = min(scored)[4:]
        order.append((j, flip))
        remaining.discard(j)
        cnt -= feet[j]
        cur = ends(j, flip)[1]
    out = [paths[j][::-1] if flip else paths[j] for j, flip in order]
    out.append(paths[pinned])
    return out
