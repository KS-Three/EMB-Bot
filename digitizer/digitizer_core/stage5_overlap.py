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
fabric preset's amount.

By default that growth is UNIFORM: one `buffer(pull)` outward in every
direction. That matches the browser engine, and it is wrong in a specific way
(Law 22). Thread tension pulls each stitch's two penetration points together,
so an object loses size ALONG its stitch direction and gains it across —
one effect, two directions, and no major package compensates isotropically.
Uniform growth is right on average and wrong everywhere specific: it under-
compensates nothing and over-compensates the two faces the stitches run
parallel to.

`cfg.directional_comp` turns on the version that follows the stitches, and the
two tiers need opposite treatment:

- **Fill.** Rows run along the fill angle, so the row ENDS are where the
  penetrations pull together. Growth goes on those edges only, tapering as
  `pull x |n . axis|` around the outline, and the edges the rows run parallel
  to keep their artwork size. This is why the fill angle is computed HERE and
  handed forward (see below).
- **Satin.** Growth stays uniform, and that is not a shortcut — it is exact.
  A column's stitch direction is perpendicular to its rails, which is to say
  parallel to the boundary normal there, so `pull x |n . axis|` IS `pull` all
  the way along both rails. The uniform buffer is only wrong at the two CAPS,
  where it adds `pull` in the one direction that should be losing length. That
  is corrected where the caps actually exist, in stage 6 — see below.

**Where the fill angle comes from, and why that is a seam problem.** Pull
direction is the stitch direction. For a fill that is the per-region principal
axis, and `stage6_fill.stitch_shape` has always computed it from the polygon
stage 5 hands it — so compensating along it here is circular: the angle depends
on the growth that depends on the angle. The cut is to compute the angle ONCE,
on the artwork polygon, before any growth, and carry it on `PlannedRegion.
stitch_angle_deg` for stage 7 to pass back down. Comp direction and fill
direction are then the same number by construction instead of by luck. With the
flag off nothing is computed and stage 6 keeps deriving its own angle.

**Where push compensation lives, and why it is not here.** Law 24's end cutback
is a satin-cap correction, and stage 5 has no caps: a column's ends are the ends
of a SPINE that stage 6 extracts by skeletonising the polygon. On a curved
column the cap normal is different at each end and neither one is a property of
the outline. So stage 5 cannot express it, and the cutback is applied in
`stage6_satin.satin_stroke`, on the spine, right after `_extend_to_cap` puts the
end on the boundary. Stage 7 carries the number across. What stage 5 owes that
correction is the `pull` its uniform buffer wrongly added at the cap, which is
why the cutback stage 7 passes is `pull + PUSH_CUTBACK_MM` and not `0.4` alone.

**Keeping same-thread neighbours apart.** Compensation grows every shape, and two
shapes of the SAME thread have no seam logic to separate them: the order rules
above only ever compare different colours. So two letters sitting a third of a
millimetre apart each grow toward the other and meet in the middle, and the pair
sews as one blob. Measured on the benchmark logo at 90 mm on pique knit, eight
letter pairs fused this way and "ENTERPRISES INC." sewed as "ENERPRSES NC".

The gap between two letters is artwork exactly as much as the counter inside an
"e" is, so it gets the same treatment the counter already gets: it is held open.
The corridor a shape may not grow into is the bare fabric within ONE pull of both
it and a same-thread neighbour — the lens the two compensations would jointly
cover. That lens is non-empty exactly when the gap is under 2 x pull (the gaps
compensation can actually close) and never reaches a face whose local separation
is wider, so every face keeps its full compensation except where growing would
fuse. Underlap is untouched — the corridor is bare fabric only, and an underlap
by definition runs under another colour.
"""
from __future__ import annotations

from dataclasses import dataclass

from shapely import STRtree, affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .config import PipelineConfig
from .fabrics import Fabric
from .machine import SATIN_MAX_WIDTH_MM
from .regions import Region
from .stage6_fill import principal_angle_deg
from .stage6_satin import is_satin_candidate
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
    # `polygon` minus everything that sews AFTER this layer — the part of this
    # color a person will actually see. `polygon` deliberately includes the
    # underlap tongue, which is scaffolding hidden under the next color, so
    # anything decorative (build step 11's border) must be drawn on this
    # instead: a border on the tongue is sewn under another thread, invisible,
    # costing stitches and adding bulk exactly where two colors already stack.
    # None means "not computed" and callers fall back to `polygon`, so every
    # existing construction site stays valid.
    visible: object | None = None
    # The union of every layer that sews AFTER this one — `later[L]` below,
    # the same object `visible` is derived from and the underlap reaches into,
    # shared by reference across every region of the layer.
    #
    # Stage 7 needs it to decide whether a needle-down link between two shapes
    # will be buried (chaining law 60: professionals route links to be COVERED,
    # not to be short). It is a stage-5 fact — which colours sew after this one,
    # and where — so stage 7 is handed it rather than recomputing it; two
    # copies of one derivation is how the underlap and the chaining test would
    # drift apart the first time either side changed.
    #
    # ARTWORK geometry, not the grown sewing polygons: a later layer's grown
    # polygon is a superset of its artwork (pull compensation only adds, and
    # `difference(earlier)` can only remove area that belongs to an EARLIER
    # layer, which is disjoint from this one). Handing over the artwork union
    # therefore under-promises coverage, which is the safe direction for a test
    # whose failure mode is a visible float.
    #
    # None on the last layer — nothing sews after it — and callers must treat
    # that as "no coverage from other colours", not as "not computed".
    covered_by: object | None = None
    # The stitch axis this shape was compensated along, in degrees, or None
    # when compensation was isotropic (flag off, or a satin-tier shape, whose
    # axis is not one number — it turns with the spine). Stage 7 hands it back
    # to stage 6 so the fill sews along the axis it was compensated for; None
    # leaves stage 6 deriving its own, which is the shipped behaviour.
    stitch_angle_deg: float | None = None
    # Which tier stage 5 believed this shape would sew as, decided by the same
    # `is_satin_candidate` call on the same artwork polygon stage 7 uses, so
    # the two cannot disagree. Recorded rather than re-derived because the
    # compensation already committed to it.
    satin_tier: bool = False

    @property
    def visible_geom(self):
        """The visible part, or the whole sewing polygon when it was not set."""
        if self.visible is None or self.visible.is_empty:
            return self.polygon
        return self.visible

    @property
    def shape_id(self) -> str:
        return self.region.shape_id

    @property
    def layer(self) -> int:
        return self.region.meta["layer"]


# The structuring element for directional compensation is a SEGMENT lying on
# the stitch axis: dilating by it offsets each face by `amount x |n . axis|`,
# which is the whole of Law 22 in one operation — full compensation where the
# stitches penetrate head-on, none where they run parallel. A segment is an
# ellipse with a zero minor axis, and an ellipse dilation is a circular buffer
# with the plane squashed, so that is how it is built. The minor axis is held a
# hair off zero to keep the squash factor finite; 10 microns is a hundredth of
# the 0.1 mm DST grid and a fiftieth of `simplify_tol_mm`, so it can never
# reach the file. Measured on a 30x8 rectangle at six axes: 0.3000 mm along,
# 0.0100 across, and the oblique offsets match `amount x |cos|` to 4 decimals.
_COMP_MINOR_MM = 0.01
# The buffer's circle approximation is what limits accuracy after unsquashing;
# 64 segments per quadrant puts the worst-case shortfall at 1 - cos(pi/256),
# about 75 nanometres.
_COMP_QUAD_SEGS = 64


def _axial_offset(geom, amount_mm: float, axis_deg: float, sign: float):
    """Offset `geom` by `amount_mm` ALONG `axis_deg` only. sign -1 erodes.

    The result is simplified before it is returned, and that is not tidiness.
    Squashing puts `_COMP_QUAD_SEGS * 4` vertices on every corner's arc, and
    unsquashing flattens most of them into a near-straight run along the minor
    axis: a 5-vertex rectangle came back with 261, and `principal_angle_deg`
    sums second moments over VERTICES, so the cloud — not the shape — decided
    the answer. Measured: the artwork's 26.2 deg axis read as -22.7 deg off the
    dilated polygon. `stage6_fill._underlay_paths` asks exactly that question
    about exactly this polygon, so it is a live wrong answer, not a latent one.
    Simplifying at the minor axis collapses the flattened arcs and nothing else
    — the arcs deviate from their chord by at most `_COMP_MINOR_MM` by
    construction. Measured after: 5-9 vertices, axial offset still 0.3000 mm.
    """
    if amount_mm <= 0:
        return geom
    rot = affinity.rotate(geom, -axis_deg, origin=(0, 0))
    sq = affinity.scale(rot, 1.0 / amount_mm, 1.0 / _COMP_MINOR_MM, origin=(0, 0))
    sq = sq.buffer(sign, quad_segs=_COMP_QUAD_SEGS)
    if sq.is_empty:
        return sq
    sq = affinity.scale(sq, amount_mm, _COMP_MINOR_MM, origin=(0, 0))
    out = affinity.rotate(sq, axis_deg, origin=(0, 0))
    # 0.01 mm is a tenth of the DST grid and a twentieth of `simplify_tol_mm`,
    # so this cannot move a penetration.
    return out.simplify(_COMP_MINOR_MM, preserve_topology=True)


def _grow(poly, pull: float, axis_deg: float | None):
    """The compensation dilation for one shape.

    `axis_deg is None` is the isotropic case — the shipped behaviour, and the
    exact one for a satin column, whose rails face their own stitch direction
    the whole way along.
    """
    if pull <= 0:
        return poly
    if axis_deg is None:
        return poly.buffer(pull)
    return _axial_offset(poly, pull, axis_deg, 1.0)


def _shrink(poly, pull: float, axis_deg: float | None):
    """The matching erosion, for asking whether a hole survives compensation."""
    if pull <= 0:
        return poly
    if axis_deg is None:
        return poly.buffer(-pull)
    return _axial_offset(poly, pull, axis_deg, -1.0)


def _comp_axis(region: Region, cfg: PipelineConfig, satin_max: float) -> tuple[float | None, bool]:
    """-> (stitch axis to compensate along or None for isotropic, satin tier?).

    Classified on the ARTWORK polygon with the same call stage 7 makes, for the
    same reason stage 7 makes it there: compensation must not be able to flip a
    shape's tier, or a logo would sew differently structured on a towel than on
    a polo.
    """
    if is_satin_candidate(region.polygon, satin_max):
        return None, True
    if cfg.fill_angle_deg is not None:
        return cfg.fill_angle_deg, False
    return principal_angle_deg(region.polygon), False


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

    # Law 22. Off: one axis of None per shape, so every `_grow` below is the
    # `poly.buffer(pull)` this stage has always done, byte for byte.
    directional = bool(cfg.directional_comp) and pull > 0
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    axis_by_id: dict[str, float | None] = {}
    satin_by_id: dict[str, bool] = {}
    for r in regions:
        axis, is_satin = _comp_axis(r, cfg, satin_max) if directional else (None, False)
        axis_by_id[r.shape_id] = axis
        satin_by_id[r.shape_id] = is_satin

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

    # Each shape's own compensated reach, for the keep-apart corridor below.
    # Isotropic growth distributes over a union, so with the flag off the
    # corridor is built the cheap way it always was; directional growth does
    # not — every shape has its own axis — so the reaches are unioned per
    # shape instead. Only built when the flag is on.
    reach_by_id: dict[str, object] = (
        {r.shape_id: _grow(r.polygon, pull, axis_by_id[r.shape_id]) for r in regions}
        if directional else {}
    )

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
            axis = axis_by_id[r.shape_id]
            grown = _grow(poly, pull, axis)

            # Extend under whatever sews later — the underlap that hides the seam.
            if overlap > 0 and later[L] is not None:
                reach = poly.buffer(pull + overlap).intersection(later[L])
                if not reach.is_empty:
                    grown = grown.union(reach)

            # Hold open the bare fabric between this shape and any neighbour on
            # the same thread. Nothing else separates them: they share a colour,
            # so neither the sew order nor the underlap rule above ever applies.
            #
            # The corridor is the lens each side reaches by ONE pull — the
            # region both compensations would jointly cover — so it is
            # non-empty exactly for gaps under 2 x pull, the ones compensation
            # can actually close, and it never touches a face whose local
            # separation is wider. Adversarial review caught the first version
            # buffering both sides by 2 x pull: that carved compensation off
            # frontage out to nearly 4 x pull of separation (faces that were
            # never in danger sewed up to ~0.5 mm short on terry towel), and
            # whether it happened at all rode on STRtree bounding boxes, so
            # the same artwork sewed differently rotated 45 degrees.
            if pull > 0 and len(by_layer[L]) > 1:
                # Candidates come from a 2 x pull query — the bbox of a ONE-pull
                # reach misses an axis-aligned neighbour whose gap sits between
                # pull and 2 x pull, which is still a gap in danger. The lens
                # itself is built at one pull per side.
                others = [
                    by_layer[L][i]
                    for i in trees[L].query(poly.buffer(fuse_reach))
                    if by_layer[L][i] is not r
                ]
                if others:
                    others_reach = (
                        unary_union([reach_by_id[o.shape_id] for o in others])
                        if directional
                        else unary_union([o.polygon for o in others]).buffer(pull)
                    )
                    corridor = _grow(poly, pull, axis).intersection(
                        others_reach
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
                if _shrink(hole, pull, axis).area < hole_floor:
                    held.append(hole)
            if held:
                holes_held += len(held)
                grown = _largest_polygon(grown.difference(unary_union(held)))
                if grown is None or grown.is_empty:
                    lost += 1
                    continue

            # `later[L]` is already computed for the underlap reach above and
            # was previously discarded. Keeping it is the whole cost of knowing
            # which part of this color is visible: subtract the layers that
            # sew after it and what remains is the finished visible edge.
            # NOT run through `_largest_polygon` — a later color can legitimately
            # split this one in two, and dropping the smaller half would silently
            # lose a real visible piece.
            visible = None
            if later[L] is not None:
                vis = grown.difference(later[L])
                visible = None if vis.is_empty else vis

            planned.append(PlannedRegion(region=r, polygon=grown,
                                         sew_index=sew_index, visible=visible,
                                         covered_by=later[L],
                                         stitch_angle_deg=axis,
                                         satin_tier=satin_by_id[r.shape_id]))

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
