"""Beanie knockdown: a sparse fill under the whole design, sewn first.

Rule R9 of `docs/pro-digitizer-rules-2026-10-21.md`: every beanie job in the
professional's zip (Becker, Plowing, Roofing, Proseal, To a T — 6 files, 5
jobs) opens with one colour block that is nothing but a sparse tatami over
the design's whole footprint plus a margin. It flattens the knit's pile so
the design sits on top instead of sinking between the ribs. Read off the DSTs
(`docs/beanie-knockdown-2026-10-21.md` has the table and the script):

  * block 0, ONE piece — no trim inside it, every file;
  * rows 0.45-0.51 mm (`row_pitch_union`), no underlay (1d: BARE/RUNONLY);
  * stitch 3.0 mm (Roofing, Proseal) or 3.5 mm (the other four);
  * outline: the design grown with every hole filled. The same raster read
    gives 1.6-1.8 mm median margin on the four free-standing logos and 1.32
    on ours built at 1.5, so it reads about 0.2 mm short: the pro's margin is
    about 1.8-2.0 mm. On the two badge files it stops at the badge's satin
    border instead: +0.74 mm past its outer edge on To a T, 0.95 mm under it
    on Machine E (needle points against the design's outer edge). Kent
    2026-10-21: stop at the satin border, so a badge's knockdown ends on
    that edge (`badge_border`, `BADGE_EDGE_MM` 0);
  * thread: Khaki / PMS 155 on both PES files that carry the job — a colour
    the design does not use, i.e. the garment's.

So the block is sewn in the cone nearest `cfg.garment_rgb`, and when the
garment colour is unknown there is no knockdown: a design-coloured one would
sew a visible 2 mm halo round the logo, which is worse than none.

`cfg.beanie_knockdown`, and only ever for `garment_id == "beanie"`. Built
OFF and flipped ON by Kent on 2026-10-21 over the renders: like backing, it
is the engine's call per garment, not the customer's. The three constants
below are the professional's, read from his files and not sewn here.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from . import machine, stitches
from .stage6_fill import _densify, _inset_ring, _ring_route, stitch_shape
from .stitches import StitchBlock, StitchRun
from .threads import chart_for, rgb_to_lab

GARMENT = "beanie"
#: Row spacing of the knockdown tatami. [P] candidate, gate 1 — the pro's
#: 0.48-0.50 (`row_pitch_union` 0.45-0.51 over his six files).
ROW_MM = 0.50
#: Stitch length along a row. [P] candidate — 3.5 on four files, 3.0 on two.
STITCH_MM = 3.5
#: How far past the design's outline the knockdown reaches. [P] candidate —
#: the pro's four free-standing logos read 1.6-1.8 mm median through a raster
#: that reads ours (built at 1.5) as 1.32, so about 1.8-2.0 mm.
MARGIN_MM = 2.0
#: Simplify the grown outline to this before filling it: a buffer's round
#: joins carry hundreds of vertices that move no row end visibly.
OUTLINE_SIMPLIFY_MM = 0.05
#: Pieces of the grown outline smaller than this are dropped (a stray speck
#: of the design grown into a 3 mm disc is not worth a trim).
MIN_PIECE_MM2 = 10.0
#: Badge: where the knockdown stops relative to the satin border's OUTER edge
#: (mm, + outside). Kent 2026-10-21: "stop at the satin border". See
#: `badge_border`.
BADGE_EDGE_MM = 0.0
#: A badge border is a RING: its hole holds at least this share of the area
#: inside its outer edge (To a T's: 95%), so a solid shape with counters is not
#: one.
BADGE_HOLE_SHARE = 0.5
#: ...and every other shape lies inside its outer edge, give or take this
#: much of their area (a stray speck just outside does not undo a badge).
BADGE_OUTSIDE_SHARE = 0.01
#: Slack on "inside its outer edge", mm: a shape abutting the ring's outside.
BADGE_SLACK_MM = 0.3
SHAPE_ID = "knockdown"


def applies(cfg) -> bool:
    return bool(getattr(cfg, "beanie_knockdown", False)) and cfg.garment_id == GARMENT


def badge_border(shapes, satin_ids) -> Polygon | None:
    """The outer edge of the design's badge border, or None.

    `shapes` are (shape_id, polygon) pairs, `satin_ids` the shapes stage 7
    sewed as satin columns. A badge border is a satin RING (`BADGE_HOLE_SHARE`)
    whose outer edge holds every other shape (`BADGE_OUTSIDE_SHARE`). On the
    pro's two badge beanies (To a T, Machine E) the knockdown stops at that
    border instead of running 2 mm past it; on every free-standing logo there
    is no such shape and the margin applies."""
    best = None
    for sid, g in shapes:
        if sid not in satin_ids or g.geom_type != "Polygon" or not g.interiors:
            continue
        outer = Polygon(g.exterior)
        if outer.area <= 0 or (outer.area - g.area) < BADGE_HOLE_SHARE * outer.area:
            continue
        others = [o for oid, o in shapes if oid != sid and not o.is_empty]
        total = sum(o.area for o in others)
        if total <= 0:
            continue
        inside = outer.buffer(BADGE_SLACK_MM)
        out = sum(o.difference(inside).area for o in others)
        if out > BADGE_OUTSIDE_SHARE * total:
            continue
        if best is None or outer.area > best.area:
            best = outer
    return best


def outline(polys, margin_mm: float = MARGIN_MM, badge: Polygon | None = None) -> list[Polygon]:
    """The design's footprint grown by `margin_mm`, holes filled, largest first.

    With `badge` (`badge_border`'s outer edge) everything inside it is covered
    out to `BADGE_EDGE_MM` from that edge and no further; only a shape lying
    outside it still gets the margin."""
    polys = [p for p in polys if p is not None and not p.is_empty]
    if not polys:
        return []
    if badge is not None:
        inside = badge.buffer(BADGE_SLACK_MM)
        parts = [badge.buffer(BADGE_EDGE_MM, join_style=2) if BADGE_EDGE_MM else badge]
        parts += [p.buffer(0).buffer(margin_mm) for p in polys if not inside.covers(p)]
        grown = unary_union(parts)
    else:
        grown = unary_union([p.buffer(0) for p in polys]).buffer(margin_mm)
    # Filling holes is a second union, not a per-piece step: an island of the
    # design inside a wide counter grows into its own piece, which lies inside
    # its host once the host's hole is filled and would sew twice.
    solids = unary_union([Polygon(g.exterior) for g in getattr(grown, "geoms", [grown])
                          if g.geom_type == "Polygon" and not g.is_empty])
    pieces = []
    for g in getattr(solids, "geoms", [solids]):
        if g.geom_type != "Polygon" or g.is_empty:
            continue
        solid = Polygon(g.exterior).simplify(OUTLINE_SIMPLIFY_MM, preserve_topology=True)
        if solid.area >= MIN_PIECE_MM2:
            pieces.append(solid)
    return sorted(pieces, key=lambda p: -p.area)


def _bridge(poly: Polygon, cover: Polygon, rings, a, b):
    """A needle-down route from a to b inside `poly`, however long, or None.

    Stage 6's `travel_path` gives up past four times the straight distance
    (or 20 mm) and lifts the needle; on Becker that cost the knockdown three
    trims where the pro's has none on any of his six files. Here the thread is
    the garment's colour and everything else sews over it, so a long run along
    the edge costs only thread: straight when straight stays inside, else the
    shorter of the two ways round whichever inset ring stays inside."""
    if cover.covers(LineString([a, b])):
        return _densify(a, b, machine.TRAVEL_STITCH_MM)
    best = None
    pa, pb = Point(a), Point(b)
    for ring in sorted(rings, key=lambda r: max(r.distance(pa), r.distance(pb)))[:3]:
        for way in ("ahead", "back"):
            route = [a, *_ring_route(ring, a, b, way), b]
            if not cover.covers(LineString(route)):
                continue
            length = sum(math.dist(p, q) for p, q in zip(route, route[1:]))
            if best is None or length < best[0]:
                best = (length, route)
    if best is None:
        return None
    out, cur = [], a
    for p in best[1][1:]:
        out.extend(_densify(cur, p, machine.TRAVEL_STITCH_MM))
        cur = p
    return out


def _stay_down(runs: list[StitchRun], poly: Polygon) -> list[StitchRun]:
    """`runs` (one piece's, from `stitch_shape`) with every lift inside the
    piece replaced by a travel run along `_bridge`, where one exists."""
    cover = poly.buffer(0.01)
    rings = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    out: list[StitchRun] = []
    for run in runs:
        if run.jump and out:
            route = _bridge(poly, cover, rings, out[-1].points[-1], run.points[0])
            if route is not None:
                if route[:-1]:
                    out.append(StitchRun(points=route[:-1], kind=stitches.TRAVEL,
                                         shape_id=SHAPE_ID))
                run.jump = run.trim = False
        out.append(run)
    return out


def satin_shape_ids(blocks) -> set[str]:
    """Shapes stage 7 sewed mostly as satin columns (satin/border points over
    fill points)."""
    sat: dict[str, int] = {}
    fill: dict[str, int] = {}
    for b in blocks:
        for r in b.runs:
            if r.kind in (stitches.SATIN, stitches.BORDER):
                sat[r.shape_id] = sat.get(r.shape_id, 0) + len(r.points)
            elif r.kind == stitches.FILL:
                fill[r.shape_id] = fill.get(r.shape_id, 0) + len(r.points)
    return {sid for sid, n in sat.items() if n > fill.get(sid, 0)}


def knockdown_block(shapes, cfg, trim_at_mm: float,
                    satin_ids=frozenset()) -> tuple[StitchBlock | None, dict]:
    """-> (the knockdown block, report) or (None, report) when it declines.

    `shapes` are the plan's (shape_id, polygon) pairs (stage 5's polygons; a
    bare polygon is accepted as one with no id), `satin_ids` the ones sewn as
    satin (`satin_shape_ids`), which is how a badge border is told. The block's
    runs are tied like any colour block's: in at the start, off at the end and
    either side of every trim between pieces.
    """
    report = {"applied": False, "reason": "", "pieces": 0, "area_mm2": 0.0, "badge": False}
    if cfg.garment_rgb is None:
        report["reason"] = "no garment colour"
        return None, report
    shapes = [s if isinstance(s, tuple) else (f"_{i}", s) for i, s in enumerate(shapes)]
    badge = badge_border(shapes, satin_ids)
    report["badge"] = badge is not None
    pieces = outline([g for _, g in shapes], badge=badge)
    if not pieces:
        report["reason"] = "nothing to cover"
        return None, report
    runs: list[StitchRun] = []
    for poly in pieces:
        here = runs[-1].points[-1] if runs else None
        got, _ = stitch_shape(poly, SHAPE_ID, angle_deg=None, row_mm=ROW_MM,
                              stitch_mm=STITCH_MM, underlay_style="none",
                              trim_at_mm=trim_at_mm, start_near=here)
        if not got:
            continue
        got = _stay_down(got, poly)
        if runs:
            first = got[0]
            first.jump = True
            first.trim = math.dist(here, first.points[0]) > trim_at_mm
        runs.extend(got)
    if not runs:
        report["reason"] = "fill produced nothing"
        return None, report
    stitches.apply_ties(runs)
    chart = chart_for(cfg)
    rgb = np.array([list(cfg.garment_rgb)[:3]], dtype=np.float64)
    idx = chart.nearest_index(rgb_to_lab(rgb)[0])
    block = StitchBlock(thread_index=idx, thread_number=chart[idx].number,
                        rgb=tuple(chart[idx].rgb), runs=runs)
    report.update(applied=True, pieces=len(pieces),
                  area_mm2=round(float(sum(p.area for p in pieces)), 1),
                  thread=chart[idx].number)
    return block, report


def prepend(blocks: list[StitchBlock], kd: StitchBlock) -> list[StitchBlock]:
    """The knockdown first. When the design's first block is the same cone
    (and an ordinary block, not a specialty step) it joins that block across
    a trim instead of costing the operator a stop for no change of thread."""
    if blocks and blocks[0].thread_index == kd.thread_index and blocks[0].step is None:
        head = blocks[0]
        if head.runs:
            head.runs[0].jump = True
            head.runs[0].trim = True
        merged = StitchBlock(thread_index=head.thread_index,
                             thread_number=head.thread_number, rgb=head.rgb,
                             runs=[*kd.runs, *head.runs], step=None)
        return [merged, *blocks[1:]]
    return [kd, *blocks]
