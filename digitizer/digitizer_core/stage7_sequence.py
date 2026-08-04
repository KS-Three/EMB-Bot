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
from shapely.geometry import LineString, Point
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
from .stage6_satin import is_satin_candidate, satin_shape
from .stage6_streamline import streamline_fill
from .stitches import StitchBlock, StitchRun, tie_run
from .threads import chart_for
from .warnings_codes import (BORDER_LIGHTENED, BORDER_SKIPPED_TOO_NARROW,
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
PHOTO_CLASSES = ("photo_subject", "photo_scene")

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


def _link_cover(runs: list[StitchRun], regions: list[PlannedRegion]):
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
    """
    laid = [LineString(r.points) for r in runs
            if r.kind != stitches.TRAVEL and len(r.points) >= 2]
    parts: list[object] = list(laid)
    seen: list[object] = []
    for p in regions:
        c = p.covered_by
        if c is not None and not c.is_empty and not any(c is s for s in seen):
            seen.append(c)
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


def _chain(runs: list[StitchRun], regions: list[PlannedRegion]
           ) -> tuple[list[StitchRun], int]:
    """Sew every needle-up move this colour can bury. -> (runs, in-shape links).

    Runs in one pass over the finished block, after every shape has stitched,
    because that is the first moment the full covering geometry is known — and
    because it makes ONE rule govern every needle lift in the block, the ones
    stage 6 raised inside a shape as well as the ones this stage raised between
    them. Stage 6 decides on the shape's own polygon, which is all it can see;
    it cannot know that the gap it is jumping is about to be covered by the next
    colour, and on the benchmark that blind spot is eight of its ten trims.

    `runs[0]` is never touched. The thread is always cut into a new colour, and
    a link across a colour change would be sewn in the wrong thread.

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
    cover, waypoints = _link_cover(runs, regions)
    if cover is None:
        return runs, 0

    out = [runs[0]]
    in_shape = 0
    for run in runs[1:]:
        if not run.jump:
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
            out.append(StitchRun(points=inner, kind=stitches.TRAVEL,
                                 shape_id=run.shape_id))
        run.jump = False
        run.trim = False
        out.append(run)
    return out, in_shape


def _apply_ties(runs: list[StitchRun]) -> None:
    """Lock the thread wherever it starts and wherever it gets cut.

    Ties are folded into the run they protect rather than added as runs of
    their own, so nothing downstream has to special-case a two-millimetre run
    that is not really stitching.
    """
    if not runs:
        return

    def tie_in(run: StitchRun) -> None:
        if len(run.points) < 2:
            return
        pts = tie_run(run.points[0], run.points[1]).points
        run.points = pts[:-1] + run.points

    def tie_off(run: StitchRun) -> None:
        if len(run.points) < 2:
            return
        pts = tie_run(run.points[-1], run.points[-2]).points
        run.points = run.points + pts[1:]

    # The first run needs a tie because the thread starts there, and a trimmed
    # run needs one because the thread starts there too. Ask both questions in
    # one pass: the first run of a color is always both, and tying it twice
    # doubles the lock into eight stitches of thread piled in one spot.
    for i, run in enumerate(runs):
        if i == 0 or run.trim:
            tie_in(run)
        if run.trim and i > 0:
            tie_off(runs[i - 1])
    tie_off(runs[-1])


def sequence(
    planned: list[PlannedRegion], fabric: Fabric, cfg: PipelineConfig,
    source_pixels: SourcePixels | None = None,
    design_class: str = "flat",
) -> tuple[list[StitchBlock], list[dict]]:
    """-> (blocks in sew order, warnings).

    `design_class` is stage 0's verdict (PipelineResult.design_class, handed
    through by plan_stitches). Only the photo classes change anything here —
    the underlay split below; flat and gradient take byte-identical paths,
    which is why the default is "flat" and every pre-existing caller needs
    no edit.
    """
    row_mm = (cfg.fill_row_mm or FILL_ROW_MM) * max(0.1, fabric.density_adjust)
    stitch_mm = cfg.fill_stitch_mm or FILL_STITCH_MM
    # Row 14's underlay split (see _PHOTO_FILL_UNDERLAY above for the craft
    # case). Precedence is unchanged in shape, only the FALLBACK moves: an
    # explicit cfg.underlay_style still wins over the class default exactly
    # as it wins over the fabric preset, the design-wide `underlay` off
    # switch still zeroes both, and the per-shape meta["underlay_style"]
    # override still beats all of it both ways (`eff_underlay_style` in
    # stitch_one — its documented "beats the mode both ways" contract).
    photo = (design_class in PHOTO_CLASSES
             or bool(cfg.extra.get("photo_sequencing")))
    class_fill_underlay = _PHOTO_FILL_UNDERLAY if photo else fabric.fill_underlay
    underlay_style = (cfg.underlay_style or class_fill_underlay) if cfg.underlay else "none"
    satin_underlay = ((_PHOTO_SATIN_UNDERLAY if photo else fabric.satin_underlay)
                      if cfg.underlay else "none")
    satin_max = cfg.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    trim_at = fabric.trim_at_mm

    border_style = (cfg.border or "off").lower()
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
    technique = (cfg.fill_technique or "tatami").lower()
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

    thin = empty = jumps = as_run = 0
    bordered = lightened = border_narrow = 0
    rings_skipped = starved = 0
    blocks: list[StitchBlock] = []
    cursor: tuple[float, float] | None = None

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
            if tier == "satin" or (tier == "auto" and cfg.satin
                                   and is_satin_candidate(p.region.polygon, satin_max)):
                runs, report = satin_shape(
                    p.polygon,
                    p.shape_id,
                    underlay_style=satin_underlay,
                    trim_at_mm=trim_at,
                    start_near=entry,
                    split_above_mm=split_above,
                    end_cutback_mm=end_cutback,
                    use_shapefield=use_shapefield,
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
            # pair yet; it is recorded here rather than silently combined.
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
            elif streamline and source_pixels is not None:
                # Same contract again, thread-paint look: the explicit
                # opt-in beats the gradient class's blend routing, empty is
                # honest (an all-highlight shape sews nothing) and falls
                # through to tatami below rather than dropping artwork.
                runs, report = streamline_fill(p.region, source_pixels, cfg)
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
                want = border_style != "off"
            if want and runs:
                b_runs, b_report = border_runs(
                    p.visible_geom,
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
            if report.get("starved"):
                starved += 1
                rings_skipped += report.get("skipped_rings", 0)
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
            ordered, linked_in_shape = _chain(ordered, sewn)
            jumps -= linked_in_shape
        _apply_ties(ordered)

        thread = chart_for(cfg)[group[0].region.thread_index]
        blocks.append(
            StitchBlock(
                thread_index=group[0].region.thread_index,
                thread_number=thread.number,
                rgb=tuple(thread.rgb),
                runs=ordered,
            )
        )
        cursor = ordered[-1].points[-1]

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
    if (cfg.detail_layer or sketch) and source_pixels is not None:
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
                "to hold a fill or satin and sewed as a light outline run "
                "instead.",
                count=as_run,
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
    if border_narrow:
        warnings.append(
            warn(
                BORDER_SKIPPED_TOO_NARROW,
                f"{border_narrow} shape{'s were' if border_narrow != 1 else ' was'} "
                "too narrow to hold an outline at all, and went unbordered.",
                count=border_narrow,
            )
        )
    return blocks, warnings
