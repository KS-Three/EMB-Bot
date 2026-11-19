"""Stage 6 3D puff: config gate, per-shape eligibility, and the construction
of one puffed shape (inset walk, end-capped puff satin, tied) and the
pre-stop foam grip (`puff_tackdown`).

Spec: docs/superpowers/specs/2026-11-19-3d-puff-design.md. Satin only; tatami
never puffs. Eligibility is against the puff width band (machine.PUFF_*),
never the flat satin ceiling.
"""
from __future__ import annotations

import math

from shapely.geometry import LinearRing, LineString, Point

from . import machine
from .stitches import RUN, SATIN, TRAVEL, StitchRun, tie_run
from .stitchwidth import measure_width_mm


def _max_inscribed_diameter_mm(geom) -> float:
    """Widest inscribed circle's diameter over every part; holes count as edges."""
    from shapely.ops import polylabel
    parts = list(getattr(geom, "geoms", [geom]))
    best = 0.0
    for part in parts:
        try:
            c = polylabel(part, tolerance=0.02)
            best = max(best, 2.0 * float(part.boundary.distance(c)))
        except Exception:  # noqa: BLE001 -- a degenerate part has no width
            continue
    return best


def wants_puff(region, cfg) -> bool:
    """Master switch gates everything; then mode and per-shape meta."""
    if not cfg.puff:
        return False
    want = region.meta.get("puff")
    if cfg.puff_mode == "select":
        return want is True
    return want is not False


def puff_eligible(region, cfg) -> tuple[bool, str]:
    """-> (eligible, reason); reason is "" when eligible."""
    geom = region.polygon
    # measure_width_mm takes a single Polygon: a MultiPolygon is judged by its
    # largest part.
    main = max(getattr(geom, "geoms", [geom]), key=lambda g: g.area)
    w = measure_width_mm(main)
    if w is None or w < machine.PUFF_MIN_WIDTH_MM:
        shown = "0.0" if w is None else f"{w:.1f}"
        return False, f"too thin for foam ({shown} mm)"
    # Too wide is the widest inscribed circle, not the skeleton mean: the mean
    # under-reads wide bars (a 14 mm bar reads 9.8) and would defeat the ceiling.
    widest = _max_inscribed_diameter_mm(region.polygon)
    if widest > machine.PUFF_MAX_WIDTH_MM:
        return False, f"too wide to puff ({widest:.1f} mm)"
    return True, ""


# --- Ties (§3.9: 5 in, 5 off, for the foam's thickness) ----------------------

def _puff_tie(at, toward) -> list[tuple[float, float]]:
    """The PUFF_TIE_STITCHES points that lead INTO `at`, bouncing between a
    point into the shape and `at` (so PUFF_TIE_STITCHES stitches arrive at
    `at`). The inner point is `stitches.tie_run`'s, so a leg never overshoots
    the path; only the leg COUNT is puff's, and `tie_run`'s default stays."""
    pts = tie_run(at, toward).points
    if len(pts) < 2:
        return []
    inner = pts[1]
    n = machine.PUFF_TIE_STITCHES
    # ..., inner, at, inner -> at: the last lead point is always `inner`.
    return [inner if (n - k) % 2 == 1 else at for k in range(n)]


def _tie_puff_in(run: StitchRun) -> None:
    if len(run.points) < 2:
        return
    lead = _puff_tie(run.points[0], run.points[1])
    run.points = lead + run.points
    run.tie_in_pts += len(lead)


def _tie_puff_off(run: StitchRun) -> None:
    if len(run.points) < 2:
        return
    run.points = run.points + _puff_tie(run.points[-1], run.points[-2])[::-1]


def _apply_puff_ties(runs: list[StitchRun]) -> None:
    """`stitches.apply_ties`' rule -- tie in at the start and after every cut,
    tie off before every cut and at the end -- at puff's leg count."""
    for i, run in enumerate(runs):
        if i == 0 or run.trim:
            _tie_puff_in(run)
        if run.trim and i > 0:
            _tie_puff_off(runs[i - 1])
    if runs:
        _tie_puff_off(runs[-1])


# --- End-caps (§3.5 method 1) ------------------------------------------------

def _unit(v):
    d = math.hypot(v[0], v[1])
    return (v[0] / d, v[1] / d) if d > 1e-9 else None


def _column_end(points, at_start: bool):
    """One end of a satin run, read off its crosses (consecutive pairs of
    penetrations). -> (outward unit, lateral unit, reference centre, half
    width) or None. Read from a cross ~1 mm inboard: the end cross itself
    can be a half cross, and the cap must run square to the column."""
    pairs = [(points[i], points[i + 1]) for i in range(0, len(points) - 1, 2)]
    if len(pairs) < 3:
        return None
    if not at_start:
        pairs = pairs[::-1]
    mid = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in pairs]
    # ~1 mm in along BOTH rails: a half end cross moves its midpoint across
    # the column, so a midpoint distance would stop one station in.
    k = 1
    while k < len(pairs) - 1 and min(math.dist(pairs[k][0], pairs[0][0]),
                                     math.dist(pairs[k][1], pairs[0][1])) < 1.0:
        k += 1
    # The short-stitch guard pulls every other cross in on a dense column,
    # so take the fuller of two neighbours as the column's width.
    if k + 1 < len(pairs) and math.dist(*pairs[k + 1]) > math.dist(*pairs[k]):
        k += 1
    a, b = pairs[k]
    lat = _unit((b[0] - a[0], b[1] - a[1]))
    if lat is None:
        return None
    out = (-lat[1], lat[0])
    if (mid[0][0] - mid[k][0]) * out[0] + (mid[0][1] - mid[k][1]) * out[1] < 0:
        out = (-out[0], -out[1])
    return out, lat, mid[k], math.dist(a, b) / 2.0


def _closes_on_itself(points, poly) -> bool:
    """A column whose two ends meet: the run's first and last crosses are
    near each other with nothing but the shape between them. An O's seam
    measured 2.3 mm apart, with the closing crosses skewed so `_open_end`'s
    probe reads one end as free; a C's two ends straddle its gap, so the
    line between them leaves the shape and the C keeps both caps."""
    if len(points) < 4:
        return False
    a = ((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2)
    b = ((points[-1][0] + points[-2][0]) / 2, (points[-1][1] + points[-2][1]) / 2)
    if math.dist(a, b) > machine.PUFF_MAX_WIDTH_MM:
        return False
    return math.dist(a, b) < 1e-6 or poly.buffer(0.01).contains(LineString([a, b]))


def _open_end(poly, end) -> bool:
    """A terminus no other column continues: just past it is outside the art.
    A closed ring's seam and an arm run into a junction both land inside."""
    out, _lat, ref, _half = end
    probe = Point(ref[0] + out[0] * 1.5, ref[1] + out[1] * 1.5)  # ref is ~1 mm in
    return not poly.buffer(-0.05).contains(probe)


def _end_cap(poly, end) -> list[tuple[float, float]]:
    """Cap rows over one open column end: one stitch per lateral station,
    along the spine, from the art edge in by PUFF_CAP_DEPTH_MM, stations
    PUFF_CAP_SPACING_MM apart across the column, sewn as a zigzag. The
    outboard penetrations are the line that closes the end. [] if none fit."""
    out, lat, ref, half = end
    reach = 3.0 * half + 2.0
    span = max(0.0, half - 0.05)
    n = max(1, math.ceil(2 * span / machine.PUFF_CAP_SPACING_MM))
    pts: list[tuple[float, float]] = []
    for j in range(n + 1):
        t = -span + 2 * span * j / n
        base = (ref[0] + lat[0] * t, ref[1] + lat[1] * t)
        far = (base[0] + out[0] * reach, base[1] + out[1] * reach)
        piece = LineString([base, far]).intersection(poly)
        # Only the piece connected to the column (it starts at `base`).
        parts = [g for g in getattr(piece, "geoms", [piece])
                 if g.geom_type == "LineString" and not g.is_empty
                 and g.distance(Point(base)) < 1e-6]
        if not parts:
            continue
        s_out = max((c[0] - base[0]) * out[0] + (c[1] - base[1]) * out[1]
                    for c in parts[0].coords)
        s_in = max(0.0, s_out - machine.PUFF_CAP_DEPTH_MM)
        if s_out - s_in < 0.1:
            continue
        o = (base[0] + out[0] * s_out, base[1] + out[1] * s_out)
        i = (base[0] + out[0] * s_in, base[1] + out[1] * s_in)
        pts += [o, i] if len(pts) % 4 == 0 else [i, o]
    return pts


def _join(runs: list[StitchRun], nxt: StitchRun, poly, shape_id: str) -> None:
    """Append `nxt`, reached from the last run's end by a travel run when the
    straight line stays inside the shape (it is buried under satin sewn
    later), else by a jump, trimmed at TRIM_AT_MM."""
    if runs:
        a, b = runs[-1].points[-1], nxt.points[0]
        d = math.dist(a, b)
        nxt.jump = nxt.trim = False
        if d > 1e-6:
            if poly.buffer(0.01).contains(LineString([a, b])):
                steps = max(1, math.ceil(d / machine.RUN_STITCH_MM))
                runs.append(StitchRun(
                    points=[(a[0] + (b[0] - a[0]) * s / steps,
                             a[1] + (b[1] - a[1]) * s / steps) for s in range(steps + 1)],
                    kind=TRAVEL, shape_id=shape_id))
            else:
                nxt.jump = True
                nxt.trim = d >= machine.TRIM_AT_MM
    runs.append(nxt)


def puff_shape(poly, shape_id: str, cfg) -> list[StitchRun]:
    """One puffed shape -> runs in sew order: §3.7's inset walk (every ring,
    two passes, `_inset_walk`), the end-caps, then the top satin, tied at
    PUFF_TIE_STITCHES (§3.9) at the walk's start and the satin's end.

    The top satin is `satin_shape` at PUFF_SATIN_SPACING_MM with no underlay
    (§3.7: underlay crushes the foam) and puff's own width ceiling.
    `junction_stack` is forced on: it runs an arm into its node by its own
    half width, which is §3.8's junction overlap -- at least
    PUFF_JUNCTION_OVERLAP_MM for any puffable width, since half of
    PUFF_MIN_WIDTH_MM exceeds it. Off, a T's stem stops 0.3 mm short of its
    bar and the foam leaks through the gap.

    Satin penetrates only along its rails, so each OPEN column terminus gets a
    cap (`_end_cap`) sewn before the top satin covers it (§3.5). A closed
    column (an O) has no terminus; its two rails already close both rings."""
    from .stage6_satin import satin_shape
    satin, _report = satin_shape(
        poly, shape_id, underlay_style="none", trim_at_mm=machine.TRIM_AT_MM,
        split_above_mm=machine.PUFF_MAX_WIDTH_MM,
        spacing_mm=machine.PUFF_SATIN_SPACING_MM,
        max_width_mm=machine.PUFF_MAX_WIDTH_MM,
        use_shapefield=bool(cfg.extra.get("shapefield")),
        patch_junctions=cfg.satin_patch_junctions,
        stroke_order=cfg.satin_stroke_order,
        corner_twigs=cfg.satin_corner_twigs,
        junction_stack=True,
        # §3.6 "short stitches OFF": at 0.18 mm the guard would retract every
        # other penetration 0.6 mm into the shape, crushing the foam there.
        short_stitches=False)
    # satin_shape is memoized: copy before tying, never mutate its runs.
    satin = [StitchRun(points=list(r.points), kind=r.kind, jump=r.jump, trim=r.trim,
                       shape_id=r.shape_id, shade_thread_index=r.shade_thread_index,
                       role=r.role, piece=r.piece, tie_in_pts=r.tie_in_pts)
             for r in satin if r.points]
    if not satin:
        return []
    caps = []
    for r in satin:
        if r.kind != SATIN:
            continue
        if _closes_on_itself(r.points, poly):
            continue  # a closed column (an O): no terminus
        for at_start in (True, False):
            end = _column_end(r.points, at_start)
            if end is not None and _open_end(poly, end):
                pts = _end_cap(poly, end)
                if len(pts) >= 2:
                    caps.append(pts)
    # Chain the caps backwards from where the top satin starts, so the last
    # cap sewn ends nearest it and each one ends nearest the next.
    order, cursor = [], satin[0].points[0]
    while caps:
        nxt = min(caps, key=lambda c: min(math.dist(cursor, c[0]), math.dist(cursor, c[-1])))
        caps.remove(nxt)
        if math.dist(cursor, nxt[0]) < math.dist(cursor, nxt[-1]):
            nxt = nxt[::-1]
        order.insert(0, nxt)
        cursor = nxt[0]
    runs: list[StitchRun] = []
    # §3.7's inset walk first, in place of underlay: every ring, two passes,
    # started nearest where the caps (or the top satin) begin.
    for walk in _inset_walk(poly, shape_id, order[0][0] if order else satin[0].points[0]):
        _join(runs, walk, poly, shape_id)
    for pts in order:
        _join(runs, StitchRun(points=pts, kind=SATIN, shape_id=shape_id), poly, shape_id)
    if runs:
        _join(runs, satin[0], poly, shape_id)
        runs += satin[1:]
    else:
        runs = satin
    # One tie rule over the whole shape: in at its first run (the walk) and
    # after every cut, off before every cut and at its last run.
    _apply_puff_ties(runs)
    return runs


# --- Foam tack-down ----------------------------------------------------------

# How far a thinned walk/grip ring may stray from the traced one: a
# geometry tolerance (well under a stitch width), not a physical constant.
_WALK_TOLERANCE_MM = 0.1


def _walk_ring(coords, cursor, stitch_mm: float = None,
               passes: int = 2) -> list[tuple[float, float]]:
    """A closed ring as stitches no longer than `stitch_mm` (default
    PUFF_TACKDOWN_STITCH_MM), from the vertex nearest `cursor` round and back
    to it; every point is on it. `passes=2` is §3.7's "twice around": the
    second pass comes back over the same path."""
    if stitch_mm is None:
        stitch_mm = machine.PUFF_TACKDOWN_STITCH_MM
    if len(coords) < 3:
        return []
    # A traced contour carries a vertex every pixel step, far closer than a
    # stitch; subdividing per segment would put a penetration on every one
    # (TIRES at 114 mm: a 597-stitch "4 mm" grip on one shape). Thin the
    # ring first (Douglas-Peucker keeps a subset of its vertices, every
    # dropped one within _WALK_TOLERANCE_MM of the result), then subdivide.
    thin = LinearRing(coords).simplify(_WALK_TOLERANCE_MM, preserve_topology=False)
    if not thin.is_empty and len(thin.coords) >= 4:
        coords = list(thin.coords)[:-1]
    coords = [(float(x), float(y)) for x, y in coords]
    if cursor is not None:
        k = min(range(len(coords)), key=lambda i: math.dist(cursor, coords[i]))
        coords = coords[k:] + coords[:k]
    coords.append(coords[0])
    out = [coords[0]]
    for a, b in zip(coords, coords[1:]):
        steps = max(1, math.ceil(math.dist(a, b) / stitch_mm))
        out += [(a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps)
                for s in range(1, steps + 1)]
    out[-1] = out[0]
    return out + out[-2::-1] if passes == 2 else out


def _inset_rings(poly, outer_only: bool):
    """The rings of `poly` inset PUFF_INSET_MM: every ring, or only each
    part's outer ring (no counters)."""
    inset = poly.buffer(-machine.PUFF_INSET_MM, join_style=2)
    for part in getattr(inset, "geoms", [inset]):
        if part.is_empty or part.geom_type != "Polygon":
            continue
        yield part.exterior
        if not outer_only:
            yield from part.interiors


def _inset_walk(poly, shape_id: str, cursor) -> list[StitchRun]:
    """§3.7's inset walk, the puff satin's replacement for underlay: every
    ring of the shape, counters included, inset PUFF_INSET_MM, at
    PUFF_TACKDOWN_STITCH_MM, two passes, each ring started nearest the
    needle. Joined and tied by `puff_shape`, never here."""
    runs: list[StitchRun] = []
    for ring in _inset_rings(poly, outer_only=False):
        pts = _walk_ring(list(ring.coords)[:-1], cursor)
        if len(pts) < 4:
            continue
        runs.append(StitchRun(points=pts, kind=RUN, shape_id=shape_id))
        cursor = pts[-1]
    return runs


def puff_tackdown(polys: list, shape_ids: list[str], cfg) -> list[StitchRun]:
    """The pre-stop "puff grip" (spec "Tack-down"; the pro's 279-stitch
    "Puff Grip"): ONE pass round each puffed shape's OUTER ring only (no
    counters), inset PUFF_INSET_MM, at PUFF_GRIP_STITCH_MM, each ring started
    nearest the needle. It holds the foam's position; §3.7's two-pass walk of
    every ring is not this, it sews after the stop (`puff_shape`). Untied:
    it sews as ordinary flat stitching before the foam stop."""
    runs: list[StitchRun] = []
    cursor = None
    for poly, sid in zip(polys, shape_ids):
        for ring in _inset_rings(poly, outer_only=True):
            pts = _walk_ring(list(ring.coords)[:-1], cursor,
                             stitch_mm=machine.PUFF_GRIP_STITCH_MM, passes=1)
            if len(pts) < 4:
                continue
            run = StitchRun(points=pts, kind=RUN, shape_id=sid)
            if cursor is not None:
                run.jump = True
                run.trim = math.dist(cursor, pts[0]) >= machine.TRIM_AT_MM
            runs.append(run)
            cursor = pts[-1]
    return runs


# --- The pass (stage 7's puff tier) ------------------------------------------

PUFF_TACKDOWN_CODE = "PUFF_TACKDOWN"
PUFF_CODE = "PUFF"
NOT_A_COLUMN = "not a column shape"


def puff_column(region, cfg, design_class: str = "flat") -> bool:
    """Puff is satin only, so a shape puffs only if it is a column shape:
    never the design's ground (`meta["enclosed_background"]`, stage 4's tag
    from stage 1's mask -- the one region-level background fact stage 7's
    depth order reads), and only when stage 7's own satin decision
    (`stage7_sequence._sews_satin`, the predicate `stitch_one` routes on)
    says satin with puff's width ceiling in place of the flat one. A white
    ground stage 1 could not find (BACKGROUND_ABSENT) carries no tag; it is
    refused here because it is no column. `outlines` is not passed: stage 7
    builds that set later, and without it the predicate errs toward fill.

    Asked with `cfg.border_by_size` off: that rule sends every shape about
    6 mm across or more to "a fill under a border, never whole satin", which
    is the flat width preference the spec re-routes for puff ("puff's own
    ceiling applies"); left on, the 3-11 mm band would end near 6 mm."""
    from dataclasses import replace
    # Local on purpose: stage7_sequence imports this module (puff_pass), so
    # a top-level import of stage 7 here would be a circular pair.
    from .stage7_sequence import _sews_satin
    if region.meta.get("enclosed_background"):
        return False
    if getattr(cfg, "border_by_size", False):
        cfg = replace(cfg, border_by_size=False)
    return _sews_satin(region, cfg, machine.PUFF_MAX_WIDTH_MM, design_class)


def puff_pass(planned, cfg, chart, design_class: str = "flat"
              ) -> tuple[list, list[dict], list]:
    """The stage-7 puff branch. -> (blocks, warnings, remaining).

    Off (`cfg.puff` False) this is `([], [], list(planned))` and touches
    nothing. On, every shape `wants_puff` and `puff_eligible` passes leaves
    the flat sequence; the rest go back to the colour loop in their order.
    Puffed shapes are grouped by thread in sew order, and each puff thread
    becomes two operator-step blocks: the tack-down round all of that
    thread's shapes, stopping for the foam, then the puff satin of each
    shape (`puff_shape`, already tied at PUFF_TIE_STITCHES -- never run
    through `stitches.apply_ties`, which would lock it twice), stopping to
    tear the foam away. Satin only: a puffed shape is never tatami, even
    past the flat satin ceiling (eligibility caps the width).

    Stage 7 appends these blocks LAST, after every other block: foam goes
    on top of finished flat work. Each step's `index` here counts from this
    list's first block; stage 7 renumbers it to the block's place in the plan.
    """
    from .stage6_applique import COLOR_CHANGE, Step, assert_steps_valid
    from .stitches import StitchBlock, apply_ties, drop_tie_ins
    from .warnings_codes import PUFF_NONE_ELIGIBLE, PUFF_SHAPE_INELIGIBLE, warn

    if not cfg.puff:
        return [], [], list(planned)

    wanted = [p for p in planned if wants_puff(p.region, cfg)]
    warnings: list[dict] = []
    satins: dict[int, list] = {}  # id(planned region) -> its tied puff satin

    def ineligible(p, reason):
        warnings.append(warn(
            PUFF_SHAPE_INELIGIBLE,
            f"Shape {p.shape_id} can't be puffed ({reason}), so it sews flat.",
            shape_id=p.shape_id, reason=reason))

    for p in wanted:
        if not puff_column(p.region, cfg, design_class):
            ineligible(p, NOT_A_COLUMN)
            continue
        ok, reason = puff_eligible(p.region, cfg)
        if not ok:
            ineligible(p, reason)
            continue
        runs = puff_shape(p.region.polygon, p.shape_id, cfg)
        if not runs:
            ineligible(p, "no satin column")
            continue
        satins[id(p)] = runs

    picked = [p for p in planned if id(p) in satins]
    # Bottom-to-top, as appliqué orders its pieces: stage 5 settled the layers.
    picked.sort(key=lambda p: (p.region.meta.get("layer", 0), p.sew_index, p.shape_id))
    threads: list[int] = []
    for p in picked:
        if p.region.thread_index not in threads:
            threads.append(p.region.thread_index)

    blocks: list = []
    sewn: set[int] = set()
    for t_index in threads:
        group = [p for p in picked if p.region.thread_index == t_index]
        tack = puff_tackdown([p.region.polygon for p in group],
                             [p.shape_id for p in group], cfg)
        if not tack:
            # No foam stop without a tack-down to hold the foam: sew flat.
            for p in group:
                ineligible(p, "no room for a foam tack-down")
            continue
        # The tack-down is ordinary flat stitching: stage 7's own tie rule,
        # and its run-start locks go when stage 7's do (`cfg.tie_in_off`).
        tack[0].jump = tack[0].trim = True
        apply_ties(tack)
        top: list[StitchRun] = []
        for p in group:
            runs = satins[id(p)]
            if top:
                # Shape to shape is a lift, never a needle-down drag across
                # the foam; cut at TRIM_AT_MM, as `puff_tackdown` does.
                gap = math.dist(top[-1].points[-1], runs[0].points[0])
                runs[0].jump = True
                runs[0].trim = gap >= machine.TRIM_AT_MM
            top += runs
        steps = [
            Step(code=PUFF_TACKDOWN_CODE, label="Puff outline", runs=tack,
                 action="Stop: lay 3 mm puff foam over the outline, then continue",
                 function=COLOR_CHANGE),
            Step(code=PUFF_CODE, label="3D puff", runs=top,
                 action="Tear away the excess foam, then continue",
                 function=COLOR_CHANGE),
        ]
        assert_steps_valid(steps)
        thread = chart[t_index]
        for st in steps:
            # A new block always lifts in and cuts out, as appliqué's do.
            st.runs[0].jump = st.runs[0].trim = True
            blk = StitchBlock(thread_index=t_index, thread_number=thread.number,
                              rgb=tuple(thread.rgb), runs=st.runs)
            if st.code == PUFF_TACKDOWN_CODE and cfg.tie_in_off:
                drop_tie_ins([blk])
            blk.step = st.as_meta(len(blocks) + 1, thread.number)
            blocks.append(blk)
        sewn.update(id(p) for p in group)

    if wanted and not sewn:
        warnings.append(warn(
            PUFF_NONE_ELIGIBLE,
            "No shape in this design can be puffed (puff needs satin columns "
            f"{machine.PUFF_MIN_WIDTH_MM:g}–{machine.PUFF_MAX_WIDTH_MM:g} mm "
            "wide), so it sews flat.",
            count=len(wanted)))
    return blocks, warnings, [p for p in planned if id(p) not in sewn]
