"""The widest-inscribed-bare-circle instrument — the DEFINITION of `starved`.

Mandated by `config.py`'s fill_technique block after the 2026-08-02 adversarial
pass on the contour tier: the tier's own bookkeeping (`skipped_area_mm2`)
charges only the rings it KNOWS it dropped, and the fabric inside the last
surviving ring — the bare core `buffer(-d, join_style=2)` annihilates on any
notched interior — is never a ring and never charged. An instrument that
trusted that ledger would inherit the same blindness, so this one trusts only
two things: the polygon, and the stitches that were actually emitted.

The measurement: the radius of the largest circle inscribable in the region of
the polygon further than half a thread width from any emitted stitch. That is
the physical question — "how big is the biggest patch of garment fabric the eye
will find inside this shape" — and it is a MAXIMUM, not an area sum, because a
hundred pinprick slivers along a boundary are invisible while one 3 mm disc in
the middle of a star is the whole defect.

Implementation is a rasterized exact-EDT pass (`shapefield.py` is the repo's
precedent for the conventions; this module deliberately does NOT share its
raster, because that one is pinned byte-for-byte to stage6_satin and this one
answers a different question at a different resolution):

    clearance(p) = min( dist(p, outside the polygon),
                        dist(p, nearest stitch centreline) - thread_w/2 )
    radius       = max over p inside the polygon of clearance(p)

Both distances are exact Euclidean distance transforms on one grid, so the
result is deterministic and accurate to about one pixel (0.03 mm at the
default 32 px/mm). Stitch centrelines are drawn with sub-pixel coordinates
(cv2 fixed-point shift) so a diagonal stitch does not stairstep its ribbon.

Every needle-DOWN run counts as thread — fill, underlay, travel, ties alike:
the question is what the fabric shows, not which tier put thread there.
Needle-UP moves (the jump/trim BETWEEN runs) put no thread on the fabric and
are correctly invisible here.

Validated against the 2026-08-02 adversarial pass's own figures before the
`starved` gate was re-pointed at it — see `tests/test_barecircle.py` for the
reproduction of the fixture logo's contour-vs-tatami gap (0.640 vs 0.090 mm)
and the 10-point star's annihilated core, and for the one cited figure that
did NOT survive re-measurement as written (the star's "2.94 mm bare disc"
reads as a diameter — the measured radius is 1.33-1.42 across every
reconstruction of that star; the test states both readings).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Polygon

from . import machine

# 32 px/mm = 0.03125 mm pixels: fine enough that the one-pixel EDT error is an
# order of magnitude under the 0.4 mm ring spacing the answer is judged
# against. The cap keeps a full-hoop shape from allocating a gigapixel — at the
# 200 mm hoop maximum the grid degrades to ~16 px/mm, still 0.06 mm pixels.
_PX_PER_MM = 32.0
_MAX_PX = 3200


@dataclass(frozen=True)
class BareCircle:
    """The widest bare spot: its radius, and where it is (mm, artwork space)."""

    radius_mm: float
    center: tuple[float, float]


def _needle_down_points(runs) -> list[list[tuple[float, float]]]:
    """Each run's polyline of needle-down penetrations. Every run in a stage-6
    emitter's output is needle-down thread (jumps are the gaps BETWEEN runs,
    flagged on the following run, never points inside one)."""
    return [list(r.points) for r in runs if len(r.points) >= 2]


def widest_bare_circle(
    poly: Polygon, runs, *,
    thread_w_mm: float = machine.COVERAGE_THREAD_W_MM,
    px_per_mm: float = _PX_PER_MM,
) -> BareCircle:
    """The largest circle inscribable in `poly` further than `thread_w_mm / 2`
    from every emitted stitch in `runs`.

    `runs` is a stage-6 emitter's output (any iterable of StitchRun-likes with
    `.points`); pass `[]` to measure the shape with no thread at all, which
    returns its plain inradius. Empty/degenerate polygons measure 0.0.
    """
    if poly is None or poly.is_empty or poly.area <= 0:
        return BareCircle(0.0, (0.0, 0.0))

    x0, y0, x1, y1 = poly.bounds
    dim = max(x1 - x0, y1 - y0)
    scale = min(px_per_mm, _MAX_PX / max(dim, 1e-6))
    w = int(math.ceil((x1 - x0) * scale)) + 4
    h = int(math.ceil((y1 - y0) * scale)) + 4
    ox, oy = x0 - 2 / scale, y0 - 2 / scale

    # The shape. Same fillPoly convention as shapefield.rasterize_polygon.
    mask = np.zeros((h, w), np.uint8)

    def to_px_int(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        return np.column_stack([(a[:, 0] - ox) * scale,
                                (a[:, 1] - oy) * scale]).astype(np.int32)

    polys = [poly] if poly.geom_type == "Polygon" else [
        g for g in poly.geoms if g.geom_type == "Polygon"]
    for p in polys:
        cv2.fillPoly(mask, [to_px_int(p.exterior.coords)], 255)
        for ring in p.interiors:
            cv2.fillPoly(mask, [to_px_int(ring.coords)], 0)
    if not mask.any():
        return BareCircle(0.0, (0.0, 0.0))

    # The thread: every needle-down centreline, drawn at 1/8-pixel precision.
    shift = 3
    q = float(1 << shift)
    thread = np.zeros((h, w), np.uint8)
    for pts in _needle_down_points(runs):
        a = np.asarray(pts, np.float64)
        px = np.column_stack([(a[:, 0] - ox) * scale * q,
                              (a[:, 1] - oy) * scale * q])
        cv2.polylines(thread, [np.round(px).astype(np.int32)],
                      isClosed=False, color=255, thickness=1, shift=shift)

    # Two exact EDTs on the one grid. `distance_transform_edt` measures each
    # nonzero pixel's distance to the nearest zero, so the thread mask is
    # inverted to make stitches the zeros being measured to.
    dist_out = distance_transform_edt(mask > 0)
    if thread.any():
        dist_thread = distance_transform_edt(thread == 0)
        clearance = np.minimum(dist_out,
                               dist_thread - (thread_w_mm / 2.0) * scale)
    else:
        clearance = dist_out
    clearance[mask == 0] = 0.0

    idx = int(np.argmax(clearance))
    cy, cx = divmod(idx, w)
    r = float(clearance[cy, cx])
    if r <= 0.0:
        return BareCircle(0.0, (0.0, 0.0))
    return BareCircle(r / scale, (cx / scale + ox, cy / scale + oy))


def starved_threshold_mm(spacing_mm: float) -> float:
    """The widest bare radius a HEALTHY contour fill can leave, plus half a
    ring spacing of margin — the line past which `starved` fires.

    Two terms, both from the tier's own geometry:

      * `machine.CONTOUR_BARE_CORE_MM` (0.13, since the 2026-08-04 shrink —
        see that constant's comment for the terminal-refine + finishing-pass
        fix and its own before/after measurements) — the bare dot every
        healthy shape leaves at its own centre, MEASURED with this
        instrument at the shipped 0.40 mm spacing. The `(spacing -
        FILL_ROW_MM)` term carries the one part of that residue that scales
        with density — the gap between the dropped terminal ring and the
        last sewn one — so an opened-up ring tier is allowed a
        proportionally wider centre.
      * half a `spacing_mm` of margin: fire only when the core is at least
        one full ring spacing wider in DIAMETER than the structural dot,
        i.e. when a ring that geometrically had room to exist is MISSING.
        That is the "~one ring spacing" definition of starved, with the
        constants named.

    At the shipped 0.40 mm spacing the line sits at 0.33 mm (was 1.07 before
    the shrink — the formula and this docstring were both re-derived off the
    new `CONTOUR_BARE_CORE_MM`, not just the constant swapped in). Current
    calibration against measured ground truth (`tests/test_barecircle.py`
    reproduces all of these): tatami's worst bare spot on the fixture logo
    is 0.090 mm — still under this line but no longer an order of magnitude
    under it, since a healthy contour fixture is now close to tatami's own
    floor (discs 0.067-0.070 mm, dumbbell 0.129 mm — all comfortably silent).
    For history, the shapes the old area gate false-fired on (whitebg
    Sf5200f3f at 0.499 mm "cited as firing on 0.51", Sb253ebba at 0.644 mm,
    the dumbbell at its OLD 0.863 mm pre-shrink reading) are silent against
    either threshold. The 10-point star's annihilated core — still the
    worst case even after the shrink, because a notched interior the
    mitred offset annihilates outright is a different failure mode than a
    healthy shape's structural dot — now measures 0.441 mm (was 1.33 mm
    pre-shrink) and still fires, at 34 % past the current 0.33 mm line.
    """
    return (machine.CONTOUR_BARE_CORE_MM
            + (spacing_mm - machine.FILL_ROW_MM)
            + spacing_mm / 2.0)
