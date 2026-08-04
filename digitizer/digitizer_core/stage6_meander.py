"""Stage 6 — the meander mono tonal tier (photo plan, technique-menu row 9).

The Reef/Sfumato class: ONE continuous wandering run line whose local density
renders tone — dark fabric gets a tight, zigzagging meander, midtones a
sparser line, highlights almost nothing, with the fabric itself as the
highlight value. Reimplemented from the published math of Velho & Gomes,
"Digital halftoning with space filling curves", SIGGRAPH 1991: traverse the
image along a Hilbert curve and spend ink in proportion to the darkness the
curve is passing through. No reference implementation was consulted.

A sibling of `stage6_scanline.py` (row 8) with the same `(runs, report)`
contract, the same mm / y-down coordinates, and the same shared tone reader
(`stage6_blend.darkness_sampler`).

**The one structural adaptation from the paper, and why.** Velho & Gomes run
the curve at ONE fine resolution everywhere and modulate the ink released
along it — a printer's dot costs nothing where no dot is placed. Thread is
different: the curve itself IS the ink, so a fixed-resolution curve would lay
a line through every highlight at shadow spacing (or lift the needle at every
highlight crossing — hundreds of trims, destroying the genre's single-trim
selling point). So here the CURVE's resolution adapts to tone: a quadtree
over the shape's bounding square subdivides where local darkness demands
finer line spacing, the leaves are traversed in Hilbert order (the classic
recursion carries orientation through mixed depths), and the traversal visits
leaf centers. Darkness then drives three things along that one path, each
measurable from the emitted stitches:

1. **Line spacing** — the leaf size: 0.9 mm cells in shadow, doubling per
   level to 7.2 mm in the highlights. 0.9 mm plus the zigzag burst below
   puts adjacent thread passes ~0.4 mm apart at the excursion peaks —
   Sfumato's published Highest Density band (0.35–0.45 mm), the plan's
   density bound for this tier. See MEANDER_CELL_MM for why 0.9 exactly
   (it is load-bearing for the trim budget too).
2. **Penetration pitch** — 3.0 mm (FILL_STITCH_MM) at the light end down to
   `machine.MIN_STITCH_MM` at full black. Pitch is arc length along the
   curve; the floor is enforced on the emitted euclidean distance, so a
   hairpin of the curve cannot shorten a stitch under the floor.
3. **Zigzag bursts** — perpendicular excursions around the path, amplitude
   rising with darkness: the paper's ink-release mechanism, expressed as
   LINE WEIGHT. Measured plainly: the burst spreads the sewn line into a
   band ~2x its amplitude wide (which is what closes the finest cells to
   the Sfumato spacing at the peaks); the thread budget itself is carried
   by the other two knobs, and the oscillation mechanism is pinned by a
   walk-level test on a straight path (at tier level it reads as texture —
   the curve's own turns are the same size as the burst, by design). An
   excursion that would escape the shape collapses to the centerline, the
   same containment rule the scanline tier uses.

**Non-crossing by construction.** The Hilbert traversal of a 2:1-balanced
quadtree visits leaves in an order where consecutive leaves are edge-adjacent
and the center-to-center segment stays inside those two leaves, so segments
from different parts of the curve live in disjoint quad pairs and cannot
cross (the balance step is what makes the geometric argument hold for mixed
leaf sizes — without it a center chord can cut through a third quad). The
zigzag excursions stay well under half the local leaf size, preserving the
corridor argument. The test suite checks this property on the emitted
geometry, not on this paragraph.

**Highlight gaps: travel along the curve, never a lift.** Below the darkness
cutoff a stretch of curve sews no tone — but the needle stays down and
follows the curve at sparse travel pitch (`machine.TRAVEL_STITCH_MM`),
emitted as TRAVEL runs. Decided against lifting because a Hilbert curve
re-enters a highlight region once per boundary crossing, so lifting costs a
trim per crossing — tens per shape — while the genre ships single-digit trims
BECAUSE the wandering line is continuous; and the coarse (7.2 mm) highlight
cells mean the traveled line lays only ~0.15 mm of thread per mm² there — a
sparse wandering line through the lights is exactly what the Reef look is.
Leading and trailing travel (before the first and after the last real
stitch) is dropped: the path starts and ends where tone starts and ends. A
shape that is ENTIRELY highlight comes back `empty` with no thread at all —
honestly reported, and stage 7's never-drop-artwork ladder falls back to
tatami exactly as it does for the scanline tier.

The only breaks in the one path come from the curve leaving the polygon —
shape concavity, or the margin between the shape and its power-of-two
Hilbert square. A break sews a short straight link ONLY when that link
provably conflicts with nothing (checked against every needle-down segment
of the plan — blind bridging was tried first and its chords were precisely
the segments that violated the non-crossing check, because a chord across a
space-filling curve's interior has no free corridor); otherwise it LIFTS
the needle, which carries no thread and can cross nothing. Lifts are
counted in `report["jumps"]`, trims measured in the tests against the
genre's own single-digit budget, and the corner-aligned grid (see
`meander_fill`) is what keeps the count that low.

No underlay, and that is the craft consensus the plan records for the whole
fabric-as-value class, not an omission. No grain angle either: the meander
is isotropic by nature — there is no one direction the stitches run — so
`cfg.fill_angle_deg` is deliberately not consulted.

Strictly opt-in: nothing routes here except stage 7 on
`cfg.fill_technique == "meander_tonal"`.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.geometry import box as shp_box

from . import debugviz, machine, stitches
from .regions import Region
from .stage6_blend import SourcePixels, darkness_sampler
from .stitches import StitchRun

# --- The darkness -> geometry mapping ---------------------------------------

# Finest quadtree cell — the meander's line spacing in solid shadow. With
# the zigzag burst at full amplitude, adjacent passes approach to
# 0.9 - 2*0.25 = 0.4 mm at the excursion peaks — the Sfumato Highest
# Density band (0.35-0.45 mm). It also sits just under the needle floor,
# and that is load-bearing twice over: the walk emits penetrations by ARC
# length with a euclidean floor (so the needle shortcuts the curve's
# tightest wiggles by a fraction of a cell instead of ever throwing an
# illegal stitch), and the Hilbert boundary weave's characteristic 3-cell
# break (see `meander_fill`) measures 2.7 mm — under the 3.0 mm trim
# threshold, so a weave break costs a needle-up hop, not a trim.
MEANDER_CELL_MM = 0.9

# How many doublings above the finest cell the tree may rest at. 3 puts the
# coarsest (highlight/travel) cells at 0.9 * 2**3 = 7.2 mm — sparse enough
# that fabric reads as the highlight value, local enough that the traversal
# still meanders rather than striding across the shape.
MEANDER_COARSE_LEVELS = 3

# Darkness at which each finer cell size switches in, coarse to fine: below
# the first number nothing sews at all (the highlight cutoff — the curve is
# traveled, not stitched); past the last the curve runs at the finest cell.
# The cutoff is the scanline tier's own 0.08 (one shared definition of "too
# light to stitch"); the upper thresholds sit lower than scanline's because a
# meander lays thread along ONE line per cell where scanline lays a full row,
# so the same tone needs the finer cell sooner to reach the same coverage.
MEANDER_LEVEL_DARKNESS = (0.08, 0.35, 0.62)

# Penetration pitch ALONG the curve, light end -> dark end. Same span as the
# scanline tier: tatami's own stitch length down to the needle floor. Pitch
# is arc length — the stitches follow the curve — while the floor is
# enforced on the emitted euclidean distance, so a hairpin in the curve can
# never shorten a stitch under what the needle survives.
MEANDER_PITCH_MAX_MM = machine.FILL_STITCH_MM
MEANDER_PITCH_MIN_MM = machine.MIN_STITCH_MM

# Zigzag half-amplitude at full black — the burst that renders shadow. 0.25
# closes the finest 0.9 mm cell to ~0.4 mm between adjacent thread passes at
# the peaks (the Sfumato band), and stays under the 0.35 * cell corridor
# bound that keeps an excursion from reaching another pass.
MEANDER_AMP_MAX_MM = 0.25

# Tone is sampled at grain scale — same rationale (and same shared sampler)
# as the scanline tier: one dark pixel of JPEG noise must not flip a stitch.
MEANDER_BLUR_MM = 0.6

# The walk's substep when advancing along the curve. Small enough that a
# pitch lands within ~0.2 mm of its target arc position.
MEANDER_SUBSTEP_MM = 0.2

# Consecutive in-shape leaves further apart than this multiple of their mean
# cell size are a BREAK (the curve left the polygon between them): adjacent
# leaves of a 2:1-balanced tree sit at most ~1.06 mean-cells apart
# (same-size edge neighbours at exactly 1.0), so 1.25 separates adjacency
# from absence with margin on both sides.
MEANDER_ADJACENT_FACTOR = 1.25

# The longest gap a needle-down link may sew across (see the chaining block
# in `meander_fill` — a link is only sewn when it provably conflicts with
# nothing). One coarsest cell (7.2 mm) plus change: a link inside that range
# reads as the meander stepping to its neighbour; anything longer reads as a
# stray line laid across the rendering, and lifts instead.
MEANDER_LINK_MAX_MM = 8.0


def _t(darkness: float) -> float:
    """Darkness normalized over the sewing range [cutoff, 1] -> [0, 1]."""
    cutoff = MEANDER_LEVEL_DARKNESS[0]
    return min(1.0, max(0.0, (darkness - cutoff) / (1.0 - cutoff)))


def _pitch_mm(darkness: float) -> float:
    return MEANDER_PITCH_MAX_MM - (MEANDER_PITCH_MAX_MM - MEANDER_PITCH_MIN_MM) * _t(darkness)


def _amp_mm(darkness: float, cell_mm: float) -> float:
    return min(MEANDER_AMP_MAX_MM, 0.35 * cell_mm) * _t(darkness)


# --- The adaptive Hilbert traversal -----------------------------------------


def _desired_depth_grid(darkness_grid: np.ndarray, inside: np.ndarray,
                        max_depth: int) -> np.ndarray:
    """Per finest-cell target subdivision depth, 2:1-balanced.

    Depth `max_depth` = the finest (MEANDER_CELL_MM) cell; each level up doubles the
    cell. Cells outside the shape (and pure highlight) rest at the coarsest
    sewing-relevant depth. The balance pass then widens each fine region by
    one coarser-cell ring so no two edge-adjacent leaves differ by more than
    one level — the property the non-crossing argument in the module
    docstring rests on.
    """
    base = max(0, max_depth - MEANDER_COARSE_LEVELS)
    d = np.where(inside, darkness_grid, 0.0)
    depth = np.full(d.shape, base, dtype=np.int32)
    cutoff, mid, dark = MEANDER_LEVEL_DARKNESS
    depth[d >= cutoff] = max(base, max_depth - 2)
    depth[d >= mid] = max(base, max_depth - 1)
    depth[d >= dark] = max_depth

    # 2:1 balance: any cell within one depth-(k-1) cell of a depth>=k region
    # must itself reach depth k-1. Runs coarse-ward so the requirement
    # cascades.
    for k in range(max_depth, base, -1):
        need = (depth >= k).astype(np.uint8)
        if not need.any():
            continue
        r = 1 << (max_depth - k + 1)  # the coarser cell's size, in fine cells
        kernel = np.ones((2 * r + 1, 2 * r + 1), np.uint8)
        near = cv2.dilate(need, kernel).astype(bool)
        depth = np.maximum(depth, np.where(near, k - 1, 0))
    return depth


def _max_pyramid(grid: np.ndarray, levels: int) -> list[np.ndarray]:
    """pyr[m][j, i] = max of `grid` over the size-2**m quad at (i, j)."""
    pyr = [grid]
    for _ in range(levels):
        g = pyr[-1]
        pyr.append(g.reshape(g.shape[0] // 2, 2, g.shape[1] // 2, 2).max(axis=(1, 3)))
    return pyr


def _hilbert_leaves(depth_pyr: list[np.ndarray], prunable,
                    max_depth: int) -> list[tuple[float, float, int]]:
    """The adaptive traversal itself: -> leaf (cx, cy, size) in Hilbert
    order, coordinates in finest-cell units.

    The classic vector recursion (the curve's orientation is carried by the
    two frame vectors, so each child's sub-curve enters and exits where its
    neighbours expect) — with one change: recursion stops early wherever the
    depth pyramid says local tone needs no finer line spacing.

    `prunable(bx, by, s) -> bool` cuts off subtrees that have left the shape
    for good. It must be MONOTONE — a prunable node's children would all be
    prunable too — so that pruning a node and pruning its descendants are
    the same decision (the box-distance rule in `meander_fill` is: a child's
    box lies inside its parent's, so its distance can only grow while its
    own tolerance shrinks).
    """
    out: list[tuple[float, float, int]] = []

    def rec(x0: float, y0: float, xix: float, xiy: float,
            yix: float, yiy: float) -> None:
        s = int(abs(xix + xiy))  # one of the two components is always 0
        bx = int(x0 + min(0.0, xix) + min(0.0, yix))
        by = int(y0 + min(0.0, xiy) + min(0.0, yiy))
        m = s.bit_length() - 1  # log2(s)
        j, i = by >> m, bx >> m
        if prunable(bx, by, s):
            return
        if s == 1 or depth_pyr[m][j, i] <= max_depth - m:
            out.append((bx + s / 2.0, by + s / 2.0, s))
            return
        rec(x0, y0, yix / 2, yiy / 2, xix / 2, xiy / 2)
        rec(x0 + xix / 2, y0 + xiy / 2, xix / 2, xiy / 2, yix / 2, yiy / 2)
        rec(x0 + xix / 2 + yix / 2, y0 + xiy / 2 + yiy / 2,
            xix / 2, xiy / 2, yix / 2, yiy / 2)
        rec(x0 + xix / 2 + yix, y0 + xiy / 2 + yiy,
            -yix / 2, -yiy / 2, -xix / 2, -xiy / 2)

    n = depth_pyr[-1].shape  # sanity: top of the pyramid is 1x1
    assert n == (1, 1)
    side = depth_pyr[0].shape[0]
    rec(0.0, 0.0, float(side), 0.0, 0.0, float(side))
    return out


# --- The walk: one path, tone-driven penetrations ---------------------------


def _walk_polyline(polyline: list[tuple[float, float]], cells: list[float],
                   darkness, inside) -> list[tuple[tuple[float, float], bool]]:
    """Resample one continuous stretch of curve into penetrations.

    -> [(point, sewing)] in path order. The walk advances in small substeps
    ALONG the polyline (so the stitches follow the curve rather than
    cutting chords across its turns) and emits a penetration when the arc
    travelled since the last one reaches the local tone's pitch — with the
    needle floor enforced on the emitted euclidean distance too, so a
    hairpin turn between two penetrations can never produce a stitch the
    needle cannot survive; the walk keeps advancing until both hold.

    (A euclidean-clocked variant was measured first and rejected: the
    emitted distance stagnates around every U-turn of the curve, and at the
    dark end — where the cell is smaller than the pitch — that skipped
    enough of the curve to cost a quarter of the penetration density.)
    """
    if len(polyline) < 2:
        return []
    cutoff = MEANDER_LEVEL_DARKNESS[0]
    pts: list[tuple[tuple[float, float], bool]] = []
    side = 1

    d0 = darkness(*polyline[0])
    pts.append((polyline[0], d0 >= cutoff))
    prev = polyline[0]
    arc = 0.0  # arc length walked since the last emitted penetration

    for si in range(len(polyline) - 1):
        ax, ay = polyline[si]
        bx, by = polyline[si + 1]
        seg_len = math.hypot(bx - ax, by - ay)
        if seg_len < 1e-9:
            continue
        ux, uy = (bx - ax) / seg_len, (by - ay) / seg_len
        cell = min(cells[si], cells[si + 1])
        s = 0.0
        while s < seg_len:
            step = min(MEANDER_SUBSTEP_MM, seg_len - s)
            s += step
            arc += step
            cx, cy = ax + ux * s, ay + uy * s
            d = darkness(cx, cy)
            sewing = d >= cutoff
            if sewing:
                pitch = _pitch_mm(d)
                amp = _amp_mm(d, cell) * side
                cand = (cx - uy * amp, cy + ux * amp)
                if amp != 0.0 and not inside(cand):
                    cand = (cx, cy)
            else:
                pitch = machine.TRAVEL_STITCH_MM
                cand = (cx, cy)
            if arc >= pitch and math.dist(prev, cand) >= machine.MIN_STITCH_MM:
                pts.append((cand, sewing))
                prev = cand
                arc = 0.0
                if sewing:
                    side = -side
    return pts


def _runs_from_points(pts: list[tuple[tuple[float, float], bool]],
                      shape_id: str) -> list[StitchRun]:
    """Group one walk's penetrations into FILL / TRAVEL runs.

    A lone sewing penetration between travel stretches is demoted to travel —
    a single point is not a stitch, and keeping it as a one-point FILL run
    would invent a tone mark tone never asked for.
    """
    groups: list[tuple[bool, list[tuple[float, float]]]] = []
    for pt, sewing in pts:
        if groups and groups[-1][0] == sewing:
            groups[-1][1].append(pt)
        else:
            groups.append((sewing, [pt]))
    merged: list[tuple[bool, list[tuple[float, float]]]] = []
    for sewing, g in groups:
        if sewing and len(g) < 2:
            sewing = False
        if merged and merged[-1][0] == sewing:
            merged[-1][1].extend(g)
        else:
            merged.append((sewing, list(g)))
    runs = []
    for sewing, g in merged:
        pts_split = stitches.split_long_moves(g, machine.MAX_STITCH_MM)
        if not pts_split:
            continue
        runs.append(StitchRun(points=pts_split,
                              kind=stitches.FILL if sewing else stitches.TRAVEL,
                              shape_id=shape_id))
    return runs


def _densify(a: tuple[float, float], b: tuple[float, float],
             step_mm: float) -> list[tuple[float, float]]:
    """Points from a (exclusive) to b (inclusive), no step longer than
    step_mm. Deliberately a local copy of the same three lines stage 6's
    fill and stage 7 each carry, for the same reason stage 7 documents: a
    link's pitch is this tier's own decision, not an import of a sibling's
    private."""
    d = math.dist(a, b)
    if d <= step_mm:
        return [b]
    n = math.ceil(d / step_mm)
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(1, n + 1)]


# Spatial-hash cell for the link conflict check. Comfortably larger than any
# stitch (max ~3 mm), so a segment touches at most a handful of cells.
_HASH_CELL_MM = 4.0


def _segments_conflict(p1, p2, p3, p4) -> bool:
    """True when the two segments cross, T-touch, or overlap collinearly in
    more than a shared endpoint. Sharing an endpoint is the one legal
    contact (consecutive stitches do it constantly) — unless the segments
    also double back along one line, which is thread laid on thread."""
    eps = 1e-9

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    shared = [(u, v) for u in (p1, p2) for v in (p3, p4)
              if abs(u[0] - v[0]) < eps and abs(u[1] - v[1]) < eps]
    if shared:
        # Legal contact unless collinear AND extending the same way.
        u, _ = shared[0]
        o1 = p2 if u is p1 else p1
        o2 = p4 if (abs(u[0] - p3[0]) < eps and abs(u[1] - p3[1]) < eps) else p3
        if abs(orient(u, o1, o2)) > eps:
            return False
        dot = (o1[0] - u[0]) * (o2[0] - u[0]) + (o1[1] - u[1]) * (o2[1] - u[1])
        return dot > eps
    d1 = orient(p3, p4, p1)
    d2 = orient(p3, p4, p2)
    d3 = orient(p1, p2, p3)
    d4 = orient(p1, p2, p4)
    if ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
       ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)):
        return True
    if abs(d1) < eps and abs(d2) < eps and abs(d3) < eps and abs(d4) < eps:
        # Collinear: conflict if the projections overlap at all.
        if abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1]):
            lo1, hi1 = sorted((p1[0], p2[0]))
            lo2, hi2 = sorted((p3[0], p4[0]))
        else:
            lo1, hi1 = sorted((p1[1], p2[1]))
            lo2, hi2 = sorted((p3[1], p4[1]))
        return min(hi1, hi2) - max(lo1, lo2) > eps
    # An endpoint landing ON the other segment's interior (T-touch).
    def on_segment(p, a, b):
        return (abs(orient(a, b, p)) < eps
                and min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
                and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps)
    return (on_segment(p1, p3, p4) or on_segment(p2, p3, p4)
            or on_segment(p3, p1, p2) or on_segment(p4, p1, p2))


class _SegmentHash:
    """Every needle-down segment of the plan so far, hashed on a coarse
    grid, so a candidate link can be tested against exactly the segments
    near it instead of all of them."""

    def __init__(self) -> None:
        self.segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
        self.grid: dict[tuple[int, int], list[int]] = {}

    @staticmethod
    def _keys(a, b):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for i in range(math.floor(x0 / _HASH_CELL_MM),
                       math.floor(x1 / _HASH_CELL_MM) + 1):
            for j in range(math.floor(y0 / _HASH_CELL_MM),
                           math.floor(y1 / _HASH_CELL_MM) + 1):
                yield (i, j)

    def add(self, a, b) -> None:
        idx = len(self.segs)
        self.segs.append((a, b))
        for key in self._keys(a, b):
            self.grid.setdefault(key, []).append(idx)

    def conflicts(self, a, b) -> bool:
        seen: set[int] = set()
        for key in self._keys(a, b):
            for idx in self.grid.get(key, ()):
                if idx in seen:
                    continue
                seen.add(idx)
                s, t = self.segs[idx]
                if _segments_conflict(a, b, s, t):
                    return True
        return False


def meander_fill(region: Region, source_pixels: SourcePixels, cfg
                 ) -> tuple[list[StitchRun], dict]:
    """One shape -> its meander tonal runs plus the standard tier report.

    Same `(runs, report)` contract as every stage-6 sibling: `too_thin`,
    `jumps` (needle lifts a concavity forced), `empty` (nothing sewn — for
    this tier that includes "the shape is entirely highlight", a correct
    outcome; stage 7's fallback ladder decides what happens next).
    """
    poly = region.polygon
    report = {"too_thin": False, "jumps": 0, "empty": False}
    if poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
        report["too_thin"] = True

    minx, miny, maxx, maxy = poly.bounds
    span = max(maxx - minx, maxy - miny)
    if span <= 0:
        report["empty"] = True
        return [], report
    max_depth = max(1, math.ceil(math.log2(span / MEANDER_CELL_MM)))
    side = 1 << max_depth  # finest cells per bounding-square edge
    # The shape sits in the CORNER of the Hilbert square, not its center:
    # the square's side is the next power of two above the shape, so there
    # is always a margin, and where the shape sits in it decides where the
    # curve's boundary weave lands and how long the breaks are. Measured
    # end to end on the fixtures (trims after chaining and linking): ramp
    # 3 corner-aligned vs 5 centered, drone render 7 vs 10 — the corner
    # placement leaves shorter, more linkable breaks.
    ox, oy = minx, miny

    shapely.prepare(poly)

    def inside(pt: tuple[float, float]) -> bool:
        return poly.covers(Point(pt))

    darkness = darkness_sampler(source_pixels, MEANDER_BLUR_MM)

    # Fine-grid tone + membership, then the balanced depth field and its
    # max-pyramid — everything the adaptive traversal consults.
    xs = ox + (np.arange(side) + 0.5) * MEANDER_CELL_MM
    ys = oy + (np.arange(side) + 0.5) * MEANDER_CELL_MM
    dark_grid = np.zeros((side, side))
    in_grid = np.zeros((side, side), dtype=bool)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            if inside((x, y)):
                in_grid[j, i] = True
                dark_grid[j, i] = darkness(x, y)

    if not in_grid.any():
        report["empty"] = True
        return [], report

    depth = _desired_depth_grid(dark_grid, in_grid, max_depth)
    depth_pyr = _max_pyramid(depth, max_depth)

    # The traversal prunes a subtree once its box no longer meets the shape
    # at all. Monotone in the sense `_hilbert_leaves` requires: a child's
    # box lies inside its parent's, so a disjoint parent has only disjoint
    # children.
    def prunable(bx: int, by: int, s: int) -> bool:
        node_box = shp_box(ox + bx * MEANDER_CELL_MM, oy + by * MEANDER_CELL_MM,
                           ox + (bx + s) * MEANDER_CELL_MM,
                           oy + (by + s) * MEANDER_CELL_MM)
        return not poly.intersects(node_box)

    # A leaf's VISIT point is its center when the center is inside. A leaf
    # whose center falls outside but whose cell still genuinely overlaps the
    # shape is visited at a point clipped into the overlap
    # (`representative_point`, deterministic) — the clipped point stays
    # inside the leaf's own quad, so the corridor argument behind the
    # non-crossing property is untouched. A cell that has left the shape is
    # dropped, and the path breaks there with a needle-up lift. Pinning
    # such cells' visits onto the boundary instead — sewing through the
    # weave — was built and measured first: it saved about one trim in three
    # on the ramp fixture but collapsed distinct quad corridors onto one
    # boundary strip, and the measured non-crossing check caught its own
    # V-dips cutting each other. The lift is the version that keeps the
    # property absolute.
    leaves: list[tuple[float, float, float, tuple[float, float]]] = []
    for cx, cy, s in _hilbert_leaves(depth_pyr, prunable, max_depth):
        x = ox + cx * MEANDER_CELL_MM
        y = oy + cy * MEANDER_CELL_MM
        c = s * MEANDER_CELL_MM
        if inside((x, y)):
            leaves.append((x, y, c, (x, y)))
            continue
        half = c / 2.0
        overlap = shp_box(x - half, y - half, x + half, y + half).intersection(poly)
        if overlap.is_empty or overlap.area < 1e-6:
            continue
        p = overlap.representative_point()
        leaves.append((float(p.x), float(p.y), c, (x, y)))
    if len(leaves) < 2:
        report["empty"] = True
        return [], report

    # Split the leaf sequence into continuous stretches at breaks — judged
    # on the CELL CENTERS (grid-exact adjacency), not the clipped visit
    # points, so a clip can neither invent a break nor hide one.
    stretches: list[tuple[list[tuple[float, float]], list[float]]] = [([], [])]
    prev_center: tuple[float, float] | None = None
    prev_cell = 0.0
    for x, y, c, center in leaves:
        pl, cl = stretches[-1]
        if pl:
            limit = MEANDER_ADJACENT_FACTOR * (prev_cell + c) / 2.0
            if math.dist(prev_center, center) > limit:
                stretches.append(([], []))
                pl, cl = stretches[-1]
        pl.append((x, y))
        cl.append(c)
        prev_center, prev_cell = center, c

    # A break between two stretches either LIFTS the needle or sews a short
    # straight link — and the link is only allowed when it PROVABLY conflicts
    # with nothing. A chord across a space-filling curve's interior has no
    # corridor of its own (the curve owns the whole interior), so unlike the
    # curve's segments its safety cannot be argued — it is checked instead:
    # against every needle-down segment of every stretch (all of which exist
    # by the time the chain runs), for proper crossings AND collinear
    # overlap, via `_conflicts`. A chord that fails, leaves the shape, or
    # is simply long becomes a lift: counted in `jumps` and, past
    # TRIM_AT_MM, a trim.
    #
    # Each stretch is walked and trimmed to its sewing (leading/trailing
    # travel dropped — the path starts and ends where tone does; a stretch
    # with no sewing at all is dropped whole, since with a lift on either
    # side its travel would connect nothing). Then the stretches are chained
    # nearest-endpoint-first, either way round — their geometry is fixed, so
    # reordering cannot affect the non-crossing property, but it decides
    # which gaps the needle has to cross at all.
    pieces: list[list[StitchRun]] = []
    for polyline, cells in stretches:
        stretch_runs = _runs_from_points(
            _walk_polyline(polyline, cells, darkness, inside), region.shape_id)
        while stretch_runs and stretch_runs[0].kind == stitches.TRAVEL:
            stretch_runs.pop(0)
        while stretch_runs and stretch_runs[-1].kind == stitches.TRAVEL:
            stretch_runs.pop()
        if stretch_runs:
            pieces.append(stretch_runs)

    def _reversed_piece(piece: list[StitchRun]) -> list[StitchRun]:
        return [StitchRun(points=list(reversed(r.points)), kind=r.kind,
                          shape_id=r.shape_id) for r in reversed(piece)]

    seg_hash = _SegmentHash()
    for piece in pieces:
        prev_end = None
        for r in piece:
            if prev_end is not None:
                seg_hash.add(prev_end, r.points[0])
            for a, b in zip(r.points, r.points[1:]):
                seg_hash.add(a, b)
            prev_end = r.points[-1]
    slack = poly.buffer(0.01)
    shapely.prepare(slack)

    runs: list[StitchRun] = []
    remaining = list(range(len(pieces)))
    while remaining:
        if not runs:
            pick, flip = remaining[0], False  # curve order seeds the chain
        else:
            here = runs[-1].points[-1]

            def _gap(i: int) -> tuple[float, float]:
                return (math.dist(here, pieces[i][0].points[0]),
                        math.dist(here, pieces[i][-1].points[-1]))

            pick = min(remaining, key=lambda i: (round(min(_gap(i)), 6), i))
            fwd, bwd = _gap(pick)
            flip = bwd < fwd
        remaining.remove(pick)
        piece = _reversed_piece(pieces[pick]) if flip else pieces[pick]
        if runs:
            a, b = runs[-1].points[-1], piece[0].points[0]
            d = math.dist(a, b)
            linkable = (d <= MEANDER_LINK_MAX_MM
                        and slack.covers(LineString([a, b]))
                        and not seg_hash.conflicts(a, b))
            if linkable:
                seg_hash.add(a, b)
                inner = _densify(a, b, machine.TRAVEL_STITCH_MM)[:-1]
                if inner:
                    runs.append(StitchRun(points=inner, kind=stitches.TRAVEL,
                                          shape_id=region.shape_id))
            else:
                piece[0].jump = True
                piece[0].trim = d > machine.TRIM_AT_MM
                report["jumps"] += 1
        runs.extend(piece)

    if not any(r.kind == stitches.FILL for r in runs):
        runs = []
    if not runs:
        report["empty"] = True
        report["jumps"] = 0

    if cfg.debug_dir and runs:
        debugviz.stage6_meander_path(Path(cfg.debug_dir), runs,
                                     (maxx - minx, maxy - miny))

    return runs, report
