"""Stage 6 — turning a polygon into stitches.

Three things decide whether a fill looks professional or homemade, and all
three are here:

1. **Stagger.** Every row's penetrations are offset by a fraction of a stitch,
   repeating every `FILL_STAGGERS` rows. Without it every row starts its
   stitches at the same place, the needle holes line up, and light runs down
   those channels — the single most recognisable mark of a naive scanline fill.

2. **Where the rows go.** Rows are cut into monotone columns first: a strip of
   consecutive rows that each contribute exactly one span. Where a shape forks
   (the top of a ring splitting around its hole) the column ends and new ones
   begin. Boustrophedon inside a column is then exact, and every awkward move
   becomes an explicit travel decision instead of a stitch flung across a hole.

3. **Travel.** Between columns the thread has to get somewhere. In order of
   preference: a straight run if it stays inside the shape, a run following the
   shape's own edge if it does not, and only then a needle-up jump. Fills that
   sew a line straight across a counter are the classic auto-digitizer tell.

Everything works in mm, y-down, the same space stage 4 produced.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon

from . import machine, stitches
from .stitches import StitchRun

# Spans on adjacent rows count as connected when they overlap by at least this
# much in x. Pure touching (overlap 0) is a corner, not a passage.
_OVERLAP_EPS_MM = 1e-6
# Travel that follows the edge is only worth it up to this much detour; past it
# the thread is better lifted and cut than dragged around the whole shape.
_TRAVEL_DETOUR_FACTOR = 4.0
_TRAVEL_DETOUR_FLOOR_MM = 20.0


def _ring_moments(coords) -> tuple[float, float, float, float, float, float]:
    """Signed area and raw second moments of one closed ring, exactly.

    -> (area, mx, my, ixx, iyy, ixy), all about the origin. The sign follows
    the ring's winding, so summing a shell with its holes subtracts them
    without anyone having to know which way shapely wound them.
    """
    a = np.asarray(coords, dtype=np.float64)
    if len(a) > 1 and a[0][0] == a[-1][0] and a[0][1] == a[-1][1]:
        a = a[:-1]
    if len(a) < 3:
        return (0.0,) * 6
    x0, y0 = a[:, 0], a[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    cross = x0 * y1 - x1 * y0
    return (
        float(cross.sum()) / 2.0,
        float((cross * (x0 + x1)).sum()) / 6.0,
        float((cross * (y0 + y1)).sum()) / 6.0,
        float((cross * (y0 * y0 + y0 * y1 + y1 * y1)).sum()) / 12.0,
        float((cross * (x0 * x0 + x0 * x1 + x1 * x1)).sum()) / 12.0,
        float((cross * (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0)).sum()) / 24.0,
    )


def principal_angle_deg(poly: Polygon) -> float:
    """Angle of the shape's long axis, in degrees.

    Rows run ALONG this axis: long rows mean fewer turns, fewer row-end
    penetrations piling up on the edges, and a fill that follows the shape
    instead of cutting across it.

    Measured from the polygon's AREA, not from its vertices. A vertex cloud
    answers "where are the points dense", which is a question about how the
    boundary happens to be sampled — and stage 5 hands this function a
    pull-compensated polygon whose corners carry a buffer's arc of ~16
    vertices each. Weighted by vertex, four such corners outvote the shape:
    a plain 24 mm square measured that way returns -87.3 deg and sews its
    rows across the diagonal. By area it returns 0.
    """
    area, mx, my, ixx, iyy, ixy = _ring_moments(poly.exterior.coords)
    for ring in poly.interiors:
        r = _ring_moments(ring.coords)
        area, mx, my = area + r[0], mx + r[1], my + r[2]
        ixx, iyy, ixy = ixx + r[3], iyy + r[4], ixy + r[5]
    if abs(area) < 1e-12:
        return 45.0
    cx, cy = mx / area, my / area
    # Parallel-axis shift onto the centroid, where the principal axes live.
    sxx = iyy - area * cx * cx          # the spread in x is the moment about y
    syy = ixx - area * cy * cy
    sxy = ixy - area * cx * cy
    if area < 0:
        # A clockwise ring measures every moment negative, which swaps which
        # axis looks longer and turns the answer a quarter turn. Shapely does
        # not promise a winding — `buffer` returns the opposite of what these
        # literals use — so normalise rather than trusting one.
        sxx, syy, sxy = -sxx, -syy, -sxy
    # A square and a disc have no long axis: their two principal moments are
    # equal, so the angle is whatever the arithmetic noise says, and a buffered
    # square swings 50 deg between join styles. Rows on such a shape have to
    # run SOMEWHERE, and level is the answer that does not look like a mistake.
    spread = math.hypot(sxx - syy, 2 * sxy)
    if spread <= 1e-3 * abs(sxx + syy):
        return 0.0
    return math.degrees(0.5 * math.atan2(2 * sxy, sxx - syy))


def _row_spans(poly: Polygon, row_mm: float) -> list[tuple[int, float, list[tuple[float, float]]]]:
    """Horizontal scanlines through an already-rotated polygon.

    -> [(row_index, y, [(x0, x1), ...]), ...], rows top to bottom, spans left to
    right. The first row sits half a spacing inside the top edge so a scanline
    never runs exactly along a horizontal boundary, where the intersection
    degenerates to a point or a whole edge depending on float noise.

    The row index is the SPATIAL one, counted from the top of the shape, and a
    scanline that finds nothing is left out of the list without consuming an
    index. That keeps the stagger anchored to real geometry and lets callers
    tell "the next row" from "the next row that had anything in it".
    """
    # Stage 5's pull compensation can hand fill a SELF-INTERSECTING polygon even
    # though stage 4 validated every region it emitted (`stage4_vectorize.py:181`
    # runs `make_valid`). `photo_sunset_backlit.png` at the DEFAULT 80 mm arrives
    # here as Self-intersection[30.946, 22.677] and GEOS raises TopologyException
    # out of the `intersection` below, failing the entire digitize -- at 80 mm
    # only, and on no other committed fixture, so nothing caught it. The same
    # defensive repair `stage6_border` (:249) and `stage6_contour` (:109) already
    # make. It fires ONLY on geometry that is already invalid, so a valid polygon
    # -- every other shape in the corpus -- takes the identical path it always
    # did and no golden moves.
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return []
    minx, miny, maxx, maxy = poly.bounds
    out: list[tuple[int, float, list[tuple[float, float]]]] = []
    n_rows = max(1, int(math.floor((maxy - miny) / row_mm)))
    for i in range(n_rows + 1):
        y = miny + row_mm * (i + 0.5)
        if y > maxy:
            break
        line = LineString([(minx - 1.0, y), (maxx + 1.0, y)])
        inter = poly.intersection(line)
        if inter.is_empty:
            continue
        parts = getattr(inter, "geoms", [inter])
        spans = []
        for g in parts:
            if g.geom_type != "LineString" or g.length <= 0:
                continue
            xs = [c[0] for c in g.coords]
            spans.append((min(xs), max(xs)))
        if spans:
            spans.sort()
            out.append((i, y, spans))
    return out


def _columns(rows: list[tuple[int, float, list[tuple[float, float]]]]) -> list[list[tuple[int, float, float, float]]]:
    """Cut the rows into monotone columns.

    A column continues from one row to the next only when the correspondence is
    one-to-one: this span overlaps exactly one span below it, and that span
    overlaps exactly one span above it. Forks and merges end the columns
    involved and start fresh ones, which is what keeps boustrophedon honest.

    -> list of columns; each column is [(row_index, y, x0, x1), ...] top-down.
    """
    columns: list[list[tuple[int, float, float, float]]] = []
    # span key (row_index, span_index) -> index of the column it belongs to
    open_cols: dict[int, int] = {}

    def overlaps(a: tuple[float, float], b: tuple[float, float]) -> bool:
        return min(a[1], b[1]) - max(a[0], b[0]) > _OVERLAP_EPS_MM

    prev_spans: list[tuple[float, float]] = []
    prev_row_idx = -2
    for ri, y, spans in rows:
        # A column may only continue into the row physically next to it. If a
        # scanline came up empty, the rows either side are a millimetre apart
        # and joining them would sew a line through whatever lies between.
        contiguous = ri == prev_row_idx + 1
        new_open: dict[int, int] = {}
        for si, sp in enumerate(spans):
            parent = None
            if contiguous:
                hits = [pi for pi, psp in enumerate(prev_spans) if overlaps(sp, psp)]
                if len(hits) == 1:
                    pi = hits[0]
                    # one-to-one only: the row above must not fan into two here
                    fan = sum(1 for s2 in spans if overlaps(s2, prev_spans[pi]))
                    if fan == 1 and pi in open_cols:
                        parent = open_cols[pi]
            if parent is None:
                columns.append([])
                parent = len(columns) - 1
            columns[parent].append((ri, y, sp[0], sp[1]))
            new_open[si] = parent
        open_cols = new_open
        prev_spans = spans
        prev_row_idx = ri
    return [c for c in columns if c]


# Candidate row directions swept by best_fill_angle_deg, evenly spaced across
# the meaningful [0, 180) range (row direction is a LINE, not a vector — a
# 30deg row and a 210deg row are the same rows).
_FILL_ANGLE_CANDIDATES = 16


def best_fill_angle_deg(poly: Polygon, row_mm: float) -> float:
    """The auto (no explicit override) fill angle: whichever of 16 evenly
    spaced candidate row directions, PLUS `principal_angle_deg`'s own
    answer, cuts the shape into the fewest monotone columns (`_columns`) at
    the row spacing this fill will actually run at.

    Fewer columns means fewer forced end-of-column travel decisions —
    `_fill_paths` already reasons about this at the travel-planning level
    ("Travel between columns... the classic auto-digitizer tell"); this
    picks the row direction that gives travel-planning the least to do in
    the first place. Same "enumerate candidate angles, minimise fragment
    count" method the expired Goldman/SoftSight auto-digitizing patents
    disclose (docs/masters-teardown-2026-08-01.md, gap G3).

    `principal_angle_deg` alone already gets this right for anything with a
    real long axis. It's *right where it says it's arbitrary* — a shape
    with no dominant axis by area, which its own docstring notes falls
    back to a flat 0deg — that column count can still swing hard with
    angle: a diagonal staircase of overlapping squares measures a 45deg
    principal axis (correctly, that IS the long axis by area) but sews that
    axis as 13 columns, while a candidate near-perpendicular to the stair
    direction sews it as 1. Including `principal_angle_deg`'s own answer as
    one of the candidates means this function can never do WORSE than
    today's behaviour, only tie or improve on it — a shape where the plain
    PCA angle was already optimal keeps generating byte-identical output.

    Ties (equal column count) prefer whichever candidate sits closest to
    the plain PCA angle, then the smallest angle — deterministic, and keeps
    a shape with one clear right answer from wobbling between
    equally-good-on-paper candidates for arbitrary float-noise reasons.
    """
    pca = principal_angle_deg(poly)
    candidates = [i * (180.0 / _FILL_ANGLE_CANDIDATES) for i in range(_FILL_ANGLE_CANDIDATES)]
    candidates.append(pca)

    def angular_dist(a: float, b: float) -> float:
        d = abs(a - b) % 180.0
        return min(d, 180.0 - d)

    best_angle = pca
    best_key = None
    for angle in candidates:
        rotated = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
        cols = len(_columns(_row_spans(rotated, row_mm)))
        if cols == 0:
            continue
        key = (cols, angular_dist(angle, pca), angle)
        if best_key is None or key < best_key:
            best_key = key
            best_angle = angle
    return best_angle


@lru_cache(maxsize=16)
def _stagger_slots(n: int) -> tuple[int, ...]:
    """Which offset slot each row in a stagger cycle uses.

    The obvious answer — row `i` takes slot `i` — is what a naive tatami does,
    and it is wrong for a reason that only shows on fabric. Walking the offset
    one notch per row moves every penetration a constant step sideways as the
    rows step down, so the holes line up along a diagonal and light runs down
    it: the channel is still there, just tilted. Reversing the bits of the row
    index (a van der Corput ordering) makes consecutive rows jump about half
    the pattern instead of one notch, so no three rows in a row share a slope.
    Rows still realign every `n` rows, which is what the density depends on.

    n = 4 gives slots (0, 2, 1, 3).
    """
    n = max(1, n)
    if n == 1:
        return (0,)
    bits = max(1, (n - 1).bit_length())
    rev = [int(format(i, f"0{bits}b")[::-1], 2) for i in range(n)]
    slots = [0] * n
    for slot, row in enumerate(sorted(range(n), key=lambda i: (rev[i], i))):
        slots[row] = slot
    return tuple(slots)


def _stagger_phase(row_index: int, staggers: int, stitch_mm: float) -> float:
    n = max(1, staggers)
    return _stagger_slots(n)[row_index % n] / n * stitch_mm


def _row_points_at_phase(x0: float, x1: float, y: float, phase: float,
                         stitch_mm: float, reverse: bool) -> list[tuple[float, float]]:
    """Penetrations across one row at an EXPLICIT stagger phase — the interior-
    grid geometry `_row_points` (phase from `_stagger_phase`'s van der Corput
    ordering) and `_brick_row_points` (phase a plain period-2 running-bond
    alternation) both build on, factored out once so every technique's row
    shares the same boundary handling instead of two near-identical copies of
    it drifting apart.

    Both row ends land exactly on the boundary: that is what makes the edge
    crisp.

    An interior penetration is only kept when BOTH of its neighbours are a real
    stitch — `MIN_STITCH_MM` away, not merely longer than the tiny-stitch
    floor. The grid is anchored globally, so the first grid point inside a row
    lands an arbitrary fraction of a stitch past the edge; keeping it put two
    penetrations a few tenths of a millimetre apart, which is the needle
    landing beside the hole it just made. Skipping it can leave a step longer
    than `stitch_mm`, and `split_long_moves` in `emit` subdivides that back
    into legal stitches.
    """
    span = x1 - x0
    if span < machine.TINY_STITCH_MM:
        mid = (x0 + x1) / 2.0
        return [(mid, y)]
    xs = [x0]
    # Below two stitches' worth of room there is no interior penetration that
    # clears both edges; the row is the single stitch between them, which is
    # what keeps a tapering tip's edge on the boundary.
    if span >= 2 * machine.MIN_STITCH_MM:
        x = math.ceil((x0 - phase) / stitch_mm) * stitch_mm + phase
        while x < x1:
            if x - xs[-1] >= machine.MIN_STITCH_MM and x1 - x >= machine.MIN_STITCH_MM:
                xs.append(x)
            x += stitch_mm
    xs.append(x1)
    pts = [(vx, y) for vx in xs]
    return list(reversed(pts)) if reverse else pts


def _row_points(x0: float, x1: float, y: float, row_index: int, stitch_mm: float,
                staggers: int, reverse: bool) -> list[tuple[float, float]]:
    """Penetrations across one row, staggered against its neighbours.

    Interior stitches sit on a global grid shifted by the row's stagger phase
    (`_stagger_phase`'s van der Corput ordering), so rows only realign every
    `staggers` rows. See `_row_points_at_phase` for the shared interior-grid
    geometry every row-point function in this module — tatami's own included
    — builds on.
    """
    return _row_points_at_phase(x0, x1, y, _stagger_phase(row_index, staggers, stitch_mm),
                                stitch_mm, reverse)


def _wave_row_points(x0: float, x1: float, y: float, row_index: int, stitch_mm: float,
                     staggers: int, reverse: bool) -> list[tuple[float, float]]:
    """`_row_points`, with every INTERIOR point's y perturbed by a subtle sine
    wave perpendicular to the row — the "wave" fill technique
    (`machine.WAVE_AMPLITUDE_MM`, `machine.WAVE_LENGTH_MM`).

    Built ON `_row_points`, not a parallel reimplementation: the interior x
    positions (and their own stagger phase) are exactly what plain tatami
    would place; only y moves, and only for interior points. The two row
    ends are left completely alone — same edge-crispness contract
    `_row_points_at_phase`'s own docstring states, and what keeps a wavy
    fill's silhouette identical to a straight one's.

    Phase rule: 0 on even rows, pi on odd rows — the simplest deterministic
    rule that puts adjacent rows' waves in OPPOSITE motion at any given x
    (sin(theta) and sin(theta+pi) are negatives of each other everywhere),
    which is what stops the wave from stacking into a corrugated-cardboard
    ridge the way an in-phase wave repeated down every row would. It does
    not need to be cleverer than that: unlike the anti-moire stagger
    (`_stagger_phase`), which has to avoid a periodic pattern across many
    rows, a 2-row alternation is already enough to break a *continuous* wave's
    only failure mode (two neighbours moving the same way at the same x).
    """
    pts = _row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse)
    if len(pts) < 3:
        # A single-point tip, or a row with no interior penetration at all —
        # nothing to perturb, and pts[0]/pts[-1] would otherwise be the same
        # point counted twice.
        return pts
    phase = 0.0 if row_index % 2 == 0 else math.pi
    out = [pts[0]]
    for x, py in pts[1:-1]:
        out.append((x, py + machine.WAVE_AMPLITUDE_MM *
                    math.sin(2.0 * math.pi * x / machine.WAVE_LENGTH_MM + phase)))
    out.append(pts[-1])
    return out


def _chevron_row_points(x0: float, x1: float, y: float, row_index: int, stitch_mm: float,
                        staggers: int, reverse: bool) -> list[tuple[float, float]]:
    """`_row_points`, with every INTERIOR point's y alternating
    +-`machine.CHEVRON_AMPLITUDE_MM` — the "chevron" fill technique's
    simplified, textural herringbone impression at one fill angle (a full
    multi-angle banded herringbone would need new column/travel logic; see
    `machine.py`'s chevron section).

    Same "built on `_row_points`, only interior y moves" contract as
    `_wave_row_points` — reuses tatami's own interior x grid (stagger
    included) unchanged, and leaves both row ends on the boundary.

    Period: the sign flips every single interior stitch (period two
    stitches), starting +amplitude on the first interior point. No row-to-
    row phase rule is needed the way wave's is: the interior grid a row's
    alternation walks is already `_row_points`' own staggered one, so which
    x each row's peaks and valleys land on already varies row to row — the
    same anti-channelling effect the stagger exists for in the first place,
    inherited for free rather than re-derived.
    """
    pts = _row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse)
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i, (x, py) in enumerate(pts[1:-1]):
        sign = 1.0 if i % 2 == 0 else -1.0
        out.append((x, py + sign * machine.CHEVRON_AMPLITUDE_MM))
    out.append(pts[-1])
    return out


def _brick_row_points(x0: float, x1: float, y: float, row_index: int, stitch_mm: float,
                      staggers: int, reverse: bool) -> list[tuple[float, float]]:
    """`_row_points`, with its van der Corput anti-moire stagger
    (`_stagger_phase`) replaced by a strict, visually obvious 2-phase
    "running bond" stagger — the "brick" fill technique: even rows' interior
    grid starts at phase 0, odd rows at phase `stitch_mm / 2`.

    `staggers` is accepted, unused, purely to keep every row-point function
    in this module to the identical call signature `_fill_paths` dispatches
    on. No new `machine.py` constant: the phase IS `stitch_mm / 2`, already
    a known quantity, so there is nothing to tune.

    Shares `_row_points_at_phase` — the boundary handling, MIN_STITCH_MM
    clearance floor and TINY_STITCH_MM tip case — with `_row_points` itself,
    so tatami's own (van der Corput) stagger behaviour is completely
    untouched by this technique existing.
    """
    phase = 0.0 if row_index % 2 == 0 else stitch_mm / 2.0
    return _row_points_at_phase(x0, x1, y, phase, stitch_mm, reverse)


def _densify(a: tuple[float, float], b: tuple[float, float], step_mm: float) -> list[tuple[float, float]]:
    """Points from a (exclusive) to b (inclusive), no step longer than step_mm."""
    d = math.dist(a, b)
    if d <= step_mm:
        return [b]
    n = math.ceil(d / step_mm)
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(1, n + 1)]


def _inset_ring(poly: Polygon, inset_mm: float) -> list[LineString]:
    """Closed paths just inside the shape, for travel to follow — ONE PER
    FRAGMENT the inset leaves behind.

    A shape narrower than 2 * inset anywhere pinches apart here, and that is
    the common case, not the exotic one: an outlined wordmark is a single
    connected region joined by keylines a millimetre wide, so the inset
    shatters it into one piece per letter. becker_hat_small's largest region
    breaks into 59.

    This used to `max(inner.geoms, key=area)` and discard the rest, which left
    72% of that region with no travel guide at all — every fill path landing
    there had to be reached by lifting the needle, and past `trim_at_mm` that
    is a thread cut. 17 of the design's 32 cuts were this one discard.
    """
    inner = poly.buffer(-inset_mm)
    if inner.is_empty:
        inner = poly
    parts = list(inner.geoms) if inner.geom_type == "MultiPolygon" else [inner]
    return [LineString(g.exterior.coords) for g in parts
            if not g.is_empty and g.geom_type == "Polygon"]


# How many candidate rings a single travel query will pay a containment test
# for. Ranked nearest-first, so the ring actually holding both ends is the
# first or second try in every case measured on the corpus; the cap is what
# keeps a 59-fragment region from turning one travel into 59 `covers()` calls,
# which is the most expensive thing stage 6 does.
_TRAVEL_RING_CANDIDATES = 3


def _ring_route(ring: LineString, a: tuple[float, float],
                b: tuple[float, float]) -> list[tuple[float, float]]:
    """The shorter way around `ring` from a to b, as waypoints.

    The ring's OWN VERTICES, not samples taken at a fixed arc-length step.
    Sampling a corner at 2.5 mm intervals puts one waypoint on each side of it
    and the straight chord between them cuts it off — which at a concave corner
    means the route leaves the shape. That is how travel escaped into the notch
    of a U before the containment check caught it; routing vertex to vertex
    cannot cut a corner because every corner IS a waypoint. Spacing is applied
    afterwards by `_densify`, which only ever subdivides.
    """
    coords = list(ring.coords)
    total = ring.length
    cum = [0.0]
    for i in range(1, len(coords)):
        cum.append(cum[-1] + math.dist(coords[i - 1], coords[i]))
    ta, tb = ring.project(Point(a)), ring.project(Point(b))
    forward = (tb - ta) % total
    backward = total - forward
    ahead = forward <= backward
    span = forward if ahead else backward

    between: list[tuple[float, tuple[float, float]]] = []
    for i in range(1, len(coords)):
        offset = (cum[i] - ta) % total if ahead else (ta - cum[i]) % total
        if 0.0 < offset < span:
            between.append((offset, coords[i]))
    between.sort()

    start, end = ring.interpolate(ta), ring.interpolate(tb)
    route = [(start.x, start.y)] + [c for _, c in between] + [(end.x, end.y)]

    # A ring is a BUFFER's output, so its vertices are as dense as the buffer's
    # arc resolution — tenths of a millimetre around every corner. Keeping all
    # of them puts a penetration on each, and `_densify` only ever subdivides,
    # so nothing downstream thins them again: becker_hat_small landed 2464
    # travel stitches over 551 mm of path, 0.22 mm apart, a third of the whole
    # design. Fixed-step sampling capped that as a side effect; preserving
    # vertices removed the cap, so the floor is applied here deliberately.
    #
    # TINY_STITCH_MM and not something larger because the point of keeping
    # vertices is corners, and a corner dropped is a corner cut. At 0.5 mm
    # against a 0.6 mm inset the furthest a dropped vertex can move the path is
    # a quarter millimetre, and `travel_path` re-checks containment regardless.
    out = [route[0]]
    for p in route[1:-1]:
        if math.dist(out[-1], p) >= machine.TINY_STITCH_MM:
            out.append(p)
    out.append(route[-1])
    return out


def travel_path(poly: Polygon, ring, a: tuple[float, float],
                b: tuple[float, float], slack: Polygon | None = None
                ) -> list[tuple[float, float]] | None:
    """Stitchable route from a to b that never leaves the shape.

    Straight if it can be, along the edge if it must be, None when the thread
    genuinely has to be lifted. The straight test is run against a hair-widened
    copy of the polygon so a route hugging the boundary is not rejected for
    float noise, while a route across a hole (never narrower than the minimum
    detail size) still is. Pass that widened copy in as `slack` when calling
    repeatedly for one shape — buffering is the most expensive thing in stage 6
    and the result is the same every time.

    `ring` is `_inset_ring`'s list of per-fragment guides (a bare LineString or
    None is still accepted — stage6_border passes None, and the guide for a
    shape that does not pinch is a one-element list). Candidates are tried
    nearest-first, and a route is only returned once it has been checked to
    stay inside the shape. That check is new with the multi-fragment guides and
    is not bookkeeping: handed a guide on the far side of a closed neck, the
    old single-ring code would run along it and then strike out across bare
    cloth to reach `b`, emitting travel that left the shape entirely.
    """
    if math.dist(a, b) < machine.TINY_STITCH_MM:
        return []
    cover = slack if slack is not None else poly.buffer(0.01)
    seg = LineString([a, b])
    if cover.covers(seg):
        return _densify(a, b, machine.TRAVEL_STITCH_MM)
    if ring is None:
        return None
    rings = [ring] if isinstance(ring, LineString) else list(ring)
    if not rings:
        return None

    step = machine.TRAVEL_STITCH_MM
    budget = max(_TRAVEL_DETOUR_FLOOR_MM, math.dist(a, b) * _TRAVEL_DETOUR_FACTOR)
    pa, pb = Point(a), Point(b)
    rings.sort(key=lambda r: max(r.distance(pa), r.distance(pb)))

    for candidate in rings[:_TRAVEL_RING_CANDIDATES]:
        pts = _ring_route(candidate, a, b)
        route = [a] + pts + [b]
        length = sum(math.dist(route[i - 1], route[i]) for i in range(1, len(route)))
        if length > budget:
            continue
        if not cover.covers(LineString(route)):
            continue
        out: list[tuple[float, float]] = []
        cur = a
        for p in pts + [b]:
            out.extend(_densify(cur, p, step))
            cur = p
        return out
    return None


# How many nearest candidates the routable-first walk probes before it accepts
# that nothing reachable is left and takes the cut. Measured on
# `logo_hotel_fremont.webp`'s 46-hole white field (the worst shape in the
# corpus, 280 fill runs): no candidate past the 40th ever changed the chosen
# next run. It is a work cap, not a quality knob — raising it cannot make the
# result worse, only slower.
_ROUTABLE_PROBE_LIMIT = 40


def _count_cuts(paths: list[list[tuple[float, float]]], poly: Polygon, ring,
                slack: Polygon, entry: tuple[float, float] | None,
                trim_at_mm: float) -> int:
    """How many thread cuts this path ORDER costs, by `fill_region`'s own rule.

    `emit` cuts exactly when `travel_path` finds no route AND the gap exceeds
    `trim_at_mm` (see its `bridge is None` branch). Scoring here with the same
    rule — rather than a distance proxy — is what makes the comparison in
    `_reorder_for_fewer_cuts` honest: a proxy measured against the real count
    is how three earlier attempts at this defect reached wrong conclusions.
    """
    cuts = 0
    cur = entry
    for path in paths:
        if not path:
            continue
        if cur is not None:
            if (travel_path(poly, ring, cur, path[0], slack) is None
                    and math.dist(cur, path[0]) > trim_at_mm):
                cuts += 1
        cur = path[-1]
    return cuts


def _reorder_for_fewer_cuts(paths: list[list[tuple[float, float]]], poly: Polygon,
                            ring, slack: Polygon, entry: tuple[float, float] | None,
                            trim_at_mm: float) -> list[list[tuple[float, float]]]:
    """Prefer a REACHABLE next path over merely the nearest one, if it cuts less.

    `_fill_paths` orders columns by straight-line distance. On a shape with
    holes the nearest column is often across one, where `travel_path` cannot
    route, so `emit` cuts — while a slightly farther column in the same
    travel-connected island would have cost no cut at all. The cut is
    manufactured by the choice, not forced by the geometry.

    Measured on `logo_hotel_fremont.webp`'s 46-hole field: 57 cuts -> 24, a 58%
    reduction for +752 mm of travel (+2.9% stitches). Across the committed photo
    corpus, 17 holed shapes went 290 -> 163 cuts. **But four of those seventeen
    got WORSE** — on shapes whose boundaries are naturally sub-`trim_at_mm`, the
    distance-greedy walk keeps hops short enough that a failed travel becomes a
    silent jump rather than a cut, and chasing reachability instead lands
    somewhere both far and unroutable. So this does NOT replace the ordering: it
    scores both and keeps the better, and ties keep the incoming one. A shape
    can only improve or stay identical.

    Skipped entirely when the incoming order already cuts nothing, which is the
    common case and keeps this free for every shape that never needed it.
    """
    if len(paths) < 3:
        return paths
    before = _count_cuts(paths, poly, ring, slack, entry, trim_at_mm)
    if before == 0:
        return paths                     # nothing to win; do not pay for the walk

    ends = [(p[0], p[-1]) for p in paths if p]
    if len(ends) != len(paths):
        return paths                     # an empty path: leave this shape alone
    remaining = set(range(len(paths)))
    order: list[int] = []
    flipped: set[int] = set()
    cur = entry
    while remaining:
        cand = sorted(remaining, key=lambda j: (
            min(math.dist(cur, ends[j][0]), math.dist(cur, ends[j][1]))
            if cur is not None else 0.0))[:_ROUTABLE_PROBE_LIMIT]
        picked = None
        if cur is not None:
            for j in cand:
                for flip in (False, True):
                    head = ends[j][1] if flip else ends[j][0]
                    if travel_path(poly, ring, cur, head, slack) is not None:
                        picked = (j, flip)
                        break
                if picked:
                    break
        if picked is None:               # nothing reachable -> take the nearest
            j = cand[0]
            flip = (cur is not None
                    and math.dist(cur, ends[j][1]) < math.dist(cur, ends[j][0]))
            picked = (j, flip)
        j, flip = picked
        order.append(j)
        if flip:
            flipped.add(j)
        cur = ends[j][0] if flip else ends[j][1]
        remaining.discard(j)

    # Reversing a path sews the same penetrations in the other direction — the
    # holes land in identical places, so this changes travel, never stitch
    # placement.
    candidate = [paths[j][::-1] if j in flipped else paths[j] for j in order]
    after = _count_cuts(candidate, poly, ring, slack, entry, trim_at_mm)
    return candidate if after < before else paths


# Which row-point function each fill `technique` dispatches to inside
# `_fill_paths` — every entry shares `_row_points`' exact call signature
# `(x0, x1, y, row_index, stitch_mm, staggers, reverse)`, so `_fill_paths`
# itself needs no per-technique branching beyond this one lookup, and its
# column-walking, ordering and travel-adjacent logic (everything below this
# point) is identical for every technique in the table. Anything not listed
# — "tatami" included — gets plain `_row_points`, so this table is what makes
# adding a technique here additive: a name nobody asks for changes nothing.
_ROW_POINT_FNS = {
    "wave": _wave_row_points,
    "chevron": _chevron_row_points,
    "brick": _brick_row_points,
}


def _fill_paths(poly: Polygon, angle_deg: float, row_mm: float, stitch_mm: float,
                staggers: int, start_near: tuple[float, float] | None = None,
                technique: str = "tatami",
                ) -> list[list[tuple[float, float]]]:
    """Fill one polygon; -> continuous stitch paths in original (unrotated) mm space.

    Columns are visited nearest-first from the end of the previous one, and each
    is entered from whichever of its two ends is closer, so ordering never
    invents a long haul it could have avoided.

    `start_near` is where the needle already is. Without it the first column is
    picked by geometry alone — topmost, then leftmost — so every shape began at
    its own top-left corner however far that was from the last stitch of the
    shape before it.

    `technique` picks which function places each row's own penetrations —
    see `_ROW_POINT_FNS`. "tatami" (the default, and every caller before
    "wave"/"chevron"/"brick" existed) keeps `_row_points`, byte-identical.
    Everything else about this function — the column walk, both-ends-of-
    every-column traversal, nearest-neighbour ordering, the rotate out at
    the end — is exactly the same regardless of `technique`: unlike
    "crosshatch" (`_crosshatch_fill_paths`, a second whole pass at a wider
    spacing), these three techniques only change how ONE row's own interior
    points are placed, so they need no travel-planning logic of their own
    and share this function outright instead of wrapping it.
    """
    row_point_fn = _ROW_POINT_FNS.get(technique, _row_points)
    rotated = affinity.rotate(poly, -angle_deg, origin=(0, 0), use_radians=False)
    rows = _row_spans(rotated, row_mm)
    if not rows:
        return []
    cols = _columns(rows)
    if not cols:
        return []

    def col_points(col, from_bottom: bool) -> list[tuple[float, float]]:
        seq = list(reversed(col)) if from_bottom else col
        pts: list[tuple[float, float]] = []
        for k, (ri, y, x0, x1) in enumerate(seq):
            # Scan direction alternates per emitted row so consecutive rows meet
            # end to end; the absolute row index still drives the stagger phase.
            pts.extend(row_point_fn(x0, x1, y, ri, stitch_mm, staggers, reverse=k % 2 == 1))
        return pts

    # Both traversals of every column, generated once: the ordering loop below
    # inspects each candidate repeatedly, and regenerating them there turns a
    # linear amount of work into a quadratic amount on shapes with many columns.
    variants = [(col_points(c, False), col_points(c, True)) for c in cols]

    # Deterministic start: nearest to the needle if it is already somewhere,
    # otherwise the column that begins highest, then leftmost.
    remaining = [i for i in range(len(cols)) if variants[i][0]]
    remaining.sort(key=lambda i: (cols[i][0][0], cols[i][0][2]))
    order: list[list[tuple[float, float]]] = []
    cur: tuple[float, float] | None = None
    if start_near is not None:
        # The columns live in the rotated frame, so the entry point has to.
        sp = affinity.rotate(Point(start_near), -angle_deg, origin=(0, 0),
                             use_radians=False)
        cur = (sp.x, sp.y)
    while remaining:
        if cur is None:
            pick, flip = remaining[0], 0
        else:
            best = None
            for i in remaining:
                for fb in (0, 1):
                    key = (round(math.dist(cur, variants[i][fb][0]), 6), i, fb)
                    if best is None or key < best[0]:
                        best = (key, i, fb)
            pick, flip = best[1], best[2]
        pts = variants[pick][flip]
        remaining.remove(pick)
        order.append(pts)
        cur = pts[-1]

    back = []
    for path in order:
        rp = affinity.rotate(LineString(path) if len(path) > 1 else Point(path[0]),
                             angle_deg, origin=(0, 0), use_radians=False)
        back.append([(x, y) for x, y in (rp.coords if len(path) > 1 else [(rp.x, rp.y)])])
    return back


def _crosshatch_fill_paths(poly: Polygon, angle_deg: float, row_mm: float, stitch_mm: float,
                           staggers: int, start_near: tuple[float, float] | None = None
                           ) -> list[list[tuple[float, float]]]:
    """Two overlapping tatami passes on the same shape -> concatenated paths
    in original (unrotated) mm space, one pass at `angle_deg`, one at
    `angle_deg + 90`.

    Exactly the trick `_underlay_paths`'s `double_lattice` style already uses
    for its own +-45deg underlay passes (`lattice()` below, called twice),
    aimed at the visible fill instead of underlay. Each pass runs at
    `row_mm * machine.CROSSHATCH_ROW_SCALE_FACTOR` — wider than a normal
    single-pass fill, so the two passes TOGETHER land near a single pass's
    stitch density instead of roughly doubling it.

    The second pass starts from the first pass's own last point (the same
    handoff `stitch_shape` uses between its underlay and fill), so the two
    passes chain through whatever caller feeds this concatenated list to —
    ordinarily `stitch_shape`'s `emit()` — the same generic multi-path travel
    bridging every other list of paths already gets. No travel-planning logic
    of its own.
    """
    wide_row_mm = row_mm * machine.CROSSHATCH_ROW_SCALE_FACTOR
    first_pass = _fill_paths(poly, angle_deg, wide_row_mm, stitch_mm, staggers, start_near)
    entry = first_pass[-1][-1] if first_pass else start_near
    second_pass = _fill_paths(poly, angle_deg + 90.0, wide_row_mm, stitch_mm, staggers, entry)
    return first_pass + second_pass


def is_solid_fill(poly: Polygon) -> bool:
    """Whether `poly` has a real solid body wide enough for the density
    boost's second pass (`machine.FILL_DENSITY_BOOST_MIN_WIDTH_MM`), rather
    than being a thin strip or a fine lattice arm that would only gain
    pucker risk from a second full-density pass, not coverage.

    Same erosion test `stitch_shape`'s own `too_thin` report already runs
    (`poly.buffer(-half_width).is_empty`), at the density boost's own,
    wider threshold — MIN_FILL_WIDTH_MM asks "can this hold a fill row at
    all", this asks the harder "is this a field, not a stroke".
    """
    return not poly.buffer(-machine.FILL_DENSITY_BOOST_MIN_WIDTH_MM / 2.0).is_empty


def _density_fill_paths(poly: Polygon, angle_deg: float, row_mm: float, stitch_mm: float,
                        staggers: int, start_near: tuple[float, float] | None = None,
                        ) -> list[list[tuple[float, float]]]:
    """The density-targeted default for a SOLID fill shape: two overlapping
    tatami passes at the shape's own `row_mm` (unwidened) -- the "cross pass
    + top pass" professional solid elements measure
    (`machine.FILL_DENSITY_BOOST_MIN_WIDTH_MM`'s own comment).

    Structurally identical to `_crosshatch_fill_paths` (angle, then
    angle+90, concatenated, second pass entering from the first pass's own
    exit point) MINUS that technique's `CROSSHATCH_ROW_SCALE_FACTOR`
    widening: crosshatch widens each pass so the combined density stays near
    ONE ordinary pass (an opt-in texture, not a density change); here two
    full-density passes landing at roughly double density *is* the point,
    so nothing widens.
    """
    first_pass = _fill_paths(poly, angle_deg, row_mm, stitch_mm, staggers, start_near)
    entry = first_pass[-1][-1] if first_pass else start_near
    second_pass = _fill_paths(poly, angle_deg + 90.0, row_mm, stitch_mm, staggers, entry)
    return first_pass + second_pass


def _underlay_paths(poly: Polygon, style: str, angle_deg: float,
                    start_near: tuple[float, float] | None = None
                    ) -> list[list[tuple[float, float]]]:
    """Underlay runs for one shape, in the named style.

    Underlay lives inside the finished edge — its whole job is to hold the
    fabric still and give the top stitching something to sit on, and any of it
    that peeks past the edge is a defect.

    `start_near` is where the needle already is. A closed edge walk may begin
    anywhere on its ring, so it begins at the point nearest the needle.
    """
    if style == "none":
        return []
    inner = poly.buffer(-machine.UNDERLAY_INSET_MM)
    if inner.is_empty:
        return []
    if inner.geom_type == "MultiPolygon":
        inner = max(inner.geoms, key=lambda g: g.area)
    if inner.geom_type != "Polygon":
        return []

    def edge_run() -> list[list[tuple[float, float]]]:
        out = []
        for ring in [inner.exterior, *inner.interiors]:
            line = LineString(ring.coords)
            total = line.length
            n = max(2, math.ceil(total / machine.UNDERLAY_STITCH_MM))
            s0 = line.project(Point(start_near)) if (start_near is not None and total > 0) else 0.0
            pts = [line.interpolate((s0 + total * i / n) % total) for i in range(n)]
            pts.append(line.interpolate(s0))
            out.append([(p.x, p.y) for p in pts])
        return out

    def lattice(offset_deg: float, row_mm: float) -> list[list[tuple[float, float]]]:
        return _fill_paths(inner, angle_deg + offset_deg, row_mm,
                           machine.UNDERLAY_STITCH_MM, staggers=1,
                           start_near=start_near)

    def center_run() -> list[list[tuple[float, float]]]:
        c = inner.centroid
        ang = math.radians(principal_angle_deg(inner))
        minx, miny, maxx, maxy = inner.bounds
        ext = math.hypot(maxx - minx, maxy - miny)
        line = LineString([(c.x - math.cos(ang) * ext, c.y - math.sin(ang) * ext),
                           (c.x + math.cos(ang) * ext, c.y + math.sin(ang) * ext)])
        inter = inner.intersection(line)
        if inter.is_empty:
            return []
        parts = [g for g in getattr(inter, "geoms", [inter]) if g.geom_type == "LineString"]
        if not parts:
            return []
        best = max(parts, key=lambda g: g.length)
        n = max(1, math.ceil(best.length / machine.UNDERLAY_STITCH_MM))
        pts = [best.interpolate(best.length * i / n) for i in range(n + 1)]
        return [[(p.x, p.y) for p in pts]]

    if style == "edge_run":
        return edge_run()
    if style == "center_run":
        return center_run()
    if style == "zigzag":
        return lattice(90, machine.UNDERLAY_ZIGZAG_MM)
    if style == "edge_zigzag":
        return edge_run() + lattice(90, machine.UNDERLAY_ZIGZAG_MM)
    if style == "double_lattice":
        return (edge_run() + lattice(45, machine.UNDERLAY_LATTICE_MM)
                + lattice(-45, machine.UNDERLAY_LATTICE_MM))
    # edge_lattice and anything unrecognised
    return edge_run() + lattice(90, machine.UNDERLAY_LATTICE_MM)


def stitch_shape(poly: Polygon, shape_id: str, *, angle_deg: float | None,
                 row_mm: float, stitch_mm: float, underlay_style: str,
                 trim_at_mm: float,
                 start_near: tuple[float, float] | None = None,
                 technique: str = "tatami",
                 density_boost: bool = False,
                 ) -> tuple[list[StitchRun], dict]:
    """One shape -> its runs, in sew order (underlay first), plus a small report.

    `start_near` is where the needle is when this shape's turn comes; the
    underlay and the fill both begin at whichever of their own valid starting
    points is nearest it.

    `technique` picks the visible FILL pass only — underlay is unaffected
    either way. "tatami" (the default, and every existing caller with
    `density_boost` left at its own default False) keeps today's single
    `_fill_paths` call, byte-identical. "crosshatch" swaps it for
    `_crosshatch_fill_paths`: two angled tatami passes at a wider spacing
    each, concatenated — see that function's docstring. "wave", "chevron"
    and "brick" stay on the ordinary single `_fill_paths` call — they only
    change how one row's own interior points are placed
    (`_wave_row_points`/`_chevron_row_points`/`_brick_row_points`, dispatched
    inside `_fill_paths` itself via `_ROW_POINT_FNS`), so unlike crosshatch
    they need no second pass or dedicated wrapper function.

    `density_boost` (task A2, machine.FILL_DENSITY_BOOST_MIN_WIDTH_MM) only
    ever matters together with `technique == "tatami"`: when both hold AND
    the shape is solid (`is_solid_fill`), the fill pass swaps to
    `_density_fill_paths` — the same two-pass shape as crosshatch, at full
    row_mm on both passes instead of crosshatch's deliberately widened one,
    landing the combined density at the corpus-measured professional target
    instead of near a single ordinary pass. Defaults False (not "tatami"'s
    own default technique choice) so every caller that does not explicitly
    ask for it keeps exactly today's single-pass output — stage 7's plain-
    tatami fallback is the one caller that turns it on, gated by
    `PipelineConfig.fill_density_boost`.

    Report keys: `too_thin` (nowhere wide enough for a fill), `jumps` (travel
    that had to lift the needle), `empty` (produced nothing).
    """
    report = {"too_thin": False, "jumps": 0, "empty": False}
    angle = best_fill_angle_deg(poly, row_mm) if angle_deg is None else angle_deg
    if poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
        report["too_thin"] = True

    runs: list[StitchRun] = []
    ring = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)

    def emit(paths: list[list[tuple[float, float]]], kind: str, max_step: float) -> None:
        for path in paths:
            # No tiny-stitch filter here, deliberately. Row turns are exactly one
            # row spacing long — 0.4 mm at standard density — and dropping them
            # deletes the penetration that lands on the shape's edge, which is
            # what makes the edge crisp. Every step ALONG a row is already kept
            # above the floor by _row_points. Turns get split instead of dropped:
            # on a steeply sloped edge the step to the next row can run several
            # millimetres, and a fill has no business emitting a stitch longer
            # than its own stitch length.
            pts = stitches.split_long_moves(path, max_step)
            if len(pts) < 2:
                continue
            if runs:
                bridge = travel_path(poly, ring, runs[-1].points[-1], pts[0], slack)
                if bridge is None:
                    d = math.dist(runs[-1].points[-1], pts[0])
                    report["jumps"] += 1
                    runs.append(StitchRun(points=pts, kind=kind, jump=True,
                                          trim=d > trim_at_mm, shape_id=shape_id))
                    continue
                # The bridge starts where the last run ended and finishes where
                # the next one begins, so both ends belong to their own runs.
                # Repeating them here would emit zero-length stitch records and
                # inflate every count the operator is shown.
                middle = bridge[:-1]
                if middle:
                    runs.append(StitchRun(points=middle, kind=stitches.TRAVEL,
                                          shape_id=shape_id))
            runs.append(StitchRun(points=pts, kind=kind, shape_id=shape_id))

    emit(_underlay_paths(poly, underlay_style, angle, start_near),
         stitches.UNDERLAY, machine.UNDERLAY_STITCH_MM)
    # The fill picks up where the underlay put the needle down — otherwise it
    # starts at the shape's top-left corner and the first travel of the fill is
    # a haul back across everything the underlay just laid.
    entry = runs[-1].points[-1] if runs else start_near
    if technique == "crosshatch":
        fill_paths = _crosshatch_fill_paths(poly, angle, row_mm, stitch_mm,
                                            machine.FILL_STAGGERS, entry)
    elif technique == "tatami" and density_boost and is_solid_fill(poly):
        fill_paths = _density_fill_paths(poly, angle, row_mm, stitch_mm,
                                         machine.FILL_STAGGERS, entry)
    else:
        fill_paths = _fill_paths(poly, angle, row_mm, stitch_mm,
                                 machine.FILL_STAGGERS, entry, technique=technique)
    fill_paths = _reorder_for_fewer_cuts(fill_paths, poly, ring, slack, entry,
                                         trim_at_mm)
    emit(fill_paths, stitches.FILL, stitch_mm)

    if not runs:
        report["empty"] = True
    return runs, report


