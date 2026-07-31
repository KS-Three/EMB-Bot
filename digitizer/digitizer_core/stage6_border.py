"""Stage 6 — the border tier: an outline sewn as one closed circuit.

A border is not a path with a width. It is the region between two offsets of
one ring, and every question a border raises — where it goes, where it stops,
what happens at a corner, what happens when the shape is too thin — is a
question `shapely.buffer` already answers as a boolean. That is the only
formulation that survives holes, pinches and self-touching outlines, and it is
the one the corpus asks for: 18 of 18 professional borders are ONE closed
circuit, not an assembly of arcs.

What the corpus measured (39 DSTs, `tools/border_pro.py`):

- A border column is **thinner** than a lettering column: median 1.40 mm
  (p10 0.78, p90 2.98) against 2.21 mm for satin generally. Sewing borders at
  lettering width is most of why a machine outline reads heavy.
- Border density is **looser** than lettering: 0.45 mm against 0.40–0.42. A
  border rides an edge that already has coverage under it.
- Corners are sewn THROUGH: 1,436 in-run corner events against 18 splits, the
  turn spread over roughly one column width. So this module has no splitter.
- The light tier is a bean / triple run: 14 found, 2.75 passes median at
  0.73 mm stitch length.

What the corpus did NOT measure is the **seam offset** — how far a border's
centreline sits from the fill edge it covers. The over-a-fill detector fired
zero times across 39 files, so the number does not exist and is not invented
here. `machine.BORDER_SEAM_OFFSET_MM` is pinned to 0.0, which is the boundary
condition rather than a guess: the column's OUTER rail lies exactly on the
region's visible edge and the whole column lies inside it. When the number is
measured, it is the only thing that changes — see `_centre_inset`.

Why the geometry is built with `buffer` and never `offset_curve`: the sign of
`offset_curve` depends on ring winding, silently. `stage4_vectorize` builds its
polygons straight from `cv2.findContours`, which arrives clockwise; any future
`orient()` or shapely upgrade flips that and every border in the shop lands
OUTSIDE its shape with no exception and no warning. `buffer(-d)` cannot express
that bug, returns every ring of a shape with holes in one call, and returns
empty — rather than a curve in the wrong place — when the shape is too thin to
hold a column.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

from . import machine, stitches
from .stage6_fill import travel_path
from .stitches import StitchRun

# Codes the report hands back to stage 7, which turns them into warnings.
TOO_NARROW = "too_narrow"
LIGHTENED = "lightened"
SPLIT_AT_PINCH = "split_at_pinch"

# Containment ladder for a cross that will not fit: fractions of the full
# column width, tried in order. Nothing below the minimum-cross rule survives
# anyway, so the ladder stops there.
_CLAMP_STEPS = (1.0, 0.85, 0.7, 0.55, 0.45, 0.35)

# Hair-width tolerance for "inside the shape". Same order as stage 6 fill's
# `slack`; float noise on a ring must not reject a cross that lies on it.
_SLACK_MM = 1e-3

# How many samples either side the corner detector measures curvature over is
# derived from the corner radius; this only bounds the relaxation so a
# pathological ring cannot spin.
_RELAX_ITERS = 240


# --- Ring sampling ---------------------------------------------------------

def _ring_arc_samples(coords: list[tuple[float, float]], n: int
                      ) -> tuple[list[tuple[float, float]], float]:
    """`n` points evenly spaced by ARCLENGTH around a closed ring, plus its length.

    Arclength, not vertex index: the outer rail is the rail that must hold
    density on a curve (law 4), and walking it by arclength makes the outer
    penetration spacing exactly the density with no refinement pass at all.
    """
    line = LineString(coords)
    total = line.length
    if total <= 0 or n < 3:
        return [], total
    pts = []
    for i in range(n):
        p = line.interpolate(total * i / n)
        pts.append((p.x, p.y))
    return pts, total


def _tangents(pts: list[tuple[float, float]], k: int) -> list[tuple[float, float]]:
    """Unit tangent at every sample, measured over a ±k baseline."""
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[(i - k) % n]
        b = pts[(i + k) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 1e-12:
            a = pts[(i - 1) % n]
            b = pts[(i + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1.0
        out.append((dx / d, dy / d))
    return out


def _turn_radius(pts: np.ndarray, k: int) -> np.ndarray:
    """Local turn radius at every sample, from the circumcircle of (i-k, i, i+k).

    Straight stretches come back as `inf`, which is what the corner detector
    wants: a threshold on radius flags corners and never flags a straight.
    """
    a = np.roll(pts, k, axis=0)
    b = pts
    c = np.roll(pts, -k, axis=0)
    ab = np.hypot(*(b - a).T)
    bc = np.hypot(*(c - b).T)
    ca = np.hypot(*(a - c).T)
    cross = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1])
                   - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    area2 = cross                      # 2 * triangle area
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(area2 > 1e-12, ab * bc * ca / (2.0 * area2), np.inf)
    return r


def _relax_corners(pts: list[tuple[float, float]], r_corner: float, k: int
                   ) -> list[tuple[float, float]]:
    """Give a ring a minimum turn radius, touching only what is sharper than it.

    A windowed Laplacian, iterated to a fixed point, applied inside a ±k window
    around every sample whose local turn radius is under `r_corner`. Straight
    stretches are never touched because the window never reaches them.

    This is deliberately NOT `buffer(-R).buffer(+R)`. That was measured and it
    is destructive: opening deletes any feature narrower than 2R, and it ate
    42% of a five-point star's centreline and 46% of a real letterform's. This
    is the one place in the border where shapely's offset is the wrong tool and
    a polyline operation is the right one.
    """
    n = len(pts)
    if n < 8:
        return pts
    p = np.asarray(pts, dtype=float)
    for _ in range(_RELAX_ITERS):
        r = _turn_radius(p, k)
        sharp = r < r_corner
        if not sharp.any():
            break
        # Widen the flag to the window so the fix is spread over the corner
        # rather than pinned to its apex.
        mask = np.zeros(n, dtype=bool)
        for s in range(-k, k + 1):
            mask |= np.roll(sharp, s)
        prev = np.roll(p, 1, axis=0)
        nxt = np.roll(p, -1, axis=0)
        moved = 0.25 * prev + 0.5 * p + 0.25 * nxt
        new = np.where(mask[:, None], moved, p)
        if float(np.abs(new - p).max()) < 1e-5:
            p = new
            break
        p = new
    return [(float(x), float(y)) for x, y in p]


def round_inward(poly: Polygon, r_corner: float, step_mm: float) -> Polygon:
    """`poly` with every corner sharper than `r_corner` relaxed, INWARD only.

    Intersecting the relaxed shape back with the original means the rounding
    can only ever REMOVE material, so a border built on the result is contained
    in the original by construction — for the exterior and every hole at once.
    Measured bite at r = 2.10 mm: 0.074 mm at a right angle, saturating at
    ~0.66 mm on a spike-sharp tip, ~1% of a 20 mm star's area. That bite is
    invisible only because the border rides over a fill that already reaches
    the true corner, which is why the "no border without coverage under it"
    rule and this one must move together.
    """
    rings: list[list[tuple[float, float]]] = []
    for ring in [poly.exterior, *poly.interiors]:
        n = max(8, int(round(ring.length / step_mm)))
        pts, total = _ring_arc_samples(list(ring.coords), n)
        if not pts:
            return poly
        k = max(1, int(round(r_corner / max(step_mm, 1e-6))))
        k = min(k, max(1, len(pts) // 4))
        rings.append(_relax_corners(pts, r_corner, k))
    try:
        relaxed = Polygon(rings[0], rings[1:])
        if not relaxed.is_valid:
            relaxed = relaxed.buffer(0)
        out = poly.intersection(relaxed)
    except Exception:
        return poly
    out = _keep_polygons(out)
    if out is None or out.is_empty or out.area < 0.5 * poly.area:
        # The relaxation ate the shape — a ring too small or too spiky for the
        # radius. Better a sharp border than no border; the corner cost is the
        # inner rail's, and the inner rail is under a fill.
        return poly
    return out


def _keep_polygons(geom):
    """Polygonal parts of a boolean result, or None. Never drops a real part."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"
             and not g.is_empty]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    from shapely.geometry import MultiPolygon
    return MultiPolygon(parts)


def _parts(geom) -> list[Polygon]:
    """Every polygon of a Polygon/MultiPolygon, ordered deterministically."""
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    out = [g for g in getattr(geom, "geoms", [])
           if g.geom_type == "Polygon" and not g.is_empty]
    return sorted(out, key=lambda g: (round(g.bounds[1], 6), round(g.bounds[0], 6),
                                      -round(g.area, 6)))


# --- The column ------------------------------------------------------------

def _centre_inset(half_mm: float) -> float:
    """Distance from the visible edge to the border's centreline.

    `BORDER_SEAM_OFFSET_MM` is 0.0 and UNMEASURED — see the module docstring.
    At 0.0 the column's outer rail lies exactly on the visible edge. When the
    corpus finally measures how far a professional's border sits off the fill
    edge it covers, this expression is the whole change: nothing else in the
    module reads the edge.
    """
    return half_mm + machine.BORDER_SEAM_OFFSET_MM


def _inward_sign(pts: list[tuple[float, float]], tans: list[tuple[float, float]],
                 inside) -> float:
    """+1 or -1: which way the left-hand normal points into the material.

    Decided by asking the geometry, not by trusting ring winding. `buffer`
    output is consistently oriented today, but the whole reason this module
    uses `buffer` is that winding assumptions fail silently, and a border on
    the wrong side of its own ring is a wrong DST with no warning. Majority
    vote over evenly spaced samples, so one sample landing on a cusp cannot
    flip a loop.
    """
    n = len(pts)
    votes = 0
    eps = 0.02
    for j in range(min(24, n)):
        i = (j * n) // min(24, n)
        (px, py), (tx, ty) = pts[i], tans[i]
        nx, ny = -ty, tx
        if inside.contains(Point(px + nx * eps, py + ny * eps)):
            votes += 1
        elif inside.contains(Point(px - nx * eps, py - ny * eps)):
            votes -= 1
    return 1.0 if votes >= 0 else -1.0


def _clamped_cross(px: float, py: float, nx: float, ny: float, width: float,
                   inside) -> tuple[tuple[float, float], float]:
    """The inner end of one cross, shortened until the whole cross fits.

    A pinch or an isthmus narrower than the column does not get a border that
    escapes the shape; it gets a shorter cross, and one shorter than
    `SATIN_MIN_CROSS_MM` gets dropped by the caller — the same rule the satin
    module already applies to a tapering tip.
    """
    for frac in _CLAMP_STEPS:
        w = width * frac
        q = (px + nx * w, py + ny * w)
        if inside.covers(LineString([(px, py), q])):
            return q, w
    return (px, py), 0.0


def _loop_stations(pts: list[tuple[float, float]], total: float, step: float,
                   start: int, overlap_mm: float) -> list[int | float]:
    """Station indices for one circuit, plus the phase-shifted closing overlap.

    The loop runs the full ring and then continues PAST its own start by
    `overlap_mm`, offset by half a station so the closing penetrations land
    between the opening ones instead of back in them. A butt joint is visible;
    one column width of doubled thread is not, and re-entering three needle
    holes frays the edge.
    """
    n = len(pts)
    out: list[int | float] = [(start + i) % n for i in range(n)]
    if overlap_mm > 0 and total > 0:
        extra = int(overlap_mm / step)
        for j in range(extra):
            out.append(((start + j + 0.5) % n))
    return out


def _at(pts: list[tuple[float, float]], idx: float) -> tuple[float, float]:
    """Sample a ring at a fractional index (the half-station overlap phase)."""
    n = len(pts)
    i = int(math.floor(idx)) % n
    f = idx - math.floor(idx)
    if f < 1e-9:
        return pts[i]
    a, b = pts[i], pts[(i + 1) % n]
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def _pick_start(pts: list[tuple[float, float]], radii: np.ndarray,
                entry: tuple[float, float] | None, search_mm: float,
                step: float) -> int:
    """Where the circuit joins: near the needle, on the flattest stretch.

    A butt joint on a straight is a line you have to look for; a butt joint on
    a corner is a lump. Nearest-to-entry first, then slid to the flattest
    station within `search_mm`. Ties break on index, so it is deterministic.
    """
    n = len(pts)
    if entry is None:
        base = 0
    else:
        base = min(range(n), key=lambda i: (round(math.dist(pts[i], entry), 6), i))
    span = max(1, int(search_mm / max(step, 1e-6)))
    best, best_r = base, -1.0
    for d in range(-span, span + 1):
        i = (base + d) % n
        r = float(radii[i]) if math.isfinite(radii[i]) else 1e9
        if r > best_r + 1e-9:
            best, best_r = i, r
    return best


def _satin_loop(ring_pts: list[tuple[float, float]], total: float, step: float,
                width: float, inside, entry: tuple[float, float] | None,
                k_tan: int) -> tuple[list[tuple[float, float]], int, int]:
    """One closed circuit as a satin column. -> (points, crosses, clamped)."""
    n = len(ring_pts)
    tans = _tangents(ring_pts, k_tan)
    sign = _inward_sign(ring_pts, tans, inside)
    radii = _turn_radius(np.asarray(ring_pts, dtype=float), k_tan)
    start = _pick_start(ring_pts, radii, entry, machine.BORDER_JOIN_SEARCH_MM, step)

    outer: list[tuple[float, float]] = []
    inner: list[tuple[float, float]] = []
    widths: list[float] = []
    for i in range(n):
        px, py = ring_pts[i]
        tx, ty = tans[i]
        nx, ny = -ty * sign, tx * sign
        q, w = _clamped_cross(px, py, nx, ny, width, inside)
        outer.append((px, py))
        inner.append(q)
        widths.append(w)

    stations = _loop_stations(ring_pts, total, step, start,
                              machine.BORDER_CLOSURE_OVERLAP_MM)

    pts: list[tuple[float, float]] = []
    rails: list[int] = []          # which rail each emitted point sits on
    partners: list[tuple[float, float]] = []
    clamped = 0
    kept = 0
    for s in stations:
        if isinstance(s, int):
            o, q, w = outer[s], inner[s], widths[s]
        else:
            # Half-station overlap phase: interpolate both rails so the closing
            # crosses land between the opening ones on BOTH sides.
            i0, i1 = int(math.floor(s)) % n, (int(math.floor(s)) + 1) % n
            f = s - math.floor(s)
            o = _at(outer, s)
            q = (inner[i0][0] + (inner[i1][0] - inner[i0][0]) * f,
                 inner[i0][1] + (inner[i1][1] - inner[i0][1]) * f)
            w = math.dist(o, q)
        if w < machine.SATIN_MIN_CROSS_MM:
            continue               # rails pinched: nothing to sew here
        if w < width - 1e-6:
            clamped += 1
        # Alternate on the count of KEPT crosses, never on the source index.
        # A dropped cross must not flip the rail the next one lands on, or the
        # machine sews a stitch straight along the rail instead of across it.
        if kept % 2 == 0:
            pts.append(o)
            partners.append(q)
            rails.append(0)
        else:
            pts.append(q)
            partners.append(o)
            rails.append(1)
        kept += 1

    _short_stitch_guard(pts, partners, rails)
    return pts, kept, clamped


def _short_stitch_guard(pts: list[tuple[float, float]],
                        partners: list[tuple[float, float]],
                        rails: list[int]) -> None:
    """Pull back an inner penetration that landed in its neighbour's hole.

    On the inside of a corner the inner rail is shorter than the outer one, so
    its penetrations bunch. Below `SATIN_SHORT_STITCH_AT_MM` the needle starts
    re-entering the same hole and the edge frays. Same rule and same constants
    the satin column already uses — the outer rail is never touched, because
    the outer rail is the one holding the density.
    """
    pull = machine.SATIN_SHORT_STITCH_PULL
    for j in range(2, len(pts)):
        if rails[j] != 1 or rails[j - 2] != 1:
            continue
        if math.dist(pts[j], pts[j - 2]) >= machine.SATIN_SHORT_STITCH_AT_MM:
            continue
        a, b = pts[j], partners[j]
        pts[j] = (a[0] + (b[0] - a[0]) * pull, a[1] + (b[1] - a[1]) * pull)


def _bean_loop(ring_pts: list[tuple[float, float]], entry: tuple[float, float] | None,
               step: float, passes: int) -> list[tuple[float, float]]:
    """One closed circuit as a bean / triple run — the light outline tier.

    Corpus law: 14 bean outlines, 2.75 passes median (p90 3.27) at 0.73 mm
    stitch length. Same geometry as the column, same closure rule, one tenth
    the bulk — and it cannot self-overlap, which is exactly why a shape too
    narrow to host a column gets this instead.
    """
    n = len(ring_pts)
    if n < 3:
        return []
    if entry is None:
        start = 0
    else:
        start = min(range(n), key=lambda i: (round(math.dist(ring_pts[i], entry), 6), i))
    lap = [ring_pts[(start + i) % n] for i in range(n)] + [ring_pts[start]]
    out = list(lap)
    for p in range(1, passes):
        leg = list(reversed(lap)) if p % 2 == 1 else list(lap)
        out.extend(leg[1:])
    return out


# --- Entry point -----------------------------------------------------------

def border_runs(visible, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float, style: str = "auto",
                width_mm: float | None = None,
                density_mm: float | None = None) -> tuple[list[StitchRun], dict]:
    """Outline the VISIBLE part of one shape. -> (runs, report).

    `visible` is stage 5's grown polygon with everything that sews after it
    subtracted — see `PlannedRegion.visible_geom`. It is the geometry a person
    will actually see, and it is the only geometry a border may be drawn on.

    One `StitchRun` per ring that passes the gates: exterior first, then every
    counter, each its own closed circuit (law 13, 18/18). Report keys:
    `loops`, `bean_loops`, `crosses`, `clamped`, `too_narrow`, `jumps`,
    `empty`, `split_at_pinch`.
    """
    report = {"loops": 0, "bean_loops": 0, "crosses": 0, "clamped": 0,
              "too_narrow": 0, "jumps": 0, "empty": True, "split_at_pinch": 0}
    if style == "none" or visible is None:
        return [], report

    width = machine.BORDER_WIDTH_MM if width_mm is None else float(width_mm)
    density = machine.BORDER_DENSITY_MM if density_mm is None else float(density_mm)
    if width <= 0 or density <= 0:
        return [], report
    half = width / 2.0
    inset = _centre_inset(half)
    # A zigzag holds `density` between consecutive penetrations on the SAME
    # rail (law 4 measures the rails), and every stitch crosses the column. So
    # stations sit at half the density and each contributes ONE penetration,
    # alternating sides: same-rail spacing `density`, no hop along a rail.
    step = density / 2.0

    runs: list[StitchRun] = []
    parts = _parts(visible)
    if len(parts) > 1:
        report["split_at_pinch"] = len(parts) - 1

    cursor = entry
    for part in parts:
        rounded = round_inward(part, machine.BORDER_CORNER_RADIUS_MM, step)
        for host in _parts(rounded):
            # Can a centreline live in here at all?
            spine_geom = _keep_polygons(host.buffer(-inset))
            if spine_geom is None:
                report["too_narrow"] += 1
                continue
            core = host.buffer(-(inset + half + machine.BORDER_HOST_MARGIN_MM))
            lighten = style == "bean" or core.is_empty
            slack = prep(host.buffer(_SLACK_MM))

            rings: list[list[tuple[float, float]]] = []
            if lighten:
                for sp in _parts(spine_geom):
                    rings.extend([list(sp.exterior.coords)]
                                 + [list(r.coords) for r in sp.interiors])
                sample_step = machine.BEAN_STITCH_MM
            else:
                rings = [list(host.exterior.coords)] + \
                        [list(r.coords) for r in host.interiors]
                sample_step = step

            for coords in rings:
                length = LineString(coords).length
                if length < machine.BORDER_MIN_LOOP_MM:
                    continue       # shorter than 2*pi*W: a dot, not an outline
                n = max(8, int(round(length / sample_step)))
                ring_pts, total = _ring_arc_samples(coords, n)
                if not ring_pts:
                    continue
                if lighten:
                    pts = _bean_loop(ring_pts, cursor, sample_step,
                                     machine.BEAN_PASSES)
                    kind = stitches.BEAN
                    crosses = 0
                else:
                    k_tan = max(1, int(round(half / sample_step)))
                    pts, crosses, clamped = _satin_loop(
                        ring_pts, total, total / n, width, slack, cursor, k_tan)
                    kind = stitches.BORDER
                    report["clamped"] += clamped
                if len(pts) < 2:
                    continue

                # Bridge from wherever the needle is. A border starts on the
                # shape's own edge and the fill ended inside the same shape, so
                # this is a few millimetres and almost always stays needle-down.
                jump = trim = False
                if cursor is not None:
                    bridge = travel_path(host, None, cursor, pts[0])
                    if bridge is None:
                        d = math.dist(cursor, pts[0])
                        if d >= machine.TINY_STITCH_MM:
                            jump = True
                            trim = d > trim_at_mm
                            report["jumps"] += 1
                    elif len(bridge) > 1:
                        runs.append(StitchRun(points=bridge[:-1],
                                              kind=stitches.TRAVEL,
                                              shape_id=shape_id))
                runs.append(StitchRun(points=stitches.split_long_moves(pts),
                                      kind=kind, jump=jump, trim=trim,
                                      shape_id=shape_id))
                cursor = pts[-1]
                report["crosses"] += crosses
                if lighten:
                    report["bean_loops"] += 1
                else:
                    report["loops"] += 1

    report["empty"] = not runs
    return runs, report
