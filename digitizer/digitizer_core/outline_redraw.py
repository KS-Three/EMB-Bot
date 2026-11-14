"""Outline redraw: every traced shape's rings refit to straight lines and
circular arcs, moving nothing further than a fraction of the SOURCE pixel --
the pen-tool redraw a digitizer does by hand, for every shape, not only
lettering.

Built 2026-11-13 behind `PipelineConfig.outline_redraw_k` (built None, OFF:
the module is imported inside the flag's branch, so off nothing here runs and
the output is byte-identical); 0.75 since 2026-11-14 by Kent's flip ("Set
0.75"). A source stage 1 did not upscale still comes through untouched. Diagnosis and proof:
`docs/jag-source-2026-11-13.md`.

## Why

Kent's most-pinned fault is edges that should be smooth or straight. Traced
spot by spot (`tools/jag_strips.py`), the jag enters in two places before a
stitch is planned:

1. **The source's own pixels** on a low-resolution upload (Becker at 102 mm
   is 1.42 px/mm, 0.70 mm a pixel): the mask is a staircase, the native read
   leaves a stair of short chords and kinks, and the satin border sews every
   step.
2. **Douglas-Peucker's chords** on a clean upload (lettering at 22 px/mm): the
   mask is a smooth arc, but stage 4 writes it back as chords 0.6-3 mm long
   whose corners (12-20 degrees each) the satin follows and the eye reads as
   facets.

The pro redraws both by hand as clean curves and straight runs. So does this,
for (1) by default. For (2) only with `cfg.outline_redraw_native`: measured
2026-11-13, the bowls' polygons came out as true arcs but the Column lane's
satin answered them unpredictably, so a clean upload is left byte-identical
unless that is set.

## How it differs from what was measured before

- DOCTRINE "Smoothing region polygons ... NO EFFECT" (2026-08-25) blurred
  polygons with a Gaussian of a fixed radius in mm and scored the result on a
  raggedness number that turned out to be macro sprawl. Nothing here blurs:
  each run of the trace is REPLACED by the one line or one circle that
  explains it within the cap, and a corner between two lines is their exact
  intersection, so corners get sharper, not rounder. The cap is a raster
  quantity of the source (`k` source pixels), not a radius in mm; and the
  result is checked at the spots Kent pinned, not on a whole-design number.
- `letterform_priors` (ON at 0.75 since 2026-10-07) does this for text-tagged
  letters only, and only on an upload stage 1 upscaled. Its geometry is
  reused verbatim (`primitives_of`, `_rebuild`, the cap check); its word
  prior (stem / width / baseline snaps) is not -- a logo's border has no word.
- `coverage_edges` (the 2026-10-10 research's first-ranked iso-contour, built
  as PR #818) was ruled no by Kent 2026-10-12: it narrowed counters. This
  pass moves no edge further than the cap from the stage-4 trace and refuses
  any ring whose hole count or validity changes.

No physical constant: the cap is `k` times the source pixel (a raster
quantity), the arc rules are `letterform_priors`'.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from . import deadline
from .letterform_priors import (MIN_ARC_CHORDS, Prim, RingFit, _cap_check, _chords_of,
                                _drop_chamfers, _initial_lines, _invalid_point, _merge_arcs,
                                _offenders, _rebuild, _samples_of, _try_arc, _try_line,
                                densify_ring, dp_closed, sample_step)

K_DEFAULT = 0.75


# An arc may need a few more chords than a failed one had to reach its
# minimum sweep (`letterform_priors.MIN_ARC_SWEEP_DEG`): a run keeps extending
# past this many consecutive misses before it gives up.
_RUN_MISSES = 2


def _merge_runs(S: np.ndarray, prims: list[Prim], tol: float, rmin: float,
                rmax: float) -> list[Prim]:
    """Consecutive chords one straight line -- or, failing that, one circle
    -- explains within `tol` become that primitive, WHATEVER the sign of
    their turns. A source staircase turns left, right, left:
    `letterform_priors._merge_arcs` stops at the first sign change (right
    for a letter's bowl, wrong for a 0.7 mm-pixel border), and Douglas-
    Peucker splits wherever the endpoint chord misses a stair by more than
    the cap even when a fitted line holds every stair. A line is tried first
    at every length (straight runs stay straight); the longest run that one
    primitive explains wins. Greedy from the longest chord, so a run never
    starts inside a corner's neighbourhood. Every sample must sit within the
    cap of the ONE primitive, so a corner sharper than the cap is never
    absorbed."""
    n = len(prims)
    if n < 3:
        return prims
    start = max(range(n), key=lambda i: prims[i].length)
    order = [(start + i) % n for i in range(n)]
    out: list[Prim] = []
    pos = 0
    while pos < n:
        p = prims[order[pos]]
        best, used = p, 1
        misses = 0
        for extra in range(1, n):
            if pos + extra >= n:
                break
            q = prims[order[pos + extra]]
            if q.kind != "line":
                break
            cand = _try_line(S, p.i0, q.i1, tol)
            if cand is None and extra + 1 >= MIN_ARC_CHORDS:
                cand = _try_arc(S, p.i0, q.i1, tol, rmin, rmax)
            if cand is None:
                misses += 1
                if misses > _RUN_MISSES:
                    break
                continue
            misses = 0
            best, used = cand, extra + 1
        out.append(best)
        pos += used
    return out


def primitives_plain(S: np.ndarray, tol: float) -> list[Prim]:
    """`letterform_priors.primitives_of` with runs merged across a staircase
    first: chords -> line/arc runs -> chamfers dropped -> arcs. An arc's
    radius is bounded as there: at least 2 caps, at most the ring's extent."""
    prims = _initial_lines(S, dp_closed(S, tol))
    extent = float(np.hypot(*(S.max(axis=0) - S.min(axis=0))))
    prims = _merge_runs(S, prims, tol, rmin=2.0 * tol, rmax=extent)
    prims = _drop_chamfers(S, prims, tol, 2.0 * tol)
    return _merge_arcs(S, prims, tol, rmin=2.0 * tol, rmax=extent)


def fit_ring_plain(coords: np.ndarray, tol: float) -> RingFit:
    """`letterform_priors.fit_ring` with no word prior: chords -> straight
    runs -> chamfers dropped -> runs merged into one line or one arc ->
    rebuilt; a primitive that breaks the cap is softened to its chords, then
    put back verbatim."""
    S = densify_ring(coords, sample_step(tol))
    length = float(LineString(np.vstack([S, S[:1]])).length)
    prims = primitives_plain(S, tol)
    lmin = 2.0 * tol
    unexplained = 0.0
    for p in prims:
        if p.kind == "line" and p.length < lmin:
            p.kind = "pass"
            unexplained += p.length
    R, own = _rebuild(S, prims, tol)
    bad = _offenders(S, prims, R, own, tol)
    if bad:
        soft = []
        for k, p in enumerate(prims):
            if k in bad and p.kind in ("line", "arc"):
                soft += _chords_of(S, p.i0, p.i1, tol)
            else:
                soft.append(p)
        prims = soft
        R, own = _rebuild(S, prims, tol)
        bad = _offenders(S, prims, R, own, tol)
        for k in bad:
            p = prims[k]
            p.kind = "pass"
            unexplained += float(LineString(_samples_of(S, p.i0, p.i1)).length)
        if bad:
            R, own = _rebuild(S, prims, tol)
    return RingFit(prims=prims, coords=R, unexplained_mm=unexplained, length_mm=length, S=S, own=own)


_CAP_REPAIR_ROUNDS = 6


def _revert_near(fit: RingFit, pt: np.ndarray, radius: float, tol: float) -> bool:
    """`RingFit.revert_near`, widened: when only pass-through pieces wrote
    the vertices near `pt`, the breach is a NEIGHBOUR's -- `_rebuild` moves a
    line's or an arc's end onto the pass piece's endpoint -- so the
    primitives either side of those pieces go back to the trace."""
    if fit.revert_near(pt, radius, tol):
        return True
    if fit.S is None or fit.own is None:
        return False
    near = np.hypot(*(fit.coords[:-1] - pt).T) <= radius
    n = len(fit.prims)
    hit = set()
    for k in {int(k) for k in fit.own[near]}:
        for j in ((k - 1) % n, (k + 1) % n):
            if fit.prims[j].kind != "pass":
                hit.add(j)
    if not hit:
        return False
    for j in hit:
        p = fit.prims[j]
        p.kind = "pass"
        fit.unexplained_mm += float(LineString(_samples_of(fit.S, p.i0, p.i1)).length)
    fit.coords, fit.own = _rebuild(fit.S, fit.prims, tol)
    return True


def _worst_breach(src_rings, out_rings, tol: float, step: float):
    """The rebuilt-ring point furthest past the cap from its source ring (or
    the source point furthest from the rebuilt ring), or None when every
    sampled point is within it. Same sampling as `_cap_check`."""
    worst, where = tol * (1.0 + 1e-6), None
    for A, B in zip(src_rings, out_rings):
        la, lb = LineString(A), LineString(B)
        for P, other in ((densify_ring(B, step), la), (densify_ring(A, step), lb)):
            for q in P:
                d = other.distance(Point(q))
                if d > worst:
                    worst, where = d, np.asarray(q, float)
    return where


def _vertex_samples(coords: np.ndarray, step: float) -> np.ndarray:
    """Where each of the ring's own vertices sits among `densify_ring`'s
    samples (it keeps every vertex and adds points between them), by the same
    arithmetic."""
    P = np.asarray(coords, float)
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        P = P[:-1]
    idx, k, n = [], 0, len(P)
    for i in range(n):
        d = float(np.hypot(*(P[(i + 1) % n] - P[i])))
        idx.append(k)
        k += max(1, int(math.ceil(d / step))) if step > 0 else 1
    return np.asarray(idx)


def _arcs_only(fit: RingFit, coords: np.ndarray, step: float) -> np.ndarray:
    """The ring's OWN vertices, with each run an arc explains replaced by that
    arc and nothing else touched: straight runs and corners stay exactly as
    stage 4 traced them. The arc's ends are the trace's own points (within
    the cap of the circle by the fit), its inside the circle written finely.
    Sets `fit.own` to the arc each written vertex belongs to (-1: the trace)
    for the cap repair."""
    from .letterform_priors import arc_points
    S, n = fit.S, len(fit.S)
    P = np.asarray(coords, float)
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        P = P[:-1]
    vidx = _vertex_samples(coords, step)
    arcs = [(k, p) for k, p in enumerate(fit.prims) if p.kind == "arc"]
    if not arcs:
        fit.own = np.full(len(P), -1)
        return np.vstack([P, P[:1]])
    vertex_at = {int(i): P[j] for j, i in enumerate(vidx)}
    arc_from = {p.i0: (k, p) for k, p in arcs}
    out: list[np.ndarray] = []
    own: list[int] = []
    i, walked = arcs[0][1].i0, 0
    while walked < n:
        if i in arc_from:
            k, p = arc_from[i]
            a0 = math.atan2(S[p.i0][1] - p.c[1], S[p.i0][0] - p.c[0])
            a1 = math.atan2(S[p.i1][1] - p.c[1], S[p.i1][0] - p.c[0])
            inner = arc_points(p.c, p.r, a0, a1, p.ccw)[1:-1]
            out.append(S[p.i0])
            own.append(k)
            out.extend(inner)
            own += [k] * len(inner)
            span = (p.i1 - p.i0) % n
            if span == 0:
                break
            i, walked = p.i1, walked + span
            continue
        if i in vertex_at:
            out.append(vertex_at[i])
            own.append(-1)
        i, walked = (i + 1) % n, walked + 1
    R = np.vstack(out)
    keep = np.ones(len(R), bool)
    keep[1:] = np.hypot(*(R[1:] - R[:-1]).T) > 1e-9
    R, own_a = R[keep], np.asarray(own)[keep]
    fit.own = own_a
    return np.vstack([R, R[:1]])


def _revert_arc_near(fit: RingFit, pt: np.ndarray, radius: float) -> bool:
    """Arcs-only repair: the arcs that wrote a vertex near `pt` go back to the
    trace (the trace's own vertices are never the breach)."""
    near = np.hypot(*(fit.coords[:-1] - pt).T) <= radius
    hit = {int(k) for k in fit.own[near] if k >= 0}
    for k in hit:
        fit.prims[k].kind = "pass"
    return bool(hit)


def redraw_polygon(poly: Polygon, tol: float, arcs_only: bool = False) -> tuple[Polygon, str]:
    """-> (polygon, outcome). Outcome "redrawn" or a refusal reason; on a
    refusal the input polygon comes back untouched. Never raises.

    `arcs_only` (a source at its own resolution, `apply_outline_redraw`):
    the trace's straight runs and corners are kept vertex for vertex and only
    the runs one circle explains are rewritten, so a clean upload's straight
    edges, corners and every shape with no bowl come through byte-identical."""
    if poly.is_empty or not poly.is_valid or poly.geom_type != "Polygon":
        return poly, "invalid-input"
    src = [np.asarray(poly.exterior.coords, float)] + [np.asarray(h.coords, float) for h in poly.interiors]
    step = sample_step(tol)
    try:
        fits = [fit_ring_plain(r, tol) for r in src]
    except Exception as e:                                       # noqa: BLE001
        return poly, f"error:{type(e).__name__}"
    if arcs_only:
        if not any(p.kind == "arc" for f in fits for p in f.prims):
            return poly, "no-arc"
        return _redraw_arcs_only(poly, src, fits, tol, step)

    def assemble():
        rings = [f.coords for f in fits]
        try:
            return rings, Polygon(rings[0], rings[1:])
        except Exception:                                        # noqa: BLE001
            return rings, None

    rings, new = assemble()
    for _round in range(3):
        if new is not None and new.is_valid and not new.is_empty and new.geom_type == "Polygon":
            break
        pt = _invalid_point(new) if new is not None else None
        if pt is None:
            break
        if not any(f.revert_near(pt, 2.0 * tol, tol) for f in fits):
            break
        rings, new = assemble()
    if new is None or new.is_empty or not new.is_valid or new.geom_type != "Polygon":
        return poly, "invalid"
    if len(new.interiors) != len(poly.interiors):
        return poly, "holes"
    # The cap, both ways. A breach is repaired where it is -- the primitives
    # that wrote the rebuilt ring near it go back to the trace -- before the
    # whole shape is refused: one arc's junction must not cost a border its
    # every straight run.
    for _round in range(_CAP_REPAIR_ROUNDS):
        breach = _worst_breach(src, rings, tol, step)
        if breach is None:
            break
        if not any(_revert_near(f, breach, 2.0 * tol, tol) for f in fits):
            break
        rings, new = assemble()
        if new is None or new.is_empty or not new.is_valid or new.geom_type != "Polygon":
            return poly, "invalid"
    mx, _p95 = _cap_check(src, rings, tol, step)
    if mx > tol * (1.0 + 1e-6):
        return poly, "cap"
    if not any(p.kind in ("line", "arc") for f in fits for p in f.prims):
        return poly, "unexplained"
    return new, "redrawn"


def _redraw_arcs_only(poly: Polygon, src: list[np.ndarray], fits: list[RingFit], tol: float,
                      step: float) -> tuple[Polygon, str]:
    def assemble():
        rings = [_arcs_only(f, s, step) for f, s in zip(fits, src)]
        for f, r in zip(fits, rings):
            f.coords = r
        try:
            return rings, Polygon(rings[0], rings[1:])
        except Exception:                                        # noqa: BLE001
            return rings, None

    def ok(g):
        return g is not None and g.is_valid and not g.is_empty and g.geom_type == "Polygon"

    rings, new = assemble()
    for _round in range(_CAP_REPAIR_ROUNDS):
        if ok(new):
            breach = _worst_breach(src, rings, tol, step)
        else:
            breach = _invalid_point(new) if new is not None else None
        if breach is None:
            break
        if not any(_revert_arc_near(f, breach, 2.0 * tol) for f in fits):
            break
        rings, new = assemble()
    if not ok(new):
        return poly, "invalid"
    if len(new.interiors) != len(poly.interiors):
        return poly, "holes"
    if not any(p.kind == "arc" for f in fits for p in f.prims):
        return poly, "no-arc"
    mx, _p95 = _cap_check(src, rings, tol, step)
    if mx > tol * (1.0 + 1e-6):
        return poly, "cap"
    return new, "redrawn"


def redraw_cap_mm(src_px_mm: float, grid_px_mm: float, k: float = K_DEFAULT) -> float:
    """How far the redraw may move an edge: `k` SOURCE pixels, and never less
    than one working-grid pixel. On an upload stage 1 upscaled the source
    pixel governs (Becker at 102 mm: 0.75 x 0.70 = 0.53 mm). On a clean
    upload at its own resolution the grid pixel does: stage 4's curve
    refinement already lets a chord sit a whole grid pixel off the arc
    (`stage4_vectorize._refine_curves`' floor), so a cap under that could
    not lift the facets that floor leaves (lettering at 22 px/mm: 0.034 mm
    fitted some bowls as arcs and left most as chords; 0.046 fitted all)."""
    return max(float(k) * float(src_px_mm), float(grid_px_mm))


def redraws_lines(src_px_mm: float, grid_px_mm: float, k: float = K_DEFAULT) -> bool:
    """True on an upload stage 1 UPSCALED (its source pixel is larger than
    the working grid's -- the same test as `stage4_vectorize`'s `upscaled`):
    stage 1 judged it under the engine's resolution floor and its trace is a
    staircase of source pixels, so straight runs are redrawn too. False on a
    source at its own resolution: only arcs (`redraw_polygon(arcs_only=True)`).
    `k` is not read; the signature matches `redraw_cap_mm`. MFab at 105 mm
    (3.85 px/mm, x1.04 to 4.0) is upscaled although 0.75 of its pixel is
    under the grid's, and its 0.26 mm stairs are what Kent pinned."""
    return float(src_px_mm) > float(grid_px_mm) * (1.0 + 1e-6)


def apply_outline_redraw(regions, src_px_mm: float, grid_px_mm: float,
                         k: float = K_DEFAULT, native: bool = False) -> dict[str, int]:
    """Refit every region's polygon in place (same `shape_id`, `meta` plus
    `outline_redraw` naming the outcome). A letter `letterform_priors` already
    refit is left as it is. Returns outcome counts.

    Two regimes, by `redraws_lines`: on an upload stage 1 upscaled (k source
    pixels over the grid pixel) the trace is a staircase of source pixels and
    every run is redrawn, lines and arcs; on a source at its own resolution
    the trace already carries straight edges and corners to the grid pixel,
    and only its bowls -- chords of a curve -- are rewritten as arcs.

    The second regime runs only with `native` (`cfg.outline_redraw_native`,
    default False): measured 2026-11-13 it rounds the polygon's bowls but the
    Column lane's satin answers the new polygon unpredictably (and_pizza's "p"
    sewed a straight cut across a perfect arc and opened a seam), so the
    stitched edge did not reliably improve. Without it a source at its own
    resolution passes through untouched: nothing runs, nothing is stamped."""
    tol = redraw_cap_mm(src_px_mm, grid_px_mm, k)
    arcs_only = not redraws_lines(src_px_mm, grid_px_mm, k)
    counts: dict[str, int] = {}
    if not tol > 0.0 or (arcs_only and not native):
        return counts
    for r in regions:
        deadline.check("outline redraw")
        if r.meta.get("letterform_prior") == "refit":
            outcome = "letterform"
        else:
            new, outcome = redraw_polygon(r.polygon, tol, arcs_only=arcs_only)
            if outcome == "redrawn":
                r.polygon = new
                r.area_mm2 = float(new.area)
        r.meta["outline_redraw"] = outcome
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts
