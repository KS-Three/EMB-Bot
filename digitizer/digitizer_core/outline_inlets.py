"""A shape's own inlets, kept open at stitch time (`cfg.extra["outline_inlets_kept"]`, built OFF).

Found 2026-11-14 tracing Kent's "shape detail lost" pins
(`docs/shape-detail-traced-2026-11-14.md`). An INLET is bare fabric the
art keeps inside a shape's own outer outline but open to the outside: a
gear's tooth gaps, a bird's open beak, a notch cut into a disc. Stage 4
traces it (the polygon has it) and then the stitches sew over it:

- a SATIN column draws its rails as a smoothed offset of the spine
  (`stage6_satin._rail_points`: a median over 5 stations, then 4 averaging
  passes), so a width profile that steps in and out every millimetre comes
  out as a ripple, and its crosses run across the gaps (Ahora's gear: 16
  square teeth sewn as a scalloped ring; the crest's beak: one column over
  the open mouth);
- a FILL is grown by the pull (`stage5_overlap._grow`), outward from both
  walls of a slot, so a slot under twice the pull closes (music's notch,
  0.6 mm across).

ON, both stop:

1. stage 5 keeps a fill's growth out of its own inlets (`kept_inlets`), as
   `growth_keeps_gaps` does for the gaps between shapes and for counters;
2. a satin shape whose crosses cover at least `SATIN_OVER_INLET_FRAC` of one
   of its inlets is planned again as a fill (`satin_over_inlets`), on a copy
   of the regions (the `tier="fill"` field every stage-5/7 reader honours),
   where the rows end at the inlet's walls.

A letter is never moved: its tier is the lettering lane's, and its
openings are what the per-stroke satin is built to keep.

Only WHERE thread goes changes. The pull itself (`Fabric.pull_comp_mm`) is
gate 1 and untouched; whether a kept inlet stays open on the cloth is the
sew-out's to settle.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon
from shapely.ops import polylabel, unary_union

FLAG = "outline_inlets_kept"
#: the narrowest inlet worth keeping (mm): two thread edges, each half a 40 wt
#: laid thread, meet across anything narrower anyway (the same floor as
#: `stage5_overlap.GAP_SEWABLE_MM`, restated to keep this module import-free)
INLET_MIN_MM = 0.5
#: inlets are found by closing the outline with a disc of this radius (mm):
#: an inlet narrower than twice it closes, so this is half of
#: `stage5_overlap.GAP_PROTECT_MM` (2.0 mm, the widest gap growth is kept
#: out of; past it the pull leaves the gap readable)
CLOSE_RADIUS_MM = 1.0
#: an inlet smaller than this (mm²) is a corner's fillet, not a feature
INLET_MIN_AREA_MM2 = 0.1
#: a satin covering at least this share of one inlet with its thread has
#: sewn over it: the column cannot draw that shape
SATIN_OVER_INLET_FRAC = 0.5
#: half a laid 40 wt thread (mm), the width a cross covers either side of
#: its centre line
THREAD_HALF_MM = 0.2

#: meta keys that make a region a letter (stage 2's text tags)
_LETTER_KEYS = ("text_candidate", "ocr_char", "text_cluster_id")


def enabled(cfg) -> bool:
    return bool((getattr(cfg, "extra", None) or {}).get(FLAG))


def inscribed_width(poly: Polygon) -> float:
    """Twice the radius of the largest circle inside `poly` (mm)."""
    try:
        c = polylabel(poly, tolerance=0.01)
    except Exception:  # noqa: BLE001 -- a degenerate ring is no inlet
        return 0.0
    return 2.0 * float(poly.exterior.distance(c))


def inlets(poly) -> list[Polygon]:
    """The inlets of `poly`'s OUTER outline: what closing it with a
    `CLOSE_RADIUS_MM` disc adds, in pieces at least `INLET_MIN_MM` across
    and `INLET_MIN_AREA_MM2` in area. Holes are counters, not inlets
    (`growth_keeps_gaps` keeps those)."""
    if poly is None or poly.is_empty or poly.geom_type != "Polygon":
        return []
    shell = Polygon(poly.exterior)
    closed = shell.buffer(CLOSE_RADIUS_MM).buffer(-CLOSE_RADIUS_MM)
    bays = closed.difference(shell)
    out = []
    for g in getattr(bays, "geoms", [bays]):
        if g.is_empty or g.geom_type != "Polygon" or g.area < INLET_MIN_AREA_MM2:
            continue
        if inscribed_width(g) >= INLET_MIN_MM:
            out.append(g)
    return out


def kept_inlets(poly, grown, all_art, reach: float = 0.0):
    """`grown` less the inlets of `poly` that no artwork fills (stage 5,
    for a fill): the growth stays out of them, `poly` itself is kept whole.
    `reach` (the pull) carries the opening out through the growth band
    round the outline, or the band welds the inlet's MOUTH shut (music's
    notch, first cut: the slot stayed open inside and closed at the edge)."""
    bays = inlets(poly)
    if not bays:
        return grown
    bare = unary_union(bays).difference(all_art)
    if bare.area < INLET_MIN_AREA_MM2:
        return grown            # another colour's art fills it: a seam, not bare
    if reach > 0:
        bare = bare.buffer(reach).difference(all_art)
    return grown if bare.is_empty else grown.difference(bare).union(poly)


def is_letter(region) -> bool:
    meta = getattr(region, "meta", None) or {}
    return any(meta.get(k) for k in _LETTER_KEYS)


def satin_over_inlets(regions, plan) -> dict[str, float]:
    """{shape id: the largest share of one of its inlets its satin thread
    covers} for every satin shape (not a letter) at or over
    `SATIN_OVER_INLET_FRAC`. The cover is the satin runs' needle path
    widened by `THREAD_HALF_MM`."""
    from .stitches import SATIN
    paths: dict[str, list] = {}
    for _blk, run in plan.iter_runs():
        if run.kind != SATIN or len(run.points or []) < 2:
            continue
        paths.setdefault(str(run.shape_id), []).append(LineString(run.points))
    out: dict[str, float] = {}
    for r in regions:
        lines = paths.get(str(r.shape_id))
        if not lines or is_letter(r) or str(r.meta.get("tier", "auto")).lower() != "auto":
            continue
        bays = inlets(r.polygon)
        if not bays:
            continue
        cover = unary_union(lines).buffer(THREAD_HALF_MM)
        worst = max(cover.intersection(b).area / b.area for b in bays)
        if worst >= SATIN_OVER_INLET_FRAC:
            out[str(r.shape_id)] = round(float(worst), 3)
    return out


def as_fill(regions, ids) -> list:
    """`regions` with `ids` re-tiered to fill, on copies (the caller's
    regions are untouched and the plan stays re-runnable)."""
    from dataclasses import replace
    return [replace(r, meta={**r.meta, "tier": "fill", "inlet_satin_to_fill": True})
            if str(r.shape_id) in ids else r for r in regions]
