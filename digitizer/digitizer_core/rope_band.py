"""Sew a twisted rope border as ONE band (`cfg.rope_band`, built OFF 2026-11-17).

**Why.** Hotel Fremont's hexagon carries a twisted rope of tan strands. The art
draws ~100 separate strand blobs, each ~2.3 x 1.2 mm and ~1.1 mm^2 -- under the
detail floor -- so stage 4 rescues every one (`rescued_small_shape`) and stage 7
sews each as its own run-stitch loop: the prime grader's "row of thin
running-stitch ticks ... a faint zigzag instead of a rope" (scorecard
2026-11-17, pin x 30.0 y 9.5 mm). The professional's file does not draw the
twist at all: his rope is one plain tan satin band round the hexagon
(`docs/renders/rope-band-2026-11-17/`).

**What this does.** After stage 5 (and `fragment_absorb`), on the planned
regions: a chain of same-thread, sub-floor, rescued strands -- each within
`ROPE_LINK_MM` of the next, not lettering (no text cluster), at least
`MIN_STRANDS` of them and `MIN_SPAN_MM` long -- is replaced by ONE region
whose polygon is the chain closed over its gaps (`buffer(+r).buffer(-r)`,
pockets under `MAX_POCKET_MM2` filled). It is a long band about as wide as one
strand, so stage 7's ordinary ladder sews it as a satin column. Nothing is
dropped: every strand's area is inside the band.

A text cluster's glyph pieces (`text_cluster_id`), and a chain too short or too
few (a single letter's rescued specks), are never touched.

ON by default since 2026-11-17 (Kent: "Flip ON (Recommended)"); off it returns
its input, so the plan is byte-identical to the engine as it was. Not
a physical constant: the numbers are read from the art's geometry (strand
gaps 0.0-0.3 mm in the Fremont plan) and the choice of one band over a drawn
twist is LAYOUT, judged from renders.
"""
from __future__ import annotations

import dataclasses

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

KEY = "rope_band"
ROPE_LINK_MM = 0.5          # strands this near are one chain (art gaps 0.0-0.3 mm)
MIN_STRANDS = 8        # a letter's rescued specks are never this many in a row
MIN_SPAN_MM = 12.0     # ... nor this long
MAX_STRAND_MM2 = 3.0   # a strand blob; a glyph piece is larger (6-8 mm^2 in Fremont)
MAX_POCKET_MM2 = 0.6   # a hole the closing leaves between strands is not a hole

_LETTER_KEYS = ("text_cluster_id", "word_id", "bean_letter", "small_text_stray", "detail_spokes")
#: what describes ONE strand (its bean spines, its measured width) and not the band
_STRAND_KEYS = ("rescued_small_shape", "lettering_group", "dark_ink_floor_rescued", "bean_letter_spines",
                "stitch_width_measured_mm", "stitch_width_pull_mm", "stitch_width_source")


def enabled(cfg) -> bool:
    return bool((getattr(cfg, "extra", None) or {}).get(KEY, getattr(cfg, "rope_band", False)))


def _strand(p) -> bool:
    r = p.region
    m = r.meta or {}
    return (bool(m.get("rescued_small_shape")) and not any(m.get(k) for k in _LETTER_KEYS)
            and not r.polygon.is_empty and r.polygon.area <= MAX_STRAND_MM2)


def _chains(polys: list) -> list[list[int]]:
    """Connected components of `polys` under distance <= ROPE_LINK_MM."""
    n = len(polys)
    seen, out = [False] * n, []
    for s in range(n):
        if seen[s]:
            continue
        seen[s], comp, stack = True, [], [s]
        while stack:
            i = stack.pop()
            comp.append(i)
            for j in range(n):
                if not seen[j] and polys[i].distance(polys[j]) <= ROPE_LINK_MM:
                    seen[j] = True
                    stack.append(j)
        out.append(comp)
    return out


def _span(geom) -> float:
    x0, y0, x1, y1 = geom.bounds
    return max(x1 - x0, y1 - y0)


def _close(geoms: list):
    """The strands closed over their gaps into one polygon (None if not one)."""
    r = ROPE_LINK_MM / 2.0 + 0.01
    band = unary_union(geoms).buffer(r).buffer(-r)
    if isinstance(band, MultiPolygon):
        band = max(band.geoms, key=lambda g: g.area)
    if not isinstance(band, Polygon) or band.is_empty:
        return None
    keep = [h for h in band.interiors if Polygon(h).area > MAX_POCKET_MM2]
    return Polygon(band.exterior, keep)


def join(planned: list, cfg) -> tuple[list, dict]:
    """`planned` with each rope chain replaced by one band; the list is new.
    Also returns {strand shape_id: band shape_id} for the merge record.
    Off: `planned` itself."""
    if not enabled(cfg):
        return planned, {}
    by_thread: dict = {}
    for i, p in enumerate(planned):
        if _strand(p):
            by_thread.setdefault(p.region.thread_index, []).append(i)
    merged: dict[str, str] = {}
    out = list(planned)
    for members in by_thread.values():
        polys = [planned[i].region.polygon for i in members]
        for comp in _chains(polys):
            if len(comp) < MIN_STRANDS:
                continue
            ids = [members[k] for k in comp]
            art = _close([planned[i].region.polygon for i in ids])
            if art is None or _span(art) < MIN_SPAN_MM:
                continue
            sewn = _close([planned[i].polygon for i in ids])
            if sewn is None:
                continue
            host = max(ids, key=lambda i: planned[i].region.polygon.area)
            h = planned[host]
            meta = {k: v for k, v in (h.region.meta or {}).items()
                    if k not in _STRAND_KEYS}
            meta["rope_band"] = [planned[i].region.shape_id for i in ids if i != host]
            region = dataclasses.replace(h.region, polygon=art, area_mm2=float(art.area), meta=meta)
            visible = None
            if h.visible is not None:
                visible = unary_union([planned[i].visible if planned[i].visible is not None
                                       else planned[i].polygon for i in ids] + [sewn])
            out[host] = dataclasses.replace(h, region=region, polygon=sewn, visible=visible)
            for i in ids:
                if i != host:
                    out[i] = None
                    merged[planned[i].region.shape_id] = h.region.shape_id
    return [p for p in out if p is not None], merged
