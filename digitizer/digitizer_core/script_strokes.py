"""A script word sewn as the pen wrote it (`cfg.script_strokes`, built OFF
2026-10-26; Kent: "Measure, then build OFF").

THE PRO'S RULE (read off his files by `tools/script_census.py` and the pen
order of each colour block, 2026-10-26). A joined or italic script word --
Bridge's bold brush "Bridge", Tires' monoline "ires", To a T's brush
"achine" -- is satin columns that FOLLOW THE PEN: one column per stroke (a
bowl, a stem, an arch; Bridge hat B 5, r 3, i 1, d 3, g 4, e 2), crosses
square to the stroke as it turns (square share 0.77 / 0.87 on Bridge hat /
LC), every move inside a word under thread still to come. Ours sewed 14
columns at clashing angles across a skeleton that welds the fused baseline
into one 22.8 mm stroke from the i's top through the d to the g -- crosses
running UP the letters along the baseline, not across the pen's strokes.

WHAT A SCRIPT WORD IS (`script_word`). One shape, not text (the letter door
refuses it: aspect 2.6 on Bridge, 3.8 on Tires, against its 1.4 ceiling, and
a cluster of one where a word needs three), that reads as a written word:
wider than tall (`SCRIPT_ASPECT_MIN`), several strokes deep (`SCRIPT_
CROSSINGS_MIN` ink runs across its middle), a pen line long for its height
(`SCRIPT_SKELETON_MIN_HEIGHTS`), one pen's width throughout, if a brush's
(`SCRIPT_WIDTH_CV_MAX`), and no hole bigger than a letter's counter
(`SCRIPT_HOLE_MAX_FRAC`). Over the 21 pro-paired jobs (L9's cache, 235
shapes of 20 mm2 and up) it reads 7: Bridge hat and LC, Tires' "ires", To a
T's "achine" on hat, LC and both beanies -- every script word the corpus
holds, nothing else. n = 3 artworks: a rule read off three artworks, not a
rate; the nearest refusal is Golden Tee's fused italic GOLF, on width CV
alone (0.455 against 0.43).

WHERE THE PEN WENT (`ink_grid`). Read on the artwork's own pixels when the
pipeline hands them over: each pixel projected onto the ground-to-ink colour
axis, the PATH taken on the ink's core (`INK_PATH_T`), the width on its
half-max edge (`INK_EDGE_T`). On Bridge at 63 mm the trace closed the g's
and the e's counters and fused the i's dot into its stem; the ink's core has
them open and apart, so the path follows the bowls round instead of
running along the fused baseline. With no pixels, no contrast, or a reading
the artwork's texture shatters (Tires' bevel, `INK_EDGES_RATIO_MAX`), the
traced polygon is read instead (`polygon_grid`).

WHAT IT BUILDS (`script_columns`). The path's medial axis (the satin
tier's own pruning and junction clustering) is cut into PEN STROKES: at a
junction two arms that continue within `WELD_MAX_DEG` of straight are one
stroke -- the pen goes THROUGH a crossing -- and the rest end there; a stroke
that turns more than `CUSP_DEG` within a stroke width (a cusp: the i's foot
turning into the join) is two. Each stroke is stationed at the satin pitch
with crosses SQUARE to its own smoothed direction, reaching the traced
POLYGON's outline on both sides, but never more than `REACH_HALVES` of its
drawn local half-width, so a cross stops at a junction instead of sweeping
through the stroke it meets. The polygon, not the ink, because the ground
under the word is knocked out to the polygon: a counter the trace closed
and the rails opened would show bare garment (Bridge hat: 2.8 mm2 with no
ground under it). Where the polygon runs on past the drawn edge (that closed
counter) the cross stops at the drawn edge (`CLOSED_GAP_MM`), and what no
stroke reaches is a patch (`uncovered`). A stroke that ends on a longer one
is cut back to its edge. Strokes and patches go to `columns.column_runs` as
one word -- pull on the rails, the cross floor, split satin, the walk that
sews each span's satin on its last visit and runs under it on the earlier
ones -- then `monoline.py`'s clean-ups for a joined word (underlay off
finished satin, hops buried under satin to come).

WIDTH. The rails sit on the polygon's outline plus the fabric's own pull,
as every Column letter's do. Measured on Bridge (the pipeline's ink read,
half-max): the drawn stroke is 1.76 mm at hat width, 2.12 at LC; the pro's
crosses are 1.56 / 1.78 (needle to needle), ours 2.0-2.8 (the drawn stroke
plus 0.4 mm a side). Matching him needs a smaller pull on script strokes: a
physical constant (ROADMAP gate 1), NOT built here.

WHAT IT CANNOT DO. Open the counters the trace closed (the ground is
knocked out there), sew a fused word letter by letter (the pro's letters are
apart, ours touch: the walk crosses the word under its own thread instead),
or re-set the word: the pro drew Bridge again in a taller font of his own,
a design call no trace reproduces.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from . import stitches

# ------------------------------------------------------------------ the door
#: bbox width over height: the letter door's own aspect ceiling, read the
#: other way -- a script word is what that ceiling refuses
SCRIPT_ASPECT_MIN = 1.4
#: median ink runs across three lines at 35 / 50 / 65 % of the height:
#: Bridge 5 (hat) / 6 (LC), Tires 7, To a T 11; Golden Tee's swoosh 3
SCRIPT_CROSSINGS_MIN = 5
#: medial-axis length over height: a word is a long pen line for its height
#: (script 6.3-8.8)
SCRIPT_SKELETON_MIN_HEIGHTS = 4.0
#: coefficient of variation of the half-width along the medial axis: one
#: pen, if a brush one. Script 0.18-0.41 (To a T's brush "achine" 0.40-0.41
#: on its four jobs); the one shape refused on this gate ALONE is Golden
#: Tee's fused italic GOLF at 0.455 -- a thin margin, n = 3 artworks -- and
#: the frames, ropes and bands read 0.48-0.92
SCRIPT_WIDTH_CV_MAX = 0.43
#: the largest hole over the convex hull: counters only (script <= 0.024;
#: a frame, a band or a badge holding other art 0.05-0.65)
SCRIPT_HOLE_MAX_FRAC = 0.05
#: below this the medial axis is junction noise, not strokes
SCRIPT_MIN_AREA_MM2 = 20.0
_ROWS = (0.35, 0.5, 0.65)
_READ_PX_PER_MM = 10.0

# ----------------------------------------------------------- the ink
#: the ink reading's grid: this many pixels across the traced stroke, between
#: the satin tier's own 6 px/mm and 20 (Bridge hat 8.1, Tires 6), and never
#: over `INK_MAX_PX` on the long side -- the raster the satin tier's skeleton
#: helpers are tuned on. At a flat 20 px/mm Tires' 4.4 mm stroke was 88 px
#: across and its axis shattered into 608 edges
INK_PX_ACROSS = 16.0
INK_PX_PER_MM_MIN, INK_PX_PER_MM_MAX = 6.0, 20.0
INK_MAX_PX = 1200
#: a hole in the ink's core smaller than this is a speck of JPEG, not a counter
INK_MIN_HOLE_MM2 = 0.1
#: the ink's path is refused (the polygon read instead) when its skeleton has
#: more than this many times the polygon's edges, plus `_INK_EDGES_SLACK`: a
#: reading the artwork's texture shattered (a bevel, a highlight)
INK_EDGES_RATIO_MAX = 3.0
_INK_EDGES_SLACK = 6
#: share of the way from ground to ink: the PEN PATH is the ink's core (a
#: blurred join between two letters falls under it, a stroke's centre never
#: does: Bridge's g and e counters, closed in the trace, are open at 0.85) ...
INK_PATH_T = 0.85
#: ... and the DRAWN EDGE is half-max, where a stroke's width is read
INK_EDGE_T = 0.5
#: ink and ground at least this far apart (Lab + alpha) or there is no reading
INK_MIN_DE = 15.0
#: ink further than this from the traced polygon is another shape's
SCRIPT_INK_REACH_MM = 0.6
#: a core part smaller than this is a speck, not a stroke (an i's dot is ~1 mm2)
INK_MIN_PART_MM2 = 0.15

# ----------------------------------------------------------- the pen strokes
#: two arms at a junction whose directions continue within this many degrees
#: of straight are one pen stroke: the pen carries on through a junction and
#: round a bend. The pro's columns hand over at a median 1 deg on Tires, 5 on
#: To a T's "achine", 23 on Bridge LC (`tools/script_flow.py`); welded at 40
#: ours turned 47-75 deg at the hand-over, at 60 (with `CUSP_DEG` 120) 3 /
#: 22 / 20. At 90 Tires' junctions left 22 mm2 of the word to patches
WELD_MAX_DEG = 60.0
#: a stroke turning more than this within one stroke width is a cusp -- the
#: pen reversing -- and is two strokes; anything gentler is one, its crosses
#: turned round the bend by `CROSS_SIGMA_HALVES`
CUSP_DEG = 120.0
#: a cross reaches the outline, but no further from its station than this
#: many of its stroke's local drawn half-widths (a junction blob is not a
#: stroke). 2.0, not 1.5: a cross turned round a bend reaches the outer corner
#: on the diagonal (1.41 half-widths at 90 deg, more beyond); at 1.5 the
#: bends left Tires 22 mm2 for patches, at 2.0 10
REACH_HALVES = 2.0
#: an arm's direction is read between these distances from its node, in
#: half-widths: past the junction blob, inside the arm
_ARM_FROM, _ARM_TO = 1.0, 3.0
#: a free end runs on along its tangent up to this many half-widths, to its
#: cap (stations off the polygon are not sewn)
_CAP_HALVES = 3.0
#: on an ink reading a cross stops at the DRAWN edge where it would run into a
#: counter the trace closed (Bridge's g and e: 2.8 mm2 with no ground under
#: them; a cross to the polygon fanned across them) more than this short of
#: the polygon's edge -- and at the polygon's own edge otherwise. The fabric's
#: pull, so a trace a pull fatter than the ink still sews to its edge
CLOSED_GAP_MM = 0.4
#: polygon the strokes leave uncovered (a closed counter, a fused join the
#: pen path skips, a wedge between two strokes) is sewn as a straight patch
#: column in the same walk: pieces of at least this ...
PATCH_MIN_MM2 = 0.15
#: ... once slivers this thin (the pull covers them) are opened away ...
PATCH_SLIVER_MM = 0.1
#: ... each cross running on this far under the strokes round it
PATCH_TUCK_MM = 0.3
#: the stations sit on the skeleton Gaussian-smoothed along its length with
#: this many drawn half-widths of sigma (`smooth_spine`) -- little, so a cross
#: keeps the stroke's middle and reaches both edges ...
SPINE_SIGMA_HALVES = 0.75
#: ... and each cross lies square to the pen path smoothed this much, so the
#: crosses turn as a hand turns them. Read off the pro's own centrelines
#: (`tools/script_flow.py`, kinks over 35 deg within 1 mm, per 10 mm): his
#: 0.7 / 1.3 / 2.4 / 0.8 on Bridge hat / LC / Tires / To a T hat; ours at 1
#: half-width 3.1 / 3.4 / 2.5 / 1.8, at 2: 2.1 / 1.8 / 1.0 / 1.4 -- the
#: smallest sigma that brings every file near his
CROSS_SIGMA_HALVES = 2.0
_SPINE_STEP_MM = 0.1
#: crosses are cast this many times per pitch along the spine, then kept one
#: per pitch of the faster rail
_STATION_SUBSTEPS = 4
#: a piece shorter than this many half-widths is not split off at a corner
_MIN_PIECE_HALVES = 3.0
#: a stroke shorter than this many half-widths (not a dot) is a knot of the
#: axis, dropped (Tires' r shoulder: a loop round a pinhole, crosses spiking)
_MIN_STROKE_HALVES = 4.0


@dataclass(frozen=True)
class ScriptReading:
    """The door's five numbers for one polygon (`script_reading`)."""

    aspect: float
    crossings: tuple[int, ...]
    skeleton_heights: float
    width_cv: float
    hole_frac: float
    stroke_mm: float

    @property
    def is_script(self) -> bool:
        return (self.aspect >= SCRIPT_ASPECT_MIN
                and sorted(self.crossings)[len(self.crossings) // 2] >= SCRIPT_CROSSINGS_MIN
                and self.skeleton_heights >= SCRIPT_SKELETON_MIN_HEIGHTS
                and self.width_cv <= SCRIPT_WIDTH_CV_MAX
                and self.hole_frac <= SCRIPT_HOLE_MAX_FRAC)


@lru_cache(maxsize=1024)
def _reading(wkb: bytes) -> ScriptReading | None:
    import cv2
    from shapely import wkb as _wkb

    from .fast_skimage import medial_axis

    poly = _wkb.loads(wkb)
    if poly.is_empty or poly.geom_type != "Polygon":
        return None
    x0, y0, x1, y1 = poly.bounds
    w, h = x1 - x0, y1 - y0
    if h <= 0 or w <= 0:
        return None
    R = _READ_PX_PER_MM
    W, H = int(math.ceil(w * R)) + 5, int(math.ceil(h * R)) + 5

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - x0) * R + 2, (a[:, 1] - y0) * R + 2]).astype(np.int32)

    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [px(poly.exterior.coords)], 1)
    for ring in poly.interiors:
        cv2.fillPoly(m, [px(ring.coords)], 0)
    skel, dist = medial_axis(m > 0, return_distance=True, rng=0)
    if not skel.any():
        return None
    d = dist[skel]
    crossings = []
    for f in _ROWS:
        row = m[min(H - 1, int(round(2 + f * h * R)))]
        crossings.append(int(np.count_nonzero(np.diff(np.r_[0, row, 0]) == 1)))
    hull = poly.convex_hull.area
    holes = [Polygon(r).area for r in poly.interiors]
    return ScriptReading(
        aspect=w / h, crossings=tuple(crossings),
        skeleton_heights=float(skel.sum()) / R / h,
        width_cv=float(np.std(d) / max(float(np.mean(d)), 1e-9)),
        hole_frac=(max(holes) / hull) if holes and hull > 0 else 0.0,
        stroke_mm=float(2.0 * np.median(d) / R))


def script_reading(poly) -> ScriptReading | None:
    """The door's reading of one polygon; None where there is nothing to read."""
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return None
    return _reading(poly.wkb)


def script_word(region, cfg) -> bool:
    """Does `cfg.script_strokes` take this shape? An auto-tier shape no
    lettering tagger took (`columns.is_lettering`), at least
    `SCRIPT_MIN_AREA_MM2`, that reads as a written word (`ScriptReading`).
    False whenever the flag is off, before anything is read."""
    if not getattr(cfg, "script_strokes", False):
        return False
    meta = region.meta or {}
    if str(meta.get("tier", "auto")).lower() != "auto":
        return False
    from .columns import is_lettering
    if is_lettering(region, cfg):
        return False
    poly = region.polygon
    if poly is None or poly.geom_type != "Polygon" or poly.area < SCRIPT_MIN_AREA_MM2:
        return False
    r = script_reading(poly)
    return bool(r and r.is_script)


# --------------------------------------------------------------- the grids
@dataclass
class _Grid:
    """Where the pen path is read: a binary `mask` whose medial axis is the
    path, `dist` (px) the DRAWN half-width at each pixel, on a grid of
    `scale` px/mm whose pixel (x, y) centre is (ox + (x + .5) / scale,
    oy + (y + .5) / scale) mm. `source`: "ink" or "polygon"."""

    mask: np.ndarray
    dist: np.ndarray
    scale: float
    ox: float
    oy: float
    source: str
    #: an ink reading's CLOSED pockets: ground the polygon covers and the
    #: drawn stroke rings round (a counter the trace closed); None otherwise
    counters: np.ndarray | None = None

    def to_mm(self, p) -> tuple[float, float]:
        return (self.ox + (p[0] + 0.5) / self.scale, self.oy + (p[1] + 0.5) / self.scale)

    def half_at(self, p_mm) -> float:
        """The drawn half-width (mm) at the pixel under `p_mm`; 0 off the grid."""
        x = int(math.floor((p_mm[0] - self.ox) * self.scale))
        y = int(math.floor((p_mm[1] - self.oy) * self.scale))
        H, W = self.dist.shape
        if 0 <= x < W and 0 <= y < H:
            return float(self.dist[y, x]) / self.scale
        return 0.0

    def counter_at(self, p_mm) -> bool:
        """Is `p_mm` in a closed pocket (`counters`)?"""
        if self.counters is None:
            return False
        x = int(math.floor((p_mm[0] - self.ox) * self.scale))
        y = int(math.floor((p_mm[1] - self.oy) * self.scale))
        H, W = self.counters.shape
        return bool(0 <= x < W and 0 <= y < H and self.counters[y, x])

    def edge_hit(self, s, u, reach: float) -> float:
        """Distance from `s` along unit `u` to where the drawn stroke ends
        (the half-width reads 0), or `reach` when it does not end that close."""
        step = 0.5 / self.scale
        k = 1
        while k * step < reach:
            if self.half_at((s[0] + u[0] * k * step, s[1] + u[1] * k * step)) <= 0.0:
                return k * step
            k += 1
        return reach


def polygon_grid(poly: Polygon) -> _Grid | None:
    """The traced polygon on the satin tier's own raster (`_rasterize`)."""
    import cv2

    from .stage6_satin import _rasterize
    mask, scale, ox, oy = _rasterize(poly)
    if not mask.any():
        return None
    m = (mask > 0).astype(np.uint8)
    return _Grid(mask=m, dist=cv2.distanceTransform(m, cv2.DIST_L2, 5), scale=scale,
                 ox=ox, oy=oy, source="polygon")


def ink_grid(ink, poly: Polygon) -> _Grid | None:
    """The word as it was DRAWN (`stage6_hairline.InkSource`, the artwork's
    own pixels), on an `INK_PX_PER_MM` grid: each pixel's colour projected
    onto the ground-to-ink axis (ink: the polygon's core, ground: a ring
    just outside it), so 0 is ground and 1 is ink. The path mask is the
    ink's core (`INK_PATH_T` and up), the half-width read on the half-max
    edge (`INK_EDGE_T`), both kept within `SCRIPT_INK_REACH_MM` of the polygon.
    None when the two colours are not `INK_MIN_DE` apart or no core is
    found: the polygon is read instead."""
    import cv2
    if ink is None:
        return None
    reading = script_reading(poly)
    stroke = reading.stroke_mm if reading and reading.stroke_mm > 0 else 2.0
    x0, y0, x1, y1 = poly.bounds
    pad = 1.5
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    R = min(max(INK_PX_ACROSS / stroke, INK_PX_PER_MM_MIN), INK_PX_PER_MM_MAX,
            INK_MAX_PX / max(x1 - x0, y1 - y0))
    W, H = int(math.ceil((x1 - x0) * R)), int(math.ceil((y1 - y0) * R))
    gx, gy = np.meshgrid(x0 + (np.arange(W) + 0.5) / R, y0 + (np.arange(H) + 0.5) / R)
    src = ink.to_src(np.column_stack([gx.ravel(), gy.ravel()])).astype(np.float32)
    mx, my = src[:, 0].reshape(H, W), src[:, 1].reshape(H, W)
    F = ink.field()
    lab = np.stack([cv2.remap(np.ascontiguousarray(F[..., k]), mx, my, cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
                    for k in range(F.shape[-1])], -1).astype(np.float64)

    def px(coords):
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - x0) * R, (a[:, 1] - y0) * R]).astype(np.int32)

    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [px(poly.exterior.coords)], 1)
    for ring in poly.interiors:
        cv2.fillPoly(m, [px(ring.coords)], 0)

    def disk(mm):
        k = max(1, int(round(mm * R)))
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))

    core = cv2.erode(m, disk(0.4))
    if not core.any():
        core = m
    ring = cv2.dilate(m, disk(1.0)) & (1 - cv2.dilate(m, disk(0.3)))
    if not ring.any() or not core.any():
        return None
    ink_c = np.median(lab[core > 0], 0)
    ground = np.median(lab[ring > 0], 0)
    v = ink_c - ground
    if float(np.linalg.norm(v)) < INK_MIN_DE:
        return None
    t = ((lab - ground) @ v) / float(v @ v)
    near = cv2.dilate(m, disk(SCRIPT_INK_REACH_MM))
    edge = ((t >= INK_EDGE_T) & (near > 0)).astype(np.uint8)
    path = ((t >= INK_PATH_T) & (near > 0)).astype(np.uint8)
    n, ids, stats, _c = cv2.connectedComponentsWithStats(path, connectivity=8)
    keep = np.zeros_like(path)
    for i in range(1, n):
        part = ids == i
        if stats[i, cv2.CC_STAT_AREA] / R ** 2 >= INK_MIN_PART_MM2 and m[part].any():
            keep[part] = 1
    if not keep.any():
        return None
    # specks of JPEG inside a stroke are not counters: each would ring the
    # medial axis with a loop of its own
    n, ids, stats, _c = cv2.connectedComponentsWithStats(1 - keep, connectivity=4)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if x > 0 and y > 0 and x + w < W and y + h < H and a / R ** 2 < INK_MIN_HOLE_MM2:
            keep[ids == i] = 1
    # the counters the trace closed: ground inside the polygon that the
    # drawn stroke rings round. Ground inside the polygon that reaches its
    # outside is not one (Tires' bevel: the photo trace runs past the ink
    # along whole strokes)
    pocket = ((m > 0) & (edge == 0)).astype(np.uint8)
    outside = cv2.dilate((1 - m).astype(np.uint8), np.ones((3, 3), np.uint8))
    counters = np.zeros_like(pocket)
    n, ids, stats, _c = cv2.connectedComponentsWithStats(pocket, connectivity=4)
    for i in range(1, n):
        part = ids == i
        if stats[i, cv2.CC_STAT_AREA] / R ** 2 >= INK_MIN_HOLE_MM2 and not outside[part].any():
            counters[part] = 1
    return _Grid(mask=keep, dist=cv2.distanceTransform(edge, cv2.DIST_L2, 5), scale=R,
                 ox=x0, oy=y0, source="ink", counters=counters)


# ------------------------------------------------------------ pen strokes
@dataclass
class PenStroke:
    """One stroke of the pen: its spine in mm (smoothed), whether each end is
    free (a terminal the stroke runs out to) or meets other strokes, and
    whether it closes on itself (an e's eye)."""

    spine: list[tuple[float, float]]
    free_start: bool
    free_end: bool
    closed: bool = False


def _arc_point(pts: list, s: float) -> tuple[float, float]:
    """The point arc length `s` along `pts` (clamped)."""
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if acc + L >= s and L > 0:
            t = (s - acc) / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        acc += L
    return tuple(pts[-1])


def _length(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _arm_dir(pts: list, from_start: bool, half: float) -> tuple[float, float] | None:
    """Unit direction of an arm AWAY from the node at its start (or end):
    from `_ARM_FROM` to `_ARM_TO` half-widths out, clamped to the arm."""
    seq = pts if from_start else pts[::-1]
    L = _length(seq)
    if L <= 0:
        return None
    a = _arc_point(seq, min(_ARM_FROM * half, 0.5 * L))
    b = _arc_point(seq, min(_ARM_TO * half, L))
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    if n < 1e-9:
        a, b = seq[0], seq[-1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        if n < 1e-9:
            return None
    return (dx / n, dy / n)


def _turn_deg(u, v) -> float:
    """Degrees between two unit directions."""
    c = max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1]))
    return math.degrees(math.acos(c))


def _skeleton(grid: _Grid):
    """-> (edges in px, drawn half-width px): the path mask's medial axis,
    pruned and junction-clustered with the satin tier's own functions."""
    from .fast_skimage import medial_axis
    from .stage6_satin import (_JUNCTION_CLUSTER_HALFWIDTHS, _JUNCTION_CLUSTER_MIN_PX,
                               _MIN_STROKE_HALFWIDTHS, _cluster_junctions, _collapse_pinholes,
                               _prune_spurs, _skeleton_edges)
    skel, own = medial_axis(grid.mask > 0, return_distance=True, rng=0)
    skel = _collapse_pinholes(skel)
    if not skel.any():
        return [], 0.0
    half_px = float(np.median(grid.dist[skel]))
    sk = skel.astype(np.uint8)
    # spurs are judged on the path mask's own width: a core read thinner
    # than the drawn stroke grows shorter corner twigs
    _prune_spurs(sk, max(3.0, 1.6 * float(np.median(own[skel]))))

    def dt_mm(p):
        return float(grid.dist[p[1], p[0]]) / grid.scale

    edges = _cluster_junctions(_skeleton_edges(sk),
                               max(_JUNCTION_CLUSTER_MIN_PX, _JUNCTION_CLUSTER_HALFWIDTHS * half_px),
                               dt_mm)
    min_len = max(3.0, _MIN_STROKE_HALFWIDTHS * half_px)
    keep = []
    for e in edges:
        if len(e["pts"]) < 2:
            continue
        if not e["closed"] and _length(e["pts"]) < min_len and not (e["free_start"] and e["free_end"]):
            continue        # a stub between two nodes: junction noise
        keep.append(e)
    return keep, half_px


def pen_strokes(grid: _Grid) -> tuple[list[PenStroke], float]:
    """The pen's strokes read on `grid` -> (strokes, drawn half-width mm).

    Arms meeting at a junction are paired most-straight first, and welded
    when they continue within `WELD_MAX_DEG`; every other arm ends there.
    Welded chains are one stroke each (a chain that comes back on itself
    is closed). A stroke is then split at each cusp (`CUSP_DEG`)."""
    edges, half_px = _skeleton(grid)
    if not edges:
        return [], 0.0
    E = [[grid.to_mm(p) for p in e["pts"]] for e in edges]
    half = half_px / grid.scale
    # node -> arms (edge, at_start)
    arms: dict[tuple[int, int], list[tuple[int, bool]]] = {}
    for i, e in enumerate(edges):
        if e["closed"]:
            continue
        if not e["free_start"]:
            arms.setdefault(tuple(e["pts"][0]), []).append((i, True))
        if not e["free_end"]:
            arms.setdefault(tuple(e["pts"][-1]), []).append((i, False))
    weld: dict[tuple[int, bool], tuple[int, bool]] = {}
    for node in sorted(arms):
        here = arms[node]
        dirs = {a: _arm_dir(E[a[0]], a[1], half) for a in here}
        pairs = []
        for x in range(len(here)):
            for y in range(x + 1, len(here)):
                a, b = here[x], here[y]
                if a[0] == b[0] or dirs[a] is None or dirs[b] is None:
                    continue
                dev = _turn_deg(dirs[a], (-dirs[b][0], -dirs[b][1]))
                pairs.append((dev, a, b))
        pairs.sort(key=lambda t: (round(t[0], 6), t[1], t[2]))
        used: set = set()
        for dev, a, b in pairs:
            if dev > WELD_MAX_DEG or a in used or b in used:
                continue
            used.update((a, b))
            weld[a] = b
            weld[b] = a

    strokes: list[PenStroke] = []
    seen: set[int] = set()

    def walk(i: int, from_start: bool) -> tuple[list, bool, bool, bool]:
        """Chain edges from edge `i` entered at its start (or end)."""
        pts: list = []
        start_free = edges[i]["free_start"] if from_start else edges[i]["free_end"]
        cur, fwd = i, from_start
        while True:
            seen.add(cur)
            seq = E[cur] if fwd else E[cur][::-1]
            pts.extend(seq if not pts else seq[1:])
            nxt = weld.get((cur, not fwd))        # the arm at this edge's far end
            if nxt is None:
                end_free = edges[cur]["free_end"] if fwd else edges[cur]["free_start"]
                return pts, start_free, end_free, False
            if nxt[0] in seen:
                return pts, start_free, False, nxt[0] == i
            cur, fwd = nxt[0], nxt[1]

    for i, e in enumerate(edges):
        if e["closed"]:
            seen.add(i)
            strokes.append(PenStroke(list(E[i]), False, False, True))
    # chains from an end with no weld first (free ends, unpaired arms), in
    # the order the skeleton walk listed the edges, so nothing depends on
    # set order
    for i in range(len(edges)):
        for from_start in (True, False):
            if i not in seen and weld.get((i, from_start)) is None:
                pts, fs, fe, closed = walk(i, from_start)
                strokes.append(PenStroke(pts, fs, fe, closed))
    for i in range(len(edges)):
        if i not in seen:               # a ring of welds
            pts, _fs, _fe, _c = walk(i, True)
            strokes.append(PenStroke(pts, False, False, True))
    out: list[PenStroke] = []
    for s in strokes:
        for piece in _split_cusps(s, half):
            # a knot of the axis -- a loop round a pinhole, a stub between two
            # junctions -- is not a stroke: its crosses would spike out of
            # the word. What it covered the patches take. A dot (free at
            # both ends) stays.
            short = _length(piece.spine) < _MIN_STROKE_HALVES * half
            if short and not (piece.free_start and piece.free_end):
                continue
            out.append(piece)
    # an end that met only what was dropped now meets nothing: it runs on
    # to its cap like any free end (Tires' r: both arms of the shoulder knot)
    lines = [LineString(st.spine) if len(st.spine) >= 2 else None for st in out]
    reach = _ARM_TO * half
    for i, st in enumerate(out):
        if st.closed:
            continue
        for at_start in (True, False):
            if st.free_start if at_start else st.free_end:
                continue
            end = Point(st.spine[0] if at_start else st.spine[-1])
            if not any(j != i and ln is not None and ln.distance(end) <= reach
                       for j, ln in enumerate(lines)):
                if at_start:
                    st.free_start = True
                else:
                    st.free_end = True
    return out, half


def smooth_spine(pts: list, sigma_mm: float, closed: bool) -> list[tuple[float, float]]:
    """The pen's path through a skeleton polyline: resampled every
    `_SPINE_STEP_MM` and Gaussian-smoothed along its arc length with
    `sigma_mm` (wrapped round a closed stroke, the ends held for an open
    one), so the crosses cast square to it turn as a hand turns them rather
    than with every pixel step of the medial axis."""
    from scipy.ndimage import gaussian_filter1d

    from .stage6_satin import _resample
    pts = list(pts)
    if closed and len(pts) > 2 and math.dist(pts[0], pts[-1]) > 1e-9:
        pts.append(pts[0])
    L = _length(pts)
    if L <= 0 or len(pts) < 3 or sigma_mm <= 0:
        return pts
    n = max(3, int(math.ceil(L / _SPINE_STEP_MM)) + 1)
    a = np.asarray(_resample(pts, n), np.float64)
    if closed:
        a = a[:-1]
    sig = sigma_mm / (L / (n - 1))
    mode = "wrap" if closed else "nearest"
    xs = gaussian_filter1d(a[:, 0], sig, mode=mode)
    ys = gaussian_filter1d(a[:, 1], sig, mode=mode)
    out = list(zip(xs.tolist(), ys.tolist()))
    if closed:
        out.append(out[0])
    return out


def _split_cusps(s: PenStroke, half: float) -> list[PenStroke]:
    """Smooth a stroke, then split it wherever it turns more than
    `CUSP_DEG` within one stroke width (2 half-widths each side), at the
    sharpest point of each such stretch, keeping pieces of at least
    `_MIN_PIECE_HALVES`. A closed stroke is smoothed and kept whole."""
    pts = smooth_spine(s.spine, SPINE_SIGMA_HALVES * half, s.closed)
    n = len(pts)
    if n < 5 or s.closed:
        return [PenStroke(pts, s.free_start, s.free_end, s.closed)]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    reach = 2.0 * half
    turn = [0.0] * n
    j0 = j1 = 0
    for i in range(n):
        while j0 < i and cum[i] - cum[j0] > reach:
            j0 += 1
        j1 = max(j1, i)
        while j1 < n - 1 and cum[j1] - cum[i] < reach:
            j1 += 1
        if j0 == i or j1 == i:
            continue
        u = (pts[i][0] - pts[j0][0], pts[i][1] - pts[j0][1])
        v = (pts[j1][0] - pts[i][0], pts[j1][1] - pts[i][1])
        nu, nv = math.hypot(*u), math.hypot(*v)
        if nu < 1e-9 or nv < 1e-9:
            continue
        turn[i] = _turn_deg((u[0] / nu, u[1] / nu), (v[0] / nv, v[1] / nv))
    cuts: list[int] = []
    min_piece = _MIN_PIECE_HALVES * half
    i = 0
    while i < n:
        if turn[i] <= CUSP_DEG:
            i += 1
            continue
        k = i
        while k + 1 < n and turn[k + 1] > CUSP_DEG:
            k += 1
        best = max(range(i, k + 1), key=lambda q: (turn[q], -q))
        if (cum[best] - (cum[cuts[-1]] if cuts else 0.0) >= min_piece
                and cum[-1] - cum[best] >= min_piece):
            cuts.append(best)
        i = k + 1
    if not cuts:
        return [PenStroke(pts, s.free_start, s.free_end, False)]
    # a cusp is where the pen turns back at the outline (the top of an s):
    # each piece runs on through it to the cap there, as a free end does
    bounds = [0, *cuts, n - 1]
    return [PenStroke(pts[a:b + 1], s.free_start if k == 0 else True,
                      s.free_end if k == len(bounds) - 2 else True, False)
            for k, (a, b) in enumerate(zip(bounds, bounds[1:]))]


# --------------------------------------------------------------- stations
def _boundary_hit(poly: Polygon, s, u, reach: float) -> float:
    """Distance from `s` along unit `u` to the first boundary crossing of
    `poly` (exterior or a counter), or `reach` when none is that close."""
    seg = LineString([s, (s[0] + u[0] * reach, s[1] + u[1] * reach)])
    hit = seg.intersection(poly.boundary)
    if hit.is_empty:
        return reach
    best = reach
    for g in getattr(hit, "geoms", [hit]):
        for c in g.coords:
            d = math.dist(s, c)
            if 1e-9 < d < best:
                best = d
    return best


def _stations(poly: Polygon, stroke: PenStroke, half: float, pitch_mm: float,
              grid: _Grid) -> list[tuple]:
    """Crosses square to the stroke, one per `pitch_mm` of whichever rail
    runs faster, each reaching the polygon's outline on both sides, capped
    at `REACH_HALVES` of the drawn local half-width (a rolling median along
    the stroke, so a junction's deep blob does not widen the cap)."""
    from .stage6_satin import _resample
    spine = list(stroke.spine)
    if len(spine) < 2:
        return []
    if stroke.closed and math.dist(spine[0], spine[-1]) > 1e-9:
        spine.append(spine[0])
    # a free end runs on along its tangent to the cap
    for at_start in (True, False):
        if stroke.closed or not (stroke.free_start if at_start else stroke.free_end):
            continue
        d = _arm_dir(spine, at_start, half)     # pointing INTO the stroke from this end
        if d is None:
            continue
        tip = spine[0] if at_start else spine[-1]
        ext = [(tip[0] - d[0] * half * k / 4, tip[1] - d[1] * half * k / 4)
               for k in range(1, int(_CAP_HALVES * 4) + 1)]
        spine = (ext[::-1] + spine) if at_start else (spine + ext)
    L = _length(spine)
    step = pitch_mm / _STATION_SUBSTEPS
    n = max(2, int(round(L / step)) + 1)
    pts = _resample(spine, n)
    # the cross DIRECTION comes off the pen's smoothed path, the station
    # itself stays on the stroke's middle: smoothing the positions as hard
    # pulled the path inside every bend and left 56-116 mm2 of a word for
    # patches to cover
    dirs = _resample(smooth_spine(spine, CROSS_SIGMA_HALVES * half, stroke.closed), n)
    local = [grid.half_at(p) for p in pts]
    win = max(1, int(round(3.0 * half / step)))
    ref = []
    for i in range(n):
        vals = sorted(v for v in local[max(0, i - win):i + win + 1] if v > 0)
        ref.append(vals[len(vals) // 2] if vals else half)
    m = max(1, int(round(half / step)))
    crosses = []
    for i, p in enumerate(pts):
        if not poly.covers(Point(p)):
            continue
        if stroke.closed:
            a, b = dirs[(i - m) % (n - 1)], dirs[(i + m) % (n - 1)]
        else:
            a, b = dirs[max(0, i - m)], dirs[min(n - 1, i + m)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        tn = math.hypot(tx, ty)
        if tn < 1e-9:
            continue
        nx, ny = -ty / tn, tx / tn
        reach = REACH_HALVES * max(ref[i], 0.5 * half)
        da = _drawn(grid, p, (nx, ny), _boundary_hit(poly, p, (nx, ny), reach))
        db = _drawn(grid, p, (-nx, -ny), _boundary_hit(poly, p, (-nx, -ny), reach))
        crosses.append(((p[0] + nx * da, p[1] + ny * da), (p[0] - nx * db, p[1] - ny * db)))
    # one cross per pitch on the FASTER rail: round a bend the outer rail
    # runs further than the spine, and stationed on the spine it opened to
    # twice the pitch on Bridge's tight loops (the inner rail's pile is the
    # emitter's short-stitch rule)
    out: list = []
    for c in crosses:
        if not out or max(math.dist(c[0], out[-1][0]), math.dist(c[1], out[-1][1])) >= pitch_mm - 1e-9:
            out.append(c)
    if crosses and out[-1] is not crosses[-1] and max(
            math.dist(crosses[-1][0], out[-1][0]), math.dist(crosses[-1][1], out[-1][1])) >= 0.5 * pitch_mm:
        out.append(crosses[-1])
    return out


def _drawn(grid: _Grid, s, u, hit: float) -> float:
    """Where a cross that would end `hit` along `u` ends on an ink reading:
    at the drawn edge when, past it, the cross would run into a counter the
    trace closed (`_Grid.counters`) -- more than `CLOSED_GAP_MM` short of
    the polygon's edge, which a cross reaching the polygon fans across --
    and at `hit`, the polygon's own edge, everywhere else. A polygon grid
    has no counters of its own: `hit`."""
    if grid.counters is None:
        return hit
    e = grid.edge_hit(s, u, hit)
    if hit - e <= CLOSED_GAP_MM:
        return hit
    past = e + 1.0 / grid.scale
    return e if grid.counter_at((s[0] + u[0] * past, s[1] + u[1] * past)) else hit


def _cross_near(columns, at) -> tuple[float, float] | None:
    """Unit direction of the stroke cross nearest `at` (middle to middle)."""
    best, d = None, math.inf
    for c in columns:
        for pa, pb in c.stations:
            m = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
            e = math.dist(m, at)
            L = math.dist(pa, pb)
            if e < d and L > 1e-9:
                best, d = ((pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L), e
    return best


def _patch_stations(piece: Polygon, poly: Polygon, pitch_mm: float,
                    cross_dir: tuple[float, float] | None = None) -> list[tuple]:
    """A straight column across one uncovered piece of the polygon, its
    crosses along `cross_dir` -- the nearest stroke's own cross, so the
    patch lies the way the satin round it does -- or, with none, along the
    short side of its minimum rectangle; one cross per `pitch_mm` across the
    piece, each running `PATCH_TUCK_MM` on under the strokes round it
    (inside the polygon)."""
    if cross_dir is None:
        rect = piece.minimum_rotated_rectangle
        if rect.geom_type != "Polygon":
            return []
        c = list(rect.exterior.coords)[:4]
        e0 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
        e1 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
        long = e0 if math.hypot(*e0) >= math.hypot(*e1) else e1
        Ll = math.hypot(*long)
        if Ll < 1e-9:
            return []
        cross_dir = (-long[1] / Ll, long[0] / Ll)
    v = cross_dir
    u = (v[1], -v[0])
    cx, cy = piece.centroid.x, piece.centroid.y
    ext = [(x - cx) * u[0] + (y - cy) * u[1] for x, y in piece.exterior.coords]
    lo, hi = min(ext), max(ext)
    L = hi - lo
    if L < 1e-9:
        return []
    grown = piece.buffer(PATCH_TUCK_MM).intersection(poly)
    x0, y0, x1, y1 = grown.bounds
    big = math.hypot(x1 - x0, y1 - y0) + 1.0
    n = max(3, int(math.ceil(L / pitch_mm)) + 1)
    out = []
    for k in range(n):
        t = lo + L * k / (n - 1)
        m = (cx + u[0] * t, cy + u[1] * t)
        seg = LineString([(m[0] - v[0] * big, m[1] - v[1] * big),
                          (m[0] + v[0] * big, m[1] + v[1] * big)]).intersection(grown)
        parts = [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and not g.is_empty]
        if not parts:
            continue
        g = min(parts, key=lambda q: q.distance(Point(m)))
        a, b = g.coords[0], g.coords[-1]
        if (b[0] - a[0]) * v[0] + (b[1] - a[1]) * v[1] < 0:
            a, b = b, a
        out.append((tuple(b), tuple(a)))
    return out


def uncovered(poly: Polygon, columns) -> list[Polygon]:
    """The pieces of `poly` no column's drawn ground reaches (its crosses
    plus half a thread), slivers under `PATCH_SLIVER_MM` (the pull covers
    them) opened away, `PATCH_MIN_MM2` and up."""
    from shapely.ops import unary_union
    ground = unary_union([c.piece for c in columns if not c.piece.is_empty])
    rest = poly.difference(ground.buffer(0.15))
    rest = rest.buffer(-PATCH_SLIVER_MM).buffer(PATCH_SLIVER_MM).intersection(poly)
    parts = [g for g in getattr(rest, "geoms", [rest]) if g.geom_type == "Polygon"]
    return sorted((g for g in parts if g.area >= PATCH_MIN_MM2),
                  key=lambda g: (round(g.bounds[0], 6), round(g.bounds[1], 6)))


def _ribbon(stations) -> Polygon:
    if len(stations) < 2:
        return Polygon()
    return Polygon([a for a, _ in stations] + [b for _, b in stations][::-1]).buffer(0)


def _mid(st):
    return Point((st[0][0] + st[1][0]) / 2, (st[0][1] + st[1][1]) / 2)


def _left_key(stations) -> tuple[float, float]:
    """A stroke's leftmost cross (the higher on a tie): the order the
    columns are handed to the walk in, so its nodes are numbered left to
    right and the plan is the same every run."""
    m = min((((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in stations),
            key=lambda q: (q[0], q[1]))
    return (round(m[0], 6), round(m[1], 6))


def script_columns(poly: Polygon, pitch_mm: float, ink=None):
    """One script word's polygon -> (`columns.Column`s, one per pen stroke
    piece, left to right; the strokes, in the same order; the grid the path
    was read on, or None). The path is read on the artwork's ink
    (`ink_grid`) when `ink` gives one, else on the polygon; the crosses
    always reach the POLYGON's outline.

    A stroke that ENDS where a longer one passes is cut back to that one's
    edge (its end stations whose middle lies inside the other's ribbon go,
    three always kept), so the emitter reads a butt, not a stack: the walk
    then runs it on under the stroke it meets when it sews first (the
    junction tuck) and stops it at the edge when it sews after."""
    from .columns import Column
    grid = polygon_grid(poly)
    if grid is None:
        return [], [], None
    inked = ink_grid(ink, poly)
    if inked is not None:
        # the ink's path stands only if it is a pen line, not the artwork's
        # texture: no more than `INK_EDGES_RATIO_MAX` the polygon's edges
        if len(_skeleton(inked)[0]) <= (INK_EDGES_RATIO_MAX * len(_skeleton(grid)[0])
                                        + _INK_EDGES_SLACK):
            grid = inked
    strokes, half = pen_strokes(grid)
    raw = []
    for st in strokes:
        sts = _stations(poly, st, half, pitch_mm, grid)
        if len(sts) >= 3:
            raw.append((st, sts))
    raw.sort(key=lambda t: _left_key(t[1]))
    ribbons = [_ribbon(s).buffer(-0.05) for _st, s in raw]
    out_cols, out_strokes = [], []
    for ci, (st, sts) in enumerate(raw):
        sts = list(sts)
        for at_start in (True, False):
            if st.closed or (st.free_start if at_start else st.free_end):
                continue
            mid = _mid(sts[0] if at_start else sts[-1])
            others = [cj for cj, r in enumerate(ribbons)
                      if cj != ci and not r.is_empty and len(raw[cj][1]) >= len(sts)
                      and r.covers(mid)]
            if not others:
                continue
            through = ribbons[min(others, key=lambda cj: (-len(raw[cj][1]), cj))]
            while len(sts) > 3 and through.covers(_mid(sts[0] if at_start else sts[-1])):
                sts.pop(0 if at_start else -1)
        ws = sorted(math.dist(a, b) for a, b in sts)
        out_cols.append(Column(stations=sts, piece=_ribbon(sts), kind="curved", axis=None,
                               width_mm=ws[len(ws) // 2]))
        out_strokes.append(st)
    return out_cols, out_strokes, grid


def script_strokes_shape(poly: Polygon, shape_id: str, *, trim_at_mm: float,
                         spacing_mm: float, split_above_mm: float | None = None,
                         pull_mm: float = 0.0, pull_floor_mm: float = 0.0,
                         underlay_style: str = "none",
                         start_near=None, end_near=None,
                         inside_connectors: bool = False,
                         inside_stagger: bool = False,
                         ink=None):
    """One script word (its ARTWORK polygon) -> (runs, report), the satin
    tier's contract (`empty` when nothing could be built: the caller falls
    through to the ladder). `ink`: `stage6_hairline.InkSource` or None.

    A patch over each piece of polygon the strokes leave uncovered
    (`uncovered`), its crosses the way the nearest stroke's lie, is sewn
    first; then the strokes go to `columns.column_runs` as ONE word: pull on
    the rails, the cross floor, split satin, the centre underlay, and the
    walk that sews each span's satin on its last visit and runs under it on
    the earlier ones, so the needle crosses the word under thread still to
    come. Measured against sewing each stroke in turn, left to right: cuts
    inside the word 6 / 5 / 14 (Bridge hat / Tires / To a T hat) that way,
    0 / 1 / 1 with the walk. Then `monoline.py`'s two clean-ups for a
    joined word: underlay left on finished satin cut back, and any hop
    still cut routed under satin to come (`bury_hops`)."""
    from .columns import Column, column_runs
    from .monoline import bury_hops, clear_finished_underlay
    cols, strokes, grid = script_columns(poly, spacing_mm, ink)
    if not cols:
        return [], {"empty": True, "too_thin": False, "jumps": 0}
    kw = dict(trim_at_mm=trim_at_mm, spacing_mm=spacing_mm, split_above_mm=split_above_mm,
              pull_mm=pull_mm, pull_floor_mm=pull_floor_mm,
              **({"inside_connectors": True} if inside_connectors else {}),
              **({"inside_stagger": True} if inside_stagger else {}))
    patches = []
    for piece in uncovered(poly, cols):
        c = piece.representative_point()
        sts = _patch_stations(piece, poly, spacing_mm, _cross_near(cols, (c.x, c.y)))
        if len(sts) >= 3:
            ws = sorted(math.dist(a, b) for a, b in sts)
            patches.append(Column(stations=sts, piece=_ribbon(sts), kind="curved", axis=None,
                                  width_mm=ws[len(ws) // 2]))
    # the patches first, so the strokes lie over their edges; then the
    # strokes as one walk from where the patches left the needle
    under: list = []
    if patches:
        under, _prep = column_runs(patches, poly, shape_id, underlay_style="none",
                                   start_near=start_near, **kw)
    runs, report = column_runs(
        cols, poly, shape_id, underlay_style=underlay_style,
        start_near=under[-1].points[-1] if under else start_near, end_near=end_near, **kw)
    if report.get("empty") or not runs:
        return [], {**report, "empty": True}
    if under:
        # the satin tier's link rule between the two: needle-down inside the
        # word within `trim_at_mm`, else a jump (cut past it) for `bury_hops`
        a, b = under[-1].points[-1], runs[0].points[0]
        d = math.dist(a, b)
        if d >= 1e-9 and not (d <= trim_at_mm and poly.buffer(0.1 + pull_mm).covers(LineString([a, b]))):
            runs[0].jump = True
            runs[0].trim = d > trim_at_mm
        runs = under + runs
    report["script_strokes"] = len(strokes)
    report["script_patches"] = len(patches)
    report["script_path_ink"] = int(grid.source == "ink")
    report["script_underlay_cleared"] = clear_finished_underlay(runs, trim_at_mm)
    report["script_hops_buried"] = bury_hops(runs, trim_at_mm)
    report["jumps"] = sum(1 for r in runs[1:] if r.jump)
    return runs, report

