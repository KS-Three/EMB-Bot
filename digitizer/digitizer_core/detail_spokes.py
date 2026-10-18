"""Spoked detail marks (`cfg.detail_spokes`, built OFF 2026-10-15).

A small detail of another colour enclosed by one shape -- the white star in
the black Wisconsin of Hotel Fremont's hat -- is too small for the run tier's
outline (its 2 x max(w, h) loop proxy is under `machine.RUN_MIN_LOOP_MM`), so
stage 3 absorbs it into the shape round it and the engine paints it over. The
professional's file does neither: the black sews solid underneath and ONE
white run sews a five-spoke asterisk on top of it, each spoke out from a
common centre and straight back (two 1.4-1.5 mm stitches per spoke, tips 72
degrees apart, ~2.9 mm across on a 92.6 mm design whose art star is ~0.9 mm),
then a tie. The pro exaggerates the detail about three times and sews it as
spokes, not as a hole and not as an outline.

Two halves live here so stage 3 and stage 7 read one definition:

* `find_tips` -- the detector, on the region's MASK: the boundary's distance
  from the centroid, read round the ring; a tip is a prominent local maximum
  (a convex point the boundary falls away from on both sides by at least
  `TIP_DEPTH` of its radius). A star, a cross or an asterisk has three or
  more; a round dot, a square or a pentagon has none deep enough (a square's
  corners stand only 29% proud of its sides), so they keep today's path.
* `spoke_runs` -- the builder: one run of the region's thread from the
  centroid out to each tip, extended along its own direction to at least
  `machine.DETAIL_SPOKE_MIN_MM`, and straight back, tips in angular order.
  No underlay, no outline, no pull compensation; stage 7 ties it as any run.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from scipy.signal import find_peaks

from . import machine
from .stitches import RUN, StitchRun

# A tip must stand this far proud of the boundary on both sides, as a share
# of its own radius. 0.3 admits a triangle (its sides sit at 0.5 of a tip),
# a regular pentagram (0.62) and any cross; refuses a square (0.71), a
# pentagon (0.81) and a round dot. A classification ratio, not a physical
# constant.
TIP_DEPTH = 0.3
# ...and at least this many pixels, so the staircase of a small round dot's
# boundary (half a pixel) is never read as a tip.
TIP_DEPTH_MIN_PX = 1.5
# Fewer boundary pixels than this is not a shape with a readable outline.
_MIN_RING_PX = 12
# The fewest tips a spoked detail has: a cross. Built at 3 (a triangle);
# measured over the 17-design corpus (docs/renders/detail-spokes/README.md)
# the one mark 3 admitted besides Fremont's star was a 0.15 mm² three-tipped
# speck of tyre tread on `screenshot_phone_ui_golke`, so Kent tightened it to
# 4 when he flipped the flag ON (2026-10-16): every star and cross still
# passes, the speck is refused.
MIN_TIPS = 4


def find_tips(crop: np.ndarray, min_tips: int = MIN_TIPS
              ) -> tuple[tuple[float, float], list[tuple[float, float]]] | None:
    """The spoked-detail reading of one bbox-tight bool mask.

    Returns `(centre, tips)` in the crop's own pixel coordinates (x, y),
    `tips` in angular order round the centre, or None when the mask has
    fewer than `min_tips` tips. The centre is the pixel centroid. A tip is
    the boundary pixel of greatest radius in its lobe; a lobe whose crest is
    two corners (a fat cross arm, whose end corners stand equally proud with
    a shallow dip between) is read as one tip, at the lobe's mean direction.
    """
    min_tips = max(3, int(min_tips))
    ys, xs = np.nonzero(crop)
    if xs.size < _MIN_RING_PX:
        return None
    cx, cy = float(xs.mean()), float(ys.mean())
    padded = np.zeros((crop.shape[0] + 2, crop.shape[1] + 2), np.uint8)
    padded[1:-1, 1:-1] = crop
    contours, _ = cv2.findContours(padded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE,
                                   offset=(-1, -1))
    if not contours:
        return None
    ring = max(contours, key=len).reshape(-1, 2).astype(np.float64)
    n = len(ring)
    if n < _MIN_RING_PX:
        return None
    dx, dy = ring[:, 0] - cx, ring[:, 1] - cy
    r = np.hypot(dx, dy)
    r_max = float(r.max())
    if r_max <= 0.0:
        return None
    depth = max(TIP_DEPTH * r_max, TIP_DEPTH_MIN_PX)
    # The ring is circular: read it three times over so a peak at the seam
    # has both its valleys, then keep the middle copy.
    r3 = np.concatenate([r, r, r])
    peaks, _props = find_peaks(r3, prominence=depth)
    peaks = sorted({int(k) - n for k in peaks if n <= k < 2 * n})
    if len(peaks) < min_tips:
        return None

    def valley(a: int, b: int) -> float:
        """Lowest radius on the arc from peak `a` forward to peak `b`."""
        if b > a:
            return float(r[a:b + 1].min())
        return float(min(r[a:].min(), r[:b + 1].min()))

    # Two crests with no real valley between them are one lobe (a fat arm's
    # two end corners): merge them. Groups are circular.
    groups: list[list[int]] = [[peaks[0]]]
    for k in peaks[1:]:
        prev = groups[-1][-1]
        if valley(prev, k) > (1.0 - TIP_DEPTH) * min(r[prev], r[k]):
            groups[-1].append(k)
        else:
            groups.append([k])
    if len(groups) > 1:
        first, last = groups[0], groups[-1]
        if valley(last[-1], first[0]) > (1.0 - TIP_DEPTH) * min(r[last[-1]], r[first[0]]):
            groups[0] = last + first
            groups.pop()
    if len(groups) < min_tips:
        return None
    tips: list[tuple[float, float, float]] = []
    for g in groups:
        ux = float(np.mean([dx[k] / r[k] for k in g]))
        uy = float(np.mean([dy[k] / r[k] for k in g]))
        norm = math.hypot(ux, uy)
        if norm < 1e-9:
            continue
        radius = float(max(r[k] for k in g))
        ang = math.atan2(uy / norm, ux / norm)
        tips.append((ang, cx + ux / norm * radius, cy + uy / norm * radius))
    if len(tips) < min_tips:
        return None
    tips.sort()
    return (cx, cy), [(x, y) for _ang, x, y in tips]


def spoke_runs(centre: tuple[float, float], tips: list[tuple[float, float]], shape_id: str, *,
               min_mm: float | None = None) -> tuple[list[StitchRun], dict]:
    """One run: centre -> tip -> centre for each tip, in angular order.

    Each spoke is two stitches, out and back, the pro's construction. A tip
    nearer the centre than `min_mm` (None: `machine.DETAIL_SPOKE_MIN_MM`) is
    pushed out along its own direction to it. Returns `(runs, report)` with
    the run tier's report keys (`empty`, `jumps`, `loops`, `too_thin`) plus
    `spokes`; empty when no tip has a direction.
    """
    floor = machine.DETAIL_SPOKE_MIN_MM if min_mm is None else float(min_mm)
    cx, cy = float(centre[0]), float(centre[1])
    ordered = sorted(tips, key=lambda t: math.atan2(t[1] - cy, t[0] - cx))
    pts: list[tuple[float, float]] = [(cx, cy)]
    spokes = 0
    for tx, ty in ordered:
        vx, vy = float(tx) - cx, float(ty) - cy
        d = math.hypot(vx, vy)
        if d < 1e-9:
            continue
        length = max(d, floor)
        pts.append((cx + vx / d * length, cy + vy / d * length))
        pts.append((cx, cy))
        spokes += 1
    report = {"loops": 0, "jumps": 0, "empty": spokes == 0, "too_thin": False, "spokes": spokes}
    if not spokes:
        return [], report
    return [StitchRun(points=pts, kind=RUN, shape_id=shape_id)], report
