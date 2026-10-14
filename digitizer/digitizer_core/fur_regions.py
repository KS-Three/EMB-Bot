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
`FUR_MIN_AREA_MM2`. Many strands over an area is a texture; one strand along
a thin shape is that shape (the hairline tier's business, not this).

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
# mm of strand per mm2 of region. Census 2026-10-13 (`tools/
# fur_regions_census.py`, 80 mm): the densest qualifying region on the nine
# logos is logo_bridge_bar's, 0.70 (9 strands); on owl_kent (Studio route)
# the bristle patch beside the beak, 0.72 (4 strands); the owl's body reads
# 0.025. Nothing separates the two, so the candidate sits above every logo
# and the corpus routes NOTHING: a measured negative, the gate shipped for
# the photo it was built for. At 0.25 both regions route (the PR's bill).
FUR_MIN_STRAND_DENSITY = 0.75

TIER = "streamline"


def applies(cfg, design_class: str | None) -> bool:
    return bool(getattr(cfg, "hair_regions_directional", False)
                and design_class in FUR_CLASSES)


def read_regions(regions, sp, cfg) -> dict[str, dict]:
    """-> {shape_id: {"area_mm2", "strands", "strand_mm", "density", "fur"}}
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
        out[r.shape_id] = {
            "area_mm2": round(float(r.area_mm2), 2), "strands": n,
            "strand_mm": round(length, 2), "density": round(density, 4),
            "fur": bool(r.area_mm2 >= FUR_MIN_AREA_MM2 and n >= FUR_MIN_STRANDS
                        and density >= FUR_MIN_STRAND_DENSITY)}
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
