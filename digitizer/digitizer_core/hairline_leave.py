"""`cfg.extra["lettering_columns_hairline_leave"]` (built OFF 2026-11-19; the Toat
Machine h, `docs/toat-machine-script-plan-2026-11-18.md`).

Why. A script word is one satin column per pen stroke (`script_strokes`). Where a
thin stroke (the h's arch hairline) meets a heavier one (its stem) the ink MERGES,
and the skeleton routes the hairline down the merged blob: its stations there are
blob-wide (2.1 mm against the hairline's 0.7) and turned to the blob's axis, so
they sew as a second, crosshatched layer over the stem. Hat: the arch x stem pair
overlaps 5.95 mm2 at crosses turned more than 30 degrees; the professional's file
for the same pair, 1.95.

What it does. A column whose stations run through a HEAVIER column's ribbon
(median cross at least `HEAVIER` times its own), between stations that lie
outside it, LEAVES the heavier stroke at once: the run's stations are replaced by
the straight line from the last station before the merge to the first after it,
their cross length and angle eased between those two thin, clean crosses, each
cross clipped to the artwork. Ends of a column are never touched (a stroke that
ENDS on another is `end_overlap`'s). What the shorter crosses leave bare is the
patch lane's (`script_strokes._patches` runs after this).

Off, byte-identical (the scope reads False and the columns pass through).
Tests: `tests/test_hairline_leave.py`.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
from dataclasses import replace

from shapely.geometry import LineString, Point

#: the heavier column's median cross must be this many times the thin column's
HEAVIER = 1.4
#: the merge runs on past the heavier ribbon's edge while a station is wider
#: than this many times the column's own thin cross (its lower quartile)
WIDEN = 1.35
#: a run of this many stations or more is a merge (shorter is a graze)
MIN_RUN = 3
#: a run longer than this is not a merge but a stroke running beside another
MAX_RUN = 24

_ON: contextvars.ContextVar[bool] = contextvars.ContextVar("hairline_leave", default=False)


@contextlib.contextmanager
def hairline_leave_scope(on: bool):
    token = _ON.set(bool(on))
    try:
        yield
    finally:
        _ON.reset(token)


def armed() -> bool:
    return _ON.get()


def _len(s) -> float:
    return math.dist(s[0], s[1])


def _mid(s):
    return ((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2)


def _ang(s) -> float:
    return math.degrees(math.atan2(s[1][1] - s[0][1], s[1][0] - s[0][0])) % 180.0


def _axial_lerp(a: float, b: float, t: float) -> float:
    """Degrees mod 180, along the shorter way from a to b."""
    d = (b - a + 90.0) % 180.0 - 90.0
    return (a + d * t) % 180.0


def _cross(mid, ang_deg: float, length: float, poly, like):
    """A cross of `length` at `mid` and `ang_deg`, clipped to `poly`, oriented like `like`."""
    h = length / 2.0
    dx, dy = h * math.cos(math.radians(ang_deg)), h * math.sin(math.radians(ang_deg))
    a, b = (mid[0] - dx, mid[1] - dy), (mid[0] + dx, mid[1] + dy)
    if poly is not None:
        g = LineString([a, b]).intersection(poly.buffer(0.05))
        pieces = [g] if g.geom_type == "LineString" else list(getattr(g, "geoms", []))
        pieces = [q for q in pieces if q.geom_type == "LineString" and not q.is_empty]
        if not pieces:
            return None
        best = min(pieces, key=lambda q: q.distance(Point(mid)))
        if best.length < 0.5 * length:
            return None
        a, b = best.coords[0], best.coords[-1]
    if (b[0] - a[0]) * (like[1][0] - like[0][0]) + (b[1] - a[1]) * (like[1][1] - like[0][1]) < 0:
        a, b = b, a
    return (a[0], a[1]), (b[0], b[1])


def leave_columns(columns: list, poly) -> tuple[list, int]:
    """-> (columns, stations replaced). The same list when nothing changes."""
    if len(columns) < 2:
        return columns, 0
    from .script_strokes import _ribbon
    medlen = []
    for c in columns:
        ws = sorted(_len(s) for s in c.stations)
        medlen.append(ws[len(ws) // 2] if ws else 0.0)
    ribbons = [_ribbon(c.stations).buffer(-0.05) if len(c.stations) >= 2 else None for c in columns]
    out, total = [], 0
    for i, col in enumerate(columns):
        n = len(col.stations)
        heavy = [ribbons[j] for j in range(len(columns))
                 if j != i and ribbons[j] is not None and not ribbons[j].is_empty
                 and medlen[j] >= HEAVIER * medlen[i]]
        if col.kind != "curved" or n < MIN_RUN + 2 or not heavy:
            out.append(col)
            continue
        inside = [any(r.covers(Point(_mid(s))) for r in heavy) for s in col.stations]
        sts = list(col.stations)
        thin = sorted(_len(s) for s in sts)[n // 4]
        wide = [_len(s) > WIDEN * thin for s in sts]
        k, changed = 1, 0
        while k < n - 1:
            if not inside[k]:
                k += 1
                continue
            a = k - 1                              # the last station before the merge
            while k < n and inside[k]:
                k += 1
            b = k                                  # the first station past it
            while a > 0 and wide[a]:               # the blob runs on past the ribbon's edge
                a -= 1
            while b < n and wide[b]:
                b += 1
            k = max(k, b)
            run = b - a - 1
            if b >= n or a < 0 or inside[a] or wide[a] or run < MIN_RUN or run > MAX_RUN \
                    or not any(wide[a + 1:b]):
                continue
            la, lb = _len(col.stations[a]), _len(col.stations[b])
            ma, mb = _mid(col.stations[a]), _mid(col.stations[b])
            ga, gb = _ang(col.stations[a]), _ang(col.stations[b])
            new = []
            for m in range(a + 1, b):
                t = (m - a) / (b - a)
                c = _cross((ma[0] + (mb[0] - ma[0]) * t, ma[1] + (mb[1] - ma[1]) * t),
                           _axial_lerp(ga, gb, t), la + (lb - la) * t, poly, col.stations[m])
                if c is None:
                    new = None
                    break
                new.append(c)
            if new is None:
                continue
            sts[a + 1:b] = new
            changed += run
        if not changed:
            out.append(col)
            continue
        out.append(replace(col, stations=sts, piece=_ribbon(sts)))
        total += changed
    return (out, total) if total else (columns, 0)
