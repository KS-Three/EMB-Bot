"""One border band round a word, a column for each stem between its faces
(`cfg.outline_one_band`, built OFF 2026-11-18).

`border_from_outline` sews an art outline as one satin loop round each face
hole it holds (`stage6_border.keyline_runs`). Where two faces stand under two
loop widths apart (BECKER: the B and the E, the C and the K ...) the stem of
outline between them is covered by BOTH loops, and the two columns pile into a
knot at the dip (prime grader, Becker large, pin x 21.0 y 8.5; Kent 2026-11-10,
"The border around this logo should be smooth"). `outline_loop_split_shared`
(#1657) butted the two loops at the line the faces share and traded the lump
for a seam down each stem.

The professional's Becker file (read 2026-11-18, numbers only; see the PR) does
not sew a loop per face. At the B/E dip, over one fill laid under the whole
group, he sews

  * the STEM first, as its own satin column (122 stitch pairs, 19 mm long, the
    width of the stem between the two faces), its first crosses following the
    border and turning square to the stem as it runs down;
  * then ONE border band along the top across the V, its crosses near-square
    to the band all the way (79 to 93 deg), no fan and no mitre.

Here, for an outline whose band is shared by two or more bodies and has such
stems:

  * the band's STEMS are the pieces of band within one loop width of two
    different holes and further than one width from the outer edge: each is
    sewn as a satin column of its own, first (`stage6_satin.satin_shape`);
  * ONE loop runs on the band's OUTER ring, its crosses cast inward at the
    band width and cut where they reach a hole, so it passes the dip as one
    band, last;
  * what is left near a hole and in neither of those (a drop shadow thicker
    than the band) keeps the hole's own loop, its crosses cut where they would
    enter the band or a stem.

No new constant: the width is the outline's own (`outline_holes`), a stem is
told by being longer than two of its own widths (geometry, not thread).
A band with no stem, or one the layout cannot sew, returns nothing and the
caller keeps its loops.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import nearest_points, substring, unary_union

from . import machine, stitches
from .stitches import StitchRun
from .stage6_fill import _densify, travel_path
from .stage6_border import keyline_runs
from .stage6_satin import satin_shape


def _parts(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]


def _length_over_width(poly: Polygon) -> tuple[float, float]:
    """(length, width) of the minimum rotated rectangle round `poly`."""
    rect = poly.minimum_rotated_rectangle
    c = list(rect.exterior.coords)
    a, b = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    return (max(a, b), min(a, b))


#: raster step for the stem test (mm): the stem's loose ends sit on the mask's
#: edge, its long sides on the holes' own rings (restored by the vector band)
_STEP_MM = 0.05


def _sum_mask_polys(art: Polygon, hi: Polygon, hj: Polygon, limit: float) -> list[Polygon]:
    """The polygons of {p: d(p, hi) + d(p, hj) <= limit} over the band's box:
    across a stem of gap g between two faces the sum is g everywhere, wide
    black between letters reads more than `limit`."""
    import cv2
    import numpy as np
    x0, y0, x1, y1 = art.bounds
    n_x, n_y = int((x1 - x0) / _STEP_MM) + 3, int((y1 - y0) / _STEP_MM) + 3

    def px(pts):
        return np.array([[(x - x0) / _STEP_MM + 1, (y - y0) / _STEP_MM + 1] for x, y in pts], np.int32)

    def dist_to(h):
        m = np.full((n_y, n_x), 255, np.uint8)
        cv2.fillPoly(m, [px(h.exterior.coords)], 0)
        return cv2.distanceTransform(m, cv2.DIST_L2, 5) * _STEP_MM

    s = dist_to(hi) + dist_to(hj)
    m = (s <= limit).astype(np.uint8)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        pts = [((float(a) - 1) * _STEP_MM + x0, (float(b) - 1) * _STEP_MM + y0) for a, b in c[:, 0, :]]
        if len(pts) >= 3:
            g = Polygon(pts).buffer(0)
            if not g.is_empty:
                out += _parts(g)
    return out


def stem_pieces(art: Polygon, rings: list[tuple[Polygon, float]]) -> tuple[list[Polygon], Polygon, float]:
    """-> (stems, outer zone, band width). A stem is a piece of band whose two
    nearest faces stand less than two loop widths apart across it (the
    distance to one plus the distance to the other is under two widths), lies
    outside the zone the outer loop sews, and is at least two of its own
    widths long."""
    if len(rings) < 2:
        return [], Polygon(), 0.0
    w = max(float(width) for _h, width in rings)
    outer = LineString(list(art.exterior.coords)).buffer(w)
    near = [h.buffer(w) for h, _w in rings]
    shared = []
    for i in range(len(near)):
        for j in range(i + 1, len(near)):
            if not near[i].intersects(near[j]):
                continue
            for g in _sum_mask_polys(art, rings[i][0], rings[j][0], 2.0 * w):
                shared.append(g)
    if not shared:
        return [], outer, w
    s = unary_union(shared).intersection(art).difference(outer)
    # the opening drops the slivers where two hole buffers just touch
    s = s.buffer(-0.05).buffer(0.05)
    stems = []
    for part in _parts(s):
        length, width = _length_over_width(part)
        if width > 0 and length >= 2.0 * width:
            stems.append(part)
    return stems, outer, w


def _loops_exit(rings: list[tuple[Polygon, float]], entry):
    """Where the per-hole loops (`keyline_runs`, nearest loop first, each starting and
    ending at its own point nearest the needle) leave the needle after the last one."""
    cursor = entry
    todo = [h.exterior for h, _w in rings]
    while todo:
        if cursor is None:
            ring = todo.pop(0)
            cursor = ring.coords[0]
            continue
        here = Point(cursor)
        k = min(range(len(todo)), key=lambda j: (round(todo[j].distance(here), 6), j))
        ring = todo.pop(k)
        near = nearest_points(ring, here)[0]
        cursor = (near.x, near.y)
    return cursor


def _keep_out_of_faces(runs: list, faces, outer_line: LineString) -> int:
    """No stitch of the outer loop crosses a face: where one does (a cross grazing a face's
    corner), its far end -- the end further from the outer ring -- is pulled back to where
    the stitch first enters the face. -> stitches shortened."""
    from shapely.geometry import MultiPoint
    n = 0
    for r in runs:
        if r.kind != stitches.SATIN or not r.points:
            continue
        pts = list(r.points)
        for i in range(len(pts) - 1):
            seg = LineString([pts[i], pts[i + 1]])
            if not seg.intersects(faces):
                continue
            near, far = (i, i + 1) if outer_line.distance(Point(pts[i])) <= outer_line.distance(Point(pts[i + 1])) else (i + 1, i)
            hit = seg.intersection(faces)
            if hit.is_empty:
                continue
            cand = [Point(c) for g in getattr(hit, "geoms", [hit]) for c in g.coords]
            first = min(cand, key=lambda q: Point(pts[near]).distance(q))
            pts[far] = (first.x, first.y)
            n += 1
        r.points = pts
    return n


def _outer_centre(art: Polygon, w: float) -> LineString | None:
    """The outer loop's centre line: the outer ring moved in half a width."""
    inner = Polygon(art.exterior).buffer(-w / 2.0)
    parts = _parts(inner)
    if not parts:
        return None
    return LineString(list(max(parts, key=lambda g: g.area).exterior.coords))


def _guides(art: Polygon) -> list[LineString]:
    """Routes for the needle inside the band: the band moved in 0.35 mm, every ring of it
    (`travel_path` runs along one where a straight line would leave the band)."""
    out = []
    for part in _parts(art.buffer(-0.35)):
        out.append(LineString(list(part.exterior.coords)))
        out += [LineString(list(r.coords)) for r in part.interiors]
    return out


def _centre_walk(band: Polygon, centre: LineString | None, a, b):
    """A walk a -> b through the band under the outer loop: in to the loop's
    centre line, round it the short way, out again; None when a leg leaves the
    band or the walk is longer than max(20 mm, 4 x the direct distance) (the
    bound `stage6_border._bury_walks` keeps)."""
    if centre is None or centre.length <= 0:
        return None
    cover = band.buffer(0.01)
    pa, pb = Point(a), Point(b)
    ta, tb = centre.project(pa), centre.project(pb)
    ca, cb = centre.interpolate(ta), centre.interpolate(tb)
    if not (cover.covers(LineString([a, (ca.x, ca.y)])) and cover.covers(LineString([(cb.x, cb.y), b]))):
        return None
    lo, hi = sorted((ta, tb))
    short = substring(centre, lo, hi)
    other_len = centre.length - (hi - lo)
    if other_len < short.length:
        first, second = substring(centre, hi, centre.length), substring(centre, 0.0, lo)
        along = list(first.coords) + list(second.coords)
        if ta > tb:
            along = along[::-1]
    else:
        along = list(short.coords)
        if ta > tb:
            along = along[::-1]
    route = [a] + [(x, y) for x, y in along] + [b]
    length = sum(math.dist(route[i - 1], route[i]) for i in range(1, len(route)))
    if length > max(20.0, 4.0 * math.dist(a, b)):
        return None
    if not cover.covers(LineString(route)):
        return None                       # the centre line leaves the band where it is thin
    out, cur = [], a
    for pt in route[1:]:
        out.extend(_densify(cur, pt, machine.TRAVEL_STITCH_MM))
        cur = pt
    return out


def _hop(runs: list, new: list, cursor, band: Polygon, shape_id: str, trim_at_mm: float,
         centre: LineString | None = None, guides=None, sewn=None) -> int:
    """The needle's way to the first stitch of `new`: through the band where a
    route exists (`travel_path`), else a lift, cut past `trim_at_mm`, as
    `keyline_runs` leaves its own loops. -> lifts made."""
    if cursor is None or not new or not new[0].points:
        return 0
    to = new[0].points[0]
    d = math.dist(cursor, to)
    if d < machine.TINY_STITCH_MM:
        return 0
    bridge = _route(band, guides, centre, cursor, to, sewn)
    if bridge is None:
        new[0].jump = True
        new[0].trim = d > trim_at_mm
        return 1
    if len(bridge) > 1:
        runs.append(StitchRun(points=bridge[:-1], kind=stitches.TRAVEL, shape_id=shape_id))
    return 0


def _route(band: Polygon, guides, centre, a, b, sewn=None):
    """The needle's way a -> b inside the band: along the band (`travel_path` on `guides`),
    else round the outer loop's centre line; a route that runs over finished thread
    (`sewn`: the stems already sewn) for more than half a millimetre is no route."""
    for make in (lambda: travel_path(band, guides, a, b), lambda: _centre_walk(band, centre, a, b)):
        r = make()
        if r is None:
            continue
        if sewn is not None and len(r) > 1 and LineString(r).intersection(sewn).length > 0.5:
            continue
        return r
    return None


def _reroute(new: list, cursor, band: Polygon, shape_id: str, centre, guides, sewn=None) -> list:
    """`new` with every lift inside it (and the lift into it) walked through the band
    where a route exists (`_hop`), so the needle is cut only where none does."""
    out: list = []
    last = cursor
    for r in new:
        if not r.points:
            out.append(r)
            continue
        if last is not None and (r.jump or r.trim):
            d = math.dist(last, r.points[0])
            if d >= machine.TINY_STITCH_MM:
                bridge = _route(band, guides, centre, last, r.points[0], sewn)
                if bridge is not None:
                    if len(bridge) > 1:
                        out.append(StitchRun(points=bridge[:-1], kind=stitches.TRAVEL, shape_id=shape_id))
                    r.jump = r.trim = False
        out.append(r)
        last = r.points[-1]
    return out


def _split_at_gaps(runs: list, longest: float, trim_at_mm: float, shape_id: str,
                   band: Polygon, centre: LineString | None = None, guides=None) -> tuple[list, int]:
    """A loop clamped to `reach` keeps only the crosses that fit, and joins the
    arcs it keeps with a straight stitch across the gap. Each satin run is cut
    at every stitch longer than any cross (`longest`) into one run per arc,
    the needle walking through the band to the next arc (`_hop`: thread the
    stems and the outer loop sewn after cover), else lifting. -> (runs, lifts)."""
    out, lifts = [], 0
    for r in runs:
        pts = list(r.points or [])
        cuts = ([i + 1 for i in range(len(pts) - 1) if math.dist(pts[i], pts[i + 1]) > longest]
                if r.kind == stitches.SATIN and len(pts) >= 3 else [])
        if not cuts:
            out.append(r)
            continue
        prev = 0
        for n, c in enumerate(cuts + [len(pts)]):
            seg = pts[prev:c]
            prev = c
            if len(seg) < 2:
                continue
            piece = StitchRun(points=seg, kind=stitches.SATIN, shape_id=shape_id)
            if n == 0:
                piece.jump, piece.trim = r.jump, r.trim
            elif out and out[-1].points:
                lifts += _hop(out, [piece], out[-1].points[-1], band, shape_id, trim_at_mm, centre, guides)
            out.append(piece)
    return out, lifts


def one_band_runs(art: Polygon, rings: list[tuple[Polygon, float]], shape_id: str, *,
                  entry, trim_at_mm: float, underlay: bool, satin_kw: dict):
    """The band as stems, the hole loops that remain, and one outer loop.
    -> (runs, report); empty runs when the band has no stem to sew apart."""
    stems, outer, w = stem_pieces(art, rings)
    report = {"jumps": 0, "empty": True, "outline_loops": 0, "stems": 0}
    if not stems:
        return [], report
    runs = []
    cursor = entry
    centre = _outer_centre(art, w)
    guides = _guides(art)
    stem_union = unary_union(stems).buffer(1e-3)
    # the holes' own loops where the outer loop and the stems do not reach,
    # sewn FIRST so the walks between their arcs lie under what follows
    reach = art.difference(outer).difference(stem_union)
    if not reach.is_empty:
        h_runs, h_rep = keyline_runs(art, shape_id, reach=reach, entry=cursor, trim_at_mm=trim_at_mm,
                                     underlay=False, holes=list(rings), bridge_guides=guides)
        if not h_rep["empty"]:
            h_runs, lifts = _split_at_gaps(h_runs, w + 0.05, trim_at_mm, shape_id, art, centre, guides)
            runs += h_runs
            report["jumps"] += h_rep["jumps"] + lifts
            report["outline_loops"] += h_rep["loops"]
            cursor = runs[-1].points[-1]
    # the stems, each a satin column of its own: the outer loop covers the top of each
    sewn = None
    todo = sorted(stems, key=lambda g: (round(g.centroid.y, 3), round(g.centroid.x, 3)))
    while todo:
        if cursor is None:
            piece = todo.pop(0)
        else:
            here = Point(cursor)
            piece = min(todo, key=lambda g: (round(g.distance(here), 6), todo.index(g)))
            todo.remove(piece)
        _l, width = _length_over_width(piece)
        s_runs, s_rep = satin_shape(piece, shape_id, start_near=cursor,
                                    max_width_mm=max(machine.SATIN_MAX_WIDTH_MM, 1.5 * width),
                                    **satin_kw)
        if s_rep.get("empty") or not s_runs:
            return [], report                     # a stem the satin cannot sew: keep the loops
        s_runs = _reroute(s_runs, cursor, art, shape_id, centre, guides, sewn)
        report["jumps"] += _hop(runs, s_runs, cursor, art, shape_id, trim_at_mm, centre, guides, sewn)
        runs += s_runs
        sewn = piece.buffer(0.05) if sewn is None else sewn.union(piece.buffer(0.05))
        report["stems"] += 1
        cursor = runs[-1].points[-1]
    # ... and the one band on the outer ring, last
    ext = Polygon(art.exterior)
    # The band ends where the loops it replaces would have ended, so what is sewn after the
    # outline (the next shape's entry, and the order it picks its neighbours in) is the order
    # it was: the loop is entered there and the needle's way to it is walked first.
    seed = _loops_exit(rings, entry) or cursor
    o_runs, o_rep = keyline_runs(art, shape_id, reach=art.difference(stem_union), entry=seed,
                                 trim_at_mm=trim_at_mm, underlay=underlay,
                                 holes=[(ext, w)], bridge_guides=guides)
    if o_rep["empty"]:
        return [], report
    _keep_out_of_faces(o_runs, unary_union([h for h, _w in rings]).buffer(-0.0005),
                       LineString(list(art.exterior.coords)))
    o_runs = _reroute(o_runs, cursor, art, shape_id, centre, guides, sewn)
    report["jumps"] += _hop(runs, o_runs, cursor, art, shape_id, trim_at_mm, centre, guides, sewn)
    runs += o_runs
    report["jumps"] += o_rep["jumps"]
    report["outline_loops"] += o_rep["loops"]
    report["empty"] = False
    return runs, report
