#!/usr/bin/env python
"""Generate the committed synthetic palette-selection fixture
(testdata/photo/fur_ramp.png).

Deterministic by construction (seeded RNG, fixed constants — no per-run
randomness), matching the convention `make_test_logo.py`,
`make_gradient_fixture.py` and `make_photo_region_fixture.py` established,
and honoring the photo plan's own fixture rule F6: goldens must not depend
on found photographs.

Fixture:
  fur_ramp.png    eight spatially separated round patches stepping evenly
                  along ONE color family — a dark-brown -> light-tan sweep,
                  the "fur ramp" of the plan's step-7 accept criterion
                  ("F4 fur ramp = 3-5 shades of one family"). Each patch
                  carries a mild internal radial shade variation (a lit
                  tuft, not a flat disc) plus seeded grain, so the region
                  former has something photographic to chew on, but the
                  patch MEANS sit on the ramp line.

Why the patches are separated by background: SLIC + RAG merging
(stage2_photo_segment) can only merge graph-ADJACENT superpixels, so
background-separated patches are guaranteed to survive as eight distinct
regions regardless of how close their colors are — which is exactly the
setup the palette selector needs to be tested against. Adjacent ramp steps
here measure ~6-8 ΔE00 apart (end-to-end ~58): close enough that per-region
nearest-thread snapping scatters them across ~7 near-duplicate spools
(measured — see digitizer_core/palette.py's docstring), wide enough that
each step is a real shade, not noise.

Why hard-edged circles, unlike region_blobs.png's Gaussian falloff: the
region former's soft-edge behavior is region_blobs' job. THIS fixture tests
palette selection, and a wide falloff halo blends each patch's rim toward
the background color, dragging the region MEANS off the ramp line the test
asserts against. A hard edge keeps each region's mean where the ramp put it
(the 1px anti-alias rim cv2.circle draws is noise-level at r=70).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "testdata" / "photo"

W, H = 900, 500

# BGR (cv2 convention). Background near-white, same neighborhood as
# region_blobs.png's — far enough (ΔE >> bg_tolerance_lab) from even the
# lightest ramp step that stage 1's border flood never eats a patch.
_BG = np.array([240, 245, 245], np.float64)

# The ramp, in RGB: dark brown -> light tan, one family. These are the same
# endpoints palette.py's measured before/after used (its docstring numbers
# were produced from this sweep).
_RAMP_DARK_RGB = np.array([62, 42, 26], np.float64)
_RAMP_LIGHT_RGB = np.array([214, 186, 148], np.float64)
STEPS = 8

RADIUS = 70
# Mild internal shade variation: center at t - SHADE_SPAN/2 along the ramp,
# rim at t + SHADE_SPAN/2. Small on purpose — well inside the region
# former's merge threshold, so each patch stays one region and its mean
# stays at its own ramp position t.
SHADE_SPAN = 0.06

NOISE_SIGMA = 4.0
NOISE_SEED = 0


def _render() -> np.ndarray:
    canvas = np.tile(_BG, (H, W, 1))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # Two rows of four, comfortably separated by background.
    centers = [(130 + 214 * c, 130 + 240 * r) for r in range(2) for c in range(4)]
    for i, (cx, cy) in enumerate(centers):
        t = i / (STEPS - 1)
        rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        inside = rr <= RADIUS
        # Radial position 0 (center) -> 1 (rim), mapped to a small ramp span.
        local_t = np.clip(t + SHADE_SPAN * (rr / RADIUS - 0.5), 0.0, 1.0)
        rgb = _RAMP_DARK_RGB[None, None, :] + \
            (_RAMP_LIGHT_RGB - _RAMP_DARK_RGB)[None, None, :] * local_t[:, :, None]
        bgr = rgb[:, :, ::-1]
        canvas = np.where(inside[:, :, None], bgr, canvas)

    rng = np.random.default_rng(NOISE_SEED)
    noise = rng.normal(0, NOISE_SIGMA, canvas.shape)
    return np.clip(canvas + noise, 0, 255).round().astype(np.uint8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "fur_ramp.png"), _render())
    for f in sorted(OUT.glob("fur_ramp.png")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
