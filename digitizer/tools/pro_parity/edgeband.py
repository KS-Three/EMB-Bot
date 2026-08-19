"""Edge coverage — how much of the band just inside a boundary carries no thread.

THE QUESTION. Along a shape's boundary, how much of the band just inside it has
no thread on it, and how does that compare to what a professional digitiser
leaves on the same artwork? Two numbers: the bare FRACTION of the band, and the
longest contiguous bare ARC along the boundary.

WHY THE ARC IS THE HEADLINE. Five percent of a band left bare as scattered
pinpricks is invisible; five percent as one 8 mm strip down the side of a letter
is the defect. `barecircle.py` makes exactly this argument for shape interiors
(:14-16) and then declines to make it for edges — its `clearance` is
`min(dist_out, dist_thread - w/2)` (:133-137), which caps any point's score at
its own distance from the boundary, so a continuous uncovered perimeter band is
indistinguishable from flawless work. This module answers the case that one
discounts. Nothing here supersedes it; they measure different failures.

WHY BOTH SIDES GO THROUGH ONE READER. `side_mask` delegates to
`artfidelity.pro_mask` for pro and ours alike. `prep_both.py` once hand-rolled a
second copy of a shared block and silently dropped three keys from it for weeks
(fixed 2026-08-18, 5328257); one rasteriser is how that does not happen here.

WHAT THIS DOES NOT DO. It sets no threshold. "How much bare edge is too much" is
a cloth question and ROADMAP gate 1 says cloth settles it, so the probe reports
millimetres at three band widths and lets the professional's own files be the
tolerance. It adds no key to the scorecard's WEIGHTS and changes no engine
behaviour.
"""
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artfidelity import RES  # noqa: E402

# Reported at all three, never one. Picking one would invent a physical
# constant; gate 1 says cloth settles those. Three widths also separate a thin
# uniform shortfall (visible at 0.2, washed out at 0.8) from a genuinely wide
# gap. At RES = 10 px/mm these are 2, 4 and 8 pixels.
BAND_WIDTHS_MM = (0.2, 0.4, 0.8)


def band_mask(shape: np.ndarray, w_px: float) -> np.ndarray:
    """Every pixel of `shape` within `w_px` of being outside it.

    Exact Euclidean, not a morphological erosion: a square structuring element
    measures Chebyshev distance, so a 4 px band would reach 5.7 px into a
    corner. `barecircle.py` uses the same EDT convention for the same reason.
    """
    if not shape.any():
        return np.zeros(shape.shape, bool)
    return shape & (distance_transform_edt(shape) <= w_px)


def bare_frac(band: np.ndarray, thread: np.ndarray) -> float | None:
    """Share of `band` with no thread on it, or None for an empty band.

    None rather than 0.0 deliberately: an empty band is a shape too small to
    measure, and 0.0 would read as "perfectly covered" in every table it
    reaches.
    """
    n = int(np.count_nonzero(band))
    if not n:
        return None
    return float(np.count_nonzero(band & ~thread) / n)


def _rings(shape: np.ndarray) -> list[np.ndarray]:
    """Every boundary ring of `shape` as an (N, 2) array of (row, col).

    `CHAIN_APPROX_NONE` because an arc length is a walk along real pixels — the
    simplified chain would drop the very pixels being measured. `RETR_CCOMP`
    returns holes as their own rings, and a hole's boundary is an edge like any
    other.
    """
    cs, _h = cv2.findContours(shape.astype(np.uint8), cv2.RETR_CCOMP,
                              cv2.CHAIN_APPROX_NONE)
    return [c.reshape(-1, 2)[:, ::-1] for c in cs if len(c) >= 2]


def _runs(flags: np.ndarray) -> list[list[int]]:
    """Maximal runs of True in a CLOSED sequence, as index lists.

    Rings close, so a run straddling index 0 is one run. Rotating the sequence
    to start at a False is what makes that fall out for free; an all-True ring
    has no False to rotate to and is returned whole.
    """
    n = len(flags)
    if not flags.any():
        return []
    if flags.all():
        return [list(range(n))]
    start = int(np.argmax(~flags))
    out, cur = [], []
    for k in range(n):
        i = (start + k) % n
        if flags[i]:
            cur.append(i)
        elif cur:
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def bare_arcs(shape: np.ndarray, thread: np.ndarray, w_px: float,
              res: float = RES) -> list[float]:
    """Lengths in mm of every maximal boundary run further than `w_px` from thread.

    A boundary pixel is bare when the nearest thread pixel is more than `w_px`
    away. Distance rather than an inward-normal probe: a normal is ambiguous at
    a corner and wherever a ring doubles back, and two implementations would
    disagree there. An exact EDT has no such freedom.

    A run's length is the distance walked BETWEEN its pixels, so a lone bare
    pixel measures 0.0 and a 30 px strip measures 29 steps of 0.1 mm. That is
    the span a strip of that length actually occupies; counting the step off its
    final pixel would add a pixel of length that is not there.
    """
    if not shape.any():
        return []
    dist = (distance_transform_edt(~thread) if thread.any()
            else np.full(shape.shape, np.inf))
    out: list[float] = []
    for ring in _rings(shape):
        bare = dist[ring[:, 0], ring[:, 1]] > w_px
        if not bare.any():
            continue
        step = np.hypot(*(np.roll(ring, -1, axis=0) - ring).T) / res
        for run in _runs(bare):
            out.append(float(step[run[:-1]].sum()) if len(run) > 1 else 0.0)
    return out
