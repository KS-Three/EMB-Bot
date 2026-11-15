"""A small three-sided counter sewn as ONE fanned satin, the way the pro's
file sews it (`cfg.extra["counter_fan_satin"]`, built OFF 2026-11-14).

Kent's MFab pin "random stitch in the middle" and his word that day, "I want it
exactly like the pros". The A's white counter in M-FAB (hat, 104.9 mm) is a
triangle with a narrow arm up its right side. In the pro's file
(`docs/counter-fan-2026-11-14.md`, with the sheets and closeness) it is:
- an underlay of zigzag stitches plus a short run into the tip;
- then ONE satin from the base to the tip, its crosses TURNING:
  - 3 deg at the base, about 40 deg mid-shape, 80-90 deg in the narrow arm,
    where they run along it;
  - lengths from 5.73 mm at the base down to 1.5 mm at the tip.

Ours sewed it as a fill, and before #1519 a bean loop on top. The satin tier
splits it into two columns whose caps bulge past the triangle.

THE CONSTRUCTION, a pivoting sweep (`counter_fan_runs`):
- **The wedge.** The tip is the sharpest convex corner of the ring
  simplified at `FAN_RING_TOL_MM`; the two base corners are the next two.
- **The rails.** The OUTER rail is the longer boundary path from a base
  corner to the tip, the inner rail the other.
- **The stations.** The outer end steps along the outer rail from its base
  corner to the tip, every half satin spacing.
- **The pivot.** The inner end climbs the inner rail in step, but stops
  `FAN_TIP_LAG_SHARE` of that rail short of the tip. Near the tip it all but
  stands still while the outer end keeps climbing, so the crosses turn about
  it: the base edge's direction at the base, lying along the inner rail in
  the narrow arm, the way the pro's 3 -> 40 -> 85 deg does.
- **Why not paired rails.** Pairing the rails by arc length all the way to
  the tip (the 11-14 prototype) keeps the crosses near-parallel, and the
  narrow arm never turns. The lagging pivot turns it.
- **Order.** Satin from the base to the tip, alternating ends, each end
  pushed out by the fabric's pull along its cross (the magnitude is not
  touched: gate 1). It is preceded by a zigzag underlay from the tip to the
  base on the rails inset `FAN_UNDER_INSET_MM`, whose first legs in the
  narrow arm are the pro's run into the tip.

REFUSALS (`None`: the shape sews as it did):
- no three dominant convex corners;
- a cross longer than `max_cross_mm`, which reads
  `machine.SATIN_MAX_WIDTH_MM` (5.0) by default. **The ceiling is gate 1 and
  stays**: the pro crosses 5.73 mm on MFab's 104.9 mm counter, so there it
  refuses (our base cross 5.37 mm; 5.11 at 96 mm), and fits from about 93 mm
  down. Allowing more is Kent's call, after a sew-out;
- crosses that cross one another;
- a sweep that leaves part of the shape bare.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Polygon

from . import machine, stitches
from .stitches import StitchRun

FAN_RING_TOL_MM = 0.4       # the ring is read for its corners at this simplify
FAN_STRAIGHT_DEG = 150.0    # a vertex this open is no corner
FAN_CORNER_MAX_DEG = 120.0  # each of the three corners at least this sharp
FAN_TRIANGLE_FIT = (0.8, 1.25)  # shape area over its corner triangle's
# Area over convex hull: the counters it is for read 0.71 (MFab's A, notched
# by its arm) to 1.0 (ProSeal's and Drone's A, Bukit Asam's); the vintage
# badge's engraving specks that also pass the corner test read 0.34-0.56.
FAN_SOLID_MIN = 0.65
FAN_UNDER_INSET_MM = 0.4    # the underlay zigzag stays this far in from each rail
FAN_UNDER_PITCH_MM = 2.0    # zigzag legs along the outer rail
FAN_MIN_CROSS_MM = 0.3      # a cross shorter than this ends the sweep (the tip)
FAN_COVER_MIN = 0.9         # the sweep must reach this share of the shape
# Where the inner end stops, as a share of the inner rail short of the tip:
# the pro's last crosses in MFab's arm run 1.5-1.95 mm down a 7.6 mm side
# (0.2-0.26). Layout read off his file, not a fabric constant.
FAN_TIP_LAG_SHARE = 0.22
FAN_INSIDE_TOL_MM = 0.15    # a cross may graze the outline by this much
FAN_OUTSIDE_MM = 0.1        # ...and leave it by no more than this (a trace's notch)


def _ring(poly: Polygon) -> list[tuple[float, float]]:
    pts = list(poly.exterior.simplify(FAN_RING_TOL_MM).coords)[:-1]
    if not Polygon(pts).exterior.is_ccw:
        pts = pts[::-1]
    return pts


def _corners(pts) -> list[tuple[float, int]]:
    """(interior angle deg, index) of each convex vertex sharper than
    `FAN_STRAIGHT_DEG` on a ccw ring."""
    n, out = len(pts), []
    for i in range(n):
        a, b, c = np.array(pts[i - 1]), np.array(pts[i]), np.array(pts[(i + 1) % n])
        u, v = a - b, c - b
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu < 1e-9 or nv < 1e-9:
            continue
        ang = math.degrees(math.acos(float(np.clip(u @ v / (nu * nv), -1.0, 1.0))))
        turn = (b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0]
        if turn > 0 and ang < FAN_STRAIGHT_DEG:
            out.append((ang, i))
    return out


def _path(pts, i: int, j: int) -> LineString:
    n, out, k = len(pts), [pts[i]], i
    while k != j:
        k = (k + 1) % n
        out.append(pts[k])
    return LineString(out)


def wedge(poly: Polygon):
    """-> (tip, outer rail tip->base, inner rail base->tip, outer base corner,
    inner base corner) or None."""
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return None
    if poly.area < FAN_SOLID_MIN * poly.convex_hull.area:
        return None
    pts = _ring(poly)
    if len(pts) < 3:
        return None
    cs = sorted(_corners(pts))
    if len(cs) < 3 or cs[2][0] > FAN_CORNER_MAX_DEG:
        return None
    tip, x, y = cs[0][1], cs[1][1], cs[2][1]
    # three-sided: the shape all but fills the triangle of its three corners
    # (MFab's A counter 0.92; a round counter's best three corners, or a
    # square's, leave it half again or twice as large)
    tri = Polygon([pts[tip], pts[x], pts[y]])
    if tri.area < 1e-9 or not (FAN_TRIANGLE_FIT[0] <= poly.area / tri.area <= FAN_TRIANGLE_FIT[1]):
        return None
    # The corners are read on the simplified ring, but the rails walk the
    # REAL one: Douglas-Peucker keeps a subset of the ring's own vertices,
    # so each corner is one of them. Rails on the simplified ring leave the
    # traced edge's bulge bare (MFab's counter at 90 mm: 0.86 covered).
    full = list(poly.exterior.coords)[:-1]
    if not poly.exterior.is_ccw:
        full = full[::-1]
    fa = np.asarray(full, float)

    def at(i):
        return int(np.argmin(np.sum((fa - np.asarray(pts[i], float)) ** 2, axis=1)))
    t, x, y = at(tip), at(x), at(y)
    n = len(full)
    if len({t, x, y}) < 3:
        return None
    a, b = (x, y) if (x - t) % n < (y - t) % n else (y, x)
    ra = _path(full, t, a)                              # tip -> base a (forward)
    rb = LineString(list(_path(full, b, t).coords)[::-1])  # tip -> base b
    if ra.length >= rb.length:
        outer, inner, base_o, base_i = ra, rb, full[a], full[b]
    else:
        outer, inner, base_o, base_i = rb, ra, full[b], full[a]
    return full[t], outer, inner, base_o, base_i


def fan_crosses(poly: Polygon, spacing_mm: float, max_cross_mm: float):
    """-> list of (outer end, inner end) from the base to the tip, or None.

    The pivoting sweep: the outer end climbs the outer rail evenly; the inner
    end climbs the inner rail but stops `FAN_TIP_LAG_SHARE` of that rail short
    of the tip, so toward the tip it all but stands still while the outer end
    keeps climbing, and the crosses turn about it. At the base the cross is
    the base edge; at the tip it lies along the inner rail (the pro's 80-90
    deg in MFab's arm, 1.5-2 mm long)."""
    w = wedge(poly)
    if w is None:
        return None
    tip, outer, inner, base_o, base_i = w
    Lo, Li = outer.length, inner.length                 # both measured from the tip
    if Lo < 1e-6 or Li < 1e-6:
        return None
    lag = FAN_TIP_LAG_SHARE * Li
    zone = poly.buffer(FAN_INSIDE_TOL_MM)
    n = max(2, int(math.ceil(Lo / (spacing_mm / 2.0))))
    crosses = []
    for k in range(n + 1):
        so = Lo * (1.0 - k / n)                         # base -> tip
        si = lag + (Li - lag) * (so / Lo)
        p = np.array(outer.interpolate(so).coords[0])
        q = np.array(inner.interpolate(si).coords[0])
        Lc = float(np.linalg.norm(q - p))
        if Lc < FAN_MIN_CROSS_MM:
            continue
        if Lc > max_cross_mm:
            return None
        if LineString([tuple(p), tuple(q)]).difference(zone).length > FAN_OUTSIDE_MM:
            return None
        crosses.append((p, q))
    # a station where the outer rail doubles back (a trace's notch, MFab's
    # base-left corner) would cross the crosses before it: skip it
    kept, segs = [], []
    for p, q in crosses:
        s = LineString([tuple(p), tuple(q)])
        if any(s.crosses(t) for t in segs[-4:]):
            continue
        kept.append((p, q))
        segs.append(s)
    crosses = kept
    if len(crosses) < 3:
        return None
    # a counter whose base is narrower than the fill tier's floor has nothing
    # a fill would sew either: a speck, not a counter (the vintage badge's)
    if float(np.linalg.norm(crosses[0][1] - crosses[0][0])) < machine.MIN_FILL_WIDTH_MM:
        return None
    swept = Polygon([tuple(p) for p, _q in crosses] + [tuple(q) for _p, q in reversed(crosses)])
    if not swept.is_valid:
        swept = swept.buffer(0)
    if swept.area < FAN_COVER_MIN * poly.area:
        return None
    return crosses


def counter_fan_runs(poly: Polygon, shape_id: str, *, pull_mm: float = 0.0,
                     spacing_mm: float = machine.SATIN_SPACING_MM,
                     max_cross_mm: float | None = None):
    """The counter as one fanned satin: (runs, report) or None (module notes)."""
    cap = machine.SATIN_MAX_WIDTH_MM if max_cross_mm is None else float(max_cross_mm)
    crosses = fan_crosses(poly, spacing_mm, cap)
    if crosses is None:
        return None
    # underlay: zigzag tip -> base on the crosses inset, one leg every FAN_UNDER_PITCH_MM
    under = []
    step = max(1, int(round(FAN_UNDER_PITCH_MM / (spacing_mm / 2.0))))
    for k, (p, q) in enumerate(reversed(crosses[::step] + [crosses[-1]])):
        d = q - p
        Lc = float(np.linalg.norm(d))
        if Lc <= 2 * FAN_UNDER_INSET_MM + 0.1:
            u = d / max(Lc, 1e-9)
            under.append(tuple(p + u * Lc / 2.0))         # in the narrow arm: the run up the tip
            continue
        u = d / Lc
        under.append(tuple(p + u * FAN_UNDER_INSET_MM) if k % 2 == 0 else tuple(q - u * FAN_UNDER_INSET_MM))
    satin = []
    for k, (p, q) in enumerate(crosses):
        d = q - p
        u = d / float(np.linalg.norm(d))
        a, b = tuple(p - u * pull_mm), tuple(q + u * pull_mm)
        satin += [a, b] if k % 2 == 0 else [b, a]
    runs = []
    if len(under) >= 2:
        runs.append(StitchRun(points=under, kind=stitches.UNDERLAY, shape_id=shape_id))
    runs.append(StitchRun(points=satin, kind=stitches.SATIN, shape_id=shape_id))
    lens = [float(np.linalg.norm(q - p)) for p, q in crosses]
    report = {"too_thin": False, "jumps": 0, "empty": False, "counter_fan": 1,
              "counter_fan_crosses": len(crosses), "counter_fan_longest_mm": round(max(lens), 2)}
    return runs, report
