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

Split satin, and the rail-parity contract
-----------------------------------------
A cross longer than `machine.SPLIT_SATIN_ABOVE_MM` carries intermediate
penetrations (split satin): long stitches float, snag, and pull, and the
professional corpus splits them — 53% of 5 mm crosses, ~100% from 7.5 mm.
The split points are staggered station to station so the holes never trench a
line down the column, mirroring the corpus's 3-6-station cycles.

That collides with a load-bearing contract: emitted satin points strictly
alternate rails (A, B, A, B, ...), and every instrument reads them that way —
the tests slice rails as even/odd points, `tools/audit.py` and the fan test
scan same-rail pairs two apart. The resolution, chosen over flagging split
crosses as separate runs or length-classifying in every instrument:

1. Below the threshold nothing changes — a column with no over-threshold
   cross emits byte-identical points, so every existing fixture, benchmark
   and instrument keeps its exact parity read (current fixtures top out at
   3.71 mm crosses against the 5.0 threshold).
2. An over-threshold cross keeps its rail penetrations in strict A/B order
   and inserts split points BETWEEN them, exactly on the cross segment
   (`_split_points` lerps along A->B). `strip_splits` removes them exactly —
   a point collinear with and between its neighbours can only be a split
   penetration, because a real rail-to-rail step always turns (the return
   leg reverses; degenerate crosses are dropped) — the same
   strip-before-reading contract `stitches.strip_ties` established for lock
   stitches. Instruments that may meet wide columns strip ties first, then
   splits, then read parity as ever.

Everything works in mm, y-down, the space stage 4 produced.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import cv2
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as SPoint
from skimage.morphology import medial_axis

from . import machine, stitches
from .shapefield import build_shape_field
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
# A spine turning more than this many degrees within about one stroke width
# gets the column CUT there. This started at 35 and the corpus overruled it:
# across 19 professional files, 1,436 corner events sit INSIDE a continuing
# run and only 18 are splits — pros sew through corners, letting the outside
# rail fan while the short-stitch guard protects the inside. Splitting is the
# fallback for corners so sharp the column would fold back over itself.
_SPLIT_TURN_DEG = 90.0
# A free end is a TAPERED TIP (not a square cap) when the ray-measured
# corridor ONE STATION IN is already narrower than this fraction of the
# stroke's half-width. Square caps read 0.85-0.94 there (BAR 0.851 is the
# floor of the measured fixtures — the terminal ray tilt costs a few percent);
# the ribbon_curve taper reads 0.59. The terminal station itself cannot be
# the tell: ON a cap face the perpendicular ray skims the boundary and reads
# 0.0 for square caps and tips alike (measured 0.0 on BAR, C and the ribbon).
_TAPER_ZONE_FRAC = 0.8
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

    A thin view over the same numbers `digitizer_core.shapefield.ShapeField`
    carries (`dist`/`scale`/`ox`/`oy`, and `half_at` reads them identically) —
    this class predates that module and stays the type `extract_strokes`
    returns either way; `ShapeField` additionally carries `mask`/`skel` for
    whatever downstream stage the DT-first migration eventually gives them to.
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


def is_satin_candidate(poly: Polygon, max_width_mm: float, *,
                        design_class: str = "flat") -> bool:
    """Should this shape be satin rather than fill?

    Two conditions, both about how the result reads on fabric: the ribbon must
    be narrow enough that crosses do not float (`max_width_mm`), and it must
    actually BE a ribbon — long relative to its width — rather than a small
    compact blob, which sews better as a few rows of fill.

    Both conditions are read off `2*area/perimeter` and the raw perimeter,
    and both share one blind spot: boundary NOISE inflates the perimeter,
    which shrinks the measured width and inflates the length estimate at the
    same time — so a compact, organic blob with a jittery outline can read as
    a narrow, long ribbon on both tests at once. Measured on
    `docs/dt-classifier-spike-2026-08-02.md`'s synthetic case: a 20mm
    serrated disc (tooth 0.6mm) reads `ribbon_width_mm` 2.12mm against a 5mm
    cap and passes the aspect gate too, purely from the noise, not from
    being a stroke. Confirmed on this repo's own committed fixtures too —
    `testdata/photo/region_blobs.png`'s `Sd12bfc9e`/`S94f29987` and
    `testdata/photo/summit_badge.png`'s `Sed818ef7`/`S00d736bf`/`S6096e7a9`
    are near-square, organic, segmentation-noisy regions (bounding-box
    aspect 1.05-1.13) that this test alone waves through as satin.

    `design_class` scopes the fix: a second, independent width read off the
    exact distance transform at the shape's own medial axis (`docs/
    dt-classifier-spike-2026-08-02.md`'s `VP90` arm — a pure TIGHTENING, it
    can only turn a satin call into a fill call, never the reverse) runs
    for every class except `"flat"`. Flat-classified art — clean,
    spot-colour, vector-like boundaries, the shipped byte-identical goldens'
    entire population — keeps exactly today's behaviour, unchanged, because
    that population is not where the noise this fix targets comes from and
    `tests/test_flat_lane_byte_identical.py` pins its output byte for byte.
    Non-flat classes (`gradient`, `photo_subject`, `photo_scene`) are where
    the noisy, segmentation-derived boundaries this fix exists for actually
    occur, and the spike's own measurement (0/21 misses on the synthetic
    archetype population, 26/28 agreement with the shipped rule on real
    artwork, both disagreements being shapes the shipped rule already sews
    wrong) is the evidence for extending it there. See
    `_dt_regular_and_within_cap` for the check itself.
    """
    w = ribbon_width_mm(poly)
    if w <= 0 or w > max_width_mm:
        return False
    # Ribbon length estimate: half the perimeter minus one width. For a blob
    # (circle: w = r) this comes out ~2.1 w and fails the aspect test.
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    length_est = perim / 2.0 - w
    if length_est < 3.0 * w:
        return False
    if design_class == "flat":
        return True
    return _dt_regular_and_within_cap(poly, max_width_mm)


# The percentile Melco's own patent (US9702070) is documented to use is 70;
# the spike measured 90 sits above every letterform junction spike (a serif
# crossbar's inscribed circle running sqrt(2) times its stroke) while still
# rejecting a wide compact blob. Not swept against 70/80/95 here -- flagged
# in the spike doc as the one open tuning question before this ships wider.
_DT_TIGHTEN_PERCENTILE = 90.0


def _dt_regular_and_within_cap(poly: Polygon, max_width_mm: float) -> bool:
    """A second opinion on `is_satin_candidate`'s call, read off the exact
    distance transform at the medial axis instead of `2*area/perimeter`.

    Local, per-point measurements are immune to the perimeter-based test's
    failure mode: boundary noise moves individual medial-axis radii by the
    noise amplitude, not by a global perimeter sum, so a compact blob's
    radii stay large (its true half-size) no matter how jittery its outline
    is. Two AND terms, exactly `docs/dt-classifier-spike-2026-08-02.md`'s
    recommended `VP90` arm:

    - **Regularity** (`2*sigma < mu` at skeletal pixels): a uniform-thickness
      stroke has a tight radius distribution; a blob's medial axis collapses
      toward its centre, spreading the radii out. This is what actually
      separates a ribbon from a blob here -- not `max_width_mm`, which both
      can satisfy.
    - **The 90th-percentile width stays under the cap**: `max` is a junction
      artefact (a serif crossbar's inscribed circle runs sqrt(2) times its
      stroke) and rejects real letterforms; `p90` strips that spike while
      still catching a genuinely wide blob.

    Returns True (defers to the caller's already-True verdict) on a
    degenerate raster -- a shape too small or thin to skeletonize is not
    this check's problem to solve, and failing closed here would convert a
    raster edge case into a fill verdict for a shape that may be a perfectly
    good ribbon.
    """
    field = build_shape_field(poly)
    if field is None or not field.skel.any():
        return True
    r = field.dist[field.skel]
    if r.size == 0 or r.mean() <= 0:
        return True
    if 2.0 * r.std() >= r.mean():
        return False
    p90_mm = 2.0 * np.percentile(r, _DT_TIGHTEN_PERCENTILE) / field.scale
    return p90_mm <= max_width_mm


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


def _split_sharp_corners(strokes: list[Stroke], half_mm: float) -> list[Stroke]:
    """Cut stroke spines at concentrated corners so each piece sews as its own
    column, meeting its neighbour in a mitred overlap at the joint.

    The turn at each sample is measured over a baseline of one half-width per
    side — the same resolution the crosses themselves have — so a smooth curve
    (turn spread over many widths, like the C fixture's 13 mm radius) never
    trips it, while the N's diagonal junctions, a star's points and a hexagon
    border's corners all do. Cut ends become free ends: the existing cap
    machinery extends each piece to the boundary, which is exactly the overlap
    a mitred satin joint wants.
    """
    if half_mm <= 0:
        return strokes
    out: list[Stroke] = []
    for st in strokes:
        pts = st.spine
        n = len(pts)
        seg = [math.dist(pts[i], pts[i + 1]) for i in range(n - 1)]
        spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
        if n < 5 or spacing <= 0:
            out.append(st)
            continue
        k = max(1, round(half_mm / spacing))
        if n <= 2 * k + 1 and not st.closed:
            out.append(st)          # shorter than one baseline: nothing to see
            continue

        # Turns are measured on a SMOOTHED copy of the spine (cuts are applied
        # to the original — indices align). The raw medial axis dips toward the
        # stem at every junction weld, and over a one-half-width baseline that
        # raster dip reads ~36 deg — the T fixture's bar was being cut at a
        # corner the artwork does not have. Smoothing flattens the dip; a real
        # corner (N diagonal 56 deg, hexagon 60, star point 100+) survives it.
        sm = _smooth(pts, 3, st.closed)
        idx = range(n) if st.closed else range(k, n - k)
        turns: list[tuple[float, int]] = []
        for i in idx:
            a, b, c = sm[(i - k) % n], sm[i], sm[(i + k) % n]
            d1 = math.atan2(b[1] - a[1], b[0] - a[0])
            d2 = math.atan2(c[1] - b[1], c[0] - b[0])
            turn = abs(math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi))
            turns.append((turn, i))

        # Strongest corners first, and no second cut within a baseline of one
        # already made — a corner is one apex, not every sample on its shoulder.
        cuts: list[int] = []
        for turn, i in sorted(turns, reverse=True):
            if turn < _SPLIT_TURN_DEG:
                break
            gap = (min(abs(i - j), n - abs(i - j)) for j in cuts) if st.closed \
                else (abs(i - j) for j in cuts)
            if all(g > 2 * k for g in gap):
                cuts.append(i)
        if not cuts:
            out.append(st)
            continue
        cuts.sort()

        def keep(piece: list[tuple[float, float]]) -> bool:
            return len(piece) >= 3 and \
                sum(math.dist(a, b) for a, b in zip(piece, piece[1:])) >= 0.6 * half_mm

        if st.closed:
            ring = cuts + [cuts[0] + n]
            for s0, s1 in zip(ring, ring[1:]):
                piece = [pts[j % n] for j in range(s0, s1 + 1)]
                if keep(piece):
                    out.append(Stroke(spine=piece, free_start=True,
                                      free_end=True, closed=False))
        else:
            bounds = [0, *cuts, n - 1]
            for bi, (s0, s1) in enumerate(zip(bounds, bounds[1:])):
                piece = pts[s0:s1 + 1]
                if not keep(piece):
                    continue
                out.append(Stroke(
                    spine=piece,
                    free_start=st.free_start if bi == 0 else True,
                    free_end=st.free_end if s1 == n - 1 else True,
                    closed=False,
                ))
    return out


def extract_strokes(poly: Polygon, *,
                     use_shapefield: bool = False,
                     ) -> tuple[list[Stroke], float, _WidthField | None]:
    """-> (strokes in mm, mean half-width in mm, local width field).

    Strokes are sorted longest first, so a letter's main stem sews before its
    serifs and the between-stroke hops stay short.

    `use_shapefield` (DT-first migration M1, off by default) routes the
    rasterize + `medial_axis(rng=0)` pair below through
    `digitizer_core.shapefield.build_shape_field` instead of the inline call
    that follows. Both paths compute the identical raster and the identical
    `medial_axis` result — the flag exists purely to prove the new, shared
    module byte-identical before anything downstream depends on it; see
    `shapefield.py`'s module docstring and
    `tests/test_shapefield_byte_identical.py`. Off (the default) never
    imports or executes any of `shapefield.py`'s work.
    """
    if use_shapefield:
        sf = build_shape_field(poly)
        if sf is None:
            return [], 0.0, None
        scale, ox, oy, skel, dist = sf.scale, sf.ox, sf.oy, sf.skel, sf.dist
    else:
        mask, scale, ox, oy = _rasterize(poly)
        if not mask.any():
            return [], 0.0, None
        # rng is REQUIRED for determinism: medial_axis breaks ties between
        # equally valid skeleton pixels in a randomly permuted order, and
        # unseeded it returns a different skeleton on every call — which
        # came out as the same artwork digitizing to different stitches run
        # to run.
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
    strokes = _split_sharp_corners(strokes, half_px / scale)
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
    # Found and fixed 2026-08-05 (satin self-overlap). First read as a
    # junction measurement artifact (`field.half_at()` reporting a MERGED
    # footprint where several strokes meet) and a local-neighbourhood
    # outlier cap was tried -- reverted, disproven by direct inspection:
    # `logo_alpha.png`'s `Sf5200f3f` stroke 0 (a glyph's apex, both ends
    # FREE, no junction node on this stroke at all) profiles as a smooth,
    # continuous, single-peaked taper across all 36 of its own stations --
    # half-width ramping 0.17 -> 4.67mm -> 0.17mm, no isolated spike a local
    # window could tell apart from its neighbours, because EVERY neighbour
    # near the peak agrees. This is the shape's real medial-axis width, not
    # noise: an "A"-like apex genuinely is that wide where its two legs
    # converge. It is real width, but width the corpus never validates satin
    # crosses for at all -- `SATIN_MAX_WIDTH_MM` is exactly the ceiling this
    # module's own classifier gates satin-vs-fill on ("ribbons wider than
    # this sew better as fill", machine.py), the same one `_stroke_
    # underlay`'s oversize check and `SPLIT_SATIN_ABOVE_MM` already reuse for
    # the identical reason -- so a flat per-station cap at that ceiling,
    # not a new number, is the same "don't extrapolate into an unvalidated
    # regime" call this module already made twice. Measured on `Sf5200f3f`:
    # eliminates all 2580 non-adjacent self-crossing segment pairs the
    # uncapped peak produced and drops the shape's own isolated coverage
    # peak from 9.57 to 3.41 layers (`tests/test_satin.py::
    # test_satin_crosses_do_not_self_overlap_across_a_wide_junction`,
    # `tests/test_preflight.py::
    # test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_glue`).
    #
    # This cap is a hard ceiling, not a proportional one, so it also (lightly)
    # touches a column whose GROWN width crosses the ceiling only because
    # directional pull comp (Law 22, axial) legitimately widened it a few
    # tenths of a millimetre past 5.0mm -- `tests/test_pushcomp.py`'s 4.5mm
    # bar grows to 5.1mm and loses ~0.02mm of that growth to this cap. That
    # is not a separate bug to route around: a satin cross this module will
    # not classify past 5.0mm in the first place should not be asked to sew
    # one past 5.0mm because comp grew it there either -- see that test's own
    # updated fixture comment.
    for i in range(n):
        width[i] = min(width[i], floors[i] * 1.6 + 0.2, machine.SATIN_MAX_WIDTH_MM / 2)

    # --- taper zones at free ends ------------------------------------------
    #
    # Where a stroke ends in a TAPERED TIP the corridor pinches to zero, and
    # the smoothed profile above — a median over neighbours — cannot follow
    # it down (it read 0.938 mm at the ribbon_curve tip whose true corridor
    # is 0). The containment fallback in `place` then decides the rails by
    # which discrete shrink factor happens to fit, and on the pinched side
    # the offsets jump between factors instead of ramping with the taper:
    # measured on ribbon_curve at 80 mm, the tip's pinched-side penetration
    # degenerated onto the spine (no factor fit), the next station's offset
    # popped to 0.93 mm — a 0.96 mm same-rail hole — and two stations later
    # the recovering offset cancelled the spine advance down to a 0.16 mm
    # crawl, tripping the short-stitch guard mid-taper. Capping the interior
    # taper-zone widths to the honest per-station ray measurement makes the
    # rails ramp with the taper itself: the same intervals measure 0.30-0.56.
    # The terminal station is NOT capped — its cross is the designed cap
    # finish — and a floor of half the minimum cross keeps a mid-zone ray
    # miss from collapsing a station that `place` can still fit.
    zs = ze = 0
    if not closed and n >= 4:
        while zs + 1 < n - 1 and raw[zs + 1] < _TAPER_ZONE_FRAC * fallback_half_mm:
            zs += 1
            width[zs] = min(width[zs],
                            max(raw[zs], machine.SATIN_MIN_CROSS_MM / 2))
        while ze + 1 < n - 1 - zs and \
                raw[n - 2 - ze] < _TAPER_ZONE_FRAC * fallback_half_mm:
            ze += 1
            width[n - 1 - ze] = min(width[n - 1 - ze],
                                    max(raw[n - 1 - ze], machine.SATIN_MIN_CROSS_MM / 2))

    # Containment still governs: a smoothed width can overshoot where the
    # ribbon pinches, and thread outside the artwork is the one defect this
    # module is never allowed to ship. Each side yields on its own — pulling
    # both in because one overshot drags the good rail off the artwork edge,
    # which is what left the fixture bar's cap bare by 0.06 mm.
    def place(px: float, py: float, sx: float, sy: float, w: float):
        for f in (1.0, 0.85, 0.7, 0.5, 0.3):
            q = (px + sx * w * f, py + sy * w * f)
            if poly.covers(SPoint(q)):
                return q
        return (px, py)

    for i, (px, py) in enumerate(spine):
        nx, ny = norms[i]
        rail_a.append(place(px, py, nx, ny, width[i]))
        rail_b.append(place(px, py, -nx, -ny, width[i]))

    # --- outer-rail density -----------------------------------------------
    #
    # Stations are spaced along the SPINE, but thread lands on the RAILS, and
    # on a bend the outer rail runs further than the spine by (half-width x
    # angle turned) — measured 0.59 mm between outer penetrations against the
    # 0.40 target on a tight ring, 47% under density. Where the faster rail
    # outruns SATIN_SPACING, extra stations are INTERPOLATED into that
    # interval: spine, normal angle, and width all lerp between two already
    # -filtered stations, so the proven profile is untouched, no new rays are
    # cast, and a straight column (every interval already at spacing) comes
    # out byte-identical. A first attempt fine-sampled the whole spine and
    # re-ran the profile instead — the width filters are sample-count-based,
    # so 3x sampling shrank their mm reach 3x and rail noise tripled (outer
    # p95 0.49 -> 1.04 mm). Interpolation is the version that does not touch
    # what already works.
    ref_a: list = [rail_a[0]]
    ref_b: list = [rail_b[0]]
    for i in range(1, n):
        # Only refine intervals that are genuinely over-wide: at exactly one
        # spacing, adv/SPACING is 1.0 plus float dust and a bare ceil() doubled
        # EVERY interval of a straight bar (measured: 120 crosses where 60
        # belong, alternating full and guard-mangled). And never refine the
        # cap zone — those stations are the deliberate terminal fan onto the
        # cap corners, and packing crosses into it rebuilds the starburst this
        # module exists to prevent. EXCEPT at a tapered tip: there is no fan
        # to protect (the rails pinch, the terminal cross is a fraction of the
        # column), and the tip's first interval is where the pinched rail
        # jumps — 0.96 mm on ribbon_curve — so the taper zone refines by the
        # same gate as everywhere else.
        in_taper = not closed and ((zs and i <= zs + 1)
                                   or (ze and i >= n - 1 - ze))
        near_cap = not closed and (i <= 2 or i >= n - 2) and not in_taper
        adv = max(math.dist(rail_a[i - 1], rail_a[i]),
                  math.dist(rail_b[i - 1], rail_b[i]))
        if near_cap or adv <= machine.SATIN_SPACING_MM * 1.3:
            ref_a.append(rail_a[i])
            ref_b.append(rail_b[i])
            continue
        m = int(math.ceil(adv / machine.SATIN_SPACING_MM))
        if in_taper:
            # In the taper zone the pieces must also stay ABOVE the guard
            # threshold: a bare ceil splits a 0.53 mm interval into 0.26 mm
            # halves, the guard fires on every one, and the retracted points
            # read as fresh ~0.8 mm same-rail steps — the defect rebuilt by
            # its own repair (measured on the ribbon tail before this floor).
            m = max(1, min(m, int(adv / machine.SATIN_SHORT_STITCH_AT_MM)))
        for j in range(1, m):
            t = j / m
            px = spine[i - 1][0] * (1 - t) + spine[i][0] * t
            py = spine[i - 1][1] * (1 - t) + spine[i][1] * t
            ang = angles[i - 1] * (1 - t) + angles[i] * t   # unwrapped: lerp-safe
            w = width[i - 1] * (1 - t) + width[i] * t
            nx, ny = math.cos(ang), math.sin(ang)
            ref_a.append(place(px, py, nx, ny, w))
            ref_b.append(place(px, py, -nx, -ny, w))
        ref_a.append(rail_a[i])
        ref_b.append(rail_b[i])
    return ref_a, ref_b


def _short_stitch_guard(rail_a: list, rail_b: list) -> list[tuple]:
    """Shorten alternate crosses where a rail's penetrations bunch up.

    -> [(pa, pb), ...] with the crowded side of every other cross pulled toward
    the middle. On the inside of a curve the rail is shorter than the spine, so
    penetrations land closer together than the satin spacing; below the
    threshold the needle starts re-entering the same hole and the edge frays.

    The pull is a FRACTION of the cross capped at an ABSOLUTE distance. Its job
    is to clear the previous needle hole, and a hole is the same size whatever
    the column width — but a plain fraction scales with the column, and on a
    wide column it threw the retracted penetration far past where any hole
    could be: 0.35 x a 2.78 mm cross moved the point 0.97 mm off its rail,
    which any rail-based density read (the pinned tests, tools/audit.py) sees
    as two ~1.0 mm same-rail gaps. Capped, the same stitch retracts 0.6 mm —
    two same-hole radii: a full radius clear of the old hole, still supporting
    the inner edge it was pulled from.
    """
    out = []
    for i, (pa, pb) in enumerate(zip(rail_a, rail_b)):
        if 0 < i and i % 2 == 1:
            if math.dist(pa, rail_a[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pa = _pull_short(pa, pb)
            if math.dist(pb, rail_b[i - 1]) < machine.SATIN_SHORT_STITCH_AT_MM:
                pb = _pull_short(pb, pa)
        out.append((pa, pb))
    return out


def _pull_short(p: tuple, toward: tuple) -> tuple:
    """Retract one penetration toward the far rail, by fraction-with-a-cap."""
    cross = math.dist(p, toward)
    f = machine.SATIN_SHORT_STITCH_PULL
    if cross > 1e-9:
        f = min(f, machine.SATIN_SHORT_STITCH_PULL_MAX_MM / cross)
    return (p[0] + (toward[0] - p[0]) * f, p[1] + (toward[1] - p[1]) * f)


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


def _round_corners(spine: list[tuple[float, float]], half_mm: float,
                   closed: bool) -> list[tuple[float, float]]:
    """Spread each sharp corner's turn across about one column width.

    The professional in-run corner (every file in the corpus) is a gradual
    fan: crosses rotate a few degrees each, spokes around the bend. That falls
    out of the geometry only if the SPINE bends gradually — a hard apex packs
    the whole turn into the two or three crosses nearest it, which is the
    uncontrolled sweep the N junction showed once splitting was demoted.
    Extra smoothing passes confined to a window around each apex turn the
    corner into an arc of roughly the column's own radius; straight stretches
    keep their exact line because the window never reaches them.
    """
    n = len(spine)
    if n < 5 or half_mm <= 0:
        return spine
    seg = [math.dist(spine[i], spine[i + 1]) for i in range(n - 1)]
    spacing = sorted(seg)[len(seg) // 2] if seg else 0.0
    if spacing <= 0:
        return spine
    k = max(1, round(half_mm / spacing))
    sm = _smooth(spine, 3, closed)
    apexes: list[int] = []
    idx = range(n) if closed else range(k, n - k)
    for i in idx:
        a, b, c = sm[(i - k) % n], sm[i], sm[(i + k) % n]
        d1 = math.atan2(b[1] - a[1], b[0] - a[0])
        d2 = math.atan2(c[1] - b[1], c[0] - b[0])
        turn = abs(math.degrees((d2 - d1 + math.pi) % (2 * math.pi) - math.pi))
        if turn >= 30.0 and (not apexes or i - apexes[-1] > k):
            apexes.append(i)
    if not apexes:
        return spine
    out = list(spine)
    for ap in apexes:
        lo, hi = ap - k, ap + k
        for _ in range(8):
            prev = list(out)
            for i in range(lo, hi + 1):
                j = i % n if closed else i
                if not closed and (j <= 0 or j >= n - 1):
                    continue
                a, b, c = prev[(j - 1) % n], prev[j], prev[(j + 1) % n]
                out[j] = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
    return out


def _split_points(pa: tuple[float, float], pb: tuple[float, float],
                  station: int, above_mm: float) -> list[tuple[float, float]]:
    """Intermediate penetrations for one cross, or [] when it needs none.

    A cross longer than `above_mm` is divided into k = ceil(len /
    SPLIT_SEGMENT_MM) segments with penetrations at j/k along it, the whole
    comb shifted by the station's phase of the stagger wave so consecutive
    stations never stack their holes (corpus: aligned split holes are the
    minority, 131 columns of 1,922 — see machine.py for all the numbers).

    Points are exact lerps on the A->B segment: `strip_splits` depends on
    that collinearity to remove them exactly. The shift is +-0.23 of one
    segment, so the shortest end segment is 0.77 * len/k — above 1.9 mm at
    the 5.0 threshold, comfortably clear of MIN_STITCH_MM — and the longest
    is 1.23 * len/k, under 3.7 mm for any splittable cross up to the format
    ceiling.
    """
    cross = math.dist(pa, pb)
    if cross <= above_mm:
        return []
    k = int(math.ceil(cross / machine.SPLIT_SEGMENT_MM))
    wave = machine.SPLIT_STAGGER_WAVE[station % machine.SPLIT_STAGGER_PERIOD]
    shift = machine.SPLIT_STAGGER_STEP_SEGS * wave
    out = []
    for j in range(1, k):
        t = (j + shift) / k
        out.append((pa[0] + (pb[0] - pa[0]) * t, pa[1] + (pb[1] - pa[1]) * t))
    return out


def _on_segment(a: tuple, p: tuple, b: tuple, eps: float = 1e-6) -> bool:
    """Is p strictly between a and b, on the segment to within eps mm?"""
    abx, aby = b[0] - a[0], b[1] - a[1]
    apx, apy = p[0] - a[0], p[1] - a[1]
    len2 = abx * abx + aby * aby
    if len2 <= eps * eps:
        return False
    if abs(apx * aby - apy * abx) > eps * math.sqrt(len2):
        return False
    t = (apx * abx + apy * aby) / len2
    return 0.0 < t < 1.0


def strip_splits(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """A satin run's points with split penetrations removed — rails only.

    The exact inverse of `_split_points`, for any instrument that reads a
    run's points as alternating rail penetrations: split points lie ON the
    segment between their neighbours (they are lerps along the cross), and no
    real rail penetration ever can — consecutive rail points always turn,
    because the return leg reverses direction and degenerate crosses are
    dropped at SATIN_MIN_CROSS_MM. Same reading contract as
    `stitches.strip_ties`; strip ties first on plan-level runs (tie bounces
    revisit one point, so their zero-length base segments never read as
    collinear here).
    """
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for i in range(1, len(points) - 1):
        if _on_segment(out[-1], points[i], points[i + 1]):
            continue
        out.append(points[i])
    out.append(points[-1])
    return out


def satin_stroke(poly: Polygon, stroke: Stroke, half_mm: float,
                 field: _WidthField | None = None,
                 split_above_mm: float | None = None,
                 end_cutback_mm: float = 0.0) -> list[tuple[float, float]]:
    """One stroke -> flat zigzag points (A1, B1, A2, B2, ...).

    Rails strictly alternate, so EVERY consecutive pair of points is a stitch
    that crosses the column: the outbound leg A(i)->B(i) square across, the
    return leg B(i)->A(i+1) leaning one spacing forward. That is what a satin
    column is on the machine.

    One exception, and it is fenced: a cross longer than `split_above_mm`
    (None = machine.SPLIT_SATIN_ABOVE_MM) carries intermediate split
    penetrations between its rail points — see the module docstring for the
    contract and `strip_splits` for the exact way back to pure rails.

    `end_cutback_mm` is push compensation (Law 24), applied to OPEN ends only.
    Zero is the shipped behaviour; stage 7 supplies the number when
    `PipelineConfig.directional_comp` is on.
    """
    spine = _smooth(stroke.spine, 3, stroke.closed)
    spine = _round_corners(spine, half_mm, stroke.closed)

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

    # Push compensation (Law 24). Pull comp is a WIDTH and stage 5 owns it;
    # push is a LENGTH and only this line of the pipeline knows where a column's
    # length ends. The stitches run across the column, so the fabric their
    # tension gathers is shoved out the ends — a column sewn flush to the
    # artwork cap lands past it, which is exactly what a border is later asked
    # to hide. Cutting the last cross back fixes it at the source.
    #
    # Only OPEN ends: an end at a junction is not a cap, it is tucked under the
    # arm it meets (`_JUNCTION_TUCK_MM` above), and shortening it would open the
    # gap that tuck exists to close. A closed stroke has no ends at all.
    #
    # `_trim_chain` leaves a stroke alone when the cutbacks would take it under
    # half a millimetre, so a short stub degrades to today's behaviour instead
    # of vanishing.
    if end_cutback_mm > 0 and not stroke.closed:
        c0 = end_cutback_mm if stroke.free_start else 0.0
        c1 = end_cutback_mm if stroke.free_end else 0.0
        if c0 or c1:
            spine = _trim_chain(spine, c0, c1)

    length = sum(math.dist(a, b) for a, b in zip(spine, spine[1:]))
    if length <= 0:
        return []

    steps = max(2, int(math.ceil(length / machine.SATIN_SPACING_MM)))
    spine = _resample(spine, steps)
    rail_a, rail_b = _rail_points(poly, spine, stroke.closed, half_mm, field)
    crosses = _short_stitch_guard(rail_a, rail_b)
    above = machine.SPLIT_SATIN_ABOVE_MM if split_above_mm is None else split_above_mm

    out: list[tuple[float, float]] = []
    prev_kept: tuple | None = None
    kept = 0
    for i, (pa, pb) in enumerate(crosses):
        if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
            continue  # rails pinched together: shared tip or degenerate cap
        # Corridor capping at a junction can leave consecutive crosses nearly
        # coincident — both penetrations landing in the previous needle holes.
        if prev_kept is not None and \
                math.dist(pa, prev_kept[0]) < 0.05 and math.dist(pb, prev_kept[1]) < 0.05:
            continue
        prev_kept = (pa, pb)
        # Rail order is CONSTANT: A, B, A, B, ... Flipping alternate crosses to
        # (B, A) makes consecutive crosses meet on the same rail, and the step
        # between them is then a hop ALONG that rail — one satin spacing long,
        # 0.41 mm measured, into the hole the previous penetration just made.
        # Keeping the order constant turns that step into the RETURN LEG of the
        # zigzag: same two penetrations, but the thread crosses the column
        # instead of running up its edge.
        #
        # An over-threshold stitch gets its split penetrations HERE, between
        # its rail points, from the final guarded geometry — so the guard,
        # the dedup and the rail order never see them. BOTH legs split: the
        # return leg B(i)->A(i+1) spans the same column as the cross (one
        # spacing of lean longer), and the corpus's split columns split every
        # traverse in both directions — splitting only the outbound leg would
        # leave every other stitch over-length. Stagger phase runs on the
        # KEPT-station count: dropped stations must not advance the wave.
        if out:
            out.extend(_split_points(out[-1], pa, kept, above))
        out.append(pa)
        out.extend(_split_points(pa, pb, kept, above))
        out.append(pb)
        kept += 1
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
    # Law 23's 1.45mm pitch / 0.82x-width figures are corpus-measured over
    # columns up to the corpus's own 4.5-7.0mm width bucket (docs/corpus-
    # laws-round3-2026-08-01.md law 22/23) -- and satin classification
    # (`is_satin_candidate`) gates on a shape's MEAN width (`ribbon_width_
    # mm`), so a multi-stroke glyph can stay classified satin overall while
    # one skeleton stroke's own LOCAL corridor runs well past SATIN_MAX_
    # WIDTH_MM (measured on `logo_alpha.png`'s `Sf5200f3f`: shape mean
    # ~5.0mm, one stroke's local width 0.33-10.33mm). The corpus's own
    # >7.0mm bucket is flagged "junk" (82% non-ribbon fragments) in that
    # same doc, so neither law 23's new figures nor the pre-law-23 defaults
    # were ever validated for a corridor that wide -- extrapolating either
    # one is a guess, not a corpus finding. Skip the zigzag pass entirely
    # for a stroke whose local width anywhere exceeds SATIN_MAX_WIDTH_MM
    # (the same corpus-validated ceiling `SPLIT_SATIN_ABOVE_MM` already
    # reuses, not a new number): the center-run walk above still covers it,
    # which is the honest, corpus-supported fallback rather than a chosen
    # pitch/width for a regime nobody measured.
    #
    # Found and fixed 2026-08-05: an independent stitch-geometry audit of
    # the initial law 23 landing caught `logo_alpha.png`'s DENSITY_STACKED
    # finding flipping warn -> block on exactly this shape (coverage_max
    # 13.11 -> 16.69, peak driven by the satin crosses' own pre-existing
    # self-overlap on this wide/blob stroke -- unrelated to law 23 and
    # unchanged by THIS fix -- with the widened, denser zigzag underlay
    # supplying just enough extra "glue" thread to bridge that pre-existing
    # near-miss over `_COVERAGE_MIN_PATCH_MM2`'s 25mm2 connected-patch
    # gate). See test_preflight.py's logo_alpha regression test.
    #
    # The self-overlap itself is FIXED, same day, separate pass: see
    # `_rail_points`'s own `SATIN_MAX_WIDTH_MM / 2` per-station cap comment
    # above (root cause: this same OVERSIZE stroke -- its own apex genuinely,
    # smoothly widens to ~9.3mm, no junction or measurement artifact
    # involved -- was still casting full-width crosses there; capped now the
    # same way the zigzag skip above already treats this regime, at the same
    # ceiling). This shape's `coverage_max` before any of these fixes was
    # 13.11 -- now 3.24, see the updated regression pin below.
    oversize = field is not None and any(
        field.half_at(p) * 2.0 > machine.SATIN_MAX_WIDTH_MM for p in spine)
    if style == "zigzag" and not oversize:
        steps = max(2, int(math.ceil(length / machine.SATIN_ZIGZAG_PITCH_MM)))
        sp = _resample(spine, steps)
        ra, rb = _rail_points(poly, sp, st.closed, ribbon_width_mm(poly) / 2, field)
        pts: list[tuple[float, float]] = []
        for i, (pa0, pb0) in enumerate(zip(ra, rb)):
            # Narrow both ends from the ORIGINALS — pulling pb toward an
            # already-moved pa drifts the zigzag off the column's center.
            # 0.09 (corpus law 23): each leg spans 0.82x the RAIL SPAN
            # (1 - 2*0.09), not the old 0.4x (1 - 2*0.3) -- the prior
            # narrowing left satin's zigzag underlay too under-specified to
            # actually anchor the rails it sits beneath.
            #
            # Defense in depth alongside the oversize skip above: `sp` is a
            # coarser resample than the `spine` the skip check walks, and
            # `_rail_points`'s own smoothing can measure a rail span the
            # per-point field check didn't quite catch. Cap the leg the same
            # way, at what a column pinned to SATIN_MAX_WIDTH_MM would
            # produce (SATIN_MAX_WIDTH_MM * 0.82 =~ 4.1mm) -- below that
            # width nothing changes (frac is exactly the corpus's 0.09);
            # above it, frac rises smoothly so leg length asymptotes toward
            # the cap instead of continuing to grow with a corridor width
            # the corpus never measured.
            rail_span = math.dist(pa0, pb0)
            frac = 0.09
            if rail_span > machine.SATIN_MAX_WIDTH_MM:
                capped_leg = machine.SATIN_MAX_WIDTH_MM * 0.82
                frac = max(frac, 0.5 * (1.0 - capped_leg / rail_span))
            pa = (pa0[0] + (pb0[0] - pa0[0]) * frac, pa0[1] + (pb0[1] - pa0[1]) * frac)
            pb = (pb0[0] + (pa0[0] - pb0[0]) * frac, pb0[1] + (pa0[1] - pb0[1]) * frac)
            if math.dist(pa, pb) < machine.SATIN_MIN_CROSS_MM:
                continue
            pts.extend((pa, pb) if i % 2 == 0 else (pb, pa))
        if len(pts) >= 2:
            runs.append(StitchRun(points=pts, kind=stitches.UNDERLAY,
                                  shape_id=shape_id))
    return runs


def _build_travel_graph(strokes: list[Stroke]):
    """-> (nodes, edges, adjacency) over the strokes' spines.

    The skeleton the strokes came from is one connected web for a connected
    shape, and the professional trick the corpus files all use is to TRAVEL
    along that web with the needle down — the leg is covered when the stroke
    it follows sews its own column later. Endpoints within 0.5 mm share a
    node; a stroke whose end lands on another's interior (a T's stem on its
    bar) splits that spine so the junction is reachable.
    """
    endpoints = []
    for st in strokes:
        endpoints += [st.spine[0], st.spine[-1]]
    segs: list[tuple[int, list]] = []
    for k, st in enumerate(strokes):
        sp = st.spine
        cuts: set[int] = set()
        for p in endpoints:
            best_i, best_d = None, 0.5
            for i in range(1, len(sp) - 1):
                d = math.dist(p, sp[i])
                if d < best_d:
                    best_i, best_d = i, d
            if best_i is not None:
                cuts.add(best_i)
        idxs = [0, *sorted(cuts), len(sp) - 1]
        for a, b in zip(idxs, idxs[1:]):
            if b > a:
                segs.append((k, sp[a:b + 1]))

    nodes: list[tuple[float, float]] = []

    def node_at(p) -> int:
        for i, q in enumerate(nodes):
            if math.dist(p, q) <= 0.5:
                return i
        nodes.append(p)
        return len(nodes) - 1

    edges: list[dict] = []
    adj: dict[int, list[int]] = {}
    for k, poly in segs:
        if len(poly) < 2:
            continue
        a, b = node_at(poly[0]), node_at(poly[-1])
        ei = len(edges)
        edges.append({"a": a, "b": b, "k": k, "pts": poly,
                      "len": sum(math.dist(p, q) for p, q in zip(poly, poly[1:]))})
        adj.setdefault(a, []).append(ei)
        adj.setdefault(b, []).append(ei)
    return nodes, edges, adj


def _graph_travel(cur, target, sewn: set[int], allow: set[int],
                  nodes, edges, adj) -> list[tuple[float, float]] | None:
    """Needle-down path from cur to target over UNSEWN spines, or None.

    Edges belonging to already-sewn strokes are forbidden: running stitches on
    top of finished satin show, which is the same reason the fill path prefers
    a trim over long travel across finished coverage.
    """
    def snap(p):
        best, bd = None, 0.8
        for i, q in enumerate(nodes):
            d = math.dist(p, q)
            if d < bd:
                best, bd = i, d
        return best

    s, t = snap(cur), snap(target)
    if s is None or t is None:
        return None
    if s == t:
        return []
    dist = {s: 0.0}
    prev: dict[int, tuple[int, int]] = {}
    pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t:
            break
        if d > dist.get(u, 1e18):
            continue
        for ei in adj.get(u, []):
            e = edges[ei]
            if e["k"] in sewn and e["k"] not in allow:
                continue
            v = e["b"] if e["a"] == u else e["a"]
            nd = d + e["len"]
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, ei)
                heapq.heappush(pq, (nd, v))
    if t not in prev:
        return None
    chain: list[list] = []
    u = t
    while u != s:
        pu, ei = prev[u]
        e = edges[ei]
        pts = list(e["pts"]) if e["a"] == pu else list(reversed(e["pts"]))
        chain.append(pts)
        u = pu
    chain.reverse()
    out: list[tuple[float, float]] = []
    for pts in chain:
        out.extend(pts if not out else pts[1:])
    return out


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
                start_near: tuple[float, float] | None = None,
                split_above_mm: float | None = None,
                end_cutback_mm: float = 0.0,
                use_shapefield: bool = False,
                ) -> tuple[list[StitchRun], dict]:
    """One satin-classified shape -> runs in sew order, plus the same report
    contract `stitch_shape` uses, so stage 7 can treat the two identically.

    `start_near` is where the needle is when this shape's turn comes.
    `split_above_mm` caps the stitch length before crosses split (None =
    machine.SPLIT_SATIN_ABOVE_MM; `math.inf` disables splitting — the
    mapping stage 7 applies for `PipelineConfig.split_satin = False`).

    `end_cutback_mm` is push compensation at open column ends (Law 24); 0.0 is
    the shipped behaviour. It is a length taken off the spine, NOT a shrink of
    `poly`, which is why it cannot live in stage 5 — see `satin_stroke`.

    `use_shapefield` forwards to `extract_strokes` — see its docstring. Off
    by default; stage 7 sets it from `cfg.extra["shapefield"]`.
    """
    report = {"too_thin": False, "jumps": 0, "empty": False}
    strokes, half_mm, field = extract_strokes(poly, use_shapefield=use_shapefield)
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
    kept: list[tuple[Stroke, list]] = []
    for st in strokes:
        pts = satin_stroke(poly, st, half_mm, field, split_above_mm,
                           end_cutback_mm)
        if len(pts) >= 4:
            kept.append((st, pts))
    if not kept:
        report["empty"] = True
        return [], report

    # The travel graph spans only strokes that will actually sew — a leg over
    # a stub the emitter skipped would never be covered by anything.
    nodes, g_edges, g_adj = _build_travel_graph([st for st, _ in kept])
    sewn: set[int] = set()

    runs: list[StitchRun] = []
    for ki, (st, pts) in enumerate(kept):
        # Wide columns carry zigzag underlay or their crosses float — every
        # wide-satin file in the corpus shows the support passes.
        if field is not None and st.spine:
            step = max(1, len(st.spine) // 8)
            halves = [field.half_at(p) for p in st.spine[::step]]
            stroke_w = 2.0 * (sum(halves) / len(halves)) if halves else 2.0 * half_mm
        else:
            stroke_w = 2.0 * half_mm
        eff_style = "zigzag" if (underlay_style != "none"
                                 and stroke_w > machine.SATIN_ZIGZAG_ABOVE_MM) \
            else underlay_style

        stroke_runs = [*_stroke_underlay(poly, st, eff_style, shape_id, field),
                       StitchRun(points=pts, kind=stitches.SATIN, shape_id=shape_id)]
        first_of_stroke = True
        for run in stroke_runs:
            cursor = runs[-1].points[-1] if runs else start_near
            if cursor is not None and \
                    math.dist(cursor, run.points[-1]) < math.dist(cursor, run.points[0]):
                run.points.reverse()
            if first_of_stroke and cursor is not None:
                # Between strokes, walk the unsewn web instead of lifting.
                direct = math.dist(cursor, run.points[0])
                if direct >= machine.TINY_STITCH_MM:
                    path = _graph_travel(cursor, run.points[0], sewn, {ki},
                                         nodes, g_edges, g_adj)
                    if path is not None and len(path) >= 2:
                        plen = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
                        # Same cap as the fill path: past this, travel under
                        # future coverage reads worse than the trim it saves.
                        if plen <= max(20.0, 4.0 * direct):
                            n = max(2, int(math.ceil(plen / machine.TRAVEL_STITCH_MM)) + 1)
                            runs.append(StitchRun(points=_resample(path, n),
                                                  kind=stitches.TRAVEL,
                                                  shape_id=shape_id))
            first_of_stroke = False
            runs.append(run)
        sewn.add(ki)

    if not any(r.kind == stitches.SATIN for r in runs):
        report["empty"] = True
        return [], report

    # Link EVERY consecutive run pair, underlay included. A short hop whose
    # stitch would stay INSIDE the shape is sewn as a stitch, not jumped —
    # this is where the corpus's 180-880-stitch runs come from: a column's
    # cap-extended start sits a millimetre past the underlay walk that led to
    # it, and lifting there fragmented every stroke into ~25-stitch runs
    # (measured: ~50 short jumps on the benchmark logo). A hop is only a jump
    # when it is long, or when the straight line between the runs would cross
    # outside the artwork (a counter's hole, the gap between two strokes) —
    # thread over bare fabric is a float no matter how short.
    poly_link = poly.buffer(0.1)
    for prev, cur in zip(runs, runs[1:]):
        a, b = prev.points[-1], cur.points[0]
        d = math.dist(a, b)
        if d < machine.TINY_STITCH_MM:
            continue
        if d <= trim_at_mm and poly_link.covers(LineString([a, b])):
            continue        # needle-down: encoder sews end -> start as one stitch
        cur.jump = True
        cur.trim = d > trim_at_mm
        report["jumps"] += 1
    return runs, report

