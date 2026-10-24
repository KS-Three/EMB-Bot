"""The art's own outline (`cfg.border_from_outline`, built OFF 2026-10-24).

The pro's border choice is not a stroke threshold (#1043 census, #1052):
MARINE and MFAB carry the same stroke and he satins one and borders the
other. What his bordered shapes share is an OUTLINE IN THE ART -- a thin
band of another colour drawn round the shape -- and his border is that
outline, sewn as one satin loop at 2.0-2.5 mm on top of the shape's fill:
BECKER's white faces inside their black keyline, MFab's black M-FAB inside
its white keyline, Hotel Fremont's two discs inside their black rings.

An outline here is a region O with a hole that holds a BODY B:

  * B lies in the hole (`HOLD_FRAC` of its exterior, within `HOLD_PAD_MM`)
    and meets the hole's ring along `TOUCH_FRAC` of its edge, and the shapes
    that do fill at least `FILL_FRAC` of the hole -- so a letter's counter
    sitting inside a face is not a body of the face's keyline, and MFab's
    F and hyphen, touching in one hole, are both bodies;
  * B is not a COUNTER: not tagged `counter`, and not an enclosed
    background area held by a letter (`enclosed_white`'s own rule) -- the
    gap inside a satin O is not a shape the pro borders;
  * B is wider than its outline is thick: B's stroke (2 x area / perimeter)
    is at least `machine.OUTLINE_BODY_RATIO` x the outline's band round it
    (O's area within `machine.OUTLINE_PROBE_MM` of B, per mm of B's edge).
    Measured on the census cache (`tools/outline_census.py`): BECKER's faces
    read 1.34-2.30, MFab's big letters 1.65-3.14, Fremont's discs 2.89; a
    satin letter's counter, MFab's AND WELDING LLC inside the same keyline
    (0.50-0.87, sewn satin by the pro) and every letter in Fremont's white
    field (0.03-0.55) fall under it.

The hole ring must be a loop the border tier would sew
(`machine.BORDER_MIN_LOOP_MM`). Pure: reads geometry and tags.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon

from . import machine
from .columns import is_lettering

#: share of a body's exterior that must lie in the hole (the shapes are
#: vectorized separately; their edges disagree by simplification wobble).
HOLD_FRAC = 0.8
HOLD_PAD_MM = 0.3
#: share of the hole's area its bodies together must cover (MFab's F and
#: hyphen touch, and share one keyline hole).
FILL_FRAC = 0.5
#: share of a body's own edge that must run along the hole's ring: a letter's
#: counter inside a face is in the hole but never meets it.
TOUCH_FRAC = 0.25


def _counter(body, holder, cfg) -> bool:
    m = body.meta or {}
    return bool(m.get("counter")) or (bool(m.get("enclosed_background"))
                                      and is_lettering(holder, cfg))


def outline_measures(holder, body, hole: Polygon) -> tuple[float, float]:
    """(band, stroke) mm: the outline's thickness round `body` and the
    body's own stroke."""
    ext = Polygon(body.polygon.exterior)
    band = holder.polygon.intersection(ext.buffer(machine.OUTLINE_PROBE_MM)).area
    band /= max(ext.exterior.length, 1e-9)
    stroke = 2.0 * body.polygon.area / max(body.polygon.length, 1e-9)
    return band, stroke


def find_art_outlines(regions, cfg=None) -> dict[str, list[tuple[str, Polygon]]]:
    """-> {outline shape_id: [(body shape_id, hole polygon), ...]} for every
    region whose hole holds a body under the rule above, bodies in input
    order. A body has at most one outline (the first holder that reads)."""
    regions = list(regions)
    out: dict[str, list[tuple[str, Polygon]]] = {}
    taken: set[str] = set()
    for o in regions:
        poly = o.polygon
        if poly is None or poly.is_empty or poly.geom_type != "Polygon" or not poly.interiors:
            continue
        holes = [Polygon(r) for r in poly.interiors
                 if LineString(r.coords).length >= machine.BORDER_MIN_LOOP_MM]
        if not holes:
            continue
        ox0, oy0, ox1, oy1 = poly.bounds
        inside = []
        for b in regions:
            if (b is o or b.shape_id in taken or b.polygon is None or b.polygon.is_empty
                    or b.polygon.geom_type != "Polygon"):
                continue
            bx0, by0, bx1, by1 = b.polygon.bounds
            if bx0 < ox0 or by0 < oy0 or bx1 > ox1 or by1 > oy1:
                continue
            inside.append(b)
        for hole in holes:
            ring = hole.exterior.buffer(HOLD_PAD_MM)
            pad = hole.buffer(HOLD_PAD_MM)
            held = []
            for b in inside:
                ext = Polygon(b.polygon.exterior)
                if ext.area <= 0 or pad.intersection(ext).area < HOLD_FRAC * ext.area:
                    continue
                if b.polygon.exterior.intersection(ring).length < TOUCH_FRAC * b.polygon.exterior.length:
                    continue
                held.append((b, ext))
            if sum(ext.area for _b, ext in held) < FILL_FRAC * hole.area:
                continue
            for b, _ext in held:
                if b.shape_id in taken or _counter(b, o, cfg):
                    continue
                band, stroke = outline_measures(o, b, hole)
                if stroke < machine.OUTLINE_BODY_RATIO * band:
                    continue
                out.setdefault(o.shape_id, []).append((b.shape_id, hole))
                taken.add(b.shape_id)
    return out


def outline_width_mm(body) -> float:
    """The pro's border width for an outlined body, by its smallest
    dimension (`machine.OUTLINE_WIDTH_MM`, widest band first)."""
    from .stage7_sequence import _min_dim_mm
    d = _min_dim_mm(body.polygon)
    for floor, width in machine.OUTLINE_WIDTH_MM:
        if d >= floor:
            return width
    return machine.OUTLINE_WIDTH_MM[-1][1]
