"""Satin columns — how thin strokes, borders and lettering get sewn.

A shape narrower than a few millimetres must not be filled: tatami rows have
nowhere to run and the result is a lumpy scribble. It is sewn as SATIN — zigzag
crosses perpendicular to the stroke, reading as one solid band of parallel
thread. This is the single technique that most separates professional
embroidery from hobby output, and it is why lettering is satin practically
everywhere it fits.

The pipeline mirrors the browser engine's `medialSatin` (src/satin.js), whose
design lessons were learned the hard way and are kept deliberately:

- The stroke's spine comes from the **medial axis** of a raster of the shape.
  scikit-image's `medial_axis` returns the distance transform with the
  skeleton, so the local half-width comes free — the browser engine has to
  ray-cast for it.
- Skeleton branch points are detected with the **Rutovitz crossing number**
  (arms leaving the pixel), never the raw 8-neighbour count: a pixelated curve
  is a staircase, a staircase pixel has 3 raw neighbours, and raw degree would
  shatter a smooth O into hundreds of fragments.
- Thinning grows **spurs** — short dead-end twigs at curvature bumps — and they
  are pruned (short, exactly one free end) before strokes are read off,
  iterating because removing one spur can expose another.
- Pure cycles (O, 0, a counter's wall) contain no node at all, so they are
  walked separately as closed strokes: no free ends, no end trim.
- Normal angles along the spine are **unwrapped** (±π jumps folded away) then
  smoothed, so the crosses never flip direction partway along a stroke.
- Free stroke ends are **trimmed by about half the stroke width**: the medial
  axis bends toward corners at a cap, and crosses placed there degenerate.

Everything works in mm, y-down, the space stage 4 produced.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as SPoint
from skimage.morphology import medial_axis

from . import machine, stitches
from .stitches import StitchRun

# Raster resolution for the medial axis. Enough that a 0.8 mm stroke is ~5 px
# wide (thinning needs a few pixels of meat to find the middle); capped so a
# huge shape cannot allocate an absurd grid.
_RASTER_PX_PER_MM = 6.0
_RASTER_MAX_PX = 900
# A stroke shorter than this many half-widths is skeleton noise, not artwork.
_MIN_STROKE_HALFWIDTHS = 1.2
# The half-width profile is median-filtered over this many samples to drop rays
# that escaped through a junction, then averaged this many times to make the
# two rails run parallel instead of tracking every wobble in the boundary.
_WIDTH_MEDIAN_WINDOW = 5
_WIDTH_SMOOTH_PASSES = 4
# Distance, in stroke half-widths, over which a cross's direction is measured.
_TANGENT_WIDTHS = 1.0
# How opposed two arms must be to count as one stroke through a node. -0.5 welds
# arms 120 deg apart -- a stroke turning 60 deg, which pivots and sprays.
_WELD_MAX_DOT = -0.5
_RING8 = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


@dataclass
class Stroke:
    spine: list[tuple[float, float]]   # mm
    free_start: bool
    free_end: bool
    closed: bool


@dataclass
class _WidthField:
    """The medial-axis distance transform kept queryable in mm space.

    The local half-width at any point of the shape, for free, from the same
    computation that produced the skeleton. Used to keep a cross from escaping
    its own stroke: at a junction (the top of a T) a perpendicular ray from the
    stem hits the BAR's far boundary, and without a local cap those crosses
    span the whole junction as an X of thread.
    """

    dist: np.ndarray
    scale: float
    ox: float
    oy: float

    def half_at(self, pt: tuple[float, float]) -> float:
        x = int((pt[0] - self.ox) * self.scale)
        y = int((pt[1] - self.oy) * self.scale)
        h, w = self.dist.shape
        if 0 <= y < h and 0 <= x < w:
            v = float(self.dist[y, x])
            if v > 0:
                return v / self.scale
        return 0.0


# --- Classification --------------------------------------------------------

def ribbon_width_mm(poly: Polygon) -> float:
    """Mean stroke width of a shape treated as a ribbon: 2·area / perimeter.

    Exact for a long rectangle, close enough for letterforms, and cheap enough
    to run on every region. Counters subtract from the area and add to the
    perimeter, which is what makes it right for an O as well.
    """
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    if perim <= 0:
        return 0.0
    return 2.0 * poly.area / perim


def is_satin_candidate(poly: Polygon, max_width_mm: float) -> bool:
    """Should this shape be satin rather than fill?

    Two conditions, both about how the result reads on fabric: the ribbon must
    be narrow enough that crosses do not float (`max_width_mm`), and it must
    actually BE a ribbon — long relative to its width — rather than a small
    compact blob, which sews better as a few rows of fill.
    """
    w = ribbon_width_mm(poly)
    if w <= 0 or w > max_width_mm:
        return False
    # Ribbon length estimate: half the perimeter minus one width. For a blob
    # (circle: w = r) this comes out ~2.1 w and fails the aspect test.
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    length_est = perim / 2.0 - w
    return length_est >= 3.0 * w


# --- Skeleton extraction ---------------------------------------------------

def _rasterize(poly: Polygon) -> tuple[np.ndarray, float, float, float]:
    """-> (binary mask, scale px/mm, x-origin mm, y-origin mm).

    The scale adapts to the ribbon: thinning a wall under ~8 px wide invents
    branch points at every wiggle and the skeleton shatters (a 0.8 mm S-curve
    came back as 14 strokes at the base resolution). Narrow shapes are small,
    so raising their resolution never threatens the grid cap.
    """
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0)
    wall = ribbon_width_mm(poly)
    need = _RASTER_PX_PER_MM if wall <= 0 else max(_RASTER_PX_PER_MM, 8.0 / wall)
    scale = min(need, _RASTER_MAX_PX / max(dim, 1e-6))
    w = int(math.ceil((x1 - x0) * scale)) + 4
    h = int(math.ceil((y1 - y0) * scale)) + 4
    img = np.zeros((h, w), np.uint8)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - x0) * scale + 2, (a[:, 1] - y0) * scale + 2]).astype(np.int32)

    cv2.fillPoly(img, [to_px(poly.exterior.coords)], 255)
    for ring in poly.interiors:
        cv2.fillPoly(img, [to_px(ring.coords)], 0)
    return img, scale, x0 - 2 / scale, y0 - 2 / scale


def _crossing_number(mask: np.ndarray, x: int, y: int) -> int:
    h, w = mask.shape
    c = 0
    for k in range(8):
        ax, ay = _RING8[k]
        bx, by = _RING8[(k + 1) % 8]
        a = mask[y + ay, x + ax] if 0 <= y + ay < h and 0 <= x + ax < w else 0
        b = mask[y + by, x + bx] if 0 <= y + by < h and 0 <= x + bx < w else 0
        if not a and b:
            c += 1
    return c


def _skeleton_edges(mask: np.ndarray) -> list[dict]:
    """Decompose a 1-px skeleton into edges between nodes, plus closed loops.

    A faithful port of the browser engine's `skeletonEdges` — see the module
    docstring for why crossing number and the separate loop walk matter.
    Returns [{"pts": [(x, y), ...], "free_start": bool, "free_end": bool,
    "closed": bool}].
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    pixels = set(zip(xs.tolist(), ys.tolist()))

    def nbrs(x: int, y: int) -> list[tuple[int, int]]:
        return [(x + dx, y + dy) for dx, dy in _RING8 if (x + dx, y + dy) in pixels]

    # Node-ness depends only on the mask, so compute it once: the walks below
    # ask "is this a node" for nearly every pixel on every step, and doing the
    # 8-neighbour scan each time multiplied the whole decomposition by ~4.
    node_set = {p for p in pixels
                if len(nbrs(*p)) == 1 or _crossing_number(mask, *p) >= 3}

    def is_node(x: int, y: int) -> bool:
        return (x, y) in node_set

    edges: list[dict] = []
    used_dir: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    # Non-node pixels each belong to exactly ONE edge. Consuming them as they
    # are walked is what makes that true: without it, a walk that slipped past
    # a junction diagonally could re-traverse another walk's corridor, and the
    # review measured segments emitted at up to 4x multiplicity — thread laid
    # down 2-4 times as dense along the doubled strokes.
    consumed: set[tuple[int, int]] = set()

    def walk(start: tuple[int, int], first: tuple[int, int]) -> list[tuple[int, int]]:
        path = [start, first]
        if not is_node(*first):
            consumed.add(first)
        prev, cur = start, first
        for _ in range(len(pixels) + 1):
            if is_node(*cur):
                break
            cand = [p for p in nbrs(*cur) if p != prev]
            # A node neighbour ends the edge NOW. _RING8 order puts some
            # diagonals before their adjacent orthogonals, so preferring plain
            # order can step past the junction pixel and keep walking into the
            # next stroke — the node-slip the review confirmed on Arial glyphs.
            node_next = next((p for p in cand if is_node(*p)), None)
            if node_next is not None:
                path.append(node_next)
                break
            cand = [p for p in cand if p not in consumed]
            if not cand:
                break
            prev, cur = cur, cand[0]
            path.append(cur)
            consumed.add(cur)
        return path

    for node in sorted(node_set):
        for nb in nbrs(*node):
            if (node, nb) in used_dir or (nb in consumed and not is_node(*nb)):
                continue
            used_dir.add((node, nb))
            path = walk(node, nb)
            if len(path) >= 2:
                used_dir.add((path[-1], path[-2]))
            edges.append({
                "pts": path,
                "free_start": len(nbrs(*node)) == 1,
                "free_end": len(nbrs(*path[-1])) == 1,
                "closed": False,
            })

    # Pure cycles never contain a node, so the scan above never touched them.
    # Walk only through still-unconsumed pixels, and NEVER close a path that
    # did not come back to its start on its own: appending the start
    # unconditionally welded stray leftover pixels into phantom "loops" whose
    # closing chord sewed a satin band across up to 12 mm of bare fabric (the
    # review's one confirmed-high finding). A walk that dead-ends is emitted as
    # an open stroke instead.
    for start in sorted(pixels):
        if start in consumed or is_node(*start):
            continue
        ring = [p for p in nbrs(*start) if not is_node(*p) and p not in consumed]
        if len(ring) != 2:
            continue
        path = [start]
        consumed.add(start)
        prev, cur = start, ring[0]
        closed = False
        for _ in range(len(pixels) + 1):
            if cur == start:
                closed = True
                break
            path.append(cur)
            consumed.add(cur)
            cand = [p for p in nbrs(*cur) if p != prev
                    and (p == start or (p not in consumed and not is_node(*p)))]
            if not cand:
                break
            prev, cur = cur, cand[0]
        if closed and len(path) >= 5:
            path.append(start)
            edges.append({"pts": path, "free_start": False, "free_end": False, "closed": True})
        elif len(path) >= 2:
            edges.append({"pts": path, "free_start": True, "free_end": True, "closed": False})
    return edges


def _merge_through_junctions(edges: list[dict]) -> list[dict]:
    """Join skeleton edges that run straight through a branch node.

    The skeleton of a T is three edges meeting at one node — but the BAR is one
    stroke that happens to have a stem joining it, not two half-bars. Sewing it
    as two trimmed halves leaves a gap of bare fabric in the middle of the bar
    (measured on the T fixture). At every node, the two incident arms whose
    tangents are most nearly opposite are welded into a single stroke; arms
    that genuinely turn a corner stay separate and later yield to the through
    stroke at the junction.
    """
    def arm_dir(edge: dict, at_start: bool) -> tuple[float, float]:
        pts = edge["pts"] if at_start else list(reversed(edge["pts"]))
        far = pts[min(5, len(pts) - 1)]
        dx, dy = far[0] - pts[0][0], far[1] - pts[0][1]
        d = math.hypot(dx, dy) or 1.0
        return dx / d, dy / d

    # node pixel -> [(edge_index, end_is_start)]
    incident: dict[tuple[int, int], list[tuple[int, bool]]] = {}
    for i, e in enumerate(edges):
        if e["closed"]:
            continue
        if not e["free_start"]:
            incident.setdefault(e["pts"][0], []).append((i, True))
        if not e["free_end"]:
            incident.setdefault(e["pts"][-1], []).append((i, False))

    parent = list(range(len(edges)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # (edge_index, end) pairs already welded, so an edge merges at most once
    # per end and a three-way junction cannot chain all its arms together.
    welded: set[tuple[int, bool]] = set()
    joins: list[tuple[tuple[int, bool], tuple[int, bool]]] = []
    for node, arms in incident.items():
        # Keep pairing while a through-pair remains: an X crossing has FOUR
        # arms and two of the pairs run straight through each other.
        while len(arms) >= 2:
            best = None
            for ai in range(len(arms)):
                for bi in range(ai + 1, len(arms)):
                    (ei, es), (ej, js) = arms[ai], arms[bi]
                    if ei == ej or (ei, es) in welded or (ej, js) in welded:
                        continue
                    da, db = arm_dir(edges[ei], es), arm_dir(edges[ej], js)
                    dot = da[0] * db[0] + da[1] * db[1]
                    if best is None or dot < best[0]:
                        best = (dot, (ei, es), (ej, js))
            # Anti-aligned means straight-through; the threshold admits a bend
            # but refuses a corner sharp enough that the column would have to
            # pivot, which no parallel-rail satin can sew.
            if best is None or best[0] >= _WELD_MAX_DOT:
                break
            welded.add(best[1])
            welded.add(best[2])
            joins.append((best[1], best[2]))
            arms = [a for a in arms if a != best[1] and a != best[2]]

    chains: dict[int, dict] = {i: dict(e) for i, e in enumerate(edges)}
    for (ei, es), (ej, js) in joins:
        ri, rj = find(ei), find(ej)
        if ri == rj:
            continue  # would close a cycle; leave as separate strokes
        # Orient by the weld NODE, not by the original edges' end flags: after
        # a first weld the chain's pts run node-to-node across several edges,
        # and edge ei's "start" may now be buried in the middle of the chain.
        # The node pixel is unambiguous — a ends at it, b starts at it.
        node = edges[ei]["pts"][0] if es else edges[ei]["pts"][-1]
        a, b = chains[ri], chains[rj]
        if a["pts"][-1] == node:
            a_pts, a_free = a["pts"], a["free_start"]
        elif a["pts"][0] == node:
            a_pts, a_free = list(reversed(a["pts"])), a["free_end"]
        else:
            continue  # node no longer an endpoint of the chain: skip the weld
        if b["pts"][0] == node:
            b_pts, b_free = b["pts"], b["free_end"]
        elif b["pts"][-1] == node:
            b_pts, b_free = list(reversed(b["pts"])), b["free_start"]
        else:
            continue
        chains[ri] = {
            "pts": a_pts + b_pts[1:],
            "free_start": a_free,
            "free_end": b_free,
            "closed": False,
        }
        parent[rj] = ri
        del chains[rj]
    return [c for i, c in chains.items() if find(i) == i]


def _prune_spurs(mask: np.ndarray, spur_len_px: float) -> None:
    """Erase short dead-end twigs in place, keeping their branch node."""
    for _ in range(4):
        removed = 0
        for e in _skeleton_edges(mask):
            if e["closed"] or (e["free_start"] == e["free_end"]):
                continue  # spur = exactly one free end
            length = sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
            if length >= spur_len_px:
                continue
            keep = e["pts"][-1] if e["free_start"] else e["pts"][0]
            for px in e["pts"]:
                if px != keep:
                    mask[px[1], px[0]] = 0
                    removed += 1
        if not removed:
            return


def extract_strokes(poly: Polygon) -> tuple[list[Stroke], float, _WidthField | None]:
    """-> (strokes in mm, mean half-width in mm, local width field).

    Strokes are sorted longest first, so a letter's main stem sews before its
    serifs and the between-stroke hops stay short.
    """
    mask, scale, ox, oy = _rasterize(poly)
    if not mask.any():
        return [], 0.0, None
    # rng is REQUIRED for determinism: medial_axis breaks ties between equally
    # valid skeleton pixels in a randomly permuted order, and unseeded it
    # returns a different skeleton on every call — which came out as the same
    # artwork digitizing to different stitches run to run.
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    skel_mask = skel.astype(np.uint8)
    half_px = float(dist[skel].mean()) if skel.any() else 0.0
    field = _WidthField(dist=dist, scale=scale, ox=ox, oy=oy)
    _prune_spurs(skel_mask, max(3.0, half_px * 1.6))
    if not skel_mask.any():
        return [], half_px / scale, field

    def to_mm(p: tuple[int, int]) -> tuple[float, float]:
        return (ox + (p[0] + 0.5) / scale, oy + (p[1] + 0.5) / scale)

    strokes: list[Stroke] = []
    min_len_px = max(3.0, _MIN_STROKE_HALFWIDTHS * half_px)
    for e in _merge_through_junctions(_skeleton_edges(skel_mask)):
        length = sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
        if length < min_len_px and not (e["free_start"] and e["free_end"]):
            continue  # stub between two branch nodes: junction noise
        strokes.append(Stroke(
            spine=[to_mm(p) for p in e["pts"]],
            free_start=e["free_start"],
            free_end=e["free_end"],
            closed=e["closed"],
        ))
    strokes.sort(key=lambda s: -sum(math.dist(a, b) for a, b in zip(s.spine, s.spine[1:])))
    return strokes, half_px / scale, field


# --- Geometry along a stroke ----------------------------------------------

def _smooth(pts: list[tuple[float, float]], passes: int, closed: bool) -> list[tuple[float, float]]:
    out = list(pts)
    n = len(out)
    if n < 3:
        return out
    for _ in range(passes):
        prev = list(out)
        rng = range(n) if closed else range(1, n - 1)
        for i in rng:
            a, b, c = prev[i - 1], prev[i], prev[(i + 1) % n]
            out[i] = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
    return out


def _median_filter(vals: list[float], window: int) -> list[float]:
    """Median of each value's neighbourhood — drops single-sample outliers.

    A ray that escapes a junction reports one wildly long half-width between
    two honest ones. An average would spread that error over the neighbours; a
    median discards it outright, which is what a width profile needs.
    """
    n = len(vals)
    if n == 0 or window < 3:
        return list(vals)
    half = window // 2
    return [sorted(vals[max(0, i - half):min(n, i + half + 1)])[
        len(vals[max(0, i - half):min(n, i + half + 1)]) // 2] for i in range(n)]


def _resample(pts: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    line = LineString(pts)
    if line.length <= 0 or n < 2:
        return list(pts[:1]) * max(n, 1)
    return [(p.x, p.y) for p in (line.interpolate(line.length * i / (n - 1)) for i in range(n))]


def _rail_points(poly: Polygon, spine: list[tuple[float, float]], closed: bool,
                 fallback_half_mm: float,
                 field: _WidthField | None = None) -> tuple[list, list]:
    """Cast the smoothed, unwrapped normals both ways to find the two rails.

    Each rail is capped at ~1.6x the LOCAL medial half-width: at a branch
    junction the ray escapes the stroke's own ribbon and hits another arm's far
    boundary, and uncapped that draws an X of full-width crosses over the
    junction. Capped, each stroke covers its own corridor and the junction gets
    the modest overlap of its arms — which is exactly what a human digitizer
    does there.
    """
    n = len(spine)
    boundary = poly.boundary

    # Tangent angles, unwrapped so a cross never flips direction mid-stroke.
    # The tangent is measured across ONE STROKE WIDTH, not one sample. The
    # spine is a raster staircase: over a ±1-sample baseline (a third of a
    # millimetre here) its direction can only take the eight neighbour
    # directions, so every cross inherits up to ±22.5 deg of quantisation
    # noise. With ray-cast rails that noise was partly hidden — the two
    # boundary hits smoothed it away — but a parallel-offset rail lays the
    # cross exactly along the normal, so the path itself has to be honest. A
    # satin column cannot resolve curvature finer than its own width, so
    # measuring the direction over that distance discards nothing real.
    seg = [math.dist(spine[i], spine[i + 1]) for i in range(n - 1)]
    spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
    k = 1 if spacing <= 0 else max(1, round(fallback_half_mm * _TANGENT_WIDTHS / spacing))

    angles: list[float] = []
    for i in range(n):
        a = spine[max(0, i - k)] if not closed else spine[(i - k) % n]
        b = spine[min(n - 1, i + k)] if not closed else spine[(i + k) % n]
        angles.append(math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2)
    for i in range(1, n):
        while angles[i] - angles[i - 1] > math.pi / 2:
            angles[i] -= math.pi
        while angles[i] - angles[i - 1] < -math.pi / 2:
            angles[i] += math.pi
    for _ in range(6):
        prev = list(angles)
        for i in range(1, n - 1):
            angles[i] = (prev[i - 1] + prev[i] + prev[i + 1]) / 3.0

    reach = max(fallback_half_mm * 4.0, 2.0)
    rail_a: list = []
    rail_b: list = []
    norms: list[tuple[float, float]] = []
    raw: list[float] = []
    floors: list[float] = []
    for i, (px, py) in enumerate(spine):
        nx, ny = math.cos(angles[i]), math.sin(angles[i])

        def hit(dx: float, dy: float):
            ray = LineString([(px, py), (px + dx * reach, py + dy * reach)])
            inter = ray.intersection(boundary)
            if inter.is_empty:
                return None
            pts = []
            for g in getattr(inter, "geoms", [inter]):
                if g.geom_type == "Point":
                    pts.append((g.x, g.y))
                else:
                    pts.extend((c[0], c[1]) for c in g.coords)
            # The terminal station sits ON the boundary (the cap extension put
            # it there), so the nearest intersection is the station itself and
            # keeping it collapses the final cross to a point. Skipping
            # near-zero hits lets the tip's perpendicular ray run along the cap
            # face and land on the cap CORNERS — the square-end terminal stitch
            # a professional column finishes with.
            pts = [q for q in pts if (q[0] - px) ** 2 + (q[1] - py) ** 2 > 0.0025]
            if not pts:
                return None
            return min(pts, key=lambda q: (q[0] - px) ** 2 + (q[1] - py) ** 2)

        def fallback(dx: float, dy: float) -> tuple[float, float]:
            # No ray hit (a corner shadow, a cap tangent skimming the edge).
            # The guess must still be INSIDE the artwork: at free ends the
            # extended tangent can skew, and an unchecked guess put crosses
            # up to ~1 mm outside the C fixture. Shrink the guess until the
            # polygon covers it; a point at the station itself just makes a
            # degenerate cross that the minimum-cross rule drops.
            for f in (1.0, 0.6, 0.35, 0.15):
                q = (px + dx * fallback_half_mm * f, py + dy * fallback_half_mm * f)
                if poly.covers(SPoint(q)):
                    return q
            return (px, py)

        pa = hit(nx, ny) or fallback(nx, ny)
        pb = hit(-nx, -ny) or fallback(-nx, -ny)
        norms.append((nx, ny))
        # The HALF-WIDTH this sample is evidence for. The nearer of the two hits
        # is the honest one: a ray that escapes through a junction into the next
        # arm reports a distance belonging to a different part of the shape, and
        # it is always the longer of the pair.
        raw.append(min(math.dist((px, py), pa), math.dist((px, py), pb)))
        floors.append(max(field.half_at((px, py)), 0.75 * fallback_half_mm)
                      if field is not None else fallback_half_mm)

    # --- width profile -> parallel rails ----------------------------------
    #
    # The rails are PARALLEL OFFSETS of the spine at a smoothed half-width, not
    # two independently ray-cast boundary points. Casting per sample and taking
    # the nearest hit lets consecutive samples land on different boundary
    # features — one cross ends on the edge it belongs to, the next on the far
    # side of a junction — and clamping each side on its own then walks the
    # column's centre off its own spine. Measured on the real logo, 27% of
    # crosses ended up rotated more than 15 deg from the cross two before them:
    # that is the spray, and it is a property of the model, not a tuning error.
    #
    # The medial axis is equidistant from both edges by construction, so a
    # symmetric offset is the correct shape for a ribbon; a median filter drops
    # the junction escapes before the profile is smoothed, and the result is
    # capped by the local corridor so a cross can never span a junction.
    width = _median_filter(raw, _WIDTH_MEDIAN_WINDOW)
    for _ in range(_WIDTH_SMOOTH_PASSES):
        prev = list(width)
        for i in range(1, n - 1):
            width[i] = (prev[i - 1] + prev[i] + prev[i + 1]) / 3.0
    for i in range(n):
        width[i] = min(width[i], floors[i] * 1.6 + 0.2)

    for i, (px, py) in enumerate(spine):
        nx, ny = norms[i]
        w = width[i]
        # Containment still governs: a smoothed width can overshoot where the
        # ribbon pinches, and thread outside the artwork is the one defect this
        # module is never allowed to ship. Each side yields on its own — pulling
        # both in because one overshot drags the good rail off the artwork edge,
        # which is what left the fixture bar's cap bare by 0.06 mm.
        def place(sx: float, sy: float) -> tuple[float, float]:
            for f in (1.0, 0.85, 0.7, 0.5, 0.3):
                q = (px + sx * w * f, py + sy * w * f)
                if poly.covers(SPoint(q)):
                    return q
            return (px, py)

        rail_a.append(place(nx, ny))
        rail_b.append(place(-nx, -ny))
    return rail_a, rail_b


def _short_stitch_guard(rail_a: list, rail_b: list) -> list[tuple]:
    """Shorten alternate crosses where a rail's penetrations bunch up.

    -> [(pa, pb), ...] with the crowded side of every other cross pulled toward
    the middle. On the inside of a curve the rail is shorter than the spine, so
    penetrations land closer together than the satin spacing; below the
    threshold the needle starts re-entering the same hole and the edge frays.
    """
    out = []
    for i, (pa, pb) in enumerate(zip(rail_a, rail_b)):
        if 0 < i and i % 2 == 1:
            pull = machine.SATIN_SHORT_STITCH_PULL
            if math.dist(pa, rail_a[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pa = (pa[0] + (pb[0] - pa[0]) * pull, pa[1] + (pb[1] - pa[1]) * pull)
            if math.dist(pb, rail_b[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pb = (pb[0] + (pa[0] - pb[0]) * pull, pb[1] + (pa[1] - pb[1]) * pull)
        out.append((pa, pb))
    return out


# --- The column ------------------------------------------------------------

def _extend_to_cap(spine: list[tuple[float, float]], poly: Polygon, half_mm: float,
                   at_start: bool) -> list[tuple[float, float]]:
    """Push a free spine end out to the shape's cap edge along its tangent.

    The medial axis of a stroke stops half a width short of each cap (the
    skeleton of a rectangle ends where the corner diagonals meet), so a column
    built on the raw spine leaves the cap unsewn — measured at 1.8 mm of bare
    fabric per end on the fixture bar. Extending along the end tangent until
    the boundary puts the final cross ON the cap edge, which is where a
    professional column ends. Degenerate crosses in a tapering tip are dropped
    later by the minimum-cross rule, so overshooting into a point is safe.
    """
    pts = list(reversed(spine)) if at_start else list(spine)
    if len(pts) < 2:
        return spine
    tip = pts[-1]
    prev = pts[-2]
    d = math.dist(prev, tip)
    if d < 1e-9:
        return spine
    ux, uy = (tip[0] - prev[0]) / d, (tip[1] - prev[1]) / d
    # Long enough to still find the cap after `_retract_cap_corner` has walked
    # the end back in. The nearest hit is the one taken, so a longer ray can
    # only find a cap where there was none — never move one.
    reach = half_mm * 4.5 + 0.5
    ray = LineString([tip, (tip[0] + ux * reach, tip[1] + uy * reach)])
    inter = ray.intersection(poly.boundary)
    if inter.is_empty:
        return spine
    cands = []
    for g in getattr(inter, "geoms", [inter]):
        if g.geom_type == "Point":
            cands.append((g.x, g.y))
        else:
            cands.extend((c[0], c[1]) for c in g.coords)
    if not cands:
        return spine
    cap = min(cands, key=lambda q: (q[0] - tip[0]) ** 2 + (q[1] - tip[1]) ** 2)
    pts.append(cap)
    return list(reversed(pts)) if at_start else pts


# A free end whose corridor is narrower than this fraction of the stroke's own
# half-width is not the stroke any more, it is a cap corner.
_CAP_CORNER_FRAC = 0.8
# Never chase a corner further in than this many half-widths: on a genuinely
# tapering stroke the corridor narrows all the way and there is nothing wrong
# with that.
_CAP_CORNER_REACH_HALFWIDTHS = 1.5


def _retract_cap_corner(spine: list[tuple[float, float]], field: _WidthField | None,
                        half_mm: float, at_start: bool) -> list[tuple[float, float]]:
    """Walk a free spine end back out of the cap corner it ran into.

    A flat cap's medial axis forks toward the two corners. Spur pruning removes
    most of each fork, but what survives leaves the last millimetre of the
    spine running diagonally at a corner instead of down the middle of the
    stroke. Every cross built on that stretch pivots on the same needle hole
    and swings across the cap — the starburst measured on the curved-ribbon
    case: five penetrations in one hole and 3.3 mm crosses on a 2.8 mm ribbon,
    thread laid outside the artwork at the tip and the cap itself left bare.

    The corridor width is the tell — at a corner the distance transform reads a
    fraction of the stroke's half-width. Walk in until it does not, and let
    `_extend_to_cap` rebuild a square end from a point that is genuinely in the
    middle of the stroke.
    """
    if field is None or len(spine) < 4 or half_mm <= 0:
        return spine
    pts = list(reversed(spine)) if at_start else list(spine)
    floor = _CAP_CORNER_FRAC * half_mm
    budget = _CAP_CORNER_REACH_HALFWIDTHS * half_mm
    eaten = 0.0
    cut = 0
    for i in range(len(pts) - 1, 1, -1):
        if field.half_at(pts[i]) >= floor:
            break
        eaten += math.dist(pts[i], pts[i - 1])
        if eaten > budget:
            break
        cut += 1
    if not cut:
        return spine
    pts = pts[: len(pts) - cut]
    return list(reversed(pts)) if at_start else pts


def _trim_chain(pts: list[tuple[float, float]], from_start_mm: float,
                from_end_mm: float) -> list[tuple[float, float]]:
    line = LineString(pts)
    s0, s1 = from_start_mm, line.length - from_end_mm
    if line.length <= 0 or s1 - s0 < 0.5:
        return list(pts)
    n = max(2, int(math.ceil((s1 - s0) / 0.2)))
    return [(p.x, p.y) for p in (line.interpolate(s0 + (s1 - s0) * i / (n - 1)) for i in range(n))]


# How far a stroke reaches under the arm it joins at a junction. Enough that
# fabric pull cannot open a gap between stem and bar, small enough that the
# doubled coverage never reads as a lump.
_JUNCTION_TUCK_MM = 0.4


def satin_stroke(poly: Polygon, stroke: Stroke, half_mm: float,
                 field: _WidthField | None = None) -> list[tuple[float, float]]:
    """One stroke -> flat zigzag points (A, B, B, A, A, B, ...)."""
    spine = _smooth(stroke.spine, 3, stroke.closed)

    # An end at a branch NODE sits in the middle of the junction — the skeleton
    # of a T puts the node halfway up the bar, so an untrimmed stem sews right
    # across crosses the bar already laid down. Step back to the junction edge
    # plus a small tuck; the free ends, by contrast, get EXTENDED to the cap.
    if not stroke.closed and field is not None:
        t0 = 0.0 if stroke.free_start else max(
            0.0, field.half_at(spine[0]) - _JUNCTION_TUCK_MM)
        t1 = 0.0 if stroke.free_end else max(
            0.0, field.half_at(spine[-1]) - _JUNCTION_TUCK_MM)
        if t0 or t1:
            spine = _trim_chain(spine, t0, t1)

    if stroke.free_start:
        spine = _retract_cap_corner(spine, field, half_mm, at_start=True)
        spine = _extend_to_cap(spine, poly, half_mm, at_start=True)
    if stroke.free_end:
        spine = _retract_cap_corner(spine, field, half_mm, at_start=False)
        spine = _extend_to_cap(spine, poly, half_mm, at_start=False)
    length = sum(math.dist(a, b) for a, b in zip(spine, spine[1:]))
    if length <= 0:
        return []

    steps = max(2, int(math.ceil(length / machine.SATIN_SPACING_MM)))
    spine = _resample(spine, steps)
    rail_a, rail_b = _rail_points(poly, spine, stroke.closed, half_mm, field)
    crosses = _short_stitch_guard(rail_a, rail_b)

    out: list[tuple[float, float]] = []
    prev_kept: tuple | None = None
    for i, (pa, pb) in enumerate(crosses):
        if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
            continue  # rails pinched together: shared tip or degenerate cap
        # Corridor capping at a junction can leave consecutive crosses nearly
        # coincident — both penetrations landing in the previous needle holes.
        if prev_kept is not None and \
                math.dist(pa, prev_kept[0]) < 0.05 and math.dist(pb, prev_kept[1]) < 0.05:
            continue
        prev_kept = (pa, pb)
        out.extend((pa, pb) if i % 2 == 0 else (pb, pa))
    return out


def _stroke_underlay(poly: Polygon, st: Stroke, style: str, shape_id: str,
                     field: _WidthField | None) -> list[StitchRun]:
    """Underlay for ONE stroke: a center run down its spine, plus a sparse
    zigzag for the styles that ask for it. Built from the same spine the satin
    will follow, so it always sits under the column."""
    if style == "none":
        return []
    runs: list[StitchRun] = []
    spine = _smooth(st.spine, 3, st.closed)
    length = sum(math.dist(a, b) for a, b in zip(spine, spine[1:]))
    if length < machine.UNDERLAY_STITCH_MM:
        return []
    n = max(2, int(math.ceil(length / machine.UNDERLAY_STITCH_MM)))
    runs.append(StitchRun(points=_resample(spine, n), kind=stitches.UNDERLAY,
                          shape_id=shape_id))
    if style == "zigzag":
        steps = max(2, int(math.ceil(length / machine.UNDERLAY_ZIGZAG_MM)))
        sp = _resample(spine, steps)
        ra, rb = _rail_points(poly, sp, st.closed, ribbon_width_mm(poly) / 2, field)
        pts: list[tuple[float, float]] = []
        for i, (pa0, pb0) in enumerate(zip(ra, rb)):
            # Narrow both ends from the ORIGINALS — pulling pb toward an
            # already-moved pa drifts the zigzag off the column's center.
            pa = (pa0[0] + (pb0[0] - pa0[0]) * 0.3, pa0[1] + (pb0[1] - pa0[1]) * 0.3)
            pb = (pb0[0] + (pa0[0] - pb0[0]) * 0.3, pb0[1] + (pa0[1] - pb0[1]) * 0.3)
            if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
                continue
            pts.extend((pa, pb) if i % 2 == 0 else (pb, pa))
        if len(pts) >= 2:
            runs.append(StitchRun(points=pts, kind=stitches.UNDERLAY,
                                  shape_id=shape_id))
    return runs


def _order_strokes(strokes: list[Stroke],
                   start_near: tuple[float, float] | None) -> list[Stroke]:
    """Sew order within one shape: whichever stroke's nearer end is closest to
    where the needle already is, then on by the same rule.

    `extract_strokes` sorts longest-first, which keeps a letter's main stem
    ahead of its serifs but says nothing about the hops between them. Sewing
    in that order alone means the needle can be sent back across a whole
    glyph — and between shapes it meant every letter started at its own
    longest stroke however far that was from the last stitch of the letter
    before it. With nothing sewn yet the longest stroke still goes first.
    """
    remaining = list(range(len(strokes)))
    out: list[Stroke] = []
    cur = start_near
    while remaining:
        if cur is None:
            pick = remaining[0]
        else:
            pick = min(remaining, key=lambda i: (
                round(min(math.dist(cur, strokes[i].spine[0]),
                          math.dist(cur, strokes[i].spine[-1])), 6), i))
        st = strokes[pick]
        remaining.remove(pick)
        out.append(st)
        # It comes out of the end it did not go in at.
        a, b = st.spine[0], st.spine[-1]
        cur = a if (cur is not None and math.dist(cur, b) < math.dist(cur, a)) else b
    return out


def satin_shape(poly: Polygon, shape_id: str, *, underlay_style: str,
                trim_at_mm: float,
                start_near: tuple[float, float] | None = None
                ) -> tuple[list[StitchRun], dict]:
    """One satin-classified shape -> runs in sew order, plus the same report
    contract `stitch_shape` uses, so stage 7 can treat the two identically.

    `start_near` is where the needle is when this shape's turn comes.
    """
    report = {"too_thin": False, "jumps": 0, "empty": False}
    strokes, half_mm, field = extract_strokes(poly)
    if not strokes:
        report["empty"] = True
        return [], report
    strokes = _order_strokes(strokes, start_near)

    # Per stroke: its underlay, then its column, then move on. Sewing ALL the
    # underlay first meant hopping back across the whole letter to start the
    # first column — on the drone logo that pattern alone put 100+ extra trims
    # in the file, and a trim is 2-3 seconds of machine time each.
    #
    # Each run is also ORIENTED to start at whichever of its ends is nearer to
    # where the needle already is. The center run walks the spine one way and
    # the column would otherwise start back where the underlay began — a full
    # stroke-length hop between them, once per stroke. Reversing an
    # alternating zigzag keeps it an alternating zigzag, so orientation is
    # free to choose.
    runs: list[StitchRun] = []
    for st in strokes:
        pts = satin_stroke(poly, st, half_mm, field)
        if len(pts) < 4:
            continue
        for run in [*_stroke_underlay(poly, st, underlay_style, shape_id, field),
                    StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id)]:
            cursor = runs[-1].points[-1] if runs else start_near
            if cursor is not None and \
                    math.dist(cursor, run.points[-1]) < math.dist(cursor, run.points[0]):
                run.points.reverse()
            runs.append(run)

    if not any(r.kind == stitches.SATIN for r in runs):
        report["empty"] = True
        return [], report

    # Link EVERY consecutive run pair, underlay included: two spines can sit a
    # letter-width apart, and a plain needle-down continuation between their
    # runs would sew a stitch across the gap (over bare fabric, and past the
    # 12.1 mm record ceiling on wide letters). The count matches the fill
    # path's honesty rule: every lift counts, trimmed or not.
    for prev, cur in zip(runs, runs[1:]):
        d = math.dist(prev.points[-1], cur.points[0])
        if d >= machine.TINY_STITCH_MM:
            cur.jump = True
            cur.trim = d > trim_at_mm
            report["jumps"] += 1
    return runs, report

