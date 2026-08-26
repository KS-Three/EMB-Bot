"""Stage 7 — sew order within a color, lock stitches, and the jump/trim call.

Stage 5 fixed which thread goes first. What is left is the order shapes are
sewn inside one thread, and the housekeeping that decides whether a finished
design runs clean on a machine or produces a garment covered in loose ends:

- **Order within a color** is nearest-neighbour on the sewing geometry, not on
  centroids: the distance that matters is the one the needle travels, and a
  long thin shape's centroid can sit nowhere near the part of it the needle
  can actually reach. Order is settled BEFORE the stitches exist, because
  where a shape starts now depends on where the needle already is — stage 6
  takes `start_near` and enters the shape there. Generating first and ordering
  on the result meant every shape began at its own top-left corner and the
  needle was sent back across the design to get there.
  The review screen may pin a shape to an explicit slot in this order
  (`Region.meta["sew_order"]`, shape-layers contract v1.2) — nearest-neighbour
  still fills every slot no one pinned, so an unedited design, and every shape
  in an edited one that carries no override, sews exactly as before.
- **Ties.** A lock stitch goes in wherever the thread starts and wherever it is
  about to be cut. Without them the first stitches pull out the moment the
  garment is worn, which is the kind of defect that surfaces after delivery.
- **Link, jump or trim.** The needle only has to lift when the thread would
  show. Where the path between two shapes runs under a colour that sews later,
  or over work this colour has already laid, it is sewn as a needle-down link
  instead — 434 transitions in the professional corpus say distance is not what
  decides this (chaining laws 59-62), coverage is, and professionals link about
  two thirds of transitions at every gap out to 40 mm. Only where nothing will
  bury the path does the old rule apply: a short hop stays a jump, and anything
  past the fabric preset's trim distance is cut, because a float long enough to
  catch a finger is a float someone has to remove with scissors.

  Those two laws ship together on purpose. Linking on distance alone, without
  the coverage test, converts trims into visible floats on bare fabric — which
  is strictly worse than the trims it removes.

- **Photo depth sequencing** (photo plan §2 row 14) is also this module's
  vocabulary, even though `depth_sort_layers` runs BEFORE stage 5: the order
  color blocks sew in is `meta["layer"]`, and stage 5's whole underlap/
  coverage model (`covered_by`, "extend the color that sews FIRST underneath
  the one that sews after it") is built on that order — so a sequencing
  override that reordered blocks here, after stage 5 had already planned
  against the old order, would bury links under colors that no longer sew
  later and put seams on the wrong side of every boundary. The override
  therefore edits the layer order upstream (pipeline.run_stages calls it
  right after `compact_layers`) and everything downstream follows one
  consistent story. See `depth_sort_layers` for what "depth" can honestly
  mean today.
"""
from __future__ import annotations

import heapq
import math

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import machine, stitches
from .config import PipelineConfig
from .fabrics import Fabric
from .machine import FILL_ROW_MM, FILL_STITCH_MM, SATIN_MAX_WIDTH_MM, TINY_STITCH_MM
from .stage5_overlap import PlannedRegion
from .stage6_applique import applique_pass, nn_group_key
from .stage6_blend import SourcePixels, blend_fill
from .stage6_border import border_runs, run_outline
from .stage6_contour import contour_fill
from .stage6_detail import detail_runs
from .stage6_fill import stitch_shape
from .stage6_meander import meander_fill
from .stage6_scanline import scanline_fill
from .stage6_sketch import sketch_fill
from .stage6_satin import classify_ribbon, satin_shape
from .stage6_streamline import streamline_fill
from .stitches import StitchBlock, StitchRun
from .threads import chart_for
from .warnings_codes import (BLEND_NO_REGIONS_DECOMPOSED, BORDER_LIGHTENED,
                             BORDER_SEAM_SHARED,
                             BORDER_SKIPPED_TOO_NARROW,
                             CONTOUR_DIRECTIONAL_COMP_UNSEWN,
                             CONTOUR_RING_UNREACHABLE, LONG_JUMPS_TRIMMED,
                             SHAPE_NOT_STITCHED, SHAPE_TOO_THIN_TO_FILL,
                             SMALL_SHAPES_AS_RUN, warn)


# How many waypoints the link router may consider. The candidates are already
# filtered to those that could lie on a path inside this link's own budget, so
# this only caps the pathological case: a colour whose covering geometry packs
# thousands of vertices into that ellipse.
_LINK_SEARCH_NODES = 120

# The two stage-0 classes that engage photo sequencing (depth-sorted layers +
# the underlay split, plan §2 row 14). A caller may also opt any design in
# explicitly via cfg.extra["photo_sequencing"] — same knob, both halves.
# MIRRORED verbatim as stage6_satin._PHOTO_CLASSES (importing from here
# would cycle — this module imports stage6_satin); a membership change here
# must land there too, and tests/test_photo_width_floor.py pins the
# lockstep so drift fails loud instead of quietly un-flooring a new class.
from .config import PHOTO_CLASSES, is_photographic  # canonical copy lives in config.py

# Row 14's underlay split, expressed in the vocabularies the two tiers
# actually speak (fabrics.py's ids):
#  - Fill zones get a LIGHT MESH — edge run + one lattice pass — instead of
#    the fabric preset's own style. On stable fabrics that is roughly what
#    the preset already says; on nap presets (fleece/terry ship
#    double_lattice) it is the difference between a drawing and a board:
#    full-coverage photo work already sustains 2.0-3.5 st/mm2, and stacking a
#    heavy double lattice under it is the "stiff as a piece of wood" outcome
#    the plan's class (d) ceiling names.
#  - Satin details get a light spine run ("center_run" — satin's underlay
#    vocabulary has no separate edge-run id; its center run IS the single
#    light run under the column, and stage 6 still force-upgrades columns
#    wider than SATIN_ZIGZAG_ABOVE_MM to zigzag, which top details never
#    are) instead of a nap preset's zigzag.
#  - The meander/scanline/streamline/sketch tiers sew NO underlay by
#    construction (their emitters never call an underlay path — fabric-as-
#    value is those tiers' whole point, stage6_meander/stage6_streamline
#    docstrings), so row 14's "none under meander/sketch" needs no code
#    here; the tests pin it stays true.
_PHOTO_FILL_UNDERLAY = "edge_lattice"
_PHOTO_SATIN_UNDERLAY = "center_run"


def _rel_luminance(rgb: tuple[int, int, int]) -> float:
    """Rec. 709 relative luminance of a thread's chart RGB — the 'dark' in
    dark→light. Chart color, not source pixels, on purpose: it is the thread
    that goes down on the fabric, it exists for every class (photo runs do
    not carry source pixels unless a tonal tier asked for them), and it is
    deterministic per palette."""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def depth_sort_layers(regions, thread_indices: list[int], chart) -> list[int]:
    """Reorder color layers depth-sorted for photo classes (plan §2 row 14):
    background first, then dark→light, detail layers last. Mutates
    `regions`' meta["layer"] (and re-sorts the list into the stable
    layer/area/id order stage 4 promises) and returns `thread_indices`
    permuted to match, so the palette stays the sew-order thread list.

    Replaces the largest-area-first order stage 2 produced. That order is
    right for flat logos (big fields down first, small details last and
    crisp) and wrong for photo work, where the universal craft consensus is
    that winners read as drawings executed in thread: the scene is laid in
    back-to-front and shadow-to-highlight, so every later, lighter layer
    sits ON the darker ground the way a painter's highlight does — and a
    largest-area-first photo sews as a uniform scan conversion instead.

    What "depth" can honestly mean today, stated plainly:

    - **Background** is the one region-level background fact the pipeline
      has: `meta["enclosed_background"]` (stage 4's tag from stage 1's
      mask). A layer whose every stitched region carries it sews first.
    - **Dark→light** is the thread's own chart luminance (`_rel_luminance`),
      per layer — regions of one thread share a block, so within-object
      shade order IS the layer order of that object's shade ramp.
    - **Details last** keys on the review screen's explicit detail tiers: a
      layer whose every stitched region is pinned `tier` "run" or "satin"
      is a detail pass and sews last. The auto satin classifier is NOT a
      depth signal — a satin-classified ribbon may be a whole object.

    TRUE INSTANCE-LEVEL DEPTH — subject vs. mid-ground vs. sky, "the dog in
    front of the fence" — is not computable from any of that. It needs the
    photo plan's step-3 segmentation (rembg subject mask, SAM instance
    splits) to tag regions with which INSTANCE they belong to; when that
    lands, its tag slots in as a depth band between background and the
    dark→light ramp here, exactly the way `face_regions` is documented as
    the seam in stage2_photo_segment._face_local_threshold. Until then this
    function does not fake it, and the docstring says so instead.

    Ties break dark-first, then larger-first (the old order's spirit), then
    the old layer number — fully deterministic. Call AFTER `compact_layers`
    (layers dense 0..n-1, one thread per layer) and BEFORE
    `apply_layer_overrides`, so an explicit review-screen `layer` override
    still beats this default, the same way an explicit `sew_order` pin
    still wins within its layer (stage 7's picking loop is untouched).
    """
    if not regions:
        return list(thread_indices)
    layers = sorted({r.meta["layer"] for r in regions})
    by_layer = {L: [r for r in regions if r.meta["layer"] == L] for L in layers}

    def key(L: int):
        members = by_layer[L]
        # Unstitched regions (enclosed background hidden by default, review
        # deletions resolved earlier) put no thread down, so they get no
        # vote — unless they are all the layer has, in which case they are
        # the only evidence there is.
        basis = [r for r in members if r.meta.get("stitched", True)] or members
        if all(r.meta.get("enclosed_background") for r in basis):
            depth = 0
        elif all(str(r.meta.get("tier", "")).lower() in ("run", "satin")
                 for r in basis):
            depth = 2
        else:
            depth = 1
        lum = _rel_luminance(chart[thread_indices[L]].rgb)
        area = sum(r.area_mm2 for r in basis)
        return (depth, round(lum, 6), -round(area, 6), L)

    order = sorted(layers, key=key)
    remap = {old: new for new, old in enumerate(order)}
    for r in regions:
        r.meta["layer"] = remap[r.meta["layer"]]
    # Restore stage 4's stable output order under the new layer numbers —
    # the same re-sort apply_shape_edits/apply_layer_overrides already do.
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    return [thread_indices[L] for L in order]


def _link_budget_mm(direct_mm: float) -> float:
    """How much path this link may spend, in millimetres.

    Law 62 budgets links in stitches, and this is that budget expressed as
    length so the route search can prune with it: at least the median link
    (7 stitches), at most the p90 one (36), and in between no more than
    LINK_DETOUR_FACTOR times the gap it is crossing.
    """
    return min(machine.LINK_MAX_STITCHES * machine.RUN_STITCH_MM,
               max(machine.LINK_MEDIAN_STITCHES * machine.RUN_STITCH_MM,
                   direct_mm * machine.LINK_DETOUR_FACTOR))


def _densify(a: tuple[float, float], b: tuple[float, float],
             step_mm: float) -> list[tuple[float, float]]:
    """Points from a (exclusive) to b (inclusive), no step longer than step_mm.

    Deliberately a local copy of stage 6's helper rather than an import of its
    private: a link's pitch is a chaining law (61) and a fill bridge's is a
    fill decision, and the two are already different numbers.
    """
    d = math.dist(a, b)
    if d <= step_mm:
        return [b]
    n = math.ceil(d / step_mm)
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(1, n + 1)]


def _ring_points(geom) -> list[tuple[float, float]]:
    """Every boundary vertex of a polygon/multipolygon, or every point of a
    line/multiline, rings closed once."""
    parts = ([geom] if geom.geom_type in ("Polygon", "LineString")
             else [g for g in getattr(geom, "geoms", [])
                   if g.geom_type in ("Polygon", "LineString")])
    out: list[tuple[float, float]] = []
    for g in parts:
        if g.geom_type == "LineString":
            out.extend(g.coords)
            continue
        out.extend(g.exterior.coords[:-1])
        for ring in g.interiors:
            out.extend(ring.coords[:-1])
    return out


def _link_cover(runs: list[StitchRun], regions: list[PlannedRegion],
                run_tier_art=None):
    """Where this colour's needle may travel down without showing.

    -> (cover geometry, candidate waypoints), or (None, []) with nothing to go on.

    Law 60: professionals route a link to be COVERED, not to be short, and the
    corpus shows them using two kinds of cover. Geometry that sews LATER buries
    the link under another thread — that is `covered_by`, handed over by stage 5
    rather than recomputed here, since that colour's own stitches do not exist
    yet. Geometry this colour has ALREADY laid carries the link on top of
    itself, in its own thread — and by the time this runs, that thread is not a
    prediction, it is `runs`: the whole block has already been stitched, so the
    real sewn centrelines are sitting right here.

    A shape's sewing POLYGON is not that thread. A fill's first row sits half a
    row inside the boundary and drops non-monotone spans; a satin column stops
    short at its own tips and fans on curves. Routing a link under "the shape"
    instead of under "what the shape actually sewed" buries it under fabric no
    thread ever reached — measured on the benchmark as a 0.947 mm-deep hole in
    one satin column alone. So the already-laid half of the cover is built from
    `runs` directly: every non-TRAVEL run's centreline, buffered by the same
    LINK_COVER_TOL_MM the polygon edges get below. That buffer is exactly half
    of COVERAGE_THREAD_W_MM, so a centreline buffered by it is not a tolerance
    on top of the thread — it IS the thread, at its real physical width.

    Only shapes that actually produced stitches are passed in for `covered_by`.
    A shape that came back empty covers nothing, and routing a link under one
    would put a float on bare fabric — the exact defect this test exists to
    prevent.

    The cover is buffered by LINK_COVER_TOL_MM (the reach of the covering
    element's own edge thread, or half the width of the already-laid thread
    itself) for the containment test, while the waypoints come from the
    UNBUFFERED union: buffering rounds every corner into an arc and multiplies
    the vertex count for waypoints that say nothing new, and a vertex of the
    raw union sits a full tolerance inside the cover.

    Those waypoints are simplified by HALF the tolerance before they are taken.
    Simplification moves a vertex by at most that much, so every waypoint is
    still a half-tolerance inside the cover — and the corner detail it drops is
    detail no route needs, at a scale finer than the thread that would cover it.

    `covered_by` is still a future colour's sewing POLYGON, not its thread —
    that colour has not been planned yet, so its real path cannot be known
    here. What CAN be known is how far short of its polygon that thread will
    stop, because every tier's shortfall has been measured: so each future
    polygon is eroded by LINK_COVER_INSET_MM (see machine.py for the
    measurement) before it may bury anything. Geometry the erosion consumes
    entirely — a band thinner than twice the inset, a run-tier sliver whose
    outline run covers no interior — promises nothing, and a link it would
    have carried becomes a jump instead: the cheap direction to be wrong in.

    The inset alone is blind to TIER, and `run_tier_art` is that fix: a
    later shape that will sew as an outline RUN puts zero thread anywhere in
    its interior, so its shortfall is not a sub-millimetre boundary margin —
    it is the whole shape, however large. No inset bounds that. The caller
    passes the union of every later shape whose tier is predictably RUN
    (`sequence` computes it from the same predicate `stitch_one` routes on),
    and it is subtracted from `covered_by` before the erosion. Subtracting
    the whole polygon can also remove honest cover where a run-tier shape
    overlaps a genuine later fill — that is accepted on purpose: it can only
    turn a buriable link into a jump, never sew a float. Its outline run's
    own thread is deliberately NOT credited either: a single 0.4 mm bean
    line is not the kind of cover law 60's professionals route under.
    """
    laid: list[object] = []
    for i, r in enumerate(runs):
        if r.kind == stitches.TRAVEL:
            continue
        if len(r.points) >= 2:
            laid.append(LineString(r.points))
        elif r.points:
            # A one-point run is real thread too: export writes a plain
            # STITCH record for it, so the machine sews needle-down straight
            # through the point — the thread arrives from the previous run's
            # last penetration and leaves into the next run's first. A
            # 1-point LineString raises in shapely, so the sewn path is
            # rebuilt from the neighbours instead; each half only exists
            # where the needle stayed down (`jump` False on the run the
            # segment enters).
            pts: list[tuple[float, float]] = []
            if not r.jump and i > 0 and runs[i - 1].points:
                pts.append(runs[i - 1].points[-1])
            pts.append(r.points[0])
            if i + 1 < len(runs):
                nxt = runs[i + 1]
                if not nxt.jump and nxt.points:
                    pts.append(nxt.points[0])
            if len(pts) >= 2:
                laid.append(LineString(pts))
    parts: list[object] = list(laid)
    seen: list[object] = []
    for p in regions:
        c = p.covered_by
        if c is not None and not c.is_empty and not any(c is s for s in seen):
            seen.append(c)
            if run_tier_art is not None and not run_tier_art.is_empty:
                c = c.difference(run_tier_art)
                if c.is_empty:
                    continue
            g = c.buffer(-machine.LINK_COVER_INSET_MM)
            if not g.is_empty:
                parts.append(g)
    parts = [g for g in parts if g is not None and not g.is_empty]
    if not parts:
        return None, []
    raw = unary_union(parts)
    if raw.is_empty:
        return None, []
    # Buffer each part on its own and union the results, rather than buffering
    # the assembled union in one call — mathematically identical (a Minkowski
    # buffer distributes over union), but not computationally identical. A
    # block's own fill rows sit LINK_COVER_TOL_MM*2 apart, and GEOS's buffer of
    # one large network of many near-parallel, near-touching lines has to node
    # and union every offset curve against every other internally; buffering
    # each row alone is cheap (it is a single simple line) and the union of the
    # resulting simple capsules is cheap too. Same geometry, the order that
    # does not fall off GEOS's performance cliff.
    cover = unary_union([g.buffer(machine.LINK_COVER_TOL_MM) for g in parts])
    shapely.prepare(cover)
    lean = raw.simplify(machine.LINK_COVER_TOL_MM / 2.0)
    return cover, _ring_points(raw if lean.is_empty else lean)


def _link_route(a: tuple[float, float], b: tuple[float, float], cover,
                waypoints: list[tuple[float, float]]
                ) -> list[tuple[float, float]] | None:
    """Shortest path from a to b that never leaves `cover`, or None.

    The straight segment is the floor and answers most transitions. Where it
    does not, the route bends into the covering geometry instead of giving up —
    which is the whole of law 60: a 27 mm link shows no float because it was
    routed under something, not because it was short. Shortest-path over a
    visibility graph on the cover's own corners, pruned to the waypoints that
    could lie on a path within budget (dist(a,v) + dist(v,b) <= budget is
    exactly the ellipse a feasible detour must stay inside).

    Every segment of the returned path has been tested against `cover`, so the
    caller may sew it without re-checking: coverage is a property of the route
    by construction, not an assertion made about it afterwards.
    """
    if cover is None:
        return None
    if cover.covers(LineString([a, b])):
        return [a, b]

    budget_mm = _link_budget_mm(math.dist(a, b))
    inside = [v for v in waypoints
              if math.dist(a, v) + math.dist(v, b) <= budget_mm]
    if not inside:
        return None
    inside.sort(key=lambda v: math.dist(a, v) + math.dist(v, b))
    pts = [a, *inside[:_LINK_SEARCH_NODES], b]
    n = len(pts)
    end = n - 1

    best = [math.inf] * n
    prev = [-1] * n
    done = [False] * n
    best[0] = 0.0
    heap: list[tuple[float, int]] = [(0.0, 0)]
    while heap:
        d, u = heapq.heappop(heap)
        if done[u]:
            continue
        done[u] = True
        if u == end:
            break
        for v in range(n):
            if done[v] or v == u:
                continue
            nd = d + math.dist(pts[u], pts[v])
            # Both cheap tests first: a segment test is the expensive part, and
            # most candidate edges are already too long to be worth one.
            if nd > budget_mm or nd >= best[v]:
                continue
            if not cover.covers(LineString([pts[u], pts[v]])):
                continue
            best[v] = nd
            prev[v] = u
            heapq.heappush(heap, (nd, v))

    if not done[end]:
        return None
    route: list[tuple[float, float]] = []
    u = end
    while u != -1:
        route.append(pts[u])
        u = prev[u]
    route.reverse()
    return route


def _link_stitches(route: list[tuple[float, float]]) -> list[tuple[float, float]] | None:
    """A route's interior stitch positions at link pitch, or None if too dear.

    The endpoints belong to the runs on either side and are not repeated, the
    same convention stage 6's in-shape bridges use.

    Law 62 budgets a link in STITCHES, not millimetres — the median link is 7
    stitches and a link is short in stitches even when long in millimetres — so
    a legal-but-enormous route is refused here rather than silently costing
    more than the trim it replaced.
    """
    pts: list[tuple[float, float]] = []
    for a, b in zip(route, route[1:]):
        pts.extend(_densify(a, b, machine.RUN_STITCH_MM))
    inner = pts[:-1]
    if len(inner) > machine.LINK_MAX_STITCHES:
        return None
    return inner


def _chain(runs: list[StitchRun], regions: list[PlannedRegion], base_thread: int,
           run_tier_art=None) -> tuple[list[StitchRun], int]:
    """Sew every needle-up move this colour can bury. -> (runs, in-shape links).

    Runs in one pass over the finished block, after every shape has stitched,
    because that is the first moment the full covering geometry is known — and
    because it makes ONE rule govern every needle lift in the block, the ones
    stage 6 raised inside a shape as well as the ones this stage raised between
    them. Stage 6 decides on the shape's own polygon, which is all it can see;
    it cannot know that the gap it is jumping is about to be covered by the next
    colour, and on the benchmark that blind spot is eight of its ten trims.

    `runs[0]` is never touched. The thread is always cut into a new colour, and
    a link across a colour change would be sewn in the wrong thread. That same
    law now also guards every `shade_thread_index` boundary: `runs` is still
    the whole group's flat list at this point (block assembly partitions it
    into one StitchBlock per shade AFTER this returns), so without the guard
    a gap between two different accepted shades could bury itself under
    nearby same-block thread the way an ordinary same-colour gap does — legal
    today only because every shade still sewed in the group's one thread.
    Once shade partitioning splits them into separate blocks that link would
    cross a colour it does not share, so it is refused here, at the one
    place both the runs and their shade keys are still in one list together.

    `base_thread` is the same group thread `_shade_blocks` (below) receives —
    the guard compares `shade_thread_index` values normalized the identical
    way `_shade_blocks` buckets them (`None` reads as `base_thread`, F7,
    2026-08-19), so a run that never went through the blend tier bridges
    cleanly into one explicitly carrying the group's own base thread; only a
    REAL cross-shade boundary refuses. Before this normalization the raw `!=`
    compared `None` against an explicit `base_thread` as unequal, refusing a
    bridge that cost nothing to bury — a needless trim on any design where
    chaining and a base-thread-tagged run met.

    The returned count is how many of the links replaced a lift INSIDE a shape,
    so the operator-facing "the thread had to be lifted N times inside a shape"
    warning still reports what the machine will actually do.

    Distance is refused a vote on everything except the far end of the range.
    Law 59's curve is flat out to 40 mm and then turns over, so a gap wider than
    LINK_MAX_GAP_MM is left to the needle even when the geometry would bury it —
    see that constant for why the knee and not the p90, and why the two errors
    are not worth trading evenly.
    """
    if len(runs) < 2 or not regions:
        return runs, 0
    cover, waypoints = _link_cover(runs, regions, run_tier_art)
    if cover is None:
        return runs, 0

    def shade_key(st: int | None) -> int:
        return base_thread if st is None else st

    out = [runs[0]]
    in_shape = 0
    for run in runs[1:]:
        if not run.jump:
            out.append(run)
            continue
        if shade_key(out[-1].shade_thread_index) != shade_key(run.shade_thread_index):
            # Refused independent of geometry: burying this gap would sew a
            # bridge in one shade's thread across into another's block.
            # Normalized through `shade_key` the same way `_shade_blocks`
            # buckets (`None` reads as `base_thread`), so every existing
            # caller — whose runs carry `shade_thread_index=None` on both
            # sides of every boundary — still normalizes to
            # `base_thread == base_thread` and stays a no-op, same as
            # before this guard existed.
            out.append(run)
            continue
        a, b = out[-1].points[-1], run.points[0]
        if math.dist(a, b) > machine.LINK_MAX_GAP_MM:
            out.append(run)
            continue
        route = _link_route(a, b, cover, waypoints)
        inner = _link_stitches(route) if route is not None else None
        if inner is None:
            out.append(run)
            continue
        if run.shape_id == out[-1].shape_id:
            in_shape += 1
        if inner:
            # Tagged with the shade both sides already share (the guard
            # above refused this bridge otherwise) — untagged, it would
            # default to the group's own region thread and land in the
            # WRONG bucket once block assembly partitions `runs` by shade,
            # stranding a travel stitch between two runs of a block it is
            # not actually in.
            out.append(StitchRun(points=inner, kind=stitches.TRAVEL,
                                 shape_id=run.shape_id,
                                 shade_thread_index=run.shade_thread_index))
        run.jump = False
        run.trim = False
        out.append(run)
    return out, in_shape


# Lock-stitch application for a finished block. Hoisted verbatim to
# `stitches.apply_ties` so the appliqué fall-through (stage6_applique) can tie
# its plain-stitching block by the same rule; the local name is kept because
# every call site and comment in this module reads `_apply_ties`.
_apply_ties = stitches.apply_ties


def _shade_blocks(ordered: list[StitchRun], base_thread: int, chart,
                  trim_at: float) -> list[StitchBlock]:
    """One group's finished, chained run list -> one StitchBlock per shade,
    dark to light.

    Task 1 (photo/tonal v1): a blend-tier run carries the thread its OWN
    shade snapped to (`shade_thread_index`, stamped by `blend_fill`'s band
    loop); every other run carries `None` and falls back to `base_thread`
    (the group's `region.thread_index`), exactly as if this partition were
    never taken — a design with no blend runs buckets everything into that
    ONE key and reproduces the pre-Task-1 single block byte-for-byte.

    Bucketing (not a contiguous re-slice) because `_choose_shade_count`'s
    bands walk the ramp's own spatial `t`, not chart lightness — two
    non-adjacent bands can snap to the same cone, and they belong in the
    same block when they do. A run REJOINING a bucket some other shade's
    runs already interrupted (in `ordered`'s own spatial order) has its
    jump/trim recomputed against the neighbour it will actually follow —
    this bucket's own last run so far, not whatever ran right before it in
    the ramp's band order, which is the wrong question once that other
    shade sews as its own separate block. Plain distance, the same rule
    stage 7 already uses to splice unrelated shapes into one group (in
    `sequence`, above the call site) — no `_chain` retry, since two runs
    that were never flat-adjacent in `ordered` never had the chance to be
    considered for a chain bridge either (`_chain`'s own shade guard is
    what makes that refusal necessary in the first place — see its
    docstring).

    `_apply_ties` runs once per bucket here, not once on the flat `ordered`
    list the way it ran before this task existed: a tie protects the block
    it opens or closes, and once bucketing can pull two flat-sequence-
    separated runs into the same final block (the same-cone case above),
    `ordered`'s own trim flags stop marking where the real seams are — only
    the bucket knows that now. Every bucket's own first run is forced
    `jump=True, trim=True` unconditionally, not just for buckets past the
    first — dark -> light sorting can, and often will, put a different
    bucket first than whichever one happened to start the flat sew order.
    """
    shade_buckets: dict[int, list[StitchRun]] = {}
    bucket_order: list[int] = []
    prev_key = None
    for idx, run in enumerate(ordered):
        key = run.shade_thread_index
        if key is None:
            key = base_thread
        bucket = shade_buckets.get(key)
        if bucket is None:
            bucket = shade_buckets[key] = []
            bucket_order.append(key)
        elif idx > 0 and prev_key != key:
            prev_run = bucket[-1]
            d = math.dist(prev_run.points[-1], run.points[0])
            run.jump = d >= TINY_STITCH_MM
            run.trim = run.jump and d > trim_at
        bucket.append(run)
        prev_key = key

    # Dark -> light by the chart's own L*, the plan contract's sew order for
    # a region's shade blocks. Chart index breaks an exact-L* tie so the
    # order is deterministic (mirrors `Chart.nearest_index`'s own tiebreak).
    bucket_order.sort(key=lambda k: (chart.lab[k][0], k))
    out: list[StitchBlock] = []
    for key in bucket_order:
        shade_runs = shade_buckets[key]
        shade_runs[0].jump = True
        shade_runs[0].trim = True
        _apply_ties(shade_runs)
        thread = chart[key]
        out.append(
            StitchBlock(
                thread_index=key,
                thread_number=thread.number,
                rgb=tuple(thread.rgb),
                runs=shade_runs,
            )
        )
    return out


# Hair-width: stage 5 makes two abutting shapes' visible edges the identical
# curve (float noise aside), so this only has to bridge floating-point slop,
# never a real gap. Same order as stage6_border's own `_SLACK_MM`.
_BORDER_SEAM_EPS_MM = 0.02


def _polygonal_boundary(geom):
    """`geom.boundary`, but defined for a GeometryCollection too.

    Shapely returns **None** for `GeometryCollection.boundary` (2.1.2), and
    stage 5's overlap resolution can leave a shape's visible geometry as a
    collection — a polygon plus a degenerate sliver the difference could not
    remove. `_seam_band` then did `.boundary.buffer(...)` on None and took the
    whole `plan_stitches` call down with an AttributeError, not a warning.
    Never fired in production because `border` was "off" for everything;
    `photo_dof_meadow.png` hits it the moment borders are on (regression:
    tests/test_border.py::test_geometry_collection_visible_geom_does_not_crash).

    Taking the polygonal parts first gives the identical boundary for every
    geometry that already had one, and None — not a crash — for one with no
    area to bound at all.
    """
    edge = getattr(geom, "boundary", None)
    if edge is not None:
        return edge
    polys = [g for g in getattr(geom, "geoms", ())
             if g.geom_type in ("Polygon", "MultiPolygon")]
    if not polys:
        return None
    return unary_union(polys).boundary


def _raggedness(geom) -> float:
    """The WORST isoperimetric ratio (perimeter^2 / 4*pi*area) among the
    shape's own rings. 1.0 is a circle; higher is a more contorted outline for
    the area it encloses.

    The "abrupt" half of the `significant` border gate. Scale-free by
    construction, so it says the same thing about a shape at 30 mm and at
    90 mm — which is what makes it safe to compare against one constant.

    It measures MACRO SHAPE SPRAWL, not edge noise, and the distinction is
    load-bearing (established 2026-08-25 — the gate's first comment claimed
    the opposite). Stage 4 already simplifies every contour with
    Douglas-Peucker at `cfg.simplify_tol_mm` (0.2 mm) and meets it to within
    0.002 mm, so there is no pixel staircase left at the polygon's own scale
    for a border to trace. What a high number marks is a multi-armed shape:
    owl_kent's three largest regions have solidity 0.873 / 0.476 / 0.329, and
    Gaussian smoothing at 8.6x the simplify tolerance moves the worst one by
    0.04. That is a segmentation output, not a contour-quality one — reaching
    for a smoother to lower it is a measured negative, not a fix.

    PER RING, not per shape (fixed 2026-08-25, hours after the gate shipped).
    A border is sewn as one closed circuit PER RING — `stage6_border`'s own
    contract: "A shape with a hole has two visible edges, so it has two
    borders." Measuring the whole shape at once summed every ring's perimeter
    over the hole-subtracted area, which conflated "contorted outline" with
    "thin" and got a smooth annulus flatly wrong: a clean ring of outer 10 /
    inner 8 scored 9.0 and was refused a border, 32.3 at inner 9.4 — when a
    ring is the IDEAL border candidate (a letter O, a badge outline). Per
    ring every one of those reads 1.0, which is what they are.

    That failure was the gate quietly measuring WIDTH, and width is already
    handled downstream and better: `border_runs` lightens a shape too thin to
    host a column to a bean run, and refuses a hairline outright. The gate was
    doing that job a second time, worse, by accident.

    Costs nothing on real content — `owl_kent` borders the same 4 shapes of 35
    either way — and it still keeps ragged shapes out for the right reason:
    that owl's head carries TEN holes and its worst ring reads 4.02, clear of
    the 3.5 cutoff. (Judging only the exterior ring also fixes the annulus,
    but drops the same head to 3.77 — a 7% margin where this keeps 15%.)
    """
    parts = ([geom] if getattr(geom, "geom_type", "") == "Polygon"
             else [g for g in getattr(geom, "geoms", ())
                   if g.geom_type == "Polygon"])
    worst = 0.0
    for part in parts:
        for ring in [part.exterior, *part.interiors]:
            enclosed = Polygon(ring).area
            if enclosed <= 0.0:
                return math.inf
            worst = max(worst, (ring.length ** 2) / (4.0 * math.pi * enclosed))
    return worst or math.inf


def _border_worthy(geom, total_area: float, share_min: float,
                   iso_max: float) -> bool:
    """Kent's rule (2026-08-25): border a shape that is SIGNIFICANT and not
    ABRUPT. Significant = it carries a real share of the design. Abrupt = its
    outline is contorted enough that a border would trace the raggedness in a
    contrasting texture rather than cover it.

    Returns False rather than raising on a degenerate shape: a zero-area
    fragment is neither significant nor borderable, and stage 7 must not die
    on one (see `_polygonal_boundary` for what that failure looked like).
    """
    area = getattr(geom, "area", 0.0) or 0.0
    if total_area <= 0.0 or area <= 0.0:
        return False
    if (area / total_area) < share_min:
        return False
    return _raggedness(geom) < iso_max


def _seam_band(a_geom, b_geom) -> tuple[object | None, float]:
    """-> (the coincident strip between two shapes' own edges, its length).

    `stage6_border`'s KNOWN LIMITATION: two border-enabled shapes that abut
    get the identical line for a visible edge (stage 5's overlap resolution),
    so their outline circuits would ride it at full density each — a
    double-thick bar in two threads. Buffering each shape's boundary by a
    hair-width epsilon and intersecting turns "same curve" into an ordinary
    polygon overlap; the strip is `2 * eps` wide everywhere but the end caps,
    so its AREA divided by that width recovers the coincident length without
    walking the curve. `(None, 0.0)` when the edges do not coincide at all.
    """
    a_edge, b_edge = _polygonal_boundary(a_geom), _polygonal_boundary(b_geom)
    if a_edge is None or b_edge is None:
        return None, 0.0
    shared = (a_edge.buffer(_BORDER_SEAM_EPS_MM)
             .intersection(b_edge.buffer(_BORDER_SEAM_EPS_MM)))
    if shared.is_empty:
        return None, 0.0
    return shared, shared.area / (2.0 * _BORDER_SEAM_EPS_MM)


def _border_seam_pairs(geoms: dict[str, object], threshold_mm: float
                       ) -> list[tuple[str, str, float]]:
    """Shape-id pairs whose OWN edges run coincident for over `threshold_mm`.

    Pure geometry, order-independent — used by tests and diagnostics to find
    every seam a design has, regardless of whether `_yield_frontage` (below)
    already resolved it. Production code no longer calls this for the
    `BORDER_SEAM_SHARED` warning: that is now driven by which seams the
    sew-order fix actually could not resolve, tracked incrementally as shapes
    sew (see `sequence`'s `border_seam_unresolved`), not recomputed here after
    the fact.
    """
    ids = sorted(geoms)
    out: list[tuple[str, str, float]] = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            _band, length = _seam_band(geoms[a], geoms[b])
            if length > threshold_mm:
                out.append((a, b, length))
    return out


def _yield_frontage(
    visible_geom, committed: dict[str, object], width_mm: float,
    threshold_mm: float,
) -> tuple[object, list[tuple[str, float]]]:
    """`visible_geom` pulled back off any seam it shares with an
    ALREADY-COMMITTED border. -> (geometry to hand `border_runs`, unresolved
    seams as `[(other_shape_id, shared_length_mm), ...]`).

    THE REAL FIX for `stage6_border`'s KNOWN LIMITATION. `committed` holds
    only shapes whose border has already been traced — every shape that will
    ever compete with this one for the same seam has, by the time this runs,
    either already committed a real border (and is in here) or has not (and
    there is nothing to yield to). That is what makes the tie-break SEW
    ORDER: whichever shape's thread is already on the fabric keeps the seam;
    whatever sews after it steps back. No lookahead, no second pass, and no
    pair can end up with neither shape covering the seam or both riding it —
    see the call site in `sequence` for why the causal ordering guarantees
    that.

    The retreat is `width_mm` (the full column) plus `BORDER_HOST_MARGIN_MM`
    of slack for the corner relaxation's own inward bite — the same margin
    `stage6_border`'s own `core` check adds around the column before it will
    call a host "wide enough" — applied by DIFFERENCING a buffered band
    around the coincident curve: "inset its border circuit locally", so a
    ring stays a ring and `stage6_border` never has to know a seam was
    involved. A shape whose entire frontage IS the seam — hemmed in by more
    than one already-bordered neighbor, nothing left to retreat to — falls
    back to the untouched geometry rather than erasing its border outright
    (the same "better a sharp border than no border" call `round_inward`
    already makes when its own relaxation eats a shape whole), and every
    seam that produced it is reported back unresolved.
    """
    if not committed:
        return visible_geom, []
    bands: list[tuple[str, object, float]] = []
    for other_id, other_geom in committed.items():
        band, length = _seam_band(visible_geom, other_geom)
        if band is not None and length > threshold_mm:
            bands.append((other_id, band, length))
    if not bands:
        return visible_geom, []
    try:
        zone = unary_union([b for _id, b, _len in bands]).buffer(
            width_mm + machine.BORDER_HOST_MARGIN_MM)
        trimmed = visible_geom.difference(zone)
    except Exception:
        return visible_geom, []
    if trimmed.is_empty or trimmed.area < 1e-6:
        return visible_geom, [(oid, length) for oid, _b, length in bands]
    return trimmed, []


def _border_seam_warning(unresolved: list[tuple[str, str, float]]) -> dict | None:
    """`BORDER_SEAM_SHARED`, built from the seams `_yield_frontage` could not
    resolve — or `None` when every shared seam this design had was.

    Split out from `sequence` so the wiring from "a shape's retreat erased
    its own border" to "the operator hears about it" is one small function a
    test can call directly with a synthetic list, without reconstructing a
    whole design that hits the exact geometry `_yield_frontage`'s fallback
    needs.
    """
    if not unresolved:
        return None
    n = len(unresolved)
    return warn(
        BORDER_SEAM_SHARED,
        f"{n} pair{'s' if n != 1 else ''} of bordered shapes share an outline "
        "seam too fully to separate automatically — both circuits still ride "
        "the same line and will sew as one doubled bar. Turn border off on "
        "one side of the seam.",
        count=n,
        pairs=[[a, b] for a, b, _length in unresolved],
    )


def sequence(
    planned: list[PlannedRegion], fabric: Fabric, cfg: PipelineConfig,
    source_pixels: SourcePixels | None = None,
    design_class: str = "flat",
    fill_technique: str | None = None,
    streamline_mode: str | None = None,
    detail_layer: bool | None = None,
    palette_spools: list[int] | None = None,
) -> tuple[list[StitchBlock], list[dict]]:
    """-> (blocks in sew order, warnings).

    `design_class` is stage 0's verdict (PipelineResult.design_class, handed
    through by plan_stitches). Only the photo classes change anything here —
    the underlay split below; flat and gradient take byte-identical paths,
    which is why the default is "flat" and every pre-existing caller needs
    no edit.

    `fill_technique`/`streamline_mode`/`detail_layer` (Task 3, photo/tonal
    v1 spec decision 3 — `fill_technique`/`streamline_mode` fix round 1,
    `detail_layer` fix round 2): the EFFECTIVE values `plan_stitches`
    resolved via `pipeline.auto_photo_tier`, threaded in as explicit
    parameters — never by mutating `cfg` (jobs cache on it) — the same
    pattern Task 2 used to thread `effective_split_tonal`'s resolved value
    into `stage2_photo_segment.segment`. All three default `None`, meaning
    "no override, read `cfg.fill_technique`/`cfg.streamline_mode`/`cfg.
    detail_layer` exactly as before"; every pre-existing caller (every call
    site before fix round 1, including every test that builds a plan
    directly via this function) passes none of them and is byte-identical
    by construction. `plan_stitches` is the one caller that resolves and
    passes real values, and only when `auto_photo_tier` actually fires
    (photo_subject, no explicit `fill_technique`/`detail_layer`) — every
    other class, and an explicitly-configured photo_subject, gets `None`
    back from that helper and this function reads `cfg` exactly as it
    always has. `detail_layer` additionally resolves `True` only when a
    face was actually detected (`PipelineResult.faces_present` — round 2's
    own field, a runtime fact `plan_stitches` cannot recompute the way it
    recomputes the tier decision) — see `plan_stitches`' own comment at its
    call site for the exact formula, identical to `run_stages`' own
    `effective_detail_layer` (the one the `PHOTO_AUTO_TIER` warning's text
    already promises).

    `palette_spools` (2026-08-23, `cfg.shade_palette_demand`'s EXPERIMENT):
    the full stage-2 demand palette — `PipelineResult.palette_spools`,
    threaded by `plan_stitches` — whose ANCHOR spools (selected for the
    shades, claimed by no region's own mean) join the shade bind's allowed
    set below. Read only inside the bind derivation, and only when
    `cfg.shade_palette_demand` is itself on: a re-plan of a demand-built
    generation with the flag turned off must ignore the stale carrier, the
    same explicit-config-wins posture every other resolved parameter here
    keeps. None (every pre-existing caller, every non-demand run) is
    byte-identical to the parameter not existing.
    """
    row_mm = (cfg.fill_row_mm or FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    # Task A2: satin gets the same fabric-scaled density the fill row spacing
    # already has — the browser engine's own digitize.js already multiplies
    # ITS satin spacingMm by fabric.densityAdjust (src/digitize.js line
    # ~574); the Python engine had left satin at the bare SATIN_SPACING_MM
    # constant regardless of fabric, the one place the two engines disagreed
    # on how a fabric preset reaches density. max(0.1, ...) mirrors row_mm's
    # own floor so a pathological preset cannot collapse spacing to zero.
    satin_spacing_mm = machine.SATIN_SPACING_MM * max(0.1, fabric.density_adjust)
    stitch_mm = cfg.fill_stitch_mm or FILL_STITCH_MM
    # Row 14's underlay split (see _PHOTO_FILL_UNDERLAY above for the craft
    # case). Precedence is unchanged in shape, only the FALLBACK moves: an
    # explicit cfg.underlay_style still wins over the class default exactly
    # as it wins over the fabric preset, the design-wide `underlay` off
    # switch still zeroes both, and the per-shape meta["underlay_style"]
    # override still beats all of it both ways (`eff_underlay_style` in
    # stitch_one — its documented "beats the mode both ways" contract).
    photo = (is_photographic(cfg, design_class)
             or bool(cfg.extra.get("photo_sequencing")))
    # The shade-palette bind (cfg.shade_palette_bind — default ON since
    # Kent's 2026-08-24 ruling; config.py's own comment and
    # docs/superpowers/plans/2026-08-23-shade-palette-binding.md option (a)
    # carry the full case): the spools
    # this plan's own regions sew, handed to the layered streamline tier so
    # its per-shade chart snap stays inside them (`_shade_layers`' masked
    # argmin + adjacent-same-spool merge). Derived from `planned` — the
    # post-edit, post-skip, post-resnap region set actually being sequenced —
    # not from `select_palette`'s raw stage-2 choice, because a review-screen
    # recolor legitimately adds a cone to the list and the bind's whole point
    # is "spools the operator will load", which by this stage is the regions'
    # own thread set (the per-layer cone list is compacted FROM it). Gated on
    # the strict class verdict, NOT the `photo` sequencing bool above: the
    # `photo_sequencing` extra opts a flat design into sew-ORDER behaviour
    # only, and the region-level binding this mirrors
    # (stage4_vectorize.revalidate_threads) keys on the classification alone
    # — the two bindings must not disagree about which designs are bound.
    # None — flag off, non-photo class, or nothing planned — reaches
    # `streamline_fill` as the documented "no restriction" default, byte-
    # identical to the parameter not existing.
    shade_palette: list[int] | None = None
    if cfg.shade_palette_bind and is_photographic(cfg, design_class) and planned:
        shade_palette = sorted({pr.region.thread_index for pr in planned})
        # The demand palette's anchors (cfg.shade_palette_demand — option
        # (b) of the same plan doc; `palette_spools`' docstring entry above
        # carries the contract): spools `select_palette` chose FOR the
        # shades that no region's own mean claimed. They exist precisely so
        # the bind has honest dark/light anchors to land on — without this
        # union the demand run would select them at stage 2 and then mask
        # the shade snap to a set that never contains them, re-shipping (a)
        # alone's bind cost with extra ceremony. Union, not replacement:
        # a review-screen recolor's cone (in `planned`, not in the stage-2
        # medoids) stays loadable exactly as the bind's own comment above
        # promises. Double-gated on the cfg flag so a stale carrier from a
        # demand-built generation cannot leak into a flag-off re-plan.
        if cfg.shade_palette_demand and palette_spools:
            shade_palette = sorted(set(shade_palette) | set(palette_spools))
    class_fill_underlay = _PHOTO_FILL_UNDERLAY if photo else fabric.fill_underlay
    underlay_style = (cfg.underlay_style or class_fill_underlay) if cfg.underlay else "none"
    satin_underlay = ((_PHOTO_SATIN_UNDERLAY if photo else fabric.satin_underlay)
                      if cfg.underlay else "none")
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    trim_at = fabric.trim_at_mm

    # `cfg.border is None` means "let the class decide" — see config.py's own
    # block for why None and not "off". Only the real PHOTO_CLASSES take the
    # significant mode: `gradient` is deliberately NOT included (Kent,
    # 2026-08-24 — gradient is also the class for genuine gradient logos), so
    # a photograph stage 0 routes to gradient does not get borders
    # automatically. That is a stage-0 routing question, not a border one.
    border_style = (cfg.border or ("significant" if photo else "off")).lower()
    # The significance denominator: the design's own stitched area, so the
    # gate is a SHARE and moves with the design instead of being a mm floor
    # (which would be a physical constant, and gate 1 territory).
    border_total_area = sum(
        (getattr(p.region.polygon, "area", 0.0) or 0.0) for p in planned
    ) if border_style == "significant" else 0.0
    border_share_min = (cfg.border_significant_area_share
                        if cfg.border_significant_area_share is not None
                        else machine.BORDER_SIGNIFICANT_AREA_SHARE)
    border_iso_max = (cfg.border_abrupt_raggedness
                      if cfg.border_abrupt_raggedness is not None
                      else machine.BORDER_ABRUPT_RAGGEDNESS)
    rescue = cfg.small_shape_rescue
    # The config-to-emitter mapping the split-satin knobs document: False
    # sews raw crosses however long (a real house style — jolly-af ships
    # 7 mm stitches), None defers to the corpus-median machine default.
    split_above = math.inf if not cfg.split_satin else cfg.split_satin_above_mm
    # Push comp (Law 24), the half of directional compensation stage 5 cannot
    # express because it has no spine to shorten. Two terms, and both are owed:
    # PUSH_CUTBACK_MM is the physical effect, and `pull_comp_mm` gives back
    # what stage 5's isotropic buffer added at the cap — correct on the rails,
    # wrong in the one direction a column is already gaining length.
    end_cutback = (fabric.pull_comp_mm + machine.PUSH_CUTBACK_MM
                   if cfg.directional_comp else 0.0)
    # The sewable-detail floor, as an area: stage 3 keeps shapes under it only
    # for the run tier, and this is where they are routed to it.
    detail_mm2 = cfg.min_detail_mm ** 2
    # DT-first migration M1 (docs/dt-first-architecture-2026-08-01.md §2):
    # off by default, so `bool(cfg.extra.get(...))` reads False on both an
    # absent key and every falsy value a caller might pass. On, satin_shape
    # sources its skeleton/DT through digitizer_core/shapefield.py instead
    # of stage6_satin's own inline call — see that module's docstring. This
    # is infrastructure only: it must not change one stitch coordinate.
    use_shapefield = bool(cfg.extra.get("shapefield"))

    # The fill tier. Contour rings follow the silhouette; tatami rows cut across
    # it. Density is the same either way — the ring spacing IS the row spacing
    # unless the caller opens it up on its own.
    #
    # `fill_technique` (the parameter, above `cfg` in precedence when set) is
    # `plan_stitches`' resolved photo_subject auto-route value — this is the
    # one line that makes the automatic tier route from spec decision 3
    # actually sew, not just warn about what it would sew.
    technique = (fill_technique or cfg.fill_technique or "tatami").lower()
    contour = technique == "contour"
    contour_spacing = cfg.contour_spacing_mm or row_mm
    # The scan-line mono tonal tier (photo plan, technique row 8). Strictly
    # opt-in: with any other fill_technique this flag is False and every
    # branch below reads exactly as it did before the tier existed. It needs
    # source pixels to read tone from — a caller who set the flag gets them
    # via pipeline.run_stages' explicit-opt-in plumbing; if they are missing
    # anyway (a hand-built PipelineResult), the shape falls through to
    # tatami rather than crashing or dropping artwork.
    scanline = technique == "scanline_tonal"
    # The meander mono tonal tier (photo plan, technique row 9): identical
    # opt-in and fallback contract to the scanline tier above — off unless
    # named, tone read from the same source-pixel plumbing, tatami on empty.
    meander = technique == "meander_tonal"
    # The streamline thread-paint tier (photo plan, technique row 10, first
    # slice): same opt-in and fallback contract, but reads the direction
    # field's raster instead of raw tone for its spacing.
    streamline = technique == "streamline"
    # The sketch tier (photo plan, technique row 12 — stage6_sketch): the
    # row-12 preset over rows 10+11, sparse mono streamlines plus the FDoG
    # detail block appended below. Same opt-in and fallback contract as
    # every tonal tier above. Design-wide only here; the per-shape
    # tier == "sketch" override is handled inside stitch_one.
    sketch = technique == "sketch"
    # The cross-hatch fill tier (stage6_fill._crosshatch_fill_paths): two
    # angled tatami passes on the same shape, sewn through the ordinary
    # stitch_shape call with technique="crosshatch". Unlike every tonal tier
    # above, this needs no source pixels — it is a purely geometric variant
    # of the plain tatami fill — so it plugs into stitch_one below closer to
    # how "contour" does than how "sketch"/"streamline" do. Design-wide only
    # here; the per-shape tier == "crosshatch" override is handled inside
    # stitch_one.
    crosshatch = technique == "crosshatch"
    # Wave, chevron and brick: three more purely-geometric fill variants,
    # same no-source-pixels-needed / design-wide-or-per-shape / never-drop-
    # artwork contract as crosshatch immediately above. Unlike crosshatch —
    # a whole second angled tatami pass — each of these three only changes
    # how ONE row's own interior points get placed
    # (stage6_fill._wave_row_points / _chevron_row_points /
    # _brick_row_points, dispatched inside _fill_paths itself), so they need
    # no new travel-planning logic of their own either. Design-wide only
    # here; the per-shape tier == "wave"/"chevron"/"brick" override is
    # handled inside stitch_one, same slot as tier == "crosshatch".
    wave = technique == "wave"
    chevron = technique == "chevron"
    brick = technique == "brick"

    thin = empty = jumps = as_run = 0
    bordered = lightened = border_narrow = 0
    rings_skipped = starved = 0
    # Blend-tier outcome, counted across the whole design so the warning can
    # report what the tier actually did rather than what stage 0's routing
    # copy promised. `blend_routed` counts regions that reached blend_fill at
    # all; `blend_decomposed` counts the ones that came back as more than one
    # thread shade.
    blend_routed = blend_decomposed = 0
    blend_rejects: dict[str, int] = {}
    blend_best_r2 = 0.0
    blocks: list[StitchBlock] = []
    cursor: tuple[float, float] | None = None
    # Every shape whose border tier actually put a circuit down, keyed by id,
    # in the order they actually sewed — `_yield_frontage` reads this as "what
    # is already on the fabric", and it only ever holds circuits that really
    # sew, not shapes that merely asked for one and went `too_narrow`, so a
    # later shape never yields to a seam nothing is going to cover.
    border_geom_by_id: dict[str, object] = {}
    # Seams `_yield_frontage` could not resolve without deleting the later
    # shape's border outright — see `_border_seam_warning`.
    border_seam_unresolved: list[tuple[str, str, float]] = []

    # --- The appliqué tier (stage6_applique, docs §2). Off unless asked for,
    # and when off this returns ([], [], planned, None) and changes nothing.
    # Appliqué pieces sew first and leave the normal color loop entirely: the
    # fabric goes down before anything decorates it, and a piece's steps must
    # be consecutive blocks so no other color lands between "lay the twill"
    # and "trim it".
    applique_blocks, applique_warnings, planned, applique_cursor = applique_pass(
        planned, cfg, chart_for(cfg))
    blocks.extend(applique_blocks)
    if applique_cursor is not None:
        cursor = applique_cursor

    # Chaining's tier-blindness fix (see `_link_cover`'s docstring): the
    # artwork polygon of every shape that will predictably sew as an outline
    # RUN, tagged with its layer's sew index so each block can subtract the
    # ones that sew AFTER it from its future-colour cover. Predicted with the
    # same predicate `stitch_one` routes on — an explicit `tier: "run"`, or
    # the small-shape rescue's area floor. `stitch_one` has three REACTIVE
    # run outcomes this cannot see, and they are asymmetric on purpose: a
    # forced-run shape whose outline comes back empty falls through to
    # fill/satin (MORE thread than predicted here — cover merely
    # under-counted, a link refused, never a float); a shape that defeats
    # both real tiers and rescues as an outline can still over-promise, but
    # it is the degenerate geometry the rescue exists for, and the
    # LINK_COVER_INSET_MM erosion still bounds any shape of that kind
    # thinner than twice the inset; and a photo-lane `photo_width_floor`
    # reroute (systematic, not degenerate) is bounded by the same argument —
    # every floored shape is under 1.0 mm wide, less than twice the 0.75 mm
    # inset, so its cover polygon erodes to empty rather than floating.
    run_tier_later: list[tuple[int, object]] = []
    if cfg.chain_links:
        for p in planned:
            p_tier = str(p.region.meta.get("tier", "auto")).lower()
            if p_tier == "run" or (p_tier == "auto" and rescue
                                   and p.region.polygon.area < detail_mm2):
                run_tier_later.append((p.sew_index, p.region.polygon))

    # Group by (sew_index, step_key) rather than by sew_index alone — §0's
    # third consequence, as code. The nearest-neighbour pass below reorders
    # shapes to save needle travel and merges a whole group into ONE block;
    # left unguarded it would weld two steps together to save a color stop and
    # destroy an operator instruction with it. Regions carrying no `step_key`
    # all key on "", so a design with no steps groups and sorts exactly as it
    # always did.
    for _group_key in sorted({nn_group_key(p) for p in planned}):
        group = [p for p in planned if nn_group_key(p) == _group_key]

        def stitch_one(p: PlannedRegion, entry: tuple[float, float] | None):
            # The review screen's per-shape tier (shape-layers contract v1;
            # "sketch" added in v1.3): "auto" is the ladder below exactly as
            # it always ran; "satin", "fill", "run" and "sketch" force one
            # rung. A forced rung that produces nothing falls back to "auto"
            # rather than dropping artwork — the same contract the auto
            # ladder already has between its own rungs.
            tier = str(p.region.meta.get("tier", "auto")).lower()
            # UNDERLAY-STYLE PRECEDENCE (shape-layers contract v1): the
            # shape's own review-screen style beats the design-wide one — in
            # BOTH directions, exactly like `border` beats `border_style`.
            # `underlay_style` here already folds in `cfg.underlay` (line
            # ~390: forced to "none" when the design-wide switch is off), so
            # an explicit per-shape style overrides that switch too — a shape
            # marked "zigzag" gets underlay with underlay=False design-wide,
            # and one marked "none" gets none with it on. Reaches the fill
            # and contour tiers only (both consult it below); satin keeps its
            # own separate, narrower underlay knob untouched.
            shape_underlay = p.region.meta.get("underlay_style")
            eff_underlay_style = (shape_underlay if shape_underlay is not None
                                  else underlay_style)
            # The run tier comes first: a shape below the sewable-detail floor
            # has nowhere to put fill rows (MIN_FILL_WIDTH_MM) and pinches
            # every satin cross under SATIN_MIN_CROSS_MM, so both real tiers
            # produce a smear of degenerate stitches or nothing. Its outline
            # sews as a bean run instead — on the ARTWORK polygon, because a
            # run does not pull fabric and compensation would fatten a
            # thread-width stroke past its own letterform (see `run_outline`).
            if tier == "run" or (tier == "auto" and rescue
                                 and p.region.polygon.area < detail_mm2):
                runs, report = run_outline(p.region.polygon, p.shape_id,
                                           entry=entry, trim_at_mm=trim_at)
                if not report["empty"]:
                    report["as_run"] = 1
                    return runs, report, False
                tier = "auto"
            # Satin or fill is decided per shape, not per design: one logo
            # routinely holds both a big filled emblem and thin satin lettering.
            # Classified on the ARTWORK polygon, not the stage-5 grown one —
            # otherwise heavy fabric (0.6 mm pull comp widens a ribbon 1.2 mm)
            # flips the same artwork from satin to fill, and a logo would sew
            # differently structured on a towel than on a polo. A forced
            # "satin" skips the classifier (and the global satin switch): the
            # user has already answered the question it asks.
            #
            # One classify_ribbon call carries both decisions the ladder needs:
            # the satin/fill verdict is_satin_candidate wrapped (identical
            # computation), and Law 31's photo-lane width floor — a shape that
            # EARNED satin but would sew a thread-width column
            # (`photo_width_floor`, photo classes only; see the constant's
            # comment in stage6_satin for why flat/gradient keep their satin)
            # reroutes to the same outline run the area rescue above uses, on
            # the artwork polygon for the same no-compensation reason. An
            # outline the run tier cannot close falls through to fill rather
            # than silently dropping artwork, exactly like the satin branch.
            ribbon = (classify_ribbon(p.region.polygon, satin_max,
                                      design_class=design_class)
                      if tier == "auto" and cfg.satin else None)
            if ribbon is not None and ribbon.reason == "photo_width_floor":
                runs, report = run_outline(p.region.polygon, p.shape_id,
                                           entry=entry, trim_at_mm=trim_at)
                if not report["empty"]:
                    report["as_run"] = 1
                    return runs, report, False
            if tier == "satin" or (ribbon is not None and ribbon.satin):
                # The house cross angle (2026-08-26). Per-shape intent beats
                # the global, the same precedence border/underlay_style/
                # fill_angle already use; None on both keeps today's output
                # byte-identical, which is what every golden is pinned to.
                satin_angle_deg = p.region.meta.get("satin_angle_deg")
                if satin_angle_deg is None:
                    satin_angle_deg = cfg.satin_angle_deg
                runs, report = satin_shape(
                    p.polygon,
                    p.shape_id,
                    underlay_style=satin_underlay,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    split_above_mm=split_above,
                    end_cutback_mm=end_cutback,
                    use_shapefield=use_shapefield,
                    spacing_mm=satin_spacing_mm,
                    angle_deg=satin_angle_deg,
                )
                # A ribbon the skeleton could not resolve still has to sew:
                # fall through to fill rather than silently dropping artwork.
                if not report["empty"]:
                    return runs, report, False
            # The ring tier. Tried first when it is on, and only when it is:
            # every golden in the suite is pinned to tatami, and the branch is
            # what keeps them byte-identical. A shape contour cannot ring — one
            # narrower than a single offset — falls through to tatami rather
            # than vanishing, the same contract the satin tier already has.
            #
            # Contour takes no fill angle, and that is not an omission: rings
            # follow the silhouette, so there is no one direction the stitches
            # run. It does mean `directional_comp` and `fill_technique="contour"`
            # do not compose — stage 5 would have compensated this shape along a
            # fill axis the rings then decline to sew along. Both flags default
            # off, neither is selected automatically, and nothing measures that
            # pair yet; the plan carries a CONTOUR_DIRECTIONAL_COMP_UNSEWN
            # warning (emitted with the other counters below) instead of
            # silently combining them.
            runs = []
            report = {}
            need_tatami = False
            if (sketch or tier == "sketch") and source_pixels is not None:
                # The sketch tier (row 12): the design-wide preset OR this
                # one shape's review-screen tier override — the per-shape
                # form is checked here so it beats whatever technique the
                # rest of the design sews with, the same precedence every
                # other forced tier value gets. Empty is honest (an
                # all-highlight shape sews nothing) and falls through to
                # tatami below rather than dropping artwork — the standing
                # contract of every tonal tier in this chain.
                runs, report = sketch_fill(p.region, source_pixels, cfg)
                need_tatami = report["empty"]
            elif (streamline or tier == "streamline") and source_pixels is not None:
                # The streamline thread-paint tier (row 10): the design-wide
                # preset OR this one shape's review-screen tier override —
                # checked here, ahead of scanline/meander, for the identical
                # reason the sketch branch above is checked first: a forced
                # per-shape tier beats whatever technique the rest of the
                # design sews with (the "shape-layers contract" precedence
                # every other forced tier value already gets). This is also
                # how a manually-classified (flat-lane) shape reaches
                # streamline fill outside the photo auto-pipeline — the
                # design can stay `fill_technique="tatami"` throughout and
                # still carry one `tier: "streamline"` shape, exactly the
                # way one shape can already carry `tier: "sketch"`.
                #
                # Direction-field source, decided once and not revisited
                # per shape: `streamline_fill` always reads
                # `directionfield.py`'s structure-tensor/ETF field over
                # THIS design's own prepped raster (`source_pixels.rgb` —
                # whatever art the job was given, photo or flat logo
                # alike), never a shape-geometry-derived field (no medial-
                # axis/skeleton tangent construction exists in this
                # codebase for that, and building one would be a new
                # clean-room algorithm, not a wiring change). That module's
                # own coherence gate already makes this the right default
                # for a flat-lane shape with no real texture: a genuinely
                # flat, textureless region reads near-zero coherence and
                # falls back to `RegionDirection.use_house_angle`'s constant
                # field, which itself reads this shape's `fill_angle_deg`
                # override first — the very same per-shape angle knob
                # ordinary tatami fill already exposes — before the design-
                # wide default. So a manually-selected streamline shape gets
                # real image-structure-following lines where the art
                # actually has texture, and clean user-controlled parallel
                # lines (not a crash, not spaghetti) where it does not.
                # Empty is honest (an all-highlight shape sews nothing) and
                # falls through to tatami below rather than dropping
                # artwork — the standing contract of every tonal tier here.
                # `streamline_mode` (this function's own resolved parameter,
                # not `cfg.streamline_mode` directly) is threaded through so
                # a photo_subject auto-route forcing "layered" reaches every
                # shape this branch fills, per-shape override included —
                # `streamline_fill` itself falls back to reading `cfg.
                # streamline_mode` when this is `None` (every other case).
                # `shade_palette` (derived once above, None unless the
                # shade-palette-bind experiment is on for a photo class) is
                # threaded the same way `streamline_mode` is: an explicit
                # keyword, never a cfg mutation — layered mode's per-shade
                # snap reads it, mono ignores it.
                runs, report = streamline_fill(p.region, source_pixels, cfg,
                                               streamline_mode=streamline_mode,
                                               shade_palette_indices=shade_palette)
                need_tatami = report["empty"]
            elif crosshatch or tier == "crosshatch":
                # The cross-hatch fill tier: two tatami passes on the same
                # shape, one at the fill angle and one at +90
                # (stage6_fill._crosshatch_fill_paths), each individually
                # spaced machine.CROSSHATCH_ROW_SCALE_FACTOR times wider so
                # the combined density of both passes lands near a
                # single-pass fill's, not roughly double it. Positioned in
                # the same slot sketch/streamline occupy above (ahead of
                # scanline/meander/gradient/contour) for the identical
                # reason: a forced per-shape tier has to beat whatever
                # technique the rest of the design sews with. Unlike those
                # two this needs no source pixels — it's a purely geometric
                # variant of plain tatami, not a tonal tier — so it is not
                # gated on `source_pixels is not None`, and it calls the
                # ordinary stitch_shape directly (technique="crosshatch")
                # rather than a dedicated emitter module, the same call the
                # plain-tatami fallback below makes, one technique over.
                # Falls back to plain tatami on empty (a shape too thin to
                # hold even the wider spacing), the same never-drop-artwork
                # contract every other fill tier here has.
                #
                # Angle precedence mirrors the trailing stitch_shape call
                # below exactly (shape override > design-wide > stage 5's
                # compensation axis) — duplicated rather than deferred to it
                # because crosshatch needs its angle now, to plan the +90
                # pass; that call's own "decided here and nowhere else"
                # comment still holds for the plain-tatami case it covers.
                shape_angle = p.region.meta.get("fill_angle_deg")
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=(float(shape_angle)
                               if shape_angle is not None
                               else cfg.fill_angle_deg
                               if cfg.fill_angle_deg is not None
                               else p.stitch_angle_deg),
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    technique="crosshatch",
                )
                need_tatami = report["empty"]
            elif wave or tier == "wave":
                # The wave fill tier: every interior row point rides a
                # subtle perpendicular sine wave, machine.WAVE_AMPLITUDE_MM
                # * sin(2*pi*x/machine.WAVE_LENGTH_MM + phase), phase
                # alternating by row parity so neighbouring rows' waves move
                # opposite ways instead of stacking into a corrugated-
                # cardboard look (stage6_fill._wave_row_points). Both row
                # ends still land exactly on the boundary — the wobble never
                # touches the shape's own edge or silhouette. Same slot,
                # same no-source-pixels-needed reasoning (purely geometric,
                # not tonal) and same never-drop-artwork fallback contract
                # as the crosshatch branch immediately above; angle
                # precedence is identical too, though unlike crosshatch this
                # technique does not need its angle any earlier than the
                # plain-tatami call below would — it is duplicated here only
                # to keep all four purely-geometric branches (crosshatch,
                # wave, chevron, brick) reading the same way.
                shape_angle = p.region.meta.get("fill_angle_deg")
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=(float(shape_angle)
                               if shape_angle is not None
                               else cfg.fill_angle_deg
                               if cfg.fill_angle_deg is not None
                               else p.stitch_angle_deg),
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    technique="wave",
                )
                need_tatami = report["empty"]
            elif chevron or tier == "chevron":
                # The chevron fill tier: a deliberately simplified, TEXTURAL
                # herringbone impression at one fill angle, not a full
                # multi-angle banded herringbone (that would need new
                # column/travel logic, out of scope for this family of
                # techniques) — interior row points alternate
                # +-machine.CHEVRON_AMPLITUDE_MM every stitch
                # (stage6_fill._chevron_row_points), on the same staggered
                # grid plain tatami already builds. Same slot/contract as
                # the wave branch immediately above.
                shape_angle = p.region.meta.get("fill_angle_deg")
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=(float(shape_angle)
                               if shape_angle is not None
                               else cfg.fill_angle_deg
                               if cfg.fill_angle_deg is not None
                               else p.stitch_angle_deg),
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    technique="chevron",
                )
                need_tatami = report["empty"]
            elif brick or tier == "brick":
                # The brick fill tier: a strict, visually obvious 2-phase
                # "running bond" stagger — even rows' interior grid starts
                # at phase 0, odd rows at stitch_mm/2
                # (stage6_fill._brick_row_points) — replacing the ordinary
                # van-der-Corput anti-moire stagger (_stagger_phase) for
                # this technique only; every other technique's stagger is
                # untouched. Same slot/contract as wave and chevron above.
                shape_angle = p.region.meta.get("fill_angle_deg")
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=(float(shape_angle)
                               if shape_angle is not None
                               else cfg.fill_angle_deg
                               if cfg.fill_angle_deg is not None
                               else p.stitch_angle_deg),
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    technique="brick",
                )
                need_tatami = report["empty"]
            elif scanline and source_pixels is not None:
                # The explicit scanline_tonal opt-in beats the gradient
                # class's blend routing — the caller already chose the mono
                # look. Empty is a legitimate outcome for this tier (a shape
                # that is entirely highlight sews nothing, honestly), and the
                # standing never-drop-artwork ladder still applies: it falls
                # through to tatami below, exactly as a shape contour cannot
                # ring does. Bare-fabric-on-purpose is a review-screen
                # decision (delete the shape), not something a fill tier may
                # decide unilaterally.
                runs, report = scanline_fill(p.region, source_pixels, cfg)
                need_tatami = report["empty"]
            elif meander and source_pixels is not None:
                # Same contract as the scanline branch above, meander look:
                # the explicit opt-in beats the gradient class's blend
                # routing, empty is honest (an all-highlight shape sews
                # nothing) and falls through to tatami below rather than
                # dropping artwork.
                runs, report = meander_fill(p.region, source_pixels, cfg)
                need_tatami = report["empty"]
            elif source_pixels is not None and source_pixels.gradient_class:
                # Stage 0 classified the whole design "gradient" (the
                # marker `pipeline.run_stages` stamps — presence of source
                # pixels alone stopped meaning "gradient" once the detail
                # layer started carrying pixels for its own, non-blend use)
                # — every
                # auto-tier shape routes through the blend fill instead of
                # tatami/contour. blend_fill's own ramp detection already
                # falls back to ordinary tatami internally when THIS shape
                # isn't actually a ramp (ramp-or-not is a per-shape question,
                # gradient-or-not is a per-design one), so unlike contour
                # there is no further fallback needed here — if blend_fill
                # came back empty, plain tatami would have too.
                runs, report = blend_fill(p.region, source_pixels, cfg)
            elif contour:
                runs, report = contour_fill(
                    p.polygon,
                    p.shape_id,
                    spacing_mm=contour_spacing,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    tolerance_mm=cfg.contour_tolerance_mm,
                    start_near=entry,
                )
                need_tatami = report["empty"]
            else:
                # Plain tatami — and also any tonal-tier flag (scanline,
                # meander, streamline) with no source pixels to read tone
                # from, which sews as tatami rather than
                # dropping the shape.
                need_tatami = True
            if need_tatami:
                # The fill angle stage 5 already committed to, when it did.
                # Passing it back is what makes directional comp honest:
                # compensation went on the edges THIS angle penetrates, so the
                # rows have to run along it. Left None (the shipped path) stage
                # 6 derives its own from the compensated polygon, which is a
                # different number.
                #
                # FILL-ANGLE PRECEDENCE, decided here and nowhere else:
                #   1. the shape's own review-screen angle
                #      (meta["fill_angle_deg"], shape-layers contract v1)
                #   2. the global cfg.fill_angle_deg
                #   3. the axis stage 5 compensated along
                #      (p.stitch_angle_deg — the directional-comp lane; None
                #      when compensation was isotropic)
                #   4. None: stage 6 derives its own per-shape PCA.
                # Stage 5's `_comp_axis` follows the same 1 > 2 order, so with
                # directional comp on, the axis a shape was compensated along
                # and the axis it sews along stay one number by construction.
                shape_angle = p.region.meta.get("fill_angle_deg")
                runs, report = stitch_shape(
                    p.polygon,
                    p.shape_id,
                    angle_deg=(float(shape_angle)
                               if shape_angle is not None
                               else cfg.fill_angle_deg
                               if cfg.fill_angle_deg is not None
                               else p.stitch_angle_deg),
                    row_mm=row_mm,
                    stitch_mm=stitch_mm,
                    underlay_style=eff_underlay_style,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    density_boost=cfg.fill_density_boost,
                )

            # The reactive rescue: a shape can pass every size floor and still
            # defeat both tiers — a skeleton the satin module cannot resolve
            # falling through to a fill whose every row degenerates. That used
            # to be a silent SHAPE_NOT_STITCHED; its outline still exists, and
            # sewing it as a run beats leaving a hole in the artwork.
            if rescue and not runs:
                r_runs, r_report = run_outline(p.region.polygon, p.shape_id,
                                               entry=entry, trim_at_mm=trim_at)
                if r_runs:
                    r_report["as_run"] = 1
                    return r_runs, r_report, False

            # The border goes on AFTER the fill it covers, and only on a filled
            # shape: a satin column already IS an outline, so bordering one
            # sews a second column on top of the first. Per-shape intent from
            # the review screen beats the mode in both directions — a shape
            # marked True is bordered with the mode off, and one marked False
            # is left alone with the mode on.
            want = p.region.meta.get("border")
            style = "bean" if border_style == "bean" else "auto"
            if isinstance(want, str):
                # The contract's per-shape border mode ("off"|"auto"|"bean")
                # carries its own style; the bool form predates it and defers
                # to the global mode for style, as it always has.
                w = want.lower()
                style = "bean" if w == "bean" else "auto"
                want = w != "off"
            if want is None:
                # "significant" is "auto" with an earned-it gate in front:
                # per-shape intent above still beats it in both directions,
                # exactly as it beats every other mode.
                if border_style == "significant":
                    want = _border_worthy(p.region.polygon, border_total_area,
                                          border_share_min, border_iso_max)
                else:
                    want = border_style != "off"
            if want and runs:
                # THE REAL FIX for stage6_border's KNOWN LIMITATION (was
                # detect-only, PR #67): pull this shape's border input back
                # off any seam it shares with a border ALREADY sewn, so the
                # two circuits stop riding the identical line. `border_width`
                # is also the seam-sharing threshold's unit — same 2x column
                # width `_border_seam_pairs` always used, so suppression
                # engages under exactly the condition that used to just warn.
                border_width = cfg.border_width_mm or machine.BORDER_WIDTH_MM
                border_geom, unresolved = _yield_frontage(
                    p.visible_geom, border_geom_by_id, border_width,
                    2.0 * border_width)
                border_seam_unresolved.extend(
                    (p.shape_id, other_id, length)
                    for other_id, length in unresolved
                )
                b_runs, b_report = border_runs(
                    border_geom,
                    p.shape_id,
                    entry=runs[-1].points[-1],
                    trim_at_mm=trim_at,
                    style=style,
                    width_mm=cfg.border_width_mm,
                )
                report["jumps"] += b_report["jumps"]
                report["bordered"] = b_report["loops"]
                report["lightened"] = b_report["bean_loops"]
                report["border_narrow"] = b_report["too_narrow"]
                if b_runs:
                    # The TRUE visible geometry, not the (possibly locally
                    # inset) `border_geom` this shape sewed from — a later
                    # shape must be able to detect the real seam it shares
                    # with THIS one even where this one yielded to someone
                    # else, so `_yield_frontage` always compares true edges.
                    report["border_geom"] = p.visible_geom
                runs.extend(b_runs)
            return runs, report, True

        # Order first, stitches second. A shape's path now depends on where the
        # needle is when it starts, so the order has to be settled before the
        # geometry exists — and the honest proxy for "how far must the needle
        # fly" is the distance to the shape itself, not to one arbitrary point
        # on it. Picking on a start point the shape had not chosen yet is what
        # sent the needle to every shape's top-left corner: on eight filled
        # letters that was 112 mm of thread flown and nine trims.
        rank = {i: r for r, i in enumerate(sorted(
            range(len(group)),
            key=lambda i: (group[i].polygon.bounds[1], group[i].polygon.bounds[0],
                           group[i].shape_id)))}
        # Where a color starts when nothing is sewn yet. Nearest-neighbour from
        # a shape in the MIDDLE of a group strands the far end and pays for it
        # with one long haul at the finish — on eight letters of a word, a
        # 42 mm flight back across the whole design. Starting at an extreme of
        # the group means the sweep never has to come back.
        centre = unary_union([p.polygon for p in group]).centroid
        far = {i: round(group[i].polygon.centroid.distance(centre), 6)
               for i in range(len(group))}

        # The review screen's within-layer sew order (shape-layers contract
        # v1.2, `Region.meta["sew_order"]`): a shape carrying one is "due" at
        # that 0-based slot in THIS group's pick sequence and is forced next
        # once the slot count reaches it, pre-empting nearest-neighbour.
        # Shapes with no override are untouched — they keep competing for
        # every slot nearest-neighbour would have given them, which is the
        # fallback the contract promises. Ties among several shapes due at
        # once break on `rank`, the same deterministic tiebreak the geometry
        # picks already use. A sparse or colliding set of values still
        # terminates cleanly: a pinned shape not yet due when every unpinned
        # shape is gone is simply forced early rather than stalling the loop.
        sew_order = {i: group[i].region.meta.get("sew_order")
                     for i in range(len(group))
                     if group[i].region.meta.get("sew_order") is not None}

        remaining = list(range(len(group)))
        ordered: list[StitchRun] = []
        # Which shapes actually put thread down. A link may only be routed
        # under geometry that will really be sewn, so a shape that produced
        # nothing must not be allowed to "cover" anything.
        sewn: list[PlannedRegion] = []
        while remaining:
            next_slot = len(group) - len(remaining)
            pinned = [i for i in remaining if i in sew_order]
            due = min(pinned, key=lambda i: (sew_order[i], rank[i])) if pinned else None
            unpinned = [i for i in remaining if i not in sew_order]
            if due is not None and (sew_order[due] <= next_slot or not unpinned):
                pick = due
            elif cursor is None:
                pick = min(unpinned, key=lambda i: (-far[i], rank[i]))
            else:
                here = Point(cursor)
                pick = min(unpinned, key=lambda i: (
                    round(group[i].polygon.distance(here), 6), rank[i]))
            p = group[pick]
            remaining.remove(pick)
            runs, report, filled = stitch_one(p, cursor)
            thin += int(filled and report["too_thin"])
            jumps += report["jumps"]
            as_run += report.get("as_run", 0)
            bordered += report.get("bordered", 0)
            lightened += report.get("lightened", 0)
            border_narrow += report.get("border_narrow", 0)
            bgeom = report.get("border_geom")
            if bgeom is not None:
                border_geom_by_id[p.shape_id] = bgeom
            if report.get("starved"):
                starved += 1
                rings_skipped += report.get("skipped_rings", 0)
            if "blend_shades" in report:
                blend_routed += 1
                if report["blend_shades"] > 1:
                    blend_decomposed += 1
                else:
                    reason = report.get("blend_reject") or "unknown"
                    blend_rejects[reason] = blend_rejects.get(reason, 0) + 1
                blend_best_r2 = max(blend_best_r2, report.get("blend_best_r2", 0.0))
            if report["empty"] or not runs:
                empty += 1
                continue
            if cursor is not None:
                d = math.dist(cursor, runs[0].points[0])
                if d >= TINY_STITCH_MM:
                    runs[0].jump = True
                    runs[0].trim = d > trim_at
            ordered.extend(runs)
            sewn.append(p)
            cursor = runs[-1].points[-1]
        if not ordered:
            continue

        # The needle always lifts into a new color, and the thread is always cut
        # coming out of the previous one.
        ordered[0].jump = True
        ordered[0].trim = True
        # Chaining comes before the ties, because the ties are a consequence of
        # it: a lock stitch goes in wherever the thread is cut, so every lift
        # this turns into a link is also two locks that no longer have to be
        # sewn (`_apply_ties` reads `run.trim` and finds one fewer).
        if cfg.chain_links:
            later_run_art = [g for i, g in run_tier_later
                             if i > group[0].sew_index]
            ordered, linked_in_shape = _chain(
                ordered, sewn, group[0].region.thread_index,
                unary_union(later_run_art) if later_run_art else None)
            jumps -= linked_in_shape

        # Task 1 (photo/tonal v1): a blend-tier run carries the thread its
        # OWN shade snapped to, so one group can sew several StitchBlocks —
        # one per accepted shade, dark to light — instead of collapsing every
        # run into `group[0].region.thread_index`. See `_shade_blocks`'
        # docstring for the bucketing/tie/recompute contract; extracted to a
        # standalone function so it has a call boundary a unit test can drive
        # directly with a hand-built run list, not just through a full
        # `sequence()` job.
        group_blocks = _shade_blocks(ordered, group[0].region.thread_index,
                                     chart_for(cfg), trim_at)
        blocks.extend(group_blocks)
        cursor = group_blocks[-1].runs[-1].points[-1]

    # --- The detail layer (stage6_detail, photo plan row 11) -----------------
    # Appended AFTER every artwork block — plan row 14's craft consensus,
    # "details last": bean lines ride ON TOP of the fills they annotate.
    # Strictly opt-in (cfg.detail_layer, default False — this branch never
    # runs otherwise and the byte-identity suites pin that), and honest on
    # empty: a design the extractor finds no coherent lines for appends no
    # block at all, no warning, rather than failing or inventing detail.
    # The block carries its own thread identity (the chart cone nearest the
    # lines' own sampled color — detail_runs' report) exactly as every
    # block does; the result-level sew-order palette is regions-derived and
    # deliberately not grown here, the same block-level-is-authoritative
    # convention the layered streamline shades already established.
    # The sketch technique IMPLIES this layer (row 12's recipe is "layered
    # run passes + FDoG detail lines" — one preset, not two knobs; see
    # stage6_sketch's module docstring). Design-wide sketch only: a single
    # shape's tier == "sketch" override changes that shape's fill, never
    # the design's detail pass.
    #
    # Fix round 2 (Critical): `detail_layer` is this function's own resolved
    # parameter (`plan_stitches`' effective value — True when a face was
    # actually detected and the auto-route fired, same as `fill_technique`/
    # `streamline_mode` above), not `cfg.detail_layer` directly — before
    # this round the PHOTO_AUTO_TIER warning could promise a detail layer
    # for a detected face while this gate still read the caller's raw,
    # untouched `cfg.detail_layer` (False) and never sewed one. `None`
    # (every pre-existing caller) falls back to `cfg.detail_layer` exactly
    # as before.
    eff_detail_layer = detail_layer if detail_layer is not None else cfg.detail_layer
    if (eff_detail_layer or sketch) and source_pixels is not None:
        d_runs, d_report = detail_runs(source_pixels, cfg, entry=cursor,
                                       trim_at_mm=trim_at)
        if d_runs:
            jumps += d_report["jumps"]
            # A new color block: the needle always lifts into it and the
            # thread is always cut coming out of the previous one — the
            # same forcing every block above gets.
            d_runs[0].jump = True
            d_runs[0].trim = True
            _apply_ties(d_runs)
            d_thread = chart_for(cfg)[d_report["thread_index"]]
            blocks.append(
                StitchBlock(
                    thread_index=d_report["thread_index"],
                    thread_number=d_thread.number,
                    rgb=tuple(d_thread.rgb),
                    runs=d_runs,
                )
            )
            cursor = d_runs[-1].points[-1]

    warnings: list[dict] = list(applique_warnings)
    if thin:
        warnings.append(
            warn(
                SHAPE_TOO_THIN_TO_FILL,
                f"{thin} shape{'s are' if thin != 1 else ' is'} too narrow to "
                "fill cleanly but not stroke-like enough for satin — worth a "
                "look on the review screen.",
                count=thin,
            )
        )
    if as_run:
        warnings.append(
            warn(
                SMALL_SHAPES_AS_RUN,
                f"{as_run} shape{'s were' if as_run != 1 else ' was'} too small "
                "to hold a fill or satin — or too narrow to satin safely — "
                "and sewed as a light outline run instead.",
                count=as_run,
            )
        )
    if blend_routed and not blend_decomposed:
        # Deliberately worded around what the tier DID, not what stage 0's
        # CLASSIFIED_GRADIENT copy said it would do. Only fires when NOT ONE
        # region decomposed — a design where some regions split into shades
        # and others sewed flat is the tier working as designed, and needs no
        # correction to the classification message.
        warnings.append(
            warn(
                BLEND_NO_REGIONS_DECOMPOSED,
                f"None of the {blend_routed} shape"
                f"{'s' if blend_routed != 1 else ''} fit a smooth ramp closely "
                "enough to split into thread shades, so each sewed as one flat "
                "color. Photographic areas often carry tonal variation that "
                "isn't a linear or radial ramp.",
                count=blend_routed,
                reasons=dict(sorted(blend_rejects.items())),
                best_r2=round(blend_best_r2, 3),
            )
        )
    if empty:
        warnings.append(
            warn(
                SHAPE_NOT_STITCHED,
                f"{empty} shape{'s' if empty != 1 else ''} produced no stitches "
                "and were left out.",
                count=empty,
            )
        )
    if jumps:
        warnings.append(
            warn(
                LONG_JUMPS_TRIMMED,
                f"The thread had to be lifted {jumps} time"
                f"{'s' if jumps != 1 else ''} inside a shape.",
                count=jumps,
            )
        )
    if lightened:
        warnings.append(
            warn(
                BORDER_LIGHTENED,
                f"{lightened} outline{'s' if lightened != 1 else ''} had no room "
                "for a satin column and sewed as a bean run instead.",
                count=lightened,
            )
        )
    if starved:
        warnings.append(
            warn(
                CONTOUR_RING_UNREACHABLE,
                f"{starved} shape{'s' if starved != 1 else ''} left a patch of bare "
                "fabric wider than a contour ring — the offsets could not reach it — "
                "worth a look on the review screen.",
                count=starved,
                rings=rings_skipped,
            )
        )
    if contour and cfg.directional_comp:
        warnings.append(
            warn(
                CONTOUR_DIRECTIONAL_COMP_UNSEWN,
                "Directional compensation assumes a fill angle, but contour "
                "rings follow the shape's outline — the compensation was "
                "applied along an axis the stitches do not sew. Consider "
                "turning one of the two off.",
            )
        )
    if border_narrow:
        warnings.append(
            warn(
                BORDER_SKIPPED_TOO_NARROW,
                f"{border_narrow} shape{'s were' if border_narrow != 1 else ' was'} "
                "too narrow to hold an outline at all, and went unbordered.",
                count=border_narrow,
            )
        )
    # `_yield_frontage` (above, called from `stitch_one`) is the real fix for
    # stage6_border's KNOWN LIMITATION now, not a mitigation: two abutting
    # bordered shapes no longer both ride the shared seam at full density —
    # the one that sews later insets its circuit off it first. This warning
    # is what is left: the seams that fix genuinely could not resolve without
    # deleting a shape's border outright, collected as `stitch_one` ran.
    seam_warning = _border_seam_warning(border_seam_unresolved)
    if seam_warning is not None:
        warnings.append(seam_warning)
    return blocks, warnings
