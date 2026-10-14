"""Fur regions as directional texture (`cfg.hair_regions_directional`, OFF).

Why. Professionals sew fur as a TEXTURE of long directional stitches --
randomised tatami at 4-6 mm, layered narrow satins, "tatami angled with the
fur" -- with single strands only as accents
(docs/fine-detail-hair-research-2026-10-12.md §2). The hairline tier sews
strands; on a photograph the segmenter merges a strand field into a few
regions the tier cannot use (PR #876, docs/hairline-photo-trial-2026-10-12.md
option 2). This routes such a region, whole, to the tier that already sews
directional runs: `streamline` (Jobard-Lefer streamlines along the ETF
direction field, `stage6_streamline`), through the per-shape
`tier: "streamline"` route the review screen already has.

Which regions. A region is FUR when the hair gate reads a strand field in
it: the line route's ridge test (`stage6_hairline_lines.extract_strands`,
both polarities, the detector's and the tier's own thresholds, nothing new)
finds at least `FUR_MIN_STRANDS` strands and `FUR_MIN_STRAND_DENSITY` mm of
strand per mm2 of the region's own area inside it, on a region of at least
`FUR_MIN_AREA_MM2` whose mean width is at least `FUR_MIN_FIELD_WIDTH_MM`.
Many strands over an area is a texture; one strand along a thin shape is
that shape, and a network of strokes reads as its own strands (the census:
logo_bridge_bar's outline) -- the hairline tier's business, not this.

On the repo's corpus the gate routes nothing that sews differently (PR
census): the one strand field it admits, photo_grass_macro, is on
`photo_subject`, where every fill is streamline already. The fixtures named
as fur do not read as fur: `fur_ramp`'s discs are a palette fixture with no
strands, and owl_kent's body reads 0.025 mm of strand per mm2 at 80 mm.

Where. The raster lanes only (`FUR_CLASSES`: gradient and the photo
classes); a flat-lane design is never read, so it pays nothing and changes
nothing. On `photo_subject` the auto-route already sews every fill as
streamline, so the flag changes nothing there unless the caller set
`fill_technique` explicitly.

Why streamline and not one tatami angle. Fur turns: a region's structure-
tensor direction (`directionfield.region_direction`) is one axial mean, and
on a curved fur field it falls under `COHERENCE_FALLBACK_MIN` and says
"use the house angle" -- i.e. no direction at all. Streamline follows the
field locally and falls back to the same house angle where the field is
flat. Its spacing and stitch length are the tier's own (no subject-relative
`d_sep` retune, DOCTRINE); its known cost is that highlights stay bare
fabric (fabric-as-value), which the PR measures.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1); the
three thresholds are plan-quality CANDIDATES.
"""
from __future__ import annotations

import shapely
from shapely.geometry import LineString

from .config import PHOTO_CLASSES

# The lanes whose regions carry raster texture the gate can read.
FUR_CLASSES = ("gradient", *PHOTO_CLASSES)

# CANDIDATES (plan quality, not cloth; module docstring and the PR census).
# A region under the area floor is a strand or a sliver, not a field; under
# the strand count it is one line along a shape.
FUR_MIN_AREA_MM2 = 25.0
FUR_MIN_STRANDS = 4
# mm of strand per mm2 of region.
FUR_MIN_STRAND_DENSITY = 0.25
# A FIELD, not a stroke: the region's mean width (2 x area / perimeter) must
# be at least this. Census 2026-10-13 (`tools/fur_regions_census.py`, 80 mm,
# PR body): every region reading over 0.3 mm/mm2 on the nine logos and on
# owl_kent is itself a stroke, 0.74-1.39 mm wide (logo_bridge_bar's black
# outline network, 0.70 mm/mm2 at 1.28 mm; the owl's bristle patch, 0.72 at
# 0.74) -- the ridge test reads the stroke as its own strand, and streamline
# then sews it as a few loose runs (the 0.25-without-width renders). The one
# true strand field in the corpus, photo_grass_macro, is 29.4 mm wide; the
# owl's body is 7.3 mm wide but reads 0.025 mm/mm2. Every region measured
# at or over the density floor is either at most 1.39 mm wide or 29.4 mm,
# so 3.0 decides nothing in the corpus on a hair; regions 2.0-2.2 mm wide
# (drone, summit, owl) read 0.12-0.20 and fail on density anyway.
FUR_MIN_FIELD_WIDTH_MM = 3.0

TIER = "streamline"


def applies(cfg, design_class: str | None) -> bool:
    return bool(getattr(cfg, "hair_regions_directional", False)
                and design_class in FUR_CLASSES)


def read_regions(regions, sp, cfg) -> dict[str, dict]:
    """-> {shape_id: {"area_mm2", "width_mm", "strands", "strand_mm", "density",
    "fur"}}
    for every stitched auto-tier region, from the hair gate's strands on
    `sp` (a `SourcePixels`)."""
    from .stage6_hairline_lines import extract_strands
    strands, _census = extract_strands(sp, cfg)
    lines = [LineString(s["pts"]) for s in strands if len(s["pts"]) >= 2]
    tree = shapely.STRtree(lines) if lines else None
    out: dict[str, dict] = {}
    for r in regions:
        if not r.meta.get("stitched", True):
            continue
        if str(r.meta.get("tier", "auto")).lower() != "auto":
            continue
        poly = r.polygon
        n = 0
        length = 0.0
        if tree is not None and r.area_mm2 >= FUR_MIN_AREA_MM2:
            for i in tree.query(poly, predicate="intersects"):
                inside = lines[i].intersection(poly).length
                if inside > 0.5 * lines[i].length:
                    n += 1
                length += inside
        density = length / r.area_mm2 if r.area_mm2 > 0 else 0.0
        width = 2.0 * poly.area / poly.length if poly.length > 0 else 0.0
        out[r.shape_id] = {
            "area_mm2": round(float(r.area_mm2), 2), "width_mm": round(width, 2), "strands": n,
            "strand_mm": round(length, 2), "density": round(density, 4),
            "fur": bool(r.area_mm2 >= FUR_MIN_AREA_MM2 and n >= FUR_MIN_STRANDS
                        and density >= FUR_MIN_STRAND_DENSITY
                        and width >= FUR_MIN_FIELD_WIDTH_MM)}
    return out


def route(regions, fur_ids) -> list:
    """Copies of `regions` with every FUR auto-tier region on `TIER` (the
    field every stage-5/7 reader honours); the caller's list is untouched,
    so `plan_stitches` stays re-runnable. A per-shape override always wins."""
    from dataclasses import replace
    ids = set(fur_ids or ())
    return [replace(r, meta={**r.meta, "tier": TIER})
            if r.shape_id in ids and str(r.meta.get("tier", "auto")).lower() == "auto"
            else r for r in regions]
