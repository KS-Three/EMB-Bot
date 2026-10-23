"""Crosses square to the LINE OF TEXT in the Column lane
(`cfg.lettering_columns_text_lean`, 2026-10-23).

The pro sews every stroke of a 13-17 mm letter with its crosses square to
the line of text -- the stems' own cross -- diagonals included: Becker's
MARINE at 76.5 mm (the hat), 101.9 (the large hat), 95.7 (left chest) and
79.8 (the beanie), where the N's diagonal, the A's legs and the M's two
diagonals all carry the stems' horizontal cross, so every stroke of the
word has one sheen and his junctions are plain overlaps. The Column lane
stations a straight piece square to ITS OWN axis (`outline_cut.scan_stations`),
so our N's diagonal and A's legs read as another sheen beside the stems,
and the M's V, where two leaned pieces meet two upright ones, sews as a
tangle (`docs/lettering-10mm-up-2026-10-23.md`, the paths render). The
satin tier has sewn the house cross since 2026-09-03
(`stage6_satin._clamp_to_span`, Kent's adopted convention: stems square to
the line of text, a lean cap of 30 degrees, station spacing over cos of
the lean); the Column lane displaced that tier for lettering on 2026-10-12
without it. This module brings the convention to the lane.

`lean_columns` re-stations each STRAIGHT column of a letter whose axis the
house cross can span within the cap: the crosses lie along the clamped
house direction, one every `pitch / cos(lean)` along the axis so the
distance BETWEEN crosses stays the satin spacing, each cross the longest
segment its line cuts from the piece, ordered along the piece's normal so
rail A and rail B keep their sides. A column the house already crosses
square (an upright stem under upright text), a curved or ring column (the
R's bowl, which the pro fans round as we do), and a column whose lean
would be nil keep their stations, byte for byte -- so the flag moves the
diagonals and the slanted legs and nothing else.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Polygon

from .columns import Column

# A lean under this is the station scan's own rounding, not a lean: the
# column keeps its original stations (caps, fans and mitres included).
MIN_LEAN_DEG = 0.5
# A cross shorter than this is a corner clipping, not a station (the same
# floor `outline_cut._scan_cross` applies to its scanline segments).
_MIN_SEG_MM = 0.05
_FAR = 200.0


def cross_direction(axis, house_deg: float) -> tuple[float, float, float]:
    """The cross direction the convention gives a straight piece of unit
    `axis` under the house cross `house_deg` (degrees, plan frame): a unit
    vector along the clamped house (`stage6_satin._clamp_to_span`) and the
    lean, in degrees, off the piece's own normal."""
    from .stage6_satin import _clamp_to_span
    tangent = math.atan2(axis[1], axis[0])
    cross = _clamp_to_span(math.radians(house_deg), tangent)
    c = (math.cos(cross), math.sin(cross))
    n = (-axis[1], axis[0])
    cosl = max(-1.0, min(1.0, c[0] * n[0] + c[1] * n[1]))
    return c[0], c[1], math.degrees(math.acos(abs(cosl)))


def _cross_along(piece: Polygon, origin, c, n):
    """The longest segment the line through `origin` along `c` cuts from
    `piece`, its ends ordered along `n`. -> ((pa, pb), other segments' length)
    or None."""
    hit = LineString([(origin[0] - c[0] * _FAR, origin[1] - c[1] * _FAR),
                      (origin[0] + c[0] * _FAR, origin[1] + c[1] * _FAR)]).intersection(piece)
    segs = [g for g in getattr(hit, "geoms", [hit])
            if g.geom_type == "LineString" and g.length > _MIN_SEG_MM]
    if not segs:
        return None
    g = max(segs, key=lambda s: s.length)
    p, q = g.coords[0], g.coords[-1]
    if (p[0] * n[0] + p[1] * n[1]) > (q[0] * n[0] + q[1] * n[1]):
        p, q = q, p
    return (tuple(p), tuple(q)), sum(s.length for s in segs) - g.length


def lean_stations(piece: Polygon, axis, c, pitch_mm: float):
    """Stations along `axis`, crosses along `c`, spaced so consecutive
    crosses sit `pitch_mm` apart measured square to themselves
    (`pitch / cos(lean)` along the axis -- the convention's spacing rule).
    -> (stations, dropped_mm) or None under three stations."""
    u = axis
    n = (-u[1], u[0])
    cosl = abs(c[0] * n[0] + c[1] * n[1])
    if cosl < 1e-6:
        return None
    step = pitch_mm / cosl
    cs = np.array(piece.exterior.coords)
    t = cs @ np.array(u)
    # Each line runs through the axis line THROUGH THE PIECE (its centroid's
    # normal offset), not the one through the origin: a leaned line through
    # a point 20 mm off the piece meets it shifted along the axis by that
    # offset times tan(lean), and a third of the stations fell off one end
    # (Becker's A, 36 -> 22 stations, the first run of this).
    g = piece.centroid
    off = g.x * n[0] + g.y * n[1]
    base = (n[0] * off, n[1] * off)
    # the piece's slanted ends: a leaned line clips a corner up to half the
    # stroke times tan(lean) past the axis extent, so the scan reaches there
    tanl = math.sqrt(max(0.0, 1.0 - cosl * cosl)) / cosl
    ext = 0.5 * float(np.ptp(cs @ np.array(n))) * tanl
    out = []
    dropped = 0.0
    for tt in np.arange(t.min() - ext + step / 2, t.max() + ext, step):
        hit = _cross_along(piece, (base[0] + u[0] * tt, base[1] + u[1] * tt), c, n)
        if hit is None:
            continue
        cross, extra = hit
        dropped += extra
        out.append(cross)
    return (out, dropped) if len(out) >= 3 else None


def lean_column(col: Column, house_deg: float, pitch_mm: float) -> Column:
    """`col` re-stationed under the house cross, or `col` itself where the
    convention leaves it: not straight, no axis, a lean under
    `MIN_LEAN_DEG`, or a scan that cannot station it."""
    if col.kind != "straight" or col.axis is None or not col.stations:
        return col
    cx, cy, lean = cross_direction(col.axis, house_deg)
    if lean < MIN_LEAN_DEG:
        return col
    sc = lean_stations(col.piece, col.axis, (cx, cy), pitch_mm)
    if sc is None:
        return col
    st, dropped = sc
    return Column(stations=st, piece=col.piece, kind=col.kind, axis=col.axis,
                  width_mm=col.width_mm, rail_a=list(col.rail_a), rail_b=list(col.rail_b),
                  dropped_mm=dropped)


def lean_columns(columns: list[Column], house_deg: float | None, pitch_mm: float) -> list[Column]:
    """Every column of a letter through `lean_column`; `house_deg` None is
    the lane as it was (the same list object)."""
    if house_deg is None:
        return columns
    return [lean_column(c, float(house_deg), pitch_mm) for c in columns]
