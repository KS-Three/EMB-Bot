"""A medial axis read from the POLYGON, not from a raster of it.

Behind `cfg.satin_polygon_axis`, DEFAULT OFF; off, `stage6_satin` never
imports or executes any of this and the engine is byte-identical.

## Why this exists

`stage6_satin.extract_strokes` thins a 6 px/mm raster of the shape
(`_rasterize` + `skimage.medial_axis`) and then erases the twigs that
thinning grew (`_prune_spurs`, at 1.6 mean half-widths). The census measured
what that costs and what the alternatives buy
(`docs/superpowers/plans/2026-09-15-decomposition-census.md`):

  * a FINER raster is not the fix -- 12 and 24 px/mm are non-monotonic and
    often worse (becker at 80 mm: bare satin 12.2 -> 17.7 mm2 at 4x; drone
    111 -> 167 strokes). More pixels give the thinning more wiggles to
    branch on;
  * this construction, on the same corpus: bare satin becker 12.2 -> 4.2
    mm2, enthusiast 7.0 -> 0.0; trims -1 / -7 / -3 / -6; in-shape trims
    enthusiast 19 -> 9, drone 49 -> 44.

## The construction

The medial axis of a polygon is a subset of the Voronoi diagram of its
boundary: sample the boundary densely, take the Voronoi edges that lie
strictly inside, and the result is the axis plus one twig into every convex
corner. Pruning those twigs is the whole problem, and the test is NOT their
length:

**a bar's axis runs spine -> corner diagonal with no junction between them**,
so a leaf-length rule finds nothing to prune and leaves the hook into the cap
corner -- the shape of the H defect that made both 2026-08-26 `_prune_spurs`
prototypes unshippable. Measured on a 10 x 2 mm bar while writing this
(`tests/test_polygon_axis.py::test_a_bar_is_one_spine_with_no_corner_hooks`).

What separates a twig from artwork is WHERE ITS GENERATORS SIT ON THE
BOUNDARY. Every axis point is equidistant from two boundary points; for a
convex corner's twig those two sit about one radius either side of the
corner, so the arc between them stays ~2 radii all the way in, while a
spine's generators sit on opposite sides of the stroke and a real arm's are
a whole arm apart. So an edge is kept when

    arc between its generators  >  2 * SIGNIFICANCE_RADII * its radius

with `SIGNIFICANCE_RADII` the shipped spur multiplier, 1.6. A hole and the
exterior are different rings and never "close along the boundary", so a
ring's axis survives whole. (Published concept -- the boundary-arc potential
residual, Ogniewicz; no code taken from anywhere.)

The axis is then drawn onto the grid `_rasterize` already built, so
everything downstream (`_collapse_pinholes`, `_skeleton_edges`,
`_cluster_junctions`, `_merge_through_junctions`, `_split_sharp_corners`,
the rails, the travel graph) reads it exactly as it reads the thinned
skeleton. The geometry is sub-pixel; the WALK is not, and making the walk
native is a later step this flag does not take.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import MultiPoint, Polygon

# The shipped `_prune_spurs` multiplier, in half-widths. A convex corner's
# twig reads ~2 radii of generator arc, so it goes at any multiplier over 1;
# what this module changes is the reference (the LOCAL radius, not the
# shape's mean half-width) and the construction, never the number.
SIGNIFICANCE_RADII = 1.6
# Boundary sampling, as a fraction of one raster pixel: fine enough that the
# diagram's interior edges trace the axis well under the grid it is drawn on.
DENSIFY_PX = 0.5
# Generators tied for nearest, as a fraction of the sample step.
_TIE_FRAC = 0.02
_NEAREST_K = 8


def axis_segments(poly: Polygon, step_mm: float) -> list[tuple[tuple, tuple]]:
    """-> the polygon's medial axis as (p, q) segments in mm.

    Pure geometry: no raster, no engine state. `step_mm` is the boundary
    sampling pitch.
    """
    from scipy.spatial import cKDTree

    if step_mm <= 0 or poly.is_empty:
        return []
    dense = shapely.segmentize(poly, step_mm)
    # A satin shape can arrive as a MultiPolygon (measured on the corpus), so
    # every part's rings are sampled; parts never share an arc.
    rings = [r for part in shapely.get_parts(dense)
             for r in (part.exterior, *part.interiors)]
    pts, ring_of, arc_of, ring_len = [], [], [], []
    for ri, ring in enumerate(rings):
        c = np.asarray(ring.coords)[:-1]
        if len(c) < 3:
            continue
        seg = np.hypot(*np.diff(np.vstack([c, c[:1]]), axis=0).T)
        pts.append(c)
        ring_of.append(np.full(len(c), ri))
        arc_of.append(np.concatenate([[0.0], np.cumsum(seg)[:-1]]))
        ring_len.append(float(seg.sum()))
    if not pts:
        return []
    pts = np.vstack(pts)
    ring_of = np.concatenate(ring_of)
    arc_of = np.concatenate(arc_of)

    vd = shapely.voronoi_polygons(MultiPoint([tuple(p) for p in pts]), only_edges=True)
    edges = np.asarray(shapely.get_parts(vd))
    if len(edges) == 0:
        return []
    shapely.prepare(poly)
    edges = edges[shapely.contains(poly, edges)]
    edges = np.asarray([e for e in edges if len(e.coords) == 2])
    if len(edges) == 0:
        return []
    coords = shapely.get_coordinates(edges)
    a, b = coords[0::2], coords[1::2]
    mid = 0.5 * (a + b)

    tree = cKDTree(pts)
    dist, idx = tree.query(mid, k=min(_NEAREST_K, len(pts)))
    tol = _TIE_FRAC * step_mm
    keep = np.zeros(len(mid), bool)
    for i in range(len(mid)):
        near = idx[i][dist[i] <= dist[i][0] + tol]
        radius = float(dist[i][0])
        widest = 0.0
        for u in range(len(near)):
            for v in range(u + 1, len(near)):
                p, q = near[u], near[v]
                if ring_of[p] != ring_of[q]:
                    widest = math.inf
                    break
                d = abs(arc_of[p] - arc_of[q])
                widest = max(widest, min(d, ring_len[ring_of[p]] - d))
            if widest == math.inf:
                break
        keep[i] = widest > 2.0 * SIGNIFICANCE_RADII * radius
    return [((float(p[0]), float(p[1])), (float(q[0]), float(q[1])))
            for p, q in zip(a[keep], b[keep])]


def draw(segs, mask: np.ndarray, scale: float, ox: float, oy: float) -> np.ndarray:
    """Draw axis segments onto `_rasterize`'s grid as a 1-px skeleton.

    `_rasterize` paints with `px = (x - x0) * scale + 2` and returns
    `ox = x0 - 2 / scale`, i.e. `px = (x - ox) * scale`; `extract_strokes`
    reads a pixel back at its centre. Same mapping here, so a walk of this
    skeleton lands where a walk of the thinned one would.
    """
    from skimage.draw import line
    from skimage.morphology import skeletonize

    h, w = mask.shape
    img = np.zeros((h, w), bool)
    for (ax, ay), (bx, by) in segs:
        r0, c0 = int(math.floor((ay - oy) * scale)), int(math.floor((ax - ox) * scale))
        r1, c1 = int(math.floor((by - oy) * scale)), int(math.floor((bx - ox) * scale))
        rr, cc = line(r0, c0, r1, c1)
        ok = (rr >= 0) & (rr < h) & (cc >= 0) & (cc < w)
        img[rr[ok], cc[ok]] = True
    img &= mask > 0
    # Drawn segments cross at junctions and land two-pixels-thick on a
    # diagonal; `skeletonize` returns the 1-px, 8-connected form the walker
    # in `_skeleton_edges` expects from `medial_axis`.
    return skeletonize(img)


def skeleton_for(poly: Polygon, mask: np.ndarray, scale: float,
                 ox: float, oy: float) -> tuple[np.ndarray, np.ndarray]:
    """-> (skeleton, distance transform) on `_rasterize`'s grid.

    The `medial_axis(mask, return_distance=True)` pair `extract_strokes`
    consumes, with the skeleton read from the polygon instead of thinned
    from the mask. The distance transform is the mask's own, unchanged: it
    measures the shape, not the skeleton.
    """
    from scipy.ndimage import distance_transform_edt

    segs = axis_segments(poly, DENSIFY_PX / scale)
    return draw(segs, mask, scale, ox, oy), distance_transform_edt(mask > 0)
