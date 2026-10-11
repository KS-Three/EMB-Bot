"""Byte-identical fast paths for two scikit-image calls the pipeline makes
thousands of times per design.

Profiled 2026-10-08 over the six `testdata/art` logos at left-chest size
(89 mm): these two calls were the top hot spots by wall time.

`medial_axis` — skimage rebuilds a 512-entry lookup table on EVERY call,
two `ndimage.label` runs per entry (1,024 labels per call; ~3M per batch of
six logos). The table is a pure constant of the 3x3 neighbourhood, so it is
built once here and the rest of the function is skimage's own body verbatim,
calling the same Cython `_skeletonize_loop` with the same ordering and rng.

`deltaE_ciede2000_1` — skimage's `deltaE_ciede2000` on ONE colour pair, the
shape `stage2_photo_segment._weight_mean_color` calls ~100k times per photo.
Almost all of its cost was array setup on 1-element arrays. This is the same
formula, operation for operation and in the same order, on numpy float64
scalars: every transcendental and power still goes through the SAME numpy
ufunc (a 0-d input runs the same inner loop as a 1-element array), and the
remaining +, -, *, / and sqrt are IEEE-exact either way. So the result is the
same float, bit for bit — `tests/test_fast_skimage.py` checks both helpers
against skimage itself.

Both lean on skimage internals, which is why `scikit-image` is pinned in
`requirements.txt`; the tests are the tripwire for a version bump.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology._skeletonize import (
    _pattern_of,
    _skeletonize_loop,
    _table_lookup,
)

_eight_connect = ndi.generate_binary_structure(2, 2)


def _build_tables() -> tuple[np.ndarray, np.ndarray]:
    # Verbatim from skimage 0.26 `medial_axis` — see its comments there.
    center_is_foreground = (np.arange(512) & 2**4).astype(bool)
    table = (
        center_is_foreground
        & (
            np.array(
                [
                    ndi.label(_pattern_of(index), _eight_connect)[1]
                    != ndi.label(_pattern_of(index & ~(2**4)), _eight_connect)[1]
                    for index in range(512)
                ]
            )
            | np.array([np.sum(_pattern_of(index)) < 3 for index in range(512)])
        )
    )
    cornerness_table = np.array(
        [9 - np.sum(_pattern_of(index)) for index in range(512)]
    )
    # Left writable: the Cython loop takes a typed memoryview, which refuses
    # a read-only buffer. Nothing writes to either table.
    return np.ascontiguousarray(table, dtype=np.uint8), cornerness_table


_TABLE, _CORNERNESS = _build_tables()


def medial_axis(image, mask=None, return_distance=False, *, rng=None):
    """`skimage.morphology.medial_axis`, with its constant tables cached."""
    if mask is None:
        masked_image = image.astype(bool)
    else:
        masked_image = image.astype(bool).copy()
        masked_image[~mask] = False

    distance = ndi.distance_transform_edt(masked_image)
    if return_distance:
        store_distance = distance.copy()

    corner_score = _table_lookup(masked_image, _CORNERNESS)

    i, j = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    result = masked_image.copy()
    distance = distance[result]
    i = np.ascontiguousarray(i[result], dtype=np.intp)
    j = np.ascontiguousarray(j[result], dtype=np.intp)
    result = np.ascontiguousarray(result, np.uint8)

    generator = np.random.default_rng(rng)
    tiebreaker = generator.permutation(np.arange(masked_image.sum()))
    order = np.lexsort((tiebreaker, corner_score[masked_image], distance))
    order = np.ascontiguousarray(order, dtype=np.int32)

    _skeletonize_loop(result, i, j, order, _TABLE)

    result = result.astype(bool)
    if mask is not None:
        result[~mask] = image[~mask]
    if return_distance:
        return result, store_distance
    return result


_PI = np.float64(np.pi)
_TWO_PI = 2 * np.pi
_25_7 = np.float64(25**7)
_D30 = np.deg2rad(30)
_D6 = np.deg2rad(6)
_D63 = np.deg2rad(63)


def _cart2polar_2pi(x, y):
    r, t = np.hypot(x, y), np.arctan2(y, x)
    if t < 0.0:
        t = t + _TWO_PI
    else:
        t = t + 0  # mirrors skimage's `t += np.where(t < 0.0, 2*pi, 0)`
    return r, t


def deltaE_ciede2000_1(lab1, lab2) -> float:
    """skimage's `deltaE_ciede2000(lab1, lab2)` (kL = kC = kH = 1) for ONE
    pair of Lab colours, each any 3-element float64 sequence."""
    L1, a1, b1 = (np.float64(v) for v in np.asarray(lab1, dtype=np.float64).ravel()[:3])
    L2, a2, b2 = (np.float64(v) for v in np.asarray(lab2, dtype=np.float64).ravel()[:3])

    Cbar = 0.5 * (np.hypot(a1, b1) + np.hypot(a2, b2))
    c7 = np.power(Cbar, 7)
    G = 0.5 * (1 - np.sqrt(c7 / (c7 + _25_7)))
    scale = 1 + G
    C1, h1 = _cart2polar_2pi(a1 * scale, b1)
    C2, h2 = _cart2polar_2pi(a2 * scale, b2)

    Lbar = 0.5 * (L1 + L2)
    tmp = np.power(Lbar - 50, 2)
    SL = 1 + 0.015 * tmp / np.sqrt(20 + tmp)
    L_term = (L2 - L1) / (1 * SL)

    Cbar = 0.5 * (C1 + C2)
    SC = 1 + 0.045 * Cbar
    C_term = (C2 - C1) / (1 * SC)

    h_diff = h2 - h1
    h_sum = h1 + h2
    CC = C1 * C2

    dH = h_diff
    if h_diff > _PI:
        dH = dH - _TWO_PI
    if h_diff < -_PI:
        dH = dH + _TWO_PI
    if CC == 0.0:
        dH = np.float64(0.0)
    dH_term = 2 * np.sqrt(CC) * np.sin(dH / 2)

    Hbar = h_sum
    mask = (CC != 0.0) and (np.abs(h_diff) > _PI)
    if mask and h_sum < _TWO_PI:
        Hbar = Hbar + _TWO_PI
    if mask and h_sum >= _TWO_PI:
        Hbar = Hbar - _TWO_PI
    if CC == 0.0:
        Hbar = Hbar * 2
    Hbar = Hbar * 0.5

    T = (
        1
        - 0.17 * np.cos(Hbar - _D30)
        + 0.24 * np.cos(2 * Hbar)
        + 0.32 * np.cos(3 * Hbar + _D6)
        - 0.20 * np.cos(4 * Hbar - _D63)
    )
    SH = 1 + 0.015 * Cbar * T

    H_term = dH_term / (1 * SH)

    c7 = np.power(Cbar, 7)
    Rc = 2 * np.sqrt(c7 / (c7 + _25_7))
    dtheta = _D30 * np.exp(-np.power((np.rad2deg(Hbar) - 275) / 25, 2))
    R_term = -np.sin(2 * dtheta) * Rc * C_term * H_term

    dE2 = np.power(L_term, 2)
    dE2 = dE2 + np.power(C_term, 2)
    dE2 = dE2 + np.power(H_term, 2)
    dE2 = dE2 + R_term
    return float(np.sqrt(np.maximum(dE2, 0)))
