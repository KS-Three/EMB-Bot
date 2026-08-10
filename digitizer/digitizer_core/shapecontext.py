"""Shape Context Descriptor — Belongie, Malik & Puzicha 2002 ("Shape Matching
and Object Recognition Using Shape Contexts"), a classical (pre-deep-learning)
shape-similarity measure: sample points around a shape's boundary, describe
each point's neighbourhood by a log-polar histogram of where every OTHER
sampled point sits relative to it, then find the cheapest one-to-one
correspondence between two shapes' point sets (the Hungarian algorithm, via
`scipy.optimize.linear_sum_assignment`) and report the matched cost. No
maintained Python package implements this (confirmed before writing this
module) — it is ~150 lines of numpy from the paper's own description, not a
dependency this repo is missing by oversight.

**What this module answers, and what it does NOT answer**: given two shapes,
how structurally similar is their POINT ARRANGEMENT — same general silhouette
(and hole layout), same relative proportions — regardless of the shapes'
absolute position, scale, or exact vertex count. It does NOT identify what a
shape depicts (no OCR, no character recognition, no template library of
letterforms) — it is a pure geometry comparison between two point sets, the
same "no OCR anywhere in this slice" discipline `textcluster.py`'s own module
docstring states. This module's one caller
(`textcluster.regularize_text_clusters`) uses it exactly that way: comparing
a SINGLE shape's geometry before and after an edit, never comparing two
DIFFERENT shapes to guess whether they are the same letter.

## Scope decisions (read before changing the bin geometry)

- **Translation invariance is automatic, not implemented separately.** Every
  histogram entry is built from a PAIRWISE DIFFERENCE between two sampled
  points of the same shape (`points[i] - points[j]`); translating the whole
  point set leaves every pairwise difference unchanged.
- **Scale invariance**: every pairwise distance is divided by the point set's
  OWN mean pairwise distance before binning (the paper's own normalization,
  section 2.1) — a shape and a 2x-larger copy of itself produce the same
  histograms.
- **Rotation invariance is deliberately NOT implemented.** The paper offers an
  optional tangent-relative angle variant for that; this module's one caller
  compares a shape to itself immediately before/after a geometry edit that
  never rotates it (`regularize_text_clusters` redraws a skeleton buffer in
  the SAME coordinate frame the original polygon was already in) — adding
  rotation invariance would only make the comparison LESS sensitive to a
  genuine defect (a corner that silently swung open), with no real case here
  that needs it. If a future caller needs to compare two independently-
  authored shapes, this is the first thing to revisit.
- **Holes are sampled too, not just the outer silhouette.** Points are drawn
  from the exterior ring AND every interior (hole) ring, proportional to each
  ring's share of the shape's total perimeter. A regularization pass that
  silently filled in a letter's counter (the hole in an "O", "e", "a", "b",
  "d"...) changes the hole ring's point count from "some" to "none" — that
  shows up as a real, large distance here; sampling the exterior only would
  miss it entirely.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon

# Points sampled per shape (evenly by arc length, split across the exterior
# ring and every hole ring by their share of the shape's total perimeter).
# The original paper uses ~100 for full-scene object silhouettes; this
# module's shapes are tiny rescued glyphs (a few hundred boundary pixels at
# most, see shapefield.py's own raster budget), so 64 is already several
# points per mm of a ~2 mm-tall letter's perimeter -- enough to resolve a
# corner or a filled-in hole without paying for a descriptor sized for a much
# bigger silhouette.
N_POINTS = 64

# Log-polar histogram bin counts (the paper's own figures, section 2.1's
# figure 2: 5 log-radius bins x 12 angle bins = 60 total).
N_RADIAL_BINS = 5
N_ANGULAR_BINS = 12

# Radial bin edges, in units of the point set's OWN mean pairwise distance
# (the scale-normalization above). log-spaced from an eighth of the mean
# distance up to twice it -- the paper's own figure spans a comparable
# multi-octave range; a point pair closer than the low edge or farther than
# the high edge still lands in the nearest (first/last) bin via the clip in
# `_log_polar_bins`, so no pair is ever discarded, only coarsely binned at
# the extremes.
_R_BIN_EDGES = np.logspace(np.log10(0.125), np.log10(2.0), N_RADIAL_BINS + 1)


def _sample_polygon_points(poly: Polygon, n: int) -> np.ndarray:
    """Evenly-by-arc-length sample `n` points total across `poly`'s exterior
    ring and every interior (hole) ring, split between rings proportional to
    each ring's share of the shape's total perimeter. Returns an (n, 2)
    array (fewer than `n` rows only if a ring is degenerate/zero-length), or
    an empty (0, 2) array if the polygon has no ring with positive length at
    all (mirrors `shapefield.build_shape_field`'s degenerate-input guard —
    the caller treats an under-sized result as "cannot compare", not a
    crash).
    """
    rings = [poly.exterior, *poly.interiors]
    lengths = [r.length for r in rings]
    total = sum(lengths)
    if total <= 0:
        return np.zeros((0, 2))

    pts: list[np.ndarray] = []
    for ring, length in zip(rings, lengths):
        if length <= 0:
            continue
        count = max(1, round(n * length / total))
        coords = np.asarray(ring.coords, dtype=np.float64)
        seg = np.hypot(np.diff(coords[:, 0]), np.diff(coords[:, 1]))
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        ring_len = cum[-1]
        if ring_len <= 0:
            continue
        targets = np.linspace(0.0, ring_len, count, endpoint=False)
        xs = np.interp(targets, cum, coords[:, 0])
        ys = np.interp(targets, cum, coords[:, 1])
        pts.append(np.column_stack([xs, ys]))
    if not pts:
        return np.zeros((0, 2))
    return np.concatenate(pts, axis=0)


def _log_polar_bins(points: np.ndarray) -> np.ndarray:
    """-> (n, n) int arrays (r_bin, theta_bin) stacked as a (2, n, n) array:
    for every ordered pair (i, j), which log-radius/angle bin point j falls
    into relative to point i, after normalizing every pairwise distance by
    the point set's own mean pairwise distance (scale invariance — see the
    module docstring). The diagonal (i == j) is meaningless and the caller
    excludes it, not this function.
    """
    diff = points[:, None, :] - points[None, :, :]  # (n, n, 2): j relative to i
    r = np.hypot(diff[..., 0], diff[..., 1])
    theta = np.arctan2(diff[..., 1], diff[..., 0])

    n = len(points)
    off_diag = ~np.eye(n, dtype=bool)
    mean_r = r[off_diag].mean() if n > 1 and off_diag.any() else 0.0
    r_norm = r / mean_r if mean_r > 0 else r

    r_bin = np.clip(np.searchsorted(_R_BIN_EDGES, r_norm, side="right") - 1,
                     0, N_RADIAL_BINS - 1)
    theta_bin = np.clip(((theta + np.pi) / (2 * np.pi) * N_ANGULAR_BINS).astype(int),
                         0, N_ANGULAR_BINS - 1)
    return np.stack([r_bin, theta_bin])


def _shape_context_histograms(points: np.ndarray) -> np.ndarray:
    """-> (n, N_RADIAL_BINS * N_ANGULAR_BINS) histogram per point: for point
    i, a count of every OTHER point j by (log-radius, angle) bin relative to
    i. Not normalized to sum 1 here — `_chi2_cost_matrix` normalizes both
    sides right before comparing, so shapes sampled at different point
    counts (a ring too short to hit the full `n`) still compare fairly.
    """
    n = len(points)
    hist = np.zeros((n, N_RADIAL_BINS, N_ANGULAR_BINS))
    if n < 2:
        return hist.reshape(n, -1)
    r_bin, theta_bin = _log_polar_bins(points)
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    off_diag = ii != jj
    np.add.at(hist, (ii[off_diag], r_bin[off_diag], theta_bin[off_diag]), 1)
    return hist.reshape(n, -1)


def _chi2_cost_matrix(hist_a: np.ndarray, hist_b: np.ndarray) -> np.ndarray:
    """-> (len(hist_a), len(hist_b)) pairwise chi-squared histogram distance,
    the paper's own point-to-point cost (section 2.2): 0.5 * sum((a-b)^2 /
    (a+b)) per bin. Both histograms are normalized to sum to 1 first (a
    probability distribution over relative position, not a raw count) so
    two shapes sampled at slightly different point counts still compare on
    equal footing.
    """
    def _normalize(h: np.ndarray) -> np.ndarray:
        totals = h.sum(axis=1, keepdims=True)
        totals[totals == 0] = 1.0
        return h / totals

    a, b = _normalize(hist_a), _normalize(hist_b)
    num = (a[:, None, :] - b[None, :, :]) ** 2
    den = a[:, None, :] + b[None, :, :]
    den[den == 0] = 1.0  # both zero -> numerator is also 0; the divide-by-1 is inert
    return 0.5 * (num / den).sum(axis=-1)


def shape_context_distance(poly_a: Polygon, poly_b: Polygon,
                            n_points: int = N_POINTS) -> float | None:
    """Shape Context distance between two polygons: sample `n_points` around
    each (exterior + holes, see module docstring), build each point's
    log-polar relative-position histogram, and return the MEAN chi-squared
    cost of the cheapest one-to-one point correspondence between the two
    sets (`scipy.optimize.linear_sum_assignment` — the paper's own matching
    step, section 3).

    0.0 means the two point sets' scale-normalized relative-position
    histograms match exactly under the best correspondence (structurally the
    same shape, any position/scale). Larger values mean the two shapes'
    point arrangements genuinely differ — a corner appeared or disappeared,
    a hole opened or closed, material moved from one part of the shape to
    another. There is no universal "same shape" threshold in the original
    paper; callers calibrate one against their own real cases (see
    `textcluster.py`'s `SHAPE_CONTEXT_MAX_DIST`, calibrated against this
    repo's own benchmark fixture).

    Returns None if either polygon is too degenerate to sample at least 3
    points from (mirrors `shapefield.build_shape_field`'s degenerate-input
    guard) — the caller treats that as "cannot compare", never a crash.
    """
    pts_a = _sample_polygon_points(poly_a, n_points)
    pts_b = _sample_polygon_points(poly_b, n_points)
    if len(pts_a) < 3 or len(pts_b) < 3:
        return None

    hist_a = _shape_context_histograms(pts_a)
    hist_b = _shape_context_histograms(pts_b)
    cost = _chi2_cost_matrix(hist_a, hist_b)
    row_ind, col_ind = linear_sum_assignment(cost)
    return float(cost[row_ind, col_ind].mean())
