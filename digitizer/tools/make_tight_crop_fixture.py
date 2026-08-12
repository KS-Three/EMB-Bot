"""One-off: generate `testdata/photo/tight_crop_pale_subject.png` — the
snowy-owl shape of failure (2026-08-11): a pale subject occupying most of a
tight portrait crop, on a slightly-different pale wall.

Deliberately tuned so the border-ring agreement lands ABOVE the
BACKGROUND_ABSENT threshold (measured 0.827 vs cfg.bg_border_agreement_min
0.75) — only the subject-dominated-border guard (cfg.bg_border_rival_min;
this fixture's rival measures 0.173) can save it, which is exactly what the
fixture exists to pin. Run from `digitizer/`:

    .venv/Scripts/python tools/make_tight_crop_fixture.py testdata/photo/tight_crop_pale_subject.png

Committed output is canonical — regenerate only if the shape of failure
itself needs to change, and re-check the printed signals stay in the zone
the tests document.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import (
    _border_ring, _dominant_border_color, _color_close_mask,
)


def build(path):
    H, W = 600, 480
    wall = (226, 217, 200)   # pale beige wall
    body = (245, 243, 238)   # snowy-owl white
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = wall
    # Tight portrait crop: the body runs through the left/right/bottom border,
    # the head through the top. Wall survives only near the top corners.
    cv2.ellipse(img, (W // 2, int(H * 0.66)), (int(W * 0.70), int(H * 0.58)), 0, 0, 360, body, -1)
    cv2.circle(img, (W // 2, int(H * 0.16)), int(W * 0.47), body, -1)
    dark = (70, 60, 50)
    cv2.circle(img, (int(W * 0.36), int(H * 0.17)), 22, dark, -1)
    cv2.circle(img, (int(W * 0.64), int(H * 0.17)), 22, dark, -1)
    cv2.ellipse(img, (W // 2, int(H * 0.26)), (12, 20), 0, 0, 360, (120, 100, 80), -1)
    for i in range(6):
        y = int(H * (0.48 + 0.08 * i))
        cv2.ellipse(img, (W // 2, y), (int(W * 0.34), 7), 0, 0, 360, (190, 180, 165), 2)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return img


def stats(rgb, cfg):
    if cfg.denoise:
        rgb = cv2.bilateralFilter(rgb, d=5, sigmaColor=30, sigmaSpace=5)
    h, w = rgb.shape[:2]
    ring = _border_ring((h, w))
    bg_color = _dominant_border_color(rgb)
    close = _color_close_mask(rgb, bg_color, cfg.bg_tolerance_lab)
    agreement = float(close[ring].mean())
    rest = rgb[ring & ~close]
    rival = 0.0
    if len(rest):
        binned = rest.reshape(-1, 3).astype(np.int32) // 16
        keys = binned[:, 0] * 65536 + binned[:, 1] * 256 + binned[:, 2]
        _, counts = np.unique(keys, return_counts=True)
        rival = float(counts.max() / ring.sum())
    # corner ownership by the modal color
    k = 8
    owned = sum(
        float(close[ys, xs].mean()) > 0.5
        for ys, xs in [(slice(0, k), slice(0, k)), (slice(0, k), slice(-k, None)),
                       (slice(-k, None), slice(0, k)), (slice(-k, None), slice(-k, None))]
    )
    return agreement, rival, owned


out = Path(sys.argv[1])
img = build(out)
a, r, o = stats(img, PipelineConfig(target_width_mm=80.0))
print(f"agreement={a:.3f} rival={r:.3f} corners_owned_by_modal={o}/4")
