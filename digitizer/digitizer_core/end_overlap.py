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
        others = []
        for j, cj in enumerate(columns):
            if j == i or len(cj.stations) <= n:
                continue                    # yield to LONGER columns only
            for k, q in enumerate(quads[j]):
                if q is not None:
                    others.append((q, angs[j][k + 1]))
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
