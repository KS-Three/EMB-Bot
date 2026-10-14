"""Small lettering sewn as ONE skeleton run (`cfg.small_lettering_skeleton`,
default OFF, 2026-10-13).

Kent's priority, "the fine details" of lettering. Hotel Fremont's tagline
(EAT | STAY | PLAY) and EST at his 81 mm Hat replay have strokes 0.22-0.30 mm
wide, thinner than the 0.40 mm a strand of 40 wt lays. They are under the
sewable-detail area, so stage 7's small-shape rescue (`routes_to_run`) sews
each as a bean run on its OUTLINE: two sides of a stroke narrower than the
thread, so 1.6-3.2x the drawn width, and a counter the outline goes round is
shut (PR #905's per-glyph table). A stroke under one thread wide has one
honest construction: one pass down its middle.

This is that pass, for a letter of a line of text (`text_line_members`: a
text-cluster member, or a house-angle-group shape inside a same-thread
cluster's box) the rescue would send to the run tier anyway, and only when
its stroke -- read off the artwork's own pixels along the skeleton
(`stage6_hairline.measure` with the plan's `InkSource`), the traced width
where the source has no edge -- is at or under the block's laid thread
width. Everything else, and every shape when the flag is off, takes the
ladder exactly as before.

How a glyph is sewn:

1. **Counters back.** Stage 4's sliver floor drops a counter under
   `min_detail_mm`^2 / 4 from the polygon; under this flag stage 4 records it
   (`meta["small_counters"]`, the record `small_print_floor` already uses)
   and it is punched back here, so the skeleton goes ROUND the counter
   instead of through the blob where it was.
2. **Skeleton.** `stage6_hairline.measure` -- the hairline tier's medial axis,
   its spur and crossing-bridge pruning (`_graph`) -- reused, not copied.
   A free end's terminal hook shorter than one stitch (a slab serif at 2 mm
   caps) is trimmed (`trim_hooks`): the needle cannot turn into it.
3. **One route.** Every skeleton edge once, from the free tip nearest the
   needle, straightest continuation at a node (the hairline walk's rule); a
   dead-end arm is taken out and back before the strand it hangs off, and
   when the needle is stranded it walks back over thread already laid
   (shortest way along the skeleton) to the nearest unsewn edge instead of
   jumping. So a connected glyph is ONE run: no jump, no trim, and no arm
   dropped for being short (the hairline tier's drop guard hands a small
   capital E back for exactly that).
4. **Stitch.** The needle points are chosen along the whole route at once
   (`_place`, a shortest path over candidates every 0.05 mm plus the
   route's corners): each stitch's chord between the floor (`min_mm`,
   `machine.MIN_STITCH_MM` unless `cfg.small_lettering_skeleton_floor_mm`
   says otherwise) and `cfg.hairline_stitch_mm`, the fewest stitches that
   follow the stroke, a chord that strays from it priced by the square of
   how far. At 2 mm caps the floor is the binding constraint, not the
   stitch length: a 1 mm floor cannot turn into a 0.8 mm arm.

Measured on the result, not assumed, and each one hands the glyph back to
the ladder (`report["declined"]`) -- the outline it had, which is the
ladder's documented behaviour, not a new defect:

- `counter_crossings`: stitches whose chord enters a counter deeper than a
  quarter of the counter's width ("counter"). A loop round a 0.5 mm counter
  is barely longer than three 0.73 mm stitches.
- `fidelity`: a chord that leaves the glyph by more than half a laid width,
  or more than a tenth of the skeleton out of the thread's reach ("shape")
  -- the floor bent the letter (an E's arms joined into a sigma).

Every number here is a CANDIDATE (ROADMAP gate 1): the width gate is one laid
width, the floor is the needle's, the tolerances are fractions of the laid
width. Nothing is settled until it is sewn.
"""
from __future__ import annotations

import heapq
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import machine, stitches
from .stage6_hairline import _arc, _at, _heading, measure
from .stitches import StitchRun

REPORT_KEY = "small_lettering_skeleton"
# A stitch chord may enter a counter by a quarter of the counter's own
# inscribed width (half of it stays clear of every needle line), and never
# less than this (mm) -- the counter ring is a traced polygon, a quarter of a
# work-grid pixel at 8 px/mm. Candidates (gate 1).
COUNTER_TOL_MM = 0.03
COUNTER_DEPTH_SHARE = 0.25
# Corners of the route offered to `_place` as exact needle positions (a free
# tip the needle turns back at, an elbow): a turn of more than this, read
# this far either side of the vertex, none closer than the separation to a
# stronger one. A traced skeleton steps by work-grid pixels (1/8 mm), so the
# reach spans two of them. Candidates, unsewn (gate 1).
CORNER_MIN_DEG = 50.0
CORNER_REACH_MM = 0.25
CORNER_SEP_MM = 0.5
# Candidate needle positions along the route (`_place`), mm apart.
_CAND_STEP_MM = 0.05
# A stitch spans at most this many stitch lengths of ROUTE (its chord is at
# most one): enough to bridge an arm shorter than the needle floor out and
# back, which the deviation term then prices.
_ARC_REACH = 2.0
# The run must still BE the letter (`fidelity`): no stitch chord leaves the
# glyph further than this many laid widths -- half a width is where the
# thread's own edge stops touching it -- and no more than `MISSED_SHARE_MAX`
# of the skeleton's length lies beyond that reach of every stitch.
# Candidates (gate 1).
SHAPE_TOL_WIDTHS = 0.5
MISSED_SHARE_MAX = 0.10
# ... and never more than this share of the letter's own size: 0.2 mm is
# nothing on a 2.2 mm cap and a seventh of a 1.35 mm one, where a chord that
# close to the stem still turns a T into a 7 (Fremont's EST, rendered).
SHAPE_TOL_SIZE_SHARE = 0.10


def _parts(geom):
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


def glyph_polygon(poly, small_counters) -> Polygon:
    """`poly` with the counters stage 4 recorded (`meta["small_counters"]`,
    rings in design mm) punched back in. Rings that do not lie inside `poly`
    are ignored; `poly` itself when there is nothing to punch."""
    if not small_counters or poly is None or poly.is_empty:
        return poly
    holes = []
    for ring in small_counters:
        if len(ring) < 3:
            continue
        h = Polygon(ring).buffer(0)
        if h.is_empty or not poly.covers(h.representative_point()):
            continue
        holes.append(h)
    if not holes:
        return poly
    out = poly.difference(unary_union(holes))
    polys = [g for g in _parts(out) if g.geom_type == "Polygon" and not g.is_empty]
    if not polys:
        return poly
    return max(polys, key=lambda g: g.area)


def qualifies(poly, max_width_mm: float, ink=None):
    """-> the `stage6_hairline.measure` dict when the glyph's stroke is at or
    under `max_width_mm` and its traced 95th percentile under twice it (a
    blob is not a stroke); else None. The stroke is read off the SOURCE
    pixels when `ink` (`stage6_hairline.InkSource`) is given and has an edge
    there -- the tracer's error at this scale has no fixed sign (a 0.40 mm
    tick traces anywhere from 0.17 to 0.45 at 8 px/mm) -- else the traced
    skeleton's median body width."""
    m = measure(poly, max_width_mm, ink=ink)
    if m is None or not m["shape_admit"]:
        return None
    return m


def text_line_members(regions) -> set[str]:
    """The shape ids this tier may take: every member of a text cluster
    (`meta["text_cluster_id"]`, `textcluster`), plus a shape only the
    house-angle tagger calls lettering (`lettering_group`) whose centroid
    lies inside the bounding box of a text cluster of the SAME thread -- a
    letter of that line the text tagger missed (Fremont's tagline A's, which
    stage 4's dropped counter turned into blobs to it). A `lettering_group`
    shape outside every line of text is left alone: on Fremont that is a
    banner's row of tick marks whose widths straddle the thread (source
    0.25-0.51 mm), so taking them one by one sewed half the row as runs and
    half as outlines."""
    boxes: dict = {}
    cents: dict = {}
    members: set[str] = set()
    for r in regions:
        cid = (r.meta or {}).get("text_cluster_id")
        if not cid or not (r.meta or {}).get("text_candidate"):
            continue
        members.add(r.shape_id)
        key = (cid, r.thread_index)
        x0, y0, x1, y1 = r.polygon.bounds
        b = boxes.get(key)
        boxes[key] = ((x0, y0, x1, y1) if b is None else
                      (min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)))
        c = r.polygon.centroid
        cents.setdefault(key, []).append((c.x, c.y))
    # Each line's reading direction: the principal axis of its letters'
    # centroids (a line on an arc reads along its chord, near enough).
    axes = {}
    for key, pts in cents.items():
        a = np.asarray(pts, np.float64)
        if len(a) < 2:
            continue
        mean = a.mean(axis=0)
        _u, _s, vt = np.linalg.svd(a - mean)
        axes[key] = (mean, vt[0], (a - mean) @ vt[0])
    for r in regions:
        m = r.meta or {}
        if r.shape_id in members or not m.get("lettering_group") or m.get("text_candidate"):
            continue
        c = r.polygon.centroid
        for key, (x0, y0, x1, y1) in boxes.items():
            if key[1] != r.thread_index or key not in axes:
                continue
            if not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
                continue
            # BETWEEN two of the line's letters along it, not past its end:
            # the bounding box of a slanted line takes in its neighbours too.
            mean, ax, proj = axes[key]
            t = float((np.array([c.x, c.y]) - mean) @ ax)
            if proj.min() < t < proj.max():
                members.add(r.shape_id)
                break
    return members


# --- the route ---------------------------------------------------------------

def _components(edges):
    """Edges grouped by connectivity through their node ids (a closed loop
    with no node is its own group)."""
    parent: dict = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    for i, e in enumerate(edges):
        ids = [("e", i)] + [("n", e[k]) for k in ("a", "b") if e[k] is not None]
        for x in ids[1:]:
            ra, rb = find(ids[0]), find(x)
            if ra != rb:
                parent[ra] = rb
    groups: dict = {}
    for i in range(len(edges)):
        groups.setdefault(find(("e", i)), []).append(i)
    return list(groups.values())


def _oriented(e, from_node):
    """The edge's points starting at `from_node` and the node it ends on."""
    if e["a"] == from_node:
        return list(e["pts"]), e["b"]
    return list(reversed(e["pts"])), e["a"]


def _route_component(edges, idx, entry):
    """One connected skeleton -> [(edge index, points, retrace)], covering
    every edge once forward, plus the retraces that keep it one run."""
    if len(idx) == 1 and edges[idx[0]]["closed"]:
        pts = list(edges[idx[0]]["pts"])
        if entry is not None and len(pts) > 2:
            ring = pts[:-1] if math.dist(pts[0], pts[-1]) < 1e-9 else pts
            k = min(range(len(ring)), key=lambda j: math.dist(ring[j], entry))
            ring = ring[k:] + ring[:k]
            pts = ring + [ring[0]]
        return [(idx[0], pts, False)]
    by_node: dict = {}
    for i in idx:
        for k in ("a", "b"):
            n = edges[i][k]
            if n is not None:
                by_node.setdefault(n, []).append(i)
    pos: dict = {}
    for i in idx:
        e = edges[i]
        if e["a"] is not None:
            pos.setdefault(e["a"], e["pts"][0])
        if e["b"] is not None:
            pos.setdefault(e["b"], e["pts"][-1])
    degree = {n: len(v) for n, v in by_node.items()}
    odd = [n for n, d in degree.items() if d % 2 == 1]
    pool = odd or list(by_node)
    start = min(pool, key=lambda n: (0.0 if entry is None else round(math.dist(pos[n], entry), 6),
                                     str(n)))
    left = set(idx)
    out = []
    node = start
    path_tail: list = []           # recent forward points, for the heading read

    def dead_end(i, at):
        other = edges[i]["b"] if edges[i]["a"] == at else edges[i]["a"]
        return other is not None and degree.get(other, 0) == 1

    while left:
        cands = [i for i in by_node.get(node, []) if i in left]
        if cands:
            ends = [i for i in cands if dead_end(i, node)]
            if ends and len(cands) > 1:
                # An arm hanging off this node is sewn out and back first: the
                # retrace costs the arm's length, never the strand's.
                pick = min(ends, key=lambda i: (round(_arc(edges[i]["pts"]), 9), i))
            else:
                h_in = _heading(path_tail, at_end=True) if len(path_tail) >= 2 else None
                best = None
                for i in cands:
                    pts, _nxt = _oriented(edges[i], node)
                    h_out = _heading(pts, at_end=False)
                    turn = 0.0 if (h_in is None or h_out is None) else \
                        -(h_in[0] * h_out[0] + h_in[1] * h_out[1])
                    key = (round(turn, 9), i)
                    if best is None or key < best[0]:
                        best = (key, i)
                pick = best[1]
            pts, nxt = _oriented(edges[pick], node)
            left.discard(pick)
            out.append((pick, pts, False))
            path_tail = (path_tail + pts)[-64:]
            node = nxt
            continue
        # Stranded: walk back over laid thread to the nearest node that still
        # has an unsewn edge (Dijkstra along the skeleton).
        dist = {node: 0.0}
        prev: dict = {}
        heap = [(0.0, 0, node)]
        seq = 1
        goal = None
        while heap:
            d, _s, n = heapq.heappop(heap)
            if d > dist.get(n, math.inf):
                continue
            if any(i in left for i in by_node.get(n, [])):
                goal = n
                break
            for i in by_node.get(n, []):
                e = edges[i]
                m = e["b"] if e["a"] == n else e["a"]
                if m is None:
                    continue
                nd = d + _arc(e["pts"])
                if nd < dist.get(m, math.inf) - 1e-12:
                    dist[m] = nd
                    prev[m] = (n, i)
                    heapq.heappush(heap, (nd, seq, m))
                    seq += 1
        if goal is None:
            break                       # nothing reachable (cannot happen in one component)
        hops = []
        n = goal
        while n != node:
            pn, i = prev[n]
            hops.append((pn, i))
            n = pn
        for pn, i in reversed(hops):
            pts, nxt = _oriented(edges[i], pn)
            out.append((i, pts, True))
            path_tail = (path_tail + pts)[-64:]
        node = goal
    return out


def route(edges, entry):
    """-> list of components, each a list of (edge index, points, retrace),
    components nearest-first from `entry`."""
    comps = _components(edges)
    out = []
    cur = entry
    left = list(comps)
    while left:
        def near(c):
            ends = [p for i in c for p in (edges[i]["pts"][0], edges[i]["pts"][-1])]
            return 0.0 if cur is None else min(math.dist(cur, p) for p in ends)
        c = min(left, key=lambda c: (round(near(c), 6), min(c)))
        left.remove(c)
        legs = _route_component(edges, c, cur)
        out.append(legs)
        if legs:
            cur = legs[-1][1][-1]
    return out


# --- stitching ---------------------------------------------------------------

def _turns(pts, reach_mm):
    """Per vertex of `pts`, how far the line turns there (degrees, 0 straight,
    180 a reversal), read `reach_mm` back and forward along it so a raster
    skeleton's pixel steps do not read as corners."""
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    out = []
    n = len(pts)
    for k in range(n):
        j = k
        while j > 0 and cum[k] - cum[j] < reach_mm:
            j -= 1
        m = k
        while m < n - 1 and cum[m] - cum[k] < reach_mm:
            m += 1
        if j == k or m == k:
            out.append(0.0)
            continue
        ux, uy = pts[k][0] - pts[j][0], pts[k][1] - pts[j][1]
        vx, vy = pts[m][0] - pts[k][0], pts[m][1] - pts[k][1]
        nu, nv = math.hypot(ux, uy), math.hypot(vx, vy)
        if nu < 1e-9 or nv < 1e-9:
            out.append(0.0)
            continue
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / (nu * nv)))
        out.append(math.degrees(math.acos(c)))
    return out, cum


def _corners(pts, cum, turns, min_turn_deg, sep_mm):
    """Indices of the route's corners: vertices turning more than
    `min_turn_deg`, strongest first, none within `sep_mm` of a stronger one;
    plus both ends."""
    cand = sorted((k for k in range(1, len(pts) - 1) if turns[k] > min_turn_deg),
                  key=lambda k: (-turns[k], k))
    picked: list = []
    for k in cand:
        if all(abs(cum[k] - cum[q]) >= sep_mm for q in picked):
            picked.append(k)
    return sorted({0, len(pts) - 1, *picked})


def _stitch_component(edges, legs, stitch_mm, tol_mm, min_mm):
    """One component's route -> needle points. The route is one polyline
    (forward edges and retraces in order); `_place` picks its needle points,
    its corners -- a free tip the needle turns back at, an L's elbow, an A's
    apex -- among the candidates."""
    line: list = []
    for _i, pts, _retrace in legs:
        for q in pts:
            q = (float(q[0]), float(q[1]))
            if not line or math.dist(line[-1], q) > 1e-9:
                line.append(q)
    if len(line) < 2:
        return []
    turns, cum = _turns(line, CORNER_REACH_MM)
    keep = _corners(line, cum, turns, CORNER_MIN_DEG, CORNER_SEP_MM)
    return _place(line, cum, [cum[k] for k in keep], stitch_mm, tol_mm, min_mm)


def _seg_dist(p, a, b) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _place(line, cum, corners, stitch_mm, tol_mm, min_mm):
    """The needle points along `line`, chosen together: candidates every
    `_CAND_STEP_MM` of arc plus every corner, from the route's start to its
    end, each stitch's chord between `min_mm` (the needle floor) and
    `stitch_mm`, minimising

        stitches + sum over stitches of (deviation / tol_mm)^2

    where a stitch's deviation is how far the route between its two needle
    points strays from the chord. So a stitch follows the stroke where it
    can, a tip the needle turns back at is landed on (a chord across a
    reversal deviates by the arm's length), and where the floor forbids a
    stitch short enough to follow, the least-bad one is taken -- measured
    afterwards by `fidelity`, which declines a glyph it bent. [] when no
    stitch at or above the floor fits (a route shorter than one stitch)."""
    total = cum[-1]
    n = int(total / _CAND_STEP_MM)
    cand = sorted({0.0, total, *(k * _CAND_STEP_MM for k in range(1, n + 1) if k * _CAND_STEP_MM < total),
                   *(s for s in corners)})
    pts = [_at(line, cum, s) for s in cand]
    N = len(cand)
    inf = math.inf
    best = [inf] * N
    prev = [-1] * N
    best[0] = 0.0
    for j in range(1, N):
        pj = pts[j]
        for i in range(j - 1, -1, -1):
            if cand[j] - cand[i] > _ARC_REACH * stitch_mm + 1e-9:
                break
            if best[i] == inf:
                continue
            chord = math.dist(pts[i], pj)
            if chord < min_mm or chord > stitch_mm:
                continue
            dev = 0.0
            for k in range(i + 1, j):
                d = _seg_dist(pts[k], pts[i], pj)
                if d > dev:
                    dev = d
            c = best[i] + 1.0 + (dev / tol_mm) ** 2
            if c < best[j]:
                best[j] = c
                prev[j] = i
    if best[-1] == inf:
        return []
    out = []
    j = N - 1
    while j != -1:
        out.append(pts[j])
        j = prev[j]
    return out[::-1]

def counter_crossings(points, counters, tol_mm: float = COUNTER_TOL_MM):
    """-> (stitches whose chord enters a counter deeper than its tolerance --
    `tol_mm` or `COUNTER_DEPTH_SHARE` of the counter's inscribed width,
    whichever is larger -- and the deepest entry into any counter, mm)."""
    from shapely.ops import polylabel

    def tol_for(c):
        try:
            w = 2.0 * float(polylabel(c, tolerance=0.005).distance(c.exterior))
        except Exception:       # a degenerate ring: the floor alone
            w = 0.0
        return max(tol_mm, COUNTER_DEPTH_SHARE * w)
    pairs = [(c.buffer(-tol_for(c)), c) for c in counters]
    pairs = [(s, c) for s, c in pairs if not s.is_empty]
    n = 0
    deepest = 0.0
    for a, b in zip(points, points[1:]):
        seg = LineString([a, b])
        hit = False
        for core, full in pairs:
            if not seg.intersects(core):
                continue
            hit = True
            steps = max(2, int(seg.length / 0.01))
            for j in range(steps + 1):
                q = seg.interpolate(j / steps, normalized=True)
                if full.contains(q):
                    deepest = max(deepest, full.exterior.distance(q))
        n += int(hit)
    return n, round(deepest, 4)


def skeleton_letter_runs(poly, shape_id: str, *, max_width_mm: float, stitch_mm: float,
                         run_width_mm: float, entry, trim_at_mm: float,
                         min_mm: float = machine.MIN_STITCH_MM,
                         ink=None, m: dict | None = None) -> tuple[list[StitchRun], dict]:
    """One glyph (`poly`, counters already punched back) -> (runs, report).
    `ink` is the artwork's pixels for the width gate (`qualifies`).

    Report: the shared tier keys (`empty`, `jumps`, `too_thin` False) plus
    `admitted`, `width_mm` (the stroke the gate read), `width_traced_mm`,
    `edges`, `components`,
    `retrace_mm` (thread walked back over), `sewn_mm` (skeleton length),
    `stitches`, `min_stitch_mm`, `counters`, `counter_crossings`,
    `counter_depth_mm`, `outside_mm` and `missed_share` (`fidelity`), and
    `declined` ("width", "empty", "counter", "shape" or None).
    `empty` means "take the ladder"."""
    report = {"empty": True, "jumps": 0, "too_thin": False, "admitted": False,
              "width_mm": None, "edges": 0, "components": 0, "retrace_mm": 0.0,
              "sewn_mm": 0.0, "stitches": 0, "min_stitch_mm": None,
              "counters": len(getattr(poly, "interiors", []) or []),
              "counter_crossings": 0, "counter_depth_mm": 0.0, "declined": None}
    if m is None:
        m = measure(poly, max_width_mm, ink=ink)
    if m is not None:
        report["width_mm"] = round(m["width_mm"], 4)
        report["width_traced_mm"] = round(m["width_traced_mm"], 4)
    if m is None or not m["shape_admit"]:
        report["declined"] = "width"
        return [], report
    report["admitted"] = True
    edges, report["hook_mm"] = trim_hooks(list(m["hair_edges"]) + list(m["thick_edges"]), min_mm)
    report["hook_mm"] = round(report["hook_mm"], 4)
    report["edges"] = len(edges)
    if not edges:
        report["declined"] = "empty"
        return [], report
    tol = min(0.5 * run_width_mm, max(m["width_traced_mm"], 0.05))
    comps = route(edges, entry)
    report["components"] = len(comps)
    runs: list[StitchRun] = []
    counters = [Polygon(r) for r in poly.interiors] if hasattr(poly, "interiors") else []
    for legs in comps:
        report["sewn_mm"] += sum(_arc(p) for _i, p, r in legs if not r)
        report["retrace_mm"] += sum(_arc(p) for _i, p, r in legs if r)
        pts = _stitch_component(edges, legs, stitch_mm, tol, min_mm)
        if len(pts) < 2:
            continue
        jump = trim = False
        if runs:
            d = math.dist(runs[-1].points[-1], pts[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(pts), kind=stitches.RUN,
                              jump=jump, trim=trim, shape_id=shape_id))
    if not runs:
        report["declined"] = "empty"
        return [], report
    allpts = [q for r in runs for q in r.points]
    seg = [math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:])]
    report["stitches"] = len(allpts)
    report["min_stitch_mm"] = round(min(seg), 4) if seg else None
    n_cross, depth = 0, 0.0
    for r in runs:
        c, d = counter_crossings(r.points, counters)
        n_cross += c
        depth = max(depth, d)
    report["counter_crossings"] = n_cross
    report["counter_depth_mm"] = depth
    report["sewn_mm"] = round(report["sewn_mm"], 4)
    report["retrace_mm"] = round(report["retrace_mm"], 4)
    gx0, gy0, gx1, gy1 = poly.bounds
    shape_tol = min(SHAPE_TOL_WIDTHS * run_width_mm,
                    SHAPE_TOL_SIZE_SHARE * max(gx1 - gx0, gy1 - gy0))
    report["shape_tol_mm"] = round(shape_tol, 4)
    outside, missed = fidelity(runs, poly, edges, shape_tol)
    report["outside_mm"] = outside
    report["missed_share"] = missed
    if n_cross:
        report["declined"] = "counter"
        return [], report
    if outside > shape_tol or missed > MISSED_SHARE_MAX:
        # The needle floor bent the letter: a chord cuts across it (an E's
        # arms joined into a sigma) or a stretch of the stroke is never
        # reached (an arm shorter than one stitch). The outline it had.
        report["declined"] = "shape"
        return [], report
    report["empty"] = False
    return runs, report


def trim_hooks(edges, min_mm: float) -> tuple[list, float]:
    """-> (edges, mm trimmed): every free end's terminal HOOK -- the stretch
    past the last corner (`CORNER_MIN_DEG`) within `min_mm` of the tip -- cut
    off. At 2 mm caps that hook is a slab serif: an E's arm turning down for
    0.3 mm at its end, a T's bar dropping at each side. A stitch at the
    needle floor cannot turn into it, so it is not asked to, and the shape
    test does not bill it as stroke the thread missed."""
    out = []
    cut = 0.0
    for e in edges:
        if e.get("closed") or not (e.get("free_a") or e.get("free_b")):
            out.append(e)
            continue
        pts = [tuple(q) for q in e["pts"]]
        if len(pts) < 3:
            out.append(e)
            continue
        turns, cum = _turns(pts, CORNER_REACH_MM)
        lo, hi = 0, len(pts) - 1
        if e.get("free_b"):
            ks = [k for k in range(1, hi) if cum[hi] - cum[k] < min_mm and turns[k] > CORNER_MIN_DEG]
            if ks:
                hi = max(ks, key=lambda k: (turns[k], -k))
        if e.get("free_a"):
            ks = [k for k in range(1, hi) if cum[k] - cum[0] < min_mm and turns[k] > CORNER_MIN_DEG]
            if ks:
                lo = max(ks, key=lambda k: (turns[k], k))
        if lo == 0 and hi == len(pts) - 1:
            out.append(e)
            continue
        if hi - lo < 1:
            out.append(e)
            continue
        cut += cum[lo] + (cum[-1] - cum[hi])
        out.append({**e, "pts": pts[lo:hi + 1]})
    return out, cut


def fidelity(runs, poly, edges, reach_mm: float,
             step_mm: float = 0.02) -> tuple[float, float]:
    """-> (`outside_mm`, `missed_share`): how far the needle's chords leave
    the glyph (largest distance of a point on a stitch from `poly`), and the
    share of the skeleton's length lying further than `reach_mm` from every
    stitch -- stroke the thread never reaches. Both 0 for a run that IS the
    skeleton. A share, not a maximum: a slab serif's stub at the end of a
    2 mm letter is a few tenths of a millimetre no stitch can turn into, and
    must not decide the letter."""
    segs = [LineString([a, b]) for r in runs for a, b in zip(r.points, r.points[1:])
            if math.dist(a, b) > 1e-9]
    if not segs:
        return 0.0, 1.0
    outside = 0.0
    for s in segs:
        steps = max(1, int(s.length / step_mm))
        for j in range(steps + 1):
            q = s.interpolate(j / steps, normalized=True)
            if not poly.covers(q):
                outside = max(outside, poly.distance(q))
    thread = unary_union(segs)
    total = far = 0.0
    for e in edges:
        pts = e["pts"]
        for a, b in zip(pts, pts[1:]):
            d = math.dist(a, b)
            total += d
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            if thread.distance(Point(mid)) > reach_mm:
                far += d
    return round(outside, 4), round(far / total, 4) if total > 0 else 0.0
