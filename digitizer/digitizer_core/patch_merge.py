"""`cfg.extra["script_strokes_patch_merge"]` (built OFF 2026-11-19; "fewer, longer
columns", the professional's script word).

Why. A script word is one satin column per pen stroke (`script_strokes`), plus a
straight PATCH column over each piece of the artwork the strokes leave uncovered
(a wedge at a junction, a step). Each patch is a column of its own with two ends.
Counted from the plan on 2026-11-19 (strokes + patches): Tires 5 + 5, Bridge hat
9 + 5, Bridge LC 9 + 6, To a T hat 11 + 2, machine beanie 10 + 1, beanie 13 + 4.
On Tires the professional sews 7 long chains to our 13 (14 column ends against
26): our 5 pen strokes are FEWER than his chains, the extra ends are the patches.
Most sit within a millimetre or two of a stroke's end, at the same cross angle
(Bridge hat 4 of 5 at 0.16-0.62 mm and 0 to 10 degrees; Tires 2 of 5 at 1.45 and
2.34 mm).

What it does. A patch whose nearer end lies within `PATCH_MERGE_MM` of a stroke column's
END, its first cross turned no more than `MERGE_TURN_DEG` from that end's, JOINS that
column: its stations are appended (or prepended), crosses oriented to the
column's, with stations interpolated across the gap at the pitch when the gap is
over a pitch -- every one of them inside the artwork, else the patch stays a patch.
The column is longer, one column end replaces the patch's two ends and the stroke
end it butted, and the needle no longer lifts for the patch. Never merged: a
patch farther than `PATCH_MERGE_MM` or turned more than `MERGE_TURN_DEG`, and a stroke that
is closed.

Off, byte-identical (the scope reads False and nothing is merged).
Tests: `tests/test_patch_merge.py`.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
from dataclasses import replace

from shapely.geometry import Point

#: a patch joins a stroke end this near (mm)
PATCH_MERGE_MM = 2.5
#: ... whose cross it continues within this many degrees
MERGE_TURN_DEG = 35.0

_ON: contextvars.ContextVar[bool] = contextvars.ContextVar("patch_merge", default=False)


@contextlib.contextmanager
def patch_merge_scope(on: bool):
    token = _ON.set(bool(on))
    try:
        yield
    finally:
        _ON.reset(token)


def armed() -> bool:
    return _ON.get()


def _mid(s):
    return ((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2)


def _ang(s) -> float:
    return math.degrees(math.atan2(s[1][1] - s[0][1], s[1][0] - s[0][0])) % 180.0


def _turn(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _like(s, ref):
    """The cross `s` with its a -> b direction the way `ref`'s runs."""
    if (s[1][0] - s[0][0]) * (ref[1][0] - ref[0][0]) + (s[1][1] - s[0][1]) * (ref[1][1] - ref[0][1]) < 0:
        return (s[1], s[0])
    return s


def merge_patches(cols: list, patches: list, poly, pitch_mm: float) -> tuple[list, list, int]:
    """-> (columns, patches left, patches merged). The inputs when nothing merges."""
    if not patches or not cols:
        return cols, patches, 0
    from .script_strokes import _ribbon
    cols = list(cols)
    left, merged = [], 0
    ground = poly.buffer(0.1)
    for p in patches:
        best = None
        for ci, c in enumerate(cols):
            if c.kind != "curved" or len(c.stations) < 3:
                continue
            for end in (0, -1):
                s = c.stations[end]
                for pe in (0, -1):
                    t = p.stations[pe]
                    d = math.dist(_mid(s), _mid(t))
                    if d <= PATCH_MERGE_MM and _turn(_ang(s), _ang(t)) <= MERGE_TURN_DEG \
                            and (best is None or d < best[0]):
                        best = (d, ci, end, pe)
        if best is None:
            left.append(p)
            continue
        d, ci, end, pe = best
        c = cols[ci]
        # the patch's stations in the order they follow the column's end
        seq = list(p.stations) if (pe == 0) == (end == -1) else list(p.stations)[::-1]
        edge = c.stations[end]
        chain = [edge] + seq if end == -1 else seq + [edge]
        # orient every cross to its neighbour toward the column
        order = range(1, len(chain)) if end == -1 else range(len(chain) - 2, -1, -1)
        for k in order:
            chain[k] = _like(chain[k], chain[k - 1] if end == -1 else chain[k + 1])
        # stations across the gap, at the pitch
        gap = []
        n = int(d / max(pitch_mm, 0.1))
        a, b = (edge, chain[1]) if end == -1 else (chain[-2], edge)
        ok = True
        for i in range(1, n):
            t = i / n
            g = tuple((a[j][0] + (b[j][0] - a[j][0]) * t, a[j][1] + (b[j][1] - a[j][1]) * t) for j in range(2))
            if not ground.covers(Point(_mid(g))):
                ok = False
                break
            gap.append(g)
        if not ok:
            left.append(p)
            continue
        oriented = chain[1:] if end == -1 else chain[:-1]
        new = list(c.stations) + gap + oriented if end == -1 else oriented + gap + list(c.stations)
        cols[ci] = replace(c, stations=new, piece=_ribbon(new))
        merged += 1
    if not merged:
        return cols, patches, 0
    return cols, left, merged
