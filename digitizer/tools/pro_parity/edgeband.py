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
