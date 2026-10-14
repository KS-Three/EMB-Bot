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

# A LETTER whose spines total less than this is under two bean stations:
# the needle would be re-entering its own holes (`run_outline` holds a ring to
# RUN_MIN_LOOP_MM; an open spine is sewn there and back, so half of it).
_MIN_SPINE_MM = machine.RUN_MIN_LOOP_MM / 2.0
# One spine of a letter that clears the floor sews if it holds one bean
# stitch. Bridge's E (2026-10-02): its middle arm is under a millimetre, and a
# per-spine floor of _MIN_SPINE_MM sewed the letter as a C.
_MIN_ARM_MM = machine.BEAN_STITCH_MM


def _length(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


# A hook is a turn of at least this many degrees within `serif_mm` of a
# spine's free end. A slab serif on a 1.9 mm letter is ~0.35 mm of spine
# turned 90 degrees; the gentle tail of a 9 or 5 turns well under this
# within the same distance.
_HOOK_TURN_DEG = 50.0


def _cut_hook(spine: list, serif_mm: float) -> list:
    """`spine` with the hook at its START cut off, or unchanged. The corner is
    the point within `serif_mm` of the end where the end's direction and the
    next `serif_mm` of spine differ most; cut there only when that turn is at
    least `_HOOK_TURN_DEG` and what is left is at least twice the hook it
    cut and at least `serif_mm`. The guard is on the hook actually found, not
    on `serif_mm`: a fixed "three serifs long" floor refused every arm of
    Fremont's E at 81 mm (about 1 mm each) and it sewed as a B again."""
    if len(spine) < 3:
        return spine
    cum = [0.0]
    for a, b in zip(spine, spine[1:]):
        cum.append(cum[-1] + math.dist(a, b))

    def at(s):
        for i in range(1, len(cum)):
            if cum[i] >= s:
                f = (s - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1.0)
                a, b = spine[i - 1], spine[i]
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), i
        return spine[-1], len(spine) - 1

    best, best_turn = None, 0.0
    steps = 12
    for k in range(2, steps + 1):
        s = serif_mm * k / steps
        c, i = at(s)
        far, _ = at(s + serif_mm)
        v1 = (c[0] - spine[0][0], c[1] - spine[0][1])
        v2 = (far[0] - c[0], far[1] - c[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        turn = math.degrees(math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
        if turn > best_turn:
            best, best_turn = (c, i, s), turn
    if best is None or best_turn < _HOOK_TURN_DEG:
        return spine
    c, i, hook = best
    if cum[-1] - hook < max(2.0 * hook, serif_mm):
        return spine
    return [c] + list(spine[i:])


def trim_serif_hooks(spines, serif_mm: float | None):
    """Every spine with a short hook cut off each free end -- the slab serif a
    1.9 mm letter's centreline turns into, which closes an E into a B once
    the thread is laid (`cfg.bean_letter_serif_mm`). None: unchanged."""
    if not serif_mm or serif_mm <= 0:
        return spines
    out = []
    for s in spines or []:
        s = [tuple(p) for p in s]
        s = _cut_hook(s, serif_mm)
        s = list(reversed(_cut_hook(list(reversed(s)), serif_mm)))
        out.append(s)
    return out


def bean_letter(spines, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float,
                stitch_mm: float | None = None,
                serif_mm: float | None = None) -> tuple[list[StitchRun], dict]:
    """One letter's spines -> bean runs in sew order, plus `run_outline`'s
    report contract (and `strokes`, how many spines sewed).

    Order: whichever unsewn spine has an end nearest the needle, entered at
    that end — strokes of one letter meet at their junctions, so the hop is
    usually nothing. A hop the needle must make is a jump, and a trim past
    `trim_at_mm`, exactly as between the rings of a run outline; the hop INTO
    the letter is the sequence loop's to book, not this function's.

    `empty` when nothing was long enough to sew: the caller falls through to
    the ladder it had before, so a letter never sews as nothing.

    `stitch_mm` (`cfg.bean_letter_stitch_mm`): the station pitch, and the
    shortest arm that sews. At `BEAN_STITCH_MM` (0.73) the loop of a 1.9 mm
    "8" -- under 2 mm round -- gets two or three stations and collapses to a
    wedge; None is that pitch, byte for byte."""
    arm_floor = stitch_mm if stitch_mm and stitch_mm > 0 else _MIN_ARM_MM
    report = {"loops": 0, "jumps": 0, "empty": True, "too_thin": False,
              "arcs": 0, "yielded": 0, "strokes": 0}
    todo = [list(map(tuple, s)) for s in (trim_serif_hooks(spines, serif_mm) or [])
            if len(s) >= 2 and _length(s) >= arm_floor]
    if sum(_length(s) for s in todo) < _MIN_SPINE_MM:
        todo = []
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
        pts = _bean_along(spine, stitch_mm)
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
