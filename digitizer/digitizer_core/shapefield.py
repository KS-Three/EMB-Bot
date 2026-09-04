"""ShapeField — skeleton and exact Euclidean distance transform, computed
together in ONE `medial_axis(rng=0)` call and packaged for every downstream
stage to share.

This is the DT-first migration's M1 slice
(`docs/dt-first-architecture-2026-08-01.md` section 2, pinned into the queue
by `docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`). The patent
record (Goldman/SoftSight, step 406) computes contour, skeleton and distance
transform as one artifact, before anything decides how a shape is sewn:

    "chain-code + THINNING + DT (208)   ONE PASS. This is the whole
    architecture."

`digitizer_core/stage6_satin.py` already makes exactly that one call —
`medial_axis(mask > 0, return_distance=True, rng=0)` inside
`extract_strokes` — but only after `stage7_sequence.py:97` has already made
the satin-vs-fill call from `2*area/perimeter`, a statistic the source
patent warns against. M1 does not touch that classifier (that is M2/M3, a
later, separate, corpus-gated slice) — it only hoists the DT/skeleton
computation into a shared, nameable object so a later stage can read it
without re-deriving it.

Byte-identical output is a hard requirement here: this module is pure
infrastructure, not a numerics change. `ShapeField`'s raster path
deliberately mirrors `stage6_satin._rasterize` + its `medial_axis(..., rng=0)`
call NUMBER FOR NUMBER — same resolution ramp, same `cv2.fillPoly` calls,
same 2px margin, same seed. It is a literal duplicate rather than a shared
import: `stage6_satin.py` imports THIS module (to route through it when
`cfg.extra["shapefield"]` is truthy), so the reverse import would be
circular, and more importantly the point of the flag is that the DEFAULT
(flag-off) code path in `stage6_satin.py` must not depend on this module
existing at all — it keeps running its own untouched inline call.
`tests/test_shapefield_byte_identical.py` is what proves the two paths still
agree; if they ever drift, that test is what will catch it, not code review.

Do not wire this into `digitizer/tools/shape_lens.py` — that tool computes
its own independent DT/skeleton on purpose (see its own module docstring)
and the two are meant to stay separate instruments.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from shapely.geometry import Polygon
from skimage.morphology import medial_axis

# Mirrors stage6_satin._RASTER_PX_PER_MM / _RASTER_MAX_PX exactly. See the
# module docstring for why this is a duplicate, not a shared import.
_RASTER_PX_PER_MM = 6.0
_RASTER_MAX_PX = 900


@dataclass(frozen=True)
class ShapeField:
    """Mask, skeleton and exact EDT from one rasterization + one
    `medial_axis(rng=0)` call, plus the px<->mm mapping needed to read them
    back in the coordinate space `poly` was given in.
    """

    mask: np.ndarray   # bool, HxW — the pixels the field was computed on
    skel: np.ndarray   # bool, HxW — the medial_axis skeleton
    dist: np.ndarray   # float, HxW — EXACT EDT in px (medial_axis's own; not chamfer/3)
    scale: float        # px per mm
    ox: float            # mm x corresponding to pixel column 0
    oy: float             # mm y corresponding to pixel row 0

    def half_at(self, pt: tuple[float, float]) -> float:
        """Local half-width in mm at a point given in mm space, or 0.0 if
        `pt` falls outside the field. Mirrors
        `stage6_satin._WidthField.half_at` exactly — same lookup, same
        truncation to the containing pixel, same `v > 0` guard.
        """
        x = int((pt[0] - self.ox) * self.scale)
        y = int((pt[1] - self.oy) * self.scale)
        h, w = self.dist.shape
        if 0 <= y < h and 0 <= x < w:
            v = float(self.dist[y, x])
            if v > 0:
                return v / self.scale
        return 0.0


def _ribbon_width_mm(poly: Polygon) -> float:
    """2*area/perimeter, duplicated from `stage6_satin.ribbon_width_mm`.

    Used only to pick the raster resolution below — the same reason
    `_rasterize` calls it today. This is NOT a classification call (see
    `stage6_satin.is_satin_candidate` for that); duplicated rather than
    imported for the same reason `rasterize_polygon` is (see module
    docstring) — it is three lines, and keeping this module import-free of
    `stage6_satin` is what lets `stage6_satin` import this module back.
    """
    perim = poly.exterior.length + sum(r.length for r in poly.interiors)
    if perim <= 0:
        return 0.0
    return 2.0 * poly.area / perim


def rasterize_polygon(poly: Polygon) -> tuple[np.ndarray, float, float, float]:
    """-> (binary mask uint8, scale px/mm, x-origin mm, y-origin mm).

    Byte-for-byte the same rasterization `stage6_satin._rasterize` performs.
    See the module docstring for why this is a deliberate duplicate.
    """
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0)
    wall = _ribbon_width_mm(poly)
    need = _RASTER_PX_PER_MM if wall <= 0 else max(_RASTER_PX_PER_MM, 8.0 / wall)
    scale = min(need, _RASTER_MAX_PX / max(dim, 1e-6))
    w = int(math.ceil((x1 - x0) * scale)) + 4
    h = int(math.ceil((y1 - y0) * scale)) + 4
    img = np.zeros((h, w), np.uint8)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - x0) * scale + 2, (a[:, 1] - y0) * scale + 2]).astype(np.int32)

    cv2.fillPoly(img, [to_px(poly.exterior.coords)], 255)
    shrink = bool(poly.is_valid) and poly.area > 0.0
    for ring in poly.interiors:
        # A hole is painted half a pixel smaller than it is, so its edge lands
        # where the exterior's does — `hole_px` below, shared with this
        # function's twin `stage6_satin._rasterize` (2026-09-04).
        for pts in hole_px(ring, scale, to_px, shrink):
            cv2.fillPoly(img, [pts], 0)
    return img, scale, x0 - 2 / scale, y0 - 2 / scale


# `fillPoly` paints its boundary pixels, so the exterior's edge is material
# and a hole painted the same way ate its own edge: half a pixel of material
# gone all round every counter, the medial axis pushed outward by it, and —
# the rails being set to the NEARER boundary hit — the hole-side rail stopped
# two half-pixels short of the outline (0.18 mm at 6 px/mm, measured on the
# icon repro's frame and ring, 2026-09-04; the exterior rail sat within
# 0.006 mm). A hole is painted half a pixel SMALLER than it is, so its edge
# lands where the exterior's does. Not by redrawing its boundary as material
# after the fill: that ring closes a counter a few pixels across to a speck
# the medial axis trips over (the drone's satin "A" at hat front lost its
# upper legs — 97% → 54% of its artwork sewn) and roughens larger holes into
# spurs. A hole too small to survive the shrink is painted as it was.
# Shared by `rasterize_polygon` below and its twin `stage6_satin._rasterize`
# (byte-equal by test_shapefield).
def hole_px(ring, scale: float, to_px, shrink: bool = True) -> list[np.ndarray]:
    # `shrink=False` paints the hole as it always was — for a polygon with no
    # material of its own (invalid, or zero area: a hole coincident with its
    # shell), where shrinking the hole would leave the exterior's own
    # half-pixel rim standing as a one-pixel loop of "material" that fields
    # and clusters as a real shape. The old painting cleared that rim too.
    if not shrink:
        return [to_px(ring.coords)]
    hole = Polygon(ring)
    shrunk = hole.buffer(-0.5 / scale)
    if shrunk.is_empty:
        return [to_px(ring.coords)]
    parts = [shrunk] if shrunk.geom_type == "Polygon" else list(getattr(shrunk, "geoms", []))
    out = [to_px(part.exterior.coords) for part in parts if part.geom_type == "Polygon" and not part.is_empty]
    return out or [to_px(ring.coords)]


def build_shape_field(poly: Polygon) -> ShapeField | None:
    """Rasterize `poly` and hoist ONE `medial_axis(rng=0)` call so the
    skeleton and exact EDT come back together, on one grid, from one pass —
    the patent-record architecture's step 406. Returns None for a
    degenerate/empty polygon (mirrors `extract_strokes`'s own `mask.any()`
    guard).

    `rng=0` is REQUIRED for determinism, exactly as
    `stage6_satin.extract_strokes` documents: unseeded, `medial_axis` breaks
    ties between equally valid skeleton pixels in a randomly permuted order,
    and the same artwork would digitize differently run to run.
    """
    mask, scale, ox, oy = rasterize_polygon(poly)
    if not mask.any():
        return None
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    return ShapeField(mask=mask.astype(bool), skel=skel, dist=dist,
                       scale=scale, ox=ox, oy=oy)
