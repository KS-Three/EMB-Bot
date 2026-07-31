"""Stage 5 — sew order, underlaps between neighbouring colors, pull compensation.

Two decisions that must be made together, because making them separately puts a
visible line on the garment.

**Sew order.** Threads sew in the order stage 2 produced them, which is
descending pixel weight: the biggest areas go down first and the small details
land last and stay crisp. Within a layer the order is stage 7's problem.

**Underlap.** Fabric pulls stitching in. Two colors that share a boundary in the
artwork will therefore pull apart on the garment and show a line of fabric
between them. The fix is not to grow both — that just moves the seam — it is to
extend the color that sews FIRST underneath the one that sews after it, and to
forbid the later color from growing back over the earlier one. The later color's
edge then lands exactly where the artwork says, with the earlier color hidden
underneath covering the gap.

This is why the order must be settled before the geometry is touched: reverse
the two, and every seam sits proud of where it belongs.

**Pull compensation** grows the free edges — the ones facing background — by the
fabric preset's amount. It is uniform here; true pull comp acts perpendicular to
the stitch direction only, which needs the fill angle and belongs with a later
directional-compensation pass. Uniform matches the browser engine's behaviour,
so both products are wrong in the same direction until sew-outs correct them.

**Keeping same-thread neighbours apart.** Compensation grows every shape, and two
shapes of the SAME thread have no seam logic to separate them: the order rules
above only ever compare different colours. So two letters sitting a third of a
millimetre apart each grow toward the other and meet in the middle, and the pair
sews as one blob. Measured on the benchmark logo at 90 mm on pique knit, eight
letter pairs fused this way and "ENTERPRISES INC." sewed as "ENERPRSES NC".

The gap between two letters is artwork exactly as much as the counter inside an
"e" is, so it gets the same treatment the counter already gets: it is held open
at its original size. The corridor a shape may not grow into is the bare fabric
within reach of both it and a same-thread neighbour; because compensation can
only close a gap narrower than two of itself, a span of 2 x pull covers every gap
that is in danger and no gap that is not. Underlap is untouched — the corridor is
bare fabric only, and an underlap by definition runs under another colour.
"""
from __future__ import annotations

from dataclasses import dataclass

from shapely import STRtree
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .config import PipelineConfig
from .fabrics import Fabric
from .regions import Region
from .warnings_codes import (
    HOLE_NEARLY_CLOSED,
    SAME_THREAD_SHAPES_MERGED,
    SHAPE_NOT_STITCHED,
    warn,
)


@dataclass
class PlannedRegion:
    """A region with its sewing geometry and its place in the order."""

    region: Region
    polygon: Polygon      # after underlap + pull compensation
    sew_index: int        # thread order; equal for regions of the same thread

    @property
    def shape_id(self) -> str:
        return self.region.shape_id

    @property
    def layer(self) -> int:
        return self.region.meta["layer"]


def _largest_polygon(geom) -> Polygon | None:
    """Boolean ops can shatter a shape; keep the part that is the shape."""
    if geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    if not parts:
        return None
    return max(parts, key=lambda g: g.area)


def resolve_overlaps(
    regions: list[Region], fabric: Fabric, cfg: PipelineConfig
) -> tuple[list[PlannedRegion], list[dict]]:
    """-> (planned regions in sew order, warnings)."""
    warnings: list[dict] = []
    if not regions:
        return [], warnings

    pull = max(0.0, fabric.pull_comp_mm)
    overlap = max(0.0, cfg.overlap_mm)
    hole_floor = cfg.min_detail_mm ** 2

    layers = sorted({r.meta["layer"] for r in regions})
    by_layer = {L: [r for r in regions if r.meta["layer"] == L] for L in layers}
    geom_by_layer = {L: unary_union([r.polygon for r in by_layer[L]]) for L in layers}

    # Bare fabric is everything the artwork does not cover. A same-thread gap is
    # only a gap where no other colour is filling it, so the keep-apart corridor
    # is carved out of this and an underlap under a later colour never qualifies.
    all_art = unary_union([r.polygon for r in regions])

    # How far compensation can push two same-thread shapes together: each one
    # grows by `pull`, so any gap narrower than two of those is at risk.
    fuse_reach = 2.0 * pull
    trees = {L: STRtree([r.polygon for r in by_layer[L]]) for L in layers} if pull > 0 else {}

    # Prefix/suffix unions: what is already on the fabric when this layer sews,
    # and what will cover it afterwards. Built once instead of per region.
    earlier: dict[int, object] = {}
    running = None
    for L in layers:
        earlier[L] = running
        running = geom_by_layer[L] if running is None else running.union(geom_by_layer[L])

    later: dict[int, object] = {}
    running = None
    for L in reversed(layers):
        later[L] = running
        running = geom_by_layer[L] if running is None else running.union(geom_by_layer[L])

    planned: list[PlannedRegion] = []
    holes_held = 0
    lost = 0
    fusing_pairs: set[tuple[str, str]] = set()

    for sew_index, L in enumerate(layers):
        for r in by_layer[L]:
            poly = r.polygon
            grown = poly.buffer(pull) if pull > 0 else poly

            # Extend under whatever sews later — the underlap that hides the seam.
            if overlap > 0 and later[L] is not None:
                reach = poly.buffer(pull + overlap).intersection(later[L])
                if not reach.is_empty:
                    grown = grown.union(reach)

            # Hold open the bare fabric between this shape and any neighbour on
            # the same thread. Nothing else separates them: they share a colour,
            # so neither the sew order nor the underlap rule above ever applies.
            if pull > 0 and len(by_layer[L]) > 1:
                near = poly.buffer(fuse_reach)
                others = [
                    by_layer[L][i] for i in trees[L].query(near) if by_layer[L][i] is not r
                ]
                if others:
                    corridor = near.intersection(
                        unary_union([o.polygon for o in others]).buffer(fuse_reach)
                    ).difference(all_art)
                    if not corridor.is_empty:
                        grown = grown.difference(corridor)
                    for other in others:
                        if poly.distance(other.polygon) < fuse_reach:
                            fusing_pairs.add(tuple(sorted((r.shape_id, other.shape_id))))

            # Never grow back over a color that is already down.
            if earlier[L] is not None:
                grown = grown.difference(earlier[L])

            grown = _largest_polygon(grown)
            if grown is None or grown.is_empty:
                lost += 1
                continue

            # Growing the shell shrinks every hole by the same amount. A counter
            # that closes up is lost artwork, so any hole that would fall below
            # the sewable floor is held open at its original size instead.
            held: list[Polygon] = []
            for ring in poly.interiors:
                hole = Polygon(ring)
                if hole.area < hole_floor:
                    continue           # already below the floor; stage 3's call
                if hole.buffer(-pull).area < hole_floor:
                    held.append(hole)
            if held:
                holes_held += len(held)
                grown = _largest_polygon(grown.difference(unary_union(held)))
                if grown is None or grown.is_empty:
                    lost += 1
                    continue

            planned.append(PlannedRegion(region=r, polygon=grown, sew_index=sew_index))

    if fusing_pairs:
        n = len(fusing_pairs)
        warnings.append(
            warn(
                SAME_THREAD_SHAPES_MERGED,
                f"{n} pair{'s' if n != 1 else ''} of shapes in the same thread sit "
                "closer together than pull compensation would have grown them, and "
                "were kept apart so they do not sew as one shape.",
                count=n,
            )
        )
    if holes_held:
        warnings.append(
            warn(
                HOLE_NEARLY_CLOSED,
                f"{holes_held} opening{'s' if holes_held != 1 else ''} would have "
                "closed up under pull compensation and were kept open.",
                count=holes_held,
            )
        )
    if lost:
        warnings.append(
            warn(
                SHAPE_NOT_STITCHED,
                f"{lost} shape{'s' if lost != 1 else ''} disappeared while being "
                "fitted against neighbouring colors and were not stitched.",
                count=lost,
            )
        )
    return planned, warnings
