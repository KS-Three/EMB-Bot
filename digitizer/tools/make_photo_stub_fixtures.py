#!/usr/bin/env python
"""Generate the committed synthetic classifier-routing stubs (testdata/photo/*.png).

Deterministic (fixed seeds below — never varies run to run). These are the
F5/F6 "photo_subject" / "photo_scene" stand-ins from Deviation #2 of
docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md: they don't
need to look like real photos, they only need to trip the specific
stage0_classify.py signals that separate photo_subject and photo_scene from
flat/gradient, so step 1's classifier-routing test has fixtures to exercise
before real portrait/pet/scenery art lands at step 3+.

Fixtures:
  photo_subject_stub.png   full-frame per-pixel random color noise -> HIGH
                            unique_color_mass (nearly every pixel differs
                            from its local 3x3 mode), unlike flat art's
                            near-zero and a ramp's smooth local agreement.
  photo_scene_stub.png     a smooth low-frequency diagonal gradient (same
                            family as make_gradient_fixture.py's ramps) with
                            coarse/medium seeded value-noise blobs plus a
                            native-resolution (not upscaled) fine-grain noise
                            layer on top -> moderate, irregular local variance
                            that reads as neither a clean ramp (the upscaled
                            value-noise alone measured LOWER local roughness
                            than a plain gradient — cv2.INTER_CUBIC smooths
                            out exactly the high-frequency component this
                            fixture needs) nor pure per-pixel noise.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "testdata" / "photo"

W, H = 1000, 650

SUBJECT_SEED = 20260802
SCENE_SEED = 20260803


def make_photo_subject_stub() -> np.ndarray:
    """Full-frame per-pixel random color noise (seeded) -> high unique_color_mass."""
    rng = np.random.default_rng(SUBJECT_SEED)
    return rng.integers(0, 256, size=(H, W, 3), dtype=np.uint8)


def _value_noise_octave(
    rng: np.random.Generator, lo_h: int, lo_w: int, amplitude: float,
) -> np.ndarray:
    """Seeded low-res random grid upscaled to (H, W) -> smooth blobby "Perlin-ish"
    noise (classic value-noise trick), not periodic like a raw sine layer."""
    lo = rng.uniform(-1.0, 1.0, size=(lo_h, lo_w))
    hi = cv2.resize(lo, (W, H), interpolation=cv2.INTER_CUBIC)
    return hi * amplitude


def make_photo_scene_stub() -> np.ndarray:
    """Smooth low-freq gradient + multi-octave seeded value-noise texture."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # low-frequency base ramp: diagonal, single hue, light -> dark
    t = np.clip((xx / W + yy / H) / 2.0, 0.0, 1.0)
    light = cv2.cvtColor(np.uint8([[[95, 60, 230]]]), cv2.COLOR_HSV2BGR)[0, 0].astype(np.float64)
    dark = cv2.cvtColor(np.uint8([[[95, 200, 90]]]), cv2.COLOR_HSV2BGR)[0, 0].astype(np.float64)
    base = light[None, None, :] * (1 - t[:, :, None]) + dark[None, None, :] * t[:, :, None]

    # coarse/medium seeded value-noise blobs, deterministic given the fixed
    # seed and call order below. Irregular and non-periodic — unlike a raw
    # sine layer — which gives the image visible scene-like structure at low
    # frequency. On its own this is NOT enough: cv2.resize(..., INTER_CUBIC)
    # upscaling smooths high-frequency content away, so a coarse-grid-only
    # value-noise stack can end up SMOOTHER (lower local pixel-to-pixel
    # roughness) than a plain gradient — measured, not hypothetical: an
    # earlier version of this fixture that stopped here scored a mean
    # abs(pixel - 3x3-blurred) roughness of ~0.26, below both
    # gradient_ramp_linear.png (~0.44) and gradient_ramp_radial.png (~0.33),
    # which defeats the point of a "gradient + texture" stub.
    rng = np.random.default_rng(SCENE_SEED)
    blobs = (
        _value_noise_octave(rng, 14, 9, amplitude=26.0)    # coarse
        + _value_noise_octave(rng, 40, 26, amplitude=14.0)  # medium
    )

    # Fine-grain noise generated DIRECTLY at native (H, W) resolution — no
    # upscale step to smooth it away. This is what actually carries the
    # "moderate higher-frequency texture" signal: it lands the fixture's
    # local roughness at ~7x gradient_ramp_linear.png's, while its amplitude
    # (+/-7 out of 0-255) stays far below photo_subject_stub.png's full-range
    # per-pixel noise, so the gradient + blobs remain the dominant structure.
    fine_grain = rng.uniform(-7.0, 7.0, size=(H, W, 3))

    variation = blobs[:, :, None] + fine_grain
    out = np.clip(base + variation, 0, 255)
    return out.round().astype(np.uint8)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "photo_subject_stub.png"), make_photo_subject_stub())
    cv2.imwrite(str(OUT / "photo_scene_stub.png"), make_photo_scene_stub())

    for f in sorted(OUT.glob("photo_*_stub.png")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
