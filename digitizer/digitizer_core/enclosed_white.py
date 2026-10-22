"""Sew the white inside the design (`cfg.sew_enclosed_white`, built OFF).

The professional sews the white or hollow areas INSIDE a design instead of
leaving them as fabric, on 5 of the 11 jobs in Kent's zip
(`docs/pro-digitizer-rules-2026-10-21.md`, rule R11): the badge fields of
To a T Machine (and Fremont, which our gradient lane already sews), the
hollow BECKER letters (filled grey inside a black keyline), Golden Tee's
white GT and ball arc, MFab's white letters and keyline. Our engine leaves
every such area unstitched (`enclosed_background`, the 2026-08-15 verdict)
unless the garment rule (`cfg.enclosed_by_garment`) sees a clearly
different garment. That changes the design, so it is the CUSTOMER's option,
never a default.

Which enclosed areas sew. Every `enclosed_background` region is one of:

  * a COUNTER -- the gap inside a letter (the A of MARINE): the region is
    not itself lettering, and the shape whose hole holds it is a text-cluster
    letter (`text_candidate`, or the L1 word under `cfg.lettering_words`), or
    `keep_counters` already called it one (`meta["counter"]`). A counter
    stays open unless `cfg.sew_enclosed_counters` -- or it sits inside a
    field that sews (the counters of the letters on Machine's badge), since a
    hole through a sewn field would show the garment through it.
  * anything else -- a FIELD (a badge, a keyline band) or a hollow letter's
    body (BECKER's interiors are themselves tagged lettering, inside an
    untagged keyline). These sew.

The house-angle group (`lettering_group`) does not make a shape a letter
here: it tags drawing fragments as well (`columns.is_lettering`'s icon
guard), and it tagged Golden Tee's ball-arc outline, whose white crescent
the pro sews as a band.

Thread. `cfg.sew_enclosed_rgb` given: the chart's nearest thread to it, for
every area. None: a hole whose colour is known keeps the thread it carries
(the artwork's own background colour), and an alpha hole, whose colour
nobody knows (`enclosed_colour_unknown`: Becker's interiors carry the ring's
black), takes white. A review recolour of one shape (`shape_overrides
thread_index`) still wins, and so does a review `stitched`.

Order. The areas this sews go in a layer of their own at the FRONT of the
sew order, one per thread: the pro sews the big fill first and its outline on
top (rule R13, Becker's BEC fill then BEC outline), and a repeated cone is
how he keeps that order (rule R12).
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from .threads import rgb_to_lab

#: share of an area's own exterior a hole must cover to be the hole that
#: holds it -- the shapes are vectorized separately, so their edges disagree
#: by simplification wobble, never by a fifth of the area.
HOLD_FRAC = 0.8
#: tolerance, mm, on the hole's ring for that test.
HOLD_PAD_MM = 0.3
WHITE = (255, 255, 255)


def _is_letter(r, cfg) -> bool:
    m = r.meta or {}
    if getattr(cfg, "lettering_words", False):
        return bool(m.get("word_id"))
    return bool(m.get("text_candidate"))


def _encloser(e, regions):
    """The region whose hole holds `e` most tightly (smallest such hole),
    or None."""
    ext = Polygon(e.polygon.exterior)
    if ext.area <= 0:
        return None
    ex0, ey0, ex1, ey1 = ext.bounds
    best, best_area = None, None
    for o in regions:
        if o is e or not o.polygon.interiors:
            continue
        ox0, oy0, ox1, oy1 = o.polygon.bounds
        if ox0 > ex0 + HOLD_PAD_MM or oy0 > ey0 + HOLD_PAD_MM \
                or ox1 < ex1 - HOLD_PAD_MM or oy1 < ey1 - HOLD_PAD_MM:
            continue
        for ring in o.polygon.interiors:
            hole = Polygon(ring)
            if hole.area <= 0 or (best_area is not None and hole.area >= best_area):
                continue
            if hole.buffer(HOLD_PAD_MM).intersection(ext).area >= HOLD_FRAC * ext.area:
                best, best_area = o, hole.area
    return best


def plan_enclosed_white(regions, cfg) -> dict[str, str]:
    """-> {shape_id: "field" | "counter" | "counter_in_field"} for every
    `enclosed_background` region this option SEWS (counters left open are
    absent). Pure: reads geometry and tags, writes nothing."""
    enclosed = [r for r in regions if r.meta.get("enclosed_background")]
    if not enclosed:
        return {}
    kind = {}
    for e in enclosed:
        if e.meta.get("counter"):
            kind[e.shape_id] = "counter"
            continue
        holder = None if _is_letter(e, cfg) else _encloser(e, regions)
        kind[e.shape_id] = ("counter" if holder is not None and _is_letter(holder, cfg)
                            else "field")
    fields = [Polygon(e.polygon.exterior) for e in enclosed if kind[e.shape_id] == "field"]
    out = {}
    for e in enclosed:
        k = kind[e.shape_id]
        if k == "counter":
            if cfg.sew_enclosed_counters:
                out[e.shape_id] = "counter"
            elif any(f.contains(e.polygon.representative_point()) for f in fields):
                out[e.shape_id] = "counter_in_field"
        else:
            out[e.shape_id] = k
    return out


def apply_enclosed_white(regions, thread_indices: list[int], cfg, chart,
                         shape_overrides: dict | None = None) -> tuple[list[int], int]:
    """Mark, recolour and re-layer the areas `plan_enclosed_white` sews.
    -> (thread indices with the new front layers, how many areas sew).

    Sets `meta["sew_enclosed_white"]` (the plan's kind) on each; the caller's
    stitched default reads it. Runs after the review edits and before
    `compact_layers`, which drops any layer this empties."""
    plan = plan_enclosed_white(regions, cfg)
    if not plan:
        return list(thread_indices), 0
    overrides = shape_overrides or {}
    chosen = None
    if cfg.sew_enclosed_rgb is not None:
        chosen = chart.nearest_index(rgb_to_lab(np.array([cfg.sew_enclosed_rgb], dtype=np.float64))[0])
    white = chart.nearest_index(rgb_to_lab(np.array([WHITE], dtype=np.float64))[0])
    sewn = []
    for r in regions:
        k = plan.get(r.shape_id)
        if k is None:
            continue
        ov = overrides.get(r.shape_id) or {}
        if ov.get("stitched") is False:
            continue
        r.meta["sew_enclosed_white"] = k
        if ov.get("thread_index") is None:
            t = chosen if chosen is not None else (
                white if r.meta.get("enclosed_colour_unknown") else r.thread_index)
            r.thread_index = int(t)
            r.thread_number = chart[int(t)].number
        sewn.append(r)
    if not sewn:
        return list(thread_indices), 0
    # One front layer per thread, in the order the threads first appear (the
    # regions' own order, so the layer list is deterministic).
    front: list[int] = []
    for r in sewn:
        if r.thread_index not in front:
            front.append(r.thread_index)
    k = len(front)
    ids = {r.shape_id for r in sewn}
    for r in regions:
        if r.shape_id in ids:
            r.meta["layer"] = front.index(r.thread_index)
        else:
            r.meta["layer"] = int(r.meta["layer"]) + k
    return front + [int(t) for t in thread_indices], len(sewn)
