"""Thread chart access: Lab-space nearest matching and snap-with-merge.

Color-space convention (PINNED — see plan doc): all color math runs in
CIELAB as produced by skimage.color.rgb2lab on float RGB in [0, 1] — i.e.
true CIELAB ranges (L 0-100, a/b roughly -128..127). cv2's 8-bit Lab
(scaled 0-255) is never mixed in; anything arriving as cv2 Lab must be
converted back to RGB first.

Two different distances, deliberately:
  * **Spool snapping uses CIEDE2000** — the perceptual standard. Measured
    during step-1 development: plain CIE76 matched a dark navy (20,40,90) to
    a GREY thread ("Concord Fog"), because Euclidean Lab distance is a poor
    perceptual model in dark saturated regions. CIEDE2000 picks "Midnight
    Blue". The operator buys the cone this function names, so this is a
    quality-critical path, and the cost is trivial (a dozen cluster colors
    against ~400 threads).
  * **Cluster merging and the anti-alias blend test use Euclidean Lab**
    (stage 2) — those need a metric geometry to project onto a line between
    two colors, which CIEDE2000 does not provide.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from .threads_isacord import ISACORD


@dataclass(frozen=True)
class Thread:
    number: str
    name: str
    rgb: tuple[int, int, int]


CHART: list[Thread] = [Thread(number, name, rgb) for number, name, rgb in ISACORD]

# Precomputed Lab for the whole chart (chart is static; one conversion).
_CHART_LAB: np.ndarray = rgb2lab(
    np.array([t.rgb for t in CHART], dtype=np.float64).reshape(1, -1, 3) / 255.0
).reshape(-1, 3)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(N,3) uint8/float RGB (0-255) -> (N,3) float CIELAB."""
    arr = np.asarray(rgb, dtype=np.float64).reshape(1, -1, 3) / 255.0
    return rgb2lab(arr).reshape(-1, 3)


def nearest_thread_index(lab: np.ndarray) -> int:
    """Index into CHART of the perceptually nearest (CIEDE2000) thread.

    Ties resolve to the lower chart index (argmin), which is deterministic
    because CHART is a fixed, sorted list.
    """
    ref = np.repeat(np.asarray(lab, dtype=np.float64).reshape(1, 3), len(_CHART_LAB), axis=0)
    return int(np.argmin(deltaE_ciede2000(ref, _CHART_LAB)))


def snap_palette(cluster_rgbs: np.ndarray) -> list[int]:
    """Snap each cluster color (N,3 RGB 0-255) to a chart index.

    Returns one chart index per cluster, in cluster order. Merging clusters
    that land on the same spool is the CALLER's job (stage 2) because it must
    also remap the label image.
    """
    labs = rgb_to_lab(cluster_rgbs)
    return [nearest_thread_index(lab) for lab in labs]
