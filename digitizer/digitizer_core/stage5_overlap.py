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

**Closing narrow gaps between colours (`cfg.forbid_gap_mm`, default OFF).** The
underlap reaches only into a later colour's ARTWORK, never across bare fabric,
so two colours the artwork separates by a strip narrower than two stitch rows
get two pull bands meeting in the middle and nobody spanning it — fabric again
once pull takes the bands back (Law 26: such gaps "close up" and cannot be sewn
as their own region). With the flag, `gap_bridges` hands each such strip to the
colour that sews first, which then plans as if its artwork ran across it: the
ordinary tongue reaches under the later colour from the strip's far edge, and
the later colour keeps its artwork edge — the colour on top owns the seam, as
Kent ruled for borders on 2026-09-09. The threshold is gate 1's to set.

**A clip that cuts a shape in two (MASTER_SCOPE defect 61), two settings.**
Clipping a grown shape by the colours already down can split it: a later
colour whose artwork overlaps an earlier one's comes out of the clip as two
or more polygons. Before the fix `_largest_polygon` kept the biggest and
dropped the rest without a word (drone's `S426e81b9` loses a 9 mm² piece) —
and "biggest" is by SEWN area, so the piece kept can be underlap tongue with
no artwork in it while the shape's ink is the piece thrown away (gaulke's
whole roof line).

`cfg.clip_parent_keeps_ink` (default ON, Kent 2026-10-12): the shape keeps
the piece carrying the most artwork. It adds no region and no warning; where
the largest piece is also the inkiest, nothing changes.

`cfg.clip_keep_pieces` (default OFF): the shape keeps the piece carrying the
most artwork as above, and every other piece whose ARTWORK clears the stage-4 region floor
(`clip_piece_floor_mm2`) sews as its own region of the same thread and tier,
planned right after its parent; smaller pieces are dropped as before and
counted in `CLIP_DROPPED_SLIVER`, which the Studio keeps silent. A piece of
pure compensation growth carries no artwork and is dropped, uncounted: it is
not ink anyone drew, and cut off from its shape it underlaps nothing of it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from shapely import STRtree, affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .config import PipelineConfig
from .fabrics import Fabric
from .machine import FILL_ROW_MM, satin_ceiling_mm
from .regions import Region
from .stitchwidth import column_sized
from .stage6_fill import best_fill_angle_deg, principal_angle_deg
from .stage6_satin import is_satin_candidate
from . import machine
from .stage6_hairline import _BLOB_FACTOR as _HAIR_BLOB_FACTOR
from .stage6_hairline import block_thread_wt
from .warnings_codes import (
    CLIP_DROPPED_SLIVER,
    HOLE_NEARLY_CLOSED,
    SAME_THREAD_SHAPES_MERGED,
    SHAPE_NOT_STITCHED,
    warn,
)


# The meta key `textcluster.regularize_text_clusters` writes on a door-1
# cluster member it widened to the sewn-column floor
# (`cfg.lettering_min_column_mm`): the radius it added, in mm. Read here and
# in stage 7, where that population — and only that population — takes the
# column route: it may grow over the ground already sewn beneath it (below),
# and it is classified and sewn on the polygon this stage grows for it
# rather than routed to the run tier on its area.
WIDENED_LETTERING_KEY = "text_cluster_widened_mm"

# ROADMAP gate 1 PLACEHOLDER -- the fabric's multiplier on the parallel-join
# underlap `cfg.overlap_by_angle` grows to (`cfg.overlap_parallel_mm`). Law
# 26 asks 1.0 mm at a parallel join on wovens and 1.5-2.0 on knits and
# fleece, but how much more a knit needs is a physical constant only a
# sew-out settles (card block 6 sews the underlap rungs), so EVERY fabric
# reads 1.0 -- the woven figure -- until one does. Do not put per-fabric
# values here without that sew-out; when it lands this becomes a `Fabric`
# field in `fabrics.py` beside `pull_comp_mm`.
OVERLAP_FABRIC_FACTOR = 1.0


def widened_lettering(region: Region) -> bool:
    """True for a shape whose polygon IS its column: a text-cluster member
    the regularizer's floor widened, or any shape `stitchwidth.
    apply_stitch_widths` offset to a width (a word's shared width, the
    floor, or a review-screen `stitch_width_mm`). Both populations need the
    same four rules downstream — no sub-floor run routing, classify and sew
    on the compensated polygon, keep the growth over the ground beneath,
    pull on the polygon not the rails — so they share one predicate."""
    return bool(region.meta.get(WIDENED_LETTERING_KEY)) or column_sized(region)


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


def _comp_axis(region: Region, cfg: PipelineConfig, satin_max: float,
               design_class: str = "flat") -> tuple[float | None, bool]:
    """-> (stitch axis to compensate along or None for isotropic, satin tier?).

    Classified on the ARTWORK polygon with the same call stage 7 makes, for the
    same reason stage 7 makes it there: compensation must not be able to flip a
    shape's tier, or a logo would sew differently structured on a towel than on
    a polo. The review screen's per-shape tier and fill angle (shape-layers
    contract v1) are honoured here in stage 7's own precedence — per-shape
    beats global — so the axis a shape is compensated along stays the axis it
    sews along. `design_class` has to travel with it for the same reason: a
    shape that stage 7 now reads as fill under the DT tightening (see
    `stage6_satin.is_satin_candidate`) must not get compensated as satin here.
    """
    tier = str(region.meta.get("tier", "auto")).lower()
    if tier == "auto" and widened_lettering(region):
        # The column route: stage 7 classifies this population on the
        # polygon THIS stage grows for it, not on the artwork, so the
        # artwork verdict is the wrong one to compensate along. Isotropic,
        # satin: the regularizer's `floor / 2 - pull` assumes the pull comes
        # back all round, and an axial add-back would leave a 0.4 mm
        # "column" stage 7 then declines, silently.
        return None, True
    if tier == "satin" or (tier == "auto"
                           and is_satin_candidate(
                               region.polygon, satin_max,
                               design_class=design_class,
                               per_stroke=cfg.satin_per_stroke)):
        return None, True
    angle = region.meta.get("fill_angle_deg")
    if angle is not None:
        return float(angle), False
    if cfg.fill_angle_deg is not None:
        return cfg.fill_angle_deg, False
    design = region.meta.get("design_angle_deg")
    if design is not None:
        # `cfg.design_angle` (2026-09-09): the design's one direction, in the
        # same slot stage 7 reads it -- behind the review's and the global.
        return float(design), False
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


# `cfg.clip_keep_pieces`: the meta key a piece's region carries, naming the
# shape it was cut from. A piece's shape_id is its parent's plus `-clip<k>`.
CLIP_PIECE_OF_KEY = "clip_piece_of"


def clip_piece_floor_mm2(cfg: PipelineConfig) -> float:
    """The artwork a cut-off piece must carry to sew as its own region: the
    floor stage 4 holds every traced region to (`min_area_mm2` in
    `stage4_vectorize.vectorize`, a quarter of `min_detail_mm²`), never under
    the run tier's `machine.RUN_MIN_AREA_MM2`. No new constant."""
    return max(machine.RUN_MIN_AREA_MM2, 0.25 * float(cfg.min_detail_mm) ** 2)


def _polygon_pieces(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]


def _split_clip(geom, art, floor: float, *, by_ink: bool = True, keep: bool = True):
    """-> (the parent's piece or None, [cut-off pieces kept], [artwork mm² of
    each cut-off piece dropped]).

    `by_ink` (`cfg.clip_parent_keeps_ink`): the parent keeps the piece
    carrying the most ARTWORK (`art`, the shape's own polygon), the largest
    among equals. Where that is also the largest piece — every split but a
    handful measured — it is `_largest_polygon(geom)` exactly, so the parent
    sews what it always did. It is not always: on drone (2026-10-12) a
    0.25 mm strip's largest piece was 3.16 mm² of underlap tongue with no
    artwork in it, and `_largest_polygon` sewed that and dropped all 2.64
    mm² of the strip's ink. Off, the parent keeps the largest piece.

    `keep` (`cfg.clip_keep_pieces`): every other piece is judged on its
    artwork: at or over `floor` it is kept; under it, dropped and its
    artwork reported; with none at all it is pull growth cut off from its
    shape — scaffolding for nothing — and is dropped uncounted, as the
    shipped engine drops it. Off, no piece is kept and nothing is reported:
    the other pieces are dropped, as `_largest_polygon` drops them.
    """
    parts = _polygon_pieces(geom)
    if not parts:
        return None, [], []
    if by_ink:
        ink = [g.intersection(art).area for g in parts]
        # Rounded so float dust on a contact (1e-9 mm²) cannot outrank area.
        i_main = max(range(len(parts)), key=lambda i: (round(ink[i], 6), parts[i].area))
    else:
        i_main = max(range(len(parts)), key=lambda i: parts[i].area)
    kept, dropped = [], []
    if not keep:
        return parts[i_main], kept, dropped
    if not by_ink:
        ink = [g.intersection(art).area for g in parts]
    for i, g in enumerate(parts):
        if i == i_main:
            continue
        if ink[i] >= floor:
            kept.append(g)
        elif ink[i] > 1e-6:
            dropped.append(float(ink[i]))
    return parts[i_main], kept, dropped


def _weld_part(joined, art) -> Polygon:
    """`cfg.forbid_gap_mm`: the part of a failed weld (artwork ∪ strip that
    stayed several polygons) the shape plans on — the one carrying its
    ARTWORK, never a strip part on its own. `_largest_polygon` picked by
    area, so a small shape with a long strip planned on the strip, bare
    fabric, and sewed none of its ink (PR #855's audit). Where the artwork's
    part is also the largest this is `_largest_polygon(joined)` exactly.

    The artwork is one polygon, so it lies in one part of the union; a strip
    part that did not weld overlaps it by nothing (or the union would have
    merged them) and is dropped -- the gap stays open there, as it did."""
    # Always by ink: this is the weld, not the clip `cfg.clip_parent_keeps_ink`
    # governs, and no other part is kept as a region.
    best, _, _ = _split_clip(joined, art, 0.0, by_ink=True, keep=False)
    return best if best is not None else art


def _judge_pieces(geom, art, floor: float):
    """`_split_clip` with no largest piece singled out: every piece judged."""
    kept, dropped = [], []
    for g in _polygon_pieces(geom):
        ink = g.intersection(art).area
        if ink >= floor:
            kept.append(g)
        elif ink > 1e-6:
            dropped.append(float(ink))
    return kept, dropped


def seam_row_angles(regions: list[Region], cfg: PipelineConfig, fabric: Fabric,
                    design_class: str = "flat") -> dict[str, float | None]:
    """-> {shape_id: the row angle `cfg.overlap_by_angle` reads, or None}.

    Stage 7's precedence (`_fill_angle_for`): the shape's own angle, the
    global, the design angle, the compensation axis -- and with none of
    those, the angle stage 6 picks itself, `best_fill_angle_deg` on the
    grown polygon at the design's row spacing, approximated here on the
    artwork grown by the pull (the real one is what stage 5 computes). Only
    plain tatami has one row angle; satin, another technique or a bean
    letter is None and keeps the scalar underlap.
    """
    pull = max(0.0, fabric.pull_comp_mm)
    satin_max = satin_ceiling_mm(cfg)
    directional = bool(cfg.directional_comp) and pull > 0
    row_mm = (cfg.fill_row_mm or FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    tatami = str(getattr(cfg, "fill_technique", "tatami") or "tatami") == "tatami"
    out: dict[str, float | None] = {}
    for r in regions:
        a, is_sat = _comp_axis(r, cfg, satin_max, design_class)
        tier = str(r.meta.get("tier", "auto")).lower()
        if (is_sat or not tatami or tier not in ("auto", "fill")
                or r.meta.get("bean_letter_spines")):
            out[r.shape_id] = None
            continue
        explicit = (r.meta.get("fill_angle_deg") is not None
                    or cfg.fill_angle_deg is not None
                    or r.meta.get("design_angle_deg") is not None
                    or directional)
        out[r.shape_id] = (a if explicit else
                           best_fill_angle_deg(_grow(r.polygon, pull, None), row_mm))
    return out


def _bare_part(hole: Polygon, covered, floor: float) -> list[Polygon]:
    """The part of a held hole that is still an opening once later colours sew.

    A hole no later stitched shape touches is returned whole and untouched, so
    a true counter is held exactly as before. Otherwise only the pieces of the
    hole that nothing covers are held, and only those at or over `floor` --
    the same `min_detail_mm²` the hole itself was judged by. ANY bare piece
    under that floor is released -- the anti-alias sliver between a piece and
    its hole's edge, and equally a small compact opening beside the piece --
    so the ground grows into it and reaches its tongue under the piece, the
    way every seam that was never held already does.
    """
    # Interiors must meet: a later shape that only TOUCHES the hole's edge
    # (on the ground, outside the hole) covers none of it, and must leave the
    # held polygon byte-identical to the engine without the flag.
    if covered is None or not hole.relate_pattern(covered, "T********"):
        return [hole]
    bare = hole.difference(covered)
    if bare.is_empty:
        return []
    parts = getattr(bare, "geoms", [bare])
    return [g for g in parts if g.geom_type == "Polygon" and g.area >= floor]


def _shares_edge(part, geom) -> bool:
    """True when `part` meets `geom` along an edge, not at a point: a union
    joined only at a vertex is two polygons, and `_largest_polygon` would
    drop the smaller. 1e-4 mm either side of a shared edge of 0.01 mm is
    1e-6 mm² of overlap."""
    x0, y0, x1, y1 = part.bounds
    m = 1e-2
    local = geom.intersection(Polygon([(x0 - m, y0 - m), (x1 + m, y0 - m),
                                       (x1 + m, y1 + m), (x0 - m, y1 + m)]))
    return (not local.is_empty) and part.intersection(local.buffer(1e-4)).area > 1e-6


def gap_bridges(regions: list[Region], gap_mm: float) -> tuple[dict[str, object], list[dict]]:
    """-> ({shape_id: the strip it closes}, [one record per bridged pair]).

    `cfg.forbid_gap_mm` (Law 26, defect 47): the bare fabric narrower than
    `gap_mm` between two STITCHED shapes on different layers, read off their
    ARTWORK, given to the one that sews first. The strip is the
    morphological closing of the pair at `gap_mm / 2` minus the pair — it
    fills exactly the fabric narrower than `gap_mm` between them and ends
    flush with their ends, where the plain "within `gap_mm` of both" lens
    would bulge past them — kept only where it lies within `gap_mm` of both
    (a notch of one shape's own is not a gap between two), where no other
    stitched shape's artwork already covers it, and where it touches both.
    Pieces under `gap_mm²` are dropped: they are the fillets the closing
    puts in every corner where two colours' edges meet at an angle, not a
    channel of fabric (a 90-degree corner's is 0.05 · gap², a 0.4 mm gap
    one gap long is already 0.5 · gap² and a real one runs far longer).

    Same-layer pairs are not gaps between colours — stage 5's corridor
    keeps those apart on purpose — and an unstitched shape is bare fabric
    by design, so neither takes part.
    """
    out: dict[str, list] = {}
    pairs: list[dict] = []
    sew = [r for r in regions if r.meta.get("stitched", True)]
    if gap_mm <= 0 or len(sew) < 2:
        return {}, pairs
    tree = STRtree([r.polygon for r in sew])
    half = gap_mm / 2.0
    floor = gap_mm * gap_mm
    reach: dict[int, object] = {}

    def near(k: int):
        if k not in reach:
            reach[k] = sew[k].polygon.buffer(gap_mm)
        return reach[k]

    for i, a in enumerate(sew):
        x0, y0, x1, y1 = a.polygon.bounds
        query = Polygon([(x0 - gap_mm, y0 - gap_mm), (x1 + gap_mm, y0 - gap_mm),
                         (x1 + gap_mm, y1 + gap_mm), (x0 - gap_mm, y1 + gap_mm)])
        for j in tree.query(query):
            j = int(j)
            b = sew[j]
            if b.meta["layer"] <= a.meta["layer"]:
                continue                 # only the EARLIER side builds; same layer never
            d = a.polygon.distance(b.polygon)
            if d >= gap_mm:
                continue
            lens = near(i).intersection(near(j))
            if lens.is_empty:
                continue
            # The closing is computed in a window round the lens: whole-shape
            # buffers would cost the full outline per pair, and a clip edge
            # 2 x gap from the lens cannot reach into it at radius gap / 2.
            lx0, ly0, lx1, ly1 = lens.bounds
            m = 2.0 * gap_mm
            win = Polygon([(lx0 - m, ly0 - m), (lx1 + m, ly0 - m),
                           (lx1 + m, ly1 + m), (lx0 - m, ly1 + m)])
            ca, cb = a.polygon.intersection(win), b.polygon.intersection(win)
            both = unary_union([ca, cb])
            strip = both.buffer(half).buffer(-half).difference(both).intersection(lens)
            if strip.is_empty:
                continue
            others = [sew[int(k)].polygon for k in tree.query(win) if int(k) not in (i, j)]
            if others:
                strip = strip.difference(unary_union(others))
            parts = [g for g in getattr(strip, "geoms", [strip])
                     if g.geom_type == "Polygon" and g.area >= floor
                     and g.distance(ca) < 1e-6 and g.distance(cb) < 1e-6]
            if not parts:
                continue
            out.setdefault(a.shape_id, []).extend(parts)
            pairs.append({"earlier": a.shape_id, "later": b.shape_id,
                          "gap_mm": round(float(d), 3),
                          "area_mm2": round(float(sum(g.area for g in parts)), 3)})

    # Where three colours crowd one patch of fabric, two strips overlap, and
    # stage 5 clips each shape by everything sewn before it -- so a strip
    # can come out of that clip cut off from its own shape, and a piece of
    # sewn polygon cut off from its shape is dropped (`_largest_polygon`):
    # fabric again. Settle it here, in sew order: each strip loses what an
    # earlier colour's strip already holds, and a piece that loses its
    # contact with its own shape goes to the earlier strip that cut it off,
    # which it touches by construction.
    #
    # The same holds for a strip on a piece of its shape that an EARLIER
    # colour's artwork cuts off from the rest (artwork polygons can overlap
    # a little): stage 5 keeps only the largest piece, so a strip on a
    # smaller one is dropped with it. It goes to the earlier colour too.
    layer_of = {r.shape_id: r.meta["layer"] for r in sew}
    art_of = {r.shape_id: r.polygon for r in sew}
    final: dict[str, object] = {}
    for sid in sorted(out, key=lambda s: layer_of[s]):
        mine = unary_union(out[sid])
        prior = [s for s in final if layer_of[s] < layer_of[sid]]
        if prior:
            mine = mine.difference(unary_union([final[s] for s in prior]))
        parts = [p for p in getattr(mine, "geoms", [mine])
                 if p.geom_type == "Polygon" and p.area >= 1e-6]
        if not parts:
            continue
        own = art_of[sid]
        x0, y0, x1, y1 = unary_union([own] + parts).bounds
        earlier_art = [sew[int(k)] for k in tree.query(Polygon(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
            if layer_of[sew[int(k)].shape_id] < layer_of[sid]]
        held_by = [(r.shape_id, r.polygon) for r in earlier_art] + [(s, final[s]) for s in prior]
        body = None
        if held_by:
            cut = unary_union([own] + parts).difference(unary_union([g for _, g in held_by]))
            body = _largest_polygon(cut)
        keep = []
        for part in parts:
            if _shares_edge(part, own) and (body is None or _shares_edge(part, body)):
                keep.append(part)
                continue
            for s, g in held_by:
                if _shares_edge(part, g):
                    final[s] = part if s not in final else unary_union([final[s], part])
                    break
        if keep:
            final[sid] = unary_union(keep)
    return final, pairs


_HAIR_TOUCH_MM = 0.1
# Rings the zone under the strands is shared out in (`_hairline_ground`):
# the split between two grounds is exact to reach / steps (0.15 mm at 40 wt).
_HAIR_SPLIT_STEPS = 8


def _hairline_ground(regions: list[Region], hairline: dict,
                     cfg: PipelineConfig, design_class: str = "flat",
                     tongue_mm: float = 0.0) -> dict[str, object]:
    """`cfg.hairline_over_ground`: what each ground shape fills UNDER the
    hairline strands sewn after it. -> {ground shape_id: geometry}.

    The pros' order for hair (docs/fine-detail-hair-research-2026-10-12.md
    §2): the ground goes down whole, then single-run strands on top. Stage 4
    traces a strand as its own shape and cuts it out of the ground — as a
    hole, or (a crossing network) by splitting the ground into cells — so
    today the ground stops at the strand's traced edge plus the underlap
    tongue, and a 0.40 mm run in a 0.45-0.7 mm slot leaves cloth beside it,
    worst at crossings (prototype finding 3).

    The ground's polygon as if the strands were never cut out is its
    morphological CLOSING across strand-width gaps: every earlier-sewn,
    non-strand shape touching a strand, unioned, grown by `reach` and shrunk
    back. A gap narrower than 2 x `reach` closes; the ground's own outline
    elsewhere does not move (a closing only fills). `reach` is the widest a
    strand can be and still be one: the blob check's factor times the
    block's hairline limit (1.2 mm at 40 wt). The strand's part of that
    closing — grown by the touch tolerance, because the strand and the
    ground's slot are two DP traces of one pixel edge — is shared out to the
    ground shapes by distance (nearest takes it), so a strand between two
    skin cells is filled to its middle from each side and a crossing core
    from its corners; what no fill ground reaches within `reach` is left.

    Only grounds that sew BEFORE the strand (an earlier layer) reach under
    it — a strand sewn first would be buried. Only FILL grounds: a narrow
    ground cell that sews as a satin column (stage 7 reads its tier on the
    artwork, `_comp_axis`) builds that column on the planned polygon, and a
    column with strand-shaped bulges along both rails decomposes worse —
    measured on the hair fixture, 2026-10-12: its satin cells lost half
    their stitches and opened bare patches INSIDE their own artwork. A satin
    ground keeps today's underlap tongue under the strand instead. A strand
    that is a bean letter is left to `ground_under`'s own rule. Candidate
    geometry, unsewn (ROADMAP gate 1): card block E (`card_E_ground.dst`)
    is the test."""
    strands = [r for r in regions
               if r.shape_id in hairline and not r.meta.get("bean_letter_spines")]
    if not strands:
        return {}
    bw = block_thread_wt(regions, cfg)
    satin_max = satin_ceiling_mm(cfg)
    grounds = [r for r in regions
               if r.shape_id not in hairline and r.meta.get("stitched", True)]
    if not grounds:
        return {}
    satin: dict[str, bool] = {}
    frags = set(getattr(hairline, "fragments", ()))

    def is_fill(g: Region) -> bool:
        if g.shape_id not in satin:
            satin[g.shape_id] = _comp_axis(g, cfg, satin_max, design_class)[1]
        return not satin[g.shape_id]
    tree = STRtree([g.polygon for g in grounds])
    pieces: dict[str, list] = {}
    for h in strands:
        reach = _HAIR_BLOB_FACTOR * machine.thread_profile(
            bw.get(h.thread_index, cfg.thread_wt)).hairline_max_width_mm
        # The per-strand gate (step 3): a shape with thick branches sews them
        # on the ladder, and the ground goes under the HAIRLINE parts only
        # (`measure`'s `hair_geom`). A shape that is hairline throughout has
        # none, and its whole polygon is the strand, as in step 2.
        hm = hairline[h.shape_id]
        hg = hm.get("hair_geom") if isinstance(hm, dict) else None
        hp = h.polygon if hg is None or hg.is_empty else hg
        mine = [grounds[int(i)] for i in tree.query(hp.buffer(_HAIR_TOUCH_MM))]
        mine = [g for g in mine
                if g.meta["layer"] < h.meta["layer"]
                and g.polygon.distance(hp) <= _HAIR_TOUCH_MM]
        if not mine:
            continue
        closed = unary_union([g.polygon for g in mine]).buffer(reach).buffer(-reach)
        # A ground cell too small to cover itself — a sliver the fragment
        # rule handed back, or a run/satin cell no bigger than a reach disk,
        # pinched between strands — is closed over like the strand is: on
        # the hair fixture these were nearly all the cloth left (2026-10-12).
        crumb_ids = {g.shape_id for g in mine
                     if g.shape_id in frags
                     or (not is_fill(g) and g.polygon.area <= math.pi * reach * reach)}
        zone = unary_union([hp.buffer(_HAIR_TOUCH_MM),
                            *[g.polygon for g in mine if g.shape_id in crumb_ids]]
                           ).intersection(closed)
        # The closing reads every ground. The zone is split among every
        # ground that is not a crumb; only FILL grounds keep their share — a
        # satin cell's share stays under its own underlap tongue, as today.
        claimers = [g for g in mine if g.shape_id not in crumb_ids]
        mine = [g for g in claimers if is_fill(g)]
        if zone.is_empty or not mine:
            continue
        # Shared out by distance, nearest ground first (a Voronoi split
        # grown in `_HAIR_SPLIT_STEPS` rings): each point of the zone goes
        # to ONE ground, so a strand between two cells is filled once, to
        # its middle from each side, not twice.
        near = {g.shape_id: zone.intersection(g.polygon.buffer(reach)) for g in claimers}
        given = []
        claimed = None
        for k in range(1, _HAIR_SPLIT_STEPS + 1):
            d = reach * k / _HAIR_SPLIT_STEPS
            ring = []
            for g in claimers:
                z = near[g.shape_id]
                if z.is_empty:
                    continue
                piece = z.intersection(g.polygon.buffer(d))
                if claimed is not None:
                    piece = piece.difference(claimed)
                if not piece.is_empty and piece.area > 1e-9:
                    if is_fill(g):
                        pieces.setdefault(g.shape_id, []).append(piece)
                        ring.append(piece)
                    else:
                        # A satin cell's share is given only as far as its
                        # own underlap tongue already covers it; the rest is
                        # left for the nearest fill ground below.
                        ring.append(piece.intersection(g.polygon.buffer(tongue_mm)))
                    claimed = piece if claimed is None else claimed.union(piece)
            if ring:
                given.extend(ring)
        # What no ground reached — the inside of a small loop of strands, a
        # cell of ground the tracer absorbed into the strand network, the
        # far side of a satin cell's tongue — goes whole to the NEAREST fill
        # ground within the reach, so the closing is filled where it closed.
        rest = zone.difference(unary_union(given)) if given else zone
        for part in (getattr(rest, "geoms", None) or [rest]):
            if part.is_empty or part.area < 1e-6 or part.geom_type != "Polygon":
                continue
            g = min(mine, key=lambda x: x.polygon.distance(part))
            if g.polygon.distance(part) <= reach:
                pieces.setdefault(g.shape_id, []).append(part)
    return {sid: unary_union(v) for sid, v in pieces.items()}


def resolve_overlaps(
    regions: list[Region], fabric: Fabric, cfg: PipelineConfig,
    design_class: str = "flat",
    hairline: dict | None = None,
) -> tuple[list[PlannedRegion], list[dict]]:
    """-> (planned regions in sew order, warnings).

    `design_class` is stage 0's verdict, forwarded only to keep the satin
    call `_comp_axis` makes (directional-comp path only) agreeing with the
    one stage 7 makes for the same shape — see `_comp_axis`'s docstring.
    Defaults to "flat" so every pre-existing caller needs no edit and keeps
    exactly today's classification.

    `hairline` is `stage6_hairline.hairline_candidates`' verdict (the shapes
    stage 7 will sew as one-thread runs), read only under
    `cfg.hairline_over_ground` — see `_hairline_ground`.
    """
    warnings: list[dict] = []
    if not regions:
        return [], warnings

    pull = max(0.0, fabric.pull_comp_mm)
    overlap = max(0.0, cfg.overlap_mm)
    hole_floor = cfg.min_detail_mm ** 2

    # Law 22. Off: one axis of None per shape, so every `_grow` below is the
    # `poly.buffer(pull)` this stage has always done, byte for byte.
    directional = bool(cfg.directional_comp) and pull > 0
    # `cfg.satin_rail_comp` (2026-09-09): a satin-tier shape keeps its
    # artwork polygon here and takes the pull on its rails in stage 6. The
    # tier is read with the same call directional comp uses, for the same
    # reason -- compensation must not be able to flip it. Widened lettering
    # is exempt: its column IS the grown polygon (see `sewn_footprint`).
    rail_comp = bool(getattr(cfg, "satin_rail_comp", False)) and pull > 0
    satin_max = satin_ceiling_mm(cfg)
    axis_by_id: dict[str, float | None] = {}
    satin_by_id: dict[str, bool] = {}
    for r in regions:
        axis, is_satin = (_comp_axis(r, cfg, satin_max, design_class)
                          if directional or rail_comp else (None, False))
        axis_by_id[r.shape_id] = axis if directional else None
        satin_by_id[r.shape_id] = is_satin

    layers = sorted({r.meta["layer"] for r in regions})
    by_layer = {L: [r for r in regions if r.meta["layer"] == L] for L in layers}

    # `cfg.forbid_gap_mm` (Law 26): a shape that sews before a neighbour it
    # is separated from by a sub-threshold strip of bare fabric plans as if
    # its artwork ran across the strip. Everything below then treats the
    # join as the ordinary seam it now is -- the tongue reaches under the
    # later colour from the strip's far edge, and the later colour, clipped
    # by what is already down, keeps its artwork edge. Off (None): no entry,
    # and every shape plans on its own artwork exactly as before.
    forbid = float(getattr(cfg, "forbid_gap_mm", None) or 0.0)
    span: dict[str, Polygon] = {}
    if forbid > 0:
        for sid, strip in gap_bridges(regions, forbid)[0].items():
            r = next(x for x in regions if x.shape_id == sid)
            # The strip's edge on the artwork is the artwork's own edge only
            # to floating point: a bare union can come back as two polygons
            # a femtometre apart (measured on bridge's lettering, 2 mm² of
            # strip dropped). A tenth of a micron of overlap welds them.
            joined = unary_union([r.polygon, strip.buffer(1e-4)])
            span[sid] = joined if joined.geom_type == "Polygon" else _weld_part(joined, r.polygon)

    def sewn_footprint(r: Region):
        """What a shape occupies on the fabric as far as the layers around
        it are concerned: its artwork — or, for widened lettering, its
        COLUMN, the artwork grown by the pull (no underlap tongue). The
        column is what sews, and the layers on either side have to plan
        against it: a ground that sews AFTER the lettering (largest-area-
        first thread order can put the lettering's thread first when that
        thread also holds the design's biggest shape) is clipped by this
        footprint and so leaves the column exposed, where clipping by the
        artwork buried 79% of it under the ground's own growth (measured
        2026-09-09, review of the first cut); a ground that sews BEFORE it
        reaches its tongue under the column, not just under the artwork.
        With `cfg.forbid_gap_mm`, the artwork includes the strip it spans."""
        art = span.get(r.shape_id, r.polygon)
        if widened_lettering(r):
            return _grow(art, pull, axis_by_id[r.shape_id])
        return art

    geom_by_layer = {L: unary_union([sewn_footprint(r) for r in by_layer[L]]) for L in layers}

    # `cfg.overlap_by_angle` (Law 26): each tatami fill's row angle in
    # stage 7's precedence (`seam_row_angles`); None keeps the scalar.
    # Off: nothing is built and the underlap below is the scalar it was.
    parallel = max(overlap, OVERLAP_FABRIC_FACTOR
                   * float(getattr(cfg, "overlap_parallel_mm", overlap) or 0.0))
    by_angle = bool(getattr(cfg, "overlap_by_angle", False)) and overlap > 0 and parallel > overlap
    row_angle: dict[str, float | None] = {}
    foot_regions: list[Region] = []
    foot_tree = None
    if by_angle:
        row_angle = seam_row_angles(regions, cfg, fabric, design_class)
        foot_regions = list(regions)
        foot_tree = STRtree([sewn_footprint(r) for r in foot_regions])

    def seam_overlap(a_deg: float, b_deg: float) -> float:
        d = math.radians((a_deg - b_deg) % 180.0)
        return overlap + (parallel - overlap) * abs(math.cos(d))

    def deep_reach(r: Region, poly, L: int):
        """The extra underlap a fill gets under each LATER fill its rows run
        near-parallel to: the seam's own depth, clipped to that neighbour."""
        a = row_angle.get(r.shape_id)
        if a is None:
            return None
        parts = []
        for i in foot_tree.query(poly.buffer(pull + parallel)):
            n = foot_regions[int(i)]
            b = row_angle.get(n.shape_id)
            if n.meta["layer"] <= L or b is None:
                continue
            ov = seam_overlap(a, b)
            if ov <= overlap + 1e-9:
                continue
            part = poly.buffer(pull + ov).intersection(sewn_footprint(n))
            if not part.is_empty:
                parts.append(part)
        return unary_union(parts) if parts else None

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

    # Bean letters (`cfg.bean_letter_max_stroke_mm`): a letter sewn as a
    # 0.4 mm line of thread along its ink no longer covers the hole its traced
    # shape left in the ground, so the ground it stands on sews THROUGH -- the
    # whole letter joins the one earlier shape it shares the most edge with.
    # No tag, no entry: byte-identical.
    ground_under: dict = {}
    for b_ in regions:
        if (not b_.meta.get("bean_letter_spines")
                or str(b_.meta.get("tier", "auto")).lower() != "auto"):
            continue
        edge = b_.polygon.boundary
        best, best_len = None, 0.0
        for r_ in regions:
            if (r_ is b_ or r_.meta["layer"] >= b_.meta["layer"]
                    or not r_.meta.get("stitched", True)):
                continue
            if r_.polygon.distance(b_.polygon) > 0.1:
                continue
            shared = edge.intersection(r_.polygon.buffer(0.1)).length
            if shared > best_len:
                best, best_len = r_, shared
        if best is not None:
            ground_under.setdefault(best.shape_id, []).append(b_.polygon)
    ground_under = {k: unary_union(v).buffer(0.1) for k, v in ground_under.items()}

    # Hairlines over their ground (`cfg.hairline_over_ground`, 2026-10-12
    # step 2): the same mechanism, for strands — the ground keeps its full
    # polygon under every strand sewn after it (`_hairline_ground`), and a
    # strand's slot in it is not held open as a counter (the hole check
    # below reads `under`). Off, or no strands: no entry, byte-identical.
    if (hairline and getattr(cfg, "hairline", False)
            and getattr(cfg, "hairline_over_ground", False)):
        for sid, geom in _hairline_ground(regions, hairline, cfg, design_class,
                                          tongue_mm=pull + overlap).items():
            prev = ground_under.get(sid)
            ground_under[sid] = geom if prev is None else prev.union(geom)

    # `cfg.held_hole_bare_only`: what later STITCHED colours cover, per
    # layer -- a suffix union like `later`, built only with the flag on. An
    # unstitched later shape is bare fabric by design and never covers a hole;
    # `plan_stitches` drops those before stage 5 anyway, but tools that pass
    # `result.regions` whole (`seam_underlap`, `sewn_compensation`) do not.
    bare_only = bool(getattr(cfg, "held_hole_bare_only", False))
    sewn_after: dict[int, object] = {}
    if bare_only:
        running = None
        for L in reversed(layers):
            sewn_after[L] = running
            mine = [sewn_footprint(o) for o in by_layer[L] if o.meta.get("stitched", True)]
            if mine:
                here = unary_union(mine)
                running = here if running is None else running.union(here)

    def later_sewn(L: int):
        return sewn_after.get(L)

    planned: list[PlannedRegion] = []
    holes_held = 0
    # The shapes, not just how many. A count answers "did anything go wrong";
    # only the id and the area answer "which shape, and is it a speck or my
    # logo" — and on the pro corpus (2026-08-14) this fired exactly once, on
    # `hotel_fremont_patch`, and the count alone gave nobody a way to tell
    # that 2.2 mm² from a dropped letter.
    lost: list[Region] = []
    fusing_pairs: set[tuple[str, str]] = set()

    # Defect 61, two halves. `cfg.clip_parent_keeps_ink` (default ON): a split
    # shape keeps the piece carrying the most ARTWORK, not the most sewn
    # area. `cfg.clip_keep_pieces` (default OFF): the other pieces carrying
    # enough artwork become regions of their own. Both off: every split below
    # goes through `_largest_polygon`, byte for byte.
    parent_ink = bool(getattr(cfg, "clip_parent_keeps_ink", True))
    keep_pieces = bool(getattr(cfg, "clip_keep_pieces", False))
    piece_floor = clip_piece_floor_mm2(cfg) if keep_pieces else 0.0
    slivers: list[tuple[str, float]] = []

    for sew_index, L in enumerate(layers):
        for r in by_layer[L]:
            poly = span.get(r.shape_id, r.polygon)
            axis = axis_by_id[r.shape_id]
            on_rails = rail_comp and satin_by_id[r.shape_id] and not widened_lettering(r)
            grown = poly if on_rails else _grow(poly, pull, axis)

            # Extend under whatever sews later — the underlap that hides the seam.
            if overlap > 0 and later[L] is not None:
                reach = poly.buffer(pull + overlap).intersection(later[L])
                if by_angle:
                    deep = deep_reach(r, poly, L)
                    if deep is not None:
                        reach = reach.union(deep)
                if not reach.is_empty:
                    grown = grown.union(reach)

            under = ground_under.get(r.shape_id)
            if under is not None:
                grown = grown.union(under)

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

            # Never grow back over a color that is already down — except
            # widened lettering. A glyph on a ground was vectorized as a hole
            # in that ground at its ORIGINAL width; the column floor then
            # redrew the glyph wider than its hole, and clipping it back here
            # is exactly how the floor sewed nothing (measured 2026-09-09 on
            # Fremont: every widened glyph classified on a 0.28 mm hole and
            # sewn as the hairline it was). Lettering sews OVER whatever is
            # already down — its ground, and any other earlier colour it
            # abuts, by the pull band the clip removes from everything else;
            # the pro's Fremont file lays its satin columns on the patch
            # fill — so the widened polygon keeps its growth here, and the
            # ground's underlap tongue still reaches under it as under any
            # later colour (`sewn_footprint`). Everything without the tag is
            # clipped exactly as before.
            if earlier[L] is not None and not widened_lettering(r):
                grown = grown.difference(earlier[L])

            # A bean letter sews the paths of its whole ink and a hairline
            # strand sews its whole ARTWORK polygon, so a piece the clip cuts
            # off them is sewn already: neither is split.
            pieces: list[Polygon] = []
            splittable = ((parent_ink or keep_pieces)
                          and not r.meta.get("bean_letter_spines")
                          and not (hairline and r.shape_id in hairline))
            if splittable:
                grown, pieces, dropped_ink = _split_clip(
                    grown, poly, piece_floor, by_ink=parent_ink, keep=keep_pieces)
                slivers.extend((r.shape_id, a) for a in dropped_ink)
            else:
                grown = _largest_polygon(grown)
            if grown is None or grown.is_empty:
                lost.append(r)
                continue

            # Growing the shell shrinks every hole by the same amount. A counter
            # that closes up is lost artwork, so any hole that would fall below
            # the sewable floor is held open at its original size instead.
            held: list[Polygon] = []
            n_holes = 0
            for ring in poly.interiors:
                hole = Polygon(ring)
                if hole.area < hole_floor:
                    continue           # already below the floor; stage 3's call
                if under is not None and hole.buffer(-0.05).within(under):
                    continue           # a bean letter's hole: sewn through, on purpose
                if _shrink(hole, pull, axis).area < hole_floor:
                    if r.shape_id in span and not any(
                            hole.equals(Polygon(o)) for o in r.polygon.interiors):
                        # `cfg.forbid_gap_mm`: a hole the closed strip narrowed
                        # down to the later colour sitting in it is a seam,
                        # not a counter -- holding it would strip the tongue
                        # off exactly the join the strip was closed for. Only
                        # what no later colour covers is held.
                        keep = _bare_part(hole, later[L], hole_floor)
                    else:
                        keep = (_bare_part(hole, later_sewn(L), hole_floor)
                                if bare_only and r.meta.get("stitched", True)
                                else [hole])
                    if keep:
                        held.extend(keep)
                        n_holes += 1
            if held:
                holes_held += n_holes
                cut = unary_union(held)
                if splittable:
                    # Same judgement for a split a held hole makes, and the
                    # cut-off pieces keep their share of the holes too.
                    grown, more, dropped_ink = _split_clip(
                        grown.difference(cut), poly, piece_floor,
                        by_ink=parent_ink, keep=keep_pieces)
                    slivers.extend((r.shape_id, a) for a in dropped_ink)
                    kept_after: list[Polygon] = []
                    for pc in pieces:
                        k_, d_ = _judge_pieces(pc.difference(cut), poly, piece_floor)
                        kept_after.extend(k_)
                        slivers.extend((r.shape_id, a) for a in d_)
                    pieces = kept_after + more
                else:
                    grown = _largest_polygon(grown.difference(cut))
                if grown is None or grown.is_empty:
                    lost.append(r)
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

            # `cfg.clip_keep_pieces`: each kept piece is a region of its own —
            # its share of the artwork, the parent's thread, tier and meta —
            # and the parent's artwork gives that share up, so a tier that
            # sews the ARTWORK (the run rung's outline) does not sew it twice.
            parent = r
            extra: list[PlannedRegion] = []
            if pieces:
                art_left = poly
                for k, pc in enumerate(pieces, start=2):
                    share = _largest_polygon(poly.intersection(pc))
                    if share is None:
                        continue
                    art_left = art_left.difference(pc)
                    meta = dict(r.meta)
                    meta[CLIP_PIECE_OF_KEY] = r.shape_id
                    sub = replace(r, shape_id=f"{r.shape_id}-clip{k}", polygon=share,
                                  area_mm2=float(share.area), meta=meta)
                    pv = None
                    if later[L] is not None:
                        v = pc.difference(later[L])
                        pv = None if v.is_empty else v
                    extra.append(PlannedRegion(region=sub, polygon=pc,
                                               sew_index=sew_index, visible=pv,
                                               covered_by=later[L],
                                               stitch_angle_deg=axis,
                                               satin_tier=satin_by_id[r.shape_id]))
                left = _largest_polygon(art_left)
                if extra and left is not None:
                    parent = replace(r, polygon=left, area_mm2=float(left.area))

            planned.append(PlannedRegion(region=parent, polygon=grown,
                                         sew_index=sew_index, visible=visible,
                                         covered_by=later[L],
                                         stitch_angle_deg=axis,
                                         satin_tier=satin_by_id[r.shape_id]))
            planned.extend(extra)

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
    if slivers:
        n = len(slivers)
        total = sum(a for _, a in slivers)
        warnings.append(
            warn(
                CLIP_DROPPED_SLIVER,
                f"{n} sliver{'s' if n != 1 else ''} of artwork ({total:.2f} mm²) cut "
                "off a shape by the colour sewn before it, too small to sew on "
                f"{'their' if n != 1 else 'its'} own, {'were' if n != 1 else 'was'} dropped.",
                count=n,
                ids=sorted({s for s, _ in slivers}),
                total_mm2=round(float(total), 3),
                largest_mm2=round(float(max(a for _, a in slivers)), 3),
                floor_mm2=round(float(piece_floor), 4),
                pieces=[{"id": s, "art_mm2": round(float(a), 3)} for s, a in slivers],
            )
        )
    if lost:
        biggest = max(lost, key=lambda r: r.area_mm2)
        total_mm2 = sum(r.area_mm2 for r in lost)
        size = (f"{biggest.area_mm2:.1f} mm² in thread {biggest.thread_number}"
                if len(lost) == 1 else
                f"{total_mm2:.1f} mm², largest {biggest.area_mm2:.1f} mm² in "
                f"thread {biggest.thread_number}")
        warnings.append(
            warn(
                SHAPE_NOT_STITCHED,
                f"{len(lost)} shape{'s' if len(lost) != 1 else ''} ({size}) "
                "disappeared while being fitted against neighbouring colors "
                f"and {'were' if len(lost) != 1 else 'was'} not stitched.",
                count=len(lost),
                ids=[r.shape_id for r in lost],
                threads=sorted({r.thread_number for r in lost}),
                total_mm2=round(float(total_mm2), 2),
                largest_mm2=round(float(biggest.area_mm2), 2),
            )
        )
    return planned, warnings
