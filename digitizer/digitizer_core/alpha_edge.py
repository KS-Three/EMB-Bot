"""The colour under an alpha cutout's transparency, made harmless.

Shared by stage 0 and stage 1, which each decode the file for themselves and
MUST read the same picture (stage 0's own comment on its `_load`). Both apply
this under `cfg.alpha_edge_extend`; stage 1 keeps the file's own colour
aside for the two readers that want it (`Prep.raw_rgb`).
"""
from __future__ import annotations

import cv2
import numpy as np


def extend_opaque_colour(rgb: np.ndarray, alpha: np.ndarray, max_px: int = 0) -> np.ndarray:
    """Every non-opaque pixel takes the RGB of its NEAREST opaque pixel; alpha
    is untouched and the input is not.

    The RGB under an alpha cutout's transparency is whatever the exporter (or
    a browser canvas) left there — the shape lives in alpha — and both of
    stage 1's filters read it: the bilateral denoise and the Lanczos upscale
    blur it into the edge pixels, and stage 0 and stage 2 then read the halo.
    Measured 2026-09-20: Becker's file (one colour everywhere, the shape in
    alpha) reads flat / 18 regions / 8,334 stitches / 59 trims; the SAME
    pixels with black under the alpha read gradient / 151 / 15,318 / 175.
    `cfg.alpha_edge_extend` makes this the image every stage reads, so what
    sits under the alpha stops mattering. Every reader, not only the two
    filters: stage 0's gradient signal and stage 2's segmentation run
    spatial kernels over the whole raster and mask to the artwork
    afterwards, so a kernel on the edge still reads the pixels under the
    alpha (measured 2026-09-20: putting the file's own colour back under
    alpha < 128 after the filters left Becker-with-black-underneath at
    gradient / 146 regions). The two places that deliberately want the
    file's OWN colour under the transparency — `bg_edge_rgb`, stage 2's
    anti-alias endpoint, and preflight's `GROUND_SEWN` border colour — read
    it from `Prep.raw_rgb` instead, which is what stopped the naive
    whole-image fill from sewing Fremont's ground.

    `cv2.distanceTransformWithLabels` with `DIST_LABEL_PIXEL` numbers the
    zero pixels of the mask 1..N in row-major order, so a non-opaque pixel's
    label indexes its nearest opaque one. Returns the input itself when
    nothing is non-opaque or nothing is opaque (nothing to extend from).

    `max_px` > 0 extends only within that many source pixels of the opaque
    edge — the reach of every kernel that reads across it (Sobel 1, the
    bilateral 2, Lanczos4 4, the segmenters' neighbourhoods a few) — and
    leaves what lies further under the alpha as the file has it. Measured
    2026-09-20 (scope-history, the extend addendum): the whole-image
    extension cures Becker and costs drone, a render whose REAL backdrop
    sits under its alpha and whose photo lane reads better with it than with
    hard colour plateaus; the halo is the variant that keeps the cure where
    the kernels reach and the backdrop where they do not.
    """
    opaque = (alpha >= 255).astype(np.uint8)
    if opaque.all() or not opaque.any():
        return rgb
    dist, labels = cv2.distanceTransformWithLabels(
        1 - opaque, cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(opaque)
    src = np.stack([ys, xs], axis=1)[labels - 1]
    out = rgb.copy()
    filled = rgb[src[..., 0], src[..., 1], :3]
    if max_px > 0:
        within = dist <= float(max_px)
        out[within, :3] = filled[within]
    else:
        out[..., :3] = filled
    return out
