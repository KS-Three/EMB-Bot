#!/usr/bin/env python
"""Generate the committed synthetic gradient-ramp fixtures (testdata/photo/*.png).

Deterministic by construction (no RNG) — pure analytic color ramps, rendered
at 2x supersample and downscaled with INTER_AREA so the shape boundary picks
up a realistic anti-alias halo, matching the convention established by
make_test_logo.py. These are the "gradient" class fixtures (F3/F4) from
docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md: smooth,
structured color ramps that stage0_classify.py must route to `gradient`, not
`flat` (near-zero local Sobel variance) and not `photo_subject`/`photo_scene`
(high local variance). A ramp has low local variance but non-zero, smoothly
and systematically directional gradient magnitude — the property
`gradient_smoothness` is meant to detect.

Fixtures:
  gradient_ramp_linear.png   a single-hue ramp sweeping light -> dark
                             left-to-right across an inset rectangle, on a
                             plain white background.
  gradient_ramp_radial.png   a single-hue ramp sweeping light (center) ->
                             dark (edge) across an inset circle, on a plain
                             white background.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "testdata" / "photo"

S = 2  # supersample factor — only the radial fixture's curved edge needs AA
W, H = 1000, 650
MARGIN = 70


def hue_ramp_endpoints(hue_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Light and dark BGR endpoints that share one HSV hue (cv2 hue is 0-179)."""
    h = hue_deg / 2.0
    light = cv2.cvtColor(np.uint8([[[h, 55, 235]]]), cv2.COLOR_HSV2BGR)[0, 0]
    dark = cv2.cvtColor(np.uint8([[[h, 235, 85]]]), cv2.COLOR_HSV2BGR)[0, 0]
    return light.astype(np.float64), dark.astype(np.float64)


def linear_ramp(w: int, h: int, light: np.ndarray, dark: np.ndarray) -> np.ndarray:
    """Horizontal sweep: light at x=0 -> dark at x=w-1, constant down each column."""
    t = np.linspace(0.0, 1.0, w, dtype=np.float64)[None, :, None]
    return light[None, None, :] * (1 - t) + dark[None, None, :] * t


def radial_ramp(
    w: int, h: int, cx: float, cy: float, radius: float,
    light: np.ndarray, dark: np.ndarray,
) -> np.ndarray:
    """Radial sweep: light at the center -> dark at `radius`, clamped beyond it."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    t = np.clip(r / radius, 0.0, 1.0)[:, :, None]
    return light[None, None, :] * (1 - t) + dark[None, None, :] * t


def to_u8(bgr: np.ndarray) -> np.ndarray:
    return np.clip(bgr, 0, 255).round().astype(np.uint8)


def down(canvas: np.ndarray) -> np.ndarray:
    return cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sw, sh = W * S, H * S
    smargin = MARGIN * S

    # --- gradient_ramp_linear.png: azure hue, sweeps left (light) -> right (dark)
    light, dark = hue_ramp_endpoints(hue_deg=205)  # azure/blue
    bgr = np.full((sh, sw, 3), 255.0, np.float64)
    rect_w, rect_h = sw - 2 * smargin, sh - 2 * smargin
    bgr[smargin:smargin + rect_h, smargin:smargin + rect_w] = linear_ramp(
        rect_w, rect_h, light, dark
    )
    cv2.imwrite(str(OUT / "gradient_ramp_linear.png"), down(to_u8(bgr)))

    # --- gradient_ramp_radial.png: amber hue, sweeps center (light) -> edge (dark)
    light, dark = hue_ramp_endpoints(hue_deg=30)  # amber/orange
    cx, cy = sw / 2.0, sh / 2.0
    radius = min(sw, sh) / 2.0 - smargin
    ramp = radial_ramp(sw, sh, cx, cy, radius, light, dark)
    mask = np.zeros((sh, sw), np.uint8)
    cv2.circle(mask, (int(round(cx)), int(round(cy))), int(round(radius)), 255, -1,
               lineType=cv2.LINE_AA)
    alpha = (mask.astype(np.float64) / 255.0)[:, :, None]
    bgr = ramp * alpha + 255.0 * (1 - alpha)
    cv2.imwrite(str(OUT / "gradient_ramp_radial.png"), down(to_u8(bgr)))

    for f in sorted(OUT.glob("gradient_ramp_*.png")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
