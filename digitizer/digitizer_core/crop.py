"""Crop the submitted raster to a normalized rectangle, before anything
reads the pixels.

Its own module, imported by BOTH `stage0_classify._load` and
`stage1_prep._load`, for exactly the reason `letterbox.py` is: stage 0
deliberately owns its own decode, so if only one of them cropped, stage 0
would classify a different picture than stage 1 digitizes.

Fractions rather than pixels because the Studio may send either the
customer's original file or its 1,200-px preview (`DigitizePanel.imageToSend`
falls back when the original exceeds the service's limits), and a pixel
rectangle would then address the wrong raster silently, and only for large
uploads.
"""
from __future__ import annotations

import math

import numpy as np

# The smallest frame the downstream background detector can read a border
# from at all: `stage1_prep._border_ring` uses a 2 px ring and
# `_modal_corner_ownership` samples 8 px corners. NOT a physical constant --
# no sew-out settles it; it is a property of those two readers.
MIN_CROP_PX = 16


def validate_crop(crop, shape) -> tuple[int, int, int, int] | None:
    """-> (x0, y0, x1, y1) in `shape`'s pixels, or None when `crop` is None.

    Raises ValueError on a rectangle the caller got wrong. That is a CALLER
    error, not artwork damage, so it must keep its own message -- see
    `digitizer_service/errors.py` on why its map is an allowlist.
    """
    if crop is None:
        return None
    if len(crop) != 4:
        raise ValueError(
            f"crop must be four fractions (x0, y0, x1, y1), got {crop!r}")
    x0f, y0f, x1f, y1f = (float(v) for v in crop)
    # NaN/inf would otherwise surface as "cannot convert float NaN to
    # integer" from the round() below -- true, and useless to a caller. The
    # service rejects these at 400 time; this guards every other caller.
    if not all(math.isfinite(v) for v in (x0f, y0f, x1f, y1f)):
        raise ValueError(f"crop fractions must be finite, got {crop!r}")
    clamp = lambda v: min(max(v, 0.0), 1.0)  # noqa: E731
    x0f, y0f, x1f, y1f = clamp(x0f), clamp(y0f), clamp(x1f), clamp(y1f)
    if x1f <= x0f or y1f <= y0f:
        raise ValueError(f"crop is empty after clamping to [0, 1]: {crop!r}")

    h, w = shape[:2]
    x0, x1 = int(round(x0f * w)), int(round(x1f * w))
    y0, y1 = int(round(y0f * h)), int(round(y1f * h))
    if x1 - x0 < MIN_CROP_PX or y1 - y0 < MIN_CROP_PX:
        raise ValueError(
            f"crop is {x1 - x0}x{y1 - y0} px; at least {MIN_CROP_PX} on each "
            "axis is needed for background detection to read a border")
    return x0, y0, x1, y1


def apply_crop(rgb: np.ndarray, alpha: np.ndarray | None, crop):
    """-> (rgb, alpha) cropped together, or the SAME objects when crop is None.

    Identity on None is load-bearing: `crop=None` must be byte-identical to
    the pre-crop engine everywhere.
    """
    box = validate_crop(crop, rgb.shape)
    if box is None:
        return rgb, alpha
    x0, y0, x1, y1 = box
    out_rgb = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    out_alpha = (np.ascontiguousarray(alpha[y0:y1, x0:x1])
                 if alpha is not None else None)
    return out_rgb, out_alpha
