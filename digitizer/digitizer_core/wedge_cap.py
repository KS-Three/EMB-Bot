"""`cfg.extra["lettering_columns_stem_wedge_cap"]` (built OFF 2026-11-18): a
column's junction wedge belongs to the column that meets it.

Why. Where a hairline or a tail joins a stem the artwork's ink widens (the
merge), and the Column lane's `curved` column takes the two OUTLINE arcs of
its piece as rails, so the stem is sewn 0.7-0.9 mm wider for the length of the
merge with a step at each end. On Toat Machine's "h" (prime grader,
2026-11-17: "built from offset segments with visible steps and a split along
its left edge"): one 61-station column, half-width 2.3-2.5 mm up the stem,
3.2-3.3 for about ten stations where the c's tail and the arch's hairline
join, back to 2.3 in three. The cut also gave the meeting column (the c's
tail, run on to the arch) the same ground, so the wedge was sewn twice and
the stem carried the step. The professional's stem is one constant-width
column with the meeting strokes as their own columns over it.

What it does. For each `curved` column, a width profile (cross length per
station) is OPENED over `BULGE_MAX_MM` of arc (running minimum, then running
maximum): every rise shorter than the window goes, a taper, a free end and a
longer swelling stay. A run of stations the opening cuts by more than
`MIN_CUT_MM`, stepping in and out by at least `STEP_MM`, is a wedge; each rail across it is replaced by the straight
chord between the stations either side of the run, and a station's cross is
shortened on a side only along its own line. A station gives its ink up ONLY
where a SIBLING column's piece already covers it (`GUARD_MM` of slack): the
cap moves ink between columns, it never leaves any bare.

The rail point of a trimmed station goes ON the chord (not onto the slanted
cross line, which shifted it along the column and bunched two penetrations), and
the rail points within `EVEN_WINDOW` stations of a run's end are re-spaced evenly
along the polyline they follow: the skeleton's join kink turns the cross there
by a few degrees and the next stage shortened it into a notch, the "seam" the
grader pinned at y 35.0 and y 39.5. (A push ramp in `_push_rails` was built for
that notch and dropped: the re-spacing alone clears it, and the ramp reached
every lane column, moving 18 of 35 runs with cover losses of up to 0.046.)

Off, byte-identical (the scope reads False and `script_strokes_shape` hands the
columns on untouched). Tests: `tests/test_wedge_cap.py`.

"""
from __future__ import annotations

import contextlib
import contextvars
import math
from dataclasses import replace

from shapely.geometry import Point
from shapely.ops import unary_union

#: A rise in the width profile shorter than this along the column is a
#: junction's merged ink (mm). The h's wedge is 3.7 mm; a brush stroke's real
#: belly is longer.
BULGE_MAX_MM = 5.0
#: The opening must cut a station by at least this much to count (mm): under
#: it the profile is the outline's own wobble.
MIN_CUT_MM = 0.2
#: A wedge is a STEP: the cross jumps by at least this much between two
#: neighbouring stations at BOTH ends of the run (the h's: 0.8 and 1.0 mm). A
#: taper or a swelling rises gradually (0.16 mm a station on a leaf) and is
#: the stroke's own shape, never a merge (mm).
STEP_MM = 0.3
#: stations either side of a wedge's end whose rail points are re-spaced evenly
EVEN_WINDOW = 3
#: ... unless that moves a point more than this (mm)
EVEN_MAX_MM = 0.35
#: A station's given-up ink must lie inside a sibling's piece buffered by this (mm)
GUARD_MM = 0.15

_ON: contextvars.ContextVar[bool] = contextvars.ContextVar("wedge_cap", default=False)


@contextlib.contextmanager
def wedge_cap_scope(on: bool):
    """`_ON` for the length of one plan (`pipeline.plan_stitches`)."""
    token = _ON.set(bool(on))
    try:
        yield
    finally:
        _ON.reset(token)


def armed() -> bool:
    return _ON.get()


#: a sibling may take a column's wedge only when it is a HAIRLINE join: its median
#: cross under this share of the column's own. The h's c-tail/arch hairline is 0.49
#: of its stem; Bridge's g-to-e link, two nearly parallel strokes, is 0.65 of its
#: column and read as a wedge at 0.85 (2026-11-18: at 0.6 the hat is byte-identical
#: to 0.85's, Bridge is byte-identical to OFF, and no other of the 44 sweep runs
#: moves either way; 0.55 gives the same two results)
THINNER = 0.6


def _median_cross(col) -> float:
    ws = sorted(math.dist(a, b) for a, b in col.stations)
    return ws[len(ws) // 2] if ws else 0.0


def _opened(w: list[float], half: int) -> list[float]:
    n = len(w)
    lo = [min(w[max(0, i - half):i + half + 1]) for i in range(n)]
    return [max(lo[max(0, i - half):i + half + 1]) for i in range(n)]


def _equalize(pts: list) -> list | None:
    """`pts` re-spaced at equal arc length along the polyline they trace (the
    two end points fixed); None for a degenerate one."""
    cum = [0.0]
    for p, q in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(p, q))
    total = cum[-1]
    if total <= 1e-9:
        return None
    out, j = [pts[0]], 0
    for k in range(1, len(pts) - 1):
        s = total * k / (len(pts) - 1)
        while j + 1 < len(cum) - 1 and cum[j + 1] < s:
            j += 1
        span = cum[j + 1] - cum[j]
        u = 0.0 if span <= 1e-12 else (s - cum[j]) / span
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u, pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u))
    out.append(pts[-1])
    return out


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    out, i, n = [], 0, len(flags)
    while i < n:
        if flags[i]:
            j = i
            while j + 1 < n and flags[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def _along(a, b, q) -> float:
    """The parameter of `q`'s foot on the line a -> b (0 at a, 1 at b)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    return 0.0 if d2 < 1e-12 else ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / d2


def cap_column(col, siblings) -> tuple[object, int]:
    """-> (column, stations capped). `siblings`: the other columns' pieces
    united (a polygon or None). The column itself when nothing is capped."""
    if col.kind != "curved" or siblings is None:
        return col, 0
    st = col.stations
    n = len(st)
    if n < 7:
        return col, 0
    cross = [math.dist(a, b) for a, b in st]
    mids = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in st]
    arc = sum(math.dist(mids[i], mids[i + 1]) for i in range(n - 1))
    pitch = arc / (n - 1) if arc > 0 else 0.0
    if pitch <= 1e-6:
        return col, 0
    half = max(1, int(round(BULGE_MAX_MM / pitch / 2.0)))
    base = _opened(cross, half)
    cut = [cross[i] - base[i] > MIN_CUT_MM for i in range(n)]
    new = list(st)
    capped = 0
    guard = siblings.buffer(GUARD_MM)
    for i0, i1 in _runs(cut):
        p, q = i0 - 1, i1 + 1
        if p < 1 or q > n - 2:             # never the column's own ends
            continue
        if min(cross[i0] - cross[p], cross[i1] - cross[q]) < STEP_MM:
            continue                       # a slope, not a step: the stroke's own swelling
        span = q - p
        for side in (0, 1):
            xp, xq = st[p][side], st[q][side]
            for i in range(i0, i1 + 1):
                t = (i - p) / span
                chord = (xp[0] + (xq[0] - xp[0]) * t, xp[1] + (xq[1] - xp[1]) * t)
                a, b = new[i]
                own, other = (a, b) if side == 0 else (b, a)
                s = _along(own, other, chord)
                if s <= 0.0:               # the chord is outside this rail: nothing to give up
                    continue
                if s >= 1.0:               # the chord is past the far rail: never
                    continue
                # the rail point goes ON the chord, not onto the cross line: a
                # cross is slanted off the column's normal, so sliding the end
                # along it shifted the rail by 0.3 x the cut ALONG the column
                # and bunched two penetrations under the short-stitch floor
                # (the stagger's notch, the grader's seam at y 35.0 / 39.5)
                moved = chord
                if math.dist(own, moved) < 0.05:
                    continue
                mid = ((own[0] + moved[0]) / 2, (own[1] + moved[1]) / 2)
                if not (guard.covers(Point(own)) and guard.covers(Point(mid))):
                    continue
                new[i] = (moved, b) if side == 0 else (a, moved)
                capped += 1
    if not capped:
        return col, 0
    # The pen-stroke cross at a wedge's end is turned a few degrees by the
    # skeleton's join kink, so a rail point there sits 0.1-0.2 mm off its
    # neighbours' pitch and the next stage shortens that cross: a notch in the
    # column (the h's seam, y 35.0 and y 39.5). Each rail's points within
    # `EVEN_WINDOW` stations of a run's end are re-spaced evenly by arc length
    # along the polyline they already follow (its shape is kept), unless that
    # moves a point more than `EVEN_MAX_MM`.
    for i0, i1 in _runs(cut):
        for e in (i0, i1):
            lo, hi = max(1, e - EVEN_WINDOW), min(n - 2, e + EVEN_WINDOW)
            if hi - lo < 3:
                continue
            for side in (0, 1):
                pts = [new[j][side] for j in range(lo - 1, hi + 2)]
                even = _equalize(pts)
                if even is None or max(math.dist(x, y) for x, y in zip(pts, even)) > EVEN_MAX_MM:
                    continue
                for k, j in enumerate(range(lo, hi + 1)):
                    a_, b_ = new[j]
                    new[j] = (even[k + 1], b_) if side == 0 else (a_, even[k + 1])
    return replace(col, stations=new), capped


def cap_columns(columns: list) -> list:
    """`columns` with each `curved` one's junction wedges handed to the
    siblings that cover them. The same list when nothing is capped."""
    if len(columns) < 2:
        return columns
    pieces = [c.piece for c in columns]
    med = [_median_cross(c) for c in columns]
    out, any_cap = [], False
    for k, col in enumerate(columns):
        if col.kind != "curved":
            out.append(col)
            continue
        # A column gives its wedge only to a THINNER sibling (median cross
        # under its own by `THINNER`): the meeting hairline keeps the ground
        # it crosses, the stem gives it up. Without this the hairline, taken
        # first, gave its ground across the stem to the stem's wedge and left
        # the stem nothing to hand over (Toat h, 2026-11-18). The siblings are
        # read AS CAPPED so far, so two overlapping columns never both give
        # the shared ink away.
        sib = unary_union([p for j, p in enumerate(pieces)
                           if j != k and med[j] < med[k] * THINNER])
        newc, n = cap_column(col, sib if not sib.is_empty else None)
        if n:
            from .script_strokes import _ribbon
            newc = replace(newc, piece=_ribbon(newc.stations))
            pieces[k] = newc.piece
        out.append(newc)
        any_cap = any_cap or n > 0
    return out if any_cap else columns
