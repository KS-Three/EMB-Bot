"""A text cluster's strokes, read from the SOURCE INK rather than the traced
shape (2026-10-02, `docs/superpowers/specs/2026-10-02-bean-letters-design.md`).

Why the ink. A 0.7 mm stroke in a 3.5 px/mm file is 2.5 source pixels and its
counter about two; stage 2's region mask closes the counter before a polygon
exists, so the traced letter is a blob (bridge's eight "RESTAURANT" shapes
carry zero holes) and the skeleton of a blob is a squiggle. The pixels still
carry the letter as a difference of DEGREE: a stroke's centre is fully ink, a
closed counter is not. Projecting each pixel onto the ground-to-ink colour
axis and thresholding that keeps the counter open.

One reading serves two callers — the stroke WIDTH that decides whether a word
is small lettering, and the PATH a bean run follows — so they cannot disagree.

Measured and rejected: a ridge filter (`skimage.filters.sato`) read bridge
better and drew triangles at Fremont's serifs and a double outline round
every bold letter.

Every length here is millimetres resolved on the raster at hand; nothing is a
pixel count.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from skimage.morphology import skeletonize

# The prepared raster is enlarged this many times before the threshold: at
# 8 px/mm a 0.5 mm counter is four pixels and the skeleton of its two walls
# needs room between them.
INK_UPSCALE = 3
# Share of the way from ground to ink a pixel must be to count as ink. Bridge
# read as letters at 0.55 and at 0.70; 0.55 keeps thin joins connected.
INK_THRESHOLD = 0.55
# Ink further than this from a member's traced polygon is not that member's.
INK_REACH_MM = 0.35
# The ground colour is read from pixels at least this far from every member.
INK_GROUND_CLEAR_MM = 0.8
# A skeleton branch with a free end shorter than this (before its end is
# carried out, below) is a corner spur, not an arm. At 0.6 it took bridge's E
# middle arm, whose skeleton is 0.47 mm.
INK_MIN_BRANCH_MM = 0.3
# The crop round the cluster.
_PAD_MM = 1.0
# Smoothing of the inkness before the threshold, against JPEG blocks.
_SMOOTH_MM = 0.08


@dataclass
class MemberInk:
    """One cluster member's ink: its median stroke width (None: no ink found)
    and its skeleton as polylines in design millimetres (stage 4's frame)."""
    stroke_mm: float | None = None
    spines: list[list[tuple[float, float]]] = field(default_factory=list)


def _length(pts) -> float:
    a = np.asarray(pts, np.float64)
    return float(np.hypot(*np.diff(a, axis=0).T).sum()) if len(a) > 1 else 0.0


def _carry_out(end, inward, width: np.ndarray) -> tuple[float, float]:
    """`end` moved outward by the ink's half-width there, along the direction
    from a point about one half-width back down the spine (`inward` runs from
    the end into the stroke). Working pixels throughout."""
    h, w = width.shape
    ex, ey = end
    r = float(width[min(h - 1, max(0, int(round(ey)))), min(w - 1, max(0, int(round(ex))))])
    if r <= 0.0 or not inward:
        return end
    back = inward[-1]
    for q in inward:
        if np.hypot(q[0] - ex, q[1] - ey) >= r:
            back = q
            break
    dx, dy = ex - back[0], ey - back[1]
    n = float(np.hypot(dx, dy))
    if n <= 1e-9:
        return end
    return (ex + dx / n * r, ey + dy / n * r)


def read_cluster_ink(p, members: list) -> list[MemberInk]:
    """-> one `MemberInk` per member, in order. `p` is the prepared raster
    (`stage1_prep.Prep`), `members` the cluster's regions.

    A cutout whose letters stand on transparency has no ground colour to
    project against — there the foreground mask IS the ink. Everywhere else
    the ground is read from the pixels round the cluster, whatever the
    background mask says of them: a white page is ground to a letter whether
    or not stage 1 called it background.

    Fails open: nothing to read is an empty `MemberInk`, never an error."""
    from .legibility import _plan_frame
    from .stage6_satin import _skeleton_edges

    if p is None or not members:
        return [MemberInk() for _ in members]
    cx, cy, ppm = _plan_frame(p)
    H0, W0 = p.rgb.shape[:2]
    bounds = np.array([m.polygon.bounds for m in members], np.float64)
    X0 = max(0, int((bounds[:, 0].min() - _PAD_MM) * ppm + cx))
    Y0 = max(0, int((bounds[:, 1].min() - _PAD_MM) * ppm + cy))
    X1 = min(W0, int(np.ceil((bounds[:, 2].max() + _PAD_MM) * ppm + cx)))
    Y1 = min(H0, int(np.ceil((bounds[:, 3].max() + _PAD_MM) * ppm + cy)))
    if X1 - X0 < 2 or Y1 - Y0 < 2:
        return [MemberInk() for _ in members]
    up = INK_UPSCALE
    S = ppm * up                                   # working pixels per millimetre
    big = cv2.resize(np.ascontiguousarray(p.rgb[Y0:Y1, X0:X1]), None, fx=up, fy=up,
                     interpolation=cv2.INTER_CUBIC)
    fg = cv2.resize((~p.bg_mask[Y0:Y1, X0:X1]).astype(np.float32), None, fx=up, fy=up,
                    interpolation=cv2.INTER_CUBIC)
    H, W = big.shape[:2]

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)[:, :2]
        return np.round(np.column_stack([(a[:, 0] * ppm + cx - X0) * up,
                                         (a[:, 1] * ppm + cy - Y0) * up])).astype(np.int32)

    def mask_of(geom) -> np.ndarray:
        m = np.zeros((H, W), np.uint8)
        for g in ([geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))):
            if g.geom_type != "Polygon" or g.is_empty:
                continue
            cv2.fillPoly(m, [to_px(g.exterior.coords)], 1)
            for hole in g.interiors:
                cv2.fillPoly(m, [to_px(hole.coords)], 0)
        return m > 0

    own = [mask_of(m.polygon) for m in members]
    inside = np.logical_or.reduce(own)
    if not inside.any():
        return [MemberInk() for _ in members]
    # Distance from every pixel to each member, in working pixels.
    dist = np.stack([cv2.distanceTransform((~o).astype(np.uint8), cv2.DIST_L2, 5) for o in own])
    nearest = dist.argmin(axis=0)
    d_any = dist.min(axis=0)
    far = d_any >= INK_GROUND_CLEAR_MM * S
    if not far.any():
        far = ~inside

    if bool(getattr(p, "bg_from_alpha", False)) and float((fg[far] > 0.5).mean()) < 0.2:
        t = np.clip(fg, 0.0, 1.0)
    else:
        lab = cv2.cvtColor(big, cv2.COLOR_RGB2LAB).astype(np.float32)
        ground = np.median(lab[far], axis=0)
        d = np.linalg.norm(lab - ground, axis=2)
        strong = inside & (d >= np.percentile(d[inside], 80))
        axis = np.median(lab[strong], axis=0) - ground
        norm = float(axis @ axis)
        if norm < 1.0:                              # the ink is the ground: nothing to read
            return [MemberInk() for _ in members]
        t = np.clip(((lab - ground) @ axis) / norm, 0.0, 1.0)
    t = cv2.GaussianBlur(t, (0, 0), max(0.5, _SMOOTH_MM * S))
    ink = (t > INK_THRESHOLD) & (d_any <= INK_REACH_MM * S)
    if not ink.any():
        return [MemberInk() for _ in members]
    width = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)

    out: list[MemberInk] = []
    for i in range(len(members)):
        mine = ink & (nearest == i)
        if int(mine.sum()) < 3:
            out.append(MemberInk())
            continue
        skel = skeletonize(mine)
        if int(skel.sum()) < 3:
            out.append(MemberInk())
            continue
        stroke_mm = 2.0 * float(np.median(width[skel])) / S
        edges = [e for e in _skeleton_edges(skel) if len(e["pts"]) >= 2]
        spines = []
        for e in edges:
            px = [(float(x), float(y)) for x, y in e["pts"]]
            spur = (e["free_start"] or e["free_end"]) and not e["closed"]
            if spur and len(edges) > 1 and _length(px) / S < INK_MIN_BRANCH_MM:
                continue
            # A skeleton stops half a stroke short of a free end; carry it out
            # to the ink's edge along its own last stretch.
            if not e["closed"]:
                if e["free_start"]:
                    px.insert(0, _carry_out(px[0], px[1:], width))
                if e["free_end"]:
                    px.append(_carry_out(px[-1], px[-2::-1], width))
            spines.append([((x / up + X0 - cx) / ppm, (y / up + Y0 - cy) / ppm) for x, y in px])
        out.append(MemberInk(stroke_mm=stroke_mm, spines=spines))
    return out
