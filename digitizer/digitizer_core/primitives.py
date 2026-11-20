"""Read the simple shape first (`cfg.read_primitives`, ON since 2026-11-19).

Kent, 2026-11-19: "a square needs to be square / a circle round / a triangle
needs 3 points / you need to do a better job reading the image before
digitizing", and "flow": like shapes sew alike. The tracer hands every shape
its own wobble: one square has corners rounded 0.3 mm, its twin 0.1 mm. Each
is fine alone; the set does not flow.

A region whose traced outline lies within `tol_mm` of an ideal rectangle,
circle or triangle (Hausdorff, both ways) is replaced by that ideal shape
BEFORE anything else reads it, so two like shapes reach stage 5 and the sewing
tiers as the same shape. Anything that is not clearly one of the three is
returned untouched, and so is a shape that already is one.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
from shapely.geometry import Point, Polygon, box

#: how far the traced outline may lie from the ideal shape (mm). A corner of
#: radius r sits 0.414 r off its square corner, so 0.2 reads corners rounded
#: up to about 0.48 mm: tracing's rounding, not drawn rounding.
PRIMITIVE_TOL_MM = 0.2
#: ... and never more than this share of the shape's short side.
PRIMITIVE_TOL_FRAC = 0.06
#: the shape must fill this much of the ideal one
PRIMITIVE_MIN_FILL = 0.94
#: smaller than this, the tolerance is below the stitch's own width
PRIMITIVE_MIN_SIDE_MM = 1.5
CIRCLE_SEGMENTS = 64
AXIS_SNAP_DEG = 0.5
#: below this deviation a shape already is its ideal; leave it byte for byte
ALREADY_MM = 0.01


def _tol(short_side: float) -> float:
    return min(PRIMITIVE_TOL_MM, PRIMITIVE_TOL_FRAC * short_side)


def _fits(poly: Polygon, ideal: Polygon, tol: float) -> bool:
    if ideal.is_empty or not ideal.is_valid or ideal.area <= 0:
        return False
    if poly.area < PRIMITIVE_MIN_FILL * ideal.area:
        return False
    return poly.hausdorff_distance(ideal) <= tol


def read_primitive(poly: Polygon) -> tuple[str, Polygon] | None:
    """-> (kind, ideal polygon) with kind in rect / circle / triangle, or None
    when the outline is none of them (or already exactly one)."""
    if poly.is_empty or poly.geom_type != "Polygon" or poly.interiors or poly.area <= 0:
        return None
    rect = poly.minimum_rotated_rectangle
    c = list(getattr(rect, "exterior", None).coords) if rect.geom_type == "Polygon" else []
    if len(c) < 5:
        return None
    s0, s1 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    long_side, short_side = max(s0, s1), min(s0, s1)
    if short_side < PRIMITIVE_MIN_SIDE_MM:
        return None
    tol = _tol(short_side)
    # A rectangle within half a degree of the axes IS axis-aligned: tracing
    # jitter tilts its minimum rectangle by hundredths of a degree, which
    # would sew each stripe's end a hair off its neighbours'.
    ang = math.degrees(math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0])) % 90.0
    if min(ang, 90.0 - ang) < AXIS_SNAP_DEG:
        rect = box(*poly.bounds)
    found = None
    if _fits(poly, rect, tol):
        found = ("rect", rect)
    else:
        # circle: the least-squares circle through the VERTICES (Kasa fit).
        # The traced vertices lie on the art's edge and the chords between
        # them sag inside it, so the area's own radius (sqrt(area / pi))
        # about the centroid came out short: a low-res cutout disc sat
        # 0.07 mm inside its circle (`test_coverage_edges`, 0.02 allowed).
        cx, cy, r = _circle_fit(list(poly.exterior.coords)[:-1])
        circ = Point(cx, cy).buffer(r, CIRCLE_SEGMENTS // 4)
        if long_side / short_side < 1.15 and _fits(poly, circ, tol):
            found = ("circle", circ)
        else:
            tri = _triangle(poly)
            # a 60 degree tip rounded by r sits r (1/sin 30 - 1) = r off, a
            # square corner 0.414 r: the triangle's tolerance is 1.6 x
            if tri is not None and _fits(poly, tri, 1.6 * tol):
                found = ("triangle", tri)
    if found is None:
        return None
    if poly.hausdorff_distance(found[1]) <= ALREADY_MM:
        return None
    return found


def _circle_fit(pts: list) -> tuple[float, float, float]:
    """Least-squares (Kasa) circle through `pts` -> (cx, cy, r)."""
    import numpy as np
    a = np.asarray(pts, dtype=float)
    m = np.column_stack([a[:, 0], a[:, 1], np.ones(len(a))])
    b = -(a[:, 0] ** 2 + a[:, 1] ** 2)
    d, e, f = np.linalg.lstsq(m, b, rcond=None)[0]
    cx, cy = -d / 2.0, -e / 2.0
    return float(cx), float(cy), float(math.sqrt(max(cx * cx + cy * cy - f, 0.0)))


def _triangle(poly: Polygon) -> Polygon | None:
    import cv2
    pts = np.asarray(poly.convex_hull.exterior.coords[:-1], dtype=np.float32)
    if len(pts) < 3:
        return None
    try:
        area, tri = cv2.minEnclosingTriangle(pts)
    except cv2.error:        # degenerate hulls make OpenCV raise: not a triangle
        return None
    if tri is None or area <= 0:
        return None
    t = Polygon([tuple(map(float, p)) for p in tri.reshape(-1, 2)])
    return t if t.is_valid and t.area > 0 else None


def read_regions(regions: list, report: dict | None = None) -> list:
    """`regions` with every region that is a clear rectangle, circle or
    triangle swapped for the ideal one (polygon and area_mm2 only; the
    shape_id, thread and meta are the region's own)."""
    out = []
    for r in regions:
        got = read_primitive(r.polygon)
        if got is None:
            out.append(r)
            continue
        kind, ideal = got
        if report is not None:
            report[kind] = report.get(kind, 0) + 1
        out.append(replace(r, polygon=ideal, area_mm2=float(ideal.area),
                           meta={**r.meta, "primitive": kind}))
    return out
