"""Stage 6 3D puff: config gate, per-shape eligibility, and the construction
of one puffed shape (end-capped puff satin, tied) and its foam tack-down.

Spec: docs/superpowers/specs/2026-11-19-3d-puff-design.md. Satin only; tatami
never puffs. Eligibility is against the puff width band (machine.PUFF_*),
never the flat satin ceiling.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point

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
    """One puffed shape -> runs in sew order: the end-caps, then the top
    satin, tied at PUFF_TIE_STITCHES (§3.9).

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
    for pts in order:
        _join(runs, StitchRun(points=pts, kind=SATIN, shape_id=shape_id), poly, shape_id)
    if runs:
        _join(runs, satin[0], poly, shape_id)
        runs += satin[1:]
    else:
        runs = satin
    _apply_puff_ties(runs)
    return runs


# --- Foam tack-down ----------------------------------------------------------

def _walk_ring(coords, cursor) -> list[tuple[float, float]]:
    """A closed ring as stitches no longer than PUFF_TACKDOWN_STITCH_MM, from
    the vertex nearest `cursor` round and back to it; every point is on it."""
    if len(coords) < 3:
        return []
    coords = [(float(x), float(y)) for x, y in coords]
    if cursor is not None:
        k = min(range(len(coords)), key=lambda i: math.dist(cursor, coords[i]))
        coords = coords[k:] + coords[:k]
    coords.append(coords[0])
    out = [coords[0]]
    for a, b in zip(coords, coords[1:]):
        steps = max(1, math.ceil(math.dist(a, b) / machine.PUFF_TACKDOWN_STITCH_MM))
        out += [(a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps)
                for s in range(1, steps + 1)]
    out[-1] = out[0]
    # §3.7 "twice around": the second pass comes back over the same path.
    return out + out[-2::-1]


def puff_tackdown(polys: list, shape_ids: list[str], cfg) -> list[StitchRun]:
    """The foam tack-down (spec "Tack-down", §3.7's walk): one run round every
    ring of every puffed shape, inset PUFF_INSET_MM, at
    PUFF_TACKDOWN_STITCH_MM, two passes (round and back over the same path,
    §3.7 "twice around"), each ring started nearest the needle. Untied:
    it sews as ordinary flat stitching before the foam stop."""
    runs: list[StitchRun] = []
    cursor = None
    for poly, sid in zip(polys, shape_ids):
        inset = poly.buffer(-machine.PUFF_INSET_MM, join_style=2)
        for part in getattr(inset, "geoms", [inset]):
            if part.is_empty or part.geom_type != "Polygon":
                continue
            for ring in [part.exterior, *part.interiors]:
                pts = _walk_ring(list(ring.coords)[:-1], cursor)
                if len(pts) < 4:
                    continue
                run = StitchRun(points=pts, kind=RUN, shape_id=sid)
                if cursor is not None:
                    run.jump = True
                    run.trim = math.dist(cursor, pts[0]) >= machine.TRIM_AT_MM
                runs.append(run)
                cursor = pts[-1]
    return runs
