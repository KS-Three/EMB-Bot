"""A shaped outline band sewn from its OUTER edge
(`cfg.border_from_outline_follow_shape`, built OFF 2026-11-13).

The first build of that flag (#1455) kept `stage6_border._satin_loop`: needle
stations on the HOLE's ring, each cross cast out along the ring's normal and
cut where it left the art, plus a bean round the outer edge to give the teeth
corners. Kent, 2026-11-13: "it's an improvement but not across the board".
Rendered close up on five drawn shapes and the Commons gear at eight sizes,
the faults were all one fault -- the needle was placed from the wrong edge:

  * the shape is on the OUTER edge, and no needle hole was put on it on
    purpose. A 1.3 mm tooth got two or three stitch ends wherever the ring's
    stations happened to cast them, never one on its corners, and its corners
    stayed open (yellow showing inside every tooth);
  * crosses cast from a small ring FAN: 0.3 mm apart on the ring is 0.5 mm
    apart on the tooth, so the outer edge -- the one that shows -- was the
    sparse one;
  * round a square corner of the hole nothing pivoted: the band's outer
    corner, 2 x its thickness of edge, was left to four stitches;
  * the bean laid on top to draw the corners sat half a thread OUTSIDE the
    art and made 0.6 mm teeth into lumps.

Here the loop is laid out from the outer ring instead, the way a two-rail
satin is digitized by hand:

  * EVERY CORNER of the outer edge (a vertex turning
    `curve_fidelity.CORNER_DEG` or more) is a needle hole, exactly, and so
    are both ends of every SIDE WALL -- read off the edge itself, because a
    traced tooth has rounded corners and no such vertex (`_read_band`);
  * BETWEEN THEM the holes are spaced evenly, and the spacing is measured
    SQUARE TO THE STITCH: a stretch gets `round(lateral length / density)`
    stitches, its lateral length being its length as seen across the crosses
    that end on it. A tooth's side wall runs along its cross and has none of
    it, so it gets its two corners and nothing between; a tooth's tip and a
    root get the satin's density, on the edge that shows;
  * each hole's PARTNER on the hole's ring is the ring point nearest it,
    never stepping backwards. Round a square corner of the hole the partners
    all stand on that corner -- the fan a hand digitizer pivots there -- and
    on a small ring they bunch: one nearer than
    `machine.SATIN_SHORT_STITCH_AT_MM` to the two before it is pulled back
    off the ring by the least that clears them, the satin's own short
    stitch, on the ring rail (the rail that does not carry the shape);
  * a side wall is sewn ONCE: its second end is reached along the wall,
    outer hole to outer hole;
  * NO line on top. The outer edge is drawn the way every satin edge is, by
    its needle holes, and they are on the art.

No new constant: density is the border's, the corner angle `curve_fidelity`'s,
the short stitch and the shortest and longest cross the satin's, the closing
overlap the border's.

A band this cannot lay out returns no runs and the caller keeps the loop it
had: an outer edge that strays further than one satin from the ring
(`machine.SATIN_MAX_WIDTH_MM`), a ring the outer edge does not go once round,
or more than `_MAX_LOST_FRAC` of its stitches lost to pinches.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon

from . import deadline, machine, stitches
from .curve_fidelity import CORNER_DEG
from .stage6_border import _keyline_centre
from .stage6_fill import travel_path
from .stitches import StitchRun

#: how finely the outer edge is read (mm between samples; every vertex is one)
_READ_MM = 0.05
#: a cross must lie in the art give or take this (a wall's cross runs ON the edge)
_SLACK_MM = 0.02
#: how finely a short stitch's pull is searched
_PULL_STEP_MM = 0.05
#: more of the stitches than this lost to pinches or cut short: not laid out
_MAX_LOST_FRAC = 0.2


def _ccw(coords) -> list[tuple[float, float]]:
    """A ring's vertices, open-listed, counter-clockwise."""
    ring = [(float(x), float(y)) for x, y in coords]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
    return ring if area >= 0 else ring[::-1]


def _turn_deg(a, b, c) -> float:
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    cos = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cos))


def _read_edge(outer: list[tuple[float, float]]):
    """The outer ring as fine samples. -> (points Nx2, arc length at each,
    is-corner flags, total length). Every vertex is a sample."""
    pts: list[tuple[float, float]] = []
    corner: list[bool] = []
    n = len(outer)
    # two corners nearer than the short-stitch line are one needle hole: the
    # sharper keeps it (a traced corner is often two vertices a hair apart)
    turns = sorted(((_turn_deg(outer[i - 1], outer[i], outer[(i + 1) % n]), i) for i in range(n)),
                   key=lambda t: (-t[0], t[1]))
    sharp: list[int] = []
    for turn, i in turns:
        if turn < CORNER_DEG:
            break
        if all(math.dist(outer[i], outer[j]) >= machine.SATIN_SHORT_STITCH_AT_MM for j in sharp):
            sharp.append(i)
    is_corner = set(sharp)
    for i in range(n):
        a, b = outer[i], outer[(i + 1) % n]
        pts.append(a)
        corner.append(i in is_corner)
        k = int(math.dist(a, b) / _READ_MM)
        for j in range(1, k + 1):
            f = j / (k + 1)
            pts.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            corner.append(False)
    P = np.asarray(pts, float)
    seg = np.hypot(*(np.roll(P, -1, axis=0) - P).T)
    arc = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
    return P, arc, np.asarray(corner, bool), float(seg.sum())


def _read_band(band, hole: Polygon):
    """The band read from its outer edge, or None when it cannot be (module
    notes). -> (P, corner, n, ring, total, lap, u, reach, lat, L, walls,
    steep): the edge's samples, which of them are needle holes by right
    (corners and wall ends), the hole's ring and each sample's partner on it
    (`u`, a distance round the ring), each sample's cross length, the lateral
    length of each sample's segment and its running sum, the side walls as
    [(first segment, one past the last)], and which segments run steep
    (within 30 degrees of their cross) before any is read as a wall."""
    if band is None or band.is_empty or band.geom_type != "Polygon":
        return None
    outer = _ccw(band.exterior.coords)
    inner = _ccw(hole.exterior.coords)
    if len(outer) < 3 or len(inner) < 3:
        return None
    ring = LineString(inner + inner[:1])
    total = ring.length
    if total <= 0:
        return None
    P, _arc, corner, _length = _read_edge(outer)
    n = len(P)
    if n < 8:
        return None

    # each sample's partner on the ring: the nearest ring point, unwrapped
    # round the ring and never stepping backwards
    at = shapely.line_locate_point(ring, shapely.points(P))
    step = (np.diff(at, append=at[:1]) + total / 2.0) % total - total / 2.0
    lap = float(step.sum())
    if not 0.9 * total <= lap <= 1.1 * total:
        return None                         # the outer edge does not go once round this ring
    u = at[0] + np.concatenate([[0.0], np.cumsum(step)[:-1]])
    u = np.maximum.accumulate(u)
    R = np.asarray([ring.interpolate(float(v) % total).coords[0] for v in u], float)
    cross = P - R
    reach = np.hypot(*cross.T)
    if float(reach.max()) > machine.SATIN_MAX_WIDTH_MM:
        return None                         # further out than one satin
    d = cross / np.maximum(reach, 1e-9)[:, None]

    # lateral length: the edge's travel as seen across the cross that ends on it
    nxt = np.roll(P, -1, axis=0) - P
    dm = d + np.roll(d, -1, axis=0)
    dm /= np.maximum(np.hypot(*dm.T), 1e-9)[:, None]
    lat = np.abs(nxt[:, 0] * dm[:, 1] - nxt[:, 1] * dm[:, 0])
    L = np.concatenate([[0.0], np.cumsum(lat)])          # L[k]: lateral length up to sample k

    # SIDE WALLS, read off the edge itself: a stretch running along its own
    # crosses (within 30 degrees) that steps the band's thickness by a needle
    # hole or more. A wall's two ends are needle holes whether or not the art
    # has a vertex there -- a TRACED tooth has rounded corners, two or three
    # shallow vertices none of which turns `CORNER_DEG`, and laid out on
    # vertex angle alone the Commons gear at 60 mm got its stitches wherever
    # the even spacing fell (rendered 2026-11-13: ragged teeth). A steep
    # stretch that steps less than a hole is the trace's noise and is part of
    # the face it sits in; a face shorter than a hole between two walls is
    # part of one wall (a stair).
    near = machine.SATIN_SHORT_STITCH_AT_MM
    ds = np.hypot(*nxt.T)
    steep = lat < 0.5 * ds
    steep_raw = steep.copy()
    reach_round = np.append(reach, reach[0])

    def _spans(flags):
        """Maximal runs of True round the ring: [(first segment, one past the last)], unwrapped."""
        if flags.all():
            return [(0, n)]
        if not flags.any():
            return []
        first = next(i for i in range(n) if flags[i] and not flags[i - 1])
        runs, i = [], first
        while i < first + n:
            if flags[i % n]:
                j = i
                while j < first + n and flags[j % n]:
                    j += 1
                runs.append((i, j))
                i = j
            else:
                i += 1
        return runs

    for a, b in _spans(steep):
        if abs(float(reach_round[b % n]) - float(reach_round[a % n])) < near:
            steep[[i % n for i in range(a, b)]] = False
    for a, b in _spans(~steep):
        if steep.any() and float(sum(lat[i % n] for i in range(a, b))) < near:
            steep[[i % n for i in range(a, b)]] = True
    walls = [] if steep.all() else _spans(steep)
    wall_ends: set[int] = set()
    in_wall: set[int] = set()
    for a, b in walls:
        wall_ends.update((a % n, b % n))
        in_wall.update(i % n for i in range(a + 1, b))
    # a vertex corner keeps its hole on a face (a star's point, the outer
    # corner of a frame); inside a wall, or a hole's width from a wall's end,
    # the wall's ends are the holes
    ends_xy = [P[i] for i in wall_ends]
    for i in np.flatnonzero(corner):
        i = int(i)
        if i in in_wall or any(float(np.hypot(*(P[i] - e))) < near for e in ends_xy):
            corner[i] = False
    for i in wall_ends:
        corner[i] = True
    return P, corner, n, ring, total, lap, u, reach, lat, L, walls, steep_raw


def stepped_share(band, hole: Polygon) -> float:
    """How much of the outer edge's change in thickness happens where the
    edge runs STEEP (within 30 degrees of its own crosses), 0 to 1: high for
    a gear, whose thickness changes at the teeth's sides and nowhere else;
    near 0 for a band whose width only wanders, however far. 0.0 for a band
    that cannot be read.

    What `art_outline.shaped_width_mm` asks of a band whose thickness swings
    by less than the shortest stitch: there a swing alone does not say
    "teeth". Commons "(hed) p.e." at 180 mm has a white keyline 0.57 to
    0.92 mm thick, a line of uneven width (the pro's widened loop); the
    Commons gear at 40 mm is 0.57 to 0.93."""
    read = _read_band(band, hole)
    if read is None:
        return 0.0
    reach, steep = read[7], read[11]
    change = np.abs(np.diff(np.append(reach, reach[0])))
    total = float(change.sum())
    return float(change[steep].sum()) / total if total > 0 else 0.0


def layout(band, hole: Polygon, density_mm: float | None = None):
    """The crosses of one shaped band round `hole`, in order round the band:
    [(ring point, outer point)], or None when the band cannot be laid out
    (module notes). The ring point of a short stitch is already pulled back;
    it is None where the needle reaches the outer point along a side wall,
    from the outer point before it."""
    density = machine.BORDER_DENSITY_MM if density_mm is None else float(density_mm)
    read = _read_band(band, hole)
    if read is None:
        return None
    P, corner, n, ring, total, lap, u, _reach, _lat, L, _walls, _steep = read

    # needle holes: every corner and wall end, and between two of them an even
    # share of the lateral length (none at all: evenly from sample 0). Inside
    # a wall there is no lateral length and no hole.
    at_corner = [int(i) for i in np.flatnonzero(corner)] or [0]
    marks: list[float] = []                               # fractional sample indices
    idx = np.arange(n + 1, dtype=float)
    for a, b in zip(at_corner, at_corner[1:] + [at_corner[0] + n]):
        marks.append(float(a))
        if b <= a:
            continue
        # this stretch's lateral length, read round the seam if it wraps
        if b <= n:
            Ls, base = L[a:b + 1], idx[a:b + 1]
        else:
            Ls = np.concatenate([L[a:], L[n] + L[1:b - n + 1]])
            base = np.concatenate([idx[a:], n + idx[1:b - n + 1]])
        span = float(Ls[-1] - Ls[0])
        k = int(round(span / density))
        for j in range(1, k):
            marks.append(float(np.interp(Ls[0] + span * j / k, Ls, base)))

    u_round = np.append(u, max(float(u[-1]), float(u[0]) + lap))   # the seam's sample, a lap on

    def at_mark(m: float):
        i = int(math.floor(m)) % n
        f = m - math.floor(m)
        j = (i + 1) % n
        o = (float(P[i][0] + (P[j][0] - P[i][0]) * f), float(P[i][1] + (P[j][1] - P[i][1]) * f))
        uu = float(u_round[i]) + (float(u_round[i + 1]) - float(u_round[i])) * f
        r = ring.interpolate(uu % total).coords[0]
        return (float(r[0]), float(r[1])), o

    art = band.buffer(_SLACK_MM)
    out: list[tuple[tuple[float, float], tuple[float, float]]] = []
    lost = 0
    for m in marks:
        deadline.check("keyline")
        r, o = at_mark(m)
        if not art.covers(LineString([r, o])):
            # cut where it leaves the art, keeping the end on the outer edge
            best = None
            part = LineString([r, o]).intersection(art)
            for g in getattr(part, "geoms", [part]):
                if g.is_empty or g.geom_type != "LineString":
                    continue
                e0, e1 = g.coords[0], g.coords[-1]
                if min(math.dist(e0, o), math.dist(e1, o)) < 1e-6:
                    best = e0 if math.dist(e1, o) < math.dist(e0, o) else e1
            lost += 1
            if best is None:
                continue
            r = (float(best[0]), float(best[1]))
        if math.dist(r, o) < machine.SATIN_MIN_CROSS_MM:
            lost += 1
            continue                        # pinched: nothing to sew here
        out.append((r, o))
    if len(out) < 8 or lost > _MAX_LOST_FRAC * len(marks):
        return None

    near = machine.SATIN_SHORT_STITCH_AT_MM

    # A side wall is sewn ONCE. Its two ends (a tooth's tip corner, the root
    # corner under it) share a ring point and lie on one line with it, so two
    # crosses there are one line of thread laid three times (up, back, up
    # again). The second end is reached along the wall instead, outer hole to
    # outer hole, and its ring point is not sewn: its cross is None for the
    # ring. Both corners keep their needle hole, and the stitch after still
    # leaves from the right one -- from the root corner into a root, so no
    # thread crosses the gap between two teeth.
    real = [r for r, _o in out]
    for i in range(len(out)):
        (_r0, o0), (r1, o1) = out[i - 1], out[i]
        r0 = real[i - 1]
        chord = math.dist(o0, o1)
        w = math.dist(r1, o1)
        if chord < 1e-6 or math.dist(r0, r1) >= near:
            continue
        across = abs((o1[0] - o0[0]) * (o1[1] - r1[1]) - (o1[1] - o0[1]) * (o1[0] - r1[0])) / w
        if across < 0.5 * chord:
            out[i] = (None, o1)
            real[i] = r0                    # a third end on the same wall chains on
    if sum(1 for r, _o in out if r is not None) < 8:
        return None

    # The satin's short stitch, on the ring rail. A ring hole nearer than
    # `SATIN_SHORT_STITCH_AT_MM` to either of the two before it is pulled back
    # along its own cross -- by the LEAST that clears them both, up to the
    # satin's own pull (`_PULL` of the cross, `_PULL_MAX_MM`). The full pull
    # every time halved the ring edge's cover where the holes were only just
    # too close (0.29 mm apart in the gear's roots: every other stitch 0.5 mm
    # short, and the disc showed between them); the least pull staggers the
    # holes into two rows 0.1 to 0.2 mm apart and the edge stays covered.
    # Round a square corner, where they all stand on one point, it comes to a
    # three-step stagger.
    kept = [r for r, _o in out if r is not None]
    before = [kept[-2], kept[-1]]
    for i, (r, o) in enumerate(out):
        if r is None:
            continue
        w = math.dist(r, o)
        most = min(machine.SATIN_SHORT_STITCH_PULL * w, machine.SATIN_SHORT_STITCH_PULL_MAX_MM,
                   w - machine.SATIN_MIN_CROSS_MM)
        if most > 0 and min(math.dist(r, b) for b in before) < near - 1e-9:
            ux, uy = (o[0] - r[0]) / w, (o[1] - r[1]) / w
            pull = most
            for k in range(1, int(most / _PULL_STEP_MM) + 1):
                q = (r[0] + ux * k * _PULL_STEP_MM, r[1] + uy * k * _PULL_STEP_MM)
                if min(math.dist(q, b) for b in before) >= near - 1e-9:
                    pull = k * _PULL_STEP_MM
                    break
            r = (r[0] + ux * pull, r[1] + uy * pull)
            out[i] = (r, o)
        before = [before[1], r]
    return out


def sews_shaped(band, holes: list[Polygon]) -> bool:
    """True when `band`, an art outline round `holes`, is one this module
    sews: round one body, shaped (`art_outline.shaped_width_mm`), and laid
    out. What stage 7's outline rung asks before it calls `shaped_band_runs`,
    for a caller that has to know beforehand."""
    from .art_outline import shaped_width_mm

    if len(holes) != 1 or band is None or band.is_empty or band.geom_type != "Polygon":
        return False
    return shaped_width_mm(band, holes[0]) is not None and layout(band, holes[0]) is not None


def shaped_band_runs(band, hole: Polygon, shape_id: str, *,
                     entry: tuple[float, float] | None, trim_at_mm: float,
                     density_mm: float | None = None,
                     underlay: bool = False) -> tuple[list[StitchRun], dict]:
    """One shaped band as a satin laid out from its outer edge (module
    notes). -> (runs, report); `report["empty"]` when the band cannot be laid
    out, and the caller keeps the loop it had.

    The loop starts on the cross nearest `entry`, goes once round, and runs on
    past its start by `machine.BORDER_CLOSURE_OVERLAP_MM`, each closing stitch
    midway between two opening ones. `underlay`: the loop's centre line is
    walked first (`stage6_border._keyline_centre`), as a keyline loop's is.

    Report keys: `loops`, `crosses`, `clamped`, `jumps`, `empty`.
    """
    report = {"loops": 0, "crosses": 0, "clamped": 0, "jumps": 0, "empty": True}
    crosses = layout(band, hole, density_mm)
    if not crosses:
        return [], report
    n = len(crosses)
    # the loop starts on a cross with a ring end (not part-way up a wall)
    whole = [i for i in range(n) if crosses[i][0] is not None]
    start = whole[0]
    if entry is not None:
        start = min(whole, key=lambda i: (round(math.dist(crosses[i][0], entry), 6), i))
    lap = [crosses[(start + i) % n] for i in range(n)]
    pts: list[tuple[float, float]] = []
    for r, o in lap:
        pts += [o] if r is None else [r, o]
    # the closing stitches stand midway between two opening ones; a side wall
    # (its second end has no ring point) has no midway and is stepped over
    done = 0.0
    for (r0, o0), (r1, o1) in zip(lap, lap[1:] + lap[:1]):
        if done >= machine.BORDER_CLOSURE_OVERLAP_MM:
            break
        done += math.dist(o0, o1)
        if r0 is None or r1 is None:
            continue
        pts += [((r0[0] + r1[0]) / 2.0, (r0[1] + r1[1]) / 2.0),
                ((o0[0] + o1[0]) / 2.0, (o0[1] + o1[1]) / 2.0)]

    runs: list[StitchRun] = []
    jump = trim = False
    if entry is not None:
        bridge = travel_path(band, None, entry, pts[0])
        if bridge is None:
            d = math.dist(entry, pts[0])
            if d >= machine.TINY_STITCH_MM:
                jump, trim = True, d > trim_at_mm
                report["jumps"] += 1
        elif len(bridge) > 1:
            runs.append(StitchRun(points=bridge[:-1], kind=stitches.TRAVEL, shape_id=shape_id))
    if underlay:
        centre = _keyline_centre(pts)
        if len(centre) > 2:
            runs.append(StitchRun(points=centre, kind=stitches.UNDERLAY, jump=jump, trim=trim,
                                  shape_id=shape_id))
            jump = trim = False
    runs.append(StitchRun(points=stitches.split_long_moves(pts), kind=stitches.SATIN,
                          jump=jump, trim=trim, shape_id=shape_id))
    report.update(loops=1, crosses=n, empty=False)
    return runs, report
