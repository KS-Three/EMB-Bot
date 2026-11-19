"""A strip between two holes of an outline band sewn ONCE, as a full-width column
(`cfg.outline_strip_column`, built OFF 2026-11-19).

`border_from_outline` sews an art outline as one satin loop round each hole it
holds (`stage6_border.keyline_runs`). Where the band between two holes (or the
two sides of one hole round a slot) is narrower than two loop widths, BOTH loop
sides cover it: on MFab's white top line the F's arm, the B's slots and the dash
get two 1.88 mm loop sides offset across a ~3 mm strip, each loop pivoting on
the strip's corners (12 crosses of one loop through one point at the F arm, 15
layers where the professional has 8; `docs/mfab-junction-census-2026-11-19.md`).

The professional's MFab file sews each such strip once, as one straight column
the full width of the strip (F arm 3.80 mm, B slots 2.83 mm), its crosses square
across it, and his loops pass its ends. Here, for an outline with two or more
holes:

  * a STRIP is a piece of band whose medial axis has both feet on hole rings
    (not on the outer edge) and a half-width up to one loop width, at least one
    loop width across (a hairline stem between two letters, BECKER's 0.55-1.1 mm,
    is left to the loops), at least two of its own widths long and close to a
    rectangle (its area at least `RECT_FILL` of its minimum rotated rectangle:
    a branched or bent strip is left to the loops);
  * each hole keeps its loop, its crosses stopping `SPLIT_LAP_MM` inside the
    strips (`keyline_runs` with the strips taken out of its reach), sewn first,
    so a loop's run along a strip edge lies under the column;
  * then each strip is one satin column (`stage6_satin.satin_shape`) laid over
    the loops' ends, the needle walking to it through the band where it can
    (`outline_band._hop`), else lifting.

No physical constant: the width is the outline's own, the lap is the one
`outline_loop_split_shared` uses. An outline with no such strip returns nothing
and the caller sews its loops as before.
"""
from __future__ import annotations


import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from . import machine
from .outline_band import _guides, _hop, _length_over_width, _outer_centre, _parts
from .stage6_border import SPLIT_LAP_MM, keyline_runs
from .stage6_satin import satin_shape

#: raster step of the strip test (mm)
_STEP_MM = 0.05
#: a strip is close to a rectangle: its area over its minimum rotated
#: rectangle's (a geometric test, not a thread figure)
RECT_FILL = 0.8


def strip_pieces(art: Polygon, rings) -> list[Polygon]:
    """The band's strips between holes (module notes). `rings` is
    [(hole polygon, loop width, ...)]."""
    import cv2
    from .fast_skimage import medial_axis
    if len(art.interiors) < 1 or not rings:
        return []
    w = max(float(r[1]) for r in rings)
    x0, y0, x1, y1 = art.bounds
    nx, ny = int((x1 - x0) / _STEP_MM) + 3, int((y1 - y0) / _STEP_MM) + 3

    def px(pts):
        return np.array([[(x - x0) / _STEP_MM + 1, (y - y0) / _STEP_MM + 1] for x, y in pts],
                        np.int32)
    band = np.zeros((ny, nx), np.uint8)
    cv2.fillPoly(band, [px(art.exterior.coords)], 1)
    for h in art.interiors:
        cv2.fillPoly(band, [px(h.coords)], 0)
    edge = np.full((ny, nx), 255, np.uint8)
    cv2.polylines(edge, [px(art.exterior.coords)], True, 0, 1)
    d_outer = cv2.distanceTransform(edge, cv2.DIST_L2, 5) * _STEP_MM
    # seeded: an unseeded call breaks ties from OS entropy (test_every_engine_medial_axis_call_is_seeded)
    skel, dist = medial_axis(band.astype(bool), return_distance=True, rng=0)
    r = dist * _STEP_MM
    # both feet on holes: the outer edge is farther than the inscribed radius
    keep = (skel & (r <= w) & (r >= w / 2.0) & (d_outer > r + 2 * _STEP_MM)).astype(np.uint8)
    def swept(mask) -> list[Polygon]:
        disk = np.zeros_like(band)
        for y, x in zip(*np.nonzero(mask)):
            cv2.circle(disk, (int(x), int(y)), int(round(r[y, x] / _STEP_MM)) + 1, 1, -1)
        disk &= band
        cnts, _ = cv2.findContours(disk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        polys = []
        for c in cnts:
            pts = [((float(a) - 1) * _STEP_MM + x0, (float(b) - 1) * _STEP_MM + y0)
                   for a, b in c[:, 0, :]]
            if len(pts) >= 3:
                polys += _parts(Polygon(pts).buffer(0).intersection(art)
                                .buffer(-_STEP_MM).buffer(_STEP_MM))
        return polys

    def straight(g) -> bool:
        length, width = _length_over_width(g)
        return (width >= w and length >= 2.0 * width
                and g.area >= RECT_FILL * g.minimum_rotated_rectangle.area)

    out = []
    n_axis, axis = cv2.connectedComponents(keep, connectivity=8)
    for k in range(1, n_axis):
        one = (axis == k).astype(np.uint8)
        whole = swept(one)
        if whole and all(straight(g) for g in whole):
            out += whole
            continue
        # a strip that is not one straight column (a slot meeting a leg, a
        # stem meeting a bar) is tested BRANCH by branch of its axis, the
        # forks cut out; each straight branch is a column of its own
        nb = cv2.filter2D(one, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT)
        forks = cv2.dilate(((nb >= 4) & (one > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
        n_br, br = cv2.connectedComponents((one & (1 - forks)).astype(np.uint8), connectivity=8)
        taken = unary_union(out) if out else Polygon()
        for j in range(1, n_br):
            for g in swept((br == j).astype(np.uint8)):
                for piece in _parts(g.difference(taken)):
                    if straight(piece):
                        out.append(piece)
                        taken = taken.union(piece)
    return out


def strip_column_runs(art: Polygon, rings, shape_id: str, *, reach, entry, trim_at_mm: float,
                      underlay: bool, satin_kw: dict, loop_kw: dict):
    """The hole loops cut at the strips, then a column per strip.
    -> (runs, report); empty runs when the band has no strip."""
    report = {"jumps": 0, "empty": True, "loops": 0, "strips": 0}
    if len(rings) < 1:
        return [], report
    strips = strip_pieces(art, rings)
    if not strips:
        return [], report
    cut = unary_union(strips).buffer(-SPLIT_LAP_MM)
    l_reach = reach.difference(cut) if not cut.is_empty else reach
    w = max(float(r[1]) for r in rings)
    centre, guides = _outer_centre(art, w), _guides(art)
    # the loops first, every ring in one call (`split_shared` reads them all);
    # then the columns over their ends. Measured 2026-11-19: one nearest-first
    # walk over loops and columns together cost MORE cuts on MFab (+5, not +4)
    # and lost the F arm's gain, so the columns go last.
    runs, l_rep = keyline_runs(art, shape_id, reach=l_reach, entry=entry,
                               trim_at_mm=trim_at_mm, underlay=underlay, holes=list(rings),
                               **loop_kw)
    if l_rep["empty"]:
        return [], report
    report["jumps"] += l_rep["jumps"]
    report["loops"] = l_rep["loops"]
    cursor = runs[-1].points[-1]
    todo = list(strips)
    while todo:
        here = Point(cursor)
        piece = min(todo, key=lambda g: (round(g.distance(here), 6), todo.index(g)))
        todo.remove(piece)
        _l, width = _length_over_width(piece)
        # the column reaches `SPLIT_LAP_MM` past the strip, over the loops'
        # rail stitch along each hole edge, as a loop's cross laps a neighbour
        sew = piece.buffer(SPLIT_LAP_MM, join_style=2)
        s_runs, s_rep = satin_shape(sew, shape_id, start_near=cursor,
                                    max_width_mm=max(machine.SATIN_MAX_WIDTH_MM, 1.5 * width),
                                    **satin_kw)
        if s_rep.get("empty") or not s_runs:
            return [], {"jumps": 0, "empty": True, "loops": 0, "strips": 0}
        report["jumps"] += _hop(runs, s_runs, cursor, art, shape_id, trim_at_mm, centre, guides)
        report["jumps"] += int(s_rep.get("jumps", 0))
        runs += s_runs
        report["strips"] += 1
        cursor = runs[-1].points[-1]
    report["empty"] = False
    return runs, report


def strip_summary(art: Polygon, rings) -> list[dict]:
    """The strips as numbers (tests, evidence): area, length, width, centre."""
    out = []
    for g in strip_pieces(art, rings):
        length, width = _length_over_width(g)
        c = g.centroid
        out.append({"area": round(g.area, 2), "length": round(length, 2),
                    "width": round(width, 2), "at": (round(c.x, 2), round(c.y, 2)),
                    "fill": round(g.area / max(1e-9, g.minimum_rotated_rectangle.area), 2)})
    return out


__all__ = ["strip_pieces", "strip_column_runs", "strip_summary", "RECT_FILL"]
