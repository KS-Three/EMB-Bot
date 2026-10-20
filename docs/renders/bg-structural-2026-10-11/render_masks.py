"""Before/after stage-1 background masks for `cfg.bg_structural`.

Run from `digitizer/`:
    python ../docs/renders/bg-structural-2026-10-11/render_masks.py

For each fixture, one sheet: source | OFF mask | ON mask. Removed background
is painted magenta over the source; the caption carries the stage-1 verdict
and the share of the canvas removed. Every fixture whose stage-1 verdict or
mask moves under the flag at the shipped tolerance is drawn, plus
summit_badge at tolerance 4.5, where OFF flips to BACKGROUND_ABSENT.
"""
import dataclasses
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.stage1_prep import prep  # noqa: E402

OUT = Path(__file__).resolve().parent
PANEL_W = 420
CASES = [
    ("summit_badge", "testdata/photo/summit_badge.png", 6.0),
    ("summit_badge_tol4.5", "testdata/photo/summit_badge.png", 4.5),
    ("toat_beanie_tol3.0", "testdata/art/logo_toat_beanie.png", 3.0),
    ("chrome_specular", "testdata/photo/photo_chrome_specular.png", 6.0),
    ("repro_gradient_white_icon", "testdata/photo/repro_gradient_white_icon.png", 6.0),
    ("region_blobs", "testdata/photo/region_blobs.png", 6.0),
]


def verdict(p) -> str:
    codes = [w["code"] for w in p.warnings]
    if "BACKGROUND_ABSENT" in codes:
        return "BACKGROUND_ABSENT"
    if any(w.get("reason") == "subject_dominated_border" for w in p.warnings):
        return "subject_dominated"
    return "background"


def panel(rgb: np.ndarray, mask: np.ndarray | None, caption: str) -> np.ndarray:
    img = rgb.copy()
    if mask is not None:
        img[mask] = (0.35 * img[mask] + 0.65 * np.array([255, 0, 200])).astype(np.uint8)
    h, w = img.shape[:2]
    img = cv2.resize(img, (PANEL_W, int(round(h * PANEL_W / w))), interpolation=cv2.INTER_AREA)
    bar = np.full((34, PANEL_W, 3), 255, np.uint8)
    cv2.putText(bar, caption, (6, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def main() -> None:
    for name, path, tol in CASES:
        base = dataclasses.replace(PipelineConfig(), bg_tolerance_lab=tol)
        off = prep(path, base)
        on = prep(path, dataclasses.replace(base, bg_structural=True))
        tiles = [
            panel(off.rgb, None, f"source  (tol {tol:g})"),
            panel(off.rgb, off.bg_mask, f"OFF {verdict(off)} {off.bg_mask.mean():.1%}"),
            panel(on.rgb, on.bg_mask, f"ON  {verdict(on)} {on.bg_mask.mean():.1%}"),
        ]
        sheet = np.hstack(tiles)
        cv2.imwrite(str(OUT / f"{name}.png"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
        print(name, verdict(off), round(float(off.bg_mask.mean()), 4),
              verdict(on), round(float(on.bg_mask.mean()), 4))


if __name__ == "__main__":
    main()
