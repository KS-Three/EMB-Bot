"""Two shapes of one ink touching at a point are two shapes (2026-11-14, built OFF).

NSYNC's logo at 70.9 mm on a beanie (eye sweep 2026-11-14, fault 11): the
star's right arm tip touches the italic N's left edge at a single point,
a neck of one or two source pixels (about 0.05 mm at 26.7 px/mm). The
star and the N are one navy, so stage 4 traces them as ONE region, and the
column build on that region fans the N's top-left into loose satin spikes
where the star hangs off it. Nothing upstream parts them: the text
tagger's neck split (`textcluster._neck_splits`) only looks at a region
beside a line of letters in the same ink, and the N's ink is not SYNC's.

`cfg.point_touch_split` (ON since 2026-11-15, Kent 2026-11-15, review pack
(review-1115): ticked ON; built OFF as `cfg.extra["point_touch_split"]`): a
region narrower at a neck
than `textcluster.TOUCH_MAX_MM` (0.15 mm, the tagger's own "two letters
touching" bound) is cut there into the pieces the tagger's stroke rule
would cut it into, when both cuts agree -- the same test `_neck_splits`
applies to touching letters, here for any body of any ink. Each piece
keeps the region's thread, layer and meta and gets its own shape id.
False, nothing runs: the engine is byte-identical. Flat logos only: the
pipeline calls it on the "flat" class alone (2026-11-15: on MFab hat, classed
`photo_scene`, it cut WELDING's W into a "~", and it moved every corpus photo
it was run on, a photo's quantised blobs pinching everywhere; on the
`drone_render` fixture, a gradient render, it cut a shading blend off a field
that then read as one more blocking thread mismatch).
"""
from __future__ import annotations

import copy

from .regions import _raw_id
from .textcluster import TOUCH_MAX_MM

# Only bodies: a band (mean width at most this, mm) is a line, and lines
# touch at their joins on purpose (a script's connected strokes).
TOUCH_BODY_MIN_WIDTH_MM = 0.8

TOUCH_PROTECT_KEYS = ("rescued_small_shape", "enclosed_background", "counter", "dark_ink",
                "text_cluster_id")
# A piece must be a body in its own right (not a serif or a spike): mean
# width over `TOUCH_BODY_MIN_WIDTH_MM` and at least this area. The tagger's own
# floor is a share of the letter (`NECK_PART_MIN_FRAC` 0.15), which NSYNC's
# star misses at 13% of star + N; here any shape is in play, so the floor is
# the piece's own size.
TOUCH_PIECE_MIN_MM2 = 2.0
# The neck the opening removes may be at most this share of the region (the
# tagger's `NECK_MAX_AREA_FRAC`): a pinch, not a waist.
TOUCH_NECK_MAX_FRAC = 0.05


def _touch_split(poly):
    """`poly` cut where it pinches under `TOUCH_MAX_MM` into pieces that tile
    it, each a body (module note); None when there is no such pinch."""
    from shapely.ops import unary_union
    r = TOUCH_MAX_MM / 2.0
    try:
        opened = poly.buffer(-r).buffer(r).intersection(poly)
    except Exception:                                    # noqa: BLE001 -- fail open
        return None
    geoms = [q for q in getattr(opened, "geoms", [opened]) if q.geom_type == "Polygon"]
    parts = [q for q in geoms if q.area >= TOUCH_PIECE_MIN_MM2 and q.length > 0
             and 2.0 * q.area / q.length > TOUCH_BODY_MIN_WIDTH_MM]
    if len(parts) < 2:
        return None
    parts.sort(key=lambda q: (round(q.bounds[0], 6), round(q.bounds[1], 6)))
    rest = poly.difference(unary_union(parts))
    owned = [[q] for q in parts]
    neck = 0.0
    for piece in getattr(rest, "geoms", [rest]):
        if piece.is_empty or piece.geom_type != "Polygon":
            continue
        shared = [piece.boundary.intersection(q.buffer(1e-6)).length for q in parts]
        if sum(1 for s in shared if s > 1e-6) >= 2:
            neck += piece.area
        best = max(range(len(parts)), key=lambda i: (shared[i], -piece.distance(parts[i])))
        owned[best].append(piece)
    if neck > TOUCH_NECK_MAX_FRAC * poly.area:
        return None
    out = [unary_union(g) for g in owned]
    if any(q.geom_type != "Polygon" or q.is_empty for q in out):
        return None
    if abs(sum(q.area for q in out) - poly.area) > 1e-6 * max(1.0, poly.area):
        return None
    return out


def apply_point_touch_split(regions) -> list[dict]:
    """Cut every region touching itself at a point (module note). Mutates
    `regions` in place; -> one row per cut."""
    rows = []
    out = []
    for r in regions:
        g = r.polygon
        m = r.meta or {}
        if (g.geom_type != "Polygon" or g.is_empty or g.length <= 0
                or any(m.get(k) for k in TOUCH_PROTECT_KEYS)):
            out.append(r)
            continue
        width = 2.0 * g.area / g.length
        if width <= TOUCH_BODY_MIN_WIDTH_MM:
            out.append(r)
            continue
        polys = _touch_split(g)
        if polys is None:
            out.append(r)
            continue
        ids = []
        for k, q in enumerate(polys):
            piece = copy.deepcopy(r)
            piece.polygon = q
            piece.area_mm2 = float(q.area)
            c = q.representative_point()
            piece.shape_id = _raw_id(c.x, c.y, r.thread_number) + (f"-pt{k}" if k else "")
            piece.meta["point_touch_split_from"] = r.shape_id
            ids.append(piece.shape_id)
            out.append(piece)
        rows.append({"shape_id": r.shape_id, "thread": r.thread_number, "pieces": ids,
                     "areas_mm2": [round(q.area, 2) for q in polys]})
    regions[:] = out
    return rows
