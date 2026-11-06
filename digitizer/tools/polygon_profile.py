"""A polygon-native width profile for the satin/fill DT gates -- measured
negative #9 for defect 26 (2026-11-06,
`docs/classifier-polygon-profile-2026-11-06.md`).

MEASUREMENT ONLY: `tools/ribbon_stability.py --variant profile` (and
`profile:raw`) reads `stage6_satin._dt_stats`' six numbers off the polygon
instead of a thinned raster, and the engine never imports this.

The construction. The medial axis is the Voronoi diagram of the boundary
sampled at half a classifier pixel, restricted to ridges inside the shape
whose two generators do not sit on one polygon edge (those are sampling
artefacts, not axis). Every ridge is a station: its radius is the EXACT
shapely distance from its midpoint to the boundary, and it counts for its
length times its OBJECT-ANGLE significance `s = |p - q| / 2r`, the
half-chord between its generators over the radius. Nothing is pruned -- the
2026-09-03 record measured pruning negative three ways, because on a compact
shape the twigs ARE the medial axis. A spine between opposite walls reads
s = 1; the twig into a convex corner of interior angle t reads cos(t/2)
(0.71 for a square corner, which the raster also keeps); a near-flat
vertex's twig reads ~0. Splitting one corner into two gentler ones splits
its weight between them, so the twig weight follows the boundary's turning,
not its vertex count.

`profile` drops stations under one classifier pixel (`_rasterize`'s own
scale, `max(6, 8 / wall)` px/mm capped at 900 px across): the thresholds were
tuned on a skeleton that never sees a radius under one pixel, and without
the floor every small shape's corner twigs run to r = 0 and its cv reads
0.03-0.13 higher (`profile:raw`, 31 shipped verdicts changed against 21).

Chosen over `polygon_axis.skeleton_for` / `extract_strokes`: both PRUNE (the
arc rule at 1.6 radii), and a pruned axis loses the blob detector -- a hard
prune at 3.2 or 2.2 radii satins the 0.3 mm serrated disc (cv 0.33, p90
0.37 mm: the disc body is pruned away and only the tooth twigs are left).
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon

from digitizer_core import stage6_satin as s6
from digitizer_core.stage6_satin import _DtStats

# Boundary sample pitch, in classifier pixels: `polygon_axis.DENSIFY_PX`.
SAMPLE_PX = 0.5


def classifier_px_mm(poly: Polygon) -> float:
    """One pixel of `stage6_satin._rasterize`'s adaptive grid, in mm."""
    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0)
    wall = s6.ribbon_width_mm(poly)
    need = s6._RASTER_PX_PER_MM if wall <= 0 else max(s6._RASTER_PX_PER_MM, 8.0 / wall)
    return 1.0 / min(need, s6._RASTER_MAX_PX / max(dim, 1e-6))


def _samples(poly: Polygon, step: float):
    """Boundary samples, and the polygon edge(s) each one sits on (a vertex
    sits on both of its edges)."""
    import shapely

    pts, edge_a, edge_b, base = [], [], [], 0
    for part in shapely.get_parts(poly):
        for ring in (part.exterior, *part.interiors):
            c = np.asarray(ring.coords, np.float64)
            if len(c) > 1 and np.allclose(c[0], c[-1]):
                c = c[:-1]
            n = len(c)
            if n < 3:
                continue
            for i in range(n):
                p0, p1 = c[i], c[(i + 1) % n]
                k = max(1, int(math.ceil(float(np.hypot(*(p1 - p0))) / step)))
                pts.append(p0 + (np.arange(k)[:, None] / k) * (p1 - p0))
                a = np.full(k, base + i)
                b = a.copy()
                b[0] = base + (i - 1) % n
                edge_a.append(a)
                edge_b.append(b)
            base += n
    if not pts:
        return None
    return np.vstack(pts), np.concatenate(edge_a), np.concatenate(edge_b)


def profile_stats(poly: Polygon, *, floor_px: float = 1.0) -> _DtStats | None:
    """`_dt_stats`' six numbers off the polygon's own medial axis.

    `floor_px` drops stations whose radius is under that many classifier
    pixels (0 keeps every station: `profile:raw`). None when the shape has
    no interior ridge, which `classify_ribbon` reads as `dt_degenerate`
    exactly as it reads a raster too small to thin.
    """
    import shapely
    from scipy.spatial import Voronoi

    if poly.is_empty or s6.ribbon_width_mm(poly) <= 0:
        return None
    px = classifier_px_mm(poly)
    smp = _samples(poly, SAMPLE_PX * px)
    if smp is None or len(smp[0]) < 4:
        return None
    P, ea, eb = smp
    try:
        vor = Voronoi(P)
    except Exception:       # QhullError on degenerate input
        return None
    gp = np.asarray(vor.ridge_points)
    rv = np.array([v if len(v) == 2 else (-1, -1) for v in vor.ridge_vertices])
    p, q = gp[:, 0], gp[:, 1]
    keep = ((rv[:, 0] >= 0) & (rv[:, 1] >= 0)
            & (ea[p] != ea[q]) & (ea[p] != eb[q]) & (eb[p] != ea[q]) & (eb[p] != eb[q]))
    if not keep.any():
        return None
    gp, rv = gp[keep], rv[keep]
    A, B = vor.vertices[rv[:, 0]], vor.vertices[rv[:, 1]]
    shapely.prepare(poly)
    inside = shapely.contains(poly, shapely.linestrings(np.stack([A, B], axis=1)))
    if not inside.any():
        return None
    A, B, gp = A[inside], B[inside], gp[inside]
    length = np.hypot(*(B - A).T)
    r = np.asarray(shapely.distance(shapely.points(0.5 * (A + B)), poly.boundary), np.float64)
    chord = np.hypot(*(P[gp[:, 0]] - P[gp[:, 1]]).T)
    w = np.clip(chord / (2.0 * np.maximum(r, 1e-12)), 0.0, 1.0) * length
    ok = (w > 0) & (r > 0) & (r >= floor_px * px)
    if not ok.any():
        return None
    r, w = r[ok], w[ok]
    mean = float(np.average(r, weights=w))
    std = float(np.sqrt(np.average((r - mean) ** 2, weights=w)))
    spine_len_mm = float(w.sum())
    width_mm = 2.0 * mean
    swept = spine_len_mm * width_mm
    return _DtStats(
        mean=mean, std=std,
        p90_mm=2.0 * s6._weighted_percentile(r, w, s6._DT_TIGHTEN_PERCENTILE),
        spine_len_mm=spine_len_mm,
        explained=(float(poly.area) / swept) if swept > 0 else 0.0,
        elongation=(spine_len_mm / width_mm) if width_mm > 0 else 0.0,
    )
