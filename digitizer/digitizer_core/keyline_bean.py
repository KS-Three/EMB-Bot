"""A hairline keyline sewn as a bean line (`cfg.border_from_outline_hairline_run`,
built OFF 2026-11-13).

`border_from_outline` sews the art's own outline as a satin loop at the art's
thickness clamped to `machine.OUTLINE_WIDTH_MM` (1.5 to 2.5 mm). That floor
was read off outlines 0.8 mm and up. Kent's keyline logo (a red wordmark,
2026-11-13) draws a 0.36-0.42 mm white keyline at 100 mm wide; it sewed 1.50 mm loops, 3.7x the art.

A keyline that thin is one thread, and a line of one thread shows every
fault (Kent, 2026-11-13: "look at it as if you are building a swiss watch,
and not a playhouse out of logs"). So the line here is built from the vector,
never from a raster skeleton:

  * THE PATH is the keyline's centreline: each body's own edge (a hole of the
    keyline polygon, the same ring the body's fill is cut to) moved out by
    half the keyline's width, mitred, so a sharp corner of the art stays a
    sharp corner of the line.
  * EVERY CORNER (a vertex turning `curve_fidelity.CORNER_DEG` or more) is a
    needle point, exactly. The run tier's even stationing steps over corners
    and cuts them by up to half a stitch.
  * BETWEEN CORNERS the stations are spaced evenly, as near
    `machine.BEAN_STITCH_MM` as the stretch divides, on the ring with its
    curve vertices softened (`stage6_border._soften_ring`: Douglas-Peucker
    leaves a curve as flat chords meeting at shallow vertices).
  * THE LOOP CLOSES on its own first needle point, and all
    `machine.BEAN_PASSES` passes use the same holes.

No new constant: the width gate is the hairline tier's
(`stage6_hairline.measure`), the pitch and passes are the bean's, the corner
angle is `curve_fidelity`'s, the loop floor is the run tier's.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import machine, stitches
from .curve_fidelity import CORNER_DEG
from .stage6_border import _bean_arc, _bean_loop, _parts, _soften_ring
from .stitches import StitchRun

#: two corners nearer than this along the line are one needle point (the
#: sharper wins): under it the needle is re-entering its own hole.
_CORNER_SEP_MM = machine.TINY_STITCH_MM


def keyline_width_mm(poly) -> float:
    """A band's own width: 2A/P (a ribbon of length L and width w has A = wL
    and P ~ 2L)."""
    return 2.0 * poly.area / poly.length if poly.length > 0 else 0.0


def centrelines(poly) -> list[list[tuple[float, float]]]:
    """The keyline's centreline loops, one per body it holds: every hole of
    `poly` moved out by half the band's width, corners mitred. Closed rings
    (first point repeated), holes in polygon order, loops under
    `machine.RUN_MIN_LOOP_MM` left out."""
    out: list[list[tuple[float, float]]] = []
    for part in _parts(poly):
        half = keyline_width_mm(part) / 2.0
        if half <= 0:
            continue
        for ring in part.interiors:
            grown = Polygon(ring).buffer(half, join_style=2)
            if grown.is_empty:
                continue
            if grown.geom_type != "Polygon":
                grown = max(grown.geoms, key=lambda g: g.area)
            coords = [(float(x), float(y)) for x, y in grown.exterior.coords]
            if LineString(coords).length < machine.RUN_MIN_LOOP_MM:
                continue
            out.append(coords)
    return out


def _turn_deg(a, b, c) -> float:
    ux, uy, vx, vy = b[0] - a[0], b[1] - a[1], c[0] - b[0], c[1] - b[1]
    if math.hypot(ux, uy) < 1e-9 or math.hypot(vx, vy) < 1e-9:
        return 0.0
    return abs(math.degrees(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)))


def corners(ring: list[tuple[float, float]]) -> list[int]:
    """Indices of the corner vertices of an OPEN-listed ring (no repeated
    first point): turning `CORNER_DEG` or more, the sharper kept of any two
    nearer than `_CORNER_SEP_MM`."""
    n = len(ring)
    turns = sorted(((_turn_deg(ring[i - 1], ring[i], ring[(i + 1) % n]), i) for i in range(n)),
                   key=lambda t: (-t[0], t[1]))
    picked: list[int] = []
    for turn, i in turns:
        if turn < CORNER_DEG:
            break
        if all(math.dist(ring[i], ring[j]) >= _CORNER_SEP_MM for j in picked):
            picked.append(i)
    return sorted(picked)


def _even(piece: list[tuple[float, float]], pitch: float) -> list[tuple[float, float]]:
    """An open stretch from one corner to the next: its first point, then
    stations at an even pitch as near `pitch` as it divides. The last point
    (the next corner) is left to the next stretch."""
    line = LineString(piece)
    total = line.length
    n = max(1, int(round(total / pitch)))
    out = [piece[0]]
    for i in range(1, n):
        q = line.interpolate(total * i / n)
        out.append((q.x, q.y))
    return out


def stations(coords: list[tuple[float, float]],
             pitch: float = machine.BEAN_STITCH_MM) -> list[tuple[float, float]]:
    """One closed ring -> its needle points, in order, the ring not repeated.

    A needle point on every corner; between corners, even stations on the
    softened ring. A ring with no corner (a circle) is stationed evenly all
    round."""
    ring = [(float(x), float(y)) for x, y in coords]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    if len(ring) < 3:
        return []
    keep = {ring[i] for i in corners(ring)}
    soft = _soften_ring(ring + ring[:1])[:-1]      # corners come through untouched
    at = [i for i, p in enumerate(soft) if p in keep]
    if not at:
        line = LineString(soft + soft[:1])
        n = max(3, int(round(line.length / pitch)))
        return [(q.x, q.y) for q in (line.interpolate(line.length * i / n) for i in range(n))]
    out: list[tuple[float, float]] = []
    m = len(soft)
    for a, b in zip(at, at[1:] + [at[0] + m]):
        piece = [soft[i % m] for i in range(a, b + 1)]
        out.extend(_even(piece, pitch))
    return out


def keyline_bean_runs(poly, shape_id: str, *, entry: tuple[float, float] | None,
                      trim_at_mm: float) -> tuple[list[StitchRun], dict]:
    """A hairline keyline polygon -> (runs, report): one bean loop per body
    it holds, on its centreline.

    Report keys: the shared tier vocabulary (`empty`, `jumps`, `too_thin`,
    always False) plus `loops`, `corners` (needle points placed on a corner),
    `width_mm`, and, where two loops share a stretch of band, `arcs` (open
    stretches sewn) and `shared` (loops wholly on a line already sewn).
    `empty` when the loops would leave more than
    1 - `machine.OUTLINE_REACH_FRAC` of the keyline further than its own
    width from every loop (a keyline with a tail no loop follows): the caller
    takes the ladder, nothing is dropped silently."""
    report = {"empty": True, "jumps": 0, "too_thin": False, "loops": 0, "corners": 0,
              "width_mm": round(keyline_width_mm(poly), 4)}
    loops = centrelines(poly)
    if not loops:
        return [], report
    width = keyline_width_mm(poly)
    reach = unary_union([LineString(c) for c in loops]).buffer(width)
    if poly.intersection(reach).area < machine.OUTLINE_REACH_FRAC * poly.area:
        return [], report
    runs: list[StitchRun] = []
    cursor = entry

    def emit(lap):
        nonlocal cursor
        if len(lap) < 2:
            return
        jump = trim = False
        if runs and cursor is not None:
            d = math.dist(cursor, lap[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(lap), kind=stitches.RUN,
                              jump=jump, trim=trim, shape_id=shape_id))
        cursor = lap[-1]

    # Longest loop first, whole. Where two bodies share one stretch of band
    # (a counter's keyline running into the word's) both centrelines lie on
    # it: the later loop sews only its own arcs, each carried on to the line
    # already sewn, so the shared stretch is three passes and not six, and no
    # arc stops short of the line it joins.
    sewn: list[LineString] = []
    holes: list[tuple[float, float]] = []       # every needle point laid so far
    for coords in sorted(loops, key=lambda c: -LineString(c).length):
        pts = stations(coords)
        if len(pts) < 3:
            continue
        ring = [(float(x), float(y)) for x, y in coords[:-1]]
        report["corners"] += len(corners(ring))
        line = LineString(coords)
        if not sewn:
            emit(_bean_loop(pts, cursor, machine.BEAN_STITCH_MM, machine.BEAN_PASSES))
            report["loops"] += 1
            sewn.append(line)
            holes.extend(pts)
            continue
        laid = unary_union(sewn)
        near = laid.buffer(width / 2.0)
        own = [not near.contains(Point(p)) for p in pts]
        if all(own):
            emit(_bean_loop(pts, cursor, machine.BEAN_STITCH_MM, machine.BEAN_PASSES))
            report["loops"] += 1
        elif any(own):
            n = len(pts)
            start = own.index(False)
            arc: list[int] = []
            arcs: list[list[int]] = []
            for k in range(1, n + 1):
                j = (start + k) % n
                if own[j]:
                    arc.append(j)
                elif arc:
                    arcs.append(arc)
                    arc = []
            if arc:
                arcs.append(arc)
            for idx in arcs:
                # each end carried on to the sewn line, into a hole the
                # needle already made there: the laid station nearest the
                # first station this loop gave up
                head = min(holes, key=lambda h: math.dist(h, pts[(idx[0] - 1) % n]))
                tail = min(holes, key=lambda h: math.dist(h, pts[(idx[-1] + 1) % n]))
                emit(_bean_arc([head, *(pts[j] for j in idx), tail],
                               cursor, machine.BEAN_PASSES))
                report["arcs"] = report.get("arcs", 0) + 1
        else:
            report["shared"] = report.get("shared", 0) + 1
        sewn.append(line)
        holes.extend(pts)
    report["empty"] = not runs
    return runs, report


def _thin_ring(poly, max_width_mm: float, ink=None) -> bool:
    """A ring (a polygon with a hole) the hairline tier's width gate admits
    WHOLE (`stage6_hairline.measure`'s `shape_admit`)."""
    from .stage6_hairline import measure

    if poly is None or poly.is_empty or not any(part.interiors for part in _parts(poly)):
        return False
    m = measure(poly, max_width_mm, ink=ink)
    return bool(m is not None and m["admit"] and m["shape_admit"])


def keyline_regions(regions, outline_ids, cfg, ink=None) -> set[str]:
    """Which regions sew as a keyline bean -> shape ids.

    An art outline (`outline_ids`) that is a thin ring, and every other thin
    ring of the same thread: the keyline round a dot or a counter is too
    short a loop to be an outline (`machine.BORDER_MIN_LOOP_MM`), and sewn as
    a satin beside its neighbours' bean it is a blob on the line. Sewn,
    "auto"-tier shapes only: a tier the user set is an instruction. The width
    is the block's hairline width (`ThreadProfile.hairline_max_width_mm`,
    0.6 mm at 40 wt)."""
    from .stage6_hairline import block_thread_wt

    bw = block_thread_wt(regions, cfg)

    def thin(r) -> bool:
        if (not r.meta.get("stitched", True)
                or str(r.meta.get("tier", "auto")).lower() != "auto"):
            return False
        prof = machine.thread_profile(bw.get(r.thread_index, cfg.thread_wt))
        return _thin_ring(r.polygon, prof.hairline_max_width_mm, ink=ink)

    out = {r.shape_id for r in regions if r.shape_id in outline_ids and thin(r)}
    if not out:
        return out
    threads = {r.thread_index for r in regions if r.shape_id in out}
    out |= {r.shape_id for r in regions
            if r.shape_id not in out and r.thread_index in threads and thin(r)}
    return out


def sew_last(regions, ids: set[str]):
    """The keyline beans moved to layers of their own after every other
    shape, one per thread in the order their layers stood: a line one thread
    wide sewn before the fill it edges is buried by it (Kent's keyline logo: the
    brackets' fill came after their keyline and covered it whole).
    Regions as copies, layers renumbered; nothing to move: the input list."""
    if not ids or not any(r.shape_id in ids for r in regions):
        return regions
    from dataclasses import replace

    top = max(r.meta["layer"] for r in regions)
    first: dict[int, int] = {}
    for r in sorted(regions, key=lambda r: r.meta["layer"]):
        if r.shape_id in ids:
            first.setdefault(r.thread_index, len(first))

    def key(r):
        return top + 1 + first[r.thread_index] if r.shape_id in ids else r.meta["layer"]

    order = sorted({key(r) for r in regions})
    renum = {L: i for i, L in enumerate(order)}
    return [replace(r, meta={**r.meta, "layer": renum[key(r)]})
            for _i, r in sorted(enumerate(regions), key=lambda t: (key(t[1]), t[0]))]


def body_limits(planned, ids: set[str]) -> dict[str, Polygon]:
    """{body shape id: the line its fill may not pass}: for every planned
    shape that sits in a hole of a keyline bean, that hole's centreline loop
    as a polygon -- the bean's own needle line. A shape in two keylines'
    holes (a counter inside a letter inside the word's keyline) takes the
    innermost."""
    by_id = {p.shape_id: p for p in planned}
    out: dict[str, Polygon] = {}
    for sid in sorted(ids):
        k = by_id.get(sid)
        if k is None:
            continue
        for part in _parts(k.region.polygon):
            half = keyline_width_mm(part) / 2.0
            for ring in part.interiors:
                hole = Polygon(ring)
                limit = hole.buffer(half, join_style=2)
                for p in planned:
                    art = p.region.polygon
                    if (p.shape_id in ids or art is None or art.is_empty
                            or not hole.contains(art.representative_point())):
                        continue
                    if p.shape_id not in out or limit.area < out[p.shape_id].area:
                        out[p.shape_id] = limit
    return out


def held(poly, limit):
    """`poly` cut to `limit`, or `poly` itself when there is no limit or the
    cut would not leave one polygon (nothing is dropped to make a line
    clean)."""
    if limit is None or poly is None or poly.is_empty:
        return poly
    cut = poly.intersection(limit)
    return cut if cut.geom_type == "Polygon" and not cut.is_empty else poly


def hold_bodies(planned, ids: set[str]) -> int:
    """No fill past its keyline: every body's sew polygon cut to its
    `body_limits` line. Stage 5 grows a body under the shape sewn after it
    (by more than a hairline keyline is wide) and adds pull compensation on
    top; unheld, the fill showed 0.5 mm outside the white line all round.
    The body keeps what growth fits under the line. In place; -> shapes
    cut."""
    limits = body_limits(planned, ids)
    cut = 0
    for p in planned:
        if p.shape_id not in limits or p.polygon is None or p.polygon.is_empty:
            continue
        new = held(p.polygon, limits[p.shape_id])
        if new is not p.polygon and new.area < p.polygon.area:
            p.polygon = new
            cut += 1
    return cut
