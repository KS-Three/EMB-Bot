#!/usr/bin/env python
"""Generate the committed synthetic photo-region fixture (testdata/photo/*.png).

Deterministic by construction (seeded RNG, fixed constants — no per-run
randomness), matching the convention `make_test_logo.py` and
`make_gradient_fixture.py` established. This is the step-4 region-former
fixture from
`docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-former.md`:
the direct test of the core claim that SLIC + perceptual region-merging
holds a soft photographic edge as one or two clean regions where naive
per-pixel color clustering dithers it into salt-and-pepper speckle.

Fixtures:
  region_blobs.png   three overlapping Gaussian-falloff color blobs (red,
                      green, blue), each with its own internal radial shade
                      gradient (peak color at the center fading to a paler
                      tint at its edge) — a broad, many-pixel-wide smooth
                      color sweep, not just a 1-2px anti-alias halo. That
                      breadth is what a per-pixel k-means fragments into
                      concentric quantization bands, and band EDGES are
                      where the grain noise below tips per-pixel cluster
                      assignment back and forth into visible speckle.

Why there is noise, unlike the (RNG-free) gradient-ramp fixtures: a clean
analytic gradient assigns to k-means clusters in monotonic order along the
gradient direction — ordered bands, not speckle. Speckle is a real
photographic artifact (sensor grain interacting with quantization near a
cluster boundary), so reproducing it here needs an actual per-pixel
perturbation, not just softness. The seeded grain below supplies that.

Noise is scaled by each pixel's total blob "coverage" (1 - product of each
blob's own (1-alpha), i.e. how much of the pixel's color is blob-influenced
rather than pure background), floored at COVERAGE_FLOOR rather than let to
reach zero. Un-floored, noise vanishes at zero coverage — clean, and correct,
except that stage1_prep's border-flood background detection then reads a few
of the ~zero-coverage halo pixels as marginally off-background anyway (float
rounding at the tail of the Gaussian), and an UNSCALED noise floor at exactly
0 made a handful of those pixels cross `cfg.bg_tolerance_lab` and register as
foreground with no blob neighbor to be absorbed into — isolated 1-pixel
"islands" purely of measurement noise. `resolve_small_regions`'
`small_shape_rescue` policy (correctly) keeps isolated small shapes rather
than silently dropping them, so those measurement-noise islands survived
segmentation as their own tiny regions, both inflating the region count and
failing the erosion-cleanliness check on a region that was never meant to
exist. COVERAGE_FLOOR=0.12 keeps grain visible through the whole blob-to-
background transition (where dithering is the realistic risk) while making
the pure-background tail's noise small enough to stay inside
`bg_tolerance_lab` — measured empirically against this exact fixture, see
`stage2_photo_segment.py`'s own tuning notes for the region-count numbers
this produced.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "testdata" / "photo"

W, H = 900, 600

# BGR (cv2 convention, matching make_test_logo.py's palette style).
_BG = np.array([245, 245, 240], np.float64)

# Three overlapping blobs: distinct hues (red / green / blue) far enough
# apart in Lab that they never merge into each other at the merge threshold
# stage2_photo_segment.py uses, each with its own peak -> edge shade gradient
# (a soft "lit sphere" look) so there is real intra-blob color variation for
# a naive per-pixel method to fragment.
_BLOBS = [
    {"c": (300, 220), "r": 150,
     "peak": np.array([40, 40, 200], np.float64),
     "edge": np.array([140, 120, 225], np.float64)},
    {"c": (560, 260), "r": 150,
     "peak": np.array([60, 150, 50], np.float64),
     "edge": np.array([150, 210, 140], np.float64)},
    {"c": (430, 400), "r": 150,
     "peak": np.array([190, 80, 40], np.float64),
     "edge": np.array([225, 160, 120], np.float64)},
]

# Grain noise: std-dev in 0-255 BGR units, seeded for determinism. See the
# module docstring for why noise exists at all (reproducing dithering, not
# just softness) and why it is coverage-scaled rather than uniform.
NOISE_SIGMA = 6.0
NOISE_SEED = 0
COVERAGE_FLOOR = 0.12


def _render() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    canvas = np.tile(_BG, (H, W, 1))
    coverage = np.zeros((H, W), np.float64)
    for b in _BLOBS:
        cx, cy = b["c"]
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        t = np.clip(r / b["r"], 0.0, 1.0)
        color = b["peak"][None, None, :] * (1 - t)[:, :, None] + \
            b["edge"][None, None, :] * t[:, :, None]
        sigma = b["r"] / 2.0
        alpha = np.exp(-(r ** 2) / (2 * sigma ** 2))
        coverage = 1 - (1 - coverage) * (1 - alpha)
        alpha3 = alpha[:, :, None]
        canvas = canvas * (1 - alpha3) + color * alpha3

    rng = np.random.default_rng(NOISE_SEED)
    noise_scale = np.clip(coverage, COVERAGE_FLOOR, 1.0)
    noise = rng.normal(0, NOISE_SIGMA, canvas.shape) * noise_scale[:, :, None]
    return np.clip(canvas + noise, 0, 255).round().astype(np.uint8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "region_blobs.png"), _render())
    for f in sorted(OUT.glob("region_blobs.png")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
