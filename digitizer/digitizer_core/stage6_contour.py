"""Stage 6 contour fill — rings that follow the silhouette instead of crossing it.

Tatami lays straight rows at one angle. Where a shape's outline curves, those
rows meet it at a different angle every row, and the needle distribution goes
uneven exactly where the eye is drawn: rings, letterforms, anything whose width
varies along its length. Contour fill answers that by making the ROWS follow the
edge — uniform inward offsets of the outline, sewn inner-to-outer as one
continuous path.

Why offsets and not a spiral: an offset forest terminates on every shape. Necks,
holes, thin arms and five-way branches all resolve into a ring set with no
topological precondition, whereas every spiral variant needs the shape to admit
one. Spirals (Fermat, connected-Fermat) are a RE-LINKING of this same ring set,
so `_link` is the seam a strategy flag would cut at, not a rewrite deferred.

Four traps this module exists to get right, all of them MEASURED on real
geometry before they were coded (see `docs/fill-techniques-2026-08-01.md`,
laws 39-44). Each one had a working-looking first draft that the smoke run
caught:

- **Ring-to-ring transitions are stitches, not travel** (law 44). Adjacent rings
  sit one spacing apart — 0.40 mm — so the obvious perpendicular hop emits a
  stitch under `MIN_STITCH_MM` and inside the needle's own hole radius. Neither
  milling nor FDM has a minimum segment length, so no algorithm in the CAM
  literature guards this and every reference implementation hands you sub-floor
  stitches. `_entry_arc` does not search for a clear entry, it SOLVES for one:
  a ring `g` away needs a walk of `sqrt(need^2 - g^2)` along itself for the
  crossing chord to reach `need`. That also scatters the transitions into a
  gentle spiral, which kills the radial seam that is the loudest tell of machine
  contour fill.

- **A ring is cut into equal chords, and `ceil` puts them under the floor.**
  Rounding the chord count UP to respect a curvature cap makes the realized
  chord shorter than the cap — and the cap bottoms out at `MIN_STITCH_MM`, so
  every tight ring came out under it. Measured before the fix: a 6.0 mm ring
  resampled to 0.83 mm steps, a 3.0 mm ring to 0.68 mm. `_step_count` takes the
  needle floor as the hard constraint and the curvature cap as the soft one,
  which is the right way round — the floor is the machine, the cap is taste.

- **A chord lies on the concave side** (law 42). Sagitta is about L^2/8R, so a
  4 mm stitch on a 5 mm radius bows 0.4 mm past the arc with BOTH endpoints
  testing inside the shape. Tatami never had this problem because its rows are
  straight, so nothing downstream looks for it. Measured before the fix: a
  2.4 mm chord across a five-point star's inner notch sat 0.48 mm outside the
  star. A per-ring curvature estimate cannot catch that — one sharp notch on an
  otherwise round ring does not move the ring's average radius — so containment
  is enforced by CLIPPING THE EMITTED CHORD, not by predicting it.

- **A dropped ring is unfilled fabric.** When a ring is too short to sew, the
  honest move is to count it and warn. Silently dropping it — which is what the
  reference implementations do — leaves bare fabric that nothing downstream can
  see. And counting alone is not enough (2026-08-04): the mitred offset can
  ANNIHILATE a notched interior wholesale — a core that was never a ring and
  never reached the ledger — so the `starved` warning is decided by measuring
  the emitted stitches against the polygon (barecircle.py), not by trusting
  this module's own accounting of what it knows it dropped.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring

from . import machine, stitches
from .barecircle import starved_threshold_mm, widest_bare_circle
from .stage6_fill import _inset_ring, travel_path
from .stitches import StitchRun


# --- Ring construction -----------------------------------------------------

@dataclass(frozen=True)
class _Ring:
    """One closed offset curve, with what `_link` needs to order it."""

    line: LineString
    gen: int          # 0 is the outermost generation
    key: tuple        # deterministic tie-break: (gen, part, ring, rounded bounds)
    # Fabric left bare if this ring is dropped. An exterior ring owns everything
    # it encloses; a hole wall owns nothing, because the material around a hole
    # is covered by whichever rings on either side of it do get sewn.
    area: float


def _polygons(geom) -> list[Polygon]:
    """Polygonal parts of a boolean result, largest first. Never drops a part."""
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    out = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    return sorted(out, key=lambda g: (-g.area, g.bounds))


def _offset(poly: Polygon, d: float) -> list[Polygon]:
    """`poly` inset by `d`, as valid polygons.

    Mitre limit 2.0, not the 10 the reference implementations use: a high limit
    lets a sharp corner throw a long spike, and the needle has to chase every
    millimetre of it.
    """
    try:
        g = poly.buffer(-d, join_style=2, mitre_limit=machine.CONTOUR_MITRE_LIMIT)
    except Exception:
        return []
    if not g.is_valid:
        g = g.buffer(0)
    return [p for p in _polygons(g) if p.area >= machine.CONTOUR_MIN_RING_AREA_MM2]


def _rings(poly: Polygon, spacing: float) -> list[list[Polygon]]:
    """Concentric offset generations, outermost first.

    Nesting is re-derived from each generation's own geometry rather than
    tracked forward, because it genuinely changes mid-sequence: a hole expanding
    outward meets an exterior contracting inward, and what was one ring becomes
    two. Caching a parent/child map across generations is the classic way to get
    a plausible-looking forest that is wrong on any shape with a counter.
    """
    first = spacing * machine.CONTOUR_FIRST_INSET_FRAC
    gens: list[list[Polygon]] = []
    d = first
    guard = 0
    while guard < machine.CONTOUR_MAX_GENERATIONS:
        guard += 1
        parts = _offset(poly, d)
        if not parts:
            break
        gens.append(parts)
        d += spacing
    return gens


def _ring_set(gens: list[list[Polygon]], report: dict) -> list[_Ring]:
    """Every ring of every generation — exteriors and the walls of every hole.

    A ring under `CONTOUR_MIN_RING_MM` is three minimum stitches round: sewing
    it is the needle re-entering its own holes. It is dropped, and both the
    count and the AREA it leaves bare are recorded — the count is the
    instrument, the area is what decides whether anyone needs to be told.
    """
    out: list[_Ring] = []
    for gi, parts in enumerate(gens):
        for pi, p in enumerate(parts):
            for ri, ring in enumerate([p.exterior, *p.interiors]):
                bare = p.area if ri == 0 else 0.0
                if ring is None or len(ring.coords) < 4:
                    report["skipped_rings"] += 1
                    report["skipped_area_mm2"] += bare
                    continue
                ls = LineString(ring.coords)
                if ls.length < machine.CONTOUR_MIN_RING_MM:
                    report["skipped_rings"] += 1
                    report["skipped_area_mm2"] += bare
                    continue
                b = tuple(round(v, 6) for v in ls.bounds)
                out.append(_Ring(line=ls, gen=gi, key=(gi, pi, ri, b), area=bare))
    return out


# --- Resampling ------------------------------------------------------------

def _curvature_cap(ring: LineString, stitch_mm: float, tol: float) -> float:
    """Longest chord this ring's own scale says is worth trying.

    From the sagitta relation h ~ L^2/8R: L <= sqrt(8*R*tol), with R estimated
    from the ring's own scale (a closed ring of perimeter P has an effective
    radius near P/2pi). This is a TASTE bound, not the containment guarantee —
    it is exactly right on circles and annuli and badly optimistic on a lobed
    ring, where one sharp notch does not move the average radius. Law 42 is
    enforced downstream in `_repair`, which measures instead of predicting.
    """
    if tol <= 0:
        return stitch_mm
    r = max(ring.length / (2.0 * math.pi), 1e-6)
    return max(machine.MIN_STITCH_MM, min(stitch_mm, math.sqrt(8.0 * r * tol)))


def _step_count(total: float, cap: float) -> int:
    """How many equal chords a ring of length `total` is cut into.

    Two bounds pull opposite ways and they are not equal in rank. The curvature
    cap wants MORE chords (each shorter, hugging the ring); the needle floor
    wants FEWER (each longer than `MIN_STITCH_MM`). The floor is a property of
    the machine and the cap is a quality target, so where they conflict the
    floor wins and the chord runs a little long.

    Rounding is what the first draft got wrong: `ceil(total/cap)` always
    overshoots, so the realized chord `total/n` is strictly SHORTER than the cap
    — and since `_curvature_cap` bottoms out at exactly `MIN_STITCH_MM`, every
    tight ring came out under the floor by construction.
    """
    if total <= 0 or cap <= 0:
        return 0
    lo = math.ceil(total / cap - 1e-9)                        # chord <= cap
    hi = math.floor(total / machine.MIN_STITCH_MM + 1e-9)     # chord >= floor
    return max(0, min(lo, hi))


def _ring_points(ring: LineString, entry: float, stitch_mm: float, tol: float
                 ) -> tuple[list[tuple[float, float]], list[float]]:
    """Penetrations round a closed ring from arc position `entry`, and their arcs.

    The closing point is `pts[0]` REUSED, not re-interpolated. Re-interpolating
    at `entry + n*step mod total` lands within a float ulp of the start but not
    ON it, and the first draft's exact `==` test for "is this ring closed"
    therefore missed — leaving a duplicated point that rotated into the middle
    of the path as a 0.000 mm stitch. Measured: 17 of them on one annulus.
    """
    total = ring.length
    n = _step_count(total, _curvature_cap(ring, stitch_mm, tol))
    if n < 3:
        return [], []
    step = total / n
    pts: list[tuple[float, float]] = []
    arcs: list[float] = []
    for i in range(n):
        s = (entry + i * step) % total
        p = ring.interpolate(s)
        pts.append((p.x, p.y))
        arcs.append(s)
    pts.append(pts[0])
    arcs.append(arcs[0])
    return pts, arcs


# --- Law 44: the crossing stitch -------------------------------------------

def _entry_arc(ring: LineString, anchor: tuple[float, float], need: float
               ) -> tuple[float, float]:
    """Where to enter `ring` so the crossing stitch clears the floor.

    -> (arc position, realized chord length from `anchor`).

    Rings sit one spacing apart — 0.40 mm at standard density — so entering at
    the NEAREST point emits a 0.40 mm stitch: under the 1.0 mm floor and inside
    the needle's same-hole radius. This does not search for a clear entry, it
    solves for one. A ring whose nearest approach is `g` away needs a walk of
    `sqrt(need^2 - g^2)` along itself for the crossing chord to reach `need`;
    the walk is arc length and the chord is the straight line, so the solved
    value is a lower bound and the loop steps forward from there.

    Because every ring is entered a short walk PAST the previous ring's seam,
    the seams advance around the shape instead of stacking into the radial spoke
    that is the loudest tell of machine contour fill.
    """
    total = ring.length
    t0 = ring.project(Point(anchor))
    p0 = ring.interpolate(t0)
    gap = math.dist(anchor, (p0.x, p0.y))
    best_t, best_d = t0, gap
    if gap >= need:
        return t0, gap
    probe = math.sqrt(max(0.0, need * need - gap * gap))
    stride = max(need / 4.0, 0.25)
    limit = total / 2.0
    while probe <= limit:
        t = (t0 + probe) % total
        p = ring.interpolate(t)
        d = math.dist(anchor, (p.x, p.y))
        if d > best_d:
            best_t, best_d = t, d
        if d >= need:
            return t, d
        probe += stride
    return best_t, best_d


# --- Law 42: the chord that bows out of the shape ---------------------------

def _arc_between(ring: LineString, sa: float, sb: float) -> LineString:
    """The ring's own path from arc `sa` to arc `sb`, forward, wrap included."""
    total = ring.length
    if sb > sa:
        return substring(ring, sa, sb)
    head = substring(ring, sa, total)
    tail = substring(ring, 0.0, sb)
    coords = list(head.coords) + list(tail.coords)[1:]
    if len(coords) < 2:
        return LineString([ring.interpolate(sa), ring.interpolate(sb)])
    return LineString(coords)


def _detour(ring: LineString, sa: float, sb: float, a: tuple[float, float],
            b: tuple[float, float], room, tol: float) -> list[tuple[float, float]]:
    """The fewest of the ring's own vertices that pull chord a->b back inside.

    Simplifying the arc to `tol` keeps every corner that matters and throws away
    the buffer's smoothing vertices; the second pass then drops each candidate
    whose absence still leaves a covered chord. On a star's inner notch that
    resolves to exactly one point — the notch apex — and the 2.4 mm chord that
    sat 0.48 mm outside becomes two chords that do not.
    """
    arc = _arc_between(ring, sa, sb)
    mids = [(x, y) for x, y in arc.simplify(tol).coords][1:-1]
    if not mids:
        p = arc.interpolate(arc.length / 2.0)
        mids = [(p.x, p.y)]
    seq = [a, *mids, b]
    kept: list[tuple[float, float]] = [seq[0]]
    i = 1
    while i < len(seq) - 1:
        if not room.covers(LineString([kept[-1], seq[i + 1]])):
            kept.append(seq[i])
        i += 1
    return kept[1:]


def _repair(ring: LineString, pts: list[tuple[float, float]], arcs: list[float],
            room, tol: float, report: dict) -> list[tuple[float, float]]:
    """Every emitted chord, clipped against the shape (law 42).

    Post-emission, not pre: a chord's endpoints both test inside while its
    middle is out, so nothing that looks at penetrations can see this.
    """
    if len(pts) < 2:
        return list(pts)
    out = [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if not room.covers(LineString([a, b])):
            out.extend(_detour(ring, arcs[i], arcs[i + 1], a, b, room, tol))
            report["clipped"] += 1
        out.append(b)
    return out


def _floor_pass(pts: list[tuple[float, float]], room, report: dict
                ) -> list[tuple[float, float]]:
    """Drop penetrations the needle would land on top of (law 18's floor).

    `_step_count` makes every chord long enough in ARC length, which is not the
    same thing: where an offset ring runs out along a thin sliver and back, two
    samples a full stitch apart around the ring sit a few tenths of a millimetre
    apart in SPACE. Measured before this pass: a 0.38 mm chord on the star and
    0.35 mm on the letter fixture, both from rings the containment clip had left
    untouched.

    A point is only dropped when the chord that replaces it is still inside the
    shape, so this cannot undo law 42's work. Both ends are pinned — the first
    because the ring was entered there and the last because the ring closes on
    it. Whatever survives under the floor is counted, not hidden.
    """
    if len(pts) < 3:
        return list(pts)
    floor = machine.MIN_STITCH_MM
    out = [pts[0]]
    i = 1
    while i < len(pts) - 1:
        if math.dist(out[-1], pts[i]) < floor:
            if room.covers(LineString([out[-1], pts[i + 1]])):
                i += 1
                continue
            # pts[i] is load-bearing — it is the corner the containment clip put
            # there, and skipping it puts the chord back outside the shape. Give
            # up the point BEFORE it instead, which is only a resample sample.
            if (len(out) >= 2 and math.dist(out[-2], pts[i]) >= floor
                    and room.covers(LineString([out[-2], pts[i]]))):
                out.pop()
        out.append(pts[i])
        i += 1
    out.append(pts[-1])
    # The closing chord is pinned at both ends, so it is the point BEFORE it
    # that has to give.
    while (len(out) > 2 and math.dist(out[-2], out[-1]) < floor
           and room.covers(LineString([out[-3], out[-1]]))):
        del out[-2]
    report["short_stitches"] += sum(
        1 for a, b in zip(out, out[1:]) if math.dist(a, b) < floor)
    return out


# --- Linking ---------------------------------------------------------------

def _link(rings: list[_Ring], spacing: float, stitch_mm: float, tol: float,
          room, start_near: tuple[float, float] | None, report: dict
          ) -> list[list[tuple[float, float]]]:
    """Rings -> continuous paths, innermost outward.

    Nearest-unvisited, seeded at the deepest generation. The first draft walked
    the generations in index order instead, which reads as inner-to-outer and is
    not: on an annulus each generation holds an outer ring and a hole wall on
    OPPOSITE sides of the band, so consecutive rings were metres apart in ring
    terms and every single one of the 22 banked its own path — 22 rings, 22
    paths, 17 travel bridges, on the one shape contour fill exists to sew well.
    Nearest-unvisited walks the outer family down and the hole family up, and
    lands 2 paths and 1 travel on the same annulus.

    Inner-to-outer so each path finishes on the OUTERMOST ring, where the tie
    stage 7 adds lands under the shape's own edge — and under a border, if one
    is sewn. A ring past the hard reach radius starts a new path (a neck split
    the shape); one past the soft radius is linked but counted, because a
    stretched link is where bare-fabric stripes hide.
    """
    need = machine.CONTOUR_TRANSITION_MIN_MM
    soft = machine.CONTOUR_ENTRY_SOFT * spacing
    hard = machine.CONTOUR_ENTRY_HARD * spacing

    unvisited = list(range(len(rings)))
    paths: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    cursor = start_near
    phase = 0.0

    while unvisited:
        pick = -1
        entry = 0.0
        if current:
            anchor = current[-1]
            here = Point(anchor)
            pick = min(unvisited, key=lambda i: (
                round(rings[i].line.distance(here), 6), rings[i].gen, rings[i].key))
            gap = rings[pick].line.distance(here)
            if gap > hard:
                paths.append(current)
                current = []
            else:
                entry, chord = _entry_arc(rings[pick].line, anchor, need)
                if chord < machine.MIN_STITCH_MM:
                    # Nowhere on this ring is a legal stitch from where the
                    # needle is. Banking costs a travel; linking anyway costs a
                    # needle. Bank.
                    paths.append(current)
                    current = []
                elif not room.covers(LineString(
                        [anchor, rings[pick].line.interpolate(entry)])):
                    # Law 42 applies to the crossing stitch too. `_entry_arc`
                    # solves only for LENGTH, so around a hole or across a neck
                    # its chord can leave the shape with both endpoints inside
                    # — measured before this test existed: 23 stitches outside
                    # over a 124-shape zoo, worst 1.10 mm out, and the shipped
                    # containment test failed verbatim on a 15 mm disc with a
                    # 0.3 mm hole. Banking turns the illegal stitch into a
                    # travel that `emit` routes inside the shape.
                    paths.append(current)
                    current = []
                elif gap > soft:
                    report["reach_stretched"] += 1
        if not current:
            deepest = max(rings[i].gen for i in unvisited)
            cand = [i for i in unvisited if rings[i].gen == deepest]
            if cursor is None:
                pick = min(cand, key=lambda i: rings[i].key)
            else:
                here = Point(cursor)
                pick = min(cand, key=lambda i: (
                    round(rings[i].line.distance(here), 6), rings[i].key))
            entry = (phase % 1.0) * rings[pick].line.length
            phase += machine.CONTOUR_PHASE_STEP

        unvisited.remove(pick)
        pts, arcs = _ring_points(rings[pick].line, entry, stitch_mm, tol)
        if len(pts) < 4:
            report["skipped_rings"] += 1
            report["skipped_area_mm2"] += rings[pick].area
            continue
        pts = _repair(rings[pick].line, pts, arcs, room, tol, report)
        pts = _floor_pass(pts, room, report)
        if len(pts) < 4:
            report["skipped_rings"] += 1
            report["skipped_area_mm2"] += rings[pick].area
            continue
        report["rings"] += 1
        if current:
            # The law 44 instrument. Every ring-to-ring crossing is a stitch and
            # this is its length; a regression here is needles, not pixels.
            report["transitions"] += 1
            report["min_transition_mm"] = min(report["min_transition_mm"],
                                              math.dist(current[-1], pts[0]))
        current.extend(pts)
        cursor = pts[-1]

    if current:
        paths.append(current)
    return paths


# --- The emitter -----------------------------------------------------------

def contour_fill(poly: Polygon, shape_id: str, *, spacing_mm: float,
                 stitch_mm: float, underlay_style: str, trim_at_mm: float,
                 tolerance_mm: float | None = None,
                 start_near: tuple[float, float] | None = None
                 ) -> tuple[list[StitchRun], dict]:
    """One shape -> contour-fill runs in sew order, plus the standard report.

    Same contract as `stitch_shape` and `satin_shape`, so stage 7 treats all
    three identically: underlay first, every run carries its own jump/trim,
    no ties (stage 7 owns those), entry nearest `start_near`.

    Report keys: `too_thin`, `jumps`, `empty` (the shared contract), plus
    `rings` (emitted), `skipped_rings` (too short to sew — unfilled fabric),
    `skipped_area_mm2` (the KNOWN-drop ledger — honest but structurally blind
    to the annihilated core, which is why it no longer decides anything),
    `bare_radius_mm` / `starved` (the widest circle of bare fabric between the
    emitted stitches, measured by barecircle.py, and whether it beats
    `starved_threshold_mm` — the warning gate since 2026-08-04),
    `reach_stretched` (linked past the soft radius), `clipped`
    (chords law 42 pulled back inside), `short_stitches` (penetrations that
    stayed under the floor because moving them would have left the shape — the
    one place laws 18 and 42 genuinely conflict, counted rather than hidden),
    `transitions` / `min_transition_mm` (law 44's instrument; `inf` when the
    shape held one ring or none) and `paths` (continuous ring runs; the travel
    between them is the only travel a contour fill has).
    """
    report = {"too_thin": False, "jumps": 0, "empty": False,
              "rings": 0, "skipped_rings": 0, "reach_stretched": 0,
              "clipped": 0, "short_stitches": 0, "paths": 0,
              "transitions": 0, "min_transition_mm": math.inf,
              "skipped_area_mm2": 0.0, "starved": 0, "bare_radius_mm": 0.0}
    tol = machine.CONTOUR_TOLERANCE_MM if tolerance_mm is None else tolerance_mm
    spacing = max(0.05, spacing_mm)

    if poly.is_empty or poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
        report["too_thin"] = True
    if poly.is_empty:
        report["empty"] = True
        return [], report

    # Containment is asked thousands of times per shape — once per emitted
    # chord — so the shape gets an index built once. Tested against the shape
    # itself, with no outward slack: the rings are already inset half a spacing,
    # so there is no float noise to forgive and an escape is a real escape.
    room = shapely.from_wkb(shapely.to_wkb(poly))
    shapely.prepare(room)

    runs: list[StitchRun] = []
    ring_guide = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)

    def emit(paths: list[list[tuple[float, float]]], kind: str) -> None:
        for path in paths:
            pts = stitches.split_long_moves(path, machine.MAX_STITCH_MM)
            if len(pts) < 2:
                continue
            jump = trim = False
            if runs:
                prev = runs[-1].points[-1]
                bridge = travel_path(poly, ring_guide, prev, pts[0], slack)
                if bridge is None:
                    d = math.dist(prev, pts[0])
                    if d >= machine.TINY_STITCH_MM:
                        jump = True
                        trim = d > trim_at_mm
                        report["jumps"] += 1
                elif len(bridge) > 1:
                    runs.append(StitchRun(points=bridge[:-1], kind=stitches.TRAVEL,
                                          shape_id=shape_id))
            runs.append(StitchRun(points=pts, kind=kind, jump=jump, trim=trim,
                                  shape_id=shape_id))

    # Underlay follows the contours too. The reference implementations run their
    # underlay at the FILL ANGLE even under a contour fill, which puts straight
    # rows under curved ones — the one place a contour fill can still telegraph
    # a grid. Matching the top layer's geometry is one call. The style names
    # (edge_run, zigzag, lattice) are tatami's vocabulary and do not survive the
    # change of geometry; anything but "none" gets the coarse ring set.
    entry = start_near
    if underlay_style and underlay_style != "none":
        u_spacing = spacing * machine.CONTOUR_UNDERLAY_SPACING_FRAC
        # An underlay ring dropped for being short is NOT unfilled fabric — the
        # fill above it covers the same ground — so the underlay's own drops are
        # counted apart and never reach the warning.
        u_report = {"rings": 0, "skipped_rings": 0, "reach_stretched": 0,
                    "clipped": 0, "short_stitches": 0, "transitions": 0,
                    "min_transition_mm": math.inf, "skipped_area_mm2": 0.0}
        u_rings = _ring_set(_rings(poly, u_spacing), u_report)
        if u_rings:
            u_paths = _link(u_rings, u_spacing, machine.UNDERLAY_STITCH_MM, tol,
                            room, entry, u_report)
            emit(u_paths, stitches.UNDERLAY)
            report["clipped"] += u_report["clipped"]
            if runs:
                entry = runs[-1].points[-1]

    rings = _ring_set(_rings(poly, spacing), report)
    if not rings:
        report["empty"] = not runs
        return runs, report

    body = _link(rings, spacing, stitch_mm, tol, room, entry, report)
    report["paths"] = len(body)
    emit(body, stitches.FILL)

    # The raw ring count is not the question, and neither — as of 2026-08-04 —
    # is the skipped-area ledger: `skipped_area_mm2` charges only the rings
    # this module KNOWS it dropped, and the bare core the mitred offset
    # annihilates was never a ring, so the ledger is structurally blind to the
    # worst case (a 10-point star of inradius 10.00 loses everything past
    # 5.60 mm of inset and charges 0.21 mm2 for it). `starved` is therefore
    # DEFINED by measurement, not bookkeeping: the widest circle of bare
    # fabric between the emitted stitches (barecircle.py — the instrument
    # trusts only the polygon and the runs), fired when it is wider than the
    # structural centre dot every healthy shape leaves plus half a ring
    # spacing (see `starved_threshold_mm` for the derivation and calibration).
    # The ledger stays in the report as the honest count of KNOWN drops.
    bare = widest_bare_circle(poly, runs)
    report["bare_radius_mm"] = bare.radius_mm
    report["starved"] = int(bare.radius_mm > starved_threshold_mm(spacing))
    report["empty"] = not runs
    return runs, report
