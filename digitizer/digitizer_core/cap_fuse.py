"""`cfg.color_cap_fuse_split_tones`: a letter the palette cut in two tones, fused after the cap.

Precision Drone (2026-11-18, the prime grader's scorecard: "THERMAL is mushed
in the middle: the E-R pair piles up"). The orange word is a gradient, and
stage 2-4 cut some of its letters across the middle into a light band (thread
0700) and a deep band (0824). The colour cap then folded BOTH onto the one
orange spool (1305) and left two overlapping shapes on two layers. Nothing
unions them afterwards, so the E and the R each sew as two shapes, each with
its own angle, neither read as a whole letter by the lettering tagger (T and H,
already 1305 and whole, are tagged and sew as clean columns).

ON, this runs right after the cap and before text detection: two regions the
cap re-threaded from DIFFERENT original threads onto the SAME thread, sharing a
seam or overlapping, become one polygon (the larger keeps its identity), so
every later stage sees the whole letter. Only cap-moved pairs: a shape that was
already one thread is never touched, and a union that is not a single polygon
is refused. Geometry only; no fabric constant (gate 1 does not apply).
"""
from __future__ import annotations

from shapely.ops import unary_union

#: Seam (mm) two halves must share, or overlap across, to be one letter.
MIN_SEAM_MM = 1.0


def _poly(r) -> bool:
    g = r.polygon
    return g.geom_type == "Polygon" and g.is_valid and not g.is_empty


def apply(regions, touch_mm: float = 0.05) -> dict:
    """Mutates `regions`; -> {"fused": [[kept id, absorbed ids...]], "removed": n}."""
    report: dict = {"fused": [], "removed": 0}
    seeds = [i for i, r in enumerate(regions)
             if r.meta.get("color_cap_merged_from") and _poly(r)]
    parent = {i: i for i in seeds}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for ai, a in enumerate(seeds):
        ra = regions[a]
        for b in seeds[ai + 1:]:
            rb = regions[b]
            if ra.thread_index != rb.thread_index:
                continue
            if ra.meta["color_cap_merged_from"] == rb.meta["color_cap_merged_from"]:
                continue                       # one tone twice is not a split tone
            ga, gb = ra.polygon, rb.polygon
            if ga.distance(gb) > touch_mm:
                continue
            # the length of each outline lying against (or inside) the other
            seam = min(ga.boundary.intersection(gb.buffer(touch_mm)).length,
                       gb.boundary.intersection(ga.buffer(touch_mm)).length)
            if seam >= MIN_SEAM_MM:
                parent[find(a)] = find(b)
    groups: dict[int, list[int]] = {}
    for i in seeds:
        groups.setdefault(find(i), []).append(i)
    removed: list[int] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda k: (-regions[k].polygon.area, regions[k].shape_id))
        g = unary_union([regions[k].polygon.buffer(touch_mm, join_style=2) for k in members]
                        ).buffer(-touch_mm, join_style=2)
        if g.geom_type != "Polygon" or not g.is_valid or g.is_empty:
            continue
        keep = regions[members[0]]
        keep.polygon = g
        keep.area_mm2 = float(g.area)
        keep.meta.setdefault("cap_fused", []).extend(regions[k].shape_id for k in members[1:])
        report["fused"].append([keep.shape_id] + [regions[k].shape_id for k in members[1:]])
        removed.extend(members[1:])
    for k in sorted(removed, reverse=True):
        del regions[k]
    report["removed"] = len(removed)
    return report
