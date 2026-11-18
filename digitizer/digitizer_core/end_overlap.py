"""`cfg.extra["lettering_columns_end_overlap_cut"]` (built OFF 2026-11-18; prime
grader, Toat Machine "Machine" on the beanie and the hat: "tangled stitch
directions and pile-ups", "crossover stitches where letters join").

Why. A script word is one satin column per pen stroke (`script_strokes`). Where
a stroke ENDS on another (the c's terminal on its arc, the h's arch hairline on
the stem, the n's entry on the i) the skeleton's last stations still lie across
the other stroke's ground, and their crosses are at a different angle: two
satin directions sewn over the same thread, a cross-hatched pile. The cut-back
in `script_columns` only drops an end station whose MIDDLE is inside the other
ribbon, so a station that straddles the edge stays. Measured on the beanie and
the hat: 6-8 column pairs overlap 0.9-6.1 mm2 at cross angles over 30 degrees.

What it does. Each column yields its END stations to a LONGER column: from an
end inward, a station goes while at least `SHARE` of its quad lies over longer
columns' quads whose cross is more than `TURN_DEG` off its own, at most
`MAX_CUT` stations an end and never below `KEEP`. Parallel overlap (a stroke
running on beside another) is never cut. The ground a cut leaves bare is the
patch lane's (`script_strokes._patches` runs after this).

Off, byte-identical (the scope reads False and the columns pass through).
Tests: `tests/test_end_overlap.py`.

SECOND MODE, `cfg.extra["lettering_columns_junction_align"]` (built OFF the same
day; `align_columns`). The pro's file (`Machine beanie.PES`, numbers only,
`docs/toat-machine-script-plan-2026-11-18.md`) overlaps its word's columns by
about as much as ours but only 1.55 mm2 of it at crosses more than 30 degrees
apart; ours is 9.5 (beanie) and 19.2 (hat). A joining stroke there TURNS its last
crosses to the through stroke's angle. `align_columns` does that: the end
stations the cut above would drop have their cross rotated about the station's
middle (length kept, clipped to the artwork) to the angle of the longer column
they lie over, with `RAMP` stations easing the rotation in.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
from dataclasses import replace

from shapely.geometry import Polygon

#: a station goes when this share of its quad is over a longer column at a turned cross (0.3 re-covered the cut ground with patches, a messier h arch; 0.6 and 0.8 cut the same stations)

SHARE = 0.60
#: ... turned by more than this (deg, folded to 0-90)
TURN_DEG = 30.0
#: at most this many stations an end
MAX_CUT = 6
#: the column keeps at least this many
KEEP = 6

_ON: contextvars.ContextVar[bool] = contextvars.ContextVar("end_overlap", default=False)


@contextlib.contextmanager
def end_overlap_scope(on: bool):
    token = _ON.set(bool(on))
    try:
        yield
    finally:
        _ON.reset(token)


def armed() -> bool:
    return _ON.get()


def _ang(s) -> float:
    a, b = s
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def _turn(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _quads(col) -> list:
    out = []
    st = col.stations
    for k in range(1, len(st)):
        (a0, b0), (a1, b1) = st[k - 1], st[k]
        p = Polygon([a0, b0, b1, a1]).buffer(0)
        out.append(p if p.area > 1e-6 and p.geom_type == "Polygon" else None)
    return out          # quad k-1 is the one ending at station k


def _share_over(p, p_ang: float, others) -> float:
    """The share of `p`'s area over `others` quads (with their angles) whose cross is turned."""
    over = 0.0
    for q, qa in others:
        if _turn(p_ang, qa) <= TURN_DEG or not p.intersects(q):
            continue
        over += p.intersection(q).area
    return over / p.area


#: a quad within this many stations of its column's own end is an END, not the column's body
END_ZONE = 6


def _others(columns, i, quads, angs):
    """(quad, angle) of every column the column `i` may yield to: a LONGER column
    wholly, a shorter one only along its BODY (the stroke that ENDS on another
    yields, whichever is longer: the h's hairline ends in the stem's body)."""
    n = len(columns[i].stations)
    out = []
    for j, cj in enumerate(columns):
        if j == i:
            continue
        m = len(cj.stations)
        for k, q in enumerate(quads[j]):
            if q is None:
                continue
            if m > n or END_ZONE <= k < m - 1 - END_ZONE:
                out.append((q, angs[j][k + 1]))
    return out


def cut_columns(columns: list) -> tuple[list, int]:
    """-> (columns, stations cut). The same list when nothing is cut."""
    if len(columns) < 2:
        return columns, 0
    quads = [_quads(c) for c in columns]
    angs = [[_ang(s) for s in c.stations] for c in columns]
    out, total = [], 0
    for i, col in enumerate(columns):
        n = len(col.stations)
        if col.kind != "curved" or n <= KEEP:
            out.append(col)
            continue
        others = _others(columns, i, quads, angs)
        if not others:
            out.append(col)
            continue
        lo, hi = 0, n                       # keep stations [lo, hi)
        for at_start in (True, False):
            cut = 0
            while cut < MAX_CUT and (hi - lo) > KEEP:
                k = (lo + 1) if at_start else (hi - 1)     # the quad k-1 .. k at that end
                p = quads[i][k - 1]
                if p is None or _share_over(p, angs[i][k], others) < SHARE:
                    break
                if at_start:
                    lo += 1
                else:
                    hi -= 1
                cut += 1
        if lo == 0 and hi == n:
            out.append(col)
            continue
        from .script_strokes import _ribbon
        sts = col.stations[lo:hi]
        out.append(replace(col, stations=sts, piece=_ribbon(sts)))
        total += n - len(sts)
    return (out, total) if total else (columns, 0)


#: stations either side of an aligned run over which the rotation eases in
RAMP = 4

_ALIGN: contextvars.ContextVar[bool] = contextvars.ContextVar("junction_align", default=False)


@contextlib.contextmanager
def junction_align_scope(on: bool):
    token = _ALIGN.set(bool(on))
    try:
        yield
    finally:
        _ALIGN.reset(token)


def align_armed() -> bool:
    return _ALIGN.get()


def _target(p, p_ang: float, others):
    """The area-weighted axial angle of the turned `others` quads `p` lies over, and the share."""
    sx = sy = over = 0.0
    for q, qa in others:
        if _turn(p_ang, qa) <= TURN_DEG or not p.intersects(q):
            continue
        ar = p.intersection(q).area
        sx += ar * math.cos(math.radians(2 * qa))
        sy += ar * math.sin(math.radians(2 * qa))
        over += ar
    if over <= 0:
        return None, 0.0
    return (math.degrees(math.atan2(sy, sx)) / 2.0) % 180.0, over / p.area


def _rot(a, b, delta_deg: float, poly):
    """The cross a-b turned by `delta_deg` about its middle, length kept; clipped to `poly`."""
    from shapely.geometry import LineString
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    c, s = math.cos(math.radians(delta_deg)), math.sin(math.radians(delta_deg))
    hx, hy = (b[0] - a[0]) / 2, (b[1] - a[1]) / 2
    nx, ny = hx * c - hy * s, hx * s + hy * c
    na, nb = (mx - nx, my - ny), (mx + nx, my + ny)
    if poly is not None:
        g = LineString([na, nb]).intersection(poly.buffer(0.05))
        pieces = [g] if g.geom_type == "LineString" else list(getattr(g, "geoms", []))
        pieces = [q for q in pieces if q.geom_type == "LineString" and not q.is_empty]
        if not pieces:
            return a, b
        from shapely.geometry import Point
        best = min(pieces, key=lambda q: q.distance(Point(mx, my)))
        if best.length < 0.5 * math.dist(a, b):
            return a, b                      # the turned cross would be mostly outside the ink
        (x0, y0), (x1, y1) = best.coords[0], best.coords[-1]
        # keep a -> b orientation
        if (x1 - x0) * (nb[0] - na[0]) + (y1 - y0) * (nb[1] - na[1]) < 0:
            x0, y0, x1, y1 = x1, y1, x0, y0
        return (x0, y0), (x1, y1)
    return na, nb


def align_columns(columns: list, poly) -> tuple[list, int]:
    """-> (columns, stations turned). Each column's END stations that lie over a
    LONGER column at a turned cross (the cut's rule) take that column's cross
    angle, easing in over `RAMP` stations. The same list when nothing turns."""
    if len(columns) < 2:
        return columns, 0
    quads = [_quads(c) for c in columns]
    angs = [[_ang(s) for s in c.stations] for c in columns]
    out, total = [], 0
    for i, col in enumerate(columns):
        n = len(col.stations)
        if col.kind != "curved" or n <= KEEP:
            out.append(col)
            continue
        others = _others(columns, i, quads, angs)
        if not others:
            out.append(col)
            continue
        delta = [0.0] * n                    # turn for each station (deg)
        turned = [False] * n
        for at_start in (True, False):
            run = 0
            while run < MAX_CUT + RAMP and run < n - 1:
                k = (1 + run) if at_start else (n - 1 - run)
                p = quads[i][k - 1]
                if p is None:
                    break
                t, share = _target(p, angs[i][k], others)
                if t is None or share < SHARE:
                    break
                d = (t - angs[i][k] + 90.0) % 180.0 - 90.0
                delta[k] = d
                turned[k] = True
                run += 1
            if run == 0:
                continue
            # the ramp: stations just inside the run take a fading share of its last turn
            edge = (1 + run - 1) if at_start else (n - 1 - (run - 1))
            step = 1 if at_start else -1
            for r in range(1, RAMP + 1):
                k = edge + step * r
                if 0 <= k < n and not turned[k]:
                    delta[k] = delta[edge] * (1.0 - r / (RAMP + 1.0))
        if not any(abs(d) > 1e-6 for d in delta):
            out.append(col)
            continue
        from .script_strokes import _ribbon
        sts = list(col.stations)
        for k, d in enumerate(delta):
            if abs(d) > 1e-6:
                sts[k] = _rot(sts[k][0], sts[k][1], d, poly)
                total += 1
        out.append(replace(col, stations=sts, piece=_ribbon(sts)))
    return (out, total) if total else (columns, 0)
