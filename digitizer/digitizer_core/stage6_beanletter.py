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
from .stage6_satin import _bean_along, _resample
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


# A spine end this close to another spine (or to its own other end) is a
# JUNCTION, not a free end. The ink skeleton's edges meet at a shared pixel,
# a few hundredths of a millimetre apart.
_JOIN_MM = 0.12


def _attached(end, i: int, spines) -> bool:
    for j, other in enumerate(spines):
        pts = other if j != i else (other[-1:] if end == other[0] else other[:1])
        for q in pts:
            if math.dist(end, q) <= _JOIN_MM:
                return True
    return False


def trim_serif_hooks(spines, serif_mm: float | None):
    """Every spine with a short hook cut off each FREE end -- the slab serif a
    1.9 mm letter's centreline turns into, which closes an E into a B once
    the thread is laid (`cfg.bean_letter_serif_mm`). None: unchanged.

    An end that meets another spine is a junction and is never cut: at 81 mm
    the turn where an 8's loops meet read as a hook and both loops were
    snipped open, and the 5 lost the stroke joining its bar to its bowl."""
    if not serif_mm or serif_mm <= 0:
        return spines
    spines = [[tuple(p) for p in s] for s in (spines or [])]
    out = []
    for i, s in enumerate(spines):
        if len(s) < 2:
            out.append(s)
            continue
        head_free = not _attached(s[0], i, spines)
        tail_free = not _attached(s[-1], i, spines)
        if head_free:
            s = _cut_hook(s, serif_mm)
        if tail_free:
            s = list(reversed(_cut_hook(list(reversed(s)), serif_mm)))
        out.append(s)
    return out


# A corner is found by comparing the spine's direction over this much spine
# on either side of a point; the ink skeleton rounds a square corner over
# about a stroke width, so the window spans that rounding.
_CORNER_WINDOW_MM = 0.2
# Two corners closer than this along the spine are one corner.
_CORNER_SEP_MM = 0.3


def _corners(spine: list, corner_deg: float) -> list[int]:
    """Indices of `spine`'s interior points where it turns at least
    `corner_deg` within `_CORNER_WINDOW_MM` either side, strongest first
    wins within `_CORNER_SEP_MM`."""
    cum = [0.0]
    for a, b in zip(spine, spine[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    total = cum[-1]
    w = _CORNER_WINDOW_MM

    def at(t: float):
        t = max(0.0, min(total, t))
        for i in range(1, len(cum)):
            if cum[i] >= t:
                f = (t - cum[i - 1]) / ((cum[i] - cum[i - 1]) or 1.0)
                a, b = spine[i - 1], spine[i]
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        return spine[-1]

    turns = []
    for i in range(1, len(spine) - 1):
        if cum[i] < w or total - cum[i] < w:
            continue
        p, q, r = at(cum[i] - w), spine[i], at(cum[i] + w)
        v1, v2 = (q[0] - p[0], q[1] - p[1]), (r[0] - q[0], r[1] - q[1])
        n1, n2 = math.hypot(*v1), math.hypot(*v2)
        if n1 < 1e-9 or n2 < 1e-9:
            continue
        c = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        turn = math.degrees(math.acos(c))
        if turn >= corner_deg:
            turns.append((turn, i))
    picked: list[int] = []
    for _turn, i in sorted(turns, reverse=True):
        if all(abs(cum[i] - cum[j]) >= _CORNER_SEP_MM for j in picked):
            picked.append(i)
    return sorted(picked)


# A stretch of spine is STRAIGHT enough for `cfg.bean_letter_straight_mm`'s
# longer stitch when no stitch's chord leaves the spine by more than this: a
# fifth of a 40 wt thread's ~0.4 mm, about what the ink skeleton itself
# wanders on a straight stem (0.03-0.13 mm measured on Fremont at 81 mm).
# Geometry, not fabric.
STRAIGHT_SAG_MM = 0.08


def _station_piece(piece: list, step: float, straight_mm: float | None) -> list:
    """One corner-to-corner piece, stationed evenly at `step` -- or, with
    `straight_mm`, at the coarsest even pitch up to `straight_mm` whose
    chords all stay within `STRAIGHT_SAG_MM` of the piece."""
    n = _length(piece)
    fine = max(2, int(round(n / step)) + 1)
    if not straight_mm or straight_mm <= step:
        return _resample(piece, fine)
    from shapely.geometry import LineString
    spine = LineString(piece)
    for k in range(max(2, math.ceil(n / straight_mm) + 1), fine):
        pts = _resample(piece, k)
        if spine.hausdorff_distance(LineString(pts)) <= STRAIGHT_SAG_MM:
            return pts
    return _resample(piece, fine)


def _bean_keep_corners(spine: list, stitch_mm: float | None, corner_deg: float | None,
                       passes: int | None = None, straight_mm: float | None = None) -> list:
    """`_bean_along`, with a station ON every corner of the spine and the
    rest spaced evenly between corners. At an even pitch the stations of
    Fremont's 5 skipped the corner where its stem meets its bar, the thread
    cut straight across it, and the top of the 5 sewed as a triangle (read
    "A", 2026-10-14). No corner and no `straight_mm`: exactly `_bean_along`.

    `straight_mm` (`cfg.bean_letter_straight_mm`): each piece takes
    `_station_piece`'s longer pitch where it is straight."""
    cuts = _corners(spine, corner_deg) if corner_deg else []
    if not cuts and not straight_mm:
        return _bean_along(spine, stitch_mm, passes)
    step = stitch_mm if stitch_mm and stitch_mm > 0 else machine.BEAN_STITCH_MM
    lap: list = []
    bounds = [0, *cuts, len(spine) - 1]
    for a, b in zip(bounds, bounds[1:]):
        piece = spine[a:b + 1]
        n = _length(piece)
        if n <= 0:
            continue
        pts = _station_piece(piece, step, straight_mm)
        lap.extend(pts if not lap else pts[1:])
    if len(lap) < 2:
        return _bean_along(spine, stitch_mm, passes)
    out = list(lap)
    for p in range(1, passes if passes and passes > 0 else machine.BEAN_PASSES):
        leg = list(reversed(lap)) if p % 2 == 1 else list(lap)
        out.extend(leg[1:])
    return out


# A BAY of a letter is a concavity of its ink: what a closing of this radius
# adds to the ink with its counters filled (`tools/bean_glyph_trace.py`'s
# `BAY_CLOSE_MM`, the instrument #953 measured the bays with). The upper bay
# of Fremont's 5, the slit between THE's E tick and its middle arm.
BAY_CLOSE_MM = 0.45
# A bay smaller than this is not held off. The instrument counts pockets from
# 0.01 mm2 (`MIN_BAY_MM2`, the outline's roughness), but every junction of two
# strokes leaves a fillet of 0.01-0.04 mm2 (a T's stem under its bar, an 8's
# waist) that a thread at the junction covers whatever the stations do.
# Fremont's 5 upper bay is 0.23 mm2, the E's 0.7. A CANDIDATE (gate 1).
BAY_MIN_MM2 = 0.05
# Candidate needle points for a held station are laid on a grid this fine.
_BAY_GRID_MM = 0.02


def _letter_ink(spines: list, stroke_mm: float):
    """The letter's ink as the bean tier knows it: each spine grown by half
    the ink's stroke, flat at a FREE end (the ink reader already carried a
    free end out to the ink's edge, `ink_path._carry_out`), round where it
    meets another spine. -> (per-spine ink, the letter's ink)."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import unary_union

    half = stroke_mm / 2.0
    own = []
    for i, s in enumerate(spines):
        if len(s) < 2 or _length(s) <= 0:
            own.append(None)
            continue
        g = LineString(s).buffer(half)
        for end, nxt in ((s[0], s[1]), (s[-1], s[-2])):
            if _attached(end, i, spines):
                continue
            dx, dy = end[0] - nxt[0], end[1] - nxt[1]
            n = math.hypot(dx, dy)
            if n < 1e-9:
                continue
            ux, uy = dx / n, dy / n                 # outward along the spine
            vx, vy = -uy * stroke_mm, ux * stroke_mm
            g = g.difference(Polygon([
                (end[0] + vx, end[1] + vy),
                (end[0] + vx + ux * stroke_mm, end[1] + vy + uy * stroke_mm),
                (end[0] - vx + ux * stroke_mm, end[1] - vy + uy * stroke_mm),
                (end[0] - vx, end[1] - vy)]))
        own.append(g)
    parts = [g for g in own if g is not None and not g.is_empty]
    return own, (unary_union(parts) if parts else None)


def letter_bays(ink) -> list:
    """The BAYS of `ink` (`BAY_CLOSE_MM`): a closing of the ink with its
    counters filled, minus that filled ink, one polygon per pocket, pockets
    under `BAY_MIN_MM2` left out. A counter is not a bay: closed counters are
    `cfg.bean_letter_counter_hold_mm`'s (#952)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    if ink is None or ink.is_empty:
        return []
    polys = [ink] if ink.geom_type == "Polygon" else list(getattr(ink, "geoms", []))
    filled = unary_union([Polygon(g.exterior) for g in polys if g.geom_type == "Polygon"])
    closed = filled.buffer(BAY_CLOSE_MM).buffer(-BAY_CLOSE_MM)
    rest = closed.difference(filled)
    pieces = [rest] if rest.geom_type == "Polygon" else list(getattr(rest, "geoms", []))
    return [g for g in pieces if g.geom_type == "Polygon" and g.area >= BAY_MIN_MM2]


def letter_counters(ink) -> list:
    """The closed counters of `ink`, one polygon each."""
    from shapely.geometry import Polygon

    if ink is None or ink.is_empty:
        return []
    polys = [ink] if ink.geom_type == "Polygon" else list(getattr(ink, "geoms", []))
    return [Polygon(r) for g in polys if g.geom_type == "Polygon" for r in g.interiors]


def _width(g) -> float:
    """A pocket's mean width, 2 x area / perimeter."""
    return 2.0 * float(g.area) / max(float(g.length), 1e-9)


def hold_off_bays(pts: list, own_ink, bays, hold_mm: float, counters=()) -> list:
    """Every station of `pts` within `hold_mm` of a bay, moved to the point of
    its OWN spine's ink (`own_ink`) within `hold_mm` of it where the worst
    pocket beside it is least crowded -- the nearest of equals. A station no
    move improves stays exactly where it is, and the needle never leaves the
    spine's ink. `ink_path.hold_off_counters`' rule (#952), served to the
    bays a closed-counter hold cannot see.

    Crowding: for each pocket (a bay, or a closed counter in `counters`), how
    far short of `hold_mm` the station sits from it, over the pocket's mean
    width (`_width`) -- the share of a pocket a thread edge takes grows with
    how far it reaches in and shrinks with how wide the pocket is. So a
    stroke between two pockets (the bowl top of a 5, between its upper bay
    and its bowl) leans toward the WIDER one, and a stroke between a bay and
    a counter (an A's leg) is never pushed into the counter. A station only
    counters crowd is not moved: that is #952's hold.

    Why (`cfg.bean_letter_bay_hold`): a bean letter sews its ink's
    centreline, and a 0.40 mm thread on Fremont's 0.19 mm strokes lays
    0.10 mm past each edge -- the 5's upper bay at 81 mm sewed 64% covered
    and read A, and THE's E at 92.5 mm sewed the 0.26 mm slit between its tick
    and its middle arm shut (#953). Held, the thread lies on each stroke's
    side away from the bay that needs it.

    This moves bean STATIONS within a centreline's ink. It is not the satin
    rail push DOCTRINE 2026-09-30 ruled out a notch guard on (that push is
    pull compensation; a bean run has none)."""
    import numpy as np
    import shapely

    if isinstance(bays, (list, tuple)):
        bays = list(bays)
    elif bays is not None:
        bays = list(getattr(bays, "geoms", [bays]))
    if not bays or own_ink is None or own_ink.is_empty or hold_mm <= 0:
        return pts
    pockets = bays + list(counters or ())
    widths = np.array([_width(g) for g in pockets], float)[:, None]
    nb = len(bays)
    r = int(math.ceil(hold_mm / _BAY_GRID_MM))
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    ox, oy = ox.ravel() * _BAY_GRID_MM, oy.ravel() * _BAY_GRID_MM
    reach = np.hypot(ox, oy)
    disc = reach <= hold_mm + 1e-9
    ox, oy, reach = ox[disc], oy[disc], reach[disc]

    def crowding(xs, ys):
        p = shapely.points(xs, ys)
        d = np.array([np.asarray(shapely.distance(g, p), float) for g in pockets]).reshape(len(pockets), -1)
        return (np.maximum(0.0, hold_mm - d) / widths).max(axis=0), d[:nb].min(axis=0)

    moved: dict = {}
    out = []
    for q in pts:
        key = (round(q[0], 9), round(q[1], 9))
        if key not in moved:
            moved[key] = tuple(q)
            here, near_bay = crowding(np.array([q[0]]), np.array([q[1]]))
            if near_bay[0] < hold_mm:
                qx, qy = q[0] + ox, q[1] + oy
                ok = shapely.contains_xy(own_ink, qx, qy)
                if ok.any():
                    qx, qy, dd = qx[ok], qy[ok], reach[ok]
                    worst, _ = crowding(qx, qy)
                    best = int(np.lexsort((qx, qy, dd, worst))[0])
                    if worst[best] < here[0] - 1e-9:
                        moved[key] = (float(qx[best]), float(qy[best]))
        out.append(moved[key])
    return out


def bean_letter(spines, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float,
                stitch_mm: float | None = None,
                serif_mm: float | None = None,
                min_arm_mm: float | None = None,
                corner_deg: float | None = None,
                passes: int | None = None,
                bay_hold_mm: float | None = None,
                stroke_mm: float | None = None,
                straight_mm: float | None = None) -> tuple[list[StitchRun], dict]:
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
    wedge; None is that pitch, byte for byte.

    `min_arm_mm` (`cfg.bean_letter_min_arm_mm`): the shortest arm with a free
    end that sews, when it should be shorter than the pitch -- a 1's flag and
    foot. None: the pitch, as above.

    `corner_deg` (`cfg.bean_letter_corner_deg`): a turn this sharp gets a
    station of its own (`_bean_keep_corners`). None: even pitch, as before.

    `passes` (`cfg.bean_letter_passes`): laps along each spine. None:
    `machine.BEAN_PASSES` (3).

    `bay_hold_mm` (`cfg.bean_letter_bay_hold`) with `stroke_mm` (the
    member's `ink_stroke_mm`): every station held that far off the letter's
    bays inside its own spine's ink (`hold_off_bays`). None: the stations
    exactly as laid, byte for byte.

    `straight_mm` (`cfg.bean_letter_straight_mm`): the longest stitch on a
    straight stretch (`_station_piece`). None: the pitch, byte for byte."""
    arm_floor = stitch_mm if stitch_mm and stitch_mm > 0 else _MIN_ARM_MM
    report = {"loops": 0, "jumps": 0, "empty": True, "too_thin": False,
              "arcs": 0, "yielded": 0, "strokes": 0}
    trimmed = [list(map(tuple, s)) for s in (trim_serif_hooks(spines, serif_mm) or [])]

    def sews(i: int, s: list) -> bool:
        if len(s) < 2:
            return False
        n = _length(s)
        if n >= arm_floor:
            return True
        # Only an arm with a FREE end gets the shorter floor: a short link
        # between two junctions is the skeleton's waist of an 8, and sewn it
        # crossed the 8 into an X (Fremont at 92.5 mm, 2026-10-14).
        return bool(min_arm_mm and min_arm_mm > 0 and n >= min_arm_mm
                    and not (_attached(s[0], i, trimmed) and _attached(s[-1], i, trimmed)))

    todo = [s for i, s in enumerate(trimmed) if sews(i, s)]
    todo_ix = [i for i, s in enumerate(trimmed) if sews(i, s)]
    if sum(_length(s) for s in todo) < _MIN_SPINE_MM:
        todo = []
    # The bay hold (`cfg.bean_letter_bay_hold`): the letter's ink and bays,
    # modelled from the spines AS READ (a cut serif hook is still ink). None
    # or no stroke: nothing is read and every station is where it was.
    own_ink = bays = counters = None
    if bay_hold_mm and bay_hold_mm > 0 and stroke_mm and stroke_mm > 0 and todo:
        own_ink, ink = _letter_ink([list(map(tuple, s)) for s in spines], float(stroke_mm))
        bays, counters = letter_bays(ink) or None, letter_counters(ink)
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
        src = todo_ix.pop(i)
        if rev:
            spine.reverse()
        pts = (_bean_keep_corners(spine, stitch_mm, corner_deg, passes, straight_mm)
               if corner_deg or straight_mm else _bean_along(spine, stitch_mm, passes))
        if bays is not None:
            pts = hold_off_bays(pts, own_ink[src], bays, float(bay_hold_mm), counters)
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
