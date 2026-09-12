"""Stage 6 — the border tier: an outline sewn as one closed circuit.

A border is not a path with a width. It is the region between two offsets of
one ring, and every question a border raises — where it goes, where it stops,
what happens at a corner, what happens when the shape is too thin — is a
question `shapely.buffer` already answers as a boolean. That is the only
formulation that survives holes, pinches and self-touching outlines, and it is
the one the corpus asks for: 18 of 18 professional borders are ONE closed
circuit, not an assembly of arcs.

What the corpus measured (39 DSTs, `tools/border_pro.py`):

- Round 2 called a border column **thinner** than a lettering column (median
  1.40 mm) — but that population was closed loops, mostly round letters.
  Round 3's law 41 (`docs/corpus-laws-round3-2026-08-01.md`) measured real
  EDGE-COVERING borders at 1.66 mm med (2.39 on the >=20 mm subset):
  `machine.BORDER_WIDTH_MM` carries the adjudicated 1.70.
- Round 2 called border density **looser** than lettering (0.45 against
  0.40–0.42, "it rides an edge that already has coverage"). Law 41 refuted
  that: real covering borders sew at 0.40 mm (p10 0.36, p90 0.42) — identical
  to lettering. There is no density relaxation.
- Corners are sewn THROUGH: 1,436 in-run corner events against 18 splits, the
  turn spread over roughly one column width. So this module has no splitter.
- The light tier is a bean / triple run: 14 found, 2.75 passes median at
  0.73 mm stitch length.

The **seam offset** — how far a border's centreline sits from the fill edge it
covers — was unmeasured by that 39-file pass: the over-a-fill detector fired
zero times because it required a `classify()`-labelled fill run in the same
colour block. Round 3's region-level re-instrument dropped that requirement
(40 files, `docs/corpus-laws-round3-2026-08-01.md` law 40) and found 41
genuinely covering columns: centreline offset vs. the fill edge (inward
positive) medians +0.05 mm (n=41) / +0.00 mm on the trustworthy >=20 mm-long
subset (n=25), both confirming `machine.BORDER_SEAM_OFFSET_MM = 0.0` rather
than moving it — see `_centre_inset`.

Why the geometry is built with `buffer` and never `offset_curve`: the sign of
`offset_curve` depends on ring winding, silently. `stage4_vectorize` builds its
polygons straight from `cv2.findContours`, which arrives clockwise; any future
`orient()` or shapely upgrade flips that and every border in the shop lands
OUTSIDE its shape with no exception and no warning. `buffer(-d)` cannot express
that bug, returns every ring of a shape with holes in one call, and returns
empty — rather than a curve in the wrong place — when the shape is too thin to
hold a column.

SEAM OWNERSHIP, one module up. Under `border="auto"` two different-colour
shapes that ABUT get coincident border rails on the shared seam — stage 5
makes both visible edges the same line — so two full circuits would ride it
as a double-thick bar in two threads. This module has no notion of "the other
shape" (a border is built from one shape's own `visible` geometry and nothing
else), so the rule lives in `stage7_sequence._owned_by_later`, which has both
shapes and the sew order: a seam is bordered ONCE, by the shape sewn LATER —
it lies on top, so its column covers both fills' edges — and the earlier
shape hands the stretch in here as `omit`. On this side that means a ring is
sewn as the open arcs that remain, still on the edge and still the same
column, rather than as a closed circuit; a ring with nothing left is skipped,
and both are counted under `yielded` so the report never goes quiet about it.

The first version of this (2026-08-06, `_yield_frontage`) had the LATER shape
retreat its whole circuit a column width off the seam instead, and the test
pinned that as the wanted outcome. On artwork where every colour abuts —
which is every flat logo — that put a satin stripe 1.9 mm inside nearly every
fill and no border on its edge at all; measured on Kent's Instagram icon,
14 of 17 bordered shapes, one border lost outright (Kent, 2026-09-09: "the
satin border is not following the outline of each color").
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points
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

# The deepest a corner relaxation may retreat from the true edge: half a
# border column width (machine.BORDER_WIDTH_MM / 2), so a rounded tip stays
# within the column's own thread coverage. See `_relax_corners` for the
# measured defect this caps.
_BITE_MAX_MM = machine.BORDER_WIDTH_MM / 2.0


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
    p0 = p.copy()
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
        # Cap how far any sample may retreat from the true edge. Uncapped, the
        # Laplacian's fixed point on a spike-sharp tip sits ~1.85 mm inside it
        # (measured on 12-24 mm five-point stars) — the outline visibly cuts
        # the corner off while the fill under it reaches the real apex, and
        # the corpus law is the opposite: pros sew THROUGH corners. Half a
        # column width keeps the true tip inside the column's own thread
        # coverage, so the cap reads as rounding, never as a missing corner.
        disp = new - p0
        d = np.hypot(disp[:, 0], disp[:, 1])
        over = d > _BITE_MAX_MM
        if over.any():
            scale = (_BITE_MAX_MM / np.where(d > 1e-12, d, 1.0))[:, None]
            new = np.where(over[:, None], p0 + disp * scale, new)
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

    Measured bite at r = 2.10 mm, WITH the `_BITE_MAX_MM` cap: 0.70 mm at a
    right angle, 0.70-0.79 mm at a spike-sharp star tip, 1.4% of a 20 mm
    square's area and 3.2% of a 20 mm star's. (This docstring once claimed
    0.074 / 0.66 / 1% for the uncapped relaxation; adversarial review measured
    the truth at 1.01 / 1.85 / 7.4% — the fixed point of the Laplacian sits
    far deeper than anyone had checked, and the cap now exists because of it.)
    STALE since law 41 (2026-08-19): `_BITE_MAX_MM` is derived from
    `BORDER_WIDTH_MM`, which moved 1.40 -> 1.70 mm, so the cap itself moved
    0.70 -> 0.85 mm and the figures above are the OLD cap's numbers, not
    re-measured. Whoever next touches this function should re-run the fixture
    and replace this paragraph rather than trust it.
    A sub-column-width bite reads as rounding; it stays invisible because the
    border rides over a fill that already reaches the true corner, which is
    why the "no border without coverage under it" rule and this one must move
    together.
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

    `BORDER_SEAM_OFFSET_MM` is 0.0 — MEASURED, not a boundary condition, per
    corpus law 40 (median +0.00 mm on the trustworthy >=20 mm-long covering
    columns; see the module docstring). At 0.0 the column's outer rail lies
    exactly on the visible edge. If a future re-measurement ever moves the
    number, this expression is the whole change: nothing else in the module
    reads the edge.
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
                   start: int, overlap_mm: float,
                   overlap_stitches: int | None = None) -> list[int | float]:
    """Station indices for one circuit, plus the phase-shifted closing overlap.

    The loop runs the full ring and then continues PAST its own start by
    `overlap_mm`, phased so the closing penetrations land midway between the
    opening ones ON THEIR OWN RAIL. A butt joint is visible; one column width
    of doubled thread is not, and re-entering three needle holes frays the
    edge.

    The phase is a whole station, not half a one — and which whole depends on
    the ring's parity. Stations alternate rails, so same-rail holes sit TWO
    stations apart; a half-station shift puts every closing penetration a
    quarter-pitch (0.11 mm, inside the same-hole radius) from an existing hole
    on its own rail — precisely the re-entry the overlap exists to avoid,
    found by adversarial review. The closing pass continues the emitter's
    alternation, so its rail parity at a given ring position flips with n:
    for even n a one-station shift lands each closing cross at the position
    of an OPPOSITE-rail opening (own-rail holes a full station away on both
    sides); for odd n the wrap itself flips parity and a zero shift does the
    same thing.

    `overlap_stitches`, when given, states the overlap directly as a station
    (stitch) count instead of a distance divided by `step` — what
    `stage6_applique._cover_layer` wants, because its own spec constant
    (`APPLIQUE_CLOSURE_OVERLAP_STITCHES`) is already a stitch count, and
    round-tripping it through an mm distance would leave the exact number
    hostage to how evenly `step` divides this particular ring's arc length.
    Every other caller passes `overlap_mm` alone and is untouched.
    """
    n = len(pts)
    out: list[int | float] = [(start + i) % n for i in range(n)]
    extra = 0
    if total > 0:
        if overlap_stitches is not None:
            extra = max(0, overlap_stitches)
        elif overlap_mm > 0:
            extra = int(overlap_mm / step)
    if extra > 0:
        shift = 1 if n % 2 == 0 else 0
        for j in range(extra):
            out.append((start + j + shift) % n)
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
                k_tan: int, overlap_stitches: int | None = None
                ) -> tuple[list[tuple[float, float]], int, int]:
    """One closed circuit as a satin column. -> (points, crosses, clamped).

    Closure overlap is `machine.BORDER_CLOSURE_OVERLAP_MM` (a distance) unless
    `overlap_stitches` gives an exact station count instead — see
    `_loop_stations` for why appliqué's cover wants that path.
    """
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
                              machine.BORDER_CLOSURE_OVERLAP_MM,
                              overlap_stitches)

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


# --- Open arcs: a ring with a stretch owned by a neighbour's border ---------

# A ring sample whose edge lies this close to an omitted stretch is on it.
# The corner relaxation can pull a sample further inside than this at a sharp
# corner; such a sample keeps its cross, which then sits inside THIS shape
# beside the neighbour's column rather than on top of it — a sub-column
# patch at the seam's two ends, not a stripe.
_OMIT_TOL_MM = machine.BORDER_HOST_MARGIN_MM

# An arc shorter than the column is wide is a blob, not an edge.
_ARC_MIN_MM = machine.BORDER_WIDTH_MM


def _ring_arcs(ring_pts: list[tuple[float, float]], omit, edge
               ) -> tuple[list[list[tuple[float, float]]], bool]:
    """The arcs of a ring NOT on `omit`. -> (arcs, whole).

    `whole` is True when no sample was omitted — the caller keeps the closed
    circuit, byte-identical to a ring that was never asked. An empty list
    with `whole` False is a ring omitted end to end.

    Each sample is judged by the EDGE it stands in for, not by where it sits:
    a satin ring's samples ARE the edge, but a bean ring rides a spine inset
    half a column from it, and on a thin shape both sides of that spine are
    within a column of the seam. `edge` is the host's boundary; the sample's
    nearest point on it is what gets tested. Splitting is circular — index 0
    is rotated onto a dropped sample first, so an arc that straddles the
    ring's own start/end stays one arc.
    """
    if edge is None:
        keep = [not omit.intersects(Point(p)) for p in ring_pts]
    else:
        keep = [not omit.intersects(nearest_points(edge, Point(p))[0])
                for p in ring_pts]
    if all(keep):
        return [ring_pts], True
    if not any(keep):
        return [], False
    n = len(ring_pts)
    start = keep.index(False)
    arcs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for i in range(1, n + 1):
        j = (start + i) % n
        if keep[j]:
            cur.append(ring_pts[j])
        elif cur:
            arcs.append(cur)
            cur = []
    if cur:
        arcs.append(cur)
    return arcs, False


def _open_tangents(pts: list[tuple[float, float]], k: int
                   ) -> list[tuple[float, float]]:
    """`_tangents` for an open polyline: the ±k baseline clamps at the ends
    instead of wrapping, so the first and last tangents point along the arc
    rather than across the gap it was cut from."""
    n = len(pts)
    out = []
    for i in range(n):
        a = pts[max(0, i - k)]
        b = pts[min(n - 1, i + k)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 1e-12:
            a = pts[max(0, i - 1)]
            b = pts[min(n - 1, i + 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy) or 1.0
        out.append((dx / d, dy / d))
    return out


def _towards(arc: list[tuple[float, float]], entry: tuple[float, float] | None
             ) -> list[tuple[float, float]]:
    """The arc, starting at whichever end is nearer the needle."""
    if entry is None or math.dist(entry, arc[0]) <= math.dist(entry, arc[-1]):
        return list(arc)
    return list(reversed(arc))


def _satin_arc(arc: list[tuple[float, float]], width: float, inside,
               entry: tuple[float, float] | None, k_tan: int
               ) -> tuple[list[tuple[float, float]], int, int]:
    """One open stretch of edge as a satin column. -> (points, crosses, clamped).

    `_satin_loop` without the loop: same crosses, same rails, same clamp
    ladder and short-stitch guard, no closure overlap (there is nothing to
    close) and no join search (it starts at the end nearer the needle).
    """
    pts_in = _towards(arc, entry)
    tans = _open_tangents(pts_in, k_tan)
    sign = _inward_sign(pts_in, tans, inside)
    pts: list[tuple[float, float]] = []
    rails: list[int] = []
    partners: list[tuple[float, float]] = []
    clamped = 0
    kept = 0
    for (px, py), (tx, ty) in zip(pts_in, tans):
        nx, ny = -ty * sign, tx * sign
        q, w = _clamped_cross(px, py, nx, ny, width, inside)
        if w < machine.SATIN_MIN_CROSS_MM:
            continue
        if w < width - 1e-6:
            clamped += 1
        if kept % 2 == 0:
            pts.append((px, py))
            partners.append(q)
            rails.append(0)
        else:
            pts.append(q)
            partners.append((px, py))
            rails.append(1)
        kept += 1
    _short_stitch_guard(pts, partners, rails)
    return pts, kept, clamped


def _bean_arc(arc: list[tuple[float, float]], entry: tuple[float, float] | None,
              passes: int) -> list[tuple[float, float]]:
    """One open stretch of spine as a bean run: there, back, and there again."""
    lap = _towards(arc, entry)
    if len(lap) < 2:
        return []
    out = list(lap)
    for p in range(1, passes):
        leg = list(reversed(lap)) if p % 2 == 1 else list(lap)
        out.extend(leg[1:])
    return out


# --- Entry point -----------------------------------------------------------

def border_runs(visible, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float, style: str = "auto",
                width_mm: float | None = None,
                density_mm: float | None = None,
                omit=None) -> tuple[list[StitchRun], dict]:
    """Outline the VISIBLE part of one shape. -> (runs, report).

    `visible` is stage 5's grown polygon with everything that sews after it
    subtracted — see `PlannedRegion.visible_geom`. It is the geometry a person
    will actually see, and it is the only geometry a border may be drawn on.

    One `StitchRun` per ring that passes the gates: exterior first, then every
    counter, each its own closed circuit (law 13, 18/18).

    `omit`, when given, is the part of this shape's edge that a neighbour's
    border already covers — the seams `stage7_sequence._owned_by_later`
    hands to the shape sewn UNDERNEATH (see the module docstring). Every
    ring sample standing in for that stretch is dropped, and what remains of
    the ring sews as open arcs — one `StitchRun` each, the same column, on
    the same edge. `None` (or a geometry the ring never meets) is the closed
    circuit, byte for byte.

    Report keys: `loops`, `bean_loops`, `arcs`, `bean_arcs`, `yielded`
    (rings that lost a stretch or all of themselves to `omit`), `crosses`,
    `clamped`, `too_narrow`, `jumps`, `empty`, `split_at_pinch`.
    """
    report = {"loops": 0, "bean_loops": 0, "arcs": 0, "bean_arcs": 0,
              "yielded": 0, "crosses": 0, "clamped": 0, "too_narrow": 0,
              "jumps": 0, "empty": True, "split_at_pinch": 0}
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
    # Prepared once; every ring sample of every part is tested against it.
    omit_prep = None
    if omit is not None and not getattr(omit, "is_empty", True):
        omit_prep = prep(omit.buffer(_OMIT_TOL_MM))

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
                if omit_prep is None:
                    arcs, whole = [ring_pts], True
                else:
                    # A satin ring's samples are the edge; a bean ring's sit
                    # on the inset spine and are judged by the edge nearest
                    # each one.
                    arcs, whole = _ring_arcs(
                        ring_pts, omit_prep, host.boundary if lighten else None)
                    if not whole:
                        report["yielded"] += 1
                for arc in arcs:
                    if whole:
                        if lighten:
                            pts = _bean_loop(ring_pts, cursor, sample_step,
                                             machine.BEAN_PASSES)
                            kind = stitches.BEAN
                            crosses = 0
                        else:
                            k_tan = max(1, int(round(half / sample_step)))
                            pts, crosses, clamped = _satin_loop(
                                ring_pts, total, total / n, width, slack,
                                cursor, k_tan)
                            kind = stitches.BORDER
                            report["clamped"] += clamped
                    else:
                        if len(arc) < 2 or LineString(arc).length < _ARC_MIN_MM:
                            continue   # a blob, not an edge
                        if lighten:
                            pts = _bean_arc(arc, cursor, machine.BEAN_PASSES)
                            kind = stitches.BEAN
                            crosses = 0
                        else:
                            k_tan = max(1, int(round(half / sample_step)))
                            pts, crosses, clamped = _satin_arc(
                                arc, width, slack, cursor, k_tan)
                            kind = stitches.BORDER
                            report["clamped"] += clamped
                    if len(pts) < 2:
                        continue

                    # Bridge from wherever the needle is. A border starts on
                    # the shape's own edge and the fill ended inside the same
                    # shape, so this is a few millimetres and almost always
                    # stays needle-down.
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
                    if not whole:
                        report["bean_arcs" if lighten else "arcs"] += 1
                    elif lighten:
                        report["bean_loops"] += 1
                    else:
                        report["loops"] += 1

    report["empty"] = not runs
    return runs, report


EDGE_CAP_STYLES = ("none", "bean", "satin")

# What the cap may bill before the plan says so OUT LOUD, as a percentage of
# the artwork's own stitches (`EDGE_CAP_OVER_BUDGET`, stage 7). Not a physical
# constant and not a taste call — a line drawn in an EMPTY GAP between two
# regimes both already measured in this repo:
#
#   * **Gate working, every fixture and every width measured: 4.4% to 26.6%.**
#     The flip's own sheet reads +5.9-26.3% median +13.4% over six fixtures at
#     80 mm (MASTER_SCOPE defect 19); the size sweep in
#     `docs/edge-cap-cliff-2026-09-12.md` reads `enthusiast_logo` 4.4-6.9%,
#     `logo_hotel_fremont` 5.5-8.6%, `logo_whitebg` 21.2-26.3% across 80-110
#     mm, and becker's own cheap widths 18.1% (80 mm) and 26.6% (96 mm).
#     `logo_whitebg` is the one that matters: it is a legitimate `width_cap`
#     fill design that never was a ribbon candidate, it sits in the low 20s at
#     EVERY width, and a ceiling that fires on it would be wrong.
#   * **Gate collapsed or absent: 53.4% and up.** becker at 88/91/95.7/100/110
#     mm bills 58.7 / 56.7 / 56.6 / 55.6 / 53.4% — at 110 mm with no gate input
#     at all. The pre-gate regime the gate was built to kill was +8.6-100.4%,
#     and `drone_render` capped at +56.9% there, which defect 19 calls "a
#     whisker off DOCTRINE's blanket-border negative" (+60% of stitches to
#     WORSEN a silhouette).
#
# No measurement anywhere in the repo falls between 26.6% and 53.4%. The
# ceiling is the midpoint of that gap: 1.5x above every bill the gate has been
# seen to produce working, 1.34x below every bill it has been seen to produce
# collapsed, and below both the +56.9% and the +60% already on record as bad.
# Round because the gap is 27 points wide and no third digit is earned.
# *(justified 2026-09-12 from figures already in the repo — nothing new sewn,
# nothing new measured for the number itself)*
EDGE_CAP_BUDGET_PCT = 40.0

# What a bill over that ceiling DOES. "warn" is the shipped behaviour and
# moves no stitch — the plan is exactly the plan it was, plus one loud
# warning. "drop" refuses the cap outright on that design. The refusal is
# opt-in because `cfg.edge_cap` is default ON in front of customers and a
# ceiling that silently deletes a pass is a second silent behaviour to debug,
# not a fix for the first. Anything unrecognised reads as "warn".
EDGE_CAP_OVER_BUDGET_ACTIONS = ("warn", "drop")


def _fill_cracks(geom, width: float) -> tuple[object, int]:
    """`geom` with every interior the column cannot stand in filled.
    -> (geometry, how many were filled).

    A hole is an edge only if a `width`-wide column fits inside it —
    `Polygon(ring).buffer(-width / 2)` survives. Anything thinner is a crack
    between two polygons that nearly share an edge, not bare fabric a person
    would see, and outlining it lays a full column on EACH side of nothing.
    Judged on the interior's own width, never its perimeter: a crack is long
    and thin, which is exactly the shape a perimeter floor waves through.

    Hands back the SAME object when nothing is filled, so a silhouette
    without cracks reaches the emitters byte-identical to before this
    existed. Part order is `_parts`' own, which both emitters re-apply, so
    rebuilding changes nothing about which edge sews first.
    """
    parts = _parts(geom)
    if not parts:
        return geom, 0
    filled = 0
    out: list[Polygon] = []
    for part in parts:
        keep = [ring for ring in part.interiors
                if not Polygon(ring).buffer(-width / 2.0).is_empty]
        filled += len(part.interiors) - len(keep)
        out.append(part if len(keep) == len(part.interiors)
                   else Polygon(part.exterior, keep))
    if filled == 0:
        return geom, 0
    if len(out) == 1:
        return out[0], filled
    from shapely.geometry import MultiPolygon
    return MultiPolygon(out), filled


def silhouette_cap(silhouette, shape_id: str, *, style: str,
                   entry: tuple[float, float] | None,
                   trim_at_mm: float,
                   width_mm: float | None = None,
                   omit=None) -> tuple[list[StitchRun], dict]:
    """Close the DESIGN's outer edge — one cap on the whole silhouette.

    The two tiers below already outline a SHAPE. This outlines the union of
    them: the boundary between the design and bare fabric, where a tatami
    row simply stops and nothing holds its end. That edge belongs to no
    single shape, so no per-shape border can reach it (`border_runs` draws
    on one region's visible geometry; several regions share the silhouette),
    which is why this is a design-level pass rather than another rung on
    stitch_one's ladder.

    Both styles are the engine's own emitters on new geometry, not new
    geometry code:

    - "bean" -> `run_outline`. Traces the ring exactly, three passes at
      0.73 mm stations. Locks the row ends and reads as a drawn line
      without adding a column's visual weight. NOT a single walking pass —
      the run tier is bean-based and there is no lighter emitter here.
    - "satin" -> `border_runs(style="auto")`. A column just inside the
      edge, the same treatment a bordered shape gets, so it covers the row
      ends outright rather than pinning them. Falls back to its own bean
      lightening wherever the silhouette is too narrow to host a column —
      that fallback is `border_runs`' contract and is reported as
      `bean_loops`, not silently.

    Interior holes of the silhouette are capped too: a hole's edge is bare
    fabric on the same terms as the outer boundary, and both emitters walk
    exterior and interiors alike — PROVIDED the hole is wide enough to be an
    edge. The silhouette is a `unary_union` of neighbouring fills' polygons,
    and that union carries hairline cracks wherever two neighbours' edges
    nearly coincide: Kent's Instagram icon at 80 mm has 20 of them, 0.0-0.1
    mm wide and up to 7.7 mm long, owned by no region at all. The loop gate
    downstream is a PERIMETER floor (`BORDER_MIN_LOOP_MM`), which a long
    crack clears easily, and a hole's crosses are cast outward into the host,
    so they always fit — the satin emitter rang one crack as an 89-cross,
    3.4 mm-wide bar down the middle of the design (Kent, 2026-09-08, "why
    would the satin border ever leave the infill perimeter?"). So before
    either emitter sees a ring, `_fill_cracks` drops every interior the
    column cannot stand in: the ruler is the column width itself, no new
    constant. A real hole — a counter, a donut's inside — survives untouched.

    `omit` IS THE GATE, and it is the difference between a cap and a tax
    (Kent's call 2026-09-11, on item 14's measurement). Without it this pass
    caps the whole outline whether or not anything already covers it, and the
    bill measured across six fixtures was **+8.6% to +100.4% stitches** — with
    Hotel Fremont, already 0.0% uncovered because its own satin border closes
    it, paying +8.6% for nothing, and `enthusiast_logo`, which is satin
    lettering with no area fill at all, paying the most on the sheet. Handed
    the linear stitching this design has ALREADY laid, both emitters drop the
    samples standing on it and sew only the stretches genuinely ending in open
    air. No new constant: the arc floor is `_ARC_MIN_MM` (the column's own
    width) and the tolerance is `_OMIT_TOL_MM`, both already here.

    -> (runs, report). Report keys are the union of both tiers' own, so a
    caller reads one shape regardless of style: `loops`, `bean_loops`,
    `jumps`, `empty`, plus `style` (what actually ran), `holes_skipped`
    (cracks filled before capping), `arcs`/`yielded` (what the gate cut) and
    `whole_loops` (rings capped as a complete circuit — see below).
    """
    report = {"loops": 0, "bean_loops": 0, "jumps": 0, "empty": True,
              "style": "none", "holes_skipped": 0, "arcs": 0, "yielded": 0,
              "whole_loops": 0}
    if silhouette is None or style not in ("bean", "satin"):
        return [], report
    if getattr(silhouette, "is_empty", True):
        return [], report

    width = machine.BORDER_WIDTH_MM if width_mm is None else float(width_mm)
    silhouette, report["holes_skipped"] = _fill_cracks(silhouette, width)

    if style == "bean":
        runs, r = run_outline(silhouette, shape_id, entry=entry,
                              trim_at_mm=trim_at_mm, omit=omit)
        report["loops"] = r["loops"]
    else:
        runs, r = border_runs(silhouette, shape_id, entry=entry,
                              trim_at_mm=trim_at_mm, style="auto",
                              width_mm=width_mm, omit=omit)
        report["loops"] = r["loops"]
        report["bean_loops"] = r["bean_loops"]
    # `border_runs` splits its count by tier (`arcs` / `bean_arcs`); the cap
    # reports one number, because a caller asking "how much of the outline
    # was already covered" does not care which emitter drew the rest.
    report["arcs"] = r.get("arcs", 0) + r.get("bean_arcs", 0)
    report["yielded"] = r.get("yielded", 0)
    # How many RINGS the cap went around, which is not what either tier's
    # own `loops` counts. `run_outline` increments `loops` once per emitted
    # RUN — one per whole ring when the gate leaves it alone, one per ARC
    # when the gate splits it — so its `loops` FALLS as the gate cuts less
    # and rises as it cuts more (becker 18 -> 25 -> 16 across 80/90/95.7 mm
    # while the bill went +18% -> +26% -> +57%). `border_runs` counts whole
    # circuits only and puts arcs in `arcs`/`bean_arcs`, so an all-arc satin
    # cap reports zero. Neither is "how fragmented is this silhouette",
    # which is the question stage 7's `edges` field claims to answer.
    #
    # Identity this rests on: a ring either survives whole or is counted
    # once in `yielded`, and a ring under the tier's own length floor is
    # skipped before `omit` is consulted at all — so
    # `whole_loops + yielded` equals the loop count the SAME geometry emits
    # with no `omit` whatsoever. Verified on becker across 80/88/95.7/100/110
    # mm (16/16/17/17/17 both ways) and on drone/fremont/whitebg/gaulke/
    # enthusiast in both styles at 80 mm. *(measured 2026-09-12)*
    report["whole_loops"] = (report["loops"] - report["arcs"] if style == "bean"
                             else report["loops"] + report["bean_loops"])
    report["jumps"] = r["jumps"]
    report["empty"] = not runs
    report["style"] = style
    return runs, report


def run_outline(poly, shape_id: str, *, entry: tuple[float, float] | None,
                trim_at_mm: float, omit=None) -> tuple[list[StitchRun], dict]:
    """The run tier: a shape too small to fill or satin, sewn as bean runs on
    its own outline instead of being dropped.

    Same light tier the border falls back to, on different geometry. The
    border's bean rides an inset spine because it stands in for a column over
    a fill's edge; here there is no fill — the outline IS the artwork — so the
    run traces the ring exactly, and on the artwork polygon rather than the
    pull-compensated one (a run lays single lines of thread that do not pull
    fabric, and growing a 0.26 mm stroke by 0.3 mm of compensation would sew
    it at twice its own weight). At rescue sizes the two sides of a stroke sit
    closer together than the thread is wide, so the traced outline reads as a
    solid monoline glyph — which is exactly how run lettering should read, and
    how the benchmark subline renders.

    No corner rounding and no short-stitch guard: a bean run has no rails to
    fold and no density to hold, so corners are simply sewn through (law 12).
    A ring shorter than `RUN_MIN_LOOP_MM` is skipped — under three bean
    stations the needle is re-entering its own holes.

    `omit`, when given, is the part of this outline something already sewn
    covers — `border_runs`' own parameter, on this tier. A ring that loses a
    stretch to it sews as open arcs instead of a circuit, each its own run,
    and a ring covered end to end sews nothing. The silhouette cap is its
    caller: measured 2026-09-11, capping a design's WHOLE outline bills
    +8.6% to +100.4% stitches, and two of six fixtures were paying for an
    edge already closed by their own satin (`tools/pro_silhouette.py`).

    Report keys: `loops`, `jumps`, `empty` (plus `too_thin`, always False,
    so stage 7 can treat every tier's report identically), and `arcs` /
    `yielded` when `omit` split a ring.
    """
    report = {"loops": 0, "jumps": 0, "empty": True, "too_thin": False,
              "arcs": 0, "yielded": 0}
    runs: list[StitchRun] = []
    cursor = entry
    omit_prep = None
    if omit is not None and not getattr(omit, "is_empty", True):
        omit_prep = prep(omit.buffer(_OMIT_TOL_MM))
    for part in _parts(poly):
        for ring in [part.exterior, *part.interiors]:
            coords = list(ring.coords)
            length = LineString(coords).length
            if length < machine.RUN_MIN_LOOP_MM:
                continue           # smaller than the mark the thread makes
            n = max(3, int(round(length / machine.BEAN_STITCH_MM)))
            ring_pts, _total = _ring_arc_samples(coords, n)
            if not ring_pts:
                continue
            if omit_prep is None:
                arcs, whole = [ring_pts], True
            else:
                # This tier's samples ARE the edge (the outline is the
                # artwork, see above), so no `edge` argument — unlike the
                # border's bean, which rides an inset spine.
                arcs, whole = _ring_arcs(ring_pts, omit_prep, None)
                if not whole:
                    report["yielded"] += 1
            for arc in arcs:
                if whole:
                    pts = _bean_loop(ring_pts, cursor, machine.BEAN_STITCH_MM,
                                     machine.BEAN_PASSES)
                else:
                    if len(arc) < 2 or LineString(arc).length < _ARC_MIN_MM:
                        continue       # a blob, not an edge
                    pts = _bean_arc(arc, cursor, machine.BEAN_PASSES)
                    report["arcs"] += 1
                if len(pts) < 2:
                    continue
            # A rescued shape is thread-width scaled: there is no interior for
            # a travel run to hide in, so a hop between its rings gets the
            # plain jump-or-trim call, no bridging. Only BETWEEN rings: the
            # hop from the previous shape into this one is the sequence
            # loop's decision, exactly as it is for a fill — booking it here
            # too double-counted every rescued shape's entry as a lifted
            # thread (measured on the benchmark: 13 phantom jumps warned).
                jump = trim = False
                if runs and cursor is not None:
                    d = math.dist(cursor, pts[0])
                    if d >= machine.TINY_STITCH_MM:
                        jump = True
                        trim = d > trim_at_mm
                        report["jumps"] += 1
                # `stitches.RUN`, not BEAN: same technique, different tier.
                # The kind records WHY the run exists, and "border off
                # changes nothing" must stay checkable with the rescue
                # active.
                runs.append(StitchRun(points=stitches.split_long_moves(pts),
                                      kind=stitches.RUN, jump=jump, trim=trim,
                                      shape_id=shape_id))
                cursor = pts[-1]
                report["loops"] += 1
    report["empty"] = not runs
    return runs, report
