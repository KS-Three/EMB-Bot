"""Byte-identical fast paths for scikit-image calls the pipeline makes
thousands of times per design, or once at great cost.

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
same float, bit for bit.

`rag_mean_color` — profiled 2026-10-27 on the gradient lane: 37-53 s of
Hotel Fremont's and Golden Tee's ~250 s, called once per photo. skimage
builds the graph with `ndi.generic_filter` calling a Python function on every
pixel (3.4M calls on Fremont), then sums colours in an `np.ndindex` loop.
Here the neighbour pairs come from shifted arrays, and the SAME `add_edge`
calls are replayed in the order the filter would have made them (first
discovery of each pair, pixels in C order, footprint in row-major order), so
node order, adjacency order, edge order and `max_id` all match;
`merge_hierarchical` downstream depends on every one of them. Colour sums are
`np.bincount`, which adds in pixel order in float64 like the loop did.
Fremont 41 s -> 0.6 s, and all seven gradient fixtures' designs md5-identical.

`tests/test_fast_skimage.py` checks every helper against skimage itself.
They lean on skimage internals, which is why `scikit-image` is pinned in
`requirements.txt`; the tests are the tripwire for a version bump.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi
from skimage.graph._rag import RAG
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


def rag_mean_color(image, labels, connectivity=2, mode="distance", sigma=255.0):
    """`skimage.graph.rag_mean_color` for a 2-D label image, without the
    per-pixel Python callback. Same RAG, same insertion orders, same floats."""
    labels = np.asarray(labels)
    if labels.ndim != 2:
        raise ValueError("fast rag_mean_color handles 2-D labels only")
    h, w = labels.shape
    # generic_filter hands its callback a float64 buffer, which
    # `_add_edge_filter` casts back with `.astype(int)`; node keys are those.
    lab = labels.astype(np.float64).astype(int)
    offsets = np.argwhere(ndi.generate_binary_structure(2, connectivity)) - 1
    padded = np.pad(lab, 1, mode="edge")  # mode='nearest'
    centres, values, order = [], [], []
    for k, (dr, dc) in enumerate(offsets):
        nb = padded[1 + dr:1 + dr + h, 1 + dc:1 + dc + w]
        idx = np.flatnonzero(nb != lab)
        centres.append(lab.ravel()[idx])
        values.append(nb.ravel()[idx])
        order.append(idx.astype(np.int64) * len(offsets) + k)
    c = np.concatenate(centres)
    v = np.concatenate(values)
    first_seen = np.argsort(np.concatenate(order), kind="stable")
    c, v = c[first_seen], v[first_seen]

    graph = RAG()
    if len(c):
        lo, hi = np.minimum(c, v), np.maximum(c, v)
        pair = lo.astype(np.int64) * (int(hi.max()) + 1) + hi
        _, first = np.unique(pair, return_index=True)
        first.sort()
        for i in first:
            graph.add_edge(c[i], v[i])

    for n in graph:
        graph.nodes[n].update({
            "labels": [n],
            "pixel count": 0,
            "total color": np.array([0, 0, 0], dtype=np.float64),
        })

    flat = labels.ravel()
    counts = np.bincount(flat)
    for label in np.flatnonzero(counts):
        if label not in graph:
            raise KeyError(label)  # skimage's loop fails on it the same way
    pixels = image.reshape(-1, image.shape[-1])
    sums = [np.bincount(flat, weights=pixels[:, ch], minlength=len(counts))
            for ch in range(pixels.shape[1])]
    for n in graph:
        d = graph.nodes[n]
        d["pixel count"] = int(counts[n])
        for ch, s in enumerate(sums):
            d["total color"][ch] = s[n]

    # From here on, skimage's own body verbatim.
    for n in graph:
        graph.nodes[n]["mean color"] = (
            graph.nodes[n]["total color"] / graph.nodes[n]["pixel count"]
        )

    for x, y, d in graph.edges(data=True):
        diff = graph.nodes[x]["mean color"] - graph.nodes[y]["mean color"]
        diff = np.linalg.norm(diff)
        if mode == "similarity":
            d["weight"] = math.e ** (-(diff**2) / sigma)
        elif mode == "distance":
            d["weight"] = diff
        else:
            raise ValueError(f"The mode '{mode}' is not recognised")

    return graph
