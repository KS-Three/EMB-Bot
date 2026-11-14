"""Curve densify (2026-11-14, `PipelineConfig.curve_chord_mm`, built None = OFF).

A clean curve written as chords sews as chords: the satin's ends and a
fill's row ends follow each chord straight, then turn at its vertex. Kent
pinned it 18 times (`docs/jag-source-2026-11-13.md`, (b)), and traced
stage by stage (`docs/curve-facets-2026-11-14.md`) two places make the
chords his pins sit on:

- the Column lane (`outline_cut._letter_columns`) re-simplifies each letter
  at max(0.12 mm, W / 16) before cutting it into stroke pieces, so a bowl
  reaches the rails as 2-2.6 mm chords turning 20-30 degrees, whatever
  stage 4 handed it (15 of the 18 pins: every lettering bowl);
- stage 4's curve refinement stops at `curve_turn_deg` (15 degrees) or its
  one-pixel floor, and under 20 px/mm splits no chord the sub-pixel read
  did not accept: a fill's edge keeps 1-3 mm chords (Gaulke's circle).

`densify_curves` is the one geometry both sites call: each edge of a clean
curve is split into pieces no longer than the chord, on a tangent-continuous
cubic through the ring's OWN vertices. Nothing reads a raster, nothing is
smoothed (DOCTRINE's measured negative blurred polygons by a radius): every
existing vertex stays exactly where it was, corners and straight runs keep
their chords, and an edge whose new points do not ALL lie within `guard`
of the trace it was simplified from keeps its chord.
"""
from __future__ import annotations

import math

import numpy as np

# A vertex turning more than this is a CORNER: the curve meets it along its
# chord and it is never rounded. Stage 4's facets turn 12-20 degrees, the
# Column lane's 20-30, a 9.8 px/mm trace's (3 mm chords on a 5 mm radius)
# about 35; a serif, a stem's foot or a polygon's corner turns 60-90.
CORNER_DEG = 45.0
# ...and so is a vertex turning this much more than both its neighbours,
# above `SPIKE_MIN_DEG`: a corner in a gentle run, not a curve.
SPIKE_RATIO = 2.5
SPIKE_MIN_DEG = 10.0
# A vertex turning less than this is on a straight run: no edge beside it
# bends. Two degrees is a 3 mm chord on an 86 mm radius.
STRAIGHT_DEG = 2.0


def _rot(v: np.ndarray, a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])


def densify_curves(ring: np.ndarray, trace, chord: float, guard: float) -> np.ndarray:
    """`ring` (closed, no repeated last vertex, any unit) with every edge of
    a clean CURVE split into pieces no longer than `chord`.

    An edge bends when both ends are on the curve (neither a corner by
    `CORNER_DEG` or `SPIKE_RATIO`, each turning at least `STRAIGHT_DEG`, the
    same way), or one end is and the other is a corner (a bowl's first chord
    off its stem). Its tangent at a vertex is the bisector of the two chords
    there when the edge beyond bends too, the neighbour's own direction when
    that edge is straight (the curve meets it tangentially), and its own
    chord at a corner (never rounded). An edge whose inserted points do not
    ALL lie within `guard` of `trace` (an (N, 2) closed contour, or any
    shapely geometry: the outline the ring was simplified from) keeps its
    chord. Returns `ring` itself when nothing changes."""
    import shapely
    from shapely.geometry import LinearRing, Polygon

    P = np.asarray(ring, dtype=np.float64)
    n = len(P)
    if n < 4 or chord <= 0.0:
        return ring
    d = np.roll(P, -1, axis=0) - P                      # edge i: P[i] -> P[i+1]
    L = np.hypot(d[:, 0], d[:, 1])
    if (L < 1e-12).any():
        return ring
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = (ang - np.roll(ang, 1) + np.pi) % (2.0 * np.pi) - np.pi   # at vertex i
    at = np.abs(turn)
    nb = np.maximum(np.roll(at, 1), np.roll(at, -1))
    corner = (at > math.radians(CORNER_DEG)) | (
        (at > math.radians(SPIKE_MIN_DEG)) & (at > SPIKE_RATIO * nb))
    live = ~corner & (at >= math.radians(STRAIGHT_DEG))
    j = (np.arange(n) + 1) % n
    bends = ((live & live[j] & (np.sign(turn) == np.sign(turn[j])))
             | (live & corner[j]) | (corner & live[j]))
    bends &= L > chord
    if not bends.any():
        return ring
    # what the NEIGHBOUR edge does decides the tangent, whatever its length
    curve_edge = ((live & live[j] & (np.sign(turn) == np.sign(turn[j])))
                  | (live & corner[j]) | (corner & live[j]))
    prev_curve = np.roll(curve_edge, 1)
    phi0 = np.where(corner, 0.0, np.where(prev_curve, turn / 2.0, turn))
    phi1 = np.where(corner[j], 0.0, np.where(curve_edge[j], turn[j] / 2.0, turn[j]))

    pieces: dict[int, np.ndarray] = {}
    for i in np.flatnonzero(bends):
        k = int(math.ceil(L[i] / chord))
        u = d[i] / L[i]
        m0 = _rot(u, -phi0[i]) * L[i]
        m1 = _rot(u, phi1[i]) * L[i]
        t = np.arange(1, k, dtype=np.float64)[:, None] / k
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        pieces[int(i)] = h00 * P[i] + h10 * m0 + h01 * P[j[i]] + h11 * m1
    if hasattr(trace, "geom_type"):
        tr = trace
    else:
        tr = LinearRing(np.asarray(trace, dtype=np.float64).reshape(-1, 2))
    out: list[np.ndarray] = []
    added = 0
    for i in range(n):
        out.append(P[i][None, :])
        q = pieces.get(i)
        if q is not None and float(shapely.distance(shapely.points(q), tr).max()) <= guard:
            out.append(q)
            added += len(q)
    if not added:
        return ring
    res = np.vstack(out)
    if Polygon(P).is_valid and not Polygon(res).is_valid:
        return ring
    return res


def densify_polygon(poly, trace, chord: float, guard: float):
    """Every ring of a shapely Polygon through `densify_curves`; the polygon
    itself when nothing changes or the result would not be valid."""
    from shapely.geometry import Polygon
    if poly.is_empty or poly.geom_type != "Polygon":
        return poly
    changed = False
    rings = []
    for r in [poly.exterior] + list(poly.interiors):
        R = np.asarray(r.coords, dtype=np.float64)[:-1]
        D = densify_curves(R, trace, chord, guard)
        changed |= D is not R
        rings.append(D)
    if not changed:
        return poly
    out = Polygon(rings[0], rings[1:])
    return out if out.is_valid and not out.is_empty else poly
