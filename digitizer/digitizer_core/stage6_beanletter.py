"""Small lettering sewn as bean runs along its ink
(`docs/superpowers/specs/2026-10-02-bean-letters-design.md`, Kent's ruling
2026-10-02: a too-small traced letter is a centreline bean, not a satin blob).

The spines come from `ink_path.read_cluster_ink` — the skeleton of the
letter's SOURCE INK, in design millimetres — and this module only sews them:
`machine.BEAN_PASSES` laps at `machine.BEAN_STITCH_MM`, the light tier the
run outline and the hairline stretch already sew, so there is no new physical
constant here. No underlay and no pull compensation: a run lays single lines
of thread that do not pull the fabric (`stage6_border.run_outline`).

Kind is `stitches.RUN` — the tier that says "this shape was too small for
satin" — never SATIN, so every satin instrument (preflight's
LETTERING_TOO_SMALL among them) leaves these runs alone by construction.
"""
from __future__ import annotations

import math

from . import machine, stitches
from .stage6_satin import _bean_along
from .stitches import StitchRun

# A spine shorter than this is under two bean stations: the needle would be
# re-entering its own holes (`run_outline` holds a ring to RUN_MIN_LOOP_MM;
# an open spine is sewn there and back, so half of it).
_MIN_SPINE_MM = machine.RUN_MIN_LOOP_MM / 2.0


def _length(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def bean_letter(spines, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float) -> tuple[list[StitchRun], dict]:
    """One letter's spines -> bean runs in sew order, plus `run_outline`'s
    report contract (and `strokes`, how many spines sewed).

    Order: whichever unsewn spine has an end nearest the needle, entered at
    that end — strokes of one letter meet at their junctions, so the hop is
    usually nothing. A hop the needle must make is a jump, and a trim past
    `trim_at_mm`, exactly as between the rings of a run outline; the hop INTO
    the letter is the sequence loop's to book, not this function's.

    `empty` when nothing was long enough to sew: the caller falls through to
    the ladder it had before, so a letter never sews as nothing."""
    report = {"loops": 0, "jumps": 0, "empty": True, "too_thin": False,
              "arcs": 0, "yielded": 0, "strokes": 0}
    todo = [list(map(tuple, s)) for s in (spines or [])
            if len(s) >= 2 and _length(s) >= _MIN_SPINE_MM]
    runs: list[StitchRun] = []
    cursor = entry
    while todo:
        if cursor is None:
            i, rev = 0, False
        else:
            i, rev = min(((k, r) for k in range(len(todo)) for r in (False, True)),
                         key=lambda kr: (round(math.dist(cursor, todo[kr[0]][-1 if kr[1] else 0]), 6),
                                         kr[0], kr[1]))
        spine = todo.pop(i)
        if rev:
            spine.reverse()
        pts = _bean_along(spine)
        if len(pts) < 2:
            continue
        jump = trim = False
        if runs:
            d = math.dist(cursor, pts[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(pts), kind=stitches.RUN,
                              jump=jump, trim=trim, shape_id=shape_id))
        cursor = pts[-1]
        report["strokes"] += 1
    report["empty"] = not runs
    return runs, report
