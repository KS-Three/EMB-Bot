"""Prototype: a small three-sided counter sewn as ONE fanned satin, the pro's way.
fan_satin(poly) -> (underlay pts, satin pts) or None. Rails = the two sides that meet at the
sharpest corner (the tip); crosses pair the rails by arc-length fraction, so at the base the
cross IS the base edge and toward the tip it turns and shortens. Zigzag underlay tip -> base on
rails inset, then satin base -> tip. Every cross <= max_cross_mm, else None."""
import math

import numpy as np
from shapely.geometry import LineString, Polygon

SPACING = 0.4        # machine.SATIN_SPACING_MM
UNDER_INSET = 0.4
UNDER_PITCH = 2.0


def corners(poly: Polygon, tol=0.25, straight_deg=150.0):
    ring = poly.exterior.simplify(tol)
    pts = list(ring.coords)[:-1]
    if Polygon(pts).exterior.is_ccw is False:
        pts = pts[::-1]
    n = len(pts)
    out = []
    for i in range(n):
        a, b, c = np.array(pts[i - 1]), np.array(pts[i]), np.array(pts[(i + 1) % n])
        u, v = a - b, c - b
        ang = math.degrees(math.acos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1)))
        cross = (b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0]
        out.append((ang, cross > 0, i, tuple(b)))
    return pts, out


def three_sided(poly: Polygon):
    """-> (tip, base_a, base_b, ring pts) when exactly three convex corners are sharper than
    `straight_deg` and no concave corner is, else None."""
    pts, cs = corners(poly)
    sharp = [c for c in cs if c[0] < 150.0]
    if any(not c[1] for c in sharp):
        return None
    if len(sharp) != 3:
        return None
    sharp.sort(key=lambda c: c[0])
    tip = sharp[0]
    others = sorted(sharp[1:], key=lambda c: c[2])
    return tip, others[0], others[1], pts


def path(pts, i, j):
    """Ring vertices from index i to j going forward."""
    n, out, k = len(pts), [pts[i]], i
    while k != j:
        k = (k + 1) % n
        out.append(pts[k])
    return LineString(out)


def wedge(poly: Polygon, tol=0.4):
    """-> (tip index, base a index, base b index, ring pts): the tip is the sharpest convex
    corner, the base corners the next two; the ring forward from the tip meets base a first."""
    pts, cs = corners(poly, tol=tol)
    conv = sorted([c for c in cs if c[1]], key=lambda c: c[0])
    if len(pts) < 3 or len(conv) < 3:
        return None
    tip, x, y = conv[0][2], conv[1][2], conv[2][2]
    n = len(pts)
    fwd = lambda j: (j - tip) % n  # noqa: E731
    a, b = (x, y) if fwd(x) < fwd(y) else (y, x)
    return tip, a, b, pts


def fan_satin(poly: Polygon, max_cross_mm=5.0, pull_mm=0.3, spacing=SPACING, inside_tol=0.15):
    w = wedge(poly)
    if w is None:
        return None
    tip_i, a_i, b_i, pts = w
    ra = path(pts, tip_i, a_i)               # tip -> base a, forward
    rb = path(pts, b_i, tip_i)               # base b -> tip, forward
    rb = LineString(list(rb.coords)[::-1])   # tip -> base b

    zone = poly.buffer(inside_tol)
    n = max(2, int(math.ceil(max(ra.length, rb.length) / (spacing / 2.0))))
    crosses = []
    for k in range(n + 1):
        f = k / n
        p = np.array(ra.interpolate(f, normalized=True).coords[0])
        q = np.array(rb.interpolate(f, normalized=True).coords[0])
        crosses.append((p, q))
    longest = max(np.linalg.norm(p - q) for p, q in crosses)
    if longest > max_cross_mm:
        return None
    outside = sum(1 for p, q in crosses if not zone.contains(LineString([tuple(p), tuple(q)])))
    if outside > 0.05 * len(crosses):
        return None
    # satin base -> tip, alternating rails, each end pushed out by the pull along its cross
    sat = []
    for k, (p, q) in enumerate(reversed(crosses)):
        d = q - p
        L = np.linalg.norm(d)
        if L < 1e-6:
            continue
        u = d / L
        pe, qe = p - u * pull_mm, q + u * pull_mm
        sat += [tuple(pe), tuple(qe)] if k % 2 == 0 else [tuple(qe), tuple(pe)]
    # zigzag underlay tip -> base on the rails inset
    under = []
    m = max(2, int(math.ceil(max(ra.length, rb.length) / UNDER_PITCH)))
    for k in range(m + 1):
        f = k / m
        p = np.array(ra.interpolate(f, normalized=True).coords[0])
        q = np.array(rb.interpolate(f, normalized=True).coords[0])
        d = q - p
        L = np.linalg.norm(d)
        if L < 2 * UNDER_INSET + 0.1:
            continue
        u = d / L
        under.append(tuple(p + u * UNDER_INSET) if k % 2 == 0 else tuple(q - u * UNDER_INSET))
    return under, sat, {"base_cross": round(float(np.linalg.norm(crosses[-1][0] - crosses[-1][1])), 2),
                        "longest": round(float(longest), 2), "crosses": len(crosses)}
