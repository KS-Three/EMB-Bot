"""The hairline tier: a one-thread stroke sewn as ONE run along its skeleton.

Kent, 2026-10-12: *"Thread is extremely thin, we should be able to embroider
hair!"* The research behind this (docs/fine-detail-hair-research-2026-10-12.md,
PR #843) found the engine never asks what weight it sews, and that a stroke
under the satin floor sews as a THREE-pass bean on its outline — three widths
of mark for a one-width stroke. A single strand of 40 wt already lays about
0.40 mm; 60 wt about 0.32. So a stroke at or under 1.5 laid widths
(`machine.HAIRLINE_MAX_WIDTHS`) sews here as one pass down its middle.

Built DEFAULT OFF (`cfg.hairline`). Every number is a CANDIDATE from a source,
not a setting — ROADMAP gate 1; the card that would settle them is restated
in docs/hairline-prototype-2026-10-12.md.

How a shape is sewn:

1. **Measure.** Rasterize the ARTWORK polygon fine enough that the stroke is
   at least `_PX_ACROSS` pixels wide (the same rule `stage6_satin._rasterize`
   uses, with a higher cap because a hair network spans the design), take the
   medial axis and its distance, and read the stroke width off the skeleton.
   The width is read on the strands' BODIES — a disk around every branch
   pixel is left out, because a crossing reads wider than either strand
   (1.41x at right angles) and a hair network is full of them. The shape is
   admitted when the MEDIAN body width is at or under the limit and the 95th
   percentile at or under twice it (a real blob is not a crossing).
   The gate is per SHAPE, and a hair network the tracer delivers as one
   region is all-or-nothing: a strand inside it drawn wider than the limit
   still sews as one run when the network's median admits it.
2. **Decompose.** `stage6_satin._skeleton_edges` (reused, not copied) splits
   the skeleton into edges between nodes. End-cap spurs — a free edge shorter
   than two stroke widths hanging off a node — are dropped.
3. **Walk.** Every edge is sewn exactly once. A path starts at the edge end
   nearest the needle and, at each node, continues onto the unsewn edge that
   turns least — so at a crossing the needle follows the strand straight
   through instead of turning onto its neighbour. When a node has nothing
   left, the path ends and the next starts at the nearest unsewn end
   (nearest-neighbour chaining, the same economy `stage6_detail.detail_runs`
   orders its lines by).
4. **Stitch.** Each path is divided into equal stitches nearest
   `stitch_mm` (`cfg.hairline_stitch_mm`, Melco's 1.5 mm walk floor). Where a
   stitch's chord leaves the drawn line by more than half a thread width (a
   curl), it is halved — but never below `machine.MIN_STITCH_MM`, which is
   the needle's floor and does not move with thread weight. A path shorter
   than `machine.RUN_MIN_LOOP_MM` is dropped and counted.
5. **Hop.** Between paths: a jump, and a trim when the hop is longer than
   `trim_at_mm` — the rule `detail_runs` already applies. No underlay, no
   travel, and no lock of its own; stage 7's existing tie rules see these
   runs like any other.

Reused, said once: `_skeleton_edges` (stage6_satin), the equal-division
arc-length resample idea and the jump/trim rule (stage6_detail), and stage 7's
per-shape emission slot, so sequencing, colour blocks and every exporter take
these runs with no change.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from skimage.morphology import medial_axis

from . import machine, stitches
from .stage6_satin import _skeleton_edges
from .stitches import StitchRun

# Pixels across the narrowest stroke when rasterizing. stage6_satin's rule is
# 8 ("thinning a wall under ~8 px wide invents branch points at every
# wiggle"); this tier also GATES on the width, and at 8 px one pixel is 12%
# of it — a 0.55 mm stroke read 0.47 and passed the 60 wt gate. 16 holds the
# read to about a twentieth of a millimetre.
_PX_ACROSS = 16.0
# Never coarser than this, whatever the stroke.
_PX_PER_MM_MIN = 20.0
# Grid cap on the long side. A hair network can span the whole design;
# stage6_satin's 900 px would put a 0.3 mm strand on 3 px at 80 mm.
_MAX_PX = 2400
_PAD_PX = 2

# Gate percentiles (see the module docstring, step 1).
_GATE_PCT = 50.0
_BLOB_PCT = 95.0
_BLOB_FACTOR = 2.0

# A free skeleton edge shorter than this many stroke widths is an end-cap
# artifact of the medial axis, not a strand.
_SPUR_WIDTHS = 2.0

# How far back along a path (mm) its heading is read when choosing the
# straightest continuation at a node — at least this, and at least
# `_HEADING_WIDTHS` stroke widths, so the read starts outside the crossing's
# core where the medial axis bends toward the junction.
_HEADING_MM = 0.6
_HEADING_WIDTHS = 4.0

# An edge between two NODES shorter than this many stroke widths is the
# inside of one crossing (an X thins to two branch points and a bridge):
# its two nodes are merged into one and the bridge is not sewn — it lies
# under the crossing strands' own thread.
_BRIDGE_WIDTHS = 2.5

# A stitch's chord may leave the drawn line by at most this fraction of the
# run's own width before the stitch is halved. Half a thread: the needle line
# stays inside the mark the thread lays. candidate: geometry, unsewn.
_CURL_TOL_WIDTHS = 0.5


def _parts(poly):
    return list(poly.geoms) if hasattr(poly, "geoms") else [poly]


def _rasterize(poly, est_width_mm: float):
    """-> (mask uint8, scale px/mm, x0 mm, y0 mm) with `_PAD_PX` of margin."""
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0, 1e-6)
    need = max(_PX_PER_MM_MIN, _PX_ACROSS / max(est_width_mm, 1e-3))
    scale = min(need, _MAX_PX / dim)
    w = int(math.ceil((x1 - x0) * scale)) + 2 * _PAD_PX + 1
    h = int(math.ceil((y1 - y0) * scale)) + 2 * _PAD_PX + 1
    img = np.zeros((h, w), np.uint8)

    def to_px(coords):
        a = np.asarray(coords, np.float64)
        return np.round(np.column_stack([(a[:, 0] - x0) * scale + _PAD_PX,
                                         (a[:, 1] - y0) * scale + _PAD_PX])).astype(np.int32)

    for part in _parts(poly):
        cv2.fillPoly(img, [to_px(part.exterior.coords)], 255)
        for ring in part.interiors:
            cv2.fillPoly(img, [to_px(ring.coords)], 0)
    return img, scale, x0, y0


def _estimate_width_mm(poly) -> float:
    """2A/P: a thin ribbon of length L and width w has A = wL, P ~ 2L."""
    per = poly.length
    return 2.0 * poly.area / per if per > 0 else 0.0


def measure(poly, max_width_mm: float):
    """-> dict(admit, width_mm (median), width_p95_mm, skel, scale, x0, y0) or None.

    `None` means the cheap 2A/P estimate already says the shape is far too
    wide to be a hairline, so nothing was rasterized."""
    if poly is None or poly.is_empty or poly.area <= 0:
        return None
    est = _estimate_width_mm(poly)
    if est > _BLOB_FACTOR * max_width_mm:
        return None
    mask, scale, x0, y0 = _rasterize(poly, max(est, 0.05))
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    if not skel.any():
        return None
    # Read the width on the strands' BODIES: where strands cross, the medial
    # axis sits in the crossing's wider core (1.41x at right angles, more at a
    # shallow angle), and a hair network is full of crossings. A disk of 1.5
    # local radii around every branch pixel is excluded; if that leaves
    # nothing (a tiny shape that is all junction), every pixel counts.
    sk = skel.astype(np.uint8)
    nbrs = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32),
                        borderType=cv2.BORDER_CONSTANT) - sk
    branch = (sk > 0) & (nbrs >= 3)
    body = skel.copy()
    if branch.any():
        veto = np.zeros_like(sk)
        for y, x in zip(*np.nonzero(branch)):
            cv2.circle(veto, (int(x), int(y)), int(math.ceil(1.5 * dist[y, x])) + 1, 1, -1)
        body &= veto == 0
        if not body.any():
            body = skel
    d = dist[body]
    # `cv2.fillPoly` paints the boundary pixels on BOTH sides, so a stroke
    # w*scale px wide fills ~w*scale + 1, and the EDT at its middle reads half
    # of that plus half a pixel: w*scale = 2d - 2. (Checked on buffered lines
    # 0.25 / 0.4 / 0.6 mm: 2d - 1 read +0.03 to +0.06 mm high.)
    widths = np.maximum(2.0 * d - 2.0, 1.0) / scale
    med = float(np.percentile(widths, _GATE_PCT))
    p95 = float(np.percentile(widths, _BLOB_PCT))
    admit = med <= max_width_mm and p95 <= _BLOB_FACTOR * max_width_mm
    return {"admit": admit, "width_mm": med, "width_p95_mm": p95,
            "skel": skel, "scale": scale, "x0": x0, "y0": y0}


def _arc(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _heading(pts, at_end: bool, reach_mm: float = _HEADING_MM) -> tuple[float, float] | None:
    """Unit direction of travel at a path's end (`at_end`) or start, read
    `reach_mm` back along it."""
    seq = list(reversed(pts)) if at_end else list(pts)
    tip = seq[0]
    acc = 0.0
    far = seq[-1]
    for a, b in zip(seq, seq[1:]):
        acc += math.dist(a, b)
        if acc >= reach_mm:
            far = b
            break
    dx, dy = (tip[0] - far[0], tip[1] - far[1]) if at_end else (far[0] - tip[0], far[1] - tip[1])
    n = math.hypot(dx, dy)
    return (dx / n, dy / n) if n > 1e-9 else None


def _graph(m: dict, width_mm: float):
    """Skeleton -> list of edges {pts (mm), a, b} with node ids; spurs pruned."""
    scale, x0, y0 = m["scale"], m["x0"], m["y0"]

    def mm(p):
        return ((p[0] - _PAD_PX) / scale + x0, (p[1] - _PAD_PX) / scale + y0)

    raw = _skeleton_edges(m["skel"].astype(np.uint8))
    # Node ids: non-free endpoints that touch (a clique) are one node.
    node_px: list[tuple[int, int]] = []

    def node_of(p) -> int:
        for i, q in enumerate(node_px):
            if max(abs(p[0] - q[0]), abs(p[1] - q[1])) <= 2:
                return i
        node_px.append(p)
        return len(node_px) - 1

    edges = []
    free_id = -1
    for e in raw:
        pts = [mm(p) for p in e["pts"]]
        if len(pts) < 2:
            continue
        if e["closed"]:
            edges.append({"pts": pts, "a": None, "b": None, "closed": True,
                          "free_a": False, "free_b": False})
            continue
        if e["free_start"]:
            a = free_id
            free_id -= 1
        else:
            a = node_of(e["pts"][0])
        if e["free_end"]:
            b = free_id
            free_id -= 1
        else:
            b = node_of(e["pts"][-1])
        edges.append({"pts": pts, "a": a, "b": b, "closed": False,
                      "free_a": e["free_start"], "free_b": e["free_end"]})

    # Spurs: a free edge hanging off a node, shorter than two stroke widths.
    spur_mm = _SPUR_WIDTHS * width_mm
    degree: dict[int, int] = {}
    for e in edges:
        for k in ("a", "b"):
            if e[k] is not None and e[k] >= 0:
                degree[e[k]] = degree.get(e[k], 0) + 1
    kept = []
    for e in edges:
        one_free = (not e["closed"]) and (e["free_a"] != e["free_b"])
        hub = e["b"] if e["free_a"] else e["a"]
        if one_free and _arc(e["pts"]) < spur_mm and degree.get(hub, 0) >= 3:
            degree[hub] -= 1
            continue
        kept.append(e)

    # Bridges: a short node-to-node edge is the inside of one crossing.
    # Merge its ends into one node and do not sew it (see `_BRIDGE_WIDTHS`).
    parent: dict[int, int] = {}

    def find(n: int) -> int:
        while parent.get(n, n) != n:
            n = parent[n]
        return n

    bridge_mm = _BRIDGE_WIDTHS * width_mm
    out = []
    for e in kept:
        a, b = e["a"], e["b"]
        if (not e["closed"] and a is not None and b is not None and a >= 0 and b >= 0
                and _arc(e["pts"]) < bridge_mm):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
            continue
        out.append(e)
    for e in out:
        for k in ("a", "b"):
            if e[k] is not None and e[k] >= 0:
                e[k] = find(e[k])
    return out


def _walk(edges, entry, reach_mm: float = _HEADING_MM):
    """Every edge once, straightest continuation at nodes, nearest-neighbour
    between paths. -> list of point lists (mm)."""
    by_node: dict[int, list[int]] = {}
    for i, e in enumerate(edges):
        for k in ("a", "b"):
            if e[k] is not None:
                by_node.setdefault(e[k], []).append(i)
    left = set(range(len(edges)))
    paths = []
    cur = entry

    # A path that starts where an odd number of unsewn edges meet (a strand's
    # free tip is the commonest case) can end at another such point having
    # swept up everything between — Euler's rule for the fewest paths. An
    # even node is a mid-strand start that leaves a stub behind it.
    rem = {n: len(js) for n, js in by_node.items()}

    def odd(node) -> bool:
        return node is None or rem.get(node, 0) % 2 == 1   # None: a closed loop

    def take(j: int) -> None:
        left.discard(j)
        for k in ("a", "b"):
            n = edges[j][k]
            if n is not None:
                rem[n] -= 1

    while left:
        best = None
        for i in sorted(left):
            e = edges[i]
            for flip in (0, 1):
                start = e["pts"][0] if flip == 0 else e["pts"][-1]
                at = e["a"] if flip == 0 else e["b"]
                d = 0.0 if cur is None else math.dist(cur, start)
                key = (0 if odd(at) else 1, round(d, 6), i, flip)
                if best is None or key < best[0]:
                    best = (key, i, flip)
        _key, i, flip = best
        take(i)
        e = edges[i]
        path = list(e["pts"]) if flip == 0 else list(reversed(e["pts"]))
        node = None if e["closed"] else (e["b"] if flip == 0 else e["a"])
        while node is not None:
            cands = [j for j in by_node.get(node, []) if j in left]
            if not cands:
                break
            h_in = _heading(path, at_end=True, reach_mm=reach_mm)
            pick = None
            for j in cands:
                ej = edges[j]
                fwd = ej["a"] == node
                pts = list(ej["pts"]) if fwd else list(reversed(ej["pts"]))
                h_out = _heading(pts, at_end=False, reach_mm=reach_mm)
                turn = 0.0 if (h_in is None or h_out is None) else \
                    -(h_in[0] * h_out[0] + h_in[1] * h_out[1])
                key = (round(turn, 9), j)
                if pick is None or key < pick[0]:
                    pick = (key, j, pts, ej["b"] if fwd else ej["a"])
            _k, j, pts, nxt = pick
            take(j)
            if math.dist(path[-1], pts[0]) < 1e-9:
                pts = pts[1:]
            path.extend(pts)
            node = nxt
        paths.append(path)
        cur = path[-1]
    return paths


def _cum(pts):
    out = [0.0]
    for a, b in zip(pts, pts[1:]):
        out.append(out[-1] + math.dist(a, b))
    return out


def _at(pts, cum, s):
    """Point at arc length `s` along `pts`."""
    if s <= 0:
        return pts[0]
    if s >= cum[-1]:
        return pts[-1]
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= s:
            lo = mid
        else:
            hi = mid
    seg = cum[hi] - cum[lo]
    f = (s - cum[lo]) / seg if seg > 0 else 0.0
    (ax, ay), (bx, by) = pts[lo], pts[hi]
    return (ax + (bx - ax) * f, ay + (by - ay) * f)


def _deviation(pts, cum, s0, s1, a, b) -> float:
    """Largest distance of the drawn line between arc lengths s0..s1 from the
    chord a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    worst = 0.0
    for k in range(len(pts)):
        if s0 < cum[k] < s1:
            px, py = pts[k]
            if L < 1e-9:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dx * (ay - py) - dy * (ax - px)) / L
            worst = max(worst, d)
    return worst


def stitch_path(pts, stitch_mm: float, tol_mm: float,
                min_mm: float = machine.MIN_STITCH_MM) -> list[tuple[float, float]]:
    """A drawn polyline -> needle positions.

    Marches along the line: each stitch is `stitch_mm` of arc unless its
    chord strays more than `tol_mm` from the line (a curl), in which case it
    shortens in 10% steps — never under `min_mm`, the needle's floor
    (`machine.MIN_STITCH_MM`). Halving would not do: half of 1.5 is under
    1.0, so a halving rule never fires at the default length. The last two
    stitches share what is left, so the path does not end on a stub; and a
    final pass drops any interior point closer than `min_mm` to the one
    before (a chord can be shorter than its arc)."""
    cum = _cum(pts)
    total = cum[-1]
    if total <= 0:
        return []
    out_s = [0.0]
    s = 0.0
    while total - s > 1e-9:
        rest = total - s
        if rest <= stitch_mm:
            out_s.append(total)
            break
        step = stitch_mm
        a = _at(pts, cum, s)
        while step > min_mm:
            b = _at(pts, cum, s + step)
            if _deviation(pts, cum, s, s + step, a, b) <= tol_mm:
                break
            step = max(min_mm, step * 0.9)
        if rest - step < min_mm:
            # Two stitches share what is left rather than leave a stub.
            half = rest / 2.0
            if half >= min_mm:
                out_s.append(s + half)
            out_s.append(total)
            break
        s += step
        out_s.append(s)
    raw = [_at(pts, cum, s) for s in out_s]
    kept = [raw[0]]
    for p in raw[1:-1]:
        if math.dist(kept[-1], p) >= min_mm:
            kept.append(p)
    last = raw[-1]
    while len(kept) > 1 and math.dist(kept[-1], last) < min_mm:
        kept.pop()
    kept.append(last)
    if len(kept) == 2 and math.dist(kept[0], kept[1]) < min_mm:
        return []
    return kept


def hairline_runs(poly, shape_id: str, *, max_width_mm: float, run_width_mm: float,
                  stitch_mm: float, entry: tuple[float, float] | None,
                  trim_at_mm: float) -> tuple[list[StitchRun], dict]:
    """One shape through the hairline tier -> (runs, report).

    Report keys: the shared tier vocabulary (`empty`, `jumps`, `too_thin` —
    always False) plus `admitted` (the width gate's verdict), `width_mm`
    (median body width), `strands` (paths sewn), `dropped` (paths under
    `RUN_MIN_LOOP_MM`) and `edges` (skeleton edges walked). `empty` with
    `admitted` False means "not a hairline — take the ladder"; `empty` with
    `admitted` True means the whole shape was too short to sew as a run,
    which stage 7 also treats as "take the ladder" so nothing is dropped
    silently."""
    report = {"empty": True, "jumps": 0, "too_thin": False, "admitted": False,
              "width_mm": None, "strands": 0, "dropped": 0, "edges": 0}
    m = measure(poly, max_width_mm)
    if m is None:
        return [], report
    report["width_mm"] = round(m["width_mm"], 4)
    if not m["admit"]:
        return [], report
    report["admitted"] = True
    edges = _graph(m, max(m["width_mm"], 1e-3))
    report["edges"] = len(edges)
    if not edges:
        return [], report
    paths = _walk(edges, entry,
                  reach_mm=max(_HEADING_MM, _HEADING_WIDTHS * m["width_mm"]))
    tol = _CURL_TOL_WIDTHS * run_width_mm
    runs: list[StitchRun] = []
    for path in paths:
        if _arc(path) < machine.RUN_MIN_LOOP_MM:
            report["dropped"] += 1
            continue
        pts = stitch_path(path, stitch_mm, tol)
        if len(pts) < 2:
            report["dropped"] += 1
            continue
        jump = trim = False
        if runs:
            d = math.dist(runs[-1].points[-1], pts[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(pts),
                              kind=stitches.RUN, jump=jump, trim=trim,
                              shape_id=shape_id))
    report["strands"] = len(runs)
    report["empty"] = not runs
    return runs, report
